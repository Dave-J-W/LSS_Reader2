"""Defects from docs/ASSESSMENT.md reproduced as strict expected failures.

Each test states the behaviour we want. When a defect is fixed its test
starts passing, pytest reports XPASS(strict) as a failure, and the xfail
marker must be removed in the same commit as the fix.
"""
import numpy as np
import pytest

import synth
from TwoDDetector import TwoDDetector


def xfail(reason):
    return pytest.mark.xfail(strict=True, reason=reason)


def test_program_does_not_import_the_removed_interp2d():
    """Defect 1 (fixed): nothing in the program imports scipy's interp2d."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ('mainwindow.py', 'TwoDDetector.py', 'spec_routines.py',
                 'mca_routines.py', 'interp_compat.py'):
        with open(os.path.join(root, name)) as f:
            assert 'scipy.interpolate import interp2d' not in f.read(), name


@pytest.mark.gui
def test_malformed_cut_range_is_reported_not_raised(loaded, qapp, dataset,
                                                    recorder):
    import sweep
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.ui.pilIntRangeLineEdit.setText('not a range')
    loaded.updatePilCutData()
    assert recorder.messages


@pytest.mark.gui
@pytest.mark.parametrize('content', [b'hello\n', b'', b'\x00\x01\xff\xfe' * 50])
def test_opening_non_spec_file_is_reported_not_raised(content, window, tmp_path,
                                                      recorder):
    """Defect 4 (fixed): text, empty and binary files are refused quietly."""
    junk = tmp_path / 'notes.txt'
    junk.write_bytes(content)
    window.openSpecFile(fname=str(junk))
    assert recorder.exceptions == []
    assert window.ui.scanListWidget.count() == 0
    assert window.specFileName is None
    assert len(recorder.messages) == 1 and 'is not a SPEC file' in recorder.messages[0]


@pytest.mark.gui
def test_opening_non_spec_file_keeps_what_is_loaded(loaded, dataset, tmp_path,
                                                    recorder, qapp):
    junk = tmp_path / 'notes.txt'
    junk.write_text('hello\n')
    loaded.openSpecFile(fname=str(junk))
    loaded.openSpecFile(fname=str(tmp_path / 'does_not_exist'))
    qapp.processEvents()
    assert recorder.exceptions == []
    assert loaded.specFileName == dataset
    assert loaded.ui.scanListWidget.count() == 4
    assert len(recorder.messages) == 2


def test_plot_roi_image_runs():
    det = TwoDDetector('Pilatus')
    img = synth.pilatus_image(peak=(97, 100))
    det.errorData = np.sqrt(img)
    det.plotROIImage(img, np.sqrt(img), slit=[11, 21], cen=[97, 100], show=0)


def test_bad_pixel_factor_controls_replacement():
    det = TwoDDetector('Pilatus')
    img = np.full((40, 30), 100.0)
    img[20, 15] = 500.0          # 5x its neighbours
    # threshold is 4x the neighbour mean; a factor of 2 raises it to 8x
    out, bad = det.removeBadPix(img.copy(), iteration=1, factor=2)
    assert len(bad) == 0
    assert out[20, 15] == 500.0


@pytest.mark.gui
def test_g_l2_dialog_accepts_typed_centres(loaded, qapp, dataset, recorder):
    """Defect 7 (fixed): centres typed into the dialog are used for the fit.
    Two scans at different incident angles with centres generated from a
    known arm length; the fit must return that length."""
    import sweep
    sweep._select_scans(loaded, qapp, [0, 1])       # Qz = 0.01 and 0.04
    loaded.scanCenter = {1: 0.0, 2: 0.0}
    loaded.calg_l2()
    alpha = np.array(loaded.g_l2alpha) * np.pi / 180
    length, offset = 185.0, 0.02
    centres = offset - length * np.sin(alpha)
    loaded.uig_l2.g_l2centercheckBox.setChecked(True)
    loaded.uig_l2.g_l2CenterLineEdit.setText(','.join('%.9f' % c for c in centres))
    recorder.messages.clear()
    loaded.uig_l2.g_l2CalPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == [] and recorder.messages == []
    text = loaded.uig_l2.g_l2TextBrowser.toPlainText()
    assert 'new g_l2\t= 185.000' in text
    assert 'offset\t= 0.020' in text


@pytest.mark.gui
@pytest.mark.parametrize('which', ['g_l2', 'g_l3'])
def test_g_l_dialogs_name_the_selected_scans(loaded, qapp, recorder, which):
    """The dialogs list the scans they use by their numbers: the scan
    list's numbers, not those plus one (found 2026-11-23 by the Tools
    session's screenshot of the dialog: scans 5 and 13 shown as 6, 14)."""
    import sweep
    sweep._select_scans(loaded, qapp, [0, 1])       # scans 1 and 2
    assert loaded.selectedScanNums == [1, 2]
    loaded.scanCenter = {1: 0.0, 2: 0.0}
    getattr(loaded, 'cal' + which)()
    ui = getattr(loaded, 'ui' + which)
    assert getattr(ui, which + 'ScanLineEdit').text() == '1, 2'
    assert recorder.exceptions == []


@pytest.mark.gui
def test_g_l2_dialog_with_one_scan_asks_for_more(loaded, qapp, dataset,
                                                 recorder):
    """One scan cannot determine two unknowns; the user is told, nothing
    raises."""
    import sweep
    sweep.state_motor_scan(loaded, qapp, dataset)
    loaded.scanCenter = {4: 0.0}
    loaded.calg_l2()
    recorder.messages.clear()
    loaded.uig_l2.g_l2CalPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert len(recorder.messages) == 1 and 'at least two scans' in recorder.messages[0]
