"""Walkthrough figures for the excess-scatter study (DATA_NEEDS row 15; AGENTS.md rule 13).

Every step on public data: one scan of the NX school file's reflectivity series (scan 9), then synthetic
known truth for the statistics, then the real results from the committed derived tables (``real_*.csv``
beside the study; made privately by the non-cloud agent). Only the within-scan estimator is shown: the
between-scan (shared-Qz) numbers were set aside by the owner on 2026-11-25, because what changed between
two scans (sample height, footprint, background at another absorber, time) is not recorded in the data.

    python tests/tools/excess_scatter_walkthrough.py [--out docs/studies/excess_scatter/walkthrough]

W1 one scan as it comes in; W2 the 6-point difference within a scan; W3 the likelihood and the core +
outlier model on known truth; W4 the real results by what they might follow.
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
NX_SCAN = 9
STUDY = os.path.join(ROOT, 'docs', 'studies', 'excess_scatter')
INK = '0.15'
MIN_RUNS = 3        # a bin drawn in W4 needs terms from at least 3 runs (files); fewer is one experiment's quirk
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
    a = ps[NX_SCAN]
    o = np.argsort(a[:, 0])
    q, y, s = a[o, 0], a[o, 1], a[o, 2]
    keep = E._ok(y, s) & (q >= E.Q_MIN)
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    ax = axs[0]
    ax.errorbar(q[keep], y[keep], yerr=s[keep], fmt='o', ms=3.5, color=C_A, capsize=2, label='points used')
    if np.any(~keep):
        ax.errorbar(q[~keep], np.where(y[~keep] > 0, y[~keep], np.nan), yerr=s[~keep], fmt='o', ms=3.5, color='0.6',
                    capsize=2, label='left out (Qz < %.2f or y/σ < %d)' % (E.Q_MIN, E.SNR_MIN))
    ax.set_yscale('log')
    ax.set_xlabel('Qz (Å⁻¹)')
    ax.set_ylabel('net counts per monitor count (box minus background)')
    ax.set_title('Scan %d of the NX school series, as reduced' % NX_SCAN, fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    ax = axs[1]
    ax.plot(q[keep], s[keep] / y[keep] * 100, 'o', ms=3.5, color=C_A)
    ax.set_yscale('log')
    ax.set_xlabel('Qz (Å⁻¹)')
    ax.set_ylabel('stated error σ / y (%)')
    from matplotlib.ticker import FormatStrFormatter
    ax.yaxis.set_major_formatter(FormatStrFormatter('%g'))
    ax.yaxis.set_minor_formatter(FormatStrFormatter('%g'))
    ax.set_title('The stated error, relative: it grows as the counts fall', fontsize=9)
    fig.suptitle('W1. The raw material: one scan, each point with its counting error', x=0.01, ha='left',
                 fontweight='bold', fontsize=11)
    foot(fig, 'Each point: one Pilatus frame, the signal box minus the two background boxes, divided by the '
         'monitor (lss_core.reflectivity, errors="budget": √counts and the monitor term). The question: do '
         'neighbouring points scatter about a smooth curve by more than these error bars? Public NX school '
         'file, scan %d.' % NX_SCAN)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    fig.savefig(os.path.join(out, 'W1_one_scan.png'), dpi=200)
    plt.close(fig)


def w2(ps, out, plt):
    a = ps[NX_SCAN]
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
    ax.errorbar(q, ly, yerr=sl, fmt='o', ms=3.5, color=C_A, capsize=2, label='scan %d: ln(R / R_F), ±1σ' % NX_SCAN)
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
    ax.set_title('Every window of scan %d: χ²/n = %.2f over %d windows' % (NX_SCAN, float(np.mean(z ** 2)), len(z)),
                 fontsize=9)
    fig.suptitle('W2. The within-scan estimator: what a smooth curve cannot explain, six points at a time',
                 x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'The 6-point difference d = Σ w_k ln(y_k/R_F,k) uses the weights that cancel every polynomial up '
         'to Qz⁴ (|w| = 1): it is the leftover of that quartic fit, one number per window. Its variance is '
         'Σ w_k² σ_k² from counting, plus X² with an excess. Fringes too fast for a quartic leave some in '
         '(known truth: about 1.2 % on a 100 Å film). Windows overlap, so neighbouring d share points.')
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(os.path.join(out, 'W2_within_scan.png'), dpi=200)
    plt.close(fig)
    return float(np.mean(z ** 2)), len(z)


def _within(terms):
    d = np.concatenate([t['d'] for t in terms if t is not None])
    a = np.concatenate([t['a'] for t in terms if t is not None])
    return d, a


def w3(out, plt):
    rng = np.random.default_rng(4)
    prof = E._curves()['water']
    sets = {}
    for lab, share in (('clean', 0.0), ('real', E.REAL_OUTLIER_SHARE), ('stress', E.OUTLIER_SHARE)):
        terms = []
        for _ in range(60):
            terms += E.series_terms(E.synth_series(prof, 0.01, 0.0, rng, outliers=share))[1]
        sets[lab] = terms
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    ax = axs[0]
    t = {k: np.concatenate([x[k] for x in sets['clean'] if x is not None]) for k in ('d', 'a', 'b')}
    ll = np.array([E._curv_loglik(t, x * x) for x in E.GRID])
    e = E.estimate('curvature', sets['clean'])
    ax.plot(E.GRID * 100, ll - ll.max(), color=C_A)
    ax.axhline(-0.5, color=INK, ls='--', lw=1)
    ax.axvspan(e['x_lo'] * 100, e['x_hi'] * 100, color=C_A, alpha=0.15)
    ax.axvline(1.0, color=C_X, lw=1.5, label='truth 1 %')
    ax.set_xlim(0, 2.5)
    ax.set_ylim(-8, 0.5)
    ax.set_xlabel('excess X (% of R)')
    ax.set_ylabel('ln L − max')
    ax.set_title('No outliers. Likelihood: best X %.2f %%, 68 %% interval %.2f–%.2f %%'
                 % (e['x_ml'] * 100, e['x_lo'] * 100, e['x_hi'] * 100), fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    for ax, key, title in ((axs[1], 'real', '0.3 % of points off ~40 % (about the real share)'),
                           (axs[2], 'stress', '3 % of points off ~40 % (10× the real share)')):
        terms = sets[key]
        g = E.estimate('curvature', terms)
        m = E.estimate_mixture('curvature', terms, profile=False)
        d, a = _within(terms)
        z = d / np.sqrt(a + m['x'] ** 2)
        bins = np.linspace(-12, 12, 97)
        ax.hist(np.clip(z, -12, 12), bins=bins, density=True, color='0.75',
                label='window d / core σ (clipped at ±12)')
        zz = np.linspace(-12, 12, 600)
        ax.plot(zz, np.exp(-zz ** 2 / 2) / math.sqrt(2 * math.pi), color=C_A, label='N(0, 1)')
        v0 = np.median(a)
        vc, vo = v0 + m['x'] ** 2, v0 + m['x'] ** 2 + m['tau'] ** 2
        mixd = ((1 - m['pi']) * np.exp(-zz ** 2 / 2) / math.sqrt(2 * math.pi)
                + m['pi'] * np.exp(-zz ** 2 * vc / vo / 2) * math.sqrt(vc / vo) / math.sqrt(2 * math.pi))
        ax.plot(zz, mixd, color=C_X, lw=1.2, label='fitted core + outliers')
        ax.set_yscale('log')
        ax.set_ylim(1e-5, 2)
        ax.set_xlabel('window difference / core σ')
        ax.set_title('%s\none Gaussian: X %.1f %%; core + outliers: X %.2f %%, π %.1f %% of windows'
                     % (title, g['x_ml'] * 100, m['x'] * 100, m['pi'] * 100), fontsize=9)
        ax.legend(frameon=False, fontsize=7.5, loc='upper right')
    fig.suptitle('W3. Why the core + outlier model: a few wild points make one Gaussian report a large excess '
                 '(truth: X = 1 %)', x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'Synthetic water, 60 series of 5 scans each (tests/tools/excess_scatter.py), 6-point windows within '
         'each scan. Left: ln L of the one-Gaussian model; the dashed line is 0.5 below the best, where the 68 % '
         'interval ends. Middle and right: the window differences, log y so the tails show. The outlier model '
         'has two more numbers: the share of outlier windows π (one bad point spoils up to six windows, so π is '
         'up to six times the share of bad points) and their size τ.')
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(os.path.join(out, 'W3_likelihood_and_outliers.png'), dpi=200)
    plt.close(fig)


def _read(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def w4(out, plt, study=STUDY):
    by = [r for r in _read(os.path.join(study, 'real_by.csv')) if r['estimator'] == 'within']
    ov = {r['bin']: r for r in _read(os.path.join(study, 'real_overall.csv')) if r['estimator'] == 'within'}
    groups = []
    for r in by:
        if r['by'] not in groups:
            groups.append(r['by'])
    fig, axs = plt.subplots(2, len(groups), figsize=(2.9 * len(groups) + 1, 6.6), squeeze=False)
    for col, g in enumerate(groups):
        bins = []
        for r in by:
            if r['by'] == g and r['bin'] not in bins:
                bins.append(r['bin'])
        for row, (key, lo, hi, lab, scale) in enumerate((
                ('core_x', 'core_x_lo', 'core_x_hi', 'core excess X (% of R)', 100),
                ('outlier_share', 'outlier_share_lo', 'outlier_share_hi', 'outlier windows (%)', 100))):
            ax = axs[row, col]
            rs = [r for r in by if r['by'] == g and r[key] not in ('', 'nan') and int(r['n_runs']) >= MIN_RUNS]
            if rs:
                xs = np.array([bins.index(r['bin']) for r in rs])
                v = np.array([float(r[key]) for r in rs]) * scale
                l = np.array([float(r[lo]) if r[lo] not in ('', 'nan') else np.nan for r in rs]) * scale
                h = np.array([float(r[hi]) if r[hi] not in ('', 'nan') else np.nan for r in rs]) * scale
                ax.errorbar(xs, v, yerr=[np.nan_to_num(v - l), np.nan_to_num(h - v)], fmt='o', color=C_A, capsize=2)
            ax.set_xticks(np.arange(len(bins)))
            ax.set_xticklabels(bins, rotation=35, fontsize=7)
            if row == 0:
                ax.set_title(g, fontsize=8.5)
            if col == 0:
                ax.set_ylabel(lab)
            ax.set_ylim(bottom=0)
    wi = ov['all']
    cb = [float(r['core_x']) for r in by if r['by'] == 'counts per point']
    trend = ('ten times larger at the fewest counts than at the most' if cb[0] > 5 * cb[-1]
             else 'larger at the fewest counts' if cb[0] > cb[-1] else 'not larger at the fewest counts')
    fig.suptitle('W4. Real data, within a scan: a core excess of %.2f %% of R, %s; %.1f %% of windows are outliers'
                 % (float(wi['core_x']) * 100, trend, float(wi['outlier_share']) * 100),
                 x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'From the committed real_by.csv (derived numbers; the non-cloud agent\'s private run of '
         'scatter_analyse.py over %s runs). Bars: 16th–84th percentiles of a bootstrap over runs (files). '
         'Outlier share: of 6-point windows (one bad point touches six windows). Bins with terms from fewer than %d '
         'runs are left out (they are in real_by.csv). High Qz goes with low counts and a large background share. '
         'Between-scan numbers are not shown: set aside (owner, 2026-11-25).' % (wi['n_runs'], MIN_RUNS))
    fig.tight_layout(rect=(0, 0.06, 1, 0.93))
    fig.savefig(os.path.join(out, 'W4_real_by.png'), dpi=200)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=os.path.join(STUDY, 'walkthrough'))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    plt = _style()
    ps, _ = nx_reduced()
    w1(ps, a.out, plt)
    c2 = w2(ps, a.out, plt)
    w3(a.out, plt)
    if os.path.exists(os.path.join(STUDY, 'real_by.csv')):
        w4(a.out, plt)
    print('NX scan %d windows: chi2/n %.2f over %d' % ((NX_SCAN,) + c2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
