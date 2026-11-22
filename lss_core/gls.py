"""Reading an xmodfit covariance file and fitting with it: a reference
generalised-least-squares (GLS) fitter.

So that the reader's covariance export can be checked end to end without
XModFit, and so that scripts can fit stitched data with the right errors.
The file format is the hand-off's schema v1
(``docs/handoff/19-lss-reader-covariance-contract.md`` §2); the reasoning
is in ``docs/reports/downstream_covariance.md``.

The dataset covariance is low rank on top of a diagonal:

    log space:     C = diag((σ_meas/y)²) + W Σ Wᵀ                (of ln y)
    linear space:  C = diag(σ_meas²)     + D W Σ Wᵀ D,  D = diag(model)

With Σ = L Lᵀ (L: K × r, r ≤ K − 1, from the eigenvalues of Σ, so a
singular Σ, whose anchor row is zero, is fine) and U = W L (or D W L),
C = A + U Uᵀ with A diagonal, and by the Woodbury identity

    C⁻¹ = A⁻¹ − A⁻¹ U (I + Uᵀ A⁻¹ U)⁻¹ Uᵀ A⁻¹,
    ln det C = ln det A + ln det(I + Uᵀ A⁻¹ U):

O(N r²) instead of O(N³) (``LowRank``). Equivalently (exactly, in log
space; to first order in linear space) the fit can carry one log scale
shift per scan, φ = L η, with the penalty |η|²: the "nuisance" or "pull"
form, which ``fit`` uses.

    from lss_core import gls
    sc = gls.load('dppc_rrf.cov.json')
    d = np.loadtxt('dppc_rrf.txt')
    assert not sc.match_problems(d[:, 0], d[:, 1])
    res = gls.fit(sc, model, p0)           # model(x, *p) -> R/R_F
    res.params, res.errors, res.chi2, res.dof, res.shifts
"""
import json
import math
from dataclasses import dataclass, field

import numpy as np

FORMAT = 'xmodfit-covariance'
VERSION = 1
KINDS = ('multiplicative', 'additive', 'dense')


@dataclass
class Term:
    name: str
    kind: str
    scope: str = 'dataset'
    labels: list = None
    weights: np.ndarray = None       # N × K (multiplicative, additive)
    cov: np.ndarray = None           # K × K, or N × N for 'dense'
    provenance: dict = field(default_factory=dict)

    def factor(self, tol=1e-14):
        """L with L Lᵀ = cov over its positive eigenvalues (K × r)."""
        S = 0.5 * (self.cov + self.cov.T)
        ev, V = np.linalg.eigh(S)
        keep = ev > tol * max(ev.max(), 0.0) if ev.size else np.zeros(0, bool)
        return V[:, keep] * np.sqrt(ev[keep])


@dataclass
class Sidecar:
    """A loaded covariance file: x, y (may be None), σ_meas, terms; ``raw``
    the whole dictionary (``data`` holds the combined file's block)."""
    x: np.ndarray
    y: np.ndarray
    sigma_meas: np.ndarray
    terms: list
    data_file: str = None
    raw: dict = field(default_factory=dict)

    @property
    def n(self):
        return len(self.x)

    def term(self, name):
        for t in self.terms:
            if t.name == name:
                return t
        raise KeyError(name)

    def match_problems(self, x, y=None, rtol=1e-4):
        """XModFit's ``match_problems``: messages if the dataset's columns do
        not equal ``x`` (and ``y``) point by point within ``rtol`` (atol 0)."""
        out = []
        x = np.asarray(x, float)
        if len(x) != self.n:
            return ['the data have %d points, the covariance %d' % (len(x), self.n)]
        if not np.allclose(x, self.x, rtol=rtol, atol=0):
            out.append('x differs from the data file (worst relative %.2g)' % _worst(x, self.x))
        if y is not None and self.y is not None:
            y = np.asarray(y, float)
            if not np.allclose(y, self.y, rtol=rtol, atol=0):
                out.append('y differs from the data file (worst relative %.2g)' % _worst(y, self.y))
        return out

    def take(self, idx):
        """Rows ``idx`` (a fit range or mask): x, y, σ_meas and every term's
        weights (a dense term's rows and columns). Σ is unchanged."""
        idx = np.asarray(idx)
        if idx.dtype == bool:
            idx = np.flatnonzero(idx)
        terms = []
        for t in self.terms:
            if t.kind == 'dense':
                terms.append(Term(t.name, t.kind, t.scope, t.labels, None, t.cov[np.ix_(idx, idx)], t.provenance))
            else:
                terms.append(Term(t.name, t.kind, t.scope, t.labels, t.weights[idx], t.cov, t.provenance))
        return Sidecar(self.x[idx], None if self.y is None else self.y[idx], self.sigma_meas[idx], terms,
                       self.data_file, self.raw)

    def sigma_total(self, model=None):
        """√diag(C) in data units (linear space, D = diag(model or y))."""
        return np.sqrt(np.diag(self.covariance('linear', model).dense()))

    def covariance(self, space='log', model=None):
        """The dataset covariance as ``LowRank`` (hand-off §2.4). ``space``
        'log' (of ln y; needs y > 0) or 'linear' (of y, D = diag(``model``),
        the measured y when no model is given; D'Agostini 1994 recommends
        the model)."""
        y = self.y if model is None else np.asarray(model, float)
        if y is None:
            raise ValueError('no y in the file: give the model curve')
        yd = self.y if self.y is not None else y
        if space == 'log':
            A = (self.sigma_meas / yd) ** 2
        elif space == 'linear':
            A = self.sigma_meas ** 2
        else:
            raise ValueError("space %r: 'log' or 'linear'" % space)
        Us, dense = [], None
        for t in self.terms:
            if t.kind == 'dense':
                Cd = np.asarray(t.cov, float)
                if space == 'log':
                    Cd = Cd / np.outer(yd, yd)
                dense = Cd if dense is None else dense + Cd
                continue
            U = np.asarray(t.weights, float) @ t.factor()
            if t.kind == 'multiplicative' and space == 'linear':
                U = y[:, None] * U
            elif t.kind == 'additive' and space == 'log':
                U = U / yd[:, None]
            Us.append(U)
        U = np.hstack(Us) if Us else np.zeros((self.n, 0))
        return LowRank(A, U, dense)


def _worst(a, b):
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.abs(a - b) / np.abs(b)
    return float(np.nanmax(r)) if r.size else 0.0


def problems(d):
    """What XModFit's loader refuses (hand-off §2.3), as messages; empty
    when the file is fine. ``d``: the parsed JSON dictionary."""
    out = []
    if d.get('format') != FORMAT:
        out.append('format is %r, not %r' % (d.get('format'), FORMAT))
    if d.get('version') != VERSION:
        out.append('version %r: only %d is understood' % (d.get('version'), VERSION))
    try:
        x = np.asarray(d['x'], float)
        sm = np.asarray(d['sigma_meas'], float)
    except (KeyError, TypeError, ValueError) as e:
        return out + ['x or sigma_meas missing or not numbers (%s)' % e]
    n = len(x)
    if x.ndim != 1 or not np.all(np.isfinite(x)):
        out.append('x not finite')
    if sm.shape != (n,):
        out.append('sigma_meas has %d values for %d points' % (sm.size, n))
    elif not (np.all(np.isfinite(sm)) and np.all(sm > 0)):
        out.append('sigma_meas not finite and > 0 everywhere')
    if 'y' in d and d['y'] is not None:
        y = np.asarray(d['y'], float)
        if y.shape != (n,):
            out.append('y has %d values for %d points' % (y.size, n))
    names = set()
    for t in d.get('terms', []) or []:
        nm = t.get('name')
        if nm in names:
            out.append('two terms are called %r' % nm)
        names.add(nm)
        kind = t.get('kind')
        if kind not in KINDS:
            out.append('term %r: kind %r unknown' % (nm, kind))
            continue
        try:
            C = np.asarray(t['cov'], float)
        except (KeyError, TypeError, ValueError):
            out.append('term %r: cov missing' % nm)
            continue
        if kind == 'dense':
            k = n
        else:
            try:
                W = np.asarray(t['weights'], float)
            except (KeyError, TypeError, ValueError):
                out.append('term %r: weights missing' % nm)
                continue
            if W.ndim != 2 or W.shape[0] != n:
                out.append('term %r: weights are %s, not %d × K' % (nm, W.shape, n))
                continue
            if not np.all(np.isfinite(W)):
                out.append('term %r: weights not finite' % nm)
            k = W.shape[1]
            lab = t.get('labels')
            if lab is not None and len(lab) != k:
                out.append('term %r: %d labels for K = %d' % (nm, len(lab), k))
        if C.shape != (k, k):
            out.append('term %r: cov is %s, not %d × %d' % (nm, C.shape, k, k))
            continue
        if not np.all(np.isfinite(C)):
            out.append('term %r: cov not finite' % nm)
            continue
        mx = np.max(np.abs(C)) if C.size else 0.0
        if C.size and np.max(np.abs(C - C.T)) > 1e-12 * mx:
            out.append('term %r: cov not symmetric' % nm)
        ev = np.linalg.eigvalsh(0.5 * (C + C.T)) if C.size else np.zeros(0)
        if ev.size and ev.min() < -1e-10 * max(ev.max(), 0.0):
            out.append('term %r: cov not positive semi-definite (smallest eigenvalue %.3g)' % (nm, ev.min()))
    return out


def load(source):
    """A ``Sidecar`` from a path or a parsed dictionary; raises ValueError
    with XModFit's reasons when the file would be refused."""
    if isinstance(source, dict):
        d = source
    else:
        with open(source) as f:
            d = json.load(f)
    p = problems(d)
    if p:
        raise ValueError('covariance file refused: ' + '; '.join(p))
    terms = []
    for t in d.get('terms', []) or []:
        W = None if t['kind'] == 'dense' else np.asarray(t['weights'], float)
        terms.append(Term(t['name'], t['kind'], t.get('scope', 'dataset'), t.get('labels'), W,
                          np.asarray(t['cov'], float), t.get('provenance', {})))
    y = d.get('y')
    return Sidecar(np.asarray(d['x'], float), None if y is None else np.asarray(y, float),
                   np.asarray(d['sigma_meas'], float), terms, d.get('data_file'), d)


# ---- the covariance in Woodbury form -----------------------------------------------------------

class LowRank:
    """C = diag(A) + U Uᵀ (+ a dense N × N part, if a 'dense' term is
    present: then plain Cholesky). ``solve``, ``chi2``, ``logdet``,
    ``dense``; ``whiten(r)`` gives e with |e|² = rᵀ C⁻¹ r."""

    def __init__(self, A, U, dense=None):
        self.A = np.asarray(A, float)
        self.U = np.asarray(U, float).reshape(len(self.A), -1)
        self.extra = dense
        if dense is None:
            Ai_U = self.U / self.A[:, None]
            self._M = np.eye(self.U.shape[1]) + self.U.T @ Ai_U
            self._cM = np.linalg.cholesky(self._M)
            self._AiU = Ai_U
        else:
            self._cC = np.linalg.cholesky(self.dense())

    def dense(self):
        C = np.diag(self.A) + self.U @ self.U.T
        if self.extra is not None:
            C = C + self.extra
        return C

    def solve(self, r):
        r = np.asarray(r, float)
        if self.extra is not None:
            from scipy.linalg import cho_solve
            return cho_solve((self._cC, True), r)
        Air = r / (self.A if r.ndim == 1 else self.A[:, None])
        t = self.U.T @ Air
        z = np.linalg.solve(self._cM.T, np.linalg.solve(self._cM, t))
        return Air - self._AiU @ z

    def chi2(self, r):
        r = np.asarray(r, float)
        return float(r @ self.solve(r))

    def logdet(self):
        if self.extra is not None:
            return float(2 * np.sum(np.log(np.diag(self._cC))))
        return float(np.sum(np.log(self.A)) + 2 * np.sum(np.log(np.diag(self._cM))))

    def whiten(self, r):
        """e = L_C⁻¹ r (Cholesky of C, dense): |e|² = χ²; for small N."""
        Lc = np.linalg.cholesky(self.dense())
        return np.linalg.solve(Lc, np.asarray(r, float))


def chi2(sc, model, space='log', free_scale=False):
    """GLS χ² = rᵀ C⁻¹ r of a model curve (N values at ``sc.x``) against the
    file's y (r = ln y − ln m, or y − m with D = diag(m)). ``free_scale``:
    minimised over an overall factor (closed form in log space; returns
    (χ², ln factor) then)."""
    m = np.asarray(model, float)
    C = sc.covariance(space, m if space == 'linear' else None)
    if space == 'log':
        r = np.log(sc.y) - np.log(m)
        if not free_scale:
            return C.chi2(r)
        one = np.ones_like(r)
        Ci1 = C.solve(one)
        s = float(r @ Ci1 / (one @ Ci1))
        return C.chi2(r - s), s
    if free_scale:
        raise ValueError('free_scale in linear space: use fit()')
    return C.chi2(sc.y - m)


# ---- fitting -----------------------------------------------------------------------------------

@dataclass
class FitResult:
    """``params`` and ``errors`` (1σ from the Jacobian, not rescaled by χ²),
    ``cov`` (of ``params``), ``chi2`` (GLS χ², penalty included), ``dof``
    (N − parameters − free scale), ``scale`` (ln of the overall factor,
    0 if fixed), ``shifts`` (the fitted log scale shift of each region,
    K, per multiplicative term; φ = L η), ``eta`` (their whitened values,
    each ~ N(0, 1) a priori: large ones show a scan whose level the
    structural model disputes), ``mode``, ``success``, ``message``, ``nfev``."""
    params: np.ndarray
    errors: np.ndarray
    cov: np.ndarray
    chi2: float
    dof: int
    scale: float
    scale_error: float
    shifts: dict
    eta: np.ndarray
    mode: str
    space: str
    success: bool
    message: str
    nfev: int


def fit(sc, model, p0, space='log', mode='covariance', free_scale=True, yerr=None, mask=None, bounds=None,
        **kw):
    """Fit ``model(x, *p)`` to the file's y.

    ``mode`` 'covariance' (default): with the full covariance, as nuisance
    scale shifts φ = L η of every multiplicative term (and offsets of every
    additive term) penalised by |η|²; in log space this gives the GLS χ²
    with C = diag((σ_meas/y)²) + W Σ Wᵀ exactly, in linear space the model
    is m·exp(Wφ) against σ_meas (C with D = diag(model) to first order,
    D'Agostini's recommendation). 'diagonal': independent errors ``yerr``
    (default: √diag C, the hand-off's corrected column; pass the legacy
    column to see the legacy fit). ``free_scale``: an overall factor (the
    normalisation is not in the covariance, contract §2.6). ``mask``: the
    points to fit (rows of x, y, σ_meas and W). ``bounds``: (lo, hi) for
    ``p``. Further keywords go to ``scipy.optimize.least_squares``."""
    from scipy.optimize import least_squares
    if mask is not None:
        sc = sc.take(mask)
    if sc.y is None:
        raise ValueError('the file has no y: give the data column')
    x, y, sm = sc.x, sc.y, sc.sigma_meas
    p0 = np.atleast_1d(np.asarray(p0, float))
    npar = len(p0)
    if space not in ('log', 'linear'):
        raise ValueError("space %r: 'log' or 'linear'" % space)
    if mode not in ('covariance', 'diagonal'):
        raise ValueError("mode %r: 'covariance' or 'diagonal'" % mode)
    if space == 'log' and np.any(y <= 0):
        raise ValueError('log space needs y > 0 at every fitted point (mask the others)')
    blocks = []                    # (term, U (N × r) in its own units, L)
    if mode == 'covariance':
        for t in sc.terms:
            if t.kind == 'dense':
                raise ValueError("term %r is 'dense': use chi2() with LowRank, fit() handles low-rank terms" % t.name)
            L = t.factor()
            blocks.append((t, t.weights @ L, L))
        sig = sm / y if space == 'log' else sm
    else:
        e = np.asarray(yerr, float) if yerr is not None else (sc.sigma_total() if sc.terms else sm)
        if mask is not None and yerr is not None and len(e) != len(x):
            e = e[np.asarray(mask)] if np.asarray(mask).dtype == bool else e[np.asarray(mask, int)]
        sig = e / y if space == 'log' else e
    nr = sum(b[1].shape[1] for b in blocks)
    ns = 1 if free_scale else 0

    def split(theta):
        return theta[:npar], (theta[npar] if ns else 0.0), theta[npar + ns:]

    def residuals(theta):
        p, s, eta = split(theta)
        m = np.asarray(model(x, *p), float)
        mult = np.zeros_like(y)
        add = np.zeros_like(y)
        k = 0
        for t, U, L in blocks:
            r = U.shape[1]
            v = U @ eta[k:k + r]
            if t.kind == 'multiplicative':
                mult = mult + v
            else:
                add = add + v
            k += r
        if space == 'log':
            with np.errstate(invalid='ignore', divide='ignore'):
                res = (np.log(y) - np.log(m) - s - mult - add / y) / sig
        else:
            res = (y - m * np.exp(s + mult) - add) / sig
        return np.concatenate([res, eta])

    th0 = np.concatenate([p0, np.zeros(ns), np.zeros(nr)])
    lsq = dict(x_scale='jac')
    lsq.update(kw)
    if bounds is not None:
        lo = np.concatenate([np.broadcast_to(bounds[0], (npar,)), np.full(ns + nr, -np.inf)])
        hi = np.concatenate([np.broadcast_to(bounds[1], (npar,)), np.full(ns + nr, np.inf)])
        out = least_squares(residuals, th0, bounds=(lo, hi), **lsq)
    else:
        out = least_squares(residuals, th0, **lsq)
    J = out.jac
    try:
        cov_all = np.linalg.inv(J.T @ J)
    except np.linalg.LinAlgError:
        cov_all = np.linalg.pinv(J.T @ J)
    p, s, eta = split(out.x)
    shifts, k = {}, 0
    for t, U, L in blocks:
        r = U.shape[1]
        shifts[t.name] = L @ eta[k:k + r]
        k += r
    chi = float(np.sum(out.fun ** 2))
    return FitResult(p.copy(), np.sqrt(np.diag(cov_all)[:npar]), cov_all[:npar, :npar], chi, len(x) - npar - ns,
                     float(s), float(math.sqrt(cov_all[npar, npar])) if ns else 0.0, shifts, eta.copy(), mode, space,
                     bool(out.success), str(out.message), int(out.nfev))
