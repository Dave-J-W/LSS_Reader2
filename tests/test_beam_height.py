"""The beam's height at the sample for the dose, from the rising edge of
the sample-height scans (lss_core.dose.beam_height; the local data agent's
study, docs/studies/sh_beam_size/summary.md, #60; 2026-11-24).

Invariant (I42): for a knife edge through a Gaussian beam of σ, the height
returned is √(2π)·σ (the inverse of the profile's peak), whatever the step;
a refused scan says which guard refused it."""
import math
import os

import numpy as np
import pytest
from scipy.stats import norm

from lss_core import dose

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


def _scan(sigma=0.013, c1=-2.24, c2=-2.16, start=-2.2785, stop=-2.1185, n=21, fall=0.013, seed=0, counts=2e5):
    x = np.linspace(start, stop, n)
    shape = 0.03 + norm.cdf((x - c1) / sigma) * norm.cdf((c2 - x) / fall)
    rng = np.random.default_rng(seed)
    N = rng.poisson(counts * shape).astype(float)
    m = np.full(n, 1e5)
    return x, N / m, np.sqrt(N + (0.01 * N) ** 2) / m


def test_the_height_is_root_2pi_sigma():
    assert dose.HEIGHT_PER_RISE_FWHM == pytest.approx(math.sqrt(2 * math.pi) / (2 * math.sqrt(2 * math.log(2))))
    assert dose.HEIGHT_PER_RISE_FWHM == pytest.approx(1.0645, abs=1e-4)
    for sigma, seed in ((0.010, 1), (0.013, 2), (0.018, 3)):
        e = dose.rising_edge(*_scan(sigma=sigma, seed=seed))
        assert e.ok, e.why
        assert e.height == pytest.approx(math.sqrt(2 * math.pi) * sigma, rel=0.08)
        assert e.centre == pytest.approx(-2.24, abs=0.004)


def test_the_guards_refuse_what_the_study_refused():
    assert 'foot' in dose.rising_edge(*_scan(start=-2.245)).why              # the rise not scanned from its foot
    assert 'points on the rising edge' in dose.rising_edge(*_scan(n=13, sigma=0.002, fall=0.002)).why   # edge < 1 step
    assert 'within 3 sigma' in dose.rising_edge(*_scan(c1=-2.20, c2=-2.18, sigma=0.01, fall=0.01)).why
    x, y, s = _scan()
    assert not dose.rising_edge(x, np.full_like(y, 1e-3), s).ok              # nothing to fit


def test_the_default_only_where_it_was_measured():
    p = {'Wavelength': 1.23984, 'S1T': 0.008, 'S1B': 0.008}
    h = dose.default_height(p)
    assert h.height_mm == dose.DEFAULT_HEIGHT_MM == 0.040 and h.source == 'default' and h.uncertainty_rel == 0.15
    assert dose.default_height(dict(p, S1T=0.05, S1B=0.05)).height_mm is None          # S1 0.1 mm
    assert dose.default_height(dict(p, Wavelength=12.39842 / 30.0)).height_mm is None   # 30 keV
    assert dose.default_height({'Wavelength': 1.23984}).height_mm is None              # S1 unknown
    assert dose.s1_gap_mm(p) == pytest.approx(0.016)


@pytest.mark.slow
def test_nx_school_height_scans():
    """NX 5, 10, 13 (S1 0.016 mm, 10 keV) accepted, NX 4 (stopped, starting
    at 54 % of the peak) refused; the height as coded."""
    from lss_core.experiment import Experiment
    exp = Experiment(NX)
    h = exp.beam_height()
    assert h.source == 'height scans' and [e.scan for e in h.edges] == [5, 10, 13]
    assert [(e.scan, 'foot' in e.why) for e in h.refused] == [(4, True)]
    assert h.height_mm == pytest.approx(0.0333, abs=0.0005)          # the study's 10 keV run medians: 0.035-0.045 mm
    assert all(0.028 < e.fwhm < 0.034 for e in h.edges)
    burn = exp.beam_height(near=14)                                  # GID burn 14 ran with S1 0.1 mm: no height
    assert burn.height_mm is None and '0.100 mm' in burn.note
    near = exp.beam_height(near=11)
    assert near.height_mm is not None or 'S1' in near.note
