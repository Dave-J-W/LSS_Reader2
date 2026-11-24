"""lss_core.display: kinds, scales, robust limits, sampling and the movie's
stepping (F69, F70, F88; owner's answers Q7, Q8, Q9, Q-IMG-4 of 2026-11-23).
No Qt: the window's use of these is tested in tests/test_gui_display.py."""
import numpy as np
import pytest

from lss_core import display


def test_kinds_from_the_series_and_the_frame():
    assert display.kind_of('reflectivity', 0.0, 1e5, 0.05) == 'ref'
    assert display.kind_of('reflectivity', 0.0, 1e5, 0.0) == 'direct'
    assert display.kind_of('gid', 14.0, 1e5) == 'gid'
    assert display.kind_of('gisaxs') == 'gisaxs'
    assert display.kind_of('direct_beam') == 'direct'
    assert display.kind_of('alignment') == 'direct'
    assert display.kind_of(None) == 'other'
    assert display.kind_of('xfntr') == 'other'
    # burn tests: Det_Th above 2 degrees is GID (owner Q10, F87; lss_core.burn.is_gid)
    assert display.kind_of('burn', 2.5, 1e5) == 'burn-gid'
    assert display.kind_of('burn', 2.0, 1e5) == 'burn-ref'
    assert display.kind_of('burn', 1.5, 1e5) == 'burn-ref'
    assert display.kind_of('burn', None, 1e5) == 'burn-ref'
    # no monitor counts: a dark frame, whatever the scan
    assert display.kind_of('reflectivity', 0.0, 0.0, 0.05) == 'dark'
    assert set(display.DEFAULT_LOG) == set(display.KINDS)


def test_log_or_linear_by_kind_q8():
    for k in ('ref', 'gid', 'gisaxs', 'burn-ref', 'burn-gid'):
        assert display.default_log(k) is True
    for k in ('direct', 'dark'):
        assert display.default_log(k) is False


def test_viridis_by_default_and_jet_still_offered():
    assert display.DEFAULT_CMAP == 'viridis' and display.CMAPS[0] == 'viridis'
    assert 'jet' in display.CMAPS and 'magma' in display.CMAPS
    assert display.INTERPOLATION == 'nearest'


def test_sampling_rule():
    assert display.sample(41, 4) == [0, 13, 27, 40]          # the example of image_display.md 2.1
    assert display.sample(3, 4) == [0, 1, 2]
    assert display.sample(10, 1) == [0]
    assert display.sample(5, 4) == [0, 1, 3, 4]
    assert display.sample(0, 4) == [] and display.sample(5, 0) == []
    for n_sel in range(1, 60):
        for n in range(1, 7):
            s = display.sample(n_sel, n)
            assert s[0] == 0 and s[-1] == (n_sel - 1 if n > 1 else 0)
            assert s == sorted(set(s)) and len(s) == min(n, n_sel)


def test_mode_for_the_selection_q7():
    assert display.MOVIE_MIN_FRAMES == 3
    assert display.mode_for(1) == 'tiles' and display.mode_for(2) == 'tiles'
    assert display.mode_for(3) == 'movie' and display.mode_for(41) == 'movie'
    assert display.mode_for(41, view='tiles') == 'tiles'
    assert display.mode_for(41, summed=True) == 'sum'
    assert display.tiles_title(4, 41) == '4 of 41 shown (sampled)'
    assert display.tiles_title(2, 2) == ''
    assert display.MAX_TILES == 6 and max(display.TILE_CHOICES) <= display.MAX_TILES


def test_movie_steps_and_keys_q7():
    assert display.step(0, -1, 5) == 0 and display.step(4, 1, 5) == 4        # held at the ends
    assert display.step(0, -1, 5, loop=True) == 4 and display.step(4, 1, 5, loop=True) == 0
    assert display.step(2, 1, 5) == 3
    assert display.key_action('space') == 'toggle'
    for k in ('up', 'back', 'left'):
        assert display.key_action(k) == -1
    for k in ('down', 'forward', 'right'):
        assert display.key_action(k) == 1
    assert display.key_action('a') is None


def test_robust_limits_leave_out_the_direct_beam():
    """A frame like NX scan 7 frame 0: mostly zeros, a weak reflected beam and
    a direct beam 100 times brighter. Masking the direct beam puts the top of
    the scale on the rest of the frame."""
    rng = np.random.default_rng(1)
    f = rng.poisson(0.05, size=(487, 195)).astype(float)
    f[50:56, 40:52] += 2000.0                                 # reflected beam
    f[28:35, 40:55] += 2e5                                    # direct beam (105 pixels, more than 0.1 %)
    f[100, 100] = -2.0                                        # a Pilatus bad-pixel marker
    row, col = 31.0, 47.0
    m = display.beam_mask(f.shape, row, col)
    assert m[28:35, 40:55].all() and not m[50:56, 40:52].any()
    lo, hi = display.robust_limits([f], log=False, masks=[m])
    lo_all, hi_all = display.robust_limits([f], log=False)
    assert hi_all > 1e5 and hi < 3000.0                       # the direct beam is out of the percentile
    assert lo == 0.0
    llo, lhi = display.robust_limits([f], log=True, masks=[m])
    assert 0 < llo <= 1.0 and lhi == pytest.approx(hi)        # log: the floor is on positive pixels
    # a selection shares one scale (Q-IMG-4): limits over every frame
    g = f / 10.0
    slo, shi = display.robust_limits([f, g], log=True, masks=[m, m])
    assert llo / 10.0 <= slo <= llo and shi <= lhi


def test_robust_limits_are_always_drawable():
    for frames in ([np.zeros((5, 5))], [np.full((4, 4), np.nan)], [np.full((3, 3), -2.0)], []):
        for log in (False, True):
            lo, hi = display.robust_limits(frames, log=log)
            assert np.isfinite(lo) and np.isfinite(hi) and hi > lo
            if log:
                assert lo > 0
    lo, hi = display.robust_limits([np.full((3, 3), 7.0)], log=False)
    assert hi > lo


def test_safe_limits_never_take_the_log_of_a_negative():
    """image_display.md 1.2: a Min of -2 made the log norm NaN (a binary mask)."""
    assert display.safe_limits(-2.0, 1000.0, True) == (1.0, 1000.0)
    assert display.safe_limits(-2.0, 1000.0, False) == (-2.0, 1000.0)
    assert display.safe_limits(5.0, 1.0, False) == (1.0, 5.0)
    lo, hi = display.safe_limits(3.0, 3.0, True)
    assert 0 < lo < hi
    assert display.safe_limits(0.0, -1.0, True) == (0.1, 1.0)
    assert display.safe_limits(float('nan'), 1.0, False) == (0.0, 1.0)


def test_sliders_include_the_low_end_and_follow_the_scale():
    """Before: the slider gave pos x (max - min) / 100, without adding min."""
    assert display.slider_value(0, 10.0, 110.0, False) == 10.0
    assert display.slider_value(100, 10.0, 110.0, False) == 110.0
    assert display.slider_value(50, 10.0, 110.0, False) == 60.0
    assert display.slider_value(50, 1.0, 1e4, True) == pytest.approx(100.0)
    for log in (False, True):
        for pos in (0, 13, 50, 99, 100):
            v = display.slider_value(pos, 2.0, 2e5, log)
            assert display.slider_position(v, 2.0, 2e5, log) == pos
    assert display.slider_position(-5.0, 1.0, 10.0, True) == 0
    assert display.slider_position(1e9, 1.0, 10.0, False) == 100
    assert display.slider_position(1.0, 1.0, 1.0, False) == 0


def test_data_range():
    assert display.data_range([np.array([[0.0, 2.0], [5.0, -2.0]])]) == (2.0, 5.0)
    assert display.data_range([np.zeros((2, 2))]) == (1.0, 10.0)


def test_direct_beam_pixel_geometry():
    """Reflectivity: the direct beam lies 2 alpha D / pixel rows below the
    reflected beam (row ycenter); GID: Det_Th D / pixel columns to the side."""
    a, D = 0.00345, 551.0
    row, col = display.direct_beam_pixel(47.0, 53.0, a, a, 0.0, D)
    assert col == 47.0 and row == pytest.approx(53.0 - 2 * a * D / 0.172, rel=1e-6)
    row, col = display.direct_beam_pixel(47.0, 53.0, 0.0, 0.0, np.radians(14.0), 271.0)
    assert col < -300                                          # far off the frame
    assert not display.beam_mask((487, 195), row, col).any()


def test_convert_limits_between_axes():
    assert display.convert_limits((10.0, 20.0), (0.0, 100.0), (1.0, 2.0)) == pytest.approx((1.1, 1.2))
    assert display.convert_limits((1.1, 1.2), (1.0, 2.0), (0.0, 100.0)) == pytest.approx((10.0, 20.0))
    assert display.convert_limits((3.0, 4.0), (5.0, 5.0), (0.0, 1.0)) == (0.0, 1.0)


def test_frame_text():
    t = display.frame_text(7, 3, 'ref', qz=0.0425, tth_deg=0.0, t_s=12.4, absorber=3, monc=1.2e5)
    assert t == 'S# 7 · pt 3 · Qz 0.0425 1/Å · t 12 s · abs 3 · Monc 1.2e+05'
    t = display.frame_text(11, 13, 'gid', qz=0.0, tth_deg=18.4, absorber=0, monc=2e5)
    assert '2θ 18.40°' in t and 'Qz' not in t and ' t ' not in t
    assert display.units() == 'counts / Monc, absorber-corrected'
    assert display.units(True).endswith('minus background')
