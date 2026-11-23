"""tests/tools/gid_movie.py (2026-11-23; docs/gui/image_display.md M7):
GID frames drawn on one 2θ axis, the public NX school scan 11 (41 frames,
Det_Th 14–18° in steps of 0.1°, the DPPC peak near 2θ = 16.64°).

Invariants (the geometry the movie rests on, docs/physics_notes.md
2026-11-23): a Bragg rod scatters at a fixed 2θ, so in every frame that
holds the peak its brightest column sits at the same 2θ, to within a 2θ
bin (one column, p/D_p), while that column walks across the detector as
far as the arm moved and lies where lss_core.pinhole.pixel_angles puts the
peak's 2θ. As coded: which of the sampled frames hold the peak (measured
2026-11-23). The tool's files: the GIF has one frame per sampled frame, a
rerun writes identical files, and everything is written under tmp_path.
"""
import csv
import math
import os
import sys

import numpy as np
import pytest
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import gid_movie  # noqa: E402
from lss_core import pinhole as ph  # noqa: E402

BIN = math.degrees(ph.PIXEL_MM / 271.0)        # one column at the header's S4-detector distance


@pytest.fixture(scope='module')
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp('gid_movie')
    assert gid_movie.main(['--every', '8', '--out', str(out)]) == 0
    with open(out / 'peak_11.csv', newline='') as fh:
        rows = list(csv.DictReader(fh))
    return out, rows


def test_the_movie_has_one_frame_per_sampled_frame(run):
    out, rows = run
    assert sorted(os.listdir(out)) == ['contact_11.png', 'movie_11.gif', 'peak_11.csv']   # no --pixels
    with Image.open(out / 'movie_11.gif') as im:
        assert im.n_frames == 6                          # points 0, 8, ..., 40 of 41
        assert im.info['loop'] == 0 and im.info['duration'] == 200      # loops, 5 frames per second
    with Image.open(out / 'contact_11.png') as im:
        assert im.size[0] == 1100 and im.size[1] > 600   # 6 frames stacked, two views
    assert [int(r['point']) for r in rows] == [0, 8, 16, 24, 32, 40]


def test_the_peak_stands_still_in_two_theta_and_walks_on_the_pixels(run):
    _, rows = run
    held = [r for r in rows if r['holds_peak'] == '1']
    assert [int(r['point']) for r in held] == [16, 24, 32]           # as coded: Det_Th 15.6, 16.4, 17.2
    dth = np.array([float(r['det_th_deg']) for r in held])
    tt = np.array([float(r['two_theta_deg']) for r in held])
    col = np.array([int(r['column']) for r in held])
    assert abs(tt.mean() - 16.64) < 0.03
    assert np.all(np.abs(tt - tt.mean()) < BIN)                      # the same 2θ to within a bin
    assert np.all(np.diff(dth) > 0) and np.all(np.diff(col) < 0)     # the column moves monotonically
    travel = (dth[-1] - dth[0]) / BIN                                # columns the arm moved (≈ 44)
    assert abs((col[0] - col[-1]) - travel) <= 2
    assert (col[0] - col[-1]) * BIN > 30 * np.abs(tt - tt.mean()).max()   # it walks, the 2θ does not
    for r in held:                                                   # where the exact geometry puts the peak
        assert abs(int(r['column']) - int(r['predicted_column'])) <= 1
        assert float(r['significance']) >= gid_movie.MIN_SIGNIFICANCE


def test_a_rerun_writes_identical_files(run, tmp_path):
    out, _ = run
    assert gid_movie.main(['--every', '8', '--out', str(tmp_path)]) == 0
    for name in ('movie_11.gif', 'contact_11.png', 'peak_11.csv'):
        assert (tmp_path / name).read_bytes() == (out / name).read_bytes(), name


def test_private_data_are_refused_under_docs(tmp_path):
    with pytest.raises(SystemExit) as e:
        gid_movie.main(['--spec', str(tmp_path / 'other_spec'), '--out', os.path.join('docs', 'figures', 'x')])
    assert 'private data' in str(e.value)
    assert not os.path.exists(os.path.join('docs', 'figures', 'x'))
