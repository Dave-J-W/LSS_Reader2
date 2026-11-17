"""Fluorescence with absorbers (F50; owner, 2026-11-17).

The foils are before the sample and the monitor upstream of them, so a
spectrum measured at absorber setting n is multiplied by absfac**n to put it
on the scale of the direct beam, as the Pilatus paths do. getandsave_mca
scans record no #A; the setting is the last #A above the scan.
"""
import numpy as np
import pytest

import sweep
import synth
from lss_core.experiment import Experiment
from lss_core.absorbers import ABSFAC_10KEV
from lss_core.fluorescence import absorber_factor
from test_script_console import _run_script

LEAD = 3            # #A of the plain scan before the MCA scans
MCA_SCANS = list(range(2, 2 + len(synth.XF_QZ)))


@pytest.fixture
def pair(tmp_path):
    """The same spectra twice: with '#A x 0' in every MCA scan (as the
    reference) and, as on the beamline, with no #A after a scan at n = LEAD."""
    ref, _ = synth.make_xfntr_dataset(tmp_path / 'ref')
    real, _ = synth.make_xfntr_dataset(tmp_path / 'real', absorber=None, lead_absorber=LEAD)
    return ref, real


def test_factor_of_an_unknown_setting_is_one():
    assert absorber_factor(1.414, None) == 1.0
    assert absorber_factor(1.414, 0) == 1.0
    assert absorber_factor(1.5, 2) == 2.25


@pytest.mark.parametrize('absfac', [1.414, 1.42])
def test_script_api_applies_absfac_to_the_inferred_setting(pair, absfac):
    ref, real = pair
    a = np.array(Experiment(ref).fluorescence(range(1, 1 + len(synth.XF_QZ)), window=(5.6, 7.2)).rows)
    exp = Experiment(real)
    assert exp.scans[2].parameters['AbsorberFrom'] == 1
    b = np.array(exp.fluorescence(MCA_SCANS, window=(5.6, 7.2), absfac=absfac).rows)
    assert np.array_equal(a[:, :3], b[:, :3])
    assert b[:, 3] == pytest.approx(a[:, 3] * absfac ** LEAD, rel=1e-12)
    assert b[:, 4] == pytest.approx(a[:, 4] * absfac ** LEAD, rel=1e-12)


def test_no_a_above_the_scans_means_no_factor(tmp_path):
    ref, _ = synth.make_xfntr_dataset(tmp_path / 'ref')
    none, _ = synth.make_xfntr_dataset(tmp_path / 'none', absorber=None)
    scans = range(1, 1 + len(synth.XF_QZ))
    a = Experiment(ref).fluorescence(scans, window=(5.6, 7.2)).rows
    b = Experiment(none).fluorescence(scans, window=(5.6, 7.2)).rows
    assert np.array_equal(a, b)


def _load(w, qapp, spec, tmp_path, rows):
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(w, qapp, rows)
    sweep._select_images(w, qapp, None)


def _sum(w, qapp):
    w.ui.mcaRanLineEdit.setText('5.6:7.2')
    w.ui.mcaSumAllPushButton.click()
    qapp.processEvents()
    return np.array(w.mcaIntData)


@pytest.mark.gui
def test_window_lists_says_and_applies_the_inferred_setting(window, qapp, recorder, pair, tmp_path):
    ref, real = pair
    w = window
    _load(w, qapp, ref, tmp_path, None)
    a = _sum(w, qapp)
    _load(w, qapp, real, tmp_path, list(range(1, 1 + len(synth.XF_QZ))))
    assert recorder.exceptions == []
    assert w.ui.imageListWidget.item(0).text().endswith('\tAbs=3 (#A of S1)')
    assert any('scan(s) 2, 3, 4, 5, 6, 7, 8, 9, 10: n = 3 from the #A of scan 1' in m and 'absfac 1.4247' in m
               for m in recorder.messages)
    b = _sum(w, qapp)
    assert b[:, 3] == pytest.approx(a[:, 3] * ABSFAC_10KEV ** LEAD, rel=1e-12)
    assert b[:, 4] == pytest.approx(a[:, 4] * ABSFAC_10KEV ** LEAD, rel=1e-12)
    # an edited factor is used at the next Sum All, and the script follows it
    w.ui.AbsFacLineEdit.setText('1.5')
    b = _sum(w, qapp)
    assert b[:, 3] == pytest.approx(a[:, 3] * 1.5 ** LEAD, rel=1e-12)
    gui = str(tmp_path / 'gui')
    recorder.save_name = gui
    w.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    text = w.scriptView.toPlainText()
    assert 'absfac=1.5' in text
    script = str(tmp_path / 'script')
    _run_script(text.replace(repr(gui), repr(script)), tmp_path)
    with open(gui + '_flu.txt', 'rb') as f1, open(script + '_flu.txt', 'rb') as f2:
        assert f1.read() == f2.read()


def test_normalised_fluorescence_does_not_depend_on_the_absorber_setting():
    """Invariant I17: the same surface measured at absorber settings 0 and n
    (counts attenuated by absfac**-n, the monitor upstream of the foils and
    so unchanged) gives the same normalised spectrum once multiplied by
    absfac**n. Exact for expected counts; within Poisson scatter for drawn
    counts."""
    from lss_core.fluorescence import normalise_spectrum, window_sum
    expected, _ = synth.xfntr_spectrum(0.02)
    expected = expected * 1e3                     # bright, so the test is sharp
    par = {'Time': (1, synth.XF_REAL, synth.XF_LIVE)}
    cal, M, n, absfac = synth.XF_CALIB, synth.XF_MONITOR, 9, ABSFAC_10KEV
    a = absorber_factor(absfac, n)
    s0 = normalise_spectrum(expected, par, M, cal)
    sn = normalise_spectrum(expected / a, par, M, cal, absorber=a)
    assert sn[:, 1] == pytest.approx(s0[:, 1], rel=1e-12)
    rng = np.random.default_rng(17)
    i0, e0, _, _ = window_sum(normalise_spectrum(rng.poisson(expected), par, M, cal), 5.6, 7.2)
    i_n, e_n, _, _ = window_sum(normalise_spectrum(rng.poisson(expected / a), par, M, cal, absorber=a), 5.6, 7.2)
    assert abs(i_n - i0) < 3 * np.hypot(e0, e_n)
    assert e_n > e0               # fewer counts at setting n: larger relative error
