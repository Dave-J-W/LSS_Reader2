"""Does a reflectivity join need coincident Qz points? Synthetic known truth.

Two scans of a known curve (``tests/synthetic/xrr.py``: bare water, DPPC, a 100 Å film; smeared by the
measured resolution, FWHM 8.9e-4 Å⁻¹, docs/studies/qz_resolution) meet at a join Qz. Scan b carries a
known factor (f = 10: b is reported ×1/10, as after a foil change) and ten times the counts of scan a.
The overlap's geometry is varied: no overlap, k coincident points, a staggered overlap with no shared Qz,
and a second scan on a coarser grid with or without one shared point. Every join is fitted by the
reader's methods (``lss_core.patching``, ``stitching.fitted_factor``) and scored against the truth:
bias of ln f, pull SD, coverage at 1σ, the error's size, and the share with no answer.

    python tests/tools/coincidence_synth.py --out <dir> [--trials 200] [--examples]

Writes ``stats.csv``, ``numbers.json`` and figures C1 (example fits) and C2 (aggregate) to ``--out``.
"""
import argparse
import json
import math
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from lss_core import patching, stitching           # noqa: E402
from lss_core.patching import Scan                 # noqa: E402
from synthetic import xrr                          # noqa: E402

F_TRUE = 10.0
RES = (8.9e-4, 0.0)
CURVES = {'water': xrr.bare_water(), 'DPPC': xrr.dppc(), 'film 100 Å': xrr.film(100.0)}
JOINS = {0.05: 0.002, 0.15: 0.005, 0.30: 0.01}      # join Qz: its step (Å⁻¹)
N_SIDE = 12                                          # points of each scan away from the join
COUNTS_A = 1000.0                                    # counts per point of scan a at the join; b has 10×
METHODS = ['legacy', 'interp', 'coincident', 'joint (default)', 'joint (guard off)', 'joint order 2']

# geometry: name -> (offsets of a's last points beyond the join, b's grid) in units of a's step
# a: ... qj-2s, qj-s, qj, then extra points; b starts at b0 with step sb.
GEOMS = {
    'abut (no overlap)': dict(a_end=0, b0=1, sb=1),
    '1 coincident': dict(a_end=0, b0=0, sb=1),
    '2 coincident': dict(a_end=1, b0=0, sb=1),
    '3 coincident': dict(a_end=2, b0=0, sb=1),
    '5 coincident': dict(a_end=4, b0=0, sb=1),
    '8 coincident': dict(a_end=7, b0=0, sb=1),
    'staggered, 1+1 (none shared)': dict(a_end=0, b0=-0.5, sb=1),
    'staggered, 2+2': dict(a_end=1, b0=-0.5, sb=1),
    'staggered, 4+4': dict(a_end=3, b0=-0.5, sb=1),
    'staggered, 8+8': dict(a_end=7, b0=-0.5, sb=1),
    'b step 1.5×, none shared': dict(a_end=4, b0=0.4, sb=1.5),
    'b step 1.5×, 1 shared': dict(a_end=4, b0=0, sb=1.5),
}


def true_r(q, prof):
    return xrr.smear(q, lambda x: xrr.parratt(x, prof), RES)


def make_scans(prof, qj, step, g, rng):
    qa = qj + step * np.arange(-N_SIDE, g['a_end'] + 1)
    qb = qj + step * (g['b0'] + g['sb'] * np.arange(0, N_SIDE + 1))
    qa, qb = np.round(qa, 10), np.round(qb, 10)
    r_j = true_r(np.array([qj]), prof)[0]
    na = COUNTS_A / r_j                          # monitor-like exposure so that a has COUNTS_A at qj
    nb = 10 * na
    ca = rng.poisson(true_r(qa, prof) * na).astype(float)
    cb = rng.poisson(true_r(qb, prof) * nb).astype(float)
    a = Scan(qa, ca / na, np.sqrt(np.maximum(ca, 1)) / na)
    b = Scan(qb, cb / nb / F_TRUE, np.sqrt(np.maximum(cb, 1)) / nb / F_TRUE)
    return a, b


def fit(a, b, m):
    if m == 'legacy':
        f, e = stitching.fitted_factor(np.column_stack([a.q, a.y, a.sigma]), np.column_stack([b.q, b.y, b.sigma]))
        if not (np.isfinite(f) and f > 0 and np.isfinite(e)):
            raise ValueError('legacy: no factor')
        return math.log(f), e / f, None
    if m == 'interp':
        j = patching.interp_factor(a, b)
        return j.delta, j.err, j
    if m == 'coincident':
        j = patching.coincident_factor(a, b)
        if j is None:
            raise ValueError('no coincident points')
        return j.delta, j.err, j
    if m == 'joint order 2':
        j = patching.joint_factor(a, b, order=2, n_ext=2, guard_p=0)
        return j.delta, j.err, j
    j = patching.joint_factor(a, b, guard_p=None if m == 'joint (default)' else 0)
    return j.delta, j.err, j


def one(args):
    cname, qj, gname, seed = args
    rng = np.random.default_rng(seed)
    a, b = make_scans(CURVES[cname], qj, JOINS[qj], GEOMS[gname], rng)
    out = []
    for m in METHODS:
        try:
            with np.errstate(all='ignore'):
                d, e, _ = fit(a, b, m)
            if not (np.isfinite(d) and np.isfinite(e) and e > 0):
                raise ValueError('non-finite')
            out.append((m, d - math.log(F_TRUE), e))
        except Exception:
            out.append((m, math.nan, math.nan))
    return cname, qj, gname, out


def stats(rows):
    """rows: list of (dev, err) for one cell -> dict."""
    d = np.array([r[0] for r in rows])
    e = np.array([r[1] for r in rows])
    ok = np.isfinite(d)
    n = int(ok.sum())
    s = dict(n=len(d), answered=n / len(d))
    if n < 20:
        return s
    d, e = d[ok], e[ok]
    p = d / e
    mad = 1.4826 * np.median(np.abs(p - np.median(p)))
    s.update(bias_pct=100 * float(np.mean(d)), bias_se_pct=100 * float(np.std(d) / math.sqrt(n)),
             rms_pct=100 * float(np.sqrt(np.mean(d ** 2))), err_med_pct=100 * float(np.median(e)),
             pull_sd=float(np.std(p)), pull_rsd=float(mad), cover1=float(np.mean(np.abs(p) < 1)),
             beyond3=float(np.mean(np.abs(p) > 3)))
    return s


def run(trials, workers):
    jobs = [(c, q, g, zlib.crc32(("%s|%s|%s|%d" % (c, q, g, k)).encode())) for c in CURVES for q in JOINS for g in GEOMS
            for k in range(trials)]
    cells = {}
    with Pool(workers) as pool:
        for cname, qj, gname, out in pool.imap_unordered(one, jobs, chunksize=20):
            for m, d, e in out:
                cells.setdefault((cname, qj, gname, m), []).append((d, e))
                cells.setdefault(('all', 0, gname, m), []).append((d, e))
    return cells


# ---------------------------------------------------------------- figures

INK = '#222222'
COL = {'legacy': '#7f7f7f', 'interp': '#bcbd22', 'coincident': '#ff7f0e', 'joint (default)': '#1f77b4',
       'joint (guard off)': '#17becf', 'joint order 2': '#9467bd'}


def style(plt):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#e6e6e6',
                         'axes.edgecolor': INK, 'text.color': INK, 'axes.labelcolor': INK})


def fig_examples(path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    style(plt)
    show = ['abut (no overlap)', '1 coincident', '3 coincident', 'staggered, 4+4', 'b step 1.5×, none shared',
            'b step 1.5×, 1 shared']
    cname, qj = 'film 100 Å', 0.15
    prof, step = CURVES[cname], JOINS[qj]
    fig, axes = plt.subplots(4, 3, figsize=(13, 11.5), gridspec_kw=dict(height_ratios=[3, 1.1, 3, 1.1]))
    for k, gname in enumerate(show):
        r, c = 2 * (k // 3), k % 3
        ax, axr = axes[r, c], axes[r + 1, c]
        rng = np.random.default_rng(7 + k)
        a, b = make_scans(prof, qj, step, GEOMS[gname], rng)
        qq = np.linspace(a.q.min(), b.q.max(), 400)
        rf = patching.fresnel(qq)
        ax.plot(qq, true_r(qq, prof) / rf, color='#bbbbbb', lw=3, zorder=1, label='truth')
        lines = []
        jfit = None
        for m in METHODS:
            try:
                with np.errstate(all='ignore'):
                    d, e, j = fit(a, b, m)
                lines.append('%-17s f = %6.3f ± %.3f (%+.1fσ)' % (m, math.exp(d), math.exp(d) * e,
                                                                  (d - math.log(F_TRUE)) / e))
                if m == 'joint (default)':
                    jfit = (d, j)
            except Exception as ex:
                lines.append('%-18s no answer: %s' % (m, str(ex)[:34]))
        fa = patching.fresnel(a.q)
        ax.errorbar(a.q, a.y / fa, a.sigma / fa, fmt='o', ms=3.5, color='#555555', label='scan a', zorder=3)
        if jfit is not None:
            d, j = jfit
            f = math.exp(d)
            fb = patching.fresnel(b.q)
            ax.errorbar(b.q, f * b.y / fb, f * b.sigma / fb, fmt='s', ms=3.5, mfc='white', color=COL['joint (default)'],
                        label='scan b × f (joint)', zorder=3)
            rung = patching.rung_fit(a, b, j.order, j.n_ext)
            qw = np.linspace(min(a.q[rung.ia].min(), b.q[rung.ib].min()),
                             max(a.q[rung.ia].max(), b.q[rung.ib].max()), 200)
            ax.plot(qw, np.exp(rung.curve(qw)), color=COL['joint (default)'], lw=1.3,
                    label='joint model (default fit)', zorder=4)
            lines[METHODS.index('joint (default)')] += ' [o%d e%d]' % (j.order, j.n_ext)
            ra = (a.y - true_r(a.q, prof)) / a.sigma
            rb = (f * b.y - true_r(b.q, prof)) / (f * b.sigma)
            axr.plot(a.q, ra, 'o', ms=3, color='#555555')
            axr.plot(b.q, rb, 's', ms=3, mfc='white', color=COL['joint (default)'])
        else:
            fb = patching.fresnel(b.q)
            ax.errorbar(b.q, F_TRUE * b.y / fb, F_TRUE * b.sigma / fb, fmt='s', ms=3.5, mfc='white', color='#d62728',
                        label='scan b × true f (no joint answer)', zorder=3)
            axr.text(0.5, 0.5, 'no joint fit: nothing to score', transform=axr.transAxes, ha='center', va='center')
        ov_lo, ov_hi = b.q.min(), a.q.max()
        if ov_hi >= ov_lo:
            ax.axvspan(ov_lo, ov_hi, color='#fff2cc', zorder=0)
        ax.set_xlim(qj - 9 * step, qj + 13 * step)
        axr.set_xlim(ax.get_xlim())
        yl = ax.get_ylim()
        ax.set_ylim(yl[0], yl[0] + (yl[1] - yl[0]) * 1.9)
        ax.set_title(gname, fontsize=10, loc='left')
        ax.text(0.01, 0.98, '\n'.join(lines), transform=ax.transAxes, va='top', ha='left', family='monospace',
                fontsize=6.6, bbox=dict(fc='white', ec='#cccccc', alpha=0.9))
        ax.set_ylabel('R / R_F')
        axr.axhline(0, color=INK, lw=0.7)
        axr.set_ylim(-4, 4)
        axr.set_ylabel('(data − truth)/σ')
        axr.set_xlabel('Qz (Å⁻¹)')
        if k in (0, 2):
            h, l = ax.get_legend_handles_labels()
            hh = hh + h if k else h
            ll = ll + l if k else l
        if k == 2:
            keep = {}
            for h_, l_ in zip(hh, ll):
                keep.setdefault(l_, h_)
            fig.legend(list(keep.values()), list(keep), loc='upper left', bbox_to_anchor=(0.01, 0.962), ncol=5, fontsize=8, frameon=False)
    fig.suptitle('One synthetic join per geometry (100 Å film, join at Qz 0.15 Å⁻¹, step 0.005):\nan overlap without '
                 'shared Qz fits as well as one with them; a lone shared point is too little for the default fit', x=0.01, ha='left', fontsize=11.5, y=0.995)
    fig.text(0.01, 0.003, 'Truth f = %g (scan b reported ×1/%g; b has 10× the counts of a, %d counts per point of a '
             'at the join). Yellow: the overlap [first Qz of b, last Qz of a]. Grey curve: the true R/R_F, smeared '
             'by FWHM 8.9e-4 Å⁻¹.\nScan b drawn × the default joint fit\'s f; residuals against the truth (a common offset of b\'s residuals is the error '
             'of f). In the boxes (±nσ) is the pull = '
             '(ln f − ln f_true)/σ.' % (F_TRUE, F_TRUE, COUNTS_A), fontsize=7, color='#666666', ha='left')
    fig.tight_layout(rect=(0, 0.022, 1, 0.945))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_aggregate(cells, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    style(plt)
    gnames = list(GEOMS)
    fig, axes = plt.subplots(1, 4, figsize=(15, 6.2), sharey=True)
    y = np.arange(len(gnames))[::-1]
    off = np.linspace(-0.32, 0.32, len(METHODS))
    panels = [('answered', 'Share of joins with an answer', (0, 1.05)),
              ('bias_pct', 'Bias of f (%), ±2 SE', None),
              ('pull_sd', 'Pull SD (1 = honest errors)', (0, 3)),
              ('err_med_pct', 'Median stated error of f (%)', None)]
    for ax, (key, title, lim) in zip(axes, panels):
        for i, m in enumerate(METHODS):
            xs, ys, xe = [], [], []
            for gy, g in zip(y, gnames):
                s = stats(cells[('all', 0, g, m)])
                if key in s:
                    xs.append(s[key])
                    ys.append(gy + off[i])
                    xe.append(2 * s['bias_se_pct'] if key == 'bias_pct' else 0)
            ax.errorbar(xs, ys, xerr=xe, fmt='o', ms=4.5, color=COL[m], label=m, lw=1)
            hi = {'pull_sd': 3, 'bias_pct': 3}.get(key)
            if hi:
                for xv, yv in zip(xs, ys):
                    if abs(xv) > hi:
                        xc = math.copysign(hi * 0.97, xv)
                        ax.plot([xc], [yv], marker='>' if xv > 0 else '<', ms=7, color=COL[m])
                        ax.text(xc - math.copysign(0.08, xv), yv, '%s %.3g' % (m.split()[0], xv), fontsize=6.5,
                                ha='right' if xv > 0 else 'left', va='center')
        ax.set_title(title, fontsize=10, loc='left')
        if lim:
            ax.set_xlim(*lim)
        if key == 'pull_sd':
            ax.axvline(1, color=INK, ls='--', lw=0.9)
            ax.set_xlim(0, 3)
        if key == 'bias_pct':
            ax.axvline(0, color=INK, ls='--', lw=0.9)
            ax.set_xlim(-3, 3)
        if key == 'err_med_pct':
            ax.set_xlim(0, None)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(gnames)
    axes[0].legend(loc='lower left', fontsize=7.5)
    for ax in axes:
        for gy in y[::2]:
            ax.axhspan(gy - 0.5, gy + 0.5, color='#f6f6f6', zorder=0)
    fig.suptitle('Over 9 joins (3 curves × Qz 0.05, 0.15, 0.30): shared Qz are not needed for the joint fit; '
                 'some overlap is', x=0.01, ha='left', fontsize=12, y=0.99)
    fig.text(0.01, 0.005, 'Each geometry: %d synthetic joins per curve and Qz, pooled. Values beyond a panel range sit at its edge as an arrow, the value beside it. A missing point: the method gave no answer at fewer '
             'than 20 joins. Bias in ln f, ×100.' % (cells[('all', 0, gnames[0], METHODS[0])].__len__() // 9),
             fontsize=7, color='#666666', ha='left')
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_cells(cells, path):
    """Per join (curve × Qz), the bias in units of the median stated error, and the pull SD, for three
    methods: what the pooled figure averages away."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    style(plt)
    plt.rcParams['axes.grid'] = False
    ms = ['legacy', 'coincident', 'joint (default)', 'joint order 2']
    gn = list(GEOMS)
    joins = [(c, q) for c in CURVES for q in JOINS]
    fig, axes = plt.subplots(1, len(ms), figsize=(17, 6.6), sharey=True)
    norm = TwoSlopeNorm(vmin=-3, vcenter=0, vmax=3)
    for ax, m in zip(axes, ms):
        z = np.full((len(gn), len(joins)), np.nan)
        for i, g in enumerate(gn):
            for k, (c, q) in enumerate(joins):
                st = stats(cells[(c, q, g, m)])
                if 'bias_pct' in st:
                    z[i, k] = st['bias_pct'] / st['err_med_pct']
                    psd = st['pull_sd']
                    txt = '%.1f' % psd if psd < 9.95 else '%.0f' % psd
                    ax.text(k, i, txt, ha='center', va='center', fontsize=6.5,
                            color='white' if abs(z[i, k]) > 2 else INK,
                            fontweight='bold' if not 0.8 <= psd <= 1.25 else 'normal')
                else:
                    ax.text(k, i, '—', ha='center', va='center', fontsize=7, color='#999999')
        im = ax.imshow(np.clip(z, -3, 3), cmap='RdBu_r', norm=norm, aspect='auto')
        ax.set_xticks(range(len(joins)))
        ax.set_xticklabels(['%s\n%.2f' % (c.replace(' 100 Å', ''), q) for c, q in joins], fontsize=7)
        ax.set_title(m, fontsize=10, loc='left')
        for k in (2.5, 5.5):
            ax.axvline(k, color='white', lw=2)
    axes[0].set_yticks(range(len(gn)))
    axes[0].set_yticklabels(gn)
    cb = fig.colorbar(im, cax=fig.add_axes([0.93, 0.12, 0.01, 0.78]))
    cb.set_label('bias / median stated error (clipped at ±3)')
    fig.suptitle('Join by join: the default joint fit is honest wherever it answers; the legacy error is 2-300x '
                 'too small with 2-3 points; order 2 cannot follow a fast fringe (film at 0.30)',
                 x=0.01, ha='left', fontsize=11.5, y=0.99)
    fig.text(0.01, 0.01, 'Colour: bias of ln f over %d joins divided by the median stated error (0 = unbiased; '
             '±1 = the bias equals the error bar). Number: pull SD (bold outside 0.8–1.25). —: no answer. '
             'Columns: curve and join Qz (step 0.002, 0.005, 0.01 Å⁻¹).' % len(cells[(joins[0][0], joins[0][1], gn[0],
                                                                                     ms[0])]),
             fontsize=7, color='#666666', ha='left')
    fig.subplots_adjust(left=0.13, right=0.92, top=0.9, bottom=0.12, wspace=0.05)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--trials', type=int, default=200)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--examples', action='store_true', help='only the example figure')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    fig_examples(os.path.join(a.out, 'C1_example_joins.png'))
    if a.examples:
        return
    cells = run(a.trials, a.workers)
    rows = []
    for (c, q, g, m), v in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1], list(GEOMS).index(kv[0][2]),
                                                                    METHODS.index(kv[0][3]))):
        s = stats(v)
        rows.append(dict(curve=c, join_qz=q, geometry=g, method=m, **s))
    cols = ['curve', 'join_qz', 'geometry', 'method', 'n', 'answered', 'bias_pct', 'bias_se_pct', 'rms_pct',
            'err_med_pct', 'pull_sd', 'pull_rsd', 'cover1', 'beyond3']
    import csv
    with open(os.path.join(a.out, 'stats.csv'), 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([('%.4g' % r[k]) if isinstance(r.get(k), float) else str(r.get(k, '')) for k in cols])
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as fh:
        json.dump(dict(f_true=F_TRUE, counts_a=COUNTS_A, trials=a.trials, resolution_fwhm=RES[0],
                       pooled=[r for r in rows if r['curve'] == 'all']), fh, indent=1)
    fig_aggregate(cells, os.path.join(a.out, 'C2_aggregate.png'))
    fig_cells(cells, os.path.join(a.out, 'C3_by_join.png'))


if __name__ == '__main__':
    main()
