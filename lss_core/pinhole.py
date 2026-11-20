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
    ``ray_geometry``'s source point, by bisection: the source point grows
    with the column, from −∞ (the column that looks along the beam) to
    L/cos Det_Th at infinity, L the sample → slit distance. Raises
    ValueError when no column sees ``x``."""
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


def column_response(theta, counts, weights, edges, iterations=20):
    """Column response R(c), mean 1, estimated from the data: alternately
    S(2θ) = ΣN/Σ(W·R) on the bins (rows summed) and R(c) = Σ_f N / Σ_f W·S
    (the review's §7.3). ``weights`` without R; arrays as for bin_counts."""
    if np.ndim(theta) == 3:                                  # per-pixel angles (pixel_angles)
        return _column_response_pixels(theta, counts, weights, edges, iterations)
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


def _column_response_pixels(theta, counts, weights, edges, iterations=20):
    """column_response with an angle per pixel (frames, rows, cols)."""
    nb = len(edges) - 1
    idx = np.digitize(theta, edges) - 1
    ok = np.isfinite(theta) & (idx >= 0) & (idx < nb)
    ncol = counts.shape[2]
    cidx = np.broadcast_to(np.arange(ncol), counts.shape)
    n_ok, w_ok, i_ok, c_ok = counts[ok], weights[ok], idx[ok], cidx[ok]
    num = np.bincount(c_ok, weights=n_ok, minlength=ncol)
    r = np.ones(ncol)
    for _ in range(iterations):
        sn = np.bincount(i_ok, weights=n_ok, minlength=nb)
        sw = np.bincount(i_ok, weights=w_ok * r[c_ok], minlength=nb)
        s = np.where(sw > 0, sn / np.where(sw > 0, sw, 1), 0.0)
        den = np.bincount(c_ok, weights=w_ok * s[i_ok], minlength=ncol)
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


def beam_response(theta, counts, weights, edges, xsrc, bin_mm=BEAM_BIN_MM, iterations=20):
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
    num = np.bincount(x_ok, weights=n_ok, minlength=nx)
    r = np.ones(nx)
    for _ in range(iterations):
        sn = np.bincount(i_ok, weights=n_ok, minlength=nb)
        sw = np.bincount(i_ok, weights=w_ok * r[x_ok], minlength=nb)
        sv = np.where(sw > 0, sn / np.where(sw > 0, sw, 1), 0.0)
        den = np.bincount(x_ok, weights=w_ok * sv[i_ok], minlength=nx)
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


def two_theta_resolution(f):
    """Full width (degrees) of the 2θ one column accepts through S4's opening
    and its own pixel width (``column_acceptance`` at the direct-beam column
    of frame ``f``), and S4's opening (mm)."""
    s4 = float(f.areainfo[2])
    acc = column_acceptance(f.geom, int(round(f.geom.c0)), s4 / 2, s4 / 2)
    return float(np.degrees(np.ptp(acc.two_theta))), s4


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


def level_map(frames, row_lo, row_hi, response='fit', area=True, pol=True, bin_step_deg=0.0, log=None,
              min_frames=2, edges=None):
    """Pinhole map of one Qz level: every usable column at its own 2θ,
    binned as ΣN/ΣW; scans of the level joined by one factor each (fitted on
    the rows-summed profiles over their common bins, as the window's
    horizontal join), applied to W. Returns (two_theta_deg (bins),
    beta_deg (rows), I (bins, rows), σ (bins, rows), info). I is per monitor
    count times the level's mean monitor, like the window's GID map. Bins
    seen by fewer than ``min_frames`` frames (the edges, through the weakest
    columns only) are left out. ``edges``: a 2θ grid shared with other
    levels (``shared_edges``); by default the level's own."""
    ncols = frames[0].counts.shape[1]
    nrows = frames[0].counts.shape[0]
    g0 = frames[0].geom
    step = bin_step_deg if bin_step_deg > 0 else math.degrees(PIXEL_MM / g0.d_pinhole)
    rows = np.arange(row_lo, row_hi + 1)
    theta, beta_px, n, w = [], [], [], []
    for f in frames:
        cols = frame_columns(f, ncols)
        tt, bb = pixel_angles(f.geom, rows, np.arange(ncols))          # exact, per pixel (IMG_COO_CONV)
        use = np.zeros(ncols, bool)
        use[cols] = True
        theta.append(np.where(use[None, :], np.degrees(tt), np.nan))
        beta_px.append(np.degrees(bb))
        n.append(np.asarray(f.counts, float)[row_lo:row_hi + 1])
        w.append(frame_weights(f.geom, nrows, ncols, f.monitor, f.areainfo, row_lo, row_hi, area, pol, angles=(tt, bb)))
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
    if response == 'beam':
        xsrc = source_positions(frames, ncols)
        xsrc = np.where(np.isfinite(theta).any(axis=1), xsrc, np.nan)       # usable columns only
        rfc, beam = beam_response(theta, n, w, edges, xsrc)
        w = w * rfc[:, None, :]
        with np.errstate(invalid='ignore', divide='ignore'):
            used = np.isfinite(xsrc)
            r = np.where(used.any(axis=0), np.sum(np.where(used, rfc, 0.0), axis=0) / np.maximum(used.sum(axis=0), 1), np.nan)
        r = np.where(np.isfinite(r), r, 1.0)
    else:
        r = column_response(theta, n, w, edges) if response == 'fit' else np.ones(ncols)
        w = w * r[None, None, :]
    scans = sorted(set(f.scan for f in frames))
    factors = {scans[0]: (1.0, 0.0)}
    if len(scans) > 1:
        sel = [np.array([f.scan == sc for f in frames]) for sc in scans]
        _, _, ref_n, ref_w = bin_counts_2d(theta[sel[0]], beta_px[sel[0]], n[sel[0]], w[sel[0]], edges, bedges)
        prof0 = ref_n.sum(axis=1), ref_w.sum(axis=1)
        for sc, m in zip(scans[1:], sel[1:]):
            _, _, sn, sw = bin_counts_2d(theta[m], beta_px[m], n[m], w[m], edges, bedges)
            a, b = sn.sum(axis=1), sw.sum(axis=1)
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
    i, s, sn, sw = bin_counts_2d(theta, beta_px, n, w, edges, bedges)
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
                beam=beam,
                sum_counts=sn_k[keep], sum_weights=sw_k[keep], frames_per_bin=nframes[keep],
                edges=edges, keep=keep, all_counts=sn_k, all_weights=sw_k, beta=bcentres[bkeep],
                beta_edges=bedges, beta_step_deg=bstep, mean_monitor=mean_m, geometry='exact (IMG_COO_CONV)',
                columns=[(int(np.flatnonzero(np.isfinite(t).any(axis=0))[0]) if np.isfinite(t).any() else -1,
                          int(np.flatnonzero(np.isfinite(t).any(axis=0))[-1]) if np.isfinite(t).any() else -1)
                         for t in theta])
    return centres[keep], bcentres[bkeep], i[keep][:, bkeep] * mean_m, s[keep][:, bkeep] * mean_m, info


def join_levels(levels, transverse='intersection', log=None, labels=None):
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

    Returns (two_theta_deg, beta_deg, I (bins, β), σ, info); I is per
    monitor count × the mean monitor of all levels."""
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
    for k in order[1:]:
        n, w, kept = rebinned[k]
        common = have & kept
        if not common.any():
            raise ValueError('%s has no 2theta bins in common with the levels below it' % labels[k])
        cells = common[:, None] & (wc > 0) & (w > 0)
        m = cells.sum(axis=0)
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
        err = ratio * np.sqrt(va[ok] / pa[ok] ** 2 + vb[ok] / pb[ok] ** 2)
        wt = 1 / err ** 2
        fac = float(np.sum(wt * ratio) / np.sum(wt))
        ferr = float(np.sum(wt) ** -0.5)
        chi2 = float(np.sum(wt * (ratio - fac) ** 2) / max(ok.sum() - 1, 1))
        factors[labels[k]] = (fac, ferr)
        if log is not None:
            x = 0.5 * (bedges[:-1] + bedges[1:])[ok]
            log.append(dict(label=' + '.join(labels[i] for i in order[:order.index(k) + 1]),
                            kind='vertical (beta)', x_from=float(x.min()), x_to=float(x.max()),
                            points=int(ok.sum()), factor=fac, error=ferr, chi2=chi2))
        w = w / fac
        shares.append((w.copy(), ferr / fac))
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
                sum_counts=nc[sel][:, rows], sum_weights=wc[sel][:, rows])
    return centres[sel], bcent[rows], i[sel][:, rows] * mean_m, s[sel][:, rows] * mean_m, info

