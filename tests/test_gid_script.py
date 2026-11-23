"""GID is scriptable (Stage 6 start, 2026-11-19): Experiment.gid uses the same
lss_core.gid functions as the window, "Save GID" writes the equivalent call
to the Script pane, and running it writes the same three files byte for
byte, in both geometries, both axes, the relaxed Q grid, a typed column
count and a subset of frames. Real data: NX school scans 11 + 12."""
import glob
import os

import numpy as np
import pytest

import sweep
from lss_core.experiment import Experiment
from lss_core.gid import GIDParams
from test_script_console import _run_script

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
pytestmark = [pytest.mark.gui, pytest.mark.slow,
              pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')]


def _menu(w, qapp, text):
    if text in ('GID Patch', 'Worksheet'):          # buttons since 2026-11-23 (Q-GID-5)
        (w.gidPatchPushButton if text == 'GID Patch' else w.gidWorksheetPushButton).click()
        qapp.processEvents()
        return
    i = w.ui.gidComboBox.findText(text)
    w.ui.gidComboBox.setCurrentIndex(i)
    w.ui.gidComboBox.activated.emit(i)
    qapp.processEvents()


def _save_and_replay(w, qapp, recorder, tmp_path, tag):
    gui = str(tmp_path / ('gui_' + tag))
    recorder.save_name = gui
    _menu(w, qapp, 'Save GID')
    body = w.scriptView.toPlainText().split('\n')
    at = max(k for k, l in enumerate(body) if l.startswith('gid = exp.gid('))
    head = [l for l in body if l.startswith(('from ', 'exp = '))][:2]
    extra = [body[at - 1]] if body[at - 1].startswith('from lss_core.gid') else []
    prog = '\n'.join(head + extra + body[at:at + 2]).replace(repr(gui), repr(gui.replace('gui_', 'script_')))
    _run_script(prog, tmp_path)
    made = sorted(glob.glob(gui + '_*'))
    assert len(made) == 3, made
    for p in made:
        q = p.replace('gui_', 'script_')
        assert open(p, 'rb').read() == open(q, 'rb').read(), os.path.basename(p)
    assert recorder.exceptions == []
    return prog


@pytest.fixture
def nx(window, qapp, tmp_path):
    window.openSpecFile(fname=SPEC)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [10, 11])
    sweep._select_images(window, qapp)
    return window


@pytest.mark.parametrize('pinhole', [True, False])
@pytest.mark.parametrize('axes', ['Q', 'Angles'])
def test_saved_gid_map_is_reproduced_by_its_script(nx, qapp, recorder, tmp_path, pinhole, axes):
    nx.gidParams = GIDParams(pinhole=pinhole)
    _menu(nx, qapp, 'GID Patch')
    nx.ui.pilAxesComboBox.setCurrentIndex(nx.ui.pilAxesComboBox.findText(axes))
    qapp.processEvents()
    prog = _save_and_replay(nx, qapp, recorder, tmp_path, '%s%s' % (pinhole, axes))
    assert ('pinhole=False' in prog) == (not pinhole)
    assert 'axes=%r' % axes in prog


def test_relaxed_grid_typed_columns_and_some_frames(nx, qapp, recorder, tmp_path):
    nx.gidParams = GIDParams(pinhole=False)
    nx.ui.pilHSlitLineEdit.setText('5')
    rows = [k for k, s in enumerate(nx.pilScanNum) if s == 11][:30] + [k for k, s in enumerate(nx.pilScanNum) if s == 12]
    sweep._select_images(nx, qapp, rows)
    _menu(nx, qapp, 'GID Patch Relax')
    nx.ui.pilAxesComboBox.setCurrentIndex(nx.ui.pilAxesComboBox.findText('Q'))
    qapp.processEvents()
    prog = _save_and_replay(nx, qapp, recorder, tmp_path, 'relax')
    for word in ('relax=True', 'columns=5', 'points={11: ['):
        assert word in prog, word


def test_script_result_matches_the_window_map(nx, qapp, recorder):
    """Without saving: the arrays and the join log are the window's."""
    nx.gidParams = GIDParams(pinhole=False)
    _menu(nx, qapp, 'GID Patch')
    res = Experiment(SPEC).gid([11, 12], params=GIDParams(pinhole=False))
    assert np.array_equal(res.data, nx.pilGIDData) and np.array_equal(res.err, nx.pilGIDDataErr)
    assert [(e['kind'], e['factor']) for e in res.joins] == [(e['kind'], e['factor']) for e in nx.gidJoinLog]
    assert res.levels == nx.gidLevels and res.info is None
    pin = Experiment(SPEC).gid([11, 12])
    assert pin.params.pinhole and pin.info['join'] is not None
    assert recorder.exceptions == []


def test_saving_without_a_map_or_in_pixels_says_so(window, qapp, recorder, tmp_path):
    window.openSpecFile(fname=SPEC)
    window.directory = str(tmp_path)
    _menu(window, qapp, 'Save GID')
    assert any('Make a GID map first' in m for m in recorder.messages)
    assert recorder.exceptions == []
