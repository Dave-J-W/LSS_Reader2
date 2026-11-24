"""Study B's figures (F90, MCA line intensities; the owner, 2026-11-24:
"Show some synthetic data replicates and their fits! Show me stats in
graphical form!"; docs/studies/2026-11-24_two_decisions_plan.md).

    python tests/tools/mca_study.py --gauntlet docs/studies/mca_fit/gauntlet --out docs/studies/mca_fit

The gauntlet's run comes first:

    python tests/tools/mca_fit_gauntlet.py --out docs/studies/mca_fit/gauntlet \\
        --design all,robust,counts --methods study --compton shells

Its tables (verdict.csv, series.csv, conditions.csv) give B3–B7. B1 and B2
are drawn here from the generator (``tests/synthetic/mca.py``, the
'shells' Compton model).

- **B1** the anatomy of the hard case: its parts stacked on a log scale,
  with the ±2 and ±3 FWHM boxes;
- **B2** six replicates at about 90, 270 and 1000 line counts, each with
  every estimator's fit, and their residuals beneath;
- **B3** the bias of the data-weighted fit and of P1 against the line
  counts, on a clean line, with the 1/N law fitted;
- **B4** bias ± its standard error per estimator, for each feature alone;
- **B5** the XFNTR series' ratio to the truth against Qz;
- **B6** the share of random conditions within 1 %, per estimator and
  class of condition;
- **B7** the robustness map: where each conclusion holds, over the escape
  fraction × the O 1s wing.

Outputs: ``B1_anatomy.png`` … ``B7_robustness.png``, the numbers behind
them as CSV (``B3_counts.csv``, ``B4_features.csv``, ``B6_pass_rates.csv``,
``B7_robustness.csv``), and ``numbers.json`` for the summary. All synthetic,
so public.
"""
import argparse
import csv
import json
import math
import os
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
sys.path.insert(0, os.path.join(os.getcwd(), 'tests', 'tools'))

import matplotlib                                         # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                           # noqa: E402

from lss_core import fluorescence as fluo, peaks          # noqa: E402
from synthetic import mca                                 # noqa: E402
import mca_fit_gauntlet as g                              # noqa: E402

FITS = ('fit', 'p1', 'p1p2', 'p1p3', 'p1p2p3')
NAMES = {'window': 'window sum', 'sides': 'window − sides', 'fit': 'fit, data weights (today)', 'p1': 'P1',
         'p1p2': 'P1+P2', 'p1p3': 'P1+P3', 'p1p2p3': 'P1+P2+P3'}
COLOURS = {'window': '0.45', 'sides': '0.7', 'fit': 'C3', 'p1': 'C0', 'p1p2': 'C2', 'p1p3': 'C1', 'p1p2p3': 'C4'}


def _read(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def _write(path, rows):
    if not rows:
        return
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})


def hard():
    return g.with_shells(g.core()['hard'])


# ---- B1 ---------------------------------------------------------------------------

def b1(out):
    cond = hard()
    s = cond.spectrum()
    e = s.energy
    sel = (e > 7.5) & (e < 10.5)
    parts = [('background', s.part(['background']), '0.8'),
             ('detector tails and shelves', s.part(None, ['tail', 'shelf']), 'C4'),
             ('Si escape peaks', s.part(None, ['escape']), 'C2'),
             ('Compton, O 1s (core)', s.part(['Compton core'], ['peak']), 'C1'),
             ('Compton, valence', s.part(['Compton valence'], ['peak']), 'C9'),
             ('Rayleigh (elastic)', s.part(['Rayleigh'], ['peak']), 'C0'),
             ('Zn Kβ', s.photopeak('Zn', 'Kb'), 'C5'),
             ('Zn Kα (the line)', s.photopeak('Zn'), 'C3')]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    base = np.full(sel.sum(), 1e-2)
    for lab, v, col in parts:
        top = base + v[sel]
        ax.fill_between(e[sel], base, top, color=col, alpha=0.75, lw=0, label=lab)
        base = top
    ax.plot(e[sel], s.expected[sel], 'k', lw=0.8, label='total (expected)')
    for k, (bx, ls) in enumerate(((2.0, '-'), (3.0, '--'))):
        lo, hi = replace(cond, box=bx).box_range()
        for v in (lo, hi):
            ax.axvline(v, color='k', ls=ls, lw=0.9, label='box ±%g FWHM' % bx if v == lo else None)
    ax.set_yscale('log')
    ax.set_ylim(0.1, s.expected[sel].max() * 3)
    ax.set_xlabel('energy (keV)')
    ax.set_ylabel('expected counts per 10 eV channel')
    ax.set_title('B1. The hard case: Zn Kα (1e3 photons) under a 10 keV beam (1e6 elastic), its parts stacked',
                 fontsize=9)
    ax.legend(fontsize=7, ncol=2, loc='upper left')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'B1_anatomy.png'), dpi=110)
    plt.close(fig)
    lo, hi = cond.box_range()
    box = (e >= lo) & (e <= hi)
    return {lab: float(v[box].sum()) for lab, v, _ in parts}


# ---- B2 ---------------------------------------------------------------------------

def _estimates(cond, s, counts):
    """{method: (estimate, error, FitResult or None)} for one spectrum."""
    out = {}
    est = g.estimate(cond, [s], [counts], list(g.STUDY_METHODS))
    data = g.normalise(counts, s.calib)
    x = data[:, 0]
    for m in FITS:
        if est[m][0] is None:
            out[m] = (math.nan, math.nan, None)
            continue
        d = fluo.strip_escape(data, cond.assumed_escape) if 'p3' in m else data
        kw = dict(fwhm=fluo.detector_fwhm(cond.line, cond.detector.noise)) if 'p2' in m else {}
        ref, each = peaks.fit_series(x, [d[:, 1]], [d[:, 2]], g.fit_options(cond, [cond.line], **kw),
                                     weights='data' if m == 'fit' else 'poisson')
        out[m] = (est[m][0][0], est[m][0][1], each[0] if each else None)
    for m in ('window', 'sides'):
        out[m] = (est[m][0][0], est[m][0][1], None) if est[m][0] is not None else (math.nan, math.nan, None)
    return out


def b2(out):
    h = hard()
    base = replace(h, beam=replace(h.beam, core_scale=0.25))     # the hard detector, a quarter of water's O 1s wing
    rows = []
    levels = ((100.0, '≈90'), (300.0, '≈270'), (1120.0, '≈1000'))
    fig = plt.figure(figsize=(19, 10.5))
    outer = fig.add_gridspec(len(levels), 6, hspace=0.32, wspace=0.28, top=0.92, bottom=0.05, left=0.04, right=0.99)
    for i, (photons, lab) in enumerate(levels):
        cond = replace(base, photons=photons, series=1)
        s = cond.spectrum()
        ka = float(s.photopeak('Zn').sum())
        lo, hi = cond.box_range()
        e = s.energy
        sel = (e > lo - 0.15) & (e < hi + 0.15)
        rng = np.random.default_rng([2026, i])
        for k in range(6):
            counts = s.draw(rng)
            inner = outer[i, k].subgridspec(2, 1, height_ratios=(3, 1), hspace=0.05)
            ax, rax = fig.add_subplot(inner[0]), fig.add_subplot(inner[1])
            ax.step(e[sel], counts[sel], where='mid', color='0.55', lw=0.7)
            ax.axvspan(lo, hi, color='C3', alpha=0.05)
            got = _estimates(cond, s, counts)
            xx = np.linspace(lo, hi, 300)
            for m in FITS:
                r = got[m][2]
                if r is None:
                    continue
                ax.plot(xx, r.model(xx) * g.scale(), color=COLOURS[m], lw=0.9)
                d = g.normalise(counts, s.calib)
                if 'p3' in m:
                    d = fluo.strip_escape(d, cond.assumed_escape)
                w = (d[:, 0] >= r.window[0]) & (d[:, 0] <= r.window[1])
                sig = np.where(d[w, 2] > 0, d[w, 2], np.median(d[w, 2][d[w, 2] > 0]))
                rax.plot(d[w, 0], (d[w, 1] - r.model(d[w, 0])) / sig, '.', ms=1.5, color=COLOURS[m])
            rax.axhline(0, color='k', lw=0.5)
            rax.set_ylim(-4, 4)
            rax.set_xlim(ax.get_xlim())
            ax.set_xticklabels([])
            ax.tick_params(labelsize=6)
            rax.tick_params(labelsize=6)
            text = ['true %.0f' % ka] + ['%s %s' % (NAMES[m].split(',')[0], '%.0f' % got[m][0] if np.isfinite(got[m][0])
                                                     else 'failed') for m in ('window',) + FITS]
            ax.text(0.02, 0.97, '\n'.join(text), transform=ax.transAxes, fontsize=5, va='top', family='monospace')
            if k == 0:
                ax.set_ylabel('Kα %s counts' % lab, fontsize=8)
                rax.set_ylabel('resid. (σ)', fontsize=6)
            for m in ('window',) + FITS:
                rows.append(dict(level=lab, replicate=k + 1, method=m, estimate=got[m][0], error=got[m][1], truth=ka))
    handles = [plt.Line2D([], [], color=COLOURS[m], lw=1.5, label=NAMES[m]) for m in FITS]
    fig.legend(handles=handles, loc='upper center', ncol=len(FITS), fontsize=8, bbox_to_anchor=(0.5, 0.955))
    fig.suptitle('B2. Six replicates at three line counts (the hard detector: Reed escapes, tail 1 %, shelf 0.2 %; Compton with '
                 'a quarter of water\'s O 1s wing): every estimator\'s fit over the box (±2 FWHM), residuals beneath',
                 fontsize=10, y=0.99)
    fig.savefig(os.path.join(out, 'B2_replicates.png'), dpi=90)
    plt.close(fig)
    _write(os.path.join(out, 'B2_replicates.csv'), rows)


# ---- B3–B7 from the gauntlet's tables -----------------------------------------------

def _verdict(gdir):
    rows = _read(os.path.join(gdir, 'verdict.csv'))
    return {(r['condition'], r['method']): r for r in rows}, rows


def _bias_se(r):
    b, rmse, n = _f(r['rel_bias']), _f(r['rel_rmse']), _f(r['n']) - _f(r['failed'])
    sd = math.sqrt(max(rmse ** 2 - b ** 2, 0.0))
    return b, sd / math.sqrt(n) if n > 1 else math.nan


def b3(gdir, out):
    idx, rows = _verdict(gdir)
    conds = sorted({r['condition'] for r in rows if r['condition'].startswith('counts_')},
                   key=lambda c: _f(idx[(c, 'fit')]['ka_counts']))
    table = []
    for c in conds:
        for m in ('fit', 'p1'):
            b, se = _bias_se(idx[(c, m)])
            table.append(dict(condition=c, method=m, ka_counts=_f(idx[(c, m)]['ka_counts']), rel_bias=b, se=se,
                              pull_mean=_f(idx[(c, m)]['pull_mean']), pull_sd=_f(idx[(c, m)]['pull_sd'])))
    _write(os.path.join(out, 'B3_counts.csv'), table)
    n = np.array([t['ka_counts'] for t in table if t['method'] == 'fit'])
    bf = np.array([t['rel_bias'] for t in table if t['method'] == 'fit'])
    use = n >= 100
    c = float(-np.sum(bf[use] / n[use]) / np.sum(1.0 / n[use] ** 2))      # least squares of b = −c/N
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for m, mk in (('fit', 'o'), ('p1', 's')):
        t = [x for x in table if x['method'] == m]
        ax.errorbar([x['ka_counts'] for x in t], [100 * x['rel_bias'] for x in t], [200 * x['se'] for x in t],
                    fmt=mk, color=COLOURS[m], label=NAMES[m], capsize=2)
    nn = np.logspace(math.log10(n.min()), math.log10(n.max()), 200)
    ax.plot(nn, -100 * c / nn, color=COLOURS['fit'], lw=0.8, ls='--', label='−c/N, c = %.1f counts' % c)
    ax.axhline(0, color=COLOURS['p1'], lw=0.8, ls='--', label='Poisson likelihood: 0 (to order 1/N²)')
    ax.axhspan(-1, 1, color='0.9', zorder=0, label='±1 %')
    ax.set_xscale('log')
    ax.set_xlabel('true Kα counts in the spectrum')
    ax.set_ylabel('bias of the line area (%)')
    ax.set_title('B3. Why weighting matters: a clean line on 1 count per channel (error bars: 2 SE)', fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'B3_weighting.png'), dpi=110)
    plt.close(fig)
    return {'neyman_c': c, 'table': table}


FEATURES = [('smooth', 'baseline (smooth)'), ('escape_x1', 'escape, Reed'), ('escape_x5', 'escape, 5 × Reed'),
            ('compton_core_0.05', 'O 1s wing ×0.25'), ('compton_core_0.2', 'O 1s wing ×1 (water)'),
            ('compton_fwhm_0.3', 'Doppler ×1.6'), ('tail_0.03', 'tail 3 %'), ('shelf_0.005', 'shelf 0.5 %'),
            ('gain_+0.005', 'gain +0.5 %'), ('offset_+0.03', 'offset +30 eV'), ('counts_x0.3', '270 counts'),
            ('hard', 'all at once (hard)')]


def b4(gdir, out):
    idx, _ = _verdict(gdir)
    meths = ('window', 'sides') + FITS
    table = []
    fig, ax = plt.subplots(figsize=(10, 6.5))
    for i, (c, lab) in enumerate(FEATURES):
        for k, m in enumerate(meths):
            r = idx.get((c, m))
            if r is None:
                continue
            b, se = _bias_se(r)
            failed = int(r['failed'])
            table.append(dict(condition=c, feature=lab, method=m, rel_bias=b, se=se, failed=failed))
            y = i + (k - len(meths) / 2) * 0.1
            if not np.isfinite(b):
                continue
            bb = float(np.clip(100 * b, -30, 30))
            ax.errorbar(bb, y, xerr=200 * se if abs(100 * b) < 30 else None, fmt='o' if not failed else 'x',
                        color=COLOURS[m], ms=4, capsize=1.5, label=NAMES[m] if i == 0 else None)
            if abs(100 * b) >= 30:
                ax.annotate('%+.0f %%' % (100 * b), (bb, y), fontsize=5, color=COLOURS[m],
                            xytext=(3 if bb > 0 else -22, -2), textcoords='offset points')
    ax.axvspan(-1, 1, color='0.9', zorder=0)
    ax.axvline(0, color='k', lw=0.6)
    ax.set_yticks(range(len(FEATURES)))
    ax.set_yticklabels([lab for _, lab in FEATURES], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(-31, 31)
    ax.set_xlabel('bias of the line area against the true line (%; clipped at ±30, ×: some fits failed)')
    ax.set_title('B4. One feature at a time (from the smooth baseline; error bars 2 SE; shaded ±1 %)', fontsize=9)
    ax.legend(fontsize=7, loc='lower right')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'B4_features.png'), dpi=110)
    plt.close(fig)
    _write(os.path.join(out, 'B4_features.csv'), table)
    return table


def b5(gdir, out):
    rows = _read(os.path.join(gdir, 'series.csv'))
    names = ['xfntr_smooth', 'xfntr_smooth_weak', 'xfntr_hard', 'xfntr_hard_cu']
    qz = np.asarray(g.SeriesCond('x', g.Cond('x')).qz)
    fig, axes = plt.subplots(len(names), 1, figsize=(8, 2.6 * len(names)), sharex=True)
    for ax, n in zip(axes, names):
        for m in ('window',) + FITS:
            t = [r for r in rows if r['condition'] == n and r['method'] == m]
            if not t:
                continue
            y = np.array([_f(r['mean_ratio']) for r in t])
            se = np.array([_f(r['se']) for r in t])
            ax.errorbar(qz[:len(y)], y, 2 * se, color=COLOURS[m], lw=1, marker='.', capsize=1.5, label=NAMES[m])
        ax.axhline(1, color='k', lw=0.6)
        ax.axvline(0.0217, color='0.5', ls=':', lw=0.8)
        ax.set_ylim(0.8, 1.2)
        ax.set_ylabel('estimate / truth\n(÷ one scale)', fontsize=8)
        ax.set_title(n, fontsize=8)
    axes[0].legend(fontsize=6, ncol=3)
    axes[-1].set_xlabel('Qz (1/Å); dotted: Qc of water')
    fig.suptitle('B5. XFNTR curves: does each estimator keep the curve\'s shape? (window clipped at 0.8–1.2)', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'B5_series.png'), dpi=110)
    plt.close(fig)
    sv = _read(os.path.join(gdir, 'series_verdict.csv'))
    return {(r['condition'], r['method']): (_f(r['chi2_dof']), _f(r['worst_point']), r['passes'] == 'True') for r in sv}


def _klass(c):
    if _f(c['photons']) * 0.887 < 300:
        return 'low counts (< 300)'
    if _f(c['core_scale']) > 1.0:
        return 'strong O 1s wing'
    if _f(c['escape']) > 2.0:
        return 'large escape (> 2 × Reed)'
    if _f(c['doppler_scale']) > 1.5:
        return 'wide Doppler (> 1.5 ×)'
    if c['others']:
        return 'Cu neighbour'
    return 'the rest'


def b6(gdir, out):
    idx, rows = _verdict(gdir)
    conds = {c['condition']: c for c in _read(os.path.join(gdir, 'conditions.csv')) if c['factor'] == 'random'}
    classes = ['low counts (< 300)', 'strong O 1s wing', 'large escape (> 2 × Reed)', 'wide Doppler (> 1.5 ×)',
               'Cu neighbour', 'the rest', 'all']
    meths = ('window', 'sides') + FITS
    share = np.full((len(meths), len(classes)), np.nan)
    count = np.zeros(len(classes), int)
    table = []
    for j, k in enumerate(classes):
        names = [n for n, c in conds.items() if k == 'all' or _klass(c) == k]
        count[j] = len(names)
        for i, m in enumerate(meths):
            ok = [idx[(n, m)]['failed'] == '0' and abs(_f(idx[(n, m)]['rel_bias'])) < 0.01 for n in names
                  if (n, m) in idx]
            share[i, j] = np.mean(ok) if ok else np.nan
            table.append(dict(method=m, klass=k, conditions=len(ok), share_within_1pc=share[i, j]))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    im = ax.imshow(share, cmap='viridis', vmin=0, vmax=1, aspect='auto')
    for i in range(len(meths)):
        for j in range(len(classes)):
            if np.isfinite(share[i, j]):
                ax.text(j, i, '%.0f %%' % (100 * share[i, j]), ha='center', va='center', fontsize=7,
                        color='w' if share[i, j] < 0.6 else 'k')
    ax.set_xticks(range(len(classes)))
    ax.set_xticklabels(['%s\n(%d)' % (k, n) for k, n in zip(classes, count)], fontsize=7)
    ax.set_yticks(range(len(meths)))
    ax.set_yticklabels([NAMES[m] for m in meths], fontsize=8)
    fig.colorbar(im, ax=ax, label='share within 1 % of the true line, no failure')
    ax.set_title('B6. Random conditions (all features at once): who passes, by class of condition', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'B6_pass_rates.png'), dpi=110)
    plt.close(fig)
    _write(os.path.join(out, 'B6_pass_rates.csv'), table)
    return table


def b7(gdir, out):
    idx, _ = _verdict(gdir)
    esc, core = (0.0, 0.5, 1.0, 2.0, 3.0), (0.0, 0.5, 1.0, 2.0)
    concl = [('P1 at least as good as today\'s fit', lambda b: abs(b['p1']) <= abs(b['fit']) + 0.002),
             ('P1+P2+P3 the best fit', lambda b: abs(b['p1p2p3']) <= min(abs(b[m]) for m in FITS) + 0.002),
             ('P1+P2+P3 within 1 %', lambda b: abs(b['p1p2p3']) < 0.01),
             ('the window sum fails (> 1 %)', lambda b: abs(b['window']) > 0.01)]
    table = []
    fig, axes = plt.subplots(1, len(concl), figsize=(4.2 * len(concl), 3.8))
    for ax, (title, rule) in zip(axes, concl):
        grid = np.full((len(core), len(esc)), np.nan)
        for i, c in enumerate(core):
            for j, e in enumerate(esc):
                name = 'robust_esc%g_core%g' % (e, c)
                b = {m: _f(idx[(name, m)]['rel_bias']) if idx[(name, m)]['failed'] == '0' else math.inf
                     for m in ('window',) + FITS if (name, m) in idx}
                if len(b) < 1 + len(FITS):
                    continue
                ok = bool(rule(b))
                grid[i, j] = ok
                table.append(dict(conclusion=title, escape=e, wing=c, holds=ok,
                                  **{'bias_' + m: b[m] for m in ('window',) + FITS}))
                ax.text(j, i, 'P1P2P3 %+.1f\nfit %+.1f' % (100 * b['p1p2p3'], 100 * b['fit'])
                        if np.isfinite(b['p1p2p3']) and np.isfinite(b['fit']) else 'failed', ha='center',
                        va='center', fontsize=6)
        ax.imshow(grid, cmap='RdYlGn', vmin=0, vmax=1, origin='lower', aspect='auto', alpha=0.8)
        ax.set_xticks(range(len(esc)))
        ax.set_xticklabels(['%g' % e for e in esc])
        ax.set_yticks(range(len(core)))
        ax.set_yticklabels(['%g' % c for c in core])
        ax.set_xlabel('Si escape (× Reed)')
        ax.set_ylabel('O 1s wing (× water)')
        ax.set_title(title, fontsize=8)
    fig.suptitle('B7. Robustness: where each conclusion holds (green), the hard case\'s other features fixed; '
                 'numbers: bias %', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'B7_robustness.png'), dpi=110)
    plt.close(fig)
    _write(os.path.join(out, 'B7_robustness.csv'), table)
    return table


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--gauntlet', required=True, help='the study run of mca_fit_gauntlet.py (its --out)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', default='', help='comma-separated figures to make (B1,...,B7); empty: all')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    want = set(a.only.split(',')) if a.only else {'B%d' % k for k in range(1, 8)}
    numbers = {}
    if 'B1' in want:
        numbers['B1_box_counts'] = b1(a.out)
    if 'B2' in want:
        b2(a.out)
    if 'B3' in want:
        numbers['B3'] = b3(a.gauntlet, a.out)
    if 'B4' in want:
        numbers['B4'] = b4(a.gauntlet, a.out)
    if 'B5' in want:
        numbers['B5'] = {'%s|%s' % k: v for k, v in b5(a.gauntlet, a.out).items()}
    if 'B6' in want:
        numbers['B6'] = b6(a.gauntlet, a.out)
    if 'B7' in want:
        numbers['B7'] = b7(a.gauntlet, a.out)
    with open(os.path.join(a.out, 'numbers.json'), 'w') as f:
        json.dump(numbers, f, indent=1, default=float)


if __name__ == '__main__':
    main()
