"""End-to-end reduction of the synthetic data set through the real widgets."""
import os

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


def test_reader_never_modifies_the_spec_file(loaded, qapp, dataset, recorder):
    """Requirement: the SPEC file belongs to the beamline; the reader must
    only ever read it."""
    import hashlib

    def digest():
        with open(dataset, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest(), os.stat(dataset).st_mtime_ns

    import os
    before = digest()
    _patch(loaded, qapp, dataset)
    loaded.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    sweep.state_mca_frames(loaded, qapp, dataset)
    sweep.state_motor_scan(loaded, qapp, dataset)
    loaded.readSpecFile()                       # the "refresh" path
    qapp.processEvents()
    assert digest() == before


def test_movie_of_a_sub_selection_uses_each_frames_own_axes(loaded, qapp,
                                                            dataset, recorder):
    """The movie loop indexed the per-selection axis limits with the frame
    number. Selecting frames that do not start at 0 raised, or silently
    showed a frame against another frame's axes."""
    sweep._select_scans(loaded, qapp, [0])
    sweep._select_images(loaded, qapp, [5, 7])
    loaded.ui.pilAxesComboBox.setCurrentIndex(loaded.ui.pilAxesComboBox.findText('Q'))
    qapp.processEvents()
    loaded.ui.pilMoviePushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    # the last frame shown is frame 7; its Qz axis must be centred on its own Qz
    ax = loaded.ui.pilMplWidget.canvas.fig.axes[0]
    assert ax.get_title() == 'F #7'
    lo, hi = ax.get_ylim()
    qz7 = loaded.pilFileQzs[7]
    row = synth.DB_Y / (synth.PIL_W - 1.0)          # beam row as a fraction
    assert lo + row * (hi - lo) == pytest.approx(qz7, abs=2e-3)


def test_cut_export_after_the_selection_changed_asks_for_a_new_cut(
        loaded, qapp, dataset, recorder, tmp_path):
    sweep.state_pilatus_two_scans_all_frames(loaded, qapp, dataset)
    loaded.ui.pilCutDirComboBox.setCurrentIndex(2)
    loaded.ui.pilIntRangeLineEdit.setText('90:110')
    loaded.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    loaded.ui.gixSumCheckBox.setChecked(True)       # cut was per frame; now "Sum"
    qapp.processEvents()
    recorder.messages.clear()
    recorder.save_name = str(tmp_path / 'cut')
    loaded.cutData = {k: v for k, v in loaded.cutData.items() if k != -1}
    loaded.ui.cutExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert len(recorder.messages) == 1 and 'make the cut again' in recorder.messages[0]
    assert [n for n in os.listdir(str(tmp_path)) if n.startswith('cut')] == []


def test_rapid_clicks_in_the_image_list_are_drawn_once(loaded, qapp, dataset,
                                                       recorder, monkeypatch):
    """With the selection delay on (the program's default is 150 ms), nine
    quick clicks give one redraw, of the final selection."""
    from PyQt5.QtTest import QTest
    monkeypatch.setenv('LSS_READER_SELECTION_DELAY_MS', '100')
    sweep._select_scans(loaded, qapp, [0])
    calls = []
    real = loaded.pilSelectedScanChanged
    monkeypatch.setattr(loaded, 'pilSelectedScanChanged',
                        lambda: (calls.append(1), real())[1])
    lw = loaded.ui.imageListWidget
    for r in range(9):
        lw.item(r).setSelected(True)
        qapp.processEvents()
    assert calls == []                       # nothing drawn while clicking
    QTest.qWait(300)
    assert len(calls) == 1
    assert list(loaded.selectedPilFramesNums) == list(range(9))
    assert recorder.exceptions == []
