"""Diffuse-cut axes (F97, F59; owner 2026-11-23, Q-IMG-12: "β, β − α (α from
Qz) and Qz and Qxy"; 2026-11-24): any cut can give its x axis as β, β − α,
Qz (vertical cuts) or Qxy (horizontal), converted from its pixels; the
intensities are the cut's own.

Invariant (I41): on a specular frame the reflected beam's row is at β − α = 0,
β = α, and its Qz is the frame's Qz; its column is at Qxy = 0."""
import math

import numpy as np
import pytest

from lss_core import cuts
from lss_core.experiment import Experiment


@pytest.fixture
def exp(dataset):
    return Experiment(dataset)


def _one(exp, direction, rng, axes, frame=3):
    return np.asarray(exp.cut([1], direction, rng, axes=axes, points={1: [frame]}).cuts[0], float)


@pytest.mark.parametrize('direction,rng', [('Pix V', (90, 105)), ('Q V', (-0.01, 0.01)),
                                           ('Pix H', (85, 110)), ('Q H', (0.005, 0.03))])
def test_the_intensities_are_the_cuts_own(exp, direction, rng):
    base = _one(exp, direction, rng, 'Pixels')
    fits = [a for a in cuts.DIFFUSE_AXES if cuts.DIRECTIONS.index(direction) in cuts.AXIS_FITS[a]]
    assert fits
    for a in fits:
        c = _one(exp, direction, rng, a)
        assert np.array_equal(c[:, 1:], base[:, 1:]) and c.shape == base.shape
        assert np.all(np.isfinite(c[:, 0])) and np.all(np.diff(c[:, 0]) * np.sign(c[-1, 0] - c[0, 0]) > 0)


def test_beta_and_qz_are_the_windows_angles_and_q_of_pix_v(exp):
    assert np.allclose(_one(exp, 'Pix V', (90, 105), 'beta')[:, 0], _one(exp, 'Pix V', (90, 105), 'Angles')[:, 0],
                       rtol=0, atol=1e-12)
    assert np.allclose(_one(exp, 'Pix V', (90, 105), 'Qz')[:, 0], _one(exp, 'Pix V', (90, 105), 'Q')[:, 0],
                       rtol=1e-12)
    q = _one(exp, 'Q V', (-0.01, 0.01), 'Qz')
    assert np.allclose(q[:, 0], _one(exp, 'Q V', (-0.01, 0.01), 'Q')[:, 0], rtol=1e-12)


@pytest.mark.parametrize('frame', [0, 3, 8])
def test_the_specular_row_is_at_beta_minus_alpha_zero(exp, frame):
    """I41, on synthetic specular frames (α_i = α: P47, the incidence from L)."""
    sc = exp.scans[1]
    qz = float(sc.columns['L'][frame])
    wl = sc.parameters['Wavelength']
    alpha = math.degrees(math.asin(qz * wl / 4 / math.pi))
    r0 = int(sc.parameters['DBPos'][0])                       # the beam's row
    rows = _one(exp, 'Pix V', (r0 - 5, r0 + 5), 'Pixels')[:, 0]
    k = int(np.where(rows == r0)[0][0])
    assert abs(_one(exp, 'Pix V', (r0 - 5, r0 + 5), 'beta-alpha', frame)[k, 0]) < 1e-12
    assert _one(exp, 'Pix V', (r0 - 5, r0 + 5), 'beta', frame)[k, 0] == pytest.approx(alpha, abs=1e-12)
    assert _one(exp, 'Pix V', (r0 - 5, r0 + 5), 'Qz', frame)[k, 0] == pytest.approx(qz, rel=1e-12)
    g = exp.cut([1], 'Pix H', (r0 - 2, r0 + 2), axes='Qxy', points={1: [frame]})
    cols = _one(exp, 'Pix H', (r0 - 2, r0 + 2), 'Pixels', frame)[:, 0]
    c0 = 194 - int(sc.parameters['DBPos'][1])                 # the image is flipped left to right
    assert abs(np.asarray(g.cuts[0])[int(np.where(cols == c0)[0][0]), 0]) < 1e-12


def test_qxy_is_the_windows_q_at_small_angles_and_exact_beyond(exp):
    q_win = _one(exp, 'Pix H', (85, 110), 'Q')[:, 0]
    qxy = _one(exp, 'Pix H', (85, 110), 'Qxy')[:, 0]
    assert np.allclose(qxy, q_win, rtol=1e-4, atol=1e-6)           # α, β of 0.1-0.3°: within 1e-4
    g = cuts.Geometry(1.24, math.radians(2.0), math.radians(2.0), 0.0, 0.0, 551.0, 551.0, 97.0, 50.0)
    cols = np.array([97.0, 147.0])
    exact = cuts.axis_values('Pix H', cols, 'Qxy', g, band=(48, 52))
    tth = math.atan(50 * cuts.PIXEL_MM / 551.0)
    k0 = 2 * math.pi / 1.24
    want = k0 * math.sqrt(2 * math.cos(math.radians(2.0)) ** 2 * (1 - math.cos(tth)))   # β = α at the band's middle
    assert exact[0] == 0.0 and exact[1] == pytest.approx(want, rel=1e-12)
    assert exact[1] < 4 * math.pi / 1.24 * math.sin(tth / 2)        # cos α cos β < 1: below the window's Q


def test_an_axis_is_for_the_cuts_it_fits(exp):
    with pytest.raises(ValueError, match='horizontal'):
        _one(exp, 'Pix V', (90, 105), 'Qxy')
    with pytest.raises(ValueError, match='vertical'):
        _one(exp, 'Q H', (0.005, 0.03), 'beta-alpha')
    with pytest.raises(ValueError):
        cuts.axis_values('Pix V', [1.0], 'alpha_f', None)
    assert cuts.axis_label('Pix V', 'beta-alpha') == 'β − α (deg)' and cuts.axis_label('Q H', 'Qxy') == 'Qxy (Å⁻¹)'
    assert cuts.axis_label('Pix V', 'Angles') == 'β (deg)' and cuts.axis_label('Q V', 'Q') == 'Qz (Å⁻¹)'


def test_the_q_ranges_the_detector_covers(exp):
    """F59: the window's Q defaults ('0:1' Qz, '1:2' Qxy) lie off a
    reflectivity frame, so those cuts sum nothing; covered_range says so,
    and centred_range gives a band about the beam that does."""
    sc = exp.scans[1]
    f = exp.frames([1])[3]
    g = cuts.Geometry(sc.parameters['Wavelength'], math.asin(f.qz * sc.parameters['Wavelength'] / 4 / math.pi),
                      math.asin(f.qz * sc.parameters['Wavelength'] / 4 / math.pi), 0.0, 0.0,
                      sc.parameters['S2D_Dist'], sc.parameters['S2D_Dist'],
                      194 - sc.parameters['DBPos'][1], sc.parameters['DBPos'][0])
    shape = (487, 195)
    qxy = cuts.covered_range('Q V', g, shape)
    assert qxy[0] < 0 < qxy[1] < 1.0                                 # '1:2' is off the detector
    assert np.all(_one(exp, 'Q V', (1.0, 2.0), 'Q')[:, 1] == 0)       # and sums nothing (the F59 defect, as coded)
    qz = cuts.covered_range('Q H', g, shape)
    assert qz[0] < f.qz < qz[1] < 1.0
    band = cuts.centred_range('Q V', g, 10)
    assert qxy[0] < band[0] < 0 < band[1] < qxy[1]
    by_q = _one(exp, 'Q V', band, 'Pixels')
    c0 = int(194 - sc.parameters['DBPos'][1])
    near = [_one(exp, 'Pix V', (c0 - a, c0 + b), 'Pixels') for a in (9, 10, 11) for b in (9, 10, 11)]
    assert any(np.array_equal(by_q[:, 1], n[:, 1]) for n in near)   # ±10 columns, to the pixel the window rounds to
    assert np.max(by_q[:, 1]) > 0
    zb = cuts.centred_range('Q H', g, 5)
    assert zb[0] < f.qz < zb[1]
    with pytest.raises(ValueError):
        cuts.centred_range('Pix V', g, 5)
    assert cuts.covered_range('Pix H', g, shape) == (0.0, 486.0) and cuts.covered_range('Pix V', g, shape) == (0.0, 194.0)
