"""The burn dialog's Trends tab (owner, 2026-11-21): opens analysed, models
and options kept, Save into the workbook; GID shows intensity, position
and width at once on two panels with three axes."""
import os

import numpy as np
import pytest

import sweep
import synth
from lss_core import preferences, trends, workbook

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


@pytest.fixture
def burn(window, qapp, tmp_path):
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp)
    return window


def _open(w, qapp):
    w.ui.pilBurnPushButton.click()
    qapp.processEvents()
    return w.uipdburn


def test_dialog_opens_on_the_analysed_trends(burn, qapp, recorder):
    d = _open(burn, qapp)
    assert recorder.exceptions == [] and recorder.messages == []
    assert d.burnTabWidget.currentIndex() == 0 and d.burnTabWidget.tabText(0) == 'Trends'
    res = burn.burnResult
    assert res is not None and res.trends['intensity'].best == 'exponential'
    text = d.burnResultLabel.text()
    assert 'Intensity: changing' in text and '5 % change in ≥ 20.5 s' in text
    assert 'AICc' in d.burnResultLabel.toolTip()
    axes = [a for a in d.burnTrendPlotWidget.canvas.fig.axes if a.axison]
    assert len(axes) == 1 and len(axes[0].lines) >= 4          # data and four models
    assert axes[0].child_axes and '% of t = 0' in axes[0].child_axes[0].get_ylabel()   # normalised, right axis
    side = ''.join(t.get_text() for a in d.burnTrendPlotWidget.canvas.fig.axes for t in a.texts)
    assert 'Intensity' in side and 'best: exp' in side and '5 % in ≥ 20.5 s' in side     # summary beside
    assert 'exp.burn(1, beam_mm=(1.0, 0.04))' in burn.burnScript        # the prefilled 1 mm beam (owner, 2026-11-25)
    d.refPushButton.click()                                    # the legacy plot: its own tab
    assert d.burnTabWidget.currentIndex() == 1


def test_options_are_kept_and_rerun(burn, qapp, recorder):
    d = _open(burn, qapp)
    d.burnDoubleExponentialCheckBox.setChecked(False)
    d.burnExponentialCheckBox.setChecked(False)
    assert set(burn.burnResult.trends['intensity'].fits) == {'constant', 'linear'}
    d.burnThresholdSpinBox.setValue(10.0)
    assert burn.burnResult.threshold == pytest.approx(0.10)
    assert d.burnTimeComboBox.currentText() == 'clock'                    # the default (owner: wall time)
    assert burn.burnResult.time == 'exposure' and 'no per-point times' in burn.burnResult.notes[0]
    d.burnTimeComboBox.setCurrentText('exposure')
    assert burn.burnResult.notes[0].startswith('exposure: counting time')
    d.burnPositionLimitCheckBox.setChecked(True)
    import json
    with open(os.environ[preferences.ENV]) as f:
        stored = json.load(f)['burn']
    assert stored['models'] == ['constant', 'linear'] and stored['threshold'] == 10.0 and stored['time'] == 'exposure'
    assert stored['position_limit'] is True
    for m in trends.MODELS:
        getattr(d, 'burn%sCheckBox' % ''.join(w.capitalize() for w in m.split())).setChecked(False)
    assert 'Tick at least one model' in d.burnResultLabel.text()
    assert recorder.exceptions == []


def test_save_puts_values_and_trends_in_the_workbook(burn, qapp, recorder):
    d = _open(burn, qapp)
    d.burnSavePushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    wb = workbook.Workbook(burn.workbookPath())
    r = wb.results(kind='burn test')[0]
    assert r['scans'] == '1' and r['columns'] == 'time_s, intensity, intensity_err'
    assert wb.data(r['id']).shape == (synth.BURN_FRAMES, 3)
    rows = wb.trends(rid=r['id'])
    assert [x['model'] for x in rows] == list(trends.MODELS)
    best = [x for x in rows if x['best']]
    assert len(best) == 1 and best[0]['model'] == 'exponential'
    assert best[0]['change_time_confident'] == pytest.approx(20.5, abs=0.2) and best[0]['time_axis'] == 'exposure'
    assert any('exp.burn(1, beam_mm=(1.0, 0.04))' in l for l in burn.scriptView.toPlainText().splitlines())


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_gid_burn_shows_three_quantities_on_two_panels(window, qapp, recorder, tmp_path):
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [14])                    # scan 15: list row 14
    sweep._select_images(window, qapp)
    d = _open(window, qapp)
    assert recorder.exceptions == [] and recorder.messages == []
    fig = d.burnTrendPlotWidget.canvas.fig
    panels = [a for a in fig.axes if a.axison]
    assert len(panels) == 3                                    # one panel per quantity (owner, 2026-11-21)
    labels = [a.get_ylabel() for a in panels]
    assert 'Intensity' in labels[0] and 'Position' in labels[1] and 'FWHM' in labels[2]
    right = [a.child_axes[0].get_ylabel() for a in panels]
    assert right == ['% of t = 0', 'shift, % of FWHM', '% of t = 0']
    assert not fig._suptitle.get_text().count('stable')        # the results beside the panels, not in the title
    res = window.burnResult
    assert res.scan == 15 and set(res.trends) == {'intensity', 'centre', 'fwhm'}
    text = d.burnResultLabel.text()
    assert 'Intensity: stable' in text and 'Position: changing' in text and 'FWHM: changing' in text
    d.burnAutoPeakCheckBox.setChecked(False)                   # the typed range instead
    d.rangeLineEdit.setText('1.40:1.53')
    d.burnAnalysePushButton.click()
    assert window.burnResult.window == (1.40, 1.53)
    assert window.burnResult.reference['estimator'] == 'stretched'         # the default
    d.burnEstimatorComboBox.setCurrentIndex(d.burnEstimatorComboBox.findData('moments'))   # the legacy arithmetic
    assert window.burnResult.reference['estimator'] == 'moments'
    d.burnErrorsComboBox.setCurrentText('counting')
    assert window.burnResult.trend_errors == 'given'
    assert recorder.exceptions == []


def test_gid_burn_rows_from_the_mean_frame(window, qapp, recorder, tmp_path):
    """Q-BURN-6 (owner, 2026-11-23): the rows a GID burn sums default to
    where the mean frame's signal is; shown in the field, which takes typed
    rows once "Rows from frame" is off. Synthetic GID burn: the rod's rows
    are 100-238 (synth.gid_burn_rows)."""
    spec = synth.make_gid_burn_dataset(tmp_path / 'gid', seed=5)
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp)
    d = _open(window, qapp)
    assert recorder.exceptions == []
    res = window.burnResult
    assert res.kind == 'gid' and d.burnRowsAutoCheckBox.isChecked() and not d.burnRowsLineEdit.isEnabled()
    lo, hi = res.rows
    assert 95 <= lo <= 100 and 238 <= hi <= 243
    assert d.burnRowsLineEdit.text() == '%d:%d' % (lo, hi)
    assert 'rows=' not in window.burnScript and any('Q-BURN-6' in n for n in res.notes)   # the default: no argument
    d.burnRowsAutoCheckBox.setChecked(False)                    # typed rows
    assert d.burnRowsLineEdit.isEnabled()
    assert preferences.load()['burn']['rows_auto'] is False
    d.burnRowsLineEdit.setText('120:200')
    d.burnRowsLineEdit.returnPressed.emit()
    qapp.processEvents()
    assert window.burnResult.rows == (120, 200) and 'rows=(120, 200)' in window.burnScript
    d.burnRowsLineEdit.setText('')                              # empty: all rows, as before
    d.burnAnalysePushButton.click()
    assert window.burnResult.rows == (0, synth.PIL_W - 1) and 'rows=None' in window.burnScript
    d.burnRowsLineEdit.setText('150')                           # not first:last
    d.burnAnalysePushButton.click()
    assert d.burnResultLabel.text().startswith('Not analysed')
    assert recorder.exceptions == []
