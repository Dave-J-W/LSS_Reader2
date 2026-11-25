"""The timeline's sx line coloured by the dose each spot has received (F107;
owner, 2026-11-24, Q-TL-7), on the public NX school file. The quick tests
stand in a fixed burn scale (the burn analysis takes seconds); the slow one
analyses NX's burns 14 and 15.

NX's "set sh 0" after scan 4 splits the file into two samples: scans 1-4
have no burn of their own, so they are scaled by the nearest burn in time
(14); scans 5-15 by their own.
"""
import os

import pytest

from lss_core import timeline as T

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
needs_nx = pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
SCALE = 1.0e13            # photons/mm2 to a 5 % change (a stand-in)


@pytest.fixture
def nx(window, qapp, tmp_path):
    window.resize(1600, 1000)
    window.show()
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    window.ui.PlotWidget.setCurrentWidget(window.timelineTab)
    qapp.processEvents()
    return window


def _stand_in(monkeypatch):
    asked = []

    def scale(exp, n, beam_mm, unit='photons', **kw):
        asked.append((n, beam_mm))
        return T.DoseScale(n, SCALE, 'intensity'), 'photons/mm2'
    monkeypatch.setattr(T, 'burn_scale', scale)
    return asked


@needs_nx
def test_the_dose_colours_the_sx_line(nx, qapp, recorder, monkeypatch):
    asked = _stand_in(monkeypatch)
    tab = nx.timelineTab
    assert tab.doseCheckBox.toolTip() and not tab.view.items['dose']
    tab.doseCheckBox.setChecked(True)
    qapp.processEvents()
    tr = tab.view.dose
    lines = tab.view.items['dose']
    assert tr is not None and len(lines) == len(tr.rows) >= 10
    assert {n for n, _ in asked} <= {14, 15} and all(b[0] == 1.0 for _, b in asked)   # the width: 1 mm unless typed
    rows = {r.scan: r for r in tr.rows}
    assert rows[3].burn == 14 and rows[3].own is False                       # sample 1: the nearest burn
    assert rows[6].own is True                                                # sample 2: its own
    assert rows[6].fraction == pytest.approx(rows[6].cumulative / SCALE)
    by_scan = {l.data(0): l for l in lines}
    tip = by_scan[3].toolTip()
    assert 'S# 3 at sx' in tip and 'nearest burn in time' in tip and '% of S# 14' in tip
    colours = {l.pen().color().name() for l in lines}
    assert len(colours) > 1                                                   # the dose grows along the file
    assert nx.prefs['timeline_dose'] is True and 'Scale: S# ' in tab.doseCheckBox.toolTip()
    tab.doseCheckBox.setChecked(False)
    qapp.processEvents()
    assert tab.view.dose is None and not tab.view.items['dose']
    assert recorder.exceptions == []


@needs_nx
def test_the_track_is_kept_while_the_file_is_unchanged(nx, qapp, recorder, monkeypatch):
    asked = _stand_in(monkeypatch)
    tab = nx.timelineTab
    tab.doseCheckBox.setChecked(True)
    qapp.processEvents()
    n = len(asked)
    tab.doseCheckBox.setChecked(False)
    tab.doseCheckBox.setChecked(True)                     # from the cache: no burn analysed again
    qapp.processEvents()
    assert len(asked) == n and tab.view.items['dose']
    assert recorder.exceptions == []


@pytest.mark.slow
@needs_nx
def test_nx_burns_set_the_scale(nx, qapp, recorder):
    """The real analysis on the dose axis (beam 1 mm wide, the height from
    NX's sample-height scans): the 95 % confident dose to a 5 % change of the
    limit's quantities (intensity, width). Measured 2026-11-25: S# 14 1.26e12
    photons/mm² (intensity), S# 15 1.87e12 (width); not lower bounds."""
    tab = nx.timelineTab
    tab.doseCheckBox.setChecked(True)
    qapp.processEvents()
    tr = tab.view.dose
    scales = {n: s for n, s in tr.scales.items() if s is not None}
    assert set(scales) <= {14, 15} and scales
    for s in scales.values():
        assert not s.lower_bound and s.quantity in ('intensity', 'fwhm') and 1e11 < s.dose < 1e14
    assert tr.unit == 'photons/mm2' and all(r.fraction is not None for r in tr.rows)
    assert recorder.exceptions == []
