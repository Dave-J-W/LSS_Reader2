"""#188 (2026-11-27): a first frame far from the next ones flattens a burn's
weighted line (a private GID burn: 0.50 of the next three, about 30 sigma low;
the intensity's linear change -2.9 % with it, -12.9 % without). The burn test
flags it with the change both ways and keeps the frame: leaving it out
changes verdicts, which is the owner's decision."""
import math

import matplotlib
import matplotlib.figure
import numpy as np
import pytest

from lss_core import burn, trends

matplotlib.use('Agg')


def _decline(n=51, total=-0.12, sigma=0.01, first=None, seed=3):
    """A burn whose value falls linearly by ``total`` over n frames, with
    relative errors ``sigma``; ``first``: the first frame's value instead."""
    rng = np.random.default_rng(seed)
    t = np.linspace(5, 520, n)
    truth = 1.0 + total * t / 525.0
    y = truth * (1 + sigma * rng.standard_normal(n))
    s = sigma * truth
    if first is not None:
        y[0] = first
    return t, y, s


def test_a_low_first_frame_is_flagged_and_its_effect_given():
    t, y, s = _decline(first=0.5)
    f = burn.first_frame_check(t, y, s, 525.0, models=trends.MODELS)
    assert f is not None and f['ratio'] == pytest.approx(0.5, abs=0.03) and f['z'] < -30
    (w, we), (wo, woe) = f['with'], f['without']
    assert abs(wo - (-0.12)) < 3 * woe                  # without it, the truth comes back
    assert w > wo + 3 * woe                             # with it, the line is flatter (P4's case)


def test_a_clean_burn_is_not_flagged():
    for seed in range(5):
        t, y, s = _decline(seed=seed)
        assert burn.first_frame_check(t, y, s, 525.0) is None
    t, y, s = _decline(first=None)
    y[0] *= 1.1                                         # 10 % off: under the 20 % threshold
    assert burn.first_frame_check(t, y, s, 525.0) is None
    t, y, s = _decline(sigma=0.2, first=0.5)            # 50 % off but only 2.5 sigma: not flagged
    assert burn.first_frame_check(t, y, s, 525.0) is None


def test_linear_change_is_the_slope_over_the_span():
    f = trends.compare(np.arange(10.0), 2.0 - 0.1 * np.arange(10.0), np.full(10, 0.01), t0=0.0).fits['linear']
    v, e = burn.linear_change(f, 10.0)
    assert v == pytest.approx(-0.5, rel=1e-6) and e > 0
    assert all(math.isnan(x) for x in burn.linear_change(None, 10.0))


def _result(first):
    t, y, s = _decline(first=first)
    res = burn.BurnResult(scan=1, kind='gid', t=t, time='clock', points=list(range(len(t))))
    res.values = {'intensity': (y, s), 'fwhm': (np.full_like(y, 0.02), np.full_like(y, 2e-4))}
    res.seconds = np.full(len(t), 10.0)
    res.trends = burn.analyse(res.x, res.values, errors='scatter')
    return res


def test_the_note_and_the_ring_on_the_plot():
    res = _result(0.5)
    notes = burn.first_frame_notes(res, models=trends.MODELS, errors='scatter')
    assert list(res.first_frame) == ['intensity'] and len(notes) == 1
    assert notes[0].startswith('first frame: Intensity 0.5') and 'kept; #188' in notes[0]
    assert res.first_frame['intensity']['ratio'] == pytest.approx(0.5, abs=0.03)
    fig = matplotlib.figure.Figure()
    axes = burn.plot(res, fig)
    rings = [ln for ln in axes[0].lines if ln.get_markeredgecolor() == 'k' and ln.get_markerfacecolor() == 'none']
    assert len(rings) == 1 and rings[0].get_xdata()[0] == res.x[0]
    clean = _result(None)
    assert burn.first_frame_notes(clean, errors='scatter') == [] and clean.first_frame == {}


def test_the_public_burns_are_not_flagged():
    """NX school burns 14 and 15: their first frames are within 3 % of the next three."""
    from lss_core.experiment import Experiment
    exp = Experiment('sample_data/NX_school/2026sep/20260923')
    for n in (14, 15):
        r = exp.burn(n)
        assert r.first_frame == {} and not any(x.startswith('first frame') for x in r.notes)
