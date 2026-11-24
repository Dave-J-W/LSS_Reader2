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
    ('empty', 'click:mcaAcceptPushButton'),
    ('empty', 'click:mcaFitPushButton'),
    ('empty', 'click:mcaRemoveFilePushButton'),
    ('empty', 'click:pilBurnPushButton'),
    ('empty', 'click:pilLineAreaPushButton'),
    ('empty', 'click:pilMoviePushButton'),
    ('empty', 'click:spExportPushButton'),
    ('empty', 'combo:cutLegendLocComboBox'),
    ('empty', 'combo:spLegendLocComboBox'),
    ('empty', 'enter:cutOffsetLineEdit'),
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
    ('mca_frames', 'click:mcaAcceptPushButton'),
    ('mca_frames', 'click:mcaRemoveFilePushButton'),
    ('mca_frames', 'click:pilBurnPushButton'),
    ('mca_frames', 'click:pilLineAreaPushButton'),
    ('mca_frames', 'click:pilMoviePushButton'),
    ('mca_frames', 'click:spExportPushButton'),
    ('mca_frames', 'combo:cutLegendLocComboBox'),
    ('mca_frames', 'combo:mcaNormComboBox'),
    ('mca_frames', 'combo:spLegendLocComboBox'),
    ('mca_frames', 'enter:cutOffsetLineEdit'),
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
    ('motor_scan', 'click:mcaAcceptPushButton'),
    ('motor_scan', 'click:mcaFitPushButton'),
    ('motor_scan', 'click:mcaRemoveFilePushButton'),
    ('motor_scan', 'click:pilBurnPushButton'),
    ('motor_scan', 'click:pilLineAreaPushButton'),
    ('motor_scan', 'click:pilMoviePushButton'),
    ('motor_scan', 'combo:cutLegendLocComboBox'),
    ('motor_scan', 'enter:cutOffsetLineEdit'),
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
    ('pilatus_scan_no_frames', 'click:mcaAcceptPushButton'),
    ('pilatus_scan_no_frames', 'click:mcaFitPushButton'),
    ('pilatus_scan_no_frames', 'click:mcaRemoveFilePushButton'),
    ('pilatus_scan_no_frames', 'click:pilBurnPushButton'),
    ('pilatus_scan_no_frames', 'click:pilLineAreaPushButton'),
    ('pilatus_scan_no_frames', 'click:pilMoviePushButton'),
    ('pilatus_scan_no_frames', 'combo:cutLegendLocComboBox'),
    ('pilatus_scan_no_frames', 'enter:cutOffsetLineEdit'),
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
    ('spec_loaded', 'click:mcaAcceptPushButton'),
    ('spec_loaded', 'click:mcaFitPushButton'),
    ('spec_loaded', 'click:mcaRemoveFilePushButton'),
    ('spec_loaded', 'click:pilBurnPushButton'),
    ('spec_loaded', 'click:pilLineAreaPushButton'),
    ('spec_loaded', 'click:pilMoviePushButton'),
    ('spec_loaded', 'click:spExportPushButton'),
    ('spec_loaded', 'combo:cutLegendLocComboBox'),
    ('spec_loaded', 'combo:spLegendLocComboBox'),
    ('spec_loaded', 'enter:cutOffsetLineEdit'),
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
    'pilLineAreaPushButton', 'cutExportPushButton',   # gix* buttons: hidden CCD tab, removed
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
        for name in ('cutLegendLocComboBox', 'spLegendLocComboBox'):   # gixCutDirComboBox: Apex tab removed (Q14)
            c = getattr(w.ui, name)
            c.setCurrentIndex((c.currentIndex() + 1) % c.count())
        for name in ('cutOffsetLineEdit', 'pilIntRangeLineEdit'):   # the gix* fields: Apex tab removed (Q14)
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


def test_background_factor_field_reloads_pilatus_frames(loaded, qapp, dataset,
                                                         recorder):
    """Enter in the background-factor field used to call the Bruker handler
    whatever the detector, which raised for Pilatus and MCA data."""
    for state in ('pilatus_one_frame', 'pilatus_two_scans_all_frames',
                  'mca_frames', 'motor_scan'):
        sweep.STATES[state](loaded, qapp, dataset)
        loaded.ui.bgFacLineEdit.setText('2.0')
        loaded.ui.bgFacLineEdit.returnPressed.emit()
        qapp.processEvents()
        assert recorder.exceptions == [], state


def test_spec_export_when_a_selected_scan_lacks_the_column(loaded, qapp, recorder, tmp_path):
    """Found by the random walk (2026-11-17): the X column was listed for one
    scan, then a scan without it was added to the selection; Export raised
    KeyError. Now it says which scan lacks which column and writes nothing."""
    w = loaded
    sweep._select_scans(w, qapp, [0])
    w.ui.spXComboBox.setCurrentIndex(w.ui.spXComboBox.findText('L'))
    sweep._select_scans(w, qapp, [0, 3])             # scan 4 is a plain sh scan
    recorder.save_name = str(tmp_path / 'spec')
    w.ui.spExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert any('Scan(s) 4 have no column L' in m for m in recorder.messages)
    assert not [f for f in os.listdir(str(tmp_path)) if f.startswith('spec_')]


def test_burn_dialog_after_the_frames_are_deselected(window, qapp, recorder, tmp_path):
    """Found by the random walk (2026-11-17): the burn-test dialog stays open
    while the selection changes; its buttons raised IndexError with no
    frames selected. Now they ask for frames."""
    import synth
    w = window
    w.openSpecFile(fname=synth.make_burn_dataset(tmp_path / 'b'))
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp)
    w.ui.pilBurnPushButton.click()
    qapp.processEvents()
    w.ui.imageListWidget.clearSelection()
    qapp.processEvents()
    assert len(w.selectedPilFramesNums) == 0
    w.uipdburn.refPushButton.click()
    w.uipdburn.gidComboBox.setCurrentIndex(1)
    w.uipdburn.gidComboBox.activated.emit(1)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert sum('burn test scan first' in m for m in recorder.messages) == 2


def test_spec_export_second_y_column_has_its_own_errors(window, qapp, recorder, tmp_path):
    """Read 2026-11-17: the Y2 file was written with the Y column's errors
    (and, unnormalised, a typo left Y2's own errors unused)."""
    import numpy as np
    import synth
    x = np.linspace(-1, 1, 5)
    rows = np.column_stack([x, x * 0 + 1, x * 0 + 1e5, x * 0 + 400, x * 0 + 9])
    spec = synth.write_spec(str(tmp_path / 'm'), [synth.spec_scan(
        1, 'm', ['sh', 'Seconds', 'Monc', 'Apex2', 'YAP'], rows, command='ascan sh -1 1 4 1', image=False)])
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0])
    for box, col in ((w.ui.spXComboBox, 'sh'), (w.ui.spYComboBox, 'Apex2'),
                     (w.ui.spY2ComboBox, 'YAP'), (w.ui.spNComboBox, 'Monc')):
        box.setCurrentIndex(box.findText(col))
    for normalised, suffix, err in ((False, '', 3.0), (True, '_Monc', np.sqrt(9 / 1e10 + 81 / 1e15))):
        w.ui.spNCheckBox.setChecked(normalised)
        recorder.save_name = str(tmp_path / ('out%d' % normalised))
        w.ui.spExportPushButton.click()
        qapp.processEvents()
        d = np.loadtxt(str(tmp_path / ('out%d_1_sh_YAP%s.txt' % (normalised, suffix))))
        assert d[:, 2] == pytest.approx(err, rel=1e-3)
    assert recorder.exceptions == []


@pytest.mark.parametrize('logx', [False, True])
def test_spec_plot_log_axis_with_zero_or_negative_points(window, qapp, recorder, tmp_path, logx):
    """Found by the random walk on 2026-11-18 (mca_frames, seed 1): Y2 = H,
    zero at every point of an L scan, with log Y on. Each point carries a red
    index label at its data coordinates; on a log axis matplotlib clips
    y <= 0 to a finite but enormous pixel position, and FreeType raised
    'raster overflow' drawing the label there. Such points are not drawn on a
    log axis, so neither are their labels; the others still are. It needs a
    narrow log range (here Y/Monc with 0.1 % errors), which puts the clipped
    point millions of pixels away."""
    import numpy as np
    import synth
    x = np.linspace(-1, 1, 5)
    rows = np.column_stack([x, x * 0 + 1, x * 0 + 1e5, x * 0 + 1e6, x * 0, x - 0.5])
    spec = synth.write_spec(str(tmp_path / 'z'), [synth.spec_scan(
        1, 'z', ['sh', 'Seconds', 'Monc', 'Apex2', 'H', 'K'], rows,
        command='ascan sh -1 1 4 1', image=False)])
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0])
    for box, col in ((w.ui.spXComboBox, 'K' if logx else 'sh'), (w.ui.spYComboBox, 'Apex2'),
                     (w.ui.spNComboBox, 'Monc')):
        box.setCurrentIndex(box.findText(col))
    w.ui.spNCheckBox.setChecked(True)
    w.ui.spLogYCheckBox.setChecked(True)
    w.ui.spLogXCheckBox.setChecked(logx)
    for col in ('H', 'K'):
        w.ui.spY2ComboBox.setCurrentIndex(w.ui.spY2ComboBox.findText(col))
        qapp.processEvents()
        w.ui.specPlotMplWidget.canvas.draw()
        assert recorder.exceptions == []
        texts = w.ui.specPlotMplWidget.canvas.ax.texts
        assert len(texts) == 10
        shown = sorted(float(t.get_position()[1]) for t in texts if t.get_visible())
        xs = np.array([t.get_position()[0] for t in texts])
        ys = np.array([t.get_position()[1] for t in texts])
        ok = (ys > 0) & ((xs > 0) if logx else True)
        assert shown == sorted(ys[ok].tolist())


def test_spec_plot_point_labels_option(window, qapp, recorder, tmp_path):
    """F55 (owner, 2026-11-18): the red point-index labels are a checkbox,
    'Point #', on by default (as before); unticked, the plot is redrawn
    with the same points and no labels."""
    import numpy as np
    import synth
    x = np.linspace(-1, 1, 5)
    rows = np.column_stack([x, x * 0 + 1, x * 0 + 1e5, 400 + 10 * x, x * 0 + 9])
    spec = synth.write_spec(str(tmp_path / 'p'), [synth.spec_scan(
        1, 'p', ['sh', 'Seconds', 'Monc', 'Apex2', 'YAP'], rows,
        command='ascan sh -1 1 4 1', image=False)])
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0])
    box = w.spPointLabelsCheckBox
    assert box.isChecked() and box.text() == 'Point #'
    ax = w.ui.specPlotMplWidget.canvas.ax
    for col in ('None', 'YAP'):                      # one series, then Y and Y2
        w.ui.spY2ComboBox.setCurrentIndex(w.ui.spY2ComboBox.findText(col))
        qapp.processEvents()
        n = 5 if col == 'None' else 10
        assert [t.get_text() for t in ax.texts] == [str(i) for i in range(5)] * (n // 5)
        lines = [l.get_ydata().tolist() for l in ax.lines]
        box.setChecked(False)
        qapp.processEvents()
        assert len(ax.texts) == 0
        assert [l.get_ydata().tolist() for l in ax.lines] == lines
        box.setChecked(True)
        qapp.processEvents()
        assert len(ax.texts) == n
    assert recorder.exceptions == []
