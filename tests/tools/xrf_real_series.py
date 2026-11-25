"""XRF shootout on real lines in real scatter: the 19 private burn series
(2026-11-25; question Q14 in ``docs/studies/xrf_shootout/QUESTIONS.md``).

    python tests/tools/xrf_real_series.py --bundle <decrypted mca_spectra folder> --line "<element> K" \\
        --out docs/studies/xrf_shootout/run_real [--jobs 19] [--methods all|a,b]

The spectra are private. They travel encrypted (``sample_data/encrypted/
mca_spectra/README.md`` on the transfer branch) and are decrypted into the
git-ignored ``sample_data/private/``. The line is named only there (the
bundle's ``README_HANDOFF.md``: "a line near 8 keV"), so this script takes
it as ``--line`` and nothing committed names it. Its outputs are **summary
values per series and method**, which the owner allows in public
(2026-11-25): no spectrum, peak position or frame-by-frame curve.

**The data.** ``interest.json``'s ``p1_series``: 19 burn series, readout A,
a 10 keV beam, 21 spectra of 15 s each at one position, the line at a few
tens of counts per spectrum. There is no known truth, but three checks
need none:

1. **Self-consistency at low counts.** Each method measures every spectrum
   alone and the series' sum. An unbiased method's mean single-spectrum
   answer equals its sum answer / 21 (the sum holds 21 times the counts).
   ``self_bias`` = mean / (sum / N) − 1, as ``docs/studies/mca_scatter``
   did for P1 and data weights.
2. **Honest error bars.** Successive spectra differ by counting noise and
   a slow burn. ``diff_pull_sd`` is the SD of (x_i − x_i+1) / √(σ_i² +
   σ_i+1²): 1 for honest errors, a little above if the burn is fast.
3. **Agreement on the sums.** Each method's sum answer, calibrated on its
   clean twin (``xrf_shootout``), divided by the median of the fitting
   methods' (``sum_vs_median``). With 21 × the counts these should agree.
   A method far from the others counts something else: the escape peak,
   a background shape.

Every method is told what a user would know: the file's refined
calibration (``spectra.csv``'s ``refined_*``), a 10 keV beam, readout A's
measured detector and scatter (``xrf_shootout.MEASURED_DET`` and
``MEASURED_BEAM``, from ``docs/studies/mca_scatter``), and the element.

**The resampled twins** (``--twins``, 20) calibrate those checks. Each twin
is 21 Poisson draws from the series' own sum / 21: the real line on the
real scatter, at the real counts, with a known answer (the method's
answer on the sum, / 21). On the twins, ``twin_true_bias`` and
``twin_true_pull_sd`` are the bias and the error bars' honesty against
that answer, and ``twin_self_bias`` and ``twin_diff_pull_sd`` are what
checks 1 and 2 read when the counts are Poisson and nothing drifts. The
real values are judged against the twins' (each ``_sd`` column is the
spread over the twins).

Outputs: ``series_scores.csv`` (series × method; ``k`` is each method's
clean-twin calibration), ``log.txt``.
"""
import os

for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')

import argparse
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
sys.path.insert(0, os.path.join(os.getcwd(), 'tests', 'tools'))

import xrf_shootout as xs                                   # noqa: E402

DEFAULT_BUNDLE = os.path.join('sample_data', 'private', 'mca_scatter_cloud', 'mca_spectra')
DEFAULT_METHODS = tuple(m for m in xs.METHODS if m != 'larch_each') + xs.SINGLE_OPTIONS
FITTERS = ('fit_data', 'p1', 'p1p2', 'p1p3', 'p1p2p3', 'xeray', 'pymca', 'pymca_tails', 'pymca_snip60',
           'pymca_snip100', 'pymca_poly', 'pyxrf', 'larch')


def bundle(folder):
    sys.path.insert(0, folder)
    import load                                              # the bundle's own loader
    return load.Bundle(folder)


def series_ids(B, name):
    v = B.interest['p1_series'][name]
    ids = v['spectra'] if isinstance(v, dict) else v
    return list(range(ids[0], ids[-1] + 1)) if len(ids) == 2 else list(ids)


def condition(B, ids, line):
    """The shootout's condition for one series: the file's refined
    calibration on the reader's convention (channel 1 first)."""
    r = B.spectra[ids[0]]
    a, b = float(r['refined_a_keV'] or r['calib_a_keV']), float(r['refined_b_keV'] or r['calib_b_keV'])
    c0, k = int(r['first_channel']), int(r['n_channels'])
    e = a + b * np.arange(c0, c0 + k)
    return xs.XCond('real series', 'real', target=line, lines={line: 1.0}, elastic=0.0, beam=xs.MEASURED_BEAM,
                    detector=xs.MEASURED_DET, background=0.0, calib=(a + b * (c0 - 1), b, 0.0), channels=k,
                    e_range=(float(e[0]), float(e[-1])), series=len(ids))


class _Spec:
    """What the adapters read from a spectrum object: the energy axis and
    the calibration."""

    def __init__(self, cond):
        a, b, _ = cond.calib
        self.energy = a + b * np.arange(1, cond.channels + 1)
        self.calib = cond.calib


def measure(m, cond, spec, counts, total):
    """(single-spectrum answers, the sum's answer) of one method."""
    try:
        single = xs.run_method(m, cond, [spec] * len(counts), counts)
    except Exception:
        single = [None] * len(counts)
    try:
        s = xs.run_method(m, replace(cond, series=1), [spec], [total])[0]
    except Exception:
        s = None
    return single, s


def stats(single, s, n, ref=None):
    """Self-consistency against the sum (``self_bias``), the SD of
    successive-difference pulls, and, given the true answer ``ref`` per
    spectrum (the twins), the bias and pull SD against it."""
    good = [(v[0], v[1]) for v in single if v is not None and np.isfinite(v[0])]
    r = dict(failed=n - len(good))
    if s is None or not np.isfinite(s[0]) or s[0] == 0 or len(good) < 3:
        return r
    x = np.array([g[0] for g in good])
    rel = x / (s[0] / n) - 1
    r.update(self_bias=float(rel.mean()), self_bias_se=float(rel.std(ddof=1) / math.sqrt(len(rel))))
    e = np.array([g[1] for g in good], float)
    honest = np.all(np.isfinite(e)) and np.all(e > 0)
    if honest and len(good) == n:
        d = (x[1:] - x[:-1]) / np.sqrt(e[1:] ** 2 + e[:-1] ** 2)
        r['diff_pull_sd'] = float(d.std(ddof=1))
    if ref is not None and np.isfinite(ref) and ref != 0:
        r['true_bias'] = float(np.mean(x) / ref - 1)
        if honest:
            r['true_pull_sd'] = float(np.std((x - ref) / e, ddof=1))
    return r


def run_one(args):
    """Every method on one series, and on ``twins`` resampled twins of it:
    21 Poisson draws from the series' own sum / 21, whose true answer is
    the method's answer on that sum / 21."""
    xs._quiet()
    name, folder, line, methods, twins = args
    B = bundle(folder)
    ids = series_ids(B, name)
    n = len(ids)
    cond = condition(B, ids, line)
    counts = [B.spectrum(i)[1] for i in ids]
    total = np.sum(counts, axis=0)
    del B
    spec = _Spec(cond)
    ks = xs.calibrate(name, cond, methods)[1]
    rng = np.random.default_rng([20261125, 14] + [ord(ch) for ch in name])
    twin_counts = [[rng.poisson(total / n).astype(float) for _ in range(n)] for _ in range(twins)]
    rows, sums = [], {}
    for m in methods:
        t0 = time.time()
        single, s = measure(m, cond, spec, counts, total)
        k = ks[m][0]
        r = dict(series=name, method=m, n=n, k=k)
        r.update(stats(single, s, n))
        if s is not None and np.isfinite(s[0]) and np.isfinite(k) and k > 0:
            r['line_counts_per_spectrum'] = float(s[0] / n / k)
            if m in FITTERS:
                sums[m] = s[0] / k
        ref = s[0] / n if s is not None and np.isfinite(s[0]) else None
        tw = []
        for c in twin_counts:
            ts, tsum = measure(m, cond, spec, c, np.sum(c, axis=0))
            tw.append(stats(ts, tsum, n, ref))
        for key in ('self_bias', 'diff_pull_sd', 'true_bias', 'true_pull_sd'):
            v = [t[key] for t in tw if key in t]
            if v:
                r['twin_' + key] = float(np.mean(v))
                r['twin_' + key + '_sd'] = float(np.std(v, ddof=1)) if len(v) > 1 else math.nan
        r['twin_failed'] = float(np.mean([t['failed'] for t in tw])) if tw else math.nan
        r['sec_per_spectrum'] = (time.time() - t0) / ((n + 1) * (twins + 1))
        rows.append(r)
    med = float(np.median(list(sums.values()))) if sums else math.nan
    for r in rows:
        if r['method'] in sums and np.isfinite(med) and med > 0:
            r['sum_vs_median'] = float(sums[r['method']] / med - 1)
    return rows


def identify_line(B, names, beam=10.0, window=(7.0, 9.0)):
    """The K family whose Kα (``synthetic.mca_more``'s tables) is nearest the
    strongest peak in ``window`` of all the series summed. Returned, never
    printed or written: the element is private."""
    from synthetic import mca_more as mm
    e, tot = None, None
    for name in names:
        ids = series_ids(B, name)
        ee, n = B.summed(ids)
        if tot is None:
            e, tot = ee, n
        else:
            tot = tot + np.interp(e, ee, n)
    m = (e > window[0]) & (e < window[1])
    peak = float(e[m][np.argmax(tot[m])])
    fams = [k for k in mm.TABLES['lines'] if k.endswith(' K') and mm.family_lines(k, beam)]
    return min(fams, key=lambda k: abs(mm.main_line(k, beam)[0] - peak))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--bundle', default=DEFAULT_BUNDLE, help='the decrypted mca_spectra folder')
    ap.add_argument('--line', default='auto',
                    help="the series' line family ('Xx K'), or 'auto': found from the data and never written out")
    ap.add_argument('--out', required=True)
    ap.add_argument('--methods', default='all')
    ap.add_argument('--jobs', type=int, default=19)
    ap.add_argument('--twins', type=int, default=20, help='resampled twins of each series')
    a = ap.parse_args(argv)
    if not os.path.exists(os.path.join(a.bundle, 'counts.npy')):
        sys.exit('no decrypted bundle at %s: see sample_data/encrypted/mca_spectra/README.md on the transfer '
                 'branch' % a.bundle)
    os.makedirs(a.out, exist_ok=True)
    methods = list(DEFAULT_METHODS) if a.methods == 'all' else a.methods.split(',')
    methods, notes = xs.available(methods)
    B = bundle(a.bundle)
    names = sorted(B.interest['p1_series'])
    if a.line == 'auto':
        a.line = identify_line(B, names)
    del B
    log = open(os.path.join(a.out, 'log.txt'), 'w', encoding='utf-8', newline='\n')
    say = lambda s: (print(s, flush=True), log.write(s + '\n'), log.flush())    # noqa: E731
    say('xrf_real_series %s: %d private series, methods %s, %d jobs (the line is named in the bundle only)'
        % (time.strftime('%Y-%m-%d %H:%M:%S'), len(names), ','.join(methods), a.jobs))
    for n in notes:
        say(n)
    t0 = time.time()
    with ProcessPoolExecutor(a.jobs) as ex:
        rows = [r for part in ex.map(run_one, [(n, a.bundle, a.line, methods, a.twins) for n in names]) for r in part]
    xs.write_csv(os.path.join(a.out, 'series_scores.csv'), rows)
    say('done in %.0f s' % (time.time() - t0))
    log.close()


if __name__ == '__main__':
    main()
