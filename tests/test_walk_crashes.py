"""Three crashes the crash sweep's random walks reached on 2026-11-23 (found
by the Tools-menu session; the walks' draws shifted with its new control).
They were latent on main; each is fixed in the window."""
import numpy as np
import pytest

import sweep

pytestmark = pytest.mark.gui


def test_ref_close_up_with_vertical_background(loaded, qapp, recorder, dataset):
    """refQzListSelectionChanged scaled the vertical-background close-up with
    the horizontal background's centres (bglcen, bgrcen), which setROI sets
    only for 'H': AttributeError on a fresh detector, a stale region after
    an 'H' run. Now the region the close-up shows."""
    sweep.state_pilatus_two_scans_all_frames(loaded, qapp, dataset)
    loaded.ui.refBGDirComboBox.setCurrentIndex(loaded.ui.refBGDirComboBox.findText('V'))
    qapp.processEvents()
    loaded.ui.pilRefPushButton.click()                     # a fresh detector: no 'H' centres at all
    qapp.processEvents()
    assert loaded.ui.refQzListWidget.count() > 0
    loaded.ui.refCenCheckBox.setChecked(True)
    loaded.ui.refQzListWidget.clearSelection()
    loaded.ui.refQzListWidget.item(0).setSelected(True)
    qapp.processEvents()
    assert recorder.exceptions == []
    d = loaded.pilatus
    s, c = loaded.slit, loaded.cen
    shown = d.imageData[max(0, d.bgucen - s[1]):d.bgdcen + s[1] + 1, c[0] - s[0]:c[0] + s[0] + 1]
    assert loaded.vmax == pytest.approx(np.max(shown))


def test_specplot_log_scale_with_nothing_positive(loaded, qapp, recorder, dataset):
    """specPlotSettings set a log axis whatever the data; with no finite
    positive value (here, normalised by a monitor column of zeros: all inf)
    matplotlib raised while drawing. Now the axis stays linear, with a note
    in the status bar."""
    sweep.state_motor_scan(loaded, qapp, dataset)
    for d in loaded.specData.values():
        if isinstance(d, dict) and 'Monc' in d:
            d['Monc'] = np.zeros_like(np.asarray(d['Monc'], float))
    loaded.ui.spYComboBox.setCurrentIndex(loaded.ui.spYComboBox.findText('Apex2'))
    loaded.ui.spNComboBox.setCurrentIndex(loaded.ui.spNComboBox.findText('Monc'))
    loaded.ui.spNCheckBox.setChecked(True)
    loaded.ui.spLogYCheckBox.setChecked(True)
    loaded.updateSpecPlotData()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert loaded.ui.specPlotMplWidget.canvas.ax.get_yscale() == 'linear'
    assert 'log' in loaded.ui.statusBar.currentMessage().lower()


def test_specplot_log_scale_with_limits_at_or_below_zero(loaded, qapp, recorder, dataset):
    """The raising case itself: limits fixed at or below zero (autoscale off)
    and no positive data, then log y: matplotlib's log locator raised
    'Data cannot be log-scaled because all values are <= 0' while drawing."""
    sweep.state_motor_scan(loaded, qapp, dataset)
    for d in loaded.specData.values():
        if isinstance(d, dict) and 'Apex2' in d:
            d['Apex2'] = -np.abs(np.asarray(d['Apex2'], float))
    loaded.ui.spYComboBox.setCurrentIndex(loaded.ui.spYComboBox.findText('Apex2'))
    loaded.ui.spNCheckBox.setChecked(False)
    loaded.updateSpecPlotData()
    loaded.ui.specPlotMplWidget.canvas.ax.set_ylim(-1200, -5)
    loaded.ui.spLogYCheckBox.blockSignals(True)
    loaded.ui.spLogYCheckBox.setChecked(True)
    loaded.ui.spLogYCheckBox.blockSignals(False)
    loaded.specPlotSettings()                               # on the plot as it is (no replot)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert loaded.ui.specPlotMplWidget.canvas.ax.get_yscale() == 'linear'


def test_pilatus_display_with_an_empty_distance_field(loaded, qapp, recorder, dataset):
    """With the SPEC box unticked, the typed distance and direct-beam
    position were read with float(): an empty field raised. Now one message
    and the SPEC values for that redraw; the typed fields are left alone."""
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.ui.pilSpecCheckBox.setChecked(False)
    loaded.ui.pilSDDistLineEdit.setText('')
    recorder.messages.clear()
    loaded.updatePilPlotData()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert len(recorder.messages) == 1 and 'SPEC values' in recorder.messages[0]
    assert loaded.ui.pilSDDistLineEdit.text() == ''
    assert np.allclose(loaded.distance, loaded.pilSelected_Dist)
