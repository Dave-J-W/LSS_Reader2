"""Single frames as the ground truth for a GID patch (owner, 2026-11-21).

An unpatched frame, with the pinhole geometry, already shows a Bragg peak at
its 2θ (each column at its own angle): no patching, no response, no joins.
So (1) every frame that holds the peak must put it at the same 2θ, whatever
columns see it, and (2) the patched map must give back the single frames'
position and width (sharper statistics, not a moved or broader peak).

    python tests/tools/single_frame_truth.py --scans 11 --peak 16.63
    python tests/tools/single_frame_truth.py --spec FILE --scans 163 --peak P --distances 255:280:2.5

For each frame whose usable columns cover peak ± half: each column's counts
over --rows per monitor count at its own mean 2θ (exact per-pixel angles;
no binning, which aliases), fitted with a Gaussian on a line
(``lss_core.pinhole.single_frame_peaks``); frames whose fit fails or is implausible are left out.
Prints the frames, then, for each S4–detector distance in --distances, how
well the frames agree (χ²/dof of their centres about the weighted mean) and
their drift with Det_Th (a wrong distance makes the peak move with the
column that sees it); then the patched map's peak (rows summed over --beta)
for each method at the header distance and at the best distance. Uses
lss_core only. Private data: print only; nothing is written.
"""
import argparse
import dataclasses
import math
import os
import sys

import numpy as np
from scipy.optimize import curve_fit

sys.path.insert(0, os.getcwd())
from lss_core import gid as gm, pinhole as ph          # noqa: E402
from lss_core.experiment import Experiment             # noqa: E402

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
K = 2 * math.sqrt(2 * math.log(2))


def _model(x, a, c, s, b0, b1, x0=0.0):
    return a * np.exp(-0.5 * ((x - c) / s) ** 2) + b0 + b1 * (x - x0)


def fit_peak(x, y, e, x0):
    """(centre, its error, FWHM, its error) of a Gaussian on a line, or None."""
    ok = np.isfinite(y) & np.isfinite(e) & (e > 0)
    x, y, e = x[ok], y[ok], e[ok]
    if len(x) < 8:
        return None
    f = lambda x_, a, c, s, b0, b1: _model(x_, a, c, s, b0, b1, x0)
    try:
        p, c = curve_fit(f, x, y, p0=[y.max() - np.median(y), x[np.argmax(y)], 0.06, np.median(y), 0],
                         sigma=e, maxfev=20000)
    except (RuntimeError, ValueError):
        return None
    err = np.sqrt(np.clip(np.diag(c), 0, None))
    return p[1], err[1], K * abs(p[2]), K * err[2]


def frame_peaks(level, peak, half, rows, distance=None):
    """``lss_core.pinhole.single_frame_peaks`` (per column, no binning)."""
    return ph.single_frame_peaks(level, peak, half, rows, distance)


def agreement(a):
    return ph.frames_agree(a)


def map_peak(e, scans, params, peak, half, beta):
    r = e.gid(scans, params=params, axes='Angles')
    x, y, d, s = map(np.asarray, (r.x, r.y, r.data, r.err))
    ax = 0 if np.allclose(x[:, 0], x[:, -1]) else 1
    tt = x[:, 0] if ax == 0 else x[0]
    b = (y >= beta[0]) & (y <= beta[1])
    prof = np.nansum(np.where(b & np.isfinite(d), d, 0), axis=1 - ax)
    pe = np.sqrt(np.nansum(np.where(b & np.isfinite(s), s ** 2, 0), axis=1 - ax))
    sel = (tt > peak - half) & (tt < peak + half)
    return fit_peak(tt[sel], prof[sel], pe[sel], peak)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', default=NX)
    ap.add_argument('--scans', default='11', help='scans of one Qz level, comma-separated')
    ap.add_argument('--peak', type=float, required=True, help='2θ of the peak (deg)')
    ap.add_argument('--half', type=float, default=0.4, help='half width of the fit window (deg)')
    ap.add_argument('--rows', default='50,170', help='rows summed in each frame')
    ap.add_argument('--beta', default='-0.1,2.0', help='β range summed in the patched map (deg)')
    ap.add_argument('--distances', default='250:281:2.5', help='S4–detector distances to try, start:stop:step (mm)')
    a = ap.parse_args()
    scans = [int(s) for s in a.scans.split(',')]
    rows = tuple(int(v) for v in a.rows.split(','))
    beta = tuple(float(v) for v in a.beta.split(','))
    e = Experiment(a.spec)
    frames, _ = e.gid_frames(scans)
    level = gm.pinhole_frames(frames, gm.GIDParams())[0]
    header = level[0].geom.d_pinhole
    fr = frame_peaks(level, a.peak, a.half, rows)
    print('Single frames at the header distance (%.1f mm):' % header)
    for d in fr:
        print('  Det_Th %.2f: centre %.4f ± %.4f, FWHM %.4f ± %.4f' % tuple(d))
    best = None
    lo, hi, st = (float(v) for v in a.distances.split(':'))
    print('Distance scan (frames-agree χ²/dof of the centres; drift of the centre with Det_Th):')
    for dist in np.arange(lo, hi, st):
        fd = frame_peaks(level, a.peak, a.half, rows, dist)
        if len(fd) < 3:
            continue
        m, me, chi, drift, fw = agreement(fd)
        print('  %.1f mm: %d frames, centre %.4f ± %.4f, χ²/dof %.2f, drift %+.4f deg/deg, FWHM %.4f'
              % (dist, len(fd), m, me, chi, drift, fw))
        if best is None or chi < best[1]:
            best = (dist, chi)
    print('Frames agree best at %.1f mm on the grid (header %.1f mm).' % (best[0], header))
    cal = ph.calibrate_distance(level, peak_deg=a.peak, half_deg=a.half)
    print('calibrate_distance: %.1f ± %.1f mm, reliable %s %s' % (cal.distance_mm, cal.error_mm, cal.reliable, cal.why))
    best = (round(cal.distance_mm, 1), cal.chi2_dof)
    for dist in (0.0, best[0]):
        fd = frame_peaks(level, a.peak, a.half, rows, dist or None)
        m, me, chi, drift, fw = agreement(fd)
        lab = 'header' if dist == 0 else '%.1f mm' % dist
        print('At %s: single frames centre %.4f ± %.4f, FWHM median %.4f' % (lab, m, me, fw))
        for name, kw in (('legacy', dict(pinhole=False)), ('fit', {}), ('physical', dict(response='physical')),
                         ('physical+fit', dict(response='physical+fit')), ('none', dict(response='none'))):
            if dist and name == 'legacy':
                continue
            r = map_peak(e, scans, gm.GIDParams(pinhole_distance_mm=dist, **kw), a.peak, a.half, beta)
            if r:
                print('  patched (%s): centre %.4f ± %.4f, FWHM %.4f ± %.4f (%+.0f %% vs single frames)'
                      % ((name,) + tuple(r) + (100 * (r[2] / fw - 1),)))


if __name__ == '__main__':
    main()
