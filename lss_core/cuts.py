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
"""
from dataclasses import dataclass

import numpy as np

DIRECTIONS = ('Q H', 'Q V', 'Pix H', 'Pix V')    # the window's list, in order
AXES = ('Pixels', 'Angles', 'Q')
PIXEL_MM = 0.172


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
    """The window's "Sum": mean of normalised frames, errors in quadrature / N."""
    total, var = data[0], errors[0] ** 2
    for d, e in zip(data[1:], errors[1:]):
        total, var = total + d, var + e ** 2
    n = len(data)
    return total / n, np.sqrt(var) / n


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
