"""The dose as peak and average, with the peak split (F109, owner 2026-11-25),
and the beam's width from S1 horizontal slit scans (lss_core.dose.dose_map,
slit_profile; Experiment.dose_summary, beam_width).

Invariant (I44): the map's peak is the dose per area that scan_dose gives
with the same beam (Σ N_i sin α_i / (width · height)); the map holds the whole
dose (captured above 0.9999); for one incidence and a Gaussian beam the
ratios are the closed forms (peak/average = −ln(1 − P)/P for extents P), and
every per-area value scales as 1/(width · height)."""
import math
import os

import numpy as np
import pytest
from scipy.stats import norm

import synth
from lss_core import dose
from lss_core.experiment import Experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


def _closed_form(P, top=0.1):
    """(peak, top, rest) / average and the area (in units of σx·σy') of a Gaussian footprint."""
    r2 = -2 * math.log(1 - P)
    area = math.pi * r2
    avg = P / area
    rin2 = top * r2
    t = (1 - math.exp(-rin2 / 2)) / (top * area)
    rest = (math.exp(-rin2 / 2) - (1 - P)) / ((1 - top) * area)
    return 1 / (2 * math.pi) / avg, t / avg, rest / avg, area


@pytest.mark.parametrize('P', [0.9, 0.5, 1 - math.exp(-2)])
def test_one_footprint_gives_the_gaussian_closed_forms(P):
    w, h, a = 1.0, 0.04, math.radians(0.1)
    r = dose.dose_map(1e12, math.sin(a), w, h, extent=P)
    peak, top, rest, area = _closed_form(P)
    assert r.peak / r.average == pytest.approx(peak, rel=2e-3)
    assert r.peak / r.average == pytest.approx(-math.log(1 - P) / P, rel=2e-3)
    assert r.top / r.average == pytest.approx(top, rel=2e-3)
    assert r.rest / r.average == pytest.approx(rest, rel=2e-3)
    sx, sy = w / math.sqrt(2 * math.pi), h / math.sqrt(2 * math.pi) / math.sin(a)
    assert r.area_mm2 == pytest.approx(area * sx * sy, rel=2e-3)
    assert r.top_area_mm2 == pytest.approx(0.1 * r.area_mm2)
    assert r.average * r.area_mm2 == pytest.approx(P * 1e12)
    assert r.captured > 0.9999
    assert r.unit == 'photons/mm2' and 'peak' in r.text() and '90 %' in dose.dose_map(1.0, 0.5, 1, 1).text()


def test_the_peak_is_todays_dose_per_area_and_scales_with_the_beam():
    N = np.array([1e11, 3e11, 2e11, 5e11])
    s = np.sin(np.radians([0.05, 0.1, 0.5, 3.0]))           # footprints 60 x apart
    r = dose.dose_map(N, s, 1.0, 0.03)
    assert r.peak == pytest.approx(float(np.sum(N * s)) / (1.0 * 0.03))
    assert r.total == pytest.approx(N.sum())
    assert r.captured > 0.9999
    assert r.peak > r.top > r.average > r.rest > 0
    r2 = dose.dose_map(N, s, 2.0, 0.06)                     # a beam twice as wide and tall
    for k in ('peak', 'average', 'top', 'rest'):
        assert getattr(r2, k) == pytest.approx(getattr(r, k) / 4, rel=2e-3)
    assert r2.area_mm2 == pytest.approx(4 * r.area_mm2, rel=2e-3)
    r3 = dose.dose_map(10 * N, s, 1.0, 0.03)                # linear in the dose
    assert r3.average == pytest.approx(10 * r.average) and r3.area_mm2 == pytest.approx(r.area_mm2)


def test_points_at_one_incidence_are_one_footprint():
    s = math.sin(math.radians(0.2))
    one = dose.dose_map(6e11, s, 1.0, 0.04)
    many = dose.dose_map([1e11, 2e11, 0.0, 3e11], [s] * 4, 1.0, 0.04)
    assert many.average == pytest.approx(one.average) and many.area_mm2 == pytest.approx(one.area_mm2)


def test_the_map_refuses_what_has_no_footprint():
    with pytest.raises(dose.DoseError):
        dose.dose_map([0.0, 0.0], 0.1, 1, 1)
    with pytest.raises(dose.DoseError):
        dose.dose_map(1.0, 0.0, 1, 1)
    with pytest.raises(dose.DoseError):
        dose.dose_map(1.0, 0.1, 0, 1)
    with pytest.raises(ValueError):
        dose.dose_map(1.0, 0.1, 1, 1, top=1.0)


def _counts(shape, seed, scale=2e5):
    c = np.random.default_rng(seed).poisson(scale * shape / shape.max() + 50).astype(float)
    return c, np.sqrt(c + (0.01 * c) ** 2)


def test_a_slit_profile_reads_the_beam_from_a_peak_an_edge_or_a_box():
    sig = 0.4
    x = np.linspace(-1.5, 1.5, 41)
    for g, seed in ((0.1, 1), (0.5, 2)):                     # a narrow gap moved across: a peak
        c, s = _counts(norm.cdf((x + g / 2) / sig) - norm.cdf((x - g / 2) / sig), seed)
        p = dose.slit_profile(x, c, s, gap_mm=g)
        assert p.ok and p.kind == 'peak', p.why
        assert p.sigma == pytest.approx(sig, rel=0.01)
        assert p.width == pytest.approx(math.sqrt(2 * math.pi) * p.sigma)
    assert dose.slit_profile(x, c, s).sigma > 1.04 * sig     # the 0.5 mm gap uncorrected reads 6 % wide
    c, s = _counts(norm.cdf(x / sig), 3)                     # one blade: an edge
    p = dose.slit_profile(x, c, s)
    assert p.ok and p.kind == 'edge' and p.sigma == pytest.approx(sig, rel=0.02)
    xb = np.linspace(-3, 3, 61)                              # a 3 mm gap moved across: a box
    c, s = _counts(norm.cdf((xb + 1.5) / sig) - norm.cdf((xb - 1.5) / sig), 4)
    p = dose.slit_profile(xb, c, s, gap_mm=3.0)
    assert p.ok and p.kind == 'box' and p.sigma == pytest.approx(sig, rel=0.02)


def test_the_slit_guards_say_why():
    x = np.linspace(-1.5, 1.5, 41)
    c = np.random.default_rng(5).poisson(np.full(41, 1e4)).astype(float)
    assert 'no fit' in dose.slit_profile(x, c, np.sqrt(c)).why                       # flat
    c, s = _counts(norm.cdf((x + 0.05) / 0.4) - norm.cdf((x - 0.05) / 0.4), 6)
    assert 'as wide as the profile' in dose.slit_profile(x, c, s, gap_mm=3.0).why
    x7 = np.linspace(-1.5, 1.5, 7)
    c, s = _counts(norm.cdf((x7 + 0.05) / 0.1) - norm.cdf((x7 - 0.05) / 0.1), 7)
    assert 'fewer than 3 points' in dose.slit_profile(x7, c, s).why                   # too coarse


def test_slit_scans_and_the_horizontal_gap():
    assert dose.is_slit_scan('ascan s1l -1 1 40 1') and dose.is_slit_scan('#S 7  dscan S1HC -1.5 1.5 30 1')
    assert not dose.is_slit_scan('ascan sh -2.3 -2.1 20 1') and not dose.is_slit_scan('ascan s1l 0 0 10 1')
    assert dose.s1_hgap_mm({'S1L': 0.05, 'S1R': 0.05}) == pytest.approx(0.1)
    assert dose.s1_hgap_mm({'S1L': 0.05}) is None
    d = dose.default_width()
    assert d.width_mm == dose.DEFAULT_WIDTH_MM == 1.0 and d.source == 'default'
    assert d.fwhm_mm == pytest.approx(0.9394, abs=1e-4)


def _slit_file(tmp_path, sig=0.35, g=0.1):
    x = np.linspace(-1.5, 1.5, 41)
    c, _s = _counts(norm.cdf((x + g / 2) / sig) - norm.cdf((x - g / 2) / sig), 8)
    rows = np.column_stack([x, np.ones_like(x), np.full_like(x, 1e5), c])
    text = [synth.spec_scan(1, 'slit', ['S1hc', 'Seconds', 'Monc', 'Pilatus'], rows,
                            command='dscan s1hc -1.5 1.5 40 1', image=False,
                            motors={'S1L': g / 2, 'S1R': g / 2})]
    return synth.write_spec(str(tmp_path / 'slit'), text)


def test_experiment_beam_width_from_a_slit_scan(tmp_path):
    exp = Experiment(_slit_file(tmp_path))
    w = exp.beam_width()
    assert w.source == 'slit scans' and [p.scan for p in w.profiles] == [1]
    assert w.width_mm == pytest.approx(math.sqrt(2 * math.pi) * 0.35, rel=0.02)
    assert w.fwhm_mm == pytest.approx(2.3548 * 0.35, rel=0.02)
    assert exp.beam_width(scans=[]).source == 'default'


@pytest.mark.slow
def test_nx_school_burns_peak_and_average():
    exp = Experiment(NX)
    h = exp.beam_height().height_mm
    assert exp.beam_width().source == 'default'              # NX school has no S1 slit scan
    with pytest.raises(dose.DoseError, match='beam_mm'):
        exp.dose_summary(14)                                 # no height scan with the burn's S1 gap
    for n, peak, avg in ((14, 1.541e12, 6.02e11), (15, 7.182e12, 2.81e12)):
        r = exp.dose_summary(n, beam_mm=(1.0, h))
        assert r.peak == pytest.approx(exp.dose(n, beam_mm=(1.0, h)).total(), rel=1e-9)
        assert r.peak == pytest.approx(peak, rel=2e-3) and r.average == pytest.approx(avg, rel=3e-3)
        assert r.peak / r.average == pytest.approx(-math.log(0.1) / 0.9, rel=2e-3)   # one incidence
