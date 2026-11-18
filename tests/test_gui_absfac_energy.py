"""The Absorber factor field follows the scans' energy (F49; owner,
2026-11-17/18): 50 um Al per unit at 10 keV and below, NIST SRD 126 μ/ρ.
"""
import pytest

import numpy as np

import sweep
import synth
from test_script_console import _run_script

pytestmark = pytest.mark.gui


def _xf(tmp_path, wavelengths=None, absorber=3):
    """XFNTR data set; ``wavelengths``: {scan: #W in Angstrom} to change."""
    spec, truth = synth.make_xfntr_dataset(tmp_path / 'xf', absorber=absorber)
    if wavelengths:
        text = open(spec).read().split('#S ')
        for k, part in enumerate(text):
            num = part.split()[0] if part.strip() else ''
            if num.isdigit() and int(num) in wavelengths:
                text[k] = part.replace('#W x %g' % synth.WAVELENGTH, '#W x %r' % wavelengths[int(num)])
        open(spec, 'w').write('#S '.join(text))
    return spec


def _open(w, qapp, spec, tmp_path, rows=None):
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(w, qapp, rows)
    qapp.processEvents()


def test_on_by_default_and_10_kev_gives_the_calibrated_foils(loaded, qapp, recorder, dataset):
    """Changed deliberately 2026-11-18 (owner): at 10 keV the calibrated
    foils replace 1.4247 per unit; with the preference off, 1.4247 as before."""
    from lss_core import absorbers
    w = loaded
    assert w.absFacEnergyCheckBox.isChecked() and w.ui.AbsFacLineEdit.isReadOnly()
    sweep.state_spec_loaded(w, qapp, dataset)
    sweep._select_scans(w, qapp, [0])
    assert w.ui.AbsFacLineEdit.text() == 'cal' and w.absfac == absorbers.calibrated(10.0)   # 1.24 A: 10 keV
    w.setPreference('calibrated_foils', False)
    assert w.ui.AbsFacLineEdit.text() == '1.4247' and w.absfac == 1.4247
    assert recorder.exceptions == []


def test_6_kev_scans_use_the_al_factor_at_their_energy(window, qapp, recorder, tmp_path):
    w = window
    spec = _xf(tmp_path, {n: 1.996518 for n in range(1, 10)})       # 6.21 keV (bu 2026oct)
    _open(w, qapp, spec, tmp_path)
    assert w.absfac == 4.0924 and w.ui.AbsFacLineEdit.text() == '4.0924'
    assert any('Absorber factor 4.0924 per unit: 50 um Al at 6.21 keV' in m for m in recorder.messages)
    sweep._select_images(w, qapp, None)
    w.ui.mcaRanLineEdit.setText('5.6:7.2')
    w.ui.mcaSumAllPushButton.click()
    qapp.processEvents()
    assert w.mcaAbsfacUsed == 4.0924
    assert w.mcaAbsorberFactor(0) == pytest.approx(4.0924 ** 3)
    gui = str(tmp_path / 'gui')
    recorder.save_name = gui
    w.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    text = w.scriptView.toPlainText()
    assert 'absfac=4.0924' in text
    script = str(tmp_path / 'script')                 # the Script pane reproduces the export
    _run_script(text.replace(repr(gui), repr(script)), tmp_path)
    with open(gui + '_flu.txt', 'rb') as f1, open(script + '_flu.txt', 'rb') as f2:
        assert f1.read() == f2.read()
    six = np.array(w.mcaIntData)[:, 3]
    w.absFacEnergyCheckBox.setChecked(False)          # the same data with the 10 keV factor
    w.ui.AbsFacLineEdit.setText('1.4247')
    w.ui.mcaSumAllPushButton.click()
    qapp.processEvents()
    ten = np.array(w.mcaIntData)[:, 3]
    assert six == pytest.approx(ten * (4.0924 / 1.4247) ** 3, rel=1e-12)
    assert recorder.exceptions == []


def test_unknown_foil_keeps_the_field_and_says_why(window, qapp, recorder, tmp_path):
    w = window
    spec = _xf(tmp_path, {n: 1.179116 for n in range(1, 10)})       # 10.52 keV (bu 2026-09-02)
    _open(w, qapp, spec, tmp_path)
    assert w.absfac == 1.4247
    assert any('10.52 keV: the foils used at this energy are not known' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_mixed_energies_are_reported(window, qapp, recorder, tmp_path):
    w = window
    spec = _xf(tmp_path, {1: 1.650036})                             # scan 1 at 7.51 keV, rest 10
    _open(w, qapp, spec, tmp_path, rows=[0, 1])
    assert w.absfac == 2.2589                                        # the first selected scan's
    msg = [m for m in recorder.messages if 'different absorber factors' in m]
    assert len(msg) == 1 and 'Reduce them separately' in msg[0]
    assert recorder.exceptions == []


def test_unticked_the_typed_value_stays(window, qapp, recorder, tmp_path):
    w = window
    w.absFacEnergyCheckBox.setChecked(False)
    assert not w.ui.AbsFacLineEdit.isReadOnly()
    w.ui.AbsFacLineEdit.setText('1.5')
    spec = _xf(tmp_path, {n: 1.996518 for n in range(1, 10)})
    _open(w, qapp, spec, tmp_path)
    assert w.absfac == 1.5
    w.absFacEnergyCheckBox.setChecked(True)                          # back on: follows the energy
    assert w.absfac == 4.0924
    assert recorder.exceptions == []
