"""One reader writes a SPEC file's workbook; a second opens it read-only (D1).

The owner's requirement (FEATURE_REQUESTS D1): "Two people can have the same
SPEC file open. The second instance opens the config **read-only**, and a
small **yellow indicator light** in the GUI shows that state." The config is
the per-SPEC workbook (``lss_core.workbook``: settings, masks, saved results),
saved by writing a temporary file and replacing the old one, so two readers
saving it would silently overwrite each other's results.

``ReaderLock(workbook_path)`` keeps ``<workbook>.lock`` beside it, a small
JSON file naming the holder (host, process, user, program version, when it
was taken and last refreshed):

- ``acquire()`` takes the lock if it is free and returns True (this reader
  writes), or returns False and fills ``holder`` (this reader is read-only).
  Taking it is atomic (the file is created exclusively).
- A lock is **stale**, and is taken over, when its file has not been
  refreshed for ``STALE_S`` seconds (its holder crashed or lost its network
  share), or when its holder is a process on this host that no longer runs.
  A takeover writes the new lock and reads it back: when two readers take a
  stale lock at once, the one whose lock is not in the file afterwards is
  read-only.
- ``refresh()`` (every ``REFRESH_S`` seconds, a window timer) keeps the lock
  alive; it returns False if another reader has taken it meanwhile (after a
  long sleep), and this reader is then read-only.
- ``release()`` removes the lock if it is this reader's: the owner's "one
  click" to give up the write access (2026-11-25, Q5; the lock is taken when
  the SPEC file is first opened).
- A read-only reader calls ``acquire()`` again from time to time; it gets
  the lock once the other reader has closed or released (``try_again``).
- **Asking for it:** a read-only reader's ``request_release()`` writes
  ``<workbook>.lock.request`` naming it. The holder's ``release_requested()``
  (checked with each refresh) returns that request, so its window can offer
  the release; nothing changes hands by itself. ``decline_request()`` removes
  it; the next ``acquire()`` that succeeds removes any request left.

Staleness is judged from the file's modification time against this host's
clock, so the hosts' clocks must agree to well within ``STALE_S``; a file
that cannot be read is judged by its age alone. Nothing here raises for a
lock that cannot be written (a read-only folder, D3): ``acquire()`` then
returns False with the reason in ``holder``, and the reader carries on
read-only.
"""
import getpass
import json
import os
import socket
import time

LOCK_SUFFIX = '.lock'
REQUEST_SUFFIX = '.request'      # beside the lock: <workbook>.lock.request
REFRESH_S = 30.0     # the holder rewrites the lock this often
STALE_S = 180.0      # a lock not refreshed for this long is taken over (6 missed refreshes)


def _me():
    try:
        user = getpass.getuser()
    except Exception:            # no user name on some systems
        user = ''
    from .workbook import program_version
    return dict(host=socket.gethostname(), pid=os.getpid(), user=user, program=program_version())


def _alive(pid):
    """Whether process ``pid`` runs on this host (POSIX; True where unknown)."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name != 'posix':
        return True                # no cheap check: the lock's age decides
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:        # another user's process: it runs
        return True
    except OSError:
        return True
    return True


class ReaderLock:
    """The write lock of one workbook (module docstring)."""

    def __init__(self, workbook_path, stale_s=STALE_S):
        self.path = str(workbook_path) + LOCK_SUFFIX
        self.stale_s = float(stale_s)
        self.me = dict(_me(), token='%s-%d-%.6f' % (socket.gethostname(), os.getpid(), time.time()))
        self.mine = False
        self.holder = None          # who holds it when this reader does not (a dict), or why it could not be taken
        self.request_path = self.path + REQUEST_SUFFIX

    # ---- state -----------------------------------------------------------------

    @property
    def writable(self):
        return self.mine

    def read(self):
        """The lock file's content (a dict), {} when unreadable, None when absent."""
        try:
            with open(self.path) as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            return {}

    def age(self):
        """Seconds since the lock file was last written (None when absent)."""
        try:
            return max(time.time() - os.path.getmtime(self.path), 0.0)
        except OSError:
            return None

    def is_stale(self, content=None):
        content = self.read() if content is None else content
        if content is None:
            return True
        age = self.age()
        if age is not None and age > self.stale_s:
            return True
        if content and content.get('host') == self.me['host'] and not _alive(content.get('pid')):
            return True
        return False

    def describe(self):
        """A line for the window's tooltip: who writes this workbook."""
        if self.mine:
            return 'this reader writes the workbook'
        h = self.holder or {}
        if 'reason' in h:
            return 'read-only: %s' % h['reason']
        who = '%s on %s' % (h.get('user') or 'another reader', h.get('host') or 'another computer')
        since = h.get('started')
        return 'read-only: %s has it open%s' % (who, ' since %s' % since if since else '')

    # ---- taking and keeping it ---------------------------------------------------

    def _content(self, started=None):
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        return dict(self.me, started=started or now, refreshed=now)

    def _write_exclusive(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, 'w') as f:
            json.dump(self._content(), f)

    def _replace(self, started=None):
        tmp = '%s.%s.tmp' % (self.path, self.me['token'])
        with open(tmp, 'w') as f:
            json.dump(self._content(started), f)
        os.replace(tmp, self.path)

    def _is_mine(self, content):
        return bool(content) and content.get('token') == self.me['token']

    def acquire(self):
        """True when this reader now holds the lock (it writes the workbook);
        False when another reader does, or the lock cannot be written (``holder``
        says which)."""
        if self.mine:
            return self.refresh()
        try:
            self._write_exclusive()
            self.mine, self.holder = True, None
            self._clear_request()
            return True
        except FileExistsError:
            pass
        except OSError as e:
            self.mine, self.holder = False, dict(reason='the lock cannot be written (%s)' % e.strerror)
            return False
        content = self.read()
        if not self.is_stale(content):
            self.mine, self.holder = False, content or dict(reason='the lock file cannot be read')
            return False
        try:                                     # a stale lock: take it over, then check that it is ours
            self._replace()
        except OSError as e:
            self.mine, self.holder = False, dict(reason='the lock cannot be written (%s)' % e.strerror)
            return False
        after = self.read()
        self.mine = self._is_mine(after)
        self.holder = None if self.mine else (after or dict(reason='the lock file cannot be read'))
        if self.mine:
            self._clear_request()
        return self.mine

    try_again = acquire

    def refresh(self):
        """Keep the lock alive (the holder, every REFRESH_S). False, and this
        reader becomes read-only, when the file is no longer this reader's."""
        if not self.mine:
            return False
        content = self.read()
        if not self._is_mine(content):
            self.mine, self.holder = False, content or dict(reason='the lock was removed')
            return False
        try:
            self._replace(started=content.get('started'))
        except OSError as e:
            self.mine, self.holder = False, dict(reason='the lock cannot be written (%s)' % e.strerror)
            return False
        return True

    def release(self):
        """Remove the lock if it is this reader's (the one click that gives up
        the write access); a reader that asked for it gets it on its next
        ``try_again``."""
        if self.mine and self._is_mine(self.read()):
            try:
                os.remove(self.path)
            except OSError:
                pass
        self.mine = False

    # ---- asking the holder to release it -------------------------------------------

    def request_release(self, note=''):
        """A read-only reader asks the holder to give up the write access:
        writes ``request_path`` naming this reader (and ``note``). True when
        written; False for the holder itself or when it cannot be written."""
        if self.mine:
            return False
        tmp = '%s.%s.tmp' % (self.request_path, self.me['token'])
        try:
            with open(tmp, 'w') as f:
                json.dump(dict(self.me, asked=time.strftime('%Y-%m-%d %H:%M:%S'), note=str(note)), f)
            os.replace(tmp, self.request_path)
        except OSError:
            return False
        return True

    def release_requested(self):
        """The holder: the pending request (a dict naming who asked, when and
        why) or None. A request this reader wrote itself is ignored."""
        if not self.mine:
            return None
        try:
            with open(self.request_path) as f:
                content = json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            content = dict(reason='a request that cannot be read')
        if content.get('token') == self.me['token']:
            return None
        return content

    def decline_request(self):
        """The holder keeps the write access: the pending request is removed."""
        if self.mine:
            self._clear_request()

    def _clear_request(self):
        try:
            os.remove(self.request_path)
        except FileNotFoundError:
            pass
        except OSError:
            pass
