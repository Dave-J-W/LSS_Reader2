"""F27: SPEC files and data folders that are not the ideal case open
quietly and give correct results for what is there."""
import os

import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui


def _dataset(root, numbers, monitors, missing=(), folder='pilatus'):
    """Pilatus reflectivity scans with the given scan numbers and monitors;
    ``missing`` lists (scan, frame) images that are not written."""
    os.makedirs(os.path.join(str(root), folder))
    qz = np.array([0.02, 0.03, 0.04])
    scans = [synth.spec_scan(n, 'g', synth.REF_COLUMNS, synth.ref_rows(qz, monitor=m))
             for n, m in zip(numbers, monitors)]
    spec = synth.write_spec(os.path.join(str(root), 'g'), scans)
    for n in numbers:
        for j in range(len(qz)):
            if (n, j) not in missing:
                synth.write_pilatus_tif(
                    os.path.join(str(root), folder, 'g_SCAN-%d_%04d.tif' % (n, j)),
                    synth.pilatus_image(peak=(97, 100), amplitude=1000.0 * n + j))
    return spec


def test_a_missing_image_does_not_shift_later_frames(window, qapp, recorder,
                                                     tmp_path):
    """Before the fix the monitor list kept one entry per SPEC point while
    the image list skipped the missing image, so every later frame was
    normalised with its neighbour's monitor, and the j-th file found was
    paired with point j, so a gap shifted images onto the wrong points."""
    spec = _dataset(tmp_path, [1, 2], [1.0e5, 3.0e5], missing={(1, 1)})
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0, 1])
    assert recorder.exceptions == []
    assert window.ui.imageListWidget.count() == 5
    assert [m for m in recorder.messages if 'no readable image' in m] == [
        'Scan 1: 1 of 3 frames have no readable image (1).']
    assert window.pilFrameNum == [0, 2, 0, 1, 2]
    assert window.pilScanNum == [1, 1, 2, 2, 2]
    assert list(window.pilMonc) == [1.0e5, 1.0e5, 3.0e5, 3.0e5, 3.0e5]
    assert [os.path.basename(f) for f in window.pilFileNames] == [
        'g_SCAN-1_0000.tif', 'g_SCAN-1_0002.tif', 'g_SCAN-2_0000.tif',
        'g_SCAN-2_0001.tif', 'g_SCAN-2_0002.tif']
    for name in ('pilFileQzs', 'pil_Dist', 'pil_AbsNum', 'pilAlpha'):
        assert len(getattr(window, name)) == 5, name
    # and the reflectivity of each frame uses its own monitor
    sweep._select_images(window, qapp)
    window.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    s1, s2 = window.scanqzframe[1], window.scanqzframe[2]
    # same peak in both scans, monitors 1e5 and 3e5: scan 2 is 3x smaller
    assert s2[0, 1] / s1[0, 1] == pytest.approx(
        (2000.0 / 3.0e5) / (1000.0 / 1.0e5), rel=2e-2)


def test_scan_numbers_need_not_start_at_one(window, qapp, recorder, tmp_path):
    spec = _dataset(tmp_path, [7, 9], [1.0e5, 1.0e5])
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [1])            # scan 9
    sweep._select_images(window, qapp, [0])
    assert recorder.exceptions == []
    assert window.pilScanNum == [9, 9, 9]
    assert window.scanRow(9) == 1 and window.scanRow(8) is None
    # typing the numbers selects the right rows
    window.ui.scansLineEdit.setText('9')
    window.ui.scansLineEdit.returnPressed.emit()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert [i.text().split()[1] for i in window.ui.scanListWidget.selectedItems()] == ['9']


def test_missing_image_folder_and_cancelled_chooser(window, qapp, recorder,
                                                    tmp_path):
    spec = _dataset(tmp_path, [1], [1.0e5], folder='elsewhere')
    recorder.directory = ''                            # user cancels the chooser
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    assert recorder.exceptions == []
    assert any('was not found beside the SPEC file' in m for m in recorder.messages)
    assert any('No Pilatus folder chosen' in m for m in recorder.messages)
    recorder.messages.clear()
    sweep._select_scans(window, qapp, [0])
    assert recorder.exceptions == []
    assert window.ui.imageListWidget.count() == 0
    assert recorder.messages == ['Scan 1: 3 of 3 frames have no readable image (0, 1, 2).']


def test_missing_image_folder_chosen_by_hand(window, qapp, recorder, tmp_path):
    spec = _dataset(tmp_path, [1], [1.0e5], folder='elsewhere')
    recorder.directory = str(tmp_path / 'elsewhere')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp, [0])
    assert recorder.exceptions == []
    assert window.ui.imageListWidget.count() == 3
    assert 0 in window.pilData
