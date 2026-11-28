"""Should the critical edge be scanned in finer Qz steps?  Known truth, calculated only (no data).

Today every edge is scanned in steps of 0.001 1/A from 0.016 to 0.030, so a resolution of sigma_Q ~ 4e-4 touches
only the two points beside the edge (docs/studies/qoff_resolution_real/, section 6).  Here synthetic bare-water
edges are blurred by the beam's own core + tail resolution (focus at S1; docs/studies/focus_and_resolution/) plus
a known extra Gaussian, sampled three ways:
  now      0.001 everywhere;
  fine 2x  0.0005 from 0.019 to 0.025, 0.001 elsewhere;
  fine 4x  0.00025 from 0.019 to 0.025, 0.001 elsewhere;
each with two time budgets: the same counting time per point (the scan gets longer), or the same total time
(each point's error grows as sqrt(points / points now)).  Two truths:
  beam     the beam's core + tail and an extra Gaussian of 0.8e-4 (the real edges' median);
  soft     the same, with the edge itself softer (absorption 3 x water's), standing in for the unexplained
           rounding of the real edges (the best-fitting variant of qoff_resolution_real).
Each edge is fitted by three models, with water's absorption: one Gaussian, the beam + a free Gaussian, and the
beam with its tail fraction free (lss_core.fresnel pieces, as on the real edges).

    python tests/tools/edge_sampling_study.py --out docs/studies/focus_and_resolution
"""
import argparse
import json
import os
import sys
import textwrap
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import numpy as np                                    # noqa: E402

TRUE_EXTRA = 0.8e-4
SAMPLINGS = (('now', 0.001), ('fine 2x', 0.0005), ('fine 4x', 0.00025))
BUDGETS = ('same time per point', 'same total time')
TRUTHS = (('beam', 1.0), ('soft', 3.0))
MODELS = ('gauss', 'beam', 'free_frac')
LABEL = {'gauss': 'one Gaussian', 'beam': 'beam + free Gaussian', 'free_frac': 'beam, tail fraction free'}


def grid(step):
    lo = np.arange(0.016, 0.019 - 1e-9, 0.001)
    mid = np.arange(0.019, 0.025 + 1e-9, step)
    hi = np.arange(0.026, 0.030 + 1e-9, 0.001)
    return np.round(np.concatenate([lo, mid, hi]), 6)


def fit(q, r, s):
    """The three models on one edge: five free parameters each (ln N, Qoff, one shape parameter, a, b)."""
    import math
    from scipy.optimize import least_squares
    from lss_core import fresnel as F
    import focus_cases_resolution as FC
    base, K, qc, beta, E = FC.beam_resolution(), FC.K, FC.QC, FC.BETA, FC.E
    qq, ly, sl = F._prepare(q, r, s, F.EDGE_Q_MAX, F.EDGE_Q_MIN * qc)
    u = (qq - qc) / qc

    def mix(qoff, frac, sx):
        out = 0.0
        for w, th in ((1 - frac, base['core']), (frac, base['tail'])):
            if w > 0:
                out = out + w * F.fresnel_smeared(qq + qoff, qc, math.hypot(K * th * 1e-6, sx), beta, E)
        return out
    spec = {'gauss': (lambda qo, x: F.fresnel_smeared(qq + qo, qc, x, beta, E), (0.0, 2e-3), (1.5e-4, 3.8e-4, 8e-4), 1e-4),
            'beam': (lambda qo, x: mix(qo, base['frac'], x), (0.0, 2e-3), (0.0, 1e-4, 3e-4), 1e-4),
            'free_frac': (lambda qo, x: mix(qo, x, 0.0), (0.0, 1.0), (0.1, 0.25, 0.5), 0.1)}
    res = {}
    lnn0 = float(np.median(ly[qq < qc - 1e-3]))
    for name in MODELS:
        fn, (blo, bhi), starts, xs = spec[name]

        def model(p):
            lnn, qoff, x, a, b = p
            return lnn + np.log(np.clip(fn(qoff, x), 1e-300, None)) + np.log(np.clip(1 + a * u + b * u * u, 1e-12, None))
        best = None
        for x0 in starts:
            rr = least_squares(lambda p: (ly - model(p)) / sl, [lnn0, -1e-4, x0, 0.0, 0.0],
                               bounds=([-np.inf, F.QOFF_BOUNDS[0], blo, -np.inf, -np.inf],
                                       [np.inf, F.QOFF_BOUNDS[1], bhi, np.inf, np.inf]),
                               loss='soft_l1', f_scale=2.0, diff_step=1e-6, x_scale=[1.0, 1e-4, xs, 1.0, 1.0])
            if best is None or rr.cost < best.cost:
                best = rr
        res[name] = dict(qoff=float(best.x[1]), x=float(best.x[2]), chi2=float(np.sum(best.fun ** 2) / (len(qq) - 5)))
    return res


def one(job):
    import focus_cases_resolution as FC
    truth, bscale, samp, step, budget, i = job
    import zlib
    rng = np.random.default_rng(zlib.crc32(('%s|%s|%s|%d' % (truth, samp, budget, i)).encode()))
    q = grid(step)
    qoff = -1.6e-4 + rng.uniform(-5e-4, 5e-4)
    r = FC.reflect(q, qoff, FC.beam_resolution(), TRUE_EXTRA, FC.BETA * bscale) * (1 + 0.05 * (q - FC.QC) / FC.QC)
    e = FC.rel_error(q)
    if budget == 'same total time':
        e = e * np.sqrt(len(q) / len(grid(0.001)))
    rr = r * (1 + rng.normal(0, e))
    out = fit(q, rr, rr * e)
    out.update(truth=truth, sampling=samp, budget=budget, true_qoff=qoff, points=int(len(q)),
               near_edge=int(np.sum(np.abs(q - (FC.QC - qoff)) < 1e-3)))
    return out


def summarise(rows):
    S = {}
    for t, _ in TRUTHS:
        for s, _ in SAMPLINGS:
            for b in BUDGETS:
                v = [r for r in rows if r['truth'] == t and r['sampling'] == s and r['budget'] == b]
                d = dict(n=len(v), points=v[0]['points'], near_edge=float(np.median([r['near_edge'] for r in v])))
                for m in MODELS:
                    x = np.array([r[m]['x'] for r in v])
                    dq = np.array([r[m]['qoff'] - r['true_qoff'] for r in v])
                    d[m] = dict(x_median=float(np.median(x)), x_robust_sd=float(1.4826 * np.median(np.abs(x - np.median(x)))),
                                x_p10=float(np.percentile(x, 10)), x_p90=float(np.percentile(x, 90)),
                                at_zero=float(np.mean(x < 2e-6)) if m != 'free_frac' else float(np.mean(x < 1e-3)),
                                qoff_bias=float(np.median(dq)), qoff_robust_sd=float(1.4826 * np.median(np.abs(dq - np.median(dq)))),
                                chi2_median=float(np.median([r[m]['chi2'] for r in v])))
                d['beam_beats_gauss'] = float(np.mean([r['beam']['chi2'] < r['gauss']['chi2'] for r in v]))
                S['%s|%s|%s' % (t, s, b)] = d
    return S


def figure(S, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import focus_cases_resolution as FC
    FC.style()
    INK, GREY, BLUE, AQUA, ORANGE = FC.INK, FC.GREY, FC.BLUE, FC.AQUA, FC.ORANGE
    k = lambda t, s, b: S['%s|%s|%s' % (t, s, b)]
    xs = np.arange(len(SAMPLINGS))
    names = [s for s, _ in SAMPLINGS]
    b0, b1 = BUDGETS
    fig, ax = plt.subplots(2, 2, figsize=(13.5, 10))
    fig.subplots_adjust(left=0.08, right=0.97, top=0.83, bottom=0.13, hspace=0.55, wspace=0.28)
    sd_now = k('beam', 'now', b0)['beam']['x_robust_sd']
    sd_f4 = k('beam', 'fine 4x', b0)['beam']['x_robust_sd']
    sd_f4t = k('beam', 'fine 4x', b1)['beam']['x_robust_sd']
    fig.text(0.04, 0.955, textwrap.fill(
        'Finer steps through the edge let the scan tell the edge\'s shape: a wrong model\'s χ²/dof grows %.0f× while '
        'the right one stays at 1. They pin the extra width %.1f–%.1f× better, but one Gaussian stays biased at any '
        'step' % (k('beam', 'fine 4x', b0)['gauss']['chi2_median'] / k('beam', 'now', b0)['gauss']['chi2_median'],
                  sd_now / sd_f4t, sd_now / sd_f4), 120), fontsize=12, fontweight='bold', color=INK,
        va='top')
    fig.text(0.04, 0.875, 'Calculated: synthetic bare-water edges, the beam\'s core + tail (focus at S1) plus an extra '
             'Gaussian of %.1f × 10⁻⁴ Å⁻¹; counting errors as on the real edges; finer steps from 0.019 to 0.025 Å⁻¹.'
             % (TRUE_EXTRA * 1e4), fontsize=9, color=GREY)

    a = ax[0, 0]
    rng = np.random.default_rng(0)
    qf = np.linspace(0.0175, 0.0265, 900)
    a.plot(qf, FC.reflect(qf, -1.6e-4, FC.beam_resolution(), TRUE_EXTRA), color=INK, lw=1.2)
    for j, (s, st) in enumerate(SAMPLINGS):
        q = grid(st)
        q = q[(q > 0.0175) & (q < 0.0265)]
        a.plot(q, FC.reflect(q, -1.6e-4, FC.beam_resolution(), TRUE_EXTRA) * (1 - 0.12 * j), 'o', ms=4,
               color=(GREY, BLUE, AQUA)[j], label='%s: %d points within ±0.001 of the edge' % (s, k('beam', s, b0)['near_edge']))
        _ = rng
    a.set(xlabel='Qz (Å⁻¹)', ylabel='R (offset down for each sampling)', yscale='log')
    a.legend(fontsize=7.5, frameon=False, loc='lower left')
    a.set_title('A. The three samplings: today only two points sit beside the edge', fontsize=9.5)

    a = ax[0, 1]
    for m, c, mk in (('beam', BLUE, 'o'), ('free_frac', AQUA, 's')):
        for b, ls in ((b0, '-'), (b1, '--')):
            v = [k('beam', s, b)[m]['x_robust_sd'] * (1e4 if m == 'beam' else 1) for s in names]
            a.plot(xs, v, ls, marker=mk, color=c, label='%s: %s, %s' % (LABEL[m], 'extra ×10⁻⁴' if m == 'beam' else 'tail fraction', b))
    a.set_xticks(xs)
    a.set_xticklabels(names)
    a.set(ylabel='scatter of the fitted value between edges (robust SD)', ylim=(0, None))
    a.legend(fontsize=7, frameon=False, loc='upper right')
    a.set_title('B. How precisely one edge pins the beam\'s shape parameters', fontsize=9.5)

    a = ax[1, 0]
    for m, c, mk in (('gauss', GREY, 'D'), ('beam', BLUE, 'o')):
        for b, ls in ((b0, '-'), (b1, '--')):
            med = [k('beam', s, b)[m]['x_median'] * 1e4 for s in names]
            a.plot(xs, med, ls, marker=mk, color=c, label='%s, %s' % (LABEL[m], b))
    a.axhline(TRUE_EXTRA * 1e4, color=INK, ls=':', lw=1)
    a.text(1.0, TRUE_EXTRA * 1e4 + 0.08, 'true extra %.1f' % (TRUE_EXTRA * 1e4), fontsize=7.5, color=INK, ha='center')
    a.set_xticks(xs)
    a.set_xticklabels(names)
    a.set(ylabel='median fitted width (10⁻⁴ Å⁻¹)', ylim=(0, 3.6))
    a.legend(fontsize=7, frameon=False, loc='center right')
    a.set_title('C. One Gaussian reads the same σ_Q at any sampling: finer steps do not fix\n'
                'the wrong shape, the beam model is unbiased at all of them', fontsize=9.5)

    a = ax[1, 1]
    for t, c in (('beam', BLUE), ('soft', ORANGE)):
        for m, mk in (('beam', 'o'), ('gauss', 'D')):
            v = [k(t, s, b0)[m]['chi2_median'] for s in names]
            a.plot(xs, v, '-' if m == 'beam' else '--', marker=mk, color=c, mec=c, mfc='white' if m == 'gauss' else c,
                   label='truth %s, fitted by %s' % ('beam' if t == 'beam' else 'softer edge', LABEL[m]))
    a.axhline(1, color=INK, lw=0.6)
    a.set_xticks(xs)
    a.set_xticklabels(names)
    a.set(ylabel='median χ²/dof (same time per point)', yscale='log')
    a.legend(fontsize=7, frameon=False, loc='upper left')
    a.set_title('D. Can the scan tell the beam from a softer edge? χ²/dof grows with\n'
                'the points through the edge only when the model is wrong', fontsize=9.5)
    fig.text(0.04, 0.06, textwrap.fill(
        'Model: R_F of water (β 5.2e-9) blurred by the beam\'s core %.1f µrad and tail %.1f µrad (fraction %.2f), each '
        'widened by the extra Gaussian; a smooth factor 1 + 0.05 u; %d edges per condition, Qoff uniform in −6.6 to '
        '+3.4 × 10⁻⁴. "Softer edge": absorption 3 × water\'s in the truth only. Same total time: each point\'s error × '
        '√(points / 15). Robust SD = 1.4826 × MAD.' % (FC.beam_resolution()['core'], FC.beam_resolution()['tail'],
                                                         FC.beam_resolution()['frac'], k('beam', 'now', b0)['n']), 190),
        fontsize=7.5, color=GREY, va='top')
    p = os.path.join(out, 'F4_finer_edge_sampling.png')
    fig.savefig(p)
    plt.close(fig)
    print('wrote', p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/focus_and_resolution')
    ap.add_argument('--n', type=int, default=60, help='synthetic edges per condition')
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    jobs = [(t, bs, s, st, b, i) for t, bs in TRUTHS for s, st in SAMPLINGS for b in BUDGETS for i in range(a.n)]
    with Pool(a.workers) as pool:
        rows = pool.map(one, jobs, chunksize=4)
    S = summarise(rows)
    json.dump(S, open(os.path.join(a.out, 'sampling.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    figure(S, a.out)
    for key, d in S.items():
        print(key, 'pts', d['points'], ' '.join('%s x %.3g±%.2g chi2 %.1f qsd %.2g' % (m, d[m]['x_median'], d[m]['x_robust_sd'],
                                                                                       d[m]['chi2_median'], d[m]['qoff_robust_sd'])
                                               for m in MODELS))


if __name__ == '__main__':
    main()
