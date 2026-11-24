"""The sample timeline tab in the main window (F83 phase 1c; owner,
2026-11-24: "Main window tab"): a view of lss_core.timeline. On the NX
school file it draws what tests/test_timeline.py measures: 15 scan bars,
the "set sh 0" line, three re-references, four aborts, the sx steps and
the four sample-height scans."""
import os

import pytest
from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QWheelEvent

import timelineview

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
needs_nx = pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')


def _show(w, qapp):
    w.ui.PlotWidget.setCurrentWidget(w.timelineTab)
    qapp.processEvents()
    return w.timelineTab


@pytest.fixture
def nx(window, qapp, tmp_path):
    window.resize(1600, 1000)
    window.show()
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    qapp.processEvents()
    return window


def test_the_tab_is_last_and_says_what_to_do_before_a_file(window, qapp, recorder):
    """Owner, 2026-11-24: "Put the timeline tab in main window, furthest to the right"."""
    pw = window.ui.PlotWidget
    assert pw.tabText(pw.count() - 1) == 'Timeline' and pw.widget(pw.count() - 1) is window.timelineTab
    tab = _show(window, qapp)
    assert 'Open a SPEC file' in tab.infoLabel.text()
    assert tab.fitButton.toolTip() and pw.tabToolTip(pw.count() - 1)
    assert recorder.exceptions == []


@needs_nx
def test_the_nx_timeline_is_drawn_when_the_tab_is_shown(nx, qapp, recorder):
    assert nx.timelineKey is None                               # nothing is read until the tab is shown
    tab = _show(nx, qapp)
    v = tab.view
    assert nx.timelineKey is not None
    assert sorted(v.items['scans']) == list(range(1, 16))
    assert sorted(v.items['heights']) == [4, 5, 10, 13]
    assert 'no reflected beam' in v.items['heights'][4].toolTip()
    assert 'µm' in v.items['heights'][10].toolTip() and 'p 3.' in v.items['heights'][10].toolTip()
    tips = [i.toolTip() for i in v.items['events']]
    assert sum('new sample?' in t for t in tips) == 1
    assert sum('re-referenced by' in t for t in tips) == 3
    assert sum('aborted' in t for t in tips) == 4
    assert len(v.items['steps']) == 5 and '18 → 16' in v.items['steps'][1].toolTip()
    assert len(v.items['gaps']) == 1
    assert 'scans' in tab.infoLabel.text() and 'new sample?' in tab.infoLabel.text()
    assert '10:37:39' in [t for t in tips if 'new sample?' in t][0]      # the file's local clock
    bar = v.items['scans'][6]
    assert 'reflectivity' in bar.toolTip()
    assert bar.brush().color().name() == timelineview.KIND_COLOURS['reflectivity']
    assert v.items['scans'][4].brush().color().alpha() < 255                # aborted: paler
    key = nx.timelineKey
    nx.ui.PlotWidget.setCurrentWidget(nx.ui.specPlotTab)
    _show(nx, qapp)
    assert nx.timelineKey == key                                 # the file did not change: not read again
    assert recorder.exceptions == []


@needs_nx
def test_zoom_pan_and_fit(nx, qapp, recorder):
    v = _show(nx, qapp).view
    full = v.visible_span()
    assert full == pytest.approx(1.04 * v.span, rel=1e-3)
    centre = v.viewport().rect().center()
    ev = QWheelEvent(QPointF(centre), QPointF(v.mapToGlobal(centre)), QPoint(0, 0), QPoint(0, 240),
                     Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    v.wheelEvent(ev)
    assert v.visible_span() == pytest.approx(full / 1.25 ** 2, rel=1e-3)
    assert v.transform().m22() == 1.0                             # the time axis only
    v.fit_all()
    assert v.visible_span() == pytest.approx(full, rel=1e-3)
    v.viewport().repaint()                                       # the axis draws (drawForeground)
    assert recorder.exceptions == []


@needs_nx
def test_a_click_on_a_scan_selects_it(nx, qapp, recorder):
    v = _show(nx, qapp).view
    bar = v.items['scans'][10]
    v.centerOn(bar)
    qapp.processEvents()
    v.scanClicked.emit(10)
    qapp.processEvents()
    assert list(nx.selectedScanNums) == [10]
    assert nx.specHeightFit is not None and nx.specHeightFit.ok       # its sh fit drawn on SpecPlot
    nx.timelineScanClicked(99)                                         # not in the file: said, nothing raised
    assert any('not in the scan list' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_a_file_without_times_says_so(loaded, qapp, recorder):
    """The synthetic files have one #D for every scan and no Epoch: spans
    still get times, so the timeline draws; it never raises."""
    tab = _show(loaded, qapp)
    assert recorder.exceptions == []
    assert tab.infoLabel.text()


def test_tick_steps_are_clock_friendly():
    assert timelineview.tick_step(60) == 10
    assert timelineview.tick_step(3600) == 600
    assert timelineview.tick_step(7 * 3600) == 3600
    assert timelineview.tick_step(10 * 86400) >= 86400


@needs_nx
def test_the_sample_height_scans_are_drawn_as_thumbnails(nx, qapp, recorder):
    """Each sh scan small: its Pilatus/Monc points and, when fitted, the
    super-Gaussian; a fixed size in pixels at every zoom; a click opens it."""
    v = _show(nx, qapp).view
    th = v.items['heights']
    assert all(isinstance(t, timelineview.HeightThumb) for t in th.values())
    assert len(th[10].points) == len(nx.timelineTab.view.timeline.heights[2].x) and th[10].fit and th[10].ok
    assert th[4].points and not th[4].fit and not th[4].ok          # no beam: the points, no fit, grey
    r = th[10].mapRectToScene(th[10].boundingRect())
    v.zoom(4.0)
    assert th[10].boundingRect().width() == timelineview.THUMB_W    # ignores the zoom
    assert th[10].data(0) == ('scan', 10)
    assert recorder.exceptions == []



@needs_nx
def test_a_new_sample_answer_is_kept_in_the_workbook_and_drawn(nx, qapp, recorder):
    v = _show(nx, qapp).view
    (event, line, label), = v.items['set_zero']
    assert label.text() == 'new sample?'
    nx.timelineAnswer(event.t, event.after_scan, 'same sample')
    (event, line, label), = nx.timelineTab.view.items['set_zero']
    assert label.text() == 'same sample' and 'Answered: same sample' in line.toolTip()
    nx.timelineAnswer(event.t, event.after_scan, 'new sample')
    (event, line, label), = nx.timelineTab.view.items['set_zero']
    assert label.text() == 'new sample'
    from lss_core import workbook
    rows = workbook.Workbook(nx.workbookPath()).results('note')
    assert [r['label'] for r in rows] == ['same sample', 'new sample'] and rows[0]['scans'] == '4'
    assert recorder.exceptions == []


@needs_nx
def test_a_note_is_added_at_a_time(nx, qapp, recorder, monkeypatch):
    from PyQt5 import QtWidgets
    monkeypatch.setattr(QtWidgets.QInputDialog, 'getMultiLineText',
                        lambda *a, **k: ('Trough cleaned\nwith ethanol', True))
    v = _show(nx, qapp).view
    t = v.items and nx.timelineTab.view.timeline.spans[5].t0 + 10
    nx.timelineAddNote(t)
    (box,) = nx.timelineTab.view.items['notes']
    assert box.text() == 'Trough cleaned' and 'with ethanol' in box.toolTip()
    monkeypatch.setattr(QtWidgets.QInputDialog, 'getMultiLineText', lambda *a, **k: ('', False))
    nx.timelineAddNote(t)                                        # cancelled: nothing added
    assert len(nx.timelineTab.view.items['notes']) == 1
    assert recorder.exceptions == []


@needs_nx
def test_the_right_click_menu(nx, qapp, recorder):
    from PyQt5.QtGui import QContextMenuEvent
    v = _show(nx, qapp).view
    (event, line, label), = v.items['set_zero']
    pos = v.mapFromScene(label.scenePos()) + QPoint(3, 3)
    v.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, pos, v.mapToGlobal(pos)))
    assert [a.text() for a in v.contextMenu.actions() if a.text()] == ['A new sample', 'The same sample',
                                                                         'Add a note here…']
    got = []
    v.answerGiven.connect(lambda t, n, a: got.append((n, a)))
    v.contextMenu.actions()[1].trigger()
    assert got == [(4, 'same sample')]
    empty = v.mapFromScene(v.items['scans'][8].rect().center()) + QPoint(0, 200)
    v.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, empty, v.mapToGlobal(empty)))
    assert [a.text() for a in v.contextMenu.actions()] == ['Add a note here…']
    assert recorder.exceptions == []
