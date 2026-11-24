"""The Pilatus frames display in the main window (F88 sticky display, F70
defaults; owner's answers of 2026-11-23, docs/gui/questions.md Q8, Q9,
Q-IMG-4, 8, 14). Synthetic data: scans 1-2 are reflectivity, 9 and 7 frames.

Before (image_display.md §1.2, measured): the zoom was lost on every redraw,
the colour limits came from the first frame's maximum (the direct beam),
jet and bicubic were the defaults, and Select All drew the first 10 frames."""
import json
import os

import numpy as np
import pytest
from matplotlib.backend_bases import _Mode
from matplotlib.colors import LogNorm, Normalize

import sweep
from lss_core import display, preferences

pytestmark = pytest.mark.gui


def _images(w):
    return [ax for ax in w.ui.pilMplWidget.canvas.fig.axes if ax.images]


def _one_frame(w, qapp, scan_row=0, frame=0):
    sweep._select_scans(w, qapp, [scan_row])
    sweep._select_images(w, qapp, [frame])
    w.flushPendingSelection()


def _zoom(w, x, y, box=True):
    """What the toolbar's zoom box does: the limits of the axes, in zoom mode."""
    tb = w.ui.pilMplWidget.toolbar
    tb.mode = _Mode.ZOOM if box else _Mode.PAN
    ax = _images(w)[0]
    ax.set_xlim(x)
    ax.set_ylim(y)
    tb.mode = _Mode.NONE
    w.pilViewReleased(None)


def test_defaults_viridis_nearest_and_log_by_kind(loaded, qapp, recorder):
    w = loaded
    _one_frame(w, qapp)
    assert recorder.exceptions == []
    assert w.ui.pilCMapComboBox.currentText() == 'viridis'
    assert w.ui.pilCMapComboBox.findText('jet') >= 0                 # jet kept (Q-IMG-14)
    im = _images(w)[0].images[0]
    assert im.get_interpolation() == 'nearest'                        # Q-IMG-8
    assert w.pilKind == 'ref'                                         # an inferred reflectivity series
    assert w.ui.pilLogIntCheckBox.isChecked()                         # Q8: log for reflectivity
    assert isinstance(im.norm, LogNorm) and im.norm.vmin > 0
    assert _images(w)[0].get_title() == 'S# 1 pt 0'                   # the point number, not the list row
    assert w.pilView['cbar'].ax.get_ylabel() == display.units()


def test_limits_are_robust_and_shared_by_the_selection(loaded, qapp, recorder):
    """Q8, Q-IMG-4: the top at the 99.9th percentile of all selected frames per
    Monc, the direct beam left out; one norm for every tile."""
    w = loaded
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp, [0, 4])
    w.flushPendingSelection()
    frames = [w.pilFrameNormalised(i)[0] for i in w.selectedPilFramesNums]
    masks = [w.pilBeamMask(j, f.shape) for j, f in enumerate(frames)]
    lo, hi = display.robust_limits(frames, True, masks)
    norms = [ax.images[0].norm for ax in _images(w)]
    assert len(norms) == 2 and all(n is norms[0] for n in norms)
    assert (norms[0].vmin, norms[0].vmax) == pytest.approx((lo, hi))
    assert float(w.ui.pilMaxLineEdit.text()) == pytest.approx(hi, rel=1e-5)
    assert w.imageMax == pytest.approx(max(f.max() for f in frames))  # the sliders' end, per Monc
    assert recorder.exceptions == []


def test_zoom_survives_redraws_scans_and_settings(loaded, qapp, recorder):
    w = loaded
    _one_frame(w, qapp)
    ax = _images(w)[0]
    _zoom(w, (60.0, 120.0), (80.0, 140.0))
    w.ui.pilLogIntCheckBox.setChecked(False)                          # log off
    w.ui.pilCMapComboBox.setCurrentIndex(w.ui.pilCMapComboBox.findText('jet'))
    _one_frame(w, qapp, frame=3)                                      # another frame
    _one_frame(w, qapp, scan_row=1, frame=2)                          # another scan
    qapp.processEvents()
    ax2 = _images(w)[0]
    assert ax2 is ax                                                  # redrawn in place
    assert ax2.get_xlim() == pytest.approx((60.0, 120.0)) and ax2.get_ylim() == pytest.approx((80.0, 140.0))
    assert w.ui.pilCMapComboBox.currentText() == 'jet'
    assert not w.ui.pilLogIntCheckBox.isChecked()                     # the choice for reflectivity frames
    assert isinstance(ax2.images[0].norm, Normalize) and not isinstance(ax2.images[0].norm, LogNorm)
    assert recorder.exceptions == []


def test_home_and_fit_all(loaded, qapp, recorder):
    w = loaded
    _one_frame(w, qapp)
    ax = _images(w)[0]
    full = ax.get_xlim() + ax.get_ylim()
    _zoom(w, (60.0, 120.0), (80.0, 140.0))                            # a zoom box: the Home view
    _zoom(w, (70.0, 130.0), (90.0, 150.0), box=False)                 # then a pan
    w.ui.pilFitAllPushButton.click()
    assert ax.get_xlim() + ax.get_ylim() == pytest.approx(full)
    w.ui.pilHomePushButton.click()
    assert ax.get_xlim() == pytest.approx((60.0, 120.0)) and ax.get_ylim() == pytest.approx((80.0, 140.0))
    home = [a for a in w.ui.pilMplWidget.toolbar.actions() if a.text() == 'Home'][0]
    home.trigger()                                                    # matplotlib's house icon: Fit all
    assert ax.get_xlim() + ax.get_ylim() == pytest.approx(full)
    for b in (w.ui.pilHomePushButton, w.ui.pilFitAllPushButton, w.ui.pilAutoScalePushButton):
        assert b.toolTip()
    assert recorder.exceptions == []


def test_zoom_follows_a_change_of_axes(loaded, qapp, recorder):
    """The zoom is kept on the same pixels when Axes changes Pixels -> Q -> Pixels."""
    w = loaded
    _one_frame(w, qapp)
    _zoom(w, (60.0, 120.0), (80.0, 140.0))
    w.ui.pilAxesComboBox.setCurrentIndex(w.ui.pilAxesComboBox.findText('Q'))
    ax = _images(w)[0]
    assert ax.get_ylim()[1] < 1.0                                     # now in 1/A
    w.ui.pilAxesComboBox.setCurrentIndex(w.ui.pilAxesComboBox.findText('Pixels'))
    assert ax.get_xlim() == pytest.approx((60.0, 120.0)) and ax.get_ylim() == pytest.approx((80.0, 140.0))
    assert recorder.exceptions == []


def test_typed_limits_stick_until_auto_scale(loaded, qapp, recorder):
    w = loaded
    _one_frame(w, qapp)
    w.ui.pilMinLineEdit.setText('-2')                                 # a negative Min on a log scale
    w.ui.pilMaxLineEdit.setText('5e-3')
    w.ui.pilMaxLineEdit.returnPressed.emit()
    norm = _images(w)[0].images[0].norm
    assert norm.vmax == pytest.approx(5e-3) and 0 < norm.vmin < norm.vmax   # never log10 of -2 (NaN)
    _one_frame(w, qapp, frame=5)
    assert _images(w)[0].images[0].norm.vmax == pytest.approx(5e-3)   # kept for the next frame
    w.ui.pilAutoScalePushButton.click()
    assert _images(w)[0].images[0].norm.vmax != pytest.approx(5e-3)
    assert recorder.exceptions == []


def test_sliders_run_from_the_smallest_to_the_largest_value(loaded, qapp, recorder):
    w = loaded
    _one_frame(w, qapp)
    w.ui.pilLogIntCheckBox.setChecked(False)
    s = w.ui.pilMaxHorizontalSlider
    s.setValue(100)
    s.sliderReleased.emit()
    assert float(w.ui.pilMaxLineEdit.text()) == pytest.approx(w.imageMax, rel=1e-5)
    w.ui.pilMinHorizontalSlider.setValue(0)
    w.ui.pilMinHorizontalSlider.sliderReleased.emit()
    assert float(w.ui.pilMinLineEdit.text()) == pytest.approx(w.imageMin, rel=1e-5)   # min included
    assert recorder.exceptions == []


def test_select_all_never_draws_more_than_six_tiles(loaded, qapp, recorder):
    w = loaded
    w.ui.pilViewComboBox.setCurrentIndex(w.ui.pilViewComboBox.findData('tiles6'))   # not the movie
    sweep._select_scans(w, qapp, [0])                                 # 9 frames
    sweep._select_images(w, qapp)
    w.flushPendingSelection()
    axs = _images(w)
    assert len(axs) == 6
    assert [ax.get_title() for ax in axs] == ['S# 1 pt %d' % p for p in display.sample(9, 6)]
    assert '6 of 9 shown (sampled)' in w.ui.pilMplWidget.canvas.fig._suptitle.get_text()
    assert recorder.exceptions == []


def test_kept_between_sessions_and_reset_by_another_spec_file(window, dataset, qapp, recorder, tmp_path):
    import synth
    from mainwindow import MainWindow
    w = window
    w.openSpecFile(fname=dataset)
    w.directory = str(tmp_path)
    _one_frame(w, qapp)
    _zoom(w, (60.0, 120.0), (80.0, 140.0))
    w.ui.pilCMapComboBox.setCurrentIndex(w.ui.pilCMapComboBox.findText('magma'))
    stored = json.load(open(os.environ[preferences.ENV]))['pil_display']
    assert stored['cmap'] == 'magma' and stored['zoom']['x'] == [60.0, 120.0]
    assert stored['spec'] == os.path.abspath(dataset)
    w2 = MainWindow()                                                 # the next session
    w2.show()
    assert w2.ui.pilCMapComboBox.currentText() == 'magma'
    w2.openSpecFile(fname=dataset)                                    # the same file: kept
    w2.directory = str(tmp_path)
    _one_frame(w2, qapp)
    ax = _images(w2)[0]
    assert ax.get_xlim() == pytest.approx((60.0, 120.0))
    other = synth.make_dataset(tmp_path / 'other')
    w2.openSpecFile(fname=other)                                      # another file: reset
    w2.directory = str(tmp_path)
    assert w2.ui.pilCMapComboBox.currentText() == 'viridis'
    _one_frame(w2, qapp)
    ax = _images(w2)[0]
    assert ax.get_xlim() == pytest.approx(tuple(ax.images[0].get_extent()[:2]))
    assert json.load(open(os.environ[preferences.ENV]))['pil_display'] == {'spec': os.path.abspath(other)}
    assert recorder.exceptions == []
