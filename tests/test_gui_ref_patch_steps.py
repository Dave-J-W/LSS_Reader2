"""The Ref Patch window's Back, Cancel and join table, and the line under
the Reflectivity plot that says how the result on show was made (F96;
owner, 2026-11-23, Q-UI-B7 and Q-UI-B5).

Invariant (Q-UI-B7, ``docs/physics_notes.md``): going Back and doing the
same steps again gives the same reflectivity, value for value, as never
going back; a cancelled patch leaves the result on show, and what
describes it (Script pane, recipe), as they were.
"""
import json
import os

import numpy as np
import pytest

import sweep
import synth
from lss_core import workbook

pytestmark = pytest.mark.gui


def _quiet(w):
    w.prefs['auto_save'] = False          # saved only when the test says so
    w.prefs['save_asks_note'] = False


@pytest.fixture
def patch(loaded, qapp, dataset):
    """The patch window on scans 1 and 2 (one join)."""
    _quiet(loaded)
    sweep._select_scans(loaded, qapp, [0, 1])
    sweep._select_images(loaded, qapp)
    loaded.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    return loaded


def _three_scan_patch(w, qapp):
    """Scans 1, 2 and its repeat 3, not merged: the patch window with two joins."""
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatchsamescan.nextPushButton.click()        # "Finish!" without merging
    qapp.processEvents()
    assert w.uirefpatch.isVisible() and len(w.pilrefsort) == 3


@pytest.fixture
def three(window, qapp, tmp_path):
    spec = synth.make_identical_scans_dataset(tmp_path / 'same')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    _quiet(window)
    sweep._select_scans(window, qapp, [0, 1, 2])
    sweep._select_images(window, qapp)
    _three_scan_patch(window, qapp)
    return window


def _click(qapp, button):
    button.click()
    qapp.processEvents()


def test_the_window_has_back_cancel_and_a_join_table(patch, recorder):
    d = patch.uirefpatch
    assert d.backPushButton.text() == '<< Back' and not d.backPushButton.isEnabled()
    assert d.cancelPushButton.text() == 'Cancel'
    t = d.joinTableWidget
    assert [t.horizontalHeaderItem(i).text() for i in range(t.columnCount())] == list(patch.REF_JOIN_COLUMNS)
    assert t.rowCount() == 1                               # the join on show
    assert t.item(0, 1).text() == '1 → 2' and t.item(0, 0).font().italic()
    assert 'on show' in t.item(0, 6).text()
    for w in (d.backPushButton, d.cancelPushButton, t):
        assert w.toolTip()
    assert recorder.exceptions == []


def test_back_undoes_a_drop(patch, qapp, recorder):
    d = patch.uirefpatch
    before = {k: v.copy() for k, v in patch.scanqzframe.items()}
    d.dropLineEdit.setText('0')
    _click(qapp, d.dropPushButton)
    assert len(patch.scanqzframe[2]) == len(before[2]) - 1
    assert d.backPushButton.isEnabled() and d.joinTableWidget.item(0, 5).text() == '0'
    _click(qapp, d.backPushButton)
    for k in before:
        assert np.array_equal(patch.scanqzframe[k], before[k])
    assert patch.refDrops == {} and not d.backPushButton.isEnabled()
    assert d.joinTableWidget.item(0, 5).text() == ''
    patch.pilRefPatchBack()                                # the button is off; called anyway, it says so
    assert any('Nothing to go back to' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_back_returns_to_the_previous_join_as_it_was_left(three, qapp, recorder):
    d = three.uirefpatch
    d.dropLineEdit.setText('0')
    _click(qapp, d.dropPushButton)                         # join 1: drop scan 2's first point
    after_drop = {k: v.copy() for k, v in three.scanqzframe.items()}
    _click(qapp, d.nextPushButton)                         # accept join 1
    assert three.pilreforder == 1 and len(three.refJoins) == 1
    assert d.joinTableWidget.rowCount() == 2               # the accepted join and the one on show
    assert d.nextPushButton.text() == 'Finish!'
    _click(qapp, d.backPushButton)
    assert three.pilreforder == 0 and three.refJoins == []
    assert three.refDrops == {0: [[0]]}                    # its drop kept
    for k in after_drop:
        assert np.array_equal(three.scanqzframe[k], after_drop[k])
    assert d.nextPushButton.text() == 'Next>>'
    assert d.joinTableWidget.rowCount() == 1
    assert recorder.exceptions == []


def test_back_then_the_same_steps_give_the_same_reflectivity(three, qapp, recorder):
    """The invariant: Back and redo changes nothing."""
    d = three.uirefpatch
    d.dropLineEdit.setText('0')
    _click(qapp, d.dropPushButton)
    _click(qapp, d.nextPushButton)
    _click(qapp, d.backPushButton)                         # back to join 1 ...
    _click(qapp, d.nextPushButton)                         # ... and on again
    d.dropLineEdit.setText('-1')
    _click(qapp, d.dropPushButton)
    _click(qapp, d.backPushButton)                         # undo that drop ...
    d.dropLineEdit.setText('-1')
    _click(qapp, d.dropPushButton)                         # ... and make it again
    _click(qapp, d.nextPushButton)                         # Finish
    with_back = np.array(three.refData, dtype=float)
    joins_back = [dict(r) for r in three.refResultJoins]
    assert three.ui.PlotWidget.currentWidget() is three.ui.refTab

    _three_scan_patch(three, qapp)                         # the same steps, never going back
    d = three.uirefpatch
    d.dropLineEdit.setText('0')
    _click(qapp, d.dropPushButton)
    _click(qapp, d.nextPushButton)
    d.dropLineEdit.setText('-1')
    _click(qapp, d.dropPushButton)
    _click(qapp, d.nextPushButton)
    straight = np.array(three.refData, dtype=float)
    # (the unmerged repeat overlaps its scan entirely: the legacy join leaves NaN and inf errors
    # there, the same on both paths)
    assert np.array_equal(with_back, straight, equal_nan=True)
    assert joins_back == three.refResultJoins
    assert [r['dropped'] for r in joins_back] == [[0], [-1]]
    assert recorder.exceptions == []


@pytest.mark.parametrize('how', ['cancel', 'close', 'escape'])
def test_cancel_says_so_and_leaves_the_result_on_show(patch, qapp, recorder, how):
    d = patch.uirefpatch
    _click(qapp, d.nextPushButton)                         # a first result: scans 1 and 2
    shown = np.array(patch.refData, dtype=float)
    script = patch.reflectivityScript('r')
    line = patch.refProvenanceLabel.text()
    patch.ui.pilRefPatchPushButton.click()                 # a second patch ...
    qapp.processEvents()
    d = patch.uirefpatch
    d.dropLineEdit.setText('0')
    _click(qapp, d.dropPushButton)                         # ... with a drop, then stopped
    recorder.messages.clear()
    if how == 'cancel':
        _click(qapp, d.cancelPushButton)
    elif how == 'close':
        d.close()
        qapp.processEvents()
    else:
        d.reject()
        qapp.processEvents()
    assert not d.isVisible()
    said = [m for m in recorder.messages if 'cancelled' in m]
    assert len(said) == 1 and 'join 1 of 1 (scans 1 and 2)' in said[0] and 'unchanged' in said[0]
    assert np.array_equal(np.array(patch.refData, dtype=float), shown)
    assert patch.reflectivityScript('r') == script         # no drops= from the cancelled patch
    assert patch.refDrops == {}
    patch.updateRefProvenance()
    assert patch.refProvenanceLabel.text() == line
    assert recorder.exceptions == []


def test_finishing_is_not_a_cancel(patch, qapp, recorder):
    _click(qapp, patch.uirefpatch.nextPushButton)
    assert not any('cancelled' in m for m in recorder.messages)
    assert patch.refResultJoins and patch.refResultJoins[0]['scans'] == [1, 2]
    assert recorder.exceptions == []


def test_a_new_patch_replaces_an_unfinished_one_and_says_so(patch, qapp, recorder):
    old = patch.uirefpatch
    patch.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert not old.isVisible() and patch.uirefpatch is not old and patch.uirefpatch.isVisible()
    assert any('abandoned' in m for m in recorder.messages)
    assert not any('cancelled' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_closing_the_identical_scans_window_says_so(window, qapp, recorder, tmp_path):
    spec = synth.make_identical_scans_dataset(tmp_path / 'same')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0, 1, 2])
    sweep._select_images(window, qapp)
    window.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    recorder.messages.clear()
    window.uirefpatchsamescan.close()
    qapp.processEvents()
    assert any('cancelled in the identical-scans window' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_the_join_table_is_kept_with_the_result_and_saved(patch, qapp, recorder):
    d = patch.uirefpatch
    d.dropLineEdit.setText('0')
    _click(qapp, d.dropPushButton)
    _click(qapp, d.nextPushButton)
    (row,) = patch.refResultJoins
    assert row['join'] == 1 and row['scans'] == [1, 2] and row['dropped'] == [0]
    assert patch.refMethodUsed == 'joint'
    # the synthetic overlap is too short for the joint fit: the legacy fit stands in, and the note says so
    assert row['source'] == ('legacy' if 'legacy fit used' in row['note'] else 'joint')
    assert row['factor'] > 0 and row['error'] > 0
    patch.saveButtons['ref'].click()
    qapp.processEvents()
    book = workbook.Workbook(patch.workbookPath())
    saved = [r for r in book.results(kind='reflectivity') if r['label'] == 'R']
    assert len(saved) == 1
    assert json.loads(saved[0]['settings'])['joins'] == [row]
    assert recorder.exceptions == []


def test_the_line_under_the_plot_says_how_the_result_was_made(patch, qapp, recorder):
    lab = patch.refProvenanceLabel
    assert lab.text() == ''                                # nothing on show yet
    d = patch.uirefpatch
    d.dropLineEdit.setText('0')
    _click(qapp, d.dropPushButton)
    _click(qapp, d.nextPushButton)
    text, tip = lab.text(), lab.toolTip()
    for part in ('joint patch', 'legacy errors', 'scans 1, 2', '1 point dropped'):
        assert part in text, (part, text)
    assert 'join 1, scans 1 → 2' in tip and 'dropped 0' in tip and 'Errors: legacy' in tip
    assert 'saved' not in text                             # the workbook is not open: not checked
    patch.saveButtons['ref'].click()
    qapp.processEvents()
    assert lab.text().endswith('saved v1')
    assert 'Saved: R v1' in lab.toolTip()
    # sits under the result plot, above the Export row
    lay = patch.ui.refTab.layout()
    assert lay.indexOf(lab) == lay.indexOf(patch.ui.splitter_2) + 1
    assert recorder.exceptions == []


def test_the_line_follows_the_method_the_patch_used_not_the_preference(patch, qapp, recorder):
    _click(qapp, patch.uirefpatch.nextPushButton)
    patch.setPreference('ref_patch_method', 'legacy')      # changed after the patch was made
    patch.updateRefProvenance()
    assert 'joint patch' in patch.refProvenanceLabel.text()
    assert recorder.exceptions == []
