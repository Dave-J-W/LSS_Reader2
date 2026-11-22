"""Stitched reflectivity with its covariance, and the xmodfit sidecar files.

The contract is ``docs/handoff/19-lss-reader-covariance-contract.md``
(schema version 1; XModFit reads it): beside every ``<name>_ref.txt`` /
``<name>_rrf.txt`` a ``<name>_ref.cov.json`` / ``<name>_rrf.cov.json``
with the counting-only error ``sigma_meas`` (N), the region weights W
(N × K, rows sum to 1) and the covariance Σ (K × K, natural-log units,
anchor row and column zero) of the scans' log scale errors. The dataset
covariance is then C_log = diag((σ_meas/y)²) + W Σ Wᵀ. Why and how a fit
uses it: ``docs/reports/downstream_covariance.md``.

What is here:

* ``CovData``: x, y, σ_meas, W, Σ (and the error column written beside
  them) with the transforms a reduction applies, point for point
  (``take``/``sort``/``cut``, ``scale`` (normalisation), ``divide``
  (Fresnel), ``shift_x`` (Q_z offset), ``average`` (binning), ``concat``
  (two stitched sets joined by a further factor)); W and Σ follow each
  of them exactly (Σ is in log units, so scaling never changes it).
* ``legacy_chain``: the reader's legacy patch (``reflectivity.patch``)
  replayed with W and σ_meas carried beside it (hand-off §3.1, §3.3) and
  Σ from the legacy factors by the §3.4 recursion. Its data are the
  legacy chain's, bit for bit, so the legacy text files stay as they are.
* ``corrected_chain``: the hand-off's corrected chain (§3.2: each factor
  fitted against counting errors, absolute σ, inflate-only χ²; the same
  merge as the legacy one).
* ``from_stitched``: a ``patching.Stitched`` (the joint fit's output).
* ``finish``: the window's normalisation, sort, Q_z offset and Fresnel
  division (``reflectivity.finish``) applied to a ``CovData``.
* ``sidecar_dict``/``write_sidecar``/``save``: the files.

The reading side (validation as XModFit does it, χ², a reference GLS
fitter) is ``lss_core.gls``.
"""
import json
import math
import os
import subprocess
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.interpolate import interp1d

from . import stitching
from . import uncertainty as unc

FORMAT = 'xmodfit-covariance'
VERSION = 1
TEXT_FMT = '%.4e\t%.4e\t%.4e'      # the window's (and reflectivity.save's) format, hand-off T9


def producer_version():
    """`git describe` of this checkout, or 'unknown' (informational only)."""
    try:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.run(['git', 'describe', '--always', '--dirty'], cwd=here, capture_output=True,
                             text=True, timeout=5)
        return out.stdout.strip() or 'unknown'
    except Exception:
        return 'unknown'


# ---- the data with its covariance ------------------------------------------------------------

@dataclass
class CovData:
    """N stitched points and their covariance (hand-off 19 §2.2, §3).

    ``x``, ``y``: the columns of the data file; ``sigma_meas``: counting-only
    error (same units as y); ``W``: N × K weights of each point on the scans'
    log scales; ``Sigma``: K × K covariance of those log scales; ``labels``:
    K names ('S<scan>'); ``yerr``: the error column written to the data file
    (None: √ of the covariance diagonal, ``sigma_total``); ``provenance``:
    free-form, written into the sidecar."""
    x: np.ndarray
    y: np.ndarray
    sigma_meas: np.ndarray
    W: np.ndarray
    Sigma: np.ndarray
    labels: list
    yerr: np.ndarray = None
    provenance: dict = field(default_factory=dict)

    def __post_init__(self):
        self.x = np.asarray(self.x, float)
        self.y = np.asarray(self.y, float)
        self.sigma_meas = np.asarray(self.sigma_meas, float)
        self.W = np.atleast_2d(np.asarray(self.W, float))
        self.Sigma = np.atleast_2d(np.asarray(self.Sigma, float))
        if self.yerr is not None:
            self.yerr = np.asarray(self.yerr, float)
        self.labels = [str(v) for v in self.labels]
        n, k = len(self.x), len(self.labels)
        if not (len(self.y) == len(self.sigma_meas) == n):
            raise ValueError('x, y, sigma_meas lengths %d, %d, %d differ' % (n, len(self.y), len(self.sigma_meas)))
        if self.W.shape != (n, k) or self.Sigma.shape != (k, k):
            raise ValueError('W %s and Sigma %s do not fit N = %d, K = %d' % (self.W.shape, self.Sigma.shape, n, k))
        if self.yerr is not None and len(self.yerr) != n:
            raise ValueError('yerr has %d values for %d points' % (len(self.yerr), n))

    @property
    def n(self):
        return len(self.x)

    @property
    def k(self):
        return len(self.labels)

    def sigma_total(self):
        """√(σ_meas² + y²·W_i Σ W_iᵀ): the covariance's diagonal in data units
        (hand-off §3.4, the corrected error column)."""
        return unc.total_sigma(self.y, self.sigma_meas, self.W, self.Sigma)

    def error_column(self):
        return self.sigma_total() if self.yerr is None else self.yerr

    def covariance(self, space='log', model=None):
        """N × N covariance (``uncertainty.stitched_covariance``)."""
        return unc.stitched_covariance(self.y, self.sigma_meas, self.W, self.Sigma, space, model)

    def array(self):
        """(N, 3) x, y, error column: what the data file holds."""
        return np.column_stack([self.x, self.y, self.error_column()])

    # -- transforms: each returns a new CovData, point for point --------------------------------
    def take(self, idx):
        """Rows ``idx`` (indices or a boolean mask), in that order: sorting,
        dropping points, cutting a Q range. Σ and the labels stay (a scan
        whose points are all gone keeps a zero column of W: harmless)."""
        idx = np.asarray(idx)
        if idx.dtype == bool:
            idx = np.flatnonzero(idx)
        return replace(self, x=self.x[idx], y=self.y[idx], sigma_meas=self.sigma_meas[idx], W=self.W[idx],
                       yerr=None if self.yerr is None else self.yerr[idx], provenance=dict(self.provenance))

    def sort(self):
        return self.take(np.argsort(self.x))

    def cut(self, xmin=-np.inf, xmax=np.inf):
        return self.take((self.x >= xmin) & (self.x <= xmax))

    def scale(self, c):
        """Divide y and its errors by ``c`` (a number or N values: a
        normalisation, a Fresnel curve). In log units nothing else moves."""
        c = np.broadcast_to(np.asarray(c, float), self.y.shape)
        return replace(self, y=self.y / c, sigma_meas=self.sigma_meas / c,
                       yerr=None if self.yerr is None else self.yerr / c, provenance=dict(self.provenance))

    divide = scale

    def shift_x(self, dx):
        return replace(self, x=self.x + dx, provenance=dict(self.provenance))

    def average(self, groups, weights='inverse-variance'):
        """Average groups of points (binning, merging repeats). ``groups``: a
        list of index lists, one per output point. Within a group with
        normalised weights w_j: ȳ = Σ w_j y_j, σ_meas = √(Σ w_j² σ_j²), and
        the W row is the linearised one, Σ_j (w_j y_j/ȳ) W_j (the share of
        each point in ȳ: exact to first order in the log scales; it equals
        Σ w_j W_j when the y_j agree). ``weights``: 'inverse-variance' (1/σ_meas²)
        or 'equal'. x is the weighted mean; the error column, if set, is
        dropped (recomputed as σ_total)."""
        xs, ys, ss, Ws = [], [], [], []
        for g in groups:
            g = np.asarray(g, int)
            if weights == 'equal':
                w = np.ones(len(g))
            elif weights == 'inverse-variance':
                w = 1.0 / self.sigma_meas[g] ** 2
            else:
                raise ValueError("weights %r: 'inverse-variance' or 'equal'" % weights)
            w = w / w.sum()
            yb = float(np.sum(w * self.y[g]))
            xs.append(float(np.sum(w * self.x[g])))
            ys.append(yb)
            ss.append(float(np.sqrt(np.sum(w ** 2 * self.sigma_meas[g] ** 2))))
            share = w * self.y[g] / yb if yb != 0 else w
            Ws.append(share @ self.W[g])
        return replace(self, x=np.array(xs), y=np.array(ys), sigma_meas=np.array(ss), W=np.array(Ws), yerr=None,
                       provenance=dict(self.provenance))

    def concat(self, other, link_error, link_row=None):
        """Join two stitched sets into one: ``other`` (scaled onto this
        set's level by a factor whose log error is ``link_error``, fitted
        against this set's scans with weights ``link_row`` (K of self; None:
        the last scan, a one-hot chain step). Σ of the result:
        [[Σ₁, Σ₁ a 1ᵀ], [1 aᵀ Σ₁, Σ₂ + (aᵀ Σ₁ a + e²) 1 1ᵀ]], with ``other``'s
        own anchor now shifted by the link (its W columns keep their rows).
        Labels must not repeat (two reductions of the same scan are not
        independent and cannot be joined this way)."""
        dup = set(self.labels) & set(other.labels)
        if dup:
            raise ValueError('labels %s appear in both sets: they share scans, so their errors are not independent'
                             % sorted(dup))
        k1, k2 = self.k, other.k
        a = np.zeros(k1)
        if link_row is None:
            a[-1] = 1.0
        else:
            a = np.asarray(link_row, float)
        S1, S2 = self.Sigma, other.Sigma
        one = np.ones(k2)
        S = np.zeros((k1 + k2, k1 + k2))
        S[:k1, :k1] = S1
        S[:k1, k1:] = np.outer(S1 @ a, one)
        S[k1:, :k1] = S[:k1, k1:].T
        S[k1:, k1:] = S2 + (a @ S1 @ a + float(link_error) ** 2) * np.outer(one, one)
        W = np.zeros((self.n + other.n, k1 + k2))
        W[:self.n, :k1] = self.W
        W[self.n:, k1:] = other.W
        ye = None
        if self.yerr is not None and other.yerr is not None:
            ye = np.concatenate([self.yerr, other.yerr])
        return CovData(np.concatenate([self.x, other.x]), np.concatenate([self.y, other.y]),
                       np.concatenate([self.sigma_meas, other.sigma_meas]), W, S, self.labels + other.labels, ye,
                       {'joined': [self.provenance, other.provenance], 'link_error': float(link_error)})


def from_stitched(st, labels=None, provenance=None):
    """A ``patching.Stitched`` (joint fit or any other) as ``CovData``; the
    error column is √ of the covariance diagonal."""
    k = np.asarray(st.Sigma).shape[0]
    labels = labels or ['S%d' % (m + 1) for m in range(k)]
    return CovData(st.q, st.y, st.sigma_meas, st.W, st.Sigma, labels, None, dict(provenance or {}))


def joint_covdata(per_scan, order, drops=None, factors=None, qc=0.0217, qoff=0.0, merge='coincident', **kw):
    """The joint-fit patch (``patching.chain``, its defaults unless ``kw``)
    of the scans in ``order`` as ``CovData``: every point as measured,
    scaled by its scan's factor, averaged only where Q_z coincide
    (``merge``); error column √diag C. ``drops`` as for the legacy patch,
    where they name points of single scans: indices ≥ 0 at join j drop
    points of scan order[j+1], negative ones at join 0 points of scan
    order[0]; negative ones at later joins name points of the legacy
    merged curve and are refused. ``factors`` (known ratios) are refused:
    the joint fit takes the foils as a prior instead (``patching.chain
    (prior=...)``)."""
    from . import patching
    if factors:
        raise ValueError('known factors are a legacy-patch option; the joint fit takes the foils as a prior')
    data = {k: np.atleast_2d(np.array(per_scan[k], float)) for k in order}
    for j in sorted(drops or {}):
        for action in _actions(drops, j):
            for d in sorted(action, key=abs, reverse=True):
                if d >= 0:
                    data[order[j + 1]] = np.delete(data[order[j + 1]], d, axis=0)
                elif j == 0:
                    data[order[0]] = np.delete(data[order[0]], d, axis=0)
                else:
                    raise ValueError('drop %d at join %d names a point of the merged legacy curve; give the joint '
                                     'patch drops of single scans' % (d, j))
    scans = [patching.Scan(data[k][:, 0], data[k][:, 1], data[k][:, 2], label='S%s' % k) for k in order]
    kw.setdefault('qc', qc)
    kw.setdefault('qoff', qoff)
    res = patching.chain(scans, **kw)
    st = res.stitch(scans, merge=merge)
    prov = dict(method='joint (%s)' % res.method, scans=[int(k) if isinstance(k, (int, np.integer)) else str(k)
                                                         for k in order],
                fac=[float(v) for v in res.factors], phi=[float(v) for v in res.phi],
                joins=[dict(delta=j.delta, err=j.err, err_counting=j.err_counting, chi2_dof=j.chi2 / max(j.dof, 1),
                            dof=j.dof, order=j.order, n_ext=j.n_ext, space=j.space, likelihood=j.likelihood,
                            prior=j.prior, prior_used=j.prior_used, z=j.z, why=j.why, flags=list(j.flags))
                       for j in res.joins], merge=merge)
    return from_stitched(st, ['S%s' % k for k in order], prov)


# ---- the chains: legacy (replayed, tracked) and corrected (hand-off §3.2) --------------------

@dataclass
class JoinRecord:
    """One join of a tracked chain (the sidecar's provenance, hand-off §2.2):
    the scan joined, the factor used and its error δ (absolute; δ/fac is the
    log error that enters Σ), the counting error and χ²_red of the ratio fit,
    a_m (the mean W row of the existing points in the overlap), the legacy
    fit's own factor and error, where the factor came from ('fit' or
    'known'), and the overlap points where the error interpolation fell
    back to linear (§3.1)."""
    scan: object
    fac: float
    facerr: float
    facerr_counting: float
    chi2_red: float
    a: np.ndarray
    fac_legacy: float
    facerr_legacy: float
    source: str = 'fit'
    n_overlap: int = 0
    linear_fallback: list = field(default_factory=list)


@dataclass
class TrackedChain:
    """A patched reflectivity with what the covariance needs.

    ``data``: (N, 3) Qz, R, error, before normalisation: for the legacy
    chain exactly ``reflectivity.patch``'s first three columns (error: the
    legacy total), for the corrected chain the corrected values (error:
    σ_meas); ``sigma_meas``, ``W`` (N × K), ``Sigma`` (K × K), ``labels``,
    ``joins`` (``JoinRecord``), ``method`` ('legacy' or 'corrected'),
    ``order`` (scan numbers in patch order)."""
    data: np.ndarray
    sigma_meas: np.ndarray
    W: np.ndarray
    Sigma: np.ndarray
    labels: list
    joins: list
    method: str
    order: list

    def covdata(self, error_column='legacy'):
        """As ``CovData``: ``error_column`` 'legacy' keeps data[:, 2] as the
        file's error column (the legacy files, byte-identical); 'total'
        writes √diag(C) (the hand-off's corrected column)."""
        ye = self.data[:, 2].copy() if error_column == 'legacy' else None
        if error_column not in ('legacy', 'total'):
            raise ValueError("error_column %r: 'legacy' or 'total'" % error_column)
        return CovData(self.data[:, 0], self.data[:, 1], self.sigma_meas, self.W, self.Sigma, self.labels, ye,
                       self.provenance())

    def provenance(self):
        K = len(self.labels)
        fac, ferr, fcnt, chi, fl, fel = [1.0], [0.0], [0.0], [None], [1.0], [0.0]
        a = [[0.0] * K]
        for j in self.joins:
            fac.append(j.fac)
            ferr.append(j.facerr)
            fcnt.append(j.facerr_counting)
            chi.append(j.chi2_red)
            a.append([float(v) for v in j.a])
            fl.append(j.fac_legacy)
            fel.append(j.facerr_legacy)
        p = dict(fac=fac, facerr=ferr, facerr_counting=fcnt, chi2_red=chi, a=a, fac_legacy=fl, facerr_legacy=fel,
                 method=self.method, scans=[int(s) if isinstance(s, (int, np.integer)) else str(s) for s in self.order],
                 factor_source=['anchor'] + [j.source for j in self.joins])
        fb = {self.labels[m + 1]: j.linear_fallback for m, j in enumerate(self.joins) if j.linear_fallback}
        if fb:
            p['linear_interpolation_fallback'] = fb
        if self.method == 'legacy':
            p['sigma_from'] = ('legacy factors; their error recomputed from counting errors, inflate-only '
                               '(hand-off §3.2 rule applied to the legacy weighted mean)')
        return p


def _cubic(x, y):
    return interp1d(x, y, kind='cubic')


def _interp_error(x2, s2, x):
    """σ of the new scan at the existing points: cubic, as the legacy code
    interpolates its error, linear where the cubic gives ≤ 0 or not finite
    (hand-off §3.1). Returns (values, indices where linear was used)."""
    v = _cubic(x2, s2)(x)
    bad = ~np.isfinite(v) | (v <= 0)
    if bad.any():
        v = np.where(bad, np.interp(x, x2, s2), v)
    return v, [int(i) for i in np.flatnonzero(bad)]


def _overlaps(x1, x2):
    overlap1 = np.where(x1 >= x2[0])[0]
    overlap2 = np.where(x2 <= x1[-1])[0]
    if len(overlap1) == 0 or len(overlap2) == 0:
        raise ValueError('the scans do not overlap in Qz')
    return overlap1, overlap2


def _ratio_counting(x1, y1, s1, x2, y2, s2, overlap1, fac=None, weights=None):
    """The hand-off §3.2 ratio fit against counting errors. r_i = y1_i /
    spline2(x_i) at the existing overlap points, r_err from σ_meas of both
    sides. With ``fac`` None: the weighted mean (absolute σ) and its error
    (Σ w)^(-1/2); with ``fac`` and ``weights`` given (the legacy fit), the
    counting variance of that weighted mean, Σ w² r_err² / (Σ w)². Then
    χ²_red = Σ ((r − fac)/r_err)² / (n − 1) (1 if n = 1) and facerr = counting
    error × max(1, √χ²_red). Returns (fac, facerr, facerr_counting, χ²_red,
    linear-fallback indices)."""
    x = x1[overlap1]
    f = _cubic(x2, y2)(x)
    fe, fb = _interp_error(x2, s2, x)
    r = y1[overlap1] / f
    rerr = r * np.sqrt((s1[overlap1] / y1[overlap1]) ** 2 + (fe / f) ** 2)
    if fac is None:
        w = 1.0 / rerr ** 2
        fac = float(np.sum(w * r) / np.sum(w))
        e_c = float(np.sum(w) ** -0.5)
    else:
        w = np.asarray(weights, float)
        e_c = float(np.sqrt(np.sum(w ** 2 * rerr ** 2)) / np.sum(w))
    n = len(r)
    chi2_red = float(np.sum(((r - fac) / rerr) ** 2) / (n - 1)) if n >= 2 else 1.0
    return fac, e_c * max(1.0, math.sqrt(chi2_red)), e_c, chi2_red, fb


def _legacy_weights(d1, d2, overlap1):
    """The weights 1/r_err² the legacy curve_fit uses (total errors, cubic)."""
    x = d1[overlap1, 0]
    f = _cubic(d2[:, 0], d2[:, 1])(x)
    fe = _cubic(d2[:, 0], d2[:, 2])(x)
    r = d1[overlap1, 1] / f
    rerr = r * np.sqrt((d1[overlap1, 2] / d1[overlap1, 1]) ** 2 + (fe / f) ** 2)
    return 1.0 / rerr ** 2


def _merge_rows(x1, s1, W1, x2, s2, m, overlap1, overlap2):
    """σ_meas and W of the merged points, row for row as stitching.join
    builds the data (hand-off §3.1, §3.3): the existing points below the
    overlap; the averaged overlap points (√(σ₁² + σ₂(x)²)/2, ½W₁ + ½e_m); the
    rest of whichever reaches further. ``s2`` is already scaled by fac."""
    K = W1.shape[1]
    e = np.zeros(K)
    e[m] = 1.0
    o0, o1 = overlap1[0], overlap1[-1]
    s3, fb = _interp_error(x2, s2, x1[overlap1])
    rng = np.arange(o0, o1 + 1)
    s_avg = np.sqrt(s1[rng] ** 2 + s3[rng - o0] ** 2) / 2.0
    W_avg = 0.5 * W1[rng] + 0.5 * e
    if x1[-1] >= x2[-1]:
        s_last, W_last = s1[o1 + 1:], W1[o1 + 1:]
    else:
        s_last = s2[overlap2[-1] + 1:]
        W_last = np.tile(e, (len(s_last), 1))
    return (np.concatenate([s1[:o0], s_avg, s_last]), np.vstack([W1[:o0], W_avg, W_last]), fb)


def _drop_rows(arrs, drops):
    """Apply one Drop action (reflectivity.apply_drops) to parallel arrays:
    ``arrs`` = (existing list, new list), each a list of arrays row-aligned."""
    old, new = list(arrs[0]), list(arrs[1])
    for d in sorted(drops, key=abs, reverse=True):
        if d >= 0:
            new = [np.delete(a, d, axis=0) for a in new]
        else:
            old = [np.delete(a, d, axis=0) for a in old]
    return old, new


def _actions(drops, j):
    acts = (drops or {}).get(j)
    if not acts:
        return []
    if not isinstance(acts[0], (list, tuple)):
        acts = [acts]
    return acts


def _chain(per_scan, order, drops, factors, method):
    if method not in ('legacy', 'corrected'):
        raise ValueError("method %r: 'legacy' or 'corrected'" % method)
    drops, factors = drops or {}, factors or {}
    K = len(order)
    labels = ['S%s' % k for k in order]
    first = np.atleast_2d(np.array(per_scan[order[0]], dtype=float))
    data = first.copy()                                  # legacy: as reflectivity.patch (all columns)
    sm = first[:, 2].copy()                              # counting-only error of the merged data
    W = np.zeros((len(first), K))
    W[:, 0] = 1.0
    joins, a_rows, deltas = [], [], []
    for j, key in enumerate(order[1:]):
        m = j + 1
        new = np.atleast_2d(np.array(per_scan[key], dtype=float))
        sm2 = new[:, 2].copy()
        for action in _actions(drops, j):
            (data, sm, W), (new, sm2) = _drop_rows(((data, sm, W), (new, sm2)), action)
        d1, d2 = stitching._three_columns(data.copy()), stitching._three_columns(new.copy())
        x1, x2 = d1[:, 0], d2[:, 0]
        overlap1, overlap2 = _overlaps(x1, x2)
        a = W[overlap1].mean(axis=0)
        given = factors.get(j)
        if method == 'legacy':
            fac_l, ferr_l = stitching._fit_factor(x1, d1[:, 1], d1[:, 2], x2, d2[:, 1], d2[:, 2], overlap1)
            if given is None:
                fac, ferr, fcnt, chi, fb = _ratio_counting(x1, d1[:, 1], sm, x2, d2[:, 1], sm2, overlap1, fac=fac_l,
                                                           weights=_legacy_weights(d1, d2, overlap1))
            merged = stitching.join(d1.copy(), d2.copy(), mtype='merge', factor=given)
        else:
            fac_l, ferr_l = math.nan, math.nan                # filled from the legacy chain (corrected_chain)
            if given is None:
                fac, ferr, fcnt, chi, fb = _ratio_counting(x1, d1[:, 1], sm, x2, d2[:, 1], sm2, overlap1)
        source = 'fit'
        if given is not None:
            # a known ratio (the window's "Known ratio"): k = (level of the previous scan) × foil step,
            # so the step is taken from the previous scan in order, its log error err/k
            fac, ferr, fcnt, chi, fb, source = float(given[0]), float(given[1]), math.nan, None, [], 'known'
            a = np.zeros(K)
            a[m - 1] = 1.0
        if method == 'corrected':
            y2 = d2[:, 1] * fac
            s2s = sm2 * fac
            # the merge of stitching.join, on the corrected values (the counting error is carried)
            o0, o1 = overlap1[0], overlap1[-1]
            f2 = _cubic(x2, y2)
            y3 = f2(x1[overlap1])
            rng = np.arange(o0, o1 + 1)
            y_avg = (d1[rng, 1] + y3[rng - o0]) / 2.0
            if x1[-1] >= x2[-1]:
                x_last, y_last = x1[o1 + 1:], d1[o1 + 1:, 1]
            else:
                x_last, y_last = x2[overlap2[-1] + 1:], y2[overlap2[-1] + 1:]
            xm = np.concatenate([x1[:o0], x1[rng], x_last])
            ym = np.concatenate([d1[:o0, 1], y_avg, y_last])
        sm, W, fb2 = _merge_rows(x1, sm, W, x2, sm2 * fac, m, overlap1, overlap2)
        if method == 'corrected':
            data = np.column_stack([xm, ym, sm])
        else:
            data = merged
        joins.append(JoinRecord(key, fac, ferr, fcnt, chi, a, float(fac_l), float(ferr_l), source,
                                int(len(overlap1)), sorted(set(fb) | set(fb2))))
        a_rows.append(a)
        deltas.append(ferr / fac)
    Sigma = unc.chain_covariance(a_rows, deltas) if K > 1 else np.zeros((1, 1))
    out = np.array(data[:, :3], dtype=float)
    if method == 'corrected':
        out[:, 2] = sm
    return TrackedChain(out, sm, W, Sigma, labels, joins, method, list(order))


def legacy_chain(per_scan, order, drops=None, factors=None):
    """The legacy patch (``reflectivity.patch``: same inputs, same drops and
    known factors) with W, σ_meas and Σ carried beside it. ``data`` equals
    ``reflectivity.patch(...)[:, :3]`` bit for bit (tests). Σ uses the
    legacy factors with their error recomputed from counting errors and
    inflated when the overlap scatters (χ²_red > 1): the legacy estimator's
    own spread, not its ``absolute_sigma=False`` error, which can fall below
    counting noise (hand-off §3.2; ``docs/OUTPUT_DECISIONS.md``). The legacy
    error is in the provenance (``facerr_legacy``)."""
    return _chain(per_scan, order, drops, factors, 'legacy')


def corrected_chain(per_scan, order, drops=None, factors=None):
    """The hand-off's corrected chain (§3.1–3.4): the same merge, each
    factor the weighted mean of the overlap ratios against counting errors
    with absolute σ, error inflated by max(1, √χ²_red); only σ_meas is
    carried; the error column is built from the covariance at the end."""
    out = _chain(per_scan, order, drops, factors, 'corrected')
    try:
        leg = legacy_chain(per_scan, order, drops, factors)
        for j, jl in zip(out.joins, leg.joins):
            j.fac_legacy, j.facerr_legacy = jl.fac_legacy, jl.facerr_legacy
    except Exception:          # the legacy fit failed where this one did not: provenance only
        pass
    return out


# ---- the window's finishing steps ------------------------------------------------------------

def finish(cd, qc, qoff=0.0, norm_factor=None, rrf=True):
    """``reflectivity.finish`` (the window's ``updateRefPlotData``) on a
    ``CovData``: normalised to the highest point below Qc and by
    ``norm_factor``, then sorted by Qz (``ref``); and the same, in patch
    order, at Qz + ``qoff`` divided by R_F (``rrf``, None unless ``rrf``).
    x, y and the error column are ``reflectivity.finish``'s own arrays (so
    a legacy file written from them is byte-identical); σ_meas and W get
    the same normalisation, permutation and Fresnel division. Returns
    (ref, rrf)."""
    from . import reflectivity as refl
    arr = cd.array()
    ref_arr, rrf_arr = refl.finish(arr, qc, qoff, norm_factor, rrf)
    sm = cd.sigma_meas.copy()
    prov = dict(cd.provenance, qc=float(qc), qoff=float(qoff),
                norm_factor=None if norm_factor is None else float(norm_factor))
    if arr[0, 0] < qc:
        norm = np.max(arr[np.where(arr[:, 0] < qc)][:, 1])
        sm = sm / norm
        prov['norm'] = float(norm)
        i = int(np.flatnonzero((arr[:, 0] < qc) & (arr[:, 1] == norm))[0])
        prov['norm_rel_err'] = float(cd.sigma_meas[i] / norm)     # its counting error: a free overall scale
    if norm_factor is not None:
        sm = sm / norm_factor
    keep = cd.yerr is not None
    perm = np.argsort(arr[:, 0])
    ref = CovData(ref_arr[:, 0], ref_arr[:, 1], sm[perm], cd.W[perm], cd.Sigma, cd.labels,
                  ref_arr[:, 2] if keep else None, dict(prov, kind='ref'))
    out = None
    if rrf:
        f = stitching.fresnel(rrf_arr[:, 0], qc)
        out = CovData(rrf_arr[:, 0], rrf_arr[:, 1], sm / f, cd.W.copy(), cd.Sigma, cd.labels,
                      rrf_arr[:, 2] if keep else None, dict(prov, kind='rrf'))
    return ref, out


# ---- writing ----------------------------------------------------------------------------------

def _floats(a):
    return [float(v) for v in np.asarray(a, float).ravel()]


def _jsonable(v):
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, np.ndarray):
        return _jsonable(v.tolist())
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        v = float(v)
        return v if math.isfinite(v) else None
    return v


def sidecar_dict(cd, data_file=None, combined=False, meta=None):
    """The schema-v1 dictionary of ``cd`` (hand-off §2.2). One term, 'stitch',
    unless K = 1 (single scan: ``terms: []``, §3.5). ``combined``: add the
    §2.6 ``data`` block (the combined ``<name>_ref.json`` file). Arrays are
    written as full-precision floats; ``x`` and ``y`` must be the arrays of
    the data file (``finish`` gives them)."""
    problems = check(cd)
    if problems:
        raise ValueError('not writing a covariance that XModFit would refuse: ' + '; '.join(problems))
    out = {'format': FORMAT, 'version': VERSION,
           'producer': {'name': 'LSS_Reader', 'version': producer_version()}}
    if data_file:
        out['data_file'] = os.path.basename(data_file)
    out['x'] = _floats(cd.x)
    out['y'] = _floats(cd.y)
    out['sigma_meas'] = _floats(cd.sigma_meas)
    terms = []
    if cd.k > 1:
        S = 0.5 * (cd.Sigma + cd.Sigma.T)
        terms.append({'name': 'stitch', 'scope': 'dataset', 'kind': 'multiplicative', 'labels': list(cd.labels),
                      'weights': [_floats(r) for r in cd.W], 'cov': [_floats(r) for r in S],
                      'provenance': _jsonable(cd.provenance)})
    out['terms'] = terms
    out['error_column'] = ('legacy total error (factor errors folded per point; use sigma_meas with the covariance)'
                           if cd.yerr is not None else 'sqrt of the covariance diagonal (hand-off §3.4)')
    if cd.k <= 1:
        out['provenance'] = _jsonable(cd.provenance)
    if combined:
        m = {'kind': cd.provenance.get('kind')}
        m.update(meta or {})
        out['data'] = {'yerr': _floats(cd.error_column()),
                       'columns': {'Qz': 'x', 'R/RF' if cd.provenance.get('kind') == 'rrf' else 'R': 'y',
                                   'R_err': 'yerr'},
                       'meta': _jsonable(m)}
    return out


def write_sidecar(path, cd, data_file=None, combined=False, meta=None):
    d = sidecar_dict(cd, data_file, combined, meta)
    with open(path, 'w') as f:
        json.dump(d, f)
    return path


def check(cd):
    """What XModFit's loader would refuse (hand-off §2.3), as messages
    (empty: fine). ``lss_core.gls.problems`` checks a written file."""
    p = []
    if not np.all(np.isfinite(cd.x)):
        p.append('x not finite')
    if not np.all(np.isfinite(cd.y)):
        p.append('y not finite')
    if not (np.all(np.isfinite(cd.sigma_meas)) and np.all(cd.sigma_meas > 0)):
        p.append('sigma_meas not finite and > 0 everywhere')
    if not np.all(np.isfinite(cd.W)):
        p.append('weights not finite')
    if cd.k > 1:
        S = cd.Sigma
        if not np.all(np.isfinite(S)):
            p.append('cov not finite')
        else:
            mx = np.max(np.abs(S)) if S.size else 0.0
            if np.max(np.abs(S - S.T)) > 1e-12 * mx:
                p.append('cov not symmetric')
            ev = np.linalg.eigvalsh(0.5 * (S + S.T))
            if ev.size and ev.min() < -1e-10 * max(ev.max(), 0.0):
                p.append('cov not positive semi-definite (smallest eigenvalue %.3g)' % ev.min())
    return p


def write_text(path, cd):
    """The 3-column data file, as the window writes it (%.4e, tabs)."""
    np.savetxt(path, cd.array(), fmt=TEXT_FMT)
    return path


def save(name, ref, rrf=None, legacy=None, combined=False, meta=None):
    """Write ``<name>_ref.txt`` (+ ``_rrf.txt``) from ``ref``/``rrf``
    (``CovData`` as ``finish`` gives them), their sidecars
    ``<name>_ref.cov.json`` / ``_rrf.cov.json``, and with ``legacy`` =
    (ref array, rrf array or None) the legacy files ``<name>_ref_legacy.txt``
    / ``_rrf_legacy.txt`` (the hand-off's two outputs, §2.5; no sidecar).
    ``combined``: also ``<name>_ref.json`` / ``_rrf.json`` (§2.6). The
    sidecars are built from the same arrays as the text files, and a sidecar
    that would not match its file (§2.3: x and y within 1e-4) is not
    written. Returns the paths written."""
    paths = []
    for tag, cd in (('ref', ref), ('rrf', rrf)):
        if cd is None:
            continue
        txt = '%s_%s.txt' % (name, tag)
        write_text(txt, cd)
        back = np.atleast_2d(np.loadtxt(txt))
        ok = (back.shape[0] == cd.n and np.allclose(back[:, 0], cd.x, rtol=1e-4, atol=0)
              and np.allclose(back[:, 1], cd.y, rtol=1e-4, atol=0))
        paths.append(txt)
        if not ok:
            raise ValueError('%s does not match its covariance point for point; no sidecar written' % txt)
        paths.append(write_sidecar('%s_%s.cov.json' % (name, tag), cd, txt, meta=meta))
        if combined:
            paths.append(write_sidecar('%s_%s.json' % (name, tag), cd, txt, combined=True, meta=meta))
    if legacy is not None:
        lref, lrrf = legacy
        np.savetxt(name + '_ref_legacy.txt', lref, fmt=TEXT_FMT)
        paths.append(name + '_ref_legacy.txt')
        if lrrf is not None:
            np.savetxt(name + '_rrf_legacy.txt', lrrf, fmt=TEXT_FMT)
            paths.append(name + '_rrf_legacy.txt')
    return paths
