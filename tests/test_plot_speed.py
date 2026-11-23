"""Plots drawn fast, showing the same thing (2026-11-23; tests/tools/plot_speed.py
measures them in the window).

- mplwidget.errorbars: the MCA spectra's error bars as one path each, not
  one per channel. 100 spectra of 2048 channels with log y: plotted in
  4.21 -> 0.76 s, log y switched on 2.37 -> 0.54 s.
- mplwidget.mesh: pcolor's maps (the GID patch map in log scale, the 2D_Plot
  tab) as one mesh: 500 x 500 cells redrawn 0.52 -> 0.09 s.
"""
import os

import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection, PolyCollection, QuadMesh
from matplotlib.figure import Figure

import mplwidget
import sweep
import synth


def _axes():
    fig = Figure()
    FigureCanvasAgg(fig)
    return fig.add_subplot(111)


def test_errorbars_draws_errorbars_bars():
    """The same bar ends, colour and width as ax.errorbar, as one path."""
    x = np.linspace(0.01, 20.48, 2048)
    y = np.random.default_rng(1).poisson(3.0, size=x.size).astype(float)
    e = np.sqrt(y)
    ax = _axes()
    line, bars = mplwidget.errorbars(ax, x, y, e, fmt='o-', label='s1')
    ref = _axes().errorbar(x, y, e, fmt='o-', label='s1')
    segs = ref.lines[2][0].get_segments()                    # errorbar: one segment per point
    bx, by = bars.get_xdata(), bars.get_ydata()
    assert np.array_equal(bx[0::3], [s[0, 0] for s in segs]) and np.isnan(bx[2::3]).all()
    assert np.array_equal(by[0::3], [s[0, 1] for s in segs]) and np.array_equal(by[1::3], [s[1, 1] for s in segs])
    assert np.array_equal(line.get_xdata(), x) and np.array_equal(line.get_ydata(), y)
    assert bars.get_color() == line.get_color() and bars.get_linewidth() == line.get_linewidth()
    assert bars.get_zorder() < line.get_zorder() and bars.get_label().startswith('_')
    ax.set_yscale('log')
    ax.figure.canvas.draw()                                   # zeros and non-positive bar ends draw on a log axis


def test_mesh_draws_pcolors_cells():
    xx, yy = np.meshgrid(np.linspace(14, 18, 40), np.linspace(0, 1.2, 30))
    c = np.log10(np.random.default_rng(2).poisson(5.0, size=xx.shape) + 0.0)      # zeros: -inf, masked by both
    a = mplwidget.mesh(_axes(), xx, yy, c, cmap='jet', vmin=0, vmax=1)
    b = _axes().pcolor(xx, yy, c, cmap='jet', vmin=0, vmax=1)
    assert isinstance(a, QuadMesh)
    va, vb = np.ma.masked_invalid(a.get_array()).ravel(), np.ma.masked_invalid(b.get_array()).ravel()
    assert va.count() == vb.count() and np.array_equal(va.compressed(), vb.compressed())
    assert a.axes.get_xlim() == b.axes.get_xlim() and a.axes.get_ylim() == b.axes.get_ylim()
    xx[0, 0] = np.nan                                          # non-finite coordinates: pcolor, which skips them
    assert isinstance(mplwidget.mesh(_axes(), xx, yy, c), PolyCollection)


@pytest.mark.gui
def test_mca_spectra_are_drawn_with_one_bar_path_each(window, qapp, recorder, tmp_path):
    """60 spectra of 2048 channels, log y: a data line and a bar line each,
    no per-channel LineCollection, one legend entry each."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
    import plot_speed
    spec = synth.make_dataset(tmp_path / 'data')
    synth.write_mca(os.path.join(os.path.dirname(spec), 'vortex', 'sample_3_mca'), plot_speed.spectra(60, 2048))
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    window.ui.mcaLegendCheckBox.setChecked(True)
    window.ui.mcaLogYCheckBox.setChecked(True)
    sweep._select_scans(window, qapp, [2])
    sweep._select_images(window, qapp)
    ax = window.ui.mcaPlotMplWidget.canvas.ax
    assert len(window.selectedMcaScanNums) == 60 and ax.get_yscale() == 'log'
    assert sum(len(l.get_xdata()) == 3 * 2048 for l in ax.lines) == 60
    assert not [c for c in ax.collections if isinstance(c, LineCollection) and len(c.get_segments()) > 2]
    assert len(ax.get_legend().get_texts()) == 60
    assert recorder.exceptions == []
