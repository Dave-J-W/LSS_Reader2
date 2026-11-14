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
