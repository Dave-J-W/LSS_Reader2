"""Every main Export says what it wrote, and where; it says when it
replaced files of the same name (the save dialog checks only the name
typed, not the endings an export adds), and when R/R_F was missing so that
no _rrf.txt was written (release push, 2026-11-26)."""
import os

import pytest

import sweep
import synth

pytestmark = pytest.mark.gui


def _patched(w, qapp):
    w.prefs['auto_save'] = False
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()


def test_the_reflectivity_export_says_what_it_wrote_and_replaced(loaded, qapp, recorder, tmp_path):
    w = loaded
    w.directory = str(tmp_path)
    w.ui.refRRFCheckBox.setChecked(True)                              # R/R_F made, so both files
    _patched(w, qapp)
    recorder.save_name = str(tmp_path / 'film')
    recorder.messages.clear()
    w.ui.refExportPushButton.click()
    said = [m for m in recorder.messages if m.startswith('Exported')]
    assert len(said) == 1 and 'film_ref.txt, film_rrf.txt' in said[0] and str(tmp_path) in said[0]
    assert 'replaced' not in said[0]
    recorder.messages.clear()
    w.ui.refExportPushButton.click()                                   # the same name again
    said = [m for m in recorder.messages if m.startswith('Exported')]
    assert 'replaced the earlier film_ref.txt, film_rrf.txt' in said[0]
    w.ui.refRRFCheckBox.setChecked(False)                             # no R/R_F of the curve on show
    qapp.processEvents()
    recorder.messages.clear()
    w.ui.refExportPushButton.click()
    said = [m for m in recorder.messages if m.startswith('Exported')]
    assert 'film_ref.txt' in said[0] and 'No _rrf.txt' in said[0] and 'tick R/RF' in said[0] and 'is an earlier one' in said[0]
    assert recorder.exceptions == []


def test_the_fluorescence_export_says_what_it_wrote(window, qapp, recorder, tmp_path):
    spec, truth = synth.make_xfntr_dataset(tmp_path / 'xf')
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    w.prefs['auto_save'] = False
    qapp.processEvents()
    sweep._select_scans(w, qapp, None)
    sweep._select_images(w, qapp, None)
    w.mcaFitLinesPushButton.click()
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'run')
    recorder.messages.clear()
    w.mcaSaveIntData()
    said = [m for m in recorder.messages if m.startswith('Exported')]
    assert len(said) == 1 and 'run_flu.txt, run_flu_xeray.txt' in said[0]
    assert recorder.exceptions == []
