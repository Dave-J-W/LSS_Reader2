"""The Qoff study's tool (tests/tools/qoff_study.py, F79): a tiny run makes
the tables and figures, and its conditions carry the truth."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import qoff_study as S          # noqa: E402


def test_the_conditions_carry_the_truth():
    c = S.conditions(['qc'])
    assert [x.label for x in c] == ['NaCl at 0.0217', 'NaCl at its Qc', 'water at 0.0221']
    assert c[0].qc_used == 0.0217 and abs(c[0].qc_true - 0.0221) < 1e-4
    assert abs(c[0].truth - 0.000884) < 1e-6                 # δα 0.005° at 10 keV
    assert {x.outliers for x in S.conditions(['outliers'])} == {0, 1, 2, -1}


def test_a_tiny_run(tmp_path):
    out = tmp_path / 'q'
    assert S.main(['--out', str(out), '--design', 'offset,qc', '--replicates', '2', '--bootstrap', '3',
                   '--jobs', '1', '--spec', str(tmp_path / 'none')]) == 0
    for name in ('Q1_anatomy.png', 'Q2_bias.png', 'Q3_pulls.png', 'Q4_qc.png', 'results.csv', 'replicates.csv',
                 'numbers.json'):
        assert (out / name).is_file(), name
    rows = list(csv.DictReader(open(out / 'results.csv', encoding='utf-8')))
    assert {r['estimator'] for r in rows} == set(S.ESTIMATORS)
    assert len(rows) == (6 + 3) * len(S.ESTIMATORS)
    assert json.loads((out / 'numbers.json').read_text())['settings']['replicates'] == 2
