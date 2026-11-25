"""The dose-or-time study's tool (tests/tools/reciprocity_study.py, F76): a
tiny run writes the tables and figures, and its conditions are the
documented ones."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import pytest                           # noqa: E402
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


def test_c54s_real_series(tmp_path):
    """Section 6 (2026-11-25), from the public, anonymised C54 tables:
    the strip scatter of the six repeat groups is relative (ρ 1.13 fits
    them better than τ 90 %/h by Δ(−2 log L) 39), dose_or_time reproduces
    C54's verdicts (19 of 19 on counting errors, 18 of 19 with its τ), and
    under ρ five series still rise and fall. Measured, as quoted."""
    import json
    import reciprocity_real as RR
    n = RR.run(str(tmp_path), design_replicates=0)
    assert n['tau'] == pytest.approx(90.1, abs=0.5) and n['rho'] == pytest.approx(1.13, abs=0.01)
    ll = n['minus_log_likelihood']
    assert ll['rho'] < ll['tau'] < ll['none'] and 2 * (ll['tau'] - ll['rho']) == pytest.approx(38.8, abs=0.5)
    assert n['agreement'] == {'counting vs C54 drop1': 19, 'tau_c54 vs C54 drop1+strip': 18}
    assert n['tallies']['rho']['opposite signs'] == 5 and n['series'] == 19
    with open(tmp_path / 'numbers.json', encoding='utf-8') as f:
        assert json.load(f)['tallies'] == n['tallies']
    assert (tmp_path / 'R6_real_beta.png').exists() and (tmp_path / 'comparison.csv').exists()
