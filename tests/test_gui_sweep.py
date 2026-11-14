"""Crash inventory: trigger every control in several application states.

``known_crashes.json`` lists the controls that currently raise. The test
fails when a control that is not listed starts raising (a regression) and
when a listed control stops raising (the list must then be shortened), so
the inventory can only shrink. Regenerate it with

    LSS_UPDATE_CRASHES=1 pytest -m sweep

The sweep takes several minutes, so it is deselected by default
(see pyproject.toml); run it with ``pytest -m sweep``.
"""
import json
import os

import pytest

import sweep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(os.path.dirname(__file__), 'known_crashes.json')


def _load():
    if os.path.exists(BASELINE):
        with open(BASELINE) as f:
            return json.load(f)
    return {}


@pytest.mark.gui
@pytest.mark.sweep
@pytest.mark.parametrize('state', list(sweep.STATES))
def test_no_new_crashes(state, qapp, recorder, dataset, tmp_path):
    from mainwindow import MainWindow

    def make_window():
        w = MainWindow()
        w.directory = str(tmp_path)
        w.show()
        qapp.processEvents()
        return w

    before = set(os.listdir(ROOT))
    try:
        found = sweep.run_state(make_window, qapp, recorder, dataset, state)
    finally:
        # some save handlers write next to the working directory even when
        # the file dialog is cancelled; keep the repository clean
        for name in set(os.listdir(ROOT)) - before:
            if os.path.isfile(os.path.join(ROOT, name)):
                os.remove(os.path.join(ROOT, name))
    recorder.exceptions.clear()
    if os.environ.get('LSS_UPDATE_CRASHES'):
        data = _load()
        data[state] = found
        with open(BASELINE, 'w') as f:
            json.dump(data, f, indent=1, sort_keys=True)
            f.write('\n')
        return
    known = _load().get(state, {})
    new = {k: v for k, v in found.items() if k not in known}
    fixed = sorted(k for k in known if k not in found)
    assert not new, 'controls that newly raise in state %r: %s' % (state, new)
    assert not fixed, ('controls that no longer raise in state %r; remove '
                       'them from known_crashes.json: %s' % (state, fixed))
