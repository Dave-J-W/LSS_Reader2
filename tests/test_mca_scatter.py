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


BLANKS = os.path.join(HERE, 'reference', 'mca_scatter')
BLANK_IDS = ['E10-d', 'E10-f', 'E10-i', 'E10-j', 'E10-k', 'E9.2-a', 'E9.2-b', 'E9.2-c', 'E9.2-d',
             'E6.1-a', 'E6.1-b', 'E6.1-c', 'E6.1-d']


def test_the_committed_blanks_are_exactly_the_owner_approved_ones():
    """Owner, 2026-11-24: "Yes, commit them" for these 13 scrubbed blanks, and no other spectrum."""
    names = sorted(os.path.splitext(f)[0] for f in os.listdir(BLANKS))
    assert names == sorted(BLANK_IDS)
    with open(TABLE, encoding='utf-8') as fh:
        head = fh.readline()
    assert 'counts' not in head.split(',')[:3]


@pytest.mark.parametrize('aid', BLANK_IDS)
def test_a_blank_loads_with_an_anonymous_header_and_its_elastic_at_the_beam(aid):
    with open(TABLE, encoding='utf-8') as fh:
        table = {r['id']: r for r in csv.DictReader(fh)}
    head, e, n = ms.read_fixture(os.path.join(BLANKS, aid + '.csv'))
    meta = ms.fixture_meta(head)
    assert set(meta) == {'beam_keV', 'readout', 'kind', 'gain_keV_per_channel', 'real_time_s', 'live_time_s',
                         'energy'}
    # nothing that ties it to a beamtime: no dates, times of day, scan numbers or file names
    assert not re.search(r'(19|20)\d\d-?\d\d-?\d\d|\d\d:\d\d|#S |scan \d|\.mac\b|vortex|_mca|\.spec\b', head, re.I)
    assert meta['beam_keV'] == table[aid]['beam_keV'] and meta['readout'] == table[aid]['readout']
    e0 = float(meta['beam_keV'])
    b = float(meta['gain_keV_per_channel'])
    assert np.allclose(np.diff(e), b, atol=2e-4)
    assert e[0] < e0 - 2.4 and e[-1] > e0 + 0.55
    assert np.all(n >= 0) and np.all(n == np.round(n)) and n.sum() > 1e5
    assert 0 < float(meta['live_time_s']) <= float(meta['real_time_s']) * 1.001
    # the elastic line's high-energy half-maximum edge (model-free; on readout A elastic and Compton blend)
    # sits at the beam energy plus half the fitted elastic FWHM; the beam is known to 0.1 keV here
    top = np.argmax(np.where(e > e0 - 0.3, n, 0))
    edge = e[top + np.argmax(n[top:] < 0.5 * n[top])]
    want = e0 + 0.5 * float(table[aid]['elastic_fwhm_keV'])
    assert abs(edge - want) < 0.06, (edge, want)


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
