"""Line cuts through the Line/Area Cuts tab, on the synthetic data set.

Cuts are made of frames divided by their monitor count (and absorber
transmission), like every other reduction (owner, 2026-11-17; P23).

One frame is selected: scan 1, frame 0 (Qz = 0.01), whose reflected peak sits
at column PIL_H - DB_X - 1 and row DB_Y of the image.
"""
import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

COL = synth.PIL_H - synth.DB_X - 1
ROW = synth.DB_Y


@pytest.fixture
def frame(loaded, qapp, dataset):
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    return loaded


def _cut(w, qapp, index, text):
    w.ui.pilCutDirComboBox.setCurrentIndex(index)
    w.ui.pilIntRangeLineEdit.setText(text)
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    return w.cutData[min(w.cutData)]


def test_cut_types_offered(frame):
    box = frame.ui.pilCutDirComboBox
    assert [box.itemText(i) for i in range(box.count())] == frame.cutDirItems
    assert len(frame.cutDirItems) == 4


def test_pixel_horizontal_cut_sums_rows(frame, qapp, recorder):
    cut = _cut(frame, qapp, 2, '90:110')
    assert recorder.exceptions == [] and recorder.messages == []
    assert frame.ui.PlotWidget.currentIndex() == 4
    # cuts are of monitor-normalised frames (since 2026-11-17, P23)
    img = frame.pilData[0] / synth.MONITOR
    var = frame.pilData[0] / synth.MONITOR ** 2 + frame.pilData[0] ** 2 / synth.MONITOR ** 3
    assert cut[:, 0] == pytest.approx(np.arange(synth.PIL_H))
    # as coded the upper limit is inclusive and one further row is added
    assert cut[:, 1] == pytest.approx(img[90:112].sum(axis=0))
    assert cut[:, 2] == pytest.approx(np.sqrt(var[90:112].sum(axis=0)))
    assert cut[np.argmax(cut[:, 1]), 0] == COL


def test_pixel_vertical_cut_sums_columns(frame, qapp, recorder):
    cut = _cut(frame, qapp, 3, '90:104')
    assert recorder.exceptions == [] and recorder.messages == []
    img = frame.pilData[0] / synth.MONITOR
    assert cut[:, 0] == pytest.approx(np.arange(synth.PIL_W))
    assert cut[:, 1] == pytest.approx(img[:, 90:106].sum(axis=1))
    assert cut[np.argmax(cut[:, 1]), 0] == ROW


def test_q_horizontal_cut_peaks_at_zero_qxy(frame, qapp, recorder):
    cut = _cut(frame, qapp, 0, '0.005:0.015')
    assert recorder.exceptions == [] and recorder.messages == []
    qxy = cut[:, 0]
    assert np.all(np.diff(qxy) > 0)
    assert qxy[np.argmax(cut[:, 1])] == pytest.approx(0.0, abs=1e-9)
    # one pixel is 0.172 mm at 600 mm: dQxy = 2 pi * 0.172 / 600 / lambda
    step = 2 * np.pi * 0.172 / synth.S2D / synth.WAVELENGTH
    assert np.diff(qxy) == pytest.approx(step, rel=1e-3)


def test_q_vertical_cut_peaks_at_specular_qz(frame, qapp, recorder):
    cut = _cut(frame, qapp, 1, '-0.005:0.005')
    assert recorder.exceptions == [] and recorder.messages == []
    qz = cut[:, 0]
    assert np.all(np.diff(qz) > 0)
    # the reflected beam of the Qz = 0.01 frame
    assert qz[np.argmax(cut[:, 1])] == pytest.approx(0.01, abs=1e-6)


def test_q_and_pixel_cuts_agree_on_total_counts(frame, qapp):
    """Same pixels, different axis: a Q window and the equivalent pixel
    window give the same integrated counts.

    As coded, a Q limit is converted to a pixel offset with int(), which
    truncates toward the beam centre instead of rounding. Limits are put at
    half-pixel positions here so that truncation is unambiguous.
    """
    pix = _cut(frame, qapp, 3, '%d:%d' % (COL - 6, COL + 5)).copy()
    step = 2 * np.pi * 0.172 / synth.S2D / synth.WAVELENGTH
    q = _cut(frame, qapp, 1, '%.7f:%.7f' % (-6.5 * step, 5.5 * step)).copy()
    assert q[:, 1].sum() == pytest.approx(pix[:, 1].sum())


def test_q_limits_truncate_toward_beam_centre_as_coded(frame, qapp):
    """Characterisation: limits of exactly -6 and +5 pixels (in Q) select
    one column fewer than the pixel window -6..+5, because int() truncates a
    limit that lands a hair inside the pixel boundary."""
    step = 2 * np.pi * 0.172 / synth.S2D / synth.WAVELENGTH
    q = _cut(frame, qapp, 1, '%.6f:%.6f' % (-6 * step, 5 * step)).copy()
    full = _cut(frame, qapp, 3, '%d:%d' % (COL - 6, COL + 5)).copy()
    one_less = _cut(frame, qapp, 3, '%d:%d' % (COL - 5, COL + 5)).copy()
    assert q[:, 1].sum() < full[:, 1].sum()
    assert q[:, 1].sum() == pytest.approx(one_less[:, 1].sum())


def test_malformed_range_gives_a_message(frame, qapp, recorder):
    frame.ui.pilCutDirComboBox.setCurrentIndex(2)
    frame.ui.pilIntRangeLineEdit.setText('ninety to one-ten')
    frame.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert recorder.messages            # user is told, nothing raises


def test_summed_cut_averages_normalised_frames(loaded, qapp, dataset, recorder):
    """Two frames of scan 2 (one absorber, factor ABSFAC set in the window)
    and different peak heights: "Sum" is the mean of the normalised frames,
    not of their raw counts."""
    from lss_core.normalise import normalise_frame
    w = loaded
    sweep._select_scans(w, qapp, [1])
    sweep._select_images(w, qapp, [0, 1])
    w.ui.gixSumCheckBox.setChecked(True)
    qapp.processEvents()
    cut = _cut(w, qapp, 3, '90:104')
    assert recorder.exceptions == []
    frames = [normalise_frame(w.pilData[i], w.pilErrorData[i], w.pilMonc[i],
                              w.absfac, w.pil_AbsNum[i]) for i in (0, 1)]
    mean = (frames[0][0] + frames[1][0]) / 2
    assert w.pil_AbsNum[0] == 1
    assert cut[:, 1] == pytest.approx(mean[:, 90:106].sum(axis=1))
