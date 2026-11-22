"""The reduced-reflectivity measurement generator (tests/synthetic/xrr_scans.py):
scans split as measured recombine to the truth with the true factors, the
reader's legacy chain recovers them where the grids coincide, Poisson
errors have the right scatter, and deliberate faults are where they are
said to be."""
import numpy as np
import pytest

from lss_core import reflectivity as refl
from lss_core import stitching
from synthetic import xrr
from synthetic import xrr_scans as xs

PROFILES = {'water': xrr.bare_water(), 'dppc': xrr.dppc(), 'film': xrr.film(100.0)}
PLANS = {'nx': xs.nx_like_plan, 'standard': xs.standard_plan, 'staggered': lambda: xs.standard_plan(grid='staggered'),
         'reaching_back': xs.reaching_back_plan, 'five': lambda: xs.standard_plan(5)}


@pytest.mark.parametrize('plan', PLANS)
@pytest.mark.parametrize('profile', PROFILES)
def test_split_scans_recombine_to_the_truth_with_the_true_factors(profile, plan):
    d = xs.measure(PROFILES[profile], PLANS[plan](), expected=True)
    c = d.combine()
    assert c[:, 1] == pytest.approx(d.truth(c[:, 0]), rel=1e-12)
    for k, v in d.per_scan.items():
        assert v.shape[1] == len(xs.COLUMNS) and v[:, 1] * d.scans[k].scale == pytest.approx(d.truth(v[:, 0]), rel=1e-12)
    assert d.order == refl.order_scans(d.per_scan)


@pytest.mark.parametrize('plan', ['standard', 'reaching_back', 'five'])
def test_legacy_chain_with_the_true_factors_gives_the_truth_where_points_coincide(plan):
    d = xs.measure(PROFILES['dppc'], PLANS[plan](), expected=True)
    joined = refl.patch(d.per_scan, d.order, factors={j: (f, 0.0) for j, f in d.true_join_factors().items()})
    s0 = d.scans[d.order[0]].scale
    assert joined[:, 1] * s0 == pytest.approx(d.truth(joined[:, 0]), rel=1e-10)
    # the fitted factors are the true ones (no noise, shared points)
    fitted = refl.patch(d.per_scan, d.order)
    assert fitted[:, 1] * s0 == pytest.approx(d.truth(fitted[:, 0]), rel=1e-9)


def test_legacy_chain_on_the_nx_grids_interpolates_points_that_do_not_coincide():
    """NX scans 6 and 7 share 0.035, 0.0375, 0.04 but scan 6 also has
    0.03625 and 0.03875: there the merge uses the cubic spline of scan 7
    (P1). Measured without noise on bare water: at most 5e-4 off the truth."""
    d = xs.measure(PROFILES['water'], xs.nx_like_plan(), expected=True)
    joined = refl.patch(d.per_scan, d.order, factors={j: (f, 0.0) for j, f in d.true_join_factors().items()})
    err = np.abs(joined[:, 1] * d.scans[d.order[0]].scale / d.truth(joined[:, 0]) - 1)
    assert 1e-5 < err.max() < 1e-3


def test_the_fitted_factor_is_exact_on_coinciding_and_biased_on_staggered_grids():
    for grid, lo, hi in (('coincide', 0.0, 1e-9), ('staggered', 1e-5, 2e-3)):
        d = xs.measure(PROFILES['water'], xs.standard_plan(grid=grid), expected=True)
        c, steps = d.curves(), d.true_steps()
        for j, (a, b) in enumerate(zip(d.order, d.order[1:])):
            f, _ = stitching.fitted_factor(c[a], c[b])
            assert lo <= abs(f / steps[j] - 1) <= hi
            if grid == 'staggered':
                assert f < steps[j]                  # low, as P1 says


def test_reaching_back_plan_overlaps_an_earlier_overlap():
    d = xs.measure(PROFILES['water'], xs.reaching_back_plan(), expected=True)
    q1, q2, q3 = (d.scans[k].qz for k in (1, 2, 3))
    assert q2[0] < q1[-1] and q3[0] < q1[-1] and q3[0] > q2[0]


def test_absorbers_are_the_least_that_keep_the_first_point_below_the_rate():
    bl = xs.Beamline()
    d = xs.measure(PROFILES['water'], xs.nx_like_plan(), bl, expected=True)
    foils = bl.foils()
    for r in d.scans.values():
        rate = r.counts['peak'][0] / r.seconds[0]
        assert rate <= bl.max_rate
        less = [n for n in range(64) if foils.factor(n) < foils.factor(r.absorber)]
        assert all(rate * r.true_attenuation / foils.factor(n) > bl.max_rate for n in less)
    # the flux was taken from NX scan 6, measured with 41: the first scan needs it too
    assert d.scans[1].absorber == 41


def test_poisson_errors_have_the_right_scatter():
    """Pulls (net − E net)/σ over 300 draws: σ from counts and monitor
    ('counting+monitor') has unit scatter; counting alone misses the
    monitor's Poisson noise where the counts are high."""
    plan = xs.standard_plan(3)
    truth = xs.measure(PROFILES['dppc'], plan, expected=True)
    pulls = {'counting': [], 'counting+monitor': []}
    rng = np.random.default_rng(5)
    for _ in range(300):
        for e in pulls:
            d = xs.measure(PROFILES['dppc'], plan, errors=e, seed=rng)
            pulls[e].append(np.concatenate([(d.per_scan[k][:, 1] - truth.per_scan[k][:, 1]) / d.per_scan[k][:, 2]
                                            for k in sorted(d.per_scan)]))
    full = np.array(pulls['counting+monitor'])
    assert np.std(full) == pytest.approx(1.0, abs=0.03)
    assert abs(np.mean(full)) < 0.03
    assert np.all(np.abs(np.std(full, axis=0) - 1) < 0.2)       # every point, 300 draws: ±0.04 expected
    bright = truth.per_scan[1][:, 3] * truth.scans[1].monc > 3e5   # counts in the box
    first = np.array(pulls['counting'])[:, :len(truth.per_scan[1])]
    assert np.std(first[:, bright]) > 1.2


def test_monitor_fault_moves_the_true_factor_away_from_the_foils():
    """P29: slits opened ×2.27 for scan 3 but Monc rose only ×1.55: scan 3's
    values per Monc are ×2.27/1.55 too high, so the true factor is the
    foils' × 1.55/2.27; Monc/Monp over the overlap shows 1.55, as
    lss_core.reflectivity.monitor_change reads it."""
    absorber = [41, 31, 15]
    plan = xs.standard_plan(3, slit_gain=[1.0, 1.0, 2.27], monitor_gain=[1.0, 1.0, 1.55], absorber=absorber)
    d = xs.measure(PROFILES['water'], plan, seed=2)
    nominal = d.nominal_join_factors()
    true = d.true_join_factors()
    assert true[0] == pytest.approx(nominal[0][0], rel=1e-12)
    assert true[1] == pytest.approx(nominal[1][0] * 1.55 / 2.27, rel=1e-12)
    a, b = d.scans[2], d.scans[3]
    mon = refl.monitor_change(a.qz, a.monc, a.monp, b.qz, b.monc, b.monp)
    assert mon == pytest.approx(1.55, rel=0.01)
    ok = xs.measure(PROFILES['water'], xs.standard_plan(3, slit_gain=[1.0, 1.0, 2.27], absorber=absorber), seed=2)
    assert ok.true_join_factors()[1] == pytest.approx(nominal[1][0], rel=1e-12)


def test_attenuation_error_is_in_the_truth_not_in_the_nominal_factor():
    plan = xs.standard_plan(3, attenuation_error=[1.0, 1.08, 1.0])
    d = xs.measure(PROFILES['water'], plan, expected=True)
    nom, true = d.nominal_join_factors(), d.true_join_factors()
    assert true[0] == pytest.approx(nom[0][0] * 1.08, rel=1e-12)
    assert true[1] == pytest.approx(nom[1][0], rel=1e-12)
    assert d.scans[2].true_attenuation == pytest.approx(d.scans[2].nominal_attenuation * 1.08)
    f, _ = stitching.fitted_factor(d.curves()[1], d.curves()[2])
    assert f == pytest.approx(true[0], rel=1e-9)            # the patch measures the truth


def test_only_the_first_frame_in_the_low_qz_range_uses_the_five_row_boxes():
    plan = [xs.ScanSpec(np.array([0.025, 0.026, 0.027])), xs.ScanSpec(np.array([0.026, 0.027, 0.028]))]
    d = xs.measure(PROFILES['water'], plan, seed=1)
    for r in d.scans.values():
        assert list(r.core_only) == [True, False, False]
        assert r.pilatus[0] == r.counts['S_core'][0]
        assert r.pilatus[1] == r.counts['S_core'][1] + r.counts['S_outer'][1]


def test_resolution_and_profile_reach_the_rows():
    plan = xs.chain_plan([(0.12, 0.3, 0.005), (0.25, 0.4, 0.005)], overlap=3)
    sharp = xs.measure(PROFILES['film'], plan, expected=True)
    smeared = xs.measure(PROFILES['film'], plan, resolution=(0.01, 0.0), expected=True)
    assert smeared.truth(0.2) == pytest.approx(float(PROFILES['film'].reflectivity(0.2, resolution=(0.01, 0.0))))
    assert not np.allclose(smeared.per_scan[1][:, 1], sharp.per_scan[1][:, 1], rtol=1e-3)
    assert list(sharp.scans[2].qz[:3]) == list(sharp.scans[1].qz[-3:])


def test_drawn_data_are_reproducible_and_whole_counts():
    a = xs.measure(PROFILES['water'], xs.reaching_back_plan(), seed=7)
    b = xs.measure(PROFILES['water'], xs.reaching_back_plan(), seed=7)
    for k in a.per_scan:
        assert a.per_scan[k].tobytes() == b.per_scan[k].tobytes()
        r = a.scans[k]
        for key in ('S_core', 'S_outer', 'B1_core', 'B2_outer'):
            assert np.all(r.counts[key] == np.round(r.counts[key]))
        assert np.all(r.monc == np.round(r.monc)) and np.all(r.monp == np.round(r.monp))
