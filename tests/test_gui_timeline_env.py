"""The timeline's Environment lane in the window (F83 phase 2): the column
chosen in the toolbar, an environment-like column chosen by itself when the
file has one, the choice remembered."""
import os

import pytest

from test_timeline_env import env_spec

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
needs_nx = pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')


def _open(w, qapp, spec, tmp_path):
    w.resize(1600, 1000)
    w.show()
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    w.ui.PlotWidget.setCurrentWidget(w.timelineTab)
    qapp.processEvents()
    return w.timelineTab


def test_an_environment_column_is_drawn_by_itself(window, qapp, recorder, tmp_path):
    tab = _open(window, qapp, env_spec(tmp_path), tmp_path)
    box = tab.envComboBox
    assert box.currentData() == 'Barrier' and box.itemData(0) == ''               # the first environment-like name
    assert len(tab.view.items['env']) == 2                                       # one line per scan
    assert 'Barrier cm²' in tab.view.items['env'][0].toolTip()
    box.setCurrentIndex(box.findData('SurfPress'))
    qapp.processEvents()
    assert tab.view.env.name == 'SurfPress' and window.prefs['timeline_env'] == 'SurfPress'
    assert 'mN/m, 20 to 31' in tab.view.items['env'][0].toolTip()
    box.setCurrentIndex(0)                                                       # none
    qapp.processEvents()
    assert tab.view.env is None and not tab.view.items['env']
    assert recorder.exceptions == []


@needs_nx
def test_nx_offers_its_columns_and_draws_monc(window, qapp, recorder, tmp_path):
    tab = _open(window, qapp, NX, tmp_path)
    box = tab.envComboBox
    assert box.currentData() == ''                                               # NX: nothing environment-like
    box.setCurrentIndex(box.findData('Monc'))
    qapp.processEvents()
    lines = tab.view.items['env']
    assert len(lines) == len(tab.view.timeline.spans) and all('Monc' in l.toolTip() for l in lines)
    assert recorder.exceptions == []
