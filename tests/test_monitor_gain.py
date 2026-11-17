"""Monitor gain in the normalisation (F52; owner, 2026-11-17).

`Monc` counts per photon scale as 1/S, S the SR570 sensitivity recorded as
'#M Monc Gain'. With the option on, values are divided by M·S/S_ref
(S_ref = 1 uA/V) instead of M. Off by default: nothing changes.
"""
import os

import numpy as np
import pytest

import sweep
import synth
from lss_core.experiment import Experiment
from lss_core.fluorescence import normalise_spectrum, window_sum
from lss_core.monitor import gain_factor, parse_gain
from spec_routines import specread
from test_script_console import _run_script


def test_gain_words_and_factors():
    assert gain_factor(parse_gain(['200', 'nA/V'])) == 5.0
    assert gain_factor(parse_gain(['10', 'uA/V'])) == 0.1
    assert gain_factor(parse_gain(['5', 'uA/V'])) == 0.2
    assert gain_factor(parse_gain(['1', 'uA/V'])) == 1.0
    # seen in real files: no unit, no value; not guessed
    assert parse_gain(['200']) is None and parse_gain([]) is None
    assert parse_gain(['x', 'uA/V']) is None and parse_gain(['0', 'uA/V']) is None
    assert gain_factor(None) == 1.0


def test_same_flux_at_two_gains_gives_the_same_value():
    """Invariant I18: the monitor read at sensitivity S2 counts M1·S1/S2 for
    the flux that gave M1 at S1; with the gain factor the normalised
    spectra agree (exactly for expected counts)."""
    expected, _ = synth.xfntr_spectrum(0.02)
    par = {'Time': (1, synth.XF_REAL, synth.XF_LIVE)}
    M1, S1, S2 = 1e5, parse_gain(['200', 'nA/V']), parse_gain(['10', 'uA/V'])
    M2 = M1 * S1 / S2
    a = normalise_spectrum(expected, par, M1, synth.XF_CALIB, gain=gain_factor(S1))
    b = normalise_spectrum(expected, par, M2, synth.XF_CALIB, gain=gain_factor(S2))
    assert b[:, 1] == pytest.approx(a[:, 1], rel=1e-12)
    # without the factor the two measurements of one flux are S2/S1 = 50 apart
    plain1 = normalise_spectrum(expected, par, M1, synth.XF_CALIB)
    plain2 = normalise_spectrum(expected, par, M2, synth.XF_CALIB)
    assert plain2[:, 1] == pytest.approx(plain1[:, 1] * 50, rel=1e-12)


def _with_gains(spec, gains):
    """Insert '#M Monc Gain <text>' into the headers of the given scans."""
    with open(spec) as f:
        text = f.read()
    for num, g in gains.items():
        head = '#S %d ' % num
        i = text.index(head)
        j = text.index('\n', i)
        text = text[:j + 1] + '#M Monc Gain %s\n' % g + text[j + 1:]
    with open(spec, 'w') as f:
        f.write(text)
    return spec


@pytest.fixture
def xf(tmp_path):
    """Plain scan 1 at 200 nA/V, then MCA scans 2..10 (no #M, as on the
    beamline), except scan 6, which records 10 uA/V."""
    spec, _ = synth.make_xfntr_dataset(tmp_path / 'g', absorber=None, lead_absorber=0)
    return _with_gains(spec, {1: '200 nA/V', 6: '10 uA/V'})


MCA = list(range(2, 2 + len(synth.XF_QZ)))
EXPECT = np.array([5.0 if s < 6 else 0.1 for s in MCA])


def test_reader_takes_the_last_gain_above_a_scan(xf, tmp_path):
    p = specread(xf, data={}, par={}).Par
    assert (p[1]['MoncGain'], p[1]['MoncGainText'], 'MoncGainFrom' in p[1]) == (parse_gain(['200', 'nA/V']), '200 nA/V', False)
    assert (p[3]['MoncGainText'], p[3]['MoncGainFrom']) == ('200 nA/V', 1)
    assert 'MoncGainFrom' not in p[6] and (p[7]['MoncGainText'], p[7]['MoncGainFrom']) == ('10 uA/V', 6)
    bad = _with_gains(synth.make_xfntr_dataset(tmp_path / 'b', absorber=None, lead_absorber=0)[0], {1: ''})
    q = specread(bad, data={}, par={}).Par
    assert q[1]['MoncGain'] is None and q[2]['MoncGain'] is None and q[2]['MoncGainFrom'] == 1


def test_script_option_divides_by_the_gain(xf):
    exp = Experiment(xf)
    off = np.array(exp.fluorescence(MCA, window=(5.6, 7.2)).rows)
    res = exp.fluorescence(MCA, window=(5.6, 7.2), monitor_gain=True)
    on = np.array(res.rows)
    assert on[:, 3] == pytest.approx(off[:, 3] * EXPECT, rel=1e-12)
    assert on[:, 4] == pytest.approx(off[:, 4] * EXPECT, rel=1e-12)
    assert res.unknown_gain == []
    # only for Monc
    other = np.array(exp.fluorescence(MCA, window=(5.6, 7.2), monitor=None, monitor_gain=True).rows)
    assert np.array_equal(other, np.array(exp.fluorescence(MCA, window=(5.6, 7.2), monitor=None).rows))


def test_unknown_gain_is_listed_and_gets_no_factor(tmp_path):
    spec, _ = synth.make_xfntr_dataset(tmp_path / 'u', absorber=None, lead_absorber=0)
    exp = Experiment(spec)
    res = exp.fluorescence(MCA, window=(5.6, 7.2), monitor_gain=True)
    assert res.unknown_gain == MCA
    assert res.rows == exp.fluorescence(MCA, window=(5.6, 7.2)).rows


@pytest.mark.gui
def test_window_option_mca(window, qapp, recorder, xf, tmp_path):
    w = window
    w.openSpecFile(fname=xf)
    w.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(w, qapp, list(range(1, 1 + len(MCA))))
    sweep._select_images(w, qapp, None)

    def total():
        w.ui.mcaRanLineEdit.setText('5.6:7.2')
        w.ui.mcaSumAllPushButton.click()
        qapp.processEvents()
        return np.array(w.mcaIntData)

    off = total()
    w.mcaGainCheckBox.setChecked(True)
    qapp.processEvents()
    assert w.monitorGain and w.spGainCheckBox.isChecked()
    on = total()
    assert on[:, 3] == pytest.approx(off[:, 3] * EXPECT, rel=1e-12)
    assert any(m.startswith('Monitor normalisation: Monc current') for m in recorder.messages)
    gui = str(tmp_path / 'gui')
    recorder.save_name = gui
    w.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    text = w.scriptView.toPlainText()
    assert 'monitor_gain=True' in text
    script = str(tmp_path / 'script')
    _run_script(text.replace(repr(gui), repr(script)), tmp_path)
    with open(gui + '_flu.txt', 'rb') as f1, open(script + '_flu.txt', 'rb') as f2:
        assert f1.read() == f2.read()
    w.spGainCheckBox.setChecked(False)            # either box switches it off
    qapp.processEvents()
    assert not w.monitorGain and not w.mcaGainCheckBox.isChecked()
    assert total()[:, 3] == pytest.approx(off[:, 3], rel=1e-12)
    assert recorder.exceptions == []


@pytest.mark.gui
def test_window_option_specplot_export(window, qapp, recorder, tmp_path):
    """Two motor scans at 200 nA/V and 10 uA/V, Apex2 normalised by Monc."""
    x = np.linspace(-1, 1, 5)
    rows = np.column_stack([x, x * 0 + 1, x * 0 + 1e5, x * 0 + 1000])
    scans = [synth.spec_scan(k, 'm', ['sh', 'Seconds', 'Monc', 'Apex2'], rows,
                             command='ascan sh -1 1 4 1', image=False) for k in (1, 2)]
    spec = _with_gains(synth.write_spec(str(tmp_path / 'm'), scans), {1: '200 nA/V', 2: '10 uA/V'})
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0, 1])
    w.ui.spXComboBox.setCurrentIndex(w.ui.spXComboBox.findText('sh'))
    w.ui.spYComboBox.setCurrentIndex(w.ui.spYComboBox.findText('Apex2'))
    w.ui.spNComboBox.setCurrentIndex(w.ui.spNComboBox.findText('Monc'))
    w.ui.spNCheckBox.setChecked(True)
    w.spGainCheckBox.setChecked(True)
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'out')
    w.ui.spExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    for scan, g in ((1, 5.0), (2, 0.1)):
        d = np.loadtxt(str(tmp_path / ('out_%d_sh_Apex2_Monc.txt' % scan)))
        assert d[:, 1] == pytest.approx(1000 / 1e5 * g, rel=1e-4)
