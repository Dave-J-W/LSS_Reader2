"""Walkthroughs of the XRF studies (AGENTS rule 13): from a raw spectrum to
the verdict, on public data, with every statistic shown on one example.

    python tests/tools/xrf_walkthrough.py [--part shootout,models]

* ``shootout`` -> ``docs/studies/xrf_shootout/walkthrough/`` (W1-W5 and
  ``numbers.json``), for ``docs/studies/xrf_shootout/walkthrough.md``: one
  committed blank (E9.2-a, the 7-element detector, 9.2 keV beam), a Ni K
  line of known photons injected, the reader's three fits (Poisson fit; with
  the escapes removed; with the width fixed too) drawn over one spectrum
  with its residuals, 500 spectra turned into a bias, its error, a pull and
  a verdict. The draws are the C66 run's own (same seeds), so the bias here
  must equal the committed ``run_blanks/scores.csv``; it is checked.
* ``models`` -> ``docs/studies/xrf_models/walkthrough/`` (W1-W5 and
  ``numbers.json``), for ``docs/studies/xrf_models/walkthrough.md``: three
  scatter models fitted to one blank (E6.1-a) with residuals, what the miss
  under a line and the misfit at use mean, a real blank against its model
  twin and a second draw, the floor, and a synthetic line with the
  7-element detector's
  measured skew fitted by a Gaussian and by one tail (the real lines'
  spectra are private; their numbers are in ``lines/line_shapes.csv``).

Public data only (``tests/reference/mca_scatter/`` and the committed study
outputs); about a minute. Run from the repository root, in the shootout's
environment.
"""
import os

for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')

import argparse
import csv
import json
import math
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

import xrf_blanks as xb                                       # noqa: E402
import xrf_shootout as xs                                     # noqa: E402
import xrf_shootout_figures as F                              # noqa: E402
import xrf_lineshape as L                                     # noqa: E402
from synthetic import mca, mca_more as mm                     # noqa: E402
from lss_core import fluorescence as fluo, peaks              # noqa: E402
import matplotlib.pyplot as plt                               # noqa: E402

SHOOT = os.path.join('docs', 'studies', 'xrf_shootout')
MODELS = os.path.join('docs', 'studies', 'xrf_models')
EX = dict(blank='E9.2-a', target='Ni K', background=1000, ratio=1.0)       # the shootout's example
MEX = dict(blank='E6.1-a', target='Ti K')                                  # the models study's example
BLUE, ORANGE, GREEN, RED, VIOLET = '#2a78d6', '#eb6834', '#1baf7a', '#e34948', '#6250d6'
MODEL_COLOR = {'generator': F.MUTED, 'gaussian': RED, 'full': BLUE}
MODEL_SHORT = {'generator': 'generator defaults', 'gaussian': 'Gaussian detector', 'full': 'full model'}


def read(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def r3(v, k=4):
    return float('%.*g' % (k, v)) if np.isfinite(v) else None


# ---- the shootout ---------------------------------------------------------------------------------

def _example():
    conds = xb.design()
    name = '%s|%s|%d|%g' % (EX['blank'], EX['target'], EX['background'], EX['ratio'])
    ci = list(conds).index(name)
    return name, ci, conds[name]


def _reader_fit(method, cond, spec, counts):
    """The reader's box fit as ``xs.reader`` makes it, keeping the fit for drawing."""
    cal = spec.calib
    data = [xs._normalise(c, cal) for c in counts]
    if method in ('p1p2p3', 'p1p3'):
        data = [fluo.strip_escape(d, cond.detector.escape) for d in data]
    kw = {}
    if method in ('p1p2p3', 'p1p2'):
        kw['fwhm'] = fluo.detector_fwhm(cond.line, cond.detector.noise)
    lo, hi = cond.box_range()
    x = data[0][:, 0]
    o = peaks.FitOptions(shape='gaussian', background='quadratic', n_peaks=1, centres=(cond.line,),
                         x_range=(lo, hi), window=50.0, **kw)
    ref, each = peaks.fit_series(x, [d[:, 1] for d in data], [d[:, 2] for d in data], o, weights='poisson')
    return x, data, ref, each


def shootout(out):
    os.makedirs(out, exist_ok=True)
    N = {}
    name, ci, bc = _example()
    b = bc.blank
    e, full = b['energy'], b['counts']
    spec = bc.spectra()
    truth = mm.family_photons(spec, bc.cond.target)
    lo, hi = bc.cond.box_range()
    box = (e >= lo) & (e <= hi)
    E0 = b['beam']
    esc = E0 - mca.SI_KA_KEV
    N['example'] = dict(condition=name, blank=b['id'], readout=b['readout'], beam_keV=E0, target=bc.cond.target,
                        line_keV=r3(bc.cond.line), fwhm_keV=r3(bc.cond.fwhm), box_keV=[r3(lo), r3(hi)],
                        blank_counts_total=int(full.sum()), blank_counts_in_box=int(full[box].sum()),
                        thinning_p=r3(bc.p), background_in_box=EX['background'], photons_injected=r3(bc.photons),
                        truth_family_photons=r3(truth), escape_of_beam_keV=r3(esc))

    # W1: the blank as it comes in
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw=dict(width_ratios=(1.5, 1)))
    a1.step(e, full, where='mid', color=F.INK, lw=0.7)
    a1.set_yscale('log')
    a1.axvspan(lo, hi, color=F.GRID, alpha=0.9, lw=0)
    ip = int(np.argmax(full))
    a1.annotate('elastic (at the beam energy) and Compton\n(scattered, a little lower): one peak\nat this resolution',
                (e[ip], full[ip]), (e[ip] - 2.2, full[ip] * 0.35), fontsize=8, color=F.INK2,
                arrowprops=dict(arrowstyle='-', color=F.INK2, lw=0.6))
    ie = int(np.argmin(abs(e - esc)))
    a1.annotate('the Si escape of that peak\n(1.74 keV lower)', (e[ie], full[ie]), (e[ie] - 0.6, full[ie] * 12), fontsize=8,
                color=F.INK2, arrowprops=dict(arrowstyle='-', color=F.INK2, lw=0.6))
    a1.text(0.5 * (lo + hi), full[box].min() * 0.6, 'the Ni K line window', ha='center', fontsize=8, color=F.INK2)
    a1.set_xlabel('energy (keV)')
    a1.set_ylabel('counts per channel')
    a1.set_title('(a) The %s as it comes in: %.3g counts, no line in it' % (F.blank_name(b['id']), full.sum()), loc='left', fontsize=9)
    z = (e > lo - 0.25) & (e < hi + 0.25)
    a2.errorbar(e[z], full[z], yerr=np.sqrt(full[z]), fmt='.', ms=2, color=F.INK, ecolor=F.MUTED, elinewidth=0.6)
    a2.axvspan(lo, hi, color=F.GRID, alpha=0.9, lw=0)
    a2.axvline(esc, color=VIOLET, lw=0.8, ls='--')
    a2.text(esc, a2.get_ylim()[1], ' escape of the beam', color=VIOLET, fontsize=7, va='top')
    a2.set_xlabel('energy (keV)')
    a2.set_title('(b) Around the Ni K line window, linear scale, error bars √counts', loc='left', fontsize=9)
    fig.suptitle('W1. The raw data: a real scatter-only spectrum (one element of the 7-element detector, '
                 'beam %.1f keV)' % E0, x=0.01, ha='left', fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W1_raw_blank.png'), dpi=150)
    plt.close(fig)

    # W2: one test spectrum, made from the blank
    rng = np.random.default_rng([20261125, 13, ci, 0])                     # the C66 run's replicate 0
    counts = [bc.draw(spec, rng) for _ in range(bc.cond.series)]
    w = (e > lo - 0.6) & (e < hi + 0.6)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    a1.plot(e[w], bc.p * full[w], color=F.MUTED, lw=1.2, label='the blank × p = %.4f, the share of its counts kept (its mean once thinned)' % bc.p)
    a1.plot(e[w], spec.expected[w], color=BLUE, lw=1.2, label='the Ni K line: %d photons, the detector measured on this blank'
            % bc.photons)
    a1.plot(e[w], bc.p * full[w] + spec.expected[w], color=F.INK, lw=1.0, label='their sum: what one spectrum should hold')
    a1.axvspan(lo, hi, color=F.GRID, alpha=0.9, lw=0)
    a1.legend(fontsize=7, loc='upper left')
    a1.set_xlabel('energy (keV)')
    a1.set_ylabel('counts per channel')
    a1.set_title('(a) The recipe: thin the real blank to %d counts in the line window, add a line of known photons'
                 % EX['background'], loc='left', fontsize=9)
    c0 = counts[0]
    a2.errorbar(e[w], c0[w], yerr=np.sqrt(np.maximum(c0[w], 1)), fmt='.', ms=3, color=F.INK, ecolor=F.MUTED, elinewidth=0.6,
                label='one spectrum: a binomial thinning of the blank + Poisson line counts')
    a2.plot(e[w], bc.p * full[w] + spec.expected[w], color=F.INK2, lw=0.8, alpha=0.6)
    a2.axvspan(lo, hi, color=F.GRID, alpha=0.9, lw=0)
    a2.legend(fontsize=7, loc='upper left')
    a2.set_xlabel('energy (keV)')
    a2.set_title('(b) What a method is given (spectrum 1 of 10 in a series)', loc='left', fontsize=9)
    fig.suptitle('W2. Making a test with a known answer: real scatter under a synthetic line', x=0.01, ha='left',
                 fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W2_one_test_spectrum.png'), dpi=150)
    plt.close(fig)
    N['one_spectrum'] = dict(counts_in_box=int(c0[box].sum()), expected_in_box=r3(float((bc.p * full + spec.expected)[box].sum())),
                             line_expected_in_box=r3(float(spec.expected[box].sum())))

    # W3: the fit, P1 and P1+P3, on spectrum 1
    methods = ('p1', 'p1p3', 'p1p2p3')
    ks = xs.calibrate(name, bc.cond, list(methods))[1]
    fig, axes = plt.subplots(2, 3, figsize=(16, 6.4), sharex=True, sharey='row', gridspec_kw=dict(height_ratios=(2.3, 1)))
    N['fit'] = {}
    for j, m in enumerate(methods):
        x, data, ref, each = _reader_fit(m, bc.cond, spec, counts)
        r = each[0]
        sel = (x >= lo) & (x <= hi)
        y = data[0][:, 1] * xs.SCALE
        mu = r.model(x) * xs.SCALE
        bgm = r.background_at(x) * xs.SCALE
        ax, rx = axes[0, j], axes[1, j]
        ax.errorbar(x[sel], y[sel], yerr=np.sqrt(np.maximum(mu[sel], 1)), fmt='.', ms=3, color=F.INK, ecolor=F.MUTED,
                    elinewidth=0.6, label='data' + (', escapes removed' if m != 'p1' else ''))
        ax.plot(x[sel], mu[sel], color=BLUE, lw=1.4, label='fit: Gaussian + quadratic' + (', width fixed' if m == 'p1p2p3' else ''))
        ax.plot(x[sel], bgm[sel], color=BLUE, lw=0.9, ls='--', label='its quadratic background')
        if m == 'p1':
            ax.axvline(esc, color=VIOLET, lw=0.8, ls='--')
        res = (y[sel] - mu[sel]) / np.sqrt(np.maximum(mu[sel], 1e-9))
        rx.axhline(0, color=F.INK2, lw=0.6)
        rx.bar(x[sel], res, width=float(np.median(np.diff(x))) * 0.8, color=BLUE, alpha=0.7)
        rx.set_ylim(-4, 4)
        rx.set_ylabel('miss / its noise\n(data − fit) / √fit')
        rx.set_xlabel('energy (keV)')
        est = r.peaks[0].area / float(np.median(np.abs(np.diff(x)))) * xs.SCALE / ks[m][0]
        err = r.peaks[0].area_err / float(np.median(np.abs(np.diff(x)))) * xs.SCALE / ks[m][0]
        k = int(sel.sum())
        chi2 = float(np.sum(res ** 2))
        N['fit'][m] = dict(estimate=r3(est), error=r3(err), truth=r3(truth), ratio=r3(est / truth), pull=r3((est - truth) / err),
                           k_calibration=r3(ks[m][0]), points=k, chi2=r3(chi2), dof=k - 4, chi2_dof=r3(chi2 / (k - 4)),
                           centre_keV=r3(ref.peaks[0].centre), fwhm_keV=r3(ref.peaks[0].fwhm))
        ax.set_title('%s\nestimate %.0f ± %.0f photons (truth %.0f); misfit χ²/dof %.2f'
                     % ({'p1': '(a) Poisson fit (the default)', 'p1p3': '(b) Poisson fit + escapes removed (before the fit)',
                         'p1p2p3': '(c) Poisson fit + fixed width + escapes removed'}[m], est, err, truth,
                        chi2 / (k - 4)), loc='left', fontsize=9)
        ax.legend(fontsize=7, loc='upper left')
        ax.set_ylabel('counts per channel')
    fig.suptitle('W3. The fit over one spectrum, with its residuals (each miss in units of its own noise, √(expected counts))',
                 x=0.01, ha='left', fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W3_fit_and_residuals.png'), dpi=150)
    plt.close(fig)

    # W4: 500 spectra: bias, its error, pulls
    rows = xb.run_blank((name, bc, list(methods), range(50), ci))
    sc = {r['method']: r for r in xs.score(rows, {name: ks}, {name: bc.cond}, list(methods))}
    committed = {(r['condition'], r['method']): r for r in read(os.path.join(SHOOT, 'run_blanks', 'scores.csv')) +
                 read(os.path.join(SHOOT, 'run_blanks_options', 'scores.csv'))}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    N['replicates'] = {}
    for m, c in zip(methods, (BLUE, GREEN, VIOLET)):
        est = np.array([r[4] for r in rows if r[3] == m and r[4] is not None]) / ks[m][0]
        err = np.array([r[5] for r in rows if r[3] == m and r[4] is not None]) / ks[m][0]
        rel = est / truth - 1
        pull = (est - truth) / err
        axes[0].hist(100 * rel, bins=40, color=c, alpha=0.55, label=xs_short(m))
        axes[0].axvline(100 * rel.mean(), color=c, lw=1.5)
        axes[1].hist(pull, bins=np.linspace(-5, 5, 41), color=c, alpha=0.55, density=True, label=xs_short(m))
        q = committed[(name, m)]
        N['replicates'][m] = dict(spectra=int(len(rel)), bias=r3(sc[m]['bias']), bias_se=r3(sc[m]['bias_se']),
                                  sd=r3(sc[m]['sd']), pull_mean=r3(sc[m]['pull_mean']), pull_sd=r3(sc[m]['pull_sd']),
                                  committed_bias=r3(num(q['bias'])), committed_bias_se=r3(num(q['bias_se'])),
                                  accurate=bool(abs(sc[m]['bias']) <= max(0.02, 2 * sc[m]['bias_se'])))
        assert abs(sc[m]['bias'] - num(q['bias'])) <= 1e-5 * max(1.0, abs(sc[m]['bias'])), (m, sc[m]['bias'], q['bias'])  # the run's own draws (the CSV keeps 6 figures)
    g = np.linspace(-5, 5, 200)
    axes[1].plot(g, np.exp(-g ** 2 / 2) / math.sqrt(2 * math.pi), color=F.INK, lw=1, label='honest errors: N(0, 1)')
    axes[0].axvline(0, color=F.INK, lw=0.8)
    axes[0].set_xlabel('estimate / truth - 1 (%)')
    axes[0].set_ylabel('spectra')
    axes[0].set_title('(a) 500 estimates (50 series of 10); the line is their mean, the bias', loc='left', fontsize=9)
    axes[0].legend(fontsize=7)
    axes[1].set_xlabel('pull = (estimate - truth) / its error bar')
    axes[1].set_title('(b) Pulls: do the error bars say the truth?', loc='left', fontsize=9)
    axes[1].legend(fontsize=7)
    ax = axes[2]
    allm = ('window', 'fit_data', 'p1', 'p1p3', 'p1p2p3', 'xeray', 'pymca', 'pyxrf')
    ys = np.arange(len(allm))[::-1]
    N['verdicts'] = {}
    for yy, m in zip(ys, allm):
        q = committed.get((name, m))
        if q is None:
            continue
        bb, ss = 100 * num(q['bias']), 100 * num(q['bias_se'])
        ok = abs(bb) <= max(2, 2 * ss)
        ax.errorbar([np.clip(bb, -30, 30)], [yy], xerr=[[2 * ss], [2 * ss]], fmt='o', color=BLUE if ok else RED, ms=5)
        N['verdicts'][m] = dict(bias=r3(bb / 100), bias_se=r3(ss / 100), accurate=bool(ok))
    ax.axvspan(-2, 2, color=F.GRID, alpha=0.9, lw=0)
    ax.axvline(0, color=F.INK2, lw=0.6)
    ax.set_yticks(ys)
    ax.set_yticklabels([xs_short(m) for m in allm], fontsize=8)
    ax.set_xlim(-30, 30)
    ax.set_xlabel('bias (%), bar = 2 × its standard error (clipped at ±30)')
    ax.set_title('(c) The verdict: blue = accurate, |bias| ≤ 2 %\n(or ≤ 2 standard errors, when those are larger)', loc='left', fontsize=9)
    fig.suptitle('W4. From 500 spectra to a verdict, this condition (Ni K, line = background, 1000 counts in the line window)',
                 x=0.01, ha='left', fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W4_bias_pulls_verdict.png'), dpi=150)
    plt.close(fig)

    # W5: the same verdict over the four line strengths, and the false signal
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.4))
    zero = {(r['condition'], r['method']): r for r in read(os.path.join(SHOOT, 'run_blanks', 'zero.csv')) +
            read(os.path.join(SHOOT, 'run_blanks_options', 'zero.csv'))}
    N['ratios'] = {}
    weakest = []
    for m, c in zip(('p1', 'p1p3', 'p1p2p3', 'pymca'), (BLUE, GREEN, VIOLET, ORANGE)):
        xsr, yb, ye = [], [], []
        for rt in xb.RATIOS:
            q = committed.get(('%s|%s|%d|%g' % (EX['blank'], EX['target'], EX['background'], rt), m))
            if q is None:
                continue
            xsr.append(rt)
            yb.append(100 * num(q['bias']))
            ye.append(200 * num(q['bias_se']))
        a1.errorbar(xsr[1:], yb[1:], yerr=ye[1:], fmt='-o', color=c, ms=4, label=xs_short(m), capsize=2)
        weakest.append('%s %+.0f %%' % (xs_short(m), yb[0]))
        N['ratios'][m] = {str(rt): r3(v / 100) for rt, v in zip(xsr, yb)}
        zq = zero.get(('%s|%s|%d|0' % (EX['blank'], EX['target'], EX['background']), m))
        if zq is not None:
            N.setdefault('false_signal_per100', {})[m] = r3(num(zq['false_per100']))
    a1.axhspan(-2, 2, color=F.GRID, alpha=0.9, lw=0)
    a1.set_xscale('log')
    a1.set_xticks(xb.RATIOS[1:])
    a1.set_xticklabels(['0.3', '1', '3'])
    a1.xaxis.set_minor_formatter(plt.NullFormatter())
    a1.text(0.98, 0.45, 'At 0.1 (off the scale):\n' + '\n'.join(weakest), transform=a1.transAxes, fontsize=7.5, ha='right',
            color=F.INK2)
    a1.set_xlabel('line strength: line photons / background counts in the line window')
    a1.set_ylabel('bias (%), bars: 2 standard errors')
    a1.set_title('(a) Bias against the line\'s strength (Ni K on %s, %d background counts)' % (F.blank_name(EX['blank']), EX['background']),
                 loc='left', fontsize=9)
    a1.legend(fontsize=7)
    fs = N.get('false_signal_per100', {})
    a2.barh(range(len(fs)), list(fs.values()), color=[BLUE, GREEN, VIOLET, ORANGE][:len(fs)])
    a2.set_yticks(range(len(fs)))
    a2.set_yticklabels([xs_short(m) for m in fs], fontsize=8)
    a2.set_xlabel('photons reported per 100 background counts, with no line at all')
    a2.set_title('(b) The false signal: the bare thinned blank, nothing injected', loc='left', fontsize=9)
    fig.suptitle('W5. Why removing the escapes matters here: the beam\'s Si escape sits on Ni Kα', x=0.01, ha='left',
                 fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W5_strength_and_false_signal.png'), dpi=150)
    plt.close(fig)
    with open(os.path.join(out, 'numbers.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(N, f, indent=1)
    return N


def xs_short(m):
    return F.SHORT.get(m, m)


# ---- the models study -----------------------------------------------------------------------------

def _resid_rows(bid):
    R = [r for r in read(os.path.join(MODELS, 'scatter', 'residuals.csv')) if r['blank'] == bid]
    out = {}
    for m in ('generator', 'gaussian', 'full'):
        rr = [r for r in R if r['model'] == m]
        out[m] = dict(e=np.array([num(r['energy_keV']) for r in rr]), n=np.array([num(r['counts']) for r in rr]),
                      mu=np.array([num(r['model_counts']) for r in rr]), sc=np.array([num(r['scatter_counts']) for r in rr]),
                      d=np.array([num(r['deviance_residual']) for r in rr]))
    return out


def _dev(n, mu):
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(n > 0, n * np.log(n / mu), 0.0)
    return 2 * (mu - n + t)


def models(out):
    os.makedirs(out, exist_ok=True)
    N = {}
    bid, tgt = MEX['blank'], MEX['target']
    R = _resid_rows(bid)
    b = xb.load_blank(os.path.join(xb.BLANKS, bid + '.csv'))
    E0 = b['beam']
    bc = xb.BlankCond(b, tgt, 1000, 1.0)
    line, fw = bc.cond.line, bc.cond.fwhm
    e = R['full']['e']
    n = R['full']['n']
    low = e < E0                                            # the half that matters
    bx = (e >= line - fw) & (e <= line + fw)               # +-1 FWHM: the box residual's box
    N['example'] = dict(blank=bid, readout=b['readout'], beam_keV=E0, line=tgt, line_keV=r3(line), fwhm_keV=r3(fw),
                        counts_in_box=int(n[bx].sum()), thinning_p_at_1000=r3(bc.p))

    # W1: three models on one blank, with residuals
    fig, axes = plt.subplots(4, 1, figsize=(11, 9.2), sharex=True, gridspec_kw=dict(height_ratios=(2.4, 1, 1, 1)))
    sel = e < E0 + 0.3
    axes[0].step(e[sel], n[sel], where='mid', color=F.INK, lw=0.7, label='%s (real counts)' % F.blank_name(bid))
    N['box'] = {}
    for k, m in enumerate(('generator', 'gaussian', 'full')):
        mu = R[m]['mu']
        axes[0].plot(e[sel], mu[sel], color=MODEL_COLOR[m], lw=1.1, label=MODEL_SHORT[m])
        d = R[m]['d']
        axes[k + 1].bar(e[sel], np.clip(d[sel], -12, 12), width=float(np.median(np.diff(e))), color=MODEL_COLOR[m], lw=0)
        axes[k + 1].axhline(0, color=F.INK2, lw=0.5)
        axes[k + 1].axvspan(line - fw, line + fw, color=F.GRID, alpha=0.9, lw=0)
        nb, mb = float(n[bx].sum()), float(mu[bx].sum())
        dl = float(np.sum(_dev(n[low], mu[low])))
        N['box'][m] = dict(data=r3(nb), model=r3(mb), box_residual=r3(nb / mb - 1), z=r3((nb - mb) / math.sqrt(mb)),
                           dev_per_point_low=r3(dl / int(low.sum())))
        axes[k + 1].set_ylabel('%s\nmiss / its noise' % MODEL_SHORT[m], fontsize=8)
        axes[k + 1].set_ylim(-12, 12)
        axes[k + 1].text(0.01, 0.85, 'in the Ti line window: data / model − 1 = %+.1f %%; below the beam, misfit (deviance per point) %.2f'
                         % (100 * (nb / mb - 1), dl / int(low.sum())), transform=axes[k + 1].transAxes, fontsize=7.5)
    axes[0].axvspan(line - fw, line + fw, color=F.GRID, alpha=0.9, lw=0)
    axes[0].set_yscale('log')
    axes[0].set_ylabel('counts per channel')
    axes[0].legend(fontsize=7, loc='upper left')
    axes[0].set_title('The %s (7-element detector, beam %.1f keV) and three scatter models fitted to it; grey: the Ti K '
                      'line window (± 1 FWHM)' % (F.blank_name(bid), E0), loc='left', fontsize=9)
    axes[-1].set_xlabel('energy (keV)')
    fig.suptitle('W1. A scatter model over the data, with its residuals (each miss in noise units: about ±1 where the model '
                 'is right)', x=0.01, ha='left', fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W1_scatter_models_and_residuals.png'), dpi=150)
    plt.close(fig)

    # W2: the misfit at use: thin the blank as the shootout does and measure the deviance per point
    rng = np.random.default_rng([20261125, 21])
    N['at_use'] = {}
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 4.4))
    for m in ('generator', 'gaussian', 'full'):
        mu = R[m]['mu']
        D = float(np.sum(_dev(n[low], mu[low]))) / int(low.sum())
        sims = []
        for _ in range(40):
            t = rng.binomial(n[low].astype(np.int64), bc.p).astype(float)
            sims.append(float(np.sum(_dev(t, bc.p * mu[low]))) / int(low.sum()))
        pred = 1 + bc.p * (D - 1)
        N['at_use'][m] = dict(full_counts=r3(D), thinned_measured=r3(float(np.mean(sims))),
                              thinned_sd=r3(float(np.std(sims, ddof=1))), predicted_1_plus_p=r3(pred))
        ax.errorbar([D], [np.mean(sims)], yerr=[np.std(sims, ddof=1)], fmt='o', color=MODEL_COLOR[m], label=MODEL_SHORT[m], ms=6)
    # a perfect model: draw from the full model itself
    sims = []
    for _ in range(40):
        t = rng.poisson(bc.p * R['full']['mu'][low]).astype(float)
        sims.append(float(np.sum(_dev(t, bc.p * R['full']['mu'][low]))) / int(low.sum()))
    N['at_use']['perfect'] = dict(thinned_measured=r3(float(np.mean(sims))), thinned_sd=r3(float(np.std(sims, ddof=1))))
    g = np.logspace(np.log10(0.5), np.log10(200), 200)
    ax.plot(g, 1 + bc.p * (g - 1), color=F.INK2, lw=0.8, label='rule: 1 + p × (misfit − 1), p = %.3f' % bc.p)
    ax.axhline(1, color=F.GRID, lw=1)
    ax.set_xscale('log')
    ax.set_xlabel('misfit (deviance per point) at full counts: the blank as measured')
    ax.set_ylabel('misfit after thinning to %d counts\nin the Ti line window (40 draws)' % 1000)
    ax.legend(fontsize=7)
    ax.set_title('W2. A misfit shrinks when the counts do: what a method sees is the thinned blank', loc='left',
                 fontsize=9.5, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W2_misfit_at_use.png'), dpi=150)
    plt.close(fig)

    # W3: the real blank, its twin and a second draw, against the scatter model
    tw = xb.load_blank(os.path.join(MODELS, 'scatter', 'twins_full', bid + '.csv'))
    tw2 = xb.load_blank(os.path.join(MODELS, 'scatter', 'twins_full_redraw', bid + '.csv'))
    sc = R['full']['sc']
    z = (e > line - 0.6) & (e < line + 0.6)
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, gridspec_kw=dict(height_ratios=(2, 1.2)))
    axes[0].plot(e[z], sc[z], color=BLUE, lw=1.4, label='the full model\'s scatter (elastic, Compton, background; no line)')
    N['twins'] = {}
    for lab, cnt, c in (('real blank', n, F.INK), ('twin (one Poisson draw of the model)', tw['counts'], ORANGE),
                        ('second draw (the floor)', tw2['counts'], GREEN)):
        axes[0].step(e[z], cnt[z], where='mid', color=c, lw=0.7, label=lab)
        r = (cnt - sc) / np.sqrt(sc)
        axes[1].plot(e[z], r[z], '.', ms=3, color=c)
        N['twins'][lab.split(' (')[0]] = dict(chi2_dof_low=r3(float(np.sum(((cnt - sc) ** 2 / sc)[low]) / int(low.sum()))),
                                              box_over_model=r3(float(cnt[bx].sum() / sc[bx].sum()) - 1))
    for ax in axes:
        ax.axvspan(line - fw, line + fw, color=F.GRID, alpha=0.9, lw=0)
    axes[1].axhline(0, color=F.INK2, lw=0.5)
    axes[1].set_ylabel('miss / its noise\n(counts − model) / √model')
    axes[1].set_xlabel('energy (keV)')
    axes[0].set_ylabel('counts per channel')
    axes[0].legend(fontsize=7, loc='upper left')
    axes[0].set_title('Around the Ti K line window of the %s: the twins scatter about the model as pure noise; the real '
                      'blank also carries what the model misses' % F.blank_name(bid), loc='left', fontsize=9)
    fig.suptitle('W3. A model twin: the model\'s scatter, drawn once (and once more, for the floor)', x=0.01, ha='left',
                 fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W3_real_twin_redraw.png'), dpi=150)
    plt.close(fig)

    # W4: the floor: how far two draws of one truth land, against how far a model lands from the real
    C = read(os.path.join(MODELS, 'scatter', 'compare.csv'))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
    cond = '%s|%s|1000|1' % (bid, tgt)
    meths = ('fit_data', 'p1', 'p1p3', 'p1p2p3', 'xeray', 'pymca', 'pyxrf')
    ys = np.arange(len(meths))[::-1]
    N['floor_example'] = {}
    for yy, m in zip(ys, meths):
        q = {r['model']: r for r in C if r['condition'] == cond and r['method'] == m}
        if 'full' not in q:
            continue
        br, bt, b2 = num(q['full']['bias_real']), num(q['full']['bias_twin']), num(q['full_redraw']['bias_twin'])
        a1.plot([100 * br], [yy + 0.18], 'o', color=F.INK, ms=5)
        a1.plot([100 * bt], [yy], 'o', color=ORANGE, ms=5)
        a1.plot([100 * b2], [yy - 0.18], 'o', color=GREEN, ms=5)
        N['floor_example'][m] = dict(real=r3(br), twin=r3(bt), second_draw=r3(b2))
    a1.plot([], [], 'o', color=F.INK, label='real blank')
    a1.plot([], [], 'o', color=ORANGE, label='full-model twin')
    a1.plot([], [], 'o', color=GREEN, label='its second draw')
    a1.axvline(0, color=F.INK2, lw=0.6)
    a1.set_yticks(ys)
    a1.set_yticklabels([xs_short(m) for m in meths], fontsize=8)
    a1.set_xlabel('bias (%)')
    a1.legend(fontsize=7)
    a1.set_title('(a) One condition (%s, Ti K, line = background): each method\'s bias three ways' % F.blank_name(bid), loc='left',
                 fontsize=9)
    N['floor_cdf'] = {}
    for m, c, lab in (('full_redraw', GREEN, 'floor: second draw against the first'), ('full', BLUE, 'full model against the real'),
                      ('gaussian', RED, 'Gaussian detector against the real'), ('generator', F.MUTED, 'generator defaults against the real')):
        d = np.sort([abs(num(r['diff'])) for r in C if r['model'] == m and r['method'] != 'window' and np.isfinite(num(r['diff']))])
        a2.plot(100 * d, np.arange(1, len(d) + 1) / len(d), color=c, lw=1.4, label=lab)
        N['floor_cdf'][m] = dict(median=r3(float(np.median(d))), p90=r3(float(np.percentile(d, 90))), n=int(len(d)))
    a2.set_xscale('log')
    a2.set_xlim(0.05, 300)
    a2.set_xlabel('|bias on the twin − bias on the reference| (%)')
    a2.set_ylabel('share of conditions × methods')
    a2.axhline(0.5, color=F.GRID, lw=1)
    a2.legend(fontsize=7, loc='lower right')
    a2.set_title('(b) All 240 conditions × 7 fitting methods: where each curve crosses 0.5 is its median', loc='left',
                 fontsize=9)
    fig.suptitle('W4. The floor: a model stands in for the real scatter only as far as two draws of one truth agree',
                 x=0.01, ha='left', fontsize=10, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W4_the_floor.png'), dpi=150)
    plt.close(fig)

    # W5: a line with readout B's measured skew (synthetic), fitted by a Gaussian and by one tail
    noise, fano = L.RESOLUTION['B']
    sh = xb.LINE_SHAPES['line']['B']
    det = mca.Detector(noise=noise, fano=fano, tail=sh['tail'], tail_slope=sh['tail_slope'], escape=L.ESCAPE['B'])
    s = mm.spectrum({'Cu K': 3e5}, detector=det, background=20.0, calib=(0.0, 0.01, 0.0), channels=1000)
    cnt = np.random.default_rng(7).poisson(s.expected).astype(float)
    fig, axes = plt.subplots(2, 3, figsize=(15, 5.8), sharex=True, gridspec_kw=dict(height_ratios=(2.2, 1)))
    N['line_ladder'] = {}
    for j, shp in enumerate(('gauss_res', 'gauss', 'tail')):
        lf = L.LineFit(s.energy, cnt, 'Cu K', 'B', shp)
        P, p, dev, dof = lf.fit()
        mu = lf.mu(p)
        ka = (lf.e > 7.6) & (lf.e < 8.4)
        ax, rx = axes[0, j], axes[1, j]
        ax.errorbar(lf.e[ka], lf.n[ka], yerr=np.sqrt(lf.n[ka]), fmt='.', ms=2.5, color=F.INK, ecolor=F.MUTED, elinewidth=0.5)
        ax.plot(lf.e[ka], mu[ka], color=BLUE, lw=1.3)
        ax.set_yscale('log')
        rx.bar(lf.e[ka], np.clip(lf.resid(p)[ka], -15, 15), width=0.008, color=BLUE)
        rx.axhline(0, color=F.INK2, lw=0.5)
        rx.set_ylim(-15, 15)
        rx.set_xlabel('energy (keV)')
        fwr = mca.Detector(noise=P['noise'], fano=fano).fwhm(8.04) / mca.Detector(noise=noise, fano=fano).fwhm(8.04)
        N['line_ladder'][shp] = dict(dev_per_dof=r3(dev / dof), tail=r3(P['tail']), tail_slope_keV=r3(P['tail_slope']),
                                     fwhm_over_resolution=r3(fwr))
        ax.set_title({'gauss_res': '(a) Gaussian at the resolution', 'gauss': '(b) Gaussian, width free',
                      'tail': '(c) Gaussian + one low-energy tail'}[shp] + ': misfit (deviance/dof) %.1f' % (dev / dof),
                     loc='left', fontsize=9)
    axes[0, 0].set_ylabel('counts per channel')
    axes[1, 0].set_ylabel('miss / its noise')
    fig.suptitle('W5. A synthetic Cu K line with the 7-element detector\'s measured skew (%.0f %% in a %.0f eV tail), 3e5 photons: '
                 'the shape ladder' % (100 * sh['tail'], 1000 * sh['tail_slope']), x=0.01, ha='left', fontsize=10,
                 fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W5_line_shape_ladder.png'), dpi=150)
    plt.close(fig)
    N['line_truth'] = dict(tail=sh['tail'], tail_slope_keV=sh['tail_slope'], photons=3e5)

    # the P2 mechanism, noise-free: elastic-shaped against real-shaped lines on the thinned blank's mean
    N['p2_noise_free'] = p2_noise_free()
    with open(os.path.join(out, 'numbers.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(N, f, indent=1)
    return N


def p2_noise_free():
    """Each method on the expected spectrum itself (the thinned blank's mean
    plus the line's, no noise), calibrated on its clean twin of the same
    shape: what is left is the method's systematic error, with no draw."""
    out = {}
    for bid, tgt in (('E9.2-a', 'Ni K'), ('E9.2-a', 'Cu K'), ('E6.1-a', 'Cr K'), ('E6.1-a', 'Ti K')):
        b = xb.load_blank(os.path.join(xb.BLANKS, bid + '.csv'))
        for shape in ('elastic', 'line'):
            bc = xb.BlankCond(b, tgt, 1000, 3.0, shape)
            spec = bc.spectra()
            truth = mm.family_photons(spec, tgt)
            ks = xs.calibrate('x', bc.cond, ['p1p3', 'p1p2p3'])[1]
            mean = bc.p * b['counts'] + spec.expected
            for m in ('p1p3', 'p1p2p3'):
                r = xs.run_method(m, bc.cond, [spec] * 3, [mean.copy() for _ in range(3)])
                out.setdefault('%s %s' % (bid, tgt), {}).setdefault(m, {})[shape] = r3(r[0][0] / ks[m][0] / truth - 1)
            # k: what the method reads on its clean twin per true photon (the shape's own loss, calibrated out)
            out['%s %s' % (bid, tgt)].setdefault('k_p1p2p3', {})[shape] = r3(ks['p1p2p3'][0])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--part', default='shootout,models')
    ap.add_argument('--shootout-out', default=os.path.join(SHOOT, 'walkthrough'))
    ap.add_argument('--models-out', default=os.path.join(MODELS, 'walkthrough'))
    a = ap.parse_args(argv)
    xs._quiet()
    F.style()
    parts = a.part.split(',')
    if 'shootout' in parts:
        print(json.dumps(shootout(a.shootout_out), indent=1))
    if 'models' in parts:
        print(json.dumps(models(a.models_out), indent=1))


if __name__ == '__main__':
    main()
