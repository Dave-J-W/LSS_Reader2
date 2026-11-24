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
    # the patch's own GIDError message since the test-speed session's #29, else gidPatch's safety net
    assert any('no GID levels' in m or 'nothing to patch' in m for m in recorder.messages)


def test_worksheet_patch_on_frames_without_gid_levels_says_so(loaded, qapp, dataset, recorder):
    """The worksheet's own Patch button reached the same ValueError as GID
    Patch on reflectivity frames (the crash sweep, 2026-11-24): now the same
    message."""
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.gidWorksheetPatch()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert any('no GID levels' in m or 'nothing to patch' in m for m in recorder.messages)


@pytest.mark.parametrize('pinhole', [True, False])
def test_a_refused_gid_patch_leaves_the_frames_shown(loaded, qapp, dataset, recorder, pinhole):
    """Found by the crash sweep's random walks (2026-11-24, after the
    Timeline tab changed them): GID Patch on frames that hold no GID level
    is refused ("has no detector column"), but the GID display stayed on,
    so the next redraw (Log Int, Axes, the view) raised AttributeError
    (pilGIDXAxs, pilGIDxlabel) or IndexError (gid.products) in
    pilGIDPlot. The frames come back instead."""
    sweep.state_pilatus_two_scans_all_frames(loaded, qapp, dataset)
    loaded.seriesWhere = {}                      # as if the kind were unknown: the button is enabled
    loaded.updateToolAvailability()
    loaded.ui.pilSpecCheckBox.setChecked(pinhole)
    qapp.processEvents()
    loaded.gidPatchPushButton.click()
    qapp.processEvents()
    assert loaded.pilGIDshow == 0
    assert loaded.pilMode in ('movie', 'tiles', 'sum')         # the frames drawn again
    loaded.ui.pilLogIntCheckBox.toggle()
    qapp.processEvents()
    loaded.ui.pilAxesComboBox.setCurrentIndex((loaded.ui.pilAxesComboBox.currentIndex() + 1) % 3)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert recorder.messages



def test_a_gid_map_without_a_common_qxy_range_is_refused_in_q_and_drawn_in_angles(loaded, qapp, dataset, recorder):
    """The crash sweep's second find (2026-11-24): the legacy GID patch of
    a reflectivity frame gives a map whose rows share no Qxy range, so its
    Q grid is empty and gid.products raised IndexError; every later redraw
    raised again. In Q it is now refused with the reason and the frames come
    back; in Angles the map is drawn as before."""
    import dataclasses
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.seriesWhere = {}
    loaded.updateToolAvailability()
    loaded.gidParams = dataclasses.replace(loaded.gidParams, pinhole=False)
    loaded.ui.pilAxesComboBox.setCurrentIndex(loaded.ui.pilAxesComboBox.findText('Q'))
    qapp.processEvents()
    loaded.gidPatchPushButton.click()
    qapp.processEvents()
    assert loaded.pilGIDshow == 0
    assert any('no Qxy range common to its rows' in m for m in recorder.messages)
    loaded.ui.pilLogIntCheckBox.toggle()
    qapp.processEvents()
    loaded.ui.pilAxesComboBox.setCurrentIndex(loaded.ui.pilAxesComboBox.findText('Angles'))
    qapp.processEvents()
    loaded.gidPatchPushButton.click()
    qapp.processEvents()
    assert loaded.pilGIDshow == 1
    assert recorder.exceptions == []


def test_a_gid_map_refused_by_lss_core_is_said_too(loaded, qapp, dataset, recorder, monkeypatch):
    """Main plans a guard in gid.products (2026-11-24): a GIDError naming the
    cause instead of the IndexError. The window refuses that map the same
    way: frames back, a message, nothing raised."""
    import dataclasses
    from lss_core import gid as gidmod

    def refuse(*a, **k):
        raise gidmod.GIDError('no Qxy range is shared by every row')
    monkeypatch.setattr(gidmod, 'products', refuse)
    sweep.state_pilatus_one_frame(loaded, qapp, dataset)
    loaded.seriesWhere = {}
    loaded.updateToolAvailability()
    loaded.gidParams = dataclasses.replace(loaded.gidParams, pinhole=False)
    loaded.ui.pilAxesComboBox.setCurrentIndex(loaded.ui.pilAxesComboBox.findText('Angles'))
    qapp.processEvents()
    loaded.gidPatchPushButton.click()
    qapp.processEvents()
    assert loaded.pilGIDshow == 0
    assert any('GID Patch' in m for m in recorder.messages)
    assert recorder.exceptions == []

