"""The test suite's own machinery: windows freed after every test, nothing
left on disk (2026-11-23, docs/TESTING.md).

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
