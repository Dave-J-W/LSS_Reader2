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


@pytest.mark.parametrize('shape', bp.SHOULDER_SHAPES)
def test_shoulder_shapes_and_a_changing_shoulder(shape):
    """P44 (2026-11-27): the profile is the floor, the shoulder of the
    stated shape and height and the stated peak; the shoulder's height
    follows ``shoulder_change``; the default shape is the old shoulder."""
    prof, truth = bp.profiles(change='fade', shoulder_shape=shape, shoulder_change=0.4, seed=None)
    x = bp.X
    dx = x[1] - x[0]
    lit = (x > bp.LIT[0]) & (x < bp.LIT[1])
    for k, (p, a, f) in enumerate(zip(prof, truth.area, truth.floor)):
        peak = p[:, 1] - lit * (f + truth.shoulder_profile(k))
        assert np.sum(peak) * dx == pytest.approx(a, rel=1e-4)
    assert truth.shoulder_height[-1] / truth.shoulder_height[0] == pytest.approx(
        (1 + 0.4 * 20.5 / 21) / (1 + 0.4 * 0.5 / 21))
    if shape != 'none':
        s = truth.shoulder_profile(0)
        assert np.max(s) == pytest.approx(truth.shoulder_height[0], rel=0.02 if shape != 'two' else 0.7)
    else:
        assert not np.any(truth.shoulder_profile(0))
    plain, _ = bp.profiles(change='fade', seed=None)
    gauss, _ = bp.profiles(change='fade', shoulder_shape='gaussian', shoulder_change=0.0, seed=None)
    assert all(np.array_equal(u, v) for u, v in zip(plain, gauss))
    with pytest.raises(ValueError):
        bp.profiles(shoulder_shape='square')


def test_a_peak_can_broaden_and_fade_together():
    """``area_change`` on top of ``change`` (an NX 15-like burn, P44)."""
    t = bp.profiles(change='broaden', amount=0.2, area_change=-0.13, seed=None)[1]
    f = t.t / (21 * 10.0)
    assert np.allclose(t.area, bp.AREA * (1 - 0.13 * f)) and np.allclose(t.fwhm, bp.FWHM * (1 + 0.2 * f))
    assert np.all(bp.profiles(change='fade', seed=None)[1].area == bp.profiles(change='fade', area_change=0.0,
                                                                                    seed=None)[1].area)
