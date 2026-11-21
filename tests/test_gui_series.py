"""Scan series in the scan list (F39, review R2; owner, 2026-11-21): a
Series list above the scans selects a series as one action; clicking a
scan selects its whole series by default, a check box turns that off;
scan rows say their series in a tooltip."""
import os

import pytest

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


@pytest.fixture
def nx(window, qapp, tmp_path):
    if not os.path.exists(NX):
        pytest.skip('NX_school data not present')
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    qapp.processEvents()
    return window


def _count_signals(w):
    calls = []
    w.ui.scanListWidget.itemSelectionChanged.connect(lambda: calls.append(1))
    return calls


def test_series_list_and_row_tooltips(nx, recorder):
    box = nx.seriesComboBox
    texts = [box.itemText(i) for i in range(box.count())]
    assert box.isEnabled() and texts[0].startswith('Series')
    assert any(t.startswith('reflectivity') and 'S# 6-9' in t for t in texts)
    assert any(t.startswith('gid') and 'partial' in t for t in texts)
    assert sum(t.startswith('burn') for t in texts) == 2
    row = nx.ui.scanListWidget.item(nx.scanRow(7))
    assert 'reflectivity series' in row.toolTip() and 'scan 2 of ?' in row.toolTip()
    assert 'align' in nx.ui.scanListWidget.item(nx.scanRow(10)).toolTip()
    assert 'not part of a series' in nx.ui.scanListWidget.item(nx.scanRow(1)).toolTip()
    gid = next(i for i, t in enumerate(texts) if t.startswith('gid'))
    assert 'aborted' in box.itemData(gid, 3)                 # the why, in the item's tooltip
    assert recorder.exceptions == []


def test_choosing_a_series_selects_its_scans_in_one_action(nx, qapp, recorder):
    calls = _count_signals(nx)
    box = nx.seriesComboBox
    i = next(k for k in range(box.count()) if 'S# 6-9' in box.itemText(k))
    box.setCurrentIndex(i)
    box.activated.emit(i)
    qapp.processEvents()
    assert calls == [1]
    assert sorted(nx.selectedScanNums) == [6, 7, 8, 9] and nx.ui.scansLineEdit.text() == '6, 7, 8, 9'
    nx.ui.scanListWidget.item(nx.scanRow(9)).setSelected(False)   # another selection: back to the placeholder
    qapp.processEvents()
    assert box.currentIndex() == 0
    assert recorder.exceptions == []


def test_a_click_selects_the_whole_series_by_default(nx, qapp, recorder):
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    nx.show()
    qapp.processEvents()
    lw = nx.ui.scanListWidget
    assert nx.seriesWholeCheckBox.isChecked()                # the default (owner)
    rect = lw.visualItemRect(lw.item(nx.scanRow(7)))
    QTest.mouseClick(lw.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())
    qapp.processEvents()
    assert sorted(nx.selectedScanNums) == [6, 7, 8, 9]
    rect = lw.visualItemRect(lw.item(nx.scanRow(9)))           # Ctrl-click removes one scan, and it stays removed
    QTest.mouseClick(lw.viewport(), Qt.LeftButton, Qt.ControlModifier, rect.center())
    qapp.processEvents()
    assert sorted(nx.selectedScanNums) == [6, 7, 8]
    rect = lw.visualItemRect(lw.item(nx.scanRow(10)))          # an alignment scan alone
    QTest.mouseClick(lw.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())
    qapp.processEvents()
    assert nx.selectedScanNums == [10]
    nx.seriesWholeCheckBox.setChecked(False)                 # off: one scan at a time, kept as a preference
    assert nx.prefs['select_whole_series'] is False
    rect = lw.visualItemRect(lw.item(nx.scanRow(7)))
    QTest.mouseClick(lw.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())
    qapp.processEvents()
    assert nx.selectedScanNums == [7]
    assert recorder.exceptions == []


def test_programmatic_and_typed_selections_are_not_widened(nx, qapp, recorder):
    import sweep
    sweep._select_scans(nx, qapp, [nx.scanRow(7)])
    assert nx.selectedScanNums == [7]
    nx.ui.scansLineEdit.setText('8')
    nx.ui.scansLineEdit.returnPressed.emit()
    qapp.processEvents()
    assert nx.selectedScanNums == [8]
    assert recorder.exceptions == []
