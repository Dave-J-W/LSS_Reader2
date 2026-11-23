"""Per-foil thicknesses from a joins table (hand-off 02 answer, joins.csv).

    python tests/tools/foil_fit_from_joins.py joins.csv

Uses the joins at 10 keV that remove absorber, are not excluded, and
across which Monc/Monp did not change (|ratio - 1| < 0.03: nothing
upstream of Monc changed, so the step is the foils alone), with
chi2/dof < 20. Fits

    -ln(step)/μ = Σ_k [b_k(n_a) - b_k(n_b)] t_k

for the six binary foils t_k (µm Al-equivalent, μ = μ/ρ·ρ of Al at 10 keV),
weighted by the Poisson error with 0.5 % added in quadrature, with
iterative 5 robust-sd clipping. Then gives every join's residual (µm) and
the implied change of the beam at the detector, F = exp(μ·res)·(Monc/Monp
ratio), which separates a foil effect from a monitor that did not follow a
slit change. Reads only.

The cuts are options (defaults as above), so that the sensitivity checks
of physics_notes (2026-11-19: Monc/Monp tolerance 1–3 %, χ² cut 5 / 20 /
none, error floor 0–1 %) are reruns:

    python tests/tools/foil_fit_from_joins.py joins.csv --monc-tol 0.01 --chi2-max 5 --floor 0
"""
import csv
import math
import sys

import numpy as np

MU_10KEV = 26.23 * 2.699 * 1e-4            # 1/µm, NIST SRD 126 Al at 10 keV
NOMINAL_UM = 50.0 * 2.0 ** np.arange(6)


def load(path):
    with open(path, newline='') as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r.get('excluded') or not r.get('step') or r.get('E_keV') in (None, ''):
            continue
        if abs(float(r['E_keV']) - 10.0) > 0.005 or int(r['n_a']) <= int(r['n_b']):
            continue
        out.append(r)
    return out


def signed_bits(r):
    a, b = int(r['n_a']), int(r['n_b'])
    return np.array([((a >> k) & 1) - ((b >> k) & 1) for k in range(6)], float)


def fit(rows, monc_tol=0.03, chi2_max=20.0, floor=0.005, clip=5.0):
    D = np.array([signed_bits(r) for r in rows])
    step = np.array([float(r['step']) for r in rows])
    y = -np.log(step) / MU_10KEV
    sig = np.hypot(np.array([float(r['step_err']) for r in rows]) / step, floor) / MU_10KEV
    mm = np.array([float(r['monc_monp_b_over_a'] or 'nan') for r in rows])
    chi = np.array([float(r['chi2_dof'] or 'nan') for r in rows])
    clean = (np.abs(mm - 1) < monc_tol) & (chi < chi2_max)
    keep = clean.copy()
    for _ in range(20):
        A, w = D[keep], sig[keep] ** -2
        t = np.linalg.solve(A.T @ (A * w[:, None]), A.T @ (w * y[keep]))
        res = y - D @ t
        sd = 1.4826 * np.median(np.abs(res[keep]))
        new = clean & (np.abs(res) < clip * max(sd, 0.5))
        if (new == keep).all():
            break
        keep = new
    A, w = D[keep], sig[keep] ** -2
    err = np.sqrt(np.diag(np.linalg.inv(A.T @ (A * w[:, None]))))
    return dict(t=t, err=err, res=res, clean=clean, kept=keep, robust_sd=sd,
                rank=int(np.linalg.matrix_rank(D[keep])),
                F=np.exp(MU_10KEV * res) * mm, monc_monp=mm)


def main(path, monc_tol=0.03, chi2_max=20.0, floor=0.005, clip=5.0):
    rows = load(path)
    f = fit(rows, monc_tol=monc_tol, chi2_max=chi2_max, floor=floor, clip=clip)
    print('%d joins at 10 keV removing absorber; %d with Monc/Monp unchanged; %d kept; rank %d; '
          'robust sd %.2f um' % (len(rows), f['clean'].sum(), f['kept'].sum(), f['rank'], f['robust_sd']))
    print('| foil | units | nominal µm | fitted µm | ± | excess | 1/T per unit |')
    print('|---|---|---|---|---|---|---|')
    for k in range(6):
        print('| %d | %d | %g | %.1f | %.1f | %+.1f %% | %.4f |' % (
            k, 2 ** k, NOMINAL_UM[k], f['t'][k], f['err'][k], 100 * (f['t'][k] / NOMINAL_UM[k] - 1),
            math.exp(MU_10KEV * f['t'][k] / 2 ** k)))
    changed = ~f['clean']
    print('Monc/Monp changed (or chi2/dof >= %g): %d joins, |res| > 5 um in %.0f %%; the others: %.0f %%'
          % (chi2_max, changed.sum(), 100 * np.mean(np.abs(f['res'][changed]) > 5),
             100 * np.mean(np.abs(f['res'][f['clean']]) > 5)))
    return f


def cli(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='Per-foil thicknesses from a joins table (hand-off 02 answer).')
    ap.add_argument('joins', help='joins.csv of the hand-off 02 answer (docs/handoff_out/03-answer/joins.csv)')
    ap.add_argument('--monc-tol', type=float, default=0.03,
                    help='keep joins with |Monc/Monp ratio - 1| below this (default %(default)s)')
    ap.add_argument('--chi2-max', type=float, default=20.0,
                    help='keep joins with chi2/dof below this; inf for no cut (default %(default)s)')
    ap.add_argument('--floor', type=float, default=0.005,
                    help='relative error added in quadrature to each step (default %(default)s)')
    ap.add_argument('--clip', type=float, default=5.0,
                    help='iterative clipping at this many robust SDs (default %(default)s)')
    a = ap.parse_args(argv)
    main(a.joins, monc_tol=a.monc_tol, chi2_max=a.chi2_max, floor=a.floor, clip=a.clip)
    return 0


if __name__ == '__main__':
    sys.exit(cli())
