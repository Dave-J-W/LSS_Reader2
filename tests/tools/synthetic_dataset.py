"""A synthetic data set with known truth, written to a folder, to open in
the reader (owner, 2026-11-23: the Tools menu's demonstrations; the
generators are those of docs/SYNTHETIC_DATA.md).

    python tests/tools/synthetic_dataset.py --out DIR                       # 100 Å film, NX-like scans
    python tests/tools/synthetic_dataset.py --out DIR --truth water --counts 0.1
    python tests/tools/synthetic_dataset.py --out DIR --fault slits         # a slit change Monc misses (P29)
    python tests/tools/synthetic_dataset.py --out DIR --kind xfntr
    python tests/tools/synthetic_dataset.py --out DIR --kind burn
    python tests/tools/synthetic_dataset.py --out DIR --kind mca --beam 12   # study B's hard case at 12 keV

Kinds:

- ``xrr``: four reflectivity scans cut like NX school scans 6–9 from the
  truth (``synthetic.xrr``: Parratt with Névot–Croce roughness, water's
  critical edge, a film's Kiessig fringes), Poisson counts in the reader's
  ROI boxes through the calibrated foils, Monc as the owner describes it
  (no Poisson noise, 0.05 %) unless ``--monitor poisson``
  (``synthetic.xrr_scans``), rendered as a SPEC file and Pilatus frames
  whose box sums reproduce the reduced rows exactly
  (``synthetic.xrr_images``). ``truth.csv``: R(Qz) on a fine grid;
  ``truth.json``: the settings and the true join factors the legacy chain
  should find.
- ``xfntr``: fluorescence near total reflection, one MCA file per Qz, a
  surface ion and a bulk ion (``synthetic.xfntr``); ``truth.csv``: the line
  counts per Qz.
- ``burn``: one spot measured 21 times, the reflected peak decaying with
  τ = 400 s, no noise (``synth.make_burn_dataset``).
- ``mca``: study B's hard case (F90; ``docs/reports/mca_fit_demo.md``),
  ``--spectra`` MCA spectra drawn from one truth (``synthetic.mca``: the
  line, Rayleigh and water's Compton shell by shell, Reed's escapes, tail
  and shelf), one scan each: select them all and "Fit lines" fits them as
  the gauntlet does. ``--beam``, ``--element``, ``--photons``, ``--wing``
  (the O 1s Compton wing × water's) and ``--escape`` (× Reed's fraction)
  as the demo's. ``truth.json``: the line's true photopeak counts per
  spectrum (what a fit should find) and in the ±2 FWHM box (what a window
  sum's line part is).

The SPEC file's path is the last line printed (``SPEC <path>``): the Tools
window opens it in the reader. Writes only under ``--out``.
"""
import argparse
import json
import os
import sys
from dataclasses import replace

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))

FAULTS = ('none', 'slits', 'foil')


def xrr_dataset(out, truth='film', thickness=100.0, counts=1.0, monitor='real', fault='none', seed=0,
                roughness=None, background=1.0):
    from synthetic import xrr, xrr_scans as xs, xrr_images as xi
    sig = {} if roughness is None else {'sigma': float(roughness)}
    profile = {'film': lambda: xrr.film(thickness, **sig), 'water': lambda: xrr.bare_water(**sig),
               'dppc': lambda: xrr.dppc(**sig)}[truth]()
    faults = {}
    if fault == 'slits':        # slits open x2.7 and x3.2 for scans 3 and 4; Monc registers 70 % of it (P29)
        faults['monitor_gain'] = [1.0, 1.0, 0.7 * xs.NX_SLIT_GAINS[2], 0.7 * xs.NX_SLIT_GAINS[3]]
    elif fault == 'foil':       # the foils of scan 3 transmit 2 % less than calibrated
        faults['attenuation_error'] = [1.0, 1.0, 0.98, 1.0]
    bl = xs.Beamline()
    if monitor == 'real':
        bl = replace(bl, **xs.REAL_MONITOR)
    bl = replace(bl, flux=bl.flux * counts, max_rate=bl.max_rate * counts, monc_rate=bl.monc_rate * counts,
                 monp_rate=bl.monp_rate * counts, background=bl.background * background)
    data = xs.measure(profile, xs.nx_like_plan(**faults), beamline=bl, errors='counting+monitor', seed=seed)
    spec = xi.render(data, out, 'xrr', seed=seed)
    qz = np.linspace(0.01, 0.5, 981)
    np.savetxt(os.path.join(out, 'truth.csv'), np.column_stack([qz, data.truth(qz)]), delimiter=',',
               header='true reflectivity of the synthetic data set: Qz (1/A), R', comments='# ')
    info = dict(kind='xrr', truth=truth, thickness_A=thickness if truth == 'film' else None, counts=counts,
                monitor=monitor, fault=fault, seed=seed, scans=sorted(data.scans),
                roughness_A=roughness if roughness is not None else xrr.SIGMA_WATER, background_scale=background,
                true_join_factors={str(k): float(v) for k, v in data.true_join_factors().items()},
                kiessig_period=xrr.kiessig_period(thickness) if truth == 'film' else None)
    return spec, info


def xfntr_dataset(out, seed=0):
    from synthetic import xfntr as xf
    qz = np.round(np.linspace(0.006, 0.04, 18), 4)
    counts, truth = xf.measure(qz, xf.Sample(1.0, 2e-4), seed=seed)
    spec = xf.write_dataset(out, counts, truth)
    np.savetxt(os.path.join(out, 'truth.csv'), np.column_stack([truth.qz, truth.line_counts]), delimiter=',',
               header='expected counts in the fluorescence line per spectrum: Qz (1/A), counts', comments='# ')
    return spec, dict(kind='xfntr', seed=seed, scans=list(range(1, len(qz) + 1)))


def mca_dataset(out, beam=10.0, element='Zn', photons=1e3, wing=1.0, escape=1.0, spectra=10, seed=0):
    import mca_fit_gauntlet as g
    from synthetic import mca
    cond = g.hard_case(beam, element, photons, wing, escape)
    if not g.excited(cond):
        raise SystemExit('%g keV is below the %s K edge (%.3f keV)' % (beam, element, mca.ELEMENTS[element][0]))
    s = cond.spectrum()
    rng = np.random.default_rng([20261124, seed])
    counts = [s.draw(rng) for _ in range(int(spectra))]
    qz = np.round(np.linspace(0.01, 0.01 + 0.002 * (len(counts) - 1), len(counts)), 4)
    spec = mca.write_dataset(out, [s] * len(counts), counts, qz=qz, monitor=1e6)
    lo, hi = cond.box_range()
    box = (s.energy >= lo) & (s.energy <= hi)
    return spec, dict(kind='mca', describe=cond.describe, beam_keV=beam, element=element, photons=photons,
                      wing=wing, escape=escape, seed=seed, scans=list(range(1, len(counts) + 1)),
                      line_keV=cond.line, box_keV=[lo, hi], fwhm_keV=cond.fwhm,
                      true_line_counts=float(s.photopeak(element).sum()),
                      true_line_counts_in_box=float(s.photopeak(element)[box].sum()),
                      expected_counts_in_box=float(s.expected[box].sum()))


def burn_dataset(out):
    import synth
    spec = synth.make_burn_dataset(out)
    return spec, dict(kind='burn', frames=synth.BURN_FRAMES, tau_s=synth.BURN_TAU, count_time_s=synth.BURN_CTIME,
                      scans=[1])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True, help='folder to write into (created)')
    ap.add_argument('--kind', choices=('xrr', 'xfntr', 'burn', 'mca'), default='xrr')
    ap.add_argument('--truth', choices=('film', 'water', 'dppc'), default='film', help='xrr: the true interface')
    ap.add_argument('--thickness', type=float, default=100.0, help='xrr film thickness (Å); fringes of period 2π/d')
    ap.add_argument('--counts', type=float, default=1.0, help='xrr: beam and monitors scaled (1: the NX school rates)')
    ap.add_argument('--monitor', choices=('real', 'poisson'), default='real',
                    help="xrr: Monc with the owner's 0.05 %% (real) or as Poisson counts")
    ap.add_argument('--fault', choices=FAULTS, default='none',
                    help='xrr: slits = Monc misses the slit change at scans 3-4; foil = scan 3\'s foils 2 %% off')
    ap.add_argument('--roughness', type=float, default=None,
                    help='xrr: every interface\'s roughness σ (Å; default the generator\'s, 3 Å): R/R_F falls as '
                         'exp(-Qz²σ²)')
    ap.add_argument('--background', type=float, default=1.0,
                    help='xrr: the diffuse background scaled (1: the NX school level)')
    ap.add_argument('--beam', type=float, default=10.0, help='mca: the beam energy (keV)')
    ap.add_argument('--element', default='Zn', help='mca: the fluorescing element (Zn, Fe, Cu, Ni, Ga, Br)')
    ap.add_argument('--photons', type=float, default=1e3, help="mca: the line's K photons per spectrum (1e6 elastic)")
    ap.add_argument('--wing', type=float, default=1.0, help="mca: the O 1s Compton wing, × water's (0: none)")
    ap.add_argument('--escape', type=float, default=1.0, help="mca: the Si escape peaks, × Reed's fraction (0: none)")
    ap.add_argument('--spectra', type=int, default=10, help='mca: spectra (one scan each) drawn from the truth')
    ap.add_argument('--seed', type=int, default=0, help='noise replicate')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    if a.kind == 'xrr':
        spec, info = xrr_dataset(a.out, a.truth, a.thickness, a.counts, a.monitor, a.fault, a.seed,
                                 a.roughness, a.background)
    elif a.kind == 'xfntr':
        spec, info = xfntr_dataset(a.out, a.seed)
    elif a.kind == 'mca':
        spec, info = mca_dataset(a.out, a.beam, a.element, a.photons, a.wing, a.escape, a.spectra, a.seed)
    else:
        spec, info = burn_dataset(a.out)
    with open(os.path.join(a.out, 'truth.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=1)
    for k, v in info.items():
        print('%s: %s' % (k, v))
    print('SPEC %s' % spec)
    return 0


if __name__ == '__main__':
    sys.exit(main())
