"""The GUI workflow map and control inventory stay in step with the window
(F67, `docs/gui/README.md`).

The map (`docs/gui/workflows.yaml`) names controls from the inventory
(`docs/gui/inventory/*.yaml`); `tests/tools/gui_map.py --check --window`
checks both directions against a live window. When this fails because a
control was added, add its entry to the inventory file of its area (the
schema is in `docs/gui/README.md`) and, if a workflow uses it, its id to
that step's `controls`; then rerun `python tests/tools/gui_map.py` to
render `docs/gui/workflows.md` and `inventory.md`.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(HERE, 'tools', 'gui_map.py')

yaml = pytest.importorskip('yaml')


def test_map_and_inventory_check_against_the_window(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', MPLBACKEND='Agg',
               LSS_READER_LOG_DIR=str(tmp_path / 'logs'), LSS_READER_PREFS=str(tmp_path / 'prefs.json'))
    r = subprocess.run([sys.executable, TOOL, '--check', '--window', '--no-render'], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'Problems: 0' in r.stdout
    assert 'every named control of the main window is inventoried' in r.stdout


def test_a_control_missing_from_the_inventory_is_found(window, recorder):
    """The reverse check finds a control the inventory lacks: here the
    covariance box, which joined the window on 2026-11-22 after the
    inventory was written and was caught only by reading the merge."""
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import gui_map
    report = gui_map.Report()
    _, entries = gui_map.load_inventory(report)
    assert report.problems == []
    assert gui_map.uninventoried_controls(window, entries) == []
    fewer = [e for e in entries if e['id'] != 'refCovarianceCheckBox']
    assert len(fewer) == len(entries) - 1
    assert gui_map.uninventoried_controls(window, fewer) == [('QCheckBox', 'refCovarianceCheckBox')]
    assert recorder.exceptions == []
