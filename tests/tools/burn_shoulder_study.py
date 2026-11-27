"""Study of the GID burn estimators on a peak with a broad shoulder (P44;
lss_core.burn.measure_gid): synthetic burns with a known truth, how well
each estimator reads the peak's change; NX school burns 14 and 15 as the
public real check.

    python tests/tools/burn_shoulder_study.py --out docs/studies/burn_shoulder            # about 90 min (4 CPUs)
    python tests/tools/burn_shoulder_study.py --out DIR --replicates 30                    # about 8 min
    python tests/tools/burn_shoulder_study.py --out DIR --only S5                          # NX only, a minute
    python tests/tools/burn_shoulder_study.py --out docs/studies/burn_shoulder --only R    # S6, about 10 min
    python tests/tools/burn_shoulder_study.py --out sample_data/private/burn_shoulder --real FILE...   # real burns

The question: a pinhole GID frame's peak is sharp and sits on a broad
shoulder. The template estimator (the default) fits each frame as the mean
frame's whole shape, shifted and stretched; the shoulder is stretched with
the peak, so a broadening peak reads as a gain in intensity (P44). The
split estimators (``split``: the shoulder's amplitude free per frame;
``split_fixed``: held at 1) take the shoulder out of the stretch. Which
reads the truth, on which shoulder, and what does each say about NX?

The truth (``tests/synthetic/burn_profiles.py``, 21 frames of 10 s; each
change over the test, f = t / t_end):

- ``none``: nothing changes (false alarms);
- ``fade``: the peak's area × (1 − 0.2 f);
- ``broaden``: its FWHM × (1 + 0.3 f) at constant area;
- ``shift``: its centre + 0.004 f Å⁻¹;
- ``shoulder``: a fade of 0.2 under a shoulder 3 × stronger;
- ``background``: the flat floor × (1 + 0.5 f);
- ``shoulder_grows``: the shoulder's height × (1 + 0.5 f), the peak steady;
- ``both_fade``: the peak fades 0.2 and the shoulder 0.3;
- ``nx15_like``: FWHM × (1 + 0.2 f) and area × (1 − 0.13 f), as the split
  reads NX burn 15.

Part A: every case on every shoulder shape ('gaussian', 'lorentzian',
'asymmetric', 'two'), at high counts (monitor 1e7: a frame's intensity
known to 0.19 %, so that what remains is bias, not noise). Part B: the
Gaussian shoulder at fewer counts, cases none, fade, broaden and
nx15_like: monitor 1e6 (0.6 % per frame), 6e4 (2.1 %, as NX 15: 2.0 %)
and 1e4 (3.9 %, as NX 14: 3.8 %; ``NX_MONITORS``, each frame's template
intensity error matched, measured 2026-11-27).

Each replicate: every estimator, then the reader's own trend analysis
(``burn.analyse``, errors from the scatter, the GID default). Per
quantity: the change over the test read from its linear model (relative
for intensity, FWHM and the split's shoulder; Å⁻¹ for the position), its
σ, and the verdict (stable or changing: a line beats a constant by AICc).
Per cell: the bias and SD of the change, the pull SD ((read − truth)/σ:
1 means honest errors), the coverage of ±1σ and ±1.96σ, the share
called changing and the share called right.

The template estimator's 'fit' sibling (one Gaussian per frame) is left
out of the synthetic part (a single Gaussian does not describe the frame:
χ²/dof 10–40 on NX; ``docs/reports/patch_demo.md`` figure 6 has it) and
kept in the NX check.

Figures: S1 the bias of each change per case and estimator (Gaussian
shoulder); S2 the intensity's bias on each shoulder shape; S3 verdicts and
coverage on the intensity; S4 fewer counts; S5 NX school burns 14 and 15;
S6 (``--only R``, part R) the reference's noise: each frame measured
against the frames' mean, the mean smoothed, and the noiseless mean, at
high counts and at NX 14's and 15's (a bias at low counts that the
noiseless reference does not have is the noise of the mean frame).
Tables: ``results.csv`` (one row per cell, estimator and quantity),
``nx.csv``, ``numbers.json``; part R: ``reference_noise.csv``,
``numbers_reference.json``.
"""
import argparse
import csv
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from lss_core import burn                              # noqa: E402
from synthetic import burn_profiles as bp              # noqa: E402

NX = 'sample_data/NX_school/2026sep/20260923'
ESTIMATORS = ('template', 'moments', 'split', 'split_fixed')
NX_ESTIMATORS = ('template', 'moments', 'fit', 'split', 'split_fixed')
QUANTITIES = ('intensity', 'fwhm', 'centre', 'shoulder')
CASES = {
    'none': dict(change='none', amount=0.0),
    'fade': dict(change='fade', amount=0.2),
    'broaden': dict(change='broaden', amount=0.3),
    'shift': dict(change='shift', amount=0.004),
    'shoulder': dict(change='shoulder', amount=0.2),
    'background': dict(change='background', amount=0.5),
    'shoulder_grows': dict(change='none', amount=0.0, shoulder_change=0.5),
    'both_fade': dict(change='fade', amount=0.2, shoulder_change=-0.3),
    'nx15_like': dict(change='broaden', amount=0.2, area_change=-0.13),
}
SHAPES = ('gaussian', 'lorentzian', 'asymmetric', 'two')
PART_B = dict(cases=('none', 'fade', 'broaden', 'nx15_like'), monitors=(1e6, 6e4, 1e4))
# the monitor at which a synthetic frame's template intensity has the error of an NX school frame
# (3.8 % on burn 14, 2.0 % on 15; synthetic 3.9 % and 2.1 %): tests/test_burn_shoulder_study.py
NX_MONITORS = {14: 1e4, 15: 6e4}
MONITOR = 1e7
FRAMES, CTIME = 21, 10.0
COLOURS = {'template': 'C0', 'moments': 'C7', 'fit': 'C5', 'split': 'C3', 'split_fixed': 'C1'}
LABEL = {'intensity': 'intensity', 'fwhm': 'FWHM', 'centre': 'position', 'shoulder': 'shoulder'}


def change_of(fit, T, relative=True):
    """(change over [0, T], σ) from a linear trend fit c + s·t: s·T/c
    (relative) or s·T, σ by the delta method from the fit's covariance."""
    if fit is None or not fit.ok:
        return math.nan, math.nan
    c, s = (float(v) for v in fit.params)
    cov = fit.cov
    if not relative:
        return s * T, math.sqrt(max(cov[1, 1], 0.0)) * T
    g = np.array([-s * T / c ** 2, T / c])
    return s * T / c, math.sqrt(max(float(g @ cov @ g), 0.0))


def true_change(t, v, T, relative=True):
    a, b = np.polyfit(t, v, 1)
    return float(a * T / b) if relative else float(a * T)


def truths(tr, T):
    return {'intensity': true_change(tr.t, tr.area, T), 'fwhm': true_change(tr.t, tr.fwhm, T),
            'centre': true_change(tr.t, tr.centre, T, relative=False),
            'shoulder': true_change(tr.t, tr.shoulder_height, T)}


def read_all(profiles, t, T, estimators=ESTIMATORS):
    """{estimator: {quantity: (change, σ, stable)}} and the split's shoulder (or None)."""
    out, extra = {}, {}
    for e in estimators:
        try:
            values, ref, _, details = burn.measure_gid(profiles, estimator=e)
            res = burn.analyse(t, values, errors='scatter')
        except (RuntimeError, ValueError):
            out[e] = {}
            continue
        out[e] = {}
        for q, c in res.items():
            v, s = change_of(c.fits.get('linear'), T, relative=q != 'centre')
            out[e][q] = (v, s, c.stable)
        if e in burn.SPLIT_ESTIMATORS:
            extra[e] = ref.get('shoulder')
    return out, extra


def _replicates(job):
    """One cell's seeds: a list of (seed, truths, reads, found shoulder)."""
    case, shape, monitor, seeds, core = job
    T = FRAMES * CTIME
    rows = []
    before, burn.SPLIT_CORE = burn.SPLIT_CORE, core          # ``--core``; set back after
    try:
        for seed in seeds:
            prof, tr = bp.profiles(n=FRAMES, ctime=CTIME, monitor=monitor, seed=seed, shoulder_shape=shape,
                                   **CASES[case])
            reads, extra = read_all(prof, tr.t, T)
            rows.append((seed, truths(tr, T), reads, {k: v is not None for k, v in extra.items()}))
    finally:
        burn.SPLIT_CORE = before
    return (case, shape, monitor), rows


def cells(parts=('A', 'B'), cases=None, shapes=None):
    out = []
    if 'A' in parts:
        out += [(c, s, MONITOR) for c in CASES if not cases or c in cases for s in SHAPES if not shapes or s in shapes]
    if 'B' in parts:
        out += [(c, 'gaussian', m) for c in PART_B['cases'] if not cases or c in cases for m in PART_B['monitors']]
    return out


def summarise(key, reps):
    case, shape, monitor = key
    rows = []
    for e in ESTIMATORS:
        for q in QUANTITIES:
            got = [(r[1][q], *r[2].get(e, {}).get(q, (math.nan, math.nan, None))) for r in reps]
            got = [g for g in got if not (q == 'shoulder' and e != 'split')]
            if not got or all(math.isnan(g[1]) for g in got):
                continue
            truth = got[0][0]
            v = np.array([g[1] for g in got])
            s = np.array([g[2] for g in got])
            ok = np.isfinite(v) & np.isfinite(s) & (s > 0)
            pull = (v[ok] - truth) / s[ok]
            changing = np.array([g[3] is False for g in got])[ok]
            moves = abs(truth) > 1e-9
            found = [r[3].get(e, True) for r in reps] if e in burn.SPLIT_ESTIMATORS else [True]
            rows.append(dict(part='A' if monitor == MONITOR else 'B', case=case, shape=shape, monitor=monitor,
                             estimator=e, quantity=q, truth=truth, n=int(np.sum(ok)), failed=int(np.sum(~ok)),
                             mean=float(np.mean(v[ok])), bias=float(np.mean(v[ok]) - truth), sd=float(np.std(v[ok])),
                             rmse=float(np.sqrt(np.mean((v[ok] - truth) ** 2))),
                             pull_mean=float(np.mean(pull)), pull_sd=float(np.std(pull)),
                             cover68=float(np.mean(np.abs(pull) < 1)), cover95=float(np.mean(np.abs(pull) < 1.96)),
                             changing=float(np.mean(changing)), right=float(np.mean(changing == moves)),
                             shoulder_found=float(np.mean(found))))
    return rows


def run(parts=('A', 'B'), replicates=300, workers=None, cases=None, shapes=None, core=burn.SPLIT_CORE):
    """``core``: the split's core half-width in FWHM (burn.SPLIT_CORE, 1.5)."""
    jobs = []
    chunk = 25
    for key in cells(parts, cases, shapes):
        for lo in range(0, replicates, chunk):
            jobs.append(key + (list(range(lo, min(lo + chunk, replicates))), core))
    got = {}
    workers = workers or min(4, os.cpu_count() or 1)
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            results = list(ex.map(_replicates, jobs))
    else:
        results = [_replicates(j) for j in jobs]
    for key, reps in results:
        got.setdefault(key, []).extend(reps)
    rows = []
    for key in cells(parts, cases, shapes):
        rows += summarise(key, sorted(got[key], key=lambda r: r[0]))
    return rows


def _write(path, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))      # every column, in order of first appearance
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})


def _pick(rows, **kw):
    return [r for r in rows if all(r[k] == v for k, v in kw.items())]


def _bars(ax, cases, rows, quantity, shape='gaussian', monitor=MONITOR, scale=1.0, estimators=ESTIMATORS):
    n = len(estimators)
    for j, e in enumerate(estimators):
        xs, ys, es = [], [], []
        for i, c in enumerate(cases):
            r = _pick(rows, case=c, shape=shape, monitor=monitor, estimator=e, quantity=quantity)
            if r:
                xs.append(i + (j - (n - 1) / 2) * 0.8 / n)
                ys.append(scale * r[0]['bias'])
                es.append(scale * r[0]['sd'])
        ax.bar(xs, ys, 0.8 / n, yerr=es, color=COLOURS[e], label=e, error_kw=dict(lw=0.7, capsize=1.5))
    ax.axhline(0, color='k', lw=0.6)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(cases, fontsize=7, rotation=25, ha='right')
    ax.tick_params(axis='y', labelsize=7)


def s1(rows, out):
    """Bias ± SD of each quantity's change, per case and estimator (Gaussian shoulder)."""
    import matplotlib.pyplot as plt
    cases = list(CASES)
    fig, axes = plt.subplots(4, 1, figsize=(9, 9.5), sharex=True)
    units = ('% points', '% points', '10⁻⁴ Å⁻¹', '% points')
    for ax, q, sc, unit in zip(axes, QUANTITIES, (100, 100, 1e4, 100), units):
        _bars(ax, cases, rows, q, scale=sc)
        ax.set_ylabel('%s change:\nread − true (%s)' % (LABEL[q], unit), fontsize=8)
    axes[0].legend(fontsize=7, ncol=4, frameon=False, loc='upper left')
    axes[0].set_title('S1. Each estimator\'s error on the change over the test (Gaussian shoulder; bars: bias, '
                      'whiskers: SD)', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'S1_bias_by_case.png'), dpi=120)
    plt.close(fig)


def s2(rows, out):
    """The intensity change's bias on each shoulder shape."""
    import matplotlib.pyplot as plt
    cases = ['fade', 'broaden', 'shoulder', 'shoulder_grows', 'both_fade', 'nx15_like']
    fig, axes = plt.subplots(1, len(SHAPES), figsize=(13, 3.8), sharey=True)
    for ax, sh in zip(axes, SHAPES):
        _bars(ax, cases, rows, 'intensity', shape=sh, scale=100)
        ax.set_title(sh, fontsize=9)
    axes[0].set_ylabel('intensity change:\nread − true (% points)', fontsize=8)
    axes[0].legend(fontsize=7, frameon=False, loc='upper left')
    fig.suptitle('S2. The intensity\'s error on each shoulder shape (bars: bias, whiskers: SD)', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'S2_bias_by_shape.png'), dpi=120)
    plt.close(fig)


def s3(rows, out):
    """Share called 'changing' and the 95 % coverage, on the intensity (Gaussian shoulder)."""
    import matplotlib.pyplot as plt
    cases = list(CASES)
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8))
    n = len(ESTIMATORS)
    for j, e in enumerate(ESTIMATORS):
        for ax, key in zip(axes, ('changing', 'cover95')):
            xs, ys = [], []
            for i, c in enumerate(cases):
                r = _pick(rows, case=c, shape='gaussian', monitor=MONITOR, estimator=e, quantity='intensity')
                if r:
                    xs.append(i + (j - (n - 1) / 2) * 0.8 / n)
                    ys.append(r[0][key])
            ax.bar(xs, ys, 0.8 / n, color=COLOURS[e], label=e)
    for i, c in enumerate(cases):
        r = _pick(rows, case=c, shape='gaussian', monitor=MONITOR, estimator='template', quantity='intensity')
        if r and abs(r[0]['truth']) > 1e-9:
            axes[0].text(i, 1.02, 'truly\nchanges', ha='center', va='bottom', fontsize=6)
    axes[0].set_ylabel('share called "changing"', fontsize=8)
    axes[0].set_ylim(0, 1.18)
    axes[1].axhline(0.95, color='k', lw=0.6, ls='--')
    axes[1].set_ylabel('share of ±1.96σ intervals\nholding the truth', fontsize=8)
    axes[1].set_ylim(0, 1.05)
    for ax in axes:
        ax.set_xticks(range(len(cases)))
        ax.set_xticklabels(cases, fontsize=7, rotation=25, ha='right')
        ax.tick_params(axis='y', labelsize=7)
    axes[1].legend(fontsize=7, frameon=False, loc='lower left')
    fig.suptitle('S3. The intensity: verdicts (left) and whether the 95 % interval holds the truth (right), '
                 'Gaussian shoulder', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'S3_verdicts_coverage.png'), dpi=120)
    plt.close(fig)


def s4(rows, out):
    """Fewer counts: SD and pull SD of the intensity change against the monitor (Gaussian)."""
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    mons = (MONITOR,) + PART_B['monitors']
    for e in ESTIMATORS:
        for c, ls in (('fade', '-'), ('nx15_like', '--')):
            got = [(m, _pick(rows, case=c, shape='gaussian', monitor=m, estimator=e, quantity='intensity'))
                   for m in mons]
            got = [(m, r[0]) for m, r in got if r]
            if not got:
                continue
            m = [g[0] for g in got]
            axes[0].plot(m, [100 * g[1]['sd'] for g in got], ls, marker='o', ms=3, color=COLOURS[e],
                         label='%s, %s' % (e, c))
            axes[1].plot(m, [100 * abs(g[1]['bias']) for g in got], ls, marker='o', ms=3, color=COLOURS[e])
            axes[2].plot(m, [g[1]['pull_sd'] for g in got], ls, marker='o', ms=3, color=COLOURS[e])
    for ax, lab in zip(axes, ('SD of the intensity change (% points)', '|bias| (% points)', 'pull SD (1: honest)')):
        ax.set_xscale('log')
        ax.set_xlabel('monitor (counts ∝ monitor)', fontsize=8)
        ax.set_ylabel(lab, fontsize=8)
        ax.tick_params(labelsize=7)
        for scan, m in NX_MONITORS.items():
            ax.axvline(m, color='0.6', lw=0.7, ls=':')
            ax.text(m, 0.98, ' NX %d' % scan, transform=ax.get_xaxis_transform(), fontsize=6, va='top',
                    color='0.4')
    axes[2].axhline(1, color='k', lw=0.6, ls='--')
    axes[0].legend(fontsize=6, frameon=False)
    fig.suptitle('S4. Fewer counts (Gaussian shoulder): fade (solid) and an NX 15-like broadening fade (dashed)',
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'S4_counts.png'), dpi=120)
    plt.close(fig)


REF_CASES = ('fade', 'nx15_like')
REF_MONITORS = (MONITOR, NX_MONITORS[15], NX_MONITORS[14])
REFERENCES = ('mean', 'spline', 'truth')


def smooth_reference(x, mean, err, window):
    """The mean frame smoothed inside ``window`` (the points the fits use;
    outside it the mean is kept): a smoothing spline weighted by 1/err with
    χ² ≈ the number of points (scipy UnivariateSpline, s = n; at high counts
    it runs out of knots first and warns: silenced)."""
    import warnings
    from scipy.interpolate import UnivariateSpline
    sel = (x >= window[0]) & (x <= window[1]) & np.isfinite(mean) & np.isfinite(err) & (err > 0)
    out = np.array(mean, float)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        out[sel] = UnivariateSpline(x[sel], mean[sel], w=1.0 / err[sel], s=int(np.sum(sel)))(x[sel])
    return out


def read_with_reference(profiles, ref_mean, window, estimator, found=None):
    """Each frame's intensity and its σ as ``burn.measure_gid`` reads them
    ('template' or 'split'), but measured against ``ref_mean`` instead of
    the frames' own mean. With the frames' mean it gives measure_gid's
    numbers exactly (tested): with ``qxy_range=window``, or with the window
    and ``found`` (the peak ``choose_window`` found: the split's starting
    centre and FWHM) that measure_gid chose itself."""
    x = profiles[0][:, 0]
    sel = (x >= window[0]) & (x <= window[1])
    xw = x[sel]
    step = float(np.median(np.abs(np.diff(xw))))
    shape = ref_mean[sel] - burn._baseline(xw, ref_mean[sel])
    c_ref = float(np.sum(shape * xw) / np.sum(shape))
    if estimator == 'split':
        c0, w0 = (found['centre'], found['fwhm']) if found else (float(xw[np.argmax(shape)]),
                                                                 burn._half_width(xw, shape))
        S, P, sp = burn.split_shoulder(xw, shape, c0, w0, burn.SPLIT_CORE)
        S = None if sp is None else S
        mt, c, area = P, float(np.sum(P * xw) / np.sum(P)), float(np.sum(P) * step)
    else:
        S, mt, c, area = None, shape, c_ref, float(np.sum(shape) * step)
    out, err = [], []
    for prof in profiles:
        y, e = prof[sel, 1], prof[sel, 2]
        e = np.where(e > 0, e, np.nan)
        e = np.where(np.isfinite(e), e, np.nanmax(e) if np.any(np.isfinite(e)) else 1.0)
        p, pe, _, cov = burn._template(xw, y, e, xw, mt, c, S, extra_free=True)
        out.append(p[0] * p[2] * area)
        err.append(math.sqrt(max((p[2] * pe[0]) ** 2 + (p[0] * pe[2]) ** 2 + 2 * p[0] * p[2] * cov[0, 2], 0.0))
                   * area)
    return np.array(out), np.array(err)


def _smoothed_change(r, estimator):
    """A burn result's intensity change re-read against its mean frame
    smoothed (``smooth_reference``), through the reader's trend analysis:
    (change, σ, stable); and the same against the mean itself (the reader's
    own number, a check)."""
    prof, T = r.profiles, r.duration()
    mean = np.mean([q[:, 1] for q in prof], axis=0)
    err = np.sqrt(np.sum([q[:, 2] ** 2 for q in prof], axis=0)) / len(prof)
    out = {}
    for k, ref in (('mean', mean), ('spline', smooth_reference(prof[0][:, 0], mean, err, r.window))):
        i, si = read_with_reference(prof, ref, r.window, estimator, r.reference.get('found'))
        c = burn.analyse(r.x, {'intensity': (i, si)}, errors='scatter')['intensity']
        out[k] = change_of(c.fits.get('linear'), T) + (bool(c.stable),)
    return out


def reference_nx(spec):
    """NX school burns 14 and 15, template and split, each frame measured
    against the frames' mean (the reader's numbers) and against the mean
    smoothed; the intensity change through the reader's trend analysis
    (errors from the scatter), as section 5."""
    import tempfile
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp())
    from lss_core.experiment import Experiment
    exp = Experiment(spec)
    rows = []
    for scan in (14, 15):
        for e in ('template', 'split'):
            r = exp.burn(scan, estimator=e)
            T = r.duration()
            for k, (v, sv, stable) in _smoothed_change(r, e).items():
                rows.append(dict(scan=scan, estimator=e, reference=k, change=v, sigma=sv,
                                 verdict='stable' if stable else 'changing',
                                 reader=float(change_of(r.trends['intensity'].fits.get('linear'), T)[0])))
    return rows


def mean_frame_noise(prof, window):
    """The mean frame's noise in the window, as a share of its peak above the
    chord (median σ of the mean / the shape's maximum): what drives the
    reference's noise (section 6). As measured (tests): NX 14 0.51 %, NX 15
    0.29 %; synthetic NX 15-like burns 0.03 % at monitor 1e7, 0.35 % at 6e4,
    0.85 % at 1e4."""
    x = prof[0][:, 0]
    sel = (x >= window[0]) & (x <= window[1])
    mean = np.mean([q[:, 1] for q in prof], axis=0)
    err = np.sqrt(np.sum([q[:, 2] ** 2 for q in prof], axis=0)) / len(prof)
    shape = mean[sel] - burn._baseline(x[sel], mean[sel])
    return float(np.median(err[sel]) / np.max(shape))


REAL_ESTIMATORS = ('template', 'split', 'split_fixed')


def find_gid_burns(exp):
    """The burn scans of a file (an ``ascan ih`` that does not move,
    lss_core.series.is_burn) whose frames are GID (Det_Th above 2°; without
    a Det_Th column, 2θ from H, K and the wavelength, as Experiment.burn)."""
    from lss_core import series
    found = []
    for n, sc in sorted(exp.scans.items()):
        if not series.is_burn(sc.command) or not sc.columns:
            continue
        cols = sc.columns
        try:
            if 'Det_Th' in cols:
                dth = float(cols['Det_Th'][0])
            else:
                q = math.hypot(float(cols['H'][0]), float(cols['K'][0])) * float(sc.parameters['Wavelength'])
                dth = math.degrees(2.0 * math.asin(q / 4.0 / math.pi))
        except (KeyError, IndexError, ValueError):
            continue
        if burn.is_gid(dth):
            found.append(n)
    return found


def real_check(out, specs, scans=None, prefix='G'):
    """The P44 questions on real GID burns (the hand-off
    docs/handoff_out/10-gid-burn-shoulder.md): every GID burn of ``specs``
    (or ``scans`` of a single file) under the template, the split and the
    split with the shoulder fixed, and the template and split re-read
    against the smoothed mean frame. Writes ``real.csv`` (summary values
    only, burns labelled G01…: no file, scan number, Qxy or frame) and
    ``real_key.csv`` (label → file and scan, and any error: PRIVATE, it
    stays beside the private data). Returns (rows, key)."""
    import tempfile
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp())
    from lss_core.experiment import Experiment
    rows, key = [], []
    for spec in specs:
        exp = Experiment(spec)
        todo = list(scans) if scans and len(specs) == 1 else find_gid_burns(exp)
        for scan in todo:
            label = '%s%02d' % (prefix, len(key) + 1)
            entry = dict(burn=label, spec=spec, scan=scan, error='')
            key.append(entry)
            try:
                got = {}
                for e in REAL_ESTIMATORS:
                    got[e] = exp.burn(scan, estimator=e)
                if got['template'].kind != 'gid':
                    entry['error'] = 'not a GID burn'
                    continue
                smooth = {e: _smoothed_change(got[e], e) for e in ('template', 'split')}
            except Exception as err:          # one bad burn must not stop the survey: recorded in the key
                entry['error'] = '%s: %s' % (type(err).__name__, err)
                rows.append(dict(burn=label, estimator='', quantity='', failed=type(err).__name__))
                continue
            t0 = got['template']
            base = dict(burn=label, frames=len(t0.x), duration_s=round(t0.duration()),
                        frame_rel_error=float(np.nanmean(t0.values['intensity'][1] / t0.values['intensity'][0])),
                        mean_frame_noise=mean_frame_noise(t0.profiles, t0.window), failed='')
            for e, r in got.items():
                fits = [d for d in r.frame_fits if d.get('ok')]
                extra = dict(frame_chi2_dof=float(np.mean([d['chi2_dof'] for d in fits])) if fits else math.nan,
                             frames_failed=len(r.frame_fits) - len(fits))
                ref = r.reference
                if e != 'template':
                    found = ref.get('shoulder') is not None
                    extra['shoulder_found'] = found
                    if found:
                        b = np.array([d['shoulder'][0] for d in fits])
                        extra.update(shoulder_to_peak_area=ref['shoulder_area'] / ref['peak_area'],
                                     shoulder_to_peak_fwhm=2.3548 * ref['shoulder'][2] / ref['peak_fwhm'],
                                     b_mean=float(np.mean(b)), b_min=float(np.min(b)), b_max=float(np.max(b)))
                for q, c in r.trends.items():
                    v, sv = change_of(c.fits.get('linear'), r.duration(), relative=q != 'centre')
                    row = dict(base, estimator=e, quantity=q, change=v, sigma=sv,
                               verdict='stable' if c.stable else 'changing', best=c.best, **extra)
                    if q == 'intensity' and e in smooth:
                        v2, s2, st2 = smooth[e]['spline']
                        row.update(smoothed_change=v2, smoothed_sigma=s2,
                                   smoothed_verdict='stable' if st2 else 'changing')
                    rows.append(row)
    _write(os.path.join(out, 'real.csv'), rows)
    _write(os.path.join(out, 'real_key.csv'), key)
    return rows, key


def _reference_replicates(job):
    case, monitor, seeds = job
    T = FRAMES * CTIME
    got = []
    for seed in seeds:
        prof, tr = bp.profiles(n=FRAMES, ctime=CTIME, monitor=monitor, seed=3000 + seed, **CASES[case])
        clean, _ = bp.profiles(n=FRAMES, ctime=CTIME, monitor=monitor, seed=None, **CASES[case])
        window = burn.measure_gid(clean, estimator='template')[2]       # one window for all: not the question
        x = prof[0][:, 0]
        mean = np.mean([q[:, 1] for q in prof], axis=0)
        err = np.sqrt(np.sum([q[:, 2] ** 2 for q in prof], axis=0)) / len(prof)
        refs = dict(mean=mean, spline=smooth_reference(x, mean, err, window),
                    truth=np.mean([q[:, 1] for q in clean], axis=0))
        truth = true_change(tr.t, tr.area, T)
        for e in ('template', 'split'):
            for k in REFERENCES:
                a, b = np.polyfit(tr.t, read_with_reference(prof, refs[k], window, e)[0], 1)
                got.append((e, k, a * T / b - truth))
    return (case, monitor), got


def reference_check(out, replicates=100, workers=None, monitors=REF_MONITORS, cases=REF_CASES, spec=None):
    """Part R: is a bias at low counts the reference's noise? Each frame
    measured against the frames' mean (the reader), the mean smoothed
    (``smooth_reference``) and the noiseless mean (the truth): the bias of
    the intensity change over the test (straight line through the frames),
    Gaussian shoulder; and, with ``spec``, NX burns 14 and 15 read against
    the mean and the smoothed mean (``reference_nx``). Writes
    reference_noise.csv, reference_nx.csv and S6; returns (rows, nx rows)."""
    jobs = [(c, m, list(range(lo, min(lo + 25, replicates)))) for c in cases for m in monitors
            for lo in range(0, replicates, 25)]
    pooled = {}
    if workers == 1:
        results = map(_reference_replicates, jobs)
    else:
        ex = ProcessPoolExecutor(max_workers=workers or min(4, os.cpu_count() or 1))
        results = ex.map(_reference_replicates, jobs)
    for key, got in results:
        pooled.setdefault(key, []).extend(got)
    if workers != 1:
        ex.shutdown()
    rows = []
    for (case, monitor), got in pooled.items():
        for e in ('template', 'split'):
            base = np.array([g[2] for g in got if g[0] == e and g[1] == 'mean'])
            for k in REFERENCES:
                b = np.array([g[2] for g in got if g[0] == e and g[1] == k])
                d = b - base                    # paired: the same burn read against this reference and the mean
                rows.append(dict(case=case, monitor=monitor, estimator=e, reference=k, n=len(b),
                                 bias=float(np.mean(b)), se=float(np.std(b) / math.sqrt(len(b))),
                                 sd=float(np.std(b)), shift=float(np.mean(d)), shift_sd=float(np.std(d))))
    _write(os.path.join(out, 'reference_noise.csv'), rows)
    nx = reference_nx(spec) if spec and os.path.exists(spec) else []
    if nx:
        _write(os.path.join(out, 'reference_nx.csv'), nx)
    s6(rows, out, nx)
    return rows, nx


def s6(rows, out, nx=()):
    import matplotlib.pyplot as plt
    cases = sorted({r['case'] for r in rows}, key=list(REF_CASES).index)
    n = len(cases) + (1 if nx else 0)
    fig, axes = plt.subplots(1, n, figsize=(5.0 * n, 3.8), squeeze=False)
    styles = {'mean': ('-', 'o', 'the frames\' mean (the reader)'), 'spline': ('--', 's', 'the mean, smoothed'),
              'truth': (':', '^', 'the noiseless mean')}
    for ax, case in zip(axes[0], cases):
        for e in ('template', 'split'):
            for k in REFERENCES:
                got = sorted((r['monitor'], r['bias'], r['se']) for r in rows
                             if r['case'] == case and r['estimator'] == e and r['reference'] == k)
                if not got:
                    continue
                m, b, se = (np.array(v) for v in zip(*got))
                ls, mk, lab = styles[k]
                ax.errorbar(m, 100 * b, 100 * se, ls=ls, marker=mk, ms=4, color=COLOURS[e], capsize=2,
                            label='%s, %s' % (e, lab))
        for scan, m in NX_MONITORS.items():
            ax.axvline(m, color='0.6', lw=0.7, ls=':')
            ax.text(m, 0.98, ' NX %d' % scan, transform=ax.get_xaxis_transform(), fontsize=6, va='top', color='0.4')
        ax.axhline(0, color='k', lw=0.6)
        ax.set_xscale('log')
        ax.set_xlabel('monitor (counts ∝ monitor)', fontsize=8)
        ax.set_title(case, fontsize=9)
        ax.tick_params(labelsize=7)
    axes[0][0].set_ylabel('intensity change: read − true (% points), ±1 SE', fontsize=8)
    axes[0][len(cases) - 1].legend(fontsize=6, frameon=False)
    if nx:
        ax = axes[0][-1]
        for j, (scan, e, k) in enumerate((sc, e, k) for sc in (14, 15) for e in ('template', 'split')
                                         for k in ('mean', 'spline')):
            r = [x for x in nx if x['scan'] == scan and x['estimator'] == e and x['reference'] == k][0]
            ls, mk, _ = styles[k]
            ax.errorbar(j + (j // 4), 100 * r['change'], 100 * r['sigma'], marker=mk, ms=5, capsize=2,
                        color=COLOURS[e], mfc=COLOURS[e] if r['verdict'] == 'changing' else 'white', ls='')
        ax.axhline(0, color='k', lw=0.6)
        ax.set_xticks([1.5, 6.5])
        ax.set_xticklabels(['burn 14', 'burn 15'], fontsize=8)
        ax.set_ylabel('intensity change over the burn (%), ±1σ', fontsize=8)
        ax.set_title('NX school: circles the mean, squares smoothed; open "stable"', fontsize=8)
        ax.tick_params(labelsize=7)
    fig.suptitle('S6. The reference\'s noise: each frame measured against the mean, the smoothed mean, the '
                 'noiseless mean', fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'S6_reference.png'), dpi=120)
    plt.close(fig)


def nx_check(out, spec):
    """NX school burns 14 and 15 under every estimator: the change of each
    quantity over the burn, its σ and the verdict; the frames' mean χ²/dof;
    the split's shoulder. Writes nx.csv and S5; returns the rows."""
    import tempfile
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp())
    from lss_core.experiment import Experiment
    exp = Experiment(spec)
    rows = []
    for scan in (14, 15):
        for e in NX_ESTIMATORS:
            r = exp.burn(scan, estimator=e)
            T = r.duration()
            fits = [d for d in r.frame_fits if d.get('ok')]
            chi = float(np.mean([d['chi2_dof'] for d in fits])) if e != 'moments' else math.nan
            ref = r.reference
            i, si = r.values['intensity']
            rel = float(np.nanmean(si / i))           # a frame's intensity error (NX_MONITORS)
            for q, c in r.trends.items():
                v, s = change_of(c.fits.get('linear'), T, relative=q != 'centre')
                row = dict(scan=scan, estimator=e, quantity=q, change=v, sigma=s,
                           verdict='stable' if c.stable else 'changing', best=c.best, frame_chi2_dof=chi,
                           duration_s=T, window_lo=r.window[0], window_hi=r.window[1], frame_rel_error=rel)
                if e in burn.SPLIT_ESTIMATORS and ref.get('shoulder') is not None:
                    h, m, sg = ref['shoulder']
                    b = [d['shoulder'][0] for d in fits]
                    row.update(shoulder_height=h, shoulder_centre=m, shoulder_sigma=sg, peak_fwhm=ref['peak_fwhm'],
                               peak_centre=ref['peak_centre'], b_min=min(b), b_max=max(b))
                rows.append(row)
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[-1]).index(k) if k in rows[-1] else 99)
    with open(os.path.join(out, 'nx.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})
    s5(rows, out)
    return rows


def s5(rows, out):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, q, sc, unit in zip(axes, ('intensity', 'fwhm', 'centre'), (100, 100, 1e4),
                               ('%', '%', '10⁻⁴ Å⁻¹')):
        for i, scan in enumerate((14, 15)):
            for j, e in enumerate(NX_ESTIMATORS):
                r = [x for x in rows if x['scan'] == scan and x['estimator'] == e and x['quantity'] == q]
                if not r:
                    continue
                x = i * (len(NX_ESTIMATORS) + 1) + j
                ax.errorbar(x, sc * r[0]['change'], sc * r[0]['sigma'], fmt='o' if r[0]['verdict'] == 'changing'
                            else 's', mfc=COLOURS[e] if r[0]['verdict'] == 'changing' else 'white', color=COLOURS[e],
                            ms=5, capsize=2)
        ax.axhline(0, color='k', lw=0.6)
        n = len(NX_ESTIMATORS)
        ax.set_xticks([(n - 1) / 2, n + 1 + (n - 1) / 2])
        ax.set_xticklabels(['burn 14', 'burn 15 (×4.7 flux)'], fontsize=8)
        ax.set_ylabel('%s change over the burn (%s)' % (LABEL[q], unit), fontsize=8)
        ax.tick_params(labelsize=7)
    from matplotlib.lines import Line2D
    axes[0].legend(handles=[Line2D([], [], color=COLOURS[e], marker='o', ls='', label=e) for e in NX_ESTIMATORS],
                   fontsize=7, frameon=False)
    fig.suptitle('S5. NX school burns 14 and 15 under every estimator (±1σ; filled: "changing", open: "stable")',
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'S5_nx.png'), dpi=120)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--replicates', type=int, default=None, help='per cell (default 300; part R 100)')
    ap.add_argument('--parts', default='A,B', help='A (every shoulder shape), B (fewer counts), or both')
    ap.add_argument('--cases', default=None, help='comma-separated: %s' % ', '.join(CASES))
    ap.add_argument('--shapes', default=None, help='comma-separated: %s' % ', '.join(SHAPES))
    ap.add_argument('--workers', type=int, default=None, help='processes (default: up to 4)')
    ap.add_argument('--core', type=float, default=burn.SPLIT_CORE,
                    help='the split: the shoulder fitted beyond this many FWHM from the peak (default %g)'
                    % burn.SPLIT_CORE)
    ap.add_argument('--only', default=None, help='S5: the NX check only (no replicates); R: the reference\'s '
                    'noise (S6, about 6 min)')
    ap.add_argument('--spec', default=NX, help='the SPEC file of the real check (burns 14 and 15)')
    ap.add_argument('--real', nargs='+', default=None, help='SPEC files: the P44 questions on their GID burns '
                    '(real.csv, real_key.csv: the key is private; hand-off 10)')
    ap.add_argument('--scans', default=None, help='with --real and one file: these scans (comma-separated)')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    numbers = {}
    if a.real:
        real_check(a.out, a.real, a.scans and [int(v) for v in a.scans.split(',')])
        return 0
    if a.only:
        only = a.only.split(',')
        if 'R' in only:
            rows, nx = reference_check(a.out, a.replicates or 100, a.workers, spec=a.spec)
            with open(os.path.join(a.out, 'numbers_reference.json'), 'w', encoding='utf-8') as f:
                json.dump(dict(replicates=a.replicates or 100, monitors=REF_MONITORS, cases=REF_CASES,
                               rows=rows, nx=nx), f, indent=1, default=str)
        if 'S5' in only and os.path.exists(a.spec):
            numbers['nx'] = nx_check(a.out, a.spec)
            with open(os.path.join(a.out, 'numbers_only.json'), 'w', encoding='utf-8') as f:
                json.dump(numbers, f, indent=1, default=str)
        return 0
    parts = tuple(a.parts.split(','))
    rows = run(parts, a.replicates or 300, a.workers, a.cases and a.cases.split(','), a.shapes and a.shapes.split(','),
               a.core)
    _write(os.path.join(a.out, 'results.csv'), rows)
    for f in (s1, s2, s3, s4):
        f(rows, a.out)
    if os.path.exists(a.spec):
        numbers['nx'] = nx_check(a.out, a.spec)
    numbers['settings'] = dict(parts=list(parts), replicates=a.replicates or 300, cases=CASES, shapes=list(SHAPES),
                               part_b=PART_B, monitor=MONITOR, frames=FRAMES, ctime=CTIME, core=a.core)
    numbers['results'] = rows
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(numbers, f, indent=1, default=str)
    for r in rows:
        if r['quantity'] == 'intensity':
            print('%s %-14s %-10s %7.0e %-11s truth %+.3f bias %+.4f sd %.4f pull %.2f cov95 %.2f chg %.2f right %.2f'
                  % (r['part'], r['case'], r['shape'], r['monitor'], r['estimator'], r['truth'], r['bias'], r['sd'],
                     r['pull_sd'], r['cover95'], r['changing'], r['right']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
