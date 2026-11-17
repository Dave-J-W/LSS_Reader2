"""Scripted reduction (F31): the same files as the window, byte for byte.

lss_core.experiment.Experiment runs the window's Ref Patch workflow without
Qt. Its output is compared with the legacy export fixtures, which were
written by the window (tests/test_ref_export_golden.py).
"""
import os
import sys

import pytest

from lss_core.experiment import Experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, 'tests', 'reference', 'legacy_export')
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')

CASES = {                     # fixture name -> keyword arguments
    'plain': {},
    'drops': {'drops': {0: [-1]}},
    'norm_factor': {'norm_factor': 2.5},
    'qoff': {'qoff': 0.0005},
    'qz2': {},                # the Qz^2 option only changes the plot now
    'no_rrf': {'rrf': False},
}


def _compare(case, tmp_path, result):
    out = str(tmp_path / 'out')
    result.save(out)
    for kind in ('ref', 'rrf'):
        golden = os.path.join(GOLDEN, '%s_%s.txt' % (case, kind))
        produced = out + '_%s.txt' % kind
        if not os.path.exists(golden):
            assert not os.path.exists(produced), (case, kind)
            continue
        with open(golden, 'rb') as a, open(produced, 'rb') as b:
            assert a.read() == b.read(), '%s %s differs from the window' % (case, kind)


@pytest.mark.parametrize('case', list(CASES))
def test_script_reproduces_window_files_synthetic(case, dataset, tmp_path):
    exp = Experiment(dataset)
    _compare(case, tmp_path, exp.reflectivity([1, 2], **CASES[case]))


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
@pytest.mark.parametrize('case,kw', [
    ('nx_scans_6-9', {}),
    ('nx_scans_6-9_drops', {'drops': {0: [0], 1: [-1], 2: [0, -1]}}),
])
def test_script_reproduces_window_files_real(case, kw, tmp_path):
    exp = Experiment(NX)
    _compare(case, tmp_path, exp.reflectivity([6, 7, 8, 9], **kw))


def test_experiment_lists_scans_and_frames(dataset):
    exp = Experiment(dataset)
    assert sorted(exp.scans) == [1, 2, 3, 4]
    assert [exp.scans[n].detector for n in (1, 2, 3, 4)] == \
        ['Pilatus', 'Pilatus', 'Vortex', 'Monitor']
    frames = exp.frames([1, 2])
    assert len(frames) == 9 + 7
    assert frames[0].scan == 1 and frames[0].index == 0
    assert frames[-1].qz == pytest.approx(0.10)
    with pytest.raises(ValueError):
        exp.frames([4])


def test_core_does_not_need_qt(dataset):
    """Reading and reducing must work in a process that never imports Qt."""
    import subprocess
    code = ("import sys\n"
            "from lss_core.experiment import Experiment\n"
            "r = Experiment(%r).reflectivity([1, 2])\n"
            "print(len(r.ref), 'PyQt5' in sys.modules)\n" % dataset)
    env = dict(os.environ, MPLBACKEND='Agg')
    out = subprocess.run([sys.executable, '-W', 'ignore', '-c', code], cwd=ROOT,
                         env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.split() == ['14', 'False']
