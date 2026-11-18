"""Absorber foils: the transmission factor per absorber unit.

At ChemMatCARS 15-ID-C each absorber unit is 50 µm more aluminium at
10 keV and at every lower energy (the foils are not changed below 10 keV);
at 30 keV the foils are copper (owner, 2026-11-17). SPEC's ``#A`` gives the
number of units n, and the beam is attenuated by absfac**-n with

    absfac = exp(μ/ρ · ρ · t)      (Beer–Lambert)

μ/ρ is the total mass attenuation coefficient (coherent scattering
included: a scattered photon leaves the beam), from the NIST table of
J. H. Hubbell and S. M. Seltzer, X-Ray Mass Attenuation Coefficients, NIST
Standard Reference Database 126,
https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z13.html
(doi:10.18434/T4D01F). The rows below were copied from that page as saved
by the owner on 2026-11-18 (μ/ρ column only, energies above the Al K edge).
ρ = 2.699 g/cm³ is the density NIST uses for Al (its Table 1); that value
is cited from memory, the saved page does not give it.

Between table energies μ/ρ is interpolated linearly in log μ/ρ against
log E (there is no absorption edge of Al between 1.56 keV and 20 MeV).
Measured on these rows: a local quadratic in log–log differs from the
linear one by 0.07–0.08 % in μ/ρ at 6.21 keV and 0.11–0.13 % at 7.51 keV.
μ/ρ enters as absfac**n = exp(n·μ/ρ·ρ·t), so that is ≈0.1 % of ln(absfac**n):
×1.01 on an attenuation of 10⁴. The foils' thickness tolerance is larger
(2 % in t is 2 % of ln(absfac**n): ×1.2 on 10⁴).

The factor is nominal: the foils' real thickness compounds over n units.
Where the scale between scans is measured (Ref Patch), no nominal factor
is used.
"""
import math

HC_KEV_ANGSTROM = 12.39842      # keV·Å, the constant the program uses for E = hc/λ

# NIST SRD 126, aluminium (Z = 13): energy (keV), μ/ρ (cm²/g), above the K edge
AL_MU_RHO = (
    (2.0, 2263.0), (3.0, 788.0), (4.0, 360.5), (5.0, 193.4), (6.0, 115.3),
    (8.0, 50.33), (10.0, 26.23), (15.0, 7.955), (20.0, 3.441), (30.0, 1.128),
    (40.0, 0.5685), (50.0, 0.3681), (60.0, 0.2778), (80.0, 0.2018), (100.0, 0.1704),
)
AL_MU_RHO_10KEV = 26.23        # cm²/g, the 10 keV row above
AL_DENSITY = 2.699             # g/cm³ (NIST SRD 126, Table 1; from memory)
UNIT_THICKNESS_UM = 50.0       # µm of Al per absorber unit (owner)

AL_MAX_KEV = 10.0              # Al foils at 10 keV and below (owner, D28, D30)
ENERGY_TOLERANCE_KEV = 0.01    # 1.239835 Å is 10.00004 keV: still "10 keV"
CU_KEV = 30.0                  # Cu foils at 30 keV (owner, D28); thickness not known


def factor(mu_rho=AL_MU_RHO_10KEV, density=AL_DENSITY, thickness_um=UNIT_THICKNESS_UM):
    """Transmission factor of one absorber unit, exp(μ/ρ · ρ · t)."""
    return math.exp(mu_rho * density * thickness_um * 1e-4)


ABSFAC_10KEV = round(factor(), 4)   # 1.4247, the window's and the scripts' default


def al_mu_rho(energy_kev):
    """μ/ρ of Al (cm²/g) at ``energy_kev``, log–log interpolation of the
    NIST rows; ValueError outside them."""
    rows = AL_MU_RHO
    if not rows[0][0] <= energy_kev <= rows[-1][0]:
        raise ValueError('energy %g keV outside the Al table (%g to %g keV)'
                         % (energy_kev, rows[0][0], rows[-1][0]))
    for (e0, m0), (e1, m1) in zip(rows, rows[1:]):
        if energy_kev <= e1:
            w = math.log(energy_kev / e0) / math.log(e1 / e0)
            return math.exp(math.log(m0) + w * math.log(m1 / m0))


def energy_kev(wavelength_angstrom):
    """Photon energy (keV) from the wavelength (Å) of SPEC's ``#W`` line."""
    return HC_KEV_ANGSTROM / wavelength_angstrom


def factor_at(energy):
    """Absorber factor per unit at ``energy`` (keV), rounded like the field
    (4 decimals), and a note saying where it came from. ``(None, reason)``
    where the foil or its thickness is not known; nothing is guessed."""
    if energy is None or not energy > 0:
        return None, 'energy not known'
    if energy <= AL_MAX_KEV + ENERGY_TOLERANCE_KEV:
        if energy < AL_MU_RHO[0][0]:
            return None, '%.4f keV is below the Al table' % energy
        a = round(factor(al_mu_rho(min(energy, AL_MAX_KEV))), 4)
        return a, '50 um Al at %.4f keV (NIST SRD 126)' % energy
    if abs(energy - CU_KEV) <= 0.5:
        return None, '%.4f keV: Cu foils, unit thickness not known yet' % energy
    return None, ('%.4f keV: the foils used at this energy are not known '
                  '(Al at <= 10 keV, Cu at 30 keV)' % energy)
