"""Burn tests: does the signal change while the same spot stays in the beam?

Reflectivity burn test on synthetic frames whose reflected peak decays with
a known time constant; GID burn test on real NX school scan 14 (21 frames at
fixed detector angle), frozen as a benchmark.
"""
import os

import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
REF = os.path.join(ROOT, 'tests', 'reference')


def _open_burn_dialog(w, qapp):
    w.ui.pilBurnPushButton.click()
    qapp.processEvents()
    return w.uipdburn


def _plotted(dialog):
    """(time, value, error) of the plotted points, and the fit line if any."""
    ax = dialog.plotWidget.canvas.ax
    cont = ax.containers[0]
    x, y = cont.lines[0].get_data()
    segs = cont.lines[2][0].get_segments()
    err = np.array([(s[1, 1] - s[0, 1]) / 2 for s in segs])
    fit = [l for l in ax.lines if l.get_linestyle() == '--']
    return np.array(x), np.array(y), err, (fit[0].get_data() if fit else None)


@pytest.fixture
def burn(window, qapp, tmp_path):
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp)
    return window


def test_reflectivity_burn_recovers_known_decay(burn, qapp, recorder):
    d = _open_burn_dialog(burn, qapp)
    d.refPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == [] and recorder.messages == []
    t, y, err, fit = _plotted(d)
    assert t == pytest.approx(synth.BURN_CTIME * np.arange(synth.BURN_FRAMES))
    # background-subtracted ROI signal per monitor count follows exp(-t/tau)
    assert y / y[0] == pytest.approx(np.exp(-t / synth.BURN_TAU), rel=2e-3)
    assert np.all(err > 0)
    tf, yf = fit
    tau = -(tf[-1] - tf[0]) / np.log(yf[-1] / yf[0])
    assert tau == pytest.approx(synth.BURN_TAU, rel=5e-3)
    label = d.plotWidget.canvas.ax.get_legend().get_texts()[0].get_text()
    # as coded: tau is truncated to an integer and shown with two digits
    assert label.startswith('$\\tau$ = 4.0e+02 (')
    assert d.Label.text() == 'Burn test for Scan #1'


def test_burn_dialog_refuses_a_scan_that_varies(loaded, qapp, dataset, recorder):
    """A reflectivity scan (Qz changes from frame to frame) is not a burn
    test; the user is told and no dialog opens."""
    sweep.state_pilatus_two_scans_all_frames(loaded, qapp, dataset)
    recorder.messages.clear()
    loaded.ui.pilBurnPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert recorder.messages == [
        'Warning: It is not a burn test scan or multiple scans are selected!']


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
@pytest.mark.parametrize('mode', ['Intensity', 'Location', 'Width'])
def test_gid_burn_on_real_scan_matches_reference(mode, window, qapp, recorder,
                                                 tmp_path):
    """NX school scan 14: 21 frames, 10 s each, detector fixed at the DPPC
    chain peak. Self-reference: the program's own numbers today."""
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [13])
    sweep._select_images(window, qapp)
    recorder.messages.clear()
    d = _open_burn_dialog(window, qapp)
    # the wrong button for this geometry only produces a message
    d.refPushButton.click()
    qapp.processEvents()
    assert recorder.messages == [
        'Warning: It it not a REF burn test. Please use GID burn test button!']
    recorder.messages.clear()
    d.rangeLineEdit.setText('1.40:1.52')
    i = d.gidComboBox.findText(mode)
    d.gidComboBox.setCurrentIndex(i)
    d.gidComboBox.activated.emit(i)
    qapp.processEvents()
    assert recorder.exceptions == [] and recorder.messages == []
    t, y, err, fit = _plotted(d)
    got = np.column_stack([t, y, err])
    path = os.path.join(REF, 'nx_school_gid_burn_scan_14_%s.txt' % mode.lower())
    if os.environ.get('LSS_UPDATE_GOLDEN'):
        np.savetxt(path, got)
    ref = np.loadtxt(path)
    assert got == pytest.approx(ref, rel=1e-6, abs=1e-12)
    assert t == pytest.approx(10.0 * np.arange(21))
    assert (fit is not None) == (mode == 'Intensity')
