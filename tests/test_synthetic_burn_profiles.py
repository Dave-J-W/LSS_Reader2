"""GID burn profiles with known truth (tests/synthetic/burn_profiles.py)."""
import numpy as np
import pytest

from lss_core import burn
from synthetic import burn_profiles as bp


@pytest.mark.parametrize('change', bp.CHANGES)
def test_expected_profiles_hold_the_stated_peak(change):
    prof, truth = bp.profiles(change=change, amount=0.3 if change != 'shift' else 0.004, seed=None)
    x = bp.X
    dx = x[1] - x[0]
    lit = (x > bp.LIT[0]) & (x < bp.LIT[1])
    shoulder = truth.shoulder * np.exp(-0.5 * ((x - bp.SHOULDER[1]) / bp.SHOULDER[2]) ** 2)
    for p, a, c, f in zip(prof, truth.area, truth.centre, truth.floor):
        peak = p[:, 1] - lit * (f + shoulder)
        assert np.sum(peak) * dx == pytest.approx(a, rel=1e-4)
        assert np.sum(peak * x) / np.sum(peak) == pytest.approx(c, abs=1e-6)
        assert np.all(p[~lit, 1] == 0)


def test_the_truths_change_as_stated():
    t = bp.profiles(change='fade', amount=0.2, seed=None)[1]
    assert t.t[0] == 5.0 and t.relative('area')[-1] == pytest.approx((1 - 0.2 * 20.5 / 21) / (1 - 0.2 * 0.5 / 21))
    t = bp.profiles(change='fade', tau=400.0, seed=None)[1]
    assert t.relative('area')[-1] == pytest.approx(np.exp(-200.0 / 400.0))
    t = bp.profiles(change='broaden', amount=0.3, seed=None)[1]
    assert np.all(t.area == t.area[0]) and t.fwhm[-1] > 1.25 * t.fwhm[0]
    t = bp.profiles(change='shoulder', seed=None)[1]
    assert t.shoulder == pytest.approx(3 * bp.SHOULDER[0])
    with pytest.raises(ValueError):
        bp.profiles(change='melt')


def test_counting_noise_follows_the_monitor():
    a, _ = bp.profiles(change='none', monitor=1e7, seed=2)
    b, _ = bp.profiles(change='none', monitor=1e5, seed=2)
    exp, _ = bp.profiles(change='none', seed=None)
    rel = lambda ps: np.std([(p[:, 1] - e[:, 1])[e[:, 1] > 0.01] / e[:, 1][e[:, 1] > 0.01] for p, e in zip(ps, exp)])
    assert rel(b) == pytest.approx(10 * rel(a), rel=0.15)
    assert np.allclose(a[0][:, 2], np.sqrt(np.maximum(a[0][:, 1] * 1e7, 1)) / 1e7)


def test_the_default_estimator_reads_a_shift():
    """Example of use (one seed): the template follows a 0.004 Å⁻¹ shift
    (0.0037 of the true 0.0038 between the first and last frames' middles)."""
    prof, truth = bp.profiles(change='shift', amount=0.004, seed=1)
    values = burn.measure_gid(prof)[0]
    c = values['centre'][0]
    assert c[-1] - c[0] == pytest.approx(truth.centre[-1] - truth.centre[0], abs=4e-4)
