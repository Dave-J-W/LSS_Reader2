"""The window's detector sizes follow the frames it has read (TODO area L,
2026-11-24): on the Pilatus 100K every default and limit is the number it
always was; on a larger detector they follow its rows and columns.

The Pilatus 100K file is 487 × 195 pixels; the reader presents it rotated,
as 487 rows and 195 columns (lss_core.images.SHAPE_100K)."""
import glob

import numpy as np
import pytest

import sweep
from lss_core import cuts
from lss_core.images import SHAPE_100K, read_pilatus

LARGER = (1043, 981)          # a Pilatus 1M's size, as a stand-in for any larger frame
LEGACY_RANGES = ('0:1', '1:2', '0:485', '0:194')


def test_the_100k_shape_is_the_shape_of_real_frames():
    frame = sorted(glob.glob('sample_data/NX_school/**/*.tif', recursive=True))[0]
    assert np.asarray(read_pilatus(frame)).shape == SHAPE_100K == (487, 195)


def test_default_ranges_are_unchanged_on_the_100k_and_follow_a_larger_detector():
    assert tuple(cuts.default_range(d) for d in range(4)) == LEGACY_RANGES
    assert tuple(cuts.default_range(d, SHAPE_100K) for d in range(4)) == LEGACY_RANGES
    assert tuple(cuts.default_range(n, LARGER) for n in cuts.DIRECTIONS) == ('0:1', '1:2', '0:1041', '0:980')


def _ranges(w, qapp):
    out = []
    for d in (1, 2, 3, 0):                      # the box starts at 0: leave it first so that each change fires
        w.ui.pilCutDirComboBox.setCurrentIndex(d)
        qapp.processEvents()
        out.append(str(w.ui.pilIntRangeLineEdit.text()))
    return (out[3],) + tuple(out[:3])


@pytest.mark.gui
def test_window_cut_ranges_before_and_after_frames(loaded, qapp, recorder, dataset, monkeypatch):
    w = loaded
    assert w.pilShape() == SHAPE_100K                       # no frame read yet
    assert _ranges(w, qapp) == LEGACY_RANGES
    sweep.state_pilatus_two_scans_all_frames(w, qapp, dataset)
    assert (w.pilatus.NROWS, w.pilatus.NCOLS) == SHAPE_100K
    assert _ranges(w, qapp) == LEGACY_RANGES
    monkeypatch.setattr(w.pilatus, 'NROWS', LARGER[0])
    monkeypatch.setattr(w.pilatus, 'NCOLS', LARGER[1])
    assert w.pilShape() == LARGER
    assert _ranges(w, qapp) == ('0:1', '1:2', '0:1041', '0:980')
    assert recorder.exceptions == []
