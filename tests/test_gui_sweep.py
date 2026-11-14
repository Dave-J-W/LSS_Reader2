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


SITES = os.path.join(os.path.dirname(__file__), 'known_crash_sites.json')
UPDATE = bool(os.environ.get('LSS_UPDATE_CRASHES'))


def _save(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write('\n')


def _load_sites():
    if os.path.exists(SITES):
        with open(SITES) as f:
            return json.load(f)
    return []


@pytest.fixture
def make_window(qapp, tmp_path):
    from mainwindow import MainWindow

    def make():
        w = MainWindow()
        w.directory = str(tmp_path)
        w.show()
        qapp.processEvents()
        return w
    return make


@pytest.fixture
def clean_root():
    """Some save handlers write into the working directory; remove that."""
    before = set(os.listdir(ROOT))
    yield
    for name in set(os.listdir(ROOT)) - before:
        if os.path.isfile(os.path.join(ROOT, name)):
            os.remove(os.path.join(ROOT, name))


def _answer_dialogs(recorder, dataset, tmp_path):
    """Make every file dialog return a usable path instead of 'cancelled'."""
    import numpy as np
    curve = tmp_path / 'curve_ref.txt'
    q = np.linspace(0.01, 0.1, 10)
    np.savetxt(str(curve), np.column_stack([q, q ** -4.0, 0.01 * q ** -4.0]))
    recorder.open_name = dataset
    recorder.open_names = [str(curve)]
    recorder.save_name = str(tmp_path / 'saved')
    recorder.directory = os.path.dirname(dataset)


@pytest.mark.gui
@pytest.mark.sweep
@pytest.mark.parametrize('dialogs', ['cancel', 'paths'])
@pytest.mark.parametrize('state', list(sweep.STATES))
def test_no_new_crashes(state, dialogs, qapp, recorder, dataset, tmp_path,
                        make_window, clean_root):
    if dialogs == 'paths':
        _answer_dialogs(recorder, dataset, tmp_path)
    key = state if dialogs == 'cancel' else state + '+paths'
    found = sweep.run_state(make_window, qapp, recorder, dataset, state)
    recorder.exceptions.clear()
    if UPDATE:
        data = _load()
        data[key] = found
        _save(BASELINE, data)
        return
    known = _load().get(key, {})
    new = {k: v for k, v in found.items() if k not in known}
    fixed = sorted(k for k in known if k not in found)
    assert not new, 'controls that newly raise in %r: %s' % (key, new)
    assert not fixed, ('controls that no longer raise in %r; remove them '
                       'from known_crashes.json: %s' % (key, fixed))


WALK_STEPS = 150
WALK_SEEDS = (1, 2, 3)


@pytest.mark.gui
@pytest.mark.sweep
@pytest.mark.parametrize('seed', WALK_SEEDS)
@pytest.mark.parametrize('state', ['spec_loaded', 'pilatus_one_frame',
                                   'mca_frames'])
def test_random_walk_raises_only_at_known_sites(state, seed, qapp, recorder,
                                                dataset, tmp_path,
                                                make_window, clean_root):
    """Sequences of controls, nothing reset in between.

    A walk changes whenever behaviour changes, so individual steps cannot be
    pinned. What is pinned is the set of places exceptions come from
    ('Type @ file:function'): single-control sweep sites plus
    known_crash_sites.json. A new site fails the test.
    """
    _answer_dialogs(recorder, dataset, tmp_path)
    raised = sweep.run_walk(make_window, qapp, recorder, dataset, state,
                            seed, WALK_STEPS)
    sites = {r[2] for r in raised}
    single = {v for d in _load().values() for v in d.values()}
    if UPDATE:
        _save(SITES, sorted((set(_load_sites()) | sites) - single))
        return
    unknown = sorted(sites - single - set(_load_sites()))
    examples = [r for r in raised if r[2] in unknown][:5]
    assert not unknown, 'new crash sites in a random walk: %s' % examples
