"""F48: the Script pane shows Python that reproduces what the window did."""
import os

import pytest

import sweep
import synth

pytestmark = pytest.mark.gui


def _run_script(text, tmp_path):
    """Execute the pane's text; return the namespace."""
    ns = {}
    exec(compile(text, 'script-pane', 'exec'), ns)
    return ns


def _same_files(a, b):
    for kind in ('ref', 'rrf'):
        pa, pb = a + '_%s.txt' % kind, b + '_%s.txt' % kind
        assert os.path.exists(pa) == os.path.exists(pb), kind
        if os.path.exists(pa):
            with open(pa, 'rb') as fa, open(pb, 'rb') as fb:
                assert fa.read() == fb.read(), kind


def _export(w, qapp, recorder, name):
    recorder.save_name = name
    w.ui.refExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []


def test_script_reproduces_a_patch_with_merge_drops_and_options(window, qapp, recorder,
                                                                tmp_path):
    spec = synth.make_identical_scans_dataset(tmp_path / 'same')
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0, 1, 2])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    w.uirefpatchsamescan.mergePushButton.click()
    w.uirefpatchsamescan.nextPushButton.click()
    d = w.uirefpatch
    d.dropLineEdit.setText('1')
    d.dropPushButton.click()
    d.dropLineEdit.setText('-1')
    d.dropPushButton.click()
    d.nextPushButton.click()
    qapp.processEvents()
    w.ui.refNormLineEdit.setText('3.0')
    w.ui.refNormFacCheckBox.setChecked(True)
    w.ui.refRRFCheckBox.setChecked(True)
    w.ui.refQoffLineEdit.setText('0.0004')
    w.ui.refQoffLineEdit.returnPressed.emit()
    qapp.processEvents()
    gui = str(tmp_path / 'gui')
    _export(w, qapp, recorder, gui)
    text = w.scriptView.toPlainText()
    assert 'exp = Experiment(' in text and "ref.save(" in text
    assert "merge=[[2, 3]]" in text and "drops={0: [[1], [-1]]}" in text
    script = str(tmp_path / 'script')
    _run_script(text.replace(repr(gui), repr(script)), tmp_path)
    _same_files(gui, script)


def test_script_reproduces_a_partial_frame_selection(loaded, qapp, recorder, tmp_path):
    w = loaded
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp, [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])   # some frames left out
    w.ui.pilRefPatchPushButton.click()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    gui = str(tmp_path / 'gui')
    _export(w, qapp, recorder, gui)
    text = w.scriptView.toPlainText()
    assert 'points={1: [0, 1, 3, 4, 5, 6, 7, 8], 2: [0, 1, 2, 3, 4]}' in text
    script = str(tmp_path / 'script')
    _run_script(text.replace(repr(gui), repr(script)), tmp_path)
    _same_files(gui, script)


def test_next_without_overlap_is_refused(loaded, qapp, recorder):
    """Hand-off trap T11: pressing Next for a pair that does not overlap."""
    w = loaded
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp, [0, 1, 2, 9, 10])        # Qz 0.01-0.02 and 0.04-0.05
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.pilRefPatchNext()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert any('do not overlap' in m for m in recorder.messages)
