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
        tt = np.degrees(ph.pixel_angles(_geom(d, d_true or d_p), np.arange(NR), np.arange(NC))[0])   # exact
        mu = monitor * intensity(tt)
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


def _ray(g, r, c):
    """Independent of IMG_COO_CONV: the ray from the beam axis (the
    footprint line) through the vertical S4 slit, a distance D_p in front of
    the detector, to pixel (r, c) on a flat detector perpendicular to the
    arm at (Det_Th, β0), D from the sample (``pinhole.ray_geometry``, which
    the figures in docs/figures/pinhole draw); its in-plane and exit angles."""
    ray = ph.ray_geometry(g, r, c)
    return ray.two_theta, ray.beta


@pytest.mark.parametrize('dth, beta0', [(14.0, 0.09), (18.0, 6.5), (25.0, 12.0), (3.0, 0.5)])
def test_pixel_angles_are_the_exact_ray_geometry(dth, beta0):
    """IMG_COO_CONV's pinhole transform (Mati Meron), as ported, equals an
    independent ray construction, on this module and where a second 200K
    module would be (columns −212…−18 and 212…406)."""
    g = ph.FrameGeometry(dth=math.radians(dth), alpha=math.radians(0.09), beta0=math.radians(beta0),
                         c0=47.0, r0=53.0, d_sample=551.0, d_pinhole=271.0, g_l3=556.0)
    rows, cols = np.array([0, 53, 200, 486]), np.array([-212, -18, 0, 47, 120, 194, 212, 406])
    tt, bb = ph.pixel_angles(g, rows, cols)
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            t, b = _ray(g, r, c)
            assert tt[i, j] == pytest.approx(t, abs=1e-12) and bb[i, j] == pytest.approx(b, abs=1e-12)


@pytest.mark.parametrize('dth, beta0', [(16.0, 0.09), (14.0, 6.5), (0.5, 0.09)])
def test_ray_geometry_goes_from_the_beam_axis_through_the_slit_to_the_pixel(dth, beta0):
    """The ray of ``ray_geometry``: starts on the beam axis, crosses the S4
    slit line (along e_v through (D − D_p)·n), ends on the pixel; its angles
    are ``pixel_angles``' and its (u, v, w) give them by IMG_COO_CONV's last
    two formulas. At Det_Th ≤ 1° (no pinhole) it starts at the sample centre."""
    g = ph.FrameGeometry(dth=math.radians(dth), alpha=math.radians(0.09), beta0=math.radians(beta0),
                         c0=47.0, r0=53.0, d_sample=551.0, d_pinhole=271.0, g_l3=556.0)
    D, Dp = ph.vertical_distance(g), ph.pinhole_distance(g)
    for r, c in [(53, 47), (486, 28), (486, 102), (0, 194), (300, -212), (300, 406)]:
        ray = ph.ray_geometry(g, r, c)
        tt, bb = ph.pixel_angles(g, [r], [c])
        assert ray.two_theta == pytest.approx(tt[0, 0], abs=1e-12) and ray.beta == pytest.approx(bb[0, 0], abs=1e-12)
        assert ray.source[1:] == pytest.approx([0, 0], abs=1e-12)                       # on the beam axis
        assert np.cross(ray.slit - (D - Dp) * ray.n, ray.e_v) == pytest.approx(np.zeros(3), abs=1e-9)  # on the slit line
        to_slit, to_pix = ray.slit - ray.source, ray.pixel - ray.source
        assert np.cross(to_slit, ray.direction) == pytest.approx(np.zeros(3), abs=1e-9)     # the slit is on the ray,
        assert 0 <= to_slit.dot(ray.direction) <= np.linalg.norm(to_pix) + 1e-9          # between source and pixel
        assert to_pix / np.linalg.norm(to_pix) == pytest.approx(ray.direction, abs=1e-12)
        assert ray.pixel == pytest.approx(D * ray.n - (c - 47) * ph.PIXEL_MM * ray.e_h + (r - 53) * ph.PIXEL_MM * ray.e_v)
        assert np.dot(ray.n, ray.e_h) == pytest.approx(0, abs=1e-15) and np.dot(ray.n, ray.e_v) == pytest.approx(0, abs=1e-15)
        assert ray.u * ray.e_h + ray.v * ray.h + ray.w * np.array([0, 0, 1.0]) == pytest.approx(ray.pixel - ray.slit)
        assert ray.two_theta == pytest.approx(g.dth - math.atan2(ray.u, ray.v), abs=1e-12)
        assert ray.beta == pytest.approx(math.atan2(ray.w, math.hypot(ray.u, ray.v)), abs=1e-12)
        if dth <= 1.0:
            assert ray.source == pytest.approx(np.zeros(3), abs=1e-12)


@pytest.mark.parametrize('dth, beta0', [(16.0, 0.09), (14.0, 6.5), (25.0, 12.0)])
def test_ray_geometry_uvw_are_img_coo_conv_s(dth, beta0):
    """Ray.u, v, w (built from the slit crossing) equal IMG_COO_CONV's
    (Mati Meron): u = wx, v = D_p cos β0 − wy' sin β0, w = D_p sin β0 +
    wy' cos β0, with its pinhole correction
    wy' = wy − (D − D_p)(wx sin β0 cos δ + wy sin δ)/(D sin δ − wx cos β0 cos δ)."""
    g = ph.FrameGeometry(dth=math.radians(dth), alpha=math.radians(0.09), beta0=math.radians(beta0),
                         c0=47.0, r0=53.0, d_sample=551.0, d_pinhole=271.0, g_l3=556.0)
    D, Dp, b, d = ph.vertical_distance(g), ph.pinhole_distance(g), g.beta0, g.dth
    for r, c in [(53, 47), (486, 28), (0, 194), (300, -212), (300, 406)]:
        ray = ph.ray_geometry(g, r, c)
        wx, wy = -(c - 47) * ph.PIXEL_MM, (r - 53) * ph.PIXEL_MM
        wy1 = wy - (D - Dp) * (wx * math.sin(b) * math.cos(d) + wy * math.sin(d)) / \
            (D * math.sin(d) - wx * math.cos(b) * math.cos(d))
        assert (ray.wx, ray.wy) == pytest.approx((wx, wy), abs=1e-12)
        assert ray.u == pytest.approx(wx, abs=1e-9)
        assert ray.v == pytest.approx(Dp * math.cos(b) - wy1 * math.sin(b), abs=1e-9)
        assert ray.w == pytest.approx(Dp * math.sin(b) + wy1 * math.cos(b), abs=1e-9)


def test_ray_geometry_refuses_a_source_at_infinity():
    """The column whose ray runs parallel to the beam (2θ = 0 at β0 = 0)
    has no footprint point: a clear error, not a division by zero."""
    g = ph.FrameGeometry(dth=math.radians(14.0), alpha=0.0016, beta0=0.0, c0=47.0, r0=53.0, d_sample=551.0,
                         d_pinhole=271.0, g_l3=556.0)
    c = g.c0 - g.d_pinhole * math.tan(g.dth) / ph.PIXEL_MM
    with pytest.raises(ValueError):
        ph.ray_geometry(g, 53, c)


def test_pixel_angles_limits():
    g = _geom(15.0)
    tt, bb = ph.pixel_angles(g, np.array([53]), np.arange(NC))
    assert np.allclose(tt[0], ph.column_two_theta(NC, g), atol=1e-6)     # direct-beam row, arm level: per-axis is exact
    tt, bb = ph.pixel_angles(g, np.arange(NR), np.array([47]))
    assert np.allclose(tt[:, 0], g.dth, atol=1e-9)                       # direct-beam column: 2θ = Det_Th
    assert np.allclose(bb[:, 0], ph.row_beta(NR, g), atol=2e-5)          # and β as the per-axis formula
    flat = ph.FrameGeometry(dth=math.radians(0.5), alpha=0.0016, beta0=0.0016, c0=47, r0=53, d_sample=551,
                            d_pinhole=271, g_l3=0.0)                     # Det_Th <= 1°: no pinhole
    tt, bb = ph.pixel_angles(flat, np.array([53]), np.array([147]))
    assert tt[0, 0] == pytest.approx(flat.dth + math.atan2(100 * ph.PIXEL_MM, 551 * math.cos(0.0016)), abs=1e-9)


def test_a_line_at_fixed_beta_stays_in_one_beta_bin():
    """The reason for the exact geometry (owner, 2026-11-19): each column
    sees another part of the footprint, so β depends on the column. A
    feature at fixed β is one β bin wide in the map; with β per row only it
    was spread over ~0.4° at the top of the detector."""
    b0 = 5.0
    rng = np.random.default_rng(5)
    out = []
    for d in np.arange(14.0, 18.01, 0.1):
        g = _geom(d)
        tt, bb = (np.degrees(a) for a in ph.pixel_angles(g, np.arange(NR), np.arange(NC)))
        step_b = math.degrees(ph.PIXEL_MM / ph.vertical_distance(g))
        mu = 1e6 * np.where(np.abs(bb - b0) < step_b / 2, 1e-3, 1e-6)
        out.append(ph.PinholeFrame(rng.poisson(mu).astype(float), 1e6, g,
                                   (2.0, 0.1, 0.2, math.radians(0.09), 551.0, 271.0), (3.0, 14.0), 678.0, 1))
    tt, beta, I, S, info = ph.level_map(out, 15, 486, response='none', area=False, pol=False)
    prof = np.nansum(I, axis=0)
    k = int(np.argmax(prof))
    assert beta[k] == pytest.approx(b0, abs=info['beta_step_deg'])
    assert (prof > 0.3 * prof[k]).sum() <= 2
    # per row, the same frames would put the line over many rows across the columns used
    g = _geom(16.0)
    tt, bb = ph.pixel_angles(g, np.arange(NR), np.arange(28, 103))
    rows_at_b0 = [int(np.argmin(np.abs(np.degrees(bb[:, j]) - b0))) for j in range(bb.shape[1])]
    assert max(rows_at_b0) - min(rows_at_b0) > 10


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
        tt, bb = (np.degrees(a) for a in ph.pixel_angles(g, np.arange(NR), np.arange(NC)))   # exact
        mu = monitor * eff * truth(tt, bb)
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
    # the level's own β grid, untouched (was its 472 rows until 2026-11-19, when β
    # became a grid per pixel; the grid covers the β range every 2θ bin shares)
    nb = len(infos[0]['beta'])
    assert np.array_equal(beta, infos[0]['beta']) and I.shape == (infos[0]['keep'].sum(), nb)
    assert np.array_equal(info['sum_counts'], infos[0]['all_counts'][infos[0]['keep']])



# ---- S4 as a finite opening (column_acceptance, s4_window; figure case 8) -------

def _level_geom(dth_deg):
    """Arm level (β0 = 0) on row r0: everything in the horizontal plane, so
    plain in-plane trigonometry is an independent check."""
    return ph.FrameGeometry(dth=math.radians(dth_deg), alpha=math.radians(0.09), beta0=0.0, c0=47.0, r0=53.0,
                            d_sample=551.0, d_pinhole=271.0, g_l3=556.0, wavelength=1.24)


def test_slit_offset_zero_is_the_reader_line():
    g = _geom(16.0)
    for r, c in ((300, 96), (53, 47), (0, 194)):
        a, b = ph.ray_geometry(g, r, c), ph.ray_geometry(g, r, c, 0.0)
        for f in ('slit', 'source', 'pixel', 'direction'):
            assert np.array_equal(getattr(a, f), getattr(b, f))
        assert (a.two_theta, a.beta, a.u, a.v, a.w) == (b.two_theta, b.beta, b.u, b.v, b.w)


@pytest.mark.parametrize('t', [-0.1, 0.1, 0.5])
def test_slit_offset_moves_the_ray_by_plain_trig(t):
    g = _level_geom(16.0)
    for c in (10.0, 47.0, 96.0, 150.0):
        r = ph.ray_geometry(g, g.r0, c, t)
        assert r.two_theta == pytest.approx(g.dth + math.atan(((c - g.c0) * ph.PIXEL_MM - t) / 271.0), abs=1e-12)
        off = r.slit - (r.slit_centre - t * r.e_h)                # the slit point lies on the offset line
        assert np.linalg.norm(np.cross(off, r.e_v)) < 1e-9
    g12 = _geom(14.0)                                              # raised arm: still through the offset line
    g12 = ph.FrameGeometry(**{**g12.__dict__, 'beta0': math.radians(6.5)})
    r = ph.ray_geometry(g12, 400, 90, t)
    assert np.linalg.norm(np.cross(r.slit - (r.slit_centre - t * r.e_h), r.e_v)) < 1e-9


@pytest.mark.parametrize('dth, beta0', [(16.0, 0.09), (14.0, 6.5), (25.0, 12.0)])
def test_column_at_source_inverts_ray_geometry(dth, beta0):
    g = ph.FrameGeometry(**{**_geom(dth).__dict__, 'beta0': math.radians(beta0)})
    for x in (-400.0, -31.6, 0.0, 31.6, 150.0):
        for t in (0.0, 0.1):
            c = ph.column_at_source(g, x, slit_offset=t)
            assert ph.ray_geometry(g, g.r0, c, t).source[0] == pytest.approx(x, abs=1e-6)
    with pytest.raises(ValueError):
        ph.column_at_source(g, 1e5)                               # beyond L / cos Det_Th: no column


def test_exact_footprint_window_has_the_reader_width_but_not_its_centre():
    """P39, as coded: footprint_window (PD_PIN_RANGE) is centred on c0, the
    exact window is not (NX geometry, measured 2026-11-19)."""
    for dth, shift in ((14.0, 4.8), (16.0, 5.4), (18.0, 6.0)):
        g = _geom(dth)
        lo, hi = ph.footprint_columns(g, 0.1, 678.0)
        flo, fhi = ph.footprint_window(g, 0.1, 678.0)
        assert (hi - lo) == pytest.approx(fhi - flo, abs=0.1)
        assert 0.5 * (lo + hi) - g.c0 == pytest.approx(shift, abs=0.15)


def test_s4_window_ramps_by_plain_trig():
    """Each edge of the footprint window becomes a ramp: a slit point moved
    by t moves the column that sees a footprint end by t·(D − x cos δ)/(D −
    D_p − x cos δ) (similar triangles between planes perpendicular to the
    arm, x the footprint end)."""
    g = _level_geom(16.0)
    half = ph.footprint_length(g, 0.1, 678.0) / 2
    line = ph.footprint_columns(g, 0.1, 678.0)
    outer, inner = ph.s4_window(g, 0.1, 0.1, 0.1, 678.0)
    for k, x in ((0, -half), (1, half)):
        a = x * math.cos(g.dth)
        ramp = 0.1 * (551.0 - a) / (551.0 - 271.0 - a) / ph.PIXEL_MM
        assert abs(outer[k] - line[k]) == pytest.approx(ramp, rel=1e-6)
        assert abs(inner[k] - line[k]) == pytest.approx(ramp, rel=1e-6)
    assert outer[0] < inner[0] < inner[1] < outer[1]
    zero = ph.s4_window(g, 0.1, 0.0, 0.0, 678.0)
    assert zero[0] == pytest.approx(line) and zero[1] == pytest.approx(line)


def test_column_acceptance_by_plain_trig():
    g = _level_geom(16.0)
    p, dp = ph.PIXEL_MM, 271.0
    for c in (47, 96):
        a = ph.column_acceptance(g, c, 0.1, 0.1, n=5)
        lo = math.atan(((c - g.c0 - 0.5) * p - 0.1) / dp)
        hi = math.atan(((c - g.c0 + 0.5) * p + 0.1) / dp)
        assert np.ptp(a.two_theta) == pytest.approx(hi - lo, rel=1e-9)
        line = ph.column_acceptance(g, c, 0.0, 0.0, n=5)          # no S4 width: the pixel alone
        assert np.ptp(line.two_theta) == pytest.approx(math.atan(((c - g.c0 + 0.5) * p) / dp)
                                                       - math.atan(((c - g.c0 - 0.5) * p) / dp), rel=1e-9)
    ftp = ph.footprint_length(g, 0.1, 678.0)
    lo, hi = ph.footprint_columns(g, 0.1, 678.0)
    assert ph.column_acceptance(g, 47, 0.1, 0.1).lit_fraction(ftp) == 1.0
    assert ph.column_acceptance(g, round(hi) + 4, 0.1, 0.1).lit_fraction(ftp) == 0.0
    assert ph.column_acceptance(g, hi, 0.1, 0.1, n=21).lit_fraction(ftp) == pytest.approx(0.5, abs=0.05)
    t2, t4 = (ph.column_acceptance(g, 47, w / 2, w / 2, n=3).throughput(ftp) for w in (0.2, 0.4))
    assert t2 == pytest.approx(ph.PIXEL_MM * 0.2) and t4 == pytest.approx(2 * t2)   # counts ∝ the opening


def _beam_lit(dths, fwhm_mm=19.0):
    """Frames lit by a Gaussian beam along the beam axis (FWHM ``fwhm_mm`` on the
    sample, centred), flat true spectrum, expected counts: each column receives
    the light of the point of the beam axis it sees through S4."""
    out = []
    for d in dths:
        g = _geom(d)
        f = ph.PinholeFrame(np.zeros((NR, NC)), 1e5, g, (2.0, 0.1, 0.2, math.radians(0.09), 551.0, 271.0),
                            (3.0, 14.0), 678.0, 1)
        x = ph.source_positions([f], NC)[0]
        lit = np.exp(-0.5 * (np.nan_to_num(x, nan=1e9) / (fwhm_mm / 2.3548)) ** 2)
        out.append(ph.PinholeFrame(1e5 * 1e-3 * np.ones((NR, NC)) * lit[None, :], 1e5, g, f.areainfo, f.s5,
                                   f.s1_to_sample_mm, 1))
    return out


def test_beam_response_follows_a_narrow_beam():
    """Owner, 2026-11-19: with a narrow Gaussian beam the light a column
    receives changes with Det_Th (the column sees another point of the beam
    axis); one factor per column cannot follow it, one profile along the beam
    axis can, and it gives the beam's position and width."""
    fr = _beam_lit(np.arange(14.0, 18.01, 0.1))
    spans = {}
    for resp in ('fit', 'beam'):
        tt, beta, I, S, info = ph.level_map(fr, 15, 486, response=resp, area=False, pol=False)
        p = np.nanmean(I, axis=1)
        p = p / np.nanmedian(p)
        inner = (tt > 14.3) & (tt < 17.7)
        spans[resp] = (np.ptp(p[inner]), np.ptp(p[~inner]))
    assert spans['beam'][0] < 0.05 and spans['beam'][0] < spans['fit'][0]
    assert spans['beam'][1] < 0.25 and spans['beam'][1] < 0.5 * spans['fit'][1]
    b = info['beam']
    assert b['centre_mm'] == pytest.approx(0.0, abs=1.0) and b['fwhm_mm'] == pytest.approx(19.0, abs=2.5)


def test_two_theta_resolution_is_in_the_map_info():
    """The 2θ resolution: the full width one column accepts through S4 and
    its pixel (column_acceptance), here S4 0.2 mm at D_p 271 mm: 0.079°,
    about 2.2 one-column bins."""
    fr = _frames(np.arange(14, 16, 0.5), lambda t: 1e-4 + 0 * t)
    tt, beta, I, S, info = ph.level_map(fr, 15, 486, response='none', area=False, pol=False)
    acc = ph.column_acceptance(fr[len(fr) // 2].geom, 47, 0.1, 0.1)
    assert info['two_theta_resolution_deg'] == pytest.approx(math.degrees(np.ptp(acc.two_theta)))
    assert info['two_theta_resolution_deg'] == pytest.approx(0.079, abs=0.003)
    assert info['two_theta_resolution_columns'] == pytest.approx(2.2, abs=0.1) and info['s4_mm'] == 0.2


# ---- P39 fix (D51): the exact footprint window in usable_columns ----------

@pytest.mark.parametrize('dth', [14.0, 16.0, 18.0])
def test_usable_columns_end_where_the_footprint_is_lit_through_all_of_s4(dth):
    """Arm level: the exact window's columns are those inside S5 and inside
    the inner edges of s4_window; IDL's ('idl') is the centred window."""
    g = _level_geom(dth)
    s5 = (2.99986, 13.9999)
    ncols = 195
    cols = ph.usable_columns(g, ncols, *s5, 0.1, 678.0, s4_mm=0.2)
    a, b = ph.s5_window(g, *s5)
    lo, hi = ph.s4_window(g, 0.1, 0.1, 0.1, 678.0)[1]
    assert cols[0] == math.ceil(max(a, lo, 0)) and cols[-1] == math.floor(min(b, hi, ncols - 1))
    idl = ph.usable_columns(g, ncols, *s5, 0.1, 678.0, s4_mm=0.2, footprint='idl')
    flo, fhi = ph.footprint_window(g, 0.1, 678.0)
    assert idl[-1] == math.floor(min(b, fhi, ncols - 1))
    assert cols[-1] > idl[-1]                                 # P39: the exact window reaches further
    line = ph.usable_columns(g, ncols, *s5, 0.1, 678.0)       # no S4 opening: the slit line
    assert line[-1] == math.floor(min(b, ph.footprint_columns(g, 0.1, 678.0)[1], ncols - 1))
    with pytest.raises(ValueError):
        ph.usable_columns(g, ncols, *s5, 0.1, 678.0, footprint='centred')


def test_raised_arm_keeps_the_idl_high_edge():
    """β0 > 1°: the high edge stays at IDL's (P40b streak), the low edge is
    the exact one."""
    g = ph.FrameGeometry(**{**_level_geom(14.0).__dict__, 'beta0': math.radians(6.5)})
    s5 = (20.0, 13.9999)                                      # S5 wide open towards low columns
    cols = ph.usable_columns(g, 195, *s5, 0.1, 678.0, s4_mm=0.2)
    lo = ph.s4_window(g, 0.1, 0.1, 0.1, 678.0)[1][0]
    fhi = ph.footprint_window(g, 0.1, 678.0)[1]
    assert cols[0] == math.ceil(max(lo, 0)) and cols[-1] == math.floor(fhi)


def test_column_at_source_gives_up_promptly_where_no_column_sees_x():
    """Pinhole 11 mm in front of the sample (D_p 540 of 551 mm): the
    footprint's upstream end may be seen by no column; the search must say so
    (it used to loop for ever), and the exact window then has no limit on
    that side."""
    import time
    g = _geom(16.0, 540.0)
    t = time.time()
    for x in (-31.8, -500.0, 1e4):
        try:
            c = ph.column_at_source(g, x)
            assert ph.ray_geometry(g, g.r0, c).source[0] == pytest.approx(x, abs=1e-6)
        except ValueError:
            pass
    lo, hi = ph._exact_window(g, 0.1, 678.0, 0.2)
    assert lo < hi
    assert time.time() - t < 5
