"""Export proposes a file name from the sample and the scans, in the folder
of the last Export (F105; owner, 2026-11-23, Q-REF-6: "Straight into
xmodfit; the reader proposes a file name from the sample and series")."""
import os

import pytest

import sweep

pytestmark = pytest.mark.gui


def _patch(w, qapp):
    w.prefs['auto_save'] = False
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()


def test_export_proposes_the_name_and_remembers_the_folder(loaded, qapp, recorder, tmp_path, monkeypatch):
    from PyQt5 import QtWidgets
    _patch(loaded, qapp)
    asked = []
    out = tmp_path / 'xmodfit'
    out.mkdir()

    def save_name(*a, **k):
        asked.append(k.get('directory'))
        return str(out / ('%s_ref.txt' % os.path.basename(k.get('directory')))), ''   # accepted, with an ending
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', save_name)
    loaded.ui.refExportPushButton.click()
    qapp.processEvents()
    assert asked[0] == os.path.join(loaded.directory, 'sample_S1-2')       # the output folder, the proposed name
    assert (out / 'sample_S1-2_ref.txt').exists()                         # the ending typed is not doubled
    assert loaded.prefs['export_folder'] == str(out)
    loaded.ui.refExportPushButton.click()                                 # the next Export opens in that folder
    qapp.processEvents()
    assert asked[1] == os.path.join(str(out), 'sample_S1-2')
    assert 'XModFit' in loaded.ui.refExportPushButton.toolTip()
    assert recorder.exceptions == []


def test_the_sample_comes_from_the_series_macro(loaded, qapp, recorder):
    _patch(loaded, qapp)
    loaded.specPar[1]['SeriesMacro'] = 'dppc_xr.do'
    assert os.path.basename(loaded.exportProposal()) == 'sample_dppc_S1-2'
    loaded.prefs['export_folder'] = '/no/such/folder'                    # gone: the output folder instead
    assert os.path.dirname(loaded.exportProposal()) == loaded.directory
    assert recorder.exceptions == []
