"""Silicon-detector helpers for "Fit lines" options (F90 P2, P3; the owner,
2026-11-24: options, not defaults): the detector's FWHM, Reed's Si K
escape fraction and escape stripping (lss_core.fluorescence)."""
import math

import numpy as np
import pytest

from lss_core import fluorescence as fluo
from synthetic import mca


def test_detector_fwhm_is_the_fano_formula():
    assert fluo.detector_fwhm(0.0, 0.12) == pytest.approx(0.12)
    want = math.sqrt(0.12 ** 2 + 8 * math.log(2) * 0.00365 * 0.115 * 8.631)
    assert fluo.detector_fwhm(8.631) == pytest.approx(want) == pytest.approx(0.1857, abs=1e-4)
    assert fluo.detector_fwhm(8.631) == pytest.approx(mca.Detector().fwhm(8.631), rel=1e-12)   # the generator's


def test_escape_fraction_reed():
    assert fluo.si_escape_fraction(1.8) == 0.0                       # below the Si K edge
    assert 0.9e-3 < fluo.si_escape_fraction(10.0) < 1.2e-3           # about 0.10 %
    assert 1.3e-3 < fluo.si_escape_fraction(8.6) < 1.7e-3            # about 0.15 %
    assert fluo.si_escape_fraction(10.0) == pytest.approx(mca.reed_escape(10.0), rel=1e-12)


def test_stripping_removes_the_elastic_escape():
    """On a synthetic spectrum with Reed's escapes, stripping leaves the
    escape-free one to within the width mismatch (the escape has the lower
    energy's resolution): under 5 % of the escape counts in any band."""
    s = mca.spectrum({'Zn': 1e4}, elastic=1e6)
    s0 = mca.spectrum({'Zn': 1e4}, elastic=1e6, detector=mca.Detector(escape=0.0))
    d = np.column_stack([s.energy, s.expected, np.sqrt(s.expected)])
    e, y = s.energy, fluo.strip_escape(d)[:, 1]
    esc = s.part(None, ['escape'])
    for a, b in [(7.9, 8.2), (8.2, 8.35), (8.35, 8.6), (8.6, 9.2)]:
        m = (e >= a) & (e < b)
        assert abs((y - s0.expected)[m].sum()) < 0.05 * esc[(e >= 7.9) & (e < 8.6)].sum() + 1.0, (a, b)


def test_stripping_keeps_zero_errors_and_scales():
    e = np.linspace(0.01, 12, 1200)
    y = np.where(e > 9.9, 100.0, 0.0)
    d = np.column_stack([e, y, np.sqrt(y)])
    out = fluo.strip_escape(d, scale=2.0)
    assert np.all(out[e < 8.0, 2] == 0)                              # zero counts: σ stays 0, as the reader has them
    k = np.argmin(abs(e - 8.3))
    assert out[k, 1] == pytest.approx(-2 * fluo.si_escape_fraction(e[k] + fluo.SI_KA_KEV) * 100.0)
    assert np.array_equal(d[:, 1], y)                                # the input is not touched
