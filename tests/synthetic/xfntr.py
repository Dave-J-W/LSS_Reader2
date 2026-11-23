"""Fluorescence near total reflection (XFNTR) with known truth.

``synth.xfntr_yield`` is only a smooth hump; this module gives the
physical shape, the line's energy-dependent width and MCA files the
reader opens (same layout as ``synth.make_xfntr_dataset``).

Physics (sharp interface; textbook, e.g. Als-Nielsen and McMorrow ch. 3;
for XFNTR at liquid surfaces see W. Bu, D. Vaknin and co-workers, and
Schlossman's group; cited from memory, no equation numbers):

* field at the surface: |T(Qz)|² = |2Qz / (Qz + Q_s)|², Q_s = sqrt(Qz² −
  Qc² + i 32π²β/λ²) as in ``synthetic.xrr``: 4 at Qc (without absorption),
  → 1 far above;
* penetration depth of the intensity, Λ = 1 / Im Q_s: about 1/sqrt(Qc² −
  Qz²) (≈ 50 Å) below Qc, the absorption length λ/(4πβ)·sin α above;
* yield per incident photon, up to a constant:

      Y(Qz) = v(Qz) · |T|² · (Γ + c · Λ_eff),   Λ_eff = 1 / (1/Λ + μ_e),

  Γ the ions at the interface (per Å², in arbitrary units), c the bulk
  concentration (same units per Å), μ_e the attenuation of the emitted line
  on its way out (1/Å; 0: none), v the fraction of the footprint the
  detector sees (1 when it sees all of it; with ``view_mm``, min(1,
  view_mm · sin α / beam_mm)).
* spectrum: the line (Kα, and Kβ at ``kb_ratio``) as Gaussians whose FWHM
  grows with energy, FWHM² = noise² + 8 ln2 · ε F E (Si: ε = 3.65 eV, Fano
  factor F = 0.115; noise 0.12 keV, an assumption for a Vortex), an elastic
  line at the beam energy ∝ |T|²Λ_eff (bulk scattering, an assumption), a
  flat background; Poisson counts at real/live time and Monc.
"""
import math
import os
from dataclasses import dataclass

import numpy as np

import synth
from . import xrr

EPS_SI_KEV = 0.00365
FANO_SI = 0.115
NOISE_FWHM_KEV = 0.12
CALIB = (0.0, 0.02, 0.0)          # keV = a + b·channel + c·channel², as synth.XF_CALIB
CHANNELS = 512


def fwhm_kev(energy_kev, noise=NOISE_FWHM_KEV, eps=EPS_SI_KEV, fano=FANO_SI):
    """Energy resolution of a Si drift detector (keV) at ``energy_kev``."""
    return math.sqrt(noise ** 2 + 8 * math.log(2) * eps * fano * energy_kev)


def _qs(qz, rho, beta, wavelength):
    return np.sqrt(np.asarray(qz, float) ** 2 - 16 * math.pi * xrr.R_E * rho
                   + 1j * 32 * math.pi ** 2 * beta / wavelength ** 2 + 0j)


def transmission(qz, rho=xrr.RHO_WATER, beta=xrr.BETA_WATER_10KEV, wavelength=xrr.WAVELENGTH):
    """|T|² at a sharp vacuum/medium interface."""
    qz = np.asarray(qz, float)
    return np.abs(2 * qz / (qz + _qs(qz, rho, beta, wavelength))) ** 2


def penetration_depth(qz, rho=xrr.RHO_WATER, beta=xrr.BETA_WATER_10KEV, wavelength=xrr.WAVELENGTH):
    """1/e depth of the intensity (Å): 1 / Im Q_s."""
    return 1.0 / _qs(qz, rho, beta, wavelength).imag


@dataclass
class Sample:
    """Γ (surface) and c (bulk) in arbitrary units; ``escape`` μ_e in 1/Å."""
    surface: float = 1.0
    bulk: float = 0.0
    escape: float = 0.0
    rho: float = xrr.RHO_WATER
    beta: float = xrr.BETA_WATER_10KEV


def yield_curve(qz, sample=Sample(), wavelength=xrr.WAVELENGTH, view_mm=None, beam_mm=0.02):
    """Y(Qz) of the module docstring (per incident photon, arbitrary units)."""
    qz = np.asarray(qz, float)
    t2 = transmission(qz, sample.rho, sample.beta, wavelength)
    lam = penetration_depth(qz, sample.rho, sample.beta, wavelength)
    eff = 1.0 / (1.0 / lam + sample.escape)
    v = 1.0
    if view_mm is not None:
        sin_a = qz * wavelength / (4 * math.pi)
        v = np.minimum(1.0, view_mm * sin_a / beam_mm)
    return v * t2 * (sample.surface + sample.bulk * eff)


@dataclass
class Line:
    """An emission line: Kα energy (keV), Kβ energy and Kβ/Kα ratio."""
    ka: float = 6.40               # Fe Kα (keV); any element by its energies
    kb: float = 7.06
    kb_ratio: float = 0.13


def spectrum(line_counts, line=Line(), elastic_counts=0.0, energy_kev=10.0, background=2.0,
             calib=CALIB, channels=CHANNELS):
    """Expected counts per channel (channels 1..N, keV = calib(channel)) and
    the expected counts of the line alone (Kα + Kβ), per channel."""
    ch = np.arange(1, channels + 1)
    e = calib[0] + calib[1] * ch + calib[2] * ch ** 2
    de = calib[1] + 2 * calib[2] * ch

    def peak(e0, n):
        s = fwhm_kev(e0) / (2 * math.sqrt(2 * math.log(2)))
        g = np.exp(-0.5 * ((e - e0) / s) ** 2) * de / (s * math.sqrt(2 * math.pi))
        return n * g
    lc = peak(line.ka, line_counts / (1 + line.kb_ratio)) + peak(line.kb, line_counts * line.kb_ratio / (1 + line.kb_ratio))
    return lc + peak(energy_kev, elastic_counts) + background, lc


@dataclass
class XfntrTruth:
    qz: np.ndarray
    line_counts: np.ndarray        # expected counts in the line (Kα + Kβ), per spectrum
    spectra: list                  # expected spectra
    lines: list                    # expected line part per channel
    monitor: float
    real: float
    live: float
    sample: Sample
    line: Line


def measure(qz, sample=Sample(), line=Line(), photons=4e4, elastic=2e3, monitor=2e5, real=10.0, live=9.0,
            background=2.0, wavelength=xrr.WAVELENGTH, seed=0, **kw):
    """Spectra at the Qz points: the line holds ``photons`` × Y(Qz)/max Y
    expected counts, the elastic line ``elastic`` × |T|²Λ_eff / its max.
    Returns (list of count arrays, XfntrTruth); counts are Poisson unless
    ``seed`` is None."""
    qz = np.atleast_1d(np.asarray(qz, float))
    y = yield_curve(qz, sample, wavelength, **kw)
    n_line = photons * y / y.max()
    bulk = yield_curve(qz, Sample(0.0, 1.0, sample.escape, sample.rho, sample.beta), wavelength, **kw)
    n_el = elastic * bulk / bulk.max()
    rng = np.random.default_rng(seed) if seed is not None else None
    counts, exp, lines = [], [], []
    for a, b in zip(n_line, n_el):
        s, lc = spectrum(a, line, b, xrr.HC_KEV_ANGSTROM / wavelength, background)
        exp.append(s)
        lines.append(lc)
        counts.append(rng.poisson(s).astype(float) if rng is not None else s)
    return counts, XfntrTruth(qz, n_line, exp, lines, monitor, real, live, sample, line)


def write_dataset(root, counts, truth, name='xf', absorber=0, energy_kev=10.0, calib=CALIB):
    """SPEC file with one getandsave_mca scan per spectrum and vortex/ beside
    it, as ``synth.make_xfntr_dataset`` writes them (``calib``: the
    calibration written, keV = a + b·channel + c·channel²). Returns the SPEC
    path."""
    root = str(root)
    os.makedirs(os.path.join(root, 'vortex'), exist_ok=True)
    scans = []
    tag = '' if absorber is None else '#A x %d\n' % absorber
    for n, (q, y) in enumerate(zip(truth.qz, counts), start=1):
        scans.append('#S %d  getandsave_mca %g\n#Q 0 0 %.6g\n#W x %g\n%s\n' % (n, truth.real, q, synth.WAVELENGTH, tag))
        path = os.path.join(root, 'vortex', '%s_%d_mca' % (name, n))
        with open(path, 'w') as f:
            f.write('#F %s\n\n#S 1  getandsave_mca %g\n' % (os.path.basename(path), truth.real))
            f.write('#@CTIME %g %g %g\n' % (truth.real, truth.real, truth.live))
            f.write('#Monc %g\n#Q 0 0 %.6g\n' % (truth.monitor, q))
            f.write('#@CALIB %g %g %g\n#Energy %g\n' % (tuple(calib) + (energy_kev,)))
            vals = ['%d' % v if float(v).is_integer() else '%.6f' % v for v in y]
            chunks = [vals[k:k + 16] for k in range(0, len(vals), 16)]
            for k, c in enumerate(chunks):
                f.write(('@A ' if k == 0 else '') + ' '.join(c) + ('\\\n' if k < len(chunks) - 1 else '\n'))
            f.write('\n')
    return synth.write_spec(os.path.join(root, name), scans)
