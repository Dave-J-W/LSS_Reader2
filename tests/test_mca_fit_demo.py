"""The MCA fit demo's beam-energy figure (tests/tools/mca_fit_demo.py, the
F90 wrap-up, 2026-11-24): its spectrum is study B's hard case, a beam
below the K edge gives no panel, and a tiny run writes the figure and the
numbers behind it."""
import csv
import json
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import mca_fit_gauntlet as g          # noqa: E402
import mca_fit_demo as demo           # noqa: E402


def test_the_demo_spectrum_is_study_b_hard_case():
    study = g.with_shells(g.core()['hard'])
    mine = demo.condition(10.0)
    assert replace(mine, describe='') == replace(study, describe='')
    assert demo.condition(12.0, wing=0.5, escape=3.0).beam.core_scale == 0.5
    assert demo.condition(12.0, wing=0.5, escape=3.0).detector.escape == 3.0
    assert not demo.excited(demo.condition(9.5))           # Zn K edge 9.659 keV
    assert demo.excited(demo.condition(9.5, element='Fe'))


def test_a_tiny_run_writes_the_figure_and_numbers(tmp_path, capsys):
    out = tmp_path / 'demo'
    assert demo.main(['--out', str(out), '--beams', '9.5,12', '--replicates', '2', '--workers', '1']) == 0
    assert 'below the Zn K edge' in capsys.readouterr().out
    for name in ('beam_energy.png', 'beam_energy.csv', 'numbers.json'):
        assert (out / name).is_file(), name
    numbers = json.loads((out / 'numbers.json').read_text())
    assert list(numbers['bias']) == ['12'] and set(numbers['bias']['12']) == {'window', 'p1'}
    rows = list(csv.DictReader(open(out / 'beam_energy.csv', encoding='utf-8')))
    assert [r['method'] for r in rows] == ['window', 'p1']
    assert float(rows[0]['rel_bias']) > 0.2                 # the window sum counts the scatter in the box
