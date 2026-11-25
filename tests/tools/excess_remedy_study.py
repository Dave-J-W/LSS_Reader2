"""C64: the joint fit's error budget with C63's measured excess (DATA_NEEDS
row 15, MQ-3), with known truth before any default changes (rule 12).

C63 measured on 384 real series: within a scan the counting σ is about
12 % small (s 1.12); between scans each point carries an extra 0.2 % of R
(Qz < 0.1), 0.4 % (0.1-0.25) or 2.65 % (≥ 0.25); and about 3 % of points
are wild (~70-90 % off). This study gives C61's six synthetic joins that
truth and asks which error budget, in the joint fit as it is today (guard
p 0.7, its own χ² inflation), gives honest join errors:

    today     the stated σ (counting and monitor)
    scale     σ × 1.12
    budget    √((1.12 σ)² + (X(Qz) y)²), C63's X by Qz class
    budgetN   the same with X keyed to each point's counts (C63's table by
              1/var(ln ratio), about counts / 2) instead of its Qz
    robust    the budget, and a Student-t (ν = 4) reweighting of each point
              by its residual from the joint fit, 4 iterations
    cauchy    the same with ν = 1, 8 iterations
    clip      the budget, and the window point furthest from the curve left
              out while it is beyond 4 σ, refitting each time (at most 6)
    clipN     clip on budgetN
    oracle    the true σ of each point and the wild points left out (the
              best attainable; not available on real data)

and, as a check of the cost, the same arms on joins with no excess at all.
Then the NX school split (real, public; the truth known by construction).

    python tests/tools/excess_remedy_study.py [--out docs/studies/excess_remedy] [--reps 400] [--procs N]

``estimate(a, b, arm)`` is the arm on any pair of scans, so the local agent
can run the arms on C56's real splits.
"""
import argparse
import csv
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
import guard_error_study as G                                # noqa: E402
from lss_core import patching                                # noqa: E402

OUT_DEFAULT = os.path.join('docs', 'studies', 'excess_remedy')
GUARD = 0.7
SCALE = 1.12                                       # C63: within a scan, s 1.12 [1.10, 1.12]
X_BINS = ((0.0, 0.10, 0.0020), (0.10, 0.25, 0.0040), (0.25, 9.0, 0.0265))   # C63 real_by.csv, pairs, core X
# the same excess keyed to the counts instead: C63's pairs by 1/var(ln ratio) (about counts / 2)
XN_BINS = ((0.0, 300.0, 0.0501), (300.0, 3000.0, 0.0270), (3000.0, 30000.0, 0.0040), (30000.0, 1e300, 0.0036))
OUTLIER_SHARE, OUTLIER_SCALE = 0.03, 0.70         # C63: 4-6 % of pair residuals wild, ~70-90 % off
NU, ITERS = 4.0, 4
ARMS = ('today', 'scale', 'scaleclip', 'budget', 'budgetN', 'robust', 'cauchy', 'clip', 'clipN', 'oracle')
CLIP_K, CLIP_MAX = 4.0, 6
CATASTROPHE = 5.0                                  # a miss beyond 5 × the oracle's median error
TRUTHS = ('c63', 'within', 'join', 'none')
# c63:    C63's between-scan numbers put on every point of both scans: the first, mistaken, reading (kept to show it)
# within: what C63's within-scan estimator measured on every point: σ × 1.12 and 0.3 % wild points (× exp(0.46 z));
#         what C56's splits (two halves of one scan) can see
# join:   within, plus the between-scan part where the pairs estimator measured it, on the later scan's overlap
#         points only: √2 X(Qz) (a pair's variance 2X², put on one side) and 5 % wild (× exp(0.73 z))
# none:   no excess (the cost of the remedies)
WITHIN_WILD, WITHIN_WILD_SCALE = 0.003, 0.46       # C63 within: 1.8 % of 6-point windows, scale 0.46
JOIN_WILD, JOIN_WILD_SCALE = 0.05, 0.73            # C63 pairs: 6 % of pair residuals, scale 0.73
LABEL = {'today': 'today (stated σ)', 'scale': 'σ × 1.12', 'budget': 'σ × 1.12 ⊕ X(Qz)',
         'budgetN': 'σ × 1.12 ⊕ X(counts)', 'clipN': 'X(counts) + 4σ clipping', 'scaleclip': 'σ × 1.12 + 4σ clipping',
         'robust': 'budget + Student-t (ν 4)', 'cauchy': 'budget + Cauchy (ν 1)', 'clip': 'budget + 4σ clipping',
         'oracle': 'oracle (true σ, wild points out)'}
COLOR = {'today': '#222222', 'scale': '#888888', 'scaleclip': '#ff9f1c', 'budget': '#2a78d6', 'budgetN': '#7fb3ea', 'robust': '#1baf7a',
         'cauchy': '#9b59b6', 'clip': '#d23', 'clipN': '#f08a8a', 'oracle': '#d4a017'}


def x_of(q):
    q = np.asarray(q, float)
    out = np.zeros_like(q)
    for lo, hi, x in X_BINS:
        out[(q >= lo) & (q < hi)] = x
    return out


def corrupt(scan, seed, truth):
    """``scan`` with C63's excess drawn into its values (stated σ unchanged): the counting part × s, the
    between-scan core X(Qz), and wild points. Returns (scan, true σ, mask of wild points)."""
    if truth == 'none':
        return scan, scan.sigma.copy(), np.zeros(len(scan.y), bool)
    rng = np.random.default_rng(seed)
    n = len(scan.y)
    extra = math.sqrt(SCALE ** 2 - 1) * scan.sigma * rng.standard_normal(n)
    core = 1 + x_of(scan.q) * rng.standard_normal(n)
    wild = rng.random(n) < OUTLIER_SHARE
    mult = np.where(wild, np.exp(OUTLIER_SCALE * rng.standard_normal(n)), 1.0)
    y = (scan.y + extra) * core * mult
    true_sigma = np.sqrt((SCALE * scan.sigma) ** 2 + (x_of(scan.q) * scan.y) ** 2)
    return patching.Scan(scan.q, y, scan.sigma), true_sigma, wild


def corrupt_pair(a, b, seed, truth):
    """Both scans of a join with ``truth``'s excess drawn in (stated σ unchanged): (a, b, (σ_a, σ_b, wild_a,
    wild_b)) with each point's true σ and the wild points."""
    if truth in ('none', 'c63'):
        ca, cb = corrupt(a, seed('a'), truth), corrupt(b, seed('b'), truth)
        return ca[0], cb[0], (ca[1], cb[1], ca[2], cb[2])
    out = []
    for side, sc in (('a', a), ('b', b)):
        rng = np.random.default_rng(seed(side))
        n = len(sc.y)
        y = sc.y + math.sqrt(SCALE ** 2 - 1) * sc.sigma * rng.standard_normal(n)
        wild = rng.random(n) < WITHIN_WILD
        mult = np.where(wild, np.exp(WITHIN_WILD_SCALE * rng.standard_normal(n)), 1.0)
        tsig = SCALE * sc.sigma
        if truth == 'join' and side == 'b':
            ov = sc.q <= a.q.max() + 1e-9                  # the later scan's points in the overlap
            xb = math.sqrt(2) * x_of(sc.q) * ov
            mult = mult * (1 + xb * rng.standard_normal(n))
            jw = ov & (rng.random(n) < JOIN_WILD)
            mult = np.where(jw, mult * np.exp(JOIN_WILD_SCALE * rng.standard_normal(n)), mult)
            wild = wild | jw
            tsig = np.sqrt(tsig ** 2 + (xb * sc.y) ** 2)
        out.append((patching.Scan(sc.q, y * mult, sc.sigma), tsig, wild))
    (ca, sa, wa), (cb, sb, wb) = out
    return ca, cb, (sa, sb, wa, wb)


def x_of_counts(scan):
    """C63's excess keyed to a point's counts: 1/var(ln ratio) of a pair of such points, 1/(2 (σ/y)²)."""
    v = 1.0 / (2.0 * np.maximum(np.asarray(scan.sigma, float) / np.abs(np.asarray(scan.y, float)), 1e-12) ** 2)
    out = np.zeros_like(v)
    for lo, hi, x in XN_BINS:
        out[(v >= lo) & (v < hi)] = x
    return out


def budget_sigma(scan, key='qz'):
    x = x_of(scan.q) if key == 'qz' else x_of_counts(scan)
    return np.sqrt((SCALE * scan.sigma) ** 2 + (x * scan.y) ** 2)


def _fit(a, b):
    f = patching.joint_factor(a, b, guard_p=GUARD)
    return f


def _residuals(a, b, f):
    """Each window point's residual from the kept rung's curve, in units of its σ (log space)."""
    rf = patching.rung_fit(a, b, f.order, f.n_ext)
    ia, ib = np.asarray(rf.ia), np.asarray(rf.ib)
    base_a = np.log(patching.fresnel(a.q[ia], patching.QC))
    base_b = np.log(patching.fresnel(b.q[ib], patching.QC))
    ra = (np.log(np.maximum(a.y[ia], 1e-300)) - base_a - rf.curve(a.q[ia])) / (a.sigma[ia] / a.y[ia])
    rb = (np.log(np.maximum(b.y[ib], 1e-300)) + rf.delta - base_b - rf.curve(b.q[ib])) / (b.sigma[ib] / b.y[ib])
    return ia, ra, ib, rb


def robust_fit(a, b, nu=NU, iters=ITERS):
    """The joint fit with each window point's σ divided by √w, w = (ν + 1)/(ν + r²) its Student-t weight
    from the previous fit's residual r: iteratively reweighted (``iters`` refits)."""
    sa, sb = a.sigma.copy(), b.sigma.copy()
    f = _fit(a, b)
    for _ in range(iters):
        aa, bb = patching.Scan(a.q, a.y, sa), patching.Scan(b.q, b.y, sb)
        try:
            ia, ra, ib, rb = _residuals(aa, bb, f)
        except (ValueError, np.linalg.LinAlgError):
            break
        wa, wb = (nu + 1) / (nu + ra ** 2), (nu + 1) / (nu + rb ** 2)
        sa, sb = a.sigma.copy(), b.sigma.copy()
        sa[ia] = a.sigma[ia] / np.sqrt(np.minimum(wa, 1.0))       # only ever widen, never shrink, a point
        sb[ib] = b.sigma[ib] / np.sqrt(np.minimum(wb, 1.0))
        f = _fit(patching.Scan(a.q, a.y, sa), patching.Scan(b.q, b.y, sb))
    return f


def clip_fit(a, b, k=CLIP_K, most=CLIP_MAX, masks=False):
    """The joint fit with the window point furthest from the curve left out while it lies beyond ``k`` σ,
    refitting each time (at most ``most`` points out)."""
    ka, kb = np.ones(len(a.y), bool), np.ones(len(b.y), bool)
    f = None
    for _ in range(most + 1):
        aa = patching.Scan(a.q[ka], a.y[ka], a.sigma[ka])
        bb = patching.Scan(b.q[kb], b.y[kb], b.sigma[kb])
        f = _fit(aa, bb)
        try:
            ia, ra, ib, rb = _residuals(aa, bb, f)
        except (ValueError, np.linalg.LinAlgError):
            break
        ja, jb = np.flatnonzero(ka)[ia], np.flatnonzero(kb)[ib]
        worst_a = np.max(np.abs(ra)) if len(ra) else 0.0
        worst_b = np.max(np.abs(rb)) if len(rb) else 0.0
        if max(worst_a, worst_b) < k:
            break
        if worst_a >= worst_b:
            ka[ja[int(np.argmax(np.abs(ra)))]] = False
        else:
            kb[jb[int(np.argmax(np.abs(rb)))]] = False
    return (f, ka, kb) if masks else f


def estimate(a, b, arm, true=None):
    """(δ, σ) of one arm on scans a and b (``true``: (σ_a, σ_b, wild_a, wild_b) for the oracle)."""
    try:
        if arm == 'today':
            f = _fit(a, b)
        elif arm == 'scale':
            f = _fit(patching.Scan(a.q, a.y, SCALE * a.sigma), patching.Scan(b.q, b.y, SCALE * b.sigma))
        elif arm == 'scaleclip':
            f = clip_fit(patching.Scan(a.q, a.y, SCALE * a.sigma), patching.Scan(b.q, b.y, SCALE * b.sigma))
        elif arm == 'budget':
            f = _fit(patching.Scan(a.q, a.y, budget_sigma(a)), patching.Scan(b.q, b.y, budget_sigma(b)))
        elif arm == 'budgetN':
            f = _fit(patching.Scan(a.q, a.y, budget_sigma(a, 'counts')), patching.Scan(b.q, b.y, budget_sigma(b, 'counts')))
        elif arm == 'clipN':
            f = clip_fit(patching.Scan(a.q, a.y, budget_sigma(a, 'counts')), patching.Scan(b.q, b.y, budget_sigma(b, 'counts')))
        elif arm == 'robust':
            f = robust_fit(patching.Scan(a.q, a.y, budget_sigma(a)), patching.Scan(b.q, b.y, budget_sigma(b)))
        elif arm == 'cauchy':
            f = robust_fit(patching.Scan(a.q, a.y, budget_sigma(a)), patching.Scan(b.q, b.y, budget_sigma(b)), 1.0, 8)
        elif arm == 'clip':
            f = clip_fit(patching.Scan(a.q, a.y, budget_sigma(a)), patching.Scan(b.q, b.y, budget_sigma(b)))
        elif arm == 'oracle':
            sa, sb, wa, wb = true
            ka, kb = ~wa, ~wb
            f = _fit(patching.Scan(a.q[ka], a.y[ka], sa[ka]), patching.Scan(b.q[kb], b.y[kb], sb[kb]))
        else:
            raise ValueError(arm)
    except (ValueError, np.linalg.LinAlgError):
        return None
    return (f.delta, f.err) if A._ok(f.delta, f.err) else None


def task(args):
    key, rep, truth = args
    warnings.simplefilter('ignore')
    patching.GUARD_P = GUARD
    a0, b0, t, _r, _m = A.draw_join(key, rep)
    seed = lambda side: zlib.crc32(('%s|%d|%s|%s' % (key, rep, truth, side)).encode())
    a, b, true = corrupt_pair(a0, b0, seed, truth)
    return dict(key=key, rep=rep, truth=truth, t=t, **{arm: estimate(a, b, arm, true) for arm in ARMS})


def stats(rows):
    out = []
    for truth in TRUTHS:
        for key in A.JOINS:
            sel = [r for r in rows if r['truth'] == truth and r['key'] == key]
            med_today = np.median([r['today'][1] for r in sel if r['today']])
            med_oracle = np.median([r['oracle'][1] for r in sel if r['oracle']])
            for arm in ARMS:
                est = [r[arm] for r in sel]
                p = np.array([(e[0] - r['t']) / e[1] for e, r in zip(est, sel) if e is not None])
                errs = np.array([e[1] for e in est if e is not None])
                dev = np.array([e[0] - r['t'] for e, r in zip(est, sel) if e is not None])
                out.append(dict(truth=truth, join=key, smooth=key == G.SMOOTH, arm=arm, n=len(p),
                                pull_sd=float(np.std(p, ddof=1)), mean_pull=float(np.mean(p)),
                                cover1=float(np.mean(np.abs(p) < 1)), cover2=float(np.mean(np.abs(p) < 2)),
                                err_ratio=float(np.median(errs) / med_today),
                                mad_oracle=float(np.median(np.abs(dev)) / med_oracle),
                                rms_oracle=float(np.sqrt(np.mean(dev ** 2)) / med_oracle),
                                catastrophic=float(np.mean(np.abs(dev) > CATASTROPHE * med_oracle))))
    return out


def run_nx():
    """The survey's interleaved split of every NX scan of ≥ 20 points (``guard_error_study.run_nx``), each arm."""
    from lss_core.experiment import Experiment
    r = Experiment(G.NX).reflectivity([6, 7, 8, 9], errors='budget')
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
        t = math.log(1.25)
        row = dict(scan=n, points=len(s.q))
        for arm in ARMS[:-1]:
            e = estimate(a, b, arm)
            row[arm + '_pull'] = None if e is None else (e[0] - t) / e[1]
            row[arm + '_err'] = None if e is None else e[1]
        rows.append(row)
    return rows


def write_csv(path, rows):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def figures(st, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    joins = list(A.JOINS)
    titles = {'c63': 'C63\'s between-scan numbers on every point (the first, mistaken reading)',
              'within': 'within a scan, as measured: σ × 1.12, 0.3 % wild points (what splits see)',
              'join': 'within, plus the between-scan part on the later scan\'s overlap points',
              'none': 'no excess at all (what the remedies cost)'}
    w = 0.08
    for name, key, ylab, ylim in (('E1_pull_sd.png', 'pull_sd', 'pull SD (1: honest)', (0, 1.6)),
                                  ('E2_tails.png', 'catastrophic', 'share of misses beyond 5 × the oracle\'s error',
                                   None)):
        fig, axes = plt.subplots(2, 2, figsize=(13, 7.5), sharey=True)
        for ax, truth in zip(axes.ravel(), TRUTHS):
            for i, arm in enumerate(ARMS):
                v = [next(r[key] for r in st if r['truth'] == truth and r['join'] == k and r['arm'] == arm)
                     for k in joins]
                ax.bar(np.arange(len(joins)) + (i - 4.5) * w, v, w, color=COLOR[arm], label=LABEL[arm])
            if key == 'pull_sd':
                ax.axhline(1, color='k', lw=0.8)
            if ylim:
                ax.set_ylim(*ylim)
            ax.set_xticks(range(len(joins)))
            ax.set_xticklabels([k.replace(':', '\njoin ') for k in joins], fontsize=6)
            ax.set_title(titles[truth], fontsize=8)
            ax.set_ylabel(ylab, fontsize=8)
        axes[0, 0].legend(fontsize=6, frameon=False, ncol=2)
        fig.suptitle('%s. %s, C61\'s six joins, 400 replicates each' % (
            name[:2], 'Which error budget gives honest join errors' if key == 'pull_sd'
            else 'The misses the pull SD hides'), fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(out, name), dpi=A.DPI)
        plt.close(fig)


def example(out, key=None, reps=400, truth='join', mode='rescue', name='E3_one_join.png'):
    """One join fitted today and with 4σ clipping: the points, both curves and the residuals. ``mode``
    'rescue' (E3): the first replicate where today misses by more than CATASTROPHE oracle errors and
    clipping (on the budget) by less than 1.5; 'failure' (E4): the first where clipping on σ × 1.12 alone
    misses by more than 6 of its own errors (it removed good points)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    key = key or G.SMOOTH
    for rep in range(reps):
        a0, b0, t, _r, _m = A.draw_join(key, rep)
        seed = lambda side: zlib.crc32(('%s|%d|%s|%s' % (key, rep, truth, side)).encode())
        a, b, true = corrupt_pair(a0, b0, seed, truth)
        sa, sb, wa, wb = true
        o = estimate(a, b, 'oracle', true)
        ft = _fit(a, b)
        if mode == 'rescue':
            ab, bb = patching.Scan(a.q, a.y, budget_sigma(a)), patching.Scan(b.q, b.y, budget_sigma(b))
        else:
            ab, bb = patching.Scan(a.q, a.y, SCALE * a.sigma), patching.Scan(b.q, b.y, SCALE * b.sigma)
        try:
            fc, ka, kb = clip_fit(ab, bb, masks=True)
        except (ValueError, np.linalg.LinAlgError):
            continue
        ia, ib = np.asarray(ft.ia), np.asarray(ft.ib)
        if not o:
            continue
        if mode == 'rescue' and abs(ft.delta - t) > CATASTROPHE * o[1] and abs(fc.delta - t) < 1.5 * o[1] and \
                (wa[ia].any() or wb[ib].any()):
            break
        if mode == 'failure' and abs(fc.delta - t) > 6 * fc.err:
            break
    else:
        return None
    fig = plt.figure(figsize=(11, 5.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1.3], hspace=0.08)
    info = {}
    for col, (title, aa, bb, f, keep_a, keep_b) in enumerate((
            ('today: stated σ, every point (δ off by %.1f oracle errors)' % (abs(ft.delta - t) / o[1]), a, b, ft,
             np.ones(len(a.y), bool), np.ones(len(b.y), bool)),
            ('%s, 4σ clipping (δ off by %.1f oracle errors, %.1f of its own)'
             % ('σ × 1.12 ⊕ X(Qz)' if mode == 'rescue' else 'σ × 1.12 alone', abs(fc.delta - t) / o[1],
                abs(fc.delta - t) / fc.err), ab, bb, fc, ka, kb))):
        ax = fig.add_subplot(gs[0, col])
        rax = fig.add_subplot(gs[1, col], sharex=ax)
        A2, B2 = patching.Scan(aa.q[keep_a], aa.y[keep_a], aa.sigma[keep_a]), \
            patching.Scan(bb.q[keep_b], bb.y[keep_b], bb.sigma[keep_b])
        rf = patching.rung_fit(A2, B2, f.order, f.n_ext)
        ja, jb = np.asarray(rf.ia), np.asarray(rf.ib)
        qa, qb = A2.q[ja], B2.q[jb]
        la = np.log(A2.y[ja] / patching.fresnel(qa, patching.QC))
        lb = np.log(B2.y[jb] * math.exp(rf.delta) / patching.fresnel(qb, patching.QC))
        ea, eb = A2.sigma[ja] / A2.y[ja], B2.sigma[jb] / B2.y[jb]
        ax.errorbar(qa, la, ea, fmt='o', ms=4, color='#2a78d6', label='scan a')
        ax.errorbar(qb, lb, eb, fmt='s', ms=4, color='#eb6834', label='scan b × the fitted factor')
        qq = np.linspace(min(qa.min(), qb.min()), max(qa.max(), qb.max()), 200)
        ax.plot(qq, rf.curve(qq), 'k-', lw=1.1)
        wild_a = np.flatnonzero(wa)
        wild_b = np.flatnonzero(wb)
        for idx, sc, isb in [(i, a, False) for i in wild_a] + [(i, b, True) for i in wild_b]:
            if min(qa.min(), qb.min()) - 1e-9 <= sc.q[idx] <= max(qa.max(), qb.max()) + 1e-9:
                yv = np.log(sc.y[idx] * (math.exp(rf.delta) if isb else 1.0) / patching.fresnel(sc.q[idx], patching.QC))
                ax.plot(sc.q[idx], yv, 'x', ms=12, mew=2, color='#d23', label='a wild point (the truth knows)')
        if col == 1:
            for msk, sc, isb in ((~ka, a, False), (~kb, b, True)):
                for idx in np.flatnonzero(msk):
                    yv = np.log(sc.y[idx] * (math.exp(rf.delta) if isb else 1.0) / patching.fresnel(sc.q[idx], patching.QC))
                    ax.plot(sc.q[idx], yv, 'o', ms=13, mfc='none', mec='#1baf7a', mew=1.5, label='left out by clipping')
        h, lab = ax.get_legend_handles_labels()
        seen = {}
        for hh, ll in zip(h, lab):
            seen.setdefault(ll, hh)
        ax.legend(seen.values(), seen.keys(), fontsize=7, frameon=False)
        ax.set_title(title, fontsize=9)
        ax.set_ylabel('ln(R / R_F)')
        ax.tick_params(labelbottom=False)
        rax.axhline(0, color='k', lw=0.6)
        rax.plot(qa, (la - rf.curve(qa)) / ea, 'o', ms=3, color='#2a78d6')
        rax.plot(qb, (lb - rf.curve(qb)) / eb, 's', ms=3, color='#eb6834')
        rax.set_ylabel('residual / σ')
        rax.set_xlabel('Qz (Å⁻¹)')
        info['today' if col == 0 else 'clip'] = dict(delta=f.delta, err=f.err, chi2_dof=f.chi2 / max(f.dof, 1),
                                                     rung=[f.order, f.n_ext])
    fig.suptitle('%s. One join (%s, replicate %d, truth \'%s\')%s: true δ %.4f, the oracle %.4f ± %.4f'
                 % (name[:2], key, rep, truth, ' with a wild point' if mode == 'rescue'
                    else ': clipping removes good points', t, o[0], o[1]), fontsize=9)
    fig.savefig(os.path.join(out, name), dpi=A.DPI, bbox_inches='tight')
    plt.close(fig)
    return dict(join=key, rep=rep, truth_model=truth, mode=mode, truth=t, oracle=list(o), **info,
                wild_in_window=int(wa[ia].sum() + wb[ib].sum()), left_out=int((~ka).sum() + (~kb).sum()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=OUT_DEFAULT)
    ap.add_argument('--reps', type=int, default=400)
    ap.add_argument('--procs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--no-nx', action='store_true', help='without the NX school split')
    o = ap.parse_args(argv)
    os.makedirs(o.out, exist_ok=True)
    patching.GUARD_P = GUARD
    warnings.simplefilter('ignore')
    t0 = time.time()
    rows = A._pmap(task, [(k, r, tr) for tr in TRUTHS for k in A.JOINS for r in range(o.reps)], o.procs)
    st = stats(rows)
    write_csv(os.path.join(o.out, 'stats.csv'), st)
    nx = [] if o.no_nx else run_nx()
    if nx:
        write_csv(os.path.join(o.out, 'nx_split.csv'), nx)
    summ = {}
    for truth in TRUTHS:
        for arm in ARMS:
            sm = [r for r in st if r['truth'] == truth and r['arm'] == arm and r['smooth']]
            bi = [r for r in st if r['truth'] == truth and r['arm'] == arm and not r['smooth']]
            summ['%s/%s' % (truth, arm)] = dict(smooth_pull_sd=sm[0]['pull_sd'],
                                                biased_pull_sd=float(np.mean([r['pull_sd'] for r in bi])),
                                                smooth_err_ratio=sm[0]['err_ratio'],
                                                biased_err_ratio=float(np.median([r['err_ratio'] for r in bi])),
                                                smooth_cover1=sm[0]['cover1'],
                                                biased_cover1=float(np.mean([r['cover1'] for r in bi])),
                                                rms_oracle=[r['rms_oracle'] for r in sm + bi],
                                                catastrophic=float(np.mean([r['catastrophic'] for r in sm + bi])))
    nums = dict(reps=o.reps, seconds=round(time.time() - t0, 1), scale=SCALE, x_bins=X_BINS,
                outliers=[OUTLIER_SHARE, OUTLIER_SCALE], nu=NU, iters=ITERS, summary=summ,
                nx_rms_pull={arm: float(np.sqrt(np.mean([r[arm + '_pull'] ** 2 for r in nx
                                                          if r[arm + '_pull'] is not None])))
                             for arm in ARMS[:-1]} if nx else None)
    with open(os.path.join(o.out, 'numbers.json'), 'w') as f:
        json.dump(nums, f, indent=1)
    figures(st, o.out)
    nums['example'] = example(o.out)
    nums['failure'] = example(o.out, mode='failure', name='E4_clipping_fails.png')
    with open(os.path.join(o.out, 'numbers.json'), 'w') as f:
        json.dump(nums, f, indent=1)
    print(json.dumps(nums, indent=1))


if __name__ == '__main__':
    main()
