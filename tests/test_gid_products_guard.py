"""gid.products on maps that are not GID series (2026-11-24; the GUI
manager's crash sweep found the first, the GISAXS bug of 2026-11-23 the
second).

1. Without Relax, a map whose rows share no Qxy range has an empty Q grid,
   and the integrals raised IndexError. Now a GIDError says why, and the
   window shows it (its refusal, test_gui_tool_availability).
2. With Relax, the bin count divided by (last − first) of the first row's
   Qxy: zero or negative for a row that runs backwards, so np.linspace
   raised. Now its size, and the row's full span when that is zero, as in
   Show GISAXS. A normal map's grid is unchanged."""
import numpy as np
import pytest

from lss_core import gid

ALPHA, WL = np.radians(0.1), 1.24


def _map(two_theta):
    X, Y = np.meshgrid(two_theta, np.linspace(0.0, 2.0, 20))
    return X, Y, np.ones_like(X), 0.1 * np.ones_like(X)


def test_rows_without_a_common_qxy_range_are_refused_with_a_reason():
    with pytest.raises(gid.GIDError, match='share no Qxy range'):
        gid.products(*_map(np.linspace(0.5, 0.1, 30)), 'Q', ALPHA, WL)


def test_relax_with_a_row_that_runs_backwards():
    p = gid.products(*_map(np.linspace(0.5, 0.1, 30)), 'Q', ALPHA, WL, relax=True)
    assert np.all(np.diff(p['x'][0]) > 0) and p['data'].shape == p['x'].shape


def test_a_normal_map_keeps_its_relax_grid():
    X, Y, D, E = _map(np.linspace(10.0, 20.0, 40))
    p = gid.products(X, Y, D, E, 'Q', ALPHA, WL, relax=True)
    k0 = 2 * np.pi / WL
    xq = k0 * np.sqrt(np.cos(ALPHA) ** 2 + np.cos(np.radians(Y)) ** 2
                      - 2 * np.cos(ALPHA) * np.cos(np.radians(Y)) * np.cos(np.radians(X)))
    n_before = int(len(xq[0]) * (np.max(xq) - np.min(xq)) / (xq[0][-1] - xq[0][0]))   # the formula of before
    assert p['x'].shape[1] == n_before
    assert np.array_equal(p['x'][0], np.linspace(np.min(xq), np.max(xq), n_before))
