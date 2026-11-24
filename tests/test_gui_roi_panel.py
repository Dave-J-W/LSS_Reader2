"""The ROI close-up panel in the window (F71; image_display.md §2.4 R1-R6).

Owner, 2026-11-23: a side panel, always visible beside the frame, the same
for both tabs (Q-IMG-7); one panel, the box moved to the found peak and the
old box dashed (Q-IMG-16). The numbers shown are the reduction's own sums:
Ref Patch's rows on the Pilatus tab, Analyze's R on the Reflectivity tab.
Synthetic data: scans 1 and 2, a Gaussian reflected peak (σ = 2 px)."""
import numpy as np
import pytest

import sweep
from lss_core import display, reflectivity
from TwoDDetector import TwoDDetector

pytestmark = pytest.mark.gui


@pytest.fixture(autouse=True)
def _ticks_by_hand(request):
    """The movie is stepped by hand (as in test_gui_movie.py): real ticks race on a loaded machine."""
    if 'loaded' in request.fixturenames:
        w = request.getfixturevalue('loaded')
        w.pilMovieTimer.timeout.disconnect(w.pilMovieTick)
    yield


def _all_of(w, qapp, rows):
    sweep._select_scans(w, qapp, rows)
    sweep._select_images(w, qapp)
    w.flushPendingSelection()
    qapp.processEvents()


def _as_ref_patch(w, i):
    """frame_row on a fresh detector, with the window's fields: Ref Patch's row of frame i."""
    d = TwoDDetector('Pilatus')
    d.errors = w.pilatus.errors
    slit = [int(v) for v in w.ui.refSlitLineEdit.text().split(',')]
    frames = list(w.selectedPilFramesNums)
    first = next(j for j in frames if w.pilScanNum[j] == w.pilScanNum[i]) == i
    row, info = reflectivity.frame_row(d, w.pilData[i], w.pilErrorData[i], w.pilMonc[i], (w.pilX[i], w.pilY[i]),
                                       w.pilFileQzs[i], slit, float(w.ui.refBGOffLineEdit.text()),
                                       str(w.ui.refBGDirComboBox.currentText()), w.pil_Dist[i], low_qz_slit=first)
    return row, info, d


def test_the_pilatus_panel_follows_the_movie_with_ref_patchs_sums(loaded, qapp, recorder):
    w = loaded
    _all_of(w, qapp, [0])
    assert w.pilMode == 'movie' and not w.ui.pilRoiPanel.isHidden()
    frames = list(w.selectedPilFramesNums)
    for k in (0, 1, 4):
        w.pilMovieShowFrame(k)
        qapp.processEvents()
        v = w.pilRoi.view
        assert v is not None and v['frame'] == frames[k] and v['title'].startswith('S# 1 pt %d' % k)
        row, info, d = _as_ref_patch(w, frames[k])
        assert v['sums'] == tuple(d.roiParts['values']) + (row[1], row[2])            # exactly
        assert v['boxes'] == display.roi_boxes(info['slit'], info['centre'], info['bg'], 'H')
        for name, b in v['boxes']:                                                    # the pixels outlined: summed
            assert display.box_sum(d.imageData, b) in d.roiParts['values']
        # R2: the same boxes outlined on the frame, in its axes' coordinates
        ax = w.pilView['axes'][0]
        x0, x1, y0, y1 = ax.images[0].get_extent()
        shape = w.pilData[frames[k]].shape
        for (name, b), patch in zip(v['boxes'], w.pilView['rois'][0]):
            assert patch.get_visible() and patch.axes is ax
            assert patch.get_x() == pytest.approx(x0 + b[2] * (x1 - x0) / shape[1])
            assert patch.get_y() == pytest.approx(y0 + b[0] * (y1 - y0) / shape[0])
            assert patch.get_width() == pytest.approx((b[3] - b[2]) * (x1 - x0) / shape[1])
    assert 'net' in w.ui.pilRoiNumbersLabel.text()
    assert w.ui.pilRoiCuesLabel.text()                                                # a cue or 'no cue'
    for name in ('pilRoiLogCheckBox', 'pilRoiNumbersLabel', 'pilRoiCuesLabel', 'pilRoiCursorLabel'):
        assert getattr(w.ui, name).toolTip(), name
    assert 'P12' in w.ui.pilRoiNumbersLabel.toolTip() and 'Q-IMG-7' in w.ui.pilRoiCuesLabel.toolTip()
    assert recorder.exceptions == []


def test_the_panel_numbers_are_ref_patchs_rows(loaded, qapp, recorder):
    """Ref Patch run over both scans; each frame's close-up shows that frame's row of the patch (S, B1,
    B2, net, σ), value for value, before any join factor."""
    w = loaded
    _all_of(w, qapp, [0, 1])
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    rows = {k: np.array(v, dtype=float, copy=True) for k, v in w.scanqzframe.items()}
    w.ui.PlotWidget.setCurrentWidget(w.ui.pilatusTab)
    frames = list(w.selectedPilFramesNums)
    seen = {}
    for k, i in enumerate(frames):
        w.pilMovieShowFrame(k)
        s = w.pilRoi.view['sums']
        scan = int(w.pilScanNum[i])
        r = rows[scan][seen.setdefault(scan, 0)]
        seen[scan] += 1
        assert (r[1], r[2], r[3], r[4], r[5], r[6]) == (s[6], s[7], s[0], s[1], s[2], s[4])
    assert seen == {1: 9, 2: 7}
    assert recorder.exceptions == []


def test_typed_roi_fields_move_the_boxes_at_once(loaded, qapp, recorder):
    w = loaded
    _all_of(w, qapp, [0])
    w.ui.refSlitLineEdit.setText('15,7')
    w.ui.refSlitLineEdit.returnPressed.emit()
    qapp.processEvents()
    sig = dict(w.pilRoi.view['boxes'])['signal']
    assert (sig[1] - sig[0], sig[3] - sig[2]) == (7, 15)
    w.ui.refBGDirComboBox.setCurrentIndex(w.ui.refBGDirComboBox.findText('V'))
    qapp.processEvents()
    assert [n for n, _ in w.pilRoi.view['boxes']] == ['signal', 'up', 'down']
    w.ui.refSlitLineEdit.setText('abc')
    w.ui.refSlitLineEdit.returnPressed.emit()
    qapp.processEvents()
    assert w.pilRoi.view is None and not any(p.get_visible() for p in w.pilView['rois'][0])
    assert recorder.exceptions == []


def test_the_panel_is_hidden_for_frames_without_a_roi(loaded, qapp, recorder, monkeypatch):
    w = loaded
    _all_of(w, qapp, [0])
    assert not w.ui.pilRoiPanel.isHidden()
    monkeypatch.setattr(w, 'scanSeriesKind', lambda n: 'gid')                       # as if a GID series
    w.pilSetKind()
    w.pilDrawFrames()
    assert w.ui.pilRoiPanel.isHidden()
    assert not any(p.get_visible() for p in w.pilView['rois'][0])
    monkeypatch.undo()
    sweep._select_images(w, qapp, [0])                                               # one frame, summed
    w.flushPendingSelection()
    w.ui.gixSumCheckBox.setChecked(True)                                             # "Sum All": no ROI drawn
    w.pilDrawFrames()
    assert w.pilMode == 'sum' and not w.ui.pilRoiPanel.isHidden() and w.pilRoi.view is None
    assert 'Sum All' in w.pilRoi.art['note'].get_text()
    assert not any(p.get_visible() for p in w.pilView['rois'][0])
    assert recorder.exceptions == []


def test_boxes_moved_by_the_peak_search_leave_dashed_ones(loaded, qapp, recorder):
    """Q-IMG-16: the box moved to the found peak, the old box dashed. Ref Patch's peakLocate starts
    from the SPEC beam position; here that is put 2 columns off the peak, which it finds again."""
    w = loaded
    _all_of(w, qapp, [0])
    i = w.selectedPilFramesNums[0]
    w.pilX[i] = w.pilX[i] + 2
    w.pilMovieShowFrame(0)
    v = w.pilRoi.view
    assert dict(v['boxes'])['signal'][2:] == (87, 108)                            # centred on column 97
    assert dict(v['old'])['signal'][2:] == (85, 106)                              # the SPEC position
    assert [p.get_visible() for p in w.pilRoi.art['old']] == [True, True, True]
    assert all(p.get_linestyle() == '--' for p in w.pilRoi.art['old'])
    assert 'dashed' in w.ui.pilRoiNumbersLabel.toolTip()
    w.pilMovieShowFrame(1)                                                          # a frame where it did not move
    assert w.pilRoi.view['old'] is None and not any(p.get_visible() for p in w.pilRoi.art['old'])
    assert recorder.exceptions == []


def test_log_is_one_setting_for_both_panels(loaded, qapp, recorder):
    w = loaded
    _all_of(w, qapp, [0])
    assert w.ui.pilRoiLogCheckBox.isChecked() and w.ui.refRoiLogCheckBox.isChecked()   # log by default (F71)
    w.ui.pilRoiLogCheckBox.setChecked(False)
    qapp.processEvents()
    assert not w.ui.refRoiLogCheckBox.isChecked() and w.pilDisplay['roi_log'] is False
    assert type(w.pilRoi.art['im'].norm).__name__ == 'Normalize'
    assert w.pilRoi.art['axc'].get_yscale() == 'linear'
    w.ui.refRoiLogCheckBox.setChecked(True)
    assert w.ui.pilRoiLogCheckBox.isChecked() and w.pilRoi.art['axc'].get_yscale() == 'log'
    assert recorder.exceptions == []


def test_the_reflectivity_tab_shows_the_same_panel_and_analyzes_r(loaded, qapp, recorder):
    """One panel (Q-IMG-16): before Analyze the boxes at the starting centre (typed here); after it,
    the numbers are R and R_Err. Analyze's peakFind keeps the centre fixed (cenfit, as coded: "Peak
    searching is dummy"), so the boxes stay and none is dashed. Before 2026-11-24 two strips with the
    box borders burned into their pixels (setROI) and a right background box drawn 2 px away from the
    one summed (image_display.md §1.5)."""
    w = loaded
    _all_of(w, qapp, [0])
    w.ui.pilRefPushButton.click()
    qapp.processEvents()
    w.ui.refCenCheckBox.setChecked(True)                      # Ref unticks it
    w.ui.refCenLineEdit.setText('100,98')                     # the box 3 px right of the peak, 2 rows low
    w.ui.refQzListWidget.clearSelection()
    w.ui.refQzListWidget.item(2).setSelected(True)
    qapp.processEvents()
    v = w.refRoi.view
    assert v is not None and v['old'] is None and dict(v['boxes'])['signal'] == (93, 104, 90, 111)
    assert 'before Analyze' in w.ui.refRoiNumbersLabel.toolTip()
    assert 'off centre' in w.ui.refRoiCuesLabel.text()        # 3 px > 25 % of the half-width (2.6 px)
    w.ui.refAnalyzePushButton.click()
    qapp.processEvents()
    v = w.refRoi.view
    s = v['sums']
    assert ('%.4e' % s[6], '%.4e' % s[7]) == (w.ui.refRLineEdit.text(), w.ui.refRErrLineEdit.text())
    assert dict(v['boxes'])['signal'] == (93, 104, 90, 111) and v['old'] is None
    assert not any(p.get_visible() for p in w.refRoi.art['old'])
    assert 'after Analyze' in w.ui.refRoiNumbersLabel.toolTip()
    images = [im for ax in w.ui.refADDataPlotWidget.canvas.fig.axes for im in ax.get_images()]
    assert len(images) == 1                                     # one close-up, no burned strip
    assert np.max(images[0].get_array()) == np.max(w.pilatus.imageData)   # no border written as 100 x max
    assert recorder.exceptions == []


def test_the_close_ups_cursor_reads_the_pixel_under_it(loaded, qapp, recorder):
    """R6: before, format_coord_ref swapped rows and columns and used the Pilatus tab's extent."""
    from matplotlib.backend_bases import MouseEvent
    w = loaded
    _all_of(w, qapp, [0])
    panel = w.pilRoi
    canvas = panel.canvas
    canvas.draw()
    ax = panel.art['ax']
    x, y = ax.transData.transform((97.0, 100.0))
    ev = MouseEvent('motion_notify_event', canvas, x, y)
    canvas.callbacks.process('motion_notify_event', ev)
    img = panel.view['image']
    assert w.ui.pilRoiCursorLabel.text() == 'col 97, row 100: %.4g' % img[100, 97]
    assert recorder.exceptions == []
