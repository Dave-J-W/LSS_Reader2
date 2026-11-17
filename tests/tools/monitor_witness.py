"""Are Monc's large jumps real beam changes, or monitor errors?

Run from the repository root:  python3 tests/tools/monitor_witness.py

The detector is the witness. If the flux on the sample changes, the
detector's counts change in the same proportion as Monc's, and dividing by
Monc removes the change: harmless. If Monc jumps and the detector does not,
the jump is a monitor error and it lands in the reduced point.

Smooth curves are removed without fitting them: the second difference
along the scan of log(x),  d2(x)_k = log x_{k-1} - 2 log x_k + log x_{k+1},
is near zero for a slowly varying curve and, for independent frame-to-frame
noise of relative size u, has variance 6 u^2. Per frame k we compare
d2(Monc) with d2(detector), using the SPEC column of the detector ROI
(``Pilatus``, else ``Pil300K``, else ``Pilatus1M``; the first that has counts).

Output:
  * per scan: the slope of d2(det) against d2(Monc) (1: the detector follows
    the monitor, i.e. the monitor's scatter is real flux; 0: it does not),
    and the excess scatter of det/Monc over the detector's own Poisson limit,
    which bounds Monc's own measurement noise from above;
  * pooled: frames with the largest Monc jumps, and whether the detector
    followed them.

Only frames with at least 2e4 detector counts and their two neighbours
likewise are used (so the detector's own Poisson scatter is below 0.7 %),
in beam-on scans (Monc >= 1000 counts/s) of at least 8 points.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monitor_ratio import scans, column              # noqa: E402
from monitor_distribution import spec_files, ROOT    # noqa: E402

DET_COLUMNS = ('Pilatus', 'Pil300K', 'Pilatus1M')
MIN_COUNTS = 2e4


def d2(x):
    lx = np.log(x)
    return lx[:-2] - 2 * lx[1:-1] + lx[2:]


def detector(s):
    for name in DET_COLUMNS:
        d = column(s, name)
        if d is not None and np.median(d) > 0:
            return name, d
    return None, None


def main():
    rows, frames = [], []
    for path in spec_files():
        for s in scans(path):
            if len(s['rows']) < 8:
                continue
            m, t = column(s, 'Monc'), column(s, 'Seconds')
            name, d = detector(s)
            if m is None or t is None or d is None or np.any(t <= 0):
                continue
            if np.mean(m / t) < 1000:
                continue
            good = (d >= MIN_COUNTS) & (m > 0)
            ok = good[:-2] & good[1:-1] & good[2:]
            if ok.sum() < 5:
                continue
            dm, dd = d2(m / t)[ok], d2(d / t)[ok]
            dr = dd - dm                                   # d2 of det/Monc
            pois = (1 / d[:-2] + 4 / d[1:-1] + 1 / d[2:])[ok]   # Poisson variance of d2(det)
            mpois = (1 / m[:-2] + 4 / m[1:-1] + 1 / m[2:])[ok]
            slope = np.sum(dm * dd) / np.sum(dm * dm) if np.any(dm) else np.nan
            excess = np.mean(dr ** 2 - pois) / 6          # per-frame relative variance
            rows.append((os.path.relpath(path, ROOT), s['num'], name, int(ok.sum()),
                         np.std(dm) / np.sqrt(6), slope, np.sqrt(np.mean(pois) / 6),
                         np.sign(excess) * np.sqrt(abs(excess)), np.median(m)))
            for k in np.nonzero(ok)[0]:
                frames.append((os.path.relpath(path, ROOT), s['num'], k + 1, m[k + 1]))
            frames_d = frames[-int(ok.sum()):]
            for i, f in enumerate(frames_d):
                frames_d[i] = f + (dm[i], dd[i], np.sqrt(pois[i]), np.sqrt(mpois[i]))
            frames[-int(ok.sum()):] = frames_d

    print('Per scan: Monc scatter, how far the detector follows it, and what is left')
    print('  file                           scan det       n   Monc scatter  slope   '
          'det Poisson  excess of det/Monc  median Monc')
    for r in sorted(rows, key=lambda r: -r[4]):
        print('  %-30s %4d %-9s %3d   %.2e     %5.2f   %.2e     %+.2e          %.3g' % r)

    f = np.array([fr[4:] for fr in frames], dtype=float)
    dm, dd, sp, smp = f[:, 0], f[:, 1], f[:, 2], f[:, 3]
    print()
    print('Pooled over %d frames in %d scans' % (len(f), len(rows)))
    slope = np.sum(dm * dd) / np.sum(dm * dm)
    print('  slope of d2(det) on d2(Monc), all frames: %.2f' % slope)
    # The biggest Monc jumps, measured against everything else that moves d2(det)
    z = np.abs(dm) / np.sqrt(sp ** 2 + smp ** 2)
    big = np.argsort(-np.abs(dm))[:max(10, len(dm) // 50)]
    s_big = np.sum(dm[big] * dd[big]) / np.sum(dm[big] ** 2)
    resid = dd[big] - dm[big]
    print('  the %d largest Monc jumps (|d2| %.1e to %.1e):' % (len(big), np.abs(dm[big]).min(),
                                                              np.abs(dm[big]).max()))
    print('    slope %.2f (1: detector follows)' % s_big)
    print('    |d2(det/Monc)| / its Poisson sigma: median %.2f, max %.2f '
          '(<~2: the jump was real flux and normalisation removed it)'
          % (np.median(np.abs(resid) / sp[big]), np.max(np.abs(resid) / sp[big])))
    print('    |d2(det)|      / its Poisson sigma: median %.2f  (what it would be without '
          'normalising)' % np.median(np.abs(dd[big]) / sp[big]))
    small = np.argsort(np.abs(dm))[:len(dm) // 2]
    print('  for comparison, the quieter half of frames: |d2(det/Monc)|/Poisson median %.2f'
          % np.median(np.abs(dd[small] - dm[small]) / sp[small]))
    print('  frames where |d2(Monc)| exceeds 5x its own Poisson sigma: %d of %d'
          % (np.sum(np.abs(dm) > 5 * smp), len(dm)))
    print('  the 10 largest jumps:')
    print('    file                           scan point     Monc   d2(Monc)  d2(det)  '
          'd2(det/Monc)/Poisson')
    for i in big[:10]:
        fr = frames[i]
        print('    %-30s %4d %5d  %8.3g  %+8.2e %+8.2e  %+6.2f'
              % (fr[0], fr[1], fr[2], fr[3], dm[i], dd[i], (dd[i] - dm[i]) / sp[i]))


if __name__ == '__main__':
    main()
