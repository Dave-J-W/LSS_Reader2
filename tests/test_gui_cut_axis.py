"""The cut's x axis and the Q cuts' ranges on the Line/Area Cuts row (F97,
F59; owner, 2026-11-23, Q-IMG-12: "β, β − α (α from Qz) and Qz and Qxy";
the core is main man's lss_core.cuts).

The diffuse axes change only the x values of a cut, never its intensities
(I41). A Q cut's range that lies off the detector used to sum nothing and
plot zeros without a word (F59, "nothing happens when I try to use Qxy or
Qz"); now it is refused with a message and a band about the beam is put in
the box.
"""
import numpy as np
import pytest

import sweep
import synth
from lss_core import cuts

pytestmark = pytest.mark.gui

COL = synth.PIL_H - synth.DB_X - 1
ROW = synth.DB_Y


@pytest.fixture
def frame(loaded, qapp, dataset):
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    return loaded


def _axis(w, key):
    box = w.cutAxisComboBox
    box.setCurrentIndex(box.findData(key))
    assert box.currentData() == key


def _cut(w, qapp, index, text, key=None):
    w.ui.pilCutDirComboBox.setCurrentIndex(index)
    _axis(w, key)
    w.ui.pilIntRangeLineEdit.setText(text)
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    return np.array(w.cutData[min(w.cutData)])


def test_the_choice_sits_beside_the_direction_and_greys_what_does_not_fit(window, recorder):
    w = window
    lay = w._layoutHolding(w.ui.pilCutDirComboBox)
    assert lay.indexOf(w.cutAxisComboBox) == lay.indexOf(w.ui.pilCutDirComboBox) + 1
    keys = [w.cutAxisComboBox.itemData(k) for k in range(w.cutAxisComboBox.count())]
    assert keys == [None] + list(cuts.DIFFUSE_AXES)

    def enabled():
        return {w.cutAxisComboBox.itemData(k) for k in range(w.cutAxisComboBox.count())
                if w.cutAxisComboBox.model().item(k).isEnabled()}
    for d in range(4):
        w.ui.pilCutDirComboBox.setCurrentIndex(d)
        assert enabled() == {None} | {a for a in cuts.DIFFUSE_AXES if d in cuts.AXIS_FITS[a]}
    w.ui.pilCutDirComboBox.setCurrentIndex(2)          # Pix H: Qxy fits
    _axis(w, 'Qxy')
    w.ui.pilCutDirComboBox.setCurrentIndex(3)          # Pix V: it does not, back to the image's axis
    assert w.cutAxisComboBox.currentIndex() == 0
    for k in range(w.cutAxisComboBox.count()):
        assert w.cutAxisComboBox.itemData(k, 3)        # Qt.ToolTipRole: every entry explains itself
    assert recorder.exceptions == []


def test_diffuse_axes_change_x_only(frame, qapp, recorder):
    """I41 in the window: the β, β − α and Qz cuts of the same columns have
    the pixel cut's intensities, and x as lss_core.cuts.axis_values gives."""
    w = frame
    w.ui.pilAxesComboBox.setCurrentIndex(0)            # Pixels
    pix = _cut(w, qapp, 3, '%d:%d' % (COL - 6, COL + 5))
    g = w.cutGeometry(0)
    for key in ('beta', 'beta-alpha', 'Qz'):
        c = _cut(w, qapp, 3, '%d:%d' % (COL - 6, COL + 5), key)
        assert c[:, 1] == pytest.approx(pix[:, 1]) and c[:, 2] == pytest.approx(pix[:, 2])
        assert c[:, 0] == pytest.approx(cuts.axis_values(3, pix[:, 0], key, g))
        assert w.ui.cutPlotMplWidget.canvas.ax.get_xlabel() == cuts.LABELS[key]
    assert recorder.exceptions == [] and recorder.messages == []


def test_beta_minus_alpha_puts_the_specular_row_at_zero(frame, qapp, recorder):
    w = frame
    c = _cut(w, qapp, 3, '%d:%d' % (COL - 6, COL + 5), 'beta-alpha')
    step = np.degrees(0.172 / synth.S2D)               # one row, in degrees
    assert abs(c[np.argmax(c[:, 1]), 0]) < step
    qz = _cut(w, qapp, 1, '-0.005:0.005', 'Qz')
    assert qz[np.argmax(qz[:, 1]), 0] == pytest.approx(0.01, abs=2e-4)   # the frame's Qz, from the row
    qxy = _cut(w, qapp, 0, '0.005:0.015', 'Qxy')
    assert qxy[np.argmax(qxy[:, 1]), 0] == pytest.approx(0.0, abs=1e-9)
    assert w.ui.cutPlotMplWidget.canvas.ax.get_xlabel() == cuts.LABELS['Qxy']
    assert recorder.exceptions == [] and recorder.messages == []


def test_the_labels_follow_the_cut_without_a_diffuse_axis(frame, qapp, recorder):
    """Before 2026-11-25 a pixel cut was labelled 'Pixels' whatever the
    image's axes; the label is now the axis the cut is on."""
    w = frame
    w.ui.pilAxesComboBox.setCurrentIndex(1)            # Angles
    _cut(w, qapp, 3, '%d:%d' % (COL - 6, COL + 5))
    assert w.ui.cutPlotMplWidget.canvas.ax.get_xlabel() == cuts.LABELS['beta']
    _cut(w, qapp, 1, '-0.005:0.005')
    assert w.ui.cutPlotMplWidget.canvas.ax.get_xlabel() == cuts.LABELS['Qz']
    assert recorder.exceptions == []


def test_a_diffuse_cut_is_scripted_and_replayed(loaded, qapp, recorder, dataset, tmp_path):
    from test_cut_script import _export_and_replay
    w = loaded
    sweep.state_pilatus_two_scans_all_frames(w, qapp, dataset)
    w.ui.pilCutDirComboBox.setCurrentIndex(3)
    _axis(w, 'beta-alpha')
    w.ui.pilIntRangeLineEdit.setText('90:105')
    prog = _export_and_replay(w, qapp, recorder, tmp_path, 'diffuse')
    assert "axes='beta-alpha'" in prog


def test_q_ranges_are_a_band_about_the_beam_and_a_miss_is_refused(frame, qapp, recorder):
    """F59: with a frame shown, choosing a Q cut puts a band about the beam
    in the box, half the reflectivity ROI either side (Slit 21,11: 5 rows
    for Qz, 10 columns for Qxy); a range off the detector is refused with a
    message (it summed nothing before), and the band put in the box."""
    w = frame
    g = w.cutGeometry(0)
    w.ui.pilCutDirComboBox.setCurrentIndex(1)
    assert (w.cutHalfWidth(0), w.cutHalfWidth(1)) == (5, 10)
    lo, hi = cuts.centred_range(1, g, 10)
    assert w.ui.pilIntRangeLineEdit.text() == '%.4g:%.4g' % (lo, hi)
    w.ui.pilCutDirComboBox.setCurrentIndex(0)
    band = w.ui.pilIntRangeLineEdit.text()
    assert band == '%.4g:%.4g' % cuts.centred_range(0, g, 5)
    w.cutData = {}
    clo, chi = cuts.covered_range(0, g, w.pilShape())  # a Qz range above the detector's top row
    off = '%g:%g' % (chi + 0.5, chi + 1.0)
    w.ui.pilIntRangeLineEdit.setText(off)
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert w.cutData == {} and len(recorder.messages) == 1
    assert 'lies off the detector' in recorder.messages[0] and band in recorder.messages[0]
    assert w.ui.pilIntRangeLineEdit.text() == band
    w.ui.pilLineAreaPushButton.click()                 # cut again: the band holds the reflected beam
    qapp.processEvents()
    cut = np.array(w.cutData[min(w.cutData)])
    assert cut[:, 1].max() > 0 and len(recorder.messages) == 1
    w.ui.pilCutDirComboBox.setCurrentIndex(1)          # Qxy 1:2, the old default, is off a reflectivity frame
    w.ui.pilIntRangeLineEdit.setText('1:2')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert len(recorder.messages) == 2 and 'Qxy range 1:2 lies off' in recorder.messages[1]
    assert recorder.exceptions == []
