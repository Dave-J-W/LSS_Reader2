"""MainWindow.oneDjoin: scaling and merging two overlapping 1D curves."""
import numpy as np
import pytest

import synth

FACTOR = 1.42
REL_ERR = 1.0e-3


def curve(q):
    return 250.0 * synth.reflectivity(q)


def scan(q, attenuation=1.0):
    y = curve(q) / attenuation
    return np.column_stack([q, y, REL_ERR * y])


Q1 = np.linspace(0.01, 0.05, 9)


@pytest.mark.gui
def test_exact_when_overlap_points_coincide(window):
    q2 = np.linspace(0.04, 0.10, 13)          # contains 0.04, 0.045, 0.05
    fac = window.oneDjoin(scan(Q1), scan(q2, FACTOR), mtype='fac')[0]
    assert fac == pytest.approx(FACTOR, rel=1e-12)
    merged = window.oneDjoin(scan(Q1), scan(q2, FACTOR), mtype='merge')
    assert merged[:, 0] == pytest.approx(np.linspace(0.01, 0.10, 19))
    assert merged[:, 1] == pytest.approx(curve(merged[:, 0]), rel=1e-9)
    rel = merged[:, 2] / merged[:, 1]
    overlap = (merged[:, 0] >= 0.04 - 1e-9) & (merged[:, 0] <= 0.05 + 1e-9)
    # two equal-weight points averaged: error falls by sqrt(2)
    assert rel[overlap] == pytest.approx(REL_ERR / np.sqrt(2), rel=1e-6)
    assert rel[~overlap] == pytest.approx(REL_ERR, rel=1e-6)


@pytest.mark.gui
def test_overlap_window_reported_by_fac_mode(window):
    q2 = np.linspace(0.04, 0.10, 13)
    fac, xmin, xmax, ymin, ymax = window.oneDjoin(scan(Q1), scan(q2, FACTOR),
                                                  mtype='fac')
    # one point either side of the overlap is included for plotting
    assert (xmin, xmax) == pytest.approx((0.035, 0.055))
    assert ymax == pytest.approx(curve(0.035))


@pytest.mark.gui
def test_staggered_grid_bias_as_coded(window):
    """Characterisation, not a requirement.

    When scan 2 has no point at Qz = 0.045 the code interpolates it with a
    cubic spline in linear intensity. On a curve falling like Qz^-4 that
    overestimates scan 2, so the scale factor comes out 1.3 % low and every
    point beyond the overlap inherits the bias.
    """
    q2 = np.linspace(0.04, 0.10, 7)
    fac = window.oneDjoin(scan(Q1), scan(q2, FACTOR), mtype='fac')[0]
    assert fac == pytest.approx(1.403700960797748, rel=1e-9)
    merged = window.oneDjoin(scan(Q1), scan(q2, FACTOR), mtype='merge')
    ratio = merged[:, 1] / curve(merged[:, 0])
    assert ratio[:6] == pytest.approx(1.0)
    assert ratio[9:] == pytest.approx(0.98686335, rel=1e-6)
    # and the fitted-factor uncertainty inflates the errors from 0.1 % to 1.3 %
    assert (merged[9:, 2] / merged[9:, 1]) == pytest.approx(0.0128516, rel=1e-4)


@pytest.mark.gui
@pytest.mark.xfail(strict=True, reason='cubic interpolation in linear '
                   'intensity biases the scale factor on staggered grids')
def test_staggered_grid_recovers_factor(window):
    q2 = np.linspace(0.04, 0.10, 7)
    fac = window.oneDjoin(scan(Q1), scan(q2, FACTOR), mtype='fac')[0]
    assert fac == pytest.approx(FACTOR, rel=1e-3)


@pytest.mark.gui
def test_extra_columns_are_dropped(window):
    q2 = np.linspace(0.04, 0.10, 13)
    a = np.column_stack([scan(Q1), np.ones((9, 4))])
    b = np.column_stack([scan(q2, FACTOR), np.ones((13, 4))])
    assert window.oneDjoin(a, b, mtype='merge').shape == (19, 3)
