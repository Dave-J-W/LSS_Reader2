"""The Tools window and menu (lss_toolbox.window, lss_toolbox.menu), tested
on their own: a bare QMainWindow stands in for the reader, so nothing here
depends on MainWindow (the reader's hook is one call, tested in
test_toolbox_reader.py). Runs go to a temporary folder.
"""
import os
import shutil
import time

import pytest

from lss_toolbox import ROOT, catalog, runner

pytestmark = pytest.mark.gui


@pytest.fixture(autouse=True)
def _runs_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv('LSS_READER_TOOLS_DIR', str(tmp_path / 'runs'))


def _wait(qapp, cond, timeout=120.0):
    from PyQt5 import QtCore
    end = time.time() + timeout
    while not cond() and time.time() < end:
        qapp.processEvents(QtCore.QEventLoop.AllEvents, 50)
    return cond()


@pytest.fixture
def host_calls():
    return {'open': [], 'notify': []}


@pytest.fixture
def tools(qapp, recorder, host_calls):
    from lss_toolbox import window
    host = window.Host(spec_file=lambda: os.path.join(ROOT, catalog.NX), open_spec=host_calls['open'].append,
                       notify=host_calls['notify'].append)
    w = window.ToolsWindow(host=host)
    assert w.wait_parsers(120)
    yield w
    for p in w.pages.values():
        if p.proc is not None:
            p.proc.kill()
            p.proc.waitForFinished(5000)
            qapp.processEvents()
    w.close()
    window.wait_workers()
    w.deleteLater()
    qapp.processEvents()


def test_menu_on_a_bare_main_window(qapp, recorder):
    from PyQt5 import QtWidgets
    from lss_toolbox import menu
    mw = QtWidgets.QMainWindow()
    mw.menuBar().addMenu('File')
    mw.menuBar().addMenu('&Help')
    m = menu.install(mw)
    titles = [a.text() for a in mw.menuBar().actions()]
    assert titles == ['File', 'Tools', '&Help']
    assert set(m.toolActions) == {'all'} | {t.id for t in catalog.TOOLS}
    subs = [a.menu().title() for a in m.actions() if a.menu()]
    assert subs == [name for cat, name in catalog.CATEGORIES if catalog.in_category(cat)]
    m.toolActions['pinhole_beam_profile'].trigger()
    w = mw.toolsWindow
    assert w is not None and w.stack.currentWidget() is w.pages['pinhole_beam_profile']
    m.toolActions['all'].trigger()
    assert w.stack.currentWidget() is w.overview and 'Burn tests' in w.overview.toPlainText()
    assert mw.toolsWindow is w                  # one window, kept
    w.wait_parsers(120)
    w.close()
    mw.close()
    from lss_toolbox import window
    window.wait_workers()
    assert recorder.exceptions == []


def test_every_page_builds_from_its_script(tools, recorder):
    """Each page's form is the script's parser; each variation changes the
    command as the catalogue says."""
    from lss_toolbox import render, window
    for t in catalog.TOOLS:
        p = tools.show_item(t.id)
        if not t.runnable:
            assert not p.settingsBox.isVisibleTo(p) and p.fileList.count() > 0      # committed figures shown
            continue
        spec = runner.effective(window.cached_parser(t.script), t.subcommand)
        assert len(p.fields) == len(spec.get('actions', [])), t.id
        assert p.commandEdit.text().startswith('python %s' % t.script), t.id
        for i, v in enumerate(t.variations, start=1):
            p.variationCombo.setCurrentIndex(i)
            cmd = p.commandEdit.text()
            for key, value in v.args.items():
                if value is True:
                    assert ' %s' % key in cmd, (t.id, v.label, key)
                elif isinstance(value, str) and value and runner.OUT not in value and key.startswith('-'):
                    a = runner.action_for(spec, key)
                    if value != runner.default_text(a):
                        assert ' %s %s' % (key, value.split()[0]) in cmd or ' %s %r' % (key, value) in cmd, \
                            (t.id, v.label, cmd)
        p.variationCombo.setCurrentIndex(0)
        assert p.at_defaults(), t.id
        expected = render.command(t).replace("'{out}'", '').replace('{out}', '')
        assert p.commandEdit.text().split()[:2] == expected.split()[:2]
    assert recorder.exceptions == []


def test_the_documented_controls_are_the_window_s(tools, recorder):
    """docs/TOOLS.md lists the Tools window's controls from texts.CONTROLS;
    each is a control of the window or of a page, with that tooltip."""
    from lss_toolbox import texts
    p = tools.show_item('pinhole_figures')
    for name, label, tip in texts.CONTROLS:
        w = getattr(p, name, None) or getattr(tools, name, None)
        assert w is not None, name
        assert w.toolTip().startswith(tip), name
    assert recorder.exceptions == []


def test_a_text_tool_runs_from_its_page(tools, qapp, recorder, host_calls, tmp_path):
    p = tools.show_item('foil_fit_from_joins')
    p.variationCombo.setCurrentIndex([v.label for v in p.item.variations].index('Strict cuts') + 1)
    assert '--monc-tol 0.01 --chi2-max 5 --floor 0' in p.commandEdit.text()
    assert not p.repoCheck.isEnabled()                 # no committed products
    p.run()
    assert _wait(qapp, lambda: p.proc is None, 60)
    assert '337 with Monc/Monp unchanged' in p.log.toPlainText()
    run_dir = runner.past_runs('foil_fit_from_joins')[0]
    assert runner.read_record(run_dir)['exit_code'] == 0
    assert p.runCombo.currentData() == run_dir
    assert [p.fileList.item(i).text() for i in range(p.fileList.count())] == [runner.STDOUT]
    assert 'Foil thicknesses' in host_calls['notify'][-1]
    assert recorder.exceptions == []


def test_compare_with_the_committed_figures(tools, qapp, recorder):
    """A run folder holding one committed figure changed in a few pixels and
    one unchanged: the page finds which is which, and where."""
    from PyQt5 import QtGui
    item = catalog.get('gid_stray_light')
    run = runner.new_run_dir(item.id)
    committed = runner.product_files(item, 'committed')
    shutil.copy(committed['bands_11_12.png'], os.path.join(run, 'bands_11_12.png'))
    img = QtGui.QImage(committed['frames_11_12.png'])
    for x in range(10, 14):
        img.setPixel(x, 20, 0xFF00FF)
    img.save(os.path.join(run, 'frames_11_12.png'))
    shutil.copy(committed['bands_11_12.png'], os.path.join(run, 'extra.png'))
    p = tools.show_item(item.id)
    p.refresh_runs(select=run)
    assert p.compareCombo.currentData() == 'committed'
    got = p.compare_all()
    assert got['same'] == ['bands_11_12.png'] and got['differ'] == ['frames_11_12.png'] and got['new'] == ['extra.png']
    assert '1 same, 1 differ, 1 new' in p.compareSummary.text()
    rows = [p.fileList.item(i).text() for i in range(p.fileList.count())]
    assert '= bands_11_12.png' in rows and '≠ frames_11_12.png' in rows and '+ extra.png' in rows
    p.fileList.setCurrentRow(rows.index('≠ frames_11_12.png'))
    p.diffCheck.setChecked(True)
    assert p.viewB.image is not None and 'differ' in p.viewB.label.toolTip()
    assert recorder.exceptions == []


@pytest.mark.parametrize('item_id', ['burn_figures'])
def test_a_figure_tool_reproduces_its_committed_figures(tools, qapp, recorder, item_id):
    """Run with the defaults, compare: the burn-trend figures come out the
    same, pixel for pixel, as the committed ones (measured 2026-11-23)."""
    p = tools.show_item(item_id)
    assert p.at_defaults() and p.repoCheck.isEnabled()
    p.run()
    assert _wait(qapp, lambda: p.proc is None, 180)
    assert runner.read_record(runner.past_runs(item_id)[0])['exit_code'] == 0
    got = p.compare_all()
    assert got['differ'] == [] and len(got['same']) == 4
    p.variationCombo.setCurrentIndex(1)
    assert not p.repoCheck.isEnabled()                # committed products are the defaults' products
    assert recorder.exceptions == []


def test_a_synthetic_data_set_opens_in_the_host(tools, qapp, recorder, host_calls):
    p = tools.show_item('synthetic_dataset')
    assert p.runButton.text() == 'Make and open'
    p.variationCombo.setCurrentIndex([v.label for v in p.item.variations].index('Burn series') + 1)
    assert '--kind burn' in p.commandEdit.text()
    p.run()
    assert _wait(qapp, lambda: p.proc is None, 60)
    assert len(host_calls['open']) == 1 and os.path.isfile(host_calls['open'][0])
    assert p.openSpecButton.isEnabled()
    p.openSpecButton.click()
    assert host_calls['open'][1] == host_calls['open'][0]
    assert recorder.exceptions == []


def test_a_demonstrator_window_starts_and_stops(tools, qapp, recorder):
    p = tools.show_item('patch_demo_burn')
    assert p.runButton.text() == 'Open window' and not p.resultsBox.isVisible()
    p.variationCombo.setCurrentIndex(1)
    assert p.commandEdit.text() == 'python tests/tools/patch_demo.py --mode burn --set change=fade'
    p.run()
    assert _wait(qapp, lambda: p.proc is not None and p.proc.state() == p.proc.Running, 30)
    p.stop()
    assert _wait(qapp, lambda: p.proc is None, 30)
    assert 'Finished' in p.log.toPlainText()
    assert recorder.exceptions == []


def test_the_open_spec_file_fills_the_spec_option(tools, recorder):
    p = tools.show_item('gid_stray_light')
    assert p.specButton.isVisibleTo(p)
    p.fields['--spec'].setText('')
    p.specButton.click()
    assert p.fields['--spec'].text().endswith(catalog.NX)
    p = tools.show_item('monitor_ratio')
    p.freeEdit.setText('')
    p.specButton.click()
    assert p.freeEdit.text().endswith(catalog.NX)
    assert recorder.exceptions == []


def test_staleness_is_shown(tools, qapp, recorder):
    p = tools.show_item('gui_map')
    assert _wait(qapp, lambda: 'Checking' not in p.statusLabel.text(), 60)
    assert 'Committed products' in p.statusLabel.text()
    assert 'Depends on' in p.statusLabel.toolTip()
    assert recorder.exceptions == []


def test_without_the_repository_nothing_runs(qapp, recorder, monkeypatch):
    from lss_toolbox import window
    monkeypatch.setattr(window, 'available', lambda: (False, 'no tools here'))
    w = window.ToolsWindow()
    p = w.show_item('pinhole_figures')
    assert not p.runButton.isEnabled() and p.runButton.toolTip() == 'no tools here'
    assert w.statusBar().currentMessage() == 'no tools here'
    w.close()
    window.wait_workers()
    assert recorder.exceptions == []
