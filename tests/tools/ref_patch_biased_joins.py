"""Why five of the reflectivity gauntlet's designed joins are biased under
the default joint fit, and why its error is about 12 % small at the first
join of the downstream-covariance study (pull SD 1.13). This is extension
4 of the gauntlet's report (Main, 2026-11-23; physics_notes, "What the
gauntlet is"; TODO B).

    python tests/tools/ref_patch_biased_joins.py --out DIR [--replicates 400] [--joins cond:join,...]
        [--covariance-seeds 300] [--no-covariance]

The joins are the default's (``joint_o4_e2``) designed joins with |mean
pull| ≥ 0.2 and at least 3 points per Kiessig fringe, in the committed
gauntlet (docs/comparisons_data/ref_patch_gauntlet). They are
layer_dppc j3, layer_film150 j2, overlap_3_staggered j3, overlap_6 j1
and scans_5 j2. Each is redrawn with the gauntlet's own conditions and
seeds (``ref_patch_gauntlet.replicate``, seed 1000·(rep+1) + 7919·ci), so
the default's numbers come back exactly. Each is then fitted with these
variants of ``patching.joint_factor``:

- ``default``: order 4, 2 points either side, the guard at p 0.3 (the
  ladder: the window and order chosen after seeing χ²);
- ``guard_off``: the same window and order every time, no ladder, no
  inflation;
- ``guard_0.01``: the guard of before 2026-11-22;
- ``o3_off``, ``o5_off``, ``o6_off``: other orders, no guard;
- ``e1_off``, ``e4_off``: other windows, no guard;
- ``log``: the log likelihood, with the default guard.

Two things separate the possible causes:
- **noise-free** δ (the same plan with ``expected=True``) gives the model
  bias, (δ̂_expected − δ_true) / the median error, with no noise and no
  selection;
- the **guard's choices** (order, points either side) per replicate, with
  the mean pull of each choice: post-selection shows as pulls that depend
  on the choice.

The covariance study's first join is redrawn the same way (NX-like plan,
a 25 Å film, the owner's monitor, seeds 0..N−1, as
``tests/tools/covariance_pulls.py``) with the same variants.

Outputs: ``joins.csv`` (join × variant: mean pull, pull SD, bias of δ,
median error, noise-free bias in errors), ``choices.csv`` (join × the
guard's choice: share, mean pull, pull SD), ``summary.md``. All the data
are synthetic, so the outputs are public.
"""
import argparse
import csv
import math
import os
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
sys.path.insert(0, os.path.join(os.getcwd(), 'tests', 'tools'))

from lss_core import patching                       # noqa: E402
from synthetic import xrr, xrr_scans as xs          # noqa: E402
import ref_patch_gauntlet as gauntlet               # noqa: E402

JOINS = ('layer_dppc:3', 'layer_film150:2', 'overlap_3_staggered:3', 'overlap_6:1', 'scans_5:2')
VARIANTS = {
    'default': dict(order=4, n_ext=2),
    'guard_off': dict(order=4, n_ext=2, guard_p=0),
    'guard_0.01': dict(order=4, n_ext=2, guard_p=0.01),
    'o3_off': dict(order=3, n_ext=2, guard_p=0),
    'o5_off': dict(order=5, n_ext=2, guard_p=0),
    'o6_off': dict(order=6, n_ext=2, guard_p=0),
    'e1_off': dict(order=4, n_ext=1, guard_p=0),
    'e4_off': dict(order=4, n_ext=4, guard_p=0),
    'log': dict(order=4, n_ext=2, likelihood='log'),
}
COV_TRUTH = (25.0, 0.39, 3.5)                       # covariance_pulls.TRUTH



def _fell_back(note):
    """True when no rung reached the guard's p, so its best one was kept. The note reads "no adequate
    fit" (before 2026-11-24, and below patching.ADEQUATE_P since) or "the best fit of the ladder"."""
    return 'no adequate' in note or 'best fit of the ladder' in note

def designed():
    """The gauntlet's designed conditions in its own order (``--design all``),
    so that the condition index, and with it the seeds, are the gauntlet's."""
    d = dict(gauntlet.core('real'))
    d.update(gauntlet.grid('real'))
    return d


def scans_of(r):
    return [patching.Scan(r.per_scan[k][:, 0], r.per_scan[k][:, 1], r.per_scan[k][:, 2], label=str(k))
            for k in r.order]


def fit(a, b, spec):
    try:
        j = patching.joint_factor(a, b, **spec)
    except Exception:
        return None
    if not (np.isfinite(j.delta) and np.isfinite(j.err) and j.err > 0):
        return None
    return j


def study(draw, truth_of, m, n_rep, expected):
    """Every variant on join ``m`` (scans m−1, m) of ``n_rep`` draws.
    ``draw(rep)`` gives ReducedScans; ``expected()`` the noise-free ones."""
    rows = defaultdict(list)            # variant -> [(pull, delta - truth, err)]
    choices = defaultdict(list)         # (order, n_ext) of the default -> [pull]
    fails = defaultdict(int)
    for rep in range(n_rep):
        r = draw(rep)
        sc = scans_of(r)
        t = truth_of(r)[m - 1]
        for name, spec in VARIANTS.items():
            j = fit(sc[m - 1], sc[m], spec)
            if j is None:
                fails[name] += 1
                continue
            rows[name].append(((j.delta - t) / j.err, j.delta - t, j.err))
            if name == 'default':
                choices[(j.order, j.n_ext, bool(j.flags and _fell_back(j.flags[-1])))].append((j.delta - t) / j.err)
    r0 = expected()
    sc0 = scans_of(r0)
    t0 = truth_of(r0)[m - 1]
    out = []
    for name in VARIANTS:
        v = np.array(rows[name]) if rows[name] else np.zeros((0, 3))
        j0 = fit(sc0[m - 1], sc0[m], VARIANTS[name])
        med = float(np.median(v[:, 2])) if len(v) else math.nan
        out.append(dict(variant=name, n=len(v), failed=fails[name],
                        mean_pull=float(v[:, 0].mean()) if len(v) else math.nan,
                        pull_sd=float(v[:, 0].std(ddof=1)) if len(v) > 1 else math.nan,
                        bias_delta=float(v[:, 1].mean()) if len(v) else math.nan,
                        rms_delta=float(np.sqrt(np.mean(v[:, 1] ** 2))) if len(v) else math.nan,
                        median_err=med,
                        noise_free_bias=(j0.delta - t0) / med if (j0 is not None and med > 0) else math.nan,
                        noise_free_order=j0.order if j0 is not None else '',
                        noise_free_n_ext=j0.n_ext if j0 is not None else ''))
    total = sum(len(v) for v in choices.values())
    ch = [dict(order=o, n_ext=e, inflated=inf, share=len(v) / total, mean_pull=float(np.mean(v)),
               pull_sd=float(np.std(v, ddof=1)) if len(v) > 1 else math.nan)
          for (o, e, inf), v in sorted(choices.items(), key=lambda kv: -len(kv[1]))]
    return out, ch


def gauntlet_join(name, m, n_rep):
    conds = designed()
    ci = list(conds).index(name)
    cond = conds[name]

    def draw(rep):
        return gauntlet.replicate(cond, 1000 * (rep + 1) + 7919 * ci)[0]

    def expected():
        return xs.measure(cond.profile, cond.plan(), beamline=cond.beamline, resolution=cond.resolution,
                          errors='counting+monitor', expected=True)

    def truth_of(r):
        return [math.log(v) for v in r.true_steps().values()]
    return study(draw, truth_of, m, n_rep, expected)


def covariance_join(seeds):
    bl = xs.Beamline(**xs.REAL_MONITOR)
    prof = xrr.film(*COV_TRUTH)

    def draw(seed):
        return xs.measure(prof, xs.nx_like_plan(), beamline=bl, seed=seed, errors='counting+monitor')

    def expected():
        return xs.measure(prof, xs.nx_like_plan(), beamline=bl, errors='counting+monitor', expected=True)

    def truth_of(r):
        return [math.log(v) for v in r.true_steps().values()]
    return study(draw, truth_of, 1, seeds, expected)


def write_csv(path, rows):
    if not rows:
        return
    keys = list(rows[0])
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})


def _f(x, fmt):
    try:
        return fmt % x if np.isfinite(x) else '—'
    except TypeError:
        return str(x)


def summary(results, choices, args, out):
    L = ['# Biased joins of the reflectivity gauntlet (extension 4)', '',
         'Generated by `tests/tools/ref_patch_biased_joins.py` (%d replicates per gauntlet join, the gauntlet\'s seeds; '
         '%s). Each cell: mean pull / pull SD; the noise-free bias is (δ̂ − δ_true)/median error on the same plan '
         'without noise. Variants are `patching.joint_factor` settings (the tool\'s docstring).'
         % (args.replicates, 'the covariance study\'s first join over %d seeds' % args.covariance_seeds
            if not args.no_covariance else 'no covariance study'), '']
    names = list(VARIANTS)
    L += ['| Join | ' + ' | '.join(names) + ' |', '|---|' + '---|' * len(names)]
    for key, rows in results.items():
        idx = {r['variant']: r for r in rows}
        L.append('| %s | %s |' % (key, ' | '.join('%s / %s' % (_f(idx[n]['mean_pull'], '%+.2f'),
                                                               _f(idx[n]['pull_sd'], '%.2f')) for n in names)))
    L += ['', 'Noise-free bias (in median errors) and the order, points either side chosen without noise:', '',
          '| Join | ' + ' | '.join(names) + ' |', '|---|' + '---|' * len(names)]
    for key, rows in results.items():
        idx = {r['variant']: r for r in rows}
        L.append('| %s | %s |' % (key, ' | '.join('%s (%s, %s)' % (_f(idx[n]['noise_free_bias'], '%+.2f'),
                                                                   idx[n]['noise_free_order'], idx[n]['noise_free_n_ext'])
                                                  for n in names)))
    L += ['', '## The default\'s choices (the guard ladder)', '',
          '| Join | order | points either side | inflated | share | mean pull | pull SD |', '|---|---|---|---|---|---|---|']
    for key, ch in choices.items():
        for c in ch:
            L.append('| %s | %d | %d | %s | %.3f | %s | %s |' % (key, c['order'], c['n_ext'], 'yes' if c['inflated'] else '',
                                                               c['share'], _f(c['mean_pull'], '%+.2f'),
                                                               _f(c['pull_sd'], '%.2f')))
    with open(os.path.join(out, 'summary.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--replicates', type=int, default=400, help='per gauntlet join (the gauntlet used 400)')
    ap.add_argument('--joins', default=','.join(JOINS), help='condition:join, comma-separated')
    ap.add_argument('--covariance-seeds', type=int, default=300)
    ap.add_argument('--no-covariance', action='store_true', help='leave out the covariance study\'s first join')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    results, choices = {}, {}
    for item in [j for j in a.joins.split(',') if j]:
        name, m = item.split(':')
        t0 = time.time()
        results[item], choices[item] = gauntlet_join(name, int(m), a.replicates)
        print('%s: %.0f s' % (item, time.time() - t0), flush=True)
    if not a.no_covariance:
        t0 = time.time()
        key = 'covariance_first_join'
        results[key], choices[key] = covariance_join(a.covariance_seeds)
        print('%s: %.0f s' % (key, time.time() - t0), flush=True)
    write_csv(os.path.join(a.out, 'joins.csv'), [dict(join=k, **r) for k, rows in results.items() for r in rows])
    write_csv(os.path.join(a.out, 'choices.csv'), [dict(join=k, **c) for k, ch in choices.items() for c in ch])
    summary(results, choices, a, a.out)


# C45 (the biased joins) as run: the joint fit's guard at p 0.3, the default from 2026-11-22 until 2026-11-24, when it
# became 0.7 (study A, docs/studies/reflectivity_guard). The committed products are that record, so
# this tool keeps its run at 0.3; the reader's default is not changed by it (restored afterwards).
GUARD_P_AS_RUN = 0.3


def main(argv=None):
    from lss_core import patching as _patching
    saved, _patching.GUARD_P = _patching.GUARD_P, GUARD_P_AS_RUN
    try:
        return _main(argv)
    finally:
        _patching.GUARD_P = saved


if __name__ == '__main__':
    main()
