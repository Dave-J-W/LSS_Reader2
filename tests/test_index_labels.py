"""The point index numbers (F113; owner, 2026-11-26: "spacing better, a
checkbox to disable in plot prefs, autohide them when they overlap,
autounhide on zoom to non-overlap condition"). mplwidget.index_labels
places each number a few points from its marker (the same gap at any zoom
and on log axes); declutter_index_labels, run at every draw, hides those
that would overlap or whose point is out of view, and shows them again
when they fit."""
import numpy as np
import pytest

import sweep
import mplwidget

pytestmark = pytest.mark.gui


def _canvas(qapp, w=500, h=350):
    c = mplwidget.MplCanvas()
    c.resize(w, h)
    c.figure.set_size_inches(w / c.figure.dpi, h / c.figure.dpi)
    return c


def _visible(ax):
    return [t for t in ax.texts if getattr(t, '_lss_index', False) and t.get_visible()]


def _overlaps(ax, texts, dpi):
    b = mplwidget._index_boxes(ax, texts, dpi)
    for i in range(len(b)):
        for j in range(i + 1, len(b)):
            if b[i, 0] < b[j, 2] and b[j, 0] < b[i, 2] and b[i, 1] < b[j, 3] and b[j, 1] < b[i, 3]:
                return True
    return False


def test_crowded_numbers_thin_out_and_come_back_on_zoom(qapp):
    c = _canvas(qapp)
    ax = c.ax
    x = np.arange(300.0)
    ax.plot(x, np.sin(x / 20), 'o')
    labels = mplwidget.index_labels(ax, x, np.sin(x / 20), range(300))
    c.draw()
    shown = _visible(ax)
    assert 0 < len(shown) < 300 and not _overlaps(ax, shown, c.figure.dpi)        # thinned, no overlap
    assert shown[0].get_text() == '0'                                              # the first kept
    ax.set_xlim(-0.5, 9.5)                                                          # zoom in: ten points
    c.draw()
    shown = _visible(ax)
    got = {int(t.get_text()) for t in shown}
    assert set(range(9)) <= got <= set(range(10))         # every one in view back (9's may not fit at the edge)
    assert not _overlaps(ax, shown, c.figure.dpi)
    assert all(t.get_text() not in {str(i) for i in range(10, 300)} for t in shown)  # none out of view
    assert all(tuple(abs(v) for v in t.xyann) == (mplwidget.INDEX_OFFSET_PT, mplwidget.INDEX_OFFSET_PT)
               and t.anncoords == 'offset points' for t in labels)                 # the gap is in points


def test_the_gap_is_the_same_at_any_zoom(qapp):
    c = _canvas(qapp)
    ax = c.ax
    ax.plot([1, 2], [1, 2], 'o')
    (t, _) = mplwidget.index_labels(ax, [1, 2], [1, 2], ['0', '1'])
    gaps = []
    for lim in ((0, 3), (0.9, 1.1)):
        ax.set_xlim(*lim)
        ax.set_ylim(*lim)
        c.draw()
        r = c.get_renderer()
        p = ax.transData.transform((1, 1))
        e = t.get_window_extent(r)
        gaps.append((e.x0 - p[0], e.y0 - p[1]))
    assert gaps[0] == pytest.approx(gaps[1], abs=1.0)


def test_unticked_hides_them_and_bad_points_have_none(qapp):
    c = _canvas(qapp)
    ax = c.ax
    y = np.array([1.0, np.nan, -1.0, 2.0])
    ax.plot([0, 1, 2, 3], y, 'o')
    out = mplwidget.index_labels(ax, [0, 1, 2, 3], y, range(4))
    assert [t.get_text() for t in out] == ['0', '2', '3']                        # NaN: no label
    ax.set_yscale('log')                                                        # -1 cannot be drawn
    ax.set_xlim(-1, 5)
    ax.set_ylim(0.5, 10)                                                        # room for the numbers
    c.draw()
    assert {t.get_text() for t in _visible(ax)} == {'0', '3'}
    c.plot_options = lambda: {'index': False}                                   # the Plot options' checkbox
    c.draw()
    assert _visible(ax) == []
    assert mplwidget.plot_options_set({'index': False}) and not mplwidget.plot_options_set({'index': True})


def test_specplot_numbers_and_the_plot_options_checkbox(loaded, qapp, recorder):
    w = loaded
    w.ui.PlotWidget.setCurrentWidget(w.ui.specPlotTab)
    sweep._select_scans(w, qapp, [3])
    qapp.processEvents()
    ax = w.ui.specPlotMplWidget.canvas.ax
    w.ui.specPlotMplWidget.canvas.draw()
    labels = [t for t in ax.texts if getattr(t, '_lss_index', False)]
    assert labels and [t.get_text() for t in labels][:3] == ['0', '1', '2']
    assert _visible(ax) and not _overlaps(ax, _visible(ax), w.ui.specPlotMplWidget.canvas.figure.dpi)
    d = w.showPlotOptions()
    d.fields['index'].setChecked(False)
    qapp.processEvents()
    w.ui.specPlotMplWidget.canvas.draw()
    assert _visible(w.ui.specPlotMplWidget.canvas.ax) == []
    d.fields['index'].setChecked(True)
    qapp.processEvents()
    w.ui.specPlotMplWidget.canvas.draw()
    assert _visible(w.ui.specPlotMplWidget.canvas.ax)
    assert recorder.exceptions == []


def test_ref_patch_numbers(loaded, qapp, recorder):
    w = loaded
    w.prefs['auto_save'] = False
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    c = w.uirefpatch.plotWidget.canvas
    c.draw()
    labels = [t for t in c.ax.texts if getattr(t, '_lss_index', False)]
    blue = [t for t in labels if t.get_color() == 'b']
    red = [t for t in labels if t.get_color() == 'r']
    assert blue and red and all(int(t.get_text()) < 0 for t in blue) and all(int(t.get_text()) >= 0 for t in red)
    assert all(t.xyann[0] < 0 for t in red)                                     # the new scan's below left
    assert not _overlaps(c.ax, _visible(c.ax), c.figure.dpi)
    assert recorder.exceptions == []


def test_a_number_at_the_edge_moves_to_a_corner_that_fits(qapp):
    """A point at the top right corner: its number goes below left of it,
    inside the axes, rather than over the frame; with room it goes back."""
    c = _canvas(qapp)
    ax = c.ax
    ax.plot([0, 1, 2], [0, 1, 2], 'o')
    labels = mplwidget.index_labels(ax, [0, 1, 2], [0, 1, 2], ['0', '1', '2'])
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)                                                   # point 2 at the top right corner
    c.draw()
    assert {t.get_text() for t in _visible(ax)} == {'0', '1', '2'}
    bb = ax.bbox
    b = mplwidget._index_boxes(ax, labels, c.figure.dpi)
    assert np.all(b[:, 0] >= bb.x0 - 1) and np.all(b[:, 2] <= bb.x1 + 1) and np.all(b[:, 3] <= bb.y1 + 1)
    assert labels[2].xyann[0] < 0 and labels[2].xyann[1] < 0             # below left of its marker
    assert labels[0].xyann[0] > 0 and labels[0].xyann[1] > 0             # the bottom left one up right
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(-0.5, 2.5)                                              # room again: its own corner
    c.draw()
    assert labels[2].xyann[0] > 0 and labels[2].xyann[1] > 0
