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

**Diffuse-cut axes** (F97, F59; owner 2026-11-23, Q-IMG-12: "β, β − α (α
from Qz) and Qz and Qxy"; 2026-11-24). Any cut, pixel or Q, can give its x
axis as one of ``DIFFUSE_AXES``. The intensities are the cut's own, the
x values are converted from its pixels:

    vertical cuts ('Q V', 'Pix V'), row r:
      δ = arctan((r − r0)·p / D_S2D)            (P34: the vertical angle from S2D)
      β = δ + arcsin(2 sin α − sin α_i)         ('beta', the exit angle; the
                                                 window's 'Angles' of Pix V)
      β − α                                     ('beta-alpha', α from Qz, so the
                                                 specular row is at 0 even on a
                                                 tilted sample: the owner's choice)
      Qz = (2π/λ)(sin β + sin α_i)              ('Qz'; the 'Q' of Pix V)
    horizontal cuts ('Q H', 'Pix H'), column c:
      2θ = Det_Th + arctan((c − c0)·p / D)      (D the pinhole distance in GID)
      Qxy = ±(2π/λ)√(cos²α_i + cos²β − 2 cos α_i cos β cos 2θ)
                                                ('Qxy', exact, at the β of the
                                                 band's middle row; the sign of 2θ)

with α = arcsin(Qz λ/4π) of the frame, α_i its true incidence
(``true_incidence``), r0 and c0 the beam's pixel. The window's 'Q' of a
horizontal cut is 4π sin(2θ/2)/λ, which equals Qxy only at α_i = β = 0 (at
0.1° they differ by less than 1e-5 relative). ``covered_range`` says what
range of a Q cut the detector covers, and ``centred_range`` gives a band
around the beam (F59: the window's Q defaults, '0:1' and '1:2', lie off the
detector for a reflectivity frame, so those cuts sum nothing).

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
DIFFUSE_AXES = ('beta', 'beta-alpha', 'Qz', 'Qxy')    # F97: any direction they fit (module docstring)
VERTICAL = (1, 3)                                     # 'Q V', 'Pix V': profiles along the rows
HORIZONTAL = (0, 2)                                   # 'Q H', 'Pix H': along the columns
AXIS_FITS = {'beta': VERTICAL, 'beta-alpha': VERTICAL, 'Qz': VERTICAL, 'Qxy': HORIZONTAL}
LABELS = {'Pixels': 'Pixels', 'beta': 'β (deg)', 'beta-alpha': 'β − α (deg)', 'Qz': 'Qz (Å⁻¹)', 'Qxy': 'Qxy (Å⁻¹)'}


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


def _direction(direction):
    return DIRECTIONS.index(direction) if isinstance(direction, str) else int(direction)


def _beta(rows, g, pix):
    """Exit angle β (rad) of detector rows (module docstring)."""
    return np.arctan((np.asarray(rows, float) - g.ycenter) * pix / g.spec_distance) + \
        np.arcsin(2 * np.sin(g.alpha) - np.sin(g.truealpha))


def _two_theta(cols, g, pix):
    return g.dth + np.arctan((np.asarray(cols, float) - g.xcenter) * pix / g.distance)


def axis_values(direction, pixels, axes, g, pix=PIXEL_MM, band=None):
    """The ``axes`` value (DIFFUSE_AXES) of each pixel row or column of a
    cut in ``direction``; ``band``: (first, last) row of a horizontal cut's
    band, for its β (default the beam's row)."""
    d = _direction(direction)
    if axes not in DIFFUSE_AXES:
        raise ValueError('axis %r: one of %s' % (axes, ', '.join(DIFFUSE_AXES)))
    if d not in AXIS_FITS[axes]:
        raise ValueError('axis %r is for %s cuts' % (axes, 'vertical' if AXIS_FITS[axes] == VERTICAL else 'horizontal'))
    if axes == 'Qxy':
        mid = g.ycenter if band is None else (float(band[0]) + float(band[1])) / 2
        beta = float(_beta([mid], g, pix)[0])
        tth = _two_theta(pixels, g, pix)
        ai = g.truealpha
        q2 = np.cos(ai) ** 2 + np.cos(beta) ** 2 - 2 * np.cos(ai) * np.cos(beta) * np.cos(tth)
        return np.sign(tth) * 2 * np.pi / g.wavelength * np.sqrt(np.maximum(q2, 0.0))
    beta = _beta(pixels, g, pix)
    if axes == 'beta':
        return beta * 180 / np.pi
    if axes == 'beta-alpha':
        return (beta - g.alpha) * 180 / np.pi
    return (np.sin(beta) + np.sin(g.truealpha)) * 2 * np.pi / g.wavelength


def axis_label(direction, axes):
    """The x label of a cut: the diffuse axes' and pixels' names; the
    window's 'Angles' and 'Q' by direction."""
    d = _direction(direction)
    if axes in LABELS:
        return LABELS[axes]
    if axes == 'Angles' and d == 3:
        return LABELS['beta']
    if axes == 'Angles' and d == 2:
        return '2θ (deg)'
    return LABELS['Qz'] if d in VERTICAL else 'Q (Å⁻¹)'


def covered_range(direction, g, shape, pix=PIXEL_MM):
    """(low, high) of the range a cut in ``direction`` can take on a
    detector of ``shape`` (rows, columns): pixels for the pixel cuts; for
    'Q H' the Qz of the rows, for 'Q V' the Qxy of the columns, as
    ``frame_cut`` turns a Q range into pixels."""
    d = _direction(direction)
    rows, cols = int(shape[0]), int(shape[1])
    if d == 2:
        return 0.0, float(rows - 1)
    if d == 3:
        return 0.0, float(cols - 1)
    if d == 0:          # rows -> Qz, the inverse of frame_cut's Q H arithmetic
        beta = np.arcsin(2 * np.sin(g.alpha) - np.sin(g.truealpha))
        r = np.array([0.0, rows - 1.0]) - g.ycenter
        q = (np.sin(np.arctan(r * pix / g.spec_distance) + beta) + np.sin(g.alpha)) * 2 * np.pi / g.wavelength
    else:               # columns -> Q of 2θ, the inverse of frame_cut's Q V arithmetic
        c = np.array([0.0, cols - 1.0]) - g.xcenter
        q = np.sin((c * pix / g.distance + g.dth) / 2) * 4 * np.pi / g.wavelength
    return float(np.min(q)), float(np.max(q))


def centred_range(direction, g, half_px, pix=PIXEL_MM):
    """(low, high) of a Q cut's range ``half_px`` pixels either side of the
    beam: 'Q H' a Qz band about the beam's row, 'Q V' a Qxy band about its
    column (as ``covered_range``)."""
    d = _direction(direction)
    if d == 0:
        beta = np.arcsin(2 * np.sin(g.alpha) - np.sin(g.truealpha))
        r = np.array([-half_px, half_px], float)
        q = (np.sin(np.arctan(r * pix / g.spec_distance) + beta) + np.sin(g.alpha)) * 2 * np.pi / g.wavelength
    elif d == 1:
        c = np.array([-half_px, half_px], float)
        q = np.sin((c * pix / g.distance + g.dth) / 2) * 4 * np.pi / g.wavelength
    else:
        raise ValueError('centred_range is for the Q cuts')
    return float(np.min(q)), float(np.max(q))


def frame_cut(det, data, error, direction, lo, hi, g, axes='Pixels', absfac=1, absnum=None, terms=None):
    """Cut of one normalised frame ``data`` (``error``) with geometry ``g``;
    ``direction`` an index into DIRECTIONS or its name. Returns (N, 3).
    ``axes`` one of DIFFUSE_AXES: the same cut, its x axis converted from
    its pixels (``axis_values``)."""
    d = _direction(direction)
    if axes in DIFFUSE_AXES:
        if d not in AXIS_FITS[axes]:
            axis_values(d, [], axes, g)                  # raises, saying which cuts the axis is for
        out = np.array(frame_cut(det, data, error, d, lo, hi, g, 'Pixels' if d in (2, 3) else '_pixels',
                                 absfac, absnum, terms), dtype=float)
        band = None
        if d == 2:
            band = (max(int(lo), 0), min(int(hi), det.NROWS - 1))
        elif d == 0:
            band = _qz_rows(lo, hi, g, det)
        out[:, 0] = axis_values(d, out[:, 0], axes, g, getattr(det, 'pix_size', PIXEL_MM), band)
        return out
    xaxis = 'Q' if axes != '_pixels' else 'Pixels'      # Q cuts: x in Q, or in pixels for the diffuse axes
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
                     vroi=[max(int(lo1), 0), min(int(hi1) + 1, det.NROWS)], ax_type=xaxis,
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
                 hroi=[max(int(lo1), 0), min(int(hi1) + 1, det.NCOLS)], vroi=None, ax_type=xaxis,
                 wavelength=g.wavelength, s2d_dist=g.spec_distance, sh=g.sh, alpha=g.alpha,
                 truealpha=g.truealpha, mon=None, terms=terms)
    return det.hintData


def _qz_rows(lo, hi, g, det):
    """The rows a 'Q H' cut over Qz (lo, hi) sums, as ``frame_cut`` makes them."""
    beta = np.arcsin(2 * np.sin(g.alpha) - np.sin(g.truealpha))
    lo1 = int(np.tan(np.arcsin(lo * g.wavelength / 2.0 / np.pi - np.sin(g.alpha)) - beta)
              * g.spec_distance / PIXEL_MM) + g.ycenter
    hi1 = int(np.tan(np.arcsin(hi * g.wavelength / 2.0 / np.pi - np.sin(g.alpha)) - beta)
              * g.spec_distance / PIXEL_MM) + g.ycenter
    return max(int(lo1), 0), min(int(hi1), det.NROWS - 1)


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
