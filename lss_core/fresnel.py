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
