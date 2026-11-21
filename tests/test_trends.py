"""lss_core.trends: constant / linear / exponential / double exponential
over time, compared by AICc, and the confident time to a 5 % change
(owner, 2026-11-21). Synthetic data with a known truth."""
import math

import numpy as np
import pytest

from lss_core import trends

T = np.arange(21) * 10.0 + 5.0          # 21 frames of 10 s, at the middle of each exposure


def _noisy(mu, rel, seed):
    rng = np.random.default_rng(seed)
    s = rel * np.abs(mu)
    return mu + rng.normal(0, 1, mu.size) * s, s


def test_constant_data_are_stable_and_allow_a_long_time():
    y, s = _noisy(np.full(T.size, 100.0), 0.01, 1)
    c = trends.compare(T, y, s, t0=0.0)
    assert c.stable and c.best == 'constant' and c.delta_constant_linear <= trends.STABLE_DELTA
    assert c.criterion == 'AICc' or c.c_hat < 2
    # a 1 % scatter over 210 s bounds the drift: 5 % takes longer than the test itself
    assert c.change.confident > 210 and c.change.confident <= c.change.best
    assert 'stable' in c.verdict()
    w = sum(f.weight for f in c.fits.values() if f.ok)
    assert w == pytest.approx(1.0)


def test_a_drift_is_detected_and_its_five_percent_time_found():
    slope = 5e-4                                     # 5 % in 100 s
    y, s = _noisy(100 * (1 - slope * T), 0.005, 2)
    c = trends.compare(T, y, s, t0=0.0)
    assert not c.stable and c.best in ('linear', 'exponential')
    assert c.change.best == pytest.approx(100.0, rel=0.1)
    assert c.change.confident < c.change.best and c.change.confident > 70
    assert not c.change.extrapolated
    assert 'changing' in c.verdict() and 'beats a constant by' in c.verdict()


def test_an_exponential_decay_is_preferred_and_tau_recovered():
    tau = 100.0
    y, s = _noisy(100 * np.exp(-T / tau), 0.005, 3)
    c = trends.compare(T, y, s, t0=0.0)
    assert c.best in ('exponential', 'double exponential')
    f = c.fits['exponential']
    k, ke = f.params[1], f.errors[1]
    assert abs(k + 1 / tau) < 3 * ke
    assert c.fits['linear'].delta > 10                     # a line is clearly worse
    assert c.change.best == pytest.approx(-tau * math.log(0.95), rel=0.1)


def test_two_time_constants_need_the_double_exponential():
    mu = 60 * np.exp(-T / 15.0) + 100 * np.exp(-T / 2000.0)
    y, s = _noisy(mu, 0.003, 4)
    c = trends.compare(T, y, s)
    assert c.best == 'double exponential'
    f = c.fits['double exponential']
    assert -1 / f.params[1] == pytest.approx(15.0, rel=0.3)      # the fast one first


def test_errors_that_understate_the_scatter_switch_to_qaicc():
    y, _ = _noisy(100 * (1 - 2e-4 * T), 0.03, 5)
    c = trends.compare(T, y, np.full(T.size, 1.0))        # σ = 1 %, scatter 3 %
    assert c.criterion == 'QAICc' and 4 < c.c_hat < 20
    assert 'QAICc' in c.summary()
    plain = trends.compare(T, y, np.full(T.size, 1.0), overdispersion=False)
    assert plain.criterion == 'AICc' and plain.c_hat == 1.0
    # with errors too small, the plain criterion sees changes that are not resolved
    assert plain.fits['constant'].delta >= c.fits['constant'].delta


def test_without_errors_they_come_from_the_scatter():
    y, _ = _noisy(np.full(T.size, 50.0), 0.02, 6)
    c = trends.compare(T, y)
    assert any('scatter' in n for n in c.notes)
    assert c.sigma[0] == pytest.approx(1.0, rel=0.4)
    assert c.stable


def test_bad_points_are_dropped_and_few_points_reported():
    y, s = _noisy(np.full(T.size, 10.0), 0.01, 7)
    y[3] = np.nan
    s[5] = 0.0
    c = trends.compare(T, y, s)
    assert len(c.t) == T.size - 2 and 'dropped' in c.notes[0]
    few = trends.compare([1, 2], [1, 2], [0.1, 0.1])
    assert not few.fits and 'fewer than 3' in few.notes[0]
    with pytest.raises(ValueError):
        trends.model_value('quadratic', [1], T)


def test_a_position_change_against_a_width():
    """The position's change is measured against the peak's FWHM: 5 % of a
    0.02 width is 0.001."""
    y, s = _noisy(1.465 + 1e-5 * T, 1e-5 / 1.465, 8)
    c = trends.compare(T, y, s, scale=0.02, t0=0.0)
    assert c.change.scale == 0.02
    assert c.change.best == pytest.approx(0.001 / 1e-5, rel=0.1)


def test_model_table_rows():
    y, s = _noisy(np.full(T.size, 10.0), 0.01, 9)
    c = trends.compare(T, y, s)
    rows = c.table()
    assert [r['model'] for r in rows] == list(trends.MODELS)
    assert all(r['params'] for r in rows if r['ok'])


@pytest.mark.slow
def test_the_confident_time_is_conservative_at_its_stated_level():
    """Coverage: over 200 noise draws of a 5 %-in-100-s drift, the 95 %
    confident time exceeds the true 100 s in about 5 % of cases (measured
    5.5 % when written); a constant is called stable in about 95 %."""
    miss = stable = 0
    n = 200
    for seed in range(n):
        y, s = _noisy(100 * (1 - 5e-4 * T), 0.01, 100 + seed)
        c = trends.compare(T, y, np.full(T.size, 1.0), models=('constant', 'linear'), t0=0.0)
        miss += c.change.confident > 100.0
        y0, _ = _noisy(np.full(T.size, 100.0), 0.01, 1000 + seed)
        stable += bool(trends.compare(T, y0, np.full(T.size, 1.0), models=('constant', 'linear')).stable)
    assert miss / n < 0.09
    assert stable / n > 0.85
