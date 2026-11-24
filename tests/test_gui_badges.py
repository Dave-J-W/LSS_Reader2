"""State badges in the status bar (F85; owner, 2026-11-23, Q12): error model,
monitor normalisation and patch method, short labels with tooltips; a
three-mode preference (on, on when not default, off)."""
import pytest

pytestmark = pytest.mark.gui


def _shown(w):
    return {k: lab.text() for k, lab in w.badges.items() if lab.isVisibleTo(w)}


def test_badges_show_the_defaults(window, recorder):
    assert _shown(window) == {'errors': 'legacy errors', 'norm': '/ Monc', 'patch': 'joint patch'}
    for lab in window.badges.values():
        assert lab.toolTip() and lab.parentWidget() is window.ui.statusBar
    assert recorder.exceptions == []


def test_badges_follow_the_settings(window, qapp, recorder):
    window.errorModeComboBox.setCurrentIndex(1)            # budget
    window.setErrorModel()
    window.spGainCheckBox.setChecked(True)
    window.setPreference('ref_patch_method', 'legacy')
    qapp.processEvents()
    assert _shown(window) == {'errors': 'budget errors', 'norm': '/ Monc / gain', 'patch': 'legacy patch'}
    window.spPhotonCheckBox.setChecked(True)
    assert window.badges['norm'].text() == '/ photon'
    assert 'fff1e0' in window.badges['patch'].styleSheet()    # changed from the default: amber
    assert recorder.exceptions == []


def test_the_three_modes(window, qapp, recorder):
    window.setPreference('state_badges', 'when_not_default')
    assert _shown(window) == {}
    window.setPreference('ref_patch_method', 'legacy')
    assert _shown(window) == {'patch': 'legacy patch'}
    window.setPreference('state_badges', 'off')
    assert _shown(window) == {}
    d = window.buildPreferences()
    combo = d.prefBadgesComboBox
    combo.setCurrentIndex(combo.findData('on'))
    assert window.prefs['state_badges'] == 'on' and len(_shown(window)) == 3
    assert recorder.exceptions == []


def test_clicking_the_error_badge_opens_the_errors_pane(window, qapp, recorder):
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    assert not window.errorDock.isVisible()
    QTest.mouseClick(window.badges['errors'], Qt.LeftButton)
    qapp.processEvents()
    assert window.errorDock.isVisible()
    QTest.mouseClick(window.badges['norm'], Qt.LeftButton)
    assert window.ui.PlotWidget.currentWidget() is window.ui.specPlotTab
    assert recorder.exceptions == []
