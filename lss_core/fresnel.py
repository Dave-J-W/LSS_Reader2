"""Qc and Qoff of R/R_F (F79, owner 2026-11-23): the critical Qz from the
subphase, and the Qz offset proposed from the data.

The owner tweaks Qoff by hand "until the fresnel-normed reflectivity looks
continuous, or has one or two outliers but is otherwise smoothly
continuous", and takes Qc as water's unless the subphase is lighter or
denser. Nothing here changes a default: the window offers the proposal
(the GUI manager's "Propose" buttons) and the user decides.

**Qc from the subphase.** Away from absorption edges (f′ small),
Qc = 4 √(π r_e ρ_e), with r_e the classical electron radius and ρ_e the
electron density (Als-Nielsen and McMorrow, *Elements of Modern X-ray
Physics*, 2nd ed., ch. 3); it does not depend on the X-ray energy. For a
solution of mass fraction w of a solute (molar mass M_s, Z_s electrons
per formula unit) at mass density ρ_m,

    ρ_e = ρ_m N_A [w Z_s / M_s + (1 − w) Z_w / M_w],

so ``electron_density`` and ``qc_from_density`` give Qc from a density
table; ``SUBPHASES`` lists a few, each density with its source (and
whether the source was opened in this session).

**Qoff.** Qz = (4π/λ) sin α, so an offset δα of the incident angle shifts
Qz by (4π/λ) cos α δα: a constant Qoff to better than 0.2 % below α = 3°.
``reflectivity.finish`` divides by R_F(Qz + Qoff), so Qoff > 0 means the
true Qz is above the recorded one. A wrong Qoff leaves a sharp feature in
R/R_F at the critical edge, where R_F falls fastest (its slope is
infinite at Qc); far above the edge it only tilts ln R/R_F slightly,
(1 + Qoff/Qz)⁴. So the edge decides Qoff, and two estimators use it:

- ``'smooth'``: Qoff minimises the roughness of y = ln(R/R_F)
  near the edge, the sum of a robust loss (Tukey's biweight, so one or two
  outliers do not count) of the second differences of y over their
  counting errors. Second differences ignore a constant and a straight
  line in y, so the scale of R, a level error of R_F (Qc far above the
  edge) and a slow sample decay do not matter.
- ``'edge'`` (default, from the study): a model fit near the edge,
  ln R = ln A + ln R_F(Qz + Qoff; Qc) + b (Qz − Qc) + c (Qz − Qc)², by
  robust least squares (soft L1): the plateau, the drop and a smooth
  sample factor.

**Qc and Qoff together are nearly degenerate.** Without absorption R_F
depends on Qz/Qc alone, and the edge sits at Qz = Qc − Qoff. Changing Qc by
Δ and Qoff by the same Δ keeps the edge in place; what is left is a level
change of R/R_F far above the edge, (1 + Δ/Qc)⁴ (the 4 % per 1 % of the
owner's note), which is indistinguishable from the sample's own level, and
small changes in the shape just above the edge. So ``fit_qc=True``
reports Qc and Qoff with their correlation (near +1); Qc is best taken
from the subphase and Qoff fitted at it.

The proposal is a ``Proposal``: ``qoff``, ``sigma`` (from a parametric
bootstrap over the counting errors), ``note`` (one line for the window),
the points used and the points down-weighted as outliers.
"""
import math
from dataclasses import dataclass, field

import numpy as np

R_E = 2.8179403262e-5          # Å, classical electron radius (CODATA 2018)
N_A = 6.02214076e23            # 1/mol (exact since 2019)
QC_WATER = 0.0217              # the reader's preset (lss_core.reflectivity.finish callers)
QOFF_BOUNDS = (-0.004, 0.004)  # Å⁻¹ searched: ±0.03° at α 0.12°, 10 keV, is ±0.0006; generous
TUKEY_C = 4.685                # biweight constant (95 % efficiency at the normal)

# solute: (molar mass g/mol, electrons per formula unit); IUPAC standard atomic weights (from memory)
SOLUTES = {
    'H2O': (18.015, 10), 'D2O': (20.028, 10), 'NaCl': (58.443, 28), 'KCl': (74.551, 36),
    'CaCl2': (110.98, 54),
}


def electron_density(mass_density, mass_fraction=0.0, solute=None, solvent='H2O'):
    """Electron density (e/Å³) of a solvent with a solute at ``mass_fraction``
    (0 for the pure solvent), at ``mass_density`` (g/cm³)."""
    ms, zs = SOLUTES[solvent]
    per_gram = (1.0 - mass_fraction) * zs / ms
    if solute is not None and mass_fraction:
        m, z = SOLUTES[solute]
        per_gram += mass_fraction * z / m
    return float(mass_density) * N_A * per_gram * 1e-24      # 1 cm³ = 1e24 Å³


def qc_from_density(rho_e):
    """Qc (Å⁻¹) of a medium of electron density ``rho_e`` (e/Å³) against
    vacuum: 4 √(π r_e ρ_e)."""
    return 4.0 * math.sqrt(math.pi * R_E * float(rho_e))


def density_from_qc(qc):
    """ρ_e (e/Å³) for a critical Qz ``qc``."""
    return float(qc) ** 2 / (16.0 * math.pi * R_E)


@dataclass(frozen=True)
class Subphase:
    name: str
    mass_density: float          # g/cm³
    temperature_c: float
    mass_fraction: float = 0.0
    solute: str = None
    solvent: str = 'H2O'
    source: str = ''
    opened: bool = False         # the source was read in this session (else: from memory)

    @property
    def rho_e(self):
        return electron_density(self.mass_density, self.mass_fraction, self.solute, self.solvent)

    @property
    def qc(self):
        return qc_from_density(self.rho_e)

    @property
    def molarity(self):
        """Approximate concentration (mol/L) of the solute."""
        if not self.solute:
            return 0.0
        return self.mass_density * 1000.0 * self.mass_fraction / SOLUTES[self.solute][0]


_CRC = ('CRC Handbook of Chemistry and Physics, "Concentrative properties of aqueous solutions" (20 °C); from '
        'memory: the source could not be opened from this session (2026-11-24: the network does not reach it)')
SUBPHASES = (
    Subphase('water', 0.99705, 25.0, source='CRC Handbook, density of water at 25 °C (from memory; not opened)'),
    Subphase('D2O', 1.1044, 25.0, solvent='D2O', source='CRC Handbook, density of heavy water at 25 °C (from memory; not opened)'),
    Subphase('NaCl 1 % (0.17 M)', 1.0053, 20.0, 0.01, 'NaCl', source=_CRC),
    Subphase('NaCl 3 % (0.52 M)', 1.0196, 20.0, 0.03, 'NaCl', source=_CRC),
    Subphase('NaCl 6 % (1.07 M)', 1.0413, 20.0, 0.06, 'NaCl', source=_CRC),
    Subphase('NaCl 10 % (1.81 M)', 1.0707, 20.0, 0.10, 'NaCl', source=_CRC),
    Subphase('KCl 7 % (0.98 M)', 1.0431, 20.0, 0.07, 'KCl', source=_CRC),
    Subphase('CaCl2 5 % (0.47 M)', 1.0404, 20.0, 0.05, 'CaCl2', source=_CRC),
    Subphase('CaCl2 10 % (0.98 M)', 1.0835, 20.0, 0.10, 'CaCl2', source=_CRC),
)


def subphase(name):
    for s in SUBPHASES:
        if s.name == name:
            return s
    raise KeyError('no subphase %r: %s' % (name, ', '.join(s.name for s in SUBPHASES)))


# ---- Fresnel ----------------------------------------------------------------

def fresnel(qz, qc):
    """Fresnel reflectivity without absorption, 1 below Qc (the reader's
    ``stitching.fresnel``, vectorised; works on arrays of any shape)."""
    q = np.asarray(qz, dtype=float)
    s = np.sqrt(np.clip(q * q - qc * qc, 0.0, None))
    with np.errstate(invalid='ignore', divide='ignore'):
        r = ((q - s) / (q + s)) ** 2
    return np.where(q <= qc, 1.0, r)


def rrf(qz, r, qc, qoff=0.0):
    """R / R_F(Qz + Qoff)."""
    return np.asarray(r, float) / fresnel(np.asarray(qz, float) + qoff, qc)


# ---- the proposal -------------------------------------------------------------

@dataclass
class Proposal:
    """A proposed Qoff (and Qc when fitted). ``sigma``: its standard error
    (parametric bootstrap); ``qc_sigma``, ``correlation``: when Qc was
    fitted too; ``points``: the Qz used; ``outliers``: the Qz down-weighted
    (|residual| beyond the loss's range); ``note``: one line for the
    window; ``grid``, ``objective``: the scan of the loss over Qoff."""
    qoff: float
    sigma: float
    qc: float
    method: str
    qc_sigma: float = None
    correlation: float = None
    points: np.ndarray = None
    outliers: list = field(default_factory=list)
    note: str = ''
    grid: np.ndarray = None
    objective: np.ndarray = None
    ok: bool = True


def _prepare(qz, r, sigma, q_max, q_min):
    """Sorted, positive, duplicates merged (inverse-variance) points: q, ln r, σ(ln r)."""
    q = np.asarray(qz, float).ravel()
    y = np.asarray(r, float).ravel()
    s = np.full_like(y, np.nan) if sigma is None else np.asarray(sigma, float).ravel()
    keep = np.isfinite(q) & np.isfinite(y) & (y > 0)
    if q_max is not None:
        keep &= q <= q_max
    if q_min is not None:
        keep &= q >= q_min
    q, y, s = q[keep], y[keep], s[keep]
    o = np.argsort(q, kind='stable')
    q, y, s = q[o], y[o], s[o]
    rel = s / y
    if not np.all(np.isfinite(rel)) or np.any(rel <= 0):
        med = np.nanmedian(rel[np.isfinite(rel) & (rel > 0)]) if np.any(np.isfinite(rel) & (rel > 0)) else 0.02
        rel = np.where(np.isfinite(rel) & (rel > 0), rel, med)
    ly = np.log(y)
    out_q, out_y, out_s = [], [], []
    i = 0
    while i < len(q):                                  # merge points at the same Qz (scan overlaps)
        j = i + 1
        while j < len(q) and q[j] - q[i] < 1e-7:
            j += 1
        w = 1.0 / rel[i:j] ** 2
        out_q.append(q[i])
        out_y.append(float(np.sum(w * ly[i:j]) / np.sum(w)))
        out_s.append(float(1.0 / math.sqrt(np.sum(w))))
        i = j
    return np.array(out_q), np.array(out_y), np.array(out_s)


def _second_difference(q):
    """Coefficients (a, b, c) of the second derivative on a non-uniform grid at
    the interior points: y'' ≈ a y[i−1] + b y[i] + c y[i+1]."""
    h1 = q[1:-1] - q[:-2]
    h2 = q[2:] - q[1:-1]
    a = 2.0 / (h1 * (h1 + h2))
    b = -2.0 / (h1 * h2)
    c = 2.0 / (h2 * (h1 + h2))
    return a, b, c


def _tukey(z, c=TUKEY_C):
    u = np.clip(np.abs(z) / c, 0.0, 1.0)
    return (c * c / 6.0) * (1.0 - (1.0 - u * u) ** 3)


HUBER_K = 1.345                # Huber's constant (95 % efficiency at the normal)
LOCAL = 10                     # Tukey's search: ± this many grid steps around the Huber estimate


def _huber(z, k=HUBER_K):
    a = np.abs(z)
    return np.where(a <= k, 0.5 * z * z, k * a - 0.5 * k * k)


LOSSES = {'tukey': _tukey, 'huber': _huber, 'squared': lambda z: 0.5 * z * z}


def _smooth_losses(q, ly, s, qc, grid, scale, loss='tukey'):
    """Loss of every Qoff in ``grid`` (vectorised): Σ ρ(d2 / (σ_d2 · scale))."""
    a, b, c = _second_difference(q)
    sd = np.sqrt(a * a * s[:-2] ** 2 + b * b * s[1:-1] ** 2 + c * c * s[2:] ** 2)
    lf = np.log(fresnel(q[None, :] + grid[:, None], qc))
    y = ly[None, :] - lf
    d2 = a * y[:, :-2] + b * y[:, 1:-1] + c * y[:, 2:]
    z = d2 / (sd * scale)
    return LOSSES[loss](z).sum(axis=1), z


def _refine(f, grid, vals):
    """The minimum of f near the best grid point (golden section on its two neighbours)."""
    k = int(np.argmin(vals))
    lo = grid[max(k - 1, 0)]
    hi = grid[min(k + 1, len(grid) - 1)]
    gr = (math.sqrt(5) - 1) / 2
    x1, x2 = hi - gr * (hi - lo), lo + gr * (hi - lo)
    f1, f2 = f(x1), f(x2)
    for _ in range(40):
        if f1 < f2:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - gr * (hi - lo)
            f1 = f(x1)
        else:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + gr * (hi - lo)
            f2 = f(x2)
    return (lo + hi) / 2


def _basin(q, ly, s, qc, grid, scale, loss):
    """The grid point to search around: the minimum of a convex loss (Huber
    for 'tukey', so that the edge points cannot be explained away as
    outliers, which gives a false minimum; the loss itself otherwise)."""
    vals, z = _smooth_losses(q, ly, s, qc, grid, scale, 'huber' if loss == 'tukey' else loss)
    return int(np.argmin(vals)), vals, z


def _smooth_estimate(q, ly, s, qc, bounds, step, loss='tukey'):
    grid = np.arange(bounds[0], bounds[1] + step / 2, step)
    k, vals, z = _basin(q, ly, s, qc, grid, 1.0, loss)
    scale = max(1.0, 1.4826 * float(np.median(np.abs(z[k]))))   # robust scale of the residuals (≥ the counting errors)
    if scale > 1.0:
        k, vals, z = _basin(q, ly, s, qc, grid, scale, loss)
    f = lambda x: float(_smooth_losses(q, ly, s, qc, np.array([x]), scale, loss)[0][0])
    if loss == 'tukey':                    # redescend only near the basin: genuine outliers lose their say
        local = grid[max(k - LOCAL, 0):k + LOCAL + 1]
        best = _refine(f, local, _smooth_losses(q, ly, s, qc, local, scale, loss)[0])
        vals = _smooth_losses(q, ly, s, qc, grid, scale, loss)[0]    # the loss scanned, for the figure
    else:
        best = _refine(f, grid, vals)
    zb = _smooth_losses(q, ly, s, qc, np.array([best]), scale, loss)[1][0]
    return best, grid, vals, scale, zb


def _edge_model(p, q, qc_fixed, fit_qc):
    if fit_qc:
        lna, b, c, qoff, qc = p
    else:
        lna, b, c, qoff = p
        qc = qc_fixed
    return lna + np.log(fresnel(q + qoff, qc)) + b * (q - qc) + c * (q - qc) ** 2


def _edge_estimate(q, ly, s, qc, fit_qc, start=0.0):
    from scipy.optimize import least_squares
    p0 = [float(np.max(ly[q < qc])) if np.any(q < qc) else 0.0, 0.0, 0.0, start] + ([qc] if fit_qc else [])
    lo = [-np.inf, -np.inf, -np.inf, QOFF_BOUNDS[0]] + ([0.8 * qc] if fit_qc else [])
    hi = [np.inf, np.inf, np.inf, QOFF_BOUNDS[1]] + ([1.2 * qc] if fit_qc else [])
    res = least_squares(lambda p: (ly - _edge_model(p, q, qc, fit_qc)) / s, p0, bounds=(lo, hi),
                        loss='soft_l1', f_scale=2.0, diff_step=1e-6, x_scale=[1, 10, 100, 1e-3] + ([1e-3] if fit_qc else []))
    return res


def propose_qoff(qz, r, sigma=None, qc=QC_WATER, method='edge', q_max=None, q_min=None, fit_qc=False,
                 bounds=QOFF_BOUNDS, step=2e-5, bootstrap=200, seed=0, loss='tukey'):
    """Propose Qoff (Å⁻¹) for R/R_F from reflectivity ``r`` (any scale) with
    errors ``sigma`` at ``qz``, for a subphase of critical Qz ``qc``.

    ``method``: 'edge' (the default: a model fit of the plateau and the
    drop; the study, docs/studies/qoff/summary.md, found it less biased,
    steadier and as robust) or 'smooth' (the roughness of ln R/R_F near the
    edge, robust: the owner's by-eye criterion made numerical). Points above
    ``q_max`` (default 4 Qc for 'smooth', 2.5 Qc for 'edge') or below
    ``q_min`` are not used. ``fit_qc``: fit Qc too ('edge' only; reports the
    correlation). ``bootstrap``: replicates for σ (0: none); they redraw
    every point with its counting error times the robust scale of the
    residuals (≥ 1), so a misfit widens σ. ``loss``: 'tukey' (robust, the
    default: the basin by Huber's loss, then Tukey's biweight within ±10
    grid steps of it, so that the edge points cannot be explained away as
    outliers), 'huber' or 'squared' (for comparison; 'smooth' only)."""
    if method not in ('smooth', 'edge'):
        raise ValueError("method: 'smooth' or 'edge', not %r" % (method,))
    if loss not in LOSSES:
        raise ValueError('loss: %s, not %r' % (', '.join(LOSSES), loss))
    if fit_qc and method != 'edge':
        raise ValueError("fit_qc needs method='edge' (the roughness ignores Qc's level)")
    q_max = (4.0 if method == 'smooth' else 2.5) * qc if q_max is None else q_max
    q, ly, s = _prepare(qz, r, sigma, q_max, q_min)
    above = int(np.sum(q > qc))
    if len(q) < 6 or above < 3 or not np.any(q < 1.5 * qc):
        return Proposal(0.0, math.nan, qc, method, points=q, ok=False,
                        note='Qoff not proposed: %d points up to %.3g, %d above Qc; the edge (Qz near %.4g) must be '
                             'measured' % (len(q), q_max, above, qc))
    rng = np.random.default_rng(seed)
    qc_sig = corr = None
    qc_out = qc
    if method == 'smooth':
        best, grid, vals, scale, z = _smooth_estimate(q, ly, s, qc, bounds, step, loss)
        outl = [float(q[i + 1]) for i in np.flatnonzero(np.abs(z) > TUKEY_C)] if loss == 'tukey' else []
        boots = []
        for _ in range(int(bootstrap)):            # the same two steps on redrawn data, on a fine local grid
            yb = ly + scale * s * rng.standard_normal(len(ly))
            k = _basin(q, yb, s, qc, grid, scale, loss)[0]
            fine = np.linspace(grid[max(k - LOCAL, 0)], grid[min(k + LOCAL, len(grid) - 1)], 201)
            v = _smooth_losses(q, yb, s, qc, fine, scale, loss)[0]
            boots.append(fine[int(np.argmin(v))])
        sig = float(np.std(boots, ddof=1)) if len(boots) > 2 else math.nan
        if np.isfinite(sig):
            sig = max(sig, step / 10 / math.sqrt(12))          # the fine grid's resolution
        what = 'the roughness of ln R/R_F' + (' (least squares)' if loss == 'squared' else '')
    else:
        res = _edge_estimate(q, ly, s, qc, fit_qc)
        best = float(res.x[3])
        resid = res.fun
        scale = max(1.0, 1.4826 * float(np.median(np.abs(resid))))
        outl = [float(q[i]) for i in np.flatnonzero(np.abs(resid) > 3 * scale)]
        boots, qcs = [], []
        for _ in range(int(bootstrap)):
            yb = ly + scale * s * rng.standard_normal(len(ly))
            rb = _edge_estimate(q, yb, s, qc, fit_qc, start=best)
            boots.append(rb.x[3])
            if fit_qc:
                qcs.append(rb.x[4])
        sig = float(np.std(boots, ddof=1)) if len(boots) > 2 else math.nan
        if fit_qc:
            qc_out = float(res.x[4])
            if len(qcs) > 2:
                qc_sig = float(np.std(qcs, ddof=1))
                corr = float(np.corrcoef(boots, qcs)[0, 1])
        grid = vals = None
        what = 'a fit of the edge' + (' with Qc free' if fit_qc else '')
    note = 'Qoff %+.5f ± %.5f Å⁻¹ from %s, %d points up to %.3g Å⁻¹ at Qc %.5f' % (
        best, sig, what, len(q), float(q[-1]), qc_out)
    if fit_qc and qc_sig is not None:
        note += ' ± %.5f (correlation with Qoff %+.2f)' % (qc_sig, corr)
    if outl:
        note += '; %d point(s) down-weighted (Qz %s)' % (len(outl), ', '.join('%.4f' % v for v in outl[:4]))
    return Proposal(float(best), sig, qc_out, method, qc_sig, corr, q, outl, note, grid, vals)


# ---- Qoff and the Qz resolution fitted together (hand-off 09, owner 2026-11-26) ----------
#
# The owner (2026-11-26): "Qoffset also has to be fit, and this could be a useful ability to have
# in reader". ``propose_qoff`` fits a sharp R_F, so it reads the beam's resolution as a negative
# Qoff (about −0.15 ΔQ FWHM, C50 §3), and its ± holds only the counting noise (×9 too small on NX,
# where its χ²/dof is 75). ``fit_edge_resolution`` fits R_F with the subphase's absorption,
# smeared by a Gaussian of σ_Q, with Qoff and σ_Q free and Qc and β held at the subphase's
# (C50 §4: Qc and Qoff lie on one line). Its model is the one DATA_NEEDS row 13 fitted to 378 real
# edges (docs/studies/qz_resolution/summary.md):
#
#     R(q) = N · [R_F(q + Qoff; Qc, β) ⊗ Gauss(σ_Q)](q) · (1 + a u + b u²),   u = (q − Qc)/Qc,
#
# over 0.6 Qc ≤ q ≤ 0.030 Å⁻¹ by a soft-L1 loss. Row 13 fitted the measured edge q_e = Qc − Qoff
# with u about q_e; with Qc fixed that is the same model (u about Qc is a linear change of a, b).
# Nothing applies the result: no default changes (rule 12, paused; docs/RELEASE_PLAN.md).

HC_KEV_ANGSTROM = 12.39842     # keV·Å, as lss_core.absorbers
EDGE_Q_MAX = 0.030             # Å⁻¹: row 13's upper limit (1.38 Qc of water)
EDGE_Q_MIN = 0.6               # × Qc: row 13's lower limit
SIGMA_Q_BOUNDS = (0.0, 2.0e-3)  # Å⁻¹; the beamline's run medians are 2.8–5.4 × 10⁻⁴ (row 13)
SIGMA_Q_STARTS = (1.5e-4, 3.8e-4, 8e-4)   # the fit starts from each; 3.8e-4 is row 13's median

# Mass attenuation coefficients μ/ρ (cm²/g, total with coherent scattering, as the NIST tables
# and row 13's β), from xraylib 4.3.0 ``CS_Total_CP`` (computed 2026-11-27; D2O from the atoms'
# cross sections, with D's taken as H's). Between the energies: log-log interpolation. No
# absorption edge of these elements lies between 8 and 30 keV.
MU_RHO_KEV = (8.0, 9.0, 10.0, 11.0, 12.0, 13.5, 15.0, 17.5, 20.0, 25.0, 30.0)
MU_RHO = {
    'H2O': (10.37, 7.289, 5.329, 4.025, 3.126, 2.236, 1.672, 1.117, 0.8097, 0.5082, 0.3756),
    'D2O': (9.331, 6.559, 4.795, 3.622, 2.813, 2.012, 1.505, 1.005, 0.7286, 0.4573, 0.338),
    'NaCl': (77.08, 55.2, 40.85, 31.07, 24.18, 17.2, 12.67, 8.1, 5.505, 2.91, 1.755),
    'KCl': (128.2, 92.34, 68.7, 52.47, 40.97, 29.25, 21.61, 13.85, 9.414, 4.946, 2.943),
    'CaCl2': (131.0, 94.47, 70.31, 53.72, 41.96, 29.98, 22.16, 14.21, 9.661, 5.079, 3.023),
}


def wavelength(energy_kev):
    return HC_KEV_ANGSTROM / float(energy_kev)


def mu_rho(substance, energy_kev):
    """μ/ρ (cm²/g) of ``substance`` (a key of ``MU_RHO``) at ``energy_kev``
    (8–30 keV; log-log interpolation in the xraylib table)."""
    e = float(energy_kev)
    if not MU_RHO_KEV[0] <= e <= MU_RHO_KEV[-1]:
        raise ValueError('μ/ρ is tabulated from %g to %g keV, not %g' % (MU_RHO_KEV[0], MU_RHO_KEV[-1], e))
    return float(np.exp(np.interp(math.log(e), np.log(MU_RHO_KEV), np.log(MU_RHO[substance]))))


def beta_of(mass_density, energy_kev, mass_fraction=0.0, solute=None, solvent='H2O'):
    """The absorption index β = μ λ / 4π of a solution (``electron_density``'s
    arguments) at ``energy_kev``: μ/ρ by mass fraction, μ = (μ/ρ) ρ_m."""
    m = (1.0 - mass_fraction) * mu_rho(solvent, energy_kev)
    if solute is not None and mass_fraction:
        m += mass_fraction * mu_rho(solute, energy_kev)
    mu = m * float(mass_density)                                 # 1/cm
    return mu * wavelength(energy_kev) * 1e-8 / (4.0 * math.pi)   # λ in cm


def subphase_beta(sub, energy_kev):
    """β of a ``Subphase`` at ``energy_kev`` (water at 10 keV: 5.24e-9)."""
    return beta_of(sub.mass_density, energy_kev, sub.mass_fraction, sub.solute, sub.solvent)


def fresnel_absorbing(qz, qc, beta=0.0, energy_kev=10.0, roughness=0.0):
    """|r|² of a bare interface with absorption: r = (Q − Q′)/(Q + Q′),
    Q′² = Q² − Qc² + i 32π²β/λ² (Als-Nielsen and McMorrow, ch. 3). With
    β = 0 it is ``fresnel``. ``roughness`` (Å): r × exp(−Q Q′ σ²/2), the
    Névot–Croce factor (L. Névot and P. Croce, Rev. Phys. Appl. 15, 761
    (1980)); 0 by default, as the hand-off's model."""
    q = np.asarray(qz, dtype=float)
    lam = wavelength(energy_kev)
    qp = np.sqrt(q * q - qc * qc + 1j * (32.0 * math.pi ** 2 * float(beta) / lam ** 2))
    with np.errstate(invalid='ignore', divide='ignore'):
        amp = (q - qp) / (q + qp)
        if roughness:
            amp = amp * np.exp(-0.5 * q * qp * float(roughness) ** 2)
        r = np.abs(amp) ** 2
    return np.where(q > 0, r, 1.0)


_SMEAR_X = np.linspace(-6.0, 6.0, 241)                  # ε / σ_Q: trapezoid over ±6σ, 0.05σ apart
_SMEAR_W = np.exp(-0.5 * _SMEAR_X ** 2)
_SMEAR_W = _SMEAR_W / _SMEAR_W.sum()


def fresnel_smeared(qz, qc, sigma_q, beta=0.0, energy_kev=10.0, roughness=0.0):
    """⟨R_F(Qz + ε)⟩ over a Gaussian ε of standard deviation ``sigma_q``
    (Å⁻¹): the trapezoid rule on 241 points over ±6σ (a different rule
    from the synthetic generator's Gauss–Hermite, so that known truth is
    not the model checking itself). σ ≤ 1e-7: the sharp curve."""
    q = np.asarray(qz, dtype=float)
    if sigma_q <= 1e-7:
        return fresnel_absorbing(q, qc, beta, energy_kev, roughness)
    e = np.abs(q[..., None] + float(sigma_q) * _SMEAR_X)
    return np.sum(fresnel_absorbing(e, qc, beta, energy_kev, roughness) * _SMEAR_W, axis=-1)


def fwhm_of(sigma):
    return 2.0 * math.sqrt(2.0 * math.log(2.0)) * sigma


@dataclass
class EdgeFit:
    """Qoff and σ_Q fitted together at the edge (``fit_edge_resolution``).

    ``qoff``, ``sigma_q`` (Å⁻¹) with ``qoff_err``, ``sigma_q_err``: the
    bootstrap's standard deviation times √(χ²/dof) when that is above 1
    (``*_err_counting``: before the scaling); ``corr``: their correlation
    over the bootstrap; ``chi2_dof`` at the fit (plain squares of the
    normalised residuals, dof = points − 5); ``flags``: 'sigma_q at its
    bound', 'few points below the edge', 'few points above the edge',
    'ill-conditioned', 'bootstrap failures'. ``params``: N, Qoff, σ_Q, a,
    b; ``residuals``: (ln R − model)/σ(ln R) at ``points``."""
    qoff: float
    qoff_err: float
    sigma_q: float
    sigma_q_err: float
    corr: float
    chi2_dof: float
    qc: float
    beta: float
    energy_kev: float
    n_points: int
    n_below: int
    n_above: int
    qoff_err_counting: float = math.nan
    sigma_q_err_counting: float = math.nan
    params: tuple = ()
    points: np.ndarray = None
    residuals: np.ndarray = None
    flags: list = field(default_factory=list)
    note: str = ''
    ok: bool = True
    q_range: tuple = ()
    roughness: float = 0.0

    @property
    def fwhm(self):
        return fwhm_of(self.sigma_q)

    @property
    def fwhm_err(self):
        return fwhm_of(self.sigma_q_err)

    @property
    def k(self):
        return 4.0 * math.pi / wavelength(self.energy_kev)

    @property
    def sigma_alpha_urad(self):
        """σ_Q as an incidence-angle spread (µrad): σ_Q / (4π/λ)."""
        return self.sigma_q / self.k * 1e6

    @property
    def qoff_deg(self):
        """Qoff as an incidence-angle offset (degrees; cos α = 1)."""
        return math.degrees(self.qoff / self.k)

    def model(self, qz):
        """R of the fit at ``qz``."""
        return _edge_res_model(self.params, np.asarray(qz, float), self.qc, self.beta, self.energy_kev, log=False,
                               roughness=self.roughness)


def _edge_res_model(p, q, qc, beta, energy_kev, log=True, roughness=0.0):
    lnn, qoff, sig, a, b = p
    u = (q - qc) / qc
    smooth = np.clip(1.0 + a * u + b * u * u, 1e-12, None)
    rf = np.clip(fresnel_smeared(q + qoff, qc, sig, beta, energy_kev, roughness), 1e-300, None)
    m = lnn + np.log(rf) + np.log(smooth)
    return m if log else np.exp(m)


def _edge_res_fit(q, ly, s, qc, beta, energy_kev, starts, f_scale, roughness=0.0):
    from scipy.optimize import least_squares
    lo = [-np.inf, QOFF_BOUNDS[0], SIGMA_Q_BOUNDS[0], -np.inf, -np.inf]
    hi = [np.inf, QOFF_BOUNDS[1], SIGMA_Q_BOUNDS[1], np.inf, np.inf]
    best = None
    for p0 in starts:
        p0 = list(p0)
        p0[1] = min(max(p0[1], lo[1] + 1e-7), hi[1] - 1e-7)
        p0[2] = min(max(p0[2], 0.0), hi[2] - 1e-7)
        res = least_squares(lambda p: (ly - _edge_res_model(p, q, qc, beta, energy_kev, True, roughness)) / s, p0,
                            bounds=(lo, hi), loss='soft_l1', f_scale=f_scale, diff_step=1e-6,
                            x_scale=[1.0, 1e-4, 1e-4, 1.0, 1.0])
        if best is None or res.cost < best.cost:
            best = res
    return best


def fit_edge_resolution(qz, r, sigma=None, qc=QC_WATER, beta=None, energy_kev=10.0, q_min=None, q_max=EDGE_Q_MAX,
                        bootstrap=200, seed=0, f_scale=2.0, roughness=0.0):
    """Qoff and the Qz resolution σ_Q fitted together at the critical edge.

    ``qz``, ``r`` (any scale), ``sigma``: one scan, or more, through the
    edge; ``qc``: the subphase's critical Qz and ``beta`` its absorption
    at ``energy_kev`` (None: water's, ``subphase_beta``), both held fixed.
    Fitted over ``q_min`` (default 0.6 Qc) to ``q_max`` (0.030 Å⁻¹), the
    range of DATA_NEEDS row 13. ``bootstrap``: parametric replicates for
    the errors (every point redrawn with its error; 0: none, the errors are
    then NaN); the errors are scaled by √(χ²/dof) when that is above 1.
    ``f_scale``: the soft-L1 loss's scale, in units of a point's error.
    ``roughness`` (Å): a fixed Névot–Croce roughness of the interface in R_F
    (0, the hand-off's model: then the smooth factor takes it up, except a
    small kink at Qc, which biases σ_Q by −8 to +18 % at σ_Q 1e-4 and less
    than 0.5 % at 3.8e-4 for water's 3 Å, measured on noiseless synthetic
    edges; tests/test_qoff_resolution.py). Returns an ``EdgeFit`` (``ok`` False with a note when the edge is not
    measured). Nothing here applies the value."""
    if beta is None:
        beta = subphase_beta(subphase('water'), energy_kev)
    q_min = EDGE_Q_MIN * qc if q_min is None else q_min
    q, ly, s = _prepare(qz, r, sigma, q_max, q_min)
    rng_txt = (float(q[0]), float(q[-1])) if len(q) else ()
    n_above_qc = int(np.sum(q > qc))
    if len(q) < 8 or n_above_qc < 3 or not np.any(q < qc):
        return EdgeFit(0.0, math.nan, math.nan, math.nan, math.nan, math.nan, qc, beta, energy_kev, len(q),
                       int(np.sum(q < qc)), n_above_qc, ok=False, points=q, q_range=rng_txt,
                       note='Qoff and resolution not fitted: %d points from %.3g to %.3g Å⁻¹, %d above Qc %.4g; '
                            'the edge must be measured on both sides' % (len(q), q_min, q_max, n_above_qc, qc))
    sharp = propose_qoff(q, np.exp(ly), np.exp(ly) * s, qc=qc, method='edge', q_max=q_max, q_min=q_min,
                         bootstrap=0)
    q0 = sharp.qoff if sharp.ok and np.isfinite(sharp.qoff) else 0.0
    lnn0 = float(np.median(ly[q < qc - abs(q0) - 1e-4])) if np.any(q < qc - abs(q0) - 1e-4) else float(np.max(ly))
    # the sharp fit reads the smearing as about −0.15 FWHM of Qoff (C50 §3): start each σ from that
    starts = [(lnn0, q0 + 0.15 * fwhm_of(sg), sg, 0.0, 0.0) for sg in SIGMA_Q_STARTS]
    res = _edge_res_fit(q, ly, s, qc, beta, energy_kev, starts, f_scale, roughness)
    p = res.x
    resid = res.fun
    dof = len(q) - len(p)
    chi2 = float(np.sum(resid ** 2) / dof) if dof > 0 else math.nan
    edge = qc - p[1]                                   # the edge as measured
    n_below = int(np.sum(q < edge))
    n_above = int(np.sum(q > edge))
    flags = []
    if p[2] <= SIGMA_Q_BOUNDS[0] + 1e-6 or p[2] >= SIGMA_Q_BOUNDS[1] * 0.999:
        flags.append('sigma_q at its bound')
    if n_below < 3:
        flags.append('few points below the edge')
    if n_above < 4:
        flags.append('few points above the edge')
    try:
        jtj = res.jac.T @ res.jac
        if not np.all(np.isfinite(jtj)) or np.linalg.cond(jtj) > 1e14:
            flags.append('ill-conditioned')
    except np.linalg.LinAlgError:
        flags.append('ill-conditioned')
    qoff_e = sig_e = corr = math.nan
    failed = 0
    if bootstrap:
        rng = np.random.default_rng(seed)
        bq, bs = [], []
        for _ in range(int(bootstrap)):
            yb = ly + s * rng.standard_normal(len(ly))
            try:
                rb = _edge_res_fit(q, yb, s, qc, beta, energy_kev, [tuple(p)], f_scale, roughness)
                bq.append(rb.x[1])
                bs.append(rb.x[2])
            except (ValueError, np.linalg.LinAlgError):
                failed += 1
        if len(bq) > 2:
            qoff_e, sig_e = float(np.std(bq, ddof=1)), float(np.std(bs, ddof=1))
            corr = float(np.corrcoef(bq, bs)[0, 1]) if sig_e > 0 and qoff_e > 0 else math.nan
        if failed:
            flags.append('bootstrap failures')
    k = max(1.0, math.sqrt(chi2)) if np.isfinite(chi2) else math.nan
    fit = EdgeFit(float(p[1]), qoff_e * k, float(p[2]), sig_e * k, corr, chi2, qc, beta, energy_kev, len(q),
                  n_below, n_above, qoff_e, sig_e, tuple(float(x) for x in p), q, resid, flags, ok=True,
                  q_range=rng_txt, roughness=float(roughness))
    fit.note = ('Qoff %+.5f ± %.5f Å⁻¹ with the resolution σ_Q %.2e ± %.1e (FWHM %.2e, %.0f µrad), '
                'χ²/dof %.2f, %d points %.4g–%.4g at Qc %.5f, β %.2e%s' % (
                    fit.qoff, fit.qoff_err, fit.sigma_q, fit.sigma_q_err, fit.fwhm, fit.sigma_alpha_urad, chi2,
                    len(q), q[0], q[-1], qc, beta, ('; ' + ', '.join(flags)) if flags else ''))
    return fit
