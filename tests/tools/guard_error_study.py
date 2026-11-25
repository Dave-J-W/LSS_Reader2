"""The guard's error: which inflation makes the joint fit's error bars honest?

The local data agent's survey of 1832 real joins (``docs/studies/ref_patch_real``,
C56) found the join guard leaving the errors about 24 % too small (pull SD
1.24 [1.09, 1.40] on 1091 real split scans, against 1.00 with the guard off):
on real joins the ladder climbs to a higher order (median 5) whose χ²/dof is
about 0.8, so the inflate-only rule never widens its error, while the
unguarded order-4 fit has χ²/dof about 1.5. Its proposal: inflate the guarded
fit's error by the unguarded fit's χ², or report the larger of the two
errors. This study tests that on data with known truth (main man,
2026-11-25).

**Synthetic joins:** study A's six (``ref_guard_study``: five biased by a
fringe or a short overlap, and the covariance study's smooth first join),
each with **excess per-point scatter** of 0, 1, 2 or 3 % (each point × (1 +
X·z), z standard normal, the stated errors unchanged): the feature that makes
real per-point errors too small (C56: 16-31 % of joins at Qz ≥ 0.25 with
χ² p < 0.01) and lets the ladder fit noise.

**The error rules,** all on the rung the guard keeps at p 0.7 (the default):

- ``own``: its counting error inflated by its own χ² (today);
- ``ref``: inflated by the unguarded order-4, ±2 fit's χ² instead;
- ``both``: by the larger of the two inflations;
- ``max``: the larger of its own error and the unguarded fit's (inflated) error;
- ``guard_off``: the unguarded fit and its own inflated error (for comparison).

**Public real check:** NX school's reflectivity scans split as the survey
splits them (``ref_patch_survey.split_rows``: two interleaved halves over 8
points, the second × 0.8, truth f = 1.25).

    python tests/tools/guard_error_study.py [--out docs/studies/guard_error] [--reps 400] [--procs N]

Writes ``stats.csv``, ``nx_split.csv``, ``numbers.json`` and the figures
G1 (pull SD against the excess scatter), G2 (the error's cost, the median
error over today's) and G3 (coverage within ±1 and ±2).
"""
import argparse
import json
import math
import os
import sys
import time
import warnings
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (ROOT, HERE, os.path.join(ROOT, 'tests')) if p not in sys.path]

import ref_guard_study as A                                  # noqa: E402
from lss_core import patching, uncertainty as unc            # noqa: E402

OUT_DEFAULT = os.path.join('docs', 'studies', 'guard_error')
EXCESS = (0.0, 0.01, 0.02, 0.03)
RULES = ('own', 'ref', 'both', 'max', 'guard_off', 'budget')
LABEL = {'own': 'own χ² (today)', 'ref': 'unguarded χ²', 'both': 'larger inflation', 'max': 'larger error',
         'guard_off': 'guard off', 'budget': 'per-point budget (oracle)'}
COLOR = {'own': '#2a78d6', 'ref': '#eb6834', 'both': '#1baf7a', 'max': '#9b59b6', 'guard_off': '0.45',
         'budget': '#d4a017'}
GUARD = 0.7
NX = A.NX
SMOOTH = A.COV


def scatter(scan, x, seed, budget=False):
    """``scan`` with each point × (1 + x·z), its stated errors unchanged; with
    ``budget`` the errors widened by the true excess, √(σ² + (x·y)²) (the
    oracle per-point budget)."""
    if not x:
        return scan
    z = np.random.default_rng(seed).standard_normal(len(scan.y))
    y = scan.y * (1 + x * z)
    sig = np.sqrt(scan.sigma ** 2 + (x * scan.y) ** 2) if budget else scan.sigma
    return patching.Scan(scan.q, y, sig)


def _seed(key, rep, x, side):
    return zlib.crc32(('%s|%d|%.3f|%s' % (key, rep, x, side)).encode())


def _task(args):
    key, rep, x = args
    warnings.simplefilter('ignore')
    a, b, t, _r, _m = A.draw_join(key, rep)
    sa, sb = _seed(key, rep, x, 'a'), _seed(key, rep, x, 'b')
    tab = A.join_table(scatter(a, x, sa), scatter(b, x, sb))
    tab['truth'] = t
    tab['budget'] = A.join_table(scatter(a, x, sa, True), scatter(b, x, sb, True)) if x else None
    return tab


def rule_estimate(t, rule, p=GUARD):
    """(δ, σ) of one rule on a rung table, or None (failed)."""
    if rule == 'budget':                   # today's rule on the same data with the oracle per-point budget
        return rule_estimate(t['budget'] if t.get('budget') is not None else t, 'own', p)
    if rule == 'guard_off':
        e = A.estimate(t, 'guard_off')
        return None if e is None else e[:2]
    k, _inf = A.guard_pick(t, p)
    if k is None:
        return None
    d, ec, c2, dof = t['rungs'][k]
    own = unc.inflate(ec, c2, dof)
    ref = t['off']
    if rule == 'own' or not isinstance(ref, tuple):
        e = own
    else:
        ref_infl = unc.inflate(1.0, ref[2], ref[3])
        if rule == 'ref':
            e = ec * ref_infl
        elif rule == 'both':
            e = max(own, ec * ref_infl)
        elif rule == 'max':
            e = max(own, unc.inflate(ref[1], ref[2], ref[3]))
        else:
            raise ValueError(rule)
    return (d, e) if A._ok(d, e) else None


def run_synthetic(reps, procs, log):
    out = {}
    for x in EXCESS:
        for key in A.JOINS:
            t0 = time.time()
            tabs = A._pmap(_task, [(key, rep, x) for rep in range(reps)], procs)
            truth = [tb['truth'] for tb in tabs]
            out[(key, x)] = {r: A.stats([rule_estimate(tb, r) for tb in tabs], truth)[0] for r in RULES}
            out[(key, x)]['_climb'] = float(np.mean([(A.guard_pick(tb, GUARD)[0] or 0) > 0 for tb in tabs]))
            log('excess %.0f %%, %s: %d replicates, %.1f s' % (100 * x, key, reps, time.time() - t0))
    return out


def run_nx(log):
    """The survey's interleaved split of every NX reflectivity scan of ≥ 20 points."""
    from lss_core.experiment import Experiment
    exp = Experiment(NX)
    r = exp.reflectivity([6, 7, 8, 9], errors='budget')
    rows = []
    for n, s in zip(r.order, patching.scans_from_reflectivity(r)):
        if len(s.q) < 20:
            continue
        h = len(s.q) // 2
        ov = np.arange(h - 4, h + 4)
        ia = np.concatenate([np.arange(0, h - 4), ov[0::2]])
        ib = np.concatenate([ov[1::2], np.arange(h + 4, len(s.q))])
        a = patching.Scan(s.q[ia], s.y[ia], s.sigma[ia])
        b = patching.Scan(s.q[ib], 0.8 * s.y[ib], 0.8 * s.sigma[ib])
        t = A.join_table(a, b)
        t['truth'] = math.log(1.25)
        row = dict(scan=n, points=len(s.q))
        for rule in RULES:
            e = rule_estimate(t, rule)
            row[rule] = None if e is None else (e[0] - t['truth']) / e[1]
            row[rule + '_err'] = None if e is None else e[1]
        k, _ = A.guard_pick(t, GUARD)
        row['guard_rung'] = '%d,%d' % tuple(t['ladder'][k]) if k is not None else ''
        rows.append(row)
    log('NX split: %d scans' % len(rows))
    return rows


def figures(res, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    xs = [100 * x for x in EXCESS]
    groups = (('smooth join (covariance study)', [SMOOTH]), ('five biased joins (mean)', list(A.BIASED)))

    def series(rule, keys, field):
        return [float(np.mean([res[(k, x)][rule][field] for k in keys])) for x in EXCESS]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, (title, keys) in zip(axes, groups):
        for rule in RULES:
            ax.plot(xs, series(rule, keys, 'pull_sd'), 'o-', color=COLOR[rule], label=LABEL[rule],
                    lw=2.2 if rule == 'own' else 1.4)
        ax.axhline(1, color='k', lw=0.8)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('excess per-point scatter (%)')
    axes[0].set_ylabel('pull SD (1 = honest error bars)')
    axes[1].legend(fontsize=8, frameon=False)
    fig.suptitle('The guard\'s error: pull SD of the join factor against hidden per-point scatter (guard p 0.7)',
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'G1_pull_sd.png'), dpi=A.DPI)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, (title, keys) in zip(axes, groups):
        base = series('own', keys, 'median_err')
        for rule in RULES:
            v = series(rule, keys, 'median_err')
            ax.plot(xs, [a / b for a, b in zip(v, base)], 'o-', color=COLOR[rule], label=LABEL[rule])
        ax.axhline(1, color='k', lw=0.8)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('excess per-point scatter (%)')
    axes[0].set_ylabel('median error / today\'s')
    axes[1].legend(fontsize=8, frameon=False)
    fig.suptitle('What honesty costs: the median error of each rule over today\'s', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'G2_error_cost.png'), dpi=A.DPI)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, (title, keys) in zip(axes, groups):
        for rule in RULES:
            ax.plot(xs, series(rule, keys, 'cover1'), 'o-', color=COLOR[rule], label=LABEL[rule])
            ax.plot(xs, series(rule, keys, 'cover2'), 's--', color=COLOR[rule], ms=4, lw=0.9)
        ax.axhline(0.683, color='k', lw=0.6)
        ax.axhline(0.954, color='k', lw=0.6)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('excess per-point scatter (%)')
    axes[0].set_ylabel('coverage within ±1 (circles) and ±2 (squares)')
    axes[1].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'G3_coverage.png'), dpi=A.DPI)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=OUT_DEFAULT)
    ap.add_argument('--reps', type=int, default=400, help='replicates per join and excess (default 400)')
    ap.add_argument('--procs', type=int, default=max(1, (os.cpu_count() or 2) - 0))
    ap.add_argument('--no-nx', action='store_true', help='skip the NX school split check')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    patching.GUARD_P = GUARD          # the guard this study is about, whatever the default is at the run
    log = lambda m: print(m, flush=True)
    t0 = time.time()
    res = run_synthetic(a.reps, a.procs, log)
    import csv
    with open(os.path.join(a.out, 'stats.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['join', 'excess', 'rule', 'n', 'failed', 'mean_pull', 'pull_sd', 'cover1', 'cover2',
                    'median_err', 'rms_delta', 'guard_climbed'])
        for (key, x), d in res.items():
            for rule in RULES:
                s = d[rule]
                w.writerow([key, x, rule, s['n'], s['failed'], '%.4f' % s['mean_pull'], '%.4f' % s['pull_sd'],
                            '%.4f' % s['cover1'], '%.4f' % s['cover2'], '%.6g' % s['median_err'],
                            '%.6g' % s['rms_delta'], '%.3f' % d['_climb']])
    nx = [] if a.no_nx else run_nx(log)
    if nx:
        with open(os.path.join(a.out, 'nx_split.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(nx[0]))
            w.writeheader()
            w.writerows(nx)
    figures(res, a.out)
    summary = {}
    for rule in RULES:
        summary[rule] = {}
        for x in EXCESS:
            summary[rule]['%.2f' % x] = dict(
                smooth_pull_sd=res[(SMOOTH, x)][rule]['pull_sd'],
                biased_pull_sd=float(np.mean([res[(k, x)][rule]['pull_sd'] for k in A.BIASED])),
                biased_abs_mean_pull=float(np.mean([abs(res[(k, x)][rule]['mean_pull']) for k in A.BIASED])),
                smooth_median_err=res[(SMOOTH, x)][rule]['median_err'],
                biased_median_err=float(np.mean([res[(k, x)][rule]['median_err'] for k in A.BIASED])))
        if nx:
            p = np.array([r[rule] for r in nx if r[rule] is not None], float)
            summary[rule]['nx_split'] = dict(n=int(len(p)), rms_pull=float(np.sqrt(np.mean(p ** 2))) if len(p) else None)
    with open(os.path.join(a.out, 'numbers.json'), 'w') as f:
        json.dump(dict(reps=a.reps, guard_p=GUARD, excess=list(EXCESS), rules=list(RULES), summary=summary,
                       climb={'%s|%.2f' % k: v['_climb'] for k, v in res.items()}, seconds=round(time.time() - t0, 1)),
                  f, indent=1)
    log('done in %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
