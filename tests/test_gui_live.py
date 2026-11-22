"""The window's live mode (owner, 2026-11-22; L1-L4): a SPEC file written
while it is watched."""
import os

import pytest

import sweep
import synth
from lss_core import workbook

pytestmark = pytest.mark.gui


def _split(spec, keep):
    """Cut the file after ``keep`` data lines of its last scan; return the rest."""
    lines = open(spec).read().splitlines(True)
    data = [k for k, l in enumerate(lines) if l.strip() and not l.startswith('#')]
    cut = data[keep]
    with open(spec, 'w') as f:
        f.writelines(lines[:cut])
    return ''.join(lines[cut:])


def test_a_growing_burn_scan_is_remade_live(window, qapp, recorder, tmp_path):
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    rest = _split(spec, 8)                                   # 8 of 21 frames written so far
    window.prefs['live_interval_s'] = 0.2
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp)
    window.ui.pilBurnPushButton.click()                       # analysed and saved automatically
    qapp.processEvents()
    qapp.processEvents()
    wb = workbook.Workbook(window.workbookPath())
    first = wb.results(kind='burn test')
    assert len(first) == 1 and first[0]['series_points'] == 8 and first[0]['origin'] == 'auto'
    window.liveCheckBox.setChecked(True)
    assert window.liveTimer.isActive()
    with open(spec, 'a') as f:                                # the scan goes on
        f.write(rest)
    window.liveTick()
    qapp.processEvents()
    assert window.remakeJobs or window.workbookCache       # the remake runs in a worker thread
    window.finishRemakes()
    wb = workbook.Workbook(window.workbookPath())
    rows = wb.results(kind='burn test')
    assert len(rows) == 2 and rows[1]['origin'] == 'live' and 'points 8 → 21' in rows[1]['note']
    assert rows[0]['stale'].startswith('superseded by %s' % rows[1]['id'])
    assert wb.data(rows[1]['id']).shape[0] == synth.BURN_FRAMES
    assert window.selectedScanNums == [1]                     # the selection kept
    assert any('remade as' in m for m in recorder.messages)
    # the open burn dialog shows the remade result, and it is not saved a third time
    assert len(window.burnResult.t) == synth.BURN_FRAMES and window.shownResults['burn test'] == rows[1]['id']
    qapp.processEvents()
    assert len(workbook.Workbook(window.workbookPath()).results(kind='burn test')) == 2
    window.liveCheckBox.setChecked(False)
    assert not window.liveTimer.isActive()
    assert recorder.exceptions == []


def test_live_follows_a_series_and_stops_at_its_end(window, qapp, recorder, tmp_path):
    from test_series import _scan
    spec = synth.write_spec(str(tmp_path / 's'), [_scan(1, sid='r1', i=1, n=2)])
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    window.liveCheckBox.setChecked(True)
    with open(spec, 'a') as f:
        f.write(_scan(2, sid='r1', i=2, n=2))
    window.liveTick()
    qapp.processEvents()
    assert sorted(window.selectedScanNums) == [1, 2]           # the selection follows the series (L3)
    assert not window.liveCheckBox.isChecked()                 # complete: live mode stops (L4)
    assert any('Live updates stopped: series r1 is complete' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_live_needs_a_file(window, recorder):
    window.liveCheckBox.setChecked(True)
    assert not window.liveCheckBox.isChecked() and any('SPEC file' in m for m in recorder.messages)


def test_a_frame_left_out_stays_out_and_new_frames_come_in(window, qapp, recorder, tmp_path):
    """Owner, 2026-11-22: point selection "should be preserved across
    updates": frame 3 left out of the burn test stays out when the scan
    grows; the frames written since are added."""
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    rest = _split(spec, 8)
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp, [0, 1, 2, 4, 5, 6, 7])
    window.ui.pilBurnPushButton.click()
    qapp.processEvents()
    qapp.processEvents()
    first = workbook.Workbook(window.workbookPath()).results(kind='burn test')[0]
    assert 'points=[0, 1, 2, 4, 5, 6, 7]' in first['recipe']
    window.liveCheckBox.setChecked(True)
    with open(spec, 'a') as f:
        f.write(rest)
    window.liveTick()
    window.finishRemakes()
    row = workbook.Workbook(window.workbookPath()).results(kind='burn test')[-1]
    assert row['origin'] == 'live'
    assert 'points=[0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]' in row['recipe']
    assert workbook.Workbook(window.workbookPath()).data(row['id']).shape[0] == synth.BURN_FRAMES - 1
    assert recorder.exceptions == []


def test_an_update_keeps_the_tab_the_axes_and_the_frames(window, qapp, recorder, tmp_path):
    """Owner, 2026-11-22: "updates shouldn't feel like a reset or clunky"."""
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    rest = _split(spec, 8)
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp, [2, 5])
    window.ui.spYComboBox.setCurrentIndex(window.ui.spYComboBox.findText('Monc'))
    window.ui.PlotWidget.setCurrentIndex(1)
    window.liveCheckBox.setChecked(True)
    with open(spec, 'a') as f:
        f.write(rest)
    window.liveTick()
    qapp.processEvents()
    assert window.ui.PlotWidget.currentIndex() == 1
    assert window.ui.spYComboBox.currentText() == 'Monc'
    assert [i for i in range(window.ui.imageListWidget.count())
            if window.ui.imageListWidget.item(i).isSelected()] == [2, 5]
    assert window.ui.imageListWidget.count() == synth.BURN_FRAMES      # the new frames listed
    assert not any('Reading scans' in m for m in recorder.messages)
    window.liveCheckBox.setChecked(False)
    window.finishRemakes()
    assert recorder.exceptions == []


def test_nothing_moves_when_the_new_scans_are_elsewhere(window, qapp, recorder, tmp_path):
    from test_series import _scan
    spec = synth.write_spec(str(tmp_path / 's'), [_scan(1), _scan(2, command='ascan oh -1 1 4 1')])
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [1])
    calls = []
    window.ui.imageListWidget.itemSelectionChanged.connect(lambda: calls.append(1))
    window.liveCheckBox.setChecked(True)
    with open(spec, 'a') as f:
        f.write(_scan(5, command='ascan oh -1 1 4 1'))
    window.liveTick()
    qapp.processEvents()
    assert window.ui.scanListWidget.count() == 3 and window.selectedScanNums == [2]
    assert calls == []                                          # no redraw: the selection did not change
    assert 'new scans 5' in window.ui.statusBar.currentMessage()
    window.liveCheckBox.setChecked(False)
    assert recorder.exceptions == []


def _ref_scan(root, name, num, qz, absorber):
    """A reflectivity scan's SPEC text and its frames (as synth.make_dataset)."""
    import numpy as np
    for j, q in enumerate(qz):
        amp = synth.PEAK_AMPLITUDE * synth.reflectivity(q) / synth.ABSFAC ** absorber
        synth.write_pilatus_tif(os.path.join(root, 'pilatus', '%s_SCAN-%d_%04d.tif' % (name, num, j)),
                                synth.pilatus_image(peak=(synth.PIL_H - synth.DB_X - 1, synth.DB_Y), amplitude=amp))
    return synth.spec_scan(num, name, synth.REF_COLUMNS, synth.ref_rows(qz), absorber=absorber)


def test_the_open_reflectivity_follows_its_series(window, qapp, recorder, tmp_path):
    """Owner, 2026-11-22: redraw the open plot from remakes. A patched
    reflectivity of scans 1-2 is on screen; scan 3 of the series arrives;
    the remade curve (scans 1-3) replaces it in the Reflectivity tab."""
    import numpy as np
    root = str(tmp_path / 'ref')
    os.makedirs(os.path.join(root, 'pilatus'))
    s1 = _ref_scan(root, 'r', 1, np.linspace(0.01, 0.05, 9), 0)
    s2 = _ref_scan(root, 'r', 2, np.linspace(0.04, 0.10, 7), 1)
    spec = synth.write_spec(os.path.join(root, 'r'), [s1, s2])
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0, 1])
    sweep._select_images(window, qapp)
    window.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    window.uirefpatch.nextPushButton.click()                  # "Finish!"
    qapp.processEvents()
    qapp.processEvents()
    shown = window.shownResults['reflectivity']
    assert window.normRefData[:, 0].max() == pytest.approx(0.10)
    window.liveCheckBox.setChecked(True)
    s3 = _ref_scan(root, 'r', 3, np.linspace(0.09, 0.15, 7), 2)
    with open(spec, 'a') as f:
        f.write(s3)
    window.liveTick()
    window.finishRemakes()
    qapp.processEvents()
    assert sorted(window.selectedScanNums) == [1, 2, 3]       # the series selection followed
    assert window.normRefData[:, 0].max() == pytest.approx(0.15)
    new = window.shownResults['reflectivity']
    assert new != shown
    wb = workbook.Workbook(window.workbookPath())
    row = next(r for r in wb.results() if r['id'] == new)
    assert row['origin'] == 'live' and row['scans'] == '1,2,3' and row['label'] == 'R'
    assert len(wb.data(new)) == len(window.normRefData)
    window.liveCheckBox.setChecked(False)
    assert recorder.exceptions == []


NX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  'sample_data', 'NX_school', '2026sep', '20260923')


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_the_open_gid_map_follows_its_series(window, qapp, recorder, tmp_path):
    """NX school GID scans 11 and 12 (one series): the file is cut before
    scan 12 (a copy; the frames are linked); the map of scan 11 is on
    screen; scan 12 arrives; the remade map of 11 + 12 replaces it."""
    import numpy as np
    text = open(NX).read()
    cut = text.index('#S 12 ')
    spec = str(tmp_path / '20260923')
    with open(spec, 'w') as f:
        f.write(text[:cut])
    os.symlink(os.path.join(os.path.dirname(NX), 'pilatus'), str(tmp_path / 'pilatus'))
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [10])
    sweep._select_images(window, qapp)
    i = window.ui.gidComboBox.findText('GID Patch')
    window.ui.gidComboBox.setCurrentIndex(i)
    window.ui.gidComboBox.activated.emit(i)
    qapp.processEvents()
    qapp.processEvents()
    first = window.shownResults['gid map']
    width = np.nanmax(window.pilGIDXAxs) - np.nanmin(window.pilGIDXAxs)
    window.liveCheckBox.setChecked(True)
    with open(spec, 'a') as f:
        f.write(text[cut:text.index('#S 13 ')])
    window.liveTick()
    window.finishRemakes(timeout=300)
    qapp.processEvents()
    new = window.shownResults['gid map']
    assert new != first
    row = next(r for r in workbook.Workbook(window.workbookPath()).results() if r['id'] == new)
    assert row['scans'] == '11,12' and row['origin'] == 'live'
    X, Y, V, E = workbook.Workbook(window.workbookPath()).map(new)
    assert np.allclose(window.pilGIDData, V, equal_nan=True)         # the map on screen is the remade one
    # two Qz levels share a narrower 2theta grid than scan 11 alone (scan 12 has 4 frames)
    assert np.nanmax(window.pilGIDXAxs) - np.nanmin(window.pilGIDXAxs) < width
    assert sorted({int(n) for lv in window.gidLevels for n in lv[1]}) == [11, 12]
    window.liveCheckBox.setChecked(False)
    assert recorder.exceptions == []


def test_images_that_arrive_after_their_spec_lines_are_picked_up(window, qapp, recorder, tmp_path):
    """Owner, 2026-11-22: updating should proceed on each new Pilatus image.
    The SPEC file has all 21 points of a burn scan but only 8 images are
    written; the other 13 arrive while the SPEC file does not change."""
    import shutil
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    pil = str(tmp_path / 'burn' / 'pilatus')
    later = str(tmp_path / 'later')
    os.makedirs(later)
    for j in range(8, synth.BURN_FRAMES):
        shutil.move(os.path.join(pil, 'burn_SCAN-1_%04d.tif' % j), later)
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    assert window.scanPoints[1] == 8                         # frames on disk, not SPEC lines
    sweep._select_scans(window, qapp, [0])
    sweep._select_images(window, qapp, list(range(8)))
    window.ui.pilBurnPushButton.click()
    qapp.processEvents()
    qapp.processEvents()
    assert workbook.Workbook(window.workbookPath()).results(kind='burn test')[0]['series_points'] == 8
    window.liveCheckBox.setChecked(True)
    stamp = window.fileStamp()
    for name in sorted(os.listdir(later)):
        shutil.move(os.path.join(later, name), pil)
    assert window.fileStamp() != stamp                        # the Pilatus folder is watched
    window.liveTick()
    window.finishRemakes()
    qapp.processEvents()
    assert window.scanPoints[1] == synth.BURN_FRAMES
    rows = workbook.Workbook(window.workbookPath()).results(kind='burn test')
    assert rows[-1]['origin'] == 'live' and 'points 8 → 21' in rows[-1]['note']
    assert len(window.burnResult.t) == synth.BURN_FRAMES
    window.liveCheckBox.setChecked(False)
    assert recorder.exceptions == []


def test_spectra_appended_to_an_mca_file_are_picked_up(window, qapp, recorder, dataset, tmp_path):
    """A fluorescence scan's MCA file grows by one spectrum; the SPEC file does not change."""
    import numpy as np
    window.openSpecFile(fname=dataset)
    window.directory = str(tmp_path)
    qapp.processEvents()
    mca = window.mcaFilePath(3)
    ch = np.arange(1, 257)
    spectrum = 500 * np.exp(-(ch - 120.0) ** 2 / 2 / 5 ** 2) + 5
    synth.write_mca(mca, [spectrum])
    window.updateSeries()
    assert window.scanPoints[3] == 1
    window.liveCheckBox.setChecked(True)
    window.liveStamp = window.fileStamp()
    synth.write_mca(mca, [spectrum, spectrum * 2, spectrum * 3])
    assert window.fileStamp() != window.liveStamp             # the last scan's MCA file is watched
    window.liveTick()
    qapp.processEvents()
    assert window.scanPoints[3] == 3
    assert window.countSpectra(mca) == 3
    window.liveCheckBox.setChecked(False)
    assert recorder.exceptions == []
