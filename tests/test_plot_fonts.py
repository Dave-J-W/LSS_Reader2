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


@pytest.mark.gui
def test_the_window_sizes_plot_text_from_the_tabs(qapp, recorder, monkeypatch):
    from PyQt5.QtGui import QFont, QFontInfo
    from PyQt5.QtWidgets import QApplication
    from mainwindow import MainWindow
    import sweep
    monkeypatch.setitem(matplotlib.rcParams, 'figure.dpi', 100.0)     # matplotlib's own default
    monkeypatch.setitem(matplotlib.rcParams, 'font.size', 10.0)       # restored after the test
    big = QFont(QApplication.font())
    big.setPixelSize(18)                                               # the tabs at 150 % scaling
    real = QApplication.font
    monkeypatch.setattr(QApplication, 'font', staticmethod(lambda *a: big if a == ('QTabBar',) else real(*a)))
    w = MainWindow()
    try:
        assert w.plotFontPt == pytest.approx(12.96, abs=0.05)
        ax = w.ui.specPlotMplWidget.canvas.ax
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel('sh')
        w.ui.specPlotMplWidget.canvas.draw()
        dpi = w.ui.specPlotMplWidget.canvas.figure.dpi
        tick = ax.xaxis.get_major_ticks()[0].label1.get_size()
        assert tick * dpi / 72 >= 18 - 0.1 and ax.xaxis.label.get_size() * dpi / 72 >= 18 - 0.1
        assert QFontInfo(big).pixelSize() == 18
    finally:
        sweep.dispose(w, qapp, recorder)
    assert recorder.exceptions == []


def test_burn_plot_keeps_its_compact_sizes_unless_given_a_base():
    from lss_core import burn
    assert burn._sizes(None)['tick'] == 7 and burn._sizes(None)['axis'] == 8      # the committed figures
    s = burn._sizes(13.0)
    assert s['tick'] == 13.0 and s['axis'] == 13.0 and s['legend'] < 13.0
