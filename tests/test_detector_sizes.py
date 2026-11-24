"""The window's detector sizes follow the frames it has read (TODO area L,
2026-11-24): on the Pilatus 100K every default and limit is the number it
always was; on a larger detector they follow its rows and columns.

The Pilatus 100K file is 487 × 195 pixels; the reader presents it rotated,
as 487 rows and 195 columns (lss_core.images.SHAPE_100K)."""
import glob

import numpy as np
import pytest

import sweep
from PyQt5.QtWidgets import QPushButton
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


def test_gid_defaults_are_unchanged_on_the_100k_and_follow_a_larger_detector():
    from lss_core.gid import GIDParams, ROW_MAX_100K
    assert ROW_MAX_100K == GIDParams().row_max == 486
    assert GIDParams.for_detector(SHAPE_100K) == GIDParams()
    assert GIDParams.for_detector(SHAPE_100K).changed() == []
    assert GIDParams.for_detector(LARGER).row_max == LARGER[0] - 1
    assert GIDParams.for_detector(LARGER, row_max=300, pinhole=False) == GIDParams(row_max=300, pinhole=False)


def test_script_gid_without_params_takes_the_frames_last_row(monkeypatch):
    from lss_core import experiment, gid as gm
    seen = []

    class Frame:
        true_alpha, wavelength = 0.0, 1.0

    def stop(frames, gp, *a, **k):
        seen.append(gp)
        raise gm.GIDError('stop here')
    monkeypatch.setattr(gm, 'pinhole_patch', stop)
    ex = experiment.Experiment.__new__(experiment.Experiment)
    for shape in (SHAPE_100K, LARGER):
        f = Frame()
        f.data = np.zeros(shape)
        monkeypatch.setattr(experiment.Experiment, 'gid_frames', lambda self, *a, f=f: ([f], None))
        with pytest.raises(gm.GIDError):
            ex.gid([1])
    assert [gp.row_max for gp in seen] == [486, LARGER[0] - 1]
    assert seen[0] == gm.GIDParams()


def _sheet(w, qapp):
    w.showGIDWorksheet()
    qapp.processEvents()
    return w.gidWorksheet


@pytest.mark.gui
def test_gid_worksheet_limits_follow_the_frames(window, qapp, recorder, monkeypatch):
    w = window
    d = _sheet(w, qapp)
    rmax, cols = d.gidRowMaxSpinBox, d.gidColumnsSpinBox
    assert (rmax.value(), cols.maximum(), w.gidEffectiveParams().row_max) == (486, 195, 486)   # the 100K, as before
    assert w.gidParams.changed() == [] and w.gidRowMaxFollows and w.gidScriptSettings()[1] == []
    monkeypatch.setattr(w.pilatus, 'NROWS', LARGER[0], raising=False)
    monkeypatch.setattr(w.pilatus, 'NCOLS', LARGER[1], raising=False)
    d = _sheet(w, qapp)
    assert (rmax.value(), cols.maximum(), w.gidEffectiveParams().row_max) == (LARGER[0] - 1, LARGER[1], LARGER[0] - 1)
    rmax.setValue(486)                                      # typed: kept, even the 100K's number
    qapp.processEvents()
    assert not w.gidRowMaxFollows and w.gidEffectiveParams().row_max == 486
    assert w.gidEffectiveParams().changed() == []           # the class default, but not what exp.gid takes here:
    assert w.gidScriptSettings()[1] == ['row_max']          # the script names it
    rmax.setValue(700)
    assert w.gidEffectiveParams().row_max == 700 and 'row_max' in w.gidEffectiveParams().changed()
    [b for b in d.findChildren(QPushButton) if b.objectName() == 'gidDefaultsPushButton'][0].click()
    qapp.processEvents()
    assert w.gidRowMaxFollows and rmax.value() == LARGER[0] - 1
    assert w.gidEffectiveParams().row_max == LARGER[0] - 1
    assert w.gidScriptSettings()[1] == ['row_max']          # a script names the larger detector's row
    assert recorder.exceptions == []
