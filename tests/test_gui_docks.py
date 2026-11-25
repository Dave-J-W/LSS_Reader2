"""The frequent windows are docks (F95 B10; owner, 2026-11-23, Q-UI-B10:
"Dock the frequent ones (burn, worksheet, fit options as docks or side
panels)"): the burn test under the tab area, tabbed with the panes; the
GID worksheet and the fit options on the right, tabbed together; each in a
scroll area, so a dock never forces the window wider; Close hides the dock;
a dock can float as a window of its own."""
import pytest
from PyQt5.QtCore import Qt

import sweep
import synth

pytestmark = pytest.mark.gui


def _burn(w, qapp, tmp_path):
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    w.prefs['auto_save'] = False
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp)
    w.ui.pilBurnPushButton.click()
    qapp.processEvents()


def test_the_burn_test_is_docked_under_the_tabs(window, qapp, recorder, tmp_path):
    w = window
    _burn(w, qapp, tmp_path)
    dock = w.docks['burn']
    host = w.paneHost
    assert dock.isVisible() and w.uipdburn.isVisible() and not dock.isFloating()
    assert host.dockWidgetArea(dock) == Qt.BottomDockWidgetArea          # alone: the panes are hidden
    assert dock.windowTitle() == 'Burn test' and w.uipdburn.isWindow() is False
    assert dock.minimumSizeHint().width() < 600                           # the scroll area: not 1943 px
    first = w.uipdburn
    w.uipdburn.closePushButton.click()                                    # Close hides the dock
    qapp.processEvents()
    assert not dock.isVisible()
    w.ui.pilBurnPushButton.click()                                        # again: the same dock, a new window in it
    qapp.processEvents()
    assert w.docks['burn'] is dock and dock.isVisible() and dock.widget().widget() is w.uipdburn
    assert w.uipdburn is not first
    assert recorder.exceptions == []


def test_with_the_panes_on_show_the_burn_test_is_tabbed_with_them(window, qapp, recorder, tmp_path):
    w = window
    w.messageDock.show()
    qapp.processEvents()
    _burn(w, qapp, tmp_path)
    assert w.docks['burn'] in w.paneHost.tabifiedDockWidgets(w.messageDock)
    assert w.docks['burn'].isVisible()
    assert recorder.exceptions == []


def test_the_fit_options_are_side_panels_tabbed_together(loaded, qapp, recorder):
    w = loaded
    w.showCutFitOptions()
    w.showMcaFitOptions()
    qapp.processEvents()
    cut, mca = w.docks['cutfit'], w.docks['mcafit']
    host = w.paneHost
    assert host.dockWidgetArea(cut) == host.dockWidgetArea(mca) == Qt.RightDockWidgetArea
    assert mca in host.tabifiedDockWidgets(cut)
    assert mca.isVisible() and w.mcaFitDialog.isVisible()
    assert cut.windowTitle() == 'Peak fit options' and mca.windowTitle() == 'Fluorescence line fit options'
    mca.setFloating(True)                                                 # a window of its own, when wanted
    qapp.processEvents()
    assert mca.isFloating() and w.mcaFitDialog.isVisible()
    w.showCutFitOptions()                                                 # shown again: the same dock, raised
    qapp.processEvents()
    assert w.docks['cutfit'] is cut and cut.isVisible()
    assert recorder.exceptions == []


def test_the_sweep_still_finds_the_docked_windows(window, qapp, recorder, tmp_path):
    """The crash sweep presses the buttons of every visible dialog: a docked
    one is still a visible QDialog child of the window."""
    w = window
    _burn(w, qapp, tmp_path)
    assert w.uipdburn in sweep._visible_dialogs(w)
    assert 'click:burnAnalysePushButton' in sweep.controls(w)
    assert recorder.exceptions == []
