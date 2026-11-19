"""Pinhole-geometry GID (F45; lss_core/pinhole.py; specification:
docs/handoff_out/04-answer/IDL_REVIEW.md §7, tests T2-T9 there).

Synthetic tests use a 100K-sized frame: 487 rows × 195 columns."""
import math
import os

import numpy as np
import pytest

from lss_core import pinhole as ph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
NR, NC = 487, 195


def _geom(dth_deg, d_p=271.0, d_s=551.0, c0=47.0, r0=53.0):
    return ph.FrameGeometry(dth=math.radians(dth_deg), alpha=math.radians(0.09), beta0=math.radians(0.09),
                            c0=c0, r0=r0, d_sample=d_s, d_pinhole=d_p, g_l3=556.0, wavelength=1.24)


def _frames(dths, intensity, d_p=271.0, monitor=1e5, rng=None, response=None, d_true=None):
    """Frames whose expected counts are monitor × response(c) × intensity(2θ_c)
    (no area or polarisation), Poisson-drawn when ``rng`` is given."""
    out = []
    for d in dths:
        g = _geom(d, d_p)
        tt = np.degrees(ph.column_two_theta(NC, _geom(d, d_true or d_p)))
        mu = monitor * intensity(tt)[None, :] * np.ones((NR, 1))
        if response is not None:
            mu = mu * response[None, :]
        n = rng.poisson(mu).astype(float) if rng is not None else mu
        out.append(ph.PinholeFrame(n, monitor, g, (2.0, 0.1, 0.2, math.radians(0.09), 551.0, d_p),
                                   (3.0, 14.0), 678.0, 1))
    return out


def test_angles_and_vertical_distance():
    g = _geom(15.0)
    tt = ph.column_two_theta(NC, g)
    assert tt[47] == pytest.approx(math.radians(15.0))
    assert np.degrees(tt[47 + 10] - tt[47]) == pytest.approx(math.degrees(math.atan(1.72 / 271)))
    assert ph.vertical_distance(g) == pytest.approx(551 + 556 * (1 / math.cos(math.radians(0.09)) - 1))
    g12 = ph.FrameGeometry(dth=0.3, alpha=0.0016, beta0=math.radians(6.5), c0=47, r0=53, d_sample=551,
                           d_pinhole=271, g_l3=556)
    assert ph.vertical_distance(g12) - 551 == pytest.approx(3.6, abs=0.05)   # 556 (1/cos 6.5° − 1)


def test_s5_window_is_asymmetric_and_matches_nx_lit_columns():
    lo, hi = ph.s5_window(_geom(15.0), 3.0, 14.0)
    assert (lo, hi) == pytest.approx((27.2, 139.3), abs=0.1)        # measured lit 29-137 on NX scan 11


def test_counts_are_conserved_and_bins_are_count_over_weight():
    rng = np.random.default_rng(1)
    fr = _frames(np.arange(14, 18, 0.1), lambda t: 1e-4 * (1 + 0 * t), rng=rng)
    theta = np.array([np.degrees(ph.column_two_theta(NC, f.geom)) for f in fr])
    n = np.array([f.counts[15:487] for f in fr])
    w = np.ones_like(n) * 1e5
    edges = np.linspace(theta.min() - 0.1, theta.max() + 0.1, 300)
    i, s, sn, sw = ph.bin_counts(theta, n, w, edges)
    assert sn.sum() == pytest.approx(n.sum())
    ok = sw > 0
    assert np.allclose(i[ok] * sw[ok], sn[ok])


def test_a_sharp_line_lands_in_one_bin_whatever_the_column():
    """T4: a line at a fixed 2θ seen through the pinhole over a Det_Th scan
    is at that 2θ in every frame, so the binned peak is one bin wide."""
    t0 = 16.65
    step = math.degrees(ph.PIXEL_MM / 271)
    line = lambda t: np.where(np.abs(t - t0) < step / 2, 1e-2, 1e-5)
    fr = _frames(np.arange(14, 18.01, 0.1), line)
    tt, beta, I, S, info = ph.level_map(fr, 15, 486, response='none', area=False, pol=False)
    prof = np.nansum(I, axis=1)
    k = int(np.argmax(prof))
    assert tt[k] == pytest.approx(t0, abs=step / 2 + 1e-9)
    assert (prof > 0.5 * prof[k]).sum() <= 2                          # no smearing with ~70 columns per frame
    assert info['counts_used'] > 20 * sum(f.counts[15:487, 46:49].sum() for f in fr) / 3 / 10


def test_wrong_distance_smears_the_line():
    t0 = 16.65
    step = math.degrees(ph.PIXEL_MM / 271)
    line = lambda t: np.where(np.abs(t - t0) < step / 2, 1e-2, 1e-5)
    fr = _frames(np.arange(14, 18.01, 0.1), line, d_p=540.0, d_true=271.0)   # mapped with ~ the sample distance
    tt, beta, I, S, info = ph.level_map(fr, 15, 486, response='none', area=False, pol=False, bin_step_deg=step)
    prof = np.nansum(I, axis=1)
    assert (prof > 0.1 * prof.max()).sum() > 5


def test_low_counts_are_unbiased():
    """T6: 0.4 counts per pixel per frame, as on NX pinhole frames: the
    count-over-weight estimate is unbiased (inverse-variance weighting of
    pixels would give about 0.3 of the truth)."""
    rng = np.random.default_rng(7)
    truth = 0.4 / 1e5
    fr = _frames(np.arange(14, 18.01, 0.1), lambda t: truth + 0 * t, rng=rng)
    tt, beta, I, S, info = ph.level_map(fr, 15, 486, response='none', area=False, pol=False)
    est = I / 1e5                                                       # I is × the mean monitor
    assert np.nanmean(est) / truth == pytest.approx(1.0, abs=0.01)
    sn, sw = info['sum_counts'], info['sum_weights']
    pulls = (sn - truth * sw) / np.sqrt(truth * sw)                     # against the expected counts
    assert np.std(pulls) == pytest.approx(1.0, abs=0.05)


def test_column_response_is_recovered():
    """T7: a known hump-shaped response (as measured on NX) is recovered from
    the data to better than 1 %."""
    rng = np.random.default_rng(3)
    c = np.arange(NC)
    resp = 0.4 + np.exp(-((c - 52) / 18.0) ** 2)
    resp = resp / resp.mean()
    spectrum = lambda t: 1e-3 * (1 + 3 * np.exp(-((t - 16.65) / 0.08) ** 2) + 0.2 * (t - 14))
    fr = _frames(np.arange(14, 18.01, 0.05), spectrum, rng=rng, response=resp, monitor=1e6)
    tt, beta, I, S, info = ph.level_map(fr, 15, 486, response='fit', area=False, pol=False)
    used = np.unique(np.concatenate([np.arange(a, b + 1) for a, b in info['columns']]))
    r = info['response'][used]
    truth = resp[used] / resp[used].mean()
    assert np.max(np.abs(r / r.mean() / truth - 1)) < 0.01


def test_distance_fit_on_synthetic_drift():
    t0 = 16.65
    spectrum = lambda t: 1e-4 * (1 + 20 * np.exp(-((t - t0) / 0.05) ** 2))
    fr = _frames(np.arange(14, 18.01, 0.1), spectrum, d_true=265.0, d_p=271.0)
    prof = np.array([f.counts[15:487].sum(0) for f in fr])
    dth = np.degrees([f.geom.dth for f in fr])
    d, err, slope, n = ph.fit_pinhole_distance(prof, dth, 47, t0, 271.0, (30, 100))
    assert d == pytest.approx(265.0, abs=2.0)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_nx_scan_11_pinhole_map():
    """T8/T9 on real data (NX school scan 11, DPPC, Det_Th 14-18°): the map
    uses an order of magnitude more counts than the 3-column patch; the DPPC
    peak sits at 2θ 16.65° (the 3-column patch's peak, IDL review §2.3); the
    distance fit over the central columns agrees with the header's 271 mm
    within the method's spread (258-280 mm depending on the columns used,
    measured 2026-11-18)."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))
    from pinhole_frames import frames_for
    fr = frames_for(NX, [11])
    tt, beta, I, S, info = ph.level_map(fr, 15, 486)
    legacy = sum(np.clip(f.counts[15:487, 46:49], 0, None).sum() for f in fr)
    assert info['counts_used'] > 10 * legacy
    k = int(np.argmax(np.nansum(I, axis=1)))
    assert tt[k] == pytest.approx(16.65, abs=0.02)
    prof = np.array([np.clip(f.counts[15:487], 0, None).sum(0) for f in fr])
    dth = np.degrees([f.geom.dth for f in fr])
    d, err, slope, n = ph.fit_pinhole_distance(prof, dth, 47, tt[k], 271.0, (30, 100))
    assert 262 < d < 280


# ---- joining Qz levels (F62) ---------------------------------------------------

def _level(dths, beta0_deg, eff, truth, rng, monitor=1e6):
    """Frames of one Qz level: counts = Poisson(M · eff · truth(2θ_c, β_r))."""
    out = []
    for d in dths:
        g = ph.FrameGeometry(dth=math.radians(d), alpha=math.radians(0.09), beta0=math.radians(beta0_deg),
                             c0=47.0, r0=53.0, d_sample=551.0, d_pinhole=271.0, g_l3=556.0, wavelength=1.24)
        tt = np.degrees(ph.column_two_theta(NC, g))
        bb = np.degrees(ph.row_beta(NR, g))
        mu = monitor * eff * truth(tt[None, :], bb[:, None])
        out.append(ph.PinholeFrame(rng.poisson(mu).astype(float), monitor, g,
                                   (2.0, 0.1, 0.2, math.radians(0.09), 551.0, 271.0), (3.0, 14.0), 678.0, 1))
    return out


def _two_levels(seed=11):
    rng = np.random.default_rng(seed)
    truth = lambda t, b: 2e-4 * (1 + 2 * np.exp(-((t - 16.5) / 0.3) ** 2)) * (1 + 0.1 * b)
    a = _level(np.arange(14.0, 17.01, 0.1), 0.09, 1.0, truth, rng)
    b = _level(np.arange(15.0, 18.51, 0.1), 3.0, 0.8, truth, rng)      # monitor reads high: factor 1.25
    edges = ph.shared_edges(a + b)
    infos = [ph.level_map(x, 15, 486, response='none', area=False, pol=False, edges=edges)[4] for x in (a, b)]
    return truth, infos, edges


def test_join_recovers_the_factor_and_the_ranges():
    """T10: levels with different 2θ extents and β ranges; the factor (truth
    1.25) is fitted on the β overlap within the common 2θ range; 'common'
    keeps the 2θ range both cover, 'all' the union with empty cells."""
    truth, infos, edges = _two_levels()
    log = []
    tt, beta, I, S, info = ph.join_levels(infos, 'intersection', log=log, labels=['low', 'high'])
    fac, err = info['factors']['high']
    assert fac == pytest.approx(1.25, abs=3 * err) and err < 0.01
    assert len(log) == 1 and log[0]['kind'] == 'vertical (beta)' and np.isfinite(log[0]['chi2'])
    a_lo, a_hi = infos[0]['edges'][:-1][infos[0]['keep']][[0, -1]]
    b_lo, b_hi = infos[1]['edges'][:-1][infos[1]['keep']][[0, -1]]
    step = edges[1] - edges[0]
    assert tt[0] == pytest.approx(max(a_lo, b_lo) + step / 2) and tt[-1] == pytest.approx(min(a_hi, b_hi) + step / 2)
    assert beta[0] < 0.0 < 3.5 < beta[-1]                              # both levels' β ranges
    assert not np.isnan(I).any()                                      # common range: every cell has data
    tu, bu, Iu, Su, iu = ph.join_levels(infos, 'union')
    assert tu[0] < tt[0] and tu[-1] > tt[-1] and np.isnan(Iu).any()
    mean_m = 1e6
    rel = (I / mean_m) / truth(tt[:, None], beta[None, :])            # the joined map is the truth
    assert np.nanmean(rel) == pytest.approx(1.0, abs=0.01)


def test_join_conserves_counts():
    truth, infos, edges = _two_levels(seed=5)
    tu, bu, Iu, Su, iu = ph.join_levels(infos, 'union')
    total = sum(lv['all_counts'][lv['keep']].sum() for lv in infos)
    assert iu['sum_counts'].sum() == pytest.approx(total)


def test_levels_must_share_the_grid():
    truth, infos, edges = _two_levels()
    other = dict(infos[1], edges=infos[1]['edges'] + 0.01)
    with pytest.raises(ValueError):
        ph.join_levels([infos[0], other])


def test_one_level_is_returned_as_it_is():
    truth, infos, edges = _two_levels()
    tt, beta, I, S, info = ph.join_levels(infos[:1])
    assert len(beta) == 472 and I.shape == (infos[0]['keep'].sum(), 472)

