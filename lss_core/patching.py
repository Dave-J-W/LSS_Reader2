"""Reflectivity patching by a joint fit of both scans at each join, with the
known absorber ratio as an optional prior, and the full covariance of the
stitched curve (owner, 2026-11-22; design and measurements:
``docs/reports/ref_patch_joint_fit.md``). An option beside the legacy
patch (``lss_core.stitching``), which stays as it is and keeps the legacy
export byte for byte.

**One join.** Scan a (on the anchor's scale) and scan b (new). Window: the
overlap [min q_b, max q_a] plus ``n_ext`` points of a below it and of b
above it. One smooth curve for both scans, so value, slope and curvature
agree across the whole window (the owner's curvature constraint, in its
strongest form):

    μ_a(q) = exp(B(q) + Σ_k c_k u^k),    μ_b(q) = μ_a(q)·exp(−δ),    δ = ln f,

u the window's q scaled to [−1, 1], B = ln R_F(q + q_off) (``space='rrf'``)
or 0 (``'raw'``), f the factor that multiplies scan b (as the legacy
patch). Likelihood ``'poisson'`` (default): Gaussian in y with the counting
variance scaled to the model, σ_i²·μ_i/y_i, by Gauss–Newton from the
log-space solution (``'log'``: weighted least squares in ln y, closed form,
biased at low counts). The reported error is the counting error ×
max(1, √(χ²/dof)) (inflate-only). Defaults: order 4, R/R_F, 4 points either
side (measured: unbiased within 0.1 %, factor scatter 20–30 % below the
spline-ratio estimator; order 2 with points either side is biased up to
−5 %); since 2026-11-22 the default is 2 points either side (``N_EXT``,
the gauntlet). **Guard** (``guard_ladder``; revised 2026-11-22 after the gauntlet,
``tests/tools/ref_patch_gauntlet.py``): the fits are tried from the
largest window down (4, 2, 1 points either side, then the overlap alone),
the order rising at each window from 4 (from 2 on the overlap alone) as
far as the points allow, and the first whose χ² has p ≥ ``guard_p`` (0.7)
is kept; if none, the most adequate, its error inflated. Before, the
ladder was (4, 4), (4, 2), (2, 0) with p ≥ 0.01: a thick film's fringes
or four coinciding points at a fringe minimum fit no quadratic, and the
factor was biased by up to 4 % or its error inflated ×17; and p ≥ 0.01
let model bias of 0.2–0.4 σ through. ``rung_fit`` fits one rung alone and
returns its curve (for studies that redo or average the guard's choice,
``tests/tools/ref_guard_study.py``); it changes no number.

**Prior.** δ_0 = ln(T(n_a)/T(n_b)) from the calibrated foils; across joins
the foil errors are shared, so the prior on the steps is correlated
(``known_steps``). It is used at a join only when the monitor ratio
Monc/Monp is within 3 % of 1 across the join and |z| ≤ 3 (``prior_mask``;
P29: a monitor that misses a slit change makes data and prior disagree
for real); elsewhere it is marginalised.

**The correlated error** cannot be avoided (each scan's level is known only
through finite overlaps); it is reported: φ and Σ (``PatchResult``), the
stitched points with their weights W and Σ (``Stitched``), from which the
per-point total error and the N × N covariance follow
(``lss_core.uncertainty``).

    from lss_core import patching
    scans = patching.scans_from_reflectivity(exp.reflectivity([6, 7, 8, 9]))
    res = patching.chain(scans)                     # joint fit at each join
    res.joins[0].factor, res.joins[0].err, res.phi, res.Sigma
    st = res.stitch(scans)
    st.q, st.y, st.sigma_meas, st.sigma_total(), st.covariance('log')
"""
import math
from dataclasses import dataclass, field

import numpy as np

from . import uncertainty as unc

QC = 0.0217


@dataclass
class Scan:
    """One scan's reduced points: q, y (per monitor count), sigma (counting
    only); ``absorber`` setting n; ``label``."""
    q: np.ndarray
    y: np.ndarray
    sigma: np.ndarray
    label: str = ''
    absorber: int = None

    def __post_init__(self):
        o = np.argsort(np.asarray(self.q, float), kind='stable')
        self.q = np.asarray(self.q, float)[o]
        self.y = np.asarray(self.y, float)[o]
        self.sigma = np.asarray(self.sigma, float)[o]


@dataclass
class JoinFit:
    """One join: δ = ln f (f multiplies scan b), its reported error and
    counting error, χ², dof, the model used, the points used (indices in a
    and b), the sensitivity of δ to a log shift of each used point (a's
    then b's), the prior offered and whether it was used (with z and why),
    and flags ('window reduced', ...)."""
    delta: float
    err: float
    err_counting: float
    chi2: float
    dof: int
    order: int
    n_ext: int
    space: str
    likelihood: str
    method: str = 'joint'
    ia: np.ndarray = None
    ib: np.ndarray = None
    sensitivity: np.ndarray = None
    prior: tuple = None
    prior_used: bool = False
    z: float = None
    why: str = ''
    flags: list = field(default_factory=list)

    @property
    def factor(self):
        return math.exp(self.delta)

    @property
    def factor_err(self):
        return self.factor * self.err

    @property
    def p_chi2(self):
        from scipy.stats import chi2 as C2
        return float(C2.sf(self.chi2, self.dof)) if self.dof > 0 else math.nan


def fresnel(q, qc=QC):
    q = np.asarray(q, float)
    s = np.sqrt(np.maximum(q ** 2 - qc ** 2, 0.0))
    return np.where(q <= qc, 1.0, ((q - s) / (q + s)) ** 2)


MAX_ORDER = 7      # the guard's highest polynomial order (guard_ladder)
# the guard keeps the first fit whose chi2 p-value is at least this. 0.3 from 2026-11-22 (the gauntlet:
# 0.01 let model bias of 0.2-0.4 sigma through at 4 of 21 synthetic joins, 0.3 passes 19 of 21); 0.7
# since 2026-11-24 (study A, docs/studies/reflectivity_guard, C48: the bias at the five hard joins halves,
# 0.24 -> 0.12 errors, for a smooth join's pull SD 1.00 -> 1.04; p 0.5-0.9 win 23 of 24 robustness
# cells; the owner's rule: the best method, demonstrated, tested and presented, is the default)
GUARD_P = 0.7
# below this chi2 p-value even the best rung is called inadequate in the join's note (the guard's
# threshold is a preference among rungs, not a test of adequacy; 2026-11-24, Main): 0.01, the guard
# of before 2026-11-22
ADEQUATE_P = 0.01
# points either side of the overlap (2026-11-22, the gauntlet with the owner's monitor model:
# 4 let a 0.4-sigma model bias through at water's first join, 2 passes 17 of 18 joins)
N_EXT = 2


def window(qa, qb, n_ext=4):
    """(indices of a, indices of b) used at a join: the overlap [min q_b,
    max q_a] plus ``n_ext`` points of a below it and of b above it."""
    qa, qb = np.asarray(qa, float), np.asarray(qb, float)
    lo, hi = qb.min(), qa.max()
    ia = np.flatnonzero(qa >= lo - 1e-9)
    ib = np.flatnonzero(qb <= hi + 1e-9)
    if n_ext and len(ia):
        ia = np.arange(max(ia.min() - n_ext, 0), len(qa))
    if n_ext and len(ib):
        ib = np.arange(0, min(ib.max() + 1 + n_ext, len(qb)))
    return ia, ib


def _fit_once(a, b, order, n_ext, space, qc, qoff, likelihood, prior, snr_min):
    ia, ib = window(a.q, b.q, n_ext)
    if len(ia) < 2 or len(ib) < 2:
        raise ValueError('the scans overlap in too few points (%d of a, %d of b)' % (len(ia), len(ib)))
    q = np.concatenate([a.q[ia], b.q[ib]])
    y = np.concatenate([a.y[ia], b.y[ib]])
    s = np.concatenate([a.sigma[ia], b.sigma[ib]])
    isb = np.concatenate([np.zeros(len(ia)), np.ones(len(ib))])
    base = np.log(fresnel(q + qoff, qc)) if space == 'rrf' else np.zeros_like(q)
    if space not in ('rrf', 'raw'):
        raise ValueError("space %r: 'rrf' or 'raw'" % space)
    xm, xh = 0.5 * (q.min() + q.max()), 0.5 * (q.max() - q.min()) or 1.0
    u = (q - xm) / xh
    X = np.column_stack([u ** k for k in range(order + 1)] + [-isb])
    good = (y > 0) & (s > 0) & (y / s >= snr_min)               # the log fit needs y > 0
    if good.sum() < X.shape[1] + 2:
        raise ValueError('too few usable points (%d) for order %d' % (good.sum(), order))
    Xl, Yl = X[good], np.log(y[good]) - base[good]
    wl = (y[good] / s[good]) ** 2
    A = Xl.T @ (Xl * wl[:, None])
    g = Xl.T @ (wl * Yl)
    if prior is not None:
        A[-1, -1] += 1 / prior[1] ** 2
        g[-1] += prior[0] / prior[1] ** 2
    th = np.linalg.solve(A, g)
    if likelihood == 'log':
        cov = np.linalg.inv(A)
        res = Yl - Xl @ th
        chi2 = float(np.sum(wl * res ** 2))
        n = int(good.sum())
        sens = np.zeros(len(q))
        sens[good] = (cov @ (Xl * wl[:, None]).T)[-1]
    elif likelihood == 'poisson':
        var_k = s ** 2 / np.maximum(np.abs(y), s)         # variance per unit intensity
        for _ in range(30):
            mu = np.exp(base + X @ th)
            var = var_k * mu
            J = X * mu[:, None]
            A = J.T @ (J / var[:, None])
            g = J.T @ ((y - mu) / var)
            if prior is not None:
                A[-1, -1] += 1 / prior[1] ** 2
                g[-1] += (prior[0] - th[-1]) / prior[1] ** 2
            step = np.linalg.solve(A, g)
            th = th + step
            if np.max(np.abs(step)) < 1e-11:
                break
        mu = np.exp(base + X @ th)
        var = var_k * mu
        J = X * mu[:, None]
        A = J.T @ (J / var[:, None])
        if prior is not None:
            A[-1, -1] += 1 / prior[1] ** 2
        cov = np.linalg.inv(A)
        chi2 = float(np.sum((y - mu) ** 2 / var))
        n = len(y)
        sens = (cov @ (J / var[:, None]).T)[-1] * y           # dδ/d ln y_i
    else:
        raise ValueError("likelihood %r: 'poisson' or 'log'" % likelihood)
    dof = n - X.shape[1]
    err_c = float(math.sqrt(cov[-1, -1]))
    return dict(delta=float(th[-1]), err_c=err_c, chi2=chi2, dof=dof, ia=ia, ib=ib, sens=sens,
                coef=np.array(th[:-1], float), centre=float(xm), half_width=float(xh))


@dataclass
class RungFit:
    """One rung (order, points either side) of the joint fit, fitted alone
    (``rung_fit``): δ, its counting error, χ², dof, and the curve, so that a
    study can redo the guard's choice, or average over rungs, without
    refitting, and draw what each rung fitted. ``coef`` are c_0..c_m of
    Σ c_k u^k, u = (q − ``centre``)/``half_width``: ln(μ_a/R_F(q + q_off))
    for ``space='rrf'``, ln μ_a for ``'raw'`` (μ_b = μ_a·exp(−δ))."""
    order: int
    n_ext: int
    delta: float
    err_counting: float
    chi2: float
    dof: int
    coef: np.ndarray
    centre: float
    half_width: float
    ia: np.ndarray
    ib: np.ndarray
    space: str = 'rrf'

    @property
    def p_chi2(self):
        """The χ² p-value as the guard computes it (1 when dof is 0)."""
        from scipy.stats import chi2 as C2
        return float(C2.sf(self.chi2, self.dof)) if self.dof > 0 else 1.0

    @property
    def err(self):
        """The error ``joint_factor`` reports at this rung (inflate-only)."""
        return unc.inflate(self.err_counting, self.chi2, self.dof)

    def curve(self, q):
        """The fitted Σ c_k u^k at ``q`` (scan a's scale; module docstring)."""
        u = (np.asarray(q, float) - self.centre) / self.half_width
        return np.polynomial.polynomial.polyval(u, self.coef)


def rung_fit(a, b, order=4, n_ext=N_EXT, space='rrf', qc=QC, qoff=0.0, likelihood='poisson', prior=None,
             snr_min=0.0):
    """The joint fit at one rung, without the guard: a ``RungFit`` with the
    same δ, error, χ² and dof as ``joint_factor(a, b, order, n_ext,
    guard_p=0)``, and the fitted curve. Raises ValueError as the fit does
    (too few points)."""
    r = _fit_once(a, b, order, n_ext, space, qc, qoff, likelihood, prior, snr_min)
    return RungFit(order, n_ext, r['delta'], r['err_c'], r['chi2'], r['dof'], r['coef'], r['centre'],
                   r['half_width'], r['ia'], r['ib'], space)


def guard_ladder(a, b, order=4, n_ext=N_EXT, max_order=MAX_ORDER):
    """The (order, points either side) the guard tries, in order of preference
    (2026-11-22, the gauntlet, ``tests/tools/ref_patch_gauntlet.py``): the
    largest window first (most precise), the order rising from ``order`` at
    each window, down to the overlap alone with orders from 2. The first fit
    whose chi2 is adequate is kept. Orders are limited to what the window
    can carry: two degrees of freedom at least, and, when no Qz is shared
    by the two scans, fewer coefficients than positions (else the
    polynomial absorbs the offset)."""
    windows = [n_ext] + [e for e in (2, 1, 0) if e < n_ext]
    out = []
    for e in windows:
        ia, ib = window(a.q, b.q, e)
        qa, qb = np.round(a.q[ia], 9), np.round(b.q[ib], 9)
        n_pos = len(np.unique(np.concatenate([qa, qb])))
        shared = len(np.intersect1d(qa, qb))
        top = min(max_order, len(ia) + len(ib) - 4, n_pos - (1 if shared else 2))
        lo = order if e else 2
        out += [(o, e) for o in range(lo, top + 1)]
    return out or [(order, n_ext)]


def joint_factor(a, b, order=4, n_ext=N_EXT, space='rrf', qc=QC, qoff=0.0, likelihood='poisson', prior=None,
                 inflate=True, guard_p=None, snr_min=0.0):
    """The joint fit at one join (module docstring): a ``JoinFit``. ``prior``:
    (δ_0, s_0) or None (a single join; for several use ``chain(prior=...)``,
    which handles the correlations). ``guard_p``: the
    guard's p, by default ``GUARD_P`` as it is at the call (a study that was run
    at another default can set ``GUARD_P`` for its run)."""
    from scipy.stats import chi2 as C2
    if guard_p is None:
        guard_p = GUARD_P
    tries = guard_ladder(a, b, order, n_ext) if guard_p else [(order, n_ext)]
    flags, last_err, best = [], None, None

    def result(r, o, e):
        err = unc.inflate(r['err_c'], r['chi2'], r['dof']) if inflate else r['err_c']
        return JoinFit(r['delta'], err, r['err_c'], r['chi2'], r['dof'], o, e, space, likelihood, 'joint',
                       r['ia'], r['ib'], r['sens'], prior, prior is not None, None, '', flags)
    for k, (o, e) in enumerate(tries):
        try:
            r = _fit_once(a, b, o, e, space, qc, qoff, likelihood, prior, snr_min)
        except (ValueError, np.linalg.LinAlgError) as err:
            last_err = err
            continue
        if not (np.isfinite(r['delta']) and np.isfinite(r['err_c']) and np.isfinite(r['chi2'])):
            last_err = ValueError('the fit at order %d, %d either side diverged' % (o, e))
            continue
        p = C2.sf(r['chi2'], r['dof']) if r['dof'] > 0 else 1.0
        if not guard_p or p >= guard_p:
            if k:
                flags.append('order %d, %d either side: the first adequate fit (%d tried)' % (o, e, k + 1))
            return result(r, o, e)
        if best is None or p > best[0]:
            best = (p, r, o, e)
    if best is not None:              # none reached guard_p: the most adequate one, its error inflated by its chi2
        p, r, o, e = best
        red = r['chi2'] / max(r['dof'], 1)
        infl = unc.inflate(1.0, r['chi2'], r['dof']) if inflate else 1.0
        how = ', error inflated ×%.2f' % infl if infl > 1.0 else ''
        if p >= ADEQUATE_P:           # an adequate fit that missed the guard's preference: say so, without alarm
            flags.append('order %d, %d either side: the best fit of the ladder (chi2 p %.2f, chi2/dof %.2f; none '
                         'reached p %g)%s' % (o, e, p, red, guard_p, how))
        else:
            flags.append('no adequate fit (chi2 p < %g everywhere): order %d, %d either side, chi2/dof %.2f%s'
                         % (ADEQUATE_P, o, e, red, how))
        return result(r, o, e)
    raise ValueError('no joint fit possible at this join: %s' % last_err)


def _ratio_fit(r, re, ia, ib, method, inflate):
    w = 1 / re ** 2
    fac = float(np.sum(w * r) / np.sum(w))
    err = float(np.sum(w) ** -0.5) / fac
    chi2 = float(np.sum(w * (r - fac) ** 2))
    dof = max(len(r) - 1, 0)
    e = unc.inflate(err, chi2, dof) if inflate else err
    return JoinFit(math.log(fac), e, err, chi2, dof, 0, 0, 'raw', 'ratio', method, ia, ib)


def interp_factor(a, b, kind='cubic', log=False, inflate=True):
    """Reference (the hand-off §3.2 estimator; the legacy patch's family):
    scan b interpolated at a's overlap points, weighted mean of the ratios.
    In linear intensity (``log`` False) it is biased when the grids do not
    coincide (P1)."""
    from scipy.interpolate import interp1d
    ia = np.flatnonzero((a.q >= b.q[0] - 1e-12) & (a.q <= b.q[-1] + 1e-12))
    if len(ia) == 0:
        raise ValueError('no point of scan a inside scan b')
    x = a.q[ia]
    k = kind if len(b.q) > 3 else 'linear'
    fb = np.exp(interp1d(b.q, np.log(b.y), kind=k)(x)) if log else interp1d(b.q, b.y, kind=k)(x)
    fe = interp1d(b.q, b.sigma, kind='linear')(x)
    r = a.y[ia] / fb
    re = r * np.hypot(a.sigma[ia] / a.y[ia], fe / fb)
    return _ratio_fit(r, re, ia, None, 'interp-log' if log else 'interp', inflate)


def coincident_factor(a, b, tol=1e-6, inflate=True):
    """Weighted mean ratio over points measured at the same q in both scans
    (no model, no interpolation); None when no q coincides."""
    pairs = [(i, j) for i in range(len(a.q)) for j in range(len(b.q)) if abs(a.q[i] - b.q[j]) < tol]
    if not pairs:
        return None
    i, j = map(np.array, zip(*pairs))
    r = a.y[i] / b.y[j]
    re = r * np.hypot(a.sigma[i] / a.y[i], b.sigma[j] / b.y[j])
    return _ratio_fit(r, re, i, j, 'coincident', inflate)


def known_steps(foils, settings, overlap_qz=None):
    """The foil prior on the steps of a chain: (δ_0 (K−1), C_prior (K−1 ×
    K−1)), δ_0,m = ln(T(n_(m−1))/T(n_m)). The foils' run-to-run errors are
    shared by the joins that change the same foil, so C_prior = S (μ² D
    diag(σ_k²) Dᵀ + s² I) S, D the signed bit differences, s the step
    scatter, S = CAL_HIGH_QZ_SCALE at overlaps with Q_z ≥ CAL_HIGH_QZ; its
    diagonal equals ``Foils.step``'s error squared. Joins with equal
    settings get δ_0 = 0 and zero variance (no information: mark them unused)."""
    from .absorbers import CAL_HIGH_QZ, CAL_HIGH_QZ_SCALE, CAL_STEP_SCATTER
    n = len(settings) - 1
    nb = len(foils.thickness_um)
    D = np.zeros((n, nb))
    mean = np.zeros(n)
    same = np.zeros(n, bool)
    for m in range(n):
        a, b = foils._bits(settings[m]), foils._bits(settings[m + 1])
        D[m] = np.array(a, float) - np.array(b, float)
        mean[m] = math.log(foils.step(settings[m], settings[m + 1])[0])
        same[m] = settings[m] == settings[m + 1]
    mu = foils.mu_per_um
    C = mu ** 2 * D @ np.diag(np.asarray(foils.sigma_um, float) ** 2) @ D.T + CAL_STEP_SCATTER ** 2 * np.eye(n)
    C[same, :] = 0.0
    C[:, same] = 0.0
    if overlap_qz is not None:
        sc = np.where(np.asarray(overlap_qz, float) >= CAL_HIGH_QZ, CAL_HIGH_QZ_SCALE, 1.0)
        C = sc[:, None] * C * sc[None, :]
    return mean, C


def prior_mask(monitor_ratios, z, tol=0.03, z_max=3.0):
    """Where the prior may be used: Monc/Monp across the join within ``tol``
    of 1 (P29: a monitor that misses a slit change), and |z| ≤ ``z_max``.
    Returns (mask, reasons: '' where used)."""
    use, why = [], []
    for r, zz in zip(monitor_ratios, z):
        if r is None or not np.isfinite(r):
            use.append(False)
            why.append('monitor ratio unknown')
        elif abs(r - 1) > tol:
            use.append(False)
            why.append('Monc/Monp changed ×%.3f across the join (slits?): the foil ratio does not apply' % r)
        elif zz is None or not np.isfinite(zz):
            use.append(False)
            why.append('no prior')
        elif abs(zz) > z_max:
            use.append(False)
            why.append('data and foils disagree by %.1f σ' % zz)
        else:
            use.append(True)
            why.append('')
    return np.array(use, bool), why


@dataclass
class PatchResult:
    """φ (K: ln of each scan's factor to the anchor), Σ (K × K, log units),
    the steps and their covariance, the joins, the method."""
    phi: np.ndarray
    Sigma: np.ndarray
    joins: list
    method: str
    steps: np.ndarray = None
    C_steps: np.ndarray = None

    @property
    def factors(self):
        """Each scan's factor to the anchor, exp(φ)."""
        return np.exp(self.phi)

    def stitch(self, scans, merge='none', tol=1e-6):
        """Every measured point on the anchor's scale (``Stitched``): no
        interpolation; ``merge='coincident'`` averages points measured at the
        same q in several scans (weights 1/σ², W rows split accordingly)."""
        K = len(scans)
        q = np.concatenate([s.q for s in scans])
        y = np.concatenate([s.y * math.exp(self.phi[m]) for m, s in enumerate(scans)])
        sm = np.concatenate([s.sigma * math.exp(self.phi[m]) for m, s in enumerate(scans)])
        sid = np.concatenate([np.full(len(s.q), m) for m, s in enumerate(scans)])
        o = np.argsort(q, kind='stable')
        q, y, sm, sid = q[o], y[o], sm[o], sid[o]
        W = np.zeros((len(q), K))
        W[np.arange(len(q)), sid] = 1.0
        if merge == 'coincident':
            qs, ys, ss, Ws = [], [], [], []
            i = 0
            while i < len(q):
                j = i + 1
                while j < len(q) and q[j] - q[i] < tol:
                    j += 1
                w = 1 / sm[i:j] ** 2
                ys.append(float(np.sum(w * y[i:j]) / np.sum(w)))
                ss.append(float(np.sum(w) ** -0.5))
                qs.append(float(np.mean(q[i:j])))
                Ws.append((w[:, None] * W[i:j]).sum(axis=0) / w.sum())
                i = j
            q, y, sm, W = np.array(qs), np.array(ys), np.array(ss), np.array(Ws)
        elif merge != 'none':
            raise ValueError("merge %r: 'none' or 'coincident'" % merge)
        return Stitched(q, y, sm, W, self.Sigma)


@dataclass
class Stitched:
    """Stitched points: q, y, the counting error σ_meas, their weights W on
    the scans' log scales and Σ (lss_core.uncertainty)."""
    q: np.ndarray
    y: np.ndarray
    sigma_meas: np.ndarray
    W: np.ndarray
    Sigma: np.ndarray

    def sigma_total(self):
        """√(σ_meas² + y²·diag(W Σ Wᵀ)): the per-point error with the factors'
        uncertainty folded in (the hand-off's error column; correct per point,
        but the common-mode part is lost: use ``covariance`` for fits)."""
        return unc.total_sigma(self.y, self.sigma_meas, self.W, self.Sigma)

    def covariance(self, space='log', model=None):
        return unc.stitched_covariance(self.y, self.sigma_meas, self.W, self.Sigma, space, model)


def chain(scans, fitter=None, prior=None, monitor_ratios=None, tol=0.03, z_max=3.0, **kw):
    """Join by join, each scan fitted against the one before it (its own
    points), the covariance carried forward (a random walk, hand-off §3.4).
    ``fitter``: ``joint_factor`` (default), ``interp_factor``,
    ``coincident_factor`` or any f(a, b, **kw) → JoinFit; ``prior``: (δ_0,
    C_prior) for the K−1 steps (``known_steps``), combined where
    ``prior_mask(monitor_ratios, z)`` allows (marginalised elsewhere).
    Returns a ``PatchResult``."""
    fitter = fitter or joint_factor
    K = len(scans)
    joins = []
    for m in range(1, K):
        j = fitter(scans[m - 1], scans[m], **kw)
        if j is None:
            raise ValueError('join %d (%s → %s): no factor' % (m, scans[m - 1].label, scans[m].label))
        joins.append(j)
    steps = np.array([j.delta for j in joins])
    C = np.diag([j.err ** 2 for j in joins])
    method = getattr(fitter, '__name__', 'fit')
    if prior is not None:
        mean, Cp = prior
        mr = monitor_ratios if monitor_ratios is not None else [None] * (K - 1)
        z = (steps - mean) / np.sqrt(np.diag(C) + np.diag(Cp))
        use, why = prior_mask(mr, z, tol, z_max)
        use &= np.diag(Cp) > 0
        steps_post, C_post, z = unc.combine(steps, C, mean, Cp, use)
        for j, u, w, zz, m0, v in zip(joins, use, why, z, mean, np.diag(Cp)):
            j.prior, j.prior_used, j.z, j.why = (float(m0), float(math.sqrt(v))), bool(u), float(zz), w
        steps, C = steps_post, C_post
        method += '+prior'
    phi, Sigma = unc.steps_to_phi(steps, C)
    return PatchResult(phi, Sigma, joins, method, steps, C)


def global_fit(scans, order=4, n_ext=4, space='rrf', qc=QC, qoff=0.0, prior_mean=None, prior_cov=None,
               inflate=True):
    """All factors in one weighted least-squares fit in ln y (each join's
    window has its own polynomial; a point is used in one window only).
    With disjoint windows this equals ``chain`` with the same window and
    order and **no guard** (``chain(likelihood='log', n_ext=4,
    guard_p=0)``, measured to the fourth digit); it adds something when a
    correlated prior couples the joins or a scan overlaps more than its
    neighbour. It has no guard and one χ² inflation for all joins: where
    one window cannot follow the curve (a 100 Å film at NX steps) that
    join is biased (−3.4 %) and every join's error is inflated about
    ten-fold (``docs/reports/patch_demo.md``, figure 2; pinned in
    ``tests/test_patch_demo.py``). Returns a ``PatchResult``."""
    K = len(scans)
    q = np.concatenate([s.q for s in scans])
    y = np.concatenate([s.y for s in scans])
    sg = np.concatenate([s.sigma for s in scans])
    sid = np.concatenate([np.full(len(s.q), m) for m, s in enumerate(scans)])
    pid = np.concatenate([np.arange(len(s.q)) for s in scans])
    base = np.log(fresnel(q + qoff, qc)) if space == 'rrf' else np.zeros_like(q)
    used = np.zeros(len(q), bool)
    blocks = []
    for m in range(1, K):
        ia, ib = window(scans[m - 1].q, scans[m].q, n_ext)
        sel = np.concatenate([np.flatnonzero((sid == m - 1) & np.isin(pid, ia)),
                              np.flatnonzero((sid == m) & np.isin(pid, ib))])
        sel = sel[~used[sel]]
        used[sel] = True
        blocks.append(sel)
    keep = np.concatenate(blocks)
    nb = order + 1
    Xc = np.zeros((len(keep), nb * (K - 1)))
    r0 = 0
    for j, sel in enumerate(blocks):
        xx = q[sel]
        xm, xh = 0.5 * (xx.min() + xx.max()), 0.5 * (xx.max() - xx.min()) or 1.0
        u = (xx - xm) / xh
        for k in range(nb):
            Xc[r0:r0 + len(sel), j * nb + k] = u ** k
        r0 += len(sel)
    good = (y[keep] > 0) & (sg[keep] > 0)
    keep, Xc = keep[good], Xc[good]
    Xs = np.zeros((len(keep), K - 1))
    for m in range(1, K):
        Xs[sid[keep] == m, m - 1] = -1.0
    X = np.hstack([Xc, Xs])                                    # parameters: polynomials, then φ_1..φ_(K-1)
    Y = np.log(y[keep]) - base[keep]
    w = (y[keep] / sg[keep]) ** 2
    A = X.T @ (X * w[:, None])
    bvec = X.T @ (w * Y)
    nc = Xc.shape[1]
    L = np.tril(np.ones((K - 1, K - 1)))
    if prior_mean is not None:
        Linv = np.linalg.inv(L)
        Pphi = Linv.T @ np.linalg.inv(prior_cov) @ Linv
        A[nc:, nc:] += Pphi
        bvec[nc:] += Pphi @ (L @ np.asarray(prior_mean, float))
    cov = np.linalg.pinv(A)
    th = cov @ bvec
    chi2 = float(np.sum(w * (Y - X @ th) ** 2))
    dof = len(Y) - X.shape[1]
    infl = max(1.0, math.sqrt(chi2 / dof)) if (inflate and dof > 0) else 1.0
    Sigma = np.zeros((K, K))
    Sigma[1:, 1:] = cov[nc:, nc:] * infl ** 2
    phi = np.concatenate([[0.0], th[nc:]])
    Linv = np.linalg.inv(L)
    steps = Linv @ phi[1:]
    C_steps = Linv @ Sigma[1:, 1:] @ Linv.T
    joins = [JoinFit(float(steps[m]), float(math.sqrt(C_steps[m, m])), math.nan, chi2, dof, order, n_ext, space,
                     'log', 'global') for m in range(K - 1)]
    return PatchResult(phi, Sigma, joins, 'global', steps, C_steps)


def scans_from_reflectivity(result, order=None):
    """``Scan``s (in patch order) from an ``Experiment.reflectivity`` result:
    each scan's points (Qz, net signal, error per monitor count)."""
    nums = order or result.order
    out = []
    for n in nums:
        d = np.atleast_2d(np.asarray(result.per_scan[n], float))
        out.append(Scan(d[:, 0], d[:, 1], d[:, 2], label='S# %d' % n))
    return out
