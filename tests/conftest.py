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
# keep every log the program writes out of the repository and sample data
import tempfile  # noqa: E402
os.environ['LSS_READER_LOG_DIR'] = tempfile.mkdtemp(prefix='lss_reader_test_logs_')
# draw image-list selections at once (the 150 ms merge of rapid clicks is
# tested on its own in test_lss_core.py)
os.environ['LSS_READER_SELECTION_DELAY_MS'] = '0'
# never write to the user's disk cache from the tests
os.environ['LSS_READER_DISK_CACHE'] = tempfile.mkdtemp(prefix='lss_reader_test_cache_')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

import pytest  # noqa: E402


@pytest.fixture(scope='session')
def qapp():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(['lss-reader-tests'])
    yield app


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
    w.close()
    w.deleteLater()
    qapp.processEvents()


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
