"""The radiation dose each point of a scan gives the sample (F98, F107, F76;
2026-11-24).

**The beam on the sample during point i.** The Monc ion chamber sits
upstream of the absorbers: the reduction multiplies counts by the
absorber factor A and divides by the monitor M (``lss_core.normalise``),
and by the gain factor g = S_ref/S. So, in monitor counts at the
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

The beam's size is not read from the header: which slit defines it, and
whether the blades are half-openings, is a question for the owner
(questions.md, 2026-11-24). A footprint longer than the sample changes
nothing: the dose per area of the illuminated part stays the same.

**Cumulative.** ``Dose.cumulative()``: the dose received since the first
point began, at the middle of each point, which is the convention of the
burn's time axis (``burn.frame_times``, ``time='exposure'``). The shutter
is assumed closed between points (owner, 2026-11-21: the default), so
the overhead between frames adds no dose.

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

    def cumulative(self):
        """The dose since the first point began, at the middle of each point."""
        d = np.asarray(self.per_point, float)
        return np.cumsum(d) - d / 2

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


def scan_dose(columns, params, points=None, unit='photons', beam_mm=None, absfac=None, monitor='Monc', scan=0):
    """Dose of the points ``points`` (all when None) of one scan, from its
    data ``columns`` and header ``params`` (module docstring). ``unit``:
    'photons' (falls back to 'monitor', with the reason in the notes, when
    the gain or the energy is unknown) or 'monitor' (counts at 5 µA/V, the
    absorbers taken out). ``beam_mm``: (width, height) of the beam for the
    dose per mm²."""
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
    return Dose(scan, idx, per, name, notes, bounds)
