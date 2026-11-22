"""lss_core.gls: the Woodbury form of the stitched-data covariance, the
equivalence of the GLS χ² and the nuisance-scale ("pull") form, and a
Monte Carlo of structural fits showing what the sidecar is for: with the
covariance the parameter pulls have SD ≈ 1, with diagonal errors they do
not (design and numbers: docs/reports/downstream_covariance.md §6)."""
import math

import numpy as np
import pytest

from lss_core import covariance_export as ce, gls
from synthetic import xrr, xrr_scans as xs

QC = 0.0217
TRUTH = np.array([25.0, 0.39, 3.5])          # film thickness (Å), electron density (e/Å³), roughness (Å)
WL = xs.Beamline().wavelength


def _model(q, d, rho, sig):
    return xrr.film(d, rho, sig).reflectivity(q, WL)


def _sidecar(seed=0, method='legacy', plan=None):
    r = xs.measure(xrr.film(*TRUTH), plan or xs.nx_like_plan(), seed=seed, errors='counting+monitor')
    if method == 'legacy':
        cd = ce.legacy_chain(r.per_scan, r.order).covdata('legacy')
    else:
        cd = ce.corrected_chain(r.per_scan, r.order).covdata('total')
    ref, _ = ce.finish(cd, QC, 0.0, None, False)
    return gls.load(ce.sidecar_dict(ref)), ref


def test_woodbury_solve_and_logdet_equal_the_dense_ones():
    sc, _ = _sidecar()
    for space, model in (('log', None), ('linear', None), ('linear', sc.y * 1.01)):
        C = sc.covariance(space, model)
        D = C.dense()
        r = np.random.default_rng(0).standard_normal(sc.n) * np.sqrt(np.diag(D))
        assert np.allclose(C.solve(r), np.linalg.solve(D, r), rtol=1e-9, atol=0)
        assert C.chi2(r) == pytest.approx(r @ np.linalg.solve(D, r), rel=1e-10)
        assert C.logdet() == pytest.approx(np.linalg.slogdet(D)[1], rel=1e-12)
        e = C.whiten(r)
        assert e @ e == pytest.approx(C.chi2(r), rel=1e-10)
    assert np.allclose(sc.sigma_total(), np.sqrt(np.diag(sc.covariance('linear').dense())))


def test_covariance_is_symmetric_positive_definite():
    """I28: C = diag + W Σ Wᵀ is SPD even though Σ is singular (anchor)."""
    sc, _ = _sidecar(1)
    for space in ('log', 'linear'):
        D = sc.covariance(space).dense()
        assert np.array_equal(D, D.T)
        assert np.linalg.eigvalsh(D).min() > 0


def test_gls_chi2_equals_the_nuisance_form():
    """The covariance form and the nuisance-scale form are the same χ²
    (log space: exactly, for any model curve, with and without a free
    overall scale); fit() minimises the nuisance form, so its χ² at the
    optimum is the GLS χ² of the fitted curve."""
    from scipy.optimize import least_squares
    sc, ref = _sidecar(2)
    t = sc.term('stitch')
    L = t.factor()
    U = t.weights @ L
    s = sc.sigma_meas / sc.y
    m = _model(sc.x, 25.3, 0.388, 3.6)
    r = np.log(sc.y) - np.log(m)
    gls_chi2 = gls.chi2(sc, m)
    A = np.vstack([U / s[:, None], np.eye(U.shape[1])])
    b = np.concatenate([r / s, np.zeros(U.shape[1])])
    eta, res, *_ = np.linalg.lstsq(A, b, rcond=None)
    assert gls_chi2 == pytest.approx(float(np.sum((A @ eta - b) ** 2)), rel=1e-9)
    chi_s, lns = gls.chi2(sc, m, free_scale=True)
    A1 = np.hstack([A, np.concatenate([1 / s, np.zeros(U.shape[1])])[:, None]])
    th, *_ = np.linalg.lstsq(A1, b, rcond=None)
    assert chi_s == pytest.approx(float(np.sum((A1 @ th - b) ** 2)), rel=1e-9)
    assert lns == pytest.approx(th[-1], rel=1e-8, abs=1e-12)
    f = gls.fit(sc, _model, TRUTH * [1.01, 0.99, 1.02])
    chi_fit, _ = gls.chi2(sc, _model(sc.x, *f.params), free_scale=True)
    assert f.chi2 == pytest.approx(chi_fit, rel=1e-6)
    assert f.success and f.dof == sc.n - 4


def test_fit_with_a_mask_selects_rows():
    sc, _ = _sidecar(3)
    keep = sc.x < 0.3
    f = gls.fit(sc, _model, TRUTH, mask=keep)
    assert f.dof == int(keep.sum()) - 4
    sub = sc.take(keep)
    assert np.array_equal(sub.term('stitch').weights, sc.term('stitch').weights[keep])


@pytest.mark.parametrize('method', ['legacy', 'corrected'])
def test_monte_carlo_pulls_with_and_without_the_covariance(method):
    """What a downstream fit gains (measured; report §6). 120 noise seeds of
    NX-like scans of a 25 Å film; d, ρ, σ fitted with a free overall scale.
    With the sidecar's covariance the pull SDs are ≈ 1 (measured 0.97–1.07
    over 300 seeds) and χ²/dof ≈ 1; with the legacy error column (factor
    errors folded into each point) the ρ and σ pulls are 3–4 and with the
    corrected diagonal (√diag C) 2–3. The SD of a pull SD from 120 draws is
    ≈ 0.065."""
    pulls = {'file': [], 'cov': []}
    chi = []
    rms = {'file': [], 'cov': []}
    for seed in range(120):
        sc, ref = _sidecar(seed, method)
        for mode, kw in (('file', dict(mode='diagonal', yerr=ref.error_column())), ('cov', dict())):
            f = gls.fit(sc, _model, TRUTH * [1.02, 0.99, 1.03], **kw)
            pulls[mode].append((f.params - TRUTH) / f.errors)
            rms[mode].append(f.params - TRUTH)
            if mode == 'cov':
                chi.append(f.chi2 / f.dof)
    sd = {k: np.std(v, axis=0, ddof=1) for k, v in pulls.items()}
    assert np.all((sd['cov'] > 0.8) & (sd['cov'] < 1.25)), sd['cov']
    assert sd['file'][1] > 2.0 and sd['file'][2] > 1.5, sd['file']
    assert 0.9 < np.mean(chi) < 1.12
    r = {k: np.sqrt(np.mean(np.square(v), axis=0)) for k, v in rms.items()}
    assert np.all(r['cov'] < r['file'])              # and more accurate, not only honest


def test_shifts_show_a_scan_whose_level_is_off():
    """The fitted nuisance shifts are the scans' level errors: a scan scaled
    by 1.02 after the patch shows a shift near ln(1.02) in its column
    (relative to the anchor), and its whitened η stands out."""
    sc, _ = _sidecar(4)
    t = sc.term('stitch')
    k = 3                                         # the last scan
    only = t.weights[:, k] == 1.0
    y = sc.y.copy()
    y[only] *= 1.02
    bad = gls.Sidecar(sc.x, y, sc.sigma_meas * np.where(only, 1.02, 1.0), sc.terms)
    f0 = gls.fit(sc, _model, TRUTH)
    f1 = gls.fit(bad, _model, TRUTH)
    d = f1.shifts['stitch'] - f0.shifts['stitch']
    assert d[k] - d[0] == pytest.approx(math.log(1.02), abs=0.006)
