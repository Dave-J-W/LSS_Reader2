"""The reflectivity generator itself (tests/synthetic/xrr.py): physics
invariants of Fresnel, Parratt, Névot–Croce, Kiessig fringes and the
kinematic limit. Analytic checks; no data files."""
import math

import numpy as np
import pytest

from lss_core import stitching
from synthetic import xrr

QC = xrr.qc(xrr.RHO_WATER)


def test_critical_qz_of_water_is_the_readers_default():
    assert QC == pytest.approx(0.02175, abs=5e-5)
    assert QC == pytest.approx(0.0217, rel=0.005)          # lss_core.reflectivity.finish default
    assert xrr.rho_from_qc(QC) == pytest.approx(xrr.RHO_WATER, rel=1e-12)
    assert xrr.WAVELENGTH == pytest.approx(1.239842, rel=1e-6)
    # Qc does not depend on the wavelength; δ does, as λ²
    assert xrr.delta(xrr.RHO_WATER, 2 * xrr.WAVELENGTH) == pytest.approx(4 * xrr.delta(xrr.RHO_WATER), rel=1e-12)
    assert 4e-9 < xrr.BETA_WATER_10KEV < 7e-9


def test_fresnel_is_one_below_qc_without_absorption_and_close_to_one_with_it():
    q = np.linspace(0.001, 0.98 * QC, 50)
    assert np.all(xrr.fresnel(q, beta=0.0) == pytest.approx(1.0, abs=1e-12))
    r = xrr.fresnel(q)
    assert np.all(r < 1) and np.all(r > 0.95)
    assert np.all(np.diff(r) < 0)                              # the deficit grows towards Qc
    weaker = xrr.fresnel(q, beta=xrr.BETA_WATER_10KEV / 100)
    assert np.all(1 - weaker < (1 - r) / 5)                    # and vanishes with β


def test_fresnel_matches_the_readers_closed_form():
    q = np.linspace(0.0, 0.6, 601)
    a = xrr.fresnel(q, beta=0.0)
    assert a == pytest.approx(stitching.fresnel(q, QC), rel=1e-9, abs=1e-15)
    assert a == pytest.approx(xrr.fresnel_no_absorption(q, QC), rel=1e-9, abs=1e-15)


@pytest.mark.parametrize('k', [5, 10, 20, 40])
def test_fresnel_tends_to_the_fourth_power_law(k):
    q = k * QC
    r = float(xrr.fresnel(q))
    assert r == pytest.approx((QC / (2 * q)) ** 4, rel=1.5 / k ** 2)   # leading correction ~ (Qc/Qz)²


def test_nevot_croce_single_interface_is_the_exact_damping():
    """One interface: R = R_F |exp(−Qz Q_s σ²/2)|² = R_F exp(−Qz Re(Q_s) σ²)
    exactly; far above Qc that is exp(−Qz² σ²); below Qc (Q_s nearly
    imaginary) almost no damping. Debye–Waller: exp(−Qz² σ²) everywhere."""
    s = 3.0
    q = np.linspace(0.002, 0.6, 400)
    w = xrr.bare_water(sigma=s)
    qs = np.sqrt(q ** 2 - QC ** 2 + 1j * 32 * math.pi ** 2 * w.beta / xrr.WAVELENGTH ** 2 + 0j)
    ratio = w.reflectivity(q) / w.fresnel(q)
    assert ratio == pytest.approx(np.exp(-q * qs.real * s ** 2), rel=1e-9)
    hi = q > 10 * QC
    assert ratio[hi] == pytest.approx(np.exp(-q[hi] ** 2 * s ** 2), rel=0.01)
    assert np.all(ratio[q < QC] > 0.999)
    dw = xrr.bare_water(sigma=s, roughness='debye-waller')
    assert dw.reflectivity(q) / dw.fresnel(q) == pytest.approx(np.exp(-q ** 2 * s ** 2), rel=1e-9)


def test_a_layer_of_the_substrate_changes_nothing():
    """A slab with the substrate's density and the same roughness is no
    interface at all (Parratt with Δρ = 0 at the inner interface)."""
    q = np.linspace(0.005, 0.5, 300)
    sub = xrr.bare_water(sigma=0.0)
    same = xrr.Profile([xrr.Layer(40.0, sub.rho, 0.0, sub.beta)], sub.rho, sub.beta, 0.0, roughness='none')
    sub.roughness = 'none'
    assert same.reflectivity(q) == pytest.approx(sub.reflectivity(q), rel=1e-9)


@pytest.mark.parametrize('d', [60.0, 100.0, 150.0, 200.0])
def test_kiessig_period_is_two_pi_over_d(d):
    f = xrr.film(d, sigma=2.0)
    q = np.linspace(0.12, 0.45, 20001)
    r = f.rrf(q)
    mins = q[1:-1][(r[1:-1] < r[:-2]) & (r[1:-1] < r[2:])]
    assert len(mins) >= 3
    period = (mins[-1] - mins[0]) / (len(mins) - 1)
    assert period == pytest.approx(xrr.kiessig_period(d), rel=0.02)


def test_fringes_have_contrast_and_resolution_fills_them():
    f = xrr.film(100.0)
    q = np.linspace(0.12, 0.40, 2001)
    r = f.rrf(q)
    smeared = f.rrf(q, resolution=(0.02, 0.0))          # FWHM a third of a period
    assert r.max() / r.min() > 4
    lo = np.where((r[1:-1] < r[:-2]) & (r[1:-1] < r[2:]))[0] + 1
    hi = np.where((r[1:-1] > r[:-2]) & (r[1:-1] > r[2:]))[0] + 1
    assert len(lo) >= 4 and len(hi) >= 3
    assert np.all(smeared[lo] > 1.05 * r[lo]) and np.all(smeared[hi] < 0.97 * r[hi])   # measured 1.11-1.17, 0.95-0.96
    assert f.reflectivity(q, resolution=(0.0, 0.0)) == pytest.approx(f.reflectivity(q), rel=1e-12)


def test_kinematic_equals_parratt_at_large_qz_for_weak_contrast():
    weak = xrr.Profile([xrr.Layer(30.0, 0.36, 3.0), xrr.Layer(12.0, 0.31, 3.0)], xrr.RHO_WATER,
                       xrr.BETA_WATER_10KEV, 3.0)
    dev = lambda a, b: np.max(np.abs(weak.kinematic(np.linspace(a * QC, b * QC, 400))
                                     / weak.reflectivity(np.linspace(a * QC, b * QC, 400)) - 1))
    assert dev(8, 25) < 0.03                 # measured 2.5 %: refraction shifts the phases by ~Qc²d/2Qz
    assert dev(30, 50) < 0.6 * dev(4, 8)     # and the difference shrinks as Qz grows
    q = np.linspace(8 * QC, 25 * QC, 200)
    # with no layers it is the Debye–Waller form exactly
    w = xrr.bare_water()
    assert w.kinematic(q) == pytest.approx(w.fresnel(q) * np.exp(-q ** 2 * 9.0), rel=1e-12)


def test_dppc_profile_has_its_slabs_and_shows_a_minimum():
    d = xrr.dppc()
    z = np.array([-20.0, 8.0, 20.5, 60.0])
    rho = d.density(z)
    assert rho[0] == pytest.approx(0.0, abs=1e-6)
    assert rho[1] == pytest.approx(xrr.DPPC_TAIL[1], rel=0.02)
    assert rho[2] == pytest.approx(xrr.DPPC_HEAD[1], rel=0.05)
    assert rho[3] == pytest.approx(xrr.RHO_WATER, rel=1e-6)
    assert d.total_thickness == pytest.approx(25.0)
    q = np.linspace(0.05, 0.6, 2000)
    r = d.rrf(q)
    assert r.max() > 1.3 and r.min() < 0.05                  # the monolayer's first minimum is deep


def test_capillary_wave_roughness_of_water():
    assert xrr.KT_OVER_2PI_GAMMA_WATER == pytest.approx(0.910, abs=0.002)
    s = xrr.capillary_sigma()                                # q_max/q_min = 1e7
    assert 3.5 < s < 4.2
    assert xrr.capillary_sigma(q_min=1e-5) < s
    assert xrr.capillary_sigma(sigma0=2.0) == pytest.approx(math.hypot(2.0, s), rel=1e-12)


def test_smearing_is_a_normalised_average():
    lin = lambda q: 3.0 * q + 1.0
    q = np.linspace(0.1, 0.5, 9)
    assert xrr.smear(q, lin, (0.01, 0.01)) == pytest.approx(lin(q), rel=1e-12)
