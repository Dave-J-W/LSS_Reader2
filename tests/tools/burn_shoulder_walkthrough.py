"""The GID burn estimators on a peak with a shoulder (P44), from the raw
frames to the judgment, step by step, for the walkthrough
(docs/studies/burn_shoulder/walkthrough.md; the owner's standing order of
2026-11-25: "the entire chain of data processing, ending with the
statistics and judgment ... data fit examples, explanations of
statistics, all ELI5").

Public data only: the NX school GID burn 15 (and 14 for the verdicts),
and synthetic burns with a known truth (calibration).

Figures (``--out``):
- BW1 the raw data: frame 0 of burn 15 with the rows summed, and the line
  cut of the first and last frame with the window;
- BW2 the split: the mean frame in the window, less its chord; the
  Gaussian and line fitted beside the peak; the shoulder and the peak;
- BW3 one frame fitted: the last frame of burn 15 under the template and
  under the split, each over its data, with the residuals in error bars;
- BW4 one number per frame: burn 15's intensity and FWHM per frame under
  both, with the constant and the line through them, and the split's
  shoulder amplitude per frame;
- BW5 the verdict: how much better a sloped line describes each
  estimator's intensities than a flat one (ΔAICc), burns 14 and 15;
- BW6 calibration: 60 synthetic NX 15-like burns (FWHM +20 %, intensity
  −13 %), each estimator's 95 % interval of the intensity change against
  the truth.

    python tests/tools/burn_shoulder_walkthrough.py --out docs/studies/burn_shoulder/walkthrough
"""
import argparse
import json
import math
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))
os.chdir(ROOT)

import numpy as np                                    # noqa: E402

from lss_core import burn, trends                      # noqa: E402

NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
CT, CS = '#1f6fb4', '#c0392b'           # template, split
SCAN = 15


def plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as p
    return p


def nx_burns():
    import tempfile
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp())
    from lss_core.experiment import Experiment
    e = Experiment(NX)
    return e, {(s, est): e.burn(s, estimator=est) for s in (14, 15) for est in ('template', 'split')}


def bw1(out, e, r):
    """The raw data: frame 0 of burn 15, the summed rows, the line cuts."""
    from lss_core import images
    p = plt()
    fr = [f for f in e.frames([SCAN]) if f.index == 0][0]
    img = np.asarray(images.read_pilatus(fr.path), float)
    fig, (a, b) = p.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1]))
    a.imshow(np.log10(np.maximum(img, 0.5)), origin='lower', aspect='auto', cmap='viridis')
    lo, hi = r.rows
    for y in (lo, hi):
        a.axhline(y, color='w', lw=1)
    a.set_title('(a) Burn %d, frame 0: counts per pixel (log scale)\nrows %d–%d between the white lines are summed'
                % (SCAN, lo, hi), fontsize=9)
    a.set_xlabel('detector column')
    a.set_ylabel('detector row')
    p0, p1 = r.profiles[0], r.profiles[-1]
    b.errorbar(p0[:, 0], p0[:, 1], p0[:, 2], fmt='.', ms=3, color='0.4', label='frame 0 (first)')
    b.errorbar(p1[:, 0], p1[:, 1], p1[:, 2], fmt='.', ms=3, color=CS, label='frame %d (last)' % (len(r.profiles) - 1))
    w0, w1 = r.window
    b.axvspan(w0, w1, color='orange', alpha=0.15, label='window: 3 FWHM either side of the peak')
    b.set_yscale('log')
    b.set_xlabel('Qxy (Å⁻¹)')
    b.set_ylabel('counts per monitor (summed rows)')
    b.set_title('(b) The line cut: each column summed over the rows, ± √counts', fontsize=9)
    b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW1_raw_frame_and_cut.png'), dpi=130)
    p.close(fig)
    sel = (p0[:, 0] >= w0) & (p0[:, 0] <= w1)
    k = int(np.argmax(np.where(sel, p0[:, 1], -np.inf)))
    peak_counts = float((p0[k, 1] / p0[k, 2]) ** 2)          # counts = (value / σ)² for counting noise
    return dict(rows=[int(lo), int(hi)], window=[float(w0), float(w1)], frames=len(r.profiles),
                points_in_window=int(np.sum(sel)), peak_counts_frame0=peak_counts)


def bw2(out, r):
    """The split of the mean frame: chord, shape, the shoulder fit beside the peak, S and P."""
    p = plt()
    ref = r.reference
    x = ref['x']
    mean = np.mean([q[:, 1] for q in r.profiles], axis=0)
    sel = (r.profiles[0][:, 0] >= r.window[0]) & (r.profiles[0][:, 0] <= r.window[1])
    mw = mean[sel]
    chord = mw - ref['shape']
    h, m, sg = ref['shoulder']
    c0, w0 = (ref['found']['centre'], ref['found']['fwhm']) if ref['found'] else (ref['centre'], ref['fwhm'])
    beside = np.abs(x - c0) > burn.SPLIT_CORE * w0
    S = h * np.exp(-0.5 * ((x - m) / sg) ** 2)
    line = ref['shape'] - S - ref['peak']
    fig, (a, b, c) = p.subplots(1, 3, figsize=(14, 4.2))
    a.plot(x, mw, 'k.', ms=4, label='mean of the %d frames' % len(r.profiles))
    a.plot(x, chord, '--', color='0.5', label='chord: the straight line through\nthe first and last 3 points')
    a.set_title('(a) The mean frame in the window, and its chord', fontsize=9)
    b.plot(x[~beside], ref['shape'][~beside], '.', color='0.7', ms=4, label='shape = mean − chord (the core)')
    b.plot(x[beside], ref['shape'][beside], 'o', color='C2', ms=3.5,
           label='beside the peak (> %.1f FWHM away):\nfitted by a Gaussian + a line' % burn.SPLIT_CORE)
    b.plot(x, S + line, '-', color='C2', lw=1.2, label='the fitted Gaussian + line')
    b.set_title('(b) The shoulder is fitted where the peak is not', fontsize=9)
    c.plot(x, ref['shape'], '.', color='0.6', ms=4, label='shape')
    c.plot(x, S, '-', color='C2', lw=1.5, label='S: the shoulder (σ %.4f Å⁻¹)' % sg)
    c.plot(x, ref['peak'], '-', color=CS, lw=1.5,
           label='P: the peak = shape − S − line\n(FWHM %.4f Å⁻¹)' % ref['peak_fwhm'])
    c.plot(x, line, '--', color='0.4', lw=1.0, label="the line: goes to each frame's\nown straight background")
    c.set_title('(c) The two parts the split fits to each frame', fontsize=9)
    for ax in (a, b, c):
        ax.set_xlabel('Qxy (Å⁻¹)')
        ax.legend(fontsize=7)
        ax.tick_params(labelsize=8)
    a.set_ylabel('counts per monitor')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW2_the_split.png'), dpi=130)
    p.close(fig)
    return dict(shoulder_height=h, shoulder_centre=m, shoulder_sigma=sg,
                shoulder_fwhm=sg * 2 * math.sqrt(2 * math.log(2)),
                peak_fwhm=ref['peak_fwhm'], peak_centre=ref['peak_centre'], template_fwhm=ref['fwhm'],
                points_beside=int(np.sum(beside)), shoulder_share_of_shape=float(np.sum(S) / np.sum(ref['shape'])))


def bw3(out, rt, rs, k=-1):
    """One frame (the last of burn 15) under the template and the split: fit over data, residuals."""
    p = plt()
    k = k % len(rt.profiles)
    prof = rt.profiles[k]
    fig, axes = p.subplots(2, 2, figsize=(12, 6.2), sharex=True, gridspec_kw=dict(height_ratios=[2.2, 1]))
    nums = {}
    for col, (r, name, colour) in enumerate(((rt, 'template', CT), (rs, 'split', CS))):
        ref, d = r.reference, r.frame_fits[k]
        x = ref['x']
        sel = (prof[:, 0] >= r.window[0]) & (prof[:, 0] <= r.window[1])
        y, s = prof[sel, 1], prof[sel, 2]
        drawn = burn.frame_model(ref, d, x)
        total = drawn[0] if name == 'split' else drawn
        a, b = axes[0, col], axes[1, col]
        a.errorbar(x, y, s, fmt='.', color='k', ms=3, lw=0.6, label='frame %d, ± √counts' % k)
        a.plot(x, total, '-', color=colour, lw=1.6, label='%s fit' % name)
        if name == 'split':
            pk, sh, bg = drawn[1]
            a.plot(x, pk + bg, ':', color=CS, lw=1, label='peak (stretched) + background')
            a.plot(x, sh + bg, '--', color='C2', lw=1, label='shoulder (not stretched) + background')
        res = (y - total) / s
        b.bar(x, res, width=0.8 * float(np.median(np.diff(x))), color=colour)
        b.axhline(0, color='k', lw=0.6)
        for v in (-2, 2):
            b.axhline(v, color='0.6', lw=0.5, ls='--')
        P = d['params']
        dof = len(x) - len(P)
        a.set_title('%s: χ²/dof = %.2f (%d points, %d parameters)' % (name, d['chi2_dof'], len(x), len(P)), fontsize=9)
        a.legend(fontsize=7)
        b.set_xlabel('Qxy (Å⁻¹)')
        b.set_ylabel('(data − fit) / σ', fontsize=8)
        nums[name] = dict(chi2_dof=d['chi2_dof'], dof=dof, A=float(P[0]), delta=float(P[1]), w=float(P[2]),
                          B=float(P[3]) if name == 'split' else None,
                          worst=float(np.max(np.abs(res))), beyond_2sigma=int(np.sum(np.abs(res) > 2)))
    axes[0, 0].set_ylabel('counts per monitor')
    fig.suptitle('BW3. The last frame of burn %d, fitted two ways (residuals: each point\'s miss in its own error bars)'
                 % SCAN, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW3_one_frame_fitted.png'), dpi=130)
    p.close(fig)
    nums['frame'] = k
    nums['mean_chi2_dof'] = {n: float(np.mean([d['chi2_dof'] for d in r.frame_fits if d.get('ok')]))
                             for n, r in (('template', rt), ('split', rs))}
    return nums


def _change(c, T, relative=True):
    from burn_shoulder_study import change_of
    return change_of(c.fits.get('linear'), T, relative)


def bw4(out, rt, rs):
    """Burn 15 per frame: intensity and FWHM (template and split, each relative to its line at t = 0), B."""
    p = plt()
    fig, axes = p.subplots(1, 3, figsize=(14, 4.2))
    tt = np.linspace(0, rt.duration(), 100)
    nums = {}
    for ax, q in zip(axes[:2], ('intensity', 'fwhm')):
        for r, name, colour in ((rt, 'template', CT), (rs, 'split', CS)):
            c = r.trends[q]
            lin, con = c.fits['linear'], c.fits['constant']
            ref = float(lin(np.array([0.0]))[0])
            y, s = c.y / ref, c.sigma / ref
            ax.errorbar(c.t, y, s, fmt='o', ms=3, color=colour, lw=0.7, label='%s (errors from the scatter)' % name)
            ax.plot(tt, lin(tt) / ref, '-', color=colour, lw=1.4)
            ax.plot(tt, con(tt) / ref, ':', color=colour, lw=1.0)
            v, e = _change(c, r.duration())
            nums['%s_%s' % (name, q)] = dict(change=v, sigma=e, stable=bool(c.stable),
                                             delta_aicc=float(c.delta_constant_linear),
                                             scatter_factor=float(c.scatter_factor or math.nan))
        ax.set_xlabel('time by the clock (s)')
        ax.set_ylabel('%s / the line\'s value at t = 0' % ('intensity' if q == 'intensity' else 'FWHM'))
        ax.set_title('(%s) %s per frame: lines (solid) and constants (dotted)'
                     % ('a' if q == 'intensity' else 'b', 'Intensity' if q == 'intensity' else 'FWHM'), fontsize=9)
        ax.legend(fontsize=7)
    b = np.array([d['shoulder'] for d in rs.frame_fits])
    ax = axes[2]
    ax.errorbar(rs.t, b[:, 0], b[:, 1], fmt='o', ms=3, color='C2', lw=0.7)
    ax.axhline(1, color='k', lw=0.6, ls='--')
    ax.set_xlabel('time by the clock (s)')
    ax.set_ylabel('B: the shoulder\'s amplitude (1 = the mean frame\'s)')
    ax.set_title('(c) The split\'s shoulder per frame (± counting σ)', fontsize=9)
    c = rs.trends['shoulder']
    v, e = _change(c, rs.duration())
    nums['split_shoulder'] = dict(change=v, sigma=e, stable=bool(c.stable), b_min=float(b[:, 0].min()),
                                  b_max=float(b[:, 0].max()))
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW4_per_frame.png'), dpi=130)
    p.close(fig)
    return nums


def bw5(out, runs):
    """ΔAICc (constant − line) of the intensity, burns 14 and 15, each estimator."""
    p = plt()
    fig, ax = p.subplots(figsize=(7.5, 3.8))
    nums = {}
    for i, s in enumerate((14, 15)):
        for j, (name, colour) in enumerate((('template', CT), ('split', CS))):
            c = runs[s, name].trends['intensity']
            d = float(c.delta_constant_linear)
            ax.bar(i * 3 + j, d, color=colour, label=name if i == 0 else None)
            ax.text(i * 3 + j, d + (0.4 if d >= 0 else -0.4), '%.1f' % d, ha='center',
                    va='bottom' if d >= 0 else 'top', fontsize=8)
            nums['%d_%s' % (s, name)] = d
    ax.axhline(trends.STABLE_DELTA, color='k', lw=0.8, ls='--',
               label='%g: above, "changing"' % trends.STABLE_DELTA)
    ax.axhline(0, color='k', lw=0.5)
    ax.set_xticks([0.5, 3.5])
    ax.set_xticklabels(['burn 14', 'burn 15 (×4.7 flux)'])
    ax.set_ylabel('AICc(constant) − AICc(line)')
    ax.set_title('BW5. Intensity: how much better a sloped line describes the frames than a flat one', fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW5_verdict.png'), dpi=130)
    p.close(fig)
    nums['threshold'] = trends.STABLE_DELTA
    return nums


def bw6(out, n=60):
    """60 synthetic NX 15-like burns at NX 15's counts (a frame's intensity
    error 2 %: the study's NX_MONITORS): 95 % intervals of the intensity
    change against the truth."""
    from burn_shoulder_study import change_of, CASES, NX_MONITORS
    from synthetic import burn_profiles as bp
    p = plt()
    T = 21 * 10.0
    got = {'template': [], 'split': []}
    for seed in range(n):
        prof, tr = bp.profiles(seed=1000 + seed, monitor=NX_MONITORS[15], **CASES['nx15_like'])
        for name in got:
            values = burn.measure_gid(prof, estimator=name)[0]
            res = burn.analyse(tr.t, values, errors='scatter')
            got[name].append(change_of(res['intensity'].fits['linear'], T) + (res['intensity'].stable,))
    truth = -0.13
    fig, axes = p.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    nums = {'truth': truth, 'replicates': n, 'monitor': NX_MONITORS[15]}
    for ax, (name, colour) in zip(axes, (('template', CT), ('split', CS))):
        v = np.array([g[0] for g in got[name]])
        s = np.array([g[1] for g in got[name]])
        hit = np.abs(v - truth) < 1.96 * s
        for i in range(n):
            ax.plot([i, i], [100 * (v[i] - 1.96 * s[i]), 100 * (v[i] + 1.96 * s[i])], '-',
                    color=colour if hit[i] else '0.65', lw=1.4)
            ax.plot(i, 100 * v[i], '.', color='k', ms=3)
        ax.axhline(100 * truth, color='k', lw=1, ls='--', label='the truth: −13 %')
        ax.axhline(0, color='0.5', lw=0.5)
        ax.set_xlabel('replicate')
        ax.set_title('%s: %d of %d intervals hold the truth; %d of %d called "changing"'
                     % (name, int(hit.sum()), n, int(sum(not g[2] for g in got[name])), n), fontsize=9)
        ax.legend(fontsize=8, loc='upper right')
        nums[name] = dict(hits=int(hit.sum()), mean=float(np.mean(v)), sd=float(np.std(v)),
                          pull_sd=float(np.std((v - truth) / s)), changing=int(sum(not g[2] for g in got[name])))
    axes[0].set_ylabel('intensity change over the burn (%), with its 95 % interval')
    fig.suptitle('BW6. Calibration: %d synthetic burns like NX 15 (FWHM +20 %%, intensity −13 %%, NX 15\'s counts)'
                 % n, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW6_calibration.png'), dpi=130)
    p.close(fig)
    return nums


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/burn_shoulder/walkthrough', help='output folder')
    ap.add_argument('--replicates', type=int, default=60, help='BW6: synthetic burns')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    e, runs = nx_burns()
    rt, rs = runs[SCAN, 'template'], runs[SCAN, 'split']
    n = OrderedDict()
    n['BW1'] = bw1(a.out, e, rt)
    n['BW2'] = bw2(a.out, rs)
    n['BW3'] = bw3(a.out, rt, rs)
    n['BW4'] = bw4(a.out, rt, rs)
    n['BW5'] = bw5(a.out, runs)
    n['BW6'] = bw6(a.out, a.replicates)
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(n, f, indent=1, default=float)
    print(json.dumps(n, indent=1, default=float))
    return 0


if __name__ == '__main__':
    sys.exit(main())
