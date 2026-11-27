"""The comprehensive plot customization (F114; owner, 2026-11-27: "begin the
comprehensive solution for plot customization", the "one merged, saved
window"): per tab, kept through redraws and between sessions, besides
F112's options: tick numbers, the legend, line width, marker size, titles;
per plot, its title and axis labels renamed, fixed ranges, and each curve's
colour, line, width, marker and size, kept by the curve's name or by its
position. Applied by the canvas at every draw (mplwidget.apply_plot_options)."""
import numpy as np
import pytest
from matplotlib.colors import to_hex

import mplwidget
import sweep

pytestmark = pytest.mark.gui
PID = 'canvas:0'


def _canvas(opts):
    c = mplwidget.MplCanvas()
    c.setObjectName('canvas')
    c.resize(500, 350)
    c.plot_options = lambda: opts
    return c


def _draw_two(c):
    ax = c.ax
    ax.clear()
    x = np.linspace(0, 1, 6)
    mplwidget.errorbars(ax, x, x, 0.05 + 0 * x, fmt='o-', label='S 4')
    ax.errorbar(x, 1 - x, 0.05 + 0 * x, fmt='s-', label='Fit (peak)', capsize=3)
    ax.axhline(0.5, color='0.5')                          # a reference line: not a curve
    ax.set_xlabel('sh')
    ax.set_ylabel('Pilatus')
    ax.set_title('S# 4')
    ax.legend()
    c.draw()
    return ax


def test_curves_by_position_and_by_name_with_their_bars_and_swatches(qapp):
    opts = {'plots': {PID: {'curves': [
        {'match': 'position', 'key': 1, 'color': 'tab:red', 'linestyle': '--', 'marker': 's', 'linewidth': 3.0,
         'markersize': 0},
        {'match': 'name', 'key': 'Fit (peak)', 'color': 'black', 'linestyle': AS, 'marker': AS, 'linewidth': 0,
         'markersize': 9.0}]}}}
    c = _canvas(opts)
    ax = _draw_two(c)
    curves = mplwidget.data_curves(ax)
    assert [n for _l, n in curves] == ['S 4', 'Fit (peak)']                  # the axhline is not a curve
    s4, fit = curves[0][0], curves[1][0]
    assert to_hex(s4.get_color()) == to_hex('tab:red') and s4.get_linestyle() == '--' and s4.get_marker() == 's'
    assert s4.get_linewidth() == 3.0
    bars = [l for l in ax.lines if getattr(l, '_lss_bar_of', None) is s4][0]
    assert to_hex(bars.get_color()) == to_hex('tab:red')                      # its error bars follow
    assert to_hex(fit.get_color()) == '#000000' and fit.get_markersize() == 9.0
    cont = [k for k in ax.containers if k.lines[0] is fit][0]
    assert all(to_hex(cap.get_color()) == '#000000' for cap in cont.lines[1])
    leg = ax.get_legend()
    sw = {t.get_text(): h for h, t in zip(leg.legend_handles, leg.get_texts())}
    assert to_hex(sw['S 4'].get_color()) == to_hex('tab:red')                # the legend agrees
    _draw_two(c)                                                              # redrawn: the same
    assert to_hex(mplwidget.data_curves(c.ax)[0][0].get_color()) == to_hex('tab:red')


AS = mplwidget.AS_DRAWN


def test_renames_follow_the_drawn_text_and_survive_redraws(qapp):
    opts = {'plots': {PID: {'labels': {'Pilatus': 'Counts / monitor', 'S# 4': 'Scan four'}}}}
    c = _canvas(opts)
    ax = _draw_two(c)
    assert ax.get_ylabel() == 'Counts / monitor' and ax.get_title() == 'Scan four' and ax.get_xlabel() == 'sh'
    assert mplwidget.drawn_text(ax.yaxis.label) == 'Pilatus'
    c.draw()                                                                  # drawn again: no double rename
    assert ax.get_ylabel() == 'Counts / monitor'
    ax.set_ylabel('YAP')                                                      # another column: its own name
    c.draw()
    assert ax.get_ylabel() == 'YAP'
    _draw_two(c)
    opts['plots'][PID]['labels'] = {}                                         # the rename taken back
    c.draw()
    assert c.ax.get_ylabel() == 'Pilatus'


def test_fixed_ranges_on_redraw_and_zoom_still_works(qapp):
    opts = {'plots': {PID: {'xlim': [0.2, 0.6], 'ylim': [0.0, 2.0]}}}
    c = _canvas(opts)
    ax = _draw_two(c)
    assert ax.get_xlim() == pytest.approx((0.2, 0.6)) and ax.get_ylim() == pytest.approx((0.0, 2.0))
    ax.set_xlim(0.3, 0.4)                                                     # a zoom
    c.draw()
    assert ax.get_xlim() == pytest.approx((0.3, 0.4))                         # not undone
    _draw_two(c)                                                              # the reader redraws
    assert c.ax.get_xlim() == pytest.approx((0.2, 0.6))


def test_legend_titles_tick_numbers_and_widths(qapp):
    opts = {'legend': 'hidden', 'titles': 'hidden', 'ticknum': 'scientific', 'linewidth': 4.0, 'markersize': 2.0,
            'plots': {PID: {'curves': [{'match': 'position', 'key': 2, 'color': AS, 'linestyle': AS, 'marker': AS,
                                        'linewidth': 1.0, 'markersize': 0}]}}}
    c = _canvas(opts)
    ax = _draw_two(c)
    assert not ax.get_legend().get_visible() and not ax.title.get_visible()
    s4, fit = (l for l, _n in mplwidget.data_curves(ax))
    assert s4.get_linewidth() == 4.0 and s4.get_markersize() == 2.0           # the tab's
    assert fit.get_linewidth() == 1.0 and fit.get_markersize() == 2.0         # the curve's width wins
    fmt = ax.yaxis.get_major_formatter()
    assert fmt._useMathText and fmt._scientific
    opts.update(legend='shown', legend_loc='lower left', legend_frame='off', titles=AS)
    _draw_two(c)
    leg = c.ax.get_legend()
    assert leg.get_visible() and leg._loc == 3 and not leg.get_frame_on()
    assert mplwidget.plot_options_set({'plots': {PID: {'xlim': [0, 1]}}})
    assert not mplwidget.plot_options_set({'plots': {PID: {'labels': {}, 'curves': []}}})


def test_the_window_on_the_specplot(loaded, qapp, recorder):
    from lss_core import preferences
    w = loaded
    w.ui.PlotWidget.setCurrentWidget(w.ui.specPlotTab)
    sweep._select_scans(w, qapp, [3])
    qapp.processEvents()
    d = w.showPlotOptions()
    d.pages.setCurrentIndex(2)
    assert d.plotCombo.currentData() == 'specPlotMplWidget:0'
    e = d.labelEdits['y']
    col = e.placeholderText()                                 # the reader's y label (the column drawn)
    assert col and e.text() == ''
    e.setText('Counts / monitor')
    e.editingFinished.emit()
    qapp.processEvents()
    ax = w.ui.specPlotMplWidget.canvas.ax
    w.ui.specPlotMplWidget.canvas.draw()
    assert ax.get_ylabel() == 'Counts / monitor'
    assert d.curveList.count() >= 2                                          # the scan and its fit
    d.curveList.setCurrentRow(0)
    d.curveFields['color'].setCurrentIndex(d.curveFields['color'].findData('tab:red'))
    qapp.processEvents()
    assert d.curveList.currentRow() == 0                                      # the choice stays put
    assert preferences.load()['plot_options']['specPlotTab']['plots']['specPlotMplWidget:0']['curves']   # saved
    sweep._select_scans(w, qapp, [0])                                         # away and back: redrawn
    sweep._select_scans(w, qapp, [3])
    w.ui.PlotWidget.setCurrentWidget(w.ui.specPlotTab)
    qapp.processEvents()
    ax = w.ui.specPlotMplWidget.canvas.ax
    w.ui.specPlotMplWidget.canvas.draw()
    assert ax.get_ylabel() == 'Counts / monitor'
    assert to_hex(mplwidget.data_curves(ax)[0][0].get_color()) == to_hex('tab:red')
    stored = preferences.load()['plot_options']['specPlotTab']['plots']['specPlotMplWidget:0']
    assert stored['labels'] == {col: 'Counts / monitor'} and stored['curves'][0]['color'] == 'tab:red'
    lo, hi = ax.get_xlim()
    z = (lo + 0.25 * (hi - lo), lo + 0.5 * (hi - lo))
    ax.set_xlim(*z)                                                           # zoom, then keep the view
    d.use_view()
    assert stored != preferences.load()['plot_options']['specPlotTab']['plots']['specPlotMplWidget:0']
    sweep._select_scans(w, qapp, [3])
    qapp.processEvents()
    w.ui.specPlotMplWidget.canvas.draw()
    assert w.ui.specPlotMplWidget.canvas.ax.get_xlim() == pytest.approx(z, rel=1e-4)
    d.fields['grid'].setCurrentIndex(d.fields['grid'].findData('major'))     # tab-wide, then to all tabs
    d.copy_all()
    ref = preferences.load()['plot_options']['refTab']
    assert ref['grid'] == 'major' and not ref.get('plots')
    d.plotResetButton.click()                                                 # this plot as drawn
    qapp.processEvents()
    w.ui.specPlotMplWidget.canvas.draw()
    assert w.ui.specPlotMplWidget.canvas.ax.get_ylabel() == col
    assert 'plots' not in preferences.load()['plot_options']['specPlotTab'] or \
        not preferences.load()['plot_options']['specPlotTab']['plots']
    assert recorder.exceptions == []
