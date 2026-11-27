"""X-ray reflectivity of liquid interfaces with known truth.

Everything is in Å and Å⁻¹; Q means the momentum transfer normal to the
surface, Qz = 4π sin(α)/λ, and electron densities ρ are in e/Å³.

Physics (textbook; equation numbers are not quoted because they were not
re-checked against the books for this module):

* **Refractive index.** n = 1 − δ + iβ with δ = r_e λ² ρ / (2π)
  (J. Als-Nielsen and D. McMorrow, *Elements of Modern X-ray Physics*,
  2nd ed., Wiley 2011, ch. 3) and β = λ μ / (4π), μ the linear attenuation
  coefficient. In a medium j the normal wave vector, written as a Q, is

      Q_j = sqrt(Qz² − Qc_j² + i 32π² β_j / λ²),   Qc_j² = 16π r_e ρ_j,

  so Qc = 4 sqrt(π r_e ρ) does not depend on λ (anomalous dispersion f'
  ignored). For water, ρ = 0.334 e/Å³ gives Qc = 0.02175 Å⁻¹, the reader's
  default 0.0217 Å⁻¹ (``lss_core.reflectivity.finish``).
* **Fresnel reflectivity** of one sharp interface, R_F = |(Qz − Q_s)/(Qz +
  Q_s)|² (Als-Nielsen and McMorrow ch. 3): 1 below Qc without absorption,
  slightly less with it, and → (Qc / 2Qz)⁴ far above Qc.
* **Layers: Parratt recursion** (L. G. Parratt, Phys. Rev. 95, 359 (1954)),
  exact within the slab model (dynamical: multiple reflection and
  refraction included): from the substrate up,

      X_j = (r_j + X_{j+1} e^{i Q_{j+1} d_{j+1}}) / (1 + r_j X_{j+1} e^{i Q_{j+1} d_{j+1}}),

  r_j the Fresnel coefficient of interface j (between media j and j+1),
  X_N = 0 in the substrate, R = |X_0|².
* **Roughness.** Each interface's r_j is multiplied by the Névot–Croce
  factor exp(−Q_j Q_{j+1} σ_j² / 2) (L. Névot and P. Croce, Rev. Phys.
  Appl. 15, 761 (1980)); in kz units that is exp(−2 k_j k_{j+1} σ²). The
  alternative ``roughness='debye-waller'`` uses exp(−Q_j² σ_j² / 2) (the
  upper medium's Q only). Far above Qc both give R ≈ R_F exp(−Qz² σ²) for
  one interface; they differ near Qc, where the Névot–Croce factor tends to
  1 (Q_{j+1} → small) and the Debye–Waller one does not.
* **Capillary waves.** On a liquid surface σ is set by thermal capillary
  waves, σ² = σ_0² + (k_B T / 2πγ) ln(q_max / q_min) (A. Braslau et al.,
  Phys. Rev. Lett. 54, 114 (1985); P. S. Pershan and M. L. Schlossman,
  *Liquid Surfaces and Interfaces*, Cambridge 2012), q_min set by the
  instrument resolution and q_max ≈ π / (molecular size). For water at
  25 °C k_B T / 2πγ = 0.91 Å² (γ = 72 mN/m), so σ ≈ 3–4 Å for
  q_max/q_min = 10⁶–10⁸; measured water roughness is about 2.5–3.3 Å
  (Braslau et al. report 3.2 Å; quoted from memory). The default σ here is
  3.0 Å, a value inside that range, not a fit to any data.
* **Kinematic (master formula)** R/R_F = |(1/Δρ_s) Σ_j Δρ_j e^{−Qz² σ_j²/2}
  e^{i Qz z_j}|² (Als-Nielsen and McMorrow ch. 3; Pershan and Schlossman),
  Δρ_j the density step at interface j (depth z_j), Δρ_s the total, R_F
  the exact Fresnel curve of the substrate. It ignores refraction and
  multiple reflection inside the layers; for weak contrast it is within
  2–3 % of Parratt from Qc up and the difference shrinks as Qz grows
  (measured in tests/test_synthetic_xrr.py).
* **Kiessig fringes**: a layer of thickness d between two interfaces makes
  R/R_F oscillate with period ΔQz = 2π/d (H. Kiessig, Ann. Phys. 402, 769
  (1931)); refraction stretches the period slightly near Qc.
* **Resolution**: a Gaussian in Qz of FWHM ΔQ = dq + dq_rel·Qz, averaged by
  Gauss–Hermite quadrature (``smear``).

Absorption of water: β from μ/ρ = 5.329 cm²/g at 10 keV (NIST SRD 126,
J. H. Hubbell and S. M. Seltzer, table for liquid water; quoted from memory
because the NIST page could not be reached from this session) and ρ_mass =
0.997 g/cm³: μ = 5.31 cm⁻¹, β = 5.2×10⁻⁹ at 1.2398 Å.
"""
import math
from dataclasses import dataclass, field, replace

import numpy as np

R_E = 2.8179403262e-5        # Å, classical electron radius (CODATA 2018)
HC_KEV_ANGSTROM = 12.39842   # keV·Å, as lss_core.absorbers
ENERGY_KEV = 10.0            # ChemMatCARS 15-ID-C default energy
WAVELENGTH = HC_KEV_ANGSTROM / ENERGY_KEV     # 1.239842 Å

RHO_WATER = 0.334            # e/Å³ (1 g/cm³: 10 e per 18.015 g/mol gives 0.3343)
WATER_MU_RHO_10KEV = 5.329   # cm²/g, NIST SRD 126 (from memory, see module docstring)
WATER_DENSITY = 0.997        # g/cm³ at 25 °C
SIGMA_WATER = 3.0            # Å, default capillary-wave roughness of water (see docstring)
KT_OVER_2PI_GAMMA_WATER = 1.380649e-23 * 298.15 / (2 * math.pi * 0.07197) * 1e20   # Å², 0.910

# DPPC monolayer in the condensed phase: representative of the values
# reported by Helm, Möhwald, Kjaer and Als-Nielsen, Europhys. Lett. 4, 697
# (1987) and reviewed by Kjaer, Physica B 198, 100 (1994); quoted from
# memory, not checked against the papers. Consistent with the electron
# count (computed here): two palmitoyl chains, 242 e, over 48 Å² x 16 Å
# give 0.315 e/Å³; the rest of the molecule (164 e) plus hydration water
# over 48 Å² x 9 Å gives about 0.46 e/Å³.
DPPC_TAIL = (16.0, 0.320)    # thickness Å, ρ e/Å³
DPPC_HEAD = (9.0, 0.460)

# A generic dense film for Kiessig fringes: PMMA-like, 1.18 g/cm³, C5H8O2
# (100.12 g/mol, 54 e) gives 0.383 e/Å³ (computed). No claim that such a
# film is stable on water: it is a test object.
FILM_RHO = 0.383


def qc(rho):
    """Critical Qz (Å⁻¹) of a medium of electron density ``rho`` (e/Å³)
    against vacuum: 4 sqrt(π r_e ρ)."""
    return 4.0 * math.sqrt(math.pi * R_E * rho)


def rho_from_qc(q):
    """Inverse of ``qc``."""
    return q * q / (16.0 * math.pi * R_E)


def delta(rho, wavelength=WAVELENGTH):
    """δ of n = 1 − δ + iβ."""
    return R_E * wavelength ** 2 * rho / (2.0 * math.pi)


def beta_from_mu(mu_per_cm, wavelength=WAVELENGTH):
    """β = λ μ / 4π, with μ in cm⁻¹ and λ in Å."""
    return wavelength * mu_per_cm * 1e-8 / (4.0 * math.pi)


BETA_WATER_10KEV = beta_from_mu(WATER_MU_RHO_10KEV * WATER_DENSITY)   # 5.24e-9


def capillary_sigma(q_max=1.0, q_min=1e-7, sigma0=0.0, kt_over_2pi_gamma=KT_OVER_2PI_GAMMA_WATER):
    """Capillary-wave roughness (Å): sqrt(σ0² + kT/(2πγ) ln(q_max/q_min)).
    Defaults: water at 25 °C, q_max = 1 Å⁻¹, q_min = 1e-7 Å⁻¹ (an
    assumption: the in-plane resolution of a liquid reflectometer)."""
    return math.sqrt(sigma0 ** 2 + kt_over_2pi_gamma * math.log(q_max / q_min))


@dataclass
class Layer:
    """A slab: ``thickness`` (Å), electron density ``rho`` (e/Å³),
    absorption ``beta``, and ``sigma`` (Å), the roughness of the interface
    at its top."""
    thickness: float
    rho: float
    sigma: float = SIGMA_WATER
    beta: float = 0.0
    name: str = ''


@dataclass
class Profile:
    """Ambient (vacuum/air, ρ = 0) on top, ``layers`` from the top down,
    then the semi-infinite substrate (``rho``, ``beta``) whose top
    interface has roughness ``sigma``."""
    layers: list = field(default_factory=list)
    rho: float = RHO_WATER
    beta: float = BETA_WATER_10KEV
    sigma: float = SIGMA_WATER
    name: str = ''
    roughness: str = 'nevot-croce'      # or 'debye-waller', or 'none'

    # ---- the slab model -------------------------------------------------
    def media(self):
        """(rho, beta, thickness) of every medium from the ambient down,
        and the roughness of each interface (one fewer)."""
        rho = [0.0] + [l.rho for l in self.layers] + [self.rho]
        beta = [0.0] + [l.beta for l in self.layers] + [self.beta]
        d = [0.0] + [l.thickness for l in self.layers] + [0.0]
        sig = [l.sigma for l in self.layers] + [self.sigma]
        return np.array(rho), np.array(beta), np.array(d), np.array(sig)

    def interfaces(self):
        """Depths z_j (Å, 0 at the top, positive into the liquid), density
        steps Δρ_j and roughnesses σ_j of every interface."""
        rho, _, d, sig = self.media()
        z = np.concatenate([[0.0], np.cumsum(d[1:-1])])
        return z, np.diff(rho), sig

    def density(self, z):
        """Electron density ρ(z) (e/Å³) of the error-function profile, z in
        Å below the top interface."""
        z = np.asarray(z, dtype=float)
        from scipy.special import erf
        zj, drho, sig = self.interfaces()
        out = np.zeros_like(z)
        for a, b, s in zip(zj, drho, sig):
            out = out + b * 0.5 * (1 + (erf((z - a) / (s * math.sqrt(2))) if s > 0 else np.sign(z - a)))
        return out

    @property
    def total_thickness(self):
        return float(sum(l.thickness for l in self.layers))

    # ---- reflectivities ---------------------------------------------------
    def reflectivity(self, qz, wavelength=WAVELENGTH, resolution=None):
        """R(Qz) by the Parratt recursion; ``resolution`` = (dq, dq_rel) or
        (dq, dq_rel, rule): Gaussian of FWHM dq + dq_rel·Qz (None: no
        smearing; ``smear``)."""
        f = lambda q: parratt(q, self, wavelength)
        return smear(qz, f, resolution) if resolution else f(qz)

    def fresnel(self, qz, wavelength=WAVELENGTH, absorption=True):
        """Fresnel reflectivity of the bare substrate (sharp, with its β
        unless ``absorption`` is False)."""
        return fresnel(qz, self.rho, self.beta if absorption else 0.0, wavelength)

    def rrf(self, qz, wavelength=WAVELENGTH, resolution=None):
        """R / R_F, R_F of the sharp bare substrate."""
        return self.reflectivity(qz, wavelength, resolution) / self.fresnel(qz, wavelength)

    def kinematic(self, qz, wavelength=WAVELENGTH):
        """Master-formula reflectivity (see module docstring)."""
        return kinematic(qz, self, wavelength)

    def with_roughness(self, sigma):
        """The same profile with every interface's roughness set to ``sigma``."""
        return replace(self, layers=[replace(l, sigma=sigma) for l in self.layers], sigma=sigma)


def _q_in(qz, rho, beta, wavelength):
    q2 = np.asarray(qz, dtype=float) ** 2
    return np.sqrt(q2 - 16 * math.pi * R_E * rho + 1j * (32 * math.pi ** 2 * beta / wavelength ** 2)
                   + 0j)


def parratt(qz, profile, wavelength=WAVELENGTH):
    """Parratt recursion with the profile's roughness model (see module
    docstring). ``qz`` ≥ 0, any shape."""
    qz = np.abs(np.asarray(qz, dtype=float))
    rho, beta, d, sig = profile.media()
    Q = [_q_in(qz, r, b, wavelength) for r, b in zip(rho, beta)]
    Q[0] = qz + 0j            # ambient: exactly Qz
    X = np.zeros(qz.shape, dtype=complex)
    for j in range(len(rho) - 2, -1, -1):
        r = (Q[j] - Q[j + 1]) / (Q[j] + Q[j + 1] + 1e-300)
        if profile.roughness == 'nevot-croce':
            r = r * np.exp(-0.5 * Q[j] * Q[j + 1] * sig[j] ** 2)
        elif profile.roughness == 'debye-waller':
            r = r * np.exp(-0.5 * Q[j] ** 2 * sig[j] ** 2)
        elif profile.roughness != 'none':
            raise ValueError('roughness %r: nevot-croce, debye-waller or none' % profile.roughness)
        p = np.exp(1j * Q[j + 1] * d[j + 1])
        X = (r + X * p) / (1 + r * X * p)
    out = np.abs(X) ** 2
    return np.where(qz == 0, 1.0, out)


def fresnel(qz, rho=RHO_WATER, beta=BETA_WATER_10KEV, wavelength=WAVELENGTH):
    """Fresnel reflectivity of a sharp interface vacuum / medium."""
    return parratt(qz, Profile(layers=[], rho=rho, beta=beta, sigma=0.0, roughness='none'), wavelength)


def fresnel_no_absorption(qz, q_c):
    """|(Qz − √(Qz² − Qc²)) / (Qz + √(Qz² − Qc²))|², 1 below Qc: the
    reader's ``lss_core.stitching.fresnel`` in closed form."""
    qz = np.asarray(qz, dtype=float)
    s = np.sqrt(np.maximum(qz ** 2 - q_c ** 2, 0.0))
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(qz <= q_c, 1.0, ((qz - s) / (qz + s)) ** 2)


def kinematic(qz, profile, wavelength=WAVELENGTH):
    """Master formula R = R_F |Σ_j (Δρ_j/Δρ_s) e^{−Qz²σ_j²/2} e^{iQz z_j}|²,
    R_F of the sharp bare substrate (with its β)."""
    qz = np.abs(np.asarray(qz, dtype=float))
    z, drho, sig = profile.interfaces()
    total = profile.rho
    amp = np.zeros(qz.shape, dtype=complex)
    for a, b, s in zip(z, drho, sig):
        amp = amp + (b / total) * np.exp(-0.5 * qz ** 2 * s ** 2) * np.exp(1j * qz * a)
    return fresnel(qz, profile.rho, profile.beta, wavelength) * np.abs(amp) ** 2


_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(31)     # weight exp(-x²/2)
_GH_W = _GH_W / _GH_W.sum()
# 'fine' (2026-11-27): Simpson's rule on 1601 points over ±8σ. The 31-node Gauss–Hermite rule is
# off by up to 0.9 % at the critical edge at σ_Q 3.8e-4 Å⁻¹ and 2 % at 8e-4 (water, 10 keV;
# against a 40001-point integral; R_F has a square-root kink there), which matters for known
# truth at the edge (tests/tools/qoff_resolution_study.py). The default stays Gauss–Hermite so
# that no earlier study's synthetic data change.
_FINE_X = np.linspace(-8.0, 8.0, 1601)
_FINE_W = np.exp(-0.5 * _FINE_X ** 2) * np.r_[1, np.tile([4, 2], 799), 4, 1]
_FINE_W = _FINE_W / _FINE_W.sum()
SMEAR_RULES = {'gauss-hermite': (_GH_X, _GH_W), 'fine': (_FINE_X, _FINE_W)}


def smear(qz, func, resolution):
    """⟨func(Qz + ε)⟩ over a Gaussian ε of FWHM dq + dq_rel·Qz;
    ``resolution`` = (dq, dq_rel) in Å⁻¹ and relative, or (dq, dq_rel,
    rule) with rule 'gauss-hermite' (the default, 31 nodes) or 'fine'
    (Simpson on 1601 points over ±8σ: use it at the critical edge, where
    Gauss–Hermite is off by about 1 % at the beamline's resolution).
    |Qz + ε| is used where the Gaussian reaches below zero."""
    dq, rel = resolution[:2]
    x, w = SMEAR_RULES[resolution[2] if len(resolution) > 2 else 'gauss-hermite']
    qz = np.asarray(qz, dtype=float)
    s = (dq + rel * qz) / (2 * math.sqrt(2 * math.log(2)))
    q = np.abs(qz[..., None] + s[..., None] * x)
    return np.sum(func(q) * w, axis=-1)


def kiessig_period(d):
    """Expected fringe period 2π/d (Å⁻¹) of a layer of thickness d (Å)."""
    return 2 * math.pi / d


# ---- presets ----------------------------------------------------------------

def bare_water(sigma=SIGMA_WATER, beta=BETA_WATER_10KEV, roughness='nevot-croce'):
    """The water–air interface: ρ = 0.334 e/Å³, β at 10 keV, σ = 3.0 Å."""
    return Profile([], RHO_WATER, beta, sigma, 'bare water', roughness)


def dppc(sigma=SIGMA_WATER, tail=DPPC_TAIL, head=DPPC_HEAD, roughness='nevot-croce'):
    """A DPPC monolayer on water (condensed phase): tails (16 Å, 0.320
    e/Å³) over heads (9 Å, 0.460 e/Å³), every interface σ; values in the
    module constants with their source."""
    layers = [Layer(tail[0], tail[1], sigma, name='tails'), Layer(head[0], head[1], sigma, name='heads')]
    return Profile(layers, RHO_WATER, BETA_WATER_10KEV, sigma, 'DPPC on water', roughness)


def film(thickness=100.0, rho=FILM_RHO, sigma=SIGMA_WATER, roughness='nevot-croce'):
    """A uniform film (default 100 Å, 0.383 e/Å³) on water: clear Kiessig
    fringes of period 2π/d."""
    return Profile([Layer(thickness, rho, sigma, name='film')], RHO_WATER, BETA_WATER_10KEV, sigma,
                   '%g A film on water' % thickness, roughness)


PRESETS = {'water': bare_water, 'dppc': dppc, 'film': film}
