"""Line cuts through Pilatus frames (the window's Line/Area Cuts tab).

``frame_cut`` is the window's per-frame arithmetic moved here unchanged:
one normalised frame (or the mean of several), a range, a direction, and
the frame's geometry give an (N, 3) array x, I, sigma. The window and
``Experiment.cut`` both call it.

Directions, as the window's list names them:

    'Q H'    horizontal cut, integrated over a Qz range      (TwoDDetector.plotVint)
    'Q V'    vertical cut, integrated over a Qxy range       (plotHint)
    'Pix H'  horizontal cut, integrated over pixel rows      (plotVint)
    'Pix V'  vertical cut, integrated over pixel columns     (plotHint)

The Q cuts turn the range into pixels with the frame's geometry and give
their x axis in Q; the pixel cuts give it in ``axes`` ('Pixels', 'Angles'
or 'Q'). As coded, the upper pixel limit is inclusive.

``default_range`` is the range the window offers for each direction: the
Q cuts '0:1' and '1:2'; the pixel cuts the detector's rows ('Pix H') and
columns ('Pix V'), as before on the Pilatus 100K: '0:485' (one short of
the last row, as the window has always had it) and '0:194'.
"""
from dataclasses import dataclass

import numpy as np

from .images import PIXEL_MM     # noqa: F401  (cuts.PIXEL_MM, as before)

DIRECTIONS = ('Q H', 'Q V', 'Pix H', 'Pix V')    # the window's list, in order
AXES = ('Pixels', 'Angles', 'Q')


def default_range(direction, shape=None):
    """The window's default range text for ``direction`` (an index into
    DIRECTIONS or its name) on a detector of ``shape`` (rows, columns;
    default the Pilatus 100K, lss_core.images.SHAPE_100K)."""
    from .images import SHAPE_100K
    rows, cols = SHAPE_100K if shape is None else (int(shape[0]), int(shape[1]))
    d = DIRECTIONS.index(direction) if isinstance(direction, str) else int(direction)
    return ('0:1', '1:2', '0:%d' % (rows - 2), '0:%d' % (cols - 1))[d]


@dataclass
class Geometry:
    """What a cut needs to know about one frame (radians, mm, pixels)."""
    wavelength: float
    alpha: float          # incidence angle from Qz, arcsin(Qz λ / 4π)
    truealpha: float      # In_Rot
    dth: float            # Det_Th
    sh: float             # sample height offset, -g_l2 tan(alpha)
    distance: float       # sample-detector distance used for the cut (S7D_Dist with a pinhole)
    spec_distance: float  # S2D_Dist, used for the vertical direction
    xcenter: float        # direct beam, column (image flipped left to right)
    ycenter: float        # direct beam, row


SPECULAR_HK_MAX = 1e-4     # |H|, |K| below this throughout: a specular scan (NX: at most 4.2e-7)


def true_incidence(columns, index, wavelength, in_rot_deg):
    """Incidence angle (rad) of point ``index`` of a scan.

    The scan header's In_Rot is written before the scan moves (P47,
    2026-11-23). In a scan at fixed incidence (GID, GISAXS, height scans)
    that is the angle of every point; in a specular scan that moves L
    (H = K = 0, L not constant) the incidence moves with it, and there
    α = β, Qz = 4π sin α / λ: α = arcsin(L λ / 4π) per point. An In_Rot
    column, when a macro writes one, wins. ``columns``: the scan's data
    columns by name (arrays; None or missing ones are ignored)."""
    col = columns.get('In_Rot')
    if col is not None:
        return float(col[index] * np.pi / 180.0)
    h, k, l = (columns.get(n) for n in ('H', 'K', 'L'))
    if h is not None and k is not None and l is not None and len(l) > 1:
        if (np.max(np.abs(h)) < SPECULAR_HK_MAX and np.max(np.abs(k)) < SPECULAR_HK_MAX
                and np.ptp(l) > 1e-6):
            return float(np.arcsin(l[index] * wavelength / 4.0 / np.pi))
    return in_rot_deg * np.pi / 180.0          # as before, to the last bit


def frame_cut(det, data, error, direction, lo, hi, g, axes='Pixels', absfac=1, absnum=None, terms=None):
    """Cut of one normalised frame ``data`` (``error``) with geometry ``g``;
    ``direction`` an index into DIRECTIONS or its name. Returns (N, 3)."""
    d = DIRECTIONS.index(direction) if isinstance(direction, str) else int(direction)
    cen = [g.xcenter, g.ycenter]
    if d == 2:
        det.plotVint(data, error, absfac=absfac, absnum=absnum, cen=cen, hroi=None,
                     vroi=[max(int(lo), 0), min(int(hi) + 1, det.NROWS)], ax_type=str(axes),
                     wavelength=g.wavelength, s2d_dist=g.distance, sh=g.sh, alpha=g.alpha, dth=g.dth,
                     mon=None, terms=terms)
        return det.vintData
    if d == 0:
        beta = np.arcsin(2 * np.sin(g.alpha) - np.sin(g.truealpha))
        lo1 = int(np.tan(np.arcsin(lo * g.wavelength / 2.0 / np.pi - np.sin(g.alpha)) - beta)
                  * g.spec_distance / PIXEL_MM) + g.ycenter
        hi1 = int(np.tan(np.arcsin(hi * g.wavelength / 2.0 / np.pi - np.sin(g.alpha)) - beta)
                  * g.spec_distance / PIXEL_MM) + g.ycenter
        det.plotVint(data, error, absfac=absfac, absnum=absnum, cen=cen, hroi=None,
                     vroi=[max(int(lo1), 0), min(int(hi1) + 1, det.NROWS)], ax_type='Q',
                     wavelength=g.wavelength, s2d_dist=g.distance, sh=g.sh, alpha=g.alpha, dth=g.dth,
                     mon=None, terms=terms)
        return det.vintData
    if d == 3:      # the vertical angle always from the sample-detector distance (P34; was g.distance)
        det.plotHint(data, error, absfac=absfac, absnum=absnum, cen=cen,
                     hroi=[max(int(lo), 0), min(int(hi) + 1, det.NCOLS)], vroi=None, ax_type=str(axes),
                     wavelength=g.wavelength, s2d_dist=g.spec_distance, sh=g.sh, alpha=g.alpha,
                     truealpha=g.truealpha, mon=None, terms=terms)
        return det.hintData
    lo1 = int((2.0 * np.arcsin(lo * g.wavelength / 4.0 / np.pi) - g.dth) * g.distance / PIXEL_MM) + g.xcenter
    hi1 = int((2.0 * np.arcsin(hi * g.wavelength / 4.0 / np.pi) - g.dth) * g.distance / PIXEL_MM) + g.xcenter
    det.plotHint(data, error, absfac=absfac, absnum=absnum, cen=cen,
                 hroi=[max(int(lo1), 0), min(int(hi1) + 1, det.NCOLS)], vroi=None, ax_type='Q',
                 wavelength=g.wavelength, s2d_dist=g.spec_distance, sh=g.sh, alpha=g.alpha,
                 truealpha=g.truealpha, mon=None, terms=terms)
    return det.hintData


def mean_frame(data, errors):
    """The window's "Sum" until 2026-11-23 (the legacy average, kept as an
    option): mean of normalised frames, errors in quadrature / N."""
    total, var = data[0], errors[0] ** 2
    for d, e in zip(data[1:], errors[1:]):
        total, var = total + d, var + e ** 2
    n = len(data)
    return total / n, np.sqrt(var) / n


def sum_frames(data, errors, normalisers):
    """"Sum All" as the owner asked (2026-11-23, F91: "sum the signals, sum
    the monitor/normalizer, then do the normalization"): the normalised
    frames ``data`` (errors ``errors``) weighted by their ``normalisers``,
    Σ w_i d_i / Σ w_i with errors √Σ(w_i σ_i)² / Σ w_i. With w_i a frame's
    monitor divided by the factors it was multiplied by (absorber, monitor
    gain), w_i d_i is its counts, so the result is ΣN / ΣM for equal factors
    (the pooled estimate); with equal monitors it is the mean."""
    w = np.asarray(normalisers, dtype=float)
    if len(w) != len(data) or not len(w) or not np.all(np.isfinite(w)) or np.any(w <= 0):
        raise ValueError('every summed frame needs a positive monitor')
    W = float(w.sum())
    total = sum(wi * d for wi, d in zip(w, data)) / W
    var = sum((wi * e) ** 2 for wi, e in zip(w, errors)) / W ** 2
    return total, np.sqrt(var)


def sum_weights(normalisers, legacy=False):
    """Each frame's share of the sum: w_i / Σw (sum_frames), or 1/N for the
    legacy mean. For the budget model's monitor terms."""
    n = len(normalisers)
    if legacy:
        return [1.0 / n] * n
    w = np.asarray(normalisers, dtype=float)
    return list(w / w.sum())


def frame_normaliser(monitor, absfac, absnum, gain=1.0):
    """The monitor of a frame divided by the factors normalise_frame
    multiplied it by: the weight of that frame in sum_frames."""
    from .normalise import attenuation
    return float(monitor) / (float(attenuation(absfac, absnum)) * float(gain))


def save(name, cuts, labels, summed_label=None):
    """Write cuts as the window's Export does: ``name + label + '_cut.txt'``
    per frame (label 'S# 1_F# 0'), or ``name + summed_label + '_sumcut.txt'``."""
    paths = []
    if summed_label is not None:
        p = name + summed_label + '_sumcut.txt'
        np.savetxt(p, cuts[0], fmt='%.4f\t%.4e\t%.4e')
        return [p]
    for cut, label in zip(cuts, labels):
        p = name + label + '_cut.txt'
        np.savetxt(p, cut, fmt='%.4f\t%.4e\t%.4e')
        paths.append(p)
    return paths
