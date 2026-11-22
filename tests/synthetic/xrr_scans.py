"""Reflectivity measured as scans, in reduced form, with the truth beside it.

``measure(profile, plan)`` turns a true curve R(Qz) (``synthetic.xrr``)
into what the reader's per-frame reduction gives (``lss_core.reflectivity.
frame_row``): for every scan, rows

    [Qz, net, σ_net, S, σ_S, B1, B2]      (all per Monc count)

like ``ReflectivityResult.per_scan``, so they can go straight into
``lss_core.reflectivity.patch`` or ``stitching.join`` or any new patching
method, and the true scale of every scan, the true join factors, the
nominal (foil) factors and every deliberate fault are known.

Measurement model (per point k of scan m; parameters in ``Beamline``):

* the beam on the sample relative to scan 1: ``slit_gain`` g_m (an S1
  change) times ``trend(Qz)`` (slits that move along a scan);
* reflected counts N = R(Qz) · flux · t · g_m · trend / A_m, A_m the true
  attenuation of absorber setting n_m: the calibrated foils
  (``lss_core.absorbers.Foils``) times ``attenuation_error`` (a foil that
  is not what the calibration says);
* background per pixel b = (background · flux · g_m · trend / A_m + dark) · t:
  scattering from the sample goes through the same foils, dark counts do not;
* Monc M ~ Poisson(monc_rate · t · h_m · trend), h_m = ``monitor_gain``
  (= g_m unless a fault says Monc saw only part of the slit change, as in
  PHYSICS_ISSUES P29), optionally with a relative Gaussian jitter (rounded
  to whole counts); Monp ~ Poisson(monp_rate · t), upstream of the slits;
* the reader's boxes: a signal box of 21 columns × 11 rows around the beam
  and two background boxes of the same size (reader defaults: slit 21 × 11,
  ``sumROI`` takes slit − 2 and adds one each side). Each box is drawn as a
  core of 5 rows plus 6 outer rows, because the reader uses only the 5
  rows for the first frame of a scan when 0.02 < Qz < 0.03
  (``Experiment.reflectivity``: ``low_qz_slit=(first or low_qz_slit)``,
  PHYSICS_ISSUES P18, kept as coded); the
  reflected beam lies inside the core. S, B1, B2 are Poisson counts;
  net = (S − (B1 + B2)/2) / M;
* σ_net = sqrt(S + (B1 + B2)/4) / M (``errors='counting'``: Poisson on the
  detector counts, the budget model's counting part), plus net²/M with
  ``errors='counting+monitor'`` (Poisson on Monc, applied once to the net
  value). The legacy per-pixel monitor term I²/M³ (PHYSICS_ISSUES P2) needs
  the pixels: render the scans (``synthetic.xrr_images``) and reduce them.

True scale of scan m: s_m = A_m · monc_rate / (flux · g_m / h_m), so that
E[net] · s_m = R(Qz) (E over the counts at the expected monitor). In the
legacy chain (scans in Qz order, each new one multiplied onto the data so
far, which stay in the first scan's scale) the true factor of join j is
s_{order[j+1]} / s_{order[0]}.

Default numbers (``Beamline``) are taken from the public NX school SPEC
file, scans 6–9 at 10 keV (read 2026-11-22): Monc about 1.1e5 /s and Monp
2.15e5 /s at the first slits; about 4e5 counts/s in the ROI at the first
point of each scan, absorbers 41, 31, 24, 18; with the calibrated foils
that means about 2.5e12 counts/s at R = 1 without absorbers. The
background level is an assumption (it makes the background comparable to
the signal near Qz = 0.45 Å⁻¹ on bare water, as the NX ROI counts suggest).
"""
import math
import os
import sys
from dataclasses import dataclass, field

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lss_core import absorbers  # noqa: E402
from lss_core.reflectivity import order_scans  # noqa: E402

from . import xrr  # noqa: E402

COLUMNS = ['Qz', 'net', 'net_err', 'S', 'S_err', 'B1', 'B2']    # per Monc count, as per_scan rows
ROI_COLS, ROI_ROWS, CORE_ROWS = 21, 11, 5      # reader's default box (slit 21 x 11) and its 5-row form
LOW_QZ_SLIT = (0.02, 0.03)                     # first frame of a scan in this Qz range: 5 rows


@dataclass
class Beamline:
    """Measurement parameters; defaults from NX school scans 6–9 (module
    docstring). ``flux``: reflected counts/s at R = 1, no absorber, scan-1
    slits. ``background``: counts/s per pixel per unit flux at the sample
    (attenuated by the foils); ``dark``: counts/s per pixel (not
    attenuated). ``max_rate``: counts/s in the ROI the automatic absorber
    choice stays below. ``monitor_jitter``: relative Gaussian noise of
    Monc beyond Poisson (0: Poisson only)."""
    flux: float = 2.5e12
    monc_rate: float = 1.1e5
    monp_rate: float = 2.15e5
    background: float = 2.0e-10
    dark: float = 0.0
    max_rate: float = 4.0e5
    monitor_jitter: float = 0.0
    energy_kev: float = xrr.ENERGY_KEV

    @property
    def wavelength(self):
        return xrr.HC_KEV_ANGSTROM / self.energy_kev

    def foils(self):
        """The calibrated foils at this energy (the nominal attenuation)."""
        f = absorbers.calibrated(self.energy_kev)
        return f if f is not None else absorbers.Foils(energy_kev=self.energy_kev)


@dataclass
class ScanSpec:
    """One scan as planned. ``absorber`` None: the smallest setting that
    keeps the first (brightest) point below ``Beamline.max_rate``.
    Faults: ``slit_gain`` (true beam relative to scan 1), ``monitor_gain``
    (Monc relative to scan 1; None = slit_gain, the monitor follows),
    ``attenuation_error`` (true attenuation / nominal). ``trend``: f(Qz)
    multiplying beam and Monc along the scan (None: 1)."""
    qz: np.ndarray
    absorber: int = None
    seconds: float = 1.0
    slit_gain: float = 1.0
    monitor_gain: float = None
    attenuation_error: float = 1.0
    trend: object = None


@dataclass
class ScanRecord:
    number: int
    qz: np.ndarray
    absorber: int
    seconds: np.ndarray
    monc: np.ndarray            # as drawn (whole counts)
    monp: np.ndarray
    counts: dict                # S_core, S_outer, B1_core, B1_outer, B2_core, B2_outer, peak (expected)
    core_only: np.ndarray       # True where the reader uses the 5-row boxes
    background_per_pixel: np.ndarray   # expected counts per pixel
    nominal_attenuation: float
    true_attenuation: float
    slit_gain: float
    monitor_gain: float
    scale: float                # s_m: E[net] * s_m = R

    @property
    def pilatus(self):
        """Raw counts in the signal box (the SPEC 'Pilatus' column)."""
        c = self.counts
        return np.where(self.core_only, c['S_core'], c['S_core'] + c['S_outer'])


@dataclass
class ReducedScans:
    """The output of ``measure``: rows, records and the truth."""
    per_scan: dict
    scans: dict                 # number -> ScanRecord
    order: list
    profile: object
    beamline: Beamline
    resolution: tuple = None
    errors: str = 'counting'
    seed: object = None
    notes: list = field(default_factory=list)

    def truth(self, qz):
        """The true R(Qz) the scans were drawn from (resolution included)."""
        return self.profile.reflectivity(np.asarray(qz, float), self.beamline.wavelength, self.resolution)

    def curves(self):
        """{scan: (N, 3) Qz, net, σ}: the first three columns."""
        return {k: v[:, :3].copy() for k, v in self.per_scan.items()}

    def true_scales(self):
        return {k: r.scale for k, r in self.scans.items()}

    def true_join_factors(self, order=None):
        """{join j: factor} of the legacy chain in ``order`` (default the
        reader's Qz order): s_{order[j+1]} / s_{order[0]}."""
        order = order or self.order
        s0 = self.scans[order[0]].scale
        return {j: self.scans[k].scale / s0 for j, k in enumerate(order[1:])}

    def true_steps(self, order=None):
        """{join j: s_b / s_a} between consecutive scans a, b of ``order``."""
        order = order or self.order
        return {j: self.scans[b].scale / self.scans[a].scale for j, (a, b) in enumerate(zip(order, order[1:]))}

    def nominal_join_factors(self, order=None):
        """{join j: (factor, relative error)}: the known ratios the reader
        would use (calibrated foils, ``Foils.step`` chained as the window's
        ``refJoinInfo`` does), blind to slit and monitor faults and to
        ``attenuation_error``."""
        order = order or self.order
        foils = self.beamline.foils()
        out, cum = {}, 1.0
        for j, (a, b) in enumerate(zip(order, order[1:])):
            r, rel = foils.step(self.scans[a].absorber, self.scans[b].absorber, qz=float(self.scans[b].qz[0]))
            cum *= r
            out[j] = (cum, rel)
        return out

    def combine(self, scales=None):
        """All scans multiplied by ``scales`` ({scan: s}, default the true
        ones) and averaged with inverse-variance weights where Qz coincide
        (to 1e-9). Returns (N, 3) Qz, R, σ sorted by Qz."""
        scales = scales or self.true_scales()
        q, y, w = [], [], []
        for k, v in self.per_scan.items():
            q.append(v[:, 0])
            y.append(v[:, 1] * scales[k])
            w.append(1.0 / np.maximum((v[:, 2] * scales[k]) ** 2, 1e-300))
        q, y, w = (np.concatenate(a) for a in (q, y, w))
        key = np.round(q, 9)
        uq = np.unique(key)
        idx = np.searchsorted(uq, key)
        sw = np.bincount(idx, w)
        sy = np.bincount(idx, w * y)
        return np.column_stack([uq, sy / sw, 1.0 / np.sqrt(sw)])


def choose_absorber(rate_at_r1, r_max, foils, max_rate, settings=range(64)):
    """Smallest setting n (by attenuation) with rate_at_r1 · r_max / A(n) ≤ max_rate."""
    best = None
    for n in sorted(settings, key=foils.factor):
        if rate_at_r1 * r_max / foils.factor(n) <= max_rate:
            return n
        best = n
    return best


def measure(profile, plan, beamline=None, resolution=None, errors='counting', seed=0,
            first_scan=1, expected=False):
    """Draw the scans of ``plan`` (list of ScanSpec) from ``profile``.
    ``seed``: an int or a numpy Generator; ``expected``: no noise (counts
    and monitors at their expectations, not rounded), for exact checks.
    Returns ReducedScans."""
    bl = beamline or Beamline()
    rng = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)
    foils = bl.foils()
    per_scan, records = {}, {}
    n_core, n_outer = CORE_ROWS * ROI_COLS, (ROI_ROWS - CORE_ROWS) * ROI_COLS
    draw = (lambda mu: np.asarray(mu, float)) if expected else (lambda mu: rng.poisson(mu).astype(float))
    for i, spec in enumerate(plan):
        num = first_scan + i
        qz = np.atleast_1d(np.asarray(spec.qz, dtype=float))
        t = np.broadcast_to(np.asarray(spec.seconds, dtype=float), qz.shape).copy()
        trend = np.ones_like(qz) if spec.trend is None else np.asarray(spec.trend(qz), float)
        R = profile.reflectivity(qz, bl.wavelength, resolution)
        g = float(spec.slit_gain)
        h = g if spec.monitor_gain is None else float(spec.monitor_gain)
        n = spec.absorber
        if n is None:
            n = choose_absorber(bl.flux * g * float(np.max(trend)), float(np.max(R)), foils, bl.max_rate)
        a_nom = foils.factor(n)
        a_true = a_nom * float(spec.attenuation_error)
        peak = R * bl.flux * t * g * trend / a_true
        b = (bl.background * bl.flux * g * trend / a_true + bl.dark) * t
        m_exp = bl.monc_rate * t * h * trend
        if expected:
            monc = m_exp.copy()
            monp = bl.monp_rate * t
        else:
            monc = rng.poisson(m_exp).astype(float)
            if bl.monitor_jitter:
                monc = np.round(monc * (1 + bl.monitor_jitter * rng.standard_normal(qz.size)))
            monp = rng.poisson(bl.monp_rate * t).astype(float)
        c = dict(S_core=draw(peak + n_core * b), S_outer=draw(n_outer * b),
                 B1_core=draw(n_core * b), B1_outer=draw(n_outer * b),
                 B2_core=draw(n_core * b), B2_outer=draw(n_outer * b), peak=peak)
        core = np.zeros(qz.size, bool)
        core[0] = LOW_QZ_SLIT[0] < qz[0] < LOW_QZ_SLIT[1]
        S = np.where(core, c['S_core'], c['S_core'] + c['S_outer'])
        B1 = np.where(core, c['B1_core'], c['B1_core'] + c['B1_outer'])
        B2 = np.where(core, c['B2_core'], c['B2_core'] + c['B2_outer'])
        net = (S - (B1 + B2) / 2.0) / monc
        var = (S + (B1 + B2) / 4.0) / monc ** 2
        if errors == 'counting+monitor':
            var = var + net ** 2 / monc
        elif errors != 'counting':
            raise ValueError("errors: 'counting' or 'counting+monitor'")
        per_scan[num] = np.column_stack([qz, net, np.sqrt(var), S / monc, np.sqrt(S) / monc,
                                         B1 / monc, B2 / monc])
        records[num] = ScanRecord(num, qz, int(n), t, monc, monp, c, core, b, a_nom, a_true, g, h,
                                  a_true * bl.monc_rate / (bl.flux * g / h))
    return ReducedScans(per_scan, records, order_scans(per_scan), profile, bl, resolution, errors, seed)


# ---- plans --------------------------------------------------------------------

def chain_plan(ranges, overlap=4, grid='coincide', seconds=1.0, **faults):
    """Scans with uniform steps: ``ranges`` = [(start, stop, step), ...];
    scan k+1 starts at the ``overlap``-th last point of scan k and keeps
    its own step after the shared points ('coincide': its first ``overlap``
    points are scan k's last ones; 'staggered': those points are moved by
    half of scan k's step, so no Qz coincides). ``faults``: lists, one value
    per scan, of ScanSpec fields (absorber, slit_gain, monitor_gain,
    attenuation_error, seconds)."""
    out, prev = [], None
    for i, (lo, hi, step) in enumerate(ranges):
        if prev is None:
            q = np.round(np.arange(lo, hi + step / 2, step), 10)
        else:
            shared = prev[-overlap:]
            if grid == 'staggered':
                shared = shared + (prev[-1] - prev[-2]) / 2.0
            elif grid != 'coincide':
                raise ValueError("grid: 'coincide' or 'staggered'")
            rest = np.arange(shared[-1] + step, hi + step / 2, step)
            q = np.round(np.concatenate([shared, rest]), 10)
        kw = {k: v[i] for k, v in faults.items()}
        kw.setdefault('seconds', seconds)
        out.append(ScanSpec(q, **kw))
        prev = q
    return out


NX_RANGES = [(0.0175, 0.04, 0.00125), (0.035, 0.10, 0.0025), (0.09, 0.19, 0.005), (0.17, 0.45, 0.01)]
NX_SECONDS = [2.0, 2.0, 2.0, 5.0]
NX_SLIT_GAINS = [1.0, 1.0, 2.7, 3.2]    # Monc per second at the first point, relative to scan 6


def nx_like_plan(**faults):
    """Four scans as NX school scans 6–9: the same Qz ranges and steps
    (0.00125, 0.0025, 0.005, 0.01 Å⁻¹; the overlaps share some points and
    not others, as measured), times 2, 2, 2, 5 s, slits opened ×2.7 and
    ×3.2 for the last two (Monc following). Absorbers chosen automatically
    unless ``absorber`` is given in ``faults`` (a list per scan)."""
    plan = []
    for i, (lo, hi, step) in enumerate(NX_RANGES):
        kw = dict(seconds=NX_SECONDS[i], slit_gain=NX_SLIT_GAINS[i])
        kw.update({k: v[i] for k, v in faults.items()})
        plan.append(ScanSpec(np.round(np.arange(lo, hi + step / 2, step), 10), **kw))
    return plan


def reaching_back_plan(**faults):
    """Three scans for the hand-off's §5 case 'overlap reaches back past the
    previous scan's own points into an earlier overlap' (docs/handoff/19):
    scan 3 starts at 0.045 Å⁻¹, inside the overlap of scans 1 (to 0.05) and 2
    (from 0.04), so the weights a_m of its join are not one-hot. Steps
    0.005 Å⁻¹ throughout, all points coincide."""
    q1 = np.round(np.arange(0.01, 0.0501, 0.005), 10)
    q2 = np.round(np.arange(0.04, 0.1001, 0.005), 10)
    q3 = np.round(np.arange(0.045, 0.2001, 0.005), 10)
    plan = []
    for i, q in enumerate((q1, q2, q3)):
        plan.append(ScanSpec(q, **{k: v[i] for k, v in faults.items()}))
    return plan


def standard_plan(n_scans=4, qz_max=0.5, overlap=4, grid='coincide', **faults):
    """``n_scans`` (3–5 for the hand-off's tests) scans from 0.01 Å⁻¹ to
    ``qz_max``, the first ending at 0.04 Å⁻¹ (above the critical edge, as
    measured), the others' ends evenly spaced in log Qz, the step doubling
    from scan to scan (0.0025 Å⁻¹ first), ``overlap`` shared points. With
    'coincide' the shared points are the previous scan's own; the points
    after them are farther apart."""
    edges = np.concatenate([[0.01], np.geomspace(0.04, qz_max, n_scans)])
    ranges = [(edges[i], edges[i + 1], 0.0025 * 2 ** i) for i in range(n_scans)]
    return chain_plan(ranges, overlap=overlap, grid=grid, **faults)
