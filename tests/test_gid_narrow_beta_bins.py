"""A GID level whose 2θ bins share no common β range (2026-11-27). Found on a
private survey set: a few 2θ bins of the upper level saw only the top rows of
the β range, so no β bin was seen by every bin, the level kept no β rows and
the join stopped on "zero-size array to reduction operation maximum".

The fix (only when the old rule leaves no β row): keep the β window that keeps
the most map cells, drop the 2θ bins that do not see all of it, and count them
in info['narrow_bins_dropped']. Known truth: synthetic pinhole frames whose
expected counts are monitor × T(2θ, β), so the map ÷ T is 1."""
import numpy as np
import pytest

from lss_core import pinhole as ph
from test_gid_unscaled_seams import _level, truth


def _shifted_level(shift_deg, seed=1):
    """Frames at 2θ arm 14–17° with the arm at β0 3°, then 17.1–17.7° with β0
    3° + shift. With an 8° shift the last bins see β 10.5° and up only, beyond
    the top of the first group's range: no β bin is common to every 2θ bin."""
    rng = np.random.default_rng(seed)
    return (_level(np.arange(14, 17.01, 0.1), 3.0, 1.0, rng)
            + _level(np.arange(17.1, 17.71, 0.1), 3.0 + shift_deg, 1.0, rng))


def test_widest_common_window_keeps_the_most_cells():
    seen = np.zeros((6, 20), bool)
    seen[:4, 2:15] = True          # four wide bins: β 2…14
    seen[4:, 12:20] = True         # two that see only β 12…19
    assert ph._widest_common_window(seen) == (2, 14)          # 4 × 13 = 52 beats 6 × 3 = 18
    seen[1, 9] = False                                         # a hole: that row's longest run is 10…14
    assert ph._widest_common_window(seen) == (2, 14)          # 3 × 13 = 39 still beats 4 × 5 = 20
    assert ph._widest_common_window(np.zeros((3, 5), bool)) == (0, -1)


def test_a_level_with_no_common_beta_range_keeps_a_window_and_says_what_it_dropped():
    tt, beta, I, S, info = ph.level_map(_shifted_level(8.0), 15, 486, response='none', area=False, pol=False)
    assert len(beta) > 100                                     # before the fix: 0 rows
    assert info['narrow_bins_dropped'] > 0
    assert int(info['keep'].sum()) == len(tt)
    rel = (I / 1e6) / truth(tt[:, None], beta[None, :])
    assert np.nanmean(rel) == pytest.approx(1.0, abs=0.003)    # nothing rescaled
    assert np.all(np.isfinite(I))


def test_levels_that_had_a_common_beta_range_are_unchanged():
    """The fallback runs only when the old rule left no β row: a 5° shift still
    has a common range, nothing is dropped, and the level keeps that range."""
    tt, beta, I, S, info = ph.level_map(_shifted_level(5.0), 15, 486, response='none', area=False, pol=False)
    assert info['narrow_bins_dropped'] == 0
    assert np.all(info['all_weights'][info['keep']] > 0)       # every kept bin sees every kept row


def test_such_a_level_now_joins_the_level_below():
    rng = np.random.default_rng(7)
    low = _level(np.arange(14, 17.71, 0.1), 0.09, 1.0, rng)
    high = _shifted_level(8.0, seed=8)
    edges = ph.shared_edges(low + high)
    infos = [ph.level_map(x, 15, 486, response='none', area=False, pol=False, edges=edges)[4] for x in (low, high)]
    log = []
    tt, beta, I, S, info = ph.join_levels(infos, log=log, labels=['low', 'high'])
    (entry,) = [e for e in log if e.get('kind') == 'vertical (beta)']
    assert entry['points'] > 0 and entry['factor'] == pytest.approx(1.0, abs=0.01)
    rel = (I / 1e6) / truth(tt[:, None], beta[None, :])
    assert np.nanmean(rel) == pytest.approx(1.0, abs=0.003)


def test_a_level_with_no_beta_rows_is_named_not_a_numpy_error():
    rng = np.random.default_rng(3)
    levels = [_level(np.arange(14, 17.01, 0.1), b0, 1.0, rng) for b0 in (0.09, 3.0)]
    edges = ph.shared_edges(levels[0] + levels[1])
    infos = [ph.level_map(x, 15, 486, response='none', area=False, pol=False, edges=edges)[4] for x in levels]
    infos[1] = dict(infos[1], beta=infos[1]['beta'][:0])
    with pytest.raises(ValueError, match='high has no beta rows'):
        ph.join_levels(infos, labels=['low', 'high'])
