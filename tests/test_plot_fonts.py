"""Plot text at least as large as the tab labels (owner, 2026-11-26: "axes
scales and labeling need an upgrade, mostly in terms of default size of the
font ... at least as large as the tab label font size").

The tab font follows the system's display scaling; matplotlib's figures do
not (rcParams figure.dpi, 100 by default), so at 150 % scaling Windows'
9 pt tab font is 18 logical pixels while matplotlib's 10 pt is 13.9. The
window sets matplotlib's base size from the tab font before it builds its
plots: pt = px x 72 / dpi, never below matplotlib's 10 pt."""
import matplotlib
import pytest

import mplwidget


@pytest.mark.parametrize('px, dpi, pt', [
    (18, 100, 12.96),         # Segoe UI 9 pt at 150 % scaling, matplotlib's default dpi
    (15, 100, 10.8),          # 125 %
    (12, 100, 10.0),          # 100 %: matplotlib's 10 pt is already larger
    (17, 200, 10.0),          # this cloud's matplotlibrc (figure.dpi 200)
])
def test_plot_font_points(px, dpi, pt):
    assert mplwidget.plot_font_points(px, dpi) == pytest.approx(pt)


def _logical_dpi(canvas):
    """The figure's dpi in logical pixels: matplotlib's Qt canvas multiplies it by
    the screen's device pixel ratio (Qt's own high-DPI scaling), the tabs' text
    height is in logical pixels."""
    return canvas.figure.dpi / (getattr(canvas, 'device_pixel_ratio', 1) or 1)


@pytest.mark.gui
def test_the_window_sizes_plot_text_from_the_tabs(qapp, recorder, monkeypatch):
    """18 px tabs (Segoe UI 9 pt at 150 % scaling) at matplotlib's 100 dpi.
    The tab size is given through mplwidget.tab_text_px, our own function:
    monkeypatching Qt's static QApplication.font did not reach the window on
    Windows (#152; plotFontPt came out 10.0), so the test depended on the
    platform rather than on the reader."""
    from mainwindow import MainWindow
    import sweep
    monkeypatch.setitem(matplotlib.rcParams, 'figure.dpi', 100.0)     # matplotlib's own default
    monkeypatch.setitem(matplotlib.rcParams, 'font.size', 10.0)       # restored after the test
    monkeypatch.setattr(mplwidget, 'tab_text_px', lambda: 18)         # the tabs at 150 % scaling
    w = MainWindow()
    try:
        assert w.plotFontPt == pytest.approx(12.96, abs=0.05)
        canvas = w.ui.specPlotMplWidget.canvas
        ax = canvas.ax
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel('sh')
        canvas.draw()
        dpi = _logical_dpi(canvas)
        tick = ax.xaxis.get_major_ticks()[0].label1.get_size()
        assert tick * dpi / 72 >= 18 - 0.1 and ax.xaxis.label.get_size() * dpi / 72 >= 18 - 0.1
    finally:
        sweep.dispose(w, qapp, recorder)
    assert recorder.exceptions == []


@pytest.mark.gui
def test_the_tab_size_is_read_from_the_tab_font_on_this_platform(qapp, recorder, monkeypatch):
    """Whatever this platform's tab font and scaling: tab_text_px reads the tab
    font, and the window's plot text is at least that tall (#152)."""
    from PyQt5.QtGui import QFontInfo
    from PyQt5.QtWidgets import QApplication
    from mainwindow import MainWindow
    import sweep
    monkeypatch.setitem(matplotlib.rcParams, 'font.size', 10.0)
    px = mplwidget.tab_text_px()
    assert px == QFontInfo(QApplication.font('QTabBar')).pixelSize() and px > 0
    w = MainWindow()
    try:
        dpi = matplotlib.rcParams['figure.dpi']
        assert w.plotFontPt == pytest.approx(round(mplwidget.plot_font_points(px, dpi), 1))
        assert w.plotFontPt * dpi / 72 >= px - 0.5
    finally:
        sweep.dispose(w, qapp, recorder)
    assert recorder.exceptions == []


def test_burn_plot_keeps_its_compact_sizes_unless_given_a_base():
    from lss_core import burn
    assert burn._sizes(None)['tick'] == 7 and burn._sizes(None)['axis'] == 8      # the committed figures
    s = burn._sizes(13.0)
    assert s['tick'] == 13.0 and s['axis'] == 13.0 and s['legend'] < 13.0
