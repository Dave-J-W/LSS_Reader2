"""Ref Patch checks as a message and marks, not modal boxes (F95; owner,
2026-11-23, Q-UI-B6 and B3).

Before: a frame whose beam centre was more than 2 px from the expected one,
or one with corrected bad pixels inside the signal box, opened a modal box
(pilPeakCenDialog, pilBadPixDialog) before the patch window. Now one
message says which frames, the points are marked on the Reflectivity plot
once the patch is on show, and the bad pixels are listed per Qz in the
tab's "Bad Pixels" list (unused until now).
"""
import os

import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

SHIFTED = (2, 3)          # scan 2, frame 3: its beam drawn 5 px away from where the geometry puts it
QZ2 = np.linspace(0.04, 0.10, 7)


def _shifted_dataset(root):
    spec = synth.make_dataset(root)
    scan, frame = SHIFTED
    r, c = synth.PIL_H - synth.DB_X - 1, synth.DB_Y
    amp = synth.PEAK_AMPLITUDE * synth.reflectivity(QZ2[frame]) / synth.ABSFAC
    synth.write_pilatus_tif(os.path.join(str(root), 'pilatus', 'sample_SCAN-%d_%04d.tif' % (scan, frame)),
                            synth.pilatus_image(peak=(r, c + 5), amplitude=amp))
    return spec


@pytest.fixture
def checked(window, qapp, tmp_path):
    spec = _shifted_dataset(tmp_path / 'data')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    window.prefs['auto_save'] = False
    sweep._select_scans(window, qapp, [0, 1])
    sweep._select_images(window, qapp)
    return window


def _frame_index(w, scan, frame):
    return next(i for i in range(len(w.pilScanNum)) if int(w.pilScanNum[i]) == scan and int(w.pilFrameNum[i]) == frame)


def test_an_off_centre_beam_is_a_message_and_a_mark_not_a_box(checked, qapp, recorder):
    checked.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert recorder.dialogs == []                          # no modal box
    said = [m for m in recorder.messages if 'beam centre is more than 2 px' in m]
    assert len(said) == 1 and 'scan 2: frame 3' in said[0] and 'marked' in said[0]
    assert [(f['scan'], f['frame']) for f in checked.refFlagsPending if f['kind'] == 'centre'] == [SHIFTED]
    assert getattr(checked, 'refFlags', []) == []          # not on show until the patch is
    checked.uirefpatch.nextPushButton.click()             # Finish
    qapp.processEvents()
    (k,) = checked.refFlagMarks['centre']
    assert checked.normRefData[k, 0] == pytest.approx(QZ2[SHIFTED[1]])
    labels = [l.get_label() for l in checked.ui.refRefDataPlotwidget.canvas.ax.get_lines()]
    assert 'beam off centre (> 2 px)' in labels
    assert 'beam centre more than 2 px off in 1 frame' in checked.refProvenanceLabel.toolTip()
    checked.ui.refLogYCheckBox.setChecked(True)            # a redraw keeps the mark
    qapp.processEvents()
    assert checked.refFlagMarks['centre'] == [k]
    assert recorder.exceptions == []


def test_bad_pixels_in_the_roi_are_listed_per_qz_and_marked(checked, qapp, recorder):
    i = _frame_index(checked, 1, 4)
    w, h = checked.pilData[i].shape
    checked.pilbadpixLoc[i] = [[y, x] for y in range(h) for x in range(w)]    # every pixel: those in the box are kept
    checked.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert recorder.dialogs == []
    said = [m for m in recorder.messages if 'bad pixels lie inside the signal box' in m]
    assert len(said) == 1 and 'scan 1: frame 4' in said[0]
    lst = checked.ui.refBadPixListWidget
    assert lst.count() == 0                                # listed with the result, not before
    checked.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert lst.count() == 1
    row = lst.item(0).text()
    assert row.startswith('Qz 0.0300  S# 1 F# 4: (') and lst.toolTip()
    (bad,) = [f for f in checked.refFlags if f['kind'] == 'badpix']
    sw, sh = checked.slit
    assert len(bad['pixels']) == sw * sh                   # the pixels strictly inside the signal box
    (k,) = checked.refFlagMarks['badpix']
    assert checked.normRefData[k, 0] == pytest.approx(0.03)
    assert recorder.exceptions == []


def test_a_cancelled_patch_keeps_the_checks_of_the_result_on_show(checked, qapp, recorder):
    checked.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    checked.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    flags, marks = list(checked.refFlags), dict(checked.refFlagMarks)
    checked.ui.pilRefPatchPushButton.click()              # again, then cancelled
    qapp.processEvents()
    checked.uirefpatch.cancelPushButton.click()
    qapp.processEvents()
    checked.updateRefPlotData()
    assert checked.refFlags == flags and checked.refFlagMarks == marks
    assert recorder.exceptions == []


def test_a_later_patch_without_findings_clears_the_marks(checked, qapp, recorder):
    checked.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    checked.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert checked.refFlagMarks
    sweep._select_scans(checked, qapp, [0])                # scan 1 alone: no flagged frame; one scan,
    sweep._select_images(checked, qapp)                    # so the curve is on show at once
    checked.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert checked.refFlags == [] and checked.refFlagMarks == {}
    assert checked.ui.refBadPixListWidget.count() == 0
    assert recorder.exceptions == []


def test_a_point_dropped_from_the_curve_has_no_mark(checked, qapp, recorder):
    checked.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    d = checked.uirefpatch
    d.dropLineEdit.setText('3')                            # scan 2's point 3: the off-centre frame (Qz 0.07)
    d.dropPushButton.click()
    qapp.processEvents()
    d.nextPushButton.click()
    qapp.processEvents()
    assert not np.any(np.isclose(checked.normRefData[:, 0], QZ2[SHIFTED[1]]))
    assert 'centre' not in checked.refFlagMarks
    assert recorder.exceptions == []
