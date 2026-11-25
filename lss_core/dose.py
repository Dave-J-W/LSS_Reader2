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
        from .cuts import true_incidence
        w, h = (float(x) for x in beam_mm)
        if not (w > 0 and h > 0):
            raise DoseError('beam size %r: width and height must be positive' % (beam_mm,))
        cols = {k: np.asarray(v, float) for k, v in columns.items() if k in ('In_Rot', 'H', 'K', 'L')}
        a0 = params.get('In_Rot')
        if a0 is None and 'In_Rot' not in cols:
            raise DoseError('incidence unknown (no In_Rot): no dose per area')
        alpha = np.array([true_incidence(cols, i, wl, float(a0) if a0 is not None else 0.0) for i in idx])
        if np.any(alpha <= 0):
            raise DoseError('incidence %g° at or below 0: no footprint' % float(np.degrees(alpha.min())))
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
