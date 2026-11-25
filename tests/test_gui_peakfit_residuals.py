"""F74 on the older Fit Peak dialog (owner, 2026-11-22: "a small residuals
plot above every plot that shows a fit", hidden by default): the Plot tab's
and the MCA tab's fits show the residuals they minimised, (y − fit)/σ at
the fitted points, behind View > Residuals above fits, and χ²/dof in the
fit's label. Their squares add up to the χ²/dof the dialog reports (I45)."""
import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

WINDOW = '5.6:7.2'                                  # keV, about the synthetic fluorescence line


@pytest.fixture
def xf(window, qapp, tmp_path):
    spec, truth = synth.make_xfntr_dataset(tmp_path / 'xf')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, None)
    sweep._select_images(window, qapp, None)
    return window


def _points(rax):
    return [l for l in rax.lines if not getattr(l, '_lss_zero', False)]


def test_mca_fit_shows_its_residuals_behind_the_switch(xf, qapp, recorder):
    w = xf
    sweep._select_images(w, qapp, [4])
    w.ui.mcaFitPushButton.click()
    qapp.processEvents()
    d = w.uipeakfit
    d.rangeLineEdit.setText(WINDOW)
    for j, v in enumerate((6.3, 1e-2, 0.1)):
        d.peakTW.item(0, j).setText(str(v))
    d.fitPushButton.click()
    qapp.processEvents()
    ax = w.ui.mcaPlotMplWidget.canvas.ax
    assert getattr(ax, '_lss_residuals', None) is None                      # hidden by default
    w.fitResidualsAction.setChecked(True)
    qapp.processEvents()
    ax = w.ui.mcaPlotMplWidget.canvas.ax
    (pts,) = _points(ax._lss_residuals)
    x, r, red = w.peakFitResiduals
    assert np.array_equal(pts.get_xdata(), x) and np.allclose(pts.get_ydata(), r)
    assert 5.6 <= x.min() and x.max() <= 7.2                                # the fit range only
    assert np.sum(r ** 2) / (len(r) - 4) == pytest.approx(red, rel=1e-12)  # I45: 3 peak + 1 background parameter
    assert float(d.chiLineEdit.text()) == pytest.approx(red, abs=1e-3)
    assert any('χ²/dof' in str(l.get_label()) for l in ax.lines)
    w.fitResidualsAction.setChecked(False)
    qapp.processEvents()
    assert getattr(w.ui.mcaPlotMplWidget.canvas.ax, '_lss_residuals', None) is None
    w.fitResidualsAction.setChecked(True)
    sweep._select_images(w, qapp, [3])                                       # another frame: no fit on show
    assert getattr(w.ui.mcaPlotMplWidget.canvas.ax, '_lss_residuals', None) is None
    w.fitResidualsAction.setChecked(False)
    assert recorder.exceptions == []


def test_plot_tab_fit_shows_its_residuals(window, qapp, recorder, tmp_path):
    rng = np.random.default_rng(7)
    x = np.linspace(-1.0, 1.0, 81)
    mu = 400.0 * np.exp(-x ** 2 / 2 / 0.15 ** 2) + 20.0
    y = rng.poisson(mu).astype(float)
    f = tmp_path / 'peak.txt'
    np.savetxt(f, np.column_stack([x, y, np.sqrt(np.maximum(y, 1.0))]))
    w = window
    w.directory = str(tmp_path)
    w.fitResidualsAction.setChecked(True)
    w.plotfiles = [str(f)]
    w.updatePlotFile()
    w.ui.plotFileListWidget.item(0).setSelected(True)
    qapp.processEvents()
    w.updateSelectedPlotFile()
    w.ui.plotPFPushButton.click()
    qapp.processEvents()
    d = w.uipeakfit
    d.rangeLineEdit.setText('-1:1')
    d.peakTW.selectAll()                                                     # vary every parameter
    d.bgTW.selectAll()
    d.fitPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    ax = w.ui.PlotMplWidget.canvas.ax
    (pts,) = _points(ax._lss_residuals)
    xr, r, red = w.peakFitResiduals
    assert np.array_equal(pts.get_xdata(), xr) and len(r) == len(x)
    nvar = w.peakresult.nvarys
    assert np.sum(r ** 2) / (len(r) - nvar) == pytest.approx(red, rel=1e-9)  # I45
    assert 0.5 < red < 2.0                                                    # Poisson data, right errors
    assert abs(np.mean(r)) < 0.5
    fit = [l for l in ax.lines if 'χ²/dof' in str(l.get_label())]
    assert len(fit) == 1
    w.fitResidualsAction.setChecked(False)
    qapp.processEvents()
    ax = w.ui.PlotMplWidget.canvas.ax
    assert getattr(ax, '_lss_residuals', None) is None
    assert not [l for l in ax.lines if 'χ²/dof' in str(l.get_label())]
    assert recorder.exceptions == []
