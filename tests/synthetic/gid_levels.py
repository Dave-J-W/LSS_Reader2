"""A legacy GID set with several Qz levels and known truth, in memory.

For PHYSICS_ISSUES P36 and P37 (the legacy patch with three Qz levels:
the first frame of each high-Qz scan not scaled by the mean monitor; with
one high-Qz scan, the middle level's key used). No such set exists in the
sample data. The frames are ``lss_core.gid.GIDFrame`` objects as
``Experiment.gid_frames`` makes them, ready for ``gid.legacy_patch``.

Geometry is the legacy patch's own (``TwoDDetector.plotHint``,
``gid.legacy_patch``): a frame contributes one column band (3 columns
around the direct-beam column) at 2θ = Det_Th, and row r is at

    β = atan((r − r0)·p / S2D) + asin(2 sin α − sin α_true)

with α = asin(Qz λ / 4π) the level's angle and α_true = In_Rot (p = 0.172
mm). It is not the exact pinhole geometry (``lss_core.pinhole``; for that,
see the helpers in tests/test_pinhole.py).

Expected counts per pixel of the band are

    μ = M_s · e_L · T(2θ, β) · A(2θ) · P(2θ, β) / 3,

T the true map, M_s the scan's monitor (constant along a scan), e_L the
level's efficiency (the scale the β join must find), A the legacy area
correction (``gid.cal_area``) and P the polarisation factor 1 − (sin 2θ
cos β)², both of which the patch divides out. So the patch, if right,
returns T times one constant per level (removed by the joins): the joined
map divided by T is flat. Pixels outside the band are filled with the
same model (they do not enter the legacy sums). Counts are Poisson when
``seed`` is given, otherwise expected values.
"""
import math
import os
import sys
from dataclasses import dataclass

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

NROWS, NCOLS = 487, 195
C0, R0 = 97, 53                    # direct-beam column and row (the reader's array)
PIX = 0.172
S2D, PDIST = 551.0, 271.0
WAVELENGTH = 1.24
IN_ROT_DEG = 0.09
SLITS = (2.0, 0.1, 0.4, 3.0)       # S1 h, S1 v, S4 h, S5 h (mm); an assumption, legacy area sensible


def level_qz(beta_offset_deg, true_alpha_deg=IN_ROT_DEG, wavelength=WAVELENGTH):
    """Qz of the level whose rows start at β offset ``beta_offset_deg``:
    asin(2 sin α − sin α_true) = offset."""
    s = (math.sin(math.radians(beta_offset_deg)) + math.sin(math.radians(true_alpha_deg))) / 2.0
    return 4 * math.pi * s / wavelength


def default_truth(tt, beta):
    """A Bragg rod at 2θ = 16.2° (Gaussian σ 0.15°) falling with β, on a
    smooth background: values per monitor count, about 1e-3."""
    rod = np.exp(-0.5 * ((tt - 16.2) / 0.15) ** 2) * np.exp(-np.maximum(beta, 0) / 6.0)
    return 1e-3 * (0.3 + 0.002 * (tt - 14.0) + rod) * (1 + 0.02 * beta)


@dataclass
class GIDTruth:
    truth: object                # T(2θ_deg, β_deg)
    levels: list                 # [(qz, beta offset deg, efficiency, [scan numbers])]
    monitors: dict               # scan -> M_s

    def at(self, patch):
        """T at every point of a legacy patch (list of [2θ, β, I, σ] columns)."""
        return [self.truth(p[:, 0], p[:, 1]) for p in patch]


def _beta(row, alpha, true_alpha):
    return np.degrees(np.arctan((row - R0) * PIX / S2D) + np.arcsin(2 * np.sin(alpha) - np.sin(true_alpha)))


def make_frames(levels=((0.0, 1.0, 2), (6.0, 0.8, 2), (12.0, 1.25, 2)), dth=(14.0, 18.5, 0.1),
                overlap_deg=0.6, truth=default_truth, monitor=1e5, seed=None, scan_numbers=None):
    """Frames of a legacy GID set. ``levels``: (β offset in degrees,
    efficiency, number of scans) per Qz level, low to high; each level's
    scans split the Det_Th range ``dth`` = (start, stop, step) into equal
    parts overlapping by ``overlap_deg``. ``scan_numbers``: one list per
    level (default 1, 2, ... in order). ``monitor``: M_s of the first scan;
    later scans read 3 % more each (so scan joins are not 1). Returns
    (frames, det, GIDTruth); ``det`` is the TwoDDetector the legacy patch
    sums with."""
    from TwoDDetector import TwoDDetector
    from lss_core import gid as gm
    det = TwoDDetector('Pilatus')
    det.NROWS, det.NCOLS = NROWS, NCOLS          # as after openFile of a 100K frame
    rng = np.random.default_rng(seed) if seed is not None else None
    start, stop, step = dth
    true_alpha = math.radians(IN_ROT_DEG)
    rows = np.arange(NROWS)
    frames, info, monitors = [], [], {}
    number = 1
    for k, (offset, eff, nscans) in enumerate(levels):
        qz = level_qz(offset)
        alpha = math.asin(qz * WAVELENGTH / 4 / math.pi)
        beta = _beta(rows, alpha, true_alpha)
        nums = list(scan_numbers[k]) if scan_numbers else list(range(number, number + nscans))
        number += nscans
        width = (stop - start + (nscans - 1) * overlap_deg) / nscans
        for i, s in enumerate(nums):
            lo = start + i * (width - overlap_deg)
            angles = np.round(np.arange(lo, min(lo + width, stop) + step / 2, step), 6)
            m = monitor * 1.03 ** (s - 1)
            monitors[s] = m
            for d in angles:
                areainfo = [SLITS[0], SLITS[1], SLITS[2], SLITS[3], true_alpha, S2D, PDIST]
                area = gm.cal_area(areainfo, d, 3.0)
                pol = 1 - (np.sin(np.radians(d)) * np.cos(np.radians(beta))) ** 2
                col = m * eff * truth(d, beta) * area * pol / 3.0
                mu = np.repeat(col[:, None], NCOLS, axis=1)
                data = rng.poisson(mu).astype(float) if rng is not None else mu
                frames.append(gm.GIDFrame(data, np.sqrt(data), m, 0, s, qz, alpha, true_alpha, math.radians(d),
                                          WAVELENGTH, (C0, R0), S2D, PDIST, 0.0, SLITS,
                                          {'In_Rot': IN_ROT_DEG, 'S2D_Dist': S2D, 'S7D_Dist': PDIST}))
        info.append((qz, offset, eff, nums))
    return frames, det, GIDTruth(truth, info, monitors)
