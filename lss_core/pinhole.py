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
The angles and windows treat S4 as a line (the centre of its opening); what
its finite opening (S4L + S4R) does — each column's 2θ acceptance and the
ramps at the footprint window's edges — is computed by ``column_acceptance``
and ``s4_window`` (docs/figures/pinhole, case 8), not used in the reduction.
"""
import math
from dataclasses import dataclass

import numpy as np

from .images import PIXEL_MM                    # noqa: E402  Pilatus pixel (mm), written once there
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


def pinhole_distance(g):
    """Slit (S4) → detector distance the exact transform uses: D_p, or the
    sample distance D (no pinhole) when D_p ≤ 0 or Det_Th ≤ 1° (IDL's rule;
    the pinhole formula is singular at Det_Th = 0)."""
    return g.d_pinhole if (g.d_pinhole > 0 and abs(math.degrees(g.dth)) > 1.0) else vertical_distance(g)


def row_beta(nrows, g):
    """β (rad) of every row."""
    r = np.arange(nrows, dtype=float)
    return g.beta0 + np.arctan((r - g.r0) * PIXEL_MM / vertical_distance(g))


def pixel_angles(g, rows, cols):
    """(2θ, β) in radians of every pixel (len(rows) × len(cols)), exactly.

    The transform of Mati Meron's IMG_COO_CONV (docs/reference_code/idl/
    img_coo_conv.pro, version 7.1, "horizontal pinhole configuration"),
    in the reader's orientation (column offsets increase 2θ, row offsets
    increase β): pixel offsets wx = −(c − c0)·p, wy = (r − r0)·p on a flat
    detector perpendicular to the arm at (Det_Th, β0); for the pinhole, wy
    is first reduced so that the vertical angle is the one of the ray from
    the footprint through the S4 slit (a vertical line D_p in front of the
    detector),

        wy ← wy − (D − D_p)(wx sin β0 cos δ + wy sin δ)/(D sin δ − wx cos β0 cos δ),

    then u = wx, v = D_p cos β0 − wy sin β0, w = D_p sin β0 + wy cos β0 and
    2θ = δ − atan2(u, v), β = atan2(w, √(u² + v²)); D = ``vertical_distance``,
    δ = Det_Th. Checked against an independent ray construction
    (tests/test_pinhole.py). Not separable: β depends on the column (each
    column sees another part of the footprint, at another distance) and 2θ
    on the row when the arm is raised. At Det_Th ≤ 1° there is no pinhole
    (IDL's rule; the formula is singular at δ = 0): D_p = D."""
    R, C = np.meshgrid(np.asarray(rows, float), np.asarray(cols, float), indexing='ij')
    wx = -(C - g.c0) * PIXEL_MM
    wy = (R - g.r0) * PIXEL_MM
    wdst = vertical_distance(g)
    pdst = pinhole_distance(g)
    b, d = g.beta0, g.dth
    if wdst != pdst:
        wy = wy - (wdst - pdst) * (wx * math.sin(b) * math.cos(d) + wy * math.sin(d)) / \
            (wdst * math.sin(d) - wx * math.cos(b) * math.cos(d))
    u = wx
    v = pdst * math.cos(b) - wy * math.sin(b)
    w = pdst * math.sin(b) + wy * math.cos(b)
    return d - np.arctan2(u, v), np.arctan2(w, np.hypot(u, v))


@dataclass
class Ray:
    """The ray that reaches one pixel, in the lab frame (mm; x along the
    incident beam, y horizontal in the sample plane, z up; origin at the
    sample centre). Returned by ``ray_geometry``."""
    n: np.ndarray            # unit vector of the arm, at (Det_Th, β0)
    e_h: np.ndarray          # detector's horizontal unit vector (towards lower 2θ)
    e_v: np.ndarray          # detector's vertical unit vector (towards higher β)
    h: np.ndarray            # horizontal unit vector of the arm's azimuth, (cos Det_Th, sin Det_Th, 0)
    centre: np.ndarray       # D·n: the direct-beam pixel (r0, c0)
    pixel: np.ndarray        # the pixel: centre + wx·e_h + wy·e_v
    slit_centre: np.ndarray  # (D − D_p)·n: the middle of the S4 slit line (direction e_v)
    slit: np.ndarray         # where the ray crosses the slit line
    source: np.ndarray       # the footprint point on the beam axis the ray comes from
    direction: np.ndarray    # unit vector, source → pixel
    wx: float                # pixel offsets on the detector (mm), as IMG_COO_CONV
    wy: float
    u: float                 # pixel − slit = u·e_h + v·h + w·z: the (u, v, w) of
    v: float                 # IMG_COO_CONV (after its wy correction), whence
    w: float                 # 2θ = Det_Th − atan2(u, v), β = atan2(w, √(u² + v²))
    two_theta: float         # in-plane angle of the ray (rad)
    beta: float              # exit angle of the ray (rad)


def ray_geometry(g, row, col, slit_offset=0.0):
    """The ray from the footprint (the beam axis) through the S4 slit to the
    pixel (``row``, ``col``; fractional values allowed), built in the lab
    frame without IMG_COO_CONV's algebra: a flat detector perpendicular to
    the arm at (Det_Th, β0), D = ``vertical_distance`` from the sample; the
    slit, a line along e_v at D − D_p (``pinhole_distance``) on the arm; the
    plane through the pixel and the slit line meets the beam axis at the
    source point. Its angles equal ``pixel_angles`` (tests/test_pinhole.py),
    which makes the two an independent check of each other; it also gives
    the points and vectors for drawing (tests/tools/pinhole_figures.py).
    It is the independent reference for ``pixel_angles``: do not build it
    from ``pixel_angles`` or from IMG_COO_CONV's wy correction.

    ``slit_offset`` (mm) moves the slit line sideways, towards higher
    columns (along −e_h), within the S4 opening: the reader's geometry is
    the line through the opening's centre (0, the default); a finite S4
    (S4L + S4R) is the range of offsets (``column_acceptance``,
    ``s4_window``). With an offset, ``slit_centre`` stays the opening's
    centre and (u, v, w) are taken from the offset slit point.

    Raises ValueError when the plane of the pixel and the slit line is
    parallel to the beam axis (the column looks along the beam, 2θ ≈ 0, and
    the source point is at infinity)."""
    D, Dp, b, d = vertical_distance(g), pinhole_distance(g), g.beta0, g.dth
    n = np.array([math.cos(b) * math.cos(d), math.cos(b) * math.sin(d), math.sin(b)])
    eh = np.array([math.sin(d), -math.cos(d), 0.0])
    ev = np.array([-math.sin(b) * math.cos(d), -math.sin(b) * math.sin(d), math.cos(b)])
    wx, wy = -(col - g.c0) * PIXEL_MM, (row - g.r0) * PIXEL_MM
    centre = D * n
    pix = centre + wx * eh + wy * ev
    slit_c = (D - Dp) * n
    line = slit_c - slit_offset * eh if slit_offset else slit_c   # the slit line the ray passes
    if D == Dp:                                                  # no pinhole: rays from the sample centre
        s = 0.0
    else:
        normal = np.cross(pix - line, ev)                        # the plane of the pixel and the slit line
        if abs(normal[0]) <= 1e-12 * np.linalg.norm(normal):
            raise ValueError('pixel (%g, %g): its plane through the slit is parallel to the beam axis '
                             '(source at infinity)' % (row, col))
        s = normal.dot(line) / normal[0]                         # meets the beam axis at (s, 0, 0)
    source = np.array([s, 0.0, 0.0])
    ray = pix - source
    (_, t), *_ = np.linalg.lstsq(np.column_stack([ray, -ev]), line - source, rcond=None)
    slit = line + t * ev
    hd = np.array([math.cos(d), math.sin(d), 0.0])
    pv = pix - slit
    return Ray(n=n, e_h=eh, e_v=ev, h=hd, centre=centre, pixel=pix, slit_centre=slit_c, slit=slit, source=source,
               direction=ray / np.linalg.norm(ray), wx=float(wx), wy=float(wy),
               u=float(pv.dot(eh)), v=float(pv.dot(hd)), w=float(pv[2]),
               two_theta=math.atan2(ray[1], ray[0]), beta=math.atan2(ray[2], math.hypot(ray[0], ray[1])))


def bin_counts_2d(theta, beta, counts, weights, edges, bedges):
    """I = ΣN/ΣW, σ = √ΣN/ΣW per (2θ bin, β bin); every array (frames, rows,
    cols), angles in the units of the edges; NaN angles count nothing.
    Returns (I, σ, ΣN, ΣW) of shape (bins, β bins)."""
    nb, nbb = len(edges) - 1, len(bedges) - 1
    i = np.digitize(theta, edges) - 1
    j = np.digitize(beta, bedges) - 1
    ok = np.isfinite(theta) & np.isfinite(beta) & (i >= 0) & (i < nb) & (j >= 0) & (j < nbb)
    flat = (i * nbb + j)[ok]
    sn = np.bincount(flat, weights=np.asarray(counts, float)[ok], minlength=nb * nbb).reshape(nb, nbb)
    sw = np.bincount(flat, weights=np.asarray(weights, float)[ok], minlength=nb * nbb).reshape(nb, nbb)
    with np.errstate(invalid='ignore', divide='ignore'):
        iv = np.where(sw > 0, sn / sw, np.nan)
        sv = np.where(sw > 0, np.sqrt(sn) / sw, np.nan)
    return iv, sv, sn, sw


def s5_window(g, s5_low, s5_high, d5=S5_TO_DETECTOR_MM, slit_offset=0.0):
    """Columns (lo, hi) the S5 slits let through from the pinhole; ``s5_low``
    opens towards low columns, ``s5_high`` towards high ones (mm).
    ``slit_offset``: seen from a point of the S4 opening that far (mm)
    towards higher columns from its centre (in-plane, as the window)."""
    k = g.d_pinhole / (g.d_pinhole - d5)
    lo, hi = g.c0 - s5_low * k / PIXEL_MM, g.c0 + s5_high * k / PIXEL_MM
    if slit_offset:
        shift = slit_offset * (1 - k) / PIXEL_MM                 # the S5 edges' shadow moves the other way
        lo, hi = lo + shift, hi + shift
    return lo, hi


def footprint_length(g, s1_vertical, s1_to_sample_mm=0.0):
    """Length (mm) of the footprint along the beam, beam / sin α (PD_PIN_RANGE);
    the beam is S1v widened by the slit's diffraction over ``s1_to_sample_mm``.
    Infinite at α ≤ 0."""
    rwid = 1e-4 * g.wavelength / s1_vertical if s1_vertical > 0 else 0.0
    beam = math.sqrt(s1_vertical ** 2 + (1e-3 * s1_to_sample_mm * rwid) ** 2)
    return beam / math.sin(g.alpha) if g.alpha > 0 else float('inf')


def footprint_window(g, s1_vertical, s1_to_sample_mm=0.0):
    """Columns (lo, hi) that see the footprint through the pinhole
    (PD_PIN_RANGE): footprint ftp = beam / sin α, seen from the pinhole at
    the sample → pinhole distance L = D_s − D_p; the angular range is
    ψ = atan(2δ sin Det_Th, 1 − δ²), δ = ftp / 2L, centred on c0 as in IDL.
    ``s1_to_sample_mm`` (g_l2 − g_l1) adds the slit's diffraction width."""
    ftp = footprint_length(g, s1_vertical, s1_to_sample_mm)
    lpin = g.d_sample - g.d_pinhole
    if lpin <= 0 or not math.isfinite(ftp):
        return -math.inf, math.inf                 # no pinhole in front of the sample: no limit
    delta = ftp / (2 * lpin)
    psi = math.atan2(2 * delta * math.sin(g.dth), 1 - delta ** 2)
    half = g.d_pinhole * psi / PIXEL_MM / 2
    return g.c0 - half, g.c0 + half


FOOTPRINT_WINDOWS = ('exact', 'idl')
RAISED_ARM_DEG = 1.0     # above this β0 the exact window keeps IDL's high edge (P40b streak)


def usable_columns(g, ncols, s5_low, s5_high, s1_vertical, s1_to_sample_mm=0.0, d5=S5_TO_DETECTOR_MM,
                   s4_mm=0.0, footprint='exact'):
    """Integer columns inside both the S5 window and the footprint window.

    ``footprint`` 'exact' (default since 2026-11-19, P39, D51): the columns
    that see the footprint through the whole S4 opening ``s4_mm`` (S4L +
    S4R, taken as two equal halves about the slit line), i.e. the inner
    edges of ``s4_window``; with ``s4_mm`` 0, ``footprint_columns``. The
    same on every row (measured at β0 0.09° and 6.5°), so it is traced on
    the direct-beam row. On frames with the arm raised (β0 > ``RAISED_ARM_DEG``)
    the high edge is kept at IDL's: there the added columns pick up a
    sharp-edged streak of stray light (P40b, junk per the owner) until it can
    be masked. 'idl': IDL's PD_PIN_RANGE window (``footprint_window``), the
    right width centred on c0."""
    a, b = s5_window(g, s5_low, s5_high, d5)
    if footprint == 'idl':
        f, h = footprint_window(g, s1_vertical, s1_to_sample_mm)
    elif footprint == 'exact':
        f, h = _exact_window(g, s1_vertical, s1_to_sample_mm, s4_mm)
        if g.beta0 > math.radians(RAISED_ARM_DEG):
            h = min(h, footprint_window(g, s1_vertical, s1_to_sample_mm)[1])
    else:
        raise ValueError('footprint window %r: use one of %s' % (footprint, ', '.join(FOOTPRINT_WINDOWS)))
    lo, hi = max(a, f, 0), min(b, h, ncols - 1)
    return np.arange(int(math.ceil(lo)), int(math.floor(hi)) + 1)


def _exact_window(g, s1_vertical, s1_to_sample_mm, s4_mm):
    """The fully lit footprint window (columns), or no limit where there is
    no pinhole in front of the sample or no footprint (α ≤ 0)."""
    if g.d_sample - g.d_pinhole <= 0 or not math.isfinite(footprint_length(g, s1_vertical, s1_to_sample_mm)):
        return -math.inf, math.inf
    half = footprint_length(g, s1_vertical, s1_to_sample_mm) / 2
    t = s4_mm / 2
    edges = []
    for x, side in ((-half, -math.inf), (half, math.inf)):
        try:                                       # fully lit: the inner of the two slit edges' columns
            cs = [column_at_source(g, x, slit_offset=o) for o in ((-t, t) if t > 0 else (0.0,))]
            edges.append(max(cs) if x < 0 else min(cs))
        except ValueError:                         # no column sees that end: no limit on that side
            edges.append(side)
    return edges[0], edges[1]


def frame_columns(f, ncols):
    """``usable_columns`` of a PinholeFrame, with its S4 opening and its
    footprint window choice (``f.footprint``)."""
    return usable_columns(f.geom, ncols, f.s5[0], f.s5[1], f.areainfo[1], f.s1_to_sample_mm,
                          s4_mm=f.areainfo[2], footprint=f.footprint)


def column_at_source(g, x, row=None, slit_offset=0.0):
    """The (fractional) column whose ray through the S4 slit line (at
    ``slit_offset``, see ``ray_geometry``) starts at ``x`` mm on the beam
    axis; ``row`` defaults to the direct-beam row r0. The inverse of
    ``ray_geometry``'s source point, in closed form: the plane through the
    slit line (point L, direction e_v) and the source S = (x, 0, 0) has the
    normal N = (L − S) × e_v, and a pixel of the row, P = centre + w_x e_h +
    w_y e_v, lies in it when N·(P − L) = 0, which is linear in w_x (N·e_v =
    0). The ray to that column is then checked to start at ``x`` and to run
    forward. Raises ValueError when no column sees ``x`` (beyond L/cos
    Det_Th, L the sample → slit distance, or behind the column that looks
    along the beam). Same columns as the bisection it replaced
    (``_column_at_source_bisection``, kept as the reference) to 1e-9; it
    took 85 % of a distance calibration (2026-11-23)."""
    row = g.r0 if row is None else row
    D, Dp, b, d = vertical_distance(g), pinhole_distance(g), g.beta0, g.dth
    if D == Dp:                                   # no pinhole: every ray starts at the sample centre
        return _column_at_source_bisection(g, x, row, slit_offset)
    n = np.array([math.cos(b) * math.cos(d), math.cos(b) * math.sin(d), math.sin(b)])
    eh = np.array([math.sin(d), -math.cos(d), 0.0])
    ev = np.array([-math.sin(b) * math.cos(d), -math.sin(b) * math.sin(d), math.cos(b)])
    line = (D - Dp) * n - slit_offset * eh
    normal = np.cross(line - np.array([x, 0.0, 0.0]), ev)
    ne = normal.dot(eh)
    if abs(ne) <= 1e-12 * np.linalg.norm(normal):
        raise ValueError('no column sees x = %g mm' % x)
    wy = (row - g.r0) * PIXEL_MM
    wx = -(normal.dot(D * n - line) + wy * normal.dot(ev)) / ne
    c = g.c0 - wx / PIXEL_MM

    def facing(w):                                 # x component of the pixel's plane normal: 0 at the column
        return np.cross(D * n + w * eh + wy * ev - line, ev)[0]   # that looks along the beam
    if not facing(wx) * facing(0.0) > 0:           # the other branch, beyond that column: no ray reaches x
        raise ValueError('no column sees x = %g mm' % x)
    try:
        r = ray_geometry(g, row, c, slit_offset)
    except ValueError:
        raise ValueError('no column sees x = %g mm' % x) from None
    if not (r.direction.dot(r.n) > 0 and abs(r.source[0] - x) <= 1e-6 * max(1.0, abs(x))):
        raise ValueError('no column sees x = %g mm' % x)
    return float(c)


def _column_at_source_bisection(g, x, row=None, slit_offset=0.0):
    """``column_at_source`` by bisection (until 2026-11-23): the source
    point grows with the column, from −∞ (the column that looks along the
    beam) to L/cos Det_Th at infinity. The reference for the closed form
    (tests/test_pinhole.py)."""
    row = g.r0 if row is None else row

    def src(c):                                   # source x, or None where the ray does not run forward
        try:
            r = ray_geometry(g, row, c, slit_offset)
        except ValueError:
            return None
        return r.source[0] if r.direction.dot(r.n) > 0 else None

    c0 = float(g.c0)
    s0 = src(c0)
    if s0 is None:
        raise ValueError('the direct-beam column has no ray from the beam axis')
    a, step = c0, 1.0                             # a: the side of the target the bracket starts from
    if s0 < x:                                    # go to higher columns
        b = c0 + step
        while (sb := src(b)) is not None and sb < x:
            a, step = b, 2 * step
            b = c0 + step
            if step > 1e7:
                raise ValueError('no column sees x = %g mm' % x)
        if sb is None:
            raise ValueError('no column sees x = %g mm' % x)
    else:                                         # go to lower columns, stopping short of 2θ = 0
        b = c0 - step
        bad = None                                # nearest column known to have no forward ray
        for _ in range(500):
            sb = src(b)
            if sb is None:                        # past the column that looks along the beam: come back
                bad = b
                b = 0.5 * (a + b)
            elif sb <= x:
                break
            else:                                 # still upstream of x: move on, never past ``bad``
                a = b
                if bad is None:
                    step *= 2
                    b = c0 - step
                else:
                    b = 0.5 * (a + bad)
            if bad is not None and abs(a - bad) < 1e-9:
                raise ValueError('no column sees x = %g mm' % x)
        else:
            raise ValueError('no column sees x = %g mm' % x)
    lo, hi = sorted((a, b))
    flo = src(lo) - x
    for _ in range(100):
        m = 0.5 * (lo + hi)
        fm = src(m) - x
        if (fm < 0) == (flo < 0):
            lo, flo = m, fm
        else:
            hi = m
        if hi - lo < 1e-10:
            break
    return 0.5 * (lo + hi)


def footprint_columns(g, s1_vertical, s1_to_sample_mm=0.0, row=None, slit_offset=0.0):
    """The exact footprint window: the (fractional) columns (first, last)
    whose rays through the S4 slit line (at ``slit_offset``) start at the
    footprint's upstream (−L/2) and downstream (+L/2) ends, L =
    ``footprint_length``; ``row`` defaults to r0. ``footprint_window``
    (PD_PIN_RANGE) has the same width but is centred on c0 (P39)."""
    half = footprint_length(g, s1_vertical, s1_to_sample_mm) / 2
    return (column_at_source(g, -half, row, slit_offset), column_at_source(g, half, row, slit_offset))


def s4_window(g, s1_vertical, s4_low, s4_high, s1_to_sample_mm=0.0, row=None):
    """The footprint window through an S4 of finite opening, ``s4_low`` mm
    towards low columns and ``s4_high`` towards high ones from the line the
    reader uses (S4L, S4R as S5L, S5R are taken). Returns (outer, inner),
    each (lo, hi): ``outer``, the columns that see some of the footprint
    through some part of the opening (where light starts); ``inner``, those
    that see it through all of the opening (fully lit). Between the two
    each edge of the window is a ramp, not a step. Exact rays
    (``ray_geometry``) on row ``row`` (default r0)."""
    a = footprint_columns(g, s1_vertical, s1_to_sample_mm, row, -s4_low)
    b = footprint_columns(g, s1_vertical, s1_to_sample_mm, row, s4_high)
    return (min(a[0], b[0]), max(a[1], b[1])), (max(a[0], b[0]), min(a[1], b[1]))


@dataclass
class Acceptance:
    """The rays one pixel accepts through a finite S4 (``column_acceptance``):
    arrays (pixel positions, slit positions)."""
    columns: np.ndarray       # fractional column of each ray's landing point
    offsets: np.ndarray       # slit offset of each ray (mm towards higher columns)
    source_x: np.ndarray      # where each ray starts on the beam axis (mm)
    two_theta: np.ndarray     # in-plane angle (rad)
    beta: np.ndarray          # exit angle (rad)

    def lit_fraction(self, footprint_length_mm):
        """Fraction of the pixel's acceptance whose rays start on a footprint
        of this length (centred on the sample): how much of the column is
        lit. Trapezoid weights over the evenly spread rays (ends half)."""
        w = np.outer(_trapezoid(self.source_x.shape[0]), _trapezoid(self.source_x.shape[1]))
        return float(np.sum(w * (np.abs(self.source_x) <= footprint_length_mm / 2)) / np.sum(w))

    def throughput(self, footprint_length_mm):
        """Pixel width × S4 opening (mm²) × ``lit_fraction``: proportional
        to the counts the column collects from a uniform footprint (the
        rays' measure; the small change of distance across the bundle is
        ignored). Needs the pixel's width (``pixel=True``)."""
        width = (self.columns.max() - self.columns.min()) * PIXEL_MM
        return float(width * (self.offsets.max() - self.offsets.min()) * self.lit_fraction(footprint_length_mm))


def _trapezoid(n):
    w = np.ones(n)
    if n > 1:
        w[[0, -1]] = 0.5
    return w


def column_acceptance(g, col, s4_low, s4_high, row=None, n=11, pixel=True):
    """The rays pixel (``row``, ``col``) accepts through an S4 opening
    ``s4_low`` + ``s4_high`` mm (see ``s4_window``): ``n`` evenly spread
    points across the pixel's width, its edges included (column ± ½;
    ``pixel=False``: its centre only), times ``n`` across the opening, its
    edges included, each traced by ``ray_geometry``. The spread of ``two_theta`` is the column's 2θ
    acceptance (its resolution; the reader gives the column the angle of
    the centre ray), the spread of ``source_x`` the stretch of footprint it
    sees. ``row`` defaults to r0."""
    row = g.r0 if row is None else row
    k = np.linspace(0.0, 1.0, n)
    cols = col - 0.5 + k if pixel else np.array([float(col)])
    offs = -s4_low + (s4_low + s4_high) * k if (s4_low + s4_high) > 0 else np.array([0.0])
    rays = [[ray_geometry(g, row, c, t) for t in offs] for c in cols]
    get = lambda f: np.array([[f(r) for r in line] for line in rays])
    return Acceptance(columns=np.repeat(cols[:, None], len(offs), axis=1),
                      offsets=np.repeat(offs[None, :], len(cols), axis=0),
                      source_x=get(lambda r: r.source[0]), two_theta=get(lambda r: r.two_theta),
                      beta=get(lambda r: r.beta))


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


def column_response(theta, counts, weights, edges, iterations=20, scans=None):
    """Column response R(c), mean 1, estimated from the data: alternately
    S(2θ) = ΣN/Σ(W·R) on the bins (rows summed) and R(c) = Σ_f N / Σ_f W·S
    (the review's §7.3). ``weights`` without R; arrays as for bin_counts.
    ``scans`` (the scan of each frame; per-pixel angles only): each scan then
    gets its own scale in the same alternation, so that R does not take up a
    scale between scans (P42; owner, 2026-11-20)."""
    if np.ndim(theta) == 3:                                  # per-pixel angles (pixel_angles)
        return _column_response_pixels(theta, counts, weights, edges, iterations, scans)
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


def _column_response_pixels(theta, counts, weights, edges, iterations=20, scans=None):
    """column_response with an angle per pixel (frames, rows, cols)."""
    nb = len(edges) - 1
    idx = np.digitize(theta, edges) - 1
    ok = np.isfinite(theta) & (idx >= 0) & (idx < nb)
    ncol = counts.shape[2]
    cidx = np.broadcast_to(np.arange(ncol), counts.shape)
    n_ok, w_ok, i_ok, c_ok = counts[ok], weights[ok], idx[ok], cidx[ok]
    if scans is not None and len(set(scans)) > 1:
        sc = np.broadcast_to(np.unique(scans, return_inverse=True)[1][:, None, None], counts.shape)[ok]
        nsc = int(sc.max()) + 1
        nscan = np.bincount(sc, weights=n_ok, minlength=nsc)
    else:
        sc, nsc = np.zeros(len(n_ok), int), 1
    fs = np.ones(nsc)
    num = np.bincount(c_ok, weights=n_ok, minlength=ncol)
    r = np.ones(ncol)
    for _ in range(iterations):
        sn = np.bincount(i_ok, weights=n_ok, minlength=nb)
        sw = np.bincount(i_ok, weights=w_ok * r[c_ok] * fs[sc], minlength=nb)
        s = np.where(sw > 0, sn / np.where(sw > 0, sw, 1), 0.0)
        if nsc > 1:
            fs = nscan / np.maximum(np.bincount(sc, weights=w_ok * r[c_ok] * s[i_ok], minlength=nsc), 1e-300)
            fs = fs / fs[0]
        den = np.bincount(c_ok, weights=w_ok * fs[sc] * s[i_ok], minlength=ncol)
        r = np.where(den > 0, num / np.where(den > 0, den, 1), 1.0)
        r = r / r[den > 0].mean() if (den > 0).any() else r
        r[den <= 0] = 1.0
    return r


BEAM_BIN_MM = 1.0      # bins of the beam-axis response (mm along the beam)


def source_positions(frames, ncols):
    """Where on the beam axis (mm, x) each column of each frame looks
    through S4 (``ray_geometry``'s source point at the direct-beam row);
    NaN where no ray runs forward. Shape (frames, cols)."""
    out = np.full((len(frames), ncols), np.nan)
    for k, f in enumerate(frames):
        for c in range(ncols):
            try:
                out[k, c] = ray_geometry(f.geom, f.geom.r0, c).source[0]
            except ValueError:
                pass
    return out


def beam_response(theta, counts, weights, edges, xsrc, bin_mm=BEAM_BIN_MM, iterations=20, scans=None):
    """The response as a function of the point on the beam axis a column
    looks at (owner, 2026-11-19): one profile R(x), shared by all frames,
    estimated as ``column_response`` does (alternately S(2θ) = ΣN/Σ(W·R) and
    R(x) = ΣN / ΣW·S), with x per (frame, column) from ``source_positions``.
    A per-column response cannot follow the light a column receives when the
    column-to-beam-axis mapping changes with Det_Th, as it does with a narrow
    Gaussian beam (physics_notes 2026-11-19). Returns (R per frame and column,
    (x bin centres, R(x))), R normalised to mean 1 over the bins with light."""
    nb = len(edges) - 1
    idx = np.digitize(theta, edges) - 1
    fin = np.isfinite(xsrc)
    x0 = np.nanmin(xsrc[fin]) if fin.any() else 0.0
    xb = np.where(fin, np.floor((np.where(fin, xsrc, x0) - x0) / bin_mm).astype(int), -1)
    nx = int(xb.max()) + 1 if fin.any() else 1
    xpix = np.broadcast_to(xb[:, None, :], counts.shape)
    ok = np.isfinite(theta) & (idx >= 0) & (idx < nb) & (xpix >= 0)
    n_ok, w_ok, i_ok, x_ok = counts[ok], weights[ok], idx[ok], xpix[ok]
    if scans is not None and len(set(scans)) > 1:           # each scan its own scale (P42)
        sc = np.broadcast_to(np.unique(scans, return_inverse=True)[1][:, None, None], counts.shape)[ok]
        nsc = int(sc.max()) + 1
        nscan = np.bincount(sc, weights=n_ok, minlength=nsc)
    else:
        sc, nsc = np.zeros(len(n_ok), int), 1
    fs = np.ones(nsc)
    num = np.bincount(x_ok, weights=n_ok, minlength=nx)
    r = np.ones(nx)
    for _ in range(iterations):
        sn = np.bincount(i_ok, weights=n_ok, minlength=nb)
        sw = np.bincount(i_ok, weights=w_ok * r[x_ok] * fs[sc], minlength=nb)
        sv = np.where(sw > 0, sn / np.where(sw > 0, sw, 1), 0.0)
        if nsc > 1:
            fs = nscan / np.maximum(np.bincount(sc, weights=w_ok * r[x_ok] * sv[i_ok], minlength=nsc), 1e-300)
            fs = fs / fs[0]
        den = np.bincount(x_ok, weights=w_ok * fs[sc] * sv[i_ok], minlength=nx)
        r = np.where(den > 0, num / np.where(den > 0, den, 1), 0.0)
        lit = den > 0
        if lit.any() and r[lit].mean() > 0:
            r = r / r[lit].mean()
    per = np.where(xb >= 0, r[np.clip(xb, 0, nx - 1)], 1.0)
    centres = x0 + bin_mm * (np.arange(nx) + 0.5)
    return per, (centres, r)


def profile_width(x, r):
    """(centre, FWHM) of a profile R(x): centre of mass of the part above
    half its maximum, FWHM between the first and last points above half."""
    r = np.asarray(r, float)
    if not len(r) or r.max() <= 0:
        return float('nan'), float('nan')
    top = r >= 0.5 * r.max()
    k = np.flatnonzero(top)
    return float(np.sum(x[top] * r[top]) / np.sum(r[top])), float(x[k[-1]] - x[k[0]])


BEAM_H_FWHM_MM = 1.0     # horizontal beam FWHM by default (owner's rough estimate, 2026-11-19)
_K = 2 * math.sqrt(2 * math.log(2))     # FWHM / σ


def source_x(g, row, cols, slit_offsets):
    """Where on the beam axis (mm) the rays through columns ``cols``
    (fractional, any shape) and the S4 slit line at ``slit_offsets`` (mm,
    broadcast against ``cols``) start: ``ray_geometry``'s source point,
    vectorised (the same construction; checked against it in the tests).
    NaN where the column looks along the beam."""
    D, Dp, b, d = vertical_distance(g), pinhole_distance(g), g.beta0, g.dth
    cols, t = np.broadcast_arrays(np.asarray(cols, float), np.asarray(slit_offsets, float))
    if D == Dp:
        return np.zeros(cols.shape)
    n = np.array([math.cos(b) * math.cos(d), math.cos(b) * math.sin(d), math.sin(b)])
    eh = np.array([math.sin(d), -math.cos(d), 0.0])
    ev = np.array([-math.sin(b) * math.cos(d), -math.sin(b) * math.sin(d), math.cos(b)])
    wx, wy = -(cols - g.c0) * PIXEL_MM, (row - g.r0) * PIXEL_MM
    pix = D * n + wx[..., None] * eh + wy * ev
    line = (D - Dp) * n - t[..., None] * eh
    normal = np.cross(pix - line, ev)
    with np.errstate(invalid='ignore', divide='ignore'):
        s = np.einsum('...k,...k->...', normal, line) / normal[..., 0]
    bad = np.abs(normal[..., 0]) <= 1e-12 * np.linalg.norm(normal, axis=-1)
    return np.where(bad, np.nan, s)


@dataclass
class BeamModel:
    """The beam as the physical response sees it (owner, 2026-11-20): a
    Gaussian vertical profile of FWHM ``fwhm_um`` whose centre meets the
    surface at ``centre_mm`` along the beam (x = 0 at the sample centre,
    positive downstream), clipped by S1 to the footprint S1v / sin α centred
    on x = 0, and a Gaussian horizontal profile of FWHM ``h_fwhm_mm``."""
    centre_mm: float
    fwhm_um: float
    h_fwhm_mm: float = BEAM_H_FWHM_MM


class PhysicalResponse:
    """The column response from the geometry and the beam, not fitted per
    column (owner, 2026-11-20: "go ahead with physical model").

    For each frame and usable column, rays are traced through ``n_pixel``
    points across the column's pixel and ``n_slit`` points across the S4
    opening (``source_x``) to the point of the beam axis each starts from;
    a point at lateral offset y on the column's line of sight sits at x + y
    cot 2θ, so the beam's horizontal profile is folded in with Gauss–Hermite
    points. The light a column records is the mean over those rays of the
    beam's illumination B(x) = g((x − x0) sin α) sin α / Γ on the footprint,
    g the vertical profile, Γ the fraction of it S1 lets through, so that ∫B
    dx = 1 over the footprint: the column's share of the beam, in absolute
    terms. The response is that light times the footprint length L, so that
    a uniformly lit footprint gives 1 everywhere: no normalisation to a mean
    of 1, and every level keeps its own scale. It replaces the uniform-
    footprint area correction (it includes it)."""

    def __init__(self, frames, cols, n_pixel=3, n_slit=3, n_y=5):
        self.frames = frames
        self.cols = cols                                     # usable columns of each frame
        up = (np.arange(n_pixel) + 0.5) / n_pixel - 0.5      # midpoints across the pixel
        ys, yw = np.polynomial.hermite_e.hermegauss(n_y)
        self.yz, self.yw = ys, yw / yw.sum()
        self.x, self.cot = [], []
        for f, c in zip(frames, cols):
            s4 = float(f.areainfo[2])
            ts = ((np.arange(n_slit) + 0.5) / n_slit - 0.5) * s4 if s4 > 0 else np.zeros(1)
            cc = np.asarray(c, float)[:, None, None] + up[None, :, None]
            self.x.append(source_x(f.geom, f.geom.r0, cc, ts[None, None, :]).reshape(len(c), -1))
            tt = pixel_angles(f.geom, [f.geom.r0], np.asarray(c))[0][0]
            self.cot.append(1.0 / np.tan(tt))

    def light(self, beam):
        """Response per frame: arrays over each frame's usable columns."""
        out = []
        for f, x, cot in zip(self.frames, self.x, self.cot):
            alpha = f.geom.alpha
            half = footprint_length(f.geom, f.areainfo[1], f.s1_to_sample_mm) / 2
            sv = beam.fwhm_um * 1e-3 / _K
            sh = beam.h_fwhm_mm / _K
            z0 = beam.centre_mm * math.sin(alpha)
            # the fraction of the vertical profile S1 passes (S1 centred on the axis: |z| <= L/2 sin α)
            zc = half * math.sin(alpha)
            gamma = 0.5 * (math.erf((zc - z0) / (sv * math.sqrt(2))) + math.erf((zc + z0) / (sv * math.sqrt(2))))
            xs = x[:, :, None] + (self.yz * sh)[None, None, :] * cot[:, None, None]
            z = xs * math.sin(alpha)
            g = np.exp(-0.5 * ((z - z0) / sv) ** 2) / (sv * math.sqrt(2 * math.pi))
            b = np.where(np.abs(xs) <= half, g * math.sin(alpha), 0.0) / max(gamma, 1e-12)
            lit = np.nansum(b * self.yw[None, None, :], axis=2).mean(axis=1)
            out.append(lit * 2 * half)
        return out


def fit_beam(resp, theta_cols, n_cols, w_cols, edges, h_fwhm_mm=BEAM_H_FWHM_MM, centre_mm=None, fwhm_um=None,
             start=None, scans=None):
    """Fit the beam's centre and vertical FWHM (those not given) to one
    level's data: per frame and usable column, rows-summed counts N and
    weights W (without response), and the column's 2θ; the model is N = W ·
    R(beam) · S(2θ bin), S estimated for each trial; minimises the Poisson
    χ² Σ(N − W R S)² / max(W R S, 1). ``scans``: the scan of each frame;
    each scan then has its own scale in the fit (a nuisance parameter), so
    that a scale between scans is not taken up by the beam (scans that cover
    different Det_Th see the beam axis through different columns, and a
    shifted beam would otherwise mimic their scale; P42). Returns
    (BeamModel, χ²/dof)."""
    from scipy.optimize import minimize
    nb = len(edges) - 1
    idx = [np.clip(np.digitize(t, edges) - 1, 0, nb - 1) for t in theta_cols]
    ok = [np.isfinite(t) & (np.digitize(t, edges) - 1 >= 0) & (np.digitize(t, edges) - 1 < nb) for t in theta_cols]
    I = np.concatenate([i[o] for i, o in zip(idx, ok)])
    N = np.concatenate([n[o] for n, o in zip(n_cols, ok)])
    W = np.concatenate([w[o] for w, o in zip(w_cols, ok)])
    sc_of = np.zeros(len(theta_cols), int) if scans is None else np.unique(scans, return_inverse=True)[1]
    SC = np.concatenate([np.full(int(o.sum()), sc_of[k]) for k, o in enumerate(ok)])
    nsc = int(SC.max()) + 1 if len(SC) else 1

    def model(p):
        c = centre_mm if centre_mm is not None else p[0]
        v = fwhm_um if fwhm_um is not None else abs(p[-1])
        beam = BeamModel(float(c), float(max(v, 1.0)), h_fwhm_mm)
        R = np.concatenate([r[o] for r, o in zip(resp.light(beam), ok)])
        return beam, W * R

    def chi2(p):
        _, wr = model(p)
        fs = np.ones(nsc)
        sn = np.bincount(I, weights=N, minlength=nb)
        for _ in range(8 if nsc > 1 else 1):
            sw = np.bincount(I, weights=wr * fs[SC], minlength=nb)
            s = np.where(sw > 0, sn / np.where(sw > 0, sw, 1), 0.0)
            if nsc > 1:
                fs = np.bincount(SC, weights=N, minlength=nsc) / np.maximum(
                    np.bincount(SC, weights=wr * s[I], minlength=nsc), 1e-300)
                fs = fs / fs[0]
        mu = wr * fs[SC] * s[I]
        return float(np.sum((N - mu) ** 2 / np.maximum(mu, 1.0)))

    free = []
    if centre_mm is None:
        free.append(0.0 if start is None else start[0])
    if fwhm_um is None:
        f0 = resp.frames[0]
        free.append((f0.areainfo[1] * 1e3 * 0.6) if start is None else start[1])
    if free:
        best = None
        for s0 in ([free] if centre_mm is not None or len(free) == 1 else
                   [free, [free[0] - 10.0, free[1]], [free[0] + 10.0, free[1]]]):
            r = minimize(chi2, np.array(s0, float), method='Nelder-Mead',
                         options=dict(xatol=0.05, fatol=1e-3, maxiter=400))
            if best is None or r.fun < best.fun:
                best = r
        p = best.x
    else:
        p = np.zeros(0)
    beam, _ = model(p if len(p) else [0.0])
    dof = max(len(N) - nb - len(free) - (nsc - 1), 1)
    return beam, chi2(p if len(p) else [0.0]) / dof


def two_theta_resolution(f):
    """Full width (degrees) of the 2θ one column accepts through S4's opening
    and its own pixel width (``column_acceptance`` at the direct-beam column
    of frame ``f``), and S4's opening (mm)."""
    s4 = float(f.areainfo[2])
    acc = column_acceptance(f.geom, int(round(f.geom.c0)), s4 / 2, s4 / 2)
    return float(np.degrees(np.ptp(acc.two_theta))), s4


def _gauss_line(x, a, c, s, b0, b1):
    return a * np.exp(-0.5 * ((x - c) / s) ** 2) + b0 + b1 * (x - c)


def single_frame_peaks(level, peak_deg, half_deg=0.4, rows=None, distance=None):
    """A peak fitted in every single frame of ``level`` that holds it, with
    no patching (owner, 2026-11-21: an unpatched frame is the ground truth
    for a peak's position and width). Each frame's usable columns, exact
    per-pixel 2θ at S4–detector ``distance`` (mm; None: the frames' own),
    each column's counts over ``rows`` (first, last) per monitor count at
    the column's mean 2θ (no binning: a fixed 2θ grid aliases the columns
    and biases the centre by ±0.02°), a Gaussian on a line over peak_deg ±
    half_deg. Frames whose fit
    fails or is implausible are left out. Returns an array of rows (Det_Th,
    centre, its error, FWHM, its error), degrees."""
    from dataclasses import replace
    from . import peaks
    out = []
    for f in level:
        g = f.geom if distance is None else replace(f.geom, d_pinhole=float(distance))
        r0, r1 = rows if rows is not None else (0, f.counts.shape[0] - 1)
        cols = frame_columns(replace(f, geom=g), f.counts.shape[1])
        if len(cols) < 3:
            continue
        tt, _ = pixel_angles(g, np.arange(r0, r1 + 1), cols)
        x = np.degrees(tt).mean(axis=0)                       # each column at its own mean 2θ: no binning
        n = np.clip(np.asarray(f.counts, float)[r0:r1 + 1][:, cols], 0, None).sum(axis=0)
        if not (x.min() < peak_deg - half_deg and x.max() > peak_deg + half_deg):
            continue
        ok = np.abs(x - peak_deg) <= half_deg
        if ok.sum() < 8:
            continue
        nrow = r1 - r0 + 1
        x, y, e = x[ok], n[ok] / f.monitor / nrow, np.sqrt(np.maximum(n[ok], 1)) / f.monitor / nrow
        r = peaks.fit(x, y, e, peaks.FitOptions(shape='gaussian', background='linear', n_peaks=1,
                                                centres=(float(x[np.argmax(y)]),), window=2 * half_deg,
                                                scale_errors=True))
        if not r.ok or not r.peaks:
            continue
        p = r.peaks[0]
        if np.isfinite(p.centre_err) and p.centre_err < 0.02 and 0.02 < p.fwhm < 4 * half_deg and \
                abs(p.centre - peak_deg) < half_deg:
            out.append((math.degrees(f.geom.dth), p.centre, p.centre_err, p.fwhm, p.fwhm_err))
    return np.array(out).reshape(-1, 5)


def frames_agree(peaks):
    """(weighted mean centre, its error, χ²/dof of the centres about it,
    drift of the centre with Det_Th in deg/deg, median FWHM) of
    ``single_frame_peaks``."""
    w = 1 / peaks[:, 2] ** 2
    m = float(np.sum(w * peaks[:, 1]) / w.sum())
    chi = float(np.sum(w * (peaks[:, 1] - m) ** 2) / max(len(peaks) - 1, 1))
    drift = float(np.polyfit(peaks[:, 0], peaks[:, 1], 1, w=1 / peaks[:, 2])[0]) if len(peaks) > 2 else float('nan')
    return m, float(w.sum() ** -0.5), chi, drift, float(np.median(peaks[:, 3]))


def rows_for_beta(f, beta_deg):
    """Detector rows whose β (at the direct-beam column) lies in
    ``beta_deg`` (low, high), as (first, last)."""
    rows = np.arange(f.counts.shape[0])
    _, bb = pixel_angles(f.geom, rows, [f.geom.c0])
    b = np.degrees(bb[:, 0])
    sel = rows[(b >= beta_deg[0]) & (b <= beta_deg[1])]
    return (int(sel.min()), int(sel.max())) if len(sel) else (0, f.counts.shape[0] - 1)


def strongest_peak(level, rows, half_deg=0.4, min_frames=6, all_candidates=False):
    """2θ (deg) of the strongest narrow feature of a level: the frames'
    counts per monitor binned in 2θ (no response), minus a running median
    over ±1°, the maximum among the bins whose whole window ± ``half_deg``
    lies inside at least ``min_frames`` frames (owner: the largest peak by
    default)."""
    step = math.degrees(PIXEL_MM / level[0].geom.d_pinhole)
    ts, ns, ws = [], [], []
    for f in level:
        cols = frame_columns(f, f.counts.shape[1])
        tt, _ = pixel_angles(f.geom, np.arange(rows[0], rows[1] + 1), cols)
        ts.append(np.degrees(tt).ravel())
        ns.append(np.clip(np.asarray(f.counts, float)[rows[0]:rows[1] + 1][:, cols], 0, None).ravel())
        ws.append(np.full(tt.size, f.monitor))
    t, n, w = np.concatenate(ts), np.concatenate(ns), np.concatenate(ws)
    edges = np.arange(t.min(), t.max() + step, step)
    sn = np.histogram(t, edges, weights=n)[0]
    sw = np.histogram(t, edges, weights=w)[0]
    x = 0.5 * (edges[1:] + edges[:-1])
    nf = np.zeros(len(edges) - 1)                     # frames that hold the whole window x ± half_deg
    for tf in ts:
        nf += (tf.min() < x - half_deg) & (tf.max() > x + half_deg)
    prof = np.where(sw > 0, sn / np.where(sw > 0, sw, 1), np.nan)
    k = max(int(round(1.0 / step)), 3)
    base = np.array([np.nanmedian(prof[max(i - k, 0):i + k + 1]) for i in range(len(prof))])
    ok = (nf >= min_frames) & np.isfinite(prof)
    if not ok.any():
        raise ValueError('the level covers too little 2theta for a peak window')
    cands = peak_candidates(x, prof - base, ok, half_deg)
    return cands if all_candidates else float(cands[0])


def peak_candidates(x, excess, ok, half_deg, n=5):
    """Up to ``n`` positions of the largest ``excess`` among ``ok`` bins, at
    least 2 × ``half_deg`` apart, strongest first."""
    order = np.argsort(np.where(ok, excess, -np.inf))[::-1]
    out = []
    for i in order:
        if not ok[i] or not np.isfinite(excess[i]):
            break
        if all(abs(x[i] - c) >= 2 * half_deg for c in out):
            out.append(float(x[i]))
        if len(out) == n:
            break
    return out


@dataclass
class DistanceCalibration:
    """``calibrate_distance``'s result. ``distance_mm`` ± ``error_mm``: the
    S4–detector distance at which the single frames agree best;
    ``header_mm``: the frames' own (header) value; ``peak_deg``, ``rows``,
    ``half_deg``: what was fitted; ``frames``: frames used at the best
    distance; ``chi2_dof``, ``drift``: their agreement and drift there;
    ``chi2_dof_header``, ``drift_header``: the same at the header distance;
    ``scan``: rows (distance, frames, centre, χ²/dof, drift, median FWHM);
    ``reliable``: enough frames, χ²/dof ≤ ``MAX_CAL_CHI2``, no residual drift
    (|drift| ≤ 0.01 deg/deg), the best distance inside the scanned range and
    an error below 5 mm; ``why``: what failed otherwise."""
    distance_mm: float
    error_mm: float
    header_mm: float
    peak_deg: float
    rows: tuple
    half_deg: float
    frames: int
    chi2_dof: float
    drift: float
    chi2_dof_header: float
    drift_header: float
    centre_deg: float
    fwhm_deg: float
    scan: np.ndarray
    reliable: bool = True
    why: str = ''


MAX_CAL_CHI2 = 25.0    # single frames agreeing worse than this: no calibration (NX 5.3, owner's 163: 11.8)


def calibrate_distance(level, peak_deg=None, half_deg=0.4, beta_deg=(-0.1, 2.0), rel_range=(0.90, 1.06),
                       step_mm=1.0, min_frames=5):
    """S4–detector distance from single frames (owner, 2026-11-21: "calibrate
    from single frames"): a peak fitted in every frame that holds it
    (``single_frame_peaks``) must sit at one 2θ whatever columns see it; a
    wrong distance scales the angle per column, so the peak then drifts with
    Det_Th. The distance is scanned over ``rel_range`` × the header value in
    ``step_mm`` steps; the result is the vertex of a parabola through the χ²
    minimum, with the error where the χ², rescaled to 1 per degree of
    freedom at the minimum, rises by 1. ``peak_deg`` None: the strongest
    peak that at least ``min_frames`` single frames fit (``strongest_peak``
    candidates, strongest first); rows from ``beta_deg`` (near the horizon,
    where GID peaks are brightest). Raises ValueError when too few frames
    hold the peak."""
    header = float(level[0].geom.d_pinhole)
    rows = rows_for_beta(level[0], beta_deg)
    cands = [peak_deg] if peak_deg is not None else strongest_peak(level, rows, half_deg, all_candidates=True)
    grid = np.arange(header * rel_range[0], header * rel_range[1] + step_mm / 2, step_mm)
    for peak_deg in cands:                              # the strongest peak that single frames fit
        if len(single_frame_peaks(level, peak_deg, half_deg, rows, header)) < min_frames:
            continue
        scan = []
        for d in grid:
            pk = single_frame_peaks(level, peak_deg, half_deg, rows, d)
            if len(pk) >= min_frames:
                m, me, chi, drift, fw = frames_agree(pk)
                scan.append((d, len(pk), m, chi, drift, fw))
        scan = np.array(scan).reshape(-1, 6)
        if len(scan) >= 3:
            break
    else:
        raise ValueError('no peak (tried %s deg) is fitted in %d single frames'
                         % (', '.join('%.3f' % c for c in cands), min_frames))
    k = int(np.argmin(scan[:, 3]))
    lo, hi = max(k - 2, 0), min(k + 3, len(scan))
    best, err = float(scan[k, 0]), float(step_mm)
    if hi - lo >= 3:
        a, b, c = np.polyfit(scan[lo:hi, 0], scan[lo:hi, 3], 2)
        if a > 0 and scan[lo, 0] <= -b / (2 * a) <= scan[hi - 1, 0]:
            best = float(-b / (2 * a))
            cmin = max(float(c - b * b / (4 * a)), 1e-9)
            err = float(math.sqrt(cmin / (a * max(scan[k, 1] - 1, 1))))
    at = single_frame_peaks(level, peak_deg, half_deg, rows, best)
    hd = single_frame_peaks(level, peak_deg, half_deg, rows, None)
    m, _, chi, drift, fw = frames_agree(at) if len(at) >= 3 else (float('nan'),) * 5
    _, _, chi_h, drift_h, _ = frames_agree(hd) if len(hd) >= 3 else (float('nan'),) * 5
    why = []
    if len(at) < min_frames:
        why.append('only %d frames fit the peak at the best distance' % len(at))
    if not chi <= MAX_CAL_CHI2:
        why.append('the frames disagree (chi2/dof %.1f)' % chi)
    if not abs(drift) <= 0.01:
        why.append('the peak still drifts with Det_Th (%.3f deg/deg)' % drift)
    if not (scan[0, 0] < best < scan[-1, 0]):
        why.append('the best distance is at the edge of the range tried')
    if not err < 5.0:
        why.append('the distance is poorly defined (+/- %.1f mm)' % err)
    return DistanceCalibration(best, err, header, float(peak_deg), rows, half_deg, len(at), chi, drift, chi_h,
                               drift_h, m, fw, scan, not why, '; '.join(why))


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


def frame_weights(g, nrows, ncols, monitor, areainfo, row_lo, row_hi, area=True, pol=True, angles=None):
    """W = M · A(2θ_c) · P(2θ, β) for one frame, rows row_lo..row_hi,
    without the column response. ``areainfo`` = (S1h, S1v, S4h, alpha, D_s,
    D_p). ``angles``: the pixels' (2θ, β) in radians (``pixel_angles``) for
    the polarisation; by default the per-axis angles. The footprint fraction
    A is per column, at the column's in-plane angle (it is a horizontal
    quantity; the row dependence of 2θ is < 0.04° on NX)."""
    tt = column_two_theta(ncols, g)
    s1h, s1v, s4h, alpha, d_s, d_p = areainfo
    if area:
        a = np.array([area_fraction(s1h, s1v, s4h, PIXEL_MM, alpha, d_s, d_s - d_p, t) for t in tt])
    else:
        a = np.ones(ncols)
    if angles is None:
        bb = row_beta(nrows, g)[row_lo:row_hi + 1]
        p = polarisation(tt[None, :], bb[:, None]) if pol else np.ones((len(bb), ncols))
    else:
        p = polarisation(angles[0], angles[1]) if pol else np.ones_like(angles[0])
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
    footprint: str = 'exact'   # footprint window: 'exact' (P39, D51) or 'idl' (usable_columns)


def frame_range(f, ncols):
    """(lowest, highest) 2θ (degrees) of the usable columns of frame ``f``,
    over all its rows (exact angles)."""
    cols = frame_columns(f, ncols)
    t = np.degrees(pixel_angles(f.geom, np.arange(f.counts.shape[0]), cols)[0])
    return float(t.min()), float(t.max())


def shared_edges(frames, step_deg=0.0):
    """One 2θ grid (bin edges, degrees) for all ``frames`` (all Qz levels),
    one column wide (p/D_p) unless ``step_deg`` is given, so the levels'
    bins coincide and need no interpolation when they are joined."""
    ncols = frames[0].counts.shape[1]
    step = step_deg if step_deg > 0 else math.degrees(PIXEL_MM / frames[0].geom.d_pinhole)
    r = [frame_range(f, ncols) for f in frames]
    lo, hi = min(a for a, _ in r), max(b for _, b in r)
    return lo - step / 2 + step * np.arange(int(math.ceil((hi - lo) / step)) + 2)


def frame_consistency(theta, n, w, edges):
    """How well a level's frames agree with the map made from them: per frame
    and column, rows summed, counts N against W · S, S = ΣN/ΣW of the 2θ bin
    the column falls in (its mean 2θ over the rows); returns the Poisson
    χ²/dof Σ(N − W S)² / max(W S, 1) / (cells − bins). 1 means the frames
    differ only by counting noise; the response and the scan factors are in
    W, so this measures what they leave unexplained (owner, 2026-11-20: the
    yardstick for choosing a method). ``theta`` etc. as ``level_map``'s."""
    nb = len(edges) - 1
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)       # columns with no angle (unused)
        th = np.nanmean(theta, axis=1)                         # (frames, cols)
    nn, ww = n.sum(axis=1), w.sum(axis=1)
    idx = np.digitize(th, edges) - 1
    ok = np.isfinite(th) & (idx >= 0) & (idx < nb) & (ww > 0)
    if not ok.any():
        return float('nan')
    sn = np.bincount(idx[ok], weights=nn[ok], minlength=nb)
    sw = np.bincount(idx[ok], weights=ww[ok], minlength=nb)
    s = np.where(sw > 0, sn / np.where(sw > 0, sw, 1), 0.0)
    mu = ww[ok] * s[idx[ok]]
    used = int((np.bincount(idx[ok], minlength=nb) > 0).sum())
    return float(np.sum((nn[ok] - mu) ** 2 / np.maximum(mu, 1.0)) / max(int(ok.sum()) - used, 1))


def level_map(frames, row_lo, row_hi, response='fit', area=True, pol=True, bin_step_deg=0.0, log=None,
              min_frames=2, edges=None, beam_centre_mm=None, beam_fwhm_um=None, beam_h_fwhm_mm=BEAM_H_FWHM_MM,
              apply_joins=True, angles='exact', join_estimator='ml'):
    """Pinhole map of one Qz level: every usable column at its own 2θ,
    binned as ΣN/ΣW; scans of the level joined by one factor each (fitted on
    the rows-summed profiles over their common bins, as the window's
    horizontal join), applied to W. Returns (two_theta_deg (bins),
    beta_deg (rows), I (bins, rows), σ (bins, rows), info). I is per monitor
    count times the level's mean monitor, like the window's GID map. Bins
    seen by fewer than ``min_frames`` frames (the edges, through the weakest
    columns only) are left out. ``edges``: a 2θ grid shared with other
    levels (``shared_edges``); by default the level's own.

    ``response`` 'physical' (owner, 2026-11-20): the response from the
    geometry and the beam (``PhysicalResponse``), the beam's centre and
    vertical FWHM fitted to the level unless given (``beam_centre_mm``,
    ``beam_fwhm_um``), its horizontal FWHM ``beam_h_fwhm_mm``; it includes the
    area correction (``area`` is then not applied) and keeps the level's
    absolute scale. ``apply_joins`` False: the scans' factors are fitted and
    logged but not applied (the data as collected). ``angles`` 'exact'
    (the default since 2026-11-19): each pixel's (2θ, β) from
    ``pixel_angles``; 'per_axis': the column's 2θ and the row's β
    (``column_two_theta``, ``row_beta``), as the map was binned before, kept
    for comparison C21 (the columns, footprint and response are found with
    the exact angles either way). ``join_estimator`` 'ml' (the default
    since 2026-11-23, P46): the scans' factors by ``ratio_ml``; 'ivw': the
    inverse-variance mean of the bins' ratios, as before (biased low when
    bins hold few counts)."""
    if angles not in ('exact', 'per_axis'):
        raise ValueError("angles: 'exact' or 'per_axis', not %r" % (angles,))
    if join_estimator not in ('ml', 'ivw'):
        raise ValueError("join_estimator: 'ml' or 'ivw', not %r" % (join_estimator,))
    ncols = frames[0].counts.shape[1]
    nrows = frames[0].counts.shape[0]
    g0 = frames[0].geom
    step = bin_step_deg if bin_step_deg > 0 else math.degrees(PIXEL_MM / g0.d_pinhole)
    rows = np.arange(row_lo, row_hi + 1)
    theta, beta_px, n, w = [], [], [], []
    for f in frames:
        cols = frame_columns(f, ncols)
        if angles == 'per_axis':                                         # before 2026-11-19 (C21)
            tt = np.repeat(column_two_theta(ncols, f.geom)[None, :], len(rows), axis=0)
            bb = np.repeat(row_beta(nrows, f.geom)[rows][:, None], ncols, axis=1)
        else:
            tt, bb = pixel_angles(f.geom, rows, np.arange(ncols))      # exact, per pixel (IMG_COO_CONV)
        use = np.zeros(ncols, bool)
        use[cols] = True
        theta.append(np.where(use[None, :], np.degrees(tt), np.nan))
        beta_px.append(np.degrees(bb))
        n.append(np.asarray(f.counts, float)[row_lo:row_hi + 1])
        w.append(frame_weights(f.geom, nrows, ncols, f.monitor, f.areainfo, row_lo, row_hi,
                               area and not response.startswith('physical'), pol, angles=(tt, bb)))
    theta, beta_px, n, w = np.array(theta), np.array(beta_px), np.array(n), np.array(w)
    n = np.where(np.isfinite(theta), np.clip(n, 0, None), 0.0)          # masked pixels (< 0) count nothing
    if edges is None:
        lo, hi = np.nanmin(theta), np.nanmax(theta)
        edges = lo - step / 2 + step * np.arange(int(math.ceil((hi - lo) / step)) + 2)
    else:
        edges = np.asarray(edges, float)
        step = float(edges[1] - edges[0])
    bstep = math.degrees(PIXEL_MM / vertical_distance(g0))               # one row at the direct beam
    blo, bhi = np.nanmin(np.where(np.isfinite(theta), beta_px, np.nan)), np.nanmax(np.where(np.isfinite(theta), beta_px, np.nan))
    bedges = blo - bstep / 2 + bstep * np.arange(int(math.ceil((bhi - blo) / bstep)) + 2)
    beam = None
    phys = None
    if response in ('physical', 'physical+fit'):
        cols_f = [frame_columns(f, ncols) for f in frames]
        presp = PhysicalResponse(frames, cols_f)
        with np.errstate(invalid='ignore'):
            th_c = [np.nanmean(theta[k][:, c], axis=0) for k, c in enumerate(cols_f)]
        n_c = [n[k][:, c].sum(axis=0) for k, c in enumerate(cols_f)]
        w_c = [w[k][:, c].sum(axis=0) for k, c in enumerate(cols_f)]
        model, chi2dof = fit_beam(presp, th_c, n_c, w_c, edges, beam_h_fwhm_mm, beam_centre_mm, beam_fwhm_um,
                                  scans=[f.scan for f in frames])
        rfc = np.ones((len(frames), ncols))
        for k, (c, lt) in enumerate(zip(cols_f, presp.light(model))):
            rfc[k, c] = np.where(lt > 0, lt, np.nan)
        w = w * rfc[:, None, :]
        theta = np.where(np.isfinite(rfc)[:, None, :], theta, np.nan)          # columns the beam does not reach
        w = np.where(np.isfinite(w), w, 0.0)
        lit = np.where(np.isfinite(theta).any(axis=1), rfc, np.nan)
        used = np.isfinite(lit).sum(axis=0)
        r = np.where(used > 0, np.nansum(lit, axis=0) / np.maximum(used, 1), 1.0)
        if response == 'physical+fit':                 # what physics misses, per column, mean 1 (scale kept)
            r2 = column_response(theta, n, w, edges, scans=[f.scan for f in frames])
            w = w * r2[None, None, :]
            r = r * r2
        along = model.fwhm_um * 1e-3 / math.sin(frames[0].geom.alpha)
        phys = dict(centre_mm=model.centre_mm, fwhm_um=model.fwhm_um, h_fwhm_mm=model.h_fwhm_mm,
                    fwhm_mm=along, fitted=[k for k, v in (('centre_mm', beam_centre_mm), ('fwhm_um', beam_fwhm_um))
                                           if v is None], chi2_dof=chi2dof)
    elif response == 'beam':
        xsrc = source_positions(frames, ncols)
        xsrc = np.where(np.isfinite(theta).any(axis=1), xsrc, np.nan)       # usable columns only
        rfc, beam = beam_response(theta, n, w, edges, xsrc, scans=[f.scan for f in frames])
        w = w * rfc[:, None, :]
        with np.errstate(invalid='ignore', divide='ignore'):
            used = np.isfinite(xsrc)
            r = np.where(used.any(axis=0), np.sum(np.where(used, rfc, 0.0), axis=0) / np.maximum(used.sum(axis=0), 1), np.nan)
        r = np.where(np.isfinite(r), r, 1.0)
    else:
        if response not in ('fit', 'none'):
            raise ValueError("response %r: use 'fit', 'beam', 'physical', 'physical+fit' or 'none'" % (response,))
        r = (column_response(theta, n, w, edges, scans=[f.scan for f in frames]) if response == 'fit'
             else np.ones(ncols))
        w = w * r[None, None, :]
    scans = sorted(set(f.scan for f in frames))
    factors = {scans[0]: (1.0, 0.0)}
    if len(scans) > 1:
        # P41 fix (2026-11-22): each scan is joined against everything joined so far (the rows-summed
        # profile of the joined scans, their factors applied), taking next the scan that overlaps it
        # most, as join_levels does for levels. Before, every scan was fitted against the first
        # scan only, so a chain (A-B, B-C, A and C apart) left C's factor undefined.
        sel = {sc: np.array([f.scan == sc for f in frames]) for sc in scans}
        prof = {}
        for sc in scans:
            _, _, sn_, sw_ = bin_counts_2d(theta[sel[sc]], beta_px[sel[sc]], n[sel[sc]], w[sel[sc]], edges, bedges)
            prof[sc] = (sn_.sum(axis=1), sw_.sum(axis=1))
        ref_n, ref_w = prof[scans[0]][0].copy(), prof[scans[0]][1].copy()
        left = list(scans[1:])
        while left:
            def overlap(sc):
                a, b = prof[sc]
                return int(np.sum((ref_w > 0) & (b > 0) & (ref_n > 0) & (a > 0)))
            sc = max(left, key=lambda k: (overlap(k), -scans.index(k)))
            left.remove(sc)
            a, b = prof[sc]
            ok = (ref_w > 0) & (b > 0) & (ref_n > 0) & (a > 0)
            if not ok.any():
                factors[sc] = (math.nan, math.nan)
                if log is not None:
                    log.append(dict(kind='horizontal (2theta)', x_from=math.nan, x_to=math.nan, points=0,
                                    factor=math.nan, error=math.nan, chi2=math.nan, applied=False, scan=sc,
                                    message='scan %d overlaps no scan joined before it: not joined' % sc))
                continue
            ratio = (ref_n[ok] / ref_w[ok]) / (a[ok] / b[ok])
            if join_estimator == 'ml':                                  # P46 (2026-11-23)
                fac, ferr = ratio_ml(ref_n[ok], ref_w[ok], a[ok], b[ok])
                err = fac * np.sqrt(1 / ref_n[ok] + 1 / a[ok])
            else:
                err = ratio * np.sqrt(1 / ref_n[ok] + 1 / a[ok])
                wt = 1 / err ** 2
                fac = float(np.sum(wt * ratio) / np.sum(wt))
                ferr = float(np.sum(wt) ** -0.5)
            chi2 = float(np.sum((ratio - fac) ** 2 / err ** 2) / max(ok.sum() - 1, 1))
            factors[sc] = (fac, ferr)
            if log is not None:
                x = 0.5 * (edges[:-1] + edges[1:])[ok]
                log.append(dict(kind='horizontal (2theta)', x_from=float(x.min()), x_to=float(x.max()),
                                points=int(ok.sum()), factor=fac, error=ferr, chi2=chi2, applied=bool(apply_joins),
                                scan=sc))
            if apply_joins:
                w[sel[sc]] = w[sel[sc]] / fac
            ref_n = ref_n + a                       # the joined scan joins the reference, on its scale
            ref_w = ref_w + b / fac
    i, s, sn, sw = bin_counts_2d(theta, beta_px, n, w, edges, bedges)
    consistency = frame_consistency(theta, n, w, edges)
    bidx = np.digitize(theta, edges) - 1
    nframes = np.array([int((bidx == k).any(axis=(1, 2)).sum()) for k in range(len(edges) - 1)])
    keep = (sw.sum(axis=1) > 0) & (nframes >= min_frames)
    # β: the range every kept 2θ bin covers (each column sees its own β range)
    bkeep = np.all(sw[keep] > 0, axis=0) if keep.any() else np.zeros(sw.shape[1], bool)
    if bkeep.any():
        k0, k1 = np.flatnonzero(bkeep)[[0, -1]]
        bkeep[:] = False
        bkeep[k0:k1 + 1] = True
    keep &= np.all(sw[:, bkeep] > 0, axis=1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    bcentres = 0.5 * (bedges[:-1] + bedges[1:])
    mean_m = float(np.mean([f.monitor for f in frames]))
    sn_k, sw_k = sn[:, bkeep], sw[:, bkeep]
    res_deg, s4 = two_theta_resolution(frames[len(frames) // 2])
    if beam is not None:
        bc, bw = profile_width(*beam)
        beam = dict(x_mm=beam[0], response=beam[1], centre_mm=bc, fwhm_mm=bw)
    info = dict(response=r, factors=factors, step_deg=step, counts_used=float(n.sum()),
                two_theta_resolution_deg=res_deg, two_theta_resolution_columns=res_deg / step, s4_mm=s4,
                beam=beam, physical=phys, joins_applied=bool(apply_joins), consistency_chi2=consistency,
                sum_counts=sn_k[keep], sum_weights=sw_k[keep], frames_per_bin=nframes[keep],
                edges=edges, keep=keep, all_counts=sn_k, all_weights=sw_k, beta=bcentres[bkeep],
                beta_edges=bedges, beta_step_deg=bstep, mean_monitor=mean_m, geometry='exact (IMG_COO_CONV)',
                columns=[(int(np.flatnonzero(np.isfinite(t).any(axis=0))[0]) if np.isfinite(t).any() else -1,
                          int(np.flatnonzero(np.isfinite(t).any(axis=0))[-1]) if np.isfinite(t).any() else -1)
                         for t in theta])
    return centres[keep], bcentres[bkeep], i[keep][:, bkeep] * mean_m, s[keep][:, bkeep] * mean_m, info


def ratio_ml(Na, Wa, Nb, Wb):
    """The common ratio f = I_a / I_b of two sets of counts over shared bins
    (E[Na] = I·Wa, E[Nb] = I·Wb / f, I free per bin) that maximises the
    likelihood of how each bin's counts split between them (binomial, given
    the bin's total), and its error from the curvature. Unlike the
    inverse-variance mean of the bins' ratios (weights falling as each bin's
    own ratio rises), it is not biased when bins hold few counts (P46:
    measured on synthetic levels, true factor 1.25: −0.03 % against −1.0 %
    at 0.13 counts per pixel, +0.1 % against −4.9 % at 0.026)."""
    from scipy.optimize import brentq
    Na, Wa, Nb, Wb = (np.asarray(x, float) for x in (Na, Wa, Nb, Wb))
    use = (Na + Nb > 0) & (Wa > 0) & (Wb > 0)
    Na, Wa, Nb, Wb = Na[use], Wa[use], Nb[use], Wb[use]
    if Na.sum() <= 0 or Nb.sum() <= 0:
        raise ValueError('no counts in the overlap')

    def score(f):
        return float(np.sum(Na / f - (Na + Nb) * Wa / (f * Wa + Wb)))
    f0 = (Na.sum() / Wa.sum()) / (Nb.sum() / Wb.sum())
    lo, hi = f0 / 4, f0 * 4
    while score(lo) < 0:
        lo /= 4
    while score(hi) > 0:
        hi *= 4
    f = brentq(score, lo, hi, xtol=1e-14, rtol=1e-13)
    curv = float(np.sum(Na / f ** 2 - (Na + Nb) * Wa ** 2 / (f * Wa + Wb) ** 2))
    return f, (curv ** -0.5 if curv > 0 else float('nan'))


def level_factor_ml(nc, wc, n, w, cells):
    """``ratio_ml`` for the β bins of a level join: each level's β bin
    enters with the effective counts and exposure of an equal-weight mean
    over its cells (N = p·W, W = m² / Σ 1/w_cell), as the bins' ratios are
    formed."""
    m = cells.sum(axis=0)
    sa = np.where(cells, wc, 1.0)
    sb = np.where(cells, w, 1.0)
    with np.errstate(invalid='ignore', divide='ignore'):
        pa = np.where(cells, nc / sa, 0.0).sum(axis=0) / np.maximum(m, 1)
        pb = np.where(cells, n / sb, 0.0).sum(axis=0) / np.maximum(m, 1)
        Wa = m ** 2 / np.where(cells, 1.0 / sa, 0.0).sum(axis=0)
        Wb = m ** 2 / np.where(cells, 1.0 / sb, 0.0).sum(axis=0)
    ok = (m > 0) & np.isfinite(Wa) & np.isfinite(Wb)
    return ratio_ml(pa[ok] * Wa[ok], Wa[ok], pb[ok] * Wb[ok], Wb[ok])


def _seam_edges(nc, wc, n, w, common, nbins=3):
    """The 2θ-averaged intensity of the joined map in its highest ``nbins`` β bins with data, and of the new level
    in its lowest ``nbins``, over the 2θ bins both have (``common``): the two sides of an unscaled seam."""
    def side(N, W, top):
        rows = np.where((W[common] > 0).any(axis=0))[0]
        if not len(rows):
            return float('nan'), float('nan'), 0
        sel = rows[-nbins:] if top else rows[:nbins]
        Ns, Ws = N[common][:, sel], W[common][:, sel]
        ok = Ws > 0
        with np.errstate(invalid='ignore', divide='ignore'):
            v = float(np.mean((Ns[ok] / Ws[ok])))
            e = float(np.sqrt(np.sum(Ns[ok] / Ws[ok] ** 2)) / max(ok.sum(), 1))
        b = sel[-1] if top else sel[0]
        return v, e, int(b)
    return side(nc, wc, True), side(n, w, False)


def join_levels(levels, transverse='intersection', log=None, labels=None, apply=True, estimator='ml',
                unmatched='refuse'):
    """Join the maps of several Qz levels (``level_map`` infos on one shared
    2θ grid) into one map (F62; the review's §7.2 step 8, after IDL's
    IMG_JOIN):

    - every level's rows are put on one β grid (nearest bin; the step is
      the largest row step of any level, so no level skips a bin), as summed
      counts and weights, so nothing is interpolated; β bins no level
      reaches are dropped;
    - levels are taken in order of their lowest β; each is scaled by one
      factor, fitted on the β overlap with what is joined so far: per β bin
      the two intensity profiles are averaged over the same cells (2θ bins
      both have), with equal weight per cell — summing counts and weights
      instead would weight a 2θ feature differently in each level and bias
      the factor — and the weighted mean of their ratios is applied to the
      level's weights;
    - the map is ΣN/ΣW over all levels; σ adds, to the counting error, each
      factor's relative error times its level's share of the weight;
    - ``transverse``: 'intersection' (IDL) keeps the 2θ bins every level
      has; 'union' keeps all, NaN where no level has data at that β.
    - ``unmatched``: what to do with a level that shares 2θ bins with the
      levels below it but no β bin (nothing to fit a factor on): 'refuse'
      (the default) raises ValueError; 'unscaled' (a stopgap, owner,
      2026-11-26) adds it as collected, factor 1 with no error, normalised
      by monitor, absorber and the level's own response only. Each such
      seam is listed in info['unscaled_seams'] (the levels, the β gap, the
      2θ-averaged intensity on each side and their ratio, a diagnostic
      only) and logged with kind 'vertical (beta), unscaled'. Its σ is
      counting only: the scale across the seam carries no error.

    Returns (two_theta_deg, beta_deg, I (bins, β), σ, info); I is per
    monitor count × the mean monitor of all levels."""
    if unmatched not in ('refuse', 'unscaled'):
        raise ValueError("unmatched %r: use 'refuse' or 'unscaled'" % (unmatched,))
    if len(levels) == 1:                                 # nothing to join: the level's own rows
        lv = levels[0]
        k = lv['keep']
        m = lv['mean_monitor']
        with np.errstate(invalid='ignore', divide='ignore'):
            i = lv['all_counts'][k] / lv['all_weights'][k]
            s = np.sqrt(lv['all_counts'][k]) / lv['all_weights'][k]
        c = 0.5 * (lv['edges'][:-1] + lv['edges'][1:])[k]
        return c, lv['beta'], i * m, s * m, dict(factors={}, transverse=transverse,
                                                  sum_counts=lv['all_counts'][k], sum_weights=lv['all_weights'][k])
    edges = levels[0]['edges']
    for lv in levels[1:]:
        if len(lv['edges']) != len(edges) or not np.allclose(lv['edges'], edges):
            raise ValueError('the levels are not on one 2theta grid (use shared_edges)')
    nb = len(edges) - 1
    bstep = max(float(np.max(np.abs(np.diff(lv['beta'])))) for lv in levels)
    blo = min(float(lv['beta'].min()) for lv in levels)
    bhi = max(float(lv['beta'].max()) for lv in levels)
    bedges = blo - bstep / 2 + bstep * np.arange(int(math.ceil((bhi - blo) / bstep)) + 2)
    nbeta = len(bedges) - 1
    order = sorted(range(len(levels)), key=lambda k: float(levels[k]['beta'].min()))
    labels = labels or ['level %d' % (k + 1) for k in range(len(levels))]
    rebinned = []
    for lv in levels:
        j = np.clip(np.digitize(lv['beta'], bedges) - 1, 0, nbeta - 1)
        n = np.zeros((nb, nbeta))
        w = np.zeros((nb, nbeta))
        kept = lv['keep']
        for r in range(len(j)):
            n[kept, j[r]] += lv['all_counts'][kept, r]
            w[kept, j[r]] += lv['all_weights'][kept, r]
        rebinned.append((n, w, kept))
    k0 = order[0]
    nc, wc = rebinned[k0][0].copy(), rebinned[k0][1].copy()
    have = rebinned[k0][2].copy()
    every = rebinned[k0][2].copy()
    factors = {labels[k0]: (1.0, 0.0)}
    shares = [(wc.copy(), 0.0)]
    seams = []
    bcentres = 0.5 * (bedges[:-1] + bedges[1:])
    for k in order[1:]:
        n, w, kept = rebinned[k]
        common = have & kept
        if not common.any():
            raise ValueError('%s has no 2theta bins in common with the levels below it' % labels[k])
        cells = common[:, None] & (wc > 0) & (w > 0)
        m = cells.sum(axis=0)
        if unmatched == 'unscaled' and not ((m > 0) & ((nc * cells).sum(axis=0) > 0) & ((n * cells).sum(axis=0) > 0)).any():
            (lo_v, lo_e, lo_b), (hi_v, hi_e, hi_b) = _seam_edges(nc, wc, n, w, common)
            ratio = hi_v / lo_v if lo_v > 0 else float('nan')
            rerr = ratio * math.sqrt((lo_e / lo_v) ** 2 + (hi_e / hi_v) ** 2) if lo_v > 0 and hi_v > 0 else float('nan')
            below = ' + '.join(labels[i] for i in order[:order.index(k)])
            seam = dict(below=below, level=labels[k], beta_below_deg=float(bcentres[lo_b]),
                        beta_above_deg=float(bcentres[hi_b]), gap_deg=float(bcentres[hi_b] - bcentres[lo_b]),
                        edge_ratio=ratio, edge_ratio_error=rerr)
            seams.append(seam)
            factors[labels[k]] = (1.0, float('nan'))
            if log is not None:
                log.append(dict(label='%s + %s: UNSCALED, no overlap' % (below, labels[k]),
                                kind='vertical (beta), unscaled', x_from=seam['beta_below_deg'],
                                x_to=seam['beta_above_deg'], points=0, factor=1.0, error=float('nan'),
                                chi2=float('nan'), applied=False, unscaled=True, edge_ratio=ratio))
            shares.append((w.copy(), 0.0))
            nc += n
            wc += w
            have |= kept
            every &= kept
            continue
        with np.errstate(invalid='ignore', divide='ignore'):
            sa = np.where(cells, wc, 1.0)
            sb = np.where(cells, w, 1.0)
            pa = np.where(cells, nc / sa, 0.0).sum(axis=0) / np.maximum(m, 1)        # mean intensity per β bin
            pb = np.where(cells, n / sb, 0.0).sum(axis=0) / np.maximum(m, 1)
            va = np.where(cells, nc / sa ** 2, 0.0).sum(axis=0) / np.maximum(m, 1) ** 2
            vb = np.where(cells, n / sb ** 2, 0.0).sum(axis=0) / np.maximum(m, 1) ** 2
        ok = (m > 0) & (pa > 0) & (pb > 0)
        if not ok.any():
            raise ValueError('%s does not overlap in beta with the levels below it' % labels[k])
        ratio = pa[ok] / pb[ok]
        if estimator == 'ml':
            fac, ferr = level_factor_ml(nc, wc, n, w, cells)
            err = fac * np.sqrt(va[ok] / pa[ok] ** 2 + vb[ok] / pb[ok] ** 2)     # χ² about f, errors at f
        else:
            err = ratio * np.sqrt(va[ok] / pa[ok] ** 2 + vb[ok] / pb[ok] ** 2)
            wt = 1 / err ** 2
            fac = float(np.sum(wt * ratio) / np.sum(wt))
            ferr = float(np.sum(wt) ** -0.5)
        chi2 = float(np.sum((ratio - fac) ** 2 / err ** 2) / max(ok.sum() - 1, 1))
        factors[labels[k]] = (fac, ferr)
        if log is not None:
            x = 0.5 * (bedges[:-1] + bedges[1:])[ok]
            log.append(dict(label=' + '.join(labels[i] for i in order[:order.index(k) + 1]),
                            kind='vertical (beta)', x_from=float(x.min()), x_to=float(x.max()),
                            points=int(ok.sum()), factor=fac, error=ferr, chi2=chi2, applied=bool(apply)))
        if apply:
            w = w / fac
            shares.append((w.copy(), ferr / fac))
        else:                                      # as collected: the factor is reported, not applied
            shares.append((w.copy(), 0.0))
        nc += n
        wc += w
        have |= kept
        every &= kept
    mean_m = float(np.mean([lv['mean_monitor'] for lv in levels]))
    with np.errstate(invalid='ignore', divide='ignore'):
        i = np.where(wc > 0, nc / wc, np.nan)
        s = np.where(wc > 0, np.sqrt(nc) / wc, np.nan)
        frac = sum(np.where(wc > 0, w_k / np.where(wc > 0, wc, 1), 0.0) * rel for w_k, rel in shares)
    s = np.sqrt(s ** 2 + (i * frac) ** 2)
    sel = every if transverse == 'intersection' else have
    if not sel.any():
        raise ValueError('the levels have no 2theta range in common')
    rows = (wc[sel] > 0).any(axis=0)                     # β bins some level reaches
    centres = 0.5 * (edges[:-1] + edges[1:])
    bcent = 0.5 * (bedges[:-1] + bedges[1:])
    info = dict(factors=factors, beta_step_deg=bstep, transverse=transverse,
                sum_counts=nc[sel][:, rows], sum_weights=wc[sel][:, rows], unscaled_seams=seams)
    return centres[sel], bcent[rows], i[sel][:, rows] * mean_m, s[sel][:, rows] * mean_m, info

