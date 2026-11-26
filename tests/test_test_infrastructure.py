"""The test suite's own machinery: windows freed after every test, nothing
left on disk, parallel by default (2026-11-23, docs/TESTING.md).

Measured before these: a quick run held about 10 GB in its one process
(every window of every test stayed alive), took 9 min 44 s, and left
1.2 GB and 121 folders in the temporary folder."""
import gc
import os

import pytest

import conftest
import sweep


def _windows_alive():
    import mainwindow
    gc.collect()
    return [o for o in gc.get_objects() if isinstance(o, mainwindow.MainWindow)]


@pytest.mark.gui
def test_free_windows_really_deletes_a_loaded_window(qapp, recorder, dataset, tmp_path):
    """close() + deleteLater() + processEvents() left the window alive (no
    event loop runs in the tests, so deferred deletes wait forever, and the
    window's own signal connections keep its Python side)."""
    from PyQt5 import sip
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    sweep.state_pilatus_two_scans_all_frames(w, qapp, dataset)
    w.close()
    w.deleteLater()
    qapp.processEvents()
    assert not sip.isdeleted(w)                        # the old fixture's teardown: still there
    assert conftest.free_windows(qapp) == []
    assert sip.isdeleted(w)
    del w
    assert _windows_alive() == []
    assert recorder.exceptions == []


@pytest.mark.gui
def test_free_windows_keeps_a_slot_exception_from_aborting(qapp):
    """By teardown the recorder's excepthook is gone, and PyQt5 aborts the
    process on an unhandled slot exception: free_windows collects them."""
    from PyQt5 import QtWidgets

    class Grumpy(QtWidgets.QWidget):
        def closeEvent(self, event):
            raise RuntimeError('refuses to close quietly')
    g = Grumpy()
    g.show()
    raised = conftest.free_windows(qapp)
    assert [type(v) for _, v, _ in raised] == [RuntimeError]
    from PyQt5.QtCore import Qt
    assert all(w.windowType() == Qt.Desktop for w in qapp.topLevelWidgets())


def test_tmp_path_kept_only_for_failures(pytestconfig):
    assert pytestconfig.getini('tmp_path_retention_policy') == 'failed'
    assert int(pytestconfig.getini('tmp_path_retention_count')) == 1


def test_temporary_folders_and_cache_budget_of_the_test_process():
    for var in ('LSS_READER_LOG_DIR', 'LSS_READER_DISK_CACHE'):
        assert os.path.isdir(os.environ[var]) and os.path.basename(os.environ[var]).startswith('lss_reader_test_')
    assert os.environ['LSS_READER_RAM_CACHE_MB'] == '512'


@pytest.mark.gui
def test_sweep_output_folders_are_inside_the_tests_tmp_path(window, qapp, dataset, tmp_path):
    """They were made in the system's temporary folder and never removed."""
    sweep.state_spec_loaded(window, qapp, dataset)
    assert os.path.commonpath([window.directory, str(tmp_path)]) == str(tmp_path)
    assert os.path.basename(window.directory).startswith('lss-sweep-out-')


def test_parallel_unless_benchmarking_or_regenerating(monkeypatch, pytestconfig):
    class Config:
        def __init__(self, mark):
            self.mark = mark

        def getoption(self, name, default=None):
            return self.mark
    for k in conftest.SERIAL_ENV:
        monkeypatch.delenv(k, raising=False)
    assert not conftest._wants_serial(Config("not sweep and not slow and not bench"))
    assert not conftest._wants_serial(Config('slow'))
    assert conftest._wants_serial(Config('bench'))
    monkeypatch.setenv('LSS_UPDATE_CRASHES', '1')
    assert conftest._wants_serial(Config('sweep'))


def test_auto_workers_fit_the_cpus_and_the_memory(monkeypatch):
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)   # Windows
    assert 1 <= conftest.pytest_xdist_auto_num_workers(None) <= cpus
    monkeypatch.setattr(conftest, '_available_memory_mb', lambda: 3 * conftest.WORKER_MEMORY_MB)
    assert conftest.pytest_xdist_auto_num_workers(None) == min(cpus, 3)
    monkeypatch.setattr(conftest, '_available_memory_mb', lambda: 100)
    assert conftest.pytest_xdist_auto_num_workers(None) == 1


@pytest.mark.gui
def test_sweep_parts_cover_every_control_once(qapp, recorder, tmp_path):
    """The crash sweep shares each state among SWEEP_PARTS tests: together
    they trigger every control, none twice."""
    import test_gui_sweep
    from mainwindow import MainWindow

    def make():
        w = MainWindow()
        w.directory = str(tmp_path)
        return w
    n = test_gui_sweep.SWEEP_PARTS
    every = sweep.control_keys(make, qapp, recorder)
    parts = [sweep.control_keys(make, qapp, recorder, (i, n)) for i in range(n)]
    assert sorted(k for p in parts for k in p) == sorted(every) and len(every) > 100
    assert all(p for p in parts)


@pytest.mark.gui
def test_a_menu_shown_with_exec_returns_at_once(qapp, recorder):
    """A QPushButton with a menu opens it with QMenu.exec, which waited
    forever offscreen (the sweep's random walk hung on the prototype
    window's button, 2026-11-23). The recorder makes it return, like a
    dialog; a timer closes any real menu after 2 s so that a missing stub
    fails here instead of hanging."""
    import time
    from PyQt5 import QtCore, QtWidgets
    button = QtWidgets.QPushButton('provenance')
    menu = QtWidgets.QMenu(button)
    menu.addAction('one')
    button.setMenu(menu)
    button.show()
    QtCore.QTimer.singleShot(2000, menu.close)
    t = time.perf_counter()
    button.click()
    qapp.processEvents()
    assert time.perf_counter() - t < 1.0
    assert recorder.menus and recorder.menus[-1] is menu
    assert QtWidgets.QMenu.exec([menu.actions()[0]], QtCore.QPoint(0, 0)) is None    # the static form
    assert recorder.exceptions == []
