"""The real-scatter study's tool (tests/tools/mca_scatter.py, DATA_NEEDS row 3): its public files are
anonymised and sane, its model-free pieces recover known truth, and its figures are made from public
files alone. The full model's recovery of known truth, and S1 on a synthetic example, are slow."""
import csv
import json
import os
import re
import sys

import numpy as np
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, 'tools'))
sys.path.insert(0, HERE)
import mca_scatter as ms                  # noqa: E402
from synthetic import mca                 # noqa: E402

ROOT = os.path.dirname(HERE)
TABLE = os.path.join(ROOT, 'docs', 'studies', 'mca_scatter', 'scatter_fits.csv')
QTABLE = os.path.join(ROOT, 'docs', 'studies', 'mca_scatter', 'quantities.csv')


def test_no_real_spectrum_is_committed():
    """Scrubbed spectra are published only with the owner's yes (coordinator, 2026-11-24): until then
    the repository holds derived numbers only."""
    assert not os.path.isdir(os.path.join(HERE, 'reference', 'mca_scatter'))
    with open(TABLE, encoding='utf-8') as fh:
        head = fh.readline()
    assert 'counts' not in head.split(',')[:3]


def test_the_public_table_holds_no_identifying_columns_and_rounded_energies():
    with open(TABLE, encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    cols = set(rows[0])
    for bad in ('run', 'scan', 'date', 'time', 'qz', 'file', 'key', 'element', 'monc'):
        assert not any(bad == c or c.startswith(bad + '_') for c in cols), bad
    for r in rows:
        assert re.fullmatch(r'E\d+(\.\d)?-[a-z]', r['id'])
        assert re.fullmatch(r'\d+\.\d', r['beam_keV'])
        assert r['readout'] in ('A', 'B')
    assert len({r['id'] for r in rows}) == len(rows)


def test_the_quantities_table_is_long_form_and_marks_its_evidence():
    with open(QTABLE, encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0]) == ['energy_kev', 'example', 'quantity', 'value', 'error', 'method', 'n_spectra', 'evidence']
    assert {r['evidence'] for r in rows} <= {'measured', 'read', 'computed'}
    for r in rows:
        assert re.fullmatch(r'[ES]\d+(\.\d)?-[a-z]', r['example']), r['example']
        assert not re.search(r'(19|20)\d\d-?\d\d-?\d\d|#S |scan \d|\.mac\b|vortex|_mca', r['method']), r['method']
    q = {r['quantity'] for r in rows}
    for need in ('fwhm_elastic_keV', 'escape_x_reed_fit', 'wing_window_counts_over_compton_data', 'box_Zn_over_elastic',
                 'p1_bias_poisson', 'p1_bias_data_weights', 'dead_time_fraction'):
        assert need in q, need


def test_the_escape_template_recovers_a_known_escape_fraction():
    rng = np.random.default_rng(3)
    det = mca.Detector(escape=1.5, tail=0.0, shelf=0.0)
    s = mca.spectrum({}, elastic=2e7, beam=mca.Beam(energy=8.0, compton_ratio=1.0), detector=det, background=2.0)
    n = s.draw(rng)
    f, fe, chi = ms.escape_template(s.energy, n, 8.0)
    want = 1.5 * mca.reed_escape(8.0)
    assert abs(f - want) < max(4 * fe, 0.1 * want), (f, fe, want)


def test_rebin_shift_keeps_the_counts_and_moves_the_peak():
    a, b = 0.0, 0.01
    e = a + b * np.arange(1, 1001)
    n = 1e4 * np.exp(-0.5 * ((e - 5.0) / 0.05) ** 2)
    m = ms.rebin_shift(n, a, b, 0.123)
    assert abs(m.sum() - n.sum()) / n.sum() < 1e-9
    assert abs(np.sum(e * m) / m.sum() - 5.123) < 1e-3


def test_the_figures_from_the_public_tables(tmp_path):
    made = ms.main(['--out', str(tmp_path), '--only', 'S2,S3'])
    assert (tmp_path / 'S2_vs_energy.png').is_file() and (tmp_path / 'S3_p1_real_series.png').is_file()
    assert len(made) == 2
    numbers = json.loads((tmp_path / 'numbers.json').read_text(encoding='utf-8'))
    assert '10.0 keV, readout A' in numbers
    # the study's headline on readout A at 10 keV, as measured (characterisation)
    a10 = numbers['10.0 keV, readout A']
    assert 0.7 < a10['o1s_core_scale'][0] < 0.95
    assert 0.95 < a10['band_ratio_real_over_generator'][0] < 1.3


@pytest.mark.slow
def test_the_model_recovers_a_known_wing_escape_and_tails():
    """A synthetic spectrum with the generator's 'shells' Compton at 0.5 of water's wing and 1.5 x Reed's
    escape: the fit (with the extra high tail at zero truth) finds them."""
    rng = np.random.default_rng(11)
    beam = mca.Beam(energy=9.0, angle=85.0, compton_ratio=2.0, compton_model='shells', core_scale=0.5)
    det = mca.Detector(noise=0.11, tail=0.02, tail_slope=0.4, shelf=1e-3, escape=1.5)
    s = mca.spectrum({}, elastic=3e6, beam=beam, detector=det, background=3.0)
    n = s.draw(rng)
    sm = ms.ScatterModel(n, mca.CALIB, 9.0, lines=[])
    p, perr, dev, dof = sm.fit()
    P = dict(zip(sm.names, p))
    E = dict(zip(sm.names, ms.fit_errors_scaled(perr, dev, dof)))
    assert dev / dof < 1.3
    assert abs(P['angle'] - 85.0) < 3.0
    assert abs(P['escape'] - 1.5) < max(4 * E['escape'], 0.15)
    assert abs(P['core'] - 0.5) < max(4 * E['core'], 0.15)
    assert abs(P['noise'] - 0.11) < 0.01


@pytest.mark.slow
def test_the_example_figure_refits_a_folder_of_spectra(tmp_path):
    """S1 on a synthetic 'example' (real ones stay private until the owner agrees)."""
    rng = np.random.default_rng(5)
    s = mca.spectrum({}, elastic=1e6, beam=mca.Beam(energy=10.0, compton_ratio=2.0, compton_model='shells',
                                                    core_scale=0.8),
                     detector=mca.Detector(tail=0.02, tail_slope=0.5), background=2.0)
    n = s.draw(rng)
    sel = (s.energy > 7.5) & (s.energy < 10.7)
    fx = tmp_path / 'fx'
    fx.mkdir()
    with open(fx / 'E10-z.csv', 'w', encoding='utf-8') as fh:
        fh.write('# synthetic\nenergy_keV,counts\n')
        for e, c in zip(s.energy[sel], n[sel]):
            fh.write('%.4f,%d\n' % (e, c))
    ms.main(['--out', str(tmp_path), '--only', 'S1', '--fixtures', str(fx), '--jobs', '1'])
    assert (tmp_path / 'S1_examples.png').is_file()
    with open(tmp_path / 'S1_example_fits.csv', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    core = [float(r['value']) for r in rows if r['parameter'] == 'core'][0]
    assert abs(core - 0.8) < 0.15
