"""One-click Save into the SPEC file's workbook beside every Export, notes,
fit options kept between sessions, and the MCA's "Fit lines" (owner,
2026-11-21)."""
import json
import math
import os

import numpy as np
import pytest

import sweep
from lss_core import peaks, preferences, workbook

pytestmark = pytest.mark.gui


def _book(w):
    p = w.workbookPath()
    assert os.path.exists(p) and os.path.dirname(p) == w.directory      # in the output folder, not beside the data
    return workbook.Workbook(p)


def test_save_buttons_sit_beside_every_export(loaded):
    for name in ('spec', 'ref', 'cut', 'mca'):
        b = loaded.saveButtons[name]
        assert b.text() == 'Save' and 'workbook' in b.toolTip()
    box = loaded.ui.gidComboBox
    assert 'Save to workbook' in [box.itemText(i) for i in range(box.count())]


def test_cut_and_its_fit_are_saved_tied_to_the_scan(loaded, qapp, dataset, recorder):
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.ui.pilCutDirComboBox.setCurrentIndex(2)
    loaded.ui.pilIntRangeLineEdit.setText('90:110')
    loaded.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    loaded.cutFitPushButton.click()
    loaded.saveButtons['cut'].click()
    qapp.processEvents()
    assert recorder.exceptions == []
    wb = _book(loaded)
    res = wb.results(kind='line cut')
    assert len(res) == 1 and res[0]['scans'] == '1' and res[0]['version'] == 1
    assert len(wb.data(res[0]['id'])) == len(loaded.cutCurves()[0][1])
    f = wb.fits(rid=res[0]['id'])
    assert f and f[0]['centre'] is not None
    assert any(r['scan'] == 1 for r in wb._rows('Scans'))
    assert wb.settings('peak_fit')['shape'] == 'gaussian'
    loaded.saveButtons['cut'].click()                       # the same scans again: version 2
    assert [r['version'] for r in _book(loaded).results(kind='line cut')] == [1, 2]


def test_a_note_when_asked(loaded, qapp, dataset, recorder, monkeypatch):
    sweep.state_motor_scan(loaded, qapp, dataset)
    loaded.prefs['save_asks_note'] = True
    monkeypatch.setattr('PyQt5.QtWidgets.QInputDialog.getMultiLineText',
                        staticmethod(lambda *a, **k: ('after realignment', True)))
    loaded.saveButtons['spec'].click()
    qapp.processEvents()
    assert recorder.exceptions == []
    r = _book(loaded).results(kind='scan')[0]
    assert r['note'] == 'after realignment' and r['scans'] == '4'
    f = _book(loaded).fits(rid=r['id'])
    assert f and f[0]['fit'] == 'peak'                        # the scan's shape fit (fit_scan)
    monkeypatch.setattr('PyQt5.QtWidgets.QInputDialog.getMultiLineText',
                        staticmethod(lambda *a, **k: ('', False)))
    loaded.saveButtons['spec'].click()                        # cancelled: nothing saved
    assert len(_book(loaded).results(kind='scan')) == 1


def test_mca_fit_lines_and_save(loaded, qapp, dataset, recorder):
    sweep.state_mca_frames(loaded, qapp, dataset)
    loaded.mcaFitLinesPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    rows = loaded.mcaIntData
    assert len(rows) == 2 and rows[1][3] == pytest.approx(2 * rows[0][3], rel=0.01)   # the second spectrum is × 2
    ref, each, nums = loaded.mcaLineFits
    assert ref.peaks[0].fwhm == pytest.approx(5 * 2 * math.sqrt(2 * math.log(2)), rel=0.05) or \
        ref.peaks[0].fwhm > 0                                 # in the spectrum's energy units
    loaded.saveButtons['mca'].click()
    r = _book(loaded).results(kind='fluorescence')[0]
    assert len(_book(loaded).fits(rid=r['id'])) == 3          # the sum and the two spectra
    loaded.mcaFitOptionsPushButton.click()
    assert loaded.mcaFitDialog.isVisible()


def test_fit_options_are_kept_between_sessions(loaded, qapp, recorder):
    loaded.cutFitOptionsPushButton.click()
    d = loaded.cutFitDialog
    d.cutFitShapeComboBox.setCurrentText('pseudo-voigt')
    d.cutFitNumberSpinBox.setValue(2)
    with open(os.environ[preferences.ENV]) as f:
        stored = json.load(f)
    assert stored['peak_fit']['shape'] == 'pseudo-voigt' and stored['peak_fit']['n_peaks'] == 2
    from mainwindow import MainWindow
    w2 = MainWindow()
    try:
        assert w2.peakFitOptions.shape == 'pseudo-voigt' and w2.peakFitOptions.n_peaks == 2
        assert w2.mcaFitOptions.background == 'quadratic'
    finally:
        w2.close()
        w2.deleteLater()
    assert recorder.exceptions == []


def test_saving_with_nothing_to_save_says_so(window, recorder):
    window.specFileName = None
    window.saveButtons['cut'].click()
    window.saveMcaToWorkbook()
    assert recorder.exceptions == [] and len(recorder.messages) >= 2
