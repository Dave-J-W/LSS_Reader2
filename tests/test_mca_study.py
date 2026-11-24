"""Study B's figure tool (tests/tools/mca_study.py, F90): on a tiny study
run of the gauntlet it makes every figure and the numbers behind them."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
import mca_fit_gauntlet as g          # noqa: E402
import mca_study                      # noqa: E402


def test_the_study_figures_from_a_tiny_run(tmp_path):
    run = tmp_path / 'gauntlet'
    g.main(['--out', str(run), '--design', 'robust,counts,series,random', '--methods', 'study', '--compton', 'shells',
            '--replicates', '2', '--random', '3', '--random-replicates', '2', '--series-replicates', '2', '--jobs', '2'])
    out = tmp_path / 'figs'
    mca_study.main(['--gauntlet', str(run), '--out', str(out), '--only', 'B1,B3,B4,B5,B6,B7'])
    for name in ('B1_anatomy.png', 'B3_weighting.png', 'B4_features.png', 'B5_series.png', 'B6_pass_rates.png',
                 'B7_robustness.png', 'B3_counts.csv', 'B6_pass_rates.csv', 'B7_robustness.csv', 'numbers.json'):
        assert (out / name).is_file(), name
    numbers = json.loads((out / 'numbers.json').read_text())
    assert numbers['B1_box_counts']['Zn Kα (the line)'] > 0
    assert len(numbers['B7']) == 4 * 20                  # four conclusions over the 5 × 4 grid
    assert numbers['B3']['neyman_c'] == numbers['B3']['neyman_c']   # finite
