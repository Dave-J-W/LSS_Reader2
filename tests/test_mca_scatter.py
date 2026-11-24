"""The real-scatter study's tool (tests/tools/mca_scatter.py, DATA_NEEDS row 3): its public files are
anonymised and sane, its model-free pieces recover known truth, and its figures are made from public
files alone. The full model's recovery of known truth is in the slow suite."""
import csv
import json
import math
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
FIX = os.path.join(HERE, 'reference', 'mca_scatter')
TABLE = os.path.join(ROOT, 'docs', 'studies', 'mca_scatter', 'scatter_fits.csv')


def test_the_example_spectra_are_anonymised_10_keV_scatter():
    files = sorted(f for f in os.listdir(FIX) if f.endswith('.csv'))
    assert files and all(re.fullmatch(r'E10-[a-z]\.csv', f) for f in files)
    for f in files:
        head, e, n = ms.read_fixture(os.path.join(FIX, f))
        assert not re.search(r'(19|20)\d\d[-/]?\d\d|scan|#S|\.mac|vortex|_mca', head, re.I), head
        assert np.all(np.diff(e) > 0) and np.all(n >= 0) and np.all(n == np.round(n))
        assert 7.4 < e[0] < 7.6 and 10.6 < e[-1] < 10.8          # E0 - 2.5 ... E0 + 0.7 keV only
        top = e[np.argmax(n)]
        assert 9.7 < top < 10.05                                  # the elastic + Compton peak


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


def test_the_figure_of_numbers_against_energy_from_the_public_table(tmp_path):
    made = ms.main(['--out', str(tmp_path), '--only', 'S2'])
    assert (tmp_path / 'S2_vs_energy.png').is_file() and len(made) == 1
    numbers = json.loads((tmp_path / 'numbers.json').read_text(encoding='utf-8'))
    assert '10.0 keV, readout A' in numbers
    # the study's headline on readout A at 10 keV, as measured (characterisation)
    a10 = numbers['10.0 keV, readout A']
    assert 0.7 < a10['o1s_core_scale'][0] < 0.95
    assert 0.95 < a10['band_ratio_real_over_generator'][0] < 1.3


@pytest.mark.slow
def test_the_model_recovers_a_known_wing_escape_and_tails():
    """A synthetic spectrum with the generator's 'shells' Compton at 0.5 of water's wing and 1.5 × Reed's
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
