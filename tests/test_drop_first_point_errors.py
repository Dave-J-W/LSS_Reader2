"""A drop of the new scan's first point at a join leaves dR NaN or inf
(found 2026-11-24 by the GUI manager while testing F96; pre-existing on
main 7b9a22b, the window and lss_core alike).

Measured on synthetic data (tests/synth.py), `Experiment.reflectivity`:
- make_dataset, scans 1 and 2, drops={0: [[0]]}: 6 of 14 points have a
  non-finite error, from Qz 0.05 (the first point of scan 2 that is left)
  to the end, with method 'joint' and 'legacy';
- make_identical_scans_dataset, scans 1, 2, 3: 8 of 14, from Qz 0.04.
- drops {0: [[-1]]} or {0: [[1]]}, or no drop: every error finite.
The window gives the same: Ref Patch, Drop "0", Finish.

Handed to Main (the session that owns the reduction) with this test; the
strict xfail came off with the fix (2026-11-24: a one-point overlap now
gives the ratio and its counting error, `stitching._fit_factor`).
"""
import numpy as np
import pytest

import synth
from lss_core.experiment import Experiment


@pytest.mark.parametrize('drop', [[[-1]], [[1]], None])
@pytest.mark.parametrize('method', ['joint', 'legacy'])
def test_other_drops_keep_every_error_finite(tmp_path, method, drop):
    spec = synth.make_dataset(tmp_path / 'd')
    ref = Experiment(spec).reflectivity([1, 2], drops=None if drop is None else {0: drop}, method=method)
    assert np.all(np.isfinite(ref.patched[:, 2]))


@pytest.mark.parametrize('method', ['joint', 'legacy'])
@pytest.mark.parametrize('maker,scans', [(synth.make_dataset, [1, 2]),
                                         (synth.make_identical_scans_dataset, [1, 2, 3])],
                         ids=['two-scans', 'with-a-repeat'])
def test_dropping_the_new_scans_first_point_keeps_every_error_finite(tmp_path, method, maker, scans):
    spec = maker(tmp_path / 'd')
    ref = Experiment(spec).reflectivity(scans, drops={0: [[0]]}, method=method)
    bad = ref.patched[~np.isfinite(ref.patched[:, 2]), 0]
    assert bad.size == 0, 'non-finite dR at Qz %s' % bad.tolist()
