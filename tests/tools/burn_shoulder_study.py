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
shoulder. Stretched estimator (the default) fits each frame as the mean
frame's whole shape, shifted and stretched; the shoulder is stretched with
the peak, so a broadening peak reads as a gain in intensity (P44). The
separated estimators (``separated``: the shoulder's amplitude free per frame;
``separated_held``: held at 1) take the shoulder out of the stretch. Which
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
- ``nx15_like``: FWHM × (1 + 0.2 f) and area × (1 − 0.13 f), as separated
  reads NX burn 15.

Part A: every case on every shoulder shape ('gaussian', 'lorentzian',
'asymmetric', 'two'), at high counts (monitor 1e7: a frame's intensity
known to 0.19 %, so that what remains is bias, not noise). Part B: the
Gaussian shoulder at fewer counts, cases none, fade, broaden and
nx15_like: monitor 1e6 (0.6 % per frame), 6e4 (2.1 %, as NX 15: 2.0 %)
and 1e4 (3.9 %, as NX 14: 3.8 %; ``NX_MONITORS``, each frame's stretched
intensity error matched, measured 2026-11-27).

Each replicate: every estimator, then the reader's own trend analysis
(``burn.analyse``, errors from the scatter, the GID default). Per
quantity: the change over the test read from its linear model (relative
for intensity, FWHM and separated's shoulder; Å⁻¹ for the position), its
σ, and the verdict (stable or changing: a line beats a constant by AICc).
Per cell: the bias and SD of the change, the pull SD ((read − truth)/σ:
1 means honest errors), the coverage of ±1σ and ±1.96σ, the share
called changing and the share called right.

Stretched estimator's 'fit' sibling (one Gaussian per frame) is left
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
ESTIMATORS = ('stretched', 'moments', 'separated', 'separated_held')
NX_ESTIMATORS = ('stretched', 'moments', 'fit', 'separated', 'separated_held')
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
# the monitor at which a synthetic frame's stretched intensity has the error of an NX school frame
# (3.8 % on burn 14, 2.0 % on 15; synthetic 3.9 % and 2.1 %): tests/test_burn_shoulder_study.py
NX_MONITORS = {14: 1e4, 15: 6e4}
MONITOR = 1e7
FRAMES, CTIME = 21, 10.0
EN = burn.ESTIMATOR_NAMES
KEY = ('stretched = shoulder stretched with the peak (the reader\'s default); separated = shoulder '
       'separated; separated & held = shoulder separated, its amplitude held')
COLOURS = {'stretched': 'C0', 'moments': 'C7', 'fit': 'C5', 'separated': 'C3', 'separated_held': 'C1'}
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
    """{estimator: {quantity: (change, σ, stable)}} and separated's shoulder (or None)."""
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
        if e in burn.SEPARATED_ESTIMATORS:
            extra[e] = ref.get('shoulder')
    return out, extra


def _replicates(job):
    """One cell's seeds: a list of (seed, truths, reads, found shoulder)."""
    case, shape, monitor, seeds, core = job
    T = FRAMES * CTIME
    rows = []
    before, burn.SEPARATE_CORE = burn.SEPARATE_CORE, core          # ``--core``; set back after
    try:
        for seed in seeds:
            prof, tr = bp.profiles(n=FRAMES, ctime=CTIME, monitor=monitor, seed=seed, shoulder_shape=shape,
                                   **CASES[case])
            reads, extra = read_all(prof, tr.t, T)
            rows.append((seed, truths(tr, T), reads, {k: v is not None for k, v in extra.items()}))
    finally:
        burn.SEPARATE_CORE = before
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
            got = [g for g in got if not (q == 'shoulder' and e != 'separated')]
            if not got or all(math.isnan(g[1]) for g in got):
                continue
            truth = got[0][0]
            v = np.array([g[1] for g in got])
            s = np.array([g[2] for g in got])
            ok = np.isfinite(v) & np.isfinite(s) & (s > 0)
            pull = (v[ok] - truth) / s[ok]
            changing = np.array([g[3] is False for g in got])[ok]
            moves = abs(truth) > 1e-9
            found = [r[3].get(e, True) for r in reps] if e in burn.SEPARATED_ESTIMATORS else [True]
            rows.append(dict(part='A' if monitor == MONITOR else 'B', case=case, shape=shape, monitor=monitor,
                             estimator=e, quantity=q, truth=truth, n=int(np.sum(ok)), failed=int(np.sum(~ok)),
                             mean=float(np.mean(v[ok])), bias=float(np.mean(v[ok]) - truth), sd=float(np.std(v[ok])),
                             rmse=float(np.sqrt(np.mean((v[ok] - truth) ** 2))),
                             pull_mean=float(np.mean(pull)), pull_sd=float(np.std(pull)),
                             cover68=float(np.mean(np.abs(pull) < 1)), cover95=float(np.mean(np.abs(pull) < 1.96)),
                             changing=float(np.mean(changing)), right=float(np.mean(changing == moves)),
                             shoulder_found=float(np.mean(found))))
    return rows


def run(parts=('A', 'B'), replicates=300, workers=None, cases=None, shapes=None, core=burn.SEPARATE_CORE):
    """``core``: separated's core half-width in FWHM (burn.SEPARATE_CORE, 1.5)."""
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
        ax.bar(xs, ys, 0.8 / n, yerr=es, color=COLOURS[e], label=EN.get(e, e), error_kw=dict(lw=0.7, capsize=1.5))
    ax.axhline(0, color='k', lw=0.6)
    ax.set_xticks(range(len(cases)))
    ax.set_xticklabels(cases, fontsize=7, rotation=25, ha='right')
    ax.tick_params(axis='y', labelsize=7)


def _key(fig):
    """The estimators' names, spelled out under a figure (owner, 2026-11-27: the names must be clear)."""
    fig.text(0.01, -0.005, KEY, fontsize=7, va='top', color='0.25')


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
    _key(fig)
    fig.savefig(os.path.join(out, 'S1_bias_by_case.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)


def s2(rows, out):
    """The intensity change's bias on each shoulder shape."""
    import matplotlib.pyplot as plt
    cases = ['fade', 'broaden', 'shoulder', 'shoulder_grows', 'both_fade', 'nx15_like']
    ncol = 2
    fig, axes = plt.subplots((len(SHAPES) + 1) // ncol, ncol, figsize=(10, 6.2 * ((len(SHAPES) + 1) // ncol)),
                             sharey=True, squeeze=False)
    axes = axes.ravel()
    for ax, sh in zip(axes, SHAPES):
        _bars(ax, cases, rows, 'intensity', shape=sh, scale=100)
        ax.set_title(sh, fontsize=9)
    for ax in axes[::ncol]:
        ax.set_ylabel('intensity change:\nread − true (% points)', fontsize=8)
    axes[0].legend(fontsize=7, frameon=False, loc='upper left')
    fig.suptitle('S2. The intensity\'s error on each shoulder shape (bars: bias, whiskers: SD)', fontsize=9)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'S2_bias_by_shape.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)


def s3(rows, out):
    """Share called 'changing' and the 95 % coverage, on the intensity (Gaussian shoulder)."""
    import matplotlib.pyplot as plt
    cases = list(CASES)
    fig, axes = plt.subplots(2, 1, figsize=(9, 8))
    n = len(ESTIMATORS)
    for j, e in enumerate(ESTIMATORS):
        for ax, key in zip(axes, ('changing', 'cover95')):
            xs, ys = [], []
            for i, c in enumerate(cases):
                r = _pick(rows, case=c, shape='gaussian', monitor=MONITOR, estimator=e, quantity='intensity')
                if r:
                    xs.append(i + (j - (n - 1) / 2) * 0.8 / n)
                    ys.append(r[0][key])
            ax.bar(xs, ys, 0.8 / n, color=COLOURS[e], label=EN.get(e, e))
    for i, c in enumerate(cases):
        r = _pick(rows, case=c, shape='gaussian', monitor=MONITOR, estimator='stretched', quantity='intensity')
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
    fig.suptitle('S3. The intensity: verdicts (top) and whether the 95 % interval holds the truth (bottom), '
                 'Gaussian shoulder', fontsize=9)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'S3_verdicts_coverage.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)


def s4(rows, out):
    """Fewer counts: SD and pull SD of the intensity change against the monitor (Gaussian)."""
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(8, 10.5), sharex=True)
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
                         label='%s, %s' % (EN.get(e, e), c))
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
    _key(fig)
    fig.savefig(os.path.join(out, 'S4_counts.png'), dpi=120, bbox_inches='tight')
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
    ('stretched' or 'separated'), but measured against ``ref_mean`` instead of
    the frames' own mean. With the frames' mean it gives measure_gid's
    numbers exactly (tested): with ``qxy_range=window``, or with the window
    and ``found`` (the peak ``choose_window`` found: separated's starting
    centre and FWHM) that measure_gid chose itself."""
    x = profiles[0][:, 0]
    sel = (x >= window[0]) & (x <= window[1])
    xw = x[sel]
    step = float(np.median(np.abs(np.diff(xw))))
    shape = ref_mean[sel] - burn._baseline(xw, ref_mean[sel])
    c_ref = float(np.sum(shape * xw) / np.sum(shape))
    if estimator == 'separated':
        c0, w0 = (found['centre'], found['fwhm']) if found else (float(xw[np.argmax(shape)]),
                                                                 burn._half_width(xw, shape))
        S, P, sp = burn.separate_shoulder(xw, shape, c0, w0, burn.SEPARATE_CORE)
        S = None if sp is None else S
        mt, c, area = P, float(np.sum(P * xw) / np.sum(P)), float(np.sum(P) * step)
    else:
        S, mt, c, area = None, shape, c_ref, float(np.sum(shape) * step)
    out, err = [], []
    for prof in profiles:
        y, e = prof[sel, 1], prof[sel, 2]
        e = np.where(e > 0, e, np.nan)
        e = np.where(np.isfinite(e), e, np.nanmax(e) if np.any(np.isfinite(e)) else 1.0)
        try:
            p, pe, _, cov = burn._stretch_fit(xw, y, e, xw, mt, c, S, extra_free=True)
        except (RuntimeError, ValueError):        # as measure_gid: a frame that will not fit is NaN, not the end
            out.append(math.nan)
            err.append(math.nan)
            continue
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
    """NX school burns 14 and 15, stretched and separated, each frame measured
    against the frames' mean (the reader's numbers) and against the mean
    smoothed; the intensity change through the reader's trend analysis
    (errors from the scatter), as section 5."""
    import tempfile
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp())
    from lss_core.experiment import Experiment
    exp = Experiment(spec)
    rows = []
    for scan in (14, 15):
        for e in ('stretched', 'separated'):
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


REAL_ESTIMATORS = ('stretched', 'separated', 'separated_held')


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
    (or ``scans`` of a single file) under stretched, separated and the
    separated with the shoulder fixed, and stretched and separated re-read
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
                if got['stretched'].kind != 'gid':
                    entry['error'] = 'not a GID burn'
                    continue
                smooth = {e: _smoothed_change(got[e], e) for e in ('stretched', 'separated')}
            except Exception as err:          # one bad burn must not stop the survey: recorded in the key
                entry['error'] = '%s: %s' % (type(err).__name__, err)
                rows.append(dict(burn=label, estimator='', quantity='', failed=type(err).__name__))
                continue
            t0 = got['stretched']
            base = dict(burn=label, frames=len(t0.x), duration_s=round(t0.duration()),
                        frame_rel_error=float(np.nanmean(t0.values['intensity'][1] / t0.values['intensity'][0])),
                        mean_frame_noise=mean_frame_noise(t0.profiles, t0.window),
                        first_frame_ratio=first_frame_ratio(t0.values['intensity'][0]), failed='')
            for e, r in got.items():
                fits = [d for d in r.frame_fits if d.get('ok')]
                extra = dict(frame_chi2_dof=float(np.mean([d['chi2_dof'] for d in fits])) if fits else math.nan,
                             frames_failed=len(r.frame_fits) - len(fits))
                ref = r.reference
                if e != 'stretched':
                    found = ref.get('shoulder') is not None
                    extra['shoulder_found'] = found
                    extra['shoulder_refused'] = ref.get('shoulder_refused') or ''     # #187: why a fit is no shoulder
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


REAL_CSV = 'docs/studies/xr_burns/gid_split.csv'
# the synthetic NX 15-like burns' mean-frame noise per monitor (mean_frame_noise's docstring, measured)
REF_NOISE = {1e7: 0.0003, 6e4: 0.0035, 1e4: 0.0085}


FIRST_FRAME_MIN = 0.8      # owner, 2026-11-27: burns whose first frame is weaker than the rest are left out


def first_frame_ratio(intensity):
    """A burn's first frame over the median of its next three (stretched intensities): about 1 when the
    first frame is like the rest; well below 1 when it is anomalously weak."""
    y = np.asarray(intensity, float)
    if len(y) < 4:
        return math.nan
    ref = np.nanmedian(y[1:4])
    return float(y[0] / ref) if ref > 0 else math.nan


def well_measured(by):
    """The real burns of ``by`` ({burn: {estimator: {quantity: row}}}, from
    real.csv) that are well measured (hand-off 10, summary section 8): the
    intensity change finite under all three estimators, one frame's
    intensity error at most 10 %, stretched's intensity change within
    ±50 % over the burn (a larger one: the peak comes or goes), the
    stretched's frames' χ²/dof at most 5, and (owner, 2026-11-27) a first
    frame not weaker than FIRST_FRAME_MIN of the next three."""
    def f(v):
        return float(v) if v not in (None, '') else math.nan
    out = []
    for b, d in sorted(by.items()):
        if not all(e in d and 'intensity' in d[e] for e in REAL_ESTIMATORS):
            continue
        t = d['stretched']['intensity']
        if (all(np.isfinite(f(d[e]['intensity']['change'])) for e in REAL_ESTIMATORS)
                and f(t['frame_rel_error']) <= 0.10 and abs(f(t['change'])) <= 0.5 and f(t['frame_chi2_dof']) <= 5
                and not f(t.get('first_frame_ratio')) < FIRST_FRAME_MIN):
            out.append(b)
    return out


def real_figures(out, csv_path=REAL_CSV, ref_csv=None, public=('G01', 'G02')):
    """Figures R1 and R2 of section 8 from the published per-burn summary
    (``csv_path``: real.csv as published, no frame of a private burn):
    R1 the intensity change under separated against stretched's, one
    point per well-measured burn; R2 the shift when the mean frame is
    smoothed against the mean frame's noise, with the synthetic NX 15-like
    expectation (``ref_csv``: reference_noise.csv). ``public``: the NX school
    burns 14 and 15 (G01, G02), drawn apart. Returns the counts drawn."""
    import csv as csvmod
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows = list(csvmod.DictReader(open(csv_path, encoding='utf-8')))
    by, failed = {}, set()
    for r in rows:
        if r.get('failed'):
            failed.add(r['burn'])
            continue
        by.setdefault(r['burn'], {}).setdefault(r['estimator'], {})[r['quantity']] = r
    f = lambda v: float(v) if v not in (None, '') else math.nan          # noqa: E731
    good = [b for b in well_measured(by) if b not in public]
    nx = [b for b in public if b in by]
    private_read = [b for b in by if b not in public]
    fig, ax = plt.subplots(figsize=(7.4, 8.6))
    lim = 0.0
    counts = dict(well_measured=len(good), read=len(private_read), failed=len(failed), wide=0, differ=0)
    for b in good + nx:
        t, s = by[b]['stretched'], by[b]['separated']
        x, y = 100 * f(t['intensity']['change']), 100 * f(s['intensity']['change'])
        ex, ey = 100 * f(t['intensity']['sigma']), 100 * f(s['intensity']['sigma'])
        wide = abs(f(t['fwhm']['change'])) >= 0.10
        differ = t['intensity']['verdict'] != s['intensity']['verdict']
        if b in nx:
            ax.errorbar(x, y, ey, ex, fmt='s', color='k', ms=7, capsize=2, zorder=5)
            ax.annotate('NX %s' % ('14' if b == public[0] else '15'), (x, y), xytext=(6, -12), textcoords='offset points')
        else:
            counts['wide'] += wide
            counts['differ'] += differ
            ax.errorbar(x, y, ey, ex, fmt='o', ms=5, capsize=0, lw=0.6,
                        color='tab:red' if wide else 'tab:blue', mfc='none' if differ else None, alpha=0.8)
        lim = max(lim, abs(x) + ex, abs(y) + ey)
    lim = min(1.05 * lim, 60)
    ax.plot([-lim, lim], [-lim, lim], color='0.5', lw=0.8)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel('shoulder stretched with the peak: intensity change over the burn (%)')
    ax.set_ylabel('shoulder separated: intensity change over the burn (%)')
    ax.set_title('R1. Private GID burns: separated against stretched (one point per burn, ±1σ)', fontsize=10)
    ax.text(0.02, 0.98, 'blue: FWHM change < 10 %% (stretched)   red: FWHM change ≥ 10 %%\n'
            'open: the two verdicts differ (stable / changing)   grey line: equal\n'
            'shown: %d well-measured private burns (%d red, %d open), NX 14 and 15 (black)\n'
            'NOT SHOWN: %d private burns read but not well measured (section 8), %d not read'
            % (counts['well_measured'], counts['wide'], counts['differ'],
               len(private_read) - len(good), len(failed)),
            transform=ax.transAxes, va='top', fontsize=7.5)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'R1_stretched_vs_separated.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)

    ref = []
    if ref_csv and os.path.exists(ref_csv):
        ref = [r for r in csvmod.DictReader(open(ref_csv, encoding='utf-8')) if r['reference'] == 'spline']
    fig, axes = plt.subplots(2, 1, figsize=(8, 10), sharex=True)
    for ax, e in zip(axes, ('stretched', 'separated')):
        for b in good:
            r = by[b][e]['intensity']
            sh = 100 * (f(r['smoothed_change']) - f(r['change']))
            nz = 100 * f(r['mean_frame_noise'])
            broad = f(by[b][e]['fwhm']['change']) >= 0.05
            ax.plot(nz, sh, 'o', ms=4, color='tab:red' if broad else 'tab:blue', alpha=0.7)
        for b in nx:
            r = by[b][e]['intensity']
            ax.plot(100 * f(r['mean_frame_noise']), 100 * (f(r['smoothed_change']) - f(r['change'])), 's', color='k', ms=7)
        for case, col in (('nx15_like', 'tab:orange'), ('fade', 'tab:green')):
            pts = sorted((REF_NOISE[float(r['monitor'])] * 100, 100 * float(r['shift']), 100 * float(r['shift_sd']))
                         for r in ref if r['case'] == case and r['estimator'] == e and float(r['monitor']) in REF_NOISE)
            if pts:
                ax.errorbar([p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts], fmt='D-', color=col, ms=6,
                            capsize=3, label='synthetic %s (±SD of the shift)' % ('NX 15-like, FWHM +20 %' if case == 'nx15_like'
                                                                                 else 'fade, FWHM steady'))
        ax.axhline(0, color='0.5', lw=0.8)
        ax.set_xscale('log')
        ax.set_xlabel('mean frame\'s noise, share of its peak (%)')
        ax.set_title(EN[e], fontsize=10)
        ax.set_ylim(-12, 12)
        ax.legend(fontsize=7, loc='lower left')
    for ax in axes:
        ax.set_ylabel('smoothed − mean: intensity change (pp)')
    fig.suptitle('R2. Does the reference\'s noise matter? Real burns (blue: FWHM steady, red: broadening ≥ 5 %%; '
                 'black: NX 14, 15), %d well-measured private burns; y clipped at ±12 pp' % len(good), fontsize=9)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'R2_reference_shift.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)
    return counts


CODES = {'dose': 'D', 'time': 'T', 'neither': 'N', 'no change': '0', 'opposite signs': '±', 'cannot tell': '?'}
SERIES_CSV = 'docs/studies/xr_burns/gid_split_series.csv'
RATES_CSV = 'docs/studies/xr_burns/gid_split_series_rates.csv'


def _real_by(csv_path):
    import csv as csvmod
    by, failed = {}, set()
    for r in csvmod.DictReader(open(csv_path, encoding='utf-8')):
        if r.get('failed'):
            failed.add(r['burn'])
            continue
        by.setdefault(r['burn'], {}).setdefault(r['estimator'], {})[r['quantity']] = r
    return by, failed


def _fl(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def explain_figures(out, csv_path=REAL_CSV, series_csv=SERIES_CSV, rates_csv=RATES_CSV, public=('G01', 'G02')):
    """The figures that explain section 8's numbers (R3-R7), from the
    published summaries alone: R3 which burns were read and what the
    well-measured cut removes; R4 how question 1's disagreement is measured;
    R5 question 2's three signs of a changing shoulder; R6 question 3's
    χ²/dof and shoulder shapes; R7 question 5's dose-or-time fit, one series
    and all of them. Returns the counts each figure states."""
    import csv as csvmod
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    f = _fl
    by, failed = _real_by(csv_path)
    priv = sorted(b for b in by if b not in public)
    good = [b for b in well_measured(by) if b not in public]
    nx = [b for b in public if b in by]
    I = lambda b, e, c='change': f(by[b][e]['intensity'][c])          # noqa: E731
    counts = {}

    # R3: the selection
    fig, ax = plt.subplots(3, 2, figsize=(10, 16))
    ax = ax.ravel()
    stages = [('GID burns found', len(by) + len(failed)), ('public NX 14, 15 (a check)', len(nx)),
              ('not read (no frames, too few, no peak)', len(failed)), ('private, read', len(priv)),
              ('well measured', len(good))]
    ax[0].barh(range(len(stages))[::-1], [s[1] for s in stages], color=['0.6', 'k', 'tab:grey', 'tab:blue', 'tab:green'])
    for i, (lab, n) in enumerate(stages):
        ax[0].text(n + 3, len(stages) - 1 - i, '%d  %s' % (n, lab), va='center', fontsize=8)
    ax[0].set_xlim(0, 1.9 * stages[0][1])
    ax[0].set_yticks([])
    ax[0].set_xlabel('burns')
    ax[0].set_title('a. what was read', fontsize=9)
    cuts = [('frame_rel_error', 'one frame\'s intensity error', 0.10, True, lambda b: I(b, 'stretched', 'frame_rel_error')),
            ('change', '|stretched intensity change| over the burn', 0.5, True, lambda b: abs(I(b, 'stretched'))),
            ('chi2', 'stretched: the frames\' χ²/dof', 5.0, True, lambda b: I(b, 'stretched', 'frame_chi2_dof'))]
    for k, (name, lab, thr, log, val) in enumerate(cuts):
        a = ax[k + 1]
        v = np.array([val(b) for b in priv])
        g = np.isfinite(v) & (v > 0)
        top = 100 * thr
        bins = np.logspace(np.log10(max(v[g].min(), 1e-4)), np.log10(top), 30)
        a.hist(np.clip(v[g], None, top * 0.999), bins, color='tab:blue', alpha=0.8)
        a.axvline(thr, color='tab:red', lw=1.5)
        a.set_xscale('log')
        n_out = int(np.sum(g & (v > thr)))
        counts['cut_' + name] = n_out
        a.set_title('%s. %s' % ('bcd'[k], lab), fontsize=9)
        a.text(0.98, 0.95, 'kept ≤ %g\nremoved: %d\noff scale: %d (last bin)'
               % (thr, n_out, int(np.sum(g & (v >= top)))), transform=a.transAxes, ha='right', va='top', fontsize=7.5,
               color='tab:red', bbox=dict(fc='w', ec='none', alpha=0.8))
        a.set_ylabel('private burns read')
        a.set_xlabel(lab)
    a = ax[4]                                   # owner, 2026-11-27: a first frame weaker than the rest is left out
    v = np.array([I(b, 'stretched', 'first_frame_ratio') for b in priv])
    g = np.isfinite(v)
    a.hist(np.clip(v[g], 0.4, 1.6), np.linspace(0.4, 1.6, 49), color='tab:blue', alpha=0.8)
    a.axvline(FIRST_FRAME_MIN, color='tab:red', lw=1.5)
    n_out = int(np.sum(g & (v < FIRST_FRAME_MIN)))
    counts['cut_first_frame'] = n_out
    a.set_title('e. the first frame ÷ the median of the next three', fontsize=9)
    a.text(0.98, 0.95, 'kept ≥ %g\nremoved: %d\n(clipped to 0.4–1.6)' % (FIRST_FRAME_MIN, n_out), transform=a.transAxes,
           ha='right', va='top', fontsize=7.5, color='tab:red', bbox=dict(fc='w', ec='none', alpha=0.8))
    a.set_ylabel('private burns read')
    a.set_xlabel('first frame ÷ next three (stretched intensity)')
    ax[5].axis('off')
    nan_out = sum(1 for b in priv if not all(np.isfinite(I(b, e)) for e in REAL_ESTIMATORS))
    counts['cut_nan'] = nan_out
    fig.suptitle('R3. From the burns found to the well-measured ones (%d private burns read; a burn can fail several '
                 'cuts; %d more have no finite change under some estimator)' % (len(priv), nan_out), fontsize=9)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'R3_selection.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)

    # R4: question 1
    z, dv, wch, diff, shc = [], [], [], [], []
    tab = np.zeros((2, 2), int)
    for b in good:
        t, s = by[b]['stretched']['intensity'], by[b]['separated']['intensity']
        zz = abs(f(t['change']) - f(s['change'])) / max(f(t['sigma']), 1.25 * f(s['sigma']))
        z.append(zz)
        tab[int(t['verdict'] == 'changing'), int(s['verdict'] == 'changing')] += 1
        wch.append(100 * f(by[b]['stretched']['fwhm']['change']))
        diff.append(100 * (f(s['change']) - f(t['change'])))
        shc.append('shoulder' in by[b]['separated'] and by[b]['separated']['shoulder']['verdict'] == 'changing')
    z = np.array(z)
    fig, ax = plt.subplots(3, 1, figsize=(8.5, 14))
    zero = z < 1e-9
    bins = np.logspace(-3, np.log10(max(z.max(), 10)), 30)
    ax[0].hist(z[~zero], bins, color='tab:blue')
    ax[0].axvline(2, color='tab:red')
    ax[0].set_xscale('log')
    ax[0].set_xlabel('z = |separated change − stretched change| / max(σ_stretched, 1.25 σ_separated)')
    ax[0].set_ylabel('burns')
    ax[0].set_title('a. how far apart the two reads are, in σ', fontsize=9)
    ax[0].text(0.02, 0.95, 'z > 2 (red line): %d of %d burns\nmedian z %.2f\nnot drawn: %d with z = 0 (no shoulder found:\n'
               'separated then equals stretched)' % (int(np.sum(z > 2)), len(z), np.median(z), int(zero.sum())),
               transform=ax[0].transAxes, va='top', fontsize=8)
    ax[1].imshow(tab, cmap='Blues')
    for i in range(2):
        for j in range(2):
            ax[1].text(j, i, str(tab[i, j]), ha='center', va='center', fontsize=14,
                       color='w' if tab[i, j] > tab.max() / 2 else 'k')
    ax[1].set_xticks([0, 1], ['separated:\nstable', 'separated:\nchanging'])
    ax[1].set_yticks([0, 1], ['stretched:\nstable', 'stretched:\nchanging'])
    ax[1].set_title('b. the intensity verdicts (off-diagonal: they differ, %d)' % (tab[0, 1] + tab[1, 0]), fontsize=9)
    wch, diff, shc = np.array(wch), np.array(diff), np.array(shc)
    ax[2].plot(wch[~shc], diff[~shc], 'o', ms=4, color='tab:blue', label='shoulder steady (separated)')
    ax[2].plot(wch[shc], diff[shc], 'o', ms=4, color='tab:orange', label='shoulder changing (separated)')
    for b in nx:
        ax[2].plot(100 * f(by[b]['stretched']['fwhm']['change']), 100 * (I(b, 'separated') - I(b, 'stretched')), 's', color='k', ms=7)
        ax[2].annotate('NX %s' % ('14' if b == public[0] else '15'), (100 * f(by[b]['stretched']['fwhm']['change']),
                       100 * (I(b, 'separated') - I(b, 'stretched'))), xytext=(5, 4), textcoords='offset points', fontsize=8)
    ax[2].axhline(0, color='0.5', lw=0.8)
    ax[2].axvline(0, color='0.5', lw=0.8)
    ax[2].set_xlim(-30, 30)
    ax[2].set_ylim(-30, 30)
    ax[2].set_xlabel('stretched: FWHM change over the burn (%)')
    ax[2].set_ylabel('separated − stretched:\nintensity change (pp)')
    ax[2].set_title('c. P44\'s mechanism needs a width change; real widths barely move', fontsize=9)
    ax[2].legend(fontsize=7, loc='lower left')
    out_of = int(np.sum((np.abs(wch) > 30) | (np.abs(diff) > 30)))
    ax[2].text(0.98, 0.02, '%d burns beyond ±30 not drawn' % out_of, transform=ax[2].transAxes, ha='right', fontsize=7)
    ax[2].text(0.98, 0.98, 'P44 predicts: a broadening peak (right)\nputs separated below stretched (lower right)',
               transform=ax[2].transAxes, ha='right', va='top', fontsize=7)
    fig.suptitle('R4. Question 1: when do stretched and separated disagree? (%d well-measured private burns)' % len(good),
                 fontsize=9)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'R4_q1_disagreement.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)
    counts.update(q1_z_over_2=int(np.sum(z > 2)), q1_verdicts_differ=int(tab[0, 1] + tab[1, 0]))

    # R5: question 2
    fig, ax = plt.subplots(figsize=(7.6, 8.4))
    n3 = 0
    nsh = 0
    for b in good + nx:
        d = by[b]['separated']
        if 'shoulder' not in d or d['intensity'].get('shoulder_found') != 'True':
            continue
        r, i, x = d['shoulder'], d['intensity'], by[b]['separated_held']['intensity']
        sc = 100 * f(r['change'])
        bdir = 100 * ((f(i['b_max']) - 1) if f(r['change']) > 0 else (1 - f(i['b_min'])))
        dis = abs(f(i['change']) - f(x['change'])) > math.hypot(f(i['sigma']), f(x['sigma']))
        ch = r['verdict'] == 'changing'
        if b in nx:
            ax.plot(sc, bdir, 's', color='k', ms=8)
            ax.annotate('NX %s' % ('14' if b == public[0] else '15'), (sc, bdir), xytext=(5, 3), textcoords='offset points',
                        fontsize=8)
            continue
        nsh += 1
        three = ch and dis and bdir > 5
        n3 += three
        ax.plot(sc, bdir, 'o', ms=5, color='tab:orange' if dis else 'tab:blue', mfc=None if ch else 'none')
    ax.axhline(5, color='tab:red', lw=0.8, ls='--')
    ax.set_xlim(-60, 60)
    ax.set_ylim(-5, 120)
    ax.set_xlabel('separated: the shoulder\'s own change over the burn (%)')
    ax.set_ylabel('B (shoulder amplitude per frame): how far it moves\nfrom 1 in the shoulder\'s direction (%)')
    ax.set_title('R5. Question 2: is a real shoulder changing? three signs', fontsize=10)
    ax.text(0.02, 0.98, 'sign 1, filled: separated calls the shoulder "changing" (open: stable)\n'
            'sign 2, above the red line: B moves the same way by more than 5 %%\n'
            'sign 3, orange: separated and separated & held disagree on the intensity by more than their σ\n'
            'all three: %d of %d well-measured burns with a shoulder; NX 14, 15 black' % (n3, nsh),
            transform=ax.transAxes, va='top', fontsize=7.5)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'R5_q2_shoulder.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)
    counts.update(q2_three=n3, q2_with_shoulder=nsh)

    # R6: question 3
    fig, ax = plt.subplots(2, 1, figsize=(7.6, 12))
    ct, cs, ar, fr = [], [], [], []
    for b in good:
        i = by[b]['separated']['intensity']
        if i.get('shoulder_found') != 'True':
            continue
        ct.append(I(b, 'stretched', 'frame_chi2_dof'))
        cs.append(I(b, 'separated', 'frame_chi2_dof'))
        ar.append(f(i['shoulder_to_peak_area']))
        fr.append(f(i['shoulder_to_peak_fwhm']))
    ct, cs = np.array(ct), np.array(cs)
    ax[0].loglog(ct, cs, 'o', ms=4, color='tab:blue')
    for b in nx:
        ax[0].loglog(I(b, 'stretched', 'frame_chi2_dof'), I(b, 'separated', 'frame_chi2_dof'), 's', color='k', ms=7)
        ax[0].annotate('NX %s' % ('14' if b == public[0] else '15'), (I(b, 'stretched', 'frame_chi2_dof'),
                       I(b, 'separated', 'frame_chi2_dof')), xytext=(5, -10), textcoords='offset points', fontsize=8)
    lo, hi = 0.5, 6
    xx = np.array([lo, hi])
    ax[0].plot(xx, xx, color='0.4', lw=0.8)
    ax[0].plot(xx, 0.9 * xx, color='0.4', lw=0.6, ls=':')
    ax[0].plot(xx, 1.1 * xx, color='0.4', lw=0.6, ls=':')
    ax[0].set_xlim(lo, hi)
    ax[0].set_ylim(lo, hi)
    ax[0].set_xlabel('stretched: the frames\' mean χ²/dof')
    ax[0].set_ylabel('separated: the frames\' mean χ²/dof')
    ax[0].set_title('a. χ²/dof ≈ 1: the model describes the frames to counting noise', fontsize=9)
    ax[0].text(0.02, 0.98, 'solid: equal; dotted: ±10 %%\nsplit lower: %d of %d; >10 %% lower: %d, >10 %% higher: %d'
               % (int(np.sum(cs < ct)), len(ct), int(np.sum(cs < 0.9 * ct)), int(np.sum(cs > 1.1 * ct))),
               transform=ax[0].transAxes, va='top', fontsize=8)
    ax[1].loglog(fr, ar, 'o', ms=4, color='tab:blue', label='private burns')
    for b in nx:
        i = by[b]['separated']['intensity']
        ax[1].loglog(f(i['shoulder_to_peak_fwhm']), f(i['shoulder_to_peak_area']), 's', color='k', ms=7)
        ax[1].annotate('NX %s' % ('14' if b == public[0] else '15'), (f(i['shoulder_to_peak_fwhm']),
                       f(i['shoulder_to_peak_area'])), xytext=(5, 3), textcoords='offset points', fontsize=8)
    from matplotlib.ticker import FormatStrFormatter, NullFormatter
    for a in ax:
        for axis in (a.xaxis, a.yaxis):
            axis.set_major_formatter(FormatStrFormatter('%g'))
            axis.set_minor_formatter(NullFormatter())
    ax[1].set_xlabel('shoulder FWHM ÷ peak FWHM')
    ax[1].set_ylabel('shoulder area ÷ peak area')
    ax[1].set_title('b. what the shoulders look like (separated\'s Gaussian)', fontsize=9)
    fig.suptitle('R6. Question 3: is a Gaussian shoulder good enough? (%d well-measured burns with a shoulder)' % len(ct),
                 fontsize=9)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'R6_q3_fit_quality.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)
    counts.update(q3_split_lower=int(np.sum(cs < ct)), q3_with_shoulder=len(ct))

    # R7: question 5
    from lss_core import reciprocity
    series = list(csvmod.DictReader(open(series_csv, encoding='utf-8')))
    rates = list(csvmod.DictReader(open(rates_csv, encoding='utf-8')))
    fig, ax = plt.subplots(2, 1, figsize=(9.5, 12))
    ex = next((s for s in series if s['stretched_rho0_verdict'] == 'dose' and s['separated_rho0_verdict'] == 'dose'), series[0])
    rr = [r for r in rates if r['series'] == ex['series']]
    for est, col, off in (('stretched', 'tab:blue', 0.97), ('separated', 'tab:orange', 1.03)):
        x = np.array([f(r['flux_rel']) for r in rr])
        y = np.array([f(r[est + '_rate_per_h']) for r in rr])
        s = np.array([f(r[est + '_sigma_per_h']) for r in rr])
        ax[0].errorbar(x * off, 100 * y, 100 * s, fmt='o', color=col, capsize=3, label='%s: one burn each' % est)
        v = reciprocity.dose_or_time_rates(list(x), list(y), list(s))
        gm = float(np.exp(np.mean(np.log(x))))
        xx = np.logspace(np.log10(x.min() / 1.3), np.log10(x.max() * 1.3), 50)
        for beta, ls in ((v.beta, '-'), (1.0, '--'), (0.0, ':')):
            k = v.k if beta == v.beta else float(np.sum(y * (x / gm) ** beta / s ** 2) / np.sum((x / gm) ** (2 * beta) / s ** 2))
            ax[0].plot(xx, 100 * k * (xx / gm) ** beta, ls, color=col, lw=1,
                       label='%s: β = %.2f (fitted)' % (est, beta) if ls == '-' else None)
    ax[0].plot([], [], 'k--', lw=1, label='β = 1: follows the dose')
    ax[0].plot([], [], 'k:', lw=1, label='β = 0: follows the clock')
    ax[0].set_xscale('log')
    from matplotlib.ticker import FormatStrFormatter, NullFormatter
    ax[0].xaxis.set_major_formatter(FormatStrFormatter('%g'))
    ax[0].xaxis.set_minor_formatter(FormatStrFormatter('%g'))
    ax[0].axhline(0, color='0.5', lw=0.8)
    ax[0].set_xlabel('flux, relative to the series\' lowest')
    ax[0].set_ylabel('intensity drift rate (% per hour)')
    ax[0].set_title('a. one series (%s, %s burns): rate = k · flux^β' % (ex['series'], ex['n_burns']), fontsize=9)
    ax[0].legend(fontsize=7)
    for j, (est, col, off) in enumerate((('stretched', 'tab:blue', -0.15), ('separated', 'tab:orange', 0.15))):
        labelled = False
        for i, s in enumerate(series):
            b, lo_, hi_ = f(s[est + '_rho0_beta']), f(s[est + '_rho0_beta_lo']), f(s[est + '_rho0_beta_hi'])
            if np.isfinite(b):
                ax[1].errorbar(i + off, b, [[b - lo_], [hi_ - b]], fmt='o', color=col, capsize=2,
                               label=None if labelled else est)
                labelled = True
            ax[1].text(i, -1.5 - 0.45 * j, CODES.get(s[est + '_rho0_verdict'], '?'), ha='center', va='center',
                       fontsize=8, color=col, fontweight='bold')
    ax[1].text(-0.6, -1.5, 'stretched', ha='right', va='center', fontsize=7, color='tab:blue')
    ax[1].text(-0.6, -1.95, 'separated', ha='right', va='center', fontsize=7, color='tab:orange')
    ax[1].text(0.01, 0.02, 'verdict: D dose, T time, N neither, 0 no change, ± opposite signs, ? cannot tell',
               transform=ax[1].transAxes, fontsize=7)
    ax[1].axhline(1, color='k', ls='--', lw=0.8)
    ax[1].axhline(0, color='k', ls=':', lw=0.8)
    ax[1].set_xticks(range(len(series)), [s['series'] for s in series], rotation=90, fontsize=7)
    ax[1].set_xlim(-1.6, len(series) - 0.4)
    ax[1].set_ylim(-2.5, 4.3)
    ax[1].set_ylabel('β with its 68 % interval (ρ = 0)')
    ax[1].set_title('b. every series: β under stretched and separated, and the verdicts', fontsize=9)
    ax[1].legend(fontsize=7, loc='upper right')
    nchg = sum(s['stretched_rho0_verdict'] != s['separated_rho0_verdict'] for s in series)
    fig.suptitle('R7. Question 5: dose or time? %d series; separated changes the verdict of %d (strip scatter ρ = 0). '
                 'β is fitted on a grid from −1 to 4: an interval at the edge is open' % (len(series), nchg), fontsize=9)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'R7_q5_dose_or_time.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)
    counts.update(q5_series=len(series), q5_changed=nchg)
    return counts


def _reference_replicates(job):
    case, monitor, seeds = job
    T = FRAMES * CTIME
    got = []
    for seed in seeds:
        prof, tr = bp.profiles(n=FRAMES, ctime=CTIME, monitor=monitor, seed=3000 + seed, **CASES[case])
        clean, _ = bp.profiles(n=FRAMES, ctime=CTIME, monitor=monitor, seed=None, **CASES[case])
        window = burn.measure_gid(clean, estimator='stretched')[2]       # one window for all: not the question
        x = prof[0][:, 0]
        mean = np.mean([q[:, 1] for q in prof], axis=0)
        err = np.sqrt(np.sum([q[:, 2] ** 2 for q in prof], axis=0)) / len(prof)
        refs = dict(mean=mean, spline=smooth_reference(x, mean, err, window),
                    truth=np.mean([q[:, 1] for q in clean], axis=0))
        truth = true_change(tr.t, tr.area, T)
        for e in ('stretched', 'separated'):
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
        for e in ('stretched', 'separated'):
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
    fig, axes = plt.subplots(n, 1, figsize=(8, 4.2 * n), squeeze=False)
    axes = axes.T
    styles = {'mean': ('-', 'o', 'the frames\' mean (the reader)'), 'spline': ('--', 's', 'the mean, smoothed'),
              'truth': (':', '^', 'the noiseless mean')}
    for ax, case in zip(axes[0], cases):
        for e in ('stretched', 'separated'):
            for k in REFERENCES:
                got = sorted((r['monitor'], r['bias'], r['se']) for r in rows
                             if r['case'] == case and r['estimator'] == e and r['reference'] == k)
                if not got:
                    continue
                m, b, se = (np.array(v) for v in zip(*got))
                ls, mk, lab = styles[k]
                ax.errorbar(m, 100 * b, 100 * se, ls=ls, marker=mk, ms=4, color=COLOURS[e], capsize=2,
                            label='%s, %s' % (EN.get(e, e), lab))
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
        for j, (scan, e, k) in enumerate((sc, e, k) for sc in (14, 15) for e in ('stretched', 'separated')
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
    _key(fig)
    fig.savefig(os.path.join(out, 'S6_reference.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)


def nx_check(out, spec):
    """NX school burns 14 and 15 under every estimator: the change of each
    quantity over the burn, its σ and the verdict; the frames' mean χ²/dof;
    separated's shoulder. Writes nx.csv and S5; returns the rows."""
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
                if e in burn.SEPARATED_ESTIMATORS and ref.get('shoulder') is not None:
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
    fig, axes = plt.subplots(3, 1, figsize=(8, 10.5))
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
    axes[0].legend(handles=[Line2D([], [], color=COLOURS[e], marker='o', ls='', label=EN.get(e, e)) for e in NX_ESTIMATORS],
                   fontsize=7, frameon=False)
    fig.suptitle('S5. NX school burns 14 and 15 under every estimator (±1σ; filled: "changing", open: "stable")',
                 fontsize=9)
    fig.tight_layout()
    _key(fig)
    fig.savefig(os.path.join(out, 'S5_nx.png'), dpi=120, bbox_inches='tight')
    plt.close(fig)


def _load_csv(path):
    """A committed product back as rows: numbers as numbers (integers as int), the rest as text."""
    import csv as csvmod
    out = []
    for r in csvmod.DictReader(open(path, encoding='utf-8')):
        row = {}
        for k, v in r.items():
            try:
                row[k] = int(v) if v.lstrip('-').isdigit() else float(v)
            except (TypeError, ValueError):
                row[k] = {'True': True, 'False': False}.get(v, v)
        out.append(row)
    return out


def redraw(out):
    """S1-S6 redrawn from the committed products in ``out`` (results.csv, nx.csv, reference_noise.csv,
    reference_nx.csv): new labels or layout without the 90-minute rerun."""
    rows = _load_csv(os.path.join(out, 'results.csv'))
    for f in (s1, s2, s3, s4):
        f(rows, out)
    s5(_load_csv(os.path.join(out, 'nx.csv')), out)
    nxp = os.path.join(out, 'reference_nx.csv')
    s6(_load_csv(os.path.join(out, 'reference_noise.csv')), out, _load_csv(nxp) if os.path.exists(nxp) else ())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--replicates', type=int, default=None, help='per cell (default 300; part R 100)')
    ap.add_argument('--parts', default='A,B', help='A (every shoulder shape), B (fewer counts), or both')
    ap.add_argument('--cases', default=None, help='comma-separated: %s' % ', '.join(CASES))
    ap.add_argument('--shapes', default=None, help='comma-separated: %s' % ', '.join(SHAPES))
    ap.add_argument('--workers', type=int, default=None, help='processes (default: up to 4)')
    ap.add_argument('--core', type=float, default=burn.SEPARATE_CORE,
                    help='the separated: the shoulder fitted beyond this many FWHM from the peak (default %g)'
                    % burn.SEPARATE_CORE)
    ap.add_argument('--only', default=None, help='S5: the NX check only (no replicates); R: the reference\'s '
                    'noise (S6, about 6 min); G: figures R1, R2 of the real GID burns from --real-csv (seconds)')
    ap.add_argument('--real-csv', default=REAL_CSV, help='with --only G: the published per-burn summary')
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
        if 'redraw' in only:
            redraw(a.out)
        if 'G' in only:
            print(real_figures(a.out, a.real_csv, os.path.join(os.path.dirname(REAL_CSV), '..', 'burn_shoulder',
                                                                'reference_noise.csv')))
            print(explain_figures(a.out, a.real_csv))
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
