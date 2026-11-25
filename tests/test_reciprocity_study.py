"""The dose-or-time study's tool (tests/tools/reciprocity_study.py, F76): a
tiny run writes the tables and figures, and its conditions are the
documented ones."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import reciprocity_study as S          # noqa: E402


def test_the_conditions_and_the_right_calls():
    labels = [c[1] for c in S.conditions(['strip'])]
    assert labels == ['strip 0.2, ignored', 'strip 0.2, as τ', 'strip 0.2, as ρ',
                      'strip 0.5, ignored', 'strip 0.5, as τ', 'strip 0.5, as ρ']
    assert S.RIGHT == {'dose': 'dose', 'time': 'time', 'half': 'neither', 'steep': 'neither', 'mix': 'neither',
                       'none': 'no change'}


def test_a_tiny_run(tmp_path):
    out = tmp_path / 'r'
    assert S.main(['--out', str(out), '--design', 'span,strip', '--replicates', '3',
                   '--spec', str(tmp_path / 'none')]) == 0
    for name in ('R1_anatomy.png', 'R2_calls.png', 'R3_beta_pulls.png', 'R4_strip.png', 'results.csv', 'numbers.json'):
        assert (out / name).is_file(), name
    rows = list(csv.DictReader(open(out / 'results.csv', encoding='utf-8')))
    assert len(rows) == (4 + 6) * len(S.TRUTHS)
    assert json.loads((out / 'numbers.json').read_text())['settings']['replicates'] == 3
