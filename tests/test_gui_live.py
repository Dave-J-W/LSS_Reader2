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
    wb = workbook.Workbook(window.workbookPath())
    rows = wb.results(kind='burn test')
    assert len(rows) == 2 and rows[1]['origin'] == 'live' and 'points 8 → 21' in rows[1]['note']
    assert rows[0]['stale'].startswith('superseded by %s' % rows[1]['id'])
    assert wb.data(rows[1]['id']).shape[0] == synth.BURN_FRAMES
    assert window.selectedScanNums == [1]                     # the selection kept
    assert any('remade as' in m for m in recorder.messages)
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
