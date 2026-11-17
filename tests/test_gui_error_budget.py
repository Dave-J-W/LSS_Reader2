"""The Errors pane: the budget error model in the window (owner, 2026-11-17).

Legacy stays the default, so exports are unchanged unless the user picks
Budget; with Budget, cuts, MCA sums and Ref Patch apply the monitor term
to whole sums, and the Script pane reproduces the exported files.
"""
import numpy as np
import pytest

import sweep
import synth
from lss_core.absorbers import ABSFAC_10KEV
from test_script_console import _export, _run_script, _same_files

pytestmark = pytest.mark.gui


U0 = 4e-4     # default monitor sigma (owner, 2026-11-17)


def _budget(w, qapp, g=None):
    """Budget errors; with ``g``, the counting monitor model with that g."""
    if g is not None:
        w.monitorKindComboBox.setCurrentIndex(2)
        w.errorFields['g'].setText(repr(g))
    w.errorModeComboBox.setCurrentIndex(1)
    w.setErrorModel()
    qapp.processEvents()


def test_default_is_legacy_and_the_pane_switches(window, qapp, recorder):
    w = window
    assert w.absfac == ABSFAC_10KEV == 1.4247    # 50 um Al at 10 keV (owner, 2026-11-17)
    assert w.ui.AbsFacLineEdit.text() == '1.4247'
    assert w.errorModel.mode == 'legacy' and w.pilatus.errors is w.errorModel
    assert w.errorFields['sigma'].text() == '0.04'
    assert w.errorModel.monitor.kind == 'gaussian' and w.errorModel.monitor.sigma == U0
    _budget(w, qapp, g=4.0)
    assert w.errorModel.budget and w.errorModel.monitor.g == 4.0
    assert w.pilatus.errors is w.errorModel
    assert any('Error model: budget' in m[2] for m in w.messages)
    assert recorder.exceptions == []


def test_pane_offers_gaussian_student_t_and_counting(window, qapp, recorder):
    w = window
    w.errorModeComboBox.setCurrentIndex(1)
    w.errorFields['sigma'].setText('0.05')
    w.errorFields['sigma'].editingFinished.emit()
    assert w.errorModel.monitor.sigma == pytest.approx(5e-4)
    w.monitorKindComboBox.setCurrentIndex(1)            # Student t
    m = w.errorModel.monitor
    assert m.kind == 'student_t' and (m.nu, m.width) == (4.0, 0.94)
    assert m.sigma_scan == pytest.approx(3.9e-4)
    w.errorFields['sigma_scan'].setText('0.05')
    w.errorFields['width'].setText('0.86')
    w.errorFields['width'].editingFinished.emit()
    assert w.pilatus.errors.monitor.relative(1e5) == pytest.approx(0.86 * 5e-4 * np.sqrt(2.0))
    assert not w.errorFields['g'].isEnabled() and not w.errorFields['sigma'].isEnabled()
    assert w.errorFields['nu'].isEnabled() and w.errorFields['width'].isEnabled()
    assert 'SR570' in w.errorModelLabel.text()
    w.errorFields['nu'].setText('1.5')                  # no finite variance: refused
    w.errorFields['nu'].editingFinished.emit()
    assert w.errorModel.monitor.nu == 4.0 and w.errorFields['nu'].text() == '4.0'
    assert recorder.exceptions == []


def test_budget_cut_points_carry_the_monitor_term_once(loaded, qapp, recorder, dataset):
    w = loaded
    sweep.state_pilatus_one_frame(w, qapp, dataset)
    _budget(w, qapp, g=10.0)
    w.ui.pilCutDirComboBox.setCurrentIndex(2)
    w.ui.pilIntRangeLineEdit.setText('90:110')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert [m for m in recorder.messages if not m.startswith('Error model')] == []
    cut = w.cutData[min(w.cutData)]
    M = synth.MONITOR
    counts = w.pilData[0][90:112].sum(axis=0)
    u2 = 1 / (10.0 * M)
    assert cut[:, 1] == pytest.approx(counts / M)
    assert cut[:, 2] ** 2 == pytest.approx(counts / M ** 2 + (counts / M) ** 2 * u2, rel=1e-9)


def test_budget_summed_cut_adds_frames_in_quadrature(loaded, qapp, recorder, dataset):
    w = loaded
    sweep.state_spec_loaded(w, qapp, dataset)
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp, [0, 1])
    _budget(w, qapp)
    w.ui.gixSumCheckBox.setChecked(True)
    w.ui.pilCutDirComboBox.setCurrentIndex(2)
    w.ui.pilIntRangeLineEdit.setText('90:110')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    cut = w.cutData[-1]
    M = synth.MONITOR
    c0, c1 = (w.pilData[k][90:112].sum(axis=0) for k in (0, 1))
    assert cut[:, 1] == pytest.approx((c0 + c1) / M / 2)
    expect = (c0 + c1) / M ** 2 / 4 + ((c0 / M / 2) ** 2 + (c1 / M / 2) ** 2) * U0 ** 2
    assert cut[:, 2] ** 2 == pytest.approx(expect, rel=1e-9)


def test_budget_mca_sum(window, qapp, recorder, tmp_path):
    w = window
    spec, truth = synth.make_xfntr_dataset(tmp_path / 'xf')
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(w, qapp, None)
    sweep._select_images(w, qapp, None)
    legacy = None
    for mode in ('legacy', 'budget'):
        if mode == 'budget':
            _budget(w, qapp)
        w.ui.mcaRanLineEdit.setText('5.6:7.2')
        w.ui.mcaSumAllPushButton.click()
        qapp.processEvents()
        rows = np.array(w.mcaIntData)
        if legacy is None:
            legacy = rows
    assert recorder.exceptions == []
    assert np.array_equal(rows[:, 3], legacy[:, 3])
    M = synth.XF_MONITOR
    live = synth.XF_REAL / synth.XF_LIVE
    Y = rows[:, 3]
    counting = Y * live / M          # sum of counts * live^2 / M^2
    assert rows[:, 4] ** 2 == pytest.approx(counting + Y ** 2 * U0 ** 2, rel=1e-9)


def test_budget_ref_patch_script_reproduces_the_export(loaded, qapp, recorder, tmp_path):
    w = loaded
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    _budget(w, qapp, g=3.0)
    w.ui.pilRefPatchPushButton.click()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    gui = str(tmp_path / 'gui')
    _export(w, qapp, recorder, gui)
    text = w.scriptView.toPlainText()
    assert "errors={'mode': 'budget', 'kind': 'counting', 'f': 0.0, 'sigma_dark': 0.0, 'g': 3.0}" in text
    script = str(tmp_path / 'script')
    _run_script(text.replace(repr(gui), repr(script)), tmp_path)
    _same_files(gui, script)
    # a legacy export of the same patch: the errors differ, and so do the
    # joined values slightly, because the patch's scale-factor fit is
    # weighted by the errors
    w.errorModeComboBox.setCurrentIndex(0)
    w.setErrorModel()
    w.ui.pilRefPatchPushButton.click()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    leg = str(tmp_path / 'leg')
    _export(w, qapp, recorder, leg)
    a, b = np.loadtxt(gui + '_ref.txt'), np.loadtxt(leg + '_ref.txt')
    assert np.array_equal(a[:, 0], b[:, 0])
    assert np.allclose(a[:, 1], b[:, 1], rtol=5e-3)
    assert not np.array_equal(a[:, 2], b[:, 2])


def test_budget_cut_of_background_subtracted_frame(loaded, qapp, recorder, dataset):
    """Frame 0 minus frame 1 of scan 1 as background: counting parts add,
    and the two frames' monitor terms add in quadrature (opposite signs)."""
    w = loaded
    sweep.state_spec_loaded(w, qapp, dataset)
    sweep._select_scans(w, qapp, [0])
    _budget(w, qapp)
    sweep._select_images(w, qapp, [1])
    raw1 = np.array(w.pilData[1])
    w.addBGImagestoList()
    w.ui.bgFacLineEdit.setText('0.5')
    w.ui.backgroundListWidget.item(0).setSelected(True)
    qapp.processEvents()
    sweep._select_images(w, qapp, [0])
    qapp.processEvents()
    w.ui.pilCutDirComboBox.setCurrentIndex(2)
    w.ui.pilIntRangeLineEdit.setText('90:110')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    cut = w.cutData[min(w.cutData)]
    M = synth.MONITOR
    p0 = w.pilGIOXSData[0][90:112].sum(axis=0) * M     # counts of frame 0
    p1 = raw1[90:112].sum(axis=0)
    assert cut[:, 1] == pytest.approx(p0 / M - 0.5 * p1 / M)
    expect = (p0 + 0.25 * p1) / M ** 2 + ((p0 / M) ** 2 + (0.5 * p1 / M) ** 2) * U0 ** 2
    assert cut[:, 2] ** 2 == pytest.approx(expect, rel=1e-9)


def test_absorber_factor_in_use_is_the_one_the_field_shows(loaded, qapp, recorder):
    """Defect fixed 2026-11-17: opening a SPEC file with Pilatus images set
    the field to 1.42 ("Al 50 um at 10 keV"), but cuts, background images
    and frame averages kept using the start-up value of the field (1.606 in
    the original program) until a reflectivity action re-read it. Now the
    value in use follows the field, and both start at 50 um Al."""
    w = loaded
    assert w.ui.AbsFacLineEdit.text() == str(ABSFAC_10KEV) and w.absfac == ABSFAC_10KEV
    w.ui.AbsFacLineEdit.setText('1.5')
    assert w.absfac == 1.5
    w.ui.AbsFacLineEdit.setText('')                 # being typed: keep the last value
    assert w.absfac == 1.5
    w.ui.AbsFacLineEdit.setText('1.606')
    assert w.absfac == 1.606
    assert recorder.exceptions == []
