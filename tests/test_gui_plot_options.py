"""The plot options of each tab (F112; owner, 2026-11-26: "Add a plot
preferences button that applies to the plots on that tab that has useful
options, like font size, minor/major ticks, grid on/off"): a button at the
right of the tab bar opens them for the tab on show; each tab keeps its
own between sessions; 'as drawn' (every default) leaves the plots as the
reader draws them, and a choice survives the tab's redraws."""
import pytest

import sweep
from lss_core import preferences

pytestmark = pytest.mark.gui


def _spec(w, qapp):
    w.ui.PlotWidget.setCurrentWidget(w.ui.specPlotTab)
    sweep._select_scans(w, qapp, [3])                     # scan 4: a motor scan (sh)
    qapp.processEvents()
    return w.ui.specPlotMplWidget.canvas


def _set(d, **kw):
    for k, v in kw.items():
        w = d.fields[k]
        if k == 'font':
            w.setValue(v)
        else:
            w.setCurrentIndex(w.findData(v))


def test_defaults_change_nothing_and_the_button_follows_the_tab(loaded, qapp, recorder):
    w = loaded
    b = w.plotOptionsButton
    assert w.ui.PlotWidget.cornerWidget() is b and b.isEnabled()
    canvas = _spec(w, qapp)
    assert not any(l.get_visible() for l in canvas.ax.xaxis.get_gridlines())
    d = w.showPlotOptions()
    assert d.isVisible() and not d.isModal() and d.key == 'specPlotTab'
    assert d.values() == {'font': 0, 'major': 'as drawn', 'minor': 'as drawn', 'direction': 'as drawn',
                          'mirror': 'as drawn', 'grid': 'as drawn', 'index': True}   # index: F113
    assert 'auto (' in d.fields['font'].specialValueText()
    w.ui.PlotWidget.setCurrentWidget(w.ui.refTab)            # the window follows the tab on show
    assert d.key == 'refTab' and 'Reflectivity' in d.windowTitle()
    w.ui.PlotWidget.setCurrentWidget(w.timelineTab)        # no plots there
    assert not b.isEnabled()
    assert recorder.exceptions == []


def test_each_option_on_the_specplot_and_kept(loaded, qapp, recorder):
    w = loaded
    canvas = _spec(w, qapp)
    d = w.showPlotOptions()
    _set(d, font=18, major=5, minor='on', direction='in', mirror='on', grid='major')
    qapp.processEvents()
    ax = canvas.ax
    canvas.draw()
    tick = ax.xaxis.get_major_ticks()[0]
    assert tick.label1.get_size() == 18 and ax.xaxis.label.get_size() == 18
    assert any(l.get_visible() for l in ax.xaxis.get_gridlines())
    assert len(ax.xaxis.get_minorticklocs()) > 0
    assert tick._tickdir == 'in' and tick.tick2line.get_visible()
    assert type(ax.xaxis.get_major_locator()).__name__ == 'MaxNLocator'
    assert preferences.load()['plot_options']['specPlotTab']['font'] == 18      # kept between sessions
    assert w.plotOptionsButton.text().endswith('*')
    w.updateSpecPlotData()                                   # the tab redraws: the choice stays
    ax = canvas.ax
    assert ax.xaxis.get_major_ticks()[0].label1.get_size() == 18
    assert any(l.get_visible() for l in ax.xaxis.get_gridlines())
    other = w.ui.refRefDataPlotwidget.canvas                  # another tab: as drawn
    other.draw()
    assert not any(l.get_visible() for l in other.ax.xaxis.get_gridlines())
    d.resetButton.click()                                    # all 'as drawn': the tab redrawn as the reader draws it
    qapp.processEvents()
    ax = canvas.ax
    assert not any(l.get_visible() for l in ax.xaxis.get_gridlines())
    assert ax.xaxis.get_major_ticks()[0].label1.get_size() != 18
    assert 'specPlotTab' not in preferences.load()['plot_options']
    assert not w.plotOptionsButton.text().endswith('*')
    assert recorder.exceptions == []


def test_grid_major_and_minor_and_the_residual_strip_is_left_alone(loaded, qapp, recorder):
    from lss_core import residuals
    w = loaded
    canvas = _spec(w, qapp)
    d = w.showPlotOptions()
    _set(d, grid='major and minor', font=16)             # the tab redraws (its strip, if any, goes)
    rax = residuals.panel(canvas.ax, True)
    rax.plot([0, 1], [0, 1])
    canvas.draw()
    ax = canvas.ax
    assert any(l.get_visible() for l in ax.xaxis.get_minorticklines())
    assert rax.xaxis.get_major_ticks()[0].label1.get_size() != 16           # the inset as drawn
    residuals.panel(canvas.ax, False)
    assert recorder.exceptions == []


def test_one_entry_matplotlibs_editor_from_inside(loaded, qapp, recorder):
    """The owner (2026-11-26) chose one entry for the tabs' plots: matplotlib's
    "Customize" icon leaves the tabs' toolbars, and its editor (one plot's
    title, limits, labels, scales, line styles; one-off) is "Axes and
    curves..." inside Plot options. Other windows keep the icon."""
    w = loaded
    for name in ('specPlotMplWidget', 'mcaPlotMplWidget', 'refRefDataPlotwidget', 'pilMplWidget'):
        tb = getattr(w.ui, name).canvas.toolbar
        assert not tb._actions['edit_parameters'].isVisible()
    canvas = _spec(w, qapp)
    d = w.showPlotOptions()
    plots = d.plots()
    assert [n for n, _ in plots] and plots[0][1] is canvas.ax and plots[0][0].startswith('Plot 1: ')
    d._fill_axes_menu()
    assert [a.text() for a in d.axesMenu.actions()] == [n for n, _ in plots]
    fe = d.edit_axes(canvas.ax)
    assert fe is not None and fe.isVisible() and not fe.isModal()
    fe.close()
    w.ui.PlotWidget.setCurrentWidget(w.ui.mcaTab)                 # two plots there, each listed once drawn
    assert d.key == 'mcaTab'
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert w.uirefpatch.plotWidget.canvas.toolbar._actions['edit_parameters'].isVisible()   # not a tab: kept
    assert recorder.exceptions == []
