"""The bottom panes (Script, Messages, Errors) follow D59 (owner, 2026-11-22;
2026-11-23, Q11): hidden by default, under the tabs only so the selection
panel keeps the full height, never showing themselves except Messages on a
warning, and the View-menu choice kept between sessions."""
import pytest

from lss_core import preferences

pytestmark = pytest.mark.gui


def _docks(w):
    return (w.messageDock, w.scriptDock, w.errorDock)


def test_all_panes_are_hidden_at_start(window, recorder):
    assert [d.isVisible() for d in _docks(window)] == [False, False, False]
    assert recorder.exceptions == []


def test_the_script_pane_does_not_show_itself(window, recorder):
    window.scriptLine("exp = Experiment('x')")
    assert "exp = Experiment('x')" in window.scriptView.toPlainText()
    assert not window.scriptDock.isVisible()
    assert recorder.exceptions == []


def test_messages_show_on_warnings_only(window, qapp, recorder):
    window.notify('Saved to the workbook', title='Save', level='info')
    qapp.processEvents()
    assert not window.messageDock.isVisible()
    assert 'Saved to the workbook' in window.messageView.toPlainText()     # kept in the pane
    assert 'Saved to the workbook' in window.ui.statusBar.currentMessage()
    window.notify('Select a scan first')                                 # a warning (the default)
    qapp.processEvents()
    assert window.messageDock.isVisible()
    assert recorder.exceptions == []


def test_panes_sit_under_the_tabs_not_under_the_selection_panel(window, qapp, recorder):
    from PyQt5.QtCore import QPoint
    window.resize(1600, 1000)
    window.messageDock.show()
    qapp.processEvents()
    left = window.ui.scanListWidget
    left_right_edge = left.mapTo(window, QPoint(left.width(), 0)).x()
    dock_left_edge = window.messageDock.mapTo(window, QPoint(0, 0)).x()
    assert dock_left_edge >= left_right_edge                     # the dock starts right of the scan list
    tabs = window.ui.PlotWidget
    assert window.messageDock.mapTo(window, QPoint(0, 0)).y() >= tabs.mapTo(window, QPoint(0, tabs.height())).y() - 1
    assert window.messageDock.parentWidget() is window.paneHost
    assert recorder.exceptions == []


def test_the_view_menu_choice_is_kept_between_sessions(window, qapp, recorder):
    act = window.scriptDock.toggleViewAction()
    act.trigger()                                                   # the user shows the Script pane
    qapp.processEvents()
    assert window.scriptDock.isVisible()
    assert preferences.load()['panes_shown'] == ['scriptDock']
    from mainwindow import MainWindow
    again = MainWindow()
    again.show()
    qapp.processEvents()
    assert again.scriptDock.isVisible() and not again.messageDock.isVisible()
    act2 = again.scriptDock.toggleViewAction()
    act2.trigger()                                                  # and hides it again
    assert preferences.load()['panes_shown'] == []
    again.close()
    assert recorder.exceptions == []
