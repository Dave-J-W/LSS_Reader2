"""The timeline's reduced lane in the window (F83 phase 1d): the workbook's
results drawn at their scans' times, placeholders for series not reduced, a
click opens the result (a reflectivity on the Compare tab), and saving a new
result redraws the lane. NX school file, with results put in its workbook
directly (fast; the reductions themselves are tested elsewhere)."""
import os

import numpy as np
import pytest

from lss_core import workbook

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
needs_nx = pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
REF = np.column_stack([np.linspace(0.02, 0.4, 30), np.logspace(0, -6, 30), np.logspace(-2, -8, 30)])


@pytest.fixture
def nx(window, qapp, tmp_path):
    window.resize(1600, 1000)
    window.show()
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    qapp.processEvents()
    return window


def _save(w, kind='reflectivity', scans=(6, 7, 8, 9), label='R'):
    wb = w.openWorkbook()
    rid = wb.add_result(kind, scans=list(scans), data=REF, columns=['Qz', 'R', 'dR'], label=label)
    w.saveWorkbook(wb)
    return rid


def _show(w, qapp):
    w.ui.PlotWidget.setCurrentWidget(w.timelineTab)
    qapp.processEvents()
    return w.timelineTab.view


@needs_nx
def test_placeholders_then_a_saved_result(nx, qapp, recorder):
    view = _show(nx, qapp)
    assert [t.item.placeholder for t in view.items['reduced']] == ['not reduced'] * 5
    assert not os.path.exists(nx.workbookPath())                   # not created to look
    rid = _save(nx)
    nx.ui.PlotWidget.setCurrentIndex(0)
    view = _show(nx, qapp)                                         # the workbook changed: redrawn
    thumbs = {t.item.rid or t.item.placeholder + str(t.item.scans): t for t in view.items['reduced']}
    assert rid in thumbs and thumbs[rid].points                    # drawn from its data (log R against Qz)
    assert 'not reduced[6, 7, 8, 9]' not in thumbs and 'not reduced[11, 12]' in thumbs
    tip = thumbs[rid].toolTip()
    assert rid in tip and 'S# 6, 7, 8, 9' in tip and 'Compare tab' in tip
    assert recorder.exceptions == []


@needs_nx
def test_a_click_opens_the_result(nx, qapp, recorder):
    rid = _save(nx)
    gid = _save(nx, 'gid map', (11, 12), '')
    view = _show(nx, qapp)
    view.resultClicked.emit(rid)                                   # a reflectivity: ticked on the Compare tab
    qapp.processEvents()
    assert nx.ui.PlotWidget.currentWidget() is nx.compareTab and rid in nx.compareTab.ticked_ids()
    _show(nx, qapp)
    view.resultClicked.emit(gid)                                   # another kind: its scans selected
    qapp.processEvents()
    assert sorted(nx.selectedScanNums) == [11, 12]
    assert recorder.exceptions == []


def test_thumbnails_draw_the_right_columns(qapp):
    """Fluorescence rows are (frame, Qz, E, I, dI[, I_xeray, dI_xeray]): the
    thumbnail draws I against Qz, not Qz against frame; a GID map (2D) draws
    no curve (2026-11-26)."""
    from lss_core.timeline import Reduced
    from timelineview import ResultThumb
    qz = np.linspace(0.01, 0.04, 9)
    inten = np.exp(-((qz - 0.02) / 0.005) ** 2)                 # one peak, nearest the fourth point
    rows = np.column_stack([np.arange(1, 10), qz, np.full(9, 10.0), inten, 0.01 * inten, inten, 0.01 * inten])
    flu = ResultThumb(Reduced('F0001', 'fluorescence', '', 1, [3], 0.0, 1.0, data=rows))
    ys = [p[1] for p in flu.points]
    assert len(flu.points) == 9 and int(np.argmin(ys)) == 3                     # the peak is drawn highest
    gmap = ResultThumb(Reduced('G0001', 'gid map', '', 1, [11], 0.0, 1.0, data=np.random.default_rng(1).random((5, 6))))
    assert gmap.points == []
