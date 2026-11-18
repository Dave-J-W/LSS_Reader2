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
×1.01 on an attenuation of 10⁴.

The factor is nominal. The setting n is a sum of six binary-weighted foils
(1, 2, 4, …, 32 units; owner, 2026-11-18), so a thickness error is a sum
over the foils in use, not n times a per-unit error. Measured on NX school
scans 6–9 at 10 keV (`tests/tools/absorber_steps.py`, PHYSICS_ISSUES P28):
each step attenuates 7–11 % more than nominal (1.458–1.481 per unit).
Where the scale between scans is measured (Ref Patch), no nominal factor
is used.

Calibrated foils (``Foils``, ``calibrated``): the six foils measured on the
owner's data, 2025-12 to 2026-10, at 10 keV (provenance in
``CAL_PROVENANCE``). A setting n then attenuates by exp(μ Σ b_k t_k), not
absfac**n. ``attenuation(absfac, n)`` is the one place the reader turns a
setting into a factor; with a number it is absfac**n exactly as before.
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

AL_MAX_KEV = 10.52             # Al foils at 10.52 keV and below, incl. 10.05 (owner, D28, D30; 2026-11-18)
ENERGY_STEP_KEV = 0.01         # energies are rounded to 10 eV first: 1.24 Å (9.9987 keV)
                               # and 1.239835 Å (10.00004 keV) are both "10 keV"
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
    """Absorber factor per unit at ``energy`` (keV, rounded to 10 eV; at
    10 keV a 5 eV change is 0.15 % in μ/ρ), rounded like the field
    (4 decimals), and a note saying where it came from. ``(None, reason)``
    where the foil or its thickness is not known; nothing is guessed."""
    if energy is None or not energy > 0:
        return None, 'energy not known'
    e = round(round(energy / ENERGY_STEP_KEV) * ENERGY_STEP_KEV, 2)
    if e <= AL_MAX_KEV:
        if e < AL_MU_RHO[0][0]:
            return None, '%.2f keV is below the Al table' % e
        return round(factor(al_mu_rho(e)), 4), '50 um Al at %.2f keV (NIST SRD 126)' % e
    if abs(e - CU_KEV) <= 0.5:
        return None, '%.2f keV: Cu foils, unit thickness not known yet' % e
    return None, ('%.2f keV: the foils used at this energy are not known '
                  '(Al at <= 10.52 keV, Cu at 30 keV)' % e)


# --- calibrated foils (measured) ------------------------------------------

# Al-equivalent thickness (µm) at 10 keV of foil k (bit k of #A, 2**k units).
# Fit of 389 joins (of 409) across which Monc/Monp did not change, 10 keV,
# absorber removed, owner's data 2025-12 to 2026-10; reproduced to 0.1 µm by
# the analysing agent (hand-off 03 answer). tests/tools/foil_fit_from_joins.py.
CAL_FOILS_UM = (54.7, 112.2, 218.0, 432.1, 862.7, 1725.1)
CAL_FOILS_FIT_ERR_UM = (0.1, 0.1, 0.2, 0.2, 0.4, 0.5)   # statistical, from the fit
# Run-to-run (leave-one-run-out) spread of each foil, µm; ABSORBER_RATIOS.md
# (docs/handoff_out/03-answer), measured on 17 runs.
CAL_FOILS_RUN_UM = (0.6, 0.5, 0.8, 0.6, 1.3, 1.3)
# A ratio's relative error: the spreads of the foils that differ, in
# quadrature, plus the scatter of one step about the fit, 0.5 %. Tested
# there by predicting runs left out: right-sized for overlaps below
# Qz = 0.25 1/Å (68 % of errors within 0.95 σ); above it single steps
# scatter 3.2 times more (68 % within 3.19 σ), so σ is scaled by 3.2.
CAL_STEP_SCATTER = 0.005
CAL_HIGH_QZ = 0.25             # 1/Å
CAL_HIGH_QZ_SCALE = 3.2
CAL_ENERGY_KEV = 10.0
# Used from 9.70 to 10.30 keV with μ of Al at the energy: no K edge of the
# usual Al impurities lies between Zn (9.66 keV) and Ga (10.37 keV)
# (reasoning; edge energies from memory). Elsewhere the nominal 50 µm Al.
CAL_RANGE_KEV = (9.70, 10.30)
CAL_PROVENANCE = ('Measured on the owner\'s reflectivity data, 2025-12 to 2026-10: 389 joins at '
                  '10 keV across which Monc/Monp did not change (docs/physics_notes.md, '
                  '2026-11-18; docs/handoff_out/02, 03; PHYSICS_ISSUES P28)')


class Foils:
    """A binary foil set: setting n = Σ b_k 2**k puts foil k in when bit k
    is set; the beam is attenuated by exp(μ Σ b_k t_k), μ = μ/ρ·ρ of Al at
    ``energy_kev``, t_k the Al-equivalent thickness of foil k (µm)."""

    def __init__(self, thickness_um=CAL_FOILS_UM, energy_kev=CAL_ENERGY_KEV,
                 sigma_um=CAL_FOILS_RUN_UM):
        self.thickness_um = tuple(float(t) for t in thickness_um)
        self.energy_kev = round(float(energy_kev), 2)
        self.mu_per_um = al_mu_rho(self.energy_kev) * AL_DENSITY * 1e-4
        self.sigma_um = tuple(float(s) for s in sigma_um)

    def _bits(self, n):
        n = int(n)
        if not 0 <= n < 2 ** len(self.thickness_um):
            raise ValueError('absorber setting %r outside 0..%d' % (n, 2 ** len(self.thickness_um) - 1))
        return [(n >> k) & 1 for k in range(len(self.thickness_um))]

    def thickness(self, n):
        """Al-equivalent thickness (µm) in the beam at setting n."""
        return sum(t for b, t in zip(self._bits(n), self.thickness_um) if b)

    def factor(self, n):
        """1/T(n): what a count at setting n is multiplied by."""
        return math.exp(self.mu_per_um * self.thickness(n))

    def step(self, n_a, n_b, qz=None):
        """(T(n_a)/T(n_b), relative error): the scale between a scan at n_a
        and one at n_b. The error is μ·σ_k of each foil that differs, in
        quadrature, ⊕ CAL_STEP_SCATTER; × CAL_HIGH_QZ_SCALE when the overlap
        is at ``qz`` ≥ CAL_HIGH_QZ (1/Å). No error when n_a == n_b."""
        a, b = self._bits(n_a), self._bits(n_b)
        ratio = math.exp(-self.mu_per_um * (self.thickness(n_a) - self.thickness(n_b)))
        var = sum((self.mu_per_um * s) ** 2 for x, y, s in zip(a, b, self.sigma_um) if x != y)
        if var == 0:
            return ratio, 0.0
        rel = math.sqrt(var + CAL_STEP_SCATTER ** 2)
        if qz is not None and qz >= CAL_HIGH_QZ:
            rel *= CAL_HIGH_QZ_SCALE
        return ratio, rel

    def __eq__(self, other):
        return (isinstance(other, Foils) and self.thickness_um == other.thickness_um
                and self.energy_kev == other.energy_kev and self.sigma_um == other.sigma_um)

    def __hash__(self):
        return hash((self.thickness_um, self.energy_kev, self.sigma_um))

    def __repr__(self):         # a script line rebuilds it
        if (self.thickness_um, self.sigma_um) == (CAL_FOILS_UM, CAL_FOILS_RUN_UM):
            return 'absorbers.calibrated(%r)' % self.energy_kev
        return 'absorbers.Foils(%r, %r, %r)' % (self.thickness_um, self.energy_kev, self.sigma_um)

    __str__ = __repr__


def calibrated(energy):
    """The calibrated foils at ``energy`` (keV, rounded to 10 eV), or None
    outside CAL_RANGE_KEV."""
    if energy is None or not energy > 0:
        return None
    e = round(round(energy / ENERGY_STEP_KEV) * ENERGY_STEP_KEV, 2)
    if not CAL_RANGE_KEV[0] <= e <= CAL_RANGE_KEV[1]:
        return None
    return Foils(energy_kev=e)


def attenuation(absfac, n, power=1):
    """The factor for setting n: absfac.factor(n)**power for Foils, else
    absfac**n (power 1) or absfac**(power*n), the legacy arithmetic exactly."""
    if isinstance(absfac, Foils):
        return absfac.factor(n) ** power
    return absfac ** n if power == 1 else absfac ** (power * n)

