"""Measured absorber steps between overlapping reflectivity scans.

    python tests/tools/absorber_steps.py SPEC scan,scan,...

Reduces the scans as Ref Patch does (lss_core Experiment.reflectivity, its
defaults), then for each pair of consecutive scans takes the points
measured at the same Q_z in both (no interpolation) and gives the
weighted mean ratio R(scan with more absorbers)/R(the other), its counting
error and χ²/dof, against the nominal absfac(E)**-Δn, and the extra Al
thickness the measured step implies, Δt = -ln(measured/nominal)/(μ/ρ·ρ).
The setting n is a sum of binary-weighted foils (bits of #A). Reads only.
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from lss_core import absorbers as A               # noqa: E402
from lss_core.experiment import Experiment       # noqa: E402


def steps(spec, scans):
    exp = Experiment(spec)
    r = exp.reflectivity(scans)
    par = {s: exp.scans[s].parameters for s in r.order}
    out = []
    for a, b in zip(r.order, r.order[1:]):
        d1, d2 = r.per_scan[a], r.per_scan[b]
        n1, n2 = int(par[a]['Absorber']), int(par[b]['Absorber'])
        e = A.energy_kev(par[a]['Wavelength'])
        pairs = [(i, j) for i in range(len(d1)) for j in range(len(d2))
                 if abs(d1[i, 0] - d2[j, 0]) < 1e-5]
        ratio = np.array([d1[i, 1] / d2[j, 1] for i, j in pairs])
        err = ratio * np.array([np.hypot(d1[i, 2] / d1[i, 1], d2[j, 2] / d2[j, 1]) for i, j in pairs])
        w = 1 / err ** 2
        mean = np.sum(w * ratio) / np.sum(w)
        nominal = A.factor_at(e)[0] ** -(n1 - n2)
        mu = A.al_mu_rho(round(e, 2)) * A.AL_DENSITY * 1e-4       # per µm
        out.append(dict(scans=(a, b), n=(n1, n2), bits=(format(n1, '06b'), format(n2, '06b')),
                        energy=e, qz=[float(d1[i, 0]) for i, _ in pairs],
                        measured=mean, error=np.sum(w) ** -0.5,
                        chi2=np.sum(w * (ratio - mean) ** 2) / max(len(ratio) - 1, 1),
                        nominal=nominal, extra_um=-np.log(mean / nominal) / mu,
                        nominal_um=(n1 - n2) * A.UNIT_THICKNESS_UM))
    return out


if __name__ == '__main__':
    print('| Scans | n (bits) | E keV | Q_z | measured | nominal | measured/nominal | χ²/dof | extra Al (µm) on Δt nominal |')
    print('|---|---|---|---|---|---|---|---|---|')
    for s in steps(sys.argv[1], [int(x) for x in sys.argv[2].split(',')]):
        print('| S%d→S%d | %d (%s) → %d (%s) | %.2f | %s | %.5f ± %.5f | %.5f | %.3f ± %.3f | %.2f | %+.1f on %g |' % (
            s['scans'] + (s['n'][0], s['bits'][0], s['n'][1], s['bits'][1], s['energy'],
                          ', '.join('%g' % q for q in s['qz']), s['measured'], s['error'], s['nominal'],
                          s['measured'] / s['nominal'], s['error'] / s['nominal'], s['chi2'],
                          s['extra_um'], s['nominal_um'])))
