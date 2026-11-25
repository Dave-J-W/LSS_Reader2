"""One reader writes a SPEC file's workbook; a second opens it read-only
(D1's core, 2026-11-25; lss_core.readerlock, Workbook(read_only=True)).

Invariant (I43): at most one reader holds a workbook's lock at a time, even
when two take over a stale lock at once; a read-only workbook never writes."""
import json
import os
import subprocess
import sys
import time

import pytest

from lss_core import readerlock
from lss_core.workbook import Workbook, WorkbookReadOnly


def _wb(tmp_path):
    return str(tmp_path / 'x_reader.xlsx')


def _other(path, **kw):
    """A lock file written by another reader."""
    content = dict(host='elsewhere', pid=12345, user='someone', token='other', started='2026-11-25 10:00:00',
                   refreshed='2026-11-25 10:00:00')
    content.update(kw)
    with open(path + readerlock.LOCK_SUFFIX, 'w') as f:
        json.dump(content, f)


def test_the_second_reader_is_read_only_until_the_first_closes(tmp_path):
    a, b = readerlock.ReaderLock(_wb(tmp_path)), readerlock.ReaderLock(_wb(tmp_path))
    assert a.acquire() and a.writable
    assert not b.acquire() and not b.writable
    assert b.holder['host'] and b.holder['pid'] == os.getpid() and 'read-only' in b.describe()
    assert a.describe() == 'this reader writes the workbook'
    assert a.refresh() and a.acquire()                     # the holder keeps it
    a.release()
    assert not os.path.exists(a.path)
    assert b.try_again() and b.writable                     # the other gets it once the first has closed
    assert not a.acquire()
    b.release()


def test_a_stale_lock_is_taken_over(tmp_path):
    p = _wb(tmp_path)
    _other(p)
    lock = readerlock.ReaderLock(p)
    assert not lock.acquire()                               # fresh: someone else's
    old = time.time() - readerlock.STALE_S - 10
    os.utime(lock.path, (old, old))                         # not refreshed for longer than STALE_S
    assert lock.acquire() and lock.read()['token'] == lock.me['token']


@pytest.mark.skipif(os.name != 'posix', reason='no cheap check of a process on Windows: only the lock\'s age decides')
def test_a_dead_process_on_this_host_leaves_a_stale_lock(tmp_path):
    p = _wb(tmp_path)
    done = subprocess.Popen([sys.executable, '-c', 'pass'])
    done.wait()
    import socket
    _other(p, host=socket.gethostname(), pid=done.pid)
    assert readerlock.ReaderLock(p).acquire()


def test_a_live_process_on_this_host_keeps_its_lock(tmp_path):
    """Everywhere: a fresh lock of a running process is not taken over."""
    import socket
    p = _wb(tmp_path)
    _other(p, host=socket.gethostname(), pid=os.getpid())   # alive (this very process, another token)
    assert not readerlock.ReaderLock(p).acquire()


def test_an_unreadable_lock_is_judged_by_its_age(tmp_path):
    p = _wb(tmp_path)
    with open(p + readerlock.LOCK_SUFFIX, 'w') as f:
        f.write('not json')
    lock = readerlock.ReaderLock(p)
    assert not lock.acquire() and 'cannot be read' in lock.describe()
    old = time.time() - readerlock.STALE_S - 10
    os.utime(lock.path, (old, old))
    assert lock.acquire()


def test_two_readers_taking_a_stale_lock_at_once_one_wins(tmp_path):
    p = _wb(tmp_path)
    _other(p)
    old = time.time() - readerlock.STALE_S - 10
    os.utime(p + readerlock.LOCK_SUFFIX, (old, old))
    a, b = readerlock.ReaderLock(p), readerlock.ReaderLock(p)
    real = a._replace

    def race(started=None):               # b writes its takeover just after a's
        real(started)
        b._replace()
    a._replace = race
    assert not a.acquire() and not a.writable               # a reads b's lock back: read-only
    assert b._is_mine(b.read())
    b.mine = True
    assert b.refresh() and not a.refresh()


def test_refresh_notices_a_lock_taken_meanwhile(tmp_path):
    p = _wb(tmp_path)
    a = readerlock.ReaderLock(p)
    assert a.acquire()
    _other(p)                                               # e.g. after a long sleep, another reader took it
    assert not a.refresh() and not a.writable and a.holder['token'] == 'other'
    a.release()
    assert os.path.exists(a.path)                           # not removed: it is not a's


def test_a_lock_that_cannot_be_written_means_read_only_not_an_error(tmp_path):
    blocker = tmp_path / 'a_file'
    blocker.write_text('x')
    lock = readerlock.ReaderLock(str(blocker / 'sub' / 'x_reader.xlsx'))   # its folder cannot be made
    assert not lock.acquire() and 'cannot be written' in lock.describe()


def test_a_read_only_workbook_never_writes(tmp_path):
    p = _wb(tmp_path)
    w = Workbook(p)
    w.set_settings('fit', {'shape': 'gaussian'})
    w.save()
    before = open(p, 'rb').read()
    r = Workbook(p, read_only=True)
    assert r.settings('fit') == {'shape': 'gaussian'}       # reads as usual
    r.set_settings('fit', {'shape': 'lorentzian'})          # changes in memory only
    with pytest.raises(WorkbookReadOnly):
        r.save()
    assert open(p, 'rb').read() == before and not os.path.exists(p + '.tmp')
    fresh = str(tmp_path / 'new_reader.xlsx')
    with pytest.raises(WorkbookReadOnly):
        Workbook(fresh, read_only=True).save()
    assert not os.path.exists(fresh)
    assert issubclass(WorkbookReadOnly, PermissionError)


def test_a_read_only_reader_asks_and_the_holder_releases(tmp_path):
    """The owner's revised Q5 (2026-11-25): one click gives up the write access, and the next reader takes
    it. A request changes nothing by itself; the holder sees it, and releasing hands the lock over."""
    a, b = readerlock.ReaderLock(_wb(tmp_path)), readerlock.ReaderLock(_wb(tmp_path))
    assert a.acquire() and not b.acquire()
    assert a.release_requested() is None and b.release_requested() is None
    assert not a.request_release()                          # the holder does not ask itself
    assert b.request_release(note='I need to save a fit')
    req = a.release_requested()
    assert req['note'] == 'I need to save a fit' and req['host'] and req['asked']
    assert a.writable and not b.try_again()                 # nothing changed hands by itself
    a.release()
    assert b.try_again() and b.writable
    assert not os.path.exists(b.request_path)               # taking the lock clears the request
    assert b.release_requested() is None
    b.release()


def test_the_holder_may_decline_and_old_requests_do_not_linger(tmp_path):
    a, b = readerlock.ReaderLock(_wb(tmp_path)), readerlock.ReaderLock(_wb(tmp_path))
    assert a.acquire() and b.request_release()
    a.decline_request()
    assert a.release_requested() is None and a.writable and not os.path.exists(a.request_path)
    b.decline_request()                                     # only the holder declines: a no-op here
    assert b.request_release()
    a.release()
    c = readerlock.ReaderLock(_wb(tmp_path))
    assert c.acquire() and c.release_requested() is None    # a request left from before is cleared
    c.release()
