"""lss_core.peaks: finding and fitting peaks in line cuts, profiles and
spectra (owner, 2026-11-21). Synthetic data with a known truth."""
import math

import numpy as np
import pytest

from lss_core import peaks

G = 2 * math.sqrt(2 * math.log(2))


def _gauss(x, c, fwhm, h):
    return h * np.exp(-0.5 * ((x - c) / (fwhm / G)) ** 2)


def _poisson(mu, seed):
    return np.random.default_rng(seed).poisson(mu).astype(float)


def test_one_gaussian_on_a_sloped_background_is_found_and_fitted():
    x = np.linspace(1.2, 1.8, 301)
    mu = 200 + 80 * (x - 1.5) + _gauss(x, 1.4663, 0.016, 900)
    y = _poisson(mu, 1)
    res = peaks.fit(x, y, np.sqrt(np.maximum(y, 1)))
    assert res.ok and len(res.peaks) == 1
    p = res.peaks[0]
    assert abs(p.centre - 1.4663) < 3 * p.centre_err and p.centre_err < 3e-4
    assert abs(p.fwhm - 0.016) < 3 * p.fwhm_err
    true_area = 900 * 0.016 * math.sqrt(math.pi / (4 * math.log(2)))
    assert abs(p.area - true_area) < 3 * p.area_err
    assert 0.7 < res.chi2_dof < 1.4                       # σ describes the scatter
    assert res.model(x).shape == x.shape


def test_two_overlapping_peaks_are_fitted_together():
    x = np.linspace(0, 10, 401)
    mu = 50 + _gauss(x, 4.6, 0.6, 400) + _gauss(x, 5.5, 0.6, 250)
    y = _poisson(mu, 2)
    res = peaks.fit(x, y, np.sqrt(np.maximum(y, 1)), peaks.FitOptions(n_peaks=2))
    assert res.ok and len(res.peaks) == 2
    c = sorted(p.centre for p in res.peaks)
    assert c[0] == pytest.approx(4.6, abs=0.03) and c[1] == pytest.approx(5.5, abs=0.04)
    assert res.peaks[0].height > res.peaks[1].height       # strongest first


def test_automatic_finds_separate_peaks_with_their_own_windows():
    x = np.linspace(0, 20, 801)
    mu = 30 + _gauss(x, 5, 0.4, 300) + _gauss(x, 14, 0.5, 150)
    y = _poisson(mu, 3)
    groups = peaks.fit_all(x, y, np.sqrt(np.maximum(y, 1)))
    assert len(groups) == 2 and all(g.ok for g in groups)
    assert sorted(round(g.peaks[0].centre, 1) for g in groups) == [5.0, 14.0]
    both = peaks.fit(x, y, np.sqrt(np.maximum(y, 1)))
    assert len(both.peaks) == 2 and both.peaks[0].centre == pytest.approx(5.0, abs=0.02)


@pytest.mark.parametrize('shape', ['lorentzian', 'pseudo-voigt'])
def test_other_shapes(shape):
    x = np.linspace(-5, 5, 501)
    lor = 1 / (1 + (x / 0.4) ** 2)
    mu = 20 + 500 * (lor if shape == 'lorentzian' else 0.5 * lor + 0.5 * np.exp(-0.5 * (x / (0.8 / G)) ** 2))
    y = _poisson(mu, 4)
    res = peaks.fit(x, y, np.sqrt(np.maximum(y, 1)), peaks.FitOptions(shape=shape, background='constant',
                                                                       window=4.0))
    assert res.ok
    p = res.peaks[0]
    assert p.centre == pytest.approx(0.0, abs=0.01) and p.fwhm == pytest.approx(0.8, rel=0.05)
    if shape == 'pseudo-voigt':
        assert p.eta == pytest.approx(0.5, abs=0.1)


def test_noise_alone_gives_no_peak_and_says_so():
    x = np.linspace(0, 1, 200)
    y = _poisson(np.full(200, 100.0), 5)
    res = peaks.fit(x, y, np.sqrt(y))
    assert not res.ok and not res.peaks and 'no peak' in res.message


def test_given_centres_and_fixed_width():
    x = np.linspace(5, 8, 301)
    mu = 10 + _gauss(x, 6.40, 0.15, 300) + _gauss(x, 7.06, 0.15, 60)
    y = _poisson(mu, 6)
    res = peaks.fit_lines(x, y, [6.40, 7.06], np.sqrt(np.maximum(y, 1)),
                          peaks.FitOptions(fix_centres=True, fwhm=0.15, background='linear', window=0.6))
    assert res.ok and len(res.peaks) == 2
    assert sorted(p.centre for p in res.peaks) == [6.40, 7.06]
    assert max(p.height for p in res.peaks) == pytest.approx(300, rel=0.08)


def test_without_sigma_errors_come_from_the_scatter():
    x = np.linspace(0, 1, 201)
    rng = np.random.default_rng(7)
    y = 1.0 + _gauss(x, 0.5, 0.05, 2.0) + rng.normal(0, 0.05, x.size)
    res = peaks.fit(x, y)
    assert res.ok and res.peaks[0].centre == pytest.approx(0.5, abs=3 * res.peaks[0].centre_err)
    assert 0 < res.peaks[0].centre_err < 0.01


def test_too_few_points_and_bad_options_are_reported():
    assert not peaks.fit([1, 2, 3], [1, 5, 1]).ok
    with pytest.raises(ValueError):
        peaks.fit(np.arange(20.0), np.ones(20), options=peaks.FitOptions(shape='voigt'))


def test_series_uses_the_sum_for_positions_and_widths():
    """Owner (2026-11-19): fit the sum of a series of MCA spectra, then each
    spectrum with the line's position and width fixed; better than a window
    sum when the background (Rayleigh spillover) changes."""
    e = np.linspace(5.5, 8.5, 300)
    amps = np.array([5.0, 20.0, 40.0, 80.0, 160.0])
    spectra, sig = [], []
    for k, a in enumerate(amps):
        mu = 30 + 15 * k * (e - 5.5) + _gauss(e, 6.93, 0.17, a)       # a background that changes along the series
        y = _poisson(mu, 10 + k)
        spectra.append(y)
        sig.append(np.sqrt(np.maximum(y, 1)))
    ref, each = peaks.fit_series(e, spectra, sig, peaks.FitOptions(background='linear'))
    assert ref.ok and len(each) == len(amps)
    assert ref.peaks[0].centre == pytest.approx(6.93, abs=0.01) and ref.peaks[0].fwhm == pytest.approx(0.17, rel=0.1)
    got = np.array([r.peaks[0].height for r in each])
    err = np.array([r.peaks[0].height_err for r in each])
    assert np.all(np.abs(got - amps) < 4 * err + 0.05 * amps)
    assert all(0.6 < r.chi2_dof < 1.6 for r in each)


def test_a_wrong_shape_is_fitted_but_flagged():
    """A Lorentzian fitted to a noiseless Gaussian with tiny error bars: a
    result, with a warning that the model does not describe the data."""
    x = np.arange(195.0)
    y = 4e-4 + 50.133 * np.exp(-0.5 * ((x - 97) / (8 / G)) ** 2)
    s = np.maximum(np.sqrt(y) * 0.009, 7e-5)
    res = peaks.fit(x, y, s, peaks.FitOptions(shape='lorentzian', background='constant', n_peaks=1))
    assert res.peaks and ('does not describe' in res.message or 'did not converge' in res.message)
    good = peaks.fit(x, y, s, peaks.FitOptions(shape='gaussian', background='constant', n_peaks=1))
    assert good.ok and not good.message and good.peaks[0].fwhm == pytest.approx(8.0, rel=1e-3)


# ---- edges, boxes, scan shapes (F22a, F43, P9) -----------------------------

def test_edge_gives_the_beam_size_of_a_half_cut():
    """A half-cut (sample height scanned through a Gaussian beam of FWHM 52
    µm): the edge's centre is where the beam is half cut, its FWHM the
    beam's."""
    from scipy.special import erf
    z = np.linspace(-0.2, 0.2, 81)
    mu = 2000 * (0.5 * (1 - erf((z - 0.013) / (0.052 / G * math.sqrt(2))))) + 20
    y = _poisson(mu, 11)
    res = peaks.fit_edge(z, y, np.sqrt(np.maximum(y, 1)))
    p = res.peaks[0]
    assert res.ok and p.centre == pytest.approx(0.013, abs=3 * p.centre_err + 1e-4)
    assert p.fwhm == pytest.approx(0.052, abs=3 * p.fwhm_err + 5e-4) and p.height < 0      # falling
    assert 0.6 < res.chi2_dof < 1.6


def test_a_box_that_cannot_converge_gives_up_early(monkeypatch):
    """The window fits the shape of every motor scan it plots. A box fitted
    to a Gaussian (the synthetic motor scan: 21 points, FWHM 0.471) cannot
    converge; with 20000 evaluations allowed it took 400 442 model calls
    (12 s) before failing all the same (2026-11-23). Capped at
    SHAPE_FIT_MAX_NFEV, the answer is unchanged and the cost bounded."""
    calls = [0]
    real = peaks._step

    def counting(*a, **k):
        calls[0] += 1
        return real(*a, **k)
    monkeypatch.setattr(peaks, '_step', counting)
    x = np.linspace(-1, 1, 21)
    y = 1000 * np.exp(-x ** 2 / 2 / 0.2 ** 2) + 10
    res = peaks.fit_scan(x, y, np.sqrt(y))
    assert res.kind == 'peak' and res.peaks[0].fwhm == pytest.approx(0.471, abs=5e-3)
    assert sorted(res.candidates) == ['edge', 'peak']          # the box failed, as before
    assert calls[0] < 150000, calls[0]                         # 112 456 with the cap of 2000


def test_a_flat_noisy_scan_is_not_fitted(monkeypatch):
    """Owner, 2026-11-23: no point hammering a flat noisy line with fits.
    NX school scan 4's Pilatus column (7-19 counts around 12) used to be
    reported as a peak at -2.2304, its one 19-count point; a ramp (Epoch,
    Out_Ht) as a peak or an edge. Both are 'flat' now, and no fit runs."""
    def must_not_run(*a, **k):
        raise AssertionError('a flat scan was fitted')
    for name in ('fit', 'fit_edge', 'fit_box'):
        monkeypatch.setattr(peaks, name, must_not_run)
    x = np.linspace(-2.2785, -2.1665, 15)
    y = np.array([10, 17, 13, 13, 14, 10, 19, 10, 10, 9, 10, 15, 12, 7, 10], float)
    res = peaks.fit_scan(x, y, np.sqrt(y))
    assert res.kind == 'flat' and not res.ok and res.peaks == [] and res.candidates == {}
    assert 'flat' in res.message
    ramp = peaks.fit_scan(x, 1.795e9 + 1.2 * np.arange(15.0), None)      # a clock column
    assert ramp.kind == 'flat'


def test_a_weak_real_peak_is_still_fitted():
    """A 4 sigma Gaussian on 12 counts (41 points): never called flat in
    200 noise draws (2026-11-23); one 3.5 sigma peak in 200 was."""
    x = np.linspace(-1, 1, 41)
    y = _poisson(12 + _gauss(x, 0.0, 0.3, 25), 0)
    res = peaks.fit_scan(x, y, np.sqrt(np.maximum(y, 1)))
    assert res.ok and res.kind != 'flat'          # which shape wins (box, here) is the Akaike choice's, as before
    assert res.candidates['peak'].peaks[0].centre == pytest.approx(0.0, abs=0.05)


def test_height_scans_are_recognised():
    """Owner, 2026-11-23: sample-height scans have good signal and a FWHM
    over 20 µm. Recognised by the command: a scan of sh over a range."""
    for c in ('#S 4  a2scan  sh -2.2785 -2.1185  oh -1.37117 -1.05117  20 1\n', 'ascan  sh -1 1 20 1',
              'dscan sh -0.1 0.1 20 1', 'd2scan sh -0.1 0.1 oh -0.2 0.2 20 1'):
        assert peaks.is_height_scan(c), c
    for c in ('ascan ih -0.994512 -0.994512  20 10', 'ascan  dth 14 18  40 7', 'ascan sh 1 1 10 1',
              'hklscan  0 0  0 0  0.0175 0.04  18 2', 'a2scan oh -1 1 sh -2 2 20 1', ''):
        assert not peaks.is_height_scan(c), c


def test_a_height_scan_needs_good_signal_and_a_width_over_20_microns():
    x = np.linspace(-2.2785, -2.1185, 21)             # sh in mm, 8 µm steps, as at the beamline
    hs = peaks.height_scan_options()
    assert hs == {'min_fwhm': 0.020, 'min_signal_to_background': 2.0}
    # NX school scan 5, Pilatus: unchanged by the height rules (a plateau 82 µm wide)
    y5 = np.array([536, 605, 878, 1347, 2213, 3126, 3870, 4178, 4259, 4429, 4230, 4292, 4088, 3539,
                   2910, 1888, 1117, 755, 530, 450, 391], float)
    a, b = peaks.fit_scan(x, y5, np.sqrt(y5)), peaks.fit_scan(x, y5, np.sqrt(y5), **hs)
    assert a.kind == b.kind == 'box' and a.peaks[0].fwhm == b.peaks[0].fwhm == pytest.approx(0.0819, abs=5e-4)
    assert peaks.signal_to_background(y5) > 6
    # a real but weak bump (S/B 0.44, far above the noise): fitted in general, not as a height scan
    weak = _poisson(1000 + _gauss(x, -2.2, 0.07, 500), 4)
    assert peaks.fit_scan(x, weak, np.sqrt(weak)).ok
    w = peaks.fit_scan(x, weak, np.sqrt(weak), **hs)
    assert w.kind == 'weak' and not w.ok and 'signal/background' in w.message
    # one hot point: every shape narrower than 20 µm, so none is reported
    spike = _poisson(np.where(np.arange(21) == 10, 3000.0, 30.0), 3)
    sp = peaks.fit_scan(x, spike, np.sqrt(np.maximum(spike, 1)), **hs)
    assert not sp.ok and sp.peaks == [] and 'wider than 0.02' in sp.message


def test_scan_shape_picks_peak_edge_or_box():
    x = np.linspace(-1, 1, 121)
    from scipy.special import erf
    st = lambda c, w: 0.5 * (1 + erf((x - c) / (w / G * math.sqrt(2))))
    cases = {'peak': 50 + _gauss(x, 0.1, 0.471, 1000),
             'edge': 50 + 1000 * st(0.2, 0.1),
             'box': 50 + 1000 * (st(-0.4, 0.05) - st(0.3, 0.05))}
    for k, (kind, mu) in enumerate(cases.items()):
        y = _poisson(mu, 20 + k)
        res = peaks.fit_scan(x, y, np.sqrt(np.maximum(y, 1)))
        assert res.kind == kind, (kind, res.kind)
    peak = peaks.fit_scan(x, _poisson(cases['peak'], 20), None)
    assert peak.peaks[0].fwhm == pytest.approx(0.471, rel=0.05)        # P9: the box model gave 0.406
    box = peaks.fit_scan(x, _poisson(cases['box'], 22), None)
    assert box.peaks[0].centre == pytest.approx(-0.05, abs=0.01) and box.peaks[0].fwhm == pytest.approx(0.7, abs=0.02)


def test_line_index_is_the_first_given_line_not_the_tallest():
    """F90, P5 (2026-11-24): with several lines placed, the line asked for
    is the first one given (the element's), even when another is taller."""
    e = np.linspace(7.8, 9.3, 151)
    mu = 20 + _gauss(e, 8.26, 0.078, 400) + _gauss(e, 8.631, 0.079, 60)   # an escape peak taller than the line
    y = _poisson(mu, 11)
    ref, each = peaks.fit_series(e, [y], [np.sqrt(np.maximum(y, 1))],
                                 peaks.FitOptions(centres=(8.631, 8.26), background='linear', window=5.0))
    assert ref.ok and ref.peaks[0].centre == pytest.approx(8.26, abs=0.01)    # the tallest comes first
    j = peaks.line_index(ref, (8.631, 8.26))
    assert ref.peaks[j].centre == pytest.approx(8.631, abs=0.01)
    assert each[0].peaks[j].height == pytest.approx(60, rel=0.25)
    assert peaks.line_index(ref) == 0 and peaks.line_index(peaks.FitResult([], np.zeros(0), 0, 1, 0, (0, 1), 0, False)) is None


def test_series_fits_each_spectrum_by_poisson_likelihood():
    """F90 P1 (the default since 2026-11-24, rule 12): each spectrum's
    heights by Poisson maximum likelihood. A line of ~300 counts on 1 count
    per channel: the old data weights read it low (Neyman's χ²), the
    Poisson step does not; at high counts the two agree."""
    e = np.linspace(5.6, 7.2, 161)
    got = {'poisson': [], 'data': []}
    for seed in range(40):
        mu = 1.0 + _gauss(e, 6.40, 0.15, 20.0)                   # area ≈ 20 × 0.15 × 1.0645 / 0.01 = 319 counts
        ys = [_poisson(mu, 100 * seed + k) for k in range(8)]
        sig = [np.sqrt(y) for y in ys]                            # as normalise_spectrum: 0 where no counts
        for w in got:
            ref, each = peaks.fit_series(e, ys, sig, peaks.FitOptions(centres=(6.40,), background='linear', window=0.8),
                                         weights=w)
            got[w] += [r.peaks[0].height / 20.0 - 1 for r in each]
    se = np.std(got['data']) / np.sqrt(len(got['data']))
    assert np.mean(got['data']) < -3 * se                        # Neyman: low
    assert abs(np.mean(got['poisson'])) < 3 * se
    hi = 100.0 + _gauss(e, 6.40, 0.15, 2000.0)
    y = _poisson(hi, 3)
    a = peaks.fit_series(e, [y], [np.sqrt(y)], peaks.FitOptions(centres=(6.40,)), weights='poisson')[1][0].peaks[0].height
    b = peaks.fit_series(e, [y], [np.sqrt(y)], peaks.FitOptions(centres=(6.40,)), weights='data')[1][0].peaks[0].height
    assert a == pytest.approx(b, rel=0.01)
    assert peaks.fit_series(e, [y], [np.sqrt(y)], peaks.FitOptions(centres=(6.40,)))[1][0].peaks[0].height == a   # the default
    with pytest.raises(ValueError):
        peaks.fit_series(e, [y], [np.sqrt(y)], weights='neyman')
