"""GID-burn detector rows from the mean frame (owner, 2026-11-23, Q-BURN-6:
"GID-burn detector rows default from the mean frame"; lss_core.burn.
signal_rows, the default of Experiment.burn since 2026-11-24). Synthetic
GID burn frames (synth.gid_burn_image, make_gid_burn_dataset): a Bragg rod
from the horizon row 100 up, falling as exp(-(row - 100)/60), on diffuse
scatter and a flat floor; the rows where the rod is above 10 % of its
maximum are 100-238."""
import numpy as np
import pytest

import synth
from lss_core import burn

TRUE = synth.gid_burn_rows()          # (100, 238)
SLACK = burn.ROWS_PAD + 3             # the padding, and the 5-row smoothing at the rod's sharp onset


def _within(rows, true=TRUE, slack=SLACK):
    return true[0] - slack <= rows[0] <= true[0] and true[1] <= rows[1] <= true[1] + slack


def test_the_rows_of_an_expected_frame():
    assert TRUE == (100, 238)
    rows = burn.signal_rows(synth.gid_burn_image() / synth.MONITOR)
    assert _within(rows), rows


def test_the_rows_of_a_noisy_mean_and_a_hot_pixel():
    rng = np.random.default_rng(4)
    frames = [rng.poisson(synth.gid_burn_image(40.0)) for _ in range(21)]     # a tenth of the counts
    mean = np.mean(frames, axis=0) / synth.MONITOR
    assert _within(burn.signal_rows(mean))
    hot = mean.copy()
    hot[400, 20] = 1e3 * mean.max()                                         # one hot pixel far from the rod
    assert burn.signal_rows(hot) == burn.signal_rows(mean)


def test_a_rod_over_the_whole_frame_and_no_rod():
    long = synth.gid_burn_image(decay=1e5)                                  # the rod does not fade on the detector
    lo, hi = burn.signal_rows(long)
    assert 100 - SLACK <= lo <= 100 and hi == synth.PIL_W - 1
    rng = np.random.default_rng(1)
    flat = rng.poisson(np.full((synth.PIL_W, synth.PIL_H), 5.0), size=(21, synth.PIL_W, synth.PIL_H)).mean(0)
    assert burn.signal_rows(flat) is None


def test_the_fraction_sets_the_top():
    image = synth.gid_burn_image()
    for f in (0.3, 0.05):
        lo, hi = burn.signal_rows(image, fraction=f)
        assert _within((lo, hi), synth.gid_burn_rows(f)), (f, lo, hi)


def test_experiment_burn_uses_them_by_default(tmp_path):
    from lss_core.experiment import Experiment
    exp = Experiment(synth.make_gid_burn_dataset(tmp_path / 'gid', seed=2))
    res = exp.burn(1)
    assert res.kind == 'gid' and _within(res.rows)
    assert any('Q-BURN-6' in n for n in res.notes)
    assert 'rows %d–%d' % res.rows in burn.summary_text(res)
    every = exp.burn(1, rows=None)                                          # all rows, as before
    assert every.rows == (0, synth.PIL_W - 1)
    typed = exp.burn(1, rows=(120, 200))
    assert typed.rows == (120, 200)
    with pytest.raises(ValueError):
        exp.burn(1, rows='max')
    # the rod fades as exp(-t/400 s) in every row: both row choices find it fading, and the rows from
    # the mean frame hold about 90 % of the rod's counts
    for r in (res, every):
        c = r.trends['intensity']
        assert not c.stable and c.best in ('exponential', 'linear', 'double exponential')
    ratio = res.values['intensity'][0] / every.values['intensity'][0]
    assert np.all(ratio > 0.5) and np.std(ratio) / np.mean(ratio) < 0.02
