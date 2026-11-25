"""More MCA spectra with known truth: any element and line family that
``data/xrf_tables.json`` holds (K lines from Ca to Y, L lines of La, Gd, Er,
Lu and Pb), with tabulated line energies and relative intensities, and
water's Compton scatter from tabulated Hartree–Fock profiles (XRF
shootout, 2026-11-25).

``mca.spectrum`` stays as it is. This module builds on its detector
response (``mca._response``: photopeak, tail, shelf, Si escape) and its
Rayleigh peak, and adds:

* **Tabulated lines** (``lines={'Zn K': 1e3, 'Pb L': 300}``): every line of
  the family at xraylib's energy, with xraylib's relative intensity at the
  beam energy (photo-ionisation, fluorescence yields, radiative rates and
  Coster–Kronig cascades: ``CS_FluorLine_Kissel_Cascade``). The numbers are
  ``tests/tools/xrf_tables.py``'s, committed as JSON, so nothing here needs
  xraylib. ``mca.ELEMENTS`` puts Kβ/Kα at 0.113 (from memory); xraylib
  gives 0.134–0.164 for Fe to Br (``docs/studies/xrf_shootout/
  physics_check.csv``).
* **Compton scatter** by one of three models (``compton=``):
  - ``'hydrogenic'`` and ``'shells'``: ``mca``'s own (``Beam.compton_model``);
  - ``'biggs'``: water's O 1s, O 2s, O 2p and H 1s from the tables of
    Biggs, Mendelsohn and Mann (1975) as xraylib holds them, in the impulse
    approximation (``mca.compton_pz``), each cut off at its binding. These
    are free-atom profiles; ``Beam.core_scale`` and ``doppler_scale``
    scale them as in ``mca.shell_compton``.

The truth: ``s.photopeak_family('Zn K')`` is the photopeak counts of every
line of the family per channel; ``s.photons['Zn K Ka1']`` and the like are
the photons per line reaching the detector; ``family_photons(s, 'Zn K')``
their sum.
"""
import json
import math
import os
from dataclasses import replace

import numpy as np

from . import mca

_PATH = os.path.join(os.path.dirname(__file__), 'data', 'xrf_tables.json')
with open(_PATH, encoding='utf-8') as _f:
    TABLES = json.load(_f)
_PZ = np.asarray(TABLES['water_compton']['pz'], float)
_SHELLS = [(s['shell'], s['electrons'], np.asarray(s['J'], float), s['binding_kev'])
           for s in TABLES['water_compton']['shells']]


def family_lines(key, beam_kev):
    """[(line, keV, relative intensity)] of the family ``key`` ('Zn K',
    'Pb L') under a beam of ``beam_kev``, from the tabulated beam energy
    nearest below it; [] when the beam is below the family's edge."""
    entry = TABLES['lines'][key]
    if beam_kev <= entry['edge']:
        return []
    rows = [float(b) for b in entry['beams'] if float(b) <= beam_kev + 1e-9]
    if not rows:
        return []
    b = max(rows)
    return [tuple(v) for v in entry['beams']['%g' % b]]


def line_energies(key):
    """{line: keV} of every line of the family, excited or not."""
    return dict(TABLES['lines'][key]['energies'])


def main_line(key, beam_kev=None):
    """(keV, name) of a family's strongest line group: the intensity-weighted
    Kα1 + Kα2 (or Lα1 + Lα2) energy. Where a box fit is placed."""
    fam = TABLES['lines'][key]['family']
    names = ('Ka1', 'Ka2') if fam == 'K' else ('La1', 'La2')
    b = beam_kev if beam_kev is not None else max(float(v) for v in TABLES['lines'][key]['beams'])
    ls = [(e, i) for n, e, i in family_lines(key, b) if n in names]
    if not ls:
        e = line_energies(key)
        ls = [(e[n], 1.0) for n in names if n in e]
    return sum(e * i for e, i in ls) / sum(i for _, i in ls), '+'.join(names)


def biggs_compton(beam, e1):
    """Compton photons per keV at ``e1`` (keV) per Compton photon, split into
    (valence, O 1s core): the tabulated profiles in the impulse approximation."""
    e1 = np.asarray(e1, float)
    pz = mca.compton_pz(beam.energy, e1, beam.angle)
    dpz = np.abs(np.gradient(pz, e1))
    total = sum(n for _, n, _, _ in _SHELLS)
    val, core = np.zeros_like(e1), np.zeros_like(e1)
    lam = beam.doppler_scale
    for name, n, j, b in _SHELLS:
        jj = np.interp(np.abs(pz) / lam, _PZ, j, right=0.0) / lam / n      # per electron
        w = (n / total) * jj * dpz * (beam.energy - e1 > b)
        if name == 'O 1s':
            core += beam.core_scale * w
        else:
            val += w
    return val, core


def spectrum(lines, elastic=0.0, beam=mca.Beam(), detector=mca.Detector(), background=0.0, slope=0.0,
             calib=mca.CALIB, channels=mca.CHANNELS, offset=0.0, gain=0.0, compton='biggs'):
    """Expected spectrum (``mca.Spectrum``). ``lines``: {family: photons
    reaching the detector}, families as in ``xrf_tables.json`` ('Zn K',
    'Pb L'); ``compton``: 'biggs', 'shells' or 'hydrogenic'. Other arguments
    as ``mca.spectrum``."""
    if compton in ('shells', 'hydrogenic'):
        base = mca.spectrum({}, elastic, replace(beam, compton_model=compton), detector, background, slope,
                            calib, channels, offset, gain)
    elif compton == 'biggs':
        base = mca.spectrum({}, elastic, replace(beam, compton_ratio=0.0), detector, background, slope,
                            calib, channels, offset, gain)
    else:
        raise ValueError('compton %r: biggs, shells or hydrogenic' % compton)
    a, b, q = calib
    ch = np.arange(0.5, channels + 1.0, 1.0)
    edges = (a + offset) + b * (1 + gain) * ch + q * ch ** 2
    parts, photons = dict(base.parts), dict(base.photons)

    def add(source, e, n):
        acc = {k: np.zeros(channels) for k in ('peak', 'tail', 'shelf', 'escape')}
        mca._response(edges, e, n, detector, acc)
        for k, v in acc.items():
            if np.any(v):
                parts[(source, k)] = parts.get((source, k), 0.0) + v
        photons[source] = photons.get(source, 0.0) + float(np.sum(n))

    if compton == 'biggs' and elastic > 0 and beam.compton_ratio > 0:
        nc = elastic * beam.compton_ratio
        de = 0.004
        e1 = np.arange(beam.compton - 4.0, min(beam.compton + 1.0, beam.energy), de)
        val, core = biggs_compton(beam, e1)
        add('Compton valence', e1, nc * val * de)
        if beam.core_scale > 0:
            add('Compton core', e1, nc * core * de)
    for key, total in (lines or {}).items():
        ls = family_lines(key, beam.energy)
        if not ls or total <= 0:
            continue
        for name, e, f in ls:
            add('%s %s' % (key, name), [e], [total * f])
    s = mca.Spectrum(base.energy, base.energy_true, tuple(calib), parts, photons, beam, detector, dict(lines or {}))
    return s


def photopeak_family(s, key):
    """Expected photopeak counts per channel of every line of a family."""
    return s.part(sources=[key], kinds=('peak',))


def family_photons(s, key):
    """Photons of the family reaching the detector (the truth a full-spectrum
    fit of the element estimates, up to its own line ratios)."""
    return float(sum(v for src, v in s.photons.items() if src.startswith(key + ' ')))
