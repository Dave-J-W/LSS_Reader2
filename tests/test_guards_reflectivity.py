'''Controls of the Reflectivity tab must not raise before data is loaded or selected.

The (state, control) pairs are the ones that crashed in tests/known_crashes.json
when the guards were added (hard-coded: the baseline shrinks as defects are fixed).
'''
import os

import pytest

import sweep
from test_ref_export_golden import reduce_and_save

PAIRS = [
    ('empty', 'click:gixRefPushButton'),
    ('empty', 'click:pilRefPatchPushButton'),
    ('empty', 'click:pilRefPushButton'),
    ('empty', 'click:refAcceptPushButton'),
    ('empty', 'click:refAnalyzeAllPushButton'),
    ('empty', 'click:refAnalyzePushButton'),
    ('empty', 'click:refExportPushButton'),
    ('empty', 'click:refRemoveFilePushButton'),
    ('empty', 'combo:refBGDirComboBox'),
    ('empty', 'enter:refBGOffLineEdit'),
    ('empty', 'enter:refBPCFacLineEdit'),
    ('empty', 'enter:refCenLineEdit'),
    ('empty', 'enter:refSeaWinLineEdit'),
    ('empty', 'enter:refSlitLineEdit'),
    ('mca_frames', 'click:gixRefPushButton'),
    ('mca_frames', 'click:pilRefPatchPushButton'),
    ('mca_frames', 'click:pilRefPushButton'),
    ('mca_frames', 'click:refAcceptPushButton'),
    ('mca_frames', 'click:refAnalyzeAllPushButton'),
    ('mca_frames', 'click:refAnalyzePushButton'),
    ('mca_frames', 'click:refExportPushButton'),
    ('mca_frames', 'click:refRemoveFilePushButton'),
    ('mca_frames', 'combo:refBGDirComboBox'),
    ('mca_frames', 'enter:refBGOffLineEdit'),
    ('mca_frames', 'enter:refBPCFacLineEdit'),
    ('mca_frames', 'enter:refCenLineEdit'),
    ('mca_frames', 'enter:refSeaWinLineEdit'),
    ('mca_frames', 'enter:refSlitLineEdit'),
    ('motor_scan', 'click:gixRefPushButton'),
    ('motor_scan', 'click:pilRefPatchPushButton'),
    ('motor_scan', 'click:pilRefPushButton'),
    ('motor_scan', 'click:refAcceptPushButton'),
    ('motor_scan', 'click:refAnalyzeAllPushButton'),
    ('motor_scan', 'click:refAnalyzePushButton'),
    ('motor_scan', 'click:refExportPushButton'),
    ('motor_scan', 'click:refRemoveFilePushButton'),
    ('motor_scan', 'combo:refBGDirComboBox'),
    ('motor_scan', 'enter:refBGOffLineEdit'),
    ('motor_scan', 'enter:refBPCFacLineEdit'),
    ('motor_scan', 'enter:refCenLineEdit'),
    ('motor_scan', 'enter:refSeaWinLineEdit'),
    ('motor_scan', 'enter:refSlitLineEdit'),
    ('pilatus_one_frame', 'click:pilRefPatchPushButton'),
    ('pilatus_one_frame', 'click:refAcceptPushButton'),
    ('pilatus_one_frame', 'click:refAnalyzeAllPushButton'),
    ('pilatus_one_frame', 'click:refAnalyzePushButton'),
    ('pilatus_one_frame', 'click:refExportPushButton'),
    ('pilatus_one_frame', 'click:refRemoveFilePushButton'),
    ('pilatus_one_frame', 'combo:refBGDirComboBox'),
    ('pilatus_one_frame', 'enter:refBGOffLineEdit'),
    ('pilatus_one_frame', 'enter:refBPCFacLineEdit'),
    ('pilatus_one_frame', 'enter:refCenLineEdit'),
    ('pilatus_one_frame', 'enter:refSeaWinLineEdit'),
    ('pilatus_one_frame', 'enter:refSlitLineEdit'),
    ('pilatus_scan_no_frames', 'click:gixRefPushButton'),
    ('pilatus_scan_no_frames', 'click:pilRefPatchPushButton'),
    ('pilatus_scan_no_frames', 'click:pilRefPushButton'),
    ('pilatus_scan_no_frames', 'click:refAcceptPushButton'),
    ('pilatus_scan_no_frames', 'click:refAnalyzeAllPushButton'),
    ('pilatus_scan_no_frames', 'click:refAnalyzePushButton'),
    ('pilatus_scan_no_frames', 'click:refExportPushButton'),
    ('pilatus_scan_no_frames', 'click:refRemoveFilePushButton'),
    ('pilatus_scan_no_frames', 'combo:refBGDirComboBox'),
    ('pilatus_scan_no_frames', 'enter:refBGOffLineEdit'),
    ('pilatus_scan_no_frames', 'enter:refBPCFacLineEdit'),
    ('pilatus_scan_no_frames', 'enter:refCenLineEdit'),
    ('pilatus_scan_no_frames', 'enter:refSeaWinLineEdit'),
    ('pilatus_scan_no_frames', 'enter:refSlitLineEdit'),
    ('pilatus_two_scans_all_frames', 'click:refAcceptPushButton'),
    ('pilatus_two_scans_all_frames', 'click:refAnalyzeAllPushButton'),
    ('pilatus_two_scans_all_frames', 'click:refAnalyzePushButton'),
    ('pilatus_two_scans_all_frames', 'click:refExportPushButton'),
    ('pilatus_two_scans_all_frames', 'click:refRemoveFilePushButton'),
    ('pilatus_two_scans_all_frames', 'combo:refBGDirComboBox'),
    ('pilatus_two_scans_all_frames', 'enter:refBGOffLineEdit'),
    ('pilatus_two_scans_all_frames', 'enter:refBPCFacLineEdit'),
    ('pilatus_two_scans_all_frames', 'enter:refCenLineEdit'),
    ('pilatus_two_scans_all_frames', 'enter:refSeaWinLineEdit'),
    ('pilatus_two_scans_all_frames', 'enter:refSlitLineEdit'),
    ('spec_loaded', 'click:gixRefPushButton'),
    ('spec_loaded', 'click:pilRefPatchPushButton'),
    ('spec_loaded', 'click:pilRefPushButton'),
    ('spec_loaded', 'click:refAcceptPushButton'),
    ('spec_loaded', 'click:refAnalyzeAllPushButton'),
    ('spec_loaded', 'click:refAnalyzePushButton'),
    ('spec_loaded', 'click:refExportPushButton'),
    ('spec_loaded', 'click:refRemoveFilePushButton'),
    ('spec_loaded', 'combo:refBGDirComboBox'),
    ('spec_loaded', 'enter:refBGOffLineEdit'),
    ('spec_loaded', 'enter:refBPCFacLineEdit'),
    ('spec_loaded', 'enter:refCenLineEdit'),
    ('spec_loaded', 'enter:refSeaWinLineEdit'),
    ('spec_loaded', 'enter:refSlitLineEdit'),
]


@pytest.mark.slow          # 93 fresh windows; the sweep covers the same ground
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


NEEDS_SOMETHING = [
    'pilRefPushButton', 'pilRefPatchPushButton',   # gix* buttons: hidden CCD tab, removed
    'refAnalyzePushButton', 'refAnalyzeAllPushButton', 'refAcceptPushButton',
    'refExportPushButton',
]


@pytest.mark.parametrize('button', NEEDS_SOMETHING)
def test_button_with_nothing_loaded_gives_one_message(qapp, recorder, tmp_path, button):
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    qapp.processEvents()
    try:
        getattr(w.ui, button).click()
        qapp.processEvents()
        assert recorder.exceptions == []
        assert len(recorder.messages) == 1
    finally:
        sweep.dispose(w, qapp, recorder)


def test_remove_files_with_nothing_loaded_is_silent(qapp, recorder, tmp_path):
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    qapp.processEvents()
    try:
        w.ui.refRemoveFilePushButton.click()
        qapp.processEvents()
        assert recorder.exceptions == []
    finally:
        sweep.dispose(w, qapp, recorder)


def test_parameter_fields_without_selected_qz_are_silent(qapp, recorder, tmp_path):
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    qapp.processEvents()
    try:
        for name in ('refSlitLineEdit', 'refBGOffLineEdit', 'refBPCFacLineEdit',
                     'refCenLineEdit', 'refSeaWinLineEdit'):
            getattr(w.ui, name).returnPressed.emit()
        w.ui.refBGDirComboBox.setCurrentIndex(1 - w.ui.refBGDirComboBox.currentIndex())
        qapp.processEvents()
        assert recorder.exceptions == []
        assert recorder.messages == []
    finally:
        sweep.dispose(w, qapp, recorder)


def test_export_cancelled_writes_nothing(loaded, qapp, recorder, dataset, tmp_path):
    sweep.state_pilatus_two_scans_all_frames(loaded, qapp, dataset)
    loaded.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    loaded.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert len(loaded.refData) > 0
    recorder.save_name = ''
    before = set(os.listdir(str(tmp_path)))
    recorder.messages.clear()
    loaded.ui.refExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert recorder.messages == []
    assert set(os.listdir(str(tmp_path))) == before


def test_export_with_data_still_writes_files(loaded, qapp, recorder, tmp_path):
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'), [0, 1])
    assert os.path.getsize(ref) > 0
    assert os.path.getsize(rrf) > 0
