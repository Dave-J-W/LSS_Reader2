"""Uncertainty of scale factors and of data stitched with them: reusable
pieces, independent of how the factors were found (owner, 2026-11-22:
"make reusable code for calculating uncertainty"). Used by
``lss_core.patching`` (reflectivity) and meant for GID joins and any other
chain of scale factors.

Conventions (as the xmodfit hand-off, ``docs/handoff/19-lss-reader-
covariance-contract.md`` §3.4): K scans; φ_m = ln of the factor that puts
scan m on the anchor scan 0's scale (φ_0 = 0); a join's **step** δ_m =
φ_m − φ_(m−1)... in general δ_m = φ_m − a_m·φ, with a_m the sensitivity of
join m to the log scales of the scans it was fitted against (one-hot,
e_(m−1), when join m fits scan m against scan m−1's own points). Σ is the
K × K covariance of φ in log units (anchor row and column zero).

Why it matters (``docs/PHYSICS_ISSUES.md`` P4): a factor's error is one
common shift of every point of its scan and of every later scan; folding
it into each point's error as if independent makes downstream fits
overconfident (measured on synthetic slabs, ``docs/reports/
ref_patch_joint_fit.md`` §5.1: pull SD of an SLD 3.4–4.8 with the diagonal
only, 1.07 with the full covariance). The covariance below is the
information to report; it cannot be removed, only made smaller (better
factors, a prior) and reported correctly.

References: G. D'Agostini, Nucl. Instrum. Meth. A 346 (1994) 306
(https://doi.org/10.1016/0168-9002(94)90719-6): build a normalisation
covariance from the model, not the measured values, or in log space;
Fogli et al., Phys. Rev. D 66 (2002) 053010
(https://arxiv.org/abs/hep-ph/0206162): the covariance and the
nuisance-parameter ("pull") forms of a fit are equivalent.
"""
import math

import numpy as np


def chain_covariance(a_rows, errors):
    """Σ (K × K, log units) of a chain of joins (hand-off §3.4):
    Σ[m, j] = a_m·Σ[:, j] (j < m), Σ[m, m] = a_m Σ a_mᵀ + σ_δm².
    ``a_rows[m−1]``: length-K sensitivity of join m to the scans before it
    (zero from m on); ``errors[m−1]``: the step's error σ_δm. With
    one-hot rows this is a random walk: Σ_mm = Σ_(k ≤ m) σ_δk²."""
    K = len(a_rows) + 1
    S = np.zeros((K, K))
    for m in range(1, K):
        a = np.asarray(a_rows[m - 1], float)
        if a.shape != (K,):
            raise ValueError('a_rows[%d] has length %d, not %d' % (m - 1, a.size, K))
        for j in range(m):
            S[m, j] = S[j, m] = a @ S[:, j]
        S[m, m] = a @ S @ a + float(errors[m - 1]) ** 2
    return S


def steps_to_phi(steps, C_steps):
    """(φ (K), Σ (K × K)) from join steps chained one after the other
    (φ_m = Σ_(k ≤ m) δ_k) and their covariance (K−1 × K−1, may be
    correlated, e.g. after a correlated prior)."""
    steps = np.asarray(steps, float)
    K = steps.size + 1
    L = np.tril(np.ones((K - 1, K - 1)))
    phi = np.concatenate([[0.0], L @ steps])
    C = np.zeros((K, K))
    C[1:, 1:] = L @ np.asarray(C_steps, float) @ L.T
    return phi, C


def combine(delta, C_data, prior_mean, prior_cov, use=None):
    """Gaussian combination of fitted steps with a prior on them.

    ``delta`` (n), ``C_data`` (n × n, usually diagonal), ``prior_mean`` (n),
    ``prior_cov`` (n × n, may be correlated: shared foils); ``use``: the
    joins where the prior applies; at the others it is **marginalised**
    (its rows and columns dropped), not just down-weighted, so a rejected
    prior cannot leak into its neighbours through the correlations.
    Returns (posterior steps, their covariance, z), z the per-join
    disagreement (δ − δ_0)/√(σ_δ² + s_0²)."""
    delta = np.asarray(delta, float)
    C_data = np.atleast_2d(np.asarray(C_data, float))
    prior_mean = np.asarray(prior_mean, float)
    prior_cov = np.atleast_2d(np.asarray(prior_cov, float))
    n = delta.size
    use = np.ones(n, bool) if use is None else np.asarray(use, bool)
    with np.errstate(invalid='ignore', divide='ignore'):
        z = (delta - prior_mean) / np.sqrt(np.diag(C_data) + np.diag(prior_cov))
    if not use.any():
        return delta.copy(), C_data.copy(), z
    idx = np.flatnonzero(use)
    Pp = np.zeros((n, n))
    Pp[np.ix_(idx, idx)] = np.linalg.inv(prior_cov[np.ix_(idx, idx)])
    Pd = np.linalg.inv(C_data)
    C_post = np.linalg.inv(Pd + Pp)
    mp = np.zeros(n)
    mp[idx] = prior_mean[idx]
    post = C_post @ (Pd @ delta + Pp @ mp)
    return post, C_post, z


def total_sigma(y, sigma_meas, W, Sigma):
    """Per-point error with the factors' uncertainty, as the hand-off's error
    column: √(σ_meas² + y²·diag(W Σ Wᵀ)) (W: N × K weights of each point on
    the scans' log scales; one-hot for a point from one scan)."""
    y = np.asarray(y, float)
    W = np.asarray(W, float)
    v = np.einsum('ik,kl,il->i', W, np.asarray(Sigma, float), W)
    return np.sqrt(np.asarray(sigma_meas, float) ** 2 + y ** 2 * v)


def stitched_covariance(y, sigma_meas, W, Sigma, space='log', model=None):
    """N × N covariance of stitched data.

    ``space='log'``: of ln y, diag((σ_meas/y)²) + W Σ Wᵀ (the hand-off's
    native form). ``space='linear'``: of y, diag(σ_meas²) + D W Σ Wᵀ D with
    D = diag(``model``) when a model curve is given (recommended: a
    covariance built on the measured values biases fits low, D'Agostini
    1994) or diag(y) otherwise."""
    y = np.asarray(y, float)
    sm = np.asarray(sigma_meas, float)
    W = np.asarray(W, float)
    F = W @ np.asarray(Sigma, float) @ W.T
    if space == 'log':
        return np.diag((sm / y) ** 2) + F
    if space != 'linear':
        raise ValueError("space %r: 'log' or 'linear'" % space)
    d = np.asarray(model, float) if model is not None else y
    return np.diag(sm ** 2) + d[:, None] * F * d[None, :]


def inflate(error, chi2, dof):
    """The hand-off §3.2 inflate-only rule: error × max(1, √(χ²/dof))."""
    if dof is None or dof <= 0 or not np.isfinite(chi2):
        return float(error)
    return float(error) * max(1.0, math.sqrt(chi2 / dof))


def pulls(estimate, truth, error):
    """How well estimates and their errors describe a known truth (tests
    and method surveys): n, bias (mean of estimate − truth), sd, rmse,
    pull_mean, pull_sd ((estimate − truth)/error), coverage68 and
    coverage95 (fraction with |pull| ≤ 1 and ≤ 1.96)."""
    e = np.asarray(estimate, float)
    t = np.broadcast_to(np.asarray(truth, float), e.shape)
    s = np.broadcast_to(np.asarray(error, float), e.shape)
    ok = np.isfinite(e) & np.isfinite(t) & np.isfinite(s) & (s > 0)
    d = e[ok] - t[ok]
    p = d / s[ok]
    n = int(ok.sum())
    if n == 0:
        return dict(n=0, bias=math.nan, sd=math.nan, rmse=math.nan, pull_mean=math.nan, pull_sd=math.nan,
                    coverage68=math.nan, coverage95=math.nan)
    return dict(n=n, bias=float(d.mean()), sd=float(d.std(ddof=1)) if n > 1 else math.nan,
                rmse=float(np.sqrt(np.mean(d ** 2))), pull_mean=float(p.mean()),
                pull_sd=float(p.std(ddof=1)) if n > 1 else math.nan,
                coverage68=float(np.mean(np.abs(p) <= 1.0)), coverage95=float(np.mean(np.abs(p) <= 1.96)))
