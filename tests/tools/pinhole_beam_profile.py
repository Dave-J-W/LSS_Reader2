"""Effect of a Gaussian beam profile on the pinhole geometry (owner,
2026-11-19: vertical FWHM about 30 um, horizontal about 1 mm).

    python tests/tools/pinhole_beam_profile.py [--fwhm-v 0.030] [--fwhm-h 1.0]

The reader takes the footprint as uniform over S1v / sin a (lss_core.pinhole).
A Gaussian beam of vertical FWHM v lights the surface with a Gaussian of
FWHM v / sin a along the beam (well inside S1 when v << S1v). Through the S4
pinhole each column sees one stretch of the beam axis (ray_geometry), so the
light a column receives follows that Gaussian, smeared by S4's opening
(column_acceptance) and by the beam's horizontal width seen along the
column's line of sight (sigma_y / tan 2theta). The script compares that
prediction with the column response the pinhole patch fits from NX scan 11,
and measures the bias left in a map made with the fitted response from
synthetic frames lit that way (expected counts, flat true spectrum).
Uses lss_core only; reads the public NX file.
"""
import argparse
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))
os.chdir(ROOT)
from lss_core import pinhole as ph          # noqa: E402
from pinhole_frames import frames_for       # noqa: E402

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
K = 2 * math.sqrt(2 * math.log(2))          # FWHM / sigma


def illumination(f, fwhm_v, fwhm_h, ncols):
    """Relative light each column of frame ``f`` receives, and the source x
    of its centre ray (mm), the effective sigma along the beam (mm)."""
    g = f.geom
    x = np.array([ph.ray_geometry(g, g.r0, c).source[0] for c in range(ncols)])
    tt = ph.column_two_theta(ncols, g)
    s_beam = fwhm_v / K / math.sin(g.alpha)                     # along the beam
    s_h = fwhm_h / K / np.tan(np.abs(tt))                       # horizontal width along each line of sight
    acc = ph.column_acceptance(g, int(round(g.c0)), f.areainfo[2] / 2, f.areainfo[2] / 2)
    s_s4 = float(np.std(acc.source_x))                           # S4 opening and pixel width
    s = np.sqrt(s_beam ** 2 + s_h ** 2 + s_s4 ** 2)
    return np.exp(-0.5 * (x / s) ** 2) * (s_beam / s), x, s, s_beam, s_s4


def gauss_fit(c, y):
    """Centre and FWHM of a Gaussian + constant fitted to y(c)."""
    from scipy.optimize import curve_fit
    p0 = [y.max() - y.min(), c[np.argmax(y)], 15.0, y.min()]
    p, _ = curve_fit(lambda c, a, m, s, b: a * np.exp(-0.5 * ((c - m) / s) ** 2) + b, c, y, p0=p0, maxfev=20000)
    return p[1], abs(p[2]) * K, p[3] / (p[0] + p[3])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--fwhm-v', type=float, default=0.030, help='vertical beam FWHM at the sample (mm)')
    ap.add_argument('--fwhm-h', type=float, default=1.0, help='horizontal beam FWHM (mm)')
    a = ap.parse_args(argv)
    frames = frames_for(NX, [11])
    ncols = frames[0].counts.shape[1]
    f0 = frames[len(frames) // 2]
    ill, x, s, sb, ss4 = illumination(f0, a.fwhm_v, a.fwhm_h, ncols)
    g = f0.geom
    ftp = ph.footprint_length(g, f0.areainfo[1], f0.s1_to_sample_mm)
    print('NX scan 11, Det_Th %.1f deg, alpha %.4f deg, S1v %.2f mm, S4 %.2f mm' %
          (math.degrees(g.dth), math.degrees(g.alpha), f0.areainfo[1], f0.areainfo[2]))
    print('footprint as the reader takes it: uniform, %.1f mm long (S1v / sin a)' % ftp)
    print('Gaussian beam: FWHM along the beam %.1f mm (sigma %.2f); with S4 (sigma %.2f mm) and the horizontal '
          'width seen along the line of sight: %.1f mm FWHM at the column of the centre'
          % (sb * K, sb, ss4, s[int(round(g.c0))] * K))
    lit = ill / ill.max()
    cols = np.arange(ncols)
    half = cols[lit >= 0.5]
    print('columns receiving >= half the peak light: %d..%d (peak at column %.1f); the reader\'s usable columns: %s'
          % (half[0], half[-1], cols[np.argmax(lit)], '%d..%d' % tuple(ph.usable_columns(
              g, ncols, f0.s5[0], f0.s5[1], f0.areainfo[1], f0.s1_to_sample_mm)[[0, -1]])))
    # the response the patch fits from the data, against the prediction
    tt, beta, I, S, info = ph.level_map(frames, 15, 486, response='fit')
    r = info['response']
    used = sorted(set(np.concatenate([np.arange(lo, hi + 1) for lo, hi in info['columns'] if lo >= 0])))
    used = np.array(used)
    pred = np.mean([illumination(f, a.fwhm_v, a.fwhm_h, ncols)[0] for f in frames], axis=0)
    m_meas, w_meas, b_meas = gauss_fit(used.astype(float), r[used] / r[used].mean())
    m_pred, w_pred, _ = gauss_fit(used.astype(float), pred[used] / pred[used].mean())
    print('fitted column response (NX data): Gaussian centre column %.1f, FWHM %.1f columns, flat part %.0f %% of the peak'
          % (m_meas, w_meas, 100 * b_meas))
    print('predicted from the beam profile:   Gaussian centre column %.1f, FWHM %.1f columns' % (m_pred, w_pred))
    # bias with the fitted response, synthetic frames lit by the Gaussian beam (expected counts)
    for label, fv in (('Gaussian beam %.0f um' % (1000 * a.fwhm_v), a.fwhm_v), ('uniform (as assumed)', None)):
        synth = []
        for f in frames:
            lit_f = illumination(f, fv, a.fwhm_h, ncols)[0] if fv else np.ones(ncols)
            n = f.monitor * 1e-3 * np.ones_like(f.counts, float) * lit_f[None, :]
            synth.append(ph.PinholeFrame(n, f.monitor, f.geom, f.areainfo, f.s5, f.s1_to_sample_mm, f.scan))
        for resp in ('fit', 'none'):
            tt2, b2, I2, S2, info2 = ph.level_map(synth, 15, 486, response=resp, area=False, pol=False)
            prof = np.nanmean(I2, axis=1)
            prof = prof / np.nanmedian(prof)
            print('  %-24s response=%-4s: patched intensity of a flat truth spans %.3f..%.3f (2theta %.2f..%.2f deg)'
                  % (label, resp, np.nanmin(prof), np.nanmax(prof), tt2[0], tt2[-1]))


if __name__ == '__main__':
    main()
