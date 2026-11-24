"""What a list item stands for is kept as item data, not read back from its
displayed text (the fragility audit, 2026-11-24, TODO area L).

Before, the scan list's text was split for scan numbers, the image list's
for scan and frame numbers, file names and cut labels, and the Ref Qz
list's for its Qz. Any change to how those lists are written would have
broken the lookups silently. These tests rewrite every item's text and check
that nothing depends on it."""
import pytest

import mainwindow as mw
import sweep

pytestmark = pytest.mark.gui


def _scramble(widget):
    for k in range(widget.count()):
        widget.item(k).setText('item %d (renamed)' % k)


def test_items_carry_their_scan_frame_and_labels(loaded, qapp, recorder):
    w = loaded
    for k in range(w.ui.scanListWidget.count()):
        it = w.ui.scanListWidget.item(k)
        assert mw.itemScan(it) == int(str(it.text()).split()[1])
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    for k in range(w.ui.imageListWidget.count()):
        it = w.ui.imageListWidget.item(k)
        scan, frame = str(it.text()).split('\t')[:2]
        assert mw.itemLabels(it) == (scan, frame)
        assert mw.itemScan(it) == w.pilScanNum[k] and mw.itemFrame(it) == int(frame.split('#')[1])
    assert recorder.exceptions == []


def test_the_scan_selection_does_not_read_the_text(loaded, qapp, recorder):
    w = loaded
    _scramble(w.ui.scanListWidget)
    sweep._select_scans(w, qapp, [1])
    assert w.selectedScanNums == [2]
    assert w.selectedScanNumbersInList() == [2]
    assert recorder.exceptions == []


def test_cut_labels_and_file_names_do_not_read_the_text(loaded, qapp, recorder, tmp_path):
    w = loaded
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp, [0, 1])
    _scramble(w.ui.imageListWidget)
    w.ui.pilCutDirComboBox.setCurrentIndex(3)
    w.ui.pilIntRangeLineEdit.setText('90:104')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert w.cutLabel[0] == 'S# 1 F# 0' and w.cutLabel[1] == 'S# 1 F# 1'
    recorder.save_name = str(tmp_path / 'c')
    w.ui.cutExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert (tmp_path / 'cS# 1_F# 0_cut.txt').exists() and (tmp_path / 'cS# 1_F# 1_cut.txt').exists()


def test_the_ref_qz_list_does_not_read_the_text(loaded, qapp, recorder, dataset):
    w = loaded
    sweep.state_pilatus_two_scans_all_frames(w, qapp, dataset)
    _scramble(w.ui.imageListWidget)                     # the Ref list is built from the image list's data
    w.ui.pilRefPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    q = w.ui.refQzListWidget
    assert q.count() > 0
    expect = [mw.itemQz(q.item(k)) for k in range(q.count())]
    for k, qz in enumerate(expect):                     # each row's Qz is its frames' Qz
        assert all(abs(w.pilFileQzs[i] - qz) < 5e-4 for i in w.refSortedFrameNums[k])
    _scramble(q)
    q.clearSelection()
    q.item(2).setSelected(True)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert w.refQzSelected == pytest.approx(expect[2])


def test_items_made_without_data_still_read_their_text(qapp):
    from PyQt5.QtWidgets import QListWidgetItem
    it = QListWidgetItem('S# 7\tF# 12\tQz=0.0400')
    assert mw.itemScan(it) == 7 and mw.itemFrame(it) == 12 and mw.itemLabels(it) == ('S# 7', 'F# 12')
    assert mw.itemQz(QListWidgetItem('Qz= 0.035\t {S:F}= {7: [3]}')) == pytest.approx(0.035)
