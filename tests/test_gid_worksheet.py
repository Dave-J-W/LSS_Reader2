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
    assert p.pinhole                                     # the default (owner, 2026-11-18)
    assert p.changed() == []
    assert GIDParams(row_min=20).changed() == ['row_min']
    assert reduced_chi2([0, 1, 2], [1.1, 0.9, 1.0], [0.1, 0.1, 0.1], 1.0) == pytest.approx(1.0)


@pytest.fixture
def nx(window, qapp, tmp_path):
    window.gidParams = GIDParams(pinhole=False)          # these tests start from the legacy patch
    window.openSpecFile(fname=SPEC)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [10, 11])
    sweep._select_images(window, qapp)
    return window


def _menu(w, qapp, text):
    if text in ('GID Patch', 'Worksheet'):          # buttons since 2026-11-23 (Q-GID-5)
        (w.gidPatchPushButton if text == 'GID Patch' else w.gidWorksheetPushButton).click()
        qapp.processEvents()
        return
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
    d.gidPinholeCheckBox.setChecked(False)      # legacy patch, as this test compares with it
    d.gidPolCheckBox.setChecked(False)          # the patch divides by 1-(sin 2θ cos β)² < 1; without it, smaller values
    patch.click()
    qapp.processEvents()
    assert nx.pilGIDData.shape == plain.shape
    assert np.nanmean(nx.pilGIDData / plain) < 1.0
    d.findChild(QPushButton, 'gidDefaultsPushButton').click()
    assert d.gidPinholeCheckBox.isChecked()                    # the default is pinhole (2026-11-18)
    d.gidPinholeCheckBox.setChecked(False)
    patch.click()
    qapp.processEvents()
    assert nx.pilGIDData.tobytes() == plain.tobytes()          # defaults (pinhole off) restore the original map
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
    legacy_beta = nx.pilGIDYAxs[:, 0].copy()
    _menu(nx, qapp, 'Worksheet')
    d = nx.gidWorksheet
    assert not d.gidPinholeCheckBox.isChecked() and not d.gidPinholeDistSpinBox.isEnabled()
    d.gidPinholeCheckBox.setChecked(True)
    assert nx.gidParams.pinhole and not d.gidColumnsSpinBox.isEnabled()
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert nx.pilGIDData.shape[1] > 150                       # 2θ bins of one column (0.036°) over 13.3-20°
    # β: bins one row wide (at the direct beam) over the range every 2θ bin
    # shares; since 2026-11-19 β is per pixel (exact geometry), not per row
    lb, pb = legacy_beta, nx.pilGIDYAxs[:, 0]
    assert np.median(np.diff(pb)) == pytest.approx(np.median(np.diff(lb)), rel=0.02)
    assert lb[0] - 0.05 <= pb[0] and pb[-1] <= lb[-1] + 0.6 and (pb[-1] - pb[0]) > 0.95 * (lb[-1] - lb[0])
    x = nx.pilGIDXAxs[0]
    assert np.all(np.diff(x) > 0) and x[0] < 14.0 < 18.0 < x[-1]
    info = nx.gidPinholeInfo[0]
    assert info['counts_used'] > 10 * 32000                   # 3-column patch: ~3.2e4 counts
    d.gidFitDistancePushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    fitted = float(d.gidFitLabel.text().split()[0])
    # owner, 2026-11-21: calibrate from single frames; the calibrated value is filled in when reliable
    # (was: a response-based fit, shown, not applied). NX scan 11: 265.2 +/- 1.6 mm
    assert fitted == pytest.approx(265.2, abs=1.5) and d.gidPinholeDistSpinBox.value() == pytest.approx(fitted, abs=0.05)
    d.gidPinholeDistSpinBox.setValue(0.0)
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


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_pinhole_is_the_default_gid_patch(window, qapp, recorder, tmp_path):
    """Owner, 2026-11-18: pinhole is how GID is measured. A fresh window's
    GID Patch is the pinhole map; the display and the raw-frame cuts take
    the S4-detector distance for frames at Det_Th > 1 deg; Save GID and the
    GID line cuts work on the pinhole map."""
    w = window
    w.openSpecFile(fname=SPEC)
    w.directory = str(tmp_path)
    qapp.processEvents()
    assert w.ui.pilPinholeCheckBox.isChecked() and w.gidParams.pinhole
    sweep._select_scans(w, qapp, [10])
    sweep._select_images(w, qapp)
    w.ui.pilAxesComboBox.setCurrentIndex(1)                 # Angles: the display uses 271 for these frames
    qapp.processEvents()
    assert np.all(w.distance == 271.0)
    w.ui.pilAxesComboBox.setCurrentIndex(2)                 # Q, as the GID save names its files by it
    qapp.processEvents()
    _menu(w, qapp, 'GID Patch')
    assert w.pilGIDData.shape[1] > 150                      # one column per bin, not one per frame
    recorder.save_name = str(tmp_path / 'pin')
    _menu(w, qapp, 'Save GID')
    assert os.path.exists(str(tmp_path / 'pin_qxy_gid.txt'))
    w.ui.pilCutDirComboBox.setCurrentIndex(0)
    w.ui.pilIntRangeLineEdit.setText('0.0:0.2')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_scripted_cut_uses_the_pinhole_distance_above_one_degree():
    """Experiment.cut follows the window: pinhole (default) gives frames at
    Det_Th > 1 deg one column = p/271 rad on the horizontal Angles axis."""
    import math
    from lss_core.experiment import Experiment
    exp = Experiment(SPEC)
    a = exp.cut([11], 'Pix H', (100, 200), axes='Angles', points={11: [20]}).cuts[0]
    b = exp.cut([11], 'Pix H', (100, 200), axes='Angles', points={11: [20]}, pinhole=False).cuts[0]
    # columns 100-200 lie 53-153 columns from the direct beam: atan makes the step ~0.2 % smaller there
    assert np.diff(a[:, 0]).mean() == pytest.approx(math.degrees(0.172 / 271), rel=5e-3)
    assert np.diff(b[:, 0]).mean() == pytest.approx(math.degrees(0.172 / 551), rel=5e-3)



@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_pinhole_join_of_nx_scans_11_and_12(window, qapp, recorder, tmp_path):
    """F62 on real data: NX scans 11 (low Qz) and 12 (second level) in
    pinhole mode are joined on one β grid with one factor, logged; 'all'
    keeps every level's 2θ range with empty cells; Save GID works."""
    from PyQt5.QtWidgets import QPushButton
    w = window
    w.openSpecFile(fname=SPEC)
    w.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(w, qapp, [10, 11])
    sweep._select_images(w, qapp)
    _menu(w, qapp, 'GID Patch')                                # pinhole is the default
    assert recorder.exceptions == []
    joins = [j for j in w.gidJoinLog if j['kind'] == 'vertical (beta)']
    assert len(joins) == 1 and joins[0]['factor'] > 0 and np.isfinite(joins[0]['chi2'])
    common = w.pilGIDData.shape
    assert not np.isnan(w.pilGIDData).any()
    _menu(w, qapp, 'Worksheet')
    d = w.gidWorksheet
    d.gidTransverseComboBox.setCurrentIndex(1)                 # all
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    assert w.pilGIDData.shape[1] >= common[1] and np.isnan(w.pilGIDData).any()
    recorder.save_name = str(tmp_path / 'joined')
    _menu(w, qapp, 'Save GID')
    assert recorder.exceptions == []


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_beam_response_and_resolution_in_the_worksheet(nx, qapp, recorder):
    """Response "beam" (owner, 2026-11-19) from the worksheet; the 2θ
    resolution and the beam's position are shown with the levels."""
    sweep._select_scans(nx, qapp, [10])
    sweep._select_images(nx, qapp)
    _menu(nx, qapp, 'Worksheet')
    d = nx.gidWorksheet
    d.gidPinholeCheckBox.setChecked(True)
    d.gidResponseComboBox.setCurrentText('beam')
    from PyQt5.QtWidgets import QPushButton
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    assert nx.gidParams.response == 'beam' and recorder.exceptions == []
    text = d.gidLevelsLabel.text()
    assert '2theta resolution 0.0' in text and 'beam on the sample' in text
    assert 'column_acceptance' in d.gidLevelsLabel.toolTip()


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_footprint_window_choice_in_the_worksheet(nx, qapp, recorder):
    """P39 fix (D51): "exact" by default, "IDL" reproduces the earlier maps;
    the exact window uses more columns and so more counts."""
    assert GIDParams().footprint == 'exact'
    sweep._select_scans(nx, qapp, [10])
    sweep._select_images(nx, qapp)
    _menu(nx, qapp, 'Worksheet')
    d = nx.gidWorksheet
    from PyQt5.QtWidgets import QPushButton
    d.gidPinholeCheckBox.setChecked(True)
    assert d.gidFootprintComboBox.currentText() == 'exact'
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    d.gidFootprintComboBox.setCurrentIndex(1)
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    assert nx.gidParams.footprint == 'idl' and recorder.exceptions == []
    d.findChild(QPushButton, 'gidDefaultsPushButton').click()
    assert d.gidFootprintComboBox.currentText() == 'exact' and nx.gidParams.footprint == 'exact'


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_exact_window_adds_columns_and_keeps_the_bragg_peak():
    """Measured with the change (2026-11-19, C24): on NX scan 11 the exact
    window covers 2θ up to 19.93° (IDL's: 19.82°) with more filled cells, and
    the Bragg peak's 2θ is unchanged to 0.002°."""
    from lss_core.experiment import Experiment
    e = Experiment(SPEC)
    out = {}
    for fp in ('idl', 'exact'):
        r = e.gid([11], params=GIDParams(footprint=fp), axes='Angles')
        x, y, d = np.asarray(r.x), np.asarray(r.y), np.asarray(r.data)
        tt = x[:, 0] if np.allclose(x[:, 0], x[:, -1]) else x[0]
        ax = 0 if np.allclose(x[:, 0], x[:, -1]) else 1
        prof = np.nanmean(np.where((y >= 0.3) & (y <= 3), d, np.nan), axis=1 - ax)
        k = int(np.nanargmax(prof))
        w = slice(k - 12, k + 13)
        p = prof[w] - np.nanmin(prof[w])
        out[fp] = (tt.max(), int(np.isfinite(d).sum()), float(np.nansum(tt[w] * p) / np.nansum(p)))
    assert out['exact'][0] > out['idl'][0] + 0.05
    assert out['exact'][1] > out['idl'][1]
    assert out['exact'][2] == pytest.approx(out['idl'][2], abs=0.002)


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_physical_response_and_joins_as_collected_in_the_worksheet(nx, qapp, recorder):
    """Owner, 2026-11-20: the physical column response, and the joins
    reported but not applied (the data as collected)."""
    sweep._select_scans(nx, qapp, [10, 11])
    sweep._select_images(nx, qapp)
    _menu(nx, qapp, 'Worksheet')
    d = nx.gidWorksheet
    from PyQt5.QtWidgets import QPushButton
    d.gidPinholeCheckBox.setChecked(True)
    assert not d.gidBeamFwhmSpinBox.isEnabled()
    d.gidResponseComboBox.setCurrentText('physical')
    assert d.gidBeamFwhmSpinBox.isEnabled() and not d.gidBeamCentreSpinBox.isEnabled()
    d.gidApplyJoinsCheckBox.setChecked(False)
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert nx.gidParams.response == 'physical' and nx.gidParams.apply_joins is False
    assert 'response "physical"' in d.gidLevelsLabel.text()
    t = d.gidJoinTable
    assert any('(not applied)' in (t.item(r, 5).text() if t.item(r, 5) else '') for r in range(t.rowCount()))
    d.gidBeamCentreFitCheckBox.setChecked(False)
    d.gidBeamCentreSpinBox.setValue(5.0)
    d.gidBeamFwhmSpinBox.setValue(60.0)
    assert nx.gidParams.beam_centre_mm == 5.0 and nx.gidParams.beam_fwhm_um == 60.0
    d.findChild(QPushButton, 'gidDefaultsPushButton').click()
    assert nx.gidParams.response == 'fit' and nx.gidParams.apply_joins and nx.gidParams.beam_centre_mm is None


@pytest.mark.gui
@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')
def test_worksheet_updates_the_map_on_every_change(nx, qapp, recorder):
    """Owner, 2026-11-20: see the effect of each method from check boxes and
    drop-down menus. After a first patch, a change starts the patch timer;
    the levels show how well the frames agree."""
    sweep._select_scans(nx, qapp, [10])
    sweep._select_images(nx, qapp)
    _menu(nx, qapp, 'Worksheet')
    d = nx.gidWorksheet
    from PyQt5.QtWidgets import QPushButton
    assert d.gidLiveCheckBox.isChecked()
    d.gidPinholeCheckBox.setChecked(True)
    d.findChild(QPushButton, 'gidPatchPushButton').click()
    qapp.processEvents()
    assert 'frames agree: chi2/dof' in d.gidLevelsLabel.text()
    d.gidResponseComboBox.setCurrentText('physical+fit')
    assert d.gidLiveTimer.isActive() and d.gidBeamFwhmSpinBox.isEnabled()
    d.gidLiveTimer.stop()
    d.gidLiveTimer.timeout.emit()                      # what the timer does when it fires
    qapp.processEvents()
    assert nx.gidParams.response == 'physical+fit' and 'response "physical"' in d.gidLevelsLabel.text()
    d.gidLiveCheckBox.setChecked(False)
    d.gidResponseComboBox.setCurrentText('fit')
    assert not d.gidLiveTimer.isActive() and recorder.exceptions == []
