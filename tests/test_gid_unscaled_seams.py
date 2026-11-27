"""The GID stopgap for Qz levels that share no β (owner, 2026-11-26): opt-in
``unmatched='unscaled'`` adds such a level as collected, marks the seam and
changes nothing else. Known truth: synthetic pinhole frames whose expected
counts are monitor × efficiency × T(2θ, β), so the joined map ÷ T is each
level's efficiency (1 where the monitor is right) and nothing rescales it."""
import math

import numpy as np
import pytest

from lss_core import gid as gm
from lss_core import pinhole as ph

NR, NC = 487, 195


def truth(t, b):
    return 2e-4 * (1 + 2 * np.exp(-((t - 16.5) / 0.3) ** 2)) * (1 + 0.1 * b)


def _level(dths, beta0_deg, eff, rng, monitor=1e6):
    out = []
    for d in dths:
        g = ph.FrameGeometry(dth=math.radians(d), alpha=math.radians(0.09), beta0=math.radians(beta0_deg),
                             c0=47.0, r0=53.0, d_sample=551.0, d_pinhole=271.0, g_l3=556.0, wavelength=1.24)
        tt, bb = (np.degrees(a) for a in ph.pixel_angles(g, np.arange(NR), np.arange(NC)))
        out.append(ph.PinholeFrame(rng.poisson(monitor * eff * truth(tt, bb)).astype(float), monitor, g,
                                   (2.0, 0.1, 0.2, math.radians(0.09), 551.0, 271.0), (3.0, 14.0), 678.0, 1))
    return out


def _infos(beta0_high, eff_high, response='none', seed=3):
    """A level at the horizon (β −0.6…7.6°) and one with the arm at ``beta0_high``
    (10°: β 9.8…17.2°, no overlap; 3°: overlapping)."""
    rng = np.random.default_rng(seed)
    a = _level(np.arange(14.0, 17.01, 0.1), 0.09, 1.0, rng)
    b = _level(np.arange(14.5, 17.51, 0.1), beta0_high, eff_high, rng)
    edges = ph.shared_edges(a + b)
    return [ph.level_map(x, 15, 486, response=response, area=False, pol=False, edges=edges)[4] for x in (a, b)]


def test_by_default_levels_without_overlap_are_refused():
    infos = _infos(10.0, 1.0)
    with pytest.raises(ValueError, match='does not overlap in beta'):
        ph.join_levels(infos)
    assert gm.GIDParams().unmatched_levels == 'refuse'


def test_unscaled_levels_are_added_as_collected_and_the_seam_is_marked():
    """Known truth: both levels on T (efficiency 1), so the map ÷ T is 1 on both
    sides of the seam; the seam is listed with its β gap, the factor is 1 with
    no error, and the log entry says UNSCALED."""
    infos = _infos(10.0, 1.0)
    log = []
    tt, beta, I, S, info = ph.join_levels(infos, log=log, labels=['low', 'high'], unmatched='unscaled')
    rel = (I / 1e6) / truth(tt[:, None], beta[None, :])
    assert np.nanmean(rel[:, beta < 8.5]) == pytest.approx(1.0, abs=0.003)
    assert np.nanmean(rel[:, beta > 8.5]) == pytest.approx(1.0, abs=0.003)
    (seam,) = info['unscaled_seams']
    assert seam['below'] == 'low' and seam['level'] == 'high'
    assert seam['beta_below_deg'] < 8.0 < 9.5 < seam['beta_above_deg'] and seam['gap_deg'] > 1.5
    # the edge ratio is a diagnostic: here the truth's own change across the 2.2° gap (1.124)
    t_ratio = truth(16.0, seam['beta_above_deg']) / truth(16.0, seam['beta_below_deg'])
    assert seam['edge_ratio'] == pytest.approx(t_ratio, rel=0.01)
    fac, err = info['factors']['high']
    assert fac == 1.0 and math.isnan(err)
    (entry,) = log
    assert entry['unscaled'] and entry['kind'] == 'vertical (beta), unscaled' and 'UNSCALED' in entry['label']
    assert entry['points'] == 0 and not entry['applied']


def test_a_wrong_monitor_shows_as_a_step_and_is_not_hidden():
    """The tradeoff: the upper level's monitor reads 25 % high (efficiency 0.8).
    No factor corrects it: the upper side is 0.8 × T, and the edge ratio drops
    by the same 0.8 (it cannot tell this from a real change across the gap)."""
    infos = _infos(10.0, 0.8)
    tt, beta, I, S, info = ph.join_levels(infos, unmatched='unscaled')
    rel = (I / 1e6) / truth(tt[:, None], beta[None, :])
    assert np.nanmean(rel[:, beta < 8.5]) == pytest.approx(1.0, abs=0.003)
    assert np.nanmean(rel[:, beta > 8.5]) == pytest.approx(0.8, abs=0.003)
    (seam,) = info['unscaled_seams']
    t_ratio = truth(16.0, seam['beta_above_deg']) / truth(16.0, seam['beta_below_deg'])
    assert seam['edge_ratio'] / t_ratio == pytest.approx(0.8, rel=0.01)


def test_counts_are_conserved_and_errors_are_counting_only():
    infos = _infos(10.0, 1.0)
    tt, beta, I, S, info = ph.join_levels(infos, 'union', unmatched='unscaled')
    total = sum(lv['all_counts'][lv['keep']].sum() for lv in infos)
    assert info['sum_counts'].sum() == pytest.approx(total)
    n, w = info['sum_counts'], info['sum_weights']
    with np.errstate(invalid='ignore', divide='ignore'):
        expect = np.where(w > 0, np.sqrt(n) / w, np.nan) * np.mean([lv['mean_monitor'] for lv in infos])
    assert np.allclose(S, expect, equal_nan=True)


def test_levels_that_overlap_are_joined_as_before():
    """Opt-in changes nothing where a factor can be fitted."""
    infos = _infos(3.0, 0.8)
    a = ph.join_levels(infos)
    b = ph.join_levels(infos, unmatched='unscaled')
    for x, y in zip(a[:4], b[:4]):
        assert np.array_equal(x, y, equal_nan=True)
    assert a[4]['factors'] == b[4]['factors'] and b[4]['unscaled_seams'] == []


def test_an_unknown_choice_is_refused():
    with pytest.raises(ValueError, match="unmatched"):
        ph.join_levels(_infos(3.0, 1.0), unmatched='scaled')


def test_seam_note_labels_saved_files_only_when_a_seam_is_unscaled(tmp_path):
    infos = _infos(10.0, 1.0)
    tt, beta, I, S, info = ph.join_levels(infos, labels=['low Qz', 'middle Qz'], unmatched='unscaled')
    note = gm.seam_note(info)
    assert note.startswith('UNSCALED ACROSS 1 SEAM:') and 'middle Qz on low Qz' in note
    assert gm.seam_note(ph.join_levels(_infos(3.0, 1.0))[4]) == '' and gm.seam_note(None) == ''
    prod = dict(axes='Angles', x=np.zeros((2, 2)), y=np.zeros((2, 2)), data=np.ones((2, 2)), err=np.ones((2, 2)),
                h=np.ones((2, 3)), v=np.ones((2, 3)))
    plain = gm.save(str(tmp_path / 'a'), prod)
    marked = gm.save(str(tmp_path / 'b'), prod, note=note)
    for p, q in zip(plain, marked):
        a, b = open(p).read(), open(q).read()
        assert not a.startswith('#') and b.startswith('# UNSCALED ACROSS 1 SEAM')
        assert b.split('\n', 1)[1] == a                          # the data lines are the same
        assert np.array_equal(np.loadtxt(p), np.loadtxt(q))       # and read back alike


def test_the_patch_refuses_with_a_hint_and_joins_when_asked(monkeypatch):
    """gid.pinhole_patch: by default the GIDError names the stopgap; with
    GIDParams(unmatched_levels='unscaled') the patch is made and its join info
    carries the seam."""

    def fake_frames(frames, params):
        rng = np.random.default_rng(3)
        return [_level(np.arange(14.0, 17.01, 0.1), 0.09, 1.0, rng), _level(np.arange(14.5, 17.51, 0.1), 10.0, 1.0, rng)]
    monkeypatch.setattr(gm, 'pinhole_frames', fake_frames)
    with pytest.raises(gm.GIDError, match='Join levels without overlap'):
        gm.pinhole_patch([], gm.GIDParams(response='none', area_correction=False, polarisation=False))
    patch, levels, level_info, jinfo = gm.pinhole_patch(
        [], gm.GIDParams(response='none', area_correction=False, polarisation=False, unmatched_levels='unscaled'))
    assert len(jinfo['unscaled_seams']) == 1 and jinfo['unscaled_seams'][0]['level'] == 'middle Qz'
    assert len(patch) > 0 and gm.seam_note(jinfo).startswith('UNSCALED')
