"""The radiation dose each point of a scan gives the sample (F98, F107, F76;
2026-11-24).

**The beam on the sample during point i.** The Monc ion chamber sits
upstream of the absorbers (confirmed by the owner, 2026-11-24): the
reduction multiplies counts by the absorber factor A and divides by the
monitor M (``lss_core.normalise``), and by the gain factor g = S_ref/S. So, in monitor counts at the
reference gain (5 µA/V) with the absorbers taken out, the sample sees

    d_i = M_i / (A_i · g_i),

the same number that weights frame i in "Sum All" (``cuts.frame_normaliser``).
``unit='photons'`` (the default) turns it into photons with the owner's
counts-to-photons route (``lss_core.flux.photon_factor``, route D of the
xray_fluxor hand-off):

    N_i = (M_i − D·t_i) · q(E) · (S / 500 nA/V) · gas / A_i,

photons through the chamber's exit plane, attenuated by the absorbers.
The windows and air between the chamber and the sample are not included,
and neither is the beam's loss in the absorbers' own windows. The flux
hand-off's bounds (±3.6 % below 13 keV) are a common scale of every point
(``Dose.bounds``): they cancel in a comparison of burns at one energy and
gain, but not across energies.

**Per area.** ``beam_mm=(width, height)``: the beam's size (mm) where it
meets the sample. The footprint is width × height / sin α, with α each
point's incidence (``cuts.true_incidence``), so the dose per area is

    N_i · sin α_i / (width · height)   (photons/mm²).

The beam's size is not read from the header (owner, 2026-11-24): the
slits upstream of the sample (S0, S1) pass more than the beam, which is
focused vertically by a curved mirror, and most of its energy lies within
about 1 mm horizontally. The header's blade values are half-openings
(owner, 2026-11-25, OQ-1), so a slit's opening is the sum of its two. The
vertical size comes from the height scans (``beam_height``, below); the
peak dose uses √(2π)σ, the study's choice for a beam with a core and tails
(OQ-2 asked FWHM or second moment). A footprint longer than the sample
changes nothing: the dose per area of the illuminated part stays the same.

**Cumulative.** ``Dose.cumulative()``: the dose received since the first
point began, at the middle of each point's exposure, the convention of the
burn's time axes (``burn.frame_times``). ``shutter='closed'`` (the
default; owner: closed between burn frames normally) gives no dose between
points. ``shutter='open'`` (fast mode, owner 2026-11-24: the shutter held
open, e.g. by ``stopabs``, and short exposures) adds the beam between
points: point i gives its counting rate × the time from its start to the
next point's start (the last: to its end, or its counting time), from the
scan's per-point times. How a file shows fast mode is open (OQ-4), so the
caller says.

**The beam's height from the sample-height scans** (``beam_height``; the
local data agent's study, ``docs/studies/sh_beam_size/summary.md``, #60,
2026-11-24). The rising edge of a routine height scan is a knife edge of
the beam: the liquid's dome cuts it at its tangent point, which moves 1:1
with sh. The height for the dose is √(2π)·σ_rise, σ_rise the erf width of
that edge (``peaks.fit_box``'s rising FWHM / 2.355), i.e. 1.0645 × the
rising FWHM: the inverse of the profile's peak, so the dose is the peak
dose per area, of the most exposed line. The profile is a core (σ ≈ 12 µm)
and a tail (σ ≈ 55 µm, a quarter to a third of the photons), so its FWHM
(about 0.84 × the rising FWHM) would overstate the peak dose by 1.3×, and
the S1 gap by 2.5×. A scan is refused (``RISE_GUARDS``, the study's) when its first
point is not below 25 % of the peak (the rise not scanned from its foot),
fewer than 2 points lie on the edge (10-90 %), the edge's centre is outside
the scan, the falling edge is within 3 σ_rise of the rising one, or χ²/dof
(Poisson + 1 % weights) is above 20. The falling side is the loss on the
curved upstream surface, never used. Without an accepted scan:
``DEFAULT_HEIGHT_MM`` 0.040 mm (±15 %, run to run) at 10 keV with S1 ≤
0.04 mm, the conditions it was measured at; elsewhere no height.

Not included: the beam's decay or top-up within a point (the monitor
counts it already) and any dose before the scan, unless the caller adds
the earlier scans' totals (the timeline does, F107).
"""
from dataclasses import dataclass, field
import math

import numpy as np

from . import absorbers
from . import flux
from .monitor import gain_factor, REFERENCE

UNITS = ('photons', 'monitor')


class DoseError(ValueError):
    """The dose cannot be worked out (the reason is the message)."""


@dataclass
class Dose:
    """The dose of the points of one scan: ``per_point`` received during each
    point, in ``unit``; ``notes`` say where each factor came from; ``bounds``:
    the relative (down, up) scale of every value (photons: the flux hand-off's;
    monitor counts: none)."""
    scan: int
    points: list
    per_point: np.ndarray
    unit: str
    notes: list = field(default_factory=list)
    bounds: tuple = (0.0, 0.0)
    to_middle: np.ndarray = None      # the dose from a point's start to the middle of its exposure (None: half)

    def cumulative(self):
        """The dose since the first point began, at the middle of each
        point's exposure."""
        d = np.asarray(self.per_point, float)
        half = d / 2 if self.to_middle is None else np.asarray(self.to_middle, float)
        return np.cumsum(d) - d + half

    def total(self):
        return float(np.sum(self.per_point))


def engineering_scale(total):
    """A power of 1000 that puts ``total`` between 1 and 1000: a burn fitted
    against dose uses it as its unit, so that the axis spans what a time in
    seconds does (the trend fits' derivative steps are absolute for a
    parameter at 0, and overflow on an axis of 1e12)."""
    if not total > 0 or not math.isfinite(total):
        return 1.0
    return 10.0 ** (3 * math.floor(math.log10(total) / 3 + 1e-12))


def scaled_unit(unit, scale):
    """'1e+12 photons' for ``scale`` 1e12; ``unit`` itself for 1."""
    return unit if scale == 1 else '%.0e %s' % (scale, unit)


def absorber_factor(params, absfac=None):
    """(A, note): the factor the scan's absorber setting attenuates the beam
    by. ``absfac``: a factor per unit or an ``absorbers.Foils``; None: the
    calibrated foils at the scan's energy where they apply, else the factor
    per unit of 50 µm Al at the energy (``absorbers.factor_at``), as the
    window's defaults. DoseError when neither is known and an absorber is in."""
    n = params.get('Absorber')
    n = 0 if n is None else int(n)
    if n == 0:
        return 1.0, 'no absorber'
    if absfac is None:
        wl = params.get('Wavelength')
        e = absorbers.energy_kev(wl) if isinstance(wl, (int, float)) and wl > 0 else None
        foils = absorbers.calibrated(e)
        if foils is not None:
            return float(absorbers.attenuation(foils, n)), 'absorber %d: calibrated foils at %.2f keV' % (n, foils.energy_kev)
        f, how = absorbers.factor_at(e)
        if f is None:
            raise DoseError('absorber %d: its factor is not known (%s)' % (n, how))
        return float(absorbers.attenuation(f, n)), 'absorber %d: %s' % (n, how)
    return float(absorbers.attenuation(absfac, n)), 'absorber %d: factor %s given' % (n, absfac)


SHUTTERS = ('closed', 'open')

# The beam's height for the dose from the height scans' rising edge (module docstring; study #60)
HEIGHT_PER_RISE_FWHM = math.sqrt(2 * math.pi) / (2 * math.sqrt(2 * math.log(2)))   # √(2π)σ over 2.355σ: 1.0645
RISE_GUARDS = dict(foot=0.25, edge_points=2, separation=3.0, chi2_dof=20.0)
DEFAULT_HEIGHT_MM = 0.040          # no accepted scan: 10 keV, S1 gap <= 0.04 mm (run medians 0.035-0.045)
DEFAULT_HEIGHT_REL = 0.15          # its run-to-run uncertainty
DEFAULT_HEIGHT_KEV = (9.9, 10.6)   # the energies it was measured at (10, 10.05, 10.52 keV)
DEFAULT_HEIGHT_MAX_S1_MM = 0.040
NEAR_SCANS = 3                     # beam_height(near=n): the nearest accepted height scans with n's S1 gap (an assumption)


@dataclass
class RisingEdge:
    """The rising edge of one height scan: its erf FWHM (the scan's x
    units, mm for sh), the height for the dose (× HEIGHT_PER_RISE_FWHM), its
    centre; ``why`` the guard that refused it ('' when accepted)."""
    scan: int
    fwhm: float
    height: float
    centre: float
    why: str = ''

    @property
    def ok(self):
        return not self.why


def rising_edge(x, y, sigma=None, scan=0, guards=None):
    """The rising edge of a height scan (x the height, y the reflected
    signal per monitor), under ``guards`` (default RISE_GUARDS)."""
    from . import peaks
    g = dict(RISE_GUARDS, **(guards or {}))
    x, y = np.asarray(x, float), np.asarray(y, float)
    o = np.argsort(x)
    x, y = x[o], y[o]
    sig = None if sigma is None else np.asarray(sigma, float)[o]
    r = peaks.fit_box(x, y, sig)
    if not r.ok:
        return RisingEdge(scan, math.nan, math.nan, math.nan, 'no box fit (%s)' % r.message)
    (c1, w1), (c2, w2) = r.edges
    e = RisingEdge(scan, float(w1), float(w1) * HEIGHT_PER_RISE_FWHM, float(c1))
    srise = w1 / (2 * math.sqrt(2 * math.log(2)))
    frac = peaks._step(x, c1, w1)
    if not y[0] < g['foot'] * np.max(y):
        e.why = 'the rise was not scanned from its foot (first point %.0f %% of the peak)' % (100 * y[0] / np.max(y))
    elif int(np.sum((frac > 0.1) & (frac < 0.9) & (x < 0.5 * (c1 + c2)))) < g['edge_points']:
        e.why = 'fewer than %d points on the rising edge' % g['edge_points']
    elif not x[0] <= c1 <= x[-1]:
        e.why = 'the edge is outside the scan'
    elif not c2 - c1 > g['separation'] * srise:
        e.why = 'the falling edge is within %g sigma of the rising one' % g['separation']
    elif sig is not None and r.chi2_dof is not None and r.chi2_dof > g['chi2_dof']:
        e.why = 'chi2/dof %.1f above %g' % (r.chi2_dof, g['chi2_dof'])
    return e


@dataclass
class BeamHeight:
    """The beam's height at the sample for the dose (mm), where it came
    from ('height scans' or 'default'; None and ``note`` the reason when
    neither applies), the edges used and refused."""
    height_mm: float
    source: str
    uncertainty_rel: float = None
    edges: list = field(default_factory=list)
    refused: list = field(default_factory=list)
    note: str = ''


def s1_gap_mm(params):
    """The S1 slit's vertical gap (mm): S1T + S1B, the two half-openings (owner, 2026-11-25, OQ-1: the
    header's slit values are half-openings). None when not recorded."""
    t, b = params.get('S1T'), params.get('S1B')
    try:
        return float(t) + float(b)
    except (TypeError, ValueError):
        return None


def height_scan_data(columns, counter='Pilatus', monitor='Monc'):
    """(x, y, sigma) of a height scan: the first column (the scanned motor),
    the counter per monitor, σ Poisson + 1 %."""
    x = np.asarray(columns[next(iter(columns))], float)
    n = np.asarray(columns[counter], float)
    m = np.asarray(columns[monitor], float)
    return x, n / m, np.sqrt(np.maximum(n, 1.0) + (0.01 * n) ** 2) / m


def default_height(params):
    """BeamHeight from the study's default, where its conditions hold."""
    wl = params.get('Wavelength')
    e = absorbers.energy_kev(wl) if isinstance(wl, (int, float)) and wl > 0 else None
    gap = s1_gap_mm(params)
    if e is None or not DEFAULT_HEIGHT_KEV[0] <= e <= DEFAULT_HEIGHT_KEV[1]:
        return BeamHeight(None, None, note='no accepted height scan, and the default is for 10 keV (%s)'
                          % ('energy unknown' if e is None else '%.2f keV' % e))
    if gap is None or gap > DEFAULT_HEIGHT_MAX_S1_MM + 1e-9:
        return BeamHeight(None, None, note='no accepted height scan, and the default is for S1 <= 0.04 mm (%s)'
                          % ('S1 unknown' if gap is None else '%.3f mm' % gap))
    return BeamHeight(DEFAULT_HEIGHT_MM, 'default', DEFAULT_HEIGHT_REL,
                      note='no accepted height scan: the study\'s default for 10 keV, S1 <= 0.04 mm (+-15 %)')


def point_incidence(columns, params, idx):
    """Each point's incidence α (radians; ``cuts.true_incidence``) for the
    points ``idx`` of a scan. DoseError when it is unknown or not above 0."""
    from .cuts import true_incidence
    cols = {k: np.asarray(v, float) for k, v in columns.items() if k in ('In_Rot', 'H', 'K', 'L')}
    a0 = params.get('In_Rot')
    if a0 is None and 'In_Rot' not in cols:
        raise DoseError('incidence unknown (no In_Rot): no dose per area')
    wl = params.get('Wavelength')
    alpha = np.array([true_incidence(cols, i, wl, float(a0) if a0 is not None else 0.0) for i in idx])
    if np.any(alpha <= 0):
        raise DoseError('incidence %g° at or below 0: no footprint' % float(np.degrees(alpha.min())))
    return alpha


# ---- F109 (owner, 2026-11-25): the beam's width, and the dose as peak and average ----

GAUSS_FWHM_PER_SIGMA = 2 * math.sqrt(2 * math.log(2))
WIDTH_PER_SIGMA = math.sqrt(2 * math.pi)  # the dose's convention for a size: √(2π)σ, the inverse of the profile's peak
DEFAULT_WIDTH_MM = 1.0       # owner (F109): prefill 1 mm; read as √(2π)σx, so a dose with it is the peak dose
EXTENT_SHARE = 0.90          # the averaged dose's extents: the smallest area that received 90 % of the dose (assumption, asked)
TOP_AREA_SHARE = 0.10        # owner (F109): the peak split, the most exposed 10 % of that area against the other 90 %
S1_H_MOTORS = ('s1l', 's1r', 's1hc', 's1hg')   # S1's horizontal motors (assumption: the file's S1L, S1R and pseudo-motors)
WIDTH_GUARDS = dict(points=3, chi2_dof=20.0)


@dataclass
class SlitProfile:
    """The beam's horizontal profile from one S1 slit scan: ``kind`` the
    shape fitted ('peak', 'edge' or 'box', ``peaks.fit_scan``), the beam's
    ``fwhm`` and ``sigma`` (mm; a peak's after the gap correction), its
    ``width`` for the dose (√(2π)σ), the ``centre``; ``why`` the guard that
    refused it ('' when accepted)."""
    scan: int
    kind: str
    fwhm: float
    sigma: float
    width: float
    centre: float
    why: str = ''

    @property
    def ok(self):
        return not self.why


@dataclass
class BeamWidth:
    """The beam's width at the sample for the dose (mm, √(2π)σx), where it
    came from ('slit scans' or 'default'), the beam's FWHM, the profiles
    used and refused."""
    width_mm: float
    source: str
    fwhm_mm: float = None
    profiles: list = field(default_factory=list)
    refused: list = field(default_factory=list)
    note: str = ''


def is_slit_scan(command, motors=S1_H_MOTORS):
    """True for a scan of S1's horizontal motors: ascan, a2scan, dscan or
    d2scan whose first motor is one of ``motors`` (any case), over a range."""
    w = str(command).split()
    if w and w[0] == '#S':
        w = w[2:]
    return (len(w) > 3 and w[0] in ('ascan', 'a2scan', 'dscan', 'd2scan') and w[1].lower() in motors
            and w[2] != w[3])


def s1_hgap_mm(params):
    """S1's horizontal gap (mm): S1L + S1R, two half-openings (OQ-1). None when not recorded."""
    try:
        return float(params.get('S1L')) + float(params.get('S1R'))
    except (TypeError, ValueError):
        return None


def slit_profile(x, y, sigma=None, gap_mm=None, scan=0, guards=None):
    """The beam's horizontal profile from one S1 slit scan (``x`` the slit's
    position in mm, ``y`` the signal), by the shape that fits it best
    (``peaks.fit_scan``):

    - a narrow gap moved across the beam reads the beam convolved with the
      gap, a **peak**: σ² = σ_fit² − g²/12, ``gap_mm`` g (a uniform gap's
      variance; none when not given);
    - one blade moved reads an **edge**, whose error-function FWHM is the
      beam's;
    - a gap wider than the beam moved across reads a **box**, each of its
      edges the beam's FWHM (their mean is used); a box whose plateau is
      narrower than its edges is read as the peak it is.

    Refused (``why``) when nothing fits, fewer than ``points`` points lie
    within a FWHM of the centre (of each edge, for a box), the centre is
    outside the scan, the gap is as wide as a peak, or χ²/dof (when
    ``sigma`` is given) is above ``chi2_dof``."""
    from . import peaks
    g = dict(WIDTH_GUARDS, **(guards or {}))
    x, y = np.asarray(x, float), np.asarray(y, float)
    nan = math.nan
    r = peaks.fit_scan(x, y, sigma)
    kind = getattr(r, 'kind', '')
    if not r.ok or not r.peaks:
        return SlitProfile(scan, kind, nan, nan, nan, nan, 'no fit (%s)' % r.message)
    if kind == 'box' and 'peak' in getattr(r, 'candidates', {}):
        (c1, w1), (c2, w2) = r.edges
        if abs(c2 - c1) < 0.5 * (abs(w1) + abs(w2)):     # a plateau narrower than its edges is a peak
            r, kind = r.candidates['peak'], 'peak'
    pk = r.peaks[0]
    why = ''
    if kind == 'box':
        (c1, w1), (c2, w2) = r.edges
        fwhm, centres = 0.5 * (abs(w1) + abs(w2)), ((c1, abs(w1)), (c2, abs(w2)))
    else:
        fwhm, centres = abs(pk.fwhm), ((pk.centre, abs(pk.fwhm)),)
    sig = fwhm / GAUSS_FWHM_PER_SIGMA
    if kind == 'peak' and gap_mm:
        var = sig ** 2 - float(gap_mm) ** 2 / 12.0
        if var <= 0:
            why = 'the gap (%.3g mm) is as wide as the profile (FWHM %.3g mm)' % (gap_mm, fwhm)
        sig = math.sqrt(max(var, 0.0))
        fwhm = sig * GAUSS_FWHM_PER_SIGMA
    if not why:
        for c, w in centres:
            if not x.min() <= c <= x.max():
                why = 'the %s is outside the scan' % ('edge' if kind != 'peak' else 'centre')
            elif int(np.sum(np.abs(x - c) <= w)) < g['points']:
                why = 'fewer than %d points within a FWHM of the %s' % (g['points'], 'edge' if kind != 'peak' else 'centre')
            if why:
                break
    if not why and sigma is not None and r.chi2_dof is not None and r.chi2_dof > g['chi2_dof']:
        why = 'chi2/dof %.1f above %g' % (r.chi2_dof, g['chi2_dof'])
    return SlitProfile(scan, kind, float(fwhm), float(sig), float(sig * WIDTH_PER_SIGMA), float(pk.centre), why)


def default_width():
    """BeamWidth from the owner's prefill (F109): 1 mm, read as √(2π)σx."""
    return BeamWidth(DEFAULT_WIDTH_MM, 'default', DEFAULT_WIDTH_MM * GAUSS_FWHM_PER_SIGMA / WIDTH_PER_SIGMA,
                     note='no accepted S1 slit scan: the owner\'s prefill, 1 mm (read as sqrt(2 pi) sigma, FWHM 0.94 mm)')


@dataclass
class DoseSummary:
    """The dose a scan gave the sample, as a map over the footprint (F109):
    ``peak`` (the most exposed point), ``average`` (over the extents, the
    smallest area that received ``extent`` of the dose, ``area_mm2``),
    ``top`` (the mean of the most exposed ``top_share`` of that area,
    ``top_area_mm2``) and ``rest`` (the mean of the other part), all in
    ``unit`` (per mm²); ``total`` what the sample received (``unit``
    without the /mm2); the beam's ``width_mm`` and ``height_mm`` (√(2π)σ).
    For one incidence and a Gaussian beam the ratios are fixed: with P the
    extent, peak/average = −ln(1 − P)/P (2.56 at 90 %)."""
    unit: str
    total: float
    peak: float
    average: float
    top: float
    rest: float
    area_mm2: float
    top_area_mm2: float
    width_mm: float
    height_mm: float
    extent: float = EXTENT_SHARE
    top_share: float = TOP_AREA_SHARE
    notes: list = field(default_factory=list)
    captured: float = 1.0          # the share of the dose the map's grid holds (a check: above 0.9999)

    def text(self, fmt='%.3g'):
        """One line for a dialog: peak, average and the split."""
        f = lambda v: fmt % v
        return ('peak %s, average %s %s over %s mm2 (%.0f %% of the dose); most exposed %.0f %% of it %s, '
                'the other %.0f %% %s' % (f(self.peak), f(self.average), self.unit, f(self.area_mm2),
                                         100 * self.extent, 100 * self.top_share, f(self.top),
                                         100 * (1 - self.top_share), f(self.rest)))


def dose_map(per_point, sin_alpha, width_mm, height_mm, extent=EXTENT_SHARE, top=TOP_AREA_SHARE, unit='photons',
             nx=400, ny=700):
    """DoseSummary of points that gave the sample ``per_point`` (photons, or
    monitor counts) each at incidence sin α ``sin_alpha``, for a Gaussian beam
    of ``width_mm`` × ``height_mm`` (√(2π)σ each, the dose's convention).

    The dose per mm² at (x across, y along the beam) is
    D = f(x) · Σ_i N_i sin α_i g(y sin α_i), f and g the beam's normalised
    profiles: each point's footprint is the beam stretched by 1/sin α_i along
    the beam, all centred on one spot. The peak, D(0, 0) = Σ N_i sin α_i /
    (width · height), is the dose per area ``scan_dose(beam_mm=)`` gives. The
    rest comes from D on a grid (a quarter, by symmetry; geometric along y, to
    span the footprints of every α): the cells sorted by D, the extents are
    the most exposed cells that received ``extent`` of the total, and the top
    part their most exposed ``top`` share by area."""
    N = np.atleast_1d(np.asarray(per_point, float))
    s = np.broadcast_to(np.asarray(sin_alpha, float), N.shape)
    w, h = float(width_mm), float(height_mm)
    if not (w > 0 and h > 0):
        raise DoseError('beam size %g x %g mm: width and height must be positive' % (w, h))
    if not 0 < extent <= 1 or not 0 < top < 1:
        raise ValueError('extent %r in (0, 1], top %r in (0, 1)' % (extent, top))
    if np.any(s <= 0) or np.any(s > 1):
        raise DoseError('sin(incidence) must be in (0, 1]')
    keep = N > 0
    total = float(np.sum(N[keep]))
    if not total > 0:
        raise DoseError('no dose: every point gave 0')
    su, inv = np.unique(np.round(s[keep], 12), return_inverse=True)
    Nu = np.bincount(inv, weights=N[keep])                      # the dose at each distinct incidence
    sx, sy = w / WIDTH_PER_SIGMA, h / WIDTH_PER_SIGMA
    foot = sy / su                                              # σ of each footprint along the beam
    xe = np.linspace(0.0, 8.0 * sx, nx + 1)
    ye = np.concatenate([[0.0], np.geomspace(1e-3 * foot.min(), 8.0 * foot.max(), ny)])
    xm, dx = 0.5 * (xe[1:] + xe[:-1]), np.diff(xe)
    ym, dy = 0.5 * (ye[1:] + ye[:-1]), np.diff(ye)
    fx = np.exp(-0.5 * (xm / sx) ** 2) / (WIDTH_PER_SIGMA * sx)
    gy = (np.exp(-0.5 * (ym[:, None] / foot[None, :]) ** 2) / (WIDTH_PER_SIGMA * foot[None, :])) @ Nu
    D = (fx[:, None] * gy[None, :]).ravel()
    A = (4.0 * dx[:, None] * dy[None, :]).ravel()
    o = np.argsort(-D)
    cum_a, cum_d = np.cumsum(A[o]), np.cumsum((D * A)[o])
    a_ext = float(np.interp(extent * total, cum_d, cum_a))
    a_top = top * a_ext
    d_top = float(np.interp(a_top, cum_a, cum_d))
    peak = float(np.sum(Nu * su)) / (w * h)
    notes = ['beam %g x %g mm (sqrt(2 pi) sigma; FWHM %.3g x %.3g mm), Gaussian; %d incidence%s'
             % (w, h, w / WIDTH_PER_SIGMA * GAUSS_FWHM_PER_SIGMA, h / WIDTH_PER_SIGMA * GAUSS_FWHM_PER_SIGMA,
                len(su), '' if len(su) == 1 else 's'),
             'the extents: the smallest area that received %.0f %% of the dose (%.3g mm2)' % (100 * extent, a_ext)]
    return DoseSummary(unit + '/mm2', total, peak, extent * total / a_ext, d_top / a_top,
                       (extent * total - d_top) / (a_ext - a_top), a_ext, a_top, w, h, extent, top, notes,
                       float(cum_d[-1] / total))


def scan_dose(columns, params, points=None, unit='photons', beam_mm=None, absfac=None, monitor='Monc', scan=0,
              shutter='closed', point_times=None):
    """Dose of the points ``points`` (all when None) of one scan, from its
    data ``columns`` and header ``params`` (module docstring). ``unit``:
    'photons' (falls back to 'monitor', with the reason in the notes, when
    the gain or the energy is unknown) or 'monitor' (counts at 5 µA/V, the
    absorbers taken out). ``beam_mm``: (width, height) of the beam for the
    dose per mm². ``shutter``: 'closed' between points (default) or 'open'
    (fast mode; needs ``point_times``, a ``timing.PointTimes`` with start
    times)."""
    if shutter not in SHUTTERS:
        raise ValueError('shutter %r: one of %s' % (shutter, ', '.join(SHUTTERS)))
    if unit not in UNITS:
        raise ValueError('unit %r: one of %s' % (unit, ', '.join(UNITS)))
    mon = columns.get(monitor)
    if mon is None and monitor == 'Monc':
        mon = columns.get('monc')
    if mon is None:
        raise DoseError('no %s column' % monitor)
    mon = np.asarray(mon, float)
    idx = list(range(len(mon))) if points is None else [int(p) for p in points]
    m = mon[idx]
    sec = columns.get('Seconds')
    sec = None if sec is None else np.asarray(sec, float)[idx]
    A, how = absorber_factor(params, absfac)
    notes = [how]
    S = params.get('MoncGain')
    wl = params.get('Wavelength')
    e = absorbers.energy_kev(wl) if isinstance(wl, (int, float)) and wl > 0 else None
    bounds = (0.0, 0.0)
    out_unit = unit
    if unit == 'photons':
        why = None
        if S is None:
            why = 'Monc gain unknown'
        elif e is None:
            why = 'energy unknown'
        elif not flux.E_KEV[0] <= e <= flux.E_KEV[-1]:
            why = '%.3g keV is outside the 5-30 keV table' % e
        if why is not None:
            notes.append('photons asked, but %s: monitor counts used' % why)
            out_unit = 'monitor'
    if out_unit == 'photons':
        per = np.zeros(len(idx))
        dark = []
        for k, mk in enumerate(m):
            rate = mk / sec[k] if sec is not None and sec[k] > 0 else None
            f, flags = flux.photon_factor(S, e, rate)
            if f is None:              # the rate is not above the dark rate: no beam
                dark.append(idx[k])
                continue
            per[k] = mk / f / A
        if sec is None:
            notes.append('no Seconds column: the monitor\'s dark rate not subtracted')
        if dark:
            notes.append('points %s: the monitor at or below its dark rate, dose 0' % dark)
        _, lo, hi, _f = flux.photons_per_second(1.0, 1.0, e, S, dark_hz=0.0, temp_c=flux.TABLE_T_C,
                                                pressure_kpa=flux.TABLE_P_KPA)
        best = flux.photons_per_second(1.0, 1.0, e, S, dark_hz=0.0, temp_c=flux.TABLE_T_C,
                                       pressure_kpa=flux.TABLE_P_KPA)[0]
        bounds = (1 - lo / best, hi / best - 1)
        notes.append('photons at the Monc chamber\'s exit, %.2f keV, %s (%s)'
                     % (e, params.get('MoncGainText') or '%g A/V' % S, 'flux route D, bounds -%.1f/+%.1f %%'
                        % (100 * bounds[0], 100 * bounds[1])))
        name = 'photons'
    else:
        g = 1.0
        if S is not None:
            g = gain_factor(S)
            notes.append('monitor counts at %g uA/V (gain factor %.4g)' % (REFERENCE * 1e6, g))
        else:
            notes.append('Monc gain unknown: counts as recorded')
        per = m / (A * g)
        name = 'Monc counts'
    if beam_mm is not None:
        w, h = (float(x) for x in beam_mm)
        if not (w > 0 and h > 0):
            raise DoseError('beam size %r: width and height must be positive' % (beam_mm,))
        alpha = point_incidence(columns, params, idx)
        per = per * np.sin(alpha) / (w * h)
        notes.append('per mm2 of footprint, beam %g x %g mm (given), footprint %.3g-%.3g mm long'
                     % (w, h, float(np.min(h / np.sin(alpha))), float(np.max(h / np.sin(alpha)))))
        name += '/mm2'
    to_middle = None
    if shutter == 'open':
        start = getattr(point_times, 'start', None)
        if start is None or sec is None:
            raise DoseError('shutter open: the per-point start times and the Seconds column are needed')
        start = np.asarray(start, float)[idx]
        end = getattr(point_times, 'end', None)
        last = (float(np.asarray(end, float)[idx[-1]]) - start[-1]) if end is not None else float(sec[-1])
        span = np.append(np.diff(start), max(last, float(sec[-1])))
        if np.any(span < sec - 1e-6):
            raise DoseError('shutter open: a point starts before the previous one has finished counting')
        to_middle = per / 2
        per = per * span / sec            # the counting rate over the whole time to the next point
        notes.append('shutter open between points (fast mode): the beam from each start to the next, %.3g s in all'
                     % float(np.sum(span)))
    return Dose(scan, idx, per, name, notes, bounds, to_middle)
