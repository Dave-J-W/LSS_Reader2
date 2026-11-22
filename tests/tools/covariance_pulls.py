"""Downstream fits with and without the stitching covariance (owner,
2026-11-22: "think about what is needed on covariance downstream for model
fitting"). Synthetic NX-like scans of a 25 Å film on water
(tests/synthetic), reduced by each patch method, written as the xmodfit
sidecar (lss_core.covariance_export) and fitted (lss_core.gls) for the
film's thickness, density and roughness with a free overall scale, under
four error treatments:

    file      the data file's own error column (legacy: factor error folded
              per point; corrected/joint: √diag C)
    total     √diag C (the hand-off's corrected column)
    counting  σ_meas alone (the factors' error ignored)
    cov       the full covariance (the sidecar)

    python tests/tools/covariance_pulls.py [--seeds 300] [--plan nx_like_plan] [--nx]
        [--out docs/comparisons_data/downstream_covariance]

Writes ``pulls.csv`` (per method × treatment: pull SD and mean of each
parameter, mean χ²/dof, RMS error) and, with ``--nx``, ``nx_sigma.csv``
(√Σ of each scan of the public NX school scans 6–9 per method). Run from
the repository root; about 10 s per 300 seeds and method.
"""
import argparse
import csv
import os
import sys
import time
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import numpy as np  # noqa: E402

from lss_core import covariance_export as ce, gls  # noqa: E402
from synthetic import xrr, xrr_scans as xs  # noqa: E402

TRUTH = np.array([25.0, 0.39, 3.5])
NAMES = ['d', 'rho', 'sigma']
QC = 0.0217


def run(plan_name, seeds, methods=('legacy', 'corrected', 'joint')):
    wl = xs.Beamline().wavelength

    def model(q, d, rho, sig):
        return xrr.film(d, rho, sig).reflectivity(q, wl)
    rows = []
    for method in methods:
        t0 = time.time()
        acc = {k: [] for k in ('file', 'total', 'counting', 'cov')}
        for seed in range(seeds):
            r = xs.measure(xrr.film(*TRUTH), getattr(xs, plan_name)(), seed=seed, errors='counting+monitor')
            if method == 'legacy':
                cd = ce.legacy_chain(r.per_scan, r.order).covdata('legacy')
            elif method == 'corrected':
                cd = ce.corrected_chain(r.per_scan, r.order).covdata('total')
            else:
                cd = ce.joint_covdata(r.per_scan, r.order)
            ref, _ = ce.finish(cd, QC, 0.0, None, False)
            sc = gls.load(ce.sidecar_dict(ref))
            p0 = TRUTH * [1.02, 0.99, 1.03]
            for k, kw in (('file', dict(mode='diagonal', yerr=ref.error_column())),
                          ('total', dict(mode='diagonal', yerr=ref.sigma_total())),
                          ('counting', dict(mode='diagonal', yerr=ref.sigma_meas)),
                          ('cov', dict())):
                f = gls.fit(sc, model, p0, **kw)
                acc[k].append(np.concatenate([(f.params - TRUTH) / f.errors, f.params - TRUTH, [f.chi2 / f.dof]]))
        for k, v in acc.items():
            v = np.array(v)
            row = dict(plan=plan_name, method=method, errors=k, seeds=seeds, points=ref.n)
            for i, n in enumerate(NAMES):
                row['pull_sd_' + n] = round(float(v[:, i].std(ddof=1)), 3)
                row['pull_mean_' + n] = round(float(v[:, i].mean()), 3)
                row['rms_' + n] = float('%.4g' % np.sqrt(np.mean(v[:, 3 + i] ** 2)))
            row['chi2_dof'] = round(float(v[:, 6].mean()), 3)
            rows.append(row)
        print('%s: %.1f s' % (method, time.time() - t0), file=sys.stderr)
    return rows


def nx_sigma():
    from lss_core.experiment import Experiment
    spec = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
    res = Experiment(spec).reflectivity([6, 7, 8, 9], errors='budget')
    rows = []
    for method in ('legacy', 'corrected', 'joint'):
        ref, _ = res.covariance(method)
        tot = ref.sigma_total() / ref.y
        for lab, s in zip(ref.labels, np.sqrt(np.diag(ref.Sigma))):
            rows.append(dict(method=method, scan=lab, sqrt_sigma=float('%.4g' % s), points=ref.n,
                             max_total_over_meas=float('%.4g' % np.max(ref.sigma_total() / ref.sigma_meas)),
                             median_rel_total=float('%.4g' % np.median(tot))))
    return rows


def write(path, rows):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--seeds', type=int, default=300)
    ap.add_argument('--plan', default='nx_like_plan')
    ap.add_argument('--nx', action='store_true')
    ap.add_argument('--out', default=os.path.join(ROOT, 'docs', 'comparisons_data', 'downstream_covariance'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    warnings.simplefilter('ignore')
    rows = run(a.plan, a.seeds)
    write(os.path.join(a.out, 'pulls_%s.csv' % a.plan), rows)
    for r in rows:
        print('%-9s %-8s pull SD %5.2f %5.2f %5.2f  chi2/dof %.2f  rms %.3g %.3g %.3g' % (
            r['method'], r['errors'], r['pull_sd_d'], r['pull_sd_rho'], r['pull_sd_sigma'], r['chi2_dof'],
            r['rms_d'], r['rms_rho'], r['rms_sigma']))
    if a.nx:
        rows = nx_sigma()
        write(os.path.join(a.out, 'nx_sigma.csv'), rows)
        for r in rows:
            print(r)


if __name__ == '__main__':
    main()
