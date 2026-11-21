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
