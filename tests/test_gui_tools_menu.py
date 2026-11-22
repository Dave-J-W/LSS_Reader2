"""The Tools menu (lss_tools.gui): one entry per registry tool; generators
open a dialog and run only on Run, as a separate process, with the result
in the Messages pane; demonstrations open a window closed with the reader;
outputs never go into sample_data/ (but private figures)."""
import os
import time

import pytest
from PyQt5 import QtWidgets

import sweep
from lss_tools import gui as toolsgui
from lss_tools import registry as reg

NX = os.path.join(reg.ROOT, *reg.NX.split('/'))


def _actions(w):
    return {a.objectName()[len('actionTool_'):]: a for a in w.findChildren(QtWidgets.QAction)
            if a.objectName().startswith('actionTool_')}


def _wait(qapp, w, tool_id, timeout=90):
    t0 = time.time()
    while tool_id in w.toolRuns and time.time() - t0 < timeout:
        qapp.processEvents()
        w.toolRuns[tool_id].proc.waitForFinished(100)
    qapp.processEvents()


def test_menu_has_every_tool_grouped(window, recorder):
    titles = [a.text() for a in window.ui.menuBar.actions()]
    assert titles.index('Tools') == titles.index('Help') - 1
    acts = _actions(window)
    assert sorted(acts) == sorted(t.id for t in reg.TOOLS)
    subs = {m.objectName(): m for m in window.toolsMenu.findChildren(QtWidgets.QMenu)}
    for kind, _ in reg.KINDS:
        ids = [a.objectName()[len('actionTool_'):] for a in subs['menuTools_' + kind].actions()]
        assert ids == [t.id for t in reg.TOOLS if t.kind == kind]
    for t in reg.TOOLS:
        assert acts[t.id].toolTip().startswith(t.summary)
        assert acts[t.id].isEnabled()
    assert recorder.exceptions == []


def test_generator_actions_open_a_dialog_and_start_nothing(window, qapp, recorder):
    for t in reg.TOOLS:
        if t.kind == 'demo':
            continue
        _actions(window)[t.id].trigger()
        qapp.processEvents()
        d = window.toolDialogs[t.id]
        assert d.isVisible() and not d.isModal()
        assert d.commandLabel.text().startswith(t.command)
        d.close()
    assert window.toolRuns == {}
    assert recorder.exceptions == []


def test_documented_job_is_the_default_run(window, recorder):
    d = window.buildToolDialog('gid_compare_figures')
    assert d.commandLabel.text() == 'python tests/tools/gid_compare_figures.py --scans 11 --out docs/figures/gid_compare'
    d.preset.setCurrentIndex(1)
    assert '--peak none' in d.commandLabel.text() and d.outFolder().endswith(os.path.join('docs', 'figures', 'gid_compare'))
    d = window.buildToolDialog('burn_figures')            # documented without --out: nothing added
    assert d.commandLabel.text() == 'python tests/tools/burn_figures.py'
    d.out.setText('/elsewhere/burn')
    assert d.argv() == ['--out', '/elsewhere/burn']
    d = window.buildToolDialog('dump_tooltips')
    assert d.commandLabel.text().endswith('> docs/manual/controls.md')
    assert recorder.exceptions == []


def test_outputs_never_go_into_sample_data(window, qapp, recorder, monkeypatch):
    started = []
    monkeypatch.setattr(toolsgui.ToolRun, 'start', lambda self: started.append(self.argv))
    d = window.buildToolDialog('burn_figures')
    d.out.setText(os.path.join(reg.ROOT, 'sample_data', 'NX_school', 'figs'))
    d.runOrStop()
    assert started == [] and 'sample_data' in recorder.messages[-1]
    d = window.buildToolDialog('gid_compare_figures')
    d.preset.setCurrentIndex(2)                            # a private job
    d.out.setText(os.path.join(reg.ROOT, 'docs', 'figures', 'x'))
    d.runOrStop()
    assert started == [] and 'not run' in recorder.messages[-1]
    assert toolsgui.output_refusal(reg.by_id('gid_compare_figures'), None,
                                   os.path.join(reg.ROOT, *reg.PRIVATE_FIGURES.split('/'), 'gid_compare')) == ''
    assert toolsgui.output_refusal(reg.by_id('patch_demo'), None,
                                   os.path.join(reg.ROOT, *reg.PRIVATE_FIGURES.split('/'))) != ''
    assert recorder.exceptions == []


@pytest.mark.skipif(not os.path.isfile(NX), reason='NX school data absent')
def test_run_a_check_reports_in_messages(window, qapp, recorder):
    _actions(window)['spec_epoch'].trigger()
    d = window.toolDialogs['spec_epoch']
    d.runButton.click()
    assert d.runButton.text() == 'Stop'
    _wait(qapp, window, 'spec_epoch')
    done = [m for m in recorder.messages if 'finished' in m]
    assert done and 'What the SPEC Epoch column measures' in done[-1]
    log = done[-1].split('Full output: ')[1]
    with open(log, encoding='utf-8') as f:
        text = f.read()
    assert 'zone offset' in text and '20260923' in text
    assert d.runButton.text() == 'Run'
    assert recorder.exceptions == []


def test_run_writes_into_the_chosen_folder(window, qapp, recorder, tmp_path):
    d = window.buildToolDialog('dump_tooltips')
    d.out.setText(str(tmp_path))
    d.runOrStop()
    _wait(qapp, window, 'dump_tooltips', timeout=120)
    with open(tmp_path / 'controls.md', encoding='utf-8') as f:
        text = f.read()
    assert text.startswith('# Controls and their tooltips') and 'actionTool_regenerate' in text
    assert any('finished' in m and '1 file(s)' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_stop_and_window_close_end_a_run(window, qapp, recorder):
    d = window.buildToolDialog('monitor_noise_mc')        # a Monte Carlo of some seconds
    d.runOrStop()
    run = window.toolRuns['monitor_noise_mc']
    assert run.running() or run.proc.waitForStarted(5000)
    d.runOrStop()                                          # Stop
    _wait(qapp, window, 'monitor_noise_mc', timeout=20)
    assert any('stopped' in m for m in recorder.messages)
    d.runOrStop()
    run = window.toolRuns['monitor_noise_mc']
    run.proc.waitForStarted(5000)
    toolsgui.stop_all(window)                              # what closing the window does
    assert not run.running()
    assert recorder.exceptions == []


def test_demonstrations_open_and_close_with_the_window(window, qapp, recorder):
    for tid in ('demo_refl', 'demo_burn'):
        _actions(window)[tid].trigger()
        qapp.processEvents()
    assert len(window.toolWindows) == 2 and all(w.isVisible() for w in window.toolWindows)
    assert window.toolWindows[0].parent() is window
    assert {w.current_mode() for w in window.toolWindows} == {'refl', 'burn'}
    assert not any(isinstance(w, QtWidgets.QDialog) for w in window.toolWindows)   # the sweep does not walk them
    window.close()
    qapp.processEvents()
    assert window.toolWindows == []
    assert recorder.exceptions == []


@pytest.mark.sweep
@pytest.mark.parametrize('tool_id,seed', [('gid_compare_figures', 0), ('gid_compare_figures', 1),
                                          ('dump_tooltips', 2), ('regenerate', 3), ('spec_epoch', 4)])
def test_walk_tool_dialog(tool_id, seed, window, qapp, recorder, monkeypatch, tmp_path):
    """Random actions in a tool's dialog (Run records instead of starting,
    so that the walk cannot rewrite docs/)."""
    started = []
    monkeypatch.setattr(toolsgui.ToolRun, 'start', lambda self: started.append(self.argv))
    recorder.directory = str(tmp_path)
    raised = sweep.run_dialog_walk(window, qapp, recorder, _actions(window)[tool_id].trigger, seed, 60)
    assert raised == []
