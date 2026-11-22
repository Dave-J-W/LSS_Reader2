"""Reflectivity patching on synthetic replicates: every method, with the truth.

A **replicate** is one draw of counting noise (seed) of one configuration
(``Config``): a true curve R(Qz) of a liquid interface (Parratt recursion,
L. G. Parratt, Phys. Rev. 95, 359 (1954), https://doi.org/10.1103/PhysRev.95.359,
with Névot–Croce roughness, L. Névot and P. Croce, Rev. Phys. Appl. 15, 761
(1980), https://doi.org/10.1051/rphysap:01980001503076100; ``synthetic.xrr``),
measured as overlapping scans through calibrated absorber foils
(``synthetic.xrr_scans``: Poisson counts in the reader's ROI boxes, Poisson
monitor). The truth kept beside it: the noise-free scans (the same plan at
the expected counts), the true scale of every scan and so the true factor of
every join.

**Foil truth.** By default (``foil_error=True``) the foils are not exactly
what the calibration says: each replicate draws the true steps from the
prior's own covariance (``patching.known_steps``), so the foil prior is
right on average with the error it claims, as it would be on real data. With
``foil_error=False`` the prior is exact (its mean is the truth).

**Methods** (``METHODS``; the names of ``tests/tools/ref_patch_survey.py``
plus a few): the legacy chain (``lss_core.reflectivity.patch``, each factor
from ``stitching.fitted_factor`` against everything joined so far, its own
error, no inheritance), the spline ratio in linear and log intensity
(``patching.interp_factor``), coinciding points only, the joint fit
(``patching.joint_factor``) at orders 2–4 with 0–4 points either side, in
R/R_F or raw, Poisson-like or log likelihood, the joint fit with the
correlated foil prior (``patching.chain(prior=...)``) and the global fit.
Every non-legacy method gives a ``PatchResult`` (φ, Σ) and the stitched
points (``Stitched``: σ_meas, σ_total, covariance).

**Display scale.** The stitched curves are on the anchor scan's scale; the
demonstrator multiplies them by the anchor's *true* scale to put them on R
(normalising the anchor to R = 1 below Qc is a separate step, not part of
patching). Join close-ups are on scan a's scale.

``join_curve`` rebuilds a joint fit's curve through both scans in the window
(``JoinFit`` keeps δ but not the polynomial): at fixed δ the maximum-
likelihood coefficients are those of the joint fit, so a fit of the
coefficients alone at δ̂ gives them back (tested against
``patching.joint_factor``).
"""
import math
from dataclasses import dataclass, field, replace

import numpy as np

from lss_core import patching, reflectivity as refl, stitching, uncertainty as unc
from lss_core.patching import Scan

from synthetic import xrr, xrr_scans as xs

# ---- configuration -------------------------------------------------------------

TRUTHS = ('water', 'dppc', 'film')
PLANS = ('nx', 'standard', 'staggered', 'edge')
PLAN_LABELS = {'nx': 'NX-like grids (6–9)', 'standard': '4 scans, coinciding', 'staggered': '4 scans, staggered',
               'edge': 'staggered across Qc (P1)'}
TRUTH_LABELS = {'water': 'bare water', 'dppc': 'DPPC monolayer', 'film': 'film (Kiessig fringes)'}

METHODS = {
    'legacy': dict(kind='legacy', label='legacy (spline ratio, merged)'),
    'interp': dict(kind='interp', label='spline ratio'),
    'interp_log': dict(kind='interp', log=True, label='spline ratio, ln y'),
    'coincident': dict(kind='coincident', label='coinciding points'),
    'joint_o2_e0': dict(kind='joint', order=2, n_ext=0, label='joint o2, overlap'),
    'joint_o2_e4': dict(kind='joint', order=2, n_ext=4, label='joint o2, 4 either side'),
    'joint_o3_e2': dict(kind='joint', order=3, n_ext=2, label='joint o3, 2 either side'),
    'joint_o4_e2': dict(kind='joint', order=4, n_ext=2, label='joint o4, 2 either side'),
    'joint_o4_e4': dict(kind='joint', order=4, n_ext=4, label='joint o4, 4 either side (default)'),
    'joint_o4_e4_raw': dict(kind='joint', order=4, n_ext=4, space='raw', label='joint o4 e4, raw'),
    'joint_o4_e4_log': dict(kind='joint', order=4, n_ext=4, likelihood='log', label='joint o4 e4, ln-y LSQ'),
    'joint_o4_e4_prior': dict(kind='prior', label='joint o4 e4 + foil prior'),
    'global': dict(kind='global', label='global fit (one LSQ)'),
}
DEFAULT_METHODS = ('legacy', 'interp', 'joint_o4_e4', 'joint_o4_e4_prior')
COLOURS = {'legacy': '#d62728', 'interp': '#ff7f0e', 'interp_log': '#bcbd22', 'coincident': '#8c564b',
           'joint_o2_e0': '#9467bd', 'joint_o2_e4': '#e377c2', 'joint_o3_e2': '#17becf', 'joint_o4_e2': '#2ca02c',
           'joint_o4_e4': '#1f77b4', 'joint_o4_e4_raw': '#7f7f7f', 'joint_o4_e4_log': '#393b79',
           'joint_o4_e4_prior': '#006d2c', 'global': '#637939'}


@dataclass
class Config:
    """One demonstration setting. ``counts`` scales the beam and the
    monitors together (1: the NX school rates, about 4e5 counts/s in the
    ROI at each scan's first point; the absorbers chosen are the same at any
    value, the counting error scales as 1/√counts). ``thickness``: of the
    film (Å). ``foil_error``: true foils drawn from the prior's covariance."""
    truth: str = 'film'
    plan: str = 'nx'
    counts: float = 1.0
    thickness: float = 100.0
    foil_error: bool = True
    errors: str = 'counting+monitor'

    def profile(self):
        if self.truth == 'film':
            return xrr.film(self.thickness)
        if self.truth == 'dppc':
            return xrr.dppc()
        if self.truth == 'water':
            return xrr.bare_water()
        raise ValueError('truth %r: one of %s' % (self.truth, ', '.join(TRUTHS)))

    def plan_specs(self):
        if self.plan == 'nx':
            return xs.nx_like_plan()
        if self.plan == 'standard':
            return xs.standard_plan(4, 0.5, overlap=4, grid='coincide')
        if self.plan == 'staggered':
            return xs.standard_plan(4, 0.5, overlap=4, grid='staggered')
        if self.plan == 'edge':
            return xs.chain_plan([(0.01, 0.0266, 0.0025), (0.0266, 0.07, 0.005), (0.06, 0.3, 0.01)],
                                 overlap=4, grid='staggered')
        raise ValueError('plan %r: one of %s' % (self.plan, ', '.join(PLANS)))

    def beamline(self):
        b = xs.Beamline()
        c = float(self.counts)
        return replace(b, flux=b.flux * c, max_rate=b.max_rate * c, monc_rate=b.monc_rate * c,
                       monp_rate=b.monp_rate * c)


@dataclass
class Replicate:
    """One noise draw and its truth. ``scans``: patching ``Scan``s in patch
    order (noisy), ``expected``: the same at the expected counts;
    ``true_steps``: f of each join (multiplies scan b onto scan a);
    ``true_phi``: ln of each scan's factor to the anchor; ``prior``: the foil
    prior (δ_0, C) offered to the joins; ``monitor_ratios``: Monc/Monp of b
    over a across each join (P29 guard); ``scale0``: the anchor's true scale
    (net × scale0 = R)."""
    config: Config
    seed: int
    data: object
    noise_free: object
    order: list
    scans: list
    expected: list
    true_steps: np.ndarray
    true_phi: np.ndarray
    prior: tuple
    monitor_ratios: list
    scale0: float
    profile: object = None

    def truth(self, q):
        """R(Qz) the scans were drawn from."""
        return self.data.truth(q)

    def scale(self, m):
        """True scale of scan m (in patch order): net × scale = R."""
        return self.data.scans[self.order[m]].scale


def replicate(config=None, seed=0):
    """Draw replicate ``seed`` of ``config`` (module docstring). The same
    seed gives the same numbers."""
    cfg = config or Config()
    profile = cfg.profile()
    plan = cfg.plan_specs()
    bl = cfg.beamline()
    rng = np.random.default_rng([20261122, int(seed)])
    # absorbers as the generator chooses them, then the foils' true errors
    first = xs.measure(profile, plan, bl, expected=True)
    order = list(first.order)
    absorbers = [first.scans[k].absorber for k in sorted(first.scans)]
    foils = bl.foils()
    settings = [first.scans[k].absorber for k in order]
    qov = [float(first.scans[k].qz.min()) for k in order[1:]]
    mean, C = patching.known_steps(foils, settings, qov)
    err = np.ones(len(plan))
    if cfg.foil_error and len(order) > 1:
        eps = rng.multivariate_normal(np.zeros(len(mean)), C, method='eigh')
        lnerr = np.concatenate([[0.0], np.cumsum(eps)])
        for m, k in enumerate(order):
            err[sorted(first.scans).index(k)] = math.exp(lnerr[m])
    plan = [replace(p, absorber=int(n), attenuation_error=float(e)) for p, n, e in zip(plan, absorbers, err)]
    data = xs.measure(profile, plan, bl, errors=cfg.errors, seed=rng)
    clean = xs.measure(profile, plan, bl, errors=cfg.errors, expected=True)
    order = list(data.order)
    scans, expected = [], []
    for k in order:
        r = data.per_scan[k]
        scans.append(Scan(r[:, 0], r[:, 1], r[:, 2], label='scan %d' % k, absorber=data.scans[k].absorber))
        e = clean.per_scan[k]
        expected.append(Scan(e[:, 0], e[:, 1], e[:, 2], label='scan %d' % k, absorber=data.scans[k].absorber))
    steps = data.true_steps(order)
    true_steps = np.array([steps[j] for j in range(len(order) - 1)])
    s0 = data.scans[order[0]].scale
    true_phi = np.array([math.log(data.scans[k].scale / s0) for k in order])
    mr = []
    for a, b in zip(order, order[1:]):
        ra, rb = data.scans[a], data.scans[b]
        mr.append(refl.monitor_change(ra.qz, ra.monc, ra.monp, rb.qz, rb.monc, rb.monp))
    return Replicate(cfg, int(seed), data, clean, order, scans, expected, true_steps, true_phi, (mean, C), mr, s0,
                     profile)


# ---- methods ---------------------------------------------------------------------

@dataclass
class MethodResult:
    """One method on one replicate. ``steps``/``step_err``: ln f of each
    join and its error (after the prior, if any); ``phi``, ``Sigma``: each
    scan's log factor to the anchor and their covariance; ``joins``: the
    JoinFit of each join (None for the legacy chain); ``stitched``: a
    ``patching.Stitched`` (None for legacy); ``curve``: (q, y, σ) on the
    anchor's scale as displayed (legacy: the merged curve of
    ``reflectivity.patch``, its error column with the factor error folded
    in); ``sigma_total``: the per-point error with Σ folded in; ``error``:
    why the method failed, if it did."""
    name: str
    label: str
    steps: np.ndarray = None
    step_err: np.ndarray = None
    phi: np.ndarray = None
    Sigma: np.ndarray = None
    joins: list = None
    stitched: object = None
    curve: tuple = None
    sigma_total: np.ndarray = None
    error: str = ''
    notes: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.error

    @property
    def factors(self):
        """f of each join."""
        return np.exp(self.steps)


def _legacy(rep, name):
    per_scan = {k: rep.data.per_scan[k][:, :3].copy() for k in rep.order}
    phi, err = [0.0], [0.0]
    for m in range(1, len(rep.order)):
        merged = refl.patch(per_scan, rep.order[:m])
        f, e = stitching.fitted_factor(merged, per_scan[rep.order[m]])
        phi.append(math.log(f))
        err.append(e / f)
    curve = refl.patch(per_scan, rep.order)
    phi = np.array(phi)
    Sigma = np.diag(np.array(err) ** 2)          # the legacy's own claim: each factor alone, no inheritance
    steps = np.diff(phi)
    step_err = np.array(err[1:])                 # each join's own fit against the data so far, as legacy claims
    return MethodResult(name, METHODS[name]['label'], steps, step_err, phi, Sigma, None, None,
                        (curve[:, 0], curve[:, 1], curve[:, 2]), curve[:, 2])


def run_method(rep, name):
    """``MethodResult`` of method ``name`` (``METHODS``) on replicate ``rep``;
    a failure is recorded in ``error``, not raised."""
    spec = dict(METHODS[name])
    kind = spec.pop('kind')
    spec.pop('label')
    try:
        if kind == 'legacy':
            return _legacy(rep, name)
        if kind == 'global':
            res = patching.global_fit(rep.scans)
        elif kind == 'prior':
            res = patching.chain(rep.scans, prior=rep.prior, monitor_ratios=rep.monitor_ratios)
        elif kind == 'interp':
            res = patching.chain(rep.scans, fitter=patching.interp_factor, **spec)
        elif kind == 'coincident':
            res = patching.chain(rep.scans, fitter=patching.coincident_factor)
        else:
            res = patching.chain(rep.scans, fitter=patching.joint_factor, **spec)
    except (ValueError, np.linalg.LinAlgError) as e:
        return MethodResult(name, METHODS[name]['label'], error='%s: %s' % (type(e).__name__, e))
    st = res.stitch(rep.scans)
    out = MethodResult(name, METHODS[name]['label'], np.asarray(res.steps, float),
                       np.sqrt(np.diag(res.C_steps)), res.phi, res.Sigma, res.joins, st,
                       (st.q, st.y, st.sigma_meas), st.sigma_total())
    for m, j in enumerate(res.joins, start=1):
        for f in j.flags:
            out.notes.append('join %d: %s' % (m, f))
        if kind == 'prior':
            out.notes.append('join %d: prior %s' % (m, 'used' if j.prior_used else 'not used (%s)' % j.why))
    return out


def run_all(rep, names=None):
    """{name: MethodResult} for ``names`` (default every method)."""
    return {n: run_method(rep, n) for n in (names or METHODS)}


# ---- the joint fit's curve through a join -------------------------------------------

def _window_fit(a, b, order, ia, ib, space, likelihood, qc=patching.QC, qoff=0.0, delta=None):
    """Coefficients (and δ, unless given) of the shared polynomial of a
    joint fit on the window (ia, ib), as ``patching._fit_once`` defines
    the model; without a prior. Returns (c, δ, (xm, xh))."""
    q = np.concatenate([a.q[ia], b.q[ib]])
    y = np.concatenate([a.y[ia], b.y[ib]])
    s = np.concatenate([a.sigma[ia], b.sigma[ib]])
    isb = np.concatenate([np.zeros(len(ia)), np.ones(len(ib))])
    base = np.log(patching.fresnel(q + qoff, qc)) if space == 'rrf' else np.zeros_like(q)
    xm, xh = 0.5 * (q.min() + q.max()), 0.5 * (q.max() - q.min()) or 1.0
    u = (q - xm) / xh
    cols = [u ** k for k in range(order + 1)]
    free = delta is None
    if free:
        cols.append(-isb)
        off = np.zeros_like(q)
    else:
        off = -isb * delta
    X = np.column_stack(cols)
    good = (y > 0) & (s > 0)
    wl = (y[good] / s[good]) ** 2
    Xl = X[good]
    th = np.linalg.solve(Xl.T @ (Xl * wl[:, None]), Xl.T @ (wl * (np.log(y[good]) - base[good] - off[good])))
    if likelihood == 'poisson':
        var_k = s ** 2 / np.maximum(np.abs(y), s)
        for _ in range(30):
            mu = np.exp(base + off + X @ th)
            var = var_k * mu
            J = X * mu[:, None]
            step = np.linalg.solve(J.T @ (J / var[:, None]), J.T @ ((y - mu) / var))
            th = th + step
            if np.max(np.abs(step)) < 1e-11:
                break
    elif likelihood != 'log':
        raise ValueError(likelihood)
    if free:
        return th[:-1], float(th[-1]), (xm, xh)
    return th, float(delta), (xm, xh)


def join_curve(a, b, jf, n=200, qc=patching.QC, qoff=0.0, q=None):
    """(q, μ_a(q)) of a joint fit ``jf`` (a ``JoinFit`` of method 'joint')
    on scan a's scale, from the lowest to the highest q of its window (or
    at ``q``); scan b's model is μ_a / f. None for other methods."""
    if jf is None or jf.method != 'joint':
        return None
    c, _, (xm, xh) = _window_fit(a, b, jf.order, jf.ia, jf.ib, jf.space, jf.likelihood, qc, qoff, jf.delta)
    lo = min(a.q[jf.ia].min(), b.q[jf.ib].min())
    hi = max(a.q[jf.ia].max(), b.q[jf.ib].max())
    qq = np.linspace(lo, hi, n) if q is None else np.asarray(q, float)
    u = (qq - xm) / xh
    base = np.log(patching.fresnel(qq + qoff, qc)) if jf.space == 'rrf' else 0.0
    return qq, np.exp(base + np.column_stack([u ** k for k in range(jf.order + 1)]) @ c)


def spline_curve(a, b, factor, log=False, n=200):
    """(q, factor × spline of scan b) over the overlap with scan a: the
    legacy patch's interpolation (cubic in linear intensity; ``log``: in
    ln y), on scan a's scale."""
    from scipy.interpolate import interp1d
    lo, hi = b.q.min(), min(a.q.max(), b.q.max())
    qq = np.linspace(lo, hi, n)
    if log:
        f = np.exp(interp1d(b.q, np.log(np.maximum(b.y, 1e-300)), kind='cubic')(qq))
    else:
        f = interp1d(b.q, b.y, kind='cubic')(qq)
    return qq, factor * f


# ---- many replicates -----------------------------------------------------------------

def survey(config=None, seeds=range(100), names=None):
    """Factors of every method over many replicates against the truth.
    Returns {name: dict(dev (n_seeds × joins, f̂/f − 1), err (relative
    error of f̂), pulls per join: uncertainty.pulls of δ, failed)} and the
    rows (seed, method, join, delta, err, true)."""
    names = list(names or METHODS)
    rows = []
    for s in seeds:
        rep = replicate(config, s)
        for n in names:
            r = run_method(rep, n)
            for j in range(len(rep.true_steps)):
                rows.append(dict(seed=s, method=n, join=j + 1,
                                 delta=float(r.steps[j]) if r.ok else math.nan,
                                 err=float(r.step_err[j]) if r.ok else math.nan,
                                 true=float(math.log(rep.true_steps[j]))))
    out = {}
    for n in names:
        rr = [r for r in rows if r['method'] == n]
        joins = sorted({r['join'] for r in rr})
        per = {}
        for j in joins:
            d = [r for r in rr if r['join'] == j]
            est = np.array([r['delta'] for r in d])
            per[j] = unc.pulls(est, np.array([r['true'] for r in d]), np.array([r['err'] for r in d]))
        out[n] = dict(joins=per, failed=sum(1 for r in rr if not np.isfinite(r['delta'])))
    return out, rows


def chi2_vs_truth(rep, res):
    """(χ²/N with σ_total on the diagonal, χ²/N with the full covariance)
    of a method's stitched ln y against the true curve on the anchor scale
    (truth / scale0): both have mean 1 when the errors are right; the
    diagonal's scatter over replicates is the larger (the scans' common
    shifts counted as independent)."""
    st = res.stitched
    if st is None:
        return math.nan, math.nan
    t = rep.truth(st.q) / rep.scale0
    ok = (st.y > 0) & (t > 0)
    r = np.log(st.y[ok]) - np.log(t[ok])
    rel_tot = res.sigma_total[ok] / st.y[ok]
    d = float(np.sum((r / rel_tot) ** 2)) / ok.sum()
    C = st.covariance('log')[np.ix_(ok, ok)]
    L = np.linalg.cholesky(C)
    w = np.linalg.solve(L, r)
    return d, float(w @ w) / ok.sum()


def denoised(rep):
    """The same replicate at the expected counts (no noise): the methods
    run on it show their bias alone (the errors stay those of one draw)."""
    return replace(rep, data=rep.noise_free, scans=rep.expected)
