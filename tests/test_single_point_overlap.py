"""A join whose overlap holds one point (the GUI manager's find, 2026-11-24:
dropping the new scan's first point at a join).

curve_fit has no scatter to scale its covariance by with one point, so the
factor's error was infinite, and every point from the join on got an
infinite or NaN error, with both patch methods (the joint fit falls back to
the legacy fit there). Now the factor is that point's ratio, with the
ratio's own counting error."""
import numpy as np
import pytest

import synth
from lss_core import stitching
from lss_core.experiment import Experiment


def test_one_point_overlap_gives_the_ratio_and_its_error():
    a = np.array([[0.01, 100.0, 5.0], [0.02, 50.0, 2.0], [0.03, 20.0, 1.0]])
    b = np.array([[0.03, 10.0, 0.4], [0.04, 5.0, 0.3], [0.05, 2.0, 0.2], [0.06, 1.0, 0.1]])
    f, e = stitching.fitted_factor(a, b)
    assert f == pytest.approx(2.0)
    assert e == pytest.approx(2.0 * np.hypot(1.0 / 20.0, 0.4 / 10.0))
    assert np.isfinite(e)


@pytest.mark.parametrize('maker,scans', [(synth.make_dataset, [1, 2]),
                                         (synth.make_identical_scans_dataset, [1, 2, 3])])
@pytest.mark.parametrize('method', ['joint', 'legacy'])
def test_dropping_the_first_point_keeps_every_error_finite(tmp_path, maker, scans, method):
    exp = Experiment(maker(tmp_path / 'd'))
    r = exp.reflectivity(scans, drops={0: [[0]]}, method=method)
    assert np.all(np.isfinite(r.ref[:, 2])) and np.all(r.ref[:, 2] > 0)
    plain = exp.reflectivity(scans, method=method)
    assert len(r.ref) == len(plain.ref)                       # the dropped point is a duplicate Qz of the merge
