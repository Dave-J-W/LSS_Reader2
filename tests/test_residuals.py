"""The residual panel above fit plots (F74; owner, 2026-11-22):
lss_core.residuals alone, and the switch in the window.

Invariant: the residuals drawn are those the fit minimised, so the sum of
their squares over the fitted points is the fit's χ² (χ²/dof × (N − p),
with p the number of parameters).
"""
import matplotlib
import numpy as np
import pytest

from lss_core import peaks, residuals


def test_weighted_by_sigma_when_every_sigma_is_good():
    r, w = residuals.weighted([3.0, 5.0], [1.0, 1.0], [2.0, 4.0])
    assert w and r == pytest.approx([1.0, 1.0])
    r, w = residuals.weighted([3.0, 5.0], [1.0, 1.0], [2.0, 0.0])      # one σ of 0: plain residuals
    assert not w and r == pytest.approx([2.0, 4.0])
    r, w = residuals.weighted([3.0], [1.0])
    assert not w and r == pytest.approx([2.0])


def test_chi2_in_the_legend_label():
    assert residuals.chi2_label('Fit (peak)', 1.234) == 'Fit (peak), χ²/dof 1.23'
    assert residuals.chi2_label('Fit', float('nan')) == 'Fit'
    assert residuals.chi2_label('Fit', None) == 'Fit'


def test_the_panel_takes_15_percent_and_gives_it_back():
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig = Figure(figsize=(6, 4))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.plot([0, 1], [0, 1])
    fig.canvas.draw()
    full = ax.get_position().height
    rax = residuals.panel(ax, True)
    fig.canvas.draw()
    h, hr = ax.get_position().height, rax.get_position().height
    assert hr / (h + hr) == pytest.approx(0.15, abs=0.01)
    assert residuals.panel(ax, True) is rax                   # made once
    ax.clear()                                                # a redraw of the main plot keeps it
    assert residuals.panel(ax, True) is rax
    assert residuals.panel(ax, False) is None
    fig.canvas.draw()
    assert len(fig.axes) == 1 and ax.get_position().height == pytest.approx(full)


def test_the_residuals_are_those_the_fit_minimised():
    rng = np.random.default_rng(3)
    x = np.linspace(-1, 1, 61)
    truth = 2000 * np.exp(-x ** 2 / 2 / 0.15 ** 2) + 100 + 30 * x
    y = rng.poisson(truth).astype(float)
    s = np.sqrt(y)
    res = peaks.fit_scan(x, y, s)
    assert res.kind == 'peak' and res.ok
    m = (x >= min(res.window)) & (x <= max(res.window))
    r, w = residuals.weighted(y[m], res.model(x[m]), s[m])
    assert w
    n_minus_p = np.sum(r ** 2) / res.chi2_dof
    assert n_minus_p == pytest.approx(round(n_minus_p), abs=1e-6)          # an integer: N − p
    assert 3 <= m.sum() - round(n_minus_p) <= 8                            # p: a peak and its background
    assert abs(np.mean(r)) < 0.5 and 0.6 < np.std(r) < 1.5                 # Poisson data, right errors: about N(0, 1)


@pytest.mark.gui
def test_the_switch_adds_the_panel_to_scan_fits_and_cut_fits(loaded, qapp, recorder):
    import sweep
    w = loaded
    act = w.fitResidualsAction
    assert act.objectName() == 'actionFitResiduals' and act.isCheckable() and not act.isChecked()
    assert act in w.findChild(type(w.ui.menuBar.actions()[0].menu()), 'menuView').actions()
    sweep._select_scans(w, qapp, [3])                          # scan 4: a plain motor scan, a Gaussian
    ax = w.ui.specPlotMplWidget.canvas.ax
    assert w.specResidualItems and getattr(ax, '_lss_residuals', None) is None    # off by default
    title = ax.get_title()
    act.setChecked(True)
    qapp.processEvents()
    assert w.prefs['fit_residuals'] is True
    ax = w.ui.specPlotMplWidget.canvas.ax
    rax = ax._lss_residuals
    assert rax is not None and rax.get_ylabel() == '(y−fit)/σ'
    assert rax.get_title() == title and ax.get_title() == ''   # the title above the pair
    fit_line = [l for l in ax.get_lines() if l.get_label().startswith('Fit (')][0]
    assert 'χ²/dof' in fit_line.get_label()
    pts = [l for l in rax.get_lines() if l.get_marker() == 'o'][0]
    assert len(pts.get_xdata()) > 5
    act.setChecked(False)
    qapp.processEvents()
    ax = w.ui.specPlotMplWidget.canvas.ax
    assert getattr(ax, '_lss_residuals', None) is None and ax.get_title() == title
    assert 'χ²/dof' not in [l for l in ax.get_lines() if l.get_label().startswith('Fit (')][0].get_label()
    assert recorder.exceptions == []


@pytest.mark.gui
def test_cut_fits_get_residuals_and_new_cuts_lose_them(loaded, qapp, dataset, recorder):
    import sweep
    w = loaded
    w.fitResidualsAction.setChecked(True)
    sweep.state_pilatus_one_frame(w, qapp, dataset)
    w.updatePilCutData()
    qapp.processEvents()
    if not w.cutCurves():
        pytest.skip('no cut on this frame')
    w.fitCuts()
    qapp.processEvents()
    ax = w.ui.cutPlotMplWidget.canvas.ax
    fitted = any(g.peaks for _, groups in w.cutFitResults for g in groups)
    assert (getattr(ax, '_lss_residuals', None) is not None) == fitted
    w.updatePilCutData()                                       # new cuts, not fitted: no residuals
    qapp.processEvents()
    assert getattr(w.ui.cutPlotMplWidget.canvas.ax, '_lss_residuals', None) is None
    assert recorder.exceptions == []


def test_burn_trends_get_the_best_models_residuals(tmp_path):
    """lss_core.burn.plot(residuals=True): above each panel, the best
    model's residuals over every frame, with χ²/dof; the default draws none."""
    import synth
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from lss_core import burn
    from lss_core.experiment import Experiment
    res = Experiment(synth.make_burn_dataset(tmp_path / 'burn')).burn(1)
    fig = Figure(figsize=(8, 4))
    FigureCanvasAgg(fig)
    (ax,) = burn.plot(res, fig, 'burn')
    assert getattr(ax, '_lss_residuals', None) is None                     # off by default
    (ax,) = burn.plot(res, fig, 'burn', residuals=True)
    rax = ax._lss_residuals
    c = res.trends['intensity']
    f = c.fits[c.best]
    pts = [l for l in rax.get_lines() if l.get_marker() == 'o'][0]
    r = np.asarray(pts.get_ydata(), float)
    assert len(r) == len(c.t)
    assert r == pytest.approx((c.y - f(c.t)) / c.sigma)
    assert np.sum(r ** 2) == pytest.approx(f.chi2, rel=1e-9)               # I37: what the trend fit minimised
    assert any('best: %s, χ²/dof' % c.best in t.get_text() for t in rax.texts)
    fig.canvas.draw()                                                       # lays out with its right axis
    assert rax.get_position().y0 > ax.get_position().y1


@pytest.mark.gui
def test_the_switch_redraws_an_open_burn_dialog(window, qapp, recorder, tmp_path):
    import sweep
    import synth
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp)
    window.ui.pilBurnPushButton.click()
    qapp.processEvents()
    fig = window.uipdburn.burnTrendPlotWidget.canvas.fig
    assert not any(getattr(a, '_lss_residuals', None) for a in fig.axes)
    window.fitResidualsAction.setChecked(True)
    qapp.processEvents()
    fig = window.uipdburn.burnTrendPlotWidget.canvas.fig
    assert any(getattr(a, '_lss_residuals', None) is not None for a in fig.axes)
    assert recorder.exceptions == []
