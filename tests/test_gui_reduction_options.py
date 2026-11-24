"""The Reduction options page and Ctrl+click (F86; owner, 2026-11-23, Q13 and
its follow-up "one button, switch picks"): legacy paths stay; the page picks
legacy or new for each; Ctrl+click on the action runs the other once and
says so in the Messages pane, never a dialog."""
import pytest

import sweep

pytestmark = pytest.mark.gui

SWITCHES = {'prefSumAllLegacyCheckBox': 'sum_all_legacy_average', 'prefGisaxsRawCheckBox': 'gisaxs_raw_counts',
            'prefRepeatsLegacyCheckBox': 'repeats_legacy_average',
            'prefMcaFitLegacyCheckBox': 'mca_fit_legacy', 'prefBurnLegacyCheckBox': 'burn_legacy_tab',
            'prefMcaFitDataWeightsCheckBox': 'mca_fit_data_weights'}   # F90: P1 the default, data weights legacy (2026-11-24)


def test_the_page_comes_first_and_holds_the_switches(window, recorder):
    d = window.buildPreferences()
    lay = d.layout()
    assert lay.itemAt(0).widget() is d.prefReductionGroup
    assert d.prefPatchMethodComboBox.parentWidget() is d.prefReductionGroup     # moved here (Q-UI-B4)
    for name, key in SWITCHES.items():
        box = getattr(d, name)
        assert box.parentWidget() is d.prefReductionGroup and not box.isChecked() and box.toolTip()
        box.setChecked(True)
        assert window.prefs[key] is True
    assert recorder.exceptions == []


def test_the_mca_fit_switch_shows_the_legacy_buttons_and_relabels_fit(window, recorder):
    legacy = (window.ui.mcaFitPushButton, window.ui.mcaFitAllPushButton, window.ui.mcaAcceptPushButton)
    assert [b.isHidden() for b in legacy] == [True, True, True]       # hidden themselves (the MCA tab need not be on show)
    assert window.mcaFitLinesPushButton.text() == 'Fit lines'
    window.setPreference('mca_fit_legacy', True)
    assert [b.isHidden() for b in legacy] == [False, False, False]
    assert window.mcaFitLinesPushButton.text() == 'Fit (legacy)'
    assert recorder.exceptions == []


def test_fit_runs_the_chosen_path_and_ctrl_click_the_other_once(window, recorder, monkeypatch):
    ran = []
    monkeypatch.setattr(window, 'mcaPeakFit', lambda: ran.append('legacy'))
    monkeypatch.setattr(window, 'mcaFitLines', lambda: ran.append('lines'))
    window.mcaFitAction()
    monkeypatch.setattr(window, 'ctrlClicked', lambda: True)
    window.mcaFitAction()
    assert ran == ['lines', 'legacy']
    assert any('Ctrl+click' in m for m in recorder.messages)
    assert not window.messageDock.isVisible()            # an info line: no pane forced open, no dialog
    assert recorder.dialogs == [] and recorder.exceptions == []


def test_ctrl_click_on_ref_patch_uses_the_other_fit_once(loaded, qapp, recorder, monkeypatch):
    sweep._select_scans(loaded, qapp, [0, 1])
    sweep._select_images(loaded, qapp)
    monkeypatch.setattr(loaded, 'ctrlClicked', lambda: True)
    loaded.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert loaded.refMethodUsed == 'legacy' and loaded.prefs['ref_patch_method'] == 'joint'
    assert any('Ctrl+click: this Ref Patch uses the legacy fit' in m for m in recorder.messages)
    monkeypatch.setattr(loaded, 'ctrlClicked', lambda: False)
    loaded.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert loaded.refMethodUsed == 'joint'
    assert recorder.exceptions == []


def test_the_burn_legacy_tab_is_behind_the_switch(window, recorder):
    window.buildBurnDialog()
    tabs = window.uipdburn.burnTabWidget
    assert tabs.tabText(1) == 'Legacy' and not tabs.isTabVisible(1)
    window.setPreference('burn_legacy_tab', True)
    assert tabs.isTabVisible(1)
    window.setPreference('burn_legacy_tab', False)
    window.uipdburn.refPushButton.click()                  # a legacy action still opens its tab
    assert tabs.isTabVisible(1) and tabs.currentIndex() == 1
    assert recorder.exceptions == []
