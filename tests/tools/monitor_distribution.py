"""What does the scatter of the monitor (Monc) look like, and how much does
it matter for each reduced point?

Run from the repository root:  python3 tests/tools/monitor_distribution.py

Part A: frame-to-frame relative deviations of Monc from a smooth trend
along each beam-on scan, pooled over all sample SPEC files: their spread,
tails, and whether a Gaussian, a Student t or a Laplace distribution
describes them; and whether consecutive deviations are correlated (drift)
or independent (noise).

Part B: for every reflectivity point of NX school scans 6-9, the relative
counting error of the reduced point against candidate monitor
uncertainties: what share of the point's variance would come from the
monitor.
"""
import glob
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monitor_ratio import scans, column   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def spec_files(paths=None):
    """SPEC files among ``paths`` (files, or folders searched below), by
    default every file two levels under sample_data/ (the private sets
    included when present)."""
    out = []
    cands = []
    for p in paths or []:
        if os.path.isdir(p):
            cands += sorted(os.path.join(d, n) for d, _, ns in os.walk(p) for n in ns)
        else:
            cands.append(p)
    if not paths:
        cands = sorted(glob.glob(os.path.join(ROOT, 'sample_data', '*', '*', '*')))
    for p in cands:
        if os.path.isfile(p):
            with open(p, 'rb') as f:
                if f.read(2) == b'#F':
                    out.append(p)
    return out


def detrend(y, order=2):
    x = np.linspace(-1, 1, len(y))
    return y / np.polyval(np.polyfit(x, y, order), x) - 1.0


def part_a(paths=None):
    dev, lag1, per_scan = [], [], []
    for path in spec_files(paths):
        for s in scans(path):
            if len(s['rows']) < 10:
                continue
            m, t = column(s, 'Monc'), column(s, 'Seconds')
            if m is None or t is None or np.any(t <= 0) or np.mean(m / t) < 1000:
                continue                         # beam off (owner: < 1000 counts/s)
            if np.std(m / t) / np.mean(m / t) > 0.05:
                continue                         # scans that move the monitor's beam (S1, mirrors, energy)
            r = detrend(m / t)
            dev.extend(r)
            per_scan.append((os.path.relpath(path, ROOT), s['num'], len(r), np.std(r, ddof=3),
                             np.mean(m)))
            if len(r) > 3:
                lag1.append(np.corrcoef(r[:-1], r[1:])[0, 1])
    d = np.array(dev)
    print('PART A  Monc relative deviations from a smooth trend, per second')
    print('  %d points from %d steady beam-on scans' % (len(d), len(per_scan)))
    sd = d.std()
    mad = 1.4826 * np.median(np.abs(d - np.median(d)))
    q = np.percentile(np.abs(d), [50, 68.27, 95, 99, 99.9])
    print('  standard deviation        %.3e' % sd)
    print('  robust sigma (1.4826 MAD) %.3e   <- the "typical" spread' % mad)
    print('  |dev| quantiles 50/68.3/95/99/99.9 %%: %s' % '  '.join('%.2e' % v for v in q))
    print('  Gaussian with the robust sigma would put 99%% within %.2e (seen: %.2e)'
          % (2.576 * mad, q[3]))
    print('  excess kurtosis %.1f (Gaussian 0)' % stats.kurtosis(d))
    fits = {}
    fits['Gaussian'] = (stats.norm, stats.norm.fit(d))
    fits['Laplace'] = (stats.laplace, stats.laplace.fit(d))
    fits['Student t'] = (stats.t, stats.t.fit(d))
    print('  model        params                          log-likelihood   AIC')
    for name, (dist, p) in fits.items():
        ll = np.sum(dist.logpdf(d, *p))
        print('  %-11s %-32s %12.1f %9.1f' % (name, ' '.join('%.3g' % v for v in p), ll,
                                              2 * len(p) - 2 * ll))
    print('  lag-1 autocorrelation of deviations within scans: median %.2f '
          '(0: independent noise; near 1: slow drift)' % np.median(lag1))
    print('  per scan (file, scan, points, sigma, mean Monc):')
    for row in sorted(per_scan, key=lambda r: -r[3])[:8]:
        print('    %-30s %4d %4d  %.2e  %.3g' % row)

    # Is the heavy tail a property of each scan, or of mixing scans whose
    # spreads differ? Standardise every scan by its own robust sigma.
    z = []
    for path in spec_files():
        for s in scans(path):
            if len(s['rows']) < 10:
                continue
            m, t = column(s, 'Monc'), column(s, 'Seconds')
            if m is None or t is None or np.any(t <= 0) or np.mean(m / t) < 1000:
                continue
            if np.std(m / t) / np.mean(m / t) > 0.05:
                continue
            r = detrend(m / t)
            rs = 1.4826 * np.median(np.abs(r - np.median(r)))
            if rs > 0:
                z.extend(r / rs)
    z = np.array(z)
    print('  standardised per scan: excess kurtosis %.1f; fraction beyond 2.576: %.2f %% '
          '(Gaussian 1.00 %%); beyond 4: %.2f %% (Gaussian 0.006 %%)'
          % (stats.kurtosis(z), 100 * np.mean(np.abs(z) > 2.576), 100 * np.mean(np.abs(z) > 4)))
    # How does a scan's spread depend on the monitor count per frame?
    sig = np.array([r[3] for r in per_scan])
    mon = np.array([r[4] for r in per_scan])
    slope, icpt = np.polyfit(np.log(mon), np.log(sig), 1)
    print('  spread vs monitor count per frame: sigma ~ M^%.2f  (-0.5: counting-like; 0: a fixed floor)'
          % slope)
    poisson = sig * np.sqrt(mon)
    print('  spread / Poisson spread (1/sqrt(M)): median %.2f, range %.2f to %.2f'
          % (np.median(poisson), poisson.min(), poisson.max()))
    return mad, q[3] / 2.576


def part_b(candidates):
    sys.path.insert(0, ROOT)
    from lss_core.experiment import Experiment
    exp = Experiment(os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923'))
    r = exp.reflectivity([6, 7, 8, 9])
    print()
    print('PART B  NX school scans 6-9: share of each point\'s variance that a')
    print('        monitor uncertainty u_M would contribute (correlated, on the net signal)')
    rows = np.vstack([r.per_scan[k] for k in r.order])
    qz, net, sig, sigerr, lbg, rbg = rows[:, 0], rows[:, 1], rows[:, 3], rows[:, 4], rows[:, 5], rows[:, 6]
    # counting part of the present error column (per-pixel monitor terms removed
    # would need the pixels; the counting part is the Poisson variance of the boxes)
    monc = np.concatenate([[f.monitor for f in exp.frames([k])] for k in r.order])
    counts_s, counts_b = sig * monc, (lbg + rbg) * monc        # box sums in counts
    rel_count = np.sqrt(counts_s + counts_b / 4) / np.maximum(net * monc, 1e-300)   # var(S) + var(L+R)/4
    print('  Qz      net counts   rel. counting   share of variance from monitor for u_M =')
    print('                       error           ' + '  '.join('%8.2e' % u for u in candidates))
    for i in np.linspace(0, len(qz) - 1, 14).astype(int):
        shares = [u ** 2 / (u ** 2 + rel_count[i] ** 2) for u in candidates]
        print('  %.4f  %10.3g   %10.2e     ' % (qz[i], net[i] * monc[i], rel_count[i])
              + '  '.join('%8.1f%%' % (100 * s) for s in shares))
    for u in candidates:
        n = np.sum(rel_count < u)
        print('  u_M = %.2e: monitor exceeds counting at %d of %d points; '
              'monitor share > 10%% at %d' % (u, n, len(qz),
                                              np.sum(u ** 2 / (u ** 2 + rel_count ** 2) > 0.1)))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='The scatter of the monitor (Monc) and how much it matters.')
    ap.add_argument('paths', nargs='*', help='SPEC files or folders for part A (default: every SPEC file '
                                             'under sample_data/, the private sets included when present); '
                                             'part B always uses NX school scans 6-9')
    a = ap.parse_args(argv)
    typical, tail = part_a(a.paths)
    part_b([typical, 0.00136, 1 / np.sqrt(2.2e5)])
    return 0


if __name__ == '__main__':
    sys.exit(main())
