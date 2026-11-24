"""A GID patch of frames that hold no GID level says why (the GUI manager's
sweep, 2026-11-24, through the new GID Patch button).

Reflectivity frames lie one per Qz, so every "level" has a single frame and
no detector column seen by two frames: `pinhole_patch` failed on tt.min()
of an empty array with a numpy error. Now it raises GIDError with a message
the window shows."""
import dataclasses

import pytest

import sweep
from lss_core import gid as gidmod
from lss_core.experiment import Experiment


def test_the_script_refuses_reflectivity_frames(dataset):
    with pytest.raises(gidmod.GIDError, match='nothing to patch'):
        Experiment(dataset).gid([1])


def test_more_levels_than_a_patch_takes(dataset):
    frames, _ = Experiment(dataset).gid_frames([1, 2])
    frames = [dataclasses.replace(frames[k % len(frames)], qz=0.01 + 0.01 * k) for k in range(25)]   # 25 levels
    with pytest.raises(gidmod.GIDError, match='at most %d' % len(gidmod.LEVEL_NAMES)):
        gidmod.pinhole_patch(frames, gidmod.GIDParams())


@pytest.mark.gui
def test_the_window_says_so(loaded, qapp, recorder):
    w = loaded
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    recorder.messages.clear()
    w.pilGIDpatchData()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert any('nothing to patch' in m for m in recorder.messages)
