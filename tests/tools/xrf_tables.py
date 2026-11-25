"""Tabulated X-ray data for the synthetic MCA spectra, taken from xraylib
(T. Schoonjans et al., Spectrochim. Acta B 66, 776 (2011);
github.com/tschoonj/xraylib), and a check of the generator's "from memory"
constants against it (XRF shootout, 2026-11-25).

    python tests/tools/xrf_tables.py [--out tests/synthetic/data/xrf_tables.json]
        [--check docs/studies/xrf_shootout]

Needs xraylib (conda-forge or pip). The JSON it writes is committed, so the
generator (``tests/synthetic/mca_more.py``) and the test suite do not need
xraylib. What the table holds:

- **Lines**: for each element and family (K, or L for heavy elements), each
  line's energy (``LineEnergy``) and its relative intensity at each beam
  energy, from ``CS_FluorLine_Kissel_Cascade`` (photo-ionisation by the beam,
  fluorescence yields, radiative rates, Coster–Kronig and cascade
  transitions), normalised to sum 1 over the family. A family is excited
  when the beam is above its lowest edge; lines under 0.3 % are dropped and
  the rest renormalised.
- **Compton profiles of water**: J(p_z) of O 1s, O 2s, O 2p and H 1s from
  the Hartree–Fock tables of F. Biggs, L. B. Mendelsohn and J. B. Mann, At.
  Data Nucl. Data Tables 16, 201 (1975), as xraylib tabulates them
  (``ComptonProfile_Partial``; ``ComptonProfile`` for H). Each is
  normalised to its number of electrons per molecule; bindings are
  xraylib's edges (O K 0.532 keV, O L1 0.024 keV; the 2p and H 1s are
  bound by less than 0.02 keV). These are free-atom profiles: the O–H
  bond is not in them.

``--check`` writes ``physics_check.csv``: every constant the generator and
``lss_core.fluorescence`` take from memory, beside xraylib's value.
"""
import argparse
import csv
import json
import math
import os
import sys

import numpy as np

try:
    import xraylib as xl
except ImportError:                                    # pragma: no cover - the tool needs it
    xl = None

K_LINES = (('Ka1', 'KL3_LINE'), ('Ka2', 'KL2_LINE'), ('Kb1', 'KM3_LINE'), ('Kb3', 'KM2_LINE'),
           ('Kb2', 'KN3_LINE'), ('Kb2b', 'KN2_LINE'))
L_LINES = (('La1', 'L3M5_LINE'), ('La2', 'L3M4_LINE'), ('Lb1', 'L2M4_LINE'), ('Lb2', 'L3N5_LINE'),
           ('Lb15', 'L3N4_LINE'), ('Lb3', 'L1M3_LINE'), ('Lb4', 'L1M2_LINE'), ('Lg1', 'L2N4_LINE'),
           ('Lg3', 'L1N3_LINE'), ('Lg2', 'L1N2_LINE'), ('Ll', 'L3M1_LINE'), ('Leta', 'L2M1_LINE'),
           ('Lb6', 'L3N1_LINE'), ('Lb5', 'L3O45_LINE'), ('Lg6', 'L2O4_LINE'))
ELEMENTS = {                     # symbol: (Z, families)
    'Ca': (20, ('K',)), 'Ti': (22, ('K',)), 'V': (23, ('K',)), 'Cr': (24, ('K',)), 'Mn': (25, ('K',)), 'Fe': (26, ('K',)), 'Co': (27, ('K',)), 'Ni': (28, ('K',)),
    'Cu': (29, ('K',)), 'Zn': (30, ('K',)), 'Ga': (31, ('K',)), 'As': (33, ('K',)), 'Se': (34, ('K',)),
    'Br': (35, ('K',)), 'Rb': (37, ('K',)), 'Sr': (38, ('K',)), 'Y': (39, ('K',)),
    'La': (57, ('L',)), 'Gd': (64, ('L',)), 'Er': (68, ('L',)), 'Lu': (71, ('L',)), 'Pb': (82, ('L',)),
}
BEAMS = (6.1, 8.5, 9.0, 9.2, 9.5, 9.8, 10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 13.5, 14.0, 15.0, 16.0, 16.2, 17.0, 18.0, 20.0)
MIN_LINE = 0.003
PZ = np.concatenate([np.linspace(0.0, 10.0, 201), np.linspace(10.25, 100.0, 360)])


def _family(z, fam, e0):
    lines = K_LINES if fam == 'K' else L_LINES
    edge = xl.EdgeEnergy(z, xl.K_SHELL) if fam == 'K' else xl.EdgeEnergy(z, xl.L3_SHELL)
    out = []
    for name, macro in lines:
        m = getattr(xl, macro)
        try:
            e = xl.LineEnergy(z, m)
            i = xl.CS_FluorLine_Kissel_Cascade(z, m, e0) if e0 > edge else 0.0
        except ValueError:
            continue
        if e > 0 and i > 0:
            out.append([name, e, i])
    tot = sum(i for _, _, i in out)
    out = [[n, e, i / tot] for n, e, i in out if tot and i / tot >= MIN_LINE]
    tot = sum(i for _, _, i in out)
    return edge, [[n, round(e, 5), round(i / tot, 6)] for n, e, i in out]


def lines_table():
    table = {}
    for sym, (z, fams) in ELEMENTS.items():
        for fam in fams:
            key = '%s %s' % (sym, fam)
            entry = {'Z': z, 'family': fam, 'beams': {}}
            for e0 in BEAMS:
                edge, ls = _family(z, fam, e0)
                entry['edge'] = round(edge, 5)
                if ls:
                    entry['beams']['%g' % e0] = ls
            # line energies whatever the beam (for fitters told where lines are)
            entry['energies'] = {n: round(xl.LineEnergy(z, getattr(xl, m)), 5) for n, m in
                                 (K_LINES if fam == 'K' else L_LINES) if _safe_energy(z, m) > 0}
            table[key] = entry
    return table


def _safe_energy(z, macro):
    try:
        return xl.LineEnergy(z, getattr(xl, macro))
    except ValueError:
        return 0.0


def water_compton():
    """J(p_z) per shell of one water molecule, each normalised to its electrons."""
    shells = (('O 1s', 8, xl.K_SHELL, 2, xl.EdgeEnergy(8, xl.K_SHELL)),
              ('O 2s', 8, xl.L1_SHELL, 2, xl.EdgeEnergy(8, xl.L1_SHELL)),
              ('O 2p', 8, (xl.L2_SHELL, xl.L3_SHELL), 4, 0.0136),
              ('H 1s', 1, None, 2, 0.0136))
    out = []
    for name, z, shell, n, b in shells:
        if shell is None:
            j = np.array([xl.ComptonProfile(z, float(p)) for p in PZ])
        elif isinstance(shell, tuple):
            j = sum(np.array([xl.ComptonProfile_Partial(z, s, float(p)) for p in PZ]) for s in shell)
        else:
            j = np.array([xl.ComptonProfile_Partial(z, shell, float(p)) for p in PZ])
        norm = 2.0 * np.trapezoid(j, PZ)                # J is even in p_z
        j = j * n / norm
        out.append({'shell': name, 'electrons': n, 'binding_kev': round(float(b), 5), 'J': [float('%.6g' % v) for v in j]})
    return {'pz': [float(p) for p in PZ], 'shells': out,
            'source': 'xraylib %s ComptonProfile(_Partial): Biggs, Mendelsohn and Mann 1975' % xl.__version__}


def check_rows():
    """The generator's remembered constants against xraylib."""
    sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
    from synthetic import mca
    rows = []

    def add(what, used, tab, where, note=''):
        rel = (used / tab - 1) if tab else math.nan
        rows.append(dict(quantity=what, used=used, xraylib=tab, rel_diff=rel, where=where, note=note))
    add('omega_K(Si)', 0.050, xl.FluorYield(14, xl.K_SHELL), 'mca.reed_escape, fluorescence.si_escape_fraction')
    add('1 - 1/r, Si K jump', 0.90, 1 - 1 / xl.JumpFactor(14, xl.K_SHELL), 'same')
    add('mu(Si Ka in Si) cm2/g', 350.0, xl.CS_Total(14, xl.LineEnergy(14, xl.KL3_LINE)), 'same')
    for e in (8.0, 8.6, 10.0, 12.0):
        add('mu_Si(%g keV) cm2/g' % e, 33.9 * (10.0 / e) ** 2.75, xl.CS_Total(14, e), 'power law 33.9(10/E)^2.75')
    for e in (8.6, 10.0, 12.0):
        mu_e, mu_k = xl.CS_Total(14, e), xl.CS_Total(14, 1.74)
        a = mu_k / mu_e
        tab = 0.5 * xl.FluorYield(14, xl.K_SHELL) * (1 - 1 / xl.JumpFactor(14, xl.K_SHELL)) * (1 - a * math.log1p(1 / a))
        add('Si escape fraction at %g keV' % e, mca.reed_escape(e), tab, 'Reed formula, remembered vs xraylib constants')
    add('Si Ka keV', mca.SI_KA_KEV, xl.LineEnergy(14, xl.KL3_LINE), 'mca.SI_KA_KEV')
    add('Si K edge keV', mca.SI_K_EDGE_KEV, xl.EdgeEnergy(14, xl.K_SHELL), 'mca.SI_K_EDGE_KEV')
    add('O K edge (1s binding) keV', 0.543, xl.EdgeEnergy(8, xl.K_SHELL), 'mca.WATER_SHELLS (0.543); hydrogenic core 0.532')
    zmap = {'Fe': 26, 'Ni': 28, 'Cu': 29, 'Zn': 30, 'Ga': 31, 'Br': 35}
    for el, (edge, ls) in mca.ELEMENTS.items():
        z = zmap[el]
        add('%s K edge keV' % el, edge, xl.EdgeEnergy(z, xl.K_SHELL), 'mca.ELEMENTS')
        for name, e, _ in ls:
            m = {'Ka1': xl.KL3_LINE, 'Ka2': xl.KL2_LINE, 'Kb1': xl.KM3_LINE}[name]
            add('%s %s keV' % (el, name), e, xl.LineEnergy(z, m), 'mca.ELEMENTS')
        i = {n: v for n, _, v in ls}
        ka = xl.RadRate(z, xl.KL3_LINE) + xl.RadRate(z, xl.KL2_LINE)
        kb = sum(xl.RadRate(z, getattr(xl, m)) for m in ('KM3_LINE', 'KM2_LINE', 'KN3_LINE', 'KN2_LINE')
                 if _safe_rate(z, m) > 0)
        add('%s Kb/Ka' % el, i['Kb1'] / (i['Ka1'] + i['Ka2']), kb / ka, 'mca.ELEMENTS 100:51:17',
            'xraylib sums Kb1, Kb3, Kb2')
        add('%s Ka2/Ka1' % el, i['Ka2'] / i['Ka1'], xl.RadRate(z, xl.KL2_LINE) / xl.RadRate(z, xl.KL3_LINE), 'mca.ELEMENTS')
    return rows


def _safe_rate(z, macro):
    try:
        return xl.RadRate(z, getattr(xl, macro))
    except ValueError:
        return 0.0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=os.path.join('tests', 'synthetic', 'data', 'xrf_tables.json'))
    ap.add_argument('--check', default=None, help='folder for physics_check.csv')
    a = ap.parse_args(argv)
    if xl is None:
        sys.exit('xraylib is needed: conda install -c conda-forge xraylib')
    data = {'xraylib': xl.__version__, 'beams_kev': list(BEAMS), 'lines': lines_table(), 'water_compton': water_compton()}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=0)
    print('wrote', a.out)
    if a.check:
        os.makedirs(a.check, exist_ok=True)
        rows = check_rows()
        p = os.path.join(a.check, 'physics_check.csv')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            for r in rows:
                w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})
        print('wrote', p)


if __name__ == '__main__':
    main()
