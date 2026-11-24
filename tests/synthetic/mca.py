"""MCA spectra of fluorescence lines under a monochromatic beam, together
with the scatter of the beam that lies under them, with known truth (F90,
owner 2026-11-23: "a gauntlet of true MCA spectra must show the fit holds
against the direct-beam scatter (Rayleigh, Compton), the hard case being
Zn Kα (8637 eV) under 10 keV excitation").

``xfntr.spectrum`` has Gaussian lines, an elastic peak and a flat
background only. This module adds what sits under a weak line next to the
beam energy, and keeps every part apart, per channel. A line fit or a
window sum over a box can then be judged against the counts it should
have found:

    from synthetic import mca
    s = mca.spectrum({'Zn': 1e3}, elastic=1e6, beam=mca.Beam(compton_core=0.2),
                     detector=mca.Detector(shelf=1e-3))
    s.energy, s.expected                   # nominal keV per channel; expected counts
    s.photopeak('Zn', 'Ka')                # the Kα photopeak, per channel (the truth)
    s.part(sources=('Rayleigh', 'Compton'), kinds=('escape',))
    counts = s.draw(rng)                   # Poisson

Physics. Textbook results; values from memory are marked so, with no
page or equation numbers.

* **Lines.** Kα1, Kα2 and Kβ1 of each element in ``ELEMENTS``, at the
  energies of the X-ray Data Booklet (A. C. Thompson et al., LBNL 2009,
  Table 1-2, after Bearden 1967). Relative intensities are 100 : 51 : 17
  (Table 1-3, from memory; measured Kβ/Kα of Cu and Zn are 0.12–0.14,
  e.g. Ertuğral et al. 2007, so ``kb_scale`` can raise it). A line is
  excited only when the beam is above its K edge (Table 1-1).
  ``lines[element]`` is the number of the element's K photons that reach
  the detector, before the detector splits them into photopeak, tail,
  shelf and escape.
* **Rayleigh** (elastic) scatter at the beam energy E0.
* **Compton** scatter at E_C = E0 / (1 + (E0/mc²)(1 − cos 2θ)) (Compton
  1923): 9.81 keV for 10 keV at 90°. It is broadened by the electrons'
  momenta (the impulse approximation; P. Eisenberger and P. M. Platzman,
  Phys. Rev. A 2, 415, 1970). The profile in energy is the hydrogenic
  J(ΔE) ∝ (1 + (ΔE/w)²)⁻³, whose tails fall as ΔE⁻⁶; its FWHM is
  2w·√(2^(1/3) − 1) = 1.0196 w. There are two parts:
  - the valence electrons (``compton_fwhm``; about 0.19 keV for water at
    10 keV and 90°, from J(0) ≈ 3.5 a.u.⁻¹ for 10 electrons and
    0.102 keV per a.u. of p_z, from memory);
  - a core part (``compton_core``, its fraction of the Compton photons;
    2 of water's 10 electrons are O 1s). It is broad (``compton_core_fwhm``:
    p0 = Z_eff ≈ 7.7 a.u., so about 0.8 keV) and cut off where the energy
    given to the electron is below its binding energy (E' < E0 − B, with
    B = 0.532 keV for O 1s). This is the sharp cutoff of R. Ribberfors,
    Phys. Rev. B 12, 2067 (1975), and of the analytic profiles of D. Brusa
    et al., NIM A 379, 167 (1996). Real profiles are tabulated by F. Biggs,
    L. B. Mendelsohn and J. B. Mann, At. Data Nucl. Data Tables 16, 201
    (1975).

  Assumptions: water's profile is close to these shapes; the spread of
  scattering angles over the detector's solid angle (≈ 0.05 keV for
  ±15° at 90°) is folded into ``compton_fwhm``; ``compton_ratio`` (the
  number of Compton over Rayleigh photons) is a free parameter, since it
  depends on the geometry and the polarisation.
* **Detector** (a Si drift detector). Every photon of energy E is
  detected as one of four things:
  - a **photopeak**, a Gaussian with FWHM² = noise² + 8 ln2·ε·F·E (as
    ``xfntr.fwhm_kev``);
  - a low-energy **exponential tail** (``tail``, decay length
    ``tail_slope``), the exponentially modified Gaussian of incomplete
    charge collection;
  - a flat **shelf** (``shelf``) from 0 to E, an error-function step.
    Tail and shelf are the Hypermet function's terms (G. W. Phillips and
    K. W. Marlow, NIM 137, 525, 1976), as AXIL uses them for Si detectors
    (P. Van Espen and co-workers);
  - a **Si K escape** peak at E − 1.740 keV (Si Kα), for E above the Si K
    edge (1.839 keV). Its fraction is Reed's formula for a thick detector
    at normal incidence (S. J. B. Reed and N. G. Ware, J. Phys. E 5, 582,
    1972):

        f = ½ ω_K (1 − 1/r) [1 − (μ_K/μ_E) ln(1 + μ_E/μ_K)],

    with ω_K(Si) = 0.050 (Krause 1979), 1 − 1/r = 0.90 (r the jump
    ratio), μ_K = 350 cm²/g (Si Kα in Si) and μ_E = 33.9·(10/E)^2.75 cm²/g
    (a power law through NIST XCOM's values from 2 to 10 keV). All of
    these are from memory. The result is f ≈ 0.10 % at 10 keV and 0.15 %
    at 8.6 keV; ``escape`` multiplies it (0: no escape peaks).
* **Background**: ``background`` + ``slope``·E counts per channel
  (electronics, cosmic rays, scatter from elsewhere), clipped at 0.
* **Calibration**: the channels' true energies are
  (a + ``offset``) + b(1 + ``gain``)·c + q·c², while the spectrum carries
  the nominal (a, b, q), as a file whose calibration is slightly off would
  (channels c = 1…N, as ``fluorescence.normalise_spectrum`` numbers them).
* Counts are Poisson (``draw``).

The hard case is built in. Under 10 keV excitation, Zn Kα (8.631 keV,
intensity-weighted) has these neighbours:
- the escape peaks of the elastic (8.26 keV) and Compton (8.07 keV) lines,
  both inside a ±3·FWHM box around the line;
- the valence Compton tail, which falls as ΔE⁻⁶ across the box;
- the core Compton wing below 9.47 keV;
- Zn Kβ (9.572 keV), 0.24 keV below the Compton peak;
- Cu Kα (8.048 keV) and Kβ (8.905 keV), when there is copper about.
"""
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.special import erf, erfc, erfcx

from . import xfntr

ME_C2_KEV = 510.99895                 # electron rest energy (CODATA 2018)
SI_KA_KEV = 1.740                     # Si Kα (X-ray Data Booklet Table 1-2: Kα1 1.73998)
SI_K_EDGE_KEV = 1.8389
CALIB = (0.0, 0.01, 0.0)              # keV = a + b·channel + c·channel² (10 eV channels; an assumption)
CHANNELS = 2048
KA, KB = ('Ka1', 'Ka2'), ('Kb1',)

# element: (K edge keV, ((line, keV, relative intensity), ...)); X-ray Data Booklet Tables 1-1 to 1-3 (from memory)
ELEMENTS = {
    'Fe': (7.112, (('Ka1', 6.40384, 100.0), ('Ka2', 6.39084, 50.0), ('Kb1', 7.05798, 17.0))),
    'Ni': (8.333, (('Ka1', 7.47815, 100.0), ('Ka2', 7.46089, 51.0), ('Kb1', 8.26466, 17.0))),
    'Cu': (8.979, (('Ka1', 8.04778, 100.0), ('Ka2', 8.02783, 51.0), ('Kb1', 8.90529, 17.0))),
    'Zn': (9.659, (('Ka1', 8.63886, 100.0), ('Ka2', 8.61578, 51.0), ('Kb1', 9.5720, 17.0))),
    'Ga': (10.367, (('Ka1', 9.25174, 100.0), ('Ka2', 9.22482, 51.0), ('Kb1', 10.2642, 17.0))),
    'Br': (13.474, (('Ka1', 11.9242, 100.0), ('Ka2', 11.8776, 52.0), ('Kb1', 13.2914, 18.0))),
}


def line_energy(element, which='Ka'):
    """Intensity-weighted energy (keV) of an element's Kα (Ka1 + Ka2) or Kβ:
    where a fit placed from the element starts (Zn Kα: 8.631 keV)."""
    names = KA if which == 'Ka' else KB
    ls = [(e, i) for n, e, i in ELEMENTS[element][1] if n in names]
    return sum(e * i for e, i in ls) / sum(i for _, i in ls)


def compton_energy(e0, angle_deg):
    """Energy (keV) of a photon of ``e0`` Compton-scattered through 2θ = ``angle_deg``
    by a free electron at rest."""
    return e0 / (1.0 + e0 / ME_C2_KEV * (1.0 - math.cos(math.radians(angle_deg))))


def reed_escape(e_kev, omega=0.050, jump=0.90, mu_k=350.0):
    """Si K escape fraction at ``e_kev`` (Reed and Ware 1972; constants from
    memory, see the module docstring); 0 below the Si K edge."""
    if e_kev <= SI_K_EDGE_KEV:
        return 0.0
    mu_e = 33.9 * (10.0 / e_kev) ** 2.75
    a = mu_k / mu_e
    return 0.5 * omega * jump * (1.0 - a * math.log1p(1.0 / a))


@dataclass(frozen=True)
class Detector:
    """The detector's response (module docstring). ``noise``: electronic
    noise FWHM (keV); ``tail``, ``shelf``: fractions of every photon put in
    the exponential tail (decay length ``tail_slope`` keV) and the flat
    shelf; ``escape``: multiple of Reed's escape fraction."""
    noise: float = xfntr.NOISE_FWHM_KEV
    eps: float = xfntr.EPS_SI_KEV
    fano: float = xfntr.FANO_SI
    tail: float = 0.0
    tail_slope: float = 0.15
    shelf: float = 0.0
    escape: float = 1.0

    def fwhm(self, e_kev):
        return xfntr.fwhm_kev(max(float(e_kev), 0.0), self.noise, self.eps, self.fano)

    def escape_fraction(self, e_kev):
        return self.escape * reed_escape(e_kev)


@dataclass(frozen=True)
class Beam:
    """Beam energy (keV), scattering angle 2θ to the detector (deg), and the
    Compton scatter: ``compton_ratio`` Compton / Rayleigh photons, the
    valence profile's FWHM, the core part's fraction, FWHM and binding
    energy (keV)."""
    energy: float = 10.0
    angle: float = 90.0
    compton_ratio: float = 1.0
    compton_fwhm: float = 0.19
    compton_core: float = 0.0
    compton_core_fwhm: float = 0.8
    compton_core_binding: float = 0.532
    compton_model: str = 'hydrogenic'      # or 'shells': water's electron shells (``WATER_SHELLS``, study B)
    core_scale: float = 1.0                # shells: × the O 1s electrons (0: none)
    doppler_scale: float = 1.0             # shells: × every shell's momentum width

    @property
    def compton(self):
        return compton_energy(self.energy, self.angle)


# Water's electron shells for the 'shells' Compton model (study B, 2026-11-24): (name, electrons,
# orbital, effective charge Z_eff, binding keV). Hydrogenic momentum densities with Clementi and
# Raimondi's (1963) Slater exponents, Z_eff = n ζ (O 1s ζ 7.658, 2s 2.246, 2p 2.227; from memory);
# for H in the O-H bond ζ ≈ 1.2 (an assumption between the free atom's 1.0 and H2's 1.19).
# Bindings: O 1s 0.543 keV (X-ray Data Booklet, the O K edge, from memory), the valence ones
# 0.03 keV or less (water's 2a1, 1b2, 3a1, 1b1 levels). Tabulated Hartree-Fock profiles (Biggs,
# Mendelsohn and Mann 1975) were not available offline: this is an approximation, swept in the
# study by core_scale and doppler_scale.
WATER_SHELLS = (
    ('O 1s', 2, '1s', 7.658, 0.543),
    ('O 2s', 2, '2s', 2 * 2.246, 0.032),
    ('O 2p', 4, '2p', 2 * 2.227, 0.013),
    ('H 1s', 2, '1s', 1.2, 0.016),
)
ALPHA_INV = 137.035999          # 1/α: p_z in atomic units from units of mc


def compton_pz(e0, e1, angle_deg):
    """The electron's momentum along the scattering vector, p_z (atomic
    units), for a photon scattered from ``e0`` to ``e1`` (keV) through 2θ:
    the impulse approximation's p_z = mc [E0 E1 (1 − cos 2θ) − mc² (E0 − E1)]
    / (mc² |k0 − k1|) (P. Eisenberger and P. M. Platzman 1970; R. Ribberfors
    1975). Zero at the free-electron Compton energy, positive above it."""
    c = math.cos(math.radians(angle_deg))
    e1 = np.asarray(e1, float)
    num = e0 * e1 * (1.0 - c) - ME_C2_KEV * (e0 - e1)
    den = ME_C2_KEV * np.sqrt(e0 ** 2 + e1 ** 2 - 2.0 * e0 * e1 * c)
    return ALPHA_INV * num / den


def hydrogenic_profile(q, orbital, z_eff):
    """Compton profile J(q) (per electron, ∫J dq = 1) of a hydrogenic
    orbital: J(q) = 2π ∫_|q|^∞ ρ(p) p dp, with the momentum densities
    ρ_1s ∝ (p² + p0²)⁻⁴, ρ_2s ∝ (p² − p0²)² (p² + p0²)⁻⁶ and
    ρ_2p ∝ p² (p² + p0²)⁻⁶, p0 = Z_eff/n (Podolsky and Pauling 1929)."""
    n = {'1s': 1, '2s': 2, '2p': 2}[orbital]
    p0 = z_eff / n
    p = np.linspace(0.0, 40.0 * p0, 20001)
    if orbital == '1s':
        rho = (p ** 2 + p0 ** 2) ** -4
    elif orbital == '2s':
        rho = (p ** 2 - p0 ** 2) ** 2 * (p ** 2 + p0 ** 2) ** -6
    else:
        rho = p ** 2 * (p ** 2 + p0 ** 2) ** -6
    tail = np.concatenate([np.cumsum((rho * p)[::-1])[::-1]])      # ∫_p^∞ ρ p dp (up to the step)
    j = tail / np.trapezoid(tail, p) / 2.0                          # J on q ≥ 0; ∫ over q from −∞ to ∞ is 1
    return np.interp(np.abs(np.asarray(q, float)), p, j, right=0.0)


def shell_compton(beam, e1):
    """Compton photons per keV at energies ``e1`` (keV) per Compton photon of
    the free-electron reference (all water's electrons, no binding), split
    into the valence and O 1s parts: (valence, core). Each shell's J(p_z)
    |dp_z/dE| (the impulse approximation), cut off where the energy given
    to the electron is below its binding, E0 − E1 < B."""
    e1 = np.asarray(e1, float)
    pz = compton_pz(beam.energy, e1, beam.angle)
    dpz = np.abs(np.gradient(pz, e1))
    total = sum(n for _, n, _, _, _ in WATER_SHELLS)
    val, core = np.zeros_like(e1), np.zeros_like(e1)
    for name, n, orb, z, b in WATER_SHELLS:
        lam = beam.doppler_scale
        j = hydrogenic_profile(pz / lam, orb, z) / lam
        w = (n / total) * j * dpz * (beam.energy - e1 > b)
        if name == 'O 1s':
            core += beam.core_scale * w
        else:
            val += w
    return val, core


def _hydrogenic(fwhm, span=10.0, n=401):
    """Offsets (keV) and weights (sum 1) of J(ΔE) ∝ (1 + (ΔE/w)²)⁻³."""
    w = fwhm / (2.0 * math.sqrt(2.0 ** (1.0 / 3.0) - 1.0))
    d = np.linspace(-span * w, span * w, n)
    j = (1.0 + (d / w) ** 2) ** -3
    return d, j / j.sum()


@dataclass
class Spectrum:
    """Expected counts per channel, kept by part. ``energy``: nominal keV
    of each channel (what a reader computes from the file's calibration);
    ``energy_true``: where the channels really are; ``parts[(source,
    kind)]``: expected counts per channel, with source one of 'Zn Ka1', …,
    'Rayleigh', 'Compton', 'background' and kind one of 'peak', 'tail',
    'shelf', 'escape' ('flat' for the background); ``photons[source]``:
    photons of each source reaching the detector."""
    energy: np.ndarray
    energy_true: np.ndarray
    calib: tuple
    parts: dict
    photons: dict
    beam: Beam
    detector: Detector
    lines: dict = field(default_factory=dict)

    @property
    def expected(self):
        return np.sum(list(self.parts.values()), axis=0)

    def part(self, sources=None, kinds=None):
        """Sum of the parts whose source starts with one of ``sources`` (None:
        all) and whose kind is in ``kinds`` (None: all)."""
        out = np.zeros(len(self.energy))
        for (src, kind), v in self.parts.items():
            if sources is not None and not any(src == s or src.startswith(s + ' ') for s in sources):
                continue
            if kinds is not None and kind not in kinds:
                continue
            out = out + v
        return out

    def photopeak(self, element, which='Ka'):
        """Expected photopeak counts per channel of an element's Kα (Ka1 +
        Ka2) or Kβ: what a Gaussian line fit measures."""
        names = KA if which == 'Ka' else KB
        return self.part(sources=['%s %s' % (element, n) for n in names], kinds=('peak',))

    def draw(self, rng):
        """Poisson counts (float array)."""
        return rng.poisson(self.expected).astype(float)


def _response(edges, e, n, det, out, kinds=('peak', 'tail', 'shelf', 'escape')):
    """Add the detector's response to ``n`` photons at energies ``e`` (arrays)
    to ``out[kind]``, on channels with true bin edges ``edges``."""
    e = np.atleast_1d(np.asarray(e, float))[:, None]
    n = np.atleast_1d(np.asarray(n, float))[:, None]
    lo, hi = edges[None, :-1], edges[None, 1:]
    mid, width = 0.5 * (lo + hi), hi - lo
    sig = np.array([det.fwhm(v) for v in e[:, 0]])[:, None] / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    esc = np.array([det.escape_fraction(v) for v in e[:, 0]])[:, None]
    p_peak = np.clip(1.0 - det.tail - det.shelf - esc, 0.0, 1.0)
    r2 = math.sqrt(2.0)

    def gauss(c, s):
        return 0.5 * (erf((hi - c) / (r2 * s)) - erf((lo - c) / (r2 * s)))
    out['peak'] += np.sum(n * p_peak * gauss(e, sig), axis=0)
    if det.tail > 0:
        b = det.tail_slope
        z = ((mid - e) / sig + sig / b) / r2
        a = (mid - e) / b + sig ** 2 / (2 * b ** 2)
        with np.errstate(over='ignore', invalid='ignore'):
            t = np.where(z > 0, np.exp(a - z ** 2) * erfcx(np.maximum(z, 0)), np.exp(np.minimum(a, 700)) * erfc(z))
        out['tail'] += np.sum(n * det.tail * t / (2 * b) * width, axis=0)
    if det.shelf > 0:
        sh = np.where(mid > 0, erfc((mid - e) / (r2 * sig)) / (2.0 * e), 0.0)
        out['shelf'] += np.sum(n * det.shelf * sh * width, axis=0)
    if np.any(esc > 0):
        ee = e - SI_KA_KEV
        se = np.array([det.fwhm(v) for v in ee[:, 0]])[:, None] / (2.0 * math.sqrt(2.0 * math.log(2.0)))
        out['escape'] += np.sum(n * esc * gauss(ee, se), axis=0)


def spectrum(lines, elastic=0.0, beam=Beam(), detector=Detector(), background=0.0, slope=0.0,
             calib=CALIB, channels=CHANNELS, offset=0.0, gain=0.0, kb_scale=1.0):
    """The expected spectrum (``Spectrum``). ``lines``: {element: K photons
    reaching the detector}; ``elastic``: Rayleigh photons (Compton:
    ``beam.compton_ratio`` × that); ``background``, ``slope``: counts per
    channel and per channel per keV; ``offset`` (keV) and ``gain``
    (relative): the calibration error; ``kb_scale``: multiplies every Kβ
    intensity."""
    a, b, q = calib
    c = np.arange(1, channels + 1, dtype=float)
    nominal = a + b * c + q * c ** 2
    ch = np.arange(0.5, channels + 1.0, 1.0)
    edges = (a + offset) + b * (1 + gain) * ch + q * ch ** 2
    true = 0.5 * (edges[:-1] + edges[1:])
    parts, photons = {}, {}

    def add(source, e, n):
        acc = {k: np.zeros(channels) for k in ('peak', 'tail', 'shelf', 'escape')}
        _response(edges, e, n, detector, acc)
        for k, v in acc.items():
            if np.any(v):
                parts[(source, k)] = v
        photons[source] = float(np.sum(n))

    for el, total in (lines or {}).items():
        edge, ls = ELEMENTS[el]
        if beam.energy <= edge or total <= 0:
            continue
        w = np.array([i * (kb_scale if name in KB else 1.0) for name, _, i in ls])
        for (name, e, _), f in zip(ls, w / w.sum()):
            add('%s %s' % (el, name), [e], [total * f])
    if elastic > 0:
        add('Rayleigh', [beam.energy], [elastic])
        nc = elastic * beam.compton_ratio
        if nc > 0 and beam.compton_model == 'shells':
            ec = beam.compton
            de = 0.004
            e1 = np.arange(ec - 4.0, min(ec + 1.0, beam.energy), de)
            val, core = shell_compton(beam, e1)
            add('Compton valence', e1, nc * val * de)
            if beam.core_scale > 0:
                add('Compton core', e1, nc * core * de)
        elif nc > 0:
            ec = beam.compton
            d, wv = _hydrogenic(beam.compton_fwhm)
            ev, nv = ec + d, nc * (1.0 - beam.compton_core) * wv
            if beam.compton_core > 0:
                d2, w2 = _hydrogenic(beam.compton_core_fwhm)
                keep = ec + d2 < beam.energy - beam.compton_core_binding    # energy given below the binding: no scatter
                if keep.any():
                    w2 = np.where(keep, w2, 0.0)
                    ev = np.r_[ev, ec + d2]
                    nv = np.r_[nv, nc * beam.compton_core * w2]     # the cut-off part is lost (bound electrons)
            add('Compton', ev, nv)
    bg = np.clip(background + slope * true, 0.0, None)
    if np.any(bg):
        parts[('background', 'flat')] = bg
    return Spectrum(nominal, true, tuple(calib), parts, photons, beam, detector, dict(lines or {}))


def write_dataset(root, spectra, counts, qz=None, monitor=1e6, real=10.0, live=10.0, name='mca'):
    """A SPEC file with one getandsave_mca scan per spectrum and vortex/
    beside it (the layout of ``xfntr.write_dataset``), with the spectra's
    nominal calibration. Returns the SPEC path."""
    qz = np.zeros(len(counts)) if qz is None else np.asarray(qz, float)
    truth = xfntr.XfntrTruth(qz, np.array([s.photons.get('Rayleigh', 0.0) for s in spectra]),
                             [s.expected for s in spectra], [s.part(kinds=('peak',)) for s in spectra],
                             monitor, real, live, xfntr.Sample(), xfntr.Line())
    return xfntr.write_dataset(root, counts, truth, name=name, energy_kev=spectra[0].beam.energy,
                               calib=spectra[0].calib)
