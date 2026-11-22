"""The reflectivity patching gauntlet on synthetic scans with known truth
(owner, 2026-11-22: "make new method the default if it passes the
gauntlet"). The judging rules are hand-off 08's (docs/handoff_out/
08-ref-patch-comparison.md, "How to judge"): at every join, per Qz class,
|mean pull| < 0.2 and pull SD within 0.9–1.15, where pull = (δ̂ − δ_true)/σ̂
and δ = ln(factor on scan b). The survey (ref_patch_survey.py) does this on
real curves split in two; this tool does it on many noise replicates of
synthetic reflectivity (tests/synthetic: Parratt, Névot–Croce, water's
critical edge, Kiessig fringes; docs/SYNTHETIC_DATA.md).

    python tests/tools/ref_patch_gauntlet.py --out DIR [--replicates 200] [--scenarios a,b]

Outputs: ``pulls.csv`` (scenario × replicate × join × method), ``verdict.csv``
(scenario × join × method: n, Qz class, mean pull, pull SD, RMSE of δ,
median σ̂, pass), ``levels.csv`` (the last scan's level φ_K against the
first, per method, chained with the carried covariance), ``summary.md``.
Synthetic data only: public.
"""
import argparse
import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from lss_core import patching, reflectivity as refl, stitching          # noqa: E402
from lss_core import uncertainty as unc                                 # noqa: E402
from synthetic import xrr, xrr_scans as xs                              # noqa: E402

METHODS = {
    'legacy': dict(kind='legacy'),
    'interp': dict(kind='interp'),
    'joint_o2_e0': dict(kind='joint', order=2, n_ext=0),
    'joint_o3_e4': dict(kind='joint', order=3, n_ext=4),
    'joint_o4_e2': dict(kind='joint', order=4, n_ext=2),          # the default since 2026-11-22
    'joint_o4_e4': dict(kind='joint', order=4, n_ext=4),
    'joint_o4_e4_log': dict(kind='joint', order=4, n_ext=4, likelihood='log'),
    'joint_o4_e1': dict(kind='joint', order=4, n_ext=1),
    'joint_o4_e4_g01': dict(kind='joint', order=4, n_ext=4, guard_p=0.01),   # the guard before 2026-11-22
    'joint_o4_e2_g01': dict(kind='joint', order=4, n_ext=2, guard_p=0.01),
    'coincident': dict(kind='coincident'),
    'hybrid_e2': dict(kind='hybrid', order=4, n_ext=2),
    'hybrid_e4': dict(kind='hybrid', order=4, n_ext=4),
}
PRIOR = 'joint_o4_e2_prior'     # the default fit with the foil prior (patching.chain)
PULL_BIAS_MAX = 0.2
PULL_SD = (0.9, 1.15)

# the critical edge of water at 10 keV is 0.0218 Å⁻¹; this first overlap
# (staggered, so no Qz coincides) straddles it (SYNTHETIC_DATA.md: the
# legacy factor is 16.7 % low there). Information only, outside the verdict:
# the owner (2026-11-22): "we dont need to patch across critical edge.
# There's really no reason to patch early in Qz (change absorbers) until
# counting statistics drop off by more than 100x, since we start from a
# place of 'plenty', with 1e6 counts per second in the ROI at total
# reflection". The other plans change absorbers at 0.04 Å⁻¹ (R about 1/200
# of the plateau).
EDGE_RANGES = [(0.01, 0.0235, 0.001), (0.0205, 0.08, 0.0025), (0.07, 0.25, 0.005), (0.22, 0.5, 0.01)]
NOT_JUDGED = {'edge_staggered'}

# the monitor (owner, 2026-11-22): no Poisson noise, a strict 0.05 % (xs.REAL_MONITOR)
MONITORS = {'real': xs.REAL_MONITOR, 'poisson': dict(monitor_poisson=True, monitor_jitter=0.0)}


def scenarios(monitor='real'):
    m = MONITORS[monitor]
    bl, lo = xs.Beamline(**m), xs.Beamline(flux=2.5e11, **m)
    return {
        'water_coincide': (xrr.bare_water(), lambda: xs.standard_plan(4, grid='coincide'), bl),
        'water_staggered': (xrr.bare_water(), lambda: xs.standard_plan(4, grid='staggered'), bl),
        'dppc_nx': (xrr.dppc(), xs.nx_like_plan, bl),
        'film100_nx': (xrr.film(100.0), xs.nx_like_plan, bl),
        'film250_staggered': (xrr.film(250.0), lambda: xs.standard_plan(4, grid='staggered'), bl),
        'edge_staggered': (xrr.bare_water(), lambda: xs.chain_plan(EDGE_RANGES, overlap=4, grid='staggered'), bl),
        'film100_lowcounts': (xrr.film(100.0), lambda: xs.standard_plan(4, grid='coincide'), lo),
    }


def q_class(q):
    return '<0.05' if q < 0.05 else ('0.05-0.25' if q < 0.25 else '>=0.25')


def fit_join(a, b, spec):
    kind = spec['kind']
    kw = {k: v for k, v in spec.items() if k != 'kind'}
    if kind == 'legacy':
        f, e = stitching.fitted_factor(np.column_stack([a.q, a.y, a.sigma]), np.column_stack([b.q, b.y, b.sigma]))
        return math.log(f), e / f
    if kind == 'interp':
        j = patching.interp_factor(a, b, **kw)
    elif kind == 'coincident':
        j = patching.coincident_factor(a, b)
        if j is None:
            raise ValueError('no coinciding points')
    elif kind == 'hybrid':        # the coinciding points where there are 3 or more, else the joint fit
        j = patching.coincident_factor(a, b)
        if j is None or len(j.ia) < 3:
            j = patching.joint_factor(a, b, **kw)
    else:
        j = patching.joint_factor(a, b, **kw)
    return j.delta, j.err


def replicate(profile, plan, beamline, seed, errors='counting+monitor'):
    r = xs.measure(profile, plan(), beamline=beamline, seed=seed, errors=errors)
    sc = [patching.Scan(r.per_scan[k][:, 0], r.per_scan[k][:, 1], r.per_scan[k][:, 2], label=str(k),
                        absorber=r.scans[k].absorber) for k in r.order]
    truth = [math.log(v) for v in r.true_steps().values()]
    mr = []
    for a, b in zip(r.order, r.order[1:]):
        A, B = r.scans[a], r.scans[b]
        mr.append(refl.monitor_change(A.qz, A.monc, A.monp, B.qz, B.monc, B.monp))
    return r, sc, truth, mr


def run(names, n_rep, out, errors='counting+monitor', monitor='real'):
    pulls, levels = [], []
    for name in names:
        profile, plan, bl = scenarios(monitor)[name]
        t0 = time.time()
        for rep in range(n_rep):
            r, sc, truth, mr = replicate(profile, plan, bl, seed=1000 * (rep + 1), errors=errors)
            phi_true = float(np.sum(truth))
            for mname, spec in METHODS.items():
                d, e = [], []
                for m in range(1, len(sc)):
                    try:
                        dm, em = fit_join(sc[m - 1], sc[m], spec)
                    except Exception as exc:          # recorded; counted as a failure in the verdict
                        pulls.append(dict(scenario=name, rep=rep, join=m, method=mname, error=type(exc).__name__))
                        dm, em = math.nan, math.nan
                    else:
                        pulls.append(dict(scenario=name, rep=rep, join=m, method=mname,
                                          q_class=q_class(float(sc[m].q.min())), delta=dm, err=em,
                                          truth=truth[m - 1], pull=(dm - truth[m - 1]) / em))
                    d.append(dm)
                    e.append(em)
                if all(np.isfinite(d)):
                    phi, S = unc.steps_to_phi(d, np.diag(np.square(e)))
                    levels.append(dict(scenario=name, rep=rep, method=mname, phi_last=float(phi[-1]),
                                       err=float(math.sqrt(S[-1, -1])), truth=phi_true,
                                       pull=(float(phi[-1]) - phi_true) / math.sqrt(S[-1, -1])))
            # the foil prior, used where the monitor shows it applies
            try:
                foils = r.beamline.foils()
                prior = patching.known_steps(foils, [s.absorber for s in sc], [s.q.min() for s in sc[1:]])
                res = patching.chain(sc, prior=prior, monitor_ratios=mr)
                for m, j in enumerate(res.joins, start=1):
                    err = float(math.sqrt(res.C_steps[m - 1, m - 1]))
                    pulls.append(dict(scenario=name, rep=rep, join=m, method=PRIOR,
                                      q_class=q_class(float(sc[m].q.min())), delta=float(res.steps[m - 1]),
                                      err=err, truth=truth[m - 1], pull=(float(res.steps[m - 1]) - truth[m - 1]) / err,
                                      prior_used=j.prior_used))
                levels.append(dict(scenario=name, rep=rep, method=PRIOR, phi_last=float(res.phi[-1]),
                                   err=float(math.sqrt(res.Sigma[-1, -1])), truth=phi_true,
                                   pull=(float(res.phi[-1]) - phi_true) / math.sqrt(res.Sigma[-1, -1])))
            except Exception as exc:
                pulls.append(dict(scenario=name, rep=rep, join=0, method=PRIOR, error='%s: %s' % (type(exc).__name__, exc)))
        print('%s: %d replicates, %.0f s' % (name, n_rep, time.time() - t0), flush=True)
    return pulls, levels


def verdict(pulls):
    rows = []
    keys = sorted({(p['scenario'], p['join'], p['method']) for p in pulls if p['join']})
    for sc, j, m in keys:
        ps = [p for p in pulls if (p['scenario'], p['join'], p['method']) == (sc, j, m)]
        ok = [p for p in ps if 'pull' in p and np.isfinite(p['pull'])]
        n_fail = len(ps) - len(ok)
        if not ok:
            rows.append(dict(scenario=sc, join=j, method=m, n=0, failures=n_fail, passed=False))
            continue
        pu = np.array([p['pull'] for p in ok])
        dd = np.array([p['delta'] - p['truth'] for p in ok])
        bias, sd = float(np.mean(pu)), float(np.std(pu, ddof=1))
        passed = abs(bias) < PULL_BIAS_MAX and PULL_SD[0] <= sd <= PULL_SD[1] and n_fail == 0
        if sc in NOT_JUDGED:
            passed = None
        row = dict(scenario=sc, join=j, method=m, q_class=ok[0]['q_class'], n=len(ok), failures=n_fail,
                   mean_pull=bias, pull_sd=sd, se_mean=sd / math.sqrt(len(ok)),
                   bias_rel=float(np.expm1(np.mean(dd))), rmse_delta=float(np.sqrt(np.mean(dd ** 2))),
                   median_err=float(np.median([p['err'] for p in ok])), passed=passed)
        if m == PRIOR:
            row['prior_used'] = float(np.mean([bool(p.get('prior_used')) for p in ok]))
        rows.append(row)
    return rows


def level_verdict(levels):
    rows = []
    for sc, m in sorted({(x['scenario'], x['method']) for x in levels}):
        xs_ = [x for x in levels if (x['scenario'], x['method']) == (sc, m)]
        pu = np.array([x['pull'] for x in xs_])
        rows.append(dict(scenario=sc, method=m, n=len(xs_), mean_pull=float(np.mean(pu)),
                         pull_sd=float(np.std(pu, ddof=1)),
                         rmse_phi=float(np.sqrt(np.mean([(x['phi_last'] - x['truth']) ** 2 for x in xs_]))),
                         median_err=float(np.median([x['err'] for x in xs_]))))
    return rows


def write_csv(path, rows):
    if not rows:
        return
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def summary(ver, lev, n_rep, out, errors='', monitor='real'):
    methods = list(METHODS) + [PRIOR]
    L = ['# Reflectivity patching gauntlet (synthetic)', '',
         '%d noise replicates per scenario; pass at a join: |mean pull| < %.1f, pull SD in %.2f–%.2f, no failed fit '
         '(hand-off 08). Per-point errors: %s; monitor: %s. Scenarios not judged (information only): %s. '
         'Generated by `tests/tools/ref_patch_gauntlet.py`.' % (n_rep, PULL_BIAS_MAX, *PULL_SD, errors, monitor,
                                                               ', '.join(sorted(NOT_JUDGED))), '',
         '## Joins passed, per method', '', '| method | joins passed | worst |mean pull| | worst pull SD | median RMSE of δ |',
         '|---|---|---|---|---|']
    for m in methods:
        r = [x for x in ver if x['method'] == m and x['scenario'] not in NOT_JUDGED]
        if not r:
            continue
        ok = [x for x in r if x.get('n')]
        L.append('| %s | %d / %d | %.2f | %.2f | %.4f |' % (
            m, sum(bool(x['passed']) for x in r), len(r), max(abs(x['mean_pull']) for x in ok),
            max(ok, key=lambda x: abs(x['pull_sd'] - 1))['pull_sd'], float(np.median([x['rmse_delta'] for x in ok]))))
    L += ['', '## Every join', '', '| scenario | join | Qz class | method | mean pull | pull SD | bias (rel.) | RMSE δ | pass |',
          '|---|---|---|---|---|---|---|---|---|']
    for x in ver:
        if not x.get('n'):
            L.append('| %s | %s | | %s | | | | | fail (%d failed fits) |' % (x['scenario'], x['join'], x['method'], x['failures']))
            continue
        L.append('| %s | %d | %s | %s | %+.2f | %.2f | %+.3f %% | %.4f | %s |' % (
            x['scenario'], x['join'], x['q_class'], x['method'], x['mean_pull'], x['pull_sd'], 100 * x['bias_rel'],
            x['rmse_delta'], 'not judged' if x['passed'] is None else ('yes' if x['passed'] else '**no**')))
    L += ['', '## The last scan\'s level (chained)', '', '| scenario | method | mean pull | pull SD | RMSE φ | median σ |',
          '|---|---|---|---|---|---|']
    for x in lev:
        L.append('| %s | %s | %+.2f | %.2f | %.4f | %.4f |' % (x['scenario'], x['method'], x['mean_pull'], x['pull_sd'],
                                                             x['rmse_phi'], x['median_err']))
    with open(os.path.join(out, 'summary.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--replicates', type=int, default=200)
    ap.add_argument('--scenarios', default='')
    ap.add_argument('--monitor', default='real', choices=sorted(MONITORS),
                    help="Monc noise: 'real' (no Poisson, 0.05 %% relative; owner) or 'poisson'")
    ap.add_argument('--errors', default='counting+monitor', help="the per-point σ of the synthetic scans: 'counting' or 'counting+monitor' (default; the reader's errors include the monitor)")
    a = ap.parse_args(argv)
    names = [s for s in a.scenarios.split(',') if s] or list(scenarios())
    os.makedirs(a.out, exist_ok=True)
    pulls, levels = run(names, a.replicates, a.out, a.errors, a.monitor)
    ver, lev = verdict(pulls), level_verdict(levels)
    write_csv(os.path.join(a.out, 'pulls.csv'), pulls)
    write_csv(os.path.join(a.out, 'verdict.csv'), ver)
    write_csv(os.path.join(a.out, 'levels.csv'), lev)
    summary(ver, lev, a.replicates, a.out, a.errors, a.monitor)


if __name__ == '__main__':
    main()
