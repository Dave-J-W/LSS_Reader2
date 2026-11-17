'''Controls of the image-display and 2D_Plot handlers must not raise before data is loaded.

The (state, control) pairs are the ones that crashed in tests/known_crashes.json
when the guards were added (hard-coded: the baseline shrinks as defects are fixed).
'''
import pytest
import sweep

PAIRS = [
    ('empty', 'click:twodUpdatePlotPushButton'),
    ('empty', 'combo:gixAxesComboBox'),
    ('empty', 'combo:gixCMapComboBox'),
    ('empty', 'combo:pilAspectComboBox'),
    ('empty', 'combo:pilAxesComboBox'),
    ('empty', 'combo:pilCMapComboBox'),
    ('empty', 'combo:twodCMapComboBox'),
    ('empty', 'combo:twodIntPolComboBox'),
    ('empty', 'enter:gixCcd_OffLineEdit'),
    ('empty', 'enter:gixDBPosLineEdit'),
    ('empty', 'enter:gixMaxLineEdit'),
    ('empty', 'enter:gixMinLineEdit'),
    ('empty', 'enter:gixSDDistLineEdit'),
    ('empty', 'enter:pilMaxLineEdit'),
    ('empty', 'enter:pilMinLineEdit'),
    ('empty', 'enter:twodMaxLineEdit'),
    ('empty', 'enter:twodMinLineEdit'),
    ('empty', 'step:twodLabelSizeSpinBox'),
    ('empty', 'step:twodTickSizeSpinBox'),
    ('empty', 'toggle:gixLogIntCheckBox'),
    ('empty', 'toggle:gixSpecCheckBox'),
    ('empty', 'toggle:gixSumCheckBox'),
    ('empty', 'toggle:pilLogIntCheckBox'),
    ('empty', 'toggle:pilPinholeCheckBox'),
    ('empty', 'toggle:pilSpecCheckBox'),
    ('empty', 'toggle:twodColBarCheckBox'),
    ('empty', 'toggle:twodLogIntCheckBox'),
    ('mca_frames', 'click:twodUpdatePlotPushButton'),
    ('mca_frames', 'combo:gixAxesComboBox'),
    ('mca_frames', 'combo:gixCMapComboBox'),
    ('mca_frames', 'combo:pilAspectComboBox'),
    ('mca_frames', 'combo:pilAxesComboBox'),
    ('mca_frames', 'combo:pilCMapComboBox'),
    ('mca_frames', 'combo:twodCMapComboBox'),
    ('mca_frames', 'combo:twodIntPolComboBox'),
    ('mca_frames', 'enter:gixCcd_OffLineEdit'),
    ('mca_frames', 'enter:gixDBPosLineEdit'),
    ('mca_frames', 'enter:gixMaxLineEdit'),
    ('mca_frames', 'enter:gixMinLineEdit'),
    ('mca_frames', 'enter:gixSDDistLineEdit'),
    ('mca_frames', 'enter:pilMaxLineEdit'),
    ('mca_frames', 'enter:pilMinLineEdit'),
    ('mca_frames', 'enter:twodMaxLineEdit'),
    ('mca_frames', 'enter:twodMinLineEdit'),
    ('mca_frames', 'step:twodLabelSizeSpinBox'),
    ('mca_frames', 'step:twodTickSizeSpinBox'),
    ('mca_frames', 'toggle:gixLogIntCheckBox'),
    ('mca_frames', 'toggle:gixSpecCheckBox'),
    ('mca_frames', 'toggle:gixSumCheckBox'),
    ('mca_frames', 'toggle:pilLogIntCheckBox'),
    ('mca_frames', 'toggle:pilPinholeCheckBox'),
    ('mca_frames', 'toggle:pilSpecCheckBox'),
    ('mca_frames', 'toggle:twodColBarCheckBox'),
    ('mca_frames', 'toggle:twodLogIntCheckBox'),
    ('motor_scan', 'click:twodUpdatePlotPushButton'),
    ('motor_scan', 'combo:gixAxesComboBox'),
    ('motor_scan', 'combo:gixCMapComboBox'),
    ('motor_scan', 'combo:pilAspectComboBox'),
    ('motor_scan', 'combo:pilAxesComboBox'),
    ('motor_scan', 'combo:pilCMapComboBox'),
    ('motor_scan', 'combo:twodCMapComboBox'),
    ('motor_scan', 'combo:twodIntPolComboBox'),
    ('motor_scan', 'enter:gixCcd_OffLineEdit'),
    ('motor_scan', 'enter:gixDBPosLineEdit'),
    ('motor_scan', 'enter:gixMaxLineEdit'),
    ('motor_scan', 'enter:gixMinLineEdit'),
    ('motor_scan', 'enter:gixSDDistLineEdit'),
    ('motor_scan', 'enter:pilMaxLineEdit'),
    ('motor_scan', 'enter:pilMinLineEdit'),
    ('motor_scan', 'enter:twodMaxLineEdit'),
    ('motor_scan', 'enter:twodMinLineEdit'),
    ('motor_scan', 'step:twodLabelSizeSpinBox'),
    ('motor_scan', 'step:twodTickSizeSpinBox'),
    ('motor_scan', 'toggle:gixLogIntCheckBox'),
    ('motor_scan', 'toggle:gixSpecCheckBox'),
    ('motor_scan', 'toggle:gixSumCheckBox'),
    ('motor_scan', 'toggle:pilLogIntCheckBox'),
    ('motor_scan', 'toggle:pilPinholeCheckBox'),
    ('motor_scan', 'toggle:pilSpecCheckBox'),
    ('motor_scan', 'toggle:twodColBarCheckBox'),
    ('motor_scan', 'toggle:twodLogIntCheckBox'),
    ('pilatus_one_frame', 'click:twodUpdatePlotPushButton'),
    ('pilatus_one_frame', 'combo:twodCMapComboBox'),
    ('pilatus_one_frame', 'combo:twodIntPolComboBox'),
    ('pilatus_one_frame', 'enter:twodMaxLineEdit'),
    ('pilatus_one_frame', 'enter:twodMinLineEdit'),
    ('pilatus_one_frame', 'step:twodLabelSizeSpinBox'),
    ('pilatus_one_frame', 'step:twodTickSizeSpinBox'),
    ('pilatus_one_frame', 'toggle:twodColBarCheckBox'),
    ('pilatus_one_frame', 'toggle:twodLogIntCheckBox'),
    ('pilatus_scan_no_frames', 'click:twodUpdatePlotPushButton'),
    ('pilatus_scan_no_frames', 'combo:gixAxesComboBox'),
    ('pilatus_scan_no_frames', 'combo:gixCMapComboBox'),
    ('pilatus_scan_no_frames', 'combo:pilAspectComboBox'),
    ('pilatus_scan_no_frames', 'combo:pilAxesComboBox'),
    ('pilatus_scan_no_frames', 'combo:pilCMapComboBox'),
    ('pilatus_scan_no_frames', 'combo:twodCMapComboBox'),
    ('pilatus_scan_no_frames', 'combo:twodIntPolComboBox'),
    ('pilatus_scan_no_frames', 'enter:gixCcd_OffLineEdit'),
    ('pilatus_scan_no_frames', 'enter:gixDBPosLineEdit'),
    ('pilatus_scan_no_frames', 'enter:gixMaxLineEdit'),
    ('pilatus_scan_no_frames', 'enter:gixMinLineEdit'),
    ('pilatus_scan_no_frames', 'enter:gixSDDistLineEdit'),
    ('pilatus_scan_no_frames', 'enter:pilMaxLineEdit'),
    ('pilatus_scan_no_frames', 'enter:pilMinLineEdit'),
    ('pilatus_scan_no_frames', 'enter:twodMaxLineEdit'),
    ('pilatus_scan_no_frames', 'enter:twodMinLineEdit'),
    ('pilatus_scan_no_frames', 'step:twodLabelSizeSpinBox'),
    ('pilatus_scan_no_frames', 'step:twodTickSizeSpinBox'),
    ('pilatus_scan_no_frames', 'toggle:gixLogIntCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:gixSpecCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:gixSumCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:pilLogIntCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:pilPinholeCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:pilSpecCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:twodColBarCheckBox'),
    ('pilatus_scan_no_frames', 'toggle:twodLogIntCheckBox'),
    ('pilatus_two_scans_all_frames', 'click:twodUpdatePlotPushButton'),
    ('pilatus_two_scans_all_frames', 'combo:twodCMapComboBox'),
    ('pilatus_two_scans_all_frames', 'combo:twodIntPolComboBox'),
    ('pilatus_two_scans_all_frames', 'enter:twodMaxLineEdit'),
    ('pilatus_two_scans_all_frames', 'enter:twodMinLineEdit'),
    ('pilatus_two_scans_all_frames', 'step:twodLabelSizeSpinBox'),
    ('pilatus_two_scans_all_frames', 'step:twodTickSizeSpinBox'),
    ('pilatus_two_scans_all_frames', 'toggle:twodColBarCheckBox'),
    ('pilatus_two_scans_all_frames', 'toggle:twodLogIntCheckBox'),
    ('spec_loaded', 'click:twodUpdatePlotPushButton'),
    ('spec_loaded', 'combo:gixAxesComboBox'),
    ('spec_loaded', 'combo:gixCMapComboBox'),
    ('spec_loaded', 'combo:pilAspectComboBox'),
    ('spec_loaded', 'combo:pilAxesComboBox'),
    ('spec_loaded', 'combo:pilCMapComboBox'),
    ('spec_loaded', 'combo:twodCMapComboBox'),
    ('spec_loaded', 'combo:twodIntPolComboBox'),
    ('spec_loaded', 'enter:gixCcd_OffLineEdit'),
    ('spec_loaded', 'enter:gixDBPosLineEdit'),
    ('spec_loaded', 'enter:gixMaxLineEdit'),
    ('spec_loaded', 'enter:gixMinLineEdit'),
    ('spec_loaded', 'enter:gixSDDistLineEdit'),
    ('spec_loaded', 'enter:pilMaxLineEdit'),
    ('spec_loaded', 'enter:pilMinLineEdit'),
    ('spec_loaded', 'enter:twodMaxLineEdit'),
    ('spec_loaded', 'enter:twodMinLineEdit'),
    ('spec_loaded', 'step:twodLabelSizeSpinBox'),
    ('spec_loaded', 'step:twodTickSizeSpinBox'),
    ('spec_loaded', 'toggle:gixLogIntCheckBox'),
    ('spec_loaded', 'toggle:gixSpecCheckBox'),
    ('spec_loaded', 'toggle:gixSumCheckBox'),
    ('spec_loaded', 'toggle:pilLogIntCheckBox'),
    ('spec_loaded', 'toggle:pilPinholeCheckBox'),
    ('spec_loaded', 'toggle:pilSpecCheckBox'),
    ('spec_loaded', 'toggle:twodColBarCheckBox'),
    ('spec_loaded', 'toggle:twodLogIntCheckBox'),
]


@pytest.mark.slow          # 153 fresh windows; the sweep covers the same ground
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


def test_update_plot_button_with_nothing_loaded_says_so(qapp, recorder, tmp_path):
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    qapp.processEvents()
    try:
        w.ui.twodUpdatePlotPushButton.click()
        qapp.processEvents()
        assert recorder.exceptions == []
        assert len(recorder.messages) == 1
    finally:
        sweep.dispose(w, qapp, recorder)


def test_pilatus_axes_combo_still_redraws_with_data(qapp, recorder, dataset, tmp_path):
    from mainwindow import MainWindow
    w = MainWindow()
    w.directory = str(tmp_path)
    w.show()
    qapp.processEvents()
    try:
        sweep.STATES['pilatus_one_frame'](w, qapp, dataset)
        recorder.exceptions.clear()
        combo = w.ui.pilAxesComboBox
        i = combo.findText('Q')
        assert i >= 0
        combo.setCurrentIndex(i)
        qapp.processEvents()
        assert recorder.exceptions == []
        assert len(w.ui.pilMplWidget.canvas.fig.axes) > 0
    finally:
        sweep.dispose(w, qapp, recorder)
