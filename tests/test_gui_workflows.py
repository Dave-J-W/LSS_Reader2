"""End-to-end reduction of the synthetic data set through the real widgets."""
import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

# integral of the synthetic Gaussian peak per monitor count at R = 1
PEAK_INTEGRAL = (2 * np.pi * synth.PEAK_SIGMA ** 2 * synth.PEAK_AMPLITUDE
                 / synth.MONITOR)


def test_open_spec_file_lists_scans(loaded, recorder):
    assert loaded.ui.scanListWidget.count() == 4
    assert loaded.ui.specFileLabel.text() == 'SpecFile: sample'
    assert recorder.messages == []
    assert recorder.exceptions == []


def test_motor_scan_is_plotted_and_peak_fitted(loaded, qapp, dataset, recorder):
    sweep.state_motor_scan(loaded, qapp, dataset)
    assert recorder.exceptions == []
    assert loaded.ui.PlotWidget.currentIndex() == 0
    assert float(loaded.peakPos) == pytest.approx(0.0, abs=1e-6)
    assert float(loaded.peakCenter) == pytest.approx(0.0, abs=2e-3)
    # As coded: the tanh-edged box model is tried first and its width is
    # reported as "FWHM". For this Gaussian (true FWHM 0.471) it gives 0.406.
    assert float(loaded.peakFWHM) == pytest.approx(0.4064, abs=2e-3)


def test_selecting_pilatus_scan_lists_frames(loaded, qapp, dataset, recorder):
    sweep.state_pilatus_scan_no_frames(loaded, qapp, dataset)
    assert loaded.ui.imageListWidget.count() == 9
    assert loaded.ui.imagesLabel.text() == 'Pilatus:'
    assert recorder.exceptions == []


def test_selecting_frame_shows_image(loaded, qapp, dataset, recorder):
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    assert recorder.exceptions == []
    assert loaded.ui.PlotWidget.currentIndex() == 2
    img = loaded.pilData[0]
    assert img.shape == (synth.PIL_W, synth.PIL_H)
    # direct-beam column is mirrored: col = NCOLS - X - 1
    assert np.unravel_index(img.argmax(), img.shape) == \
        (synth.DB_Y, synth.PIL_H - synth.DB_X - 1)


def _patch(w, qapp, dataset):
    sweep.state_pilatus_two_scans_all_frames(w, qapp, dataset)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()


def test_reflectivity_per_scan_is_proportional_to_true_curve(
        loaded, qapp, dataset, recorder):
    _patch(loaded, qapp, dataset)
    assert recorder.exceptions == []
    assert loaded.pilrefsort == [1, 2]
    for scan, attenuation in ((1, 1.0), (2, synth.ABSFAC)):
        d = loaded.scanqzframe[scan]
        ratio = d[:, 1] * attenuation / synth.reflectivity(d[:, 0])
        # ROI sum of the peak minus background, per monitor count; the ROI
        # (11 pixels across a sigma = 2 peak) clips about 0.6 % of it
        assert ratio == pytest.approx(PEAK_INTEGRAL, rel=0.015)
        assert np.all(ratio < PEAK_INTEGRAL)
        # flat within counting/rounding noise across the whole Qz range
        assert ratio.std() / ratio.mean() < 5e-3
        # sigma^2 = sig_err^2 + (lbg_err^2 + rbg_err^2)/4 >= sig_err^2
        assert np.all(d[:, 2] >= d[:, 4])


def test_reflectivity_patch_end_to_end(loaded, qapp, dataset, recorder):
    _patch(loaded, qapp, dataset)
    loaded.uirefpatch.nextPushButton.click()      # "Finish!"
    qapp.processEvents()
    assert recorder.exceptions == []
    assert loaded.ui.PlotWidget.currentIndex() == 3
    d = np.array(loaded.refData)
    assert d[:, 0] == pytest.approx(
        np.union1d(np.linspace(0.01, 0.05, 9), np.linspace(0.04, 0.10, 7)))
    norm = loaded.normRefData
    # normalised to the plateau below Qc
    assert norm[norm[:, 0] < synth.QC, 1] == pytest.approx(1.0)
    # R / R_F stays within 2 % of 1; the shortfall beyond the overlap is the
    # staggered-grid bias documented in test_stitching.py
    assert norm[:, 1] / synth.reflectivity(norm[:, 0]) == pytest.approx(1.0, abs=0.02)
    assert norm[-1, 1] / synth.reflectivity(norm[-1, 0]) == pytest.approx(0.982, abs=2e-3)


def test_mca_frames_are_normalised(loaded, qapp, dataset, recorder):
    sweep.state_mca_frames(loaded, qapp, dataset)
    assert recorder.exceptions == []
    assert loaded.ui.PlotWidget.currentIndex() == 5
    assert sorted(loaded.nomMcaData) == [0, 1]
    x, y, e = loaded.nomMcaData[0].T
    counts = round(500 * 1.0 + 5)                 # channel 120 of synth data
    live = 1.0 / 0.9                              # real / live time
    assert x[119] == pytest.approx(1.20)          # 0 + 0.01 * channel
    assert y[119] == pytest.approx(counts / synth.MONITOR * live)
    assert e[119] == pytest.approx(
        np.sqrt(counts + counts ** 2 / synth.MONITOR) / synth.MONITOR * live)
    assert loaded.nomMcaData[1][119, 1] == pytest.approx(2 * y[119], rel=0.01)
