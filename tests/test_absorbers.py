"""Absorber factor per unit from the beam energy (F49; owner, 2026-11-17/18).

50 µm Al per unit at 10 keV and every lower energy; Cu at 30 keV (thickness
not known yet). μ/ρ from the NIST table the owner saved (SRD 126, Al).
"""
import math

import pytest

from lss_core import absorbers as A
from lss_core import absorbers


def test_table_rows_are_reproduced_exactly():
    for e, m in A.AL_MU_RHO:
        assert A.al_mu_rho(e) == pytest.approx(m, rel=1e-12)


def test_10_kev_is_the_default_factor():
    assert A.factor_at(10.0)[0] == A.ABSFAC_10KEV == 1.4247
    # 1.239835 A (bu 2026-09-02) is 10.00004 keV: still the 10 keV foil factor
    assert A.factor_at(A.energy_kev(1.239835))[0] == 1.4247
    assert A.energy_kev(1.239840) == pytest.approx(10.0, abs=1e-4)   # 10.000016 keV


def test_factors_at_the_energies_in_use():
    """6.21 and 7.514 keV are in the bu data (#W 1.996518 and 1.650036 A).
    Energies are rounded to 10 eV. Values computed by hand from the rows: exp(mu/rho * 2.699 * 50e-4)."""
    assert A.factor_at(6.0)[0] == 4.7397
    assert A.factor_at(8.0)[0] == 1.9723
    assert A.factor_at(A.energy_kev(1.996518))[0] == 4.0924      # 6.2100 keV
    assert A.factor_at(A.energy_kev(1.650036))[0] == 2.2589      # 7.514 -> 7.51 keV


def test_energies_are_rounded_to_10_ev():
    """The synthetic data's 1.24 A is 9.9987 keV: nominally 10 keV."""
    assert A.factor_at(A.energy_kev(1.24)) == (1.4247, '50 um Al at 10.00 keV (NIST SRD 126)')
    assert A.factor_at(10.004)[0] == 1.4247 and A.factor_at(10.006)[0] is None


def test_mu_rho_is_monotone_and_power_law_between_rows():
    es = [5 + 0.05 * k for k in range(101)]
    ms = [A.al_mu_rho(e) for e in es]
    assert all(a > b for a, b in zip(ms, ms[1:]))
    # log-log linear: the midpoint in log E has the geometric mean of the rows
    assert A.al_mu_rho(math.sqrt(6 * 8)) == pytest.approx(math.sqrt(115.3 * 50.33))


@pytest.mark.parametrize('energy', [10.0515, 10.515, 15.0])
def test_unknown_foil_above_10_kev_is_not_guessed(energy):
    a, why = A.factor_at(energy)
    assert a is None and 'not known' in why


def test_30_kev_is_copper_with_unknown_thickness():
    a, why = A.factor_at(A.energy_kev(0.41328))
    assert a is None and 'Cu' in why


def test_no_energy():
    assert A.factor_at(None) == (None, 'energy not known')
    with pytest.raises(ValueError):
        A.al_mu_rho(1.0)


# --- calibrated foils (owner's data, physics_notes 2026-11-18) -------------

def test_calibrated_foils_reproduce_the_measured_nx_school_steps():
    """NX school 20260923 S6-S9 (tests/test_absorber_steps.py: 0.788, 0.762,
    0.870 of nominal) are predicted by the calibrated foils to within their
    own error (μ·1 µm per foil changed), although they were not in the fit."""
    import math
    f = absorbers.calibrated(10.0)
    measured = {(41, 31): 0.0228871, (31, 24): 0.0639925, (24, 18): 0.1040}
    for (a, b), m in measured.items():
        r, e = f.step(a, b)
        assert abs(math.log(m / r)) < 2 * e
        assert abs(math.log(m / (absorbers.ABSFAC_10KEV ** -(a - b)))) > 10 * e   # nominal is far off


def test_calibrated_foils_arithmetic():
    import math
    f = absorbers.Foils()
    mu = absorbers.AL_MU_RHO_10KEV * absorbers.AL_DENSITY * 1e-4
    assert f.thickness(0) == 0 and f.factor(0) == 1.0
    assert f.thickness(41) == pytest.approx(54.7 + 432.1 + 1725.1)        # 101001
    assert f.factor(41) == pytest.approx(math.exp(mu * (54.7 + 432.1 + 1725.1)))
    r, e = f.step(42, 33)                  # 101010 -> 100001: foils 3, 1 in a; 0 in b
    assert r == pytest.approx(math.exp(-mu * (432.1 + 112.2 - 54.7)))
    assert e == pytest.approx(mu * 1.0 * math.sqrt(3))
    assert f.step(20, 20) == (1.0, 0.0)
    with pytest.raises(ValueError):
        f.factor(64)


def test_calibrated_range_and_script_form():
    assert absorbers.calibrated(10.0) == absorbers.Foils()
    assert absorbers.calibrated(9.70) is not None and absorbers.calibrated(10.30) is not None
    for e in (9.66, 9.69, 10.31, 10.52, 7.51, 30.0, None, 0):
        assert absorbers.calibrated(e) is None
    f = absorbers.calibrated(9.95)
    assert repr(f) == 'absorbers.calibrated(9.95)'
    assert eval(repr(f), {'absorbers': absorbers}) == f
    # μ follows Al's μ/ρ at the energy: 9.95 keV attenuates a little more than 10
    assert f.factor(1) > absorbers.calibrated(10.0).factor(1)


def test_attenuation_is_the_legacy_arithmetic_for_a_number():
    for a, n in ((1.4247, 0), (1.4247, 7), (4.0924, 31), (1.5, 3)):
        assert absorbers.attenuation(a, n) == a ** n
        assert absorbers.attenuation(a, n, 2.0) == a ** (2.0 * n)
    f = absorbers.calibrated(10.0)
    assert absorbers.attenuation(f, 5, 2.0) == f.factor(5) ** 2.0
