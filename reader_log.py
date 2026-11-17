"""Durable logging and last-resort error handling for LSS_Reader.

Nothing here needs Qt to be imported, so it can be used from scripts and
tests. Three things live here:

* a log that survives a crash: every record is flushed and synced to disk
  before the call returns, and hard faults below Python (segmentation
  faults, aborts) are written to the same folder by ``faulthandler``;
* a per-SPEC-file log, written beside the SPEC file, or in a local folder
  when that is not possible;
* ``install_excepthook``: with it, an exception raised while handling a
  button press is logged and reported, and the program carries on. Without
  it PyQt5 aborts the whole process.

Where the files go
------------------
Session log:   <log dir>/session-<date>-<time>-<pid>.log
Hard faults:   <log dir>/session-<date>-<time>-<pid>.fault.log
Per SPEC file: <spec file>.reader.log beside the SPEC file; if that folder
               cannot be written, <log dir>/spec/<name>-<hash>.reader.log

<log dir> is ``$LSS_READER_LOG_DIR`` if set, otherwise ``~/.lss_reader/logs``.
When ``$LSS_READER_LOG_DIR`` is set the per-SPEC logs go there as well
(used by the tests, and useful when the data folder must not be touched).
The reader never writes to the SPEC file itself.
"""
import faulthandler
import hashlib
import logging
import os
import sys
import threading
import time
import traceback

LOGGER_NAME = 'lss_reader'
ENV_DIR = 'LSS_READER_LOG_DIR'
SPEC_LOG_SUFFIX = '.reader.log'
_FORMAT = '%(asctime)s %(levelname)-7s %(message)s'

_state = {
    'session_path': None,     # path of the session log, once started
    'fault_file': None,       # open file object kept alive for faulthandler
    'spec_handler': None,     # handler of the current per-SPEC log
    'spec_path': None,
    'spec_fallback': False,   # True when the per-SPEC log is not beside the file
    'previous_hook': None,
    'context': None,          # callable returning a dict describing the session
    'report': None,           # callable(text) telling the user something failed
    'failures': 0,
}


class DurableFileHandler(logging.Handler):
    """Append records to a file; flush and fsync after every record.

    Slower than the standard handler, on purpose: a record that has been
    logged is on disk even if the process dies in the next instruction.
    A handler that cannot write disables itself rather than raise.
    """

    def __init__(self, path):
        logging.Handler.__init__(self)
        self.path = path
        self._file = open(path, 'a', encoding='utf-8', errors='replace')
        self.setFormatter(logging.Formatter(_FORMAT))

    def emit(self, record):
        f = self._file
        if f is None:
            return
        try:
            f.write(self.format(record) + '\n')
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass                      # some network file systems refuse
        except Exception:
            self._file = None             # stop trying; never raise from logging

    def close(self):
        f, self._file = self._file, None
        if f is not None:
            try:
                f.close()
            except Exception:
                pass
        logging.Handler.close(self)


def log_dir():
    """The folder for session logs (created if needed), or None."""
    path = os.environ.get(ENV_DIR) or os.path.join(
        os.path.expanduser('~'), '.lss_reader', 'logs')
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except OSError:
        return None


def get_logger():
    """The reader's logger. Safe to call any number of times."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger


def start_session():
    """Open the session log and the hard-fault log. Returns the log path.

    Returns None, and logs nowhere, when no folder can be written; the
    program still runs.
    """
    logger = get_logger()
    if _state['session_path'] is not None:
        return _state['session_path']
    folder = log_dir()
    if folder is None:
        return None
    stem = os.path.join(folder, 'session-%s-%d'
                        % (time.strftime('%Y%m%d-%H%M%S'), os.getpid()))
    try:
        logger.addHandler(DurableFileHandler(stem + '.log'))
    except OSError:
        return None
    _state['session_path'] = stem + '.log'
    try:
        _state['fault_file'] = open(stem + '.fault.log', 'a')
        faulthandler.enable(file=_state['fault_file'], all_threads=True)
    except Exception:
        _state['fault_file'] = None
    logger.info('session started: python %s, pid %d, cwd %s',
                sys.version.split()[0], os.getpid(), os.getcwd())
    return _state['session_path']


def spec_log_path(spec_file):
    """(path, is_fallback) of the log that belongs to ``spec_file``."""
    spec_file = os.path.abspath(spec_file)
    beside = spec_file + SPEC_LOG_SUFFIX
    if not os.environ.get(ENV_DIR):
        folder = os.path.dirname(spec_file)
        try:                               # can we append there?
            with open(beside, 'a'):
                pass
            return beside, False
        except OSError:
            pass
    folder = log_dir()
    if folder is None:
        return None, True
    folder = os.path.join(folder, 'spec')
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        return None, True
    digest = hashlib.sha1(spec_file.encode('utf-8', 'replace')).hexdigest()[:10]
    name = '%s-%s%s' % (os.path.basename(spec_file), digest, SPEC_LOG_SUFFIX)
    return os.path.join(folder, name), not bool(os.environ.get(ENV_DIR))


def attach_spec_log(spec_file):
    """Send log records to the log of ``spec_file`` from now on.

    Returns (path, is_fallback). ``path`` is None when nothing could be
    opened; ``is_fallback`` is True when the log is not beside the SPEC
    file although it should be, which the caller should tell the user.
    """
    logger = get_logger()
    detach_spec_log()
    path, fallback = spec_log_path(spec_file)
    if path is None:
        logger.warning('no log could be opened for SPEC file %s', spec_file)
        return None, True
    try:
        handler = DurableFileHandler(path)
    except OSError:
        logger.warning('could not open %s', path)
        return None, True
    logger.addHandler(handler)
    _state.update(spec_handler=handler, spec_path=path, spec_fallback=fallback)
    logger.info('SPEC file opened: %s', os.path.abspath(spec_file))
    if fallback:
        logger.warning('the folder of the SPEC file is not writable; '
                       'this log is kept at %s instead', path)
    return path, fallback


def detach_spec_log():
    handler = _state['spec_handler']
    if handler is not None:
        get_logger().removeHandler(handler)
        handler.close()
    _state.update(spec_handler=None, spec_path=None, spec_fallback=False)


def _describe_context():
    getter = _state['context']
    if getter is None:
        return ''
    try:
        items = getter() or {}
    except Exception as exc:               # the context itself must never hurt
        return ' [context unavailable: %s]' % type(exc).__name__
    return ''.join('\n    %s: %s' % (k, v) for k, v in items.items())


def log_exception(exc_type, exc, tb, where='while handling an action'):
    """Log an exception with traceback and session context; tell the user."""
    _state['failures'] += 1
    text = ''.join(traceback.format_exception(exc_type, exc, tb)).rstrip()
    get_logger().error('unhandled %s %s%s\n%s', exc_type.__name__, where,
                       _describe_context(), text)
    report = _state['report']
    if report is not None:
        try:
            last = traceback.extract_tb(tb)[-1] if tb is not None else None
            place = (' in %s' % last.name) if last is not None else ''
            report('Operation failed: %s: %s%s. Details are in the log.'
                   % (exc_type.__name__, exc, place))
        except Exception:
            pass


def _hook(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        previous = _state['previous_hook'] or sys.__excepthook__
        previous(exc_type, exc, tb)
        return
    try:
        log_exception(exc_type, exc, tb)
    except Exception:                      # last resort: the original hook
        sys.__excepthook__(exc_type, exc, tb)


def _thread_hook(args):
    if args.exc_type is SystemExit:
        return
    try:
        log_exception(args.exc_type, args.exc_value, args.exc_traceback,
                      where='in thread %s' % getattr(args.thread, 'name', '?'))
    except Exception:
        pass


def install_excepthook(context=None, report=None):
    """Make unhandled exceptions log-and-continue instead of fatal.

    ``context`` is a callable returning a dict that describes the session
    (SPEC file, selection, ...); it is added to every logged exception.
    ``report`` is a callable taking one string, used to tell the user that
    an operation failed. Both are optional and may be replaced by calling
    this function again.
    """
    _state['context'], _state['report'] = context, report
    if sys.excepthook is not _hook:
        _state['previous_hook'] = sys.excepthook
        sys.excepthook = _hook
    threading.excepthook = _thread_hook


def uninstall_excepthook():
    if sys.excepthook is _hook:
        sys.excepthook = _state['previous_hook'] or sys.__excepthook__
    _state.update(previous_hook=None, context=None, report=None)
    threading.excepthook = threading.__excepthook__


def install_qt_message_handler():
    """Route Qt's own warnings and errors into the log."""
    from PyQt5 import QtCore
    levels = {QtCore.QtDebugMsg: logging.DEBUG, QtCore.QtInfoMsg: logging.INFO,
              QtCore.QtWarningMsg: logging.WARNING,
              QtCore.QtCriticalMsg: logging.ERROR,
              QtCore.QtFatalMsg: logging.CRITICAL}

    def handler(mode, context, message):
        get_logger().log(levels.get(mode, logging.WARNING), 'Qt: %s', message)

    QtCore.qInstallMessageHandler(handler)


def failure_count():
    """Number of unhandled exceptions logged in this process."""
    return _state['failures']


def session_log_path():
    return _state['session_path']


def current_spec_log():
    """(path, is_fallback) of the per-SPEC log in use, or (None, False)."""
    return _state['spec_path'], _state['spec_fallback']
