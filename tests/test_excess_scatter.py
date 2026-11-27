"""The excess-scatter estimators of tests/tools/excess_scatter.py (DATA_NEEDS row 15) on known truth."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import excess_scatter as E   # noqa: E402


def _terms(curve, x, n=30, seed=0):
    rng = np.random.default_rng(seed)
    prof = E._curves()[curve]
    pairs, within = [], []
    for _ in range(n):
        p, w = E.series_terms(E.synth_series(prof, x, 0.0, rng))
        pairs += p; within += w
    return pairs, within


@pytest.mark.parametrize('x', [0.0, 0.02])
def test_both_estimators_recover_the_excess_on_water(x):
    pairs, within = _terms('water', x)
    for kind, terms in (('pairs', pairs), ('curvature', within)):
        e = E.estimate(kind, terms)
        assert abs(e['x_ml'] - x) < 0.004, (kind, e)
        assert e['x_lo'] <= e['x_ml'] <= e['x_hi']


def test_shared_points_are_unbiased_on_a_fringed_film():
    pairs, _ = _terms('film 100 Å', 0.01)
    assert abs(E.estimate('pairs', pairs)['x_ml'] - 0.01) < 0.002


def test_pair_terms_need_two_shared_points():
    q = np.array([0.1, 0.11, 0.12])
    y = np.array([1e-6, 9e-7, 8e-7])
    s = y * 0.01
    assert E.pair_terms(q, y, s, q + 0.5, y, s) is None
    t = E.pair_terms(q, y, s, q, 2 * y, s)
    assert np.allclose(t['r'], -np.log(2)) and len(t['r']) == 3


def test_no_excess_gives_chi2_near_one():
    pairs, within = _terms('water', 0.0, n=20, seed=3)
    assert 0.8 < E.estimate('pairs', pairs)['chi2_dof0'] < 1.2
    assert 0.8 < E.estimate('curvature', within)['chi2_dof0'] < 1.2


def _outlier_terms(x, outliers, sigma_scale=1.0, n=40, seed=5):
    rng = np.random.default_rng(seed)
    prof = E._curves()['water']
    pairs, within = [], []
    for _ in range(n):
        p, w = E.series_terms(E.synth_series(prof, x, 0.0, rng, outliers, sigma_scale))
        pairs += p; within += w
    return pairs, within


@pytest.mark.parametrize('x', [0.0, 0.01, 0.03])
def test_the_core_survives_outliers_and_their_absence(x):
    for out in (0.0, E.OUTLIER_SHARE):
        pairs, _ = _outlier_terms(x, out)
        m = E.estimate_mixture('pairs', pairs, profile=False)
        assert abs(m['x'] - x) < 0.003, (x, out, m)
        assert m['tau'] >= E.TAU_MIN
        if out == 0.0:
            assert m['pi'] < 0.01


def test_one_gaussian_is_fooled_by_outliers():
    pairs, _ = _outlier_terms(0.005, E.OUTLIER_SHARE)
    assert E.estimate('pairs', pairs)['x_ml'] > 0.03


@pytest.mark.parametrize('x', [0.0, 0.01])
def test_the_within_scan_core_survives_the_real_share_of_outliers(x):
    # C63's real numbers come from this estimator; ~0.3 % of points are wild in the real data
    _, within = _outlier_terms(x, E.REAL_OUTLIER_SHARE)
    m = E.estimate_mixture('curvature', within, profile=False)
    assert abs(m['x'] - x) < 0.003, (x, m)
    assert E.estimate('curvature', within)['x_ml'] > x + 0.005     # one Gaussian is fooled


def test_an_understated_counting_error_is_found_as_a_scale():
    _, within = _outlier_terms(0.0, 0.0, sigma_scale=1.15)
    e = E.estimate_scale('curvature', within)
    assert abs(e['s'] - 1.15) < 0.06
