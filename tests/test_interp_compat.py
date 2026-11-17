"""interp2d_linear against known values, and against the real interp2d
where an old SciPy (< 1.14) is installed (see TESTING.md, "A second, older
environment")."""
import numpy as np
import pytest

from interp_compat import interp2d_linear


def _real_interp2d():
    try:
        from scipy.interpolate import interp2d
        interp2d([0, 1], [0, 1], [[0, 1], [1, 2]])
        return interp2d
    except Exception:
        return None


def test_bilinear_values():
    x, y = np.array([0.0, 1.0, 3.0]), np.array([0.0, 2.0])
    z = np.array([[0.0, 1.0, 3.0], [10.0, 11.0, 13.0]])     # z = x + 5 y
    f = interp2d_linear(x, y, z)
    assert f([0.5, 2.0], [1.0]) == pytest.approx([5.5, 7.0])
    assert f(x, y) == pytest.approx(z)
    assert f([2.0], [0.5, 1.5]).ravel() == pytest.approx([4.5, 9.5])


def test_shape_and_single_row():
    f = interp2d_linear([0, 1, 2], [0, 1], [[0, 1, 2], [1, 2, 3]])
    assert f([0, 1, 2], [0, 0.5, 1]).shape == (3, 3)
    assert f([0, 1, 2], [0.5]).shape == (3,)
    assert f(1.0, 0.5).shape == (1,)


def test_requested_points_are_sorted_like_interp2d():
    f = interp2d_linear([0, 1, 2], [0, 1], [[0, 1, 2], [1, 2, 3]])
    assert f([2, 0, 1], [1, 0]) == pytest.approx(f([0, 1, 2], [0, 1]))


def test_outside_takes_nearest_edge():
    f = interp2d_linear([0, 1], [0, 1], [[0, 1], [1, 2]])
    assert f([-5, 9], [-3, 7]) == pytest.approx(np.array([[0, 1], [1, 2]]))


def test_unsorted_grid_is_accepted():
    f = interp2d_linear([2, 0, 1], [1, 0], [[3, 1, 2], [2, 0, 1]])
    assert f([0, 1, 2], [0, 1]) == pytest.approx(np.array([[0, 1, 2], [1, 2, 3]]))


@pytest.mark.skipif(_real_interp2d() is None,
                    reason='interp2d was removed from this SciPy')
@pytest.mark.parametrize('seed', range(8))
def test_matches_real_interp2d(seed):
    interp2d = _real_interp2d()
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(1.2, 1.6, rng.integers(2, 45)))
    y = np.sort(rng.uniform(-0.05, 1.3, rng.integers(2, 500)))
    z = rng.uniform(0, 500, (len(y), len(x)))
    xn = rng.uniform(1.1, 1.7, rng.integers(1, 60))        # unsorted, some outside
    yn = rng.uniform(-0.1, 1.4, rng.integers(1, 400))
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        want = interp2d(x, y, z, kind='linear')(xn, yn)
        want_same_axis = interp2d(x, y, z, kind='linear')(xn, y)
    assert interp2d_linear(x, y, z)(xn, yn) == pytest.approx(want, rel=1e-12, abs=1e-12)
    assert interp2d_linear(x, y, z)(xn, y) == pytest.approx(want_same_axis, rel=1e-12, abs=1e-12)
