"""Tools that do not fit the selected series kind are greyed out, with a
tooltip saying what is needed (owner, 2026-11-23, Q-UI-A10). Only for a known
kind (reflectivity, GID, burn, GISAXS); unknown or mixed selections leave
every tool enabled, so a wrong guess never blocks an action."""
import os

import pytest

import sweep

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')

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


def test_gid_patch_with_nothing_selected_says_so(window, qapp, recorder):
    """Found by the crash sweep (2026-11-24): the GID Patch button, clicked
    with nothing loaded, raised IndexError in pinhole.shared_edges."""
    window.gidPatchPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert any('GID scans and their frames first' in m for m in recorder.messages)


@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school sample data not present')
def test_gid_patch_with_frames_selected_runs(window, qapp, recorder, tmp_path):
    """The guard above read the selected frames with 'x or []': once frames are
    selected they are a numpy array, whose truth value raised ValueError, so GID
    Patch never ran (found by the crash sweep's GID walk, 2026-11-24)."""
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [11])                      # scan 12: 4 GID frames
    sweep._select_images(window, qapp)
    window.flushPendingSelection()
    window.gidPatchPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert window.pilGIDshow == 1


def test_gid_patch_on_frames_without_gid_levels_says_so(loaded, qapp, dataset, recorder):
    """Found by the crash sweep (2026-11-24): GID Patch on reflectivity frames
    raised ValueError (an empty array tested for truth in the GID patch). The
    button now says what is needed; the detail goes to the log."""
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.seriesWhere = {}                      # as if the kind were unknown: the button is enabled
    loaded.updateToolAvailability()
    loaded.gidPatchPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert any('no GID levels' in m for m in recorder.messages)


def test_worksheet_patch_on_frames_without_gid_levels_says_so(loaded, qapp, dataset, recorder):
    """The worksheet's own Patch button reached the same ValueError as GID
    Patch on reflectivity frames (the crash sweep, 2026-11-24): now the same
    message."""
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.gidWorksheetPatch()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert any('no GID levels' in m for m in recorder.messages)
