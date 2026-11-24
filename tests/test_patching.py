"""lss_core.patching and lss_core.uncertainty: the joint-fit reflectivity
patch, the foil prior and the covariance of stitched data (owner,
2026-11-22; design and measurements: docs/reports/ref_patch_joint_fit.md,
whose §8 lists these tests). The legacy patch (lss_core.stitching) is not
touched: its staggered-grid xfail stays, for the legacy path."""
import math
import os

import numpy as np
import pytest

import synth
from lss_core import absorbers, patching, uncertainty as unc
from lss_core.patching import Scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
QC = patching.QC


def _parratt(q, d=25.0, sld=11.0e-6, sigma=3.5):
    """One slab on water, Névot–Croce roughness (as the report's sim.py)."""
    sub = QC ** 2 / (16 * np.pi)
    slds, sig, th = [0.0, sld, sub], [sigma, sigma], [0.0, d, 0.0]
    k0 = np.asarray(q, float) / 2
    kz = [np.sqrt(k0 ** 2 - 4 * np.pi * s + 0j) for s in slds]
    r = np.zeros_like(k0, dtype=complex)
    for j in range(1, -1, -1):
        rf = (kz[j] - kz[j + 1]) / (kz[j] + kz[j + 1]) * np.exp(-2 * kz[j] * kz[j + 1] * sig[j] ** 2)
        ph = np.exp(2j * kz[j + 1] * th[j + 1])
        r = (rf + r * ph) / (1 + rf * r * ph)
    return np.abs(r) ** 2


def _scans(seed=None, counts=400.0, staggered=True):
    """Four scans of a slab curve at absorber factors 1, 1/20, 1/60, 1/200
    (what multiplies the curve in each scan), each counted long enough that
    its weakest point has about ``counts`` counts; Poisson noise (none
    without a seed). Returns the scans and the true scales."""
    segs = [(0.012, 0.06, 13), (0.05, 0.16, 18), (0.14, 0.32, 19), (0.29, 0.55, 19)]
    if not staggered:
        segs = [(0.012, 0.06, 13), (0.052, 0.164, 15), (0.148, 0.316, 15), (0.292, 0.548, 17)]
    scale = [1.0, 1 / 20, 1 / 60, 1 / 200]
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for (lo, hi, n), c in zip(segs, scale):
        q = np.linspace(lo, hi, n)
        r = _parratt(q)
        i0 = counts / r.min()                         # counts per unit of reflectivity in this scan
        lam = i0 * r
        nn = rng.poisson(lam).astype(float) if rng is not None else lam
        out.append(Scan(q, nn / i0 * c, np.sqrt(np.maximum(nn, 1.0)) / i0 * c, label='S%d' % len(out)))
    return out, scale


def test_joint_factor_removes_the_staggered_grid_bias():
    """P1: the legacy spline gives 1.4013 for 1.42 on this grid (pinned as an
    xfail in test_stitching.py); the joint fit is exact to 1e-4."""
    q1, q2 = np.linspace(0.01, 0.05, 9), np.linspace(0.04, 0.10, 7)
    a = Scan(q1, 250 * synth.reflectivity(q1), 1e-3 * 250 * synth.reflectivity(q1))
    b = Scan(q2, 250 * synth.reflectivity(q2) / 1.42, 1e-3 * 250 * synth.reflectivity(q2) / 1.42)
    j = patching.joint_factor(a, b)
    assert j.factor == pytest.approx(1.42, rel=1e-4)
    assert patching.interp_factor(a, b).factor == pytest.approx(1.4013, abs=2e-3)      # the P1 bias, for reference


@pytest.mark.parametrize('space', ['rrf', 'raw'])
@pytest.mark.parametrize('likelihood', ['log', 'poisson'])
def test_exact_data_on_a_quartic_give_the_factor_exactly(space, likelihood):
    for qb in (np.linspace(0.08, 0.20, 13), np.linspace(0.081, 0.205, 11)):      # coinciding and staggered
        qa = np.linspace(0.03, 0.12, 10)
        lnr = lambda q: 1.0 - 30 * q + 50 * q ** 2 - 80 * q ** 3 + 60 * q ** 4
        base = (lambda q: np.log(patching.fresnel(q))) if space == 'rrf' else (lambda q: 0 * q)
        ya, yb = np.exp(lnr(qa) + base(qa)), np.exp(lnr(qb) + base(qb)) / 3.7
        j = patching.joint_factor(Scan(qa, ya, 1e-3 * ya), Scan(qb, yb, 1e-3 * yb), space=space,
                                  likelihood=likelihood)
        assert j.factor == pytest.approx(3.7, rel=1e-8) and j.chi2 == pytest.approx(0, abs=1e-12)


def test_scaling_rules_and_point_order():
    scans, _ = _scans(seed=1)
    a, b = scans[1], scans[2]
    j = patching.joint_factor(a, b)
    jb = patching.joint_factor(a, Scan(b.q, b.y * 2.5, b.sigma * 2.5))
    assert jb.delta == pytest.approx(j.delta - math.log(2.5), abs=1e-9)
    both = patching.joint_factor(Scan(a.q, a.y * 7, a.sigma * 7), Scan(b.q, b.y * 7, b.sigma * 7))
    assert both.delta == pytest.approx(j.delta, abs=1e-9)
    o = np.random.default_rng(0).permutation(len(b.q))
    assert patching.joint_factor(a, Scan(b.q[o], b.y[o], b.sigma[o])).delta == pytest.approx(j.delta, abs=1e-12)


def test_sensitivity_sums_to_one_per_scan_and_matches_a_finite_difference():
    scans, _ = _scans(seed=2)
    a, b = scans[0], scans[1]
    j = patching.joint_factor(a, b, likelihood='log')
    na = len(j.ia)
    assert j.sensitivity[:na].sum() == pytest.approx(1.0, abs=1e-10)
    assert j.sensitivity[na:].sum() == pytest.approx(-1.0, abs=1e-10)
    k = j.ia[2]
    y2, s2 = a.y.copy(), a.sigma.copy()
    y2[k] *= math.exp(1e-6)
    s2[k] *= math.exp(1e-6)                       # the point's weight (y/σ)² kept: a pure log shift
    d = (patching.joint_factor(Scan(a.q, y2, s2), b, likelihood='log').delta - j.delta) / 1e-6
    assert d == pytest.approx(j.sensitivity[2], rel=1e-3)
    jp = patching.joint_factor(a, b)                         # Poisson-like: the same within 1e-3
    assert jp.sensitivity[:len(jp.ia)].sum() == pytest.approx(1.0, abs=1e-3)


def test_chain_covariance_is_a_random_walk_and_matches_the_recursion():
    errs = [0.01, 0.02, 0.005]
    a_rows = [np.eye(4)[m] for m in range(3)]
    S = unc.chain_covariance(a_rows, errs)
    assert np.allclose(np.diag(S), [0, 1e-4, 5e-4, 5.25e-4])
    assert S[3, 1] == pytest.approx(1e-4) and S[3, 2] == pytest.approx(5e-4)
    # a join fitted against a mixture of earlier scans (non-one-hot a_m)
    a_rows = [np.array([1, 0, 0, 0.0]), np.array([0.3, 0.7, 0, 0]), np.array([0, 0.5, 0.5, 0])]
    S = unc.chain_covariance(a_rows, errs)
    s11 = 1e-4
    s21 = 0.7 * s11
    s22 = 0.49 * s11 + errs[1] ** 2
    assert S[2, 1] == pytest.approx(s21) and S[2, 2] == pytest.approx(s22)
    assert S[3, 3] == pytest.approx(0.25 * (s11 + 2 * s21 + s22) + errs[2] ** 2)
    phi, C = unc.steps_to_phi([0.1, 0.2, 0.3], np.diag(np.square(errs)))
    assert np.allclose(phi, [0, 0.1, 0.3, 0.6]) and np.allclose(C, unc.chain_covariance([np.eye(4)[m] for m in range(3)], errs))


def test_global_fit_equals_the_chain_with_disjoint_windows():
    scans, _ = _scans(seed=3)
    c = patching.chain(scans, likelihood='log', guard_p=0, inflate=False, n_ext=4)   # the same window
    g = patching.global_fit(scans, inflate=False, n_ext=4)
    assert np.allclose(g.phi, c.phi, atol=1e-10)
    assert np.allclose(g.Sigma, c.Sigma, atol=1e-12)


def test_combine_rules():
    d, Cd = np.array([0.10, 0.20]), np.diag([0.01 ** 2, 0.02 ** 2])
    m, Cp = np.array([0.12, 0.25]), np.diag([0.02 ** 2, 0.02 ** 2])
    post, Cpost, z = unc.combine(d, Cd, m, Cp)
    w1, w2 = 1 / 0.01 ** 2, 1 / 0.02 ** 2
    assert post[0] == pytest.approx((w1 * 0.10 + w2 * 0.12) / (w1 + w2))
    assert Cpost[0, 0] == pytest.approx(1 / (w1 + w2))
    assert z[1] == pytest.approx(-0.05 / math.sqrt(2 * 0.02 ** 2))
    same, Csame, _ = unc.combine(d, Cd, m, Cp, use=[False, False])
    assert np.allclose(same, d) and np.allclose(Csame, Cd)
    # a correlated prior, the second join's prior marginalised: the first equals a one-join combination
    Cc = np.array([[0.02 ** 2, 0.8 * 0.02 * 0.02], [0.8 * 0.02 * 0.02, 0.02 ** 2]])
    one, _, _ = unc.combine(d, Cd, m, Cc, use=[True, False])
    assert one[0] == pytest.approx(post[0]) and one[1] == pytest.approx(0.20)


def test_known_steps_diagonal_is_the_foils_step():
    foils = absorbers.calibrated(10.0)
    settings = [41, 31, 24, 18]
    mean, C = patching.known_steps(foils, settings, overlap_qz=[0.05, 0.15, 0.3])
    for m in range(3):
        ratio, rel = foils.step(settings[m], settings[m + 1], qz=[0.05, 0.15, 0.3][m])
        assert mean[m] == pytest.approx(math.log(ratio)) and math.sqrt(C[m, m]) == pytest.approx(rel)
    assert np.all(np.linalg.eigvalsh(C) > 0) and abs(C[0, 1]) > 0       # correlated through shared foils


def test_prior_guard():
    use, why = patching.prior_mask([1.58, 1.0, 1.01, 1.0], [0.5, 0.5, 4.0, None])
    assert use.tolist() == [False, True, False, False]
    assert 'Monc/Monp changed' in why[0] and 'disagree by 4.0' in why[2] and why[1] == ''


def test_stitched_errors_and_covariance():
    scans, _ = _scans(seed=4)
    res = patching.chain(scans)
    st = res.stitch(scans)
    assert len(st.q) == sum(len(s.q) for s in scans) and np.all(np.diff(st.q) >= 0)
    tot = st.sigma_total()
    assert np.all(tot >= st.sigma_meas - 1e-15)
    C = st.covariance('log')
    assert np.allclose(np.sqrt(np.diag(C)) * st.y, tot)
    last = st.W[:, 3] == 1
    off = C[np.ix_(last, last)] - np.diag(np.diag(C[np.ix_(last, last)]))
    assert np.allclose(off[off != 0], res.Sigma[3, 3])                   # one common shift for the whole scan
    merged = res.stitch(scans, merge='coincident')
    assert len(merged.q) <= len(st.q) and np.allclose(merged.W.sum(axis=1), 1)


def test_pulls():
    rng = np.random.default_rng(5)
    e = 1.0 + rng.normal(0, 0.1, 4000)
    p = unc.pulls(e, 1.0, 0.1)
    assert abs(p['bias']) < 0.01 and p['pull_sd'] == pytest.approx(1, abs=0.05)
    assert p['coverage68'] == pytest.approx(0.683, abs=0.03)


@pytest.mark.slow
def test_monte_carlo_bias_and_pulls():
    """1000 noise draws of the four-scan slab: every join's factor unbiased
    (|bias| < 0.2 σ) and its reported error right (pull SD 0.9–1.1). With
    200 draws the pull SD itself scatters by about 0.05 (one 200-draw set
    gave 0.80 at the first join, 1000 draws 0.99), hence 1000."""
    deltas, errs = [], []
    for seed in range(1000):
        scans, f = _scans(seed=5000 + seed)
        res = patching.chain(scans)
        deltas.append([j.delta for j in res.joins])
        errs.append([j.err for j in res.joins])
    deltas, errs = np.array(deltas), np.array(errs)
    truth = [math.log(f[m] / f[m + 1]) for m in range(3)]          # δ = ln f, f multiplies scan b
    for m in range(3):
        p = unc.pulls(deltas[:, m], truth[m], errs[:, m])
        assert abs(p['bias']) < 0.2 * np.median(errs[:, m]), (m, p)
        assert 0.9 < p['pull_sd'] < 1.1, (m, p)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_nx_school_scans_6_to_9():
    """Two pins, both measured.

    The settings of 2026-11-22 (report §6.1: n_ext=4, guard_p=0.01):
    joint factors 0.023004, 0.064516, 0.103604; the level of scan 9
    relative to scan 6 known to 0.75 % (legacy chain 1.03 %); no join
    flagged.

    Today's default (n_ext=2, guard_p=0.3, from the gauntlet of
    2026-11-22; measured 2026-11-23, physics_notes): factors 0.022980,
    0.064474, 0.103695; the level known to 0.85 %; join 2 (7→8) flagged,
    because no window or order passes the guard (χ²/dof 1.37 at 2 either
    side), with its error inflated ×1.17. With 6 points either side, the
    ladder now raises the order at join 8→9 (order 6, χ²/dof 1.15) where
    it used to step the window down."""
    from lss_core.experiment import Experiment
    r = Experiment(NX).reflectivity([6, 7, 8, 9], errors='budget')
    scans = patching.scans_from_reflectivity(r)
    old = patching.chain(scans, n_ext=4, guard_p=0.01)
    assert [round(j.factor, 6) for j in old.joins] == [0.023004, 0.064516, 0.103604]
    assert np.sqrt(old.Sigma[3, 3]) == pytest.approx(0.0075, abs=3e-4)
    assert not any(j.flags for j in old.joins)
    res = patching.chain(scans)
    assert [round(j.factor, 6) for j in res.joins] == [0.02298, 0.064474, 0.103695]
    assert np.sqrt(res.Sigma[3, 3]) == pytest.approx(0.00845, abs=3e-4)
    assert not res.joins[0].flags and not res.joins[2].flags
    assert 'no adequate fit' in res.joins[1].flags[0] and 'error inflated' in res.joins[1].flags[0]
    assert res.joins[1].err / res.joins[1].err_counting == pytest.approx(1.17, abs=0.02)
    wide = patching.chain(scans, n_ext=6)
    assert wide.joins[2].order == 6 and 'first adequate fit' in wide.joins[2].flags[0] and not wide.joins[0].flags
    foils = absorbers.calibrated(10.0)
    prior = patching.known_steps(foils, [41, 31, 24, 18])
    pr = patching.chain(scans, prior=prior, monitor_ratios=[1.005, 4.35, 1.32])
    assert [j.prior_used for j in pr.joins] == [True, False, False]
    assert 'Monc/Monp changed' in pr.joins[1].why


def _fringe_minimum_join():
    """Join 3 of a 100 Å film at low counts (the gauntlet's film100_lowcounts,
    seed 1000): four coinciding points at a fringe minimum."""
    from synthetic import xrr, xrr_scans as xs
    bl = xs.Beamline(flux=2.5e11, **xs.REAL_MONITOR)
    r = xs.measure(xrr.film(100.0), xs.standard_plan(4, grid='coincide'), beamline=bl, seed=1000,
                   errors='counting+monitor')
    sc = [patching.Scan(r.per_scan[k][:, 0], r.per_scan[k][:, 1], r.per_scan[k][:, 2]) for k in r.order]
    truth = [math.log(v) for v in r.true_steps().values()]
    return sc[2], sc[3], truth[2]


def test_the_guard_raises_the_order_where_no_quadratic_fits():
    """2026-11-22, the gauntlet: the old ladder ended at order 2 on the
    overlap, which fits no fringe minimum (χ²/dof ≈ 280), and inflated the
    error about ×17 although δ was right. The ladder now raises the order."""
    a, b, truth = _fringe_minimum_join()
    old = patching.joint_factor(a, b, order=2, n_ext=0, guard_p=0)
    assert old.chi2 / old.dof > 50
    j = patching.joint_factor(a, b)
    assert j.err < 2 * j.err_counting            # not inflated by an inadequate model
    assert abs(j.delta - truth) < 3 * j.err
    assert scipy_chi2_sf(j.chi2, j.dof) >= patching.GUARD_P or j.n_ext == 0


def scipy_chi2_sf(x, k):
    from scipy.stats import chi2
    return chi2.sf(x, k)


def test_the_guard_ladder_keeps_the_offset_identifiable():
    """Without a shared Qz, a polynomial through every position would absorb
    the factor: the ladder stops one order lower there."""
    q = np.linspace(0.03, 0.08, 26)
    a = patching.Scan(q[:16], np.exp(-40 * q[:16]), 1e-3 * np.ones(16))
    qb = q[11:] + 0.001                     # staggered: no Qz shared
    b = patching.Scan(qb, np.exp(-40 * qb), 1e-3 * np.ones(len(qb)))
    ladder = patching.guard_ladder(a, b)
    assert len(ladder) > 3
    for o, e in ladder:
        ia, ib = patching.window(a.q, b.q, e)
        n_pos = len(np.unique(np.round(np.concatenate([a.q[ia], b.q[ib]]), 9)))
        assert o <= n_pos - 2 and o <= len(ia) + len(ib) - 4
    assert patching.guard_ladder(a, b)[0] == (4, patching.N_EXT)


def test_rung_fit_is_the_joint_fit_at_one_rung_and_returns_its_curve():
    """patching.rung_fit (2026-11-24, study A, tests/tools/ref_guard_study.py):
    on every rung of the guard's ladder it gives joint_factor's δ, errors, χ²,
    dof and points at that rung without the guard, bit for bit; its curve is
    the fitted ln(μ_a/R_F): exact data on a quartic give the quartic back."""
    a, b, _ = _fringe_minimum_join()
    for o, e in patching.guard_ladder(a, b):
        try:
            j = patching.joint_factor(a, b, order=o, n_ext=e, guard_p=0)
        except ValueError:
            with pytest.raises(ValueError):
                patching.rung_fit(a, b, o, e)
            continue
        r = patching.rung_fit(a, b, o, e)
        assert (r.order, r.n_ext) == (o, e)
        assert (r.delta, r.err, r.err_counting, r.chi2, r.dof) == (j.delta, j.err, j.err_counting, j.chi2, j.dof)
        assert list(r.ia) == list(j.ia) and list(r.ib) == list(j.ib)
        assert r.p_chi2 == pytest.approx(scipy_chi2_sf(r.chi2, r.dof), rel=1e-12)
        assert len(r.coef) == o + 1
    qa, qb = np.linspace(0.03, 0.12, 10), np.linspace(0.081, 0.205, 11)
    lnr = lambda q: 1.0 - 30 * q + 50 * q ** 2 - 80 * q ** 3 + 60 * q ** 4
    ya, yb = np.exp(lnr(qa)) * patching.fresnel(qa), np.exp(lnr(qb)) * patching.fresnel(qb) / 3.7
    r = patching.rung_fit(Scan(qa, ya, 1e-3 * ya), Scan(qb, yb, 1e-3 * yb), order=4, n_ext=2)
    q = np.linspace(qa[r.ia].min(), qb[r.ib].max(), 9)
    assert r.curve(q) == pytest.approx(lnr(q), abs=1e-7)
    assert math.exp(r.delta) == pytest.approx(3.7, rel=1e-8)
