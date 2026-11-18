"""Photons per second from ion-chamber counts (F54): the quick route.

Source: docs/handoff/xray_fluxor_counts_to_photons.md (the owner's
xray_fluxor repository, https://github.com/Dave-J-W/xray_fluxor, published
commit 67b70b0), route D, "quick estimate". Photons/s **at the chamber's
exit plane** (windows and air to the sample not included), for the MonP
and MonC chambers read through an SR570 and a V2F (g = 1e5 Hz/V):

    Φ = (N/t − D) · q(E) · (S / 500 nA/V) · gas(T, P) · wall(E)

- q(E): photons/s per net Hz at 500 nA/V and the site-mean gas, from the
  hand-off's table (5–30 keV), interpolated linearly in log q against
  log E (an interpolation between the table's energies; the hand-off's
  own route B computes it exactly);
- S: the SR570 sensitivity (A/V), from SPEC's `#M Monc Gain` line;
- gas: +0.34 % per K above 24.9 °C, −1 % per kPa above 98.99 kPa (the
  conditions of the table; the hand-off's §3 examples reproduce it);
- wall: the lane's wall-loss correction, 1 below 18 keV; MonC ×1.02 at
  20 keV, ×1.16 at 25, ×1.37 at 30 (hand-off §5); MonP from its own row;
- D: the dark rate at the same gain (not in SPEC files: 0 by default, and
  flagged; it matters at low rates, δD/N).

Bounds (hand-off §7, "bounds, not a confidence interval"): ±3.6 % below
13 keV; above it asymmetric, known here only at 30 keV (MonP +23.2/−19.7 %,
MonC +18.2/−14.9 %), which this module uses for all energies above 13 keV
(wider than needed in between; flagged). Not checked against an
independent flux measurement (hand-off §7).

For normalising within one energy and gain most of this cancels (≲ 0.2 %,
hand-off §7); the absolute value matters for "per incident photon".
"""
import math

E_KEV = (5.0, 8.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0)
FORMULA_PER_HZ = (9.13e5, 2.65e6, 4.37e6, 6.56e6, 1.08e7, 2.02e7, 3.26e7, 4.78e7)
MONP_BEST_PER_HZ = (9.13e5, 2.65e6, 4.37e6, 6.56e6, 1.08e7, 2.18e7, 4.42e7, 8.43e7)
MONC_WALL = ((18.0, 1.0), (20.0, 1.02), (25.0, 1.16), (30.0, 1.37))
TABLE_SENSITIVITY = 500e-9      # A/V
TABLE_T_C = 24.9
TABLE_P_KPA = 98.99
LOW_BOUND_KEV = 13.0
BOUNDS_LOW_E = (0.036, 0.036)                       # (+, −) below 13 keV
BOUNDS_30KEV = {'MonP': (0.232, 0.197), 'MonC': (0.182, 0.149)}
PROVENANCE = ('xray_fluxor hand-off "monitor counts or current -> photons/s", route D (published commit '
              '67b70b0); docs/handoff/xray_fluxor_counts_to_photons.md')


def _loglog(x, xs, ys):
    if not xs[0] <= x <= xs[-1]:
        raise ValueError('%g keV is outside the table (%g-%g keV)' % (x, xs[0], xs[-1]))
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if x <= x1:
            w = math.log(x / x0) / math.log(x1 / x0)
            return math.exp(math.log(y0) + w * math.log(y1 / y0))


def per_hz(energy_kev, lane='MonC'):
    """Photons/s per net Hz at 500 nA/V, 24.9 °C, 98.99 kPa (best estimate)."""
    if lane == 'MonP':
        return _loglog(energy_kev, E_KEV, MONP_BEST_PER_HZ)
    if lane != 'MonC':
        raise ValueError('lane must be MonP or MonC')
    q = _loglog(energy_kev, E_KEV, FORMULA_PER_HZ)
    if energy_kev <= MONC_WALL[0][0]:
        return q
    for (x0, y0), (x1, y1) in zip(MONC_WALL, MONC_WALL[1:]):
        if energy_kev <= x1:
            return q * (y0 + (y1 - y0) * (energy_kev - x0) / (x1 - x0))   # linear between the hand-off's points


def photons_per_second(counts, seconds, energy_kev, sensitivity, lane='MonC', dark_hz=None,
                       temp_c=None, pressure_kpa=None):
    """(best, low, high, flags) photons/s at the chamber's exit plane for
    ``counts`` in ``seconds`` at ``energy_kev`` with SR570 ``sensitivity``
    (A/V). ``dark_hz``, ``temp_c``, ``pressure_kpa``: None uses 0, 24.9 °C,
    98.99 kPa and flags it."""
    flags = []
    if seconds is None or not seconds > 0:
        return float('nan'), float('nan'), float('nan'), ['count time <= 0']
    if dark_hz is None:
        dark_hz = 0.0
        flags.append('dark not known: 0 used')
    if temp_c is None:
        temp_c = TABLE_T_C
        flags.append('temperature not known: 24.9 C used')
    if pressure_kpa is None:
        pressure_kpa = TABLE_P_KPA
        flags.append('pressure not known: site mean 98.99 kPa used (+-0.8 %)')
    rate = counts / seconds - dark_hz
    gas = (1 + 0.0034 * (temp_c - TABLE_T_C)) * (1 - 0.01 * (pressure_kpa - TABLE_P_KPA))
    best = rate * per_hz(energy_kev, lane) * (sensitivity / TABLE_SENSITIVITY) * gas
    if energy_kev < LOW_BOUND_KEV:
        up, down = BOUNDS_LOW_E
    else:
        up, down = BOUNDS_30KEV[lane]
        flags.append('above 13 keV: the 30 keV bounds are used')
    return best, best * (1 - down), best * (1 + up), flags
