"""Options added to analysis scripts on 2026-11-23 so that the documents'
variations ("change this and rerun to see that") are command lines (the
Tools menu, F84). Each default leaves the output as it was (checked when
each was added); here, that each option reaches what it sets."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))


def test_monitor_mc_regimes_and_monitors(capsys):
    import monitor_noise_mc as mc
    assert mc.main(['--no-real', '--trials', '300', '--seed', '1', '--regimes', 'B', '--monitors', 'exact']) == 0
    out = capsys.readouterr().out
    part1 = out.split('PART 2')[0]
    rows = [l for l in part1.splitlines() if l.startswith(('A ', 'A2', 'A3', 'B ', 'C ', 'C2'))]
    assert rows and all(l.startswith('B ') and 'noiseless' in l for l in rows)
    assert '300 trials, seed 1' in out


def test_patch_demo_survey_prints_every_method_and_join(capsys):
    import patch_demo
    assert patch_demo.main(['--survey', '3', '--set', 'truth=water']) == 0
    out = capsys.readouterr().out
    assert 'reflectivity survey: 3 replicates' in out
    from demonstrator import refl
    for m in refl.DEFAULT_METHODS:
        assert any(l.startswith(m + ' ') for l in out.splitlines()), m


def test_pinhole_case8_options_reach_the_case(monkeypatch, tmp_path):
    import pinhole_figures as pf
    seen = {}
    monkeypatch.setattr(pf, 'case8', lambda out: seen.update(pf.CASE8))
    for k in range(1, 8):
        monkeypatch.setattr(pf, 'case%d' % k, lambda out: None)
    pf.main(['--out', str(tmp_path), '--only', '8', '--case8-dth', '14', '--case8-openings', '0.05,0.2,1.0'])
    assert seen == {'dth': 14.0, 'openings': (0.05, 0.2, 1.0)}


def test_synthetic_roughness_and_background(tmp_path):
    import json
    import synthetic_dataset as sd
    sd.main(['--out', str(tmp_path / 'r'), '--roughness', '6', '--background', '50'])
    with open(tmp_path / 'r' / 'truth.json', encoding='utf-8') as f:
        info = json.load(f)
    assert info['roughness_A'] == 6.0 and info['background_scale'] == 50.0
    import numpy as np
    sd.main(['--out', str(tmp_path / 's')])
    r = np.loadtxt(tmp_path / 'r' / 'truth.csv', delimiter=',')
    s = np.loadtxt(tmp_path / 's' / 'truth.csv', delimiter=',')
    hi = r[:, 0] > 0.3
    assert np.all(r[hi, 1] < s[hi, 1])                      # rougher: less reflectivity at high Qz
