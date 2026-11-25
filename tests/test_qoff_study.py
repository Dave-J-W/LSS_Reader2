"""The Qoff study's tool (tests/tools/qoff_study.py, F79): a tiny run makes
the tables and figures, and its conditions carry the truth."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import pytest                  # noqa: E402
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


@pytest.mark.slow
def test_the_qoff_walkthrough_on_nx(tmp_path):
    """The Qoff walkthrough's quoted numbers (2026-11-25): on NX scans 6-9
    the edge fit proposes -0.00028 with chi2/dof about 75 (a sharp R_F
    cannot follow the rounded edge), and on NX's own Qz points the
    beamline's median resolution reads as -1.33e-4."""
    import qoff_walkthrough as QW
    from lss_core.experiment import Experiment
    e = Experiment(QW.NX)
    ref = e.reflectivity([6, 7, 8, 9]).ref
    q, r, s = ref[:, 0], ref[:, 1], ref[:, 2]
    fit = QW.qw3(str(tmp_path), q, r, s)
    assert fit['qoff'] == pytest.approx(-0.00028, abs=1e-5) and 60 < fit['chi2'] / fit['dof'] < 90
    keep = q < 2.5 * QW.QC
    reads = {x['fwhm']: x['qoff'] for x in QW.qw5(str(tmp_path), q[keep], (s / r)[keep], fwhms=(0.0, 8.9e-4))}
    assert reads[0.0] == pytest.approx(0.0, abs=1e-6) and reads[8.9e-4] == pytest.approx(-1.33e-4, abs=0.05e-4)
