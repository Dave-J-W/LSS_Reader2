"""Burn tests over time: figures and the estimator comparison (owner,
2026-11-21).

    python tests/tools/burn_figures.py                     # NX scans 14, 15 -> docs/figures/burn_trends/, CSVs
    python tests/tools/burn_figures.py --spec PATH --scans 23 35 --out DIR

For each burn scan: one figure as the reader's Trends tab draws it
(intensity on top; position and FWHM below, on two y axes; every model
fitted, the best one thick; dotted vertical line at the confident 5 %
time) for the default estimator (template) and for the legacy moments,
and a table of the three estimators (template, moments, fit) per
quantity: best model, stable or not, ĉ (scatter / errors squared), the
median per-frame χ²/dof, and the 5 % times. CSVs: ``values_<scan>.csv``
(time and each quantity per estimator) and ``estimators.csv``.
Uses lss_core only. Run from the repository root; private data go to an
--out outside docs/ (the tool refuses docs/ for a --spec other than NX).
"""
import argparse
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())
import matplotlib                                      # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                        # noqa: E402

from lss_core import burn as burnmod, trends            # noqa: E402
from lss_core.experiment import Experiment             # noqa: E402

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
OUT = os.path.join('docs', 'figures', 'burn_trends')
CSV_OUT = os.path.join('docs', 'comparisons_data', 'burn_nx')
STYLES = {'constant': ':', 'linear': '--', 'exponential': '-.', 'double exponential': '-'}


def draw(res, path, title):
    fig = plt.figure(figsize=(7.5, 6.0))
    tt = np.linspace(0, res.duration(), 300)
    if res.kind == 'gid':
        ax1 = fig.add_subplot(2, 1, 1)
        ax2 = fig.add_subplot(2, 1, 2, sharex=ax1)
        ax3 = ax2.twinx()
        panels = [(ax1, 'intensity', 'C0', 'Intensity / Monc'), (ax2, 'centre', 'C2', r'Position $Q_{xy}$ [$\AA^{-1}$]'),
                  (ax3, 'fwhm', 'C3', r'FWHM [$\AA^{-1}$]')]
    else:
        ax1 = ax2 = fig.add_subplot(1, 1, 1)
        panels = [(ax1, 'intensity', 'C0', 'Reflected intensity / Monc')]
    for ax, q, col, lab in panels:
        y, s = res.values[q]
        ax.errorbar(res.t, y, s, fmt='o', color=col, ms=3, lw=0.8)
        ax.set_ylabel(lab, color=col)
        ax.tick_params(axis='y', colors=col)
        c = res.trends[q]
        for m, f in c.fits.items():
            if f.ok:
                ax.plot(tt, f(tt), STYLES[m], color=col, lw=2 if m == c.best else 1, alpha=1 if m == c.best else 0.45)
        if c.change is not None and np.isfinite(c.change.confident) and c.change.confident <= tt[-1]:
            ax.axvline(c.change.confident, color=col, ls=(0, (1, 3)), lw=1)
    from matplotlib.lines import Line2D
    first = res.trends['intensity']
    ax1.legend(handles=[Line2D([], [], color='k', ls=STYLES[m], lw=2 if m == first.best else 1,
                               label='%s (Δ %.1f)' % (m, f.delta)) for m, f in first.fits.items() if f.ok],
               fontsize=7, frameon=False, title='intensity: %s' % first.criterion, title_fontsize=7)
    ax2.set_xlabel('Time under the beam (s)' if res.time == 'exposure' else 'Clock time (s)')
    verdicts = ', '.join('%s %s' % (burnmod.LABELS[q].lower(), 'stable' if c.stable else 'changing')
                         for q, c in res.trends.items())
    t, q = res.safe_time()
    ax1.set_title('%s\n%s; 5 %% change in ≥ %.3g s (%s, 95 %%)' % (title, verdicts, t, burnmod.LABELS.get(q, q).lower()),
                  fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', default=NX)
    ap.add_argument('--scans', type=int, nargs='+', default=[14, 15])
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    public = os.path.abspath(a.spec) == os.path.abspath(NX)
    out = a.out or OUT
    csv_out = a.out or CSV_OUT
    if not public and os.path.abspath(out).startswith(os.path.abspath('docs')):
        sys.exit('private data: give an --out outside docs/ (e.g. under sample_data/private/figures/)')
    os.makedirs(out, exist_ok=True)
    os.makedirs(csv_out, exist_ok=True)
    exp = Experiment(a.spec)
    rows = []
    for scan in a.scans:
        per = {}
        for est in burnmod.ESTIMATORS:
            res = exp.burn(scan, estimator=est)
            per[est] = res
            for q, c in res.trends.items():
                chi = [d.get('chi2_dof', math.nan) for d in res.frame_fits]
                fit = c.fits[c.best]
                rows.append(dict(scan=scan, kind=res.kind, estimator=est, quantity=q, best=c.best,
                                 stable=c.stable, delta_constant_linear=round(c.delta_constant_linear, 2),
                                 c_hat=round(c.c_hat, 3), criterion=c.criterion,
                                 median_frame_chi2=round(float(np.nanmedian(chi)), 3) if np.any(np.isfinite(chi)) else '',
                                 residual_relative=round(float(np.std(c.y - fit(c.t)) / abs(np.mean(c.y))), 6),
                                 scatter_factor=round(c.scatter_factor, 3) if c.scatter_factor else '',
                                 change_model=c.change.model if c.change else '',
                                 change_best_s=round(c.change.best, 2) if c.change else '',
                                 change_confident_s=round(c.change.confident, 2) if c.change else ''))
        for est, suffix in (('template', ''), ('moments', '_moments')):
            draw(per[est], os.path.join(out, 'burn_scan_%d%s.png' % (scan, suffix)),
                 '%s scan %d (%s estimator, errors from the scatter, exposure time)'
                 % (os.path.basename(a.spec), scan, est))
        cols = ['time_s']
        arr = [per['moments'].t]
        for est, res in per.items():
            for q, (y, s) in res.values.items():
                cols += ['%s_%s' % (est, q), '%s_%s_err' % (est, q)]
                arr += [y, s]
        np.savetxt(os.path.join(csv_out, 'values_%d.csv' % scan), np.column_stack(arr), delimiter=',',
                   header=','.join(cols), comments='')
    with open(os.path.join(csv_out, 'estimators.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print('%(scan)d %(estimator)-8s %(quantity)-9s best %(best)-18s stable %(stable)-5s residual %(residual_relative)8.5f '
              'frame χ² %(median_frame_chi2)s  5%%: ≥ %(change_confident_s)s s' % r)


if __name__ == '__main__':
    main()
