"""Walkthrough figures for the excess-scatter study (DATA_NEEDS row 15; AGENTS.md rule 13).

Every step on public data: the NX school file's reflectivity series (scans 6-9), whose joins 7-8 and 8-9
share three Qz each, then synthetic known truth for the statistics, then the real results from the
committed derived tables (``real_*.csv`` beside the study; made privately by the non-cloud agent).

    python tests/tools/excess_scatter_walkthrough.py [--out docs/studies/excess_scatter/walkthrough]

W1 the two scans of a join as they come in; W2 the ratio at the shared Qz, its mean and residuals;
W3 the 6-point difference within a scan; W4 the likelihood and the core + outlier model on known truth;
W5 the real results by what they might follow.
"""
import argparse
import csv
import math
import os
import sys
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (ROOT, HERE, os.path.join(ROOT, 'tests')) if p not in sys.path]

import excess_scatter as E          # noqa: E402

NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
NX_SCANS = [6, 7, 8, 9]
STUDY = os.path.join(ROOT, 'docs', 'studies', 'excess_scatter')
INK = '0.15'
MIN_RUNS = 3        # a bin drawn in W5 needs terms from at least 3 runs (files); fewer is one experiment's quirk
C_A, C_B, C_X = '#1f77b4', '#ff7f0e', '#2ca02c'


def _style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.3, 'text.color': INK,
                         'axes.labelcolor': INK})
    return plt


def nx_reduced():
    from lss_core.experiment import Experiment
    warnings.simplefilter('ignore')
    exp = Experiment(NX)
    r = exp.reflectivity(NX_SCANS, errors='budget')
    return {n: r.per_scan[n] for n in r.order}, list(r.order)


def foot(fig, text, width=210):
    import textwrap
    fig.text(0.01, 0.01, textwrap.fill(text, width), fontsize=7.5, color='0.4', ha='left', va='bottom')


def w1(ps, out, plt):
    a, b = ps[7], ps[8]
    t = E.pair_terms(a[:, 0], a[:, 1], a[:, 2], b[:, 0], b[:, 1], b[:, 2])
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, zoom in zip(axs, (False, True)):
        for row, c, lab in ((a, C_A, 'scan 7 (absorber as recorded)'), (b, C_B, 'scan 8')):
            ax.errorbar(row[:, 0], row[:, 1], yerr=row[:, 2], fmt='o', ms=3.5, color=c, capsize=2, label=lab)
        ax.plot(a[t['ia'], 0], a[t['ia'], 1], 'o', ms=11, mfc='none', mec=INK, label='the three shared Qz')
        ax.plot(b[t['ib'], 0], b[t['ib'], 1], 'o', ms=11, mfc='none', mec=INK)
        ax.set_yscale('log')
        ax.set_xlabel('Qz (Å⁻¹)')
        if zoom:
            q0, q1 = t['q'].min() - 0.01, t['q'].max() + 0.01
            ax.set_xlim(q0, q1)
            m = np.concatenate([a[(a[:, 0] >= q0) & (a[:, 0] <= q1), 1], b[(b[:, 0] >= q0) & (b[:, 0] <= q1), 1]])
            ax.set_ylim(m.min() / 2, m.max() * 2)
            ax.set_title('Zoom on the join: the same Qz measured twice', fontsize=9)
        else:
            ax.set_ylabel('net counts per monitor count (box minus background)')
            ax.set_title('Two neighbouring scans of the NX school series, as reduced', fontsize=9)
            ax.legend(frameon=False, fontsize=8)
    fig.suptitle('W1. The raw material: points of two scans at the same Qz', x=0.01, ha='left',
                 fontweight='bold', fontsize=11)
    foot(fig, 'Each point: one Pilatus frame, the signal box minus the two background boxes, divided by the '
         'monitor (lss_core.reflectivity, errors="budget": √counts and the monitor term). The two scans sit '
         'at different heights because the absorber changed between them; that factor is what a join '
         'measures. Public NX school file, scans 7 and 8.')
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    fig.savefig(os.path.join(out, 'W1_two_scans.png'), dpi=200)
    plt.close(fig)


def w2(ps, out, plt):
    fig, axs = plt.subplots(2, 2, figsize=(12, 6.4), gridspec_kw=dict(height_ratios=(2.2, 1)), sharex='col')
    lines = []
    for col, (i, j) in enumerate(((7, 8), (8, 9))):
        a, b = ps[i], ps[j]
        t = E.pair_terms(a[:, 0], a[:, 1], a[:, 2], b[:, 0], b[:, 1], b[:, 2])
        w = 1 / t['v']
        c = np.sum(w * t['r']) / np.sum(w)
        chi2 = float(np.sum(w * (t['r'] - c) ** 2))
        ax = axs[0, col]
        ax.errorbar(t['q'], t['r'], yerr=np.sqrt(t['v']), fmt='o', color=C_X, capsize=3,
                    label='ln(y_a / y_b) at each shared Qz, ±1σ from counting')
        ax.axhline(c, color=INK, ls='--', lw=1, label='weighted mean c = %.4f (factor %.4f)' % (c, math.exp(c)))
        ax.set_ylabel('ln(scan %d) − ln(scan %d)' % (i, j))
        ax.set_title('Join %d–%d: χ² = %.2f on %d degrees of freedom' % (i, j, chi2, len(t['r']) - 1), fontsize=9)
        ax.legend(frameon=False, fontsize=8, loc='upper left')
        lo, hi = (t['r'] - np.sqrt(t['v'])).min(), (t['r'] + np.sqrt(t['v'])).max()
        ax.set_ylim(lo - 0.6 * (hi - lo), hi + 0.9 * (hi - lo))
        z = (t['r'] - c) * np.sqrt(w) / np.sqrt(1 - w / np.sum(w))
        axs[1, col].axhline(0, color=INK, lw=0.8)
        axs[1, col].bar(t['q'], z, width=0.002 if col == 0 else 0.004, color=C_X)
        axs[1, col].set_ylabel('residual / σ')
        axs[1, col].set_xlabel('Qz (Å⁻¹)')
        axs[1, col].set_ylim(-3, 3)
        lines.append((i, j, chi2, len(t['r']) - 1))
    fig.suptitle('W2. The shared-Qz estimator: the ratio should be the same at every shared Qz', x=0.01,
                 ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'If the stated errors were the whole story, the residuals/σ would scatter like N(0,1) and χ² would be '
         'about its degrees of freedom. An excess X adds 2X² to each ratio\'s variance (one X² per point). Two '
         'joins of 3 points are far too few to measure X (2 + 2 degrees of freedom); the study pools every '
         'real join with shared Qz. Residuals scaled by √(1 − h), h each point\'s weight share (the mean uses it).')
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(os.path.join(out, 'W2_shared_ratio.png'), dpi=200)
    plt.close(fig)
    return lines


def w3(ps, out, plt):
    a = ps[9]
    o = np.argsort(a[:, 0])
    q, y, s = a[o, 0], a[o, 1], a[o, 2]
    ok = E._ok(y, s) & (q >= E.Q_MIN)
    q, y, s = q[ok], y[ok], s[ok]
    ly = np.log(y / E._fresnel(q))
    sl = s / y
    t = E.curvature_terms(q, y, s)
    k = len(t['d']) // 2
    win = slice(k, k + E.DIFF_ORDER + 1)
    qq = q[win]
    x = (qq - qq.mean()) / np.ptp(qq)
    coef = np.polyfit(x, ly[win], E.DIFF_ORDER - 1, w=1 / sl[win])
    xf = np.linspace(x.min(), x.max(), 100)
    fig, axs = plt.subplots(2, 2, figsize=(12, 6.4), gridspec_kw=dict(height_ratios=(2.2, 1)))
    ax = axs[0, 0]
    ax.errorbar(q, ly, yerr=sl, fmt='o', ms=3.5, color=C_A, capsize=2, label='scan 9: ln(R / R_F), ±1σ')
    ax.axvspan(qq.min(), qq.max(), color=C_X, alpha=0.15, label='one 6-point window')
    ax.set_ylabel('ln(R / R_F)  (R_F: water, Qc 0.0217 Å⁻¹)')
    ax.set_title('Divide out the Fresnel curve, so what is left is smooth', fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    ax = axs[0, 1]
    ax.errorbar(qq, ly[win], yerr=sl[win], fmt='o', color=C_A, capsize=3, label='the 6 points')
    ax.plot(qq.mean() + xf * np.ptp(qq), np.polyval(coef, xf), color=C_X, label='best quartic through them')
    ax.set_title('Inside the window: any smooth curve (up to Qz⁴) is removed', fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    ax = axs[1, 1]
    res = (ly[win] - np.polyval(coef, x)) / sl[win]
    ax.bar(qq, res, width=np.ptp(qq) / 12, color=C_X)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_ylabel('residual / σ')
    ax.set_xlabel('Qz (Å⁻¹)')
    ax = axs[1, 0]
    z = t['d'] / np.sqrt(t['a'])
    ax.bar(t['q'], z, width=0.004, color=C_A)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_ylabel('d / σ_d per window')
    ax.set_xlabel('Qz (Å⁻¹, window centre)')
    ax.set_title('Every window of scan 9: χ²/n = %.2f over %d windows' % (float(np.mean(z ** 2)), len(z)),
                 fontsize=9)
    fig.suptitle('W3. The within-scan estimator: what a smooth curve cannot explain, six points at a time',
                 x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'The 6-point difference d = Σ w_k ln(y_k/R_F,k) uses the weights that cancel every polynomial up '
         'to Qz⁴ (|w| = 1): it is the leftover of that quartic fit, one number per window. Its variance is '
         'Σ w_k² σ_k² from counting, plus X² with an excess. Fringes too fast for a quartic leave some in '
         '(known truth: about 1.2 % on a 100 Å film). Windows overlap, so neighbouring d share points.')
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(os.path.join(out, 'W3_within_scan.png'), dpi=200)
    plt.close(fig)
    return float(np.mean(z ** 2)), len(z)


def w4(out, plt):
    rng = np.random.default_rng(4)
    prof = E._curves()['water']
    clean, dirty = [], []
    for _ in range(60):
        clean += E.series_terms(E.synth_series(prof, 0.01, 0.0, rng))[0]
        dirty += E.series_terms(E.synth_series(prof, 0.01, 0.0, rng, outliers=E.OUTLIER_SHARE))[0]
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    ax = axs[0]
    ll = np.array([E._pairs_loglik(clean, x * x) for x in E.GRID])
    e = E.estimate('pairs', clean)
    ax.plot(E.GRID * 100, ll - ll.max(), color=C_A)
    ax.axhline(-0.5, color=INK, ls='--', lw=1)
    ax.axvspan(e['x_lo'] * 100, e['x_hi'] * 100, color=C_A, alpha=0.15)
    ax.axvline(1.0, color=C_X, lw=1.5, label='truth 1 %')
    ax.set_xlim(0, 2.5)
    ax.set_ylim(-8, 0.5)
    ax.set_xlabel('excess X (% of R)')
    ax.set_ylabel('ln L − max (REML)')
    ax.set_title('Likelihood: best X %.2f %%, 68 %% interval %.2f–%.2f %%' % (e['x_ml'] * 100, e['x_lo'] * 100,
                                                                       e['x_hi'] * 100), fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    for ax, terms, title in ((axs[1], clean, 'No outliers'), (axs[2], dirty, '3 % of points off ~40 %')):
        g = E.estimate('pairs', terms)
        m = E.estimate_mixture('pairs', terms, profile=False)
        d, a = E._pair_resid(terms, m['x'], m['pi'], m['tau'])
        z = d / np.sqrt(a + 2 * m['x'] ** 2)
        bins = np.linspace(-12, 12, 97)
        ax.hist(np.clip(z, -12, 12), bins=bins, density=True, color='0.75', label='pair residuals / core σ (clipped at ±12)')
        zz = np.linspace(-12, 12, 600)
        ax.plot(zz, np.exp(-zz ** 2 / 2) / math.sqrt(2 * math.pi), color=C_A, label='N(0, 1)')
        # the fitted mixture, at the median counting variance
        v0 = np.median(a)
        vc, vo = v0 + 2 * m['x'] ** 2, v0 + 2 * m['x'] ** 2 + m['tau'] ** 2
        mixd = ((1 - m['pi']) * np.exp(-zz ** 2 / 2) / math.sqrt(2 * math.pi)
                + m['pi'] * np.exp(-zz ** 2 * vc / vo / 2) * math.sqrt(vc / vo) / math.sqrt(2 * math.pi))
        ax.plot(zz, mixd, color=C_X, lw=1.2, label='fitted core + outliers')
        ax.set_yscale('log')
        ax.set_ylim(1e-5, 2)
        ax.set_xlabel('residual / core σ')
        ax.set_title('%s\none Gaussian: X %.1f %%; core + outliers: X %.2f %%' % (title, g['x_ml'] * 100,
                                                                              m['x'] * 100), fontsize=9)
        ax.legend(frameon=False, fontsize=7.5, loc='upper right')
    fig.suptitle('W4. Why the core + outlier model: a few wild points make one Gaussian report a large excess '
                 '(truth: X = 1 %)', x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'Synthetic water, 60 series of 5 scans + a repeat, 3 shared Qz per join (tests/tools/excess_scatter.py). '
         'Left: ln L of the one-Gaussian model; the dashed line is 0.5 below the best, where the 68 % interval '
         'ends. Middle and right: residuals, log y so the tails show. The outlier model has two more numbers: '
         'the share of outlier pairs π (about twice the share of outlier points: either point can be the bad '
         'one) and their size τ.')
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(os.path.join(out, 'W4_likelihood_and_outliers.png'), dpi=200)
    plt.close(fig)


def _read(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def w5(out, plt, study=STUDY):
    by = _read(os.path.join(study, 'real_by.csv'))
    ov = {(r['estimator'], r['bin']): r for r in _read(os.path.join(study, 'real_overall.csv'))}
    groups = []
    for r in by:
        if r['by'] not in groups:
            groups.append(r['by'])
    fig, axs = plt.subplots(2, len(groups), figsize=(2.6 * len(groups) + 1, 6.6), squeeze=False)
    for col, g in enumerate(groups):
        for row, (key, lo, hi, lab) in enumerate((('core_x', 'core_x_lo', 'core_x_hi', 'core excess X (% of R)'),
                                                  ('outlier_share', 'outlier_share_lo', 'outlier_share_hi',
                                                   'outlier share (%)'))):
            ax = axs[row, col]
            for k, (est, c) in enumerate((('pairs', C_X), ('within', C_A))):
                rs = [r for r in by if r['by'] == g and r['estimator'] == est and r[key] not in ('', 'nan')
                      and int(r['n_runs']) >= MIN_RUNS]
                if not rs:
                    continue
                bins = []
                for r in by:
                    if r['by'] == g and r['bin'] not in bins:
                        bins.append(r['bin'])
                xs = np.array([bins.index(r['bin']) for r in rs]) + (k - 0.5) * 0.25
                v = np.array([float(r[key]) for r in rs]) * 100
                l = np.array([float(r[lo]) if r[lo] not in ('', 'nan') else np.nan for r in rs]) * 100
                h = np.array([float(r[hi]) if r[hi] not in ('', 'nan') else np.nan for r in rs]) * 100
                ax.errorbar(xs, v, yerr=[np.nan_to_num(v - l), np.nan_to_num(h - v)], fmt='o', color=c, capsize=2,
                            label='between scans (shared Qz)' if est == 'pairs' else 'within a scan')
                ax.set_xticks(np.arange(len(bins)))
                ax.set_xticklabels(bins, rotation=35, fontsize=7)
            if row == 0:
                ax.set_title(g, fontsize=8.5)
            if col == 0:
                ax.set_ylabel(lab)
            ax.set_ylim(bottom=0)
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc='upper right', ncol=2, frameon=False, bbox_to_anchor=(0.995, 0.995))
    pa, wi = ov[('pairs', 'all')], ov[('within', 'all')]
    fig.suptitle('W5. Real data: between scans the core excess is %.2f %% of R, within a scan %.2f %%; a few %% '
                 'of points are outliers' % (float(pa['core_x']) * 100, float(wi['core_x']) * 100),
                 x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'From the committed real_by.csv (derived numbers; the non-cloud agent\'s private run of '
         'scatter_analyse.py over %s runs). Bars: 16th–84th percentiles of a bootstrap over runs (files). '
         'Outlier share: of pair residuals for "between scans" (about twice the share of points), of '
         '6-point windows for "within" (one bad point touches six windows). Bins with terms from fewer than %d '
         'runs are left out (they are in real_by.csv). The covariates go together: high Qz means low counts, a '
         'large background share and points minutes apart.' % (pa['n_runs'], MIN_RUNS))
    fig.tight_layout(rect=(0, 0.06, 1, 0.92))
    fig.savefig(os.path.join(out, 'W5_real_by.png'), dpi=200)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=os.path.join(STUDY, 'walkthrough'))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    plt = _style()
    ps, _ = nx_reduced()
    lines = w1(ps, a.out, plt) or []
    lines = w2(ps, a.out, plt)
    c3 = w3(ps, a.out, plt)
    w4(a.out, plt)
    if os.path.exists(os.path.join(STUDY, 'real_by.csv')):
        w5(a.out, plt)
    for i, j, chi2, dof in lines:
        print('NX join %d-%d: chi2 %.2f on %d dof' % (i, j, chi2, dof))
    print('NX scan 9 windows: chi2/n %.2f over %d' % c3)
    return 0


if __name__ == '__main__':
    sys.exit(main())
