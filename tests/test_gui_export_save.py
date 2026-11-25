"""One meaning each for Export and Save (F95 B9; owner, 2026-11-23,
Q-UI-B9: "text-file writers are 'Export', workbook writers 'Save', both
beside every result (burn tests get an Export; the Plot tab and spectra a
Save)")."""
import os

import numpy as np
import pytest

import sweep
import synth
from lss_core import workbook

pytestmark = pytest.mark.gui


def _quiet(w):
    w.prefs['auto_save'] = False
    w.prefs['save_asks_note'] = False


def test_the_text_file_writers_are_called_export(window, qapp, recorder):
    from PyQt5 import uic
    from PyQt5.QtWidgets import QDialog
    from lss_core.resources import resource
    w = window
    gid = [w.ui.gidComboBox.itemText(k) for k in range(w.ui.gidComboBox.count())]
    gisaxs = [w.ui.gisaxsComboBox.itemText(k) for k in range(w.ui.gisaxsComboBox.count())]
    assert 'Export GID' in gid and 'Save to workbook' in gid and not any(t == 'Save GID' for t in gid)
    assert 'Export GISAXS' in gisaxs and 'Save GISAXS' not in gisaxs
    assert w.ui.savegraPushButton.text() == 'Export Gradient'
    d = uic.loadUi(resource('pdgioxs.ui'), QDialog(w))
    assert d.savePushButton.text() == 'Export'
    fit = w.buildCutFitDialog('cut')
    assert fit.findChild(type(w.ui.savegraPushButton), 'cutFitSavePushButton').text() == 'Export results...'
    for name in ('spec', 'ref', 'cut', 'mca', 'mcaSpectra', 'plot'):                  # a Save beside each Export
        assert w.saveButtons[name].text() == 'Save'
    assert recorder.exceptions == []


def test_a_burn_test_is_exported_as_text(window, qapp, recorder, tmp_path):
    w = window
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    _quiet(w)
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp)
    w.ui.pilBurnPushButton.click()
    qapp.processEvents()
    d = w.uipdburn
    lay = d.burnSavePushButton.parentWidget().layout()
    recorder.save_name = str(tmp_path / 'out_burn.txt')          # an ending typed is not doubled
    d.burnExportPushButton.click()
    qapp.processEvents()
    data = np.loadtxt(str(tmp_path / 'out_burn.txt'))
    assert data.shape == (synth.BURN_FRAMES, 3)                    # time, intensity, its error
    head = open(str(tmp_path / 'out_burn.txt')).readline()
    assert 'S# 1' in head and 'reflectivity burn' in head
    trends = open(str(tmp_path / 'out_burn_trends.txt')).read()
    assert 'exponential' in trends and 'change_time' in trends
    assert any('Exported out_burn.txt' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_spectra_and_plot_files_get_a_save(loaded, qapp, recorder, dataset, tmp_path):
    w = loaded
    _quiet(w)
    sweep.state_mca_frames(w, qapp, dataset)
    assert w.selectedMcaScanNums
    w.saveButtons['mcaSpectra'].click()
    qapp.processEvents()
    rows = workbook.Workbook(w.workbookPath()).results('fluorescence')
    assert len(rows) == len(w.selectedMcaScanNums) and all(r['label'].startswith('spectrum') for r in rows)
    assert all(str(r['scans']) == '3' for r in rows)
    f = tmp_path / 'curve.txt'
    np.savetxt(str(f), np.column_stack([np.arange(5.0), np.arange(5.0) ** 2]))
    recorder.open_names = [str(f)]
    w.ui.plotAddFilePushButton.click()
    qapp.processEvents()
    sweep._select_rows(w.ui.plotFileListWidget, qapp, [0])
    assert w.selectedplotfiles_rows == [0]
    w.saveButtons['plot'].click()
    qapp.processEvents()
    (other,) = workbook.Workbook(w.workbookPath()).results('other')
    assert other['label'] == 'curve.txt'
    assert np.array_equal(workbook.Workbook(w.workbookPath()).data(other['id'])[:, 1], np.arange(5.0) ** 2)
    assert recorder.exceptions == []
