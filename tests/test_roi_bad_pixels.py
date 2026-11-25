"""The ROI's own bad-pixel pass (F95 B3; owner, Q-UI-B3: "a separate
threshold for the ROI"), off by default until main man's study (rule 12;
issue #55, 2026-11-25). lss_core.reflectivity.roi_bad_pixels, used by
frame_row, exp.reflectivity and the window.

Known truth: a smooth reflected peak on a flat background, with one hot
pixel put inside the signal box. And the case the study must weigh: a
sparse high-Qz frame, a few lone real counts beside zeros, which the pass
takes for hot pixels."""
import numpy as np
import pytest

import sweep
import synth
from lss_core import reflectivity
from TwoDDetector import TwoDDetector

MON = 1.0e5
SLIT = (21, 11)
PEAK = (synth.PIL_H - synth.DB_X - 1, synth.DB_Y)       # (col, row) as read
BEAM_XY = (synth.DB_X, synth.DB_Y)                       # the SPEC header's X, Y


def _row(img, factor):
    det = TwoDDetector('Pilatus')
    return reflectivity.frame_row(det, img, np.sqrt(img), MON, BEAM_XY, 0.05, SLIT, 0.5, 'H', 600.0,
                                  False, roi_bad_pixel_factor=factor)


def test_off_by_default_and_a_hot_pixel_in_the_box_is_corrected():
    clean = synth.pilatus_image(peak=PEAK, amplitude=5000.0)
    hot = clean.copy()
    at = (PEAK[1] + 3, PEAK[0] + 6)                       # (row, col): inside the 21 × 11 box, off the peak
    hot[at] = 4.0e5
    none_clean, _ = _row(clean, None)
    none_hot, info0 = _row(hot, None)
    assert info0['roi_corrected'] == [] and none_hot[1] > none_clean[1] * 1.5   # off: the zinger counted
    with_hot, info = _row(hot, 10.0)
    assert info['roi_corrected'] == [(at[1], at[0])]                          # (column, row)
    assert with_hot[1] == pytest.approx(none_clean[1], rel=2e-3)              # back to the clean sum
    with_clean, info2 = _row(clean, 10.0)
    assert info2['roi_corrected'] == [] and with_clean[1] == pytest.approx(none_clean[1], rel=1e-12)


def test_a_pixel_outside_the_box_is_left_to_the_frames_correction():
    img = synth.pilatus_image(peak=PEAK, amplitude=5000.0)
    img[PEAK[1] + 30, PEAK[0]] = 4.0e5                      # far below the box
    _, info = _row(img, 10.0)
    assert info['roi_corrected'] == []


def test_as_coded_a_lone_real_count_on_a_sparse_frame_is_removed():
    """Why the pass is off: at high Qz the reflected beam is a few counts.
    A lone count beside zeros passes the neighbour test whatever the factor
    (its neighbours' mean is 0) and the floor of an almost empty box, so the
    pass removes real signal. The study decides whether a guard (enough
    counts about the pixel) makes the pass safe (rule 12)."""
    img = np.zeros((synth.PIL_W, synth.PIL_H))
    img[PEAK[1], PEAK[0]] = 6.0                              # the reflected beam: six counts in one pixel
    off, _ = _row(img, None)
    on, info = _row(img, 40.0)
    assert off[3] == pytest.approx(6.0 / MON) and info['roi_corrected'] == [(PEAK[0], PEAK[1])]
    assert on[3] == 0.0                                      # the signal is gone


@pytest.mark.gui
def test_the_window_off_by_default_and_the_script_follows(loaded, qapp, recorder, dataset):
    from lss_core.experiment import Experiment
    w = loaded
    w.prefs['auto_save'] = False
    assert w.ui.refBPCFacLineEdit.text() == '' and w.refRoiBadPixelFactor() is None
    assert 'Off until a study' in w.ui.refBPCFacLineEdit.toolTip()
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.refBPCFacLineEdit.setText('10')
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    line = w.reflectivityScript('x').split('\n')[0]
    assert 'roi_bad_pixel_factor=10.0' in line
    ns = {'exp': Experiment(dataset)}
    exec(line, ns)
    assert np.array(w.refData, dtype=float)[:, :3] == pytest.approx(ns['ref'].patched[:, :3], rel=1e-10)
    w.ui.refBPCFacLineEdit.setText('')
    assert w.refRoiBadPixelFactor() is None
    assert recorder.exceptions == []
