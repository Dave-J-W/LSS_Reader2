"""Absorber steps from overlapping reflectivity scans, SPEC columns only.

Hand-off 02 (docs/handoff_out/02-absorber-patch-check.md). Self-contained:
Python 3 and numpy, nothing else. Reads SPEC files; writes nothing.

    python 02-absorber_steps.py SPEC [--roi proi] [--mon Monc]
                                [--series 6,7,8,9 [--series ...]]
                                [--prior-um 10] [--csv steps.csv]

Without --series, reflectivity series are found automatically:
consecutive hklscans at fixed H, K (scanning L) whose L ranges overlap,
at the same wavelength.

For each consecutive pair (a, b) of a series, at the L values measured in
both scans (|ΔL| < 1e-5, no interpolation):

    r = ROI / (Monc · S)          S the Monc gain from '#M Monc Gain S unit'
    step = weighted mean of r_a / r_b, Poisson errors of ROI only
    nominal = absfac(E) ** -(n_a - n_b),  absfac = exp(μ/ρ · ρ · 50 µm)
    extra Al = -ln(step / nominal) / (μ/ρ · ρ)

Then, per series group (one file = one day by default), a fit of the
optical depth of each of the six binary foils (n = Σ b_k 2^k):

    -ln(step) = Σ_k [b_k(n_a) - b_k(n_b)] · d_k,  d_k = 2^k d_unit + δ_k

with a Gaussian prior δ_k ~ N(0, (μ/ρ·ρ·prior_um)²). A foil whose
posterior error is close to the prior is not determined by the data.
"""
import argparse
import math
import re
import sys

import numpy as np

HC = 12.39842                      # keV·Å
UNIT_UM = 50.0                     # µm Al per absorber unit (owner)
AL_RHO = 2.699                     # g/cm³ (NIST SRD 126 Table 1)
# NIST SRD 126, Al (Z = 13), E (keV), μ/ρ (cm²/g); doi:10.18434/T4D01F
AL_MU_RHO = ((2.0, 2263.0), (3.0, 788.0), (4.0, 360.5), (5.0, 193.4), (6.0, 115.3),
             (8.0, 50.33), (10.0, 26.23), (15.0, 7.955), (20.0, 3.441), (30.0, 1.128),
             (40.0, 0.5685), (50.0, 0.3681), (60.0, 0.2778), (80.0, 0.2018), (100.0, 0.1704))
GAIN_UNITS = {'pA/V': 1e-12, 'nA/V': 1e-9, 'uA/V': 1e-6, 'µA/V': 1e-6, 'mA/V': 1e-3}


def mu_per_um(e_kev):
    """μ/ρ·ρ of Al in 1/µm, log–log interpolation of the NIST rows."""
    e = round(e_kev, 2)                       # 10 eV, as the reader does
    for (e0, m0), (e1, m1) in zip(AL_MU_RHO, AL_MU_RHO[1:]):
        if e0 <= e <= e1:
            w = math.log(e / e0) / math.log(e1 / e0)
            return math.exp(math.log(m0) + w * math.log(m1 / m0)) * AL_RHO * 1e-4
    raise ValueError('%g keV outside the Al table' % e)


def read_spec(path):
    scans, cur = {}, None
    for line in open(path, errors='replace'):
        if line.startswith('#S '):
            f = line.split()
            cur = {'num': int(f[1]), 'cmd': f[2:], 'rows': [], 'A': None, 'W': None,
                   'gain': None, 'L': None}
            scans.setdefault(cur['num'], []).append(cur)   # numbers can repeat
        elif cur is None:
            continue
        elif line.startswith('#A '):
            m = re.match(r'#A\s+\S+\s+(-?\d+)\s*$', line)
            cur['A'] = int(m.group(1)) if m else None      # unreadable: unknown, not 63
        elif line.startswith('#W '):
            cur['W'] = float(line.split()[-1])
        elif line.startswith('#M '):
            m = re.match(r'#M\s+(\S+)\s+Gain\s+([-+.\deE]+)\s*(\S+)', line)
            if m and m.group(3) in GAIN_UNITS:
                cur['gain'] = (m.group(1), float(m.group(2)) * GAIN_UNITS[m.group(3)])
        elif line.startswith('#L '):
            cur['L'] = line[3:].split()
        elif line.strip() and not line.startswith('#') and cur['L']:
            try:
                row = [float(v) for v in line.split()]
            except ValueError:
                continue
            if len(row) == len(cur['L']):
                cur['rows'].append(row)
    out = []
    for lst in scans.values():
        out.extend(lst)
    return sorted(out, key=lambda s: s['num'])


def is_l_scan(s):
    return (len(s['cmd']) >= 7 and s['cmd'][0] == 'hklscan' and s['L'] and 'L' in s['L']
            and len(s['rows']) >= 2 and s['cmd'][1] == s['cmd'][2] and s['cmd'][3] == s['cmd'][4])


def find_series(scans):
    series, cur = [], []
    for s in scans:
        if not is_l_scan(s):
            if len(cur) > 1:
                series.append(cur)
            cur = []
            continue
        if cur:
            p = cur[-1]
            lp = [r[p['L'].index('L')] for r in p['rows']]
            ls = [r[s['L'].index('L')] for r in s['rows']]
            if not (min(ls) <= max(lp) + 1e-5 and s['W'] == p['W']):
                if len(cur) > 1:
                    series.append(cur)
                cur = []
        cur.append(s)
    if len(cur) > 1:
        series.append(cur)
    return series


def step(a, b, roi, mon):
    """Weighted mean of r_a/r_b at shared L; None if nothing shared."""
    def cols(s):
        d = np.array(s['rows'])
        i = s['L'].index
        g = s['gain'][1] if s['gain'] and s['gain'][0] == mon else 1.0
        return d[:, i('L')], d[:, i(roi)], d[:, i(mon)] * g
    la, ca, ma = cols(a)
    lb, cb, mb = cols(b)
    r, e, ls = [], [], []
    for i in range(len(la)):
        j = np.flatnonzero(np.abs(lb - la[i]) < 1e-5)
        if len(j) == 0 or ca[i] <= 0 or cb[j[0]] <= 0 or ma[i] <= 0 or mb[j[0]] <= 0:
            continue
        j = j[0]
        x = (ca[i] / ma[i]) / (cb[j] / mb[j])
        r.append(x)
        e.append(x * math.hypot(ca[i] ** -0.5, cb[j] ** -0.5))
        ls.append(la[i])
    if not r:
        return None
    r, e = np.array(r), np.array(e)
    w = 1 / e ** 2
    mean = float(np.sum(w * r) / np.sum(w))
    return dict(mean=mean, err=float(np.sum(w) ** -0.5), npts=len(r), L=ls,
                chi2=float(np.sum(w * (r - mean) ** 2) / max(len(r) - 1, 1)),
                max_roi=float(max(ca.max(), cb.max())))


def bits(n):
    return np.array([(n >> k) & 1 for k in range(6)], float)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('spec')
    ap.add_argument('--roi', default='proi')
    ap.add_argument('--mon', default='Monc')
    ap.add_argument('--series', action='append', default=[])
    ap.add_argument('--prior-um', type=float, default=10.0)
    ap.add_argument('--csv')
    o = ap.parse_args(argv)
    scans = read_spec(o.spec)
    by_num = {}
    for s in scans:
        by_num.setdefault(s['num'], s)       # first of repeated numbers
    series = ([[by_num[int(x)] for x in t.split(',')] for t in o.series]
              or find_series(scans))
    rows, eqs = [], []
    print('| Scans | n (bits b5..b0) | E keV | shared L | points | step | nominal | step/nominal | χ²/dof | extra Al µm on nominal µm | max ROI counts |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for ser in series:
        for a, b in zip(ser, ser[1:]):
            why = None
            if a['A'] is None or b['A'] is None:
                why = '#A not readable'
            elif o.roi not in (a['L'] or []) or o.roi not in (b['L'] or []):
                why = 'no column %s' % o.roi
            elif a['W'] != b['W'] or a['W'] is None:
                why = 'wavelength differs or missing'
            elif (a['gain'] is None) != (b['gain'] is None):
                why = 'gain known in one scan only'
            st = None if why else step(a, b, o.roi, o.mon)
            if st is None:
                print('| S%d→S%d | skipped: %s |' % (a['num'], b['num'], why or 'no shared L'))
                continue
            e = HC / a['W']
            mu = mu_per_um(e)
            dn = a['A'] - b['A']
            nominal = math.exp(-mu * UNIT_UM * dn)
            extra = -math.log(st['mean'] / nominal) / mu
            print('| S%d→S%d | %d (%s) → %d (%s) | %.2f | %s | %d | %.5f ± %.5f | %.5f | %.3f ± %.3f | %.2f | %+.1f on %g | %.3g |' % (
                a['num'], b['num'], a['A'], format(a['A'], '06b'), b['A'], format(b['A'], '06b'), e,
                ', '.join('%g' % x for x in st['L']), st['npts'], st['mean'], st['err'], nominal,
                st['mean'] / nominal, st['err'] / nominal, st['chi2'], extra, dn * UNIT_UM, st['max_roi']))
            rows.append((a['num'], b['num'], a['A'], b['A'], e, st['npts'], st['mean'], st['err'],
                         nominal, st['chi2'], extra, st['max_roi']))
            eqs.append((bits(a['A']) - bits(b['A']), -math.log(st['mean']), st['err'] / st['mean'], mu, round(e, 2)))
    if o.csv:
        with open(o.csv, 'w') as f:
            f.write('scan_a,scan_b,n_a,n_b,E_keV,points,step,step_err,nominal,chi2_dof,extra_um,max_roi\n')
            for r in rows:
                f.write(','.join(str(v) for v in r) + '\n')
    if not eqs:
        return dict(rows=rows)
    # per-foil fit; one energy assumed (eqs at another energy are left out)
    mu, energy = eqs[0][3], eqs[0][4]
    eqs = [q for q in eqs if q[4] == energy]
    D = np.array([q[0] for q in eqs])
    y = np.array([q[1] for q in eqs]) - D @ (mu * UNIT_UM * 2.0 ** np.arange(6))
    W = np.diag([q[2] ** -2 for q in eqs])
    prior = (mu * o.prior_um) ** -2
    cov = np.linalg.inv(D.T @ W @ D + prior * np.eye(6))
    delta = cov @ D.T @ W @ y
    w = np.diag(W)
    chi2_nominal = float(np.sum(w * y ** 2))
    chi2_fit = float(np.sum(w * (y - D @ delta) ** 2))
    chi2_prior = float(np.sum(delta ** 2) * prior)
    # one common fraction f for every foil: d_k = 2^k d_unit (1 + f)
    # (alloy, density, μ/ρ, or a tolerance relative to thickness)
    x = D @ (mu * UNIT_UM * 2.0 ** np.arange(6))
    f = float(np.sum(w * x * y) / np.sum(w * x * x))
    f_err = float(np.sum(w * x * x) ** -0.5)
    chi2_f = float(np.sum(w * (y - f * x) ** 2))
    print('\nAt %.2f keV, %d steps (rank %d of 6):' % (energy, len(eqs), np.linalg.matrix_rank(D)))
    print('- nominal foils (δ = 0): χ² = %.1f for %d steps' % (chi2_nominal, len(eqs)))
    print('- every foil off by the same fraction: f = %+.4f ± %.4f, χ² = %.1f for %d dof'
          % (f, f_err, chi2_f, len(eqs) - 1))
    print('- six foils, prior ±%g µm each: data χ² = %.1f, prior χ² = %.1f (6 terms; '
          '≫ 6 means the steps need foils outside ±%g µm)'
          % (o.prior_um, chi2_fit, chi2_prior, o.prior_um))
    print('\n| foil k | units 2^k | extra Al µm | ± | determined by the data? |')
    print('|---|---|---|---|---|')
    for k in range(6):
        s = math.sqrt(cov[k, k]) / mu
        print('| %d | %d | %+.1f | %.1f | %s |' % (k, 2 ** k, delta[k] / mu, s,
                                                  'yes' if s < 0.5 * o.prior_um else 'no (prior)'))
    return dict(rows=rows, f=f, f_err=f_err, chi2_f=chi2_f, chi2_nominal=chi2_nominal,
                chi2_fit=chi2_fit, chi2_prior=chi2_prior, delta_um=(delta / mu).tolist())


if __name__ == '__main__':
    main()
