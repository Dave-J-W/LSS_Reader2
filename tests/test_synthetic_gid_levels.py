"""The synthetic legacy GID set with several Qz levels
(tests/synthetic/gid_levels.py) through ``lss_core.gid.legacy_patch``:
two levels give back the truth, and since P36 and P37 were fixed
(2026-11-23) three levels do too."""
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


def test_three_levels_give_back_the_truth():
    """P36 fixed (2026-11-23): the first frame of each high-Qz scan was left
    per monitor, so where only the high level covers beta it was 1/M of the
    truth (scan 5's first frame: 1/1.03e5); now every point is within 5 %."""
    r, patch, _ = _flatness(THREE)
    assert [round(patch[i][0, 0], 3) for i in (0, 20)] == [14.0, 16.0]   # the two first frames
    assert np.all(np.abs(r - 1) < 0.05)


def test_one_high_qz_scan_of_its_own_is_patched():
    """P37 fixed (2026-11-23): a high level of one scan took the middle
    level's first key (KeyError); now its own scan, and the truth comes back."""
    levels = TWO + ((12.0, 1.25, 1),)
    r, _, info = _flatness(levels)
    assert [x[0] for x in info] == ['low Qz', 'middle Qz', 'high Qz']
    assert np.all(np.abs(r - 1) < 0.05)


def test_one_high_qz_scan_shared_with_the_middle_level_is_used_as_coded():
    """P37's case that always worked: the high level's one scan is also the
    middle level's first scan (frames at both Qz)."""
    frames, det, truth = gl.make_frames(levels=TWO + ((12.0, 1.25, 1),), scan_numbers=[[1, 2], [3, 4], [3]])
    patch, info = gm.legacy_patch(frames, gm.GIDParams(pinhole=False), det)
    assert [x[1] for x in info] == [[1, 2], [3, 4], [3]]
