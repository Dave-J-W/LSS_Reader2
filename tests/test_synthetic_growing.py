"""Replaying a data set as it was measured (tests/synthetic/growing.py)."""
import filecmp
import os

import synth
from spec_routines import specread
from synthetic.growing import Growing


def _points(spec):
    r = specread(spec, data={}, par={})
    return {n: len(r.Data[n]['L']) if 'L' in r.Data[n] else 0 for n in r.Data['ScanNums']}


def test_a_burn_scan_grows_line_by_line_with_late_images(tmp_path):
    src = synth.make_burn_dataset(tmp_path / 'src')
    g = Growing(src, tmp_path / 'dst', image_lag=3)
    assert g.advance(8) == 8
    assert _points(g.spec) == {1: 8}
    assert g.points == {1: 8} and g.images == {1: 5}
    assert len(os.listdir(tmp_path / 'dst' / 'pilatus')) == 5
    g.flush_images()
    assert g.images == {1: 8}
    g.advance_to(1, 15)
    assert _points(g.spec) == {1: 15} and g.images == {1: 12}
    g.finish()
    assert g.done and filecmp.cmp(src, g.spec, shallow=False)
    names = sorted(os.listdir(tmp_path / 'src' / 'pilatus'))
    assert sorted(os.listdir(tmp_path / 'dst' / 'pilatus')) == names
    assert all(filecmp.cmp(tmp_path / 'src' / 'pilatus' / n, tmp_path / 'dst' / 'pilatus' / n, shallow=False)
               for n in names)


def test_scans_follow_one_another_and_mca_files_come_with_their_scan(tmp_path):
    src = synth.make_dataset(tmp_path / 'src')          # scans 1-2 Pilatus, 3 MCA (no lines), 4 motor
    g = Growing(src, tmp_path / 'dst')
    g.advance(9)
    assert _points(g.spec) == {1: 9}
    g.advance(1)
    assert _points(g.spec) == {1: 9, 2: 1}
    assert os.listdir(tmp_path / 'dst' / 'vortex') == []
    g.advance(7)                                          # scan 2 done, scan 3's header and scan 4's first line
    assert os.listdir(tmp_path / 'dst' / 'vortex') == ['sample_3_mca']
    assert set(_points(g.spec)) == {1, 2, 3, 4}
    g.finish()
    assert filecmp.cmp(src, g.spec, shallow=False)
    assert os.listdir(tmp_path / 'src') and g.done        # the source is untouched
