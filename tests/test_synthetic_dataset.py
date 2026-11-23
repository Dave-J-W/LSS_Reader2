"""tests/tools/synthetic_dataset.py (2026-11-23): a synthetic data set with
known truth written to a folder for the reader to open (the Tools menu's
"Open a synthetic data set"). Each kind is read back by the scripting API,
as the window would read it."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import synthetic_dataset  # noqa: E402


@pytest.mark.parametrize('kind', ['xrr', 'xfntr', 'burn'])
def test_each_kind_is_read_back(tmp_path, kind, capsys):
    out = str(tmp_path / kind)
    extra = ['--counts', '0.1', '--fault', 'slits', '--truth', 'water'] if kind == 'xrr' else []
    assert synthetic_dataset.main(['--out', out, '--kind', kind] + extra) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last.startswith('SPEC ')
    spec = last[5:]
    assert os.path.dirname(spec) == out
    with open(os.path.join(out, 'truth.json'), encoding='utf-8') as f:
        info = json.load(f)
    from lss_core.experiment import Experiment
    e = Experiment(spec)
    assert sorted(e.scans) == info['scans']
    if kind == 'xrr':
        assert (info['truth'], info['fault'], info['counts']) == ('water', 'slits', 0.1)
        assert len(info['true_join_factors']) == 3
        r = e.reflectivity(sorted(e.scans))
        assert len(r.per_scan) == 4
        assert os.path.exists(os.path.join(out, 'truth.csv'))
    if kind == 'xfntr':
        assert len(e.scans) == 18


def test_the_fault_changes_only_the_monitor(tmp_path):
    """--fault slits: Monc registers 70 % of the slit change at scans 3-4;
    the detector counts are drawn the same (same seed)."""
    from lss_core.experiment import Experiment
    a = synthetic_dataset.xrr_dataset(str(tmp_path / 'a'), seed=2)[0]
    b = synthetic_dataset.xrr_dataset(str(tmp_path / 'b'), fault='slits', seed=2)[0]
    ea, eb = Experiment(a), Experiment(b)
    ma = ea.scans[3].columns['Monc']
    mb = eb.scans[3].columns['Monc']
    assert mb.mean() / ma.mean() == pytest.approx(0.7, rel=0.01)
    assert (ea.scans[1].columns['Monc'] == eb.scans[1].columns['Monc']).all()
