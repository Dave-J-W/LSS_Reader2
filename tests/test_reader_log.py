"""Stage 0: nothing closes the program, and what failed is on disk.

The first tests run the real program in a subprocess, with no test hooks,
because the behaviour being checked (PyQt5 aborting the process when a
button handler raises) cannot be observed from inside pytest.
"""
import glob
import os
import subprocess
import sys

import pytest

import reader_log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_program(code, tmp_path, timeout=180):
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen',
               LSS_READER_LOG_DIR=str(tmp_path / 'logs'))
    return subprocess.run([sys.executable, '-W', 'ignore', '-c', code],
                          cwd=ROOT, env=env, capture_output=True, text=True,
                          timeout=timeout)


START = (
    "import sys\n"
    "import LSS_Reader\n"
    "app, w = LSS_Reader.create_app(['test'])\n"
    "w.show(); app.processEvents()\n")


def test_application_survives_a_raising_handler(tmp_path):
    """Press "Ref Patch" with nothing loaded. Before Stage 0 this ended the
    process with SIGABRT (exit code 134)."""
    out = run_program(START + (
        "w.ui.pilRefPatchPushButton.click(); app.processEvents()\n"
        "w.ui.refAnalyzePushButton.click(); app.processEvents()\n"
        "print('survived', len(w.messages), w.messageDock.isVisible())\n"
        "print('TEXT', w.messageView.toPlainText().replace(chr(10), ' / '))\n"),
        tmp_path)
    assert out.returncode == 0, out.stderr[-2000:]
    assert 'survived 2 True' in out.stdout
    assert 'Operation failed: AttributeError' in out.stdout
    assert 'pilRefPatchData' in out.stdout
    logs = glob.glob(str(tmp_path / 'logs' / 'session-*[0-9].log'))
    assert len(logs) == 1
    text = open(logs[0]).read()
    assert 'session started' in text
    assert text.count('ERROR') == 2
    assert 'Traceback (most recent call last)' in text
    assert "has no attribute 'selectedScanNums'" in text
    # the context of the session is recorded with the failure
    assert 'SPEC file: None' in text and 'tab: SpecPlot' in text


def test_log_is_on_disk_even_if_the_process_is_killed(tmp_path):
    """A record that was logged must survive a hard kill straight after."""
    out = run_program(START + (
        "import os\n"
        "w.notify('about to be killed')\n"
        "w.ui.pilRefPatchPushButton.click(); app.processEvents()\n"
        "os._exit(7)\n"), tmp_path)          # no cleanup, no flushing
    assert out.returncode == 7
    text = open(glob.glob(str(tmp_path / 'logs' / 'session-*[0-9].log'))[0]).read()
    assert 'about to be killed' in text
    assert "has no attribute 'selectedScanNums'" in text


def test_hard_fault_is_recorded(tmp_path):
    """A crash below Python (here a deliberate abort) leaves a trace."""
    out = run_program(START + "import os\nos.abort()\n", tmp_path)
    assert out.returncode != 0
    faults = glob.glob(str(tmp_path / 'logs' / 'session-*.fault.log'))
    assert len(faults) == 1
    assert 'Fatal Python error: Aborted' in open(faults[0]).read()


def test_every_known_crash_site_is_survivable(tmp_path):
    """Drive a handful of the controls listed in known_crashes.json, in the
    real program, one after another; the process must still be alive.
    (Controls that open a file chooser are left out: a real chooser would
    wait for a person.)"""
    out = run_program(START + (
        "names = ['pilRefPatchPushButton', 'pilLineAreaPushButton', "
        "'refAcceptPushButton', 'mcaFitPushButton', 'refAnalyzeAllPushButton', "
        "'pilBurnPushButton', 'backgroundPushButton', 'pilMoviePushButton']\n"
        "for n in names:\n"
        "    getattr(w.ui, n).click(); app.processEvents()\n"
        "import reader_log\n"
        "print('alive', reader_log.failure_count())\n"), tmp_path)
    assert out.returncode == 0, out.stderr[-2000:]
    count = int(out.stdout.split('alive')[1].split()[0])
    assert count >= 6


# ---- in-process tests of the pieces ----------------------------------------

def test_messages_do_not_block_and_are_kept(window, qapp, recorder):
    assert not window.messageDock.isVisible()
    window.messageBox('Warning: something minor')
    qapp.processEvents()
    assert recorder.dialogs == []                 # no modal dialog was run
    assert window.messageDock.isVisible()
    assert 'something minor' in window.messageView.toPlainText()
    assert window.messages[-1][1:] == ('Warning', 'Warning: something minor')
    assert recorder.messages == ['Warning: something minor']


def test_spec_log_is_written_beside_the_spec_file(tmp_path, monkeypatch):
    monkeypatch.delenv('LSS_READER_LOG_DIR')
    spec = tmp_path / 'data' / 'sample'
    spec.parent.mkdir()
    spec.write_text('#F sample\n')
    before = spec.read_bytes()
    path, fallback = reader_log.attach_spec_log(str(spec))
    try:
        assert path == str(spec) + '.reader.log' and fallback is False
        reader_log.get_logger().warning('hello from the test')
        assert 'hello from the test' in open(path).read()
        assert 'SPEC file opened' in open(path).read()
    finally:
        reader_log.detach_spec_log()
    assert spec.read_bytes() == before            # the SPEC file is untouched


@pytest.mark.skipif(os.name == 'nt' or os.geteuid() == 0,
                    reason='needs a folder the user cannot write to')
def test_spec_log_falls_back_when_folder_is_read_only(tmp_path, monkeypatch):
    monkeypatch.delenv('LSS_READER_LOG_DIR')
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    folder = tmp_path / 'readonly'
    folder.mkdir()
    spec = folder / 'sample'
    spec.write_text('#F sample\n')
    folder.chmod(0o555)
    try:
        path, fallback = reader_log.attach_spec_log(str(spec))
        assert fallback is True
        assert path.startswith(str(tmp_path / 'home'))
    finally:
        reader_log.detach_spec_log()
        folder.chmod(0o755)


def test_fallback_location_is_computed_without_writing(tmp_path, monkeypatch):
    """With LSS_READER_LOG_DIR set, per-SPEC logs go there and nothing is
    created beside the SPEC file (the tests rely on this)."""
    monkeypatch.setenv('LSS_READER_LOG_DIR', str(tmp_path / 'logs'))
    spec = tmp_path / 'data' / 'sample'
    spec.parent.mkdir()
    spec.write_text('#F sample\n')
    path, fallback = reader_log.spec_log_path(str(spec))
    assert path.startswith(str(tmp_path / 'logs')) and fallback is False
    assert os.listdir(str(spec.parent)) == ['sample']


def test_opening_a_spec_file_starts_its_log(loaded, dataset):
    path, fallback = reader_log.current_spec_log()
    assert path is not None and os.path.exists(path)
    assert os.path.abspath(dataset) in open(path).read()
    # nothing was written beside the SPEC file in the tests
    assert not os.path.exists(dataset + '.reader.log')


def test_exception_hook_logs_context_and_reports(tmp_path, monkeypatch):
    monkeypatch.setenv('LSS_READER_LOG_DIR', str(tmp_path))
    handler = reader_log.DurableFileHandler(str(tmp_path / 'x.log'))
    logger = reader_log.get_logger()
    logger.addHandler(handler)
    told = []
    monkeypatch.setattr(sys, 'excepthook', sys.__excepthook__)
    reader_log.install_excepthook(context=lambda: {'SPEC file': 'abc'},
                                  report=told.append)
    try:
        try:
            raise ValueError('bad range')
        except ValueError:
            sys.excepthook(*sys.exc_info())
    finally:
        reader_log.uninstall_excepthook()
        logger.removeHandler(handler)
        handler.close()
    text = open(str(tmp_path / 'x.log')).read()
    assert 'unhandled ValueError' in text and 'SPEC file: abc' in text
    assert 'bad range' in text
    assert told and told[0].startswith('Operation failed: ValueError: bad range')
