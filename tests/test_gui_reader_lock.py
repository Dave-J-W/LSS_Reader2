"""A second reader of the same SPEC file opens its workbook read-only, with
a yellow light (D1; owner: "Two people can have the same SPEC file open. The
second instance opens the config read-only, and a small yellow indicator
light in the GUI shows that state"). The lock is main man's
lss_core.readerlock; this is the window's side.

Invariant (I43's window side): a read-only reader writes nothing to the
workbook, neither results nor masks; it saves again once the other reader
has closed.
"""
import glob
import json
import os
import socket

import pytest

import sweep
from lss_core import masks, readerlock, workbook

pytestmark = pytest.mark.gui


def _quiet(w):
    w.prefs['auto_save'] = False
    w.prefs['save_asks_note'] = False


def _held_elsewhere(w):
    """A live lock of another reader on another computer, beside w's workbook."""
    path = w.workbookPath() + readerlock.LOCK_SUFFIX
    lk = readerlock.ReaderLock(w.workbookPath())
    other = dict(lk.me, host='beamline-pc-2', user='colleague', pid=1, token='elsewhere')
    with open(path, 'w') as f:
        json.dump(other, f)
    return path


def _save_ref(w, qapp):
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    w.saveButtons['ref'].click()
    qapp.processEvents()


def test_opening_a_spec_file_writes_no_lock(loaded, recorder):
    """The lock is taken when the workbook is first needed, not when the SPEC
    file is opened, so a SPEC file whose workbook is never used gets nothing
    beside it."""
    assert glob.glob(os.path.join(os.path.dirname(loaded.workbookPath()), '*' + readerlock.LOCK_SUFFIX)) == []
    assert not loaded.readOnlyLight.isVisible()
    loaded.openWorkbook()
    assert os.path.exists(loaded.workbookPath() + readerlock.LOCK_SUFFIX) and loaded.readerLock.writable
    assert not loaded.readOnlyLight.isVisible()
    loaded.close()                                       # released on close
    assert not os.path.exists(loaded.workbookPath() + readerlock.LOCK_SUFFIX)
    assert recorder.exceptions == []


def test_a_second_reader_is_read_only_and_saves_nothing(loaded, qapp, recorder):
    w = loaded
    _quiet(w)
    _held_elsewhere(w)
    _save_ref(w, qapp)
    assert w.readOnlyLight.isVisibleTo(w) and 'colleague on beamline-pc-2' in w.readOnlyLight.toolTip()
    assert any('open in another reader' in m for m in recorder.messages)
    assert any(m.startswith('Not saved: read-only') for m in recorder.messages)
    assert not os.path.exists(w.workbookPath())          # nothing written
    assert w.openWorkbook().read_only
    assert recorder.exceptions == []


def test_masks_are_not_written_by_a_read_only_reader(loaded, qapp, recorder):
    w = loaded
    _quiet(w)
    _held_elsewhere(w)
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatch.dropLineEdit.setText('0')
    w.uirefpatch.dropPushButton.click()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert any('not kept as the mask' in m for m in recorder.messages)
    assert not os.path.exists(w.workbookPath())
    assert recorder.exceptions == []


def test_the_reader_saves_again_once_the_other_has_closed(loaded, qapp, recorder):
    w = loaded
    _quiet(w)
    lock = _held_elsewhere(w)
    w.openWorkbook()
    assert not w.readerLock.writable
    w.readerLockTick()                                   # still held: nothing changes
    assert not w.readerLock.writable and w.readOnlyLight.isVisibleTo(w)
    os.remove(lock)                                      # the other reader closed
    w.readerLockTick()
    assert w.readerLock.writable and not w.readOnlyLight.isVisibleTo(w)
    assert any('saves to it again' in m for m in recorder.messages)
    _save_ref(w, qapp)
    assert os.path.exists(w.workbookPath())
    assert 'R' in [r['label'] for r in workbook.Workbook(w.workbookPath()).results('reflectivity')]
    assert recorder.exceptions == []


def test_a_lock_taken_away_makes_the_reader_read_only(loaded, qapp, recorder):
    """After a long sleep another reader may have taken a stale lock: the
    next refresh notices, says so and stops saving."""
    w = loaded
    _quiet(w)
    w.openWorkbook()
    assert w.readerLock.writable
    _held_elsewhere(w)                                   # overwritten by the other reader
    w.readerLockTick()
    assert not w.readerLock.writable and w.readOnlyLight.isVisibleTo(w)
    assert any('Another reader took this workbook' in m for m in recorder.messages)
    assert w.openWorkbook().read_only
    assert recorder.exceptions == []


def test_two_windows_on_one_spec_file(loaded, qapp, recorder, dataset):
    """Two readers in one process (as two people on one computer would be):
    the first to need the workbook writes it, the second is read-only until
    the first closes."""
    from mainwindow import MainWindow
    first = loaded
    _quiet(first)
    first.openWorkbook()
    second = MainWindow()
    second.openSpecFile(fname=dataset)
    qapp.processEvents()
    _quiet(second)
    assert second.workbookPath() == first.workbookPath()
    assert second.openWorkbook().read_only and second.readOnlyLight.isVisibleTo(second)
    assert socket.gethostname() in second.readOnlyLight.toolTip() or 'has it open' in second.readOnlyLight.toolTip()
    first.close()
    second.readerLockTick()
    assert second.readerLock.writable
    sweep.dispose(second, qapp, recorder)
    assert recorder.exceptions == []
