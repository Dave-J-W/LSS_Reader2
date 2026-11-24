"""The saturation cue on Pilatus frames (F97, display side; owner,
2026-11-23, Q-IMG-10): per pixel, amber above 1e5 counts per second (soft
limit) and red above 1.5e5 (an absorber is needed). Counts per second are
the raw counts over the point's SPEC Seconds. Display only: no reduced
number changes.

Synthetic frames (tests/synth.py): scan 1 point 0 (Qz 0.01, below the
critical edge) peaks at 1e6 counts in 1 s, far above both limits; scan 1
point 8 (Qz 0.05) peaks at about 1e6 × R(0.05) ≈ 1e3 counts, below both.
"""
import numpy as np
import pytest

import sweep
from lss_core import display


def test_the_limits_split_soft_and_hard():
    counts = np.array([[5e4, 1.2e5], [2e5, 0.0]])
    soft, hard, top = display.saturation(counts, 1.0)
    assert soft.tolist() == [[False, True], [True, False]]       # soft includes hard
    assert hard.tolist() == [[False, False], [True, False]]
    assert top == 2e5
    soft, hard, _ = display.saturation(counts, 2.0)               # twice the time: half the rate,
    assert soft.sum() == 0 and hard.sum() == 0                    # 1e5 at most, not above the soft limit
    for t in (None, 0, -1, float('nan'), 'x'):
        assert display.saturation(counts, t) == (None, None, None)


def test_the_overlay_and_the_note():
    soft = np.array([[True, True], [False, False]])
    hard = np.array([[True, False], [False, False]])
    rgba = display.saturation_rgba(soft, hard)
    assert tuple(rgba[0, 0]) == display.HARD_RGBA and tuple(rgba[0, 1]) == display.SOFT_RGBA
    assert rgba[1, 0, 3] == 0.0                                    # clear elsewhere
    assert display.saturation_text(2, 1) == '1 px > 1.5e5 cps: absorber needed'
    assert display.saturation_text(2, 0) == '2 px > 1e5 cps'
    assert display.saturation_text(0, 0) == ''


@pytest.mark.gui
def test_a_frame_above_the_limit_is_marked_and_explained(loaded, qapp, dataset, recorder):
    w = loaded
    sweep.state_pilatus_one_frame(w, qapp, dataset)              # scan 1 point 0: 1e6 counts in 1 s
    sat = w.pilView['sats'][0]
    assert sat.get_visible()
    rgba = sat.get_array()
    assert np.any(np.all(np.isclose(rgba, display.HARD_RGBA), axis=-1))
    note = w.pilView['satnotes'][0]
    assert note.get_visible() and 'absorber needed' in note.get_text()
    assert w.pilView['axes'][0].get_title() == 'S# 1 pt 0'          # the title stays the frame's name
    assert 'counts per second' in w.ui.pilMplWidget.toolTip()
    n_soft, n_hard = w.pilSaturated[(w.selectedPilFramesNums[0],)]
    i = w.selectedPilFramesNums[0]
    assert n_hard == int(np.sum(w.pilData[i] / w.pilSeconds(i) > display.HARD_CPS)) > 0
    assert recorder.exceptions == []


@pytest.mark.gui
def test_a_frame_below_the_limits_has_no_cue(loaded, qapp, dataset, recorder):
    w = loaded
    sweep.state_spec_loaded(w, qapp, dataset)
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp, [8])                             # Qz 0.05: about 1e3 counts
    assert not w.pilView['sats'][0].get_visible()
    assert not w.pilView['satnotes'][0].get_visible()
    assert w.ui.pilMplWidget.toolTip() == ''
    assert recorder.exceptions == []


@pytest.mark.gui
def test_the_reduced_frame_is_unchanged_by_the_cue(loaded, qapp, dataset, recorder):
    """Display only: the drawn (per Monc) image and the raw frame are not altered."""
    w = loaded
    sweep.state_pilatus_one_frame(w, qapp, dataset)
    i = w.selectedPilFramesNums[0]
    raw = w.pilData[i].copy()
    shown = np.asarray(w.pilView['images'][0].get_array()).copy()
    w.pilDrawFrames()
    assert np.array_equal(w.pilData[i], raw)
    assert np.array_equal(np.asarray(w.pilView['images'][0].get_array()), shown)
    assert recorder.exceptions == []
