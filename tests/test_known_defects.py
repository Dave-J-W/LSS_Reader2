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


@xfail('#1: scipy.interpolate.interp2d was removed in SciPy 1.14; '
       'imagehjoin/imagevjoin (GID patching) call it')
def test_interp2d_dependency_is_usable():
    from scipy.interpolate import interp2d
    interp2d([0, 1], [0, 1], [[0, 1], [1, 2]], kind='linear')


@pytest.mark.gui
@xfail('#2: "sself" typo in updatePilCutData')
def test_malformed_cut_range_is_reported_not_raised(loaded, qapp, dataset,
                                                    recorder):
    import sweep
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.ui.pilIntRangeLineEdit.setText('not a range')
    loaded.updatePilCutData()
    assert recorder.messages


@pytest.mark.gui
@xfail('#4: opening a file that is not a SPEC file raises')
def test_opening_non_spec_file_is_reported_not_raised(window, tmp_path,
                                                      recorder):
    junk = tmp_path / 'notes.txt'
    junk.write_text('hello\n')
    window.openSpecFile(fname=str(junk))
    assert window.ui.scanListWidget.count() == 0


@xfail('#5: plotROIImage parameter is spelled "errodata"')
def test_plot_roi_image_runs():
    det = TwoDDetector('Pilatus')
    img = synth.pilatus_image(peak=(97, 100))
    det.errorData = np.sqrt(img)
    det.plotROIImage(img, np.sqrt(img), slit=[11, 21], cen=[97, 100], show=0)


@xfail('#14: removeBadPix detects with "factor" but replaces without it')
def test_bad_pixel_factor_controls_replacement():
    det = TwoDDetector('Pilatus')
    img = np.full((40, 30), 100.0)
    img[20, 15] = 500.0          # 5x its neighbours
    # threshold is 4x the neighbour mean; a factor of 2 raises it to 8x
    out, bad = det.removeBadPix(img.copy(), iteration=1, factor=2)
    assert len(bad) == 0
    assert out[20, 15] == 500.0


@xfail('Python 3: the Bruker header is read as bytes, so every header lookup '
       'by str key fails (and #9: removeBadPix returns a tuple that is '
       'stored as the image)')
def test_bruker_frame_can_be_read(tmp_path):
    img = np.full((16, 16), 40, dtype=np.uint8)
    img[8, 8] = 200
    path = synth.write_bruker_sfrm(str(tmp_path / 's_SCAN-1_0000.sfrm'), img)
    det = TwoDDetector('Bruker')
    assert det.openFile(path) == 1
    assert det.imageData.shape == (16, 16)
    assert det.imageData[8, 8] == 200 - 32      # reader subtracts the offset


@pytest.mark.gui
@xfail('#7: map() used as a list; typed-in centres break the g_l2 fit')
def test_g_l2_dialog_accepts_typed_centres(loaded, qapp, dataset, recorder):
    import sweep
    sweep.state_motor_scan(loaded, qapp, dataset)
    loaded.scanCenter = {4: 0.0}
    loaded.calg_l2()
    loaded.uig_l2.g_l2centercheckBox.setChecked(True)
    loaded.uig_l2.g_l2CenterLineEdit.setText('0.01')
    loaded.g_l2plot()
    assert recorder.exceptions == []


@xfail('F10: no exception hook is installed, so PyQt5 aborts the whole '
       'process (SIGABRT) when any slot raises; every entry in '
       'known_crashes.json is a hard crash for the user')
def test_application_survives_a_raising_handler():
    """Run the real program in a subprocess, with no test hooks, and press
    "Ref Patch" with nothing loaded."""
    import os
    import subprocess
    import sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import sys\n"
        "from PyQt5.QtWidgets import QApplication\n"
        "app = QApplication(sys.argv)\n"
        "from mainwindow import MainWindow\n"
        "w = MainWindow(); w.show(); app.processEvents()\n"
        "w.ui.pilRefPatchPushButton.click(); app.processEvents()\n"
        "print('survived')\n")
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    out = subprocess.run([sys.executable, '-W', 'ignore', '-c', code],
                         cwd=root, env=env, capture_output=True, text=True,
                         timeout=120)
    assert out.returncode == 0, 'exit code %d' % out.returncode
    assert 'survived' in out.stdout
