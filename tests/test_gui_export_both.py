"""The owner (2026-11-26): "Always export both raw and normalized
reflectivity", that is R (_ref.txt) and R/R_F (_rrf.txt, with the Qc and
Qoff in the fields), whether or not the R/RF box is ticked. The ticked
export is unchanged (legacy fixtures), and the unticked one writes the same
bytes; the Script line writes the same files."""
import os

import numpy as np
import pytest

import sweep

pytestmark = pytest.mark.gui


def _patched(w, qapp):
    w.prefs['auto_save'] = False
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()


def test_both_files_whether_or_not_rrf_is_ticked(loaded, qapp, recorder, tmp_path, dataset):
    from lss_core.experiment import Experiment
    w = loaded
    w.directory = str(tmp_path)
    w.ui.refQoffLineEdit.setText('0.0003')
    _patched(w, qapp)
    assert w.ui.refRRFCheckBox.checkState() == 0                       # unticked
    recorder.save_name = str(tmp_path / 'off')
    w.ui.refExportPushButton.click()
    w.ui.refRRFCheckBox.setChecked(True)
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'on')
    w.ui.refExportPushButton.click()
    for end in ('_ref.txt', '_rrf.txt'):
        off, on = (open(str(tmp_path / (n + end)), 'rb').read() for n in ('off', 'on'))
        assert off and off == on                                       # the same bytes, ticked or not
    rrf = np.loadtxt(str(tmp_path / 'off_rrf.txt'))
    ref = np.loadtxt(str(tmp_path / 'off_ref.txt'))
    assert rrf[:, 0] == pytest.approx(ref[:, 0] + 0.0003)              # Qz + Qoff, as before
    w.ui.refRRFCheckBox.setChecked(False)
    qapp.processEvents()
    script = w.reflectivityScript(str(tmp_path / 'script'))
    assert 'rrf=False' not in script
    ns = {'exp': Experiment(dataset)}
    exec(script, ns)
    assert os.path.exists(str(tmp_path / 'script_rrf.txt'))
    assert np.loadtxt(str(tmp_path / 'script_rrf.txt')) == pytest.approx(rrf, rel=1e-9)
    assert recorder.exceptions == []


def test_the_workbook_keeps_its_rule(loaded, qapp, recorder):
    """Save stores R/RF while R/RF is ticked, as before (the owner's rule is about Export)."""
    w = loaded
    _patched(w, qapp)
    assert [it['label'] for it in w.refWorkbookItems()] == ['R']
    w.ui.refRRFCheckBox.setChecked(True)
    qapp.processEvents()
    assert [it['label'] for it in w.refWorkbookItems()] == ['R', 'R/RF']
    assert recorder.exceptions == []
