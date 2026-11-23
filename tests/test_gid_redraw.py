"""The GID map regridded to Q once per map, not on every redraw (G1 in
docs/gui/image_display.md, 2026-11-23).

NX school scans 11 + 12, Q axes: a redraw (Log Int, colour map) took
1.0 s (legacy patch) to 1.4 s (pinhole patch), 70-77 % of it griddata;
now 0.30-0.35 s. The map's content is the key: only a different map is
regridded, also when a patch or a live remake gives it in new arrays."""
import os

import numpy as np
import pytest

import sweep
from lss_core import gid as gm
from lss_core.gid import GIDParams

SPEC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'sample_data', 'NX_school', '2026sep', '20260923')

pytestmark = [pytest.mark.gui, pytest.mark.slow,
              pytest.mark.skipif(not os.path.exists(SPEC), reason='NX_school sample data not present')]


def _patch(window, qapp):
    i = window.ui.gidComboBox.findText('GID Patch')
    window.ui.gidComboBox.setCurrentIndex(i)
    window.ui.gidComboBox.activated.emit(i)
    qapp.processEvents()


def test_a_redraw_does_not_regrid_the_map(window, qapp, recorder, tmp_path, monkeypatch):
    window.gidParams = GIDParams(pinhole=False)
    window.openSpecFile(fname=SPEC)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [10, 11])
    sweep._select_images(window, qapp)
    window.ui.pilAxesComboBox.setCurrentIndex(window.ui.pilAxesComboBox.findText('Q'))
    qapp.processEvents()
    calls = []
    real = gm.griddata
    import traceback

    def counted(*a, **k):                                   # regriddings made by the window, not by this test
        if any(f.name == 'gidProducts' for f in traceback.extract_stack(limit=8)):
            calls.append(1)
        return real(*a, **k)
    monkeypatch.setattr(gm, 'griddata', counted)
    _patch(window, qapp)
    assert len(calls) == 2                                  # the map and its errors, once
    window.ui.pilLogIntCheckBox.setChecked(not window.ui.pilLogIntCheckBox.isChecked())
    c = window.ui.pilCMapComboBox
    c.setCurrentIndex((c.currentIndex() + 1) % c.count())
    window.pilGIDPlot()
    qapp.processEvents()
    assert len(calls) == 2                                  # redraws use the kept regridding
    kept = window.gidProductsKept[1]
    fresh = gm.products(window.pilGIDXAxs, window.pilGIDYAxs, window.pilGIDData, window.pilGIDDataErr, 'Q',
                        window.truealpha[0], window.wavelength[0])
    for k in ('x', 'y', 'data', 'err', 'h', 'v'):
        assert np.array_equal(kept[k], fresh[k], equal_nan=True), k
    assert not kept['data'].flags.writeable and window.pilGIDData_Q is kept['data']
    _patch(window, qapp)                                    # the same patch again: the same map, kept
    assert len(calls) == 2 and window.gidProductsKept[1] is kept
    window.gidParams = GIDParams(pinhole=False, row_min=40)  # a different map: regridded once
    _patch(window, qapp)
    assert len(calls) == 4 and window.gidProductsKept[1] is not kept
    assert recorder.exceptions == []
