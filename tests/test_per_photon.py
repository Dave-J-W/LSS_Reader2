"""Values per incident photon (F54 in the window and scripts).

The option divides by the photons through the Monc chamber,
N = (M − D·t)·q(E)·S/(500 nA/V) (lss_core.flux, xray_fluxor route D), instead
of the counts M: a value normalised by M is multiplied by M/N. It includes
the gain option (invariant I20: one photon flux read at two sensitivities and
two dark-affected monitor rates gives one value).
"""
import numpy as np
import pytest

import sweep
import synth
from lss_core import flux
from lss_core.absorbers import energy_kev
from lss_core.experiment import Experiment, monitor_factor
from lss_core.monitor import parse_gain, scan_rate
from test_cut_script import _export_and_replay
from test_monitor_gain import MCA, _with_gains, pil, xf  # noqa: F401  (fixtures)
from test_script_console import _run_script

S200, S10 = parse_gain(['200', 'nA/V']), parse_gain(['10', 'uA/V'])
E = energy_kev(synth.WAVELENGTH)                    # 9.999 keV


def test_factor_is_counts_over_photons():
    f, flags = flux.photon_factor(5e-6, 10.0, 1e5)
    n = flux.photons_per_second(1e5, 1.0, 10.0, 5e-6, dark_hz=50.0, temp_c=24.9, pressure_kpa=98.99)[0]
    assert f == pytest.approx(1e5 / n, rel=1e-12) and flags == []
    # q(10 keV) = 4.37e6 photons/s per Hz at 500 nA/V; x10 at 5 uA/V; dark 50 Hz of 1e5
    assert f == pytest.approx(1.0 / (4.37e6 * 10 * (1 - 50 / 1e5)), rel=1e-12)
    g, flags = flux.photon_factor(5e-6, 10.0)
    assert g == pytest.approx(1.0 / 4.37e7, rel=1e-12) and flags == ['monitor rate unknown: dark not subtracted']


@pytest.mark.parametrize('args, why', [
    ((None, 10.0, 1e5), 'Monc gain unknown'),
    ((5e-6, None, 1e5), 'energy unknown'),
    ((5e-6, 40.0, 1e5), 'outside the 5-30 keV table'),
    ((5e-6, 4.0, 1e5), 'outside the 5-30 keV table'),
    ((5e-6, 10.0, 40.0), 'not above the dark rate'),
])
def test_unknown_factor_is_none_and_says_why(args, why):
    f, flags = flux.photon_factor(*args)
    assert f is None and why in flags[0]


def test_same_photon_flux_at_two_gains_gives_one_value():
    """Invariant I20: N photons/s read at S1 and at S2 give monitor rates
    r_k = N / (q · S_k/500 nA/V) + D; a signal I divided by r_k and
    multiplied by the factor is I/N both times."""
    n_photons, signal = 3.0e12, 1234.0
    vals = []
    for s in (S200, S10):
        r = n_photons / (flux.per_hz(E) * s / 500e-9) + flux.DARK_MONC_HZ
        vals.append(signal / r * flux.photon_factor(s, E, r)[0])
    assert vals[0] == pytest.approx(signal / n_photons, rel=1e-12)
    assert vals[1] == pytest.approx(signal / n_photons, rel=1e-12)


def test_scan_rate_and_monitor_factor():
    cols = {'Monc': np.array([1e5, 2e5, 3e5, 7.0]), 'Seconds': np.array([1.0, 1.0, 1.0, 0.0])}
    assert scan_rate(cols) == 2e5                      # median, the t = 0 point left out
    assert scan_rate({'Monc': [1.0]}) is None and scan_rate({}) is None
    p = {'MoncGain': S10, 'Wavelength': synth.WAVELENGTH}
    assert monitor_factor(p) == (1.0, True)
    assert monitor_factor(p, monitor_gain=True) == (0.5, True)
    f, known = monitor_factor(p, monitor_gain=True, per_photon=True, rate_hz=2e5)
    assert known and f == flux.photon_factor(S10, E, 2e5)[0]
    assert monitor_factor({'Wavelength': 1.24}, per_photon=True) == (1.0, False)
    assert monitor_factor({'MoncGain': S10, 'Wavelength': 0.3}, per_photon=True) == (1.0, False)   # 41 keV


def _expected(scans):
    rate = synth.XF_MONITOR / synth.XF_REAL
    return np.array([flux.photon_factor(S200 if s < 6 else S10, E, rate)[0] for s in scans])


def test_script_fluorescence_per_photon(xf):
    exp = Experiment(xf)
    off = np.array(exp.fluorescence(MCA, window=(5.6, 7.2)).rows)
    res = exp.fluorescence(MCA, window=(5.6, 7.2), per_photon=True)
    on = np.array(res.rows)
    f = _expected(MCA)
    assert on[:, 3] == pytest.approx(off[:, 3] * f, rel=1e-12)
    assert on[:, 4] == pytest.approx(off[:, 4] * f, rel=1e-12)
    assert res.unknown_gain == []
    assert np.array_equal(np.array(exp.fluorescence(MCA, window=(5.6, 7.2), monitor=None, per_photon=True).rows),
                          np.array(exp.fluorescence(MCA, window=(5.6, 7.2), monitor=None).rows))


def test_script_fluorescence_unknown_gain_is_listed(tmp_path):
    spec, _ = synth.make_xfntr_dataset(tmp_path / 'u', absorber=None, lead_absorber=0)
    exp = Experiment(spec)
    res = exp.fluorescence(MCA, window=(5.6, 7.2), per_photon=True)
    assert res.unknown_gain == MCA and res.rows == exp.fluorescence(MCA, window=(5.6, 7.2)).rows


@pytest.mark.gui
def test_window_per_photon_mca(window, qapp, recorder, xf, tmp_path):
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
    w.spPhotonCheckBox.setChecked(True)
    qapp.processEvents()
    assert w.monitorPhotons and w.monitorGain                    # per photon includes the gain
    assert all(b.isChecked() for b in w.monitorGainBoxes + w.monitorPhotonBoxes)
    on = total()
    assert on[:, 3] == pytest.approx(off[:, 3] * _expected(MCA), rel=1e-12)
    assert any(m.startswith('Monitor normalisation: per incident photon') for m in recorder.messages)
    gui = str(tmp_path / 'gui')
    recorder.save_name = gui
    w.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    text = w.scriptView.toPlainText()
    assert 'per_photon=True' in text and 'monitor_gain=True' not in text.split('flu = ')[-1]
    script = str(tmp_path / 'script')
    _run_script(text.replace(repr(gui), repr(script)), tmp_path)
    with open(gui + '_flu.txt', 'rb') as f1, open(script + '_flu.txt', 'rb') as f2:
        assert f1.read() == f2.read()
    w.mcaPhotonCheckBox.setChecked(False)                        # back to the gain alone
    qapp.processEvents()
    assert w.monitorGain and not w.monitorPhotons and not w.spPhotonCheckBox.isChecked()
    w.spPhotonCheckBox.setChecked(True)
    w.mcaGainCheckBox.setChecked(False)                          # unticking the gain unticks per photon
    qapp.processEvents()
    assert not w.monitorGain and not w.monitorPhotons
    assert not any(b.isChecked() for b in w.monitorGainBoxes + w.monitorPhotonBoxes)
    assert total()[:, 3] == pytest.approx(off[:, 3], rel=1e-12)
    assert recorder.exceptions == []


@pytest.mark.gui
def test_window_per_photon_cut_is_scripted(window, qapp, recorder, pil, tmp_path):
    w = window
    w.openSpecFile(fname=pil)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp, [0, w.pilScanNum.index(2)])
    w.ui.pilCutDirComboBox.setCurrentIndex(2)
    w.ui.pilIntRangeLineEdit.setText('90:110')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    off = {k: np.array(v) for k, v in w.cutData.items()}
    w.mcaPhotonCheckBox.setChecked(True)
    qapp.processEvents()
    prog = _export_and_replay(w, qapp, recorder, tmp_path, 'photon')
    assert 'per_photon=True' in prog
    on = {k: np.array(v) for k, v in w.cutData.items()}
    keys = sorted(k for k in off if k >= 0)
    rate = synth.MONITOR / 1.0                                   # Monc / Seconds of the synthetic scans
    for k, s in zip(keys, (S200, S10)):
        f = flux.photon_factor(s, E, rate)[0]
        assert on[k][:, 1] == pytest.approx(off[k][:, 1] * f, rel=1e-12)
        assert on[k][:, 2] == pytest.approx(off[k][:, 2] * f, rel=1e-12)
    assert recorder.exceptions == []
