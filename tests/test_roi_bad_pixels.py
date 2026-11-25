"""The ROI's own bad-pixel pass (F95 B3; owner, Q-UI-B3: "a separate
threshold for the ROI"), by the arithmetic of main man's study (C62:
removeBadPix's test over the frame, applied to the ROI's three boxes), off
by default until rule 12. lss_core.reflectivity.roi_bad_pixel_pass, used
by frame_row, exp.reflectivity and the window.

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


def test_the_whole_frame_pass_is_removeBadPix():
    """bad_pixel_pass without a region gives removeBadPix's numbers and pixels."""
    rng = np.random.default_rng(3)
    img = rng.poisson(synth.pilatus_image(peak=PEAK, amplitude=800.0)).astype(float)
    for r, c, v in ((5, 7, 9.0e4), (0, 40, 3.0e3), (PEAK[1] + 2, PEAK[0] - 4, 2.0e4), (synth.PIL_W - 1, 3, 500.0)):
        img[r, c] = v                                        # edges and corners too
    for it, fac in ((1, 4.0), (1, 10.0), (2, 3.0)):
        ref, loc = TwoDDetector('Pilatus').removeBadPix(img.copy(), iteration=it, factor=fac)
        out, changed = reflectivity.bad_pixel_pass(img, it, fac)
        assert np.array_equal(out, ref)
        if it == 1:
            assert sorted(map(tuple, np.argwhere(changed))) == sorted(map(tuple, loc))


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


def test_a_hot_pixel_in_a_background_box_is_corrected_too():
    """C62: the pass covers the three boxes (a background-only pass biased R by +107 %)."""
    clean = synth.pilatus_image(peak=PEAK, amplitude=5000.0)
    _, info = _row(clean, None)
    hot = clean.copy()
    from lss_core.display import roi_boxes
    (_, (r0, r1, c0, c1)) = [b for b in roi_boxes(SLIT, info['centre'], bg=info['bg'], direction='H')
                             if b[0] == 'left'][0]
    at = ((r0 + r1) // 2, (c0 + c1) // 2)
    hot[at] = 4.0e5
    _, info2 = _row(hot, 10.0)
    assert info2['roi_corrected'] == [(at[1], at[0])]


def test_a_pixel_outside_the_box_is_left_to_the_frames_correction():
    img = synth.pilatus_image(peak=PEAK, amplitude=5000.0)
    img[PEAK[1] + 30, PEAK[0]] = 4.0e5                      # far below the box
    _, info = _row(img, 10.0)
    assert info['roi_corrected'] == []


def test_as_coded_a_lone_real_count_on_a_sparse_frame_is_removed():
    """As coded, the extreme case: on a frame with no background at all, a
    lone count beside zeros passes the neighbour test whatever the factor
    (its neighbours' mean is 0) and the floor (about 4 on an empty frame),
    so the pass removes it. C62's realistic sparse frames, with background,
    never had a clean frame touched at factor 10; the owner's own sparse
    frames are the check before a default (DATA_NEEDS 16, rule 12)."""
    img = np.zeros((synth.PIL_W, synth.PIL_H))
    img[PEAK[1], PEAK[0]] = 6.0                              # the reflected beam: six counts in one pixel
    off, _ = _row(img, None)
    on, info = _row(img, 40.0)
    assert off[3] == pytest.approx(6.0 / MON) and info['roi_corrected'] == [(PEAK[0], PEAK[1])]
    assert on[3] == 0.0                                      # the signal is gone


def test_exp_reflectivity_restores_a_point_with_a_hot_background_pixel(tmp_path):
    """main man's end-to-end case (issue #55): a 5000-count pixel in a
    background box of one frame (scan 1's last, the weakest). Off (the
    default) the point loses half the pixel's excess, as C62's mechanism
    says (net = signal − (left + right)/2); at factor 10 the point comes
    back and every other point is the same."""
    from lss_core.experiment import Experiment
    from lss_core.display import roi_boxes
    spec = synth.make_dataset(tmp_path / 'data')
    clean = Experiment(spec).reflectivity([1, 2])
    exp = Experiment(spec)
    f = [x for x in exp.frames([1]) if x.index == 8][0]
    det = TwoDDetector('Pilatus')
    det.openFile(f.path)
    img = np.array(det.imageData, float)
    _, info = reflectivity.frame_row(det, img, np.sqrt(img), f.monitor, f.beam_xy, f.qz, (21, 11), 0.5, 'H',
                                     f.distance, False)
    (_, (r0, r1, c0, c1)) = [b for b in roi_boxes((21, 11), info['centre'], bg=info['bg'], direction='H')
                             if b[0] == 'right'][0]
    img[(r0 + r1) // 2, (c0 + c1) // 2] = 5000.0
    synth.write_pilatus_tif(f.path, img)
    off = Experiment(spec).reflectivity([1, 2])
    on = Experiment(spec).reflectivity([1, 2], roi_bad_pixel_factor=10.0)
    a, b, c = clean.per_scan[1], off.per_scan[1], on.per_scan[1]
    excess = 5000.0 - img[(r0 + r1) // 2, (c0 + c1) // 2 + 1]
    assert (a[8, 1] - b[8, 1]) * f.monitor == pytest.approx(excess / 2, rel=0.02)   # off: half taken away
    assert c[8, 1] == pytest.approx(a[8, 1], rel=1e-3)          # on: restored
    others = [k for k in range(len(a)) if k != 8]
    assert np.array_equal(c[others], a[others]) and np.array_equal(on.per_scan[2], clean.per_scan[2])
    assert np.array_equal(off.per_scan[2], clean.per_scan[2])


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
