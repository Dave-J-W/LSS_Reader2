"""F98 in the burn dialog (owner, 2026-11-23, Q-BURN-2, Q-BURN-5; cores
main man's lss_core.dose and tools man's lss_core.reciprocity): the trends
against the dose, the beam's size for a dose per mm², fast mode, and several
burns at once with F76's verdict, dose (beam damage) or time (the sample
changing by itself).

The several-burn data are synthetic with a known truth: two reflectivity
burns, the second at FLUX times the first's monitor (so its flux, the dose
per second, is FLUX times larger), the reflected intensity per monitor
falling as exp(−k φ^β t). β = 1 is damage by the beam, β = 0 a sample
changing by itself.
"""
import os

import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

FLUX = 4.0
K = 1.0e-3          # per second at the first burn's flux: about 20 % in 210 s


def _two_burns(root, beta, name='burns'):
    root = str(root)
    os.makedirs(os.path.join(root, 'pilatus'))
    n, ct = synth.BURN_FRAMES, synth.BURN_CTIME
    peak = (synth.PIL_H - synth.DB_X - 1, synth.DB_Y)
    scans = []
    for num, f in ((1, 1.0), (2, FLUX)):
        z = np.zeros(n)
        mon = synth.MONITOR * f
        rows = np.column_stack([z, z, z, z + 0.05, z + ct, z + mon, z + 1000.0])
        scans.append(synth.spec_scan(num, name, ['In_Ht', 'H', 'K', 'L', 'Seconds', 'Monc', 'Pilatus'], rows,
                                     command='ascan  ih 0 0  %d %g' % (n - 1, ct)))
        rate = K * f ** beta
        for j in range(n):
            amp = 2.0e5 * f * np.exp(-rate * (j + 0.5) * ct)      # counts ∝ monitor × reflectivity
            synth.write_pilatus_tif(os.path.join(root, 'pilatus', '%s_SCAN-%d_%04d.tif' % (name, num, j)),
                                    synth.pilatus_image(peak=peak, amplitude=amp))
    return synth.write_spec(os.path.join(root, name), scans)


def _open(w, qapp, spec, tmp_path, scans):
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    w.prefs['auto_save'] = False
    qapp.processEvents()
    sweep._select_scans(w, qapp, scans)
    sweep._select_images(w, qapp)
    w.ui.pilBurnPushButton.click()
    qapp.processEvents()
    return w.uipdburn


@pytest.mark.parametrize('beta,verdict', [(1.0, 'Dose'), (0.0, 'Time')])
def test_two_burns_are_told_apart(window, qapp, recorder, tmp_path, beta, verdict):
    w = window
    d = _open(w, qapp, _two_burns(tmp_path / 'b', beta), tmp_path, [0, 1])
    assert sorted(w.burnResults) == [1, 2] and d.burnScanComboBox.isVisibleTo(d) and d.burnScanComboBox.count() == 2
    assert d.burnVerdictLabel.text().startswith(verdict + ':'), d.burnVerdictLabel.text()
    v = w.burnVerdictResult
    assert v.beta == pytest.approx(beta, abs=0.1)
    assert v.rates[1][1] / v.rates[0][1] == pytest.approx(FLUX, rel=0.01)           # the fluxes, from the dose
    axes = d.burnVerdictPlotWidget.canvas.fig.axes
    assert len(axes) == 2 and all(len(a.lines) == 2 for a in axes)
    assert 'β = 1 is the dose' in d.burnVerdictLabel.toolTip()
    d.burnScanComboBox.setCurrentIndex(1)                                            # the second burn's trends
    assert w.burnResult.scan == 2 and 'S# 2' in d.Label.text()
    assert recorder.exceptions == []


def test_one_burn_says_how_to_compare(window, qapp, recorder, tmp_path):
    d = _open(window, qapp, synth.make_burn_dataset(tmp_path / 'one'), tmp_path, [0])
    assert not d.burnScanComboBox.isVisibleTo(d)
    assert 'two or more burns' in d.burnVerdictLabel.text()
    assert recorder.exceptions == [] and recorder.messages == []


def test_the_dose_axis_the_beam_and_fast_mode(window, qapp, recorder, tmp_path):
    w = window
    d = _open(w, qapp, synth.make_burn_dataset(tmp_path / 'one'), tmp_path, [0])
    total = w.burnResult.dose_total
    d.burnAxisComboBox.setCurrentIndex(d.burnAxisComboBox.findData('dose'))
    res = w.burnResult
    assert res.axis == 'dose' and res.x_unit() in d.burnResultLabel.text()       # the limit as a dose
    assert "axis='dose'" in w.burnScript
    assert d.burnBeamHeightLineEdit.placeholderText() == '0.04'                    # the study's default here
    assert 'default' in d.burnBeamHeightLineEdit.toolTip()
    d.burnBeamWidthLineEdit.setText('1.0')
    d.burnBeamWidthLineEdit.returnPressed.emit()
    assert w.burnKeywords[1]['beam_mm'] == (1.0, 0.04)
    from lss_core.experiment import Experiment
    core = Experiment(w.specFileName).burn(1, beam_mm=(1.0, 0.04))               # per mm² of footprint
    r = w.burnResult
    assert r.dose_unit.endswith('/mm2') and r.dose_total * r.dose_scale == pytest.approx(
        core.dose_total * core.dose_scale, rel=1e-12)
    assert r.dose_total * r.dose_scale < total * 1e6                              # spread over the footprint
    d.burnBeamHeightLineEdit.setText('0.05')
    d.burnBeamHeightLineEdit.returnPressed.emit()
    assert w.burnKeywords[1]['beam_mm'] == (1.0, 0.05)
    d.burnFastModeCheckBox.setChecked(True)
    assert w.burnKeywords[1]['shutter'] == 'open' and "shutter='open'" in w.burnScript
    assert w.prefs['burn']['axis'] == 'dose' and w.prefs['burn']['beam_width'] == '1.0' and w.prefs['burn']['fast']
    d.burnBeamWidthLineEdit.setText('-1')
    d.burnBeamWidthLineEdit.returnPressed.emit()
    assert 'must be positive' in d.burnResultLabel.text()
    assert recorder.exceptions == []


def test_a_burn_that_moves_in_qz_is_refused(loaded, qapp, recorder):
    """The reflectivity scans of the standard set move in Qz: not burns (the
    button is off for them; its handler refuses as well)."""
    sweep._select_scans(loaded, qapp, [0, 1])
    sweep._select_images(loaded, qapp)
    assert not loaded.ui.pilBurnPushButton.isEnabled()
    loaded.pilBurnTest()
    qapp.processEvents()
    assert any('not a burn test' in m and 'move in Qz' in m for m in recorder.messages)
    assert recorder.exceptions == []


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_nx_burns_14_and_15_in_the_window(window, qapp, recorder, tmp_path):
    """Two GID burns of one spot at absorbers 12 and 8 (flux ×4.68): the
    position drifts 3.7 × faster in 15. On counting errors alone 'neither'
    (β 0.85 [0.80, 0.89], all the weight on the dose); with a 10 % strip
    scatter, 'dose' (tools man's measurement, test_reciprocity.py)."""
    w = window
    d = _open(w, qapp, NX, tmp_path, [13, 14])
    assert sorted(w.burnResults) == [14, 15]
    assert d.burnVerdictLabel.text().startswith('No change')                       # the intensity changes in neither
    d.burnVerdictQuantityComboBox.setCurrentIndex(d.burnVerdictQuantityComboBox.findData('centre'))
    assert d.burnVerdictLabel.text().startswith('Neither') and 'β = 0.85 [0.80, 0.89]' in d.burnVerdictLabel.text()
    d.burnStripSpinBox.setValue(10)
    assert d.burnVerdictLabel.text().startswith('Dose:')
    assert w.prefs['burn']['verdict_quantity'] == 'centre' and w.prefs['burn']['strip_relative'] == pytest.approx(0.1)
    assert recorder.exceptions == []
