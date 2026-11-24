"""The Compare tab (F80, F105): the reflectivities saved in the workbook,
overlaid, with ratios, following new saves by itself (owner, Q-REF-5:
"provided the new data auto-update")."""
import pytest

import sweep

pytestmark = pytest.mark.gui


def _show(w, qapp):
    w.ui.PlotWidget.setCurrentWidget(w.compareTab)
    qapp.processEvents()
    return w.compareTab


def _patch(w, qapp, drop=None):
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    d = w.uirefpatch
    if drop is not None:
        d.dropLineEdit.setText(drop)
        d.dropPushButton.click()
        qapp.processEvents()
    d.nextPushButton.click()
    qapp.processEvents()


def test_the_tab_sits_left_of_timeline(window, qapp, recorder):
    pw = window.ui.PlotWidget
    assert pw.indexOf(window.compareTab) == pw.count() - 2 and pw.indexOf(window.timelineTab) == pw.count() - 1
    tab = _show(window, qapp)
    assert 'Open a SPEC file' in tab.infoLabel.text()
    for w in (tab.orderComboBox, tab.ratioCheckBox, tab.rrfCheckBox, tab.followCheckBox, tab.listWidget):
        assert w.toolTip()
    assert recorder.exceptions == []


def test_saved_curves_are_compared_and_new_ones_follow(loaded, qapp, dataset, recorder):
    w = loaded
    w.prefs['auto_save'] = True
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    tab = _show(w, qapp)
    assert 'No workbook yet' in tab.infoLabel.text()
    _patch(w, qapp)                                       # saved by itself once the event loop is idle
    qapp.processEvents()
    tab = _show(w, qapp)
    assert tab.listWidget.count() == 1 and len(tab.shown()) == 1
    assert len(tab.axes) == 1                            # one curve: no ratio panel
    _patch(w, qapp, drop='0')                             # a second version, saved while the tab is not shown
    qapp.processEvents()
    w.ui.PlotWidget.setCurrentWidget(w.compareTab)
    qapp.processEvents()
    assert tab.listWidget.count() == 2 and len(tab.shown()) == 2          # followed: ticked by itself
    assert len(tab.axes) == 2                            # the ratio panel
    rax = tab.axes[1]
    assert rax.get_ylabel().startswith('ratio to ')
    tab.ratioCheckBox.setChecked(False)
    assert len(tab.axes) == 1
    tab.listWidget.item(0).setCheckState(0)             # untick one
    assert len(tab.shown()) == 1
    for k in range(tab.orderComboBox.count()):
        tab.orderComboBox.setCurrentIndex(k)
        assert tab.listWidget.count() == 2
    tab.rrfCheckBox.setChecked(True)                    # the R/RF curves
    assert tab.listWidget.count() in (0, 2)
    assert recorder.exceptions == []


def test_a_save_while_the_tab_is_shown_refreshes_it(loaded, qapp, dataset, recorder):
    w = loaded
    w.prefs['auto_save'] = False
    w.prefs['save_asks_note'] = False
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    _patch(w, qapp)
    tab = _show(w, qapp)
    assert tab.listWidget.count() == 0
    w.saveRefToWorkbook()                                # Save, with the tab on show
    qapp.processEvents()
    assert tab.listWidget.count() == 1 and len(tab.shown()) == 1
    assert recorder.exceptions == []
