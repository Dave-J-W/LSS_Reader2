"""Figures of the XRF shootout (``tests/tools/xrf_shootout.py``'s outputs).

    python tests/tools/xrf_shootout_figures.py --run docs/studies/xrf_shootout/run \
        --out docs/studies/xrf_shootout

Needs only numpy and matplotlib (and the repository's synthetic generators
for the anatomy and Compton figures). Writes:

- ``X1_scoreboard.png``: calibrated bias of every method in every
  condition, as a diverging heat map (blue low, red high, grey on target),
  with failed fits marked;
- ``X2_counts.png``: bias against counts on a clean line (the weighting);
- ``X3_xfntr.png``: XFNTR curves divided by the truth, one panel per curve;
- ``X4_honesty.png``: the spread of the pulls (error bars that are honest
  give 1), per method and condition;
- ``X5_wins.png``: per condition, how far the reader's best method and the
  best of the others are from the truth;
- ``X6_anatomy.png``: the new synthetic cases, part by part;
- ``X7_compton.png``: the three Compton models under the Zn line, and the
  remembered constants against xraylib;
- ``X8_speed.png``: seconds per spectrum.

Colours: the dataviz reference palette in its fixed order (one hue per
method, the same in every figure); the diverging map runs from its blue
through grey to its red.
"""
import argparse
import csv
import math
import os
import sys

import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.colors import LinearSegmentedColormap              # noqa: E402

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

SURFACE, INK, INK2, MUTED, GRID, AXIS = '#fcfcfb', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
COLOR = {'p1': '#2a78d6', 'pymca': '#eb6834', 'pymca_best': '#eb6834', 'larch': '#1baf7a', 'pyxrf': '#eda100', 'xeray': '#e87ba4',
         'p1p2p3': '#008300', 'window': '#6250d6', 'fit_data': '#e34948'}
LABEL = {'window': 'reader: window sum', 'fit_data': 'reader: fit, data weights (old)', 'p1': 'reader: fit, Poisson (default)',
         'p1p2p3': 'reader: Poisson + width + escape strip', 'xeray': 'XeRay (port)', 'pymca': 'PyMca',
         'pymca_tails': 'PyMca, Hypermet tails', 'pyxrf': 'PyXRF (scikit-beam)', 'larch': 'Larch (series)',
         'larch_each': 'Larch (each spectrum)', 'pymca_snip60': 'PyMca, SNIP 60', 'pymca_snip100': 'PyMca, SNIP 100',
         'pymca_poly': 'PyMca, polynomial continuum', 'pymca_best': 'PyMca, best of 5 settings (picked with the truth)'}
SHORT = {'window': 'window', 'fit_data': 'fit (data)', 'p1': 'P1 (default)', 'p1p2p3': 'P1+P2+P3', 'xeray': 'XeRay',
         'pymca': 'PyMca', 'pymca_tails': 'PyMca tails', 'pyxrf': 'PyXRF', 'larch': 'Larch', 'larch_each': 'Larch each',
         'pymca_snip60': 'PyMca SNIP60', 'pymca_snip100': 'PyMca SNIP100', 'pymca_poly': 'PyMca poly',
         'pymca_best': 'PyMca best'}
ORDER = ['window', 'fit_data', 'p1', 'p1p2p3', 'xeray', 'pymca', 'pymca_best', 'pyxrf', 'larch', 'larch_each']
TABLE_ORDER = ORDER[:6] + ['pymca_tails', 'pymca_snip60', 'pymca_snip100', 'pymca_poly'] + ORDER[6:]
READER = ('window', 'fit_data', 'p1', 'p1p2p3')
PYMCA_ALL = ('pymca', 'pymca_tails', 'pymca_snip60', 'pymca_snip100', 'pymca_poly')
VERDICT_OTHERS = ('xeray', 'pymca_best', 'pyxrf', 'larch', 'larch_each')
LINES = ['p1', 'p1p2p3', 'fit_data', 'window', 'xeray', 'pymca_best', 'pyxrf', 'larch']
ACCURATE = 0.02          # |bias| within 2 % (or 2 standard errors, when larger) ...
FAIL_OK = 0.05           # ... with at most 5 % of fits failed: "accurate" in X5
MAX_SE = 0.01            # ... and the bias known to 1 % (one standard error)
DIVERGING = LinearSegmentedColormap.from_list('div', ['#1c5cab', '#86b6ef', '#f0efec', '#f0a3a2', '#c23b3a'])
FAIL_SHARE = 0.2


def style():
    plt.rcParams.update({
        'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
        'axes.edgecolor': AXIS, 'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': MUTED,
        'text.color': INK, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
        'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9, 'axes.titlesize': 10,
        'axes.titleweight': 'bold', 'legend.frameon': False, 'lines.linewidth': 2.0,
        'font.family': ['Segoe UI', 'DejaVu Sans', 'sans-serif'],
    })


def read(path):
    """Rows of a CSV; ``path`` inside a run folder may name several runs
    joined by commas (``--run a,b``): their rows are concatenated."""
    head, name = os.path.split(path)
    rows = []
    for folder in head.split(','):
        p = os.path.join(folder, name)
        if os.path.exists(p) or ',' not in head:
            with open(p, encoding='utf-8') as f:
                rows += list(csv.DictReader(f))
    return rows


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def scores(run):
    """{(condition, method): score row}, with 'pymca_best': per condition, the
    PyMca setting with the smallest |bias| among those failing at most
    ``FAIL_OK`` (picked with the truth: the most generous PyMca)."""
    out = {}
    for r in read(os.path.join(run, 'scores.csv')):
        out[(r['condition'], r['method'])] = {k: (num(v) if k not in ('condition', 'factor', 'method') else v)
                                              for k, v in r.items()}
    for name in dict.fromkeys(n for n, _ in out):
        c = [(abs(out[(name, m)].get('bias', math.nan)), m) for m in PYMCA_ALL if (name, m) in out
             and np.isfinite(out[(name, m)].get('bias', math.nan)) and failed_share(out[(name, m)]) <= FAIL_OK]
        if c:
            r = dict(out[(name, min(c)[1])])
            r['method'], r['config'] = 'pymca_best', min(c)[1]
            out[(name, 'pymca_best')] = r
    return out


def series_best(run):
    """{series: the PyMca setting with the smallest worst-point error}."""
    sv = read(os.path.join(run, 'series_scores.csv'))
    best = {}
    for r in sv:
        if r['method'] in PYMCA_ALL and np.isfinite(num(r['worst'])):
            if r['series'] not in best or num(r['worst']) < best[r['series']][0]:
                best[r['series']] = (num(r['worst']), r['method'])
    return {k: v[1] for k, v in best.items()}


def conditions(run):
    rows = read(os.path.join(run, 'conditions.csv'))
    return list({r['condition']: r for r in rows}.values())


def methods_in(sc, order=None):
    present = {m for _, m in sc}
    return [m for m in (order or ORDER) if m in present]


def failed_share(r):
    return r['failed'] / r['n'] if r and r['n'] else math.nan


# ---- X1 -------------------------------------------------------------------------------

def fig_scoreboard(run, out):
    sc = scores(run)
    conds = conditions(run)
    meths = methods_in(sc)
    names = [c['condition'] for c in conds]
    fac = [c['factor'] for c in conds]
    B = np.full((len(names), len(meths)), np.nan)
    F = np.zeros_like(B)
    for i, n in enumerate(names):
        for j, m in enumerate(meths):
            r = sc.get((n, m))
            if r:
                B[i, j] = r.get('bias', math.nan)
                F[i, j] = failed_share(r)
    lim = 0.3
    fig, ax = plt.subplots(figsize=(1.0 + 0.78 * len(meths), 0.27 * len(names) + 1.6))
    im = ax.imshow(np.clip(B, -lim, lim), cmap=DIVERGING, vmin=-lim, vmax=lim, aspect='auto')
    for i in range(len(names)):
        for j in range(len(meths)):
            v = B[i, j]
            if F[i, j] > FAIL_SHARE:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=True, facecolor='#ffffff', hatch='///',
                                           edgecolor=AXIS, linewidth=0))
                ax.text(j, i, 'fails\n%.0f%%' % (100 * F[i, j]), ha='center', va='center', fontsize=5.5, color=INK2)
            elif np.isfinite(v):
                txt = '%+.0f' % (100 * v) if abs(v) >= 0.095 else '%+.1f' % (100 * v)
                ax.text(j, i, txt, ha='center', va='center', fontsize=6.5,
                        color='#ffffff' if abs(v) > 0.6 * lim else INK)
    ax.set_xticks(range(len(meths)))
    ax.set_xticklabels([SHORT[m] for m in meths], rotation=35, ha='right')
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=7)
    ax.grid(False)
    for i in range(1, len(names)):
        if fac[i] != fac[i - 1]:
            ax.axhline(i - 0.5, color=INK2, linewidth=0.8)
    ax.axvline(len([m for m in meths if m in READER]) - 0.5, color=INK, linewidth=1.5)
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position('top')
    plt.setp(ax.get_xticklabels(), rotation=35, ha='left')
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label('bias, % (clipped at ±30)')
    cb.set_ticks([-0.3, -0.1, 0, 0.1, 0.3])
    cb.set_ticklabels(['−30', '−10', '0', '+10', '+30'])
    ax.set_title('Every method on every condition: bias in %, 100 series of spectra each\n'
                 'left of the black line: the reader; right: the other packages. Hatched: over 20 % of fits failed',
                 fontsize=9, loc='left', pad=60)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'X1_scoreboard.png'), dpi=150)
    plt.close(fig)


# ---- X2 -------------------------------------------------------------------------------

def fig_counts(run, out):
    sc = scores(run)
    conds = [c for c in conditions(run) if c['factor'] == 'counts']
    n = np.array([float(c['condition'].split('_')[1]) for c in conds])
    o = np.argsort(n)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.axhspan(-0.01, 0.01, color=GRID, alpha=0.7, linewidth=0)
    ax.axhline(0, color=AXIS, linewidth=1)
    for k, m in enumerate([m for m in LINES if any((c['condition'], m) in sc for c in conds)]):
        b = np.array([sc.get((c['condition'], m), {}).get('bias', math.nan) for c in conds])[o]
        se = np.array([sc.get((c['condition'], m), {}).get('bias_se', math.nan) for c in conds])[o]
        x = n[o] * (1 + 0.025 * (k - 3.5))
        ax.errorbar(x, b, yerr=2 * se, color=COLOR[m], marker='o', markersize=5, capsize=0, linewidth=2,
                    elinewidth=1, label=LABEL[m], markeredgecolor=SURFACE, markeredgewidth=1)
    ax.set_xscale('log')
    ax.set_xlabel('photons in the line (all K lines, per spectrum)')
    ax.set_ylabel('calibrated bias (fraction of the truth)')
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylim(-0.4, 0.4)
    ax.set_title('A clean line, no scatter: what the weighting alone does\nerror bars ±2 standard errors; '
                 'grey band ±1 %', loc='left')
    ax.legend(fontsize=7, ncol=2, loc='lower right')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'X2_counts.png'), dpi=150)
    plt.close(fig)


# ---- X3 -------------------------------------------------------------------------------

def fig_xfntr(run, out):
    p = os.path.join(run, 'series.csv')
    if not any(os.path.exists(os.path.join(f, 'series.csv')) for f in run.split(',')):
        return
    rows = read(p)
    sv = {(r['series'], r['method']): r for r in read(os.path.join(run, 'series_scores.csv'))}
    series = list(dict.fromkeys(r['series'] for r in rows))
    ncol = 2
    nrow = math.ceil(len(series) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(9.5, 2.5 * nrow + 0.6), sharex=True)
    axes = np.atleast_1d(axes).ravel()
    sb = series_best(run)
    for ax, s in zip(axes, series):
        ax.axhspan(0.99, 1.01, color=GRID, alpha=0.7, linewidth=0)
        ax.axhline(1, color=AXIS, linewidth=1)
        for m0 in LINES:
            m = sb.get(s) if m0 == 'pymca_best' else m0
            rr = [r for r in rows if r['series'] == s and r['method'] == m]
            if not rr:
                continue
            q = np.array([num(r['qz']) for r in rr])
            y = np.array([num(r['ratio']) for r in rr])
            t = np.array([num(r['truth']) for r in rr])
            ok = t >= 100
            ax.plot(q[ok], y[ok], color=COLOR[m0], linewidth=1.6, marker='o', markersize=3.5,
                    label='%s (worst %.1f %%)' % (SHORT[m] if m0 != 'pymca_best' else 'best PyMca: ' + SHORT[m],
                                                 100 * num(sv[(s, m)]['worst'])))
        ax.set_title(s.replace('xfntr_', ''), loc='left', fontsize=9)
        ax.set_ylim(0.8, 1.25)
        ax.legend(fontsize=5.8, ncol=2, loc='upper right')
    for ax in axes[len(series):]:
        ax.set_visible(False)
    for ax in axes[-ncol:]:
        ax.set_xlabel('Qz (1/Å)')
    fig.supylabel('measured / true, after one free scale', color=INK2, fontsize=9)
    fig.suptitle('XFNTR curves: does each method keep the shape of the curve?  Mean of 40 replicate curves; '
                 'grey band ±1 %; points with ≥ 100 true counts', fontsize=9, x=0.01, ha='left')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'X3_xfntr.png'), dpi=150)
    plt.close(fig)


# ---- X4 -------------------------------------------------------------------------------

def fig_honesty(run, out):
    sc = scores(run)
    conds = conditions(run)
    meths = [m for m in methods_in(sc) if m != 'pymca_best' and any(
        np.isfinite(sc.get((c['condition'], m), {}).get('pull_sd', math.nan)) for c in conds)]
    fig, ax = plt.subplots(figsize=(7.5, 4.1))
    ax.axhspan(0.9, 1.15, color=GRID, alpha=0.8, linewidth=0)
    ax.axhline(1, color=AXIS, linewidth=1)
    rng = np.random.default_rng(1)
    for j, m in enumerate(meths):
        v = np.array([sc.get((c['condition'], m), {}).get('pull_sd', math.nan) for c in conds])
        f = np.array([failed_share(sc.get((c['condition'], m))) for c in conds])
        v = v[np.isfinite(v) & (f <= FAIL_SHARE)]
        x = j + rng.uniform(-0.18, 0.18, len(v))
        col = COLOR.get(m, MUTED)
        ax.scatter(x, np.clip(v, 0.05, 20), s=16, color=col, edgecolor=SURFACE, linewidth=0.8, zorder=3)
        if len(v):
            ax.plot([j - 0.3, j + 0.3], [np.median(v)] * 2, color=INK, linewidth=2, zorder=4)
            ax.text(j, 22, 'median %.2f' % np.median(v), ha='center', fontsize=6.5, color=INK2)
    ax.set_yscale('log')
    ax.set_ylim(0.05, 40)
    ax.set_xticks(range(len(meths)))
    ax.set_xticklabels([SHORT[m] for m in meths], rotation=25, ha='right')
    ax.set_ylabel('SD of (estimate − truth) / its error bar')
    ax.set_title('Are the error bars honest?  1: honest; above 1: too small; below 1: too big\n'
                 'one dot per condition (failed fits excluded); grey band 0.90–1.15\n'
                 'PyXRF and Larch (series) report no error bars', loc='left', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'X4_honesty.png'), dpi=150)
    plt.close(fig)


# ---- X5 -------------------------------------------------------------------------------

def accurate(r):
    """Within ``ACCURATE`` of the truth (or 2 standard errors, when larger),
    with at most ``FAIL_OK`` of fits failed and the bias known to ``MAX_SE``."""
    if not r or failed_share(r) > FAIL_OK or not np.isfinite(r.get('bias', math.nan)):
        return False
    se = r.get('bias_se', 0.0)
    if se > MAX_SE:                 # too scattered to judge: its mean can land near the truth by chance
        return False
    return abs(r['bias']) <= max(ACCURATE, 2 * se)


def side(sc, name, meths):
    """(method, row, accurate) for one side: the accurate method with the
    smallest RMS error; else the least biased method that answers at all
    (on the spectra where its fit did not fail); else (None, None, False)."""
    rows = [(m, sc[(name, m)]) for m in meths if (name, m) in sc]
    acc = [(r['rmse'], m, r) for m, r in rows if accurate(r)]
    if acc:
        _, m, r = min(acc, key=lambda t: t[0])
        return m, r, True
    # no accurate method: the least biased one that answers at all (its failures are shown beside it)
    ok = [(abs(r['bias']), m, r) for m, r in rows if failed_share(r) < 0.99 and np.isfinite(r.get('bias', math.nan))]
    if ok:
        _, m, r = min(ok, key=lambda t: t[0])
        return m, r, False
    return None, None, False


def wins_table(run):
    """Per condition: the reader's best method and the others' best (the
    oracle PyMca counts once, as 'pymca_best'), and the verdict:
    - both accurate: the same if their RMS errors are within 10 %, else
      the more precise side is better (precision);
    - one side accurate: that side is better (accuracy);
    - neither: 'neither within 2 %'."""
    sc = scores(run)
    out = []

    def g(r, k):
        return r.get(k, math.nan) if r else math.nan
    for c in conditions(run):
        n = c['condition']
        rm, rr, ra = side(sc, n, READER)
        om, orow, oa = side(sc, n, VERDICT_OTHERS)
        if ra and oa:
            x, y = rr['rmse'], orow['rmse']
            verdict = 'same' if abs(x - y) <= 0.1 * max(x, y) else (
                'reader better (precision)' if x < y else 'others better (precision)')
        elif ra:
            verdict = 'reader better (accuracy)'
        elif oa:
            verdict = 'others better (accuracy)'
        else:
            verdict = 'neither within 2 %'
        p1 = sc.get((n, 'p1'))
        out.append(dict(condition=n, factor=c['factor'], reader_best=rm, reader_bias=g(rr, 'bias'),
                        reader_rmse=g(rr, 'rmse'), reader_failed=failed_share(rr) if rr else math.nan, reader_accurate=ra,
                        other_best=(om if om != 'pymca_best' else 'pymca_best:' + orow.get('config', '')) if om else None,
                        other_bias=g(orow, 'bias'), other_rmse=g(orow, 'rmse'),
                        other_failed=failed_share(orow) if orow else math.nan, other_accurate=oa,
                        p1_bias=g(p1, 'bias'), p1_failed=failed_share(p1) if p1 else math.nan, verdict=verdict))
    return out


def _short(m):
    if not m:
        return 'all fail'
    if m.startswith('pymca_best:'):
        return 'best PyMca (%s)' % SHORT.get(m.split(':', 1)[1], m)
    return SHORT.get(m, m)


def fig_wins(run, out):
    rows = wins_table(run)
    with open(os.path.join(out, 'wins.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.4g' % v if isinstance(v, float) else v) for k, v in r.items()})
    fig, ax = plt.subplots(figsize=(9.5, 0.27 * len(rows) + 1.8))
    y = np.arange(len(rows))[::-1]
    lo, top = 0.001, 3.0
    ax.axvspan(lo, ACCURATE, color=GRID, alpha=0.7, linewidth=0)
    for yi, r in zip(y, rows):
        pts = []
        for key, col, mk, dy in (('reader', COLOR['p1'], 'o', 0.33), ('other', COLOR['pymca'], 's', -0.62)):
            b = abs(r[key + '_bias'])
            m = r[key + '_best']
            if not np.isfinite(b):
                ax.text(top * 0.9, yi + (0.12 if key == 'reader' else -0.3), '%s: every fit fails' %
                        ('reader' if key == 'reader' else 'others'), fontsize=5, color=col, ha='right')
                continue
            bc = min(max(b, lo * 1.2), top)
            pts.append(bc)
            filled = r[key + '_accurate']
            ax.scatter(bc, yi, s=36, marker='>' if b > top else mk, zorder=3, linewidth=1.3,
                       facecolor=col if filled else SURFACE, edgecolor=col)
            fl = r[key + '_failed']
            ax.text(bc, yi + dy, _short(m) + (' %.0f%%' % (100 * b) if b > top else '')
                    + (', fails %.0f%%' % (100 * fl) if np.isfinite(fl) and fl > FAIL_OK else ''), fontsize=5,
                    color=INK2, ha='center')
        if len(pts) == 2:
            ax.plot(pts, [yi, yi], color=AXIS, linewidth=1.2, zorder=1)
        ax.text(top * 1.25, yi, r['verdict'], fontsize=6.5, va='center', color=INK, clip_on=False)
    ax.set_xscale('log')
    ax.set_xlim(lo, top)
    ax.set_ylim(-1, len(rows))
    ax.set_yticks(y)
    ax.set_yticklabels([r['condition'] for r in rows], fontsize=7)
    ax.set_xlabel("|bias| of the side's best method, fraction of the truth (log); grey: within 2 %")
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=1))
    ax.scatter([], [], s=36, color=COLOR['p1'], label="best of the reader's four")
    ax.scatter([], [], s=36, color=COLOR['pymca'], marker='s', label='best of XeRay, PyMca (best of 5 settings), PyXRF, Larch')
    ax.scatter([], [], s=36, facecolor=SURFACE, edgecolor=INK2, label='hollow: not accurate (|bias| > 2 %, or > 5 % of fits fail: bias of those that did not)')
    ax.legend(fontsize=6.5, loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2)
    ax.set_title('Better, the same or worse?  Accuracy first (within 2 %, at most 5 % of fits failing), then precision '
                 '(RMS errors within 10 %: "same")', loc='left', pad=34, fontsize=9)
    fig.tight_layout(rect=(0, 0, 0.82, 1))
    fig.savefig(os.path.join(out, 'X5_wins.png'), dpi=150)
    plt.close(fig)


# ---- X6 -------------------------------------------------------------------------------

def fig_anatomy(out):
    sys.path.insert(0, os.path.join(os.getcwd(), 'tests', 'tools'))
    import xrf_shootout as xs
    from synthetic import mca_more as mm
    conds = xs.conditions()
    names = ['hard', 'as_by_pb', 'er_L_10keV', 'br_14keV']
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.4))
    groups = [('Compton', '#898781'), ('Rayleigh', '#c3c2b7')]
    for ax, n in zip(axes.ravel(), names):
        c = conds[n]
        s = c.spectrum()
        e = s.energy
        lo, hi = c.fit_range()
        sel = (e >= lo) & (e <= hi)
        ax.semilogy(e[sel], s.expected[sel], color=INK, linewidth=1.2, label='total (expected counts)')
        ax.semilogy(e[sel], np.maximum(s.part(sources=['Compton']), 1e-3)[sel], color=MUTED, linewidth=1.2,
                    label='Compton (Biggs profiles)')
        ax.semilogy(e[sel], np.maximum(s.part(kinds=('escape',), sources=['Rayleigh', 'Compton valence', 'Compton core']),
                                       1e-3)[sel], color=COLOR['window'], linewidth=1.0, label='Si escape of the scatter')
        palette = [COLOR['p1'], COLOR['pymca'], COLOR['larch']]
        for k, key in enumerate(c.lines):
            v = mm.photopeak_family(s, key)
            ax.semilogy(e[sel], np.maximum(v, 1e-3)[sel], color=palette[k % 3], linewidth=1.4, label='%s lines' % key)
        blo, bhi = c.box_range()
        ax.axvspan(blo, bhi, color=COLOR['p1'], alpha=0.08, linewidth=0)
        ax.text(0.5 * (blo + bhi), 1.5e5, 'box', ha='center', fontsize=6.5, color=COLOR['p1'])
        ax.set_ylim(0.1, 1e6)
        ax.set_title('%s: %s' % (n, c.describe[:70] + ('…' if len(c.describe) > 70 else '')), loc='left', fontsize=7.5)
        ax.set_xlabel('energy (keV)')
        ax.set_ylabel('counts per 10 eV channel')
        ax.legend(fontsize=5.8, loc='best')
    fig.suptitle('The synthetic spectra, part by part (one spectrum; Poisson draws scatter about the black line)',
                 fontsize=9, x=0.01, ha='left')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'X6_anatomy.png'), dpi=150)
    plt.close(fig)


# ---- X7 -------------------------------------------------------------------------------

def fig_compton(out, check):
    from dataclasses import replace
    from synthetic import mca, mca_more as mm
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw=dict(width_ratios=[1.1, 1]))
    beam = mca.Beam()
    models = [('hydrogenic (core 20 %)', replace(beam, compton_core=0.2), 'hydrogenic', '#c3c2b7'),
              ('shells (study B)', beam, 'shells', '#52514e'),
              ('Biggs HF tables (xraylib)', beam, 'biggs', COLOR['p1'])]
    zn = mm.main_line('Zn K', 10.0)[0]
    for label, bb, model, col in models:
        s = mm.spectrum({}, 1e6, bb, mca.Detector(escape=0), 0.0, compton=model)
        e = s.energy
        sel = (e > 7.0) & (e < 10.6)
        a.semilogy(e[sel], np.maximum(s.part(sources=['Compton']), 1e-2)[sel], color=col, linewidth=1.8, label=label)
    fw = mca.Detector().fwhm(zn)
    a.axvspan(zn - 2 * fw, zn + 2 * fw, color=GRID, alpha=0.9, linewidth=0)
    a.text(zn, 3e4, 'Zn Kα box', ha='center', fontsize=7, color=INK2)
    a.set_ylim(1, 1e5)
    a.set_xlabel('energy (keV)')
    a.set_ylabel('Compton counts per channel (1e6 Rayleigh photons)')
    a.set_title('Water\'s Compton scatter under 10 keV, three models', loc='left')
    a.legend(fontsize=7, loc='upper left')
    rows = read(check)
    keep = [r for r in rows if 'keV' not in r['quantity'] or 'escape' in r['quantity']]
    keep = [r for r in keep if np.isfinite(num(r['rel_diff']))]
    v = np.array([100 * num(r['rel_diff']) for r in keep])
    y = np.arange(len(keep))[::-1]
    a2 = b
    a2.barh(y, v, color=[COLOR['fit_data'] if abs(x) > 5 else COLOR['p1'] for x in v], height=0.65)
    a2.axvline(0, color=AXIS, linewidth=1)
    a2.set_yticks(y)
    a2.set_yticklabels([r['quantity'] for r in keep], fontsize=6.5)
    for yi, x in zip(y, v):
        a2.text(x + (0.6 if x >= 0 else -0.6), yi, '%+.1f' % x, va='center', ha='left' if x >= 0 else 'right',
                fontsize=6, color=INK2)
    a2.set_xlabel('remembered value vs xraylib (%)')
    a2.set_title('Constants the generator took from memory, checked\n(line energies and edges agree to < 0.01 %; '
                 'not shown)', loc='left')
    a2.set_xlim(min(v.min() - 8, -35), max(v.max() + 8, 10))
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'X7_compton_and_constants.png'), dpi=150)
    plt.close(fig)


# ---- X8 -------------------------------------------------------------------------------

def fig_speed(run, out):
    sc = scores(run)
    meths = methods_in(sc)
    t = [np.nanmedian([r['sec_per_spectrum'] for (n, m), r in sc.items() if m == mm]) for mm in meths]
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    y = np.arange(len(meths))[::-1]
    ax.barh(y, t, color=[COLOR.get(m, MUTED) for m in meths], height=0.6)
    for yi, v in zip(y, t):
        ax.text(v * 1.15, yi, '%.3g s' % v, va='center', fontsize=7, color=INK2)
    ax.set_xscale('log')
    ax.set_yticks(y)
    ax.set_yticklabels([SHORT[m] for m in meths])
    ax.set_xlabel('seconds per spectrum (median over conditions; one CPU)')
    ax.set_title('How fast?', loc='left')
    ax.set_xlim(min(t) / 3, max(t) * 8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'X8_speed.png'), dpi=150)
    plt.close(fig)


def write_tables(run, out):
    """``tables.md``: the scoreboard, the pulls and the XFNTR curves as
    markdown tables, so that the summary quotes the CSVs, not a retyping."""
    sc = scores(run)
    conds = conditions(run)
    meths = methods_in(sc, TABLE_ORDER)
    lines = ['# XRF shootout: tables (generated by tests/tools/xrf_shootout_figures.py; do not edit)', '',
             '## Calibrated bias, % (failed fits, % of spectra, when any)', '',
             '| Condition | factor | ' + ' | '.join(SHORT[m] for m in meths) + ' |',
             '|---|---|' + '---|' * len(meths)]
    for c in conds:
        cells = []
        for m in meths:
            r = sc.get((c['condition'], m))
            if not r:
                cells.append('')
                continue
            f = failed_share(r)
            b = r.get('bias', math.nan)
            txt = ('%+.1f' % (100 * b)) if np.isfinite(b) else 'n/a'
            if f > 0:
                txt += ' (%.0f %% fail)' % (100 * f)
            cells.append(txt)
        lines.append('| %s | %s | %s |' % (c['condition'], c['factor'], ' | '.join(cells)))
    lines += ['', '## RMS error of one spectrum, %', '',
              '| Condition | ' + ' | '.join(SHORT[m] for m in meths) + ' |', '|---|' + '---|' * len(meths)]
    for c in conds:
        cells = []
        for m in meths:
            r = sc.get((c['condition'], m), {})
            v = r.get('rmse', math.nan)
            cells.append('%.1f' % (100 * v) if np.isfinite(v) else '')
        lines.append('| %s | %s |' % (c['condition'], ' | '.join(cells)))
    lines += ['', '## Pull SD (1 is honest; blank: no error bars or too many failures)', '',
              '| Condition | ' + ' | '.join(SHORT[m] for m in meths) + ' |', '|---|' + '---|' * len(meths)]
    for c in conds:
        cells = []
        for m in meths:
            r = sc.get((c['condition'], m), {})
            v = r.get('pull_sd', math.nan)
            cells.append('%.2f' % v if np.isfinite(v) and failed_share(r) <= FAIL_SHARE else '')
        lines.append('| %s | %s |' % (c['condition'], ' | '.join(cells)))
    p = os.path.join(run, 'series_scores.csv')
    if any(os.path.exists(os.path.join(f, 'series_scores.csv')) for f in run.split(',')):
        sv = read(p)
        names = list(dict.fromkeys(r['series'] for r in sv))
        lines += ['', '## XFNTR curves: worst point off the true shape, % (χ²/dof of the mean curve)', '',
                  '| Curve | ' + ' | '.join(SHORT[m] for m in meths) + ' |', '|---|' + '---|' * len(meths)]
        d = {(r['series'], r['method']): r for r in sv}
        for n in names:
            cells = []
            for m in meths:
                r = d.get((n, m))
                cells.append('%.1f (%.3g)' % (100 * num(r['worst']), num(r['chi2_dof'])) if r else '')
            lines.append('| %s | %s |' % (n, ' | '.join(cells)))
    def f(v, fmt):
        return fmt % (100 * v) if np.isfinite(v) else '—'
    lines += ['', '## Better, the same or worse (X5; wins.csv)', '',
              'Accurate: |bias| within 2 % (or 2 standard errors, when larger), at most 5 % of fits failed, and the '
              'bias known to 1 % (one standard error). '
              'A side that has no accurate method shows its least biased one.', '',
              '| Condition | factor | reader\'s best | bias % | RMS % | fails % | others\' best | bias % | RMS % | fails % | '
              'verdict |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in wins_table(run):
        lines.append('| %s | %s | %s%s | %s | %s | %s | %s%s | %s | %s | %s | %s |' % (
            r['condition'], r['factor'], _short(r['reader_best']), '' if r['reader_accurate'] else ' (not accurate)',
            f(r['reader_bias'], '%+.1f'), f(r['reader_rmse'], '%.1f'), f(r['reader_failed'], '%.0f'),
            _short(r['other_best']), '' if r['other_accurate'] else ' (not accurate)', f(r['other_bias'], '%+.1f'),
            f(r['other_rmse'], '%.1f'), f(r['other_failed'], '%.0f'), r['verdict']))
    with open(os.path.join(out, 'tables.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', default=os.path.join('docs', 'studies', 'xrf_shootout', 'run'))
    ap.add_argument('--out', default=os.path.join('docs', 'studies', 'xrf_shootout'))
    ap.add_argument('--only', default=None, help='comma-separated figure numbers, e.g. 1,3')
    a = ap.parse_args(argv)
    style()
    want = set(a.only.split(',')) if a.only else None
    figs = {'1': lambda: fig_scoreboard(a.run, a.out), '2': lambda: fig_counts(a.run, a.out),
            '3': lambda: fig_xfntr(a.run, a.out), '4': lambda: fig_honesty(a.run, a.out),
            '5': lambda: fig_wins(a.run, a.out), '6': lambda: fig_anatomy(a.out),
            '7': lambda: fig_compton(a.out, os.path.join(a.out, 'physics_check.csv')),
            '8': lambda: fig_speed(a.run, a.out), 't': lambda: write_tables(a.run, a.out)}
    for k, f in figs.items():
        if want is None or k in want:
            f()
            print('figure', k)


if __name__ == '__main__':
    main()
