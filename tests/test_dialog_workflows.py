"""The dialogs behind "Ref Patch", "Burn test" and the GID actions,
including the dialogs they open.

Scripted tests check what each dialog does. The random walks (marked
``sweep``) press, type into and choose from every control of whatever
dialogs are open, many times in a row, reopening the dialog when it
closes, and require that nothing raises.
"""
import os

import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
needs_nx = pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')


# ---- Ref Patch with a repeated scan: the identical-scans dialog -------------

@pytest.fixture
def same(window, qapp, tmp_path):
    spec = synth.make_identical_scans_dataset(tmp_path / 'same')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0, 1, 2])
    sweep._select_images(window, qapp)
    window.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    return window


def test_identical_scans_dialog_opens_for_a_repeated_scan(same, recorder):
    assert recorder.exceptions == []
    assert same.uirefpatchsamescan.isVisible()
    assert same.pilrefsamescannum == [[2, 3]]
    assert 'Indentical Reflectivity Scans: 2, 3' in same.uirefpatchsamescan.Label.text()


def test_merge_then_patch(same, qapp, recorder):
    d = same.uirefpatchsamescan
    s2, s3 = same.scanqzframe[2].copy(), same.scanqzframe[3].copy()
    d.mergePushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert 3 not in same.scanqzframe
    merged = same.scanqzframe[2]
    assert merged[:, 1] == pytest.approx((s2[:, 1] + s3[:, 1]) / 2)
    assert merged[:, 2] == pytest.approx(np.sqrt(s2[:, 2] ** 2 + s3[:, 2] ** 2) / 2)
    d.mergePushButton.click()                 # nothing left to merge
    qapp.processEvents()
    assert recorder.exceptions == []
    assert 'nothing to merge' in recorder.messages[-1]
    d.nextPushButton.click()                  # "Finish!" -> the patch dialog
    qapp.processEvents()
    assert same.uirefpatch.isVisible()
    same.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert same.ui.PlotWidget.currentWidget() is same.ui.refTab
    # 9 + 7 points; the new scan's 2 points inside the overlap are averaged in
    assert len(same.refData) == 9 + 7 - 2


@pytest.mark.parametrize('text,expect', [
    ('', 'separated by commas'), ('abc', 'separated by commas'),
    ('7', 'not in this group'), ('2,9', 'not in this group')])
def test_bad_drop_input_is_reported(same, qapp, recorder, text, expect):
    d = same.uirefpatchsamescan
    d.dropLineEdit.setText(text)
    d.dropPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert expect in recorder.messages[-1]
    assert same.pilrefsamescannum == [[2, 3]]  # nothing dropped


def test_dropping_both_repeats_leaves_one_scan(same, qapp, recorder):
    d = same.uirefpatchsamescan
    d.dropLineEdit.setText('2,3')
    d.dropPushButton.click()
    qapp.processEvents()
    d.mergePushButton.click()                 # empty group: says so
    d.nextPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert sorted(same.scanqzframe) == [1]
    # one scan left: no patch dialog, its data become the reflectivity
    assert same.ui.PlotWidget.currentWidget() is same.ui.refTab
    assert np.array(same.refData)[:, 0] == pytest.approx(np.linspace(0.01, 0.05, 9))


# ---- Ref Patch: the patch dialog --------------------------------------------

@pytest.fixture
def patch(loaded, qapp, dataset):
    sweep._select_scans(loaded, qapp, [0, 1])
    sweep._select_images(loaded, qapp)
    loaded.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    return loaded


@pytest.mark.parametrize('text', ['', 'abc', '99', '-99', ','])
def test_patch_dialog_bad_drop_input(patch, qapp, recorder, text):
    d = patch.uirefpatch
    before = {k: v.copy() for k, v in patch.scanqzframe.items()}
    d.dropLineEdit.setText(text)
    d.dropPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert recorder.messages
    for k in before:
        assert patch.scanqzframe[k] == pytest.approx(before[k])


def test_patch_dialog_drop_then_finish(patch, qapp, recorder):
    d = patch.uirefpatch
    d.dropLineEdit.setText('0')               # first point of the new scan
    d.dropPushButton.click()
    qapp.processEvents()
    assert patch.scanqzframe[2][0, 0] == pytest.approx(0.05)   # Qz 0.04 dropped
    d.nextPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    # 9 + 6 points, the remaining overlap point (Qz 0.05) averaged in
    assert len(patch.refData) == 9 + 6 - 1


def test_drop_after_the_last_join_says_so(patch, qapp, recorder):
    """Found by the crash sweep's random walk (2026-11-23): Drop with no join
    left raised IndexError (pilreforder + 1 past the scans)."""
    d = patch.uirefpatch
    d.nextPushButton.click()                  # the only join: Finish
    qapp.processEvents()
    recorder.messages.clear()
    d.dropLineEdit.setText('0')
    d.dropPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert any('no next scan' in m for m in recorder.messages)


def test_a_one_scan_patch_exports_three_columns(loaded, qapp, recorder, tmp_path):
    """Found by the crash sweep's random walk (2026-11-23): a Ref Patch of one
    scan keeps extra columns (signal and backgrounds apart), and Export's
    three-column format raised ValueError. The _ref.txt format is Qz, R, dR."""
    sweep._select_scans(loaded, qapp, [0])
    sweep._select_images(loaded, qapp)
    loaded.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert np.asarray(loaded.normRefData).shape[1] > 3
    recorder.save_name = str(tmp_path / 'one')
    loaded.ui.refExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    got = np.loadtxt(str(tmp_path / 'one_ref.txt'))
    assert got.shape == (len(loaded.normRefData), 3)
    assert got[:, :3] == pytest.approx(np.asarray(loaded.normRefData)[:, :3], rel=1e-4)


# ---- information Ref Patch gives (dialogs until 2026-11-24) -----------------

def test_peak_centre_report_when_the_beam_is_off_its_recorded_position(
        window, qapp, recorder, tmp_path):
    """Frames whose reflected beam is more than 2 pixels from the position
    in the SPEC header are listed: in a modal dialog until 2026-11-24, now
    in one message (F95, owner Q-UI-B6; tests/test_gui_ref_checks.py)."""
    root = tmp_path / 'off'
    os.makedirs(str(root / 'pilatus'))
    qz = np.array([0.02, 0.03])
    spec = synth.write_spec(str(root / 'off'),
                            [synth.spec_scan(1, 'off', synth.REF_COLUMNS, synth.ref_rows(qz))])
    for j in range(2):
        synth.write_pilatus_tif(str(root / 'pilatus' / ('off_SCAN-1_%04d.tif' % j)),
                                synth.pilatus_image(peak=(synth.PIL_H - synth.DB_X - 1,
                                                          synth.DB_Y + 3 * j),
                                                    amplitude=5e4))
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp)
    window.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert recorder.dialogs == []
    assert any('beam centre is more than 2 px' in m and 'scan 1: frame 1' in m for m in recorder.messages)
    assert window.pilRefPeakCen == [[1, 1, 'y', 3]]


# ---- burn test dialog --------------------------------------------------------

def test_burn_dialog_bad_range_and_mode(window, qapp, recorder, tmp_path):
    spec = synth.make_burn_dataset(tmp_path / 'b')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp)
    window.ui.pilBurnPushButton.click()
    qapp.processEvents()
    d = window.uipdburn
    for text in ('', 'abc', '1:2', '0:0.2'):
        d.rangeLineEdit.setText(text)
        for i in range(d.gidComboBox.count()):
            d.gidComboBox.setCurrentIndex(i)
            d.gidComboBox.activated.emit(i)
            qapp.processEvents()
    assert recorder.exceptions == []
    d.refPushButton.click()
    d.closePushButton.click()
    window.ui.pilBurnPushButton.click()       # reopen after closing
    window.uipdburn.refPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []


# ---- GID: form-factor dialog -------------------------------------------------

def _gid(w, qapp, name):
    if name in ('GID Patch', 'Worksheet'):          # buttons since 2026-11-23 (Q-GID-5)
        (w.gidPatchPushButton if name == 'GID Patch' else w.gidWorksheetPushButton).click()
        qapp.processEvents()
        return
    i = w.ui.gidComboBox.findText(name)
    w.ui.gidComboBox.setCurrentIndex(i)
    w.ui.gidComboBox.activated.emit(i)
    qapp.processEvents()


@pytest.mark.slow
@needs_nx
def test_form_factor_dialog(window, qapp, recorder, tmp_path):
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [10])
    sweep._select_images(window, qapp)
    _gid(window, qapp, 'Form Factor')
    d = window.uipdformfac
    d.updatePushButton.click()                # before any patch: says so
    qapp.processEvents()
    assert 'GID patch first' in recorder.messages[-1]
    _gid(window, qapp, 'GID Patch')
    _gid(window, qapp, 'Form Factor')
    d = window.uipdformfac
    d.sphCheckBox.setChecked(True)
    for text in ('', 'abc', '-3', '0'):
        d.sphLineEdit.setText(text)
        d.updatePushButton.click()
        d.okPushButton.click()
        qapp.processEvents()
        assert 'positive number' in recorder.messages[-1]
    d.ellCheckBox.setChecked(True)
    d.okPushButton.click()
    assert 'Both' in recorder.messages[-1]
    d.sphCheckBox.setChecked(False)
    d.ellXYLineEdit.setText('20')
    d.ellZLineEdit.setText('1.40:1.52')
    d.updatePushButton.click()
    assert 'positive number' in recorder.messages[-1]
    d.ellZLineEdit.setText('10')
    d.updatePushButton.click()
    qapp.processEvents()
    assert (window.formfactor_r, window.formfactor_rxy, window.formfactor_rz) == (0, 20.0, 10.0)
    d.okPushButton.click()
    qapp.processEvents()
    assert not d.isVisible()
    assert recorder.exceptions == []


# ---- random walks inside the dialogs (long; part of the sweep) --------------

WALK_STEPS = 60


@pytest.mark.sweep
@pytest.mark.parametrize('seed', range(6))
def test_walk_identical_scans_and_patch_dialogs(seed, window, qapp, recorder, tmp_path):
    spec = synth.make_identical_scans_dataset(tmp_path / 'same')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0, 1, 2])
    sweep._select_images(window, qapp)
    recorder.save_name = str(tmp_path / 'out')
    raised = sweep.run_dialog_walk(window, qapp, recorder,
                                   window.ui.pilRefPatchPushButton.click, seed, WALK_STEPS)
    assert raised == []


@pytest.mark.sweep
@pytest.mark.parametrize('seed', range(6))
def test_walk_patch_dialog(seed, loaded, qapp, recorder):
    sweep._select_scans(loaded, qapp, [0, 1])
    sweep._select_images(loaded, qapp)
    raised = sweep.run_dialog_walk(loaded, qapp, recorder,
                                   loaded.ui.pilRefPatchPushButton.click, seed, WALK_STEPS)
    assert raised == []


@pytest.mark.sweep
@pytest.mark.parametrize('seed', range(4))
def test_walk_burn_dialog_synthetic(seed, window, qapp, recorder, tmp_path):
    spec = synth.make_burn_dataset(tmp_path / 'b')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp)
    raised = sweep.run_dialog_walk(window, qapp, recorder,
                                   window.ui.pilBurnPushButton.click, seed, WALK_STEPS)
    assert raised == []


@pytest.mark.sweep
@needs_nx
@pytest.mark.parametrize('seed', range(3))
def test_walk_burn_dialog_real_gid(seed, window, qapp, recorder, tmp_path):
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [13])
    sweep._select_images(window, qapp)
    raised = sweep.run_dialog_walk(window, qapp, recorder,
                                   window.ui.pilBurnPushButton.click, seed, 40)
    assert raised == []


@pytest.mark.sweep
@needs_nx
@pytest.mark.parametrize('rows', [[10], [10, 11]])
@pytest.mark.parametrize('seed', range(3))
def test_walk_gid_actions_and_form_factor(seed, rows, window, qapp, recorder, tmp_path):
    """GID patch, then the form-factor dialog, then the GID-related main
    window controls (patch modes, save, GISAXS, axes, cuts) in random order."""
    import random
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, rows)
    sweep._select_images(window, qapp)
    recorder.save_name = str(tmp_path / 'g')
    _gid(window, qapp, 'GID Patch')
    assert recorder.exceptions == []
    raised = sweep.run_dialog_walk(window, qapp, recorder,
                                   lambda: _gid(window, qapp, 'Form Factor'), seed, 40)
    rng = random.Random(seed)
    controls = sweep.controls(window)
    keys = [k for k in controls if any(s in k for s in (
        'gidComboBox', 'gisaxsComboBox', 'pilAxes', 'pilCutDir', 'pilIntRange',
        'pilLineArea', 'cutExport', 'pilMax', 'pilMin', 'pilLogInt', 'pilAspect',
        'gixSum', 'pilHSlit'))]
    for step in range(40):
        key = rng.choice(keys)
        controls[key]()
        qapp.processEvents()
        if recorder.exceptions:
            raised.append((step, key, sweep._first(recorder)))
            recorder.exceptions.clear()
        sweep._close_dialogs(window)
    assert raised == []
