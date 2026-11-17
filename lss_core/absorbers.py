"""Absorber foils: the transmission factor per absorber unit.

At ChemMatCARS 15-ID-C, for 10 keV, each absorber unit is 50 µm more
aluminium (owner, 2026-11-17); SPEC's ``#A`` gives the number of units n,
and the beam is attenuated by absfac**-n with

    absfac = exp(μ/ρ · ρ · t)      (Beer–Lambert)

μ/ρ is the total mass attenuation coefficient (coherent scattering
included: a scattered photon leaves the beam). Values for Al at 10 keV from
the NIST table of Hubbell & Seltzer, X-Ray Mass Attenuation Coefficients,
NIST Standard Reference Database 126,
https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z13.html
(μ/ρ = 26.23 cm²/g at 1.0E-02 MeV; ρ = 2.699 g/cm³). Cited from memory: the
site could not be reached from the session that wrote this (2026-11-17);
check against the table.

The factor is nominal: the foils' real thickness (tolerance typically a
few %) compounds over n units. Where the scale between scans is measured
(Ref Patch), no nominal factor is used.

Other energies: the beamline may use other foils (the owner said 50 µm Al
is what is used *for 10 keV*); exp(μ/ρ(E)·ρ·t) for Al is not assumed (F49).
"""
import math

AL_MU_RHO_10KEV = 26.23        # cm²/g, total, Al at 10 keV (NIST SRD 126)
AL_DENSITY = 2.699             # g/cm³ (NIST SRD 126)
UNIT_THICKNESS_UM = 50.0       # µm of Al per absorber unit at 10 keV (owner)


def factor(mu_rho=AL_MU_RHO_10KEV, density=AL_DENSITY, thickness_um=UNIT_THICKNESS_UM):
    """Transmission factor of one absorber unit, exp(μ/ρ · ρ · t)."""
    return math.exp(mu_rho * density * thickness_um * 1e-4)


ABSFAC_10KEV = round(factor(), 4)   # 1.4247, the window's and the scripts' default
