"""Settings of the GID patch (the window's "GID Patch"), in one place.

Every value here was a number written into the patch code; the defaults
are those numbers, so the patch is unchanged until a value is edited in
the GID worksheet (F61). Where each one acts:

- ``columns``: pixels summed across each frame around the direct-beam
  column (the window's H slit field); one profile per frame, placed at the
  frame's detector angle.
- ``row_min``, ``row_max``: detector rows used (β range).
- ``qz_decimals``: frames are grouped into Qz levels by their Qz rounded
  to this many decimals (at most three levels: low, middle, high; any
  further level goes into "high").
- ``dth_decimals``: the detector angle (degrees) is rounded to this many
  decimals before frames are ordered and joined.
- ``area_correction``: divide by the illuminated footprint fraction seen
  through the slits (``calArea``); ``hard_slit_offset_mm`` is the 32 mm by
  which the sample-detector distance is shortened there with hard slits.
- ``polarisation``: divide by 1 − (sin 2θ cos β)².
- ``vjoin_kind``: interpolation of the β-integrated profiles in the
  vertical join (Qz levels); the horizontal join is linear.
- ``pinhole``: patch in pinhole geometry instead (lss_core.pinhole, F45):
  every usable column at its own 2θ; the default (owner, 2026-11-18: pinhole
  is how GID is measured); off gives the patch above exactly as before. ``pinhole_distance_mm``: S4 → detector, 0 for the header
  value; ``response``: 'fit' (one factor per column), 'beam' (one
  profile along the beam axis shared by all frames, for a narrow Gaussian
  beam; owner, 2026-11-19) or 'none';
  ``arm_correction``: the g_l3 term in the vertical distance;
  ``min_frames``: 2θ bins seen by fewer frames are left out (map edges);
  ``transverse``: 2θ range of a map joined from several Qz levels,
  'intersection' (common to all, IDL) or 'union' (F62).
"""
from dataclasses import dataclass, fields


@dataclass
class GIDParams:
    columns: int = 3
    row_min: int = 15
    row_max: int = 486
    qz_decimals: int = 3
    dth_decimals: int = 3
    area_correction: bool = True
    hard_slit_offset_mm: float = 32.0
    polarisation: bool = True
    vjoin_kind: str = 'cubic'
    pinhole: bool = True
    pinhole_distance_mm: float = 0.0
    response: str = 'fit'
    arm_correction: bool = True
    min_frames: int = 2
    transverse: str = 'intersection'
    footprint: str = 'exact'          # pinhole footprint window: 'exact' (P39, D51) or 'idl' (PD_PIN_RANGE)

    def changed(self):
        """Names of the settings that differ from the defaults."""
        d = GIDParams()
        return [f.name for f in fields(self) if getattr(self, f.name) != getattr(d, f.name)]


def reduced_chi2(x, y, yerr, fac):
    """χ²/dof of the overlap ratios y ± yerr about the fitted factor."""
    n = len(x)
    if n < 2:
        return float('nan')
    return float(sum(((yi - fac) / ei) ** 2 for yi, ei in zip(y, yerr)) / (n - 1))


# ---- the patch itself (moved from the window, 2026-11-19; one implementation
# for the window and Experiment.gid) ------------------------------------------

import numpy as np                                   # noqa: E402
from scipy.interpolate import griddata, interp1d    # noqa: E402
from scipy.optimize import curve_fit                 # noqa: E402

LEVEL_NAMES = ['low Qz', 'middle Qz', 'high Qz'] + ['Qz level %d' % k for k in range(4, 20)]
NO_OVERLAP = 'Warning: no overlap area between two scans!'


class GIDError(Exception):
    """The patch stopped; the message is the one the window shows."""


@dataclass
class GIDFrame:
    """One Pilatus frame as the GID patch needs it. ``data``/``error``: the
    frame's counts and errors (raw, or background-subtracted as in the
    window); angles in radians; ``centre``: (column, row) of the direct
    beam; ``params``: the scan's SPEC header values (slits, g_l1..3)."""
    data: object
    error: object
    monitor: float
    absorber: float
    scan: int
    qz: float
    alpha: float
    true_alpha: float
    dth: float
    wavelength: float
    centre: tuple
    s2d: float
    pdist: float
    sh: float
    slits: tuple            # (S1 h, S1 v as the window sums it, S4 h, S5 h)
    params: dict


def _polynomial(x, *p):
    return sum([p[i] * x ** i for i in range(len(p))])


def _log_join(log, label, kind, x, y, yerr, fac, facerr):
    if log is not None:
        log.append(dict(label=label, kind=kind, x_from=float(np.min(x)), x_to=float(np.max(x)),
                        points=int(len(x)), factor=float(fac), error=float(facerr),
                        chi2=reduced_chi2(x, y, yerr, fac)))


def cal_area(areainfo, dth, hslit_px, hard_slit_offset_mm=32.0):
    """Footprint fraction seen through the slits at detector angle ``dth``
    (degrees): the window's ``calArea``, unchanged. ``areainfo``: S1 h,
    S1 v, S4 h, S5 h, true α, sample–detector, slit–detector."""
    s1y = areainfo[0]
    s4h = areainfo[2]
    s5h = areainfo[3]
    alpha = areainfo[4]
    s1x = areainfo[1] / np.sin(alpha)
    sam2d = areainfo[5] - hard_slit_offset_mm
    sli2s = areainfo[5] - areainfo[6]
    dth = dth * np.pi / 180.0
    if s5h > float(hslit_px) * 0.172:
        s5h = float(hslit_px) * 0.172
        sam2d = areainfo[5]
    phi = np.arcsin((s4h + s5h) / 2.0 / np.sqrt((s4h + s5h) ** 2 / 4.0 + (sam2d - sli2s) ** 2))
    dist = (s4h / 2.0 * sam2d + s5h / 2.0 * sli2s) / np.sqrt((s4h + s5h) ** 2 / 4.0 + (sam2d - sli2s) ** 2)
    seg = []
    seg.append([-s1x / 2.0, s1y / 2.0, -s1x / 2.0, -s1y / 2.0])
    seg.append([-s1x / 2.0, -s1y / 2.0, s1x / 2.0, -s1y / 2.0])
    seg.append([s1x / 2.0, -s1y / 2.0, s1x / 2.0, s1y / 2.0])
    seg.append([s1x / 2.0, s1y / 2.0, -s1x / 2.0, s1y / 2.0])
    conners = [[-s1x / 2, -s1y / 2], [s1x / 2, -s1y / 2], [s1x / 2, s1y / 2], [-s1x / 2, s1y / 2]]
    pointb = []
    pointt = []
    for i in range(4):
        if seg[i][0] == seg[i][2]:
            xtemp = seg[i][0]
            ybtemp = (xtemp * np.sin(dth - phi) - dist) / np.cos(dth - phi)
            yttemp = (xtemp * np.sin(dth + phi) + dist) / np.cos(dth + phi)
            pointb.append([xtemp, ybtemp] if ybtemp > -s1y / 2 and ybtemp < s1y / 2 else 'None')
            pointt.append([xtemp, yttemp] if yttemp > -s1y / 2 and yttemp < s1y / 2 else 'None')
        else:
            ytemp = seg[i][1]
            xbtemp = (ytemp * np.cos(dth - phi) + dist) / np.sin(dth - phi)
            xttemp = (ytemp * np.cos(dth + phi) - dist) / np.sin(dth + phi)
            pointb.append([xbtemp, ytemp] if xbtemp > -s1x / 2 and xbtemp < s1x / 2 else 'None')
            pointt.append([xttemp, ytemp] if xttemp > -s1x / 2 and xttemp < s1x / 2 else 'None')
    listb = []
    listt = []
    for i in range(4):
        if pointb[i] != 'None':
            listb.append(i)
        if pointt[i] != 'None':
            listt.append(i)
    bpop = []
    if len(listb) != 0:
        bpop = list(range(listb[0], listb[1]))
    if len(listt) != 0:
        tpop = list(range(listt[1], listt[0] + 4))
        for i in range(len(tpop)):
            bpop.append(tpop[i] - 4 if tpop[i] > 3 else tpop[i])
    bpop.sort(reverse=True)
    for i in bpop:
        conners.pop(i)
    for i in range(len(listb)):
        conners.append(pointb[listb[i]])
    for i in range(len(listt)):
        conners.append(pointt[listt[i]])
    conangle = np.array([np.arctan2(conners[i][1], conners[i][0]) for i in range(len(conners))])
    conorder = [conners[i] for i in np.argsort(conangle)]
    area = 0
    for i in range(len(conorder)):
        if i == len(conorder) - 1:
            area = area + conorder[i][0] * conorder[0][1] - conorder[i][1] * conorder[0][0]
        else:
            area = area + conorder[i][0] * conorder[i + 1][1] - conorder[i][1] * conorder[i + 1][0]
    return np.abs(area) / 2 / s1x / s1y


def sorted_scans(data):
    """Scan numbers ordered by their detector-angle range (the window's
    ``sortedScans(mtype='dth')``)."""
    if len(data) < 2:
        return list(data.keys())
    x = {k: sorted([data[k][0][0][0], data[k][-1][0][0]]) for k in data.keys()}
    return [k for k, _ in sorted(x.items(), key=lambda t: t[1])]


def hjoin(data1, data2, log=None, label='', warn=None):
    """Join two sets of profiles along 2θ (the window's ``imagehjoin``)."""
    from interp_compat import interp2d_linear
    data1x = np.array([data1[i][0][0] for i in range(len(data1))])
    data1z = np.array([np.sum(data1[i][:, 2]) for i in range(len(data1))])
    data1zerr = np.array([np.sqrt(np.sum(data1[i][:, 3] ** 2)) for i in range(len(data1))])
    data2x = np.array([data2[i][0][0] for i in range(len(data2))])
    data2z = np.array([np.sum(data2[i][:, 2]) for i in range(len(data2))])
    data2zerr = np.array([np.sqrt(np.sum(data2[i][:, 3] ** 2)) for i in range(len(data2))])
    data1step = np.abs(data1x[0] - data1x[1])
    data2step = np.abs(data2x[0] - data2x[1])
    if data2x[0] >= data1x[-1]:
        if warn is not None:
            warn(NO_OVERLAP)
        return np.vstack((data1, data2))
    overlap2 = np.where(data2x <= data1x[-1])
    overlap1 = np.where(np.logical_and(data1x >= data2x[0], data1x <= data2x[overlap2[0][-1]]))
    f = interp1d(data2x[overlap2], data2z[overlap2], kind='linear')
    ferr = interp1d(data2x[overlap2], data2zerr[overlap2], kind='linear')
    nonzero = np.nonzero(f(data1x[overlap1]))
    overlap1z = data1z[overlap1][nonzero]
    overlap1zerr = data1zerr[overlap1][nonzero]
    overlap2z = f(data1x[overlap1])[nonzero]
    overlap2zerr = ferr(data1x[overlap1])[nonzero]
    x = data1x[overlap1][nonzero]
    y = overlap1z / overlap2z
    yerr = y * np.sqrt(((overlap1zerr / overlap1z) ** 2 + (overlap2zerr / overlap2z) ** 2))
    pfit, pcov = curve_fit(_polynomial, x, y, p0=[1], sigma=yerr)
    fac = pfit[0]
    facerr = pcov[0][0] ** 0.5
    _log_join(log, label, 'horizontal (2theta)', x, y, yerr, fac, facerr)
    for i in range(len(data2)):
        data2[i][:, 2] = data2[i][:, 2] * fac
        data2[i][:, 3] = np.sqrt(data2[i][:, 3] ** 2 * fac ** 2 + data2[i][:, 2] ** 2 * facerr ** 2 / fac ** 2)
    data = []
    for i in range(overlap1[0][0]):
        data.append(data1[i])
    if data1step <= data2step:
        data2zoverlap = np.array([np.hstack(data2[i][:, 2].T) for i in overlap2[0]]).T
        data2zerroverlap = np.array([np.hstack(data2[i][:, 3].T) for i in overlap2[0]]).T
        f2d = interp2d_linear(data2x[overlap2], data2[0][:, 1], data2zoverlap)
        f2derr = interp2d_linear(data2x[overlap2], data2[0][:, 1], data2zerroverlap)
        data3 = f2d(data1x[overlap1], data2[0][:, 1])
        data3err = f2derr(data1x[overlap1], data2[0][:, 1])
        for i in range(overlap1[0][0], overlap1[0][-1] + 1):
            data.append(np.vstack((data1[i][:, 0], data1[i][:, 1], (data1[i][:, 2] + data3[:, i - overlap1[0][0]]) / 2.0,
                                   np.sqrt(data1[i][:, 3] ** 2 + data3err[:, i - overlap1[0][0]] ** 2) / 2.0)).transpose())
    else:
        data1zoverlap = np.array([np.hstack(data1[i][:, 2].T) for i in overlap1[0]]).T
        data1zerroverlap = np.array([np.hstack(data1[i][:, 3].T) for i in overlap1[0]]).T
        f2d = interp2d_linear(data1x[overlap1], data1[0][:, 1], data1zoverlap)
        f2derr = interp2d_linear(data1x[overlap1], data1[0][:, 1], data1zerroverlap)
        data3 = f2d(data2x[overlap2], data1[0][:, 1])
        data3err = f2derr(data2x[overlap2], data1[0][:, 1])
        for i in range(overlap2[0][0], overlap2[0][-1] + 1):
            data.append(np.vstack((data2[i][:, 0], data2[i][:, 1], (data2[i][:, 2] + data3[:, i - overlap2[0][0]]) / 2.0,
                                   np.sqrt(data2[i][:, 3] ** 2 + data3err[:, i - overlap2[0][0]] ** 2) / 2.0)).transpose())
    if data1x[-1] >= data2x[-1]:
        for i in range(overlap1[0][-1] + 1, len(data1)):
            data.append(data1[i])
    else:
        for i in range(overlap2[0][-1] + 1, len(data2)):
            data.append(data2[i])
    return data


def vjoin(data1, data2, kind='cubic', log=None, label='', warn=None):
    """Join two Qz levels along β (the window's ``imagevjoin``)."""
    from interp_compat import interp2d_linear
    data1y = data1[0][:, 1]
    data2y = data2[0][:, 1]
    if data1y[-1] < data2y[0]:
        if warn is not None:
            warn(NO_OVERLAP)
        return np.vstack((data1, data2))
    data1x = np.array([data1[i][0][0] for i in range(len(data1))])
    data2x = np.array([data2[i][0][0] for i in range(len(data2))])
    data2z = np.array([np.hstack(data2[i][:, 2]) for i in range(len(data2))]).T
    data2zerr = np.array([np.hstack(data2[i][:, 3]) for i in range(len(data2))]).T
    fdata2 = interp2d_linear(data2x, data2y, data2z)
    fdata2err = interp2d_linear(data2x, data2y, data2zerr)
    data2znew = fdata2(data1x, data2y)
    data2zerrnew = fdata2err(data1x, data2y)
    data2new = [np.vstack((data1x[0] * np.ones_like(data2y), data2y, data2znew[:, 0], data2zerrnew[:, 0])).transpose()]
    for i in range(1, len(data1x)):
        data2new.append(np.vstack((data1x[i] * np.ones_like(data2y), data2y, data2znew[:, i], data2zerrnew[:, i])).transpose())
    data2 = data2new
    overlap1 = np.where(data1y >= data2y[0])
    overlap2 = np.where(data2y <= data1y[-1])
    data1zint = np.array([np.sum([data1[i][j, 2] for i in range(len(data1))]) for j in overlap1[0]])
    data1zinterr = np.array([np.sqrt(np.sum([data1[i][j, 3] ** 2 for i in range(len(data1))])) for j in overlap1[0]])
    data2zint = np.array([np.sum([data2[i][j, 2] for i in range(len(data2))]) for j in overlap2[0]])
    data2zinterr = np.array([np.sqrt(np.sum([data2[i][j, 3] ** 2 for i in range(len(data2))])) for j in overlap2[0]])
    f = interp1d(data2y[overlap2], data2zint, kind=kind)
    ferr = interp1d(data2y[overlap2], data2zinterr, kind=kind)
    nonzero = np.nonzero(f(data1y[overlap1][:-1]))
    overlap1z = data1zint[:-1][nonzero]
    overlap1zerr = data1zinterr[:-1][nonzero]
    overlap2z = f(data1y[overlap1][:-1])[nonzero]
    overlap2zerr = ferr(data1y[overlap1][:-1])[nonzero]
    x = data1y[overlap1][:-1][nonzero]
    y = overlap1z / overlap2z
    yerr = y * np.sqrt(((overlap1zerr / overlap1z) ** 2 + (overlap2zerr / overlap2z) ** 2))
    pfit, pcov = curve_fit(_polynomial, x, y, p0=[1], sigma=yerr)
    fac = pfit[0]
    facerr = pcov[0][0] ** 0.5
    _log_join(log, label, 'vertical (beta)', x, y, yerr, fac, facerr)
    for i in range(len(data2)):
        data2[i][:, 2] = data2[i][:, 2] * fac
        data2[i][:, 3] = np.sqrt(data2[i][:, 3] ** 2 * fac ** 2 + data2[i][:, 2] ** 2 * facerr ** 2 / fac ** 2)
    data2zoverlap = np.array([np.hstack(data2[i][:, 2][:overlap2[0][-1] + 1].T) for i in range(len(data2))]).T
    data2zerroverlap = np.array([np.hstack(data2[i][:, 3][:overlap2[0][-1] + 1].T) for i in range(len(data2))]).T
    f2d = interp2d_linear(data1x, data2y[overlap2], data2zoverlap)
    f2derr = interp2d_linear(data1x, data2y[overlap2], data2zerroverlap)
    data3 = f2d(data1x, data1y[overlap1][:-1])
    data3err = f2derr(data1x, data1y[overlap1][:-1])
    data1z = np.array([np.hstack(data1[i][:, 2]) for i in range(len(data1))])
    data1zerr = np.array([np.hstack(data1[i][:, 3]) for i in range(len(data1))])
    data2z = np.array([np.hstack(data2[i][:, 2]) for i in range(len(data2))])
    data2zerr = np.array([np.hstack(data2[i][:, 3]) for i in range(len(data2))])
    data = [np.vstack((data1y[0] * np.ones_like(data1x), data1x, data1z[:, 0], data1zerr[:, 0])).transpose()]
    for i in range(1, overlap1[0][0]):
        data.append(np.vstack((data1y[i] * np.ones_like(data1x), data1x, data1z[:, i], data1zerr[:, i])).transpose())
    for i in range(overlap1[0][0], overlap1[0][-1]):
        data.append(np.vstack((data1y[i] * np.ones_like(data1x), data1x, (data1z[:, i] + data3.T[:, i - overlap1[0][0]]) / 2.0,
                               np.sqrt(data1zerr[:, i] ** 2 + data3err.T[:, i - overlap1[0][0]] ** 2) / 2.0)).transpose())
    for i in range(overlap2[0][-1], len(data2[0])):
        data.append(np.vstack((data2y[i] * np.ones_like(data1x), data1x, data2z[:, i], data2zerr[:, i])).transpose())
    dataz = np.array([np.hstack(data[i][:, 2]) for i in range(len(data))])
    datazerr = np.array([np.hstack(data[i][:, 3]) for i in range(len(data))])
    datay = np.array([data[i][0][0] for i in range(len(data))])
    datanew = [np.vstack((data1x[0] * np.ones_like(datay), datay, dataz[:, 0], datazerr[:, 0])).transpose()]
    for i in range(1, len(data1x)):
        datanew.append(np.vstack((data1x[i] * np.ones_like(datay), datay, dataz[:, i], datazerr[:, i])).transpose())
    return datanew


def legacy_patch(frames, params, det, log=None, warn=None):
    """The window's "GID Patch" with the pinhole box off: ``params.columns``
    summed around the direct beam per frame, one profile per frame at its
    detector angle, area and polarisation corrections, scans joined along 2θ
    per Qz level and levels along β. ``det``: a TwoDDetector (its error
    model applies). Returns (patch, levels); patch is the list of [2θ, β,
    I, σ] columns the map is made from. Raises GIDError with the window's
    message where it would stop."""
    gp = params
    hslit = float(gp.columns)
    dic = [{}, {}, {}]
    areainfo = {}
    averagemonc = {}
    qzfmt = '.%df' % gp.qz_decimals
    qztol = 10.0 ** -gp.qz_decimals
    qz = np.sort(list(set([float(format(f.qz, qzfmt)) for f in frames])))
    for f in frames:
        averagemonc.setdefault(f.scan, []).append(f.monitor)
    for f in frames:
        xc, yc = f.centre
        left, right = xc - (hslit - 1) / 2, xc + (hslit - 1) / 2
        det.plotHint({0: f.data}, {0: f.error}, absnum=[f.absorber], cen=[xc, yc], hroi=[left, right],
                     vroi=[gp.row_min, gp.row_max], ax_type='Angles', wavelength=[f.wavelength], s2d_dist=[f.s2d],
                     sh=[f.sh], alpha=f.alpha, truealpha=f.true_alpha, mon=[f.monitor])
        h = det.hintData
        ckey = f.scan
        if ckey not in areainfo:
            areainfo[ckey] = [f.slits[0], f.slits[1], f.slits[2], f.slits[3], f.true_alpha, f.s2d, f.pdist]
        dth = float(format(f.dth * 180 / np.pi, '.%df' % gp.dth_decimals)) ** np.ones_like(h[:, 0])
        m = np.average(averagemonc[ckey])
        if np.abs(f.qz - qz[0]) < qztol:
            k = 0
        elif np.abs(f.qz - qz[1]) < qztol:
            k = 1
        else:
            k = 2
        if k == 2 and ckey not in dic[2]:
            # as coded: the first frame of each high-Qz scan is not multiplied
            # by the scan's mean monitor (P36)
            dic[2][ckey] = [np.vstack((dth, h[:, 0], h[:, 1], h[:, 2])).transpose()]
        else:
            dic[k].setdefault(ckey, []).append(np.vstack((dth, h[:, 0], h[:, 1] * m, h[:, 2] * m)).transpose())
    keys = [sorted_scans(d) for d in dic]
    levels = []
    for name, ks, d in zip(LEVEL_NAMES, keys, dic):
        for s in ks:
            for p in d[s]:
                areacorr = cal_area(areainfo[s], p[:, 0][0], hslit, gp.hard_slit_offset_mm) if gp.area_correction else 1.0
                pol = (1 - (np.sin(p[:, 0] * np.pi / 180) * np.cos(p[:, 1] * np.pi / 180)) ** 2) if gp.polarisation else 1.0
                p[:, 2] = p[:, 2] / areacorr / pol
                p[:, 3] = p[:, 3] / areacorr / pol
        if len(ks):
            levels.append((name, list(ks), sum(len(d[s]) for s in ks),
                           min(p[0, 0] for s in ks for p in d[s]), max(p[0, 0] for s in ks for p in d[s])))
    joined = []
    for k, name in enumerate(LEVEL_NAMES[:3]):
        ks, d = keys[k], dic[k]
        if len(ks) > 1:
            try:
                data = hjoin(d[ks[0]], d[ks[1]], log, name, warn)
                for i in range(2, len(ks)):
                    data = hjoin(data, d[ks[i]], log, name, warn)
            except Exception:
                raise GIDError('Warning: One or more of selected scans do not have enough points for the horizontal patching!')
        elif len(ks) == 1:
            # as coded: a single high-Qz scan takes the middle level's first
            # scan key (P37); with one scan at every level they coincide
            data = d[ks[0]] if k < 2 else dic[2][keys[1][0]]
        elif k == 0:
            data = d[ks[0]]                  # no frame at all: IndexError, as the window
        else:
            data = []
        joined.append(data)
    patch = joined[0]
    for data, label in ((joined[1], 'low + middle Qz'), (joined[2], '+ high Qz')):
        if len(data) != 0:
            try:
                patch = vjoin(patch, data, gp.vjoin_kind, log, label, warn)
            except Exception:
                raise GIDError('Warning: One or more of selected scans do not have enough points for the vertical patching!')
    return patch, levels


def pinhole_frames(frames, params):
    """lss_core.pinhole frames for ``frames``, grouped by Qz level."""
    from . import pinhole
    gp = params
    qzfmt = '.%df' % gp.qz_decimals
    groups = {}
    for f in frames:
        groups.setdefault(float(format(f.qz, qzfmt)), []).append(f)
    out = []
    for qz in sorted(groups):
        level = []
        for f in groups[qz]:
            p = f.params
            dp = gp.pinhole_distance_mm or float(f.pdist)
            g = pinhole.FrameGeometry(dth=float(f.dth), alpha=float(f.true_alpha),
                                      beta0=float(np.arcsin(2 * np.sin(f.alpha) - np.sin(f.true_alpha))),
                                      c0=float(f.centre[0]), r0=float(f.centre[1]), d_sample=float(f.s2d),
                                      d_pinhole=dp, g_l3=float(p.get('g_l3', 0.0)) if gp.arm_correction else 0.0,
                                      wavelength=float(f.wavelength))
            areainfo = (p['S1L'] + p['S1R'], p['S1T'] + p['S1B'], p['S4L'] + p['S4R'], float(f.true_alpha),
                        float(f.s2d), dp)
            level.append(pinhole.PinholeFrame(np.asarray(f.data, float), float(f.monitor), g, areainfo,
                                              (p['S5L'], p['S5R']), p.get('g_l2', 0.0) - p.get('g_l1', 0.0), int(f.scan),
                                              footprint=gp.footprint))
        out.append(level)
    return out


def pinhole_patch(frames, params, log=None):
    """GID patch in pinhole geometry (F45, F62; lss_core.pinhole). Returns
    (patch, levels, level_info, join_info)."""
    from . import pinhole
    gp = params
    byqz = pinhole_frames(frames, params)
    edges = pinhole.shared_edges([f for level in byqz for f in level])
    infos, level_info, levels = [], [], []
    log = [] if log is None else log
    for k, level in enumerate(byqz):
        tt, beta, I, S, info = pinhole.level_map(level, gp.row_min, gp.row_max, response=gp.response,
                                                 area=gp.area_correction, pol=gp.polarisation, log=log,
                                                 min_frames=gp.min_frames, edges=edges)
        for e in log:
            e.setdefault('label', LEVEL_NAMES[k])
        level_info.append(dict(level=LEVEL_NAMES[k], **info))
        infos.append(info)
        levels.append((LEVEL_NAMES[k], sorted(set(f.scan for f in level)), len(level), float(tt.min()), float(tt.max())))
    try:
        tt, beta, I, S, jinfo = pinhole.join_levels(infos, transverse=gp.transverse, log=log,
                                                    labels=[LEVEL_NAMES[k] for k in range(len(byqz))])
    except ValueError as e:
        raise GIDError('The Qz levels could not be joined: %s.' % e)
    patch = [np.vstack((np.full(len(beta), t), beta, I[b], S[b])).T for b, t in enumerate(tt)]
    return patch, levels, level_info, jinfo


def map_arrays(patch):
    """(2θ mesh, β mesh, intensity, error) of a patch (degrees), as the
    window's map."""
    x = [patch[i][0][0] for i in range(len(patch))]
    y = list(patch[0][:, 1])
    X, Y = np.meshgrid(x, y)
    D = np.array([np.hstack(patch[i][:, 2]) for i in range(len(patch))]).T
    E = np.array([np.hstack(patch[i][:, 3]) for i in range(len(patch))]).T
    return X, Y, D, E


def products(X, Y, D, E, axes, alpha, wavelength, relax=False):
    """What the window plots and saves for a map: for axes 'Angles' the map
    itself, for 'Q' the map regridded on (Qxy, Qz) (``relax``: the largest
    rectangle, filled with 1e-10, as "GID Patch Relax"); with h (integrated
    over the vertical axis), v (over the horizontal one) and four vertical
    slices vc. ``alpha``: true incidence angle (rad) of the first frame."""
    if axes == 'Angles':
        x, y, d, e = X, Y, D, E
    elif axes == 'Q':
        k0 = 2 * np.pi / wavelength
        xq = k0 * np.sqrt(np.cos(alpha) ** 2 + np.cos(Y / 180 * np.pi) ** 2
                          - 2 * np.cos(alpha) * np.cos(Y / 180 * np.pi) * np.cos(X / 180 * np.pi))
        yq = k0 * (np.sin(alpha) + np.sin(Y / 180 * np.pi))
        if not relax:
            r = np.where(np.logical_and(xq[0] < xq[-1][-1], xq[0] > xq[-1][0]))
            qxy, qz = np.meshgrid(xq[0][r], yq[:, 0])
            d = griddata((xq.ravel(), yq.ravel()), D.ravel(), (qxy, qz), method='linear')
            e = griddata((xq.ravel(), yq.ravel()), E.ravel(), (qxy, qz), method='linear')
        else:
            r = np.linspace(np.min(xq), np.max(xq), int(len(xq[0]) * (np.max(xq) - np.min(xq)) / (xq[0][-1] - xq[0][0])))
            qxy, qz = np.meshgrid(r, yq[:, 0])
            d = griddata((xq.ravel(), yq.ravel()), D.ravel(), (qxy, qz), method='linear', fill_value=1e-10)
            e = griddata((xq.ravel(), yq.ravel()), E.ravel(), (qxy, qz), method='linear', fill_value=1e-10)
        x, y = qxy, qz
    else:
        raise ValueError("axes must be 'Angles' or 'Q'")
    h = np.vstack((x[0, :], np.sum(d, axis=0), np.sqrt(np.sum(e ** 2, axis=0)))).transpose()
    v = np.vstack((y[:, 0], np.sum(d, axis=1), np.sqrt(np.sum(e ** 2, axis=1)))).transpose()
    vc_ran = np.linspace(np.where(y[:, 0] > 0)[0][0], np.where(y[:, 0] > 0)[0][-1], 5)
    if axes == 'Angles':
        vc_ran = list(map(int, vc_ran))
    vc = {}
    for i in range(4):
        a, b = int(vc_ran[i]), int(vc_ran[i + 1])
        vc[i] = np.vstack((x[0, :], np.sum(d[a:b, :], axis=0), np.sqrt(np.sum(e[a:b, :] ** 2, axis=0)))).transpose()
    return dict(axes=axes, x=x, y=y, data=d, err=e, h=h, v=v, vc=vc)


def save(name, prod):
    """The three files of the window's "Save GID": horizontal and vertical
    integrals and the 2D map as rows (x, y, I, σ). File names as the window
    (including its '_agnle2d' spelling, which users' scripts may expect)."""
    if prod['axes'] == 'Q':
        tags = ('_qxy_gid.txt', '_qz_gid.txt', '_q2d_gid.txt')
    else:
        tags = ('_dth_gid.txt', '_beta_gid.txt', '_agnle2d_gid.txt')
    x, y, d, e = prod['x'], prod['y'], prod['data'], prod['err']
    data2d = []
    for i in range(len(d)):
        for j in range(len(d[0])):
            data2d.append([x[i][j], y[i][j], d[i][j], e[i][j]])
    np.savetxt(name + tags[0], prod['h'], fmt='%.4e\t%.4e\t%.4e')
    np.savetxt(name + tags[1], prod['v'], fmt='%.4e\t%.4e\t%.4e')
    np.savetxt(name + tags[2], np.array(data2d), fmt='%.4e\t%.4e\t%.4e\t%.4e')
    return [name + t for t in tags]
