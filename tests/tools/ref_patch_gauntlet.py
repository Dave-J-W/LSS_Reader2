"""The reflectivity patching gauntlet on synthetic scans with known truth
(owner, 2026-11-22: "make new method the default if it passes the
gauntlet"; "The gauntlet also requires using the synthetic data
capabilities and lots of replicates under diff conditions"). The judging
rules are hand-off 08's (docs/handoff_out/08-ref-patch-comparison.md, "How
to judge"): at every join, |mean pull| < 0.2 and pull SD within 0.9–1.15,
no failed fit, where pull = (δ̂ − δ_true)/σ̂ and δ = ln(factor on scan b).
The survey (ref_patch_survey.py) does this on real curves split in two;
this tool does it on many noise replicates of synthetic reflectivity
(tests/synthetic: Parratt, Névot–Croce, water's critical edge, Kiessig
fringes, the reader's ROI boxes, foils, monitors, faults;
docs/SYNTHETIC_DATA.md).

    python tests/tools/ref_patch_gauntlet.py --out DIR [--design core|grid|random|all]
        [--replicates 400] [--random 150 --random-replicates 60] [--methods key|all]
        [--conditions a,b] [--monitor real|poisson] [--rows]

Designs. ``core``: the seven conditions of the first run. ``grid``: one
factor at a time from a baseline (a 100 Å film on water, four scans with
coinciding overlaps, NX flux, the owner's monitor): the layer (water, DPPC,
films 50–400 Å), roughness, grid (coinciding, staggered, NX-like, reaching
back), number of scans and Qz range, overlap size, counts, count time,
background, monitor noise, resolution, energy, and planted faults (a slit
change the monitor misses; a foil 2 % off its calibration). ``random``:
conditions drawn at random over the same ranges (fewer replicates each),
judged pooled and per condition with allowance for their sampling error.

Two judgements: (1) each join method on each pair of scans (the hand-off's
rule); (2) the reader's own path, ``reflectivity.patch`` with the default
('joint') and 'legacy' methods, the whole chain against everything joined
so far: the last scan's level against the truth (bias, RMSE, and pull
against the error folded into its points).

Outputs: ``conditions.csv`` (what each condition is), ``verdict.csv``
(condition × join × method), ``levels.csv`` (the last scan's level, chained
with the carried covariance), ``reader.csv`` (the reader's path),
``summary.md``; ``pulls.csv`` (every replicate; large) only with ``--rows``.
Synthetic data only: public.
"""
import argparse
import csv
import math
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field

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
KEY_METHODS = ('legacy', 'interp', 'coincident', 'joint_o4_e2', 'joint_o4_e4', 'joint_o4_e4_g01')
DEFAULT = 'joint_o4_e2'
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

# the monitor (owner, 2026-11-22): no Poisson noise, a strict 0.05 % (xs.REAL_MONITOR)
MONITORS = {'real': xs.REAL_MONITOR, 'poisson': dict(monitor_poisson=True, monitor_jitter=0.0)}
FLUX = xs.Beamline().flux
BACKGROUND = xs.Beamline().background


@dataclass
class Cond:
    profile: object
    plan: object                  # () -> list of ScanSpec
    beamline: object
    resolution: tuple = None
    judged: bool = True
    factor: str = ''              # the factor varied (grid), or 'random'
    describe: str = ''


def core(monitor='real'):
    m = MONITORS[monitor]
    bl, lo = xs.Beamline(**m), xs.Beamline(flux=FLUX / 10, **m)
    return {
        'water_coincide': Cond(xrr.bare_water(), lambda: xs.standard_plan(4, grid='coincide'), bl, factor='core'),
        'water_staggered': Cond(xrr.bare_water(), lambda: xs.standard_plan(4, grid='staggered'), bl, factor='core'),
        'dppc_nx': Cond(xrr.dppc(), xs.nx_like_plan, bl, factor='core'),
        'film100_nx': Cond(xrr.film(100.0), xs.nx_like_plan, bl, factor='core'),
        'film250_staggered': Cond(xrr.film(250.0), lambda: xs.standard_plan(4, grid='staggered'), bl, factor='core'),
        'edge_staggered': Cond(xrr.bare_water(), lambda: xs.chain_plan(EDGE_RANGES, overlap=4, grid='staggered'), bl,
                               judged=False, factor='core', describe='overlap across the critical edge: information only'),
        'film100_lowcounts': Cond(xrr.film(100.0), lambda: xs.standard_plan(4, grid='coincide'), lo, factor='core'),
    }


def grid(monitor='real'):
    """One factor at a time from the baseline (module docstring)."""
    m = MONITORS[monitor]

    def bl(**kw):
        d = dict(m)
        d.update(kw)
        return xs.Beamline(**d)

    def std(n=4, grid_='coincide', **kw):
        return lambda: xs.standard_plan(n, grid=grid_, **kw)

    base = xrr.film(100.0)
    c = {'base': Cond(base, std(), bl(), factor='baseline', describe='100 Å film, 4 scans coinciding, NX flux')}
    for name, prof in (('water', xrr.bare_water()), ('dppc', xrr.dppc()), ('film50', xrr.film(50.0)),
                       ('film150', xrr.film(150.0)), ('film250', xrr.film(250.0)), ('film400', xrr.film(400.0))):
        c['layer_' + name] = Cond(prof, std(), bl(), factor='layer')
    for s in (2.5, 4.5, 6.0):
        c['rough_film_%g' % s] = Cond(xrr.film(100.0, sigma=s), std(), bl(), factor='roughness')
    c['rough_water_4.5'] = Cond(xrr.bare_water(sigma=4.5), std(), bl(), factor='roughness')
    for name, prof in (('water', xrr.bare_water()), ('dppc', xrr.dppc()), ('film100', base), ('film250', xrr.film(250.0))):
        c['staggered_' + name] = Cond(prof, std(grid_='staggered'), bl(), factor='grid')
        c['nxgrid_' + name] = Cond(prof, xs.nx_like_plan, bl(), factor='grid')
    c['reaching_back_film100'] = Cond(base, xs.reaching_back_plan, bl(), factor='grid')
    c['scans_3'] = Cond(base, std(3), bl(), factor='scans')
    c['scans_5'] = Cond(base, std(5), bl(), factor='scans')
    c['qzmax_0.35'] = Cond(base, std(qz_max=0.35), bl(), factor='scans')
    c['qzmax_0.7'] = Cond(base, std(qz_max=0.7), bl(), factor='scans')
    for ov in (3, 6):
        c['overlap_%d' % ov] = Cond(base, std(overlap=ov), bl(), factor='overlap')
        c['overlap_%d_staggered' % ov] = Cond(base, std(grid_='staggered', overlap=ov), bl(), factor='overlap')
    for f in (0.3, 0.1, 0.03):
        c['flux_x%g' % f] = Cond(base, std(), bl(flux=FLUX * f), factor='counts')
    c['flux_x0.1_staggered'] = Cond(base, std(grid_='staggered'), bl(flux=FLUX * 0.1), factor='counts')
    c['time_x0.3'] = Cond(base, std(seconds=0.3), bl(), factor='counts')
    for f in (10, 100):
        c['background_x%g' % f] = Cond(base, std(), bl(background=BACKGROUND * f), factor='background')
    c['background_x100_film250'] = Cond(xrr.film(250.0), std(), bl(background=BACKGROUND * 100), factor='background')
    for j in (0.001, 0.002):
        c['monitor_%g' % j] = Cond(base, std(), bl(monitor_jitter=j), factor='monitor')
    c['monitor_poisson'] = Cond(base, std(), xs.Beamline(**MONITORS['poisson']), factor='monitor')
    c['resolution_dq_0.0005'] = Cond(base, std(), bl(), resolution=(0.0005, 0.0), factor='resolution')
    c['resolution_rel_0.03'] = Cond(base, std(), bl(), resolution=(0.0, 0.03), factor='resolution')
    c['resolution_rel_0.03_film250'] = Cond(xrr.film(250.0), std(), bl(), resolution=(0.0, 0.03), factor='resolution')
    for e in (8.0, 15.0):
        c['energy_%g' % e] = Cond(base, std(), bl(energy_kev=e), factor='energy')
    c['fault_slits_missed'] = Cond(base, std(slit_gain=[1, 1, 2.0, 2.0], monitor_gain=[1, 1, 1, 1]), bl(),
                                   factor='faults', describe='slits opened ×2 at scan 3, Monc misses it (P29)')
    c['fault_foil_2pc'] = Cond(base, std(attenuation_error=[1, 1.02, 1, 1]), bl(),
                               factor='faults', describe='scan 2 foil 2 % thicker than calibrated')
    c['edge_staggered'] = Cond(xrr.bare_water(), lambda: xs.chain_plan(EDGE_RANGES, overlap=4, grid='staggered'), bl(),
                               judged=False, factor='edge', describe='overlap across the critical edge: information only')
    return c


def random_conditions(n, seed=20261122, monitor='real'):
    """``n`` conditions drawn over the grid's ranges."""
    rng = np.random.default_rng(seed)
    m = MONITORS[monitor]
    out = {}
    for i in range(n):
        kind = rng.choice(['water', 'dppc', 'film', 'film', 'film'])
        sigma = float(rng.uniform(2.5, 6.0))
        if kind == 'water':
            prof, what = xrr.bare_water(sigma=sigma), 'water'
        elif kind == 'dppc':
            prof, what = xrr.dppc(sigma=sigma), 'DPPC'
        else:
            d = float(np.round(rng.uniform(30, 400)))
            prof, what = xrr.film(d, sigma=sigma), '%g Å film' % d
        g = str(rng.choice(['coincide', 'staggered']))
        n_sc = int(rng.integers(3, 6))
        ov = int(rng.integers(3, 7))
        qmax = float(rng.uniform(0.35, 0.7))
        flux = FLUX * 10 ** float(rng.uniform(-1.5, 0))
        bg = BACKGROUND * 10 ** float(rng.uniform(0, 2))
        jit = float(rng.uniform(0.0003, 0.002))
        energy = float(rng.choice([8.0, 10.0, 10.0, 15.0]))
        res = None if rng.random() < 0.5 else (0.0, float(rng.uniform(0.005, 0.04)))
        d = dict(m)
        d.update(flux=flux, background=bg, monitor_jitter=jit if not d.get('monitor_poisson') else 0.0, energy_kev=energy)
        out['random_%03d' % i] = Cond(
            prof, (lambda n_sc=n_sc, g=g, ov=ov, qmax=qmax: xs.standard_plan(n_sc, qz_max=qmax, overlap=ov, grid=g)),
            xs.Beamline(**d), res, True, 'random',
            '%s σ %.1f Å; %d scans %s, overlap %d, to %.2f Å⁻¹; flux ×%.2g, background ×%.2g, monitor %.2g %%, %g keV, '
            'resolution %s' % (what, sigma, n_sc, g, ov, qmax, flux / FLUX, bg / BACKGROUND, 100 * jit, energy,
                               'none' if res is None else '%.1f %% dQ/Q' % (100 * res[1])))
    return out


def fringe_period(profile):
    """Kiessig period 2π/d of the layers' total thickness (Å⁻¹); inf without layers."""
    d = sum(l.thickness for l in profile.layers)
    return 2 * math.pi / d if d > 0 else math.inf


def sampling_class(ppf):
    """Points per fringe period of the coarser scan at a join: whether the
    measurement resolves the fringes there at all (a plan the experimenter
    would choose samples a fringe with several points)."""
    if not np.isfinite(ppf) or ppf >= 6:
        return '>=6 per fringe'
    return '3-6 per fringe' if ppf >= 3 else '<3 per fringe'


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


def replicate(cond, seed, errors='counting+monitor'):
    r = xs.measure(cond.profile, cond.plan(), beamline=cond.beamline, resolution=cond.resolution, seed=seed,
                   errors=errors)
    sc = [patching.Scan(r.per_scan[k][:, 0], r.per_scan[k][:, 1], r.per_scan[k][:, 2], label=str(k),
                        absorber=r.scans[k].absorber) for k in r.order]
    truth = [math.log(v) for v in r.true_steps().values()]
    mr = []
    for a, b in zip(r.order, r.order[1:]):
        A, B = r.scans[a], r.scans[b]
        mr.append(refl.monitor_change(A.qz, A.monc, A.monp, B.qz, B.monc, B.monp))
    return r, sc, truth, mr


def reader_level(r, method):
    """The reader's path (``reflectivity.patch``): the last scan's level
    against the truth over its own points beyond the previous scan, and the
    part of its folded error that is the factors' (log units)."""
    patched = refl.patch(r.per_scan, r.order, method=method)
    s0 = r.scans[r.order[0]].scale
    last = r.per_scan[r.order[-1]]
    prev_max = float(np.max(r.per_scan[r.order[-2]][:, 0]))
    own = patched[:, 0] > prev_max + 1e-9
    q, y, s = patched[own, 0], patched[own, 1], patched[own, 2]
    ok = y > 0
    lev = float(np.median(np.log(y[ok] * s0 / r.truth(q[ok]))))
    # counting part of each point's relative error, from the scan itself
    rel_c = np.interp(q[ok], last[:, 0], last[:, 2] / np.maximum(np.abs(last[:, 1]), 1e-300))
    rel_t = s[ok] / y[ok]
    fac = float(np.sqrt(max(np.median(rel_t ** 2 - rel_c ** 2), 0.0)))
    return lev, fac


def run(conds, n_rep, methods, errors='counting+monitor', keep_rows=False, log=print):
    acc = defaultdict(list)        # (cond, join, method) -> [(delta - truth, err, q_class)] or 'fail'
    lev = defaultdict(list)        # (cond, method) -> [(phi - truth, err)]
    rdr = defaultdict(list)        # (cond, method) -> [(level, folded factor error)]
    prior_used = defaultdict(list)
    sampling = {}                  # (cond, join) -> points per fringe period of scan b
    rows = [] if keep_rows else None
    for ci, (name, cond) in enumerate(conds.items()):
        t0 = time.time()
        for rep in range(n_rep):
            seed = 1000 * (rep + 1) + 7919 * ci
            try:
                r, sc, truth, mr = replicate(cond, seed, errors)
            except Exception as exc:                  # a plan the generator cannot draw: recorded
                acc[(name, 0, 'generator')].append('fail')
                log('%s rep %d: generator failed: %s' % (name, rep, exc))
                continue
            phi_true = float(np.sum(truth))
            if rep == 0:
                per = fringe_period(cond.profile)
                for m in range(1, len(sc)):
                    step = float(np.median(np.diff(sc[m].q))) if len(sc[m].q) > 1 else math.inf
                    sampling[(name, m)] = per / step
            for mname in methods:
                spec = METHODS[mname]
                d, e = [], []
                for m in range(1, len(sc)):
                    try:
                        dm, em = fit_join(sc[m - 1], sc[m], spec)
                        if not (np.isfinite(dm) and np.isfinite(em) and em > 0):
                            raise ValueError('not finite')
                    except Exception as exc:          # counted as a failure in the verdict
                        acc[(name, m, mname)].append('fail')
                        d.append(math.nan)
                        e.append(math.nan)
                        if rows is not None:
                            rows.append(dict(condition=name, rep=rep, join=m, method=mname, error=type(exc).__name__))
                        continue
                    acc[(name, m, mname)].append((dm - truth[m - 1], em, q_class(float(sc[m].q.min()))))
                    if rows is not None:
                        rows.append(dict(condition=name, rep=rep, join=m, method=mname, delta=dm, err=em,
                                         truth=truth[m - 1]))
                    d.append(dm)
                    e.append(em)
                if all(np.isfinite(d)):
                    phi, S = unc.steps_to_phi(d, np.diag(np.square(e)))
                    lev[(name, mname)].append((float(phi[-1]) - phi_true, float(math.sqrt(S[-1, -1]))))
            try:                                      # the foil prior, used where the monitor shows it applies
                prior = patching.known_steps(r.beamline.foils(), [s.absorber for s in sc], [s.q.min() for s in sc[1:]])
                res = patching.chain(sc, prior=prior, monitor_ratios=mr)
                for m, j in enumerate(res.joins, start=1):
                    err = float(math.sqrt(res.C_steps[m - 1, m - 1]))
                    acc[(name, m, PRIOR)].append((float(res.steps[m - 1]) - truth[m - 1], err,
                                                  q_class(float(sc[m].q.min()))))
                    prior_used[(name, m)].append(bool(j.prior_used))
                lev[(name, PRIOR)].append((float(res.phi[-1]) - phi_true, float(math.sqrt(res.Sigma[-1, -1]))))
            except Exception:
                for m in range(1, len(sc)):
                    acc[(name, m, PRIOR)].append('fail')
            for meth in ('joint', 'legacy'):          # the reader's own path
                try:
                    rdr[(name, meth)].append(reader_level(r, meth))
                except Exception:
                    rdr[(name, meth)].append('fail')
        log('%s: %d replicates, %.0f s' % (name, n_rep, time.time() - t0))
    return acc, lev, rdr, prior_used, sampling, rows


def judge(pu, n_fail, tolerant):
    """Pass by hand-off 08's rule; ``tolerant`` (few replicates) widens the
    bounds by two standard errors of the mean and of the SD."""
    n = len(pu)
    bias, sd = float(np.mean(pu)), float(np.std(pu, ddof=1))
    if tolerant:
        se_m, se_sd = sd / math.sqrt(n), sd / math.sqrt(2 * (n - 1))
        ok = abs(bias) < PULL_BIAS_MAX + 2 * se_m and PULL_SD[0] - 2 * se_sd <= sd <= PULL_SD[1] + 2 * se_sd
    else:
        ok = abs(bias) < PULL_BIAS_MAX and PULL_SD[0] <= sd <= PULL_SD[1]
    return bias, sd, ok and n_fail == 0


def verdict(acc, conds, prior_used, sampling, tolerant_factors=('random',)):
    rows = []
    for (name, j, m), v in sorted(acc.items()):
        if m == 'generator':
            continue
        cond = conds[name]
        ok = [x for x in v if x != 'fail']
        n_fail = len(v) - len(ok)
        if len(ok) < 3:
            rows.append(dict(condition=name, factor=cond.factor, join=j, method=m, n=len(ok), failures=n_fail,
                             passed=False if cond.judged else None))
            continue
        dd = np.array([x[0] for x in ok])
        ee = np.array([x[1] for x in ok])
        bias, sd, passed = judge(dd / ee, n_fail, cond.factor in tolerant_factors)
        ppf = sampling.get((name, j), math.inf)
        row = dict(condition=name, factor=cond.factor, join=j, method=m, q_class=ok[0][2],
                   points_per_fringe=ppf, sampling=sampling_class(ppf), n=len(ok), failures=n_fail,
                   mean_pull=bias, pull_sd=sd, bias_rel=float(np.expm1(np.mean(dd))),
                   rmse_delta=float(np.sqrt(np.mean(dd ** 2))), median_err=float(np.median(ee)),
                   passed=passed if cond.judged else None)
        if m == PRIOR:
            row['prior_used'] = float(np.mean(prior_used[(name, j)])) if prior_used[(name, j)] else 0.0
        rows.append(row)
    return rows


def level_verdict(lev, conds):
    rows = []
    for (name, m), v in sorted(lev.items()):
        d = np.array([x[0] for x in v])
        e = np.array([x[1] for x in v])
        if len(d) < 3:
            continue
        rows.append(dict(condition=name, factor=conds[name].factor, method=m, n=len(d), mean_pull=float(np.mean(d / e)),
                         pull_sd=float(np.std(d / e, ddof=1)), rmse_phi=float(np.sqrt(np.mean(d ** 2))),
                         median_err=float(np.median(e))))
    return rows


def reader_verdict(rdr, conds):
    rows = []
    for (name, m), v in sorted(rdr.items()):
        ok = [x for x in v if x != 'fail']
        if len(ok) < 3:
            rows.append(dict(condition=name, factor=conds[name].factor, method=m, n=len(ok), failures=len(v) - len(ok)))
            continue
        d = np.array([x[0] for x in ok])
        f = np.array([x[1] for x in ok])
        rows.append(dict(condition=name, factor=conds[name].factor, method=m, n=len(ok), failures=len(v) - len(ok),
                         bias=float(np.mean(d)), se_bias=float(np.std(d, ddof=1) / math.sqrt(len(d))),
                         rmse=float(np.sqrt(np.mean(d ** 2))), scatter=float(np.std(d, ddof=1)),
                         median_folded_factor_err=float(np.median(f)),
                         scatter_over_folded=float(np.std(d, ddof=1) / max(np.median(f), 1e-12))))
    return rows


def pooled(ver_rows, acc, conds, sampling, factor='random'):
    """Pooled pulls over all conditions of ``factor`` by method, fringe
    sampling and Qz class; and the share of joins passed by sampling."""
    out = defaultdict(list)
    for (name, j, m), v in acc.items():
        if m == 'generator' or conds[name].factor != factor or not conds[name].judged:
            continue
        sc_ = sampling_class(sampling.get((name, j), math.inf))
        for x in v:
            if x != 'fail':
                out[(m, sc_, x[2])].append(x[0] / x[1])
    rows = []
    for (m, sc_, qc), pu in sorted(out.items()):
        pu = np.array(pu)
        passed = [x for x in ver_rows if x['method'] == m and x.get('sampling') == sc_ and x.get('q_class') == qc
                  and conds[x['condition']].factor == factor and x.get('passed') is not None]
        rows.append(dict(method=m, sampling=sc_, q_class=qc, n=len(pu), mean_pull=float(np.mean(pu)),
                         pull_sd=float(np.std(pu, ddof=1)), frac_abs_gt3=float(np.mean(np.abs(pu) > 3)),
                         joins=len(passed), joins_passed=sum(bool(x['passed']) for x in passed)))
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


def _fmt_pass(x):
    return 'not judged' if x.get('passed') is None else ('yes' if x['passed'] else '**no**')


def summary(ver, lev, rdr, pool, conds, args, out):
    methods = [m for m in list(METHODS) + [PRIOR] if any(x['method'] == m for x in ver)]
    designs = sorted({c.factor == 'random' and 'random' or 'designed' for c in conds.values()})
    L = ['# Reflectivity patching gauntlet (synthetic)', '',
         'Generated by `tests/tools/ref_patch_gauntlet.py --design %s --methods %s` (%d replicates per designed condition, %d per '
         'random one). A join passes when |mean pull| < %.1f, pull SD is within %.2f–%.2f and no fit failed (hand-off '
         '08); random conditions, with fewer replicates, are allowed two standard errors. Per-point errors: %s; monitor: '
         '%s. Conditions not judged (information only): %s.' % (
             args.design, args.methods, args.replicates, args.random_replicates, PULL_BIAS_MAX, *PULL_SD, args.errors, args.monitor,
             ', '.join(sorted(n for n, c in conds.items() if not c.judged)) or 'none'), '']
    for design in designs:
        sel = [x for x in ver if (conds[x['condition']].factor == 'random') == (design == 'random')]
        if not sel:
            continue
        L += ['## Joins passed per method (%s conditions)' % design, '',
              '| method | joins passed | worst \\|mean pull\\| | worst pull SD | median RMSE of δ |', '|---|---|---|---|---|']
        for m in methods:
            r = [x for x in sel if x['method'] == m and x.get('passed') is not None]
            ok = [x for x in r if x.get('n', 0) >= 3 and 'mean_pull' in x]
            if not r or not ok:
                continue
            L.append('| %s | %d / %d | %.2f | %.2f | %.4f |' % (
                m, sum(bool(x['passed']) for x in r), len(r), max(abs(x['mean_pull']) for x in ok),
                max(ok, key=lambda x: abs(x['pull_sd'] - 1))['pull_sd'], float(np.median([x['rmse_delta'] for x in ok]))))
        L.append('')
    if pool:
        L += ['## Pooled over the random conditions, by fringe sampling and Qz class', '',
              'Sampling: points per Kiessig period 2π/d of the coarser scan at the join (d the layers\' total '
              'thickness); below 3 the scans do not resolve the fringes there.', '',
              '| method | sampling | Qz class | joins passed | pulls | mean pull | pull SD | \|pull\| > 3 |',
              '|---|---|---|---|---|---|---|---|']
        for x in pool:
            L.append('| %s | %s | %s | %d / %d | %d | %+.3f | %.3f | %.2f %% |' % (
                x['method'], x['sampling'], x['q_class'], x['joins_passed'], x['joins'], x['n'], x['mean_pull'],
                x['pull_sd'], 100 * x['frac_abs_gt3']))
        L.append('')
    L += ['## Where the default (%s) fails' % DEFAULT, '', '| condition | what | join | Qz class | points per fringe | mean pull | pull SD | bias (rel.) | failed fits |',
          '|---|---|---|---|---|---|---|---|---|']
    for x in ver:
        if x['method'] == DEFAULT and x.get('passed') is False:
            c = conds[x['condition']]
            L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %d |' % (
                x['condition'], c.describe or c.factor, x['join'], x.get('q_class', ''),
                '%.1f' % x['points_per_fringe'] if np.isfinite(x.get('points_per_fringe', math.inf)) else '–',
                '%+.2f' % x['mean_pull'] if 'mean_pull' in x else '', '%.2f' % x['pull_sd'] if 'pull_sd' in x else '',
                '%+.3f %%' % (100 * x['bias_rel']) if 'bias_rel' in x else '', x.get('failures', 0)))
    L += ['', "## The reader's path: the last scan's level (`reflectivity.patch`)", '',
          'Bias and RMSE of ln(level) against the truth; "scatter / folded" is the observed scatter over the factors\' '
          'part of the error folded into the points (about 1 when the folded error is right; it carries only the last '
          'join\'s error, so it understates the chained level error).', '',
          '| condition | factor | method | bias | ± | RMSE | scatter / folded |', '|---|---|---|---|---|---|---|']
    for x in rdr:
        if 'bias' not in x:
            L.append('| %s | %s | %s | failed | | | |' % (x['condition'], x['factor'], x['method']))
            continue
        L.append('| %s | %s | %s | %+.4f | %.4f | %.4f | %.2f |' % (x['condition'], x['factor'], x['method'], x['bias'],
                                                                  x['se_bias'], x['rmse'], x['scatter_over_folded']))
    L += ['', '## Every join', '', '| condition | factor | join | Qz class | method | mean pull | pull SD | bias (rel.) | RMSE δ | pass |',
          '|---|---|---|---|---|---|---|---|---|---|']
    for x in ver:
        if 'mean_pull' not in x:
            L.append('| %s | %s | %s | | %s | | | | | %s (%d failed fits) |' % (x['condition'], x['factor'], x['join'],
                                                                           x['method'], _fmt_pass(x), x.get('failures', 0)))
            continue
        L.append('| %s | %s | %d | %s | %s | %+.2f | %.2f | %+.3f %% | %.4f | %s |' % (
            x['condition'], x['factor'], x['join'], x['q_class'], x['method'], x['mean_pull'], x['pull_sd'],
            100 * x['bias_rel'], x['rmse_delta'], _fmt_pass(x)))
    L += ['', "## The last scan's level, chained with the carried covariance", '',
          '| condition | method | mean pull | pull SD | RMSE φ | median σ |', '|---|---|---|---|---|---|']
    for x in lev:
        L.append('| %s | %s | %+.2f | %.2f | %.4f | %.4f |' % (x['condition'], x['method'], x['mean_pull'], x['pull_sd'],
                                                             x['rmse_phi'], x['median_err']))
    with open(os.path.join(out, 'summary.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--design', default='core', choices=['core', 'grid', 'random', 'all'])
    ap.add_argument('--replicates', type=int, default=400, help='per designed condition')
    ap.add_argument('--random', type=int, default=150, help='number of random conditions')
    ap.add_argument('--random-replicates', type=int, default=60)
    ap.add_argument('--methods', default='all', help="'all', 'key' or a comma-separated list")
    ap.add_argument('--conditions', default='', help='only these (comma-separated names)')
    ap.add_argument('--monitor', default='real', choices=sorted(MONITORS),
                    help="Monc noise: 'real' (no Poisson, 0.05 %% relative; owner) or 'poisson'")
    ap.add_argument('--errors', default='counting+monitor',
                    help="per-point σ: 'counting' or 'counting+monitor' (default; the reader's errors include the monitor)")
    ap.add_argument('--rows', action='store_true', help='also write pulls.csv (every replicate; large)')
    a = ap.parse_args(argv)
    methods = list(METHODS) if a.methods == 'all' else (list(KEY_METHODS) if a.methods == 'key' else a.methods.split(','))
    designed, randoms = {}, {}
    if a.design in ('core', 'all'):
        designed.update(core(a.monitor))
    if a.design in ('grid', 'all'):
        designed.update(grid(a.monitor))
    if a.design in ('random', 'all'):
        randoms = random_conditions(a.random, monitor=a.monitor)
    if a.conditions:
        keep = set(a.conditions.split(','))
        designed = {k: v for k, v in designed.items() if k in keep}
        randoms = {k: v for k, v in randoms.items() if k in keep}
    os.makedirs(a.out, exist_ok=True)
    logf = open(os.path.join(a.out, 'log.txt'), 'w')

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + '\n')
    acc, lev, rdr, pu, smp, rows = run(designed, a.replicates, methods, a.errors, a.rows, log)
    if randoms:
        acc2, lev2, rdr2, pu2, smp2, rows2 = run(randoms, a.random_replicates, methods, a.errors, a.rows, log)
        acc.update(acc2), lev.update(lev2), rdr.update(rdr2), pu.update(pu2), smp.update(smp2)
        if rows is not None:
            rows += rows2
    conds = dict(designed, **randoms)
    ver, lv, rv = verdict(acc, conds, pu, smp), level_verdict(lev, conds), reader_verdict(rdr, conds)
    pool = pooled(ver, acc, conds, smp) if randoms else []
    write_csv(os.path.join(a.out, 'conditions.csv'),
              [dict(condition=n, factor=c.factor, judged=c.judged, profile=getattr(c.profile, 'name', ''),
                    resolution=c.resolution, flux=c.beamline.flux, background=c.beamline.background,
                    monitor_jitter=c.beamline.monitor_jitter, monitor_poisson=c.beamline.monitor_poisson,
                    energy_kev=c.beamline.energy_kev, describe=c.describe) for n, c in conds.items()])
    write_csv(os.path.join(a.out, 'verdict.csv'), ver)
    write_csv(os.path.join(a.out, 'levels.csv'), lv)
    write_csv(os.path.join(a.out, 'reader.csv'), rv)
    if pool:
        write_csv(os.path.join(a.out, 'pooled.csv'), pool)
    if rows is not None:
        write_csv(os.path.join(a.out, 'pulls.csv'), rows)
    summary(ver, lv, rv, pool, conds, a, a.out)
    logf.close()


if __name__ == '__main__':
    main()
