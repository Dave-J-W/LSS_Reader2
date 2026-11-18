"""Pinhole-geometry GID: every detector column at its own angle (F45).

At 15-ID-C the slit S4 on the detector arm is a pinhole: a ray reaching
column c passed through S4, so the column sees one in-plane direction,

    2θ_c = Det_Th + atan((c − c0) · p / D_p),

with D_p the S4 → detector distance (`#B1` 4th number, 271 mm; the owner,
2026-11-18), whatever point of the long footprint it came from. The GID
patch of the window sums a few columns at c0 into one profile at Det_Th
and so uses ≈ 4 % of the counts of such frames (NX scan 11, measured); with
an angle per column the whole S5 window can be used without smearing the
resolution.

Reference: the IDL routines in docs/reference_code/idl (PD_PIN,
SCAN_PD_LCOO, PD_PIN_RANGE, PD_GID_READ, IMG_JOIN) and their review,
docs/handoff_out/04-answer/IDL_REVIEW.md §7, which this module follows:

- β per row: β_r = β0 + atan((r − r0) p / D_v), D_v = D_s + g_l3 (1/cos β0 − 1)
  (IDL; D_s = `#B1` 3rd number, g_l3 = `#G0` 8th; the term turns the
  horizontal arm distance into the path when the arm is raised);
- usable columns: the S5 projection from the pinhole, asymmetric
  ([c0 − S5L k, c0 + S5R k], k = D_p/(D_p − d5), d5 = 32 mm), intersected
  with the columns that see the footprint (PD_PIN_RANGE);
- weight of a pixel: W = M · A(2θ_c) · P(2θ_c, β_r) · R(c), with A the
  footprint fraction (the window's calArea arithmetic, one pixel wide, at
  the column's angle), P = 1 − (sin 2θ cos β)², R the column response;
- binning onto one 2θ grid as I = ΣN/ΣW, σ = √ΣN/ΣW (maximum likelihood for
  Poisson counts sharing a normalisation; inverse-variance weighting of
  pixels, as IDL's IMG_JOIN does, is biased low at < 1 count per pixel).

Approximations, said where they act: the footprint fraction is taken on the
band through the pinhole centre (offset e = 0); the column response R,
estimated from the data, absorbs what that leaves out. Nearest-bin
assignment (no split pixels); the bin step defaults to one column (p/D_p).
"""
import math
from dataclasses import dataclass

import numpy as np

PIXEL_MM = 0.172
S5_TO_DETECTOR_MM = 32.0       # hard slits (the window's area correction uses the same 32 mm)


@dataclass
class FrameGeometry:
    """One frame, as the reader stores it (angles in radians, mm, pixels)."""
    dth: float              # Det_Th
    alpha: float            # incidence, In_Rot
    beta0: float            # exit angle of the direct-beam row
    c0: float               # direct-beam column (reader orientation)
    r0: float               # direct-beam row
    d_sample: float         # sample → detector (#B1 3rd)
    d_pinhole: float        # S4 → detector (#B1 4th)
    g_l3: float = 0.0       # sample → arm rotation centre, horizontal (#G0 8th); 0: no arm term
    wavelength: float = 1.0


def column_two_theta(ncols, g):
    """2θ (rad) of every column, through the pinhole."""
    c = np.arange(ncols, dtype=float)
    return g.dth + np.arctan((c - g.c0) * PIXEL_MM / g.d_pinhole)


def vertical_distance(g):
    """Sample → detector path for the vertical angle, with the arm term (IDL)."""
    return g.d_sample + g.g_l3 * (1.0 / math.cos(g.beta0) - 1.0)


def row_beta(nrows, g):
    """β (rad) of every row."""
    r = np.arange(nrows, dtype=float)
    return g.beta0 + np.arctan((r - g.r0) * PIXEL_MM / vertical_distance(g))


def s5_window(g, s5_low, s5_high, d5=S5_TO_DETECTOR_MM):
    """Columns (lo, hi) the S5 slits let through from the pinhole; ``s5_low``
    opens towards low columns, ``s5_high`` towards high ones (mm)."""
    k = g.d_pinhole / (g.d_pinhole - d5)
    return g.c0 - s5_low * k / PIXEL_MM, g.c0 + s5_high * k / PIXEL_MM


def footprint_window(g, s1_vertical, s1_to_sample_mm=0.0):
    """Columns (lo, hi) that see the footprint through the pinhole
    (PD_PIN_RANGE): footprint ftp = beam / sin α, seen from the pinhole at
    the sample → pinhole distance L = D_s − D_p; the angular range is
    ψ = atan(2δ sin Det_Th, 1 − δ²), δ = ftp / 2L, centred on c0 as in IDL.
    ``s1_to_sample_mm`` (g_l2 − g_l1) adds the slit's diffraction width."""
    rwid = 1e-4 * g.wavelength / s1_vertical if s1_vertical > 0 else 0.0
    beam = math.sqrt(s1_vertical ** 2 + (1e-3 * s1_to_sample_mm * rwid) ** 2)
    ftp = beam / math.sin(g.alpha) if g.alpha > 0 else float('inf')
    lpin = g.d_sample - g.d_pinhole
    if lpin <= 0 or not math.isfinite(ftp):
        return -math.inf, math.inf                 # no pinhole in front of the sample: no limit
    delta = ftp / (2 * lpin)
    psi = math.atan2(2 * delta * math.sin(g.dth), 1 - delta ** 2)
    half = g.d_pinhole * psi / PIXEL_MM / 2
    return g.c0 - half, g.c0 + half


def usable_columns(g, ncols, s5_low, s5_high, s1_vertical, s1_to_sample_mm=0.0, d5=S5_TO_DETECTOR_MM):
    """Integer columns inside both the S5 window and the footprint window."""
    a, b = s5_window(g, s5_low, s5_high, d5)
    f, h = footprint_window(g, s1_vertical, s1_to_sample_mm)
    lo, hi = max(a, f, 0), min(b, h, ncols - 1)
    return np.arange(int(math.ceil(lo)), int(math.floor(hi)) + 1)


def area_fraction(s1h, s1v, s4h, s5h, alpha, sam2d, sli2s, dth):
    """Fraction of the footprint (s1v/sin α along the beam, s1h across) seen
    through slits s4h (at sli2s from the sample) and s5h (at sam2d) at the
    in-plane angle dth (rad): the window's ``calArea`` arithmetic, with its
    inputs explicit (there: S5 is capped at the H slit and moved to the
    detector). Normalised to the footprint area."""
    s1y = s1h
    s1x = s1v / np.sin(alpha)
    phi = np.arcsin((s4h + s5h) / 2.0 / np.sqrt((s4h + s5h) ** 2 / 4.0 + (sam2d - sli2s) ** 2))
    dist = (s4h / 2.0 * sam2d + s5h / 2.0 * sli2s) / np.sqrt((s4h + s5h) ** 2 / 4.0 + (sam2d - sli2s) ** 2)
    seg = [[-s1x / 2.0, s1y / 2.0, -s1x / 2.0, -s1y / 2.0], [-s1x / 2.0, -s1y / 2.0, s1x / 2.0, -s1y / 2.0],
           [s1x / 2.0, -s1y / 2.0, s1x / 2.0, s1y / 2.0], [s1x / 2.0, s1y / 2.0, -s1x / 2.0, s1y / 2.0]]
    corners = [[-s1x / 2, -s1y / 2], [s1x / 2, -s1y / 2], [s1x / 2, s1y / 2], [-s1x / 2, s1y / 2]]
    pointb, pointt = [], []
    for i in range(4):
        if seg[i][0] == seg[i][2]:
            x = seg[i][0]
            yb = (x * np.sin(dth - phi) - dist) / np.cos(dth - phi)
            yt = (x * np.sin(dth + phi) + dist) / np.cos(dth + phi)
            pointb.append([x, yb] if -s1y / 2 < yb < s1y / 2 else None)
            pointt.append([x, yt] if -s1y / 2 < yt < s1y / 2 else None)
        else:
            y = seg[i][1]
            xb = (y * np.cos(dth - phi) + dist) / np.sin(dth - phi)
            xt = (y * np.cos(dth + phi) - dist) / np.sin(dth + phi)
            pointb.append([xb, y] if -s1x / 2 < xb < s1x / 2 else None)
            pointt.append([xt, y] if -s1x / 2 < xt < s1x / 2 else None)
    listb = [i for i in range(4) if pointb[i] is not None]
    listt = [i for i in range(4) if pointt[i] is not None]
    bpop = list(range(listb[0], listb[1])) if listb else []
    if listt:
        for t in range(listt[1], listt[0] + 4):
            bpop.append(t - 4 if t > 3 else t)
    for i in sorted(bpop, reverse=True):
        corners.pop(i)
    corners += [pointb[i] for i in listb] + [pointt[i] for i in listt]
    ang = np.array([np.arctan2(c[1], c[0]) for c in corners])
    poly = [corners[i] for i in np.argsort(ang)]
    area = 0.0
    for i in range(len(poly)):
        j = 0 if i == len(poly) - 1 else i + 1
        area += poly[i][0] * poly[j][1] - poly[i][1] * poly[j][0]
    return abs(area) / 2 / s1x / s1y


def polarisation(two_theta, beta):
    """1 − (sin 2θ cos β)² (horizontally polarised beam), as the window."""
    return 1 - (np.sin(two_theta) * np.cos(beta)) ** 2


def bin_counts(theta, counts, weights, edges):
    """I = ΣN/ΣW, σ = √ΣN/ΣW per (bin, row): ``theta`` (frames, cols) in the
    units of ``edges``; ``counts``, ``weights`` (frames, rows, cols).
    Returns (I, σ, ΣN, ΣW) with shape (bins, rows); NaN where ΣW = 0."""
    nb = len(edges) - 1
    nf, nr, nc = counts.shape
    idx = np.digitize(theta, edges) - 1                      # (frames, cols)
    sn = np.zeros((nb, nr))
    sw = np.zeros((nb, nr))
    for f in range(nf):
        ok = (idx[f] >= 0) & (idx[f] < nb)
        for c in np.flatnonzero(ok):
            sn[idx[f, c]] += counts[f, :, c]
            sw[idx[f, c]] += weights[f, :, c]
    with np.errstate(invalid='ignore', divide='ignore'):
        i = np.where(sw > 0, sn / sw, np.nan)
        s = np.where(sw > 0, np.sqrt(sn) / sw, np.nan)
    return i, s, sn, sw


def column_response(theta, counts, weights, edges, iterations=20):
    """Column response R(c), mean 1, estimated from the data: alternately
    S(2θ) = ΣN/Σ(W·R) on the bins (rows summed) and R(c) = Σ_f N / Σ_f W·S
    (the review's §7.3). ``weights`` without R; arrays as for bin_counts."""
    n = counts.sum(axis=1)                                   # (frames, cols)
    w = weights.sum(axis=1)
    nb = len(edges) - 1
    idx = np.digitize(theta, edges) - 1
    ok = (idx >= 0) & (idx < nb)
    r = np.ones(n.shape[1])
    for _ in range(iterations):
        sn = np.bincount(idx[ok], weights=n[ok], minlength=nb)
        sw = np.bincount(idx[ok], weights=(w * r)[ok], minlength=nb)
        s = np.where(sw > 0, sn / np.where(sw > 0, sw, 1), 0.0)
        pred = np.where(ok, w * s[np.clip(idx, 0, nb - 1)], 0.0)
        num, den = n.sum(axis=0), pred.sum(axis=0)
        r = np.where(den > 0, num / np.where(den > 0, den, 1), 1.0)
        r = r / r.mean()
    return r


def fit_pinhole_distance(profiles, dth_deg, c0, peak_deg, d_guess, window, half_width=6, min_frames=6):
    """S4 → detector distance (mm) from the drift of a feature at a fixed
    angle ``peak_deg`` (e.g. a Bragg peak): each column profile (frames,
    cols) is divided by the median profile; in every frame where the
    feature is predicted inside ``window`` (columns), with ``d_guess``, its
    centroid is taken within ±``half_width`` columns of the prediction; the
    centroids are fitted linearly against Det_Th (degrees), outliers > 3
    columns dropped, and the fit repeated with the new distance.
    Returns (distance, error, slope in columns per degree, frames used)."""
    prof = np.asarray(profiles, float)
    dth = np.asarray(dth_deg, float)
    med = np.median(prof, axis=0)
    ex_all = prof - med
    k = PIXEL_MM * 180 / math.pi
    d = float(d_guess)
    for _ in range(3):
        pred = c0 + np.tan(np.radians(peak_deg - dth)) * d / PIXEL_MM
        x, y = [], []
        for f in range(len(prof)):
            if not window[0] + half_width <= pred[f] <= window[1] - half_width:
                continue
            lo, hi = int(round(pred[f])) - half_width, int(round(pred[f])) + half_width + 1
            e = np.clip(ex_all[f, lo:hi], 0, None)
            if e.sum() <= 0:
                continue
            x.append(dth[f])
            y.append((np.arange(lo, hi) * e).sum() / e.sum())
        x, y = np.array(x), np.array(y)
        if len(x) < min_frames:
            raise ValueError('the feature is seen in %d frames; at least %d are needed' % (len(x), min_frames))
        ok = np.ones(len(x), bool)
        for _ in range(3):
            (slope, icpt), cov = np.polyfit(x[ok], y[ok], 1, cov=True)
            new = np.abs(y - (slope * x + icpt)) < 3
            if new.sum() < min_frames or (new == ok).all():
                break
            ok = new
        d = abs(slope) * k
    return d, math.sqrt(cov[0, 0]) * k, slope, int(ok.sum())


def frame_weights(g, nrows, ncols, monitor, areainfo, row_lo, row_hi, area=True, pol=True):
    """W = M · A(2θ_c) · P(2θ_c, β_r) for one frame, rows row_lo..row_hi,
    without the column response. ``areainfo`` = (S1h, S1v, S4h, alpha, D_s, D_p)."""
    tt = column_two_theta(ncols, g)
    bb = row_beta(nrows, g)[row_lo:row_hi + 1]
    s1h, s1v, s4h, alpha, d_s, d_p = areainfo
    if area:
        a = np.array([area_fraction(s1h, s1v, s4h, PIXEL_MM, alpha, d_s, d_s - d_p, t) for t in tt])
    else:
        a = np.ones(ncols)
    p = polarisation(tt[None, :], bb[:, None]) if pol else np.ones((len(bb), ncols))
    return monitor * a[None, :] * p


@dataclass
class PinholeFrame:
    """One frame for a pinhole map: raw counts (rows, cols), its monitor,
    geometry, footprint inputs and slits, and the scan it belongs to."""
    counts: np.ndarray
    monitor: float
    geom: FrameGeometry
    areainfo: tuple          # (S1h, S1v, S4h, alpha, D_s, D_p)
    s5: tuple                # (S5 towards low columns, S5 towards high columns), mm
    s1_to_sample_mm: float
    scan: int


def level_map(frames, row_lo, row_hi, response='fit', area=True, pol=True, bin_step_deg=0.0, log=None,
              min_frames=2):
    """Pinhole map of one Qz level: every usable column at its own 2θ,
    binned as ΣN/ΣW; scans of the level joined by one factor each (fitted on
    the rows-summed profiles over their common bins, as the window's
    horizontal join), applied to W. Returns (two_theta_deg (bins),
    beta_deg (rows), I (bins, rows), σ (bins, rows), info). I is per monitor
    count times the level's mean monitor, like the window's GID map. Bins
    seen by fewer than ``min_frames`` frames (the edges, through the weakest
    columns only) are left out."""
    ncols = frames[0].counts.shape[1]
    nrows = frames[0].counts.shape[0]
    g0 = frames[0].geom
    step = bin_step_deg if bin_step_deg > 0 else math.degrees(PIXEL_MM / g0.d_pinhole)
    theta, n, w = [], [], []
    for f in frames:
        cols = usable_columns(f.geom, ncols, f.s5[0], f.s5[1], f.areainfo[1], f.s1_to_sample_mm)
        tt = np.full(ncols, np.nan)
        tt[cols] = np.degrees(column_two_theta(ncols, f.geom))[cols]
        theta.append(tt)
        n.append(np.asarray(f.counts, float)[row_lo:row_hi + 1])
        w.append(frame_weights(f.geom, nrows, ncols, f.monitor, f.areainfo, row_lo, row_hi, area, pol))
    theta, n, w = np.array(theta), np.array(n), np.array(w)
    n = np.where(np.isfinite(theta)[:, None, :], np.clip(n, 0, None), 0.0)   # masked pixels (< 0) count nothing
    lo, hi = np.nanmin(theta), np.nanmax(theta)
    edges = lo - step / 2 + step * np.arange(int(math.ceil((hi - lo) / step)) + 2)
    thet = np.where(np.isfinite(theta), theta, -1e9)
    r = column_response(thet, n, w, edges) if response == 'fit' else np.ones(ncols)
    w = w * r[None, None, :]
    scans = sorted(set(f.scan for f in frames))
    factors = {scans[0]: (1.0, 0.0)}
    if len(scans) > 1:
        sel = [np.array([f.scan == sc for f in frames]) for sc in scans]
        ref_i, ref_s, ref_n, ref_w = bin_counts(thet[sel[0]], n[sel[0]], w[sel[0]], edges)
        prof0 = np.nansum(ref_n, axis=1), np.nansum(ref_w, axis=1)
        for sc, m in zip(scans[1:], sel[1:]):
            _, _, sn, sw = bin_counts(thet[m], n[m], w[m], edges)
            a, b = np.nansum(sn, axis=1), np.nansum(sw, axis=1)
            ok = (prof0[1] > 0) & (b > 0) & (prof0[0] > 0) & (a > 0)
            ratio = (prof0[0][ok] / prof0[1][ok]) / (a[ok] / b[ok])
            err = ratio * np.sqrt(1 / prof0[0][ok] + 1 / a[ok])
            wt = 1 / err ** 2
            fac = float(np.sum(wt * ratio) / np.sum(wt))
            ferr = float(np.sum(wt) ** -0.5)
            chi2 = float(np.sum(wt * (ratio - fac) ** 2) / max(ok.sum() - 1, 1))
            factors[sc] = (fac, ferr)
            if log is not None:
                x = 0.5 * (edges[:-1] + edges[1:])[ok]
                log.append(dict(kind='horizontal (2theta)', x_from=float(x.min()), x_to=float(x.max()),
                                points=int(ok.sum()), factor=fac, error=ferr, chi2=chi2))
            w[m] = w[m] / fac
    i, s, sn, sw = bin_counts(thet, n, w, edges)
    bidx = np.digitize(thet, edges) - 1
    nframes = np.array([int((bidx == b).any(axis=1).sum()) for b in range(len(edges) - 1)])
    keep = np.all(sw > 0, axis=1) & (nframes >= min_frames)
    centres = 0.5 * (edges[:-1] + edges[1:])
    mean_m = float(np.mean([f.monitor for f in frames]))
    beta = np.degrees(row_beta(nrows, g0))[row_lo:row_hi + 1]
    info = dict(response=r, factors=factors, step_deg=step, counts_used=float(n.sum()),
                sum_counts=sn[keep], sum_weights=sw[keep], frames_per_bin=nframes[keep],
                columns=[(int(np.nanargmin(t)) if np.isfinite(t).any() else -1,
                          int(np.nanargmax(t)) if np.isfinite(t).any() else -1) for t in theta])
    return centres[keep], beta, i[keep] * mean_m, s[keep] * mean_m, info

