"""File > Preferences (owner, 2026-11-18): the calibrated foils on show and
their switch, and the Ref Patch known-ratio settings, kept between
sessions (lss_core.preferences; the tests use a temporary file)."""
import json
import os

import pytest

import sweep
from lss_core import absorbers, preferences


def _prefs_dialog(w, qapp):
    w.ui.actionPreferences.trigger()
    qapp.processEvents()
    d = w.preferencesDialog
    assert d.isVisible()
    return d


def test_dialog_shows_the_foils_with_tooltips(window, qapp, recorder):
    d = _prefs_dialog(window, qapp)
    t = d.prefFoilTable
    assert t.rowCount() == 6
    assert [t.item(k, 2).text() for k in range(6)] == ['%.1f' % v for v in absorbers.CAL_FOILS_UM]
    assert [t.item(k, 1).text() for k in range(6)] == ['50', '100', '200', '400', '800', '1600']
    assert [t.item(k, 3).text() for k in range(6)] == ['0.6', '0.5', '0.8', '0.6', '1.3', '1.3']
    assert '+/- 0.6 um run to run' in t.item(0, 2).toolTip()
    assert 'Qz >= 0.25' in t.horizontalHeaderItem(3).toolTip()
    for widget in (d.prefCalibratedCheckBox, t, d.prefPatchAutoCheckBox, d.prefPatchThresholdSpinBox):
        assert widget.toolTip()
    assert 'physics_notes' in t.toolTip()                  # where the numbers come from
    assert d.prefCalibratedCheckBox.isChecked() and d.prefPatchAutoCheckBox.isChecked()
    assert d.prefPatchThresholdSpinBox.value() == 3.0
    assert recorder.exceptions == []


def test_settings_are_saved_and_read_back(window, qapp, recorder):
    d = _prefs_dialog(window, qapp)
    d.prefPatchThresholdSpinBox.setValue(5.5)
    d.prefPatchAutoCheckBox.setChecked(False)
    assert not d.prefPatchThresholdSpinBox.isEnabled()
    d.prefCalibratedCheckBox.setChecked(False)
    with open(os.environ[preferences.ENV]) as f:
        stored = json.load(f)
    assert stored == {'calibrated_foils': False, 'patch_auto_known_ratio': False,
                      'patch_threshold_percent': 5.5, 'mca_channels': []}   # mca_channels: 2026-11-19
    assert preferences.load() == stored
    assert recorder.exceptions == []


def test_calibrated_foils_at_10_kev_and_the_switch(loaded, qapp, recorder):
    """Synthetic data are at 1.24 A (10.00 keV): "from E" now gives the
    calibrated foils ("cal"); with the preference off, 1.4247 as before."""
    w = loaded
    sweep._select_scans(w, qapp, [0])
    assert w.ui.AbsFacLineEdit.text() == 'cal'
    assert w.absorberModel() == absorbers.calibrated(10.0)
    assert 'calibrated foils at 10.00 keV' in w.ui.AbsFacLineEdit.toolTip()   # said in the tooltip, not a message
    d = _prefs_dialog(w, qapp)
    d.prefCalibratedCheckBox.setChecked(False)
    qapp.processEvents()
    assert w.ui.AbsFacLineEdit.text() == '1.4247' and w.absorberModel() == 1.4247
    d.prefCalibratedCheckBox.setChecked(True)
    qapp.processEvents()
    assert w.ui.AbsFacLineEdit.text() == 'cal'
    w.absFacEnergyCheckBox.setChecked(False)              # typed value replaces the foils
    assert w.ui.AbsFacLineEdit.text() == '1.4247' and w.absorberModel() == 1.4247
    assert recorder.exceptions == []
