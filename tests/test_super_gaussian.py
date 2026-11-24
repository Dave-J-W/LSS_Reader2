"""The super-Gaussian fit of sample-height scans (F78; phase 1a of the
sample timeline, docs/gui/timeline/research.md section 2).

I = A exp(−|(h − h0)/w|^p) + b, FWHM = 2 w (ln 2)^(1/p); p = 2 is a
Gaussian, larger p flatter. Known truth on synthetic Poisson scans, the
no-beam guard, and the NX school sh scans the research measured.
"""
import math
import os

import numpy as np
import pytest

from lss_core import peaks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')     # the SPEC file

X = np.linspace(-0.2, 0.2, 41)               # sh in mm, as at the beamline
MON = np.full_like(X, 1e5)


def _scan(w, p, seed, height=2e4, centre=0.01, background=300.0):
    truth = peaks.super_gaussian(X, height, centre, w, p, background)
    return np.random.default_rng(seed).poisson(truth).astype(float)


def test_the_fwhm_formula():
    # p = 2: a Gaussian with w = σ√2, FWHM = 2σ√(2 ln 2)
    sigma = 0.03
    assert peaks.super_gaussian_fwhm(sigma * math.sqrt(2), 2.0) == pytest.approx(2 * sigma * math.sqrt(2 * math.log(2)))
    w, p = 0.045, 3.4
    f = peaks.super_gaussian_fwhm(w, p)
    assert peaks.super_gaussian(w * 0 + f / 2, 1.0, 0.0, w, p, 0.0) == pytest.approx(0.5)   # half height at ±FWHM/2


def test_known_truth_is_recovered_with_calibrated_errors():
    """100 synthetic Poisson scans (FWHM 80.8 µm, p 3.4): no bias beyond
    noise and pulls of unit width (measured over 300 seeds while writing:
    FWHM pull mean 0.02, SD 0.95; p pull SD 0.98; χ²/dof mean 1.015)."""
    w, p = 0.045, 3.4
    true = peaks.super_gaussian_fwhm(w, p)
    pf, pp, chi = [], [], []
    for seed in range(100):
        f = peaks.fit_super_gaussian(X, _scan(w, p, seed), MON)
        assert f.ok, f.message
        pf.append((f.fwhm - true) / f.fwhm_err)
        pp.append((f.p - p) / f.p_err)
        chi.append(f.chi2_dof)
    for pulls in (np.array(pf), np.array(pp)):
        assert abs(pulls.mean()) < 0.3 and 0.75 < pulls.std() < 1.25
    assert 0.85 < np.mean(chi) < 1.15


def test_a_gaussian_scan_fits_p_near_2_and_a_flat_top_does_not():
    gauss = peaks.fit_super_gaussian(X, _scan(0.045, 2.0, 1), MON)
    assert gauss.p == pytest.approx(2.0, abs=4 * gauss.p_err)
    assert gauss.gaussian_chi2_dof == pytest.approx(gauss.chi2_dof, rel=0.15)        # p fixed at 2: as good
    flat = peaks.fit_super_gaussian(X, _scan(0.045, 3.4, 1), MON)
    assert flat.p > 3 and flat.gaussian_chi2_dof > 10 * flat.chi2_dof              # a Gaussian much worse


def test_no_beam_and_too_few_points_are_refused():
    rng = np.random.default_rng(2)
    flat = peaks.fit_super_gaussian(X, rng.poisson(np.full_like(X, 300.0)), MON)
    assert not flat.ok and 'no reflected beam' in flat.message
    assert np.isnan(flat.model(X)).all()
    short = peaks.fit_super_gaussian(X[:6], _scan(0.045, 3.4, 0)[:6], MON[:6])
    assert not short.ok and 'too few points' in short.message
    spike = np.full_like(X, 300.0)
    spike[20] = 5e4                                                      # one hot point is not a beam
    assert not peaks.fit_super_gaussian(X, spike, MON).ok


def test_summary_in_micrometres():
    f = peaks.fit_super_gaussian(X, _scan(0.045, 3.4, 0), MON)
    text = f.summary('µm', 1000.0)
    assert text.startswith('FWHM 8') and 'µm, p 3.' in text and 'Gaussian' in text


@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_the_nx_school_height_scans():
    """As measured in the research (research.md section 2): scans 5, 10, 13
    FWHM 81-82 µm, p 3.4-3.5, a Gaussian's χ² about ten times worse; scan
    4 (aborted) holds no reflected beam."""
    from lss_core.experiment import Experiment
    exp = Experiment(NX)
    seen = {}
    for n in (4, 5, 10, 13):
        sc = exp.scans[n]
        assert peaks.is_height_scan(sc.command)
        x = sc.columns[next(iter(sc.columns))]
        seen[n] = peaks.fit_super_gaussian(x, sc.columns['Pilatus'], sc.columns['Monc'])
    assert not seen[4].ok and 'no reflected beam' in seen[4].message
    for n in (5, 10, 13):
        f = seen[n]
        assert f.ok
        assert 0.079 < f.fwhm < 0.084, (n, f.fwhm)                       # mm: 81-82 µm
        assert 3.2 < f.p < 3.7, (n, f.p)
        assert f.gaussian_chi2_dof > 5 * f.chi2_dof
