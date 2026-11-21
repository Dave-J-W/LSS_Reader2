"""'Fit peaks' and 'Fit options...' beside the line-cut plot (owner,
2026-11-21): every plotted cut fitted automatically with lss_core.peaks;
options in a dialog."""
import math

import numpy as np
import pytest

import sweep
import synth
from lss_core import peaks
from lss_core.experiment import CutResult

pytestmark = pytest.mark.gui

COL = synth.PIL_H - synth.DB_X - 1


@pytest.fixture
def frame(loaded, qapp, dataset):
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    return loaded


def _hcut(w, qapp):
    w.ui.pilCutDirComboBox.setCurrentIndex(2)            # Pix H
    w.ui.pilIntRangeLineEdit.setText('90:110')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()


def test_fit_button_fits_the_plotted_cut(frame, qapp, recorder):
    _hcut(frame, qapp)
    n0 = len(frame.ui.cutPlotMplWidget.canvas.ax.lines)
    frame.cutFitPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert len(frame.cutFitResults) == 1
    label, groups = frame.cutFitResults[0]
    best = max((p for g in groups for p in g.peaks), key=lambda p: p.height)
    assert best.centre == pytest.approx(COL, abs=0.5)            # the direct beam's column
    assert len(frame.ui.cutPlotMplWidget.canvas.ax.lines) > n0   # fits drawn over the cut
    assert any('Fit of' in m for m in recorder.messages)


def test_fit_options_dialog_changes_the_fit(frame, qapp, recorder, tmp_path, monkeypatch):
    _hcut(frame, qapp)
    frame.cutFitOptionsPushButton.click()
    d = frame.cutFitDialog
    assert d is not None and d.isVisible()
    d.cutFitShapeComboBox.setCurrentText('lorentzian')
    d.cutFitBackgroundComboBox.setCurrentText('constant')
    d.cutFitNumberSpinBox.setValue(1)
    assert frame.peakFitOptions.shape == 'lorentzian' and frame.peakFitOptions.n_peaks == 1
    d.cutFitNowPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    g = frame.cutFitResults[0][1]
    assert g[0].options.shape == 'lorentzian' and len(g[0].peaks) == 1
    # the synthetic beam is a Gaussian with tiny error bars: a Lorentzian is fitted but flagged as a misfit
    assert 'does not describe' in g[0].message or 'did not converge' in g[0].message
    from PyQt5.QtWidgets import QLabel
    assert 'centre' in d.findChild(QLabel, 'cutFitResultLabel').text()
    out = tmp_path / 'fits.txt'
    monkeypatch.setattr('mainwindow.QFileDialog.getSaveFileName', lambda *a, **k: (str(out), ''))
    frame.saveCutFits()
    rows = [l for l in out.read_text().splitlines() if not l.startswith('#')]
    assert len(rows) == 1 and 'lorentzian' in rows[0]


def test_fit_without_a_cut_says_so(window, qapp, recorder):
    window.cutData = {}
    window.cutFitPushButton.click()
    assert recorder.exceptions == [] and any('line cut' in m for m in recorder.messages)


def test_scripted_cut_fit():
    """CutResult.fit, the script equivalent of the button."""
    x = np.linspace(0, 10, 201)
    y = 5 + 100 * np.exp(-0.5 * ((x - 4.2) / (0.3 / (2 * math.sqrt(2 * math.log(2))))) ** 2)
    cut = CutResult([np.column_stack([x, y, np.sqrt(y)])], ['S# 1_F# 0'])
    res = cut.fit(peaks.FitOptions(n_peaks=1))
    assert res[0][0].ok and res[0][0].peaks[0].centre == pytest.approx(4.2, abs=1e-3)
