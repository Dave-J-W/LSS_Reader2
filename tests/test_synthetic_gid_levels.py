"""The synthetic legacy GID set with several Qz levels
(tests/synthetic/gid_levels.py) through ``lss_core.gid.legacy_patch``:
two levels give back the truth; three levels show P36 and P37 (strict
expected failures, PHYSICS_ISSUES; the defects are not fixed here)."""
import numpy as np
import pytest

from lss_core import gid as gm
from synthetic import gid_levels as gl

TWO = ((0.0, 1.0, 2), (6.0, 0.8, 2))
THREE = TWO + ((12.0, 1.25, 2),)


def _flatness(levels, **kw):
    frames, det, truth = gl.make_frames(levels=levels, **kw)
    patch, info = gm.legacy_patch(frames, gm.GIDParams(pinhole=False), det)
    r = np.array([p[:, 2] / t for p, t in zip(patch, truth.at(patch))])
    return r / np.median(r), patch, info


def test_levels_cover_overlapping_beta_ranges():
    frames, _, truth = gl.make_frames(levels=THREE)
    assert [round(q, 4) for q, *_ in truth.levels] == [round(gl.level_qz(o), 4) for o in (0.0, 6.0, 12.0)]
    assert len({round(f.qz, 3) for f in frames}) == 3
    assert len(frames) == 3 * 54
    assert truth.monitors[2] == pytest.approx(1.03e5)


def test_two_levels_give_back_the_truth():
    """Expected counts: the legacy patch divided by T is flat to the
    interpolation of the joins (measured ±2.5 %)."""
    r, patch, info = _flatness(TWO)
    assert [x[0] for x in info] == ['low Qz', 'middle Qz']
    assert np.all(np.abs(r - 1) < 0.03)


def test_two_levels_with_counting_noise():
    r, _, _ = _flatness(TWO, seed=3, monitor=1e9)         # ~9000 counts per pixel: 0.6 % per point
    assert np.percentile(np.abs(r - 1), 95) < 0.04


def test_three_levels_as_coded_first_high_frame_of_each_scan_is_off_by_the_monitor():
    """P36 as coded: the first frame of each high-Qz scan (the columns at
    the first Det_Th of scans 5 and 6) is not multiplied by the scan's mean
    monitor, so where only the high level covers β it is ~1/M of the truth;
    every other point is within 5 %."""
    frames, det, truth = gl.make_frames(levels=THREE)
    r, patch, _ = _flatness(THREE)
    first = [0, 20]                       # Det_Th 14.0 (scan 5) and 16.0 (scan 6)
    assert [round(patch[i][0, 0], 3) for i in first] == [14.0, 16.0]
    others = np.delete(r, first, axis=0)
    assert np.all(np.abs(others - 1) < 0.05)
    # scan 5's first frame, where only the high level covers beta: 1/M_5 of the truth
    assert r[0][-50:] == pytest.approx(1 / truth.monitors[5], rel=0.01)
    # scan 6's first frame lies in the 2theta overlap with scan 5 and is averaged with it
    assert np.all((r[20][-50:] > 0.5) & (r[20][-50:] < 0.95))


@pytest.mark.xfail(strict=True, reason='P36: first frame of each high-Qz scan not scaled by the mean monitor')
def test_three_levels_give_back_the_truth():
    r, _, _ = _flatness(THREE)
    assert np.all(np.abs(r - 1) < 0.05)


@pytest.mark.xfail(strict=True, raises=KeyError, reason="P37: one high-Qz scan takes the middle level's key")
def test_one_high_qz_scan_of_its_own_is_patched():
    levels = TWO + ((12.0, 1.25, 1),)
    r, _, info = _flatness(levels)
    assert [x[0] for x in info] == ['low Qz', 'middle Qz', 'high Qz']


def test_one_high_qz_scan_shared_with_the_middle_level_is_used_as_coded():
    """P37's harmless case: the high level's one scan is the middle level's
    first scan (frames at both Qz), so the key coincides and no KeyError."""
    frames, det, truth = gl.make_frames(levels=TWO + ((12.0, 1.25, 1),), scan_numbers=[[1, 2], [3, 4], [3]])
    patch, info = gm.legacy_patch(frames, gm.GIDParams(pinhole=False), det)
    assert [x[1] for x in info] == [[1, 2], [3, 4], [3]]
