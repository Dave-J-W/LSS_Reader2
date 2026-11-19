"""S1's vertical opening is top + bottom blade (ASSESSMENT defect 10, owner
2026-11-19: "fix the S1 issue"). The legacy GID footprint correction used
S1T + S1T; identical whenever S1 is symmetric, as in every file on hand
(S1T = S1B in all 643 scans), wrong for an asymmetric S1."""
import numpy as np
import pytest

import sweep
import synth
from lss_core.experiment import Experiment
from lss_core import gid


def _asymmetric(tmp_path):
    spec = synth.make_dataset(tmp_path / 'd')
    text = open(spec).read()
    names = list(synth.MOTORS)
    old = '# ' + ' '.join(repr(v) for v in synth.MOTORS.values())
    m = dict(synth.MOTORS, S1B=0.03)
    assert old in text
    open(spec, 'w').write(text.replace(old, '# ' + ' '.join(repr(v) for v in m.values())))
    assert names.index('S1B') == names.index('S1T') + 1
    return spec


def test_script_frames_use_top_plus_bottom(tmp_path):
    frames, _ = Experiment(_asymmetric(tmp_path)).gid_frames([1])
    assert frames[0].slits[1] == pytest.approx(0.01 + 0.03)
    # and the footprint correction sees it: a longer footprint changes calArea
    info = list(frames[0].slits[:4]) + [frames[0].true_alpha, frames[0].s2d, frames[0].pdist]
    short = list(info)
    short[1] = 0.02
    assert gid.cal_area(info, 16.0, 3) != pytest.approx(gid.cal_area(short, 16.0, 3), rel=1e-6)


@pytest.mark.gui
def test_window_frames_use_top_plus_bottom(window, qapp, recorder, tmp_path):
    w = window
    w.openSpecFile(fname=_asymmetric(tmp_path))
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0])
    assert w.pil_S1v[0] == pytest.approx(0.04)
    assert recorder.exceptions == []
