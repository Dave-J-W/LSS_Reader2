"""Cuts are scriptable (Stage 2, F31/F48): exporting a cut writes the
equivalent ``exp.cut(...)`` to the Script pane, and running it writes the
same files byte for byte. The window and the script share
lss_core.cuts.frame_cut."""
import glob
import os

import pytest

import sweep
from test_script_console import _run_script

pytestmark = pytest.mark.gui

RANGES = {0: '0.005:0.02', 1: '-0.01:0.01', 2: '90:110', 3: '90:105'}


def _export_and_replay(w, qapp, recorder, tmp_path, tag):
    gui = str(tmp_path / ('gui_' + tag + '_'))
    recorder.save_name = gui
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    w.ui.cutExportPushButton.click()
    qapp.processEvents()
    text = w.scriptView.toPlainText()
    script = gui.replace('gui_', 'script_')
    body = text.split('\n')
    # the pane holds the opening line and every action since; replay the last cut only
    lines = [l for l in body if l.startswith(('from ', 'exp = '))]
    cut_at = max(k for k, l in enumerate(body) if l.startswith('cut = exp.cut('))
    tail = body[cut_at:]
    head = [l for l in body[:cut_at] if l.startswith('from lss_core import absorbers')][-1:] if \
        'absorbers.' in body[cut_at] else []
    prog = '\n'.join(lines[:2] + head + tail).replace(repr(gui), repr(script))
    _run_script(prog, tmp_path)
    produced = sorted(glob.glob(gui + '*'))
    assert produced, 'nothing exported'
    for p in produced:
        q = p.replace('gui_', 'script_')
        assert os.path.exists(q), q
        assert open(p, 'rb').read() == open(q, 'rb').read(), os.path.basename(p)
    assert recorder.exceptions == []
    return prog


@pytest.mark.parametrize('direction', [0, 1, 2, 3])
@pytest.mark.parametrize('axes', [0, 1, 2])
@pytest.mark.parametrize('summed', [False, True])
def test_exported_cut_is_reproduced_by_its_script(loaded, qapp, recorder, dataset, tmp_path,
                                                  direction, axes, summed):
    w = loaded
    sweep.state_pilatus_two_scans_all_frames(w, qapp, dataset)
    w.ui.pilAxesComboBox.setCurrentIndex(axes)
    w.ui.gixSumCheckBox.setChecked(summed)
    w.ui.pilCutDirComboBox.setCurrentIndex(direction)
    w.ui.pilIntRangeLineEdit.setText(RANGES[direction])
    prog = _export_and_replay(w, qapp, recorder, tmp_path, '%d%d%d' % (direction, axes, summed))
    assert 'exp.cut(' in prog
    assert 'absfac=absorbers.calibrated(10.0)' in prog     # scan 2 is at absorber 1, 10 keV


def test_budget_typed_geometry_partial_frames_and_pinhole(loaded, qapp, recorder, dataset, tmp_path):
    w = loaded
    sweep.state_pilatus_two_scans_all_frames(w, qapp, dataset)
    w.errorModeComboBox.setCurrentIndex(1)              # Budget
    w.setErrorModel()
    sweep._select_images(w, qapp, [0, 2, 9, 11])        # some frames of each scan
    w.ui.pilSpecCheckBox.setChecked(False)              # typed distance and direct beam
    w.ui.pilSDDistLineEdit.setText('700')
    w.ui.pilDBPosLineEdit.setText('97,100')
    w.ui.pilPinholeCheckBox.setChecked(True)
    w.ui.pilAxesComboBox.setCurrentIndex(2)             # Q
    sweep._select_images(w, qapp, [0, 2, 9, 11])        # redisplay with these settings
    w.ui.pilCutDirComboBox.setCurrentIndex(3)
    w.ui.pilIntRangeLineEdit.setText('90:105')
    prog = _export_and_replay(w, qapp, recorder, tmp_path, 'budget')
    for word in ("errors={'mode': 'budget'", 'distance=700.0', 'db_pos=(97.0, 100.0)', 'pinhole=True', 'points='):
        assert word in prog, word


def test_background_subtracted_cuts_are_noted_not_scripted(loaded, qapp, recorder, dataset, monkeypatch):
    w = loaded
    sweep.state_pilatus_two_scans_all_frames(w, qapp, dataset)
    monkeypatch.setattr(w.ui.backgroundListWidget, 'selectedItems', lambda: [object()])
    assert 'scripts cannot do that yet' in w.cutScript('x')
