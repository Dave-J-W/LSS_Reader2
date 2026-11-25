"""Dropped points kept as a mask in the Ref Patch window (F92; owner,
2026-11-23: "saved as a mask in the config file (the per-SPEC state), and a
'Restore all' button is included in the patch dialog"; the core is main
man's lss_core.masks and reflectivity.drop_points).

A finished patch's drops become (scan, point) pairs in the workbook's mask;
the next Ref Patch of those scans leaves them out from the start, as
``exp.reflectivity(mask=...)`` does, and draws them apart; Restore all
clears the mask of the patch's scans and starts the patch again.
"""
import numpy as np
import pytest

import sweep
from lss_core import masks, workbook
from lss_core.experiment import Experiment

pytestmark = pytest.mark.gui


def _quiet(w):
    w.prefs['auto_save'] = False
    w.prefs['save_asks_note'] = False


def _patch(w, qapp):
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()


def _click(qapp, button):
    button.click()
    qapp.processEvents()


def _drop(w, qapp, text):
    w.uirefpatch.dropLineEdit.setText(text)
    _click(qapp, w.uirefpatch.dropPushButton)


def _stored(w):
    return masks.load(workbook.Workbook(w.workbookPath())).pairs()


def _masked_lines(ax):
    return [l for l in ax.lines if l.get_gid() == 'masked']


def test_drops_are_kept_and_left_out_from_the_start_next_time(loaded, qapp, recorder, dataset):
    """A drop of the new scan at the first join and the mask give the same
    curve (the core's rule: no earlier fit used that point), and the window's
    curve is the script's with mask=."""
    w = loaded
    _quiet(w)
    _patch(w, qapp)
    full = len(w.scanqzframe[2])
    _drop(w, qapp, '0')
    _click(qapp, w.uirefpatch.nextPushButton)            # Finish!
    assert _stored(w) == [[2, 0]]
    assert any('kept as the mask' in m and 'S2 pt 0' in m for m in recorder.messages)
    first = np.array(w.refData, dtype=float)
    _patch(w, qapp)                                      # the same frames again
    assert len(w.scanqzframe[2]) == full - 1 and w.refMaskUsed == [(2, 0)]
    assert any('left out from the start' in m for m in recorder.messages)
    assert len(_masked_lines(w.uirefpatch.plotWidget.canvas.ax)) == 1    # drawn apart while patching
    _click(qapp, w.uirefpatch.nextPushButton)
    assert np.array(w.refData, dtype=float) == pytest.approx(first, rel=1e-12)
    line = w.reflectivityScript('x').split('\n')[0]
    assert 'mask=[[2, 0]]' in line and 'drops=' not in line
    ns = {'exp': Experiment(dataset)}
    exec(line, ns)
    assert np.array(w.refData, dtype=float)[:, :3] == pytest.approx(ns['ref'].patched[:, :3], rel=1e-10)
    assert '1 masked' in w.refProvenanceLabel.text()
    assert recorder.exceptions == []


def test_masked_points_are_drawn_apart_on_the_reflectivity_tab(loaded, qapp, recorder):
    w = loaded
    _quiet(w)
    _patch(w, qapp)
    q0 = float(w.scanqzframe[2][0, 0])
    _drop(w, qapp, '0')
    _click(qapp, w.uirefpatch.nextPushButton)
    assert _masked_lines(w.ui.refRefDataPlotwidget.canvas.ax) == []       # dropped this time: not masked yet
    _patch(w, qapp)
    _click(qapp, w.uirefpatch.nextPushButton)
    w.ui.refRRFCheckBox.setChecked(False)
    w.ui.refQzSqrCheckBox.setChecked(False)
    w.updateRefPlotData()
    (line,) = _masked_lines(w.ui.refRefDataPlotwidget.canvas.ax)
    assert list(line.get_xdata()) == pytest.approx([q0]) and np.all(np.asarray(line.get_ydata()) > 0)
    assert 'masked (1)' == line.get_label()
    assert recorder.exceptions == []


def test_restore_all_clears_the_mask_and_starts_again(loaded, qapp, recorder):
    w = loaded
    _quiet(w)
    _patch(w, qapp)
    full = len(w.scanqzframe[2])
    _drop(w, qapp, '0')
    _click(qapp, w.uirefpatch.nextPushButton)
    _patch(w, qapp)
    assert len(w.scanqzframe[2]) == full - 1
    old = w.uirefpatch
    _click(qapp, old.restoreAllPushButton)
    assert _stored(w) == [] and w.refMaskUsed == []
    assert any('Restored 1 masked point' in m for m in recorder.messages)
    assert w.uirefpatch is not old and w.uirefpatch.isVisible() and len(w.scanqzframe[2]) == full
    assert not any('cancelled' in m or 'abandoned' in m for m in recorder.messages)
    _click(qapp, w.uirefpatch.restoreAllPushButton)          # nothing left to restore: said, nothing restarted
    assert any('Nothing to restore' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_back_and_cancel_keep_only_what_was_finished(loaded, qapp, recorder):
    w = loaded
    _quiet(w)
    _patch(w, qapp)
    _drop(w, qapp, '0')
    _drop(w, qapp, '5')                                  # a point of scan 2 above the overlap
    _click(qapp, w.uirefpatch.backPushButton)            # undone
    _click(qapp, w.uirefpatch.nextPushButton)
    assert _stored(w) == [[2, 0]]
    _patch(w, qapp)
    _drop(w, qapp, '5')
    w.uirefpatch.reject()                                # Cancel: nothing recorded
    qapp.processEvents()
    assert _stored(w) == [[2, 0]]
    assert recorder.exceptions == []
