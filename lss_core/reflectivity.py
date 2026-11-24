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
4. the row is [Qz, S − (B1 + B2)/2, σ, S, σ_S, B1, B2], with
   σ = √(σ_S² + (σ_B1² + σ_B2²)/4) in the legacy error model; in the budget
   model (``detector.errors``, lss_core.errors) σ² = counting part
   + (net · u_M)², the monitor term applied once to the net signal.
"""
import math

import numpy as np

from . import stitching

from .images import PIXEL_MM                    # noqa: E402  Pilatus pixel (mm), written once there


def frame_row(detector, image, error, monitor, beam_xy, qz, slit, bg_offset_deg,
              direction, distance, low_qz_slit):
    """One reflectivity point from one frame (see module docstring).

    Returns (row, info); info holds the beam centre found, the expected
    one, the slit and background offset (pixels) used, and the offset.

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
    net, neterr = detector.netROI()     # legacy: sqrt(sigerr² + (lbgerr² + rbgerr²)/4)
    row = np.array([qz, net, neterr, sig, sigerr, lbg, rbg])
    info = {'centre': (cenx, ceny), 'expected': tuple(scen), 'slit': use, 'bg': bg,
            'offset': (cenx - scen[0], ceny - scen[1])}
    return row, info


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


def merge_identical(per_scan, group, monitors=None):
    """Merge a group of repeated scans into its first scan (columns Qz, R,
    σ; the window's "Merge").

    With ``monitors`` ({scan: monitor of each point}): the repeats' counts
    and monitors summed, then normalised once, R = Σ M R / Σ M and
    σ = √Σ(M σ)² / Σ M. That is ΣN/ΣM point by point, the Poisson
    maximum-likelihood rate (F81, the default since 2026-11-23;
    physics_notes, I32). ``monitors`` is kept up to date: the first scan's
    become the sums, so merging again goes on in the same way.

    Without ``monitors``: the legacy mean, R = mean and σ = √(Σσ²)/n."""
    first = per_scan[group[0]]
    if monitors is not None:
        m = [np.asarray(monitors[k], float) for k in group]
        if any(len(mk) != len(per_scan[k]) for mk, k in zip(m, group)):
            raise ValueError('a monitor for every point of every repeat is needed')
        msum = np.sum(m, axis=0)
        y = sum(mk * per_scan[k][:, 1] for mk, k in zip(m, group)) / msum
        err = np.sqrt(sum((mk * per_scan[k][:, 2]) ** 2 for mk, k in zip(m, group))) / msum
        for k in group[1:]:
            del per_scan[k]
            monitors.pop(k, None)
        monitors[group[0]] = msum
        per_scan[group[0]] = np.vstack((first[:, 0], y, err)).T
        return
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


def _drop_actions(drops, j):
    acts = (drops or {}).get(j)
    if not acts:
        return []
    return [acts] if not isinstance(acts[0], (list, tuple)) else acts


def drop_points(per_scan, order, points, drops):
    """The raw points the patch dialog's drops remove, and where every row
    of the patched curve comes from (F92: drops kept as a mask).

    ``per_scan``: {scan: rows} (Qz first) as ``patch`` takes them; ``points``:
    {scan: [point number of each row]}; ``drops`` as for ``patch``. Each
    row of the curve joined so far sits at the Qz of one raw point:
    ``stitching.join`` keeps the earlier curve's points through the overlap
    (averaged there with the new scan, interpolated) and the new scan's
    beyond it. So a drop of row k of either is a drop of that row's point.

    Returns (removed, origins): the (scan, point) of every dropped row, in
    the order of the presses, and the (scan, point) of each row of the
    patched curve. Masking ``removed`` from the start gives the same curve
    as the drops wherever a dropped point had not yet been used at an
    earlier join (every drop of the new scan, and of the first scan at the
    first join); a point dropped from the curve joined so far at a later
    join was used by the earlier joins' fits, and the mask leaves it out of
    those too (D2: the mask is over the raw data)."""
    def rows(k):
        q = np.atleast_2d(np.asarray(per_scan[k], float))[:, 0]
        o = [(int(k), int(p)) for p in points[k]]
        if len(o) != len(q):
            raise ValueError('scan %s: %d points for %d rows' % (k, len(o), len(q)))
        return q, o
    data_q, data_o = rows(order[0])
    removed = []
    for j, key in enumerate(order[1:]):
        new_q, new_o = rows(key)
        for action in _drop_actions(drops, j):
            for d in sorted(action, key=abs, reverse=True):
                if d >= 0:
                    removed.append(new_o.pop(d))
                    new_q = np.delete(new_q, d)
                else:
                    removed.append(data_o.pop(d))
                    data_q = np.delete(data_q, d)
        o1 = np.where(data_q >= new_q[0])[0]
        o2 = np.where(new_q <= data_q[-1])[0]
        if not o1.size or not o2.size:
            raise ValueError('join %d: scan %s does not overlap the curve so far' % (j, key))
        if data_q[-1] >= new_q[-1]:
            tail_q, tail_o = data_q[o1[-1] + 1:], data_o[o1[-1] + 1:]
        else:
            tail_q, tail_o = new_q[o2[-1] + 1:], new_o[o2[-1] + 1:]
        data_q = np.concatenate([data_q[:o1[-1] + 1], tail_q])
        data_o = data_o[:o1[-1] + 1] + list(tail_o)
    return removed, data_o


PATCH_METHODS = ('joint', 'legacy')
DEFAULT_PATCH_METHOD = 'joint'     # 2026-11-22, the gauntlet (OUTPUT_DECISIONS, COMPARISONS C36)


def join_factor(old, new, method=DEFAULT_PATCH_METHOD):
    """(factor, error, note) for scan ``new`` against the curve ``old``
    (columns Qz, R, σ): what ``patch`` uses at a join. 'legacy': the
    window's original fit (``stitching.fitted_factor``: scan b spline-
    interpolated at a's overlap points, one ratio fitted). 'joint' (the
    default since 2026-11-22): one smooth curve in ln(R/R_F) fitted through
    both scans with the factor (``lss_core.patching.joint_factor``; the
    guard tries larger windows first and raises the order until χ² is
    adequate). Where the joint fit is impossible (too few usable points),
    the legacy fit is used and ``note`` says so; ``note`` is '' otherwise,
    or the joint fit's flags."""
    old, new = np.atleast_2d(np.asarray(old, float)), np.atleast_2d(np.asarray(new, float))
    if method == 'legacy':
        f, e = stitching.fitted_factor(old, new)
        return float(f), float(e), ''
    if method != 'joint':
        raise ValueError('patch method %r: one of %s' % (method, ', '.join(PATCH_METHODS)))
    from . import patching
    try:
        j = patching.joint_factor(patching.Scan(old[:, 0], old[:, 1], old[:, 2]),
                                  patching.Scan(new[:, 0], new[:, 1], new[:, 2]))
    except (ValueError, np.linalg.LinAlgError) as err:
        f, e = stitching.fitted_factor(old, new)
        return float(f), float(e), 'joint fit impossible (%s): the legacy fit used' % err
    return j.factor, j.factor * j.err, '; '.join(j.flags)


def patch(per_scan, order, drops=None, factors=None, method=DEFAULT_PATCH_METHOD, notes=None):
    """Join the scans in ``order`` (legacy chain: each scan against
    everything joined so far, the overlap averaged, the factor's error
    folded into the points, P4). ``drops`` maps the join number (0 for the
    first pair) to a list of drop indices, or to a list of such lists for
    several successive "Drop" presses. ``factors`` maps a join number to
    the (factor, error) to use there instead of the fitted one (the known
    absorber ratio, see ``patch_choice``). ``method``: how the factor is
    fitted where ``factors`` gives none (``join_factor``; 'legacy'
    reproduces the window's files before 2026-11-22 byte for byte).
    ``notes``: a list that receives (join, note) where the fit left one."""
    drops = drops or {}
    factors = factors or {}
    data = np.array(per_scan[order[0]], dtype=float)
    for j, key in enumerate(order[1:]):
        new = np.array(per_scan[key], dtype=float)
        if j in drops:
            actions = drops[j]
            if actions and not isinstance(actions[0], (list, tuple)):
                actions = [actions]
            for action in actions:
                data, new = apply_drops(data, new, action)
        factor = factors.get(j)
        if factor is None and method != 'legacy':
            f, e, note = join_factor(data[:, :3], new[:, :3], method)
            factor = (f, e)
            if note and notes is not None:
                notes.append((j, note))
        data = stitching.join(data, new, mtype='merge', factor=factor)
    return data


MONITOR_TOLERANCE = 0.03     # |Monc/Monp of scan b over scan a - 1| below this: no slit change


def monitor_change(qz_a, monc_a, monp_a, qz_b, monc_b, monp_b):
    """Median Monc/Monp of scan b over that of scan a, each over its points
    in the overlap (P29: where it is not 1, something upstream of Monc
    changed and the scale is not the foils alone). None without Monp."""
    try:
        qa, qb = np.asarray(qz_a, float), np.asarray(qz_b, float)
        ra = np.asarray(monc_a, float) / np.asarray(monp_a, float)
        rb = np.asarray(monc_b, float) / np.asarray(monp_b, float)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    ia, ib = qa >= qb.min() - 1e-6, qb <= qa.max() + 1e-6
    if not ia.any() or not ib.any():
        return None
    ma, mb = np.median(ra[ia]), np.median(rb[ib])
    if not (np.isfinite(ma) and np.isfinite(mb)) or ma <= 0:
        return None
    return float(mb / ma)


def patch_choice(patch, known, monitor, auto=True, threshold=0.03):
    """Patch factor or known absorber ratio for one join.

    ``patch``: (factor, error) fitted at the overlap; ``known``: (ratio,
    relative error) from the foils, or None; ``monitor``: monitor_change(),
    or None. The known ratio is suggested when its error is smaller than
    the patch's, the monitor shows no slit change and the two agree within
    3 combined sigma. It is used automatically (``auto``) when the patch's
    relative error is also above ``threshold`` and at least twice the
    known one. Returns a dict: use, suggest, patch_rel, known_rel, why."""
    fac, err = patch
    p_rel = abs(err / fac) if fac else float('inf')
    out = dict(use=False, suggest=False, patch_rel=p_rel, known_rel=None, why='')
    if known is None:
        out['why'] = 'no known ratio at this energy and setting'
        return out
    ratio, k_rel = known
    out['known_rel'] = k_rel
    if p_rel <= k_rel:
        out['why'] = 'the patch is more precise'
        return out
    if monitor is None:
        out['why'] = 'no Monp: a slit change cannot be ruled out'
        return out
    if abs(monitor - 1) >= MONITOR_TOLERANCE:
        out['why'] = 'Monc/Monp changed x%.2f: slits changed, keep the patch' % monitor
        return out
    sigmas = abs(math.log(fac / ratio)) / math.hypot(p_rel, k_rel) if fac > 0 else float('inf')
    if sigmas > 3:
        out['why'] = 'known ratio is %.1f sigma from the patch: keep the patch' % sigmas
        return out
    out['suggest'] = True
    out['use'] = bool(auto and p_rel > threshold and k_rel <= p_rel / 2)
    out['why'] = 'known ratio is more precise'
    return out


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
