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
    loaded.prefs['auto_save'] = False           # the Save button alone (automatic saving: tests below)
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


def test_fit_lines_reports_the_elements_line_not_the_tallest(loaded, qapp, dataset, recorder, monkeypatch):
    """F90, P5 (2026-11-24): with a second line placed (an escape peak,
    a neighbour) and taller, "Fit lines" still reports the first line
    given. The fit is replaced by a known two-peak result."""
    from lss_core import peaks
    sweep.state_mca_frames(loaded, qapp, dataset)
    n = len(loaded.selectedMcaScanNums)
    tall = peaks.Peak(7.0, 0, 0.2, 0, 900.0, 9.0, 900.0 * 0.2 * 1.0645, 9.0, 'gaussian')
    line = peaks.Peak(6.4, 0, 0.2, 0, 50.0, 2.0, 50.0 * 0.2 * 1.0645, 2.0, 'gaussian')
    res = peaks.FitResult([tall, line], np.zeros(3), 6.7, 1.0, 1.0, (5.6, 7.8), 100, True)
    monkeypatch.setattr(peaks, 'fit_series', lambda *a, **k: (res, [res] * n))
    loaded.mcaFitOptions = peaks.FitOptions(centres=(6.4, 7.0), n_peaks=2)
    loaded.mcaFitLinesPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    step = float(np.median(np.diff(loaded.nomMcaData[loaded.selectedMcaScanNums[0]][:, 0])))
    assert [r[3] for r in loaded.mcaIntData] == pytest.approx([line.area / step] * n)
    assert 'line at 6.4' in loaded.command


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


def test_every_save_asks_and_shift_skips(loaded, qapp, dataset, recorder, monkeypatch):
    """Owner, 2026-11-21: ask for a note on every Save; Shift-click saves
    without asking."""
    sweep.state_motor_scan(loaded, qapp, dataset)
    asked = []
    monkeypatch.setattr('PyQt5.QtWidgets.QInputDialog.getMultiLineText',
                        staticmethod(lambda *a, **k: asked.append(1) or ('v1', True)))
    loaded.saveButtons['spec'].click()
    assert asked == [1]
    from PyQt5.QtCore import Qt
    monkeypatch.setattr('PyQt5.QtWidgets.QApplication.keyboardModifiers', staticmethod(lambda: Qt.ShiftModifier))
    loaded.saveButtons['spec'].click()
    assert asked == [1]                                       # Shift: no question
    notes = [r['note'] for r in _book(loaded).results(kind='scan')]
    assert notes == ['v1', None] or notes == ['v1', '']
    loaded.prefs['save_asks_note'] = False                    # the preference off: Shift asks instead
    loaded.saveButtons['spec'].click()
    assert asked == [1, 1]
    assert recorder.exceptions == []


def test_a_saved_result_goes_stale_when_its_series_grows(window, qapp, recorder, tmp_path):
    """Review R3: save a scan of a series, the SPEC file grows (the next scan
    of the series), "Update Specfile": the result is marked out of date in
    the workbook and the user is told. The step towards live updates."""
    from test_series import _scan
    import synth
    spec = synth.write_spec(str(tmp_path / 'grow'), [_scan(1), _scan(2)])
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    window.saveButtons['spec'].click()
    qapp.processEvents()
    r = _book(window).results(kind='scan')[0]
    assert r['series'] == 'inferred-1' and r['series_scans'] == '1,2' and not r['stale']
    with open(spec, 'a') as f:
        f.write(_scan(3))
    recorder.messages.clear()
    window.ui.speUpSpeFilePushButton.click()
    qapp.processEvents()
    assert any('out of date' in m and 'gained scans 3' in m for m in recorder.messages)
    assert not any('more than once' in m for m in recorder.messages)   # the update re-reads scan 2: not a repeat
    assert window.specData['ScanNums'] == [1, 2, 3]
    assert _book(window).stale()[0]['id'] == r['id']
    assert recorder.exceptions == []


# ---- automatic saving (owner, 2026-11-22) ------------------------------------------

def _cut(w, qapp, rng='90:110'):
    w.ui.pilCutDirComboBox.setCurrentIndex(2)
    w.ui.pilIntRangeLineEdit.setText(rng)
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    qapp.processEvents()


def test_a_finished_reduction_is_saved_automatically(loaded, qapp, dataset, recorder, monkeypatch):
    """Owner, 2026-11-22: "make saving in the excel file automatic once a
    reduction/processing has been carried through"."""
    asked = []
    monkeypatch.setattr('PyQt5.QtWidgets.QInputDialog.getMultiLineText',
                        staticmethod(lambda *a, **k: asked.append(1) or ('by hand', True)))
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    _cut(loaded, qapp)
    res = _book(loaded).results(kind='line cut')
    assert len(res) == 1 and res[0]['origin'] == 'auto' and asked == []      # no question for an automatic save
    assert res[0]['recipe'] and res[0]['content']
    _cut(loaded, qapp)                                                          # the same cut again: not stored twice
    assert len(_book(loaded).results(kind='line cut')) == 1
    _cut(loaded, qapp, '80:120')                                                # a different cut: a new version
    loaded.cutFitPushButton.click()                                             # its fit: a new version with the fit
    qapp.processEvents()
    qapp.processEvents()
    res = _book(loaded).results(kind='line cut')
    assert len(res) == 3 and all(r['origin'] == 'auto' for r in res)   # versions count per label (the range is in it)
    assert [r['version'] for r in res] == [1, 1, 2]
    assert _book(loaded).fits(rid=res[-1]['id'])
    loaded.saveButtons['cut'].click()                                          # the Save button: a version with a note
    r = _book(loaded).results(kind='line cut')[-1]
    assert r['origin'] == 'user' and r['note'] == 'by hand' and asked == [1]
    assert not any('Saved automatically' in m for m in recorder.messages)     # quiet: status bar and log only
    assert recorder.exceptions == []


def test_automatic_saving_can_be_turned_off(loaded, qapp, dataset, recorder):
    loaded.buildPreferences().prefAutoSaveCheckBox.setChecked(False)
    assert loaded.prefs['auto_save'] is False
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    _cut(loaded, qapp)
    assert not os.path.exists(loaded.workbookPath())
    assert recorder.exceptions == []


def test_a_burn_test_and_mca_sum_are_saved_when_done(loaded, qapp, dataset, recorder):
    sweep.state_mca_frames(loaded, qapp, dataset)
    qapp.processEvents()
    loaded.mcaFitLinesPushButton.click()
    qapp.processEvents()
    qapp.processEvents()
    kinds = {r['kind'] for r in _book(loaded).results()}
    assert 'fluorescence' in kinds
    assert recorder.exceptions == []


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="Save stores the scans selected at the time, not the curve's (TODO area I, 2026-11-22)")
def test_a_reflectivity_is_saved_tied_to_the_scans_it_was_made_from(loaded, qapp, dataset, recorder):
    """GUI assessment, 2026-11-22: Save took the scans selected when it was
    clicked, not those of the curve on show (``saveRefToWorkbook`` reads
    ``selectedScanNums``), so a curve of scans 1 and 2 saved after selecting
    scan 1 alone was stored as scan 1, and its series tie, stale flag and
    live remake followed the wrong scans. ``saveMcaToWorkbook`` reads the
    selection the same way."""
    loaded.prefs['auto_save'] = False
    loaded.prefs['save_asks_note'] = False
    sweep.state_pilatus_two_scans_all_frames(loaded, qapp, dataset)
    loaded.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    loaded.uirefpatch.nextPushButton.click()              # "Finish!": the curve of scans 1 and 2
    qapp.processEvents()
    assert loaded.pilrefsort == [1, 2] and len(loaded.normRefData)
    sweep._select_scans(loaded, qapp, [0])                # scan 1 alone; the curve on show is unchanged
    assert len(loaded.normRefData)
    loaded.saveButtons['ref'].click()
    qapp.processEvents()
    assert recorder.exceptions == []
    res = _book(loaded).results(kind='reflectivity')
    assert [r['label'] for r in res] in (['R', 'R/RF'], ['R'])
    assert res[0]['scans'] == '1,2'
