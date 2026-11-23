"""Shared fixtures.

The application loads its .ui files relative to the working directory and
needs a QApplication, so tests run from the repository root on the offscreen
Qt platform. Modal dialogs are replaced by recorders so nothing blocks, and
exceptions raised inside Qt slots are collected instead of aborting the
interpreter.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLBACKEND', 'Agg')
# keep every log the program writes out of the repository and sample data;
# the three temporary folders made here are removed when the process ends
import atexit  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402


def _temp_folder(prefix):
    path = tempfile.mkdtemp(prefix=prefix)
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    return path


os.environ['LSS_READER_LOG_DIR'] = _temp_folder('lss_reader_test_logs_')
# draw image-list selections at once (the 150 ms merge of rapid clicks is
# tested on its own in test_lss_core.py)
os.environ['LSS_READER_SELECTION_DELAY_MS'] = '0'
# preferences go to a temporary file, never to ~/.lss_reader
os.environ['LSS_READER_PREFS'] = os.path.join(_temp_folder('lss_reader_test_prefs_'), 'preferences.json')
# never write to the user's disk cache from the tests
os.environ['LSS_READER_DISK_CACHE'] = _temp_folder('lss_reader_test_cache_')
# the image cache's default budget is a quarter of the machine's memory (4 GB
# here) in every test process; each test's data are new files, never hit again
os.environ.setdefault('LSS_READER_RAM_CACHE_MB', '512')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

import pytest  # noqa: E402

@pytest.fixture(scope='session')
def qapp():
    import gc
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(['lss-reader-tests'])
    import mainwindow  # noqa: F401  (imported once, then frozen:)
    gc.collect()
    gc.freeze()        # import-time objects skip every later collection (115 -> 3-16 ms)
    yield app


def free_windows(app):
    """Delete every top-level window and dialog still open, and free them.

    A window closed with close() + deleteLater() is not deleted when no
    event loop runs (processEvents does not handle deferred deletes), and
    the window's own signal connections keep its Python side alive: each
    test leaked a whole window (about 110 MB with data). Exceptions raised
    by slots meanwhile are collected and returned, not left to abort the
    process (PyQt5 aborts on an unhandled slot exception).
    """
    import gc
    from PyQt5 import QtCore
    raised = []
    hook = sys.excepthook
    sys.excepthook = lambda t, v, tb: raised.append((t, v, tb))
    try:
        for w in app.topLevelWidgets():
            if w.windowType() != QtCore.Qt.Desktop:
                w.close()
                w.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        app.processEvents()
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    finally:
        sys.excepthook = hook
    if 'matplotlib.pyplot' in sys.modules:
        sys.modules['matplotlib.pyplot'].close('all')
    gc.collect()
    return raised


@pytest.fixture(autouse=True)
def _free_windows_after_qt_tests(request):
    """After a test that used Qt, nothing of it stays in memory."""
    yield
    if 'qapp' in request.fixturenames:
        free_windows(request.getfixturevalue('qapp'))


@pytest.fixture(autouse=True)
def _fresh_preferences():
    """Every test starts from the default preferences (lss_core.preferences)."""
    p = os.environ['LSS_READER_PREFS']
    if os.path.exists(p):
        os.remove(p)
    yield


@pytest.fixture(autouse=True)
def _repo_cwd():
    """Restore the working directory after every test."""
    yield
    os.chdir(ROOT)


class Recorder:
    """What the application tried to show or raise during a test."""

    def __init__(self):
        self.messages = []      # text of every message shown to the user
        self.failures = []      # 'Operation failed' reports (real program only)
        self.dialogs = []       # QDialog instances whose exec_ was called
        self.exceptions = []    # (type, value, traceback) from Qt slots
        self.open_name = ''     # returned by QFileDialog.getOpenFileName
        self.open_names = []    # returned by QFileDialog.getOpenFileNames
        self.save_name = ''     # returned by QFileDialog.getSaveFileName
        self.directory = ''     # returned by QFileDialog.getExistingDirectory
        self.question = None    # returned by QMessageBox.question (None = No)


@pytest.fixture
def recorder(qapp, monkeypatch):
    from PyQt5 import QtWidgets
    rec = Recorder()

    def box_exec(self, *a, **k):
        rec.messages.append(self.text())
        return QtWidgets.QMessageBox.Ok

    def dialog_exec(self, *a, **k):
        rec.dialogs.append(self)
        return 0

    def static_box(*a, **k):
        rec.messages.append(' | '.join(str(x) for x in a[1:3]))
        if rec.question is not None:
            return rec.question
        return QtWidgets.QMessageBox.No

    # Messages no longer open dialogs: MainWindow.notify appends them to the
    # Messages pane and the log. Record them here too, so tests can assert
    # what the user was told.
    import mainwindow
    real_notify = mainwindow.MainWindow.notify

    def notify(self, text, title='Warning', level='warning'):
        if title != 'Error':            # 'Error' = an exception, see .failures
            rec.messages.append(str(text))
        else:
            rec.failures.append(str(text))
        return real_notify(self, text, title, level)

    monkeypatch.setattr(mainwindow.MainWindow, 'notify', notify)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'exec_', box_exec)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'exec', box_exec)
    for name in ('question', 'information', 'warning', 'critical', 'about'):
        monkeypatch.setattr(QtWidgets.QMessageBox, name, staticmethod(static_box))
    monkeypatch.setattr(QtWidgets.QDialog, 'exec_', dialog_exec)
    monkeypatch.setattr(QtWidgets.QDialog, 'exec', dialog_exec)
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *a, **k: (rec.open_name, '')))
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileNames',
                        staticmethod(lambda *a, **k: (list(rec.open_names), '')))
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName',
                        staticmethod(lambda *a, **k: (rec.save_name, '')))
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getExistingDirectory',
                        staticmethod(lambda *a, **k: rec.directory))
    monkeypatch.setattr(QtWidgets.QInputDialog, 'getMultiLineText',      # the Save note: OK, no note
                        staticmethod(lambda *a, **k: ('', True)))
    monkeypatch.setattr(QtWidgets.QInputDialog, 'getText',
                        staticmethod(lambda *a, **k: ('', False)))
    monkeypatch.setattr(sys, 'excepthook',
                        lambda t, v, tb: rec.exceptions.append((t, v, tb)))
    import time
    monkeypatch.setattr(time, 'sleep', lambda s: None)
    return rec


@pytest.fixture
def window(qapp, recorder, tmp_path):
    """A fresh MainWindow whose default output directory is tmp_path."""
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    qapp.processEvents()
    yield w
    free_windows(qapp)


@pytest.fixture
def dataset(tmp_path):
    """Path of a synthetic SPEC file with pilatus/ and vortex/ beside it."""
    import synth
    return synth.make_dataset(tmp_path / 'data')


@pytest.fixture
def loaded(window, dataset, qapp):
    """MainWindow with the synthetic SPEC file opened."""
    window.openSpecFile(fname=dataset)
    qapp.processEvents()
    return window
