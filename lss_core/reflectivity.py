"""Specular reflectivity from Pilatus frames, without the window.

This reproduces the window's "Ref Patch" workflow (``pilRefPatchData`` ->
patch dialog -> ``updateRefPlotData`` -> ``saveRefData``) step for step,
so that a script gives the same numbers as the GUI — byte for byte in the
saved files (``tests/test_api.py`` checks that against the legacy export
fixtures). Known questionable behaviour is kept (see PHYSICS_ISSUES.md).

Per frame (the window's ``pilRefPatchData``):

1. the frame is divided by its monitor count; σ² = I/M² + I²/M³;
2. the reflected beam is looked for near the beam position from the SPEC
   header (x mirrored: NCOLS − X − 1), by the intensity-weighted centre of
   a 5 × 5 box around the brightest pixel within ±3 pixels;
3. a signal box of (slit − 2) pixels per side is summed around it, and two
   background boxes of the same size, offset by ``bg_offset`` degrees
   converted to pixels at the sample–detector distance, either side
   (direction 'H') or above and below ('V');
4. the row is [Qz, S − (B1 + B2)/2, √(σ_S² + (σ_B1² + σ_B2²)/4), S, σ_S, B1, B2].
"""
import numpy as np

from . import stitching

PIXEL_MM = 0.172


def frame_row(detector, image, error, monitor, beam_xy, qz, slit, bg_offset_deg,
              direction, distance, low_qz_slit):
    """One reflectivity point from one frame (see module docstring).

    ``detector`` is a TwoDDetector('Pilatus'); its peakLocate and sumROI do
    the arithmetic, as in the window. ``beam_xy`` is (X, Y) from the SPEC
    header. ``low_qz_slit``: use a slit height of 5 pixels for
    0.02 < Qz < 0.03.
    """
    ncols = image.shape[1]
    scen = [ncols - beam_xy[0] - 1, beam_xy[1]]
    cenx, ceny = detector.peakLocate(image, error, cen=scen, mon=monitor)
    slitx, slity = slit
    if direction == 'H':
        bg = bg_offset_deg * distance * np.pi / 180 / PIXEL_MM / slitx
    else:
        bg = bg_offset_deg * distance * np.pi / 180 / PIXEL_MM / slity
    use = [slitx, 5] if (low_qz_slit and 0.02 < qz < 0.03) else [slitx, slity]
    sig, sigerr, lbg, lbgerr, rbg, rbgerr = detector.sumROI(slit=use, cen=[cenx, ceny],
                                                           dir=direction, bg=bg)
    row = np.array([qz, sig - (lbg + rbg) / 2.0,
                    np.sqrt(sigerr ** 2 + (lbgerr ** 2 + rbgerr ** 2) / 4),
                    sig, sigerr, lbg, rbg])
    offset = (cenx - scen[0], ceny - scen[1])
    return row, offset


def order_scans(per_scan):
    """Scan numbers sorted by their (first Qz, last Qz), as the window does."""
    if len(per_scan) < 2:
        return list(per_scan)
    ranges = {k: sorted([v[0][0], v[-1][0]]) for k, v in per_scan.items()}
    return [k for k, _ in sorted(ranges.items(), key=lambda t: t[1])]


def identical_groups(per_scan):
    """Groups of scans with the same first and last Qz (3 decimals) and the
    same number of points: repeats, offered for merging by the window."""
    groups = {}
    for k, v in per_scan.items():
        groups.setdefault('%.3f_%.3f_%d' % (v[0][0], v[-1][0], len(v)), []).append(k)
    return [g for g in groups.values() if len(g) > 1]


def merge_identical(per_scan, group):
    """Average a group of repeated scans into its first scan (columns Qz, R,
    σ; the window's "Merge"): R = mean, σ = √(Σσ²)/n."""
    first = per_scan[group[0]]
    y = first[:, 1].copy()
    var = first[:, 2] ** 2
    for k in group[1:]:
        y = y + per_scan[k][:, 1]
        var = var + per_scan[k][:, 2] ** 2
        del per_scan[k]
    n = len(group)
    per_scan[group[0]] = np.vstack((first[:, 0], y / n, np.sqrt(var) / n)).T


def apply_drops(data1, data2, drops):
    """The patch dialog's "Drop": indices >= 0 remove points of the new scan
    (``data2``), negative ones remove points of the data so far (``data1``),
    farthest from zero first. Returns new arrays."""
    for d in sorted(drops, key=abs, reverse=True):
        if d >= 0:
            data2 = np.delete(data2, d, axis=0)
        else:
            data1 = np.delete(data1, d, axis=0)
    return data1, data2


def patch(per_scan, order, drops=None):
    """Join the scans in ``order`` (legacy chain). ``drops`` maps the join
    number (0 for the first pair) to a list of drop indices."""
    drops = drops or {}
    data = np.array(per_scan[order[0]], dtype=float)
    for j, key in enumerate(order[1:]):
        new = np.array(per_scan[key], dtype=float)
        if j in drops:
            data, new = apply_drops(data, new, drops[j])
        data = stitching.join(data, new, mtype='merge')
    return data


def finish(data, qc, qoff=0.0, norm_factor=None, rrf=True):
    """The window's ``updateRefPlotData`` for patched data.

    Returns (ref, rrf): ``ref`` normalised to the highest point below Qc
    (σ divided by the same number) and by ``norm_factor`` if given, sorted
    by Qz; ``rrf`` the same divided by the Fresnel reflectivity at Qz +
    ``qoff`` (in the order of the patched data, as the window writes it),
    or None when ``rrf`` is False.
    """
    data = np.array(data, dtype=float)
    if data[0, 0] < qc:
        norm = np.max(data[np.where(data[:, 0] < qc)][:, 1])
        data[:, 1] = data[:, 1] / norm
        data[:, 2] = np.sqrt(data[:, 2] ** 2 / norm ** 2 + 0 ** 2 * data[:, 1] ** 2 / norm ** 2)
    if norm_factor is not None:
        data[:, 1] = data[:, 1] / norm_factor
        data[:, 2] = data[:, 2] / norm_factor
    ref = data[np.argsort(data[:, 0])]
    out_rrf = None
    if rrf:
        data[:, 0] = data[:, 0] + qoff
        f = stitching.fresnel(data[:, 0], qc)
        data[:, 1] = data[:, 1] / f
        data[:, 2] = data[:, 2] / f
        out_rrf = data.copy()
    return ref, out_rrf


def save(name, ref, rrf=None):
    """Write <name>_ref.txt and, if given, <name>_rrf.txt exactly as the
    window does (three tab-separated columns, %.4e)."""
    np.savetxt(name + '_ref.txt', ref, fmt='%.4e\t%.4e\t%.4e')
    if rrf is not None:
        np.savetxt(name + '_rrf.txt', rrf, fmt='%.4e\t%.4e\t%.4e')
