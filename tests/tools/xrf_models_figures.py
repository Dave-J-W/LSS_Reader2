"""Figures of the models study (``docs/studies/xrf_models/README.md``), from
public files only: the committed blanks, the ladder fits and the shootout
runs on twins (``tests/tools/xrf_models.py``), and the derived line-shape
numbers (``tests/tools/xrf_lineshape.py``'s ``line_shapes.csv``).

    python tests/tools/xrf_models_figures.py --out docs/studies/xrf_models [--only 1,3]

* ``M1_scatter_fits.png``: four public blanks and the three scatter models,
  with deviance residuals;
* ``M2_scatter_boxes.png``: data / model − 1 in boxes under the scatter, by
  offset below the beam, and the misfit at the counts the shootout uses;
* ``M3_twins.png``: every method's bias on the model twins against its
  bias on the real blanks, beside the floor (a second draw of the full
  model's twin against the first);
* ``M4_line_shapes.png``: the shape ladder on real lines (derived numbers
  only: no spectrum);
* ``M5_line_shape_effect.png``: every method's bias with Gaussian and with
  real-shaped lines injected, against the elastic-shaped lines of the
  committed run.
"""
import argparse
import csv
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import xrf_shootout_figures as F                              # noqa: E402  (style, colours, labels)
import matplotlib.pyplot as plt                                # noqa: E402

MODEL_COLOR = {'generator': F.MUTED, 'gaussian': '#e34948', 'full': '#2a78d6'}
MODEL_LABEL = {'generator': 'generator defaults (the synthetic shootout)', 'gaussian': 'Gaussian detector, rest free',
               'full': 'full model (tails, shelf, high tail free)'}
MODEL_SHORT = {'generator': 'generator defaults', 'gaussian': 'Gaussian detector', 'full': 'full model'}


def probe_name(p):
    """A line probe of xrf_lineshape.py ('A-L1', 'B-K2-e3', 'B-K1-sum7raw') -> plain words."""
    parts = p.split('-')
    if parts[0] == 'A':
        return 'single-element, burn K line' if parts[1] == 'K' else 'single-element, L file %s' % parts[1][1:]
    det, f = '7-element', 'K file %s' % parts[1][1:]
    rest = parts[2]
    if rest.startswith('e'):
        return '%s, %s, element %s' % (det, f, rest[1:])
    return '%s, %s, all 7 summed%s' % (det, f, ' (header gains)' if rest.endswith('hdr') else '')
SHOW = ('E10-k', 'E10-d', 'E9.2-a', 'E6.1-a')
METHODS = ('window', 'fit_data', 'p1', 'p1p3', 'p1p2p3', 'xeray', 'pymca', 'pyxrf')


def read(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def fig_fits(scatter, out):
    R = read(os.path.join(scatter, 'residuals.csv'))
    L = {(r['blank'], r['model']): r for r in read(os.path.join(scatter, 'ladder.csv'))}
    fig, axes = plt.subplots(2, len(SHOW), figsize=(4.0 * len(SHOW), 6.2), gridspec_kw=dict(height_ratios=(2.3, 1)),
                             sharex='col')
    for j, bid in enumerate(SHOW):
        ax, rx = axes[0, j], axes[1, j]
        rows = [r for r in R if r['blank'] == bid]
        e = np.array([num(r['energy_keV']) for r in rows if r['model'] == 'full'])
        n = np.array([num(r['counts']) for r in rows if r['model'] == 'full'])
        ax.semilogy(e, np.maximum(n, 0.5), '.', ms=2.5, color=F.INK, label='real blank')
        for m in ('generator', 'gaussian', 'full'):
            mu = np.array([num(r['model_counts']) for r in rows if r['model'] == m])
            res = np.array([num(r['deviance_residual']) for r in rows if r['model'] == m])
            ax.semilogy(e, mu, color=MODEL_COLOR[m], lw=1.2, label=MODEL_LABEL[m])
            rx.plot(e, np.clip(res, -14, 14), color=MODEL_COLOR[m], lw=0.8)
        lr = L[(bid, 'full')]
        ax.set_title('%s (%s)' % (F.blank_name(bid), F.READOUT[lr['readout']]), loc='left', fontsize=9)
        txt = 'misfit (deviance per degree of freedom;\n1 = as good as the counting noise allows):\n' + '\n'.join(
            '%s: %.1f' % (MODEL_SHORT[m], num(L[(bid, m)]['dev_per_dof'])) for m in ('generator', 'gaussian', 'full'))
        ax.text(0.02, 0.97, txt, transform=ax.transAxes, va='top', fontsize=7, color=F.INK2)
        rx.axhline(0, color=F.INK2, lw=0.6)
        rx.set_ylim(-14, 14)
        rx.set_xlabel('energy (keV)')
    axes[0, 0].set_ylabel('counts per channel')
    axes[1, 0].set_ylabel('miss, in noise units\n(deviance residual,\nclipped at ±14)')
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc='lower center', ncol=4, fontsize=8, frameon=False)
    fig.suptitle('M1. Real scatter (public blanks) against three scatter models, each fitted by Poisson likelihood '
                 'over the whole blank', x=0.01, ha='left', fontsize=10, fontweight='bold')
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(out, 'M1_scatter_fits.png'), dpi=150)
    plt.close(fig)


def fig_boxes(scatter, out, blanks_run):
    L = read(os.path.join(scatter, 'ladder.csv'))
    offs = sorted({float(k.split('_')[1]) for k in L[0] if k.startswith('box_') and not k.endswith('_z')})
    conds = read(os.path.join(blanks_run, 'conditions.csv')) if os.path.exists(os.path.join(blanks_run, 'conditions.csv')) else []
    pmed = {}
    for c in conds:
        pmed.setdefault(c['blank'], []).append(num(c['p']))
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    for ax, ro in zip(axes[:2], ('A', 'B')):
        for m in ('generator', 'gaussian', 'full'):
            rows = [r for r in L if r['readout'] == ro and r['model'] == m]
            v = np.array([[num(r.get('box_%g' % d)) for d in offs] for r in rows]) * 100
            med = np.nanmedian(v, axis=0)
            ax.fill_between(offs, np.nanmin(v, axis=0), np.nanmax(v, axis=0), color=MODEL_COLOR[m], alpha=0.15, lw=0)
            ax.plot(offs, med, 'o-', color=MODEL_COLOR[m], label=MODEL_LABEL[m], ms=4)
        ax.axhspan(-2, 2, color=F.GRID, alpha=0.8, lw=0)
        ax.axhline(0, color=F.INK2, lw=0.7)
        ax.set_ylim(-70, 40)
        ax.set_xlabel('how far below the beam a line would sit (keV); window: that energy ± 1 FWHM')
        ax.set_ylabel('real counts / model counts − 1 (%)')
        ax.set_title('%s (%d blanks): line, median; band, range' % (F.READOUT[ro].capitalize(), len({r['blank'] for r in L if r['readout'] == ro})),
                     loc='left', fontsize=9)
    axes[0].legend(fontsize=7, loc='lower left')
    ax = axes[2]
    ids = [b for b in sorted({r['blank'] for r in L})]
    x = np.arange(len(ids))
    for k, m in enumerate(('generator', 'gaussian', 'full')):
        full, use = [], []
        for b in ids:
            r = [q for q in L if q['blank'] == b and q['model'] == m][0]
            d = num(r['dev_per_dof_low'])
            p = np.median(pmed[b]) if b in pmed else math.nan
            full.append(d)
            use.append(1 + p * (d - 1) if np.isfinite(p) else math.nan)
        ax.bar(x + (k - 1) * 0.27, use, 0.25, color=MODEL_COLOR[m], label=MODEL_SHORT[m])
    ax.axhline(1, color=F.INK2, lw=0.7)
    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels([F.blank_name(b) for b in ids], rotation=60, ha='right', fontsize=7)
    ax.set_ylabel('misfit below the beam, at the shootout\'s counts\n(deviance per degree of freedom)')
    ax.set_title('Misfit at the counts the shootout uses: 1 + p × (misfit − 1),\n'
                 'p the share of counts kept (median; no bar: blank not used)',
                 loc='left', fontsize=9)
    ax.legend(fontsize=7)
    fig.suptitle('M2. Where each scatter model misses the real scatter, in the windows a line would be fitted in',
                 x=0.01, ha='left', fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'M2_scatter_boxes.png'), dpi=150)
    plt.close(fig)


def _scatter_panel(ax, rows, xkey, ykey, title, lim=(-60, 60)):
    for m in METHODS:
        R = [r for r in rows if r['method'] == m]
        if not R:
            continue
        x = np.array([num(r[xkey]) for r in R]) * 100
        y = np.array([num(r[ykey]) for r in R]) * 100
        ax.scatter(np.clip(x, *lim), np.clip(y, *lim), s=7, color=F.COLOR.get(m, F.MUTED), alpha=0.7,
                   label=F.SHORT.get(m, m), lw=0)
    ax.plot(lim, lim, color=F.INK2, lw=0.7)
    ax.fill_between(lim, [lim[0] - 2, lim[1] - 2], [lim[0] + 2, lim[1] + 2], color=F.GRID, alpha=0.8, lw=0)
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_title(title, loc='left', fontsize=9)


def fig_twins(scatter, out):
    C = read(os.path.join(scatter, 'compare.csv'))
    S = read(os.path.join(scatter, 'compare_summary.csv'))
    fig, axes = plt.subplots(1, 4, figsize=(20, 5.4), sharey=True)
    for ax, m in zip(axes, ('full_redraw', 'full', 'gaussian', 'generator')):
        rows = [r for r in C if r['model'] == m]
        if not rows:
            ax.set_visible(False)
            continue
        agree = np.mean([r['accurate_real'] == r['accurate_twin'] for r in rows])
        d = np.array([num(r['diff']) for r in rows]) * 100
        name = ('The floor: two draws of the full model' if m == 'full_redraw'
                else 'Twins from the %s, against the real' % MODEL_SHORT[m])
        _scatter_panel(ax, rows, 'bias_real', 'bias_twin',
                       '%s\nmedian |difference| %.1f %%, 90th percentile %.1f %%; "accurate" the same in %.0f %%'
                       % (name, np.nanmedian(np.abs(d)), np.nanpercentile(np.abs(d), 90), 100 * agree))
        ax.set_xlabel('bias on the first draw (%)' if m == 'full_redraw' else 'bias on the real blank (%)')
    axes[0].set_ylabel('bias on the model twin of the blank (%)')
    axes[0].legend(fontsize=7, loc='upper left', markerscale=2)
    fig.suptitle('M3. The blank shootout run on model twins of the blanks: one point per condition and method '
                 '(240 conditions, 50 series of 10 each; grey band ±2 %)', x=0.01, ha='left', fontsize=10,
                 fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'M3_twins.png'), dpi=150)
    plt.close(fig)


def fig_lines(lines, out):
    R = read(os.path.join(lines, 'line_shapes.csv'))
    probes = []
    for r in R:
        if r['probe'] not in probes:
            probes.append(r['probe'])
    shapes = ['gauss_res', 'gauss', 'elastic', 'tail', 'tail_shelf', 'hypermet']
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    ax = axes[0]
    for p in probes:
        if p.endswith('sum7hdr'):
            continue                                   # the header-calibrated sum of file 2 (wrong gains): README
        v = [num([r for r in R if r['probe'] == p and r['shape'] == s][0]['dev_per_dof']) for s in shapes]
        c = '#2a78d6' if p.startswith('A') else ('#eb6834' if '-e' in p else '#6250d6')
        ax.plot(range(len(shapes)), v, '-o', color=c, ms=3, lw=0.9, alpha=0.8)
    ax.set_yscale('log')
    ax.set_xticks(range(len(shapes)))
    ax.set_xticklabels(['Gaussian\nat resolution', 'Gaussian', 'elastic\'s\nshape', 'one tail', 'tail +\nshelf',
                        'two tails\n+ shelf'], fontsize=8)
    ax.set_ylabel('misfit of the line fit (deviance per degree of freedom)')
    ax.set_title('The shape ladder on real lines\nblue: the single-element detector; orange: one element of the\n'
                 '7-element detector; violet: its seven summed', loc='left', fontsize=9)
    ax = axes[1]
    sel = [p for p in probes if not p.endswith('sum7hdr')]
    y = np.arange(len(sel))[::-1]
    for i, p in enumerate(sel):
        g = [r for r in R if r['probe'] == p and r['shape'] == 'gauss'][0]
        t = [r for r in R if r['probe'] == p and r['shape'] == 'tail'][0]
        c = '#2a78d6' if p.startswith('A') else ('#eb6834' if '-e' in p else '#6250d6')
        ax.plot([num(g['fwhm_over_resolution'])], [y[i]], 'o', color=c, ms=5)
        ax.plot([num(t['fwhm_over_resolution'])], [y[i]], 'o', mfc='none', mec=c, ms=6)
    ax.axvline(1, color=F.INK2, lw=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels([probe_name(q) for q in sel], fontsize=7)
    ax.set_xlabel('line FWHM / resolution measured on the scatter')
    ax.set_title('Width: dot, Gaussian fit; ring, the core of the one-tail fit\n(the sums with the header\'s gains are left out)', loc='left', fontsize=9)
    ax = axes[2]
    for i, p in enumerate(sel):
        t = [r for r in R if r['probe'] == p and r['shape'] == ('tail_shelf' if p.startswith('A') else 'tail')][0]
        c = '#2a78d6' if p.startswith('A') else ('#eb6834' if '-e' in p else '#6250d6')
        ax.barh(y[i], 100 * num(t['tail']), color=c, height=0.7)
        ax.barh(y[i], 100 * num(t['shelf']), left=100 * num(t['tail']), color=c, alpha=0.35, height=0.7)
        ax.text(100 * (num(t['tail']) + num(t['shelf'])) + 1, y[i], '%.0f eV' % (1000 * num(t['tail_slope_keV'])),
                va='center', fontsize=6, color=F.INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([probe_name(q) for q in sel], fontsize=7)
    ax.set_xlabel('% of the line\'s photons: tail (dark; decay length beside) and shelf (light)')
    ax.set_title('Not in the Gaussian (single-element: tail + shelf fit;\n7-element: one-tail fit)', loc='left', fontsize=9)
    fig.suptitle('M4. Is a Gaussian enough? Real lines: on the single-element detector, an L family (5 files, '
                 '1.5·10⁶ counts each) and the burn series\' K line; on the 7-element detector, a K family on every '
                 'element of two files', 
                 x=0.01, ha='left', fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'M4_line_shapes.png'), dpi=150)
    plt.close(fig)


def fig_shape_effect(out, base, runs):
    real = {(r['condition'], r['method']): r for d in base for r in read(os.path.join(d, 'scores.csv'))}
    have = [(lab, d) for lab, d in runs if os.path.exists(os.path.join(d, 'scores.csv'))]
    fig, axes = plt.subplots(1, len(have), figsize=(6.5 * len(have), 5.6), sharey=True, squeeze=False)
    for ax, (lab, d) in zip(axes[0], have):
        rows = []
        for r in read(os.path.join(d, 'scores.csv')):
            q = real.get((r['condition'], r['method']))
            if q is not None:
                rows.append(dict(method=r['method'], x=q['bias'], y=r['bias'], diff=num(r['bias']) - num(q['bias'])))
        dd = np.array([r['diff'] for r in rows]) * 100
        _scatter_panel(ax, rows, 'x', 'y', '%s lines: median |difference| %.1f %%, 90th percentile %.1f %%'
                       % (lab, np.nanmedian(np.abs(dd)), np.nanpercentile(np.abs(dd), 90)))
        ax.set_xlabel('bias with the elastic-shaped line (the committed run, %)')
    axes[0, 0].set_ylabel('bias with this line shape (%)')
    axes[0, 0].legend(fontsize=7, loc='upper left', markerscale=2)
    fig.suptitle('M5. Does the line\'s shape change the verdicts? The real-blank shootout with other injected shapes '
                 '(each method calibrated on a clean twin of the same shape)', x=0.01, ha='left', fontsize=10,
                 fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'M5_line_shape_effect.png'), dpi=150)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=os.path.join('docs', 'studies', 'xrf_models'))
    ap.add_argument('--only', default=None, help='comma-separated figure numbers')
    a = ap.parse_args(argv)
    F.style()
    sc = os.path.join(a.out, 'scatter')
    base = os.path.join('docs', 'studies', 'xrf_shootout', 'run_blanks')
    want = set(a.only.split(',')) if a.only else None
    jobs = {'1': (lambda: fig_fits(sc, a.out), os.path.join(sc, 'residuals.csv')),
            '2': (lambda: fig_boxes(sc, a.out, base), os.path.join(sc, 'ladder.csv')),
            '3': (lambda: fig_twins(sc, a.out), os.path.join(sc, 'compare.csv')),
            '4': (lambda: fig_lines(os.path.join(a.out, 'lines'), a.out), os.path.join(a.out, 'lines', 'line_shapes.csv')),
            '5': (lambda: fig_shape_effect(a.out, (base, base + '_options'), [('Gaussian', os.path.join(a.out, 'shape', 'run_gaussian')),
                                                         ('Real-shaped', os.path.join(a.out, 'shape', 'run_line'))]),
                  os.path.join(a.out, 'shape', 'run_gaussian', 'scores.csv'))}
    for k, (f, need) in jobs.items():
        if want and k not in want:
            continue
        if not os.path.exists(need):
            print('figure M%s skipped: no %s' % (k, need))
            continue
        f()
        print('M%s done' % k)


if __name__ == '__main__':
    main()
