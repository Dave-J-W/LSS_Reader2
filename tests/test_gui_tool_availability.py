"""Tools that do not fit the selected series kind are greyed out, with a
tooltip saying what is needed (owner, 2026-11-23, Q-UI-A10). Only for a known
kind (reflectivity, GID, burn, GISAXS); unknown or mixed selections leave
every tool enabled, so a wrong guess never blocks an action."""
import pytest

import sweep

pytestmark = pytest.mark.gui


def _enabled(w):
    return {name: getattr(w.ui, name, None).isEnabled() if hasattr(w.ui, name) else getattr(w, name).isEnabled()
            for name in w.TOOL_KINDS}


def test_a_reflectivity_series_greys_out_gid_and_burn(loaded, qapp, dataset, recorder):
    sweep.state_pilatus_two_scans_all_frames(loaded, qapp, dataset)
    assert loaded.selectionKind() == 'reflectivity'
    assert _enabled(loaded) == {'pilRefPushButton': True, 'pilRefPatchPushButton': True,
                                'gidPatchPushButton': False, 'gidComboBox': False, 'pilBurnPushButton': False}
    assert 'this needs a GID series' in loaded.gidPatchPushButton.toolTip()
    assert recorder.exceptions == []


def test_other_selections_leave_every_tool_enabled(loaded, qapp, dataset, recorder):
    for rows in ([2], [3], [0, 2]):                 # a fluorescence scan, a motor scan, a mixed selection
        sweep._select_scans(loaded, qapp, rows)
        assert loaded.selectionKind() not in ('reflectivity', 'gid', 'burn', 'gisaxs'), rows
        assert all(_enabled(loaded).values()), rows
    sweep._select_scans(loaded, qapp, [0, 1])       # back to reflectivity, then the tooltips are restored
    sweep._select_scans(loaded, qapp, [3])
    assert 'Greyed out' not in loaded.gidPatchPushButton.toolTip()
    assert recorder.exceptions == []
