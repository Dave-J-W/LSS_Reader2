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
