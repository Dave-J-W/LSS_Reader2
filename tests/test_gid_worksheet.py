"""GID patching worksheet (owner, 2026-11-18, F61): the settings that were
numbers in the patch code, editable, with the defaults reproducing the
patch exactly, and a table of what each join did. Real data: NX school
scans 11 (low Qz, 41 frames) and 12 (high Qz, 4 frames)."""
import os

import numpy as np
import pytest

import sweep
from lss_core.gid import GIDParams, reduced_chi2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


def test_defaults_are_the_numbers_the_code_used():
    p = GIDParams()
    assert (p.columns, p.row_min, p.row_max, p.qz_decimals, p.dth_decimals) == (3, 15, 486, 3, 3)
    assert (p.area_correction, p.hard_slit_offset_mm, p.polarisation, p.vjoin_kind) == (True, 32.0, True, 'cubic')
    assert p.changed() == []
    assert GIDParams(row_min=20).changed() == ['row_min']
    assert reduced_chi2([0, 1, 2], [1.1, 0.9, 1.0], [0.1, 0.1, 0.1], 1.0) == pytest.approx(1.0)


@pytest.fixture
def nx(window, qapp, tmp_path):
    window.openSpecFile(fname=SPEC)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [10, 11])
    sweep._select_images(window, qapp)
    return window


def _menu(w, qapp, text):
    i = w.ui.gidComboBox.findText(text)
    assert i >= 0, text
    w.ui.gidComboBox.setCurrentIndex(i)
    w.ui.gidComboBox.activated.emit(i)
    qapp.processEvents()


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_worksheet_shows_the_joins_and_defaults_change_nothing(nx, qapp, recorder):
    _menu(nx, qapp, 'GID Patch')
    before = nx.pilGIDData.copy()
    _menu(nx, qapp, 'Worksheet')
    d = nx.gidWorksheet
    assert d.isVisible()
    assert d.gidColumnsSpinBox.value() == 3 and d.gidRowMinSpinBox.value() == 15
    for w in (d.gidColumnsSpinBox, d.gidRowMinSpinBox, d.gidQzDecimalsSpinBox, d.gidAreaCheckBox,
              d.gidPolCheckBox, d.gidVJoinKindComboBox, d.gidJoinTable):
        assert w.toolTip() or w is d.gidJoinTable
    t = d.gidJoinTable
    assert t.rowCount() == 1                                  # scan 11 (low Qz) + scan 12 (second level): one vertical join
    assert t.item(0, 1).text() == 'vertical (beta)'
    assert int(t.item(0, 4).text()) > 3
    j = nx.gidJoinLog[0]
    assert j['factor'] > 0 and j['error'] > 0 and np.isfinite(j['chi2'])
    assert 'low Qz: S 11, 41 frames' in d.gidLevelsLabel.text() and 'middle Qz: S 12, 4 frames' in d.gidLevelsLabel.text()
    from PyQt5.QtWidgets import QPushButton
    d.findChild(QPushButton, 'gidPatchPushButton').click()     # same settings: same map
    qapp.processEvents()
    assert nx.pilGIDData.tobytes() == before.tobytes()
    assert recorder.exceptions == []


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_worksheet_settings_act_on_the_patch(nx, qapp, recorder):
    from PyQt5.QtWidgets import QPushButton
    _menu(nx, qapp, 'GID Patch')
    rows_before = nx.pilGIDData.shape[0]
    plain = nx.pilGIDData.copy()
    _menu(nx, qapp, 'Worksheet')
    d = nx.gidWorksheet
    patch = d.findChild(QPushButton, 'gidPatchPushButton')
    d.gidRowMinSpinBox.setValue(30)                           # 15 fewer rows per level
    patch.click()
    qapp.processEvents()
    assert nx.pilGIDData.shape[0] < rows_before
    d.findChild(QPushButton, 'gidDefaultsPushButton').click()
    d.gidPolCheckBox.setChecked(False)          # the patch divides by 1-(sin 2θ cos β)² < 1; without it, smaller values
    patch.click()
    qapp.processEvents()
    assert nx.pilGIDData.shape == plain.shape
    assert np.nanmean(nx.pilGIDData / plain) < 1.0
    d.findChild(QPushButton, 'gidDefaultsPushButton').click()
    patch.click()
    qapp.processEvents()
    assert nx.pilGIDData.tobytes() == plain.tobytes()          # defaults restore the original map
    d.gidColumnsSpinBox.setValue(5)
    assert nx.ui.pilHSlitLineEdit.text() == '5'               # one setting, two places
    assert recorder.exceptions == []


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_pinhole_mode_from_the_worksheet(nx, qapp, recorder):
    """F45: pinhole mode makes a map with one column per 2θ bin (many more
    than frames) from the same frames; off again, the legacy map is back
    byte for byte. The Fit button reports a distance without applying it."""
    from PyQt5.QtWidgets import QPushButton
    sweep._select_scans(nx, qapp, [10])                       # scan 11 only: one Qz level
    sweep._select_images(nx, qapp)
    _menu(nx, qapp, 'GID Patch')
    legacy = nx.pilGIDData.copy()
    assert legacy.shape[1] == 41                              # one profile per frame
    _menu(nx, qapp, 'Worksheet')
    d = nx.gidWorksheet
    assert not d.gidPinholeCheckBox.isChecked() and not d.gidPinholeDistSpinBox.isEnabled()
    d.gidPinholeCheckBox.setChecked(True)
    assert nx.gidParams.pinhole and not d.gidColumnsSpinBox.isEnabled()
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert nx.pilGIDData.shape[1] > 150                       # 2θ bins of one column (0.036°) over 13.3-20°
    assert nx.pilGIDData.shape[0] == legacy.shape[0]          # same rows
    x = nx.pilGIDXAxs[0]
    assert np.all(np.diff(x) > 0) and x[0] < 14.0 < 18.0 < x[-1]
    info = nx.gidPinholeInfo[0]
    assert info['counts_used'] > 10 * 32000                   # 3-column patch: ~3.2e4 counts
    d.gidFitDistancePushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    fitted = float(d.gidFitLabel.text().split()[0])
    assert 255 < fitted < 285 and d.gidPinholeDistSpinBox.value() == 0.0    # shown, not applied
    d.gidPinholeCheckBox.setChecked(False)
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    assert nx.pilGIDData.tobytes() == legacy.tobytes()


@pytest.mark.gui
def test_footprint_fraction_is_the_windows_calarea(window):
    """The pinhole footprint fraction is calArea's arithmetic: with the H slit
    at one column, calArea moves S5 to the detector and caps it at one
    pixel, which is the pinhole band of one column."""
    import math
    from lss_core import pinhole as ph
    window.ui.pilHSlitLineEdit.setText('1')
    info = [2.0, 0.1, 0.2, 17.0, math.radians(0.0905), 551.0, 271.0]   # S1h, S1v, S4h, S5h, alpha, S2D, S7D
    for dth in (12.0, 14.0, 16.65, 18.0, 22.0):
        a = window.calArea(info, dth)
        b = ph.area_fraction(2.0, 0.1, 0.2, ph.PIXEL_MM, math.radians(0.0905), 551.0, 551.0 - 271.0, math.radians(dth))
        assert b == pytest.approx(a, rel=1e-12)
