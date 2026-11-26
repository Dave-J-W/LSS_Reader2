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
    """With the opening lock off (LSS_READER_LOCK_AT_OPEN=0, the tests'
    setting) the lock is taken when the workbook is first needed."""
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


# ---- the owner's revised Q5 (2026-11-25): the lock on opening, given up in one click, asked for ----

def test_the_lock_is_taken_when_the_spec_file_is_opened(window, qapp, recorder, dataset, monkeypatch):
    monkeypatch.setenv('LSS_READER_LOCK_AT_OPEN', '1')
    w = window
    w.openSpecFile(fname=dataset)
    qapp.processEvents()
    assert os.path.exists(w.workbookPath() + readerlock.LOCK_SUFFIX) and w.readerLock.writable
    assert not os.path.exists(w.workbookPath())                       # the lock only, no workbook yet
    assert not w.readOnlyLight.isVisibleTo(w)
    assert w.ui.actionGiveUpWriteAccess.isEnabled() and not w.ui.actionAskWriteAccess.isEnabled()
    w.openSpecFile(fname=dataset)                                      # the same file again: still this reader's
    assert w.readerLock.writable
    assert recorder.exceptions == []


def test_a_second_reader_opening_the_file_is_read_only_at_once(loaded, qapp, recorder, dataset, monkeypatch):
    monkeypatch.setenv('LSS_READER_LOCK_AT_OPEN', '1')
    _held_elsewhere(loaded)
    loaded.openSpecFile(fname=dataset)
    qapp.processEvents()
    assert not loaded.readerLock.writable and loaded.readOnlyLight.isVisibleTo(loaded)
    assert any('open in another reader' in m and 'gives up its write access' in m for m in recorder.messages)
    assert not any('reader: read-only:' in m for m in recorder.messages)     # said once, not twice
    assert loaded.ui.actionAskWriteAccess.isEnabled() and not loaded.ui.actionGiveUpWriteAccess.isEnabled()
    assert recorder.exceptions == []


def test_giving_up_the_write_access_is_one_click_and_is_not_undone_by_itself(loaded, qapp, recorder):
    w = loaded
    _quiet(w)
    w.openWorkbook()
    assert w.readerLock.writable
    w.ui.actionGiveUpWriteAccess.trigger()
    lock = w.workbookPath() + readerlock.LOCK_SUFFIX
    assert not os.path.exists(lock) and not w.readerLock.writable
    assert w.readOnlyLight.isVisibleTo(w) and 'You gave up' in w.readOnlyLight.toolTip()
    assert any(m.startswith('You gave up the write access') for m in recorder.messages)
    w.readerLockTick()                                                 # the lock is free, but not taken back
    assert not w.readerLock.writable and not os.path.exists(lock)
    _save_ref(w, qapp)
    assert not os.path.exists(w.workbookPath())                        # nothing saved (Q6)
    assert any('you gave up the write access' in m and 'takes it back' in m for m in recorder.messages)
    w.ui.actionAskWriteAccess.trigger()                                # free: taken back at once
    assert w.readerLock.writable and os.path.exists(lock) and not w.readOnlyLight.isVisibleTo(w)
    assert recorder.exceptions == []


def test_a_request_for_the_write_access_offers_release(loaded, qapp, recorder):
    from PyQt5.QtWidgets import QMessageBox
    w = loaded
    _quiet(w)
    w.openWorkbook()
    other = readerlock.ReaderLock(w.workbookPath())                   # a second reader, read-only
    assert not other.acquire()
    assert other.request_release(note='second shift')
    w.readerLockTick()
    box = w.releaseRequestBox
    assert box is not None and box.isVisible() and not box.isModal()  # the work goes on
    assert any('asks for the write access' in m and 'second shift' in m for m in recorder.messages)
    n = len(recorder.messages)
    w.readerLockTick()                                                 # said once per request
    assert len(recorder.messages) == n and w.releaseRequestBox is box
    [b for b in box.buttons() if box.buttonRole(b) == QMessageBox.AcceptRole][0].click()   # Release
    qapp.processEvents()
    assert not w.readerLock.writable and w.releaseRequestBox is None
    assert other.try_again() and other.writable                        # the asker takes it
    assert recorder.exceptions == []


def test_keep_declines_the_request(loaded, qapp, recorder):
    from PyQt5.QtWidgets import QMessageBox
    w = loaded
    _quiet(w)
    w.openWorkbook()
    other = readerlock.ReaderLock(w.workbookPath())
    other.acquire()
    other.request_release()
    w.readerLockTick()
    box = w.releaseRequestBox
    [b for b in box.buttons() if box.buttonRole(b) == QMessageBox.RejectRole][0].click()   # Keep
    qapp.processEvents()
    assert w.readerLock.writable and not os.path.exists(other.request_path)
    assert w.readerLock.release_requested() is None
    assert recorder.exceptions == []


def test_a_read_only_reader_asks_the_holder(loaded, qapp, recorder):
    w = loaded
    _quiet(w)
    _held_elsewhere(w)
    w.openWorkbook()
    assert not w.readerLock.writable
    w.ui.actionAskWriteAccess.trigger()
    with open(w.readerLock.request_path) as f:
        req = json.load(f)
    assert req['token'] == w.readerLock.me['token']
    assert any(m.startswith('Asked colleague on beamline-pc-2') for m in recorder.messages)
    assert w.readOnlyLight.actions() == [w.ui.actionAskWriteAccess]    # also on the light's right-click menu
    assert recorder.exceptions == []


def test_a_share_the_user_cannot_write_to(window, qapp, recorder, dataset, monkeypatch):
    """The common beamline case (main man, issue #55, 2026-11-26): the SPEC
    file is on a share this user cannot write to. With the opening lock on,
    the file opens, the reader is read-only with one message, and nothing is
    raised; the timer's retries add no more messages. (chmod does nothing for
    root in the cloud, so the lock's exclusive create is refused here.)"""
    import errno
    real_open = os.open

    def refuse(path, flags, *a, **k):
        if str(path).endswith(readerlock.LOCK_SUFFIX):
            raise PermissionError(errno.EACCES, 'Permission denied', str(path))
        return real_open(path, flags, *a, **k)
    monkeypatch.setattr(os, 'open', refuse)
    monkeypatch.setenv('LSS_READER_LOCK_AT_OPEN', '1')
    w = window
    _quiet(w)
    w.openSpecFile(fname=dataset)
    qapp.processEvents()
    assert not w.readerLock.writable and w.readOnlyLight.isVisibleTo(w)
    said = [m for m in recorder.messages if 'cannot be saved here' in m]
    assert len(said) == 1 and 'Permission denied' in said[0]
    assert not any('open in another reader' in m for m in recorder.messages)
    assert not os.path.exists(w.workbookPath() + readerlock.LOCK_SUFFIX)
    n = len(recorder.messages)
    w.readerLockTick()                                                 # tried again: still refused, quietly
    assert not w.readerLock.writable and len(recorder.messages) == n
    _save_ref(w, qapp)
    assert not os.path.exists(w.workbookPath())                        # nothing written
    assert any(m.startswith('Not saved: read-only: the lock cannot be written') for m in recorder.messages)
    assert recorder.exceptions == []
