"""Burn tests as trends over time (lss_core.burn; owner, 2026-11-21, F22a
3-4, P30): per-frame quantities per monitor count, measured times, the
strongest GID peak found automatically, and the model comparison."""
import math
import os

import numpy as np
import pytest

import synth
from lss_core import burn, trends
from lss_core.timing import PointTimes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
G = 2 * math.sqrt(2 * math.log(2))


def test_frame_times_exposure_and_clock():
    cols = {'Seconds': np.array([10.0, 10.0, 10.0, 5.0])}
    t, note = burn.frame_times(cols, None, [0, 1, 2, 3], 'exposure')
    assert t.tolist() == [5.0, 15.0, 25.0, 32.5] and 'exposure' in note
    pt = PointTimes('old', start=np.array([100.0, 110.5, 121.0, 131.5]))
    t, note = burn.frame_times(cols, pt, [1, 2, 3], 'clock')
    assert t.tolist() == [5.0, 15.5, 23.5] and 'clock' in note
    t, note = burn.frame_times(cols, PointTimes('none'), [0, 1])          # clock is the default
    assert t.tolist() == [5.0, 15.0] and 'no per-point times' in note and note.startswith('exposure')
    with pytest.raises(ValueError):
        burn.frame_times(cols, None, [0], 'wall')


def test_reflectivity_burn_is_monitor_normalised_and_finds_tau(tmp_path):
    """Synthetic reflectivity burn (τ = 400 s): the exponential wins and the
    5 % time is τ·ln(1/0.95) = 20.5 s."""
    from lss_core.experiment import Experiment
    exp = Experiment(synth.make_burn_dataset(tmp_path / 'burn'))
    res = exp.burn(1)
    assert res.kind == 'reflectivity' and res.time == 'exposure'      # clock asked; no per-point times in this file
    assert 'clock asked' in res.notes[0]
    c = res.trends['intensity']
    assert c.best == 'exponential' and not c.stable
    f = c.fits['exponential']
    assert -1 / f.params[1] == pytest.approx(synth.BURN_TAU, rel=1e-3)
    assert c.change.best == pytest.approx(-synth.BURN_TAU * math.log(0.95), rel=1e-3)
    assert res.safe_time()[1] == 'intensity'
    assert res.duration() == pytest.approx(synth.BURN_FRAMES * synth.BURN_CTIME)
    cols, arr = res.data()
    assert cols == ['time_s', 'intensity', 'intensity_err'] and arr.shape == (synth.BURN_FRAMES, 3)
    assert 'Burn test, scan 1 (reflectivity)' in res.summary()
    assert {r['model'] for r in res.table()} == set(trends.MODELS)
    few = exp.burn(1, points=[0, 1, 2, 3, 4], models=('constant', 'linear'))
    assert set(few.trends['intensity'].fits) == {'constant', 'linear'}
    with pytest.raises(ValueError):
        exp.burn(1, points=[0, 1])


def _gid_profiles(n=21, decay=0.2, shift=0.0, grow=0.0, seed=0):
    """Horizontal GID profiles like a pinhole frame's: a lit box of columns,
    a broad shoulder and a sharp peak, Poisson-like noise."""
    x = np.linspace(1.30, 1.92, 195)
    lit = ((x > 1.39) & (x < 1.74)).astype(float)
    rng = np.random.default_rng(seed)
    out = []
    for k in range(n):
        f = k / (n - 1)
        c = 1.466 + shift * f
        w = 0.016 * (1 + grow * f)
        peak = (1 - decay * f) * 0.02 * np.exp(-0.5 * ((x - c) / (w / G)) ** 2)
        shoulder = 0.008 * np.exp(-0.5 * ((x - 1.47) / 0.04) ** 2)
        mu = lit * (0.003 + shoulder) + peak * lit
        s = np.sqrt(mu * 2e-5 + 1e-11)          # about 2 % on a frame's intensity, as NX scan 14
        out.append(np.column_stack([x, mu + rng.normal(0, 1, x.size) * s, s]))
    return out


@pytest.mark.parametrize('estimator', burn.ESTIMATORS)
def test_gid_peak_is_found_and_followed(estimator):
    prof = _gid_profiles(decay=0.2, shift=0.0, grow=0.0)
    values, ref, window, details = burn.measure_gid(prof, estimator=estimator)
    assert window[0] > 1.39 and window[1] < 1.74 and window[0] < 1.466 < window[1]
    assert ref['centre'] == pytest.approx(1.466, abs=0.003)
    t = np.arange(21) * 10.0 + 5
    res = burn.analyse(t, values)
    assert set(res) == {'intensity', 'centre', 'fwhm'}
    i = values['intensity'][0]
    # the sharp peak loses 20 %: every estimator sees the intensity fall (moments and fit less, since
    # their window sum or fit also holds part of the steady shoulder); the position holds
    assert i[-3:].mean() < 0.95 * i[:3].mean() and not res['intensity'].stable
    if estimator != 'fit':
        assert res['centre'].stable
    # 'fit': one Gaussian across the sharp peak and the shoulder moves as the peak fades
    # (a misfit artefact, as on the real frames: chi2/dof 10-40)
    if estimator == 'template':
        assert i[-1] / i[0] == pytest.approx(0.8, abs=0.08)
        assert res['fwhm'].stable                          # the shape's width is unchanged
        assert all(d['chi2_dof'] < 2 for d in details)
    assert res['centre'].change.scale == pytest.approx(np.nanmean(values['fwhm'][0]))


def test_a_strong_peak_does_not_shrink_the_lit_part():
    """The lit columns (burn._illuminated, 2026-11-24): on a floor under 5 %
    of the peak the maximum alone left the floor out, and the window shrank
    to the peak's core (found with the GID-burn rows of Q-BURN-6, which
    lower the floor). Half the median keeps the floor lit; where the floor is
    above 10 % of the peak (these profiles, NX 14 and 15) nothing changes."""
    prof = _gid_profiles(decay=0.0)
    mean = np.mean([p[:, 1] for p in prof], axis=0)
    old = np.flatnonzero(mean > 0.05 * mean.max())
    assert burn._illuminated(mean) == (old[0] + 2, old[-1] - 2)            # unchanged with a 10 % floor
    x = prof[0][:, 0]
    lit = (x > 1.39) & (x < 1.74)
    weak = []
    for p in prof:                                                            # the floor and shoulder ÷ 30
        q = p.copy()
        q[:, 1] = np.where(lit, p[:, 1] - 0.003 - 0.008 * np.exp(-0.5 * ((x - 1.47) / 0.04) ** 2), 0.0) + \
            lit * 1e-4
        weak.append(q)
    wm = np.mean([p[:, 1] for p in weak], axis=0)
    first, last = burn._illuminated(wm)
    assert x[first] == pytest.approx(1.39, abs=0.01) and x[last] == pytest.approx(1.74, abs=0.01)
    window = burn.measure_gid(weak)[2]
    assert window[1] - window[0] > 4 * 0.016                                 # ± 3 FWHM, not the peak's core


def test_gid_typed_range_and_a_moving_peak():
    prof = _gid_profiles(decay=0.0, shift=0.004, grow=0.0, seed=3)
    values, ref, window, _ = burn.measure_gid(prof, qxy_range=(1.42, 1.52))
    assert window == (1.42, 1.52)
    c = values['centre'][0]
    assert c[-1] - c[0] == pytest.approx(0.004, abs=0.0005)
    # the legacy moments: the centroid of everything in the window, so the steady shoulder
    # dilutes the peak's shift (0.0023 of 0.004 with the automatic window, when written)
    m = burn.measure_gid(prof, estimator='moments')[0]['centre'][0]
    assert 0.001 < m[-1] - m[0] < 0.003
    res = burn.analyse(np.arange(21) * 10.0 + 5, values)
    assert not res['centre'].stable and res['intensity'].stable
    with pytest.raises(ValueError):
        burn.measure_gid(prof, estimator='median')
    flat = [np.column_stack([p[:, 0], np.full(len(p), 1.0), np.full(len(p), 0.01)]) for p in prof]
    with pytest.raises(ValueError):
        burn.measure_gid(flat)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_nx_school_burn_pair():
    """NX school scans 14 and 15: the same spot and geometry, absorber 12
    then 8 (about 4 × the flux in 15). As measured 2026-11-21 (template, the
    default; errors from the scatter): the integrated intensity is stable
    in both; the position drifts in both (about 0.002 Å⁻¹ in 14, 0.008 in
    15); the width is stable in 14 and grows in 15. Template frames fit to
    χ²/dof about 1 on 14. The legacy moments agree on intensity and width
    and are about 3 × noisier in position."""
    from lss_core.experiment import Experiment
    exp = Experiment(NX)
    r14 = exp.burn(14)
    assert r14.kind == 'gid' and len(r14.t) == 21 and r14.trend_errors == 'scatter'
    assert all(d['chi2_dof'] < 2 for d in r14.frame_fits)
    assert r14.trends['intensity'].stable and r14.trends['fwhm'].stable and not r14.trends['centre'].stable
    assert r14.window[0] == pytest.approx(1.40, abs=0.01) and r14.window[1] == pytest.approx(1.53, abs=0.01)
    r15 = exp.burn(15)
    assert r15.trends['intensity'].stable and not r15.trends['fwhm'].stable and not r15.trends['centre'].stable
    w = r15.values['fwhm'][0]
    assert w[-3:].mean() > 1.1 * w[:3].mean()
    c14, c15 = r14.values['centre'][0], r15.values['centre'][0]
    assert c14[-1] - c14[0] == pytest.approx(0.0024, abs=0.0012)
    assert c15[-1] - c15[0] == pytest.approx(0.008, abs=0.002)
    m14, m15 = exp.burn(14, estimator='moments'), exp.burn(15, estimator='moments')
    assert m14.trends['intensity'].stable and m15.trends['intensity'].stable and not m15.trends['fwhm'].stable

    def spread(r):
        c = r.trends['centre']
        return np.std(c.y - c.fits[c.best](c.t))
    assert spread(r14) < 0.5 * spread(m14)                # the template follows the position more closely
    assert r14.time == 'clock'                           # the default (owner: wall time is better)
    exposure = exp.burn(14, time='exposure')
    assert r14.t[-1] > exposure.t[-1]                    # the clock includes the overhead between frames
    assert r14.safe_time()[1] in ('intensity', 'fwhm')   # the position does not set the limit by default
    assert exp.burn(14, limit=('intensity', 'fwhm', 'centre')).safe_time()[1] == 'centre'
    counting = exp.burn(14, trend_errors='given')
    assert counting.trend_errors == 'given' and counting.trends['intensity'].criterion in ('AICc', 'QAICc')


def test_burn_scans_are_ih_scans_that_do_not_move():
    """The beamline's standard (owner, 2026-11-21)."""
    from lss_core import series
    assert series.is_burn('ascan  ih -0.994512 -0.994512  20 10')
    assert not series.is_burn('ascan  ih -1 1  20 1')                 # moves: alignment
    assert not series.is_burn('ascan  oh 0 0  20 1')                  # another motor
    assert not series.is_burn('ascan  ih 0 0  1 1')                   # two points: not a trend
    assert not series.is_burn('hklscan 0 0 0 0 0.01 0.5 40 1')


def test_burn_kind_follows_det_th_above_two_degrees():
    """Owner, 2026-11-23 (Q10, F87): a GID burn when Det_Th > 2 degrees, else a
    reflectivity burn; the threshold was 0.001 degree."""
    from lss_core import burn as burnmod
    assert burnmod.GID_BURN_MIN_DTH_DEG == 2.0
    assert not burnmod.is_gid(0.0) and not burnmod.is_gid(0.5) and not burnmod.is_gid(2.0) and not burnmod.is_gid(-1.9)
    assert burnmod.is_gid(2.01) and burnmod.is_gid(16.0) and burnmod.is_gid(-3.0)
