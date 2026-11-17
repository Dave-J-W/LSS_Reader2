'''Controls of the Cuts, MCA, SpecPlot, image/background and Calibration areas
must not raise before data is loaded or selected.

The (state, control) pairs are the ones that crashed in tests/known_crashes.json
when the guards were added (hard-coded: the baseline shrinks as defects are
fixed). The pairs with a dialog step ("A > B") in those functions: none.
Entries for ccdSelectedScanChanged and APS_9IDC are not included (that code is
being removed).
'''
import os

import pytest

import sweep

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAIRS = [
    ('empty', 'action:actionAbs_ratio'),
    ('empty', 'action:actionG_l2'),
    ('empty', 'action:actionG_l3'),
    ('empty', 'click:backgroundPushButton'),
    ('empty', 'click:cutExportPushButton'),
    ('empty', 'click:gixLineAreaPushButton'),
    ('empty', 'click:mcaAcceptPushButton'),
    ('empty', 'click:mcaFitPushButton'),
    ('empty', 'click:mcaRemoveFilePushButton'),
    ('empty', 'click:pilBurnPushButton'),
    ('empty', 'click:pilLineAreaPushButton'),
    ('empty', 'click:pilMoviePushButton'),
    ('empty', 'click:spExportPushButton'),
    ('empty', 'combo:cutLegendLocComboBox'),
    ('empty', 'combo:gixCutDirComboBox'),
    ('empty', 'combo:spLegendLocComboBox'),
    ('empty', 'enter:cutOffsetLineEdit'),
    ('empty', 'enter:gixBPCfacLineEdit'),
    ('empty', 'enter:gixIntRangeLineEdit'),
    ('empty', 'enter:pilIntRangeLineEdit'),
    ('empty', 'enter:scansLineEdit'),
    ('empty', 'step:pilBPCfacSpinBox'),
    ('empty', 'step:pilBPCiteSpinBox'),
    ('empty', 'toggle:bgSelectAllCheckBox'),
    ('empty', 'toggle:cutErrorbarCheckBox'),
    ('empty', 'toggle:cutGridCheckBox'),
    ('empty', 'toggle:cutLegendCheckBox'),
    ('empty', 'toggle:cutLogXCheckBox'),
    ('empty', 'toggle:cutLogYCheckBox'),
    ('empty', 'toggle:cutOffsetCheckBox'),
    ('empty', 'toggle:spGridCheckBox'),
    ('empty', 'toggle:spLegendCheckBox'),
    ('empty', 'toggle:spLogXCheckBox'),
    ('empty', 'toggle:spLogYCheckBox'),
    ('empty', 'toggle:spNCheckBox'),
    ('mca_frames', 'action:actionG_l2'),
    ('mca_frames', 'action:actionG_l3'),
    ('mca_frames', 'click:backgroundPushButton'),
    ('mca_frames', 'click:cutExportPushButton'),
    ('mca_frames', 'click:gixLineAreaPushButton'),
    ('mca_frames', 'click:mcaAcceptPushButton'),
    ('mca_frames', 'click:mcaRemoveFilePushButton'),
    ('mca_frames', 'click:pilBurnPushButton'),
    ('mca_frames', 'click:pilLineAreaPushButton'),
    ('mca_frames', 'click:pilMoviePushButton'),
    ('mca_frames', 'click:spExportPushButton'),
    ('mca_frames', 'combo:cutLegendLocComboBox'),
    ('mca_frames', 'combo:gixCutDirComboBox'),
    ('mca_frames', 'combo:mcaNormComboBox'),
    ('mca_frames', 'combo:spLegendLocComboBox'),
    ('mca_frames', 'enter:cutOffsetLineEdit'),
    ('mca_frames', 'enter:gixIntRangeLineEdit'),
    ('mca_frames', 'enter:pilIntRangeLineEdit'),
    ('mca_frames', 'toggle:bgSelectAllCheckBox'),
    ('mca_frames', 'toggle:cutErrorbarCheckBox'),
    ('mca_frames', 'toggle:cutGridCheckBox'),
    ('mca_frames', 'toggle:cutLegendCheckBox'),
    ('mca_frames', 'toggle:cutLogXCheckBox'),
    ('mca_frames', 'toggle:cutLogYCheckBox'),
    ('mca_frames', 'toggle:cutOffsetCheckBox'),
    ('mca_frames', 'toggle:spGridCheckBox'),
    ('mca_frames', 'toggle:spLegendCheckBox'),
    ('mca_frames', 'toggle:spLogXCheckBox'),
    ('mca_frames', 'toggle:spLogYCheckBox'),
    ('mca_frames', 'toggle:spNCheckBox'),
    ('motor_scan', 'click:backgroundPushButton'),
    ('motor_scan', 'click:cutExportPushButton'),
    ('motor_scan', 'click:gixLineAreaPushButton'),
    ('motor_scan', 'click:mcaAcceptPushButton'),
    ('motor_scan', 'click:mcaFitPushButton'),
    ('motor_scan', 'click:mcaRemoveFilePushButton'),
    ('motor_scan', 'click:pilBurnPushButton'),
    ('motor_scan', 'click:pilLineAreaPushButton'),
    ('motor_scan', 'click:pilMoviePushButton'),
    ('motor_scan', 'combo:cutLegendLocComboBox'),
    ('motor_scan', 'combo:gixCutDirComboBox'),
    ('motor_scan', 'enter:cutOffsetLineEdit'),
    ('motor_scan', 'enter:gixIntRangeLineEdit'),
    ('motor_scan', 'enter:pilIntRangeLineEdit'),
    ('motor_scan', 'toggle:bgSelectAllCheckBox'),
    ('motor_scan', 'toggle:cutErrorbarCheckBox'),
    ('motor_scan', 'toggle:cutGridCheckBox'),
    ('motor_scan', 'toggle:cutLegendCheckBox'),
    ('motor_scan', 'toggle:cutLogXCheckBox'),
    ('motor_scan', 'toggle:cutLogYCheckBox'),
    ('motor_scan', 'toggle:cutOffsetCheckBox'),
    ('pilatus_one_frame', 'click:cutExportPushButton'),
    ('pilatus_one_frame', 'click:mcaAcceptPushButton'),
    ('pilatus_one_frame', 'click:mcaFitPushButton'),
    ('pilatus_one_frame', 'click:mcaRemoveFilePushButton'),
    ('pilatus_scan_no_frames', 'click:backgroundPushButton'),
    ('pilatus_scan_no_frames', 'click:cutExportPushButton'),
    ('pilatus_scan_no_frames', 'click:gixLineAreaPushButton'),
    ('pilatus_scan_no_frames', 'click:mcaAcceptPushButton'),
    ('pilatus_scan_no_frames', 'click:mcaFitPushButton'),
    ('pilatus_scan_no_frames', 'click:mcaRemoveFilePushButton'),
    ('pilatus_scan_no_frames', 'click:pilBurnPushButton'),
    ('pilatus_scan_no_frames', 'click:pilLineAreaPushButton'),
    ('pilatus_scan_no_frames', 'click:pilMoviePushButton'),
    ('pilatus_scan_no_frames', 'combo:cutLegendLocComboBox'),
    ('pilatus_scan_no_frames', 'combo:gixCutDirComboBox'),
    ('pilatus_scan_no_frames', 'enter:cutOffsetLineEdit'),
    ('pilatus_scan_no_frames', 'enter:gixIntRangeLineEdit'),
    ('pilatus_scan_no_frames', 'enter:pilIntRangeLineEdit'),
    ('pilatus_scan_no_frames', 'toggle:bgSelectAllCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:cutErrorbarCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:cutGridCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:cutLegendCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:cutLogXCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:cutLogYCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:cutOffsetCheckBox'),
    ('pilatus_two_scans_all_frames', 'action:actionG_l2'),
    ('pilatus_two_scans_all_frames', 'action:actionG_l3'),
    ('pilatus_two_scans_all_frames', 'click:cutExportPushButton'),
    ('pilatus_two_scans_all_frames', 'click:mcaAcceptPushButton'),
    ('pilatus_two_scans_all_frames', 'click:mcaFitPushButton'),
    ('pilatus_two_scans_all_frames', 'click:mcaRemoveFilePushButton'),
    ('spec_loaded', 'action:actionAbs_ratio'),
    ('spec_loaded', 'action:actionG_l2'),
    ('spec_loaded', 'action:actionG_l3'),
    ('spec_loaded', 'click:backgroundPushButton'),
    ('spec_loaded', 'click:cutExportPushButton'),
    ('spec_loaded', 'click:gixLineAreaPushButton'),
    ('spec_loaded', 'click:mcaAcceptPushButton'),
    ('spec_loaded', 'click:mcaFitPushButton'),
    ('spec_loaded', 'click:mcaRemoveFilePushButton'),
    ('spec_loaded', 'click:pilBurnPushButton'),
    ('spec_loaded', 'click:pilLineAreaPushButton'),
    ('spec_loaded', 'click:pilMoviePushButton'),
    ('spec_loaded', 'click:spExportPushButton'),
    ('spec_loaded', 'combo:cutLegendLocComboBox'),
    ('spec_loaded', 'combo:gixCutDirComboBox'),
    ('spec_loaded', 'combo:spLegendLocComboBox'),
    ('spec_loaded', 'enter:cutOffsetLineEdit'),
    ('spec_loaded', 'enter:gixBPCfacLineEdit'),
    ('spec_loaded', 'enter:gixIntRangeLineEdit'),
    ('spec_loaded', 'enter:pilIntRangeLineEdit'),
    ('spec_loaded', 'step:pilBPCfacSpinBox'),
    ('spec_loaded', 'step:pilBPCiteSpinBox'),
    ('spec_loaded', 'toggle:bgSelectAllCheckBox'),
    ('spec_loaded', 'toggle:cutErrorbarCheckBox'),
    ('spec_loaded', 'toggle:cutGridCheckBox'),
    ('spec_loaded', 'toggle:cutLegendCheckBox'),
    ('spec_loaded', 'toggle:cutLogXCheckBox'),
    ('spec_loaded', 'toggle:cutLogYCheckBox'),
    ('spec_loaded', 'toggle:cutOffsetCheckBox'),
    ('spec_loaded', 'toggle:spGridCheckBox'),
    ('spec_loaded', 'toggle:spLegendCheckBox'),
    ('spec_loaded', 'toggle:spLogXCheckBox'),
    ('spec_loaded', 'toggle:spLogYCheckBox'),
    ('spec_loaded', 'toggle:spNCheckBox'),

]


@pytest.mark.slow
@pytest.mark.parametrize('state,control', PAIRS)
def test_control_does_not_raise(qapp, recorder, dataset, tmp_path, state, control):
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    qapp.processEvents()
    try:
        sweep.STATES[state](w, qapp, dataset)
        recorder.exceptions.clear()
        sweep.controls(w)[control]()
        qapp.processEvents()
        assert recorder.exceptions == []
    finally:
        sweep.dispose(w, qapp, recorder)


def _fresh(qapp, tmp_path):
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    qapp.processEvents()
    return w


EXPLICIT_BUTTONS = [
    'gixLineAreaPushButton', 'pilLineAreaPushButton', 'cutExportPushButton',
    'mcaFitPushButton', 'mcaAcceptPushButton', 'pilBurnPushButton',
    'pilMoviePushButton', 'backgroundPushButton', 'spExportPushButton',
]
EXPLICIT_ACTIONS = ['actionAbs_ratio', 'actionG_l2', 'actionG_l3']


@pytest.mark.parametrize('button', EXPLICIT_BUTTONS)
def test_button_with_nothing_loaded_gives_one_message(qapp, recorder, tmp_path, button):
    w = _fresh(qapp, tmp_path)
    try:
        getattr(w.ui, button).click()
        qapp.processEvents()
        assert recorder.exceptions == []
        assert len(recorder.messages) == 1
    finally:
        sweep.dispose(w, qapp, recorder)


@pytest.mark.parametrize('action', EXPLICIT_ACTIONS)
def test_calibration_with_nothing_loaded_gives_one_message(qapp, recorder, tmp_path, action):
    w = _fresh(qapp, tmp_path)
    try:
        getattr(w.ui, action).trigger()
        qapp.processEvents()
        assert recorder.exceptions == []
        assert len(recorder.messages) == 1
        assert recorder.dialogs == []
    finally:
        sweep.dispose(w, qapp, recorder)


def test_scan_numbers_with_no_spec_file_give_one_message(qapp, recorder, tmp_path):
    w = _fresh(qapp, tmp_path)
    try:
        w.ui.scansLineEdit.setText('1-3')
        w.ui.scansLineEdit.returnPressed.emit()
        qapp.processEvents()
        assert recorder.exceptions == []
        assert len(recorder.messages) == 1
    finally:
        sweep.dispose(w, qapp, recorder)


@pytest.mark.parametrize('action', ['actionG_l2', 'actionG_l3'])
def test_g_l_calibration_without_plotted_scans_gives_one_message(
        qapp, recorder, dataset, tmp_path, action):
    w = _fresh(qapp, tmp_path)
    try:
        sweep.state_spec_loaded(w, qapp, dataset)
        w.scanCenter = {}
        sweep._select_scans(w, qapp, [0, 1])
        w.scanCenter = {}          # as before any peak fit
        recorder.messages.clear()
        getattr(w.ui, action).trigger()
        qapp.processEvents()
        assert recorder.exceptions == []
        assert len(recorder.messages) == 1
        assert recorder.dialogs == []
    finally:
        sweep.dispose(w, qapp, recorder)


def test_display_options_with_nothing_plotted_are_silent(qapp, recorder, tmp_path):
    w = _fresh(qapp, tmp_path)
    try:
        for name in ('cutLogXCheckBox', 'cutLogYCheckBox', 'cutGridCheckBox',
                     'cutLegendCheckBox', 'cutErrorbarCheckBox', 'cutOffsetCheckBox',
                     'spLogXCheckBox', 'spLogYCheckBox', 'spGridCheckBox',
                     'spLegendCheckBox', 'spNCheckBox', 'bgSelectAllCheckBox'):
            getattr(w.ui, name).toggle()
        for name in ('cutLegendLocComboBox', 'spLegendLocComboBox', 'gixCutDirComboBox'):
            c = getattr(w.ui, name)
            c.setCurrentIndex((c.currentIndex() + 1) % c.count())
        for name in ('cutOffsetLineEdit', 'gixIntRangeLineEdit', 'pilIntRangeLineEdit',
                     'gixBPCfacLineEdit'):
            getattr(w.ui, name).returnPressed.emit()
        w.ui.pilBPCfacSpinBox.stepUp()
        w.ui.pilBPCiteSpinBox.stepUp()
        w.ui.mcaRemoveFilePushButton.click()
        qapp.processEvents()
        assert recorder.exceptions == []
        assert recorder.messages == []
    finally:
        sweep.dispose(w, qapp, recorder)


def test_spec_display_options_with_scan_selected_but_no_columns_are_silent(
        qapp, recorder, dataset, tmp_path):
    w = _fresh(qapp, tmp_path)
    try:
        sweep.state_mca_frames(w, qapp, dataset)       # a fluorescence scan has no columns
        recorder.exceptions.clear()
        recorder.messages.clear()
        w.ui.spGridCheckBox.toggle()
        w.ui.spLegendLocComboBox.setCurrentIndex(1)
        qapp.processEvents()
        assert recorder.exceptions == []
        assert recorder.messages == []
    finally:
        sweep.dispose(w, qapp, recorder)


def test_mca_monitor_missing_from_data_gives_one_message(qapp, recorder, dataset, tmp_path):
    w = _fresh(qapp, tmp_path)
    try:
        sweep.state_mca_frames(w, qapp, dataset)
        recorder.exceptions.clear()
        recorder.messages.clear()
        w.ui.mcaNormComboBox.setCurrentIndex(1)          # Monb: not in the data
        qapp.processEvents()
        assert recorder.exceptions == []
        assert len(recorder.messages) == 1
    finally:
        sweep.dispose(w, qapp, recorder)


# ---- exports -------------------------------------------------------------

def _root_files():
    return set(os.listdir(REPO_ROOT))


def _cancelled_export_writes_nothing(w, qapp, recorder, tmp_path, button):
    recorder.save_name = ''
    before_tmp = set(os.listdir(str(tmp_path)))
    before_root = _root_files()
    recorder.messages.clear()
    getattr(w.ui, button).click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert recorder.messages == []
    assert set(os.listdir(str(tmp_path))) == before_tmp
    assert _root_files() == before_root


def test_cut_export_cancelled_writes_nothing(qapp, recorder, dataset, tmp_path):
    w = _fresh(qapp, tmp_path)
    try:
        sweep.state_pilatus_one_frame(w, qapp, dataset)
        w.ui.pilLineAreaPushButton.click()
        qapp.processEvents()
        assert len(w.cutData) > 0
        _cancelled_export_writes_nothing(w, qapp, recorder, tmp_path, 'cutExportPushButton')
    finally:
        sweep.dispose(w, qapp, recorder)


def test_cut_export_with_name_still_writes(qapp, recorder, dataset, tmp_path):
    w = _fresh(qapp, tmp_path)
    try:
        sweep.state_pilatus_one_frame(w, qapp, dataset)
        w.ui.pilLineAreaPushButton.click()
        qapp.processEvents()
        recorder.save_name = str(tmp_path / 'out_')
        w.ui.cutExportPushButton.click()
        qapp.processEvents()
        assert recorder.exceptions == []
        written = [f for f in os.listdir(str(tmp_path)) if f.endswith('_cut.txt')]
        assert len(written) == 1 and os.path.getsize(str(tmp_path / written[0])) > 0
    finally:
        sweep.dispose(w, qapp, recorder)


def test_spec_export_cancelled_writes_nothing(qapp, recorder, dataset, tmp_path):
    w = _fresh(qapp, tmp_path)
    try:
        sweep.state_motor_scan(w, qapp, dataset)
        _cancelled_export_writes_nothing(w, qapp, recorder, tmp_path, 'spExportPushButton')
    finally:
        sweep.dispose(w, qapp, recorder)


def test_spec_export_with_name_still_writes(qapp, recorder, dataset, tmp_path):
    w = _fresh(qapp, tmp_path)
    try:
        sweep.state_motor_scan(w, qapp, dataset)
        recorder.save_name = str(tmp_path / 'spec')
        w.ui.spExportPushButton.click()
        qapp.processEvents()
        assert recorder.exceptions == []
        written = [f for f in os.listdir(str(tmp_path)) if f.startswith('spec_')]
        assert written and all(os.path.getsize(str(tmp_path / f)) > 0 for f in written)
    finally:
        sweep.dispose(w, qapp, recorder)
