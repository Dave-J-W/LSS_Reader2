"""Study A of the two-decisions plan (docs/studies/2026-11-24_two_decisions_plan.md,
"Study A"): how strict the joint fit's guard should be at a reflectivity
join, with figures. The guard (``patching.joint_factor``) tries the rungs
of ``patching.guard_ladder`` (order, points either side) and keeps the
first whose χ² p-value is at least ``guard_p`` (0.3 today). C45 found that
this post-selection widens the pulls of a smooth join (SD 1.13) while a
lower p makes the joins biased by the curve model worse.

    python tests/tools/ref_guard_study.py [--out docs/studies/reflectivity_guard] [--replicates 400]
        [--figures A1,A2,A3,A4,A5,A6,A7,A8,R] [--a7-seeds 200] [--r-replicates 800] [--quick] [--procs 4]

**Choices compared** at each join (δ = ln f, f multiplies scan b):
- ``legacy``: ``stitching.fitted_factor`` (as the gauntlet);
- ``guard_p0.3`` (today's default), ``guard_p0.1``, ``guard_p0.03``,
  ``guard_p0.01``; A5 sweeps p over 0.001 … 0.9 (0.7 and 0.9 added by Main, 2026-11-24, after p 0.5 led the robustness map; R and RS, the map on staggered grids, also carry p 0.5, 0.7 and 0.9);
- ``guard_off``: order 4, 2 points either side, no ladder (``guard_p=0``;
  the error still inflate-only by √(χ²/dof), as ``joint_factor``);
- ``average``: a candidate only, never a default. Every rung of the
  ladder's largest window that fits is weighted by Akaike weights from
  AICc = χ² + 2K + 2K(K+1)/(n−K−1), K = order + 2 (the coefficients and
  δ), n the points of the window: w_k ∝ exp(−ΔAICc_k/2). Then
  δ̄ = Σ w_k δ_k and σ² = Σ w_k (σ_k² + (δ_k − δ̄)²): Burnham & Anderson
  2002 (eq. 6.12), the revised form of Buckland et al. 1997 (Burnham &
  Anderson, *Model Selection and Multimodel Inference*, 2nd ed., p. 345;
  Buckland, Burnham & Augustin 1997, Biometrics 53:603). σ_k is the error
  the rung reports (inflate-only). Only the largest window's rungs are
  weighed: a smaller window is fitted to fewer points, so its χ² is not a
  likelihood of the same data (the next window is used only when no rung
  of the largest one fits). For comparison only (data_summary.md):
  ``average_sqrt``, the same weights with Buckland et al.'s own form
  σ = Σ w_k √(σ_k² + (δ_k − δ̄)²) (never larger); ``average_all``, every
  rung of every window weighed by its own AICc.

**Efficiency.** For every replicate each rung of the ladder is fitted once
(``patching.rung_fit``) and (δ_k, σ_k, χ²_k, dof_k) kept; every guard p
and the average follow from the stored rungs without refitting. The
selection is checked against ``joint_factor`` itself on the first
replicates of every join (exact equality, reported).

**Data and seeds** (synthetic and public only):
- the five joins C45 found biased (layer_dppc j3, layer_film150 j2,
  overlap_3_staggered j3, overlap_6 j1, scans_5 j2) drawn with the
  gauntlet's conditions and seeds (``ref_patch_gauntlet.replicate``, seed
  1000·(rep+1) + 7919·ci), and the covariance study's first join (25 Å
  film, NX-like plan, the owner's monitor, seeds 0 … N−1), so that C45's
  numbers come back exactly first (checked against
  docs/comparisons_data/ref_patch_biased_joins/joins.csv);
- A7: the downstream fit of the covariance study (NX-like plan, 25 Å film,
  ``lss_core.gls`` with the full covariance), seeds 0 … 199;
- A8: the public NX school file, scans 6–9, with the calibrated foils;
- R: a 150 Å film (±3/8 of a fringe at the join, four phases), three scans
  from ``xs.chain_plan`` with the join at Qz ≈ 0.2 Å⁻¹, the coarser scan's
  step set for about 3, 4, 6 and 10 points per Kiessig period, flux ×1,
  ×0.1, ×0.01; seed 7 000 000 + 100 000·cell + 10 000·phase + rep; 800
  replicates per cell (200 per phase). The criterion is √(mean over the
  phases of (pull mean² + (pull SD − 1)²)/2); how firmly a cell's best
  choice wins is the share of 200 bootstrap resamples it wins.

**Figures** (PNG, dpi 150, each with the CSV behind it): A1 what the fit
sees; A2 pull histograms (and A2_qq); A3 noise-free bias; A4 the guard's
rung choices; A5 the decision curve; A6 coverage; A7 thickness and
roughness downstream; A8 NX school joins beside the foil ratio; R the
robustness map (R_winner, R_pull_sd). ``data_summary.md`` holds every
number, the command line and run times.
"""
import argparse
import csv
import math
import os
import sys
import time
import warnings
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for p in (ROOT, os.path.join(ROOT, 'tests'), os.path.join(ROOT, 'tests', 'tools')):
    if p not in sys.path:
        sys.path.insert(0, p)

from scipy.stats import chi2 as C2, norm                       # noqa: E402

from lss_core import patching, stitching, uncertainty as unc   # noqa: E402
from synthetic import xrr, xrr_scans as xs                     # noqa: E402
import ref_patch_gauntlet as gauntlet                          # noqa: E402
import ref_patch_biased_joins as biased                        # noqa: E402

OUT_DEFAULT = os.path.join('docs', 'studies', 'reflectivity_guard')
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
C45_CSV = os.path.join(ROOT, 'docs', 'comparisons_data', 'ref_patch_biased_joins', 'joins.csv')
FIGURES = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'R', 'RS')
QC = patching.QC
N_EXT = patching.N_EXT
COV = 'covariance_first_join'
JOINS = tuple(biased.JOINS) + (COV,)
BIASED = tuple(biased.JOINS)
COV_TRUTH = biased.COV_TRUTH
GUARD_PS = (0.001, 0.003, 0.01, 0.03, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9)
CHOICES = ('legacy', 'guard_p0.3', 'guard_p0.1', 'guard_p0.03', 'guard_p0.01', 'guard_off', 'average')
ALL_CHOICES = (CHOICES + tuple('guard_p%g' % p for p in GUARD_PS if 'guard_p%g' % p not in CHOICES)
               + ('average_sqrt', 'average_all'))
LABEL = {'legacy': 'legacy', 'guard_p0.3': 'p 0.3 (default)', 'guard_p0.1': 'p 0.1', 'guard_p0.03': 'p 0.03',
         'guard_p0.01': 'p 0.01', 'guard_off': 'guard off', 'average': 'AICc average', 'guard_p0.5': 'p 0.5', 'guard_p0.7': 'p 0.7', 'guard_p0.9': 'p 0.9',
         'average_sqrt': 'AICc average, Buckland\'s σ', 'average_all': 'AICc average, all windows'}
# categorical slots in a fixed order (the dataviz reference palette, light mode); legacy a neutral grey
COLOR = {'guard_p0.3': '#2a78d6', 'guard_p0.1': '#eb6834', 'guard_p0.03': '#1baf7a', 'guard_p0.01': '#eda100',
         'guard_off': '#e87ba4', 'average': '#008300', 'legacy': '#8a8984', 'guard_p0.5': '#7b5cc4', 'guard_p0.7': '#4d3a8c', 'guard_p0.9': '#2b1f52'}
MARK = {'legacy': 's', 'guard_p0.3': 'o', 'guard_p0.1': 'o', 'guard_p0.03': 'o', 'guard_p0.01': 'o',
        'guard_off': 'D', 'average': '^', 'guard_p0.5': 'o', 'guard_p0.7': 'o', 'guard_p0.9': 'o'}
SHORT = {'layer_dppc:3': 'layer_dppc j3', 'layer_film150:2': 'layer_film150 j2',
         'overlap_3_staggered:3': 'overlap_3_staggered j3', 'overlap_6:1': 'overlap_6 j1', 'scans_5:2': 'scans_5 j2',
         COV: 'covariance j1 (smooth)'}
A1_TYPES = (('smooth', COV), ('fringe', 'layer_dppc:3'), ('staggered', 'overlap_3_staggered:3'))
A7_CHOICES = ('guard_p0.3', 'guard_off', 'guard_p0.01', 'average', 'legacy')
# the robustness map also has p 0.5, the one setting A5 shows close to p 0.3 (Main, 2026-11-24)
R_CHOICES = CHOICES + ('guard_p0.5', 'guard_p0.7', 'guard_p0.9')
R_PPF = (3, 4, 6, 10)
R_FLUX = (1.0, 0.1, 0.01)
R_D0 = 150.0
R_Q0 = 0.2
R_PHASES = 4
R_GRID = 'coincide'      # 'staggered' for the RS map (no Qz shared by the two scans; Main, 2026-11-24)
DPI = 150


# ------------------------------------------------------------------ drawing the joins

_DESIGNED = None


def designed():
    global _DESIGNED
    if _DESIGNED is None:
        _DESIGNED = biased.designed()
    return _DESIGNED


def draw_join(key, rep, expected=False):
    """(scan a, scan b, true δ, ReducedScans, m) of join ``key`` at replicate
    ``rep`` (``expected``: noise-free), with C45's conditions and seeds."""
    if key == COV:
        bl, prof, m = xs.Beamline(**xs.REAL_MONITOR), xrr.film(*COV_TRUTH), 1
        if expected:
            r = xs.measure(prof, xs.nx_like_plan(), beamline=bl, errors='counting+monitor', expected=True)
        else:
            r = xs.measure(prof, xs.nx_like_plan(), beamline=bl, seed=rep, errors='counting+monitor')
    else:
        name, m = key.split(':')
        m = int(m)
        conds = designed()
        ci, cond = list(conds).index(name), conds[name]
        if expected:
            r = xs.measure(cond.profile, cond.plan(), beamline=cond.beamline, resolution=cond.resolution,
                           errors='counting+monitor', expected=True)
        else:
            r = gauntlet.replicate(cond, 1000 * (rep + 1) + 7919 * ci)[0]
    sc = biased.scans_of(r)
    t = math.log(list(r.true_steps().values())[m - 1])
    return sc[m - 1], sc[m], t, r, m


# ------------------------------------------------------------------ the rung table and the choices

def _rung(a, b, o, e):
    """(δ, counting error, χ², dof) of one rung; None where joint_factor
    would skip it (ValueError, LinAlgError, not finite); 'raise' where it
    would raise."""
    try:
        r = patching.rung_fit(a, b, o, e)
    except (ValueError, np.linalg.LinAlgError):
        return None
    except Exception:
        return 'raise'
    if not (np.isfinite(r.delta) and np.isfinite(r.err_counting) and np.isfinite(r.chi2)):
        return None
    return (r.delta, r.err_counting, r.chi2, int(r.dof))


def _legacy(a, b):
    try:
        f, e = stitching.fitted_factor(np.column_stack([a.q, a.y, a.sigma]), np.column_stack([b.q, b.y, b.sigma]))
        return (math.log(f), e / f)
    except Exception:
        return None


def join_table(a, b):
    """Every rung of the ladder fitted once, the guard-off fit and the legacy factor."""
    ladder = patching.guard_ladder(a, b, 4, N_EXT)
    rungs = [_rung(a, b, o, e) for o, e in ladder]
    off = rungs[0] if ladder[0] == (4, N_EXT) else _rung(a, b, 4, N_EXT)
    return dict(ladder=[tuple(x) for x in ladder], rungs=rungs, off=off, legacy=_legacy(a, b))


def _p(r):
    return float(C2.sf(r[2], r[3])) if r[3] > 0 else 1.0


def guard_pick(t, p):
    """(rung index, inflated) that ``joint_factor(guard_p=p)`` keeps;
    (None, None) where it fails."""
    best, bp = None, None
    for k, r in enumerate(t['rungs']):
        if r is None:
            continue
        if r == 'raise':
            return None, None
        pv = _p(r)
        if pv >= p:
            return k, False
        if best is None or pv > bp:
            best, bp = k, pv
    return (best, True) if best is not None else (None, None)


def _ok(d, e):
    return d is not None and np.isfinite(d) and np.isfinite(e) and e > 0


def average(t, all_windows=False, sqrt_form=False):
    """(δ̄, σ, {rung index: weight}) of the AICc average (module docstring):
    σ by Burnham & Anderson 2002 (eq. 6.12), the revised form of Buckland
    et al. 1997, or with ``sqrt_form`` Buckland et al.'s own; None when no
    rung fits."""
    rows = [(k, r) for k, r in enumerate(t['rungs']) if isinstance(r, tuple)]
    if not rows:
        return None
    if not all_windows:
        e0 = t['ladder'][rows[0][0]][1]
        rows = [(k, r) for k, r in rows if t['ladder'][k][1] == e0]
    aicc, d, s = [], [], []
    for k, (dk, ec, c2, dof) in rows:
        K = t['ladder'][k][0] + 2
        n = dof + K
        aicc.append(c2 + 2 * K + 2 * K * (K + 1) / max(n - K - 1, 1e-9))
        d.append(dk)
        s.append(unc.inflate(ec, c2, dof))
    aicc, d, s = np.array(aicc), np.array(d), np.array(s)
    w = np.exp(-0.5 * (aicc - aicc.min()))
    w /= w.sum()
    db = float(np.sum(w * d))
    if sqrt_form:
        sig = float(np.sum(w * np.sqrt(s ** 2 + (d - db) ** 2)))
    else:
        sig = float(math.sqrt(np.sum(w * (s ** 2 + (d - db) ** 2))))
    return db, sig, {k: float(wk) for (k, _), wk in zip(rows, w)}


def estimate(t, choice):
    """(δ, σ, rung index or None, inflated) of one choice, or None (failed)."""
    if choice == 'legacy':
        lg = t['legacy']
        return (lg[0], lg[1], None, False) if lg is not None and _ok(*lg) else None
    if choice == 'guard_off':
        r = t['off']
        if not isinstance(r, tuple):
            return None
        e = unc.inflate(r[1], r[2], r[3])
        return (r[0], e, 0 if t['ladder'][0] == (4, N_EXT) else None, False) if _ok(r[0], e) else None
    if choice.startswith('average'):
        a = average(t, choice == 'average_all', choice == 'average_sqrt')
        return (a[0], a[1], None, False) if a is not None and _ok(a[0], a[1]) else None
    p = float(choice[len('guard_p'):])
    k, inf = guard_pick(t, p)
    if k is None:
        return None
    r = t['rungs'][k]
    e = unc.inflate(r[1], r[2], r[3])
    return (r[0], e, k, inf) if _ok(r[0], e) else None


# ------------------------------------------------------------------ parallel work

def _pmap(func, tasks, procs, chunk=8):
    if procs <= 1 or len(tasks) < 2 * chunk:
        return [func(t) for t in tasks]
    import multiprocessing as mp
    with mp.get_context('fork').Pool(procs) as pool:
        return list(pool.imap(func, tasks, chunksize=chunk))


def _join_task(args):
    key, rep = args
    warnings.simplefilter('ignore')
    a, b, t, r, m = draw_join(key, rep)
    tab = join_table(a, b)
    tab['truth'] = t
    return tab


def check_selection(key, reps):
    """Exact equality of the stored-rung selection with ``joint_factor``
    over the p sweep and the guard off: (cases, mismatches)."""
    n = bad = 0
    for rep in reps:
        a, b, _, _, _ = draw_join(key, rep)
        t = join_table(a, b)
        for p in GUARD_PS + (0,):
            mine = estimate(t, 'guard_p%g' % p if p else 'guard_off')
            try:
                j = patching.joint_factor(a, b, guard_p=p)
                ref = (j.delta, j.err) if _ok(j.delta, j.err) else None
            except Exception:
                ref = None
            n += 1
            if (mine is None) != (ref is None) or (mine is not None and (mine[0] != ref[0] or mine[1] != ref[1])):
                bad += 1
    return n, bad


# ------------------------------------------------------------------ statistics

def stats(est, truth):
    """Pull statistics of a list of estimates (None for failures)."""
    v = np.array([(d - t, e) for x, t in zip(est, truth) if x is not None for d, e in [x[:2]]]).reshape(-1, 2)
    pulls = v[:, 0] / v[:, 1] if len(v) else np.zeros(0)
    n = len(v)
    return dict(n=n, failed=len(est) - n,
                mean_pull=float(pulls.mean()) if n else math.nan,
                pull_sd=float(pulls.std(ddof=1)) if n > 1 else math.nan,
                bias_delta=float(v[:, 0].mean()) if n else math.nan,
                rms_delta=float(np.sqrt(np.mean(v[:, 0] ** 2))) if n else math.nan,
                median_err=float(np.median(v[:, 1])) if n else math.nan,
                cover1=float(np.mean(np.abs(pulls) < 1)) if n else math.nan,
                cover2=float(np.mean(np.abs(pulls) < 2)) if n else math.nan), pulls


def _boot(pulls, f, n_boot=500, seed=12345):
    rng = np.random.default_rng(seed)
    n = len(pulls)
    return float(np.std([f(pulls[rng.integers(0, n, n)]) for _ in range(n_boot)], ddof=1)) if n > 2 else math.nan


def six_joins(n_rep, procs, log, check=True):
    """Rung tables of every join and replicate, the noise-free tables and
    the selection check."""
    out = {}
    for key in JOINS:
        t0 = time.time()
        tabs = _pmap(_join_task, [(key, rep) for rep in range(n_rep)], procs)
        a, b, t, r, m = draw_join(key, 0, expected=True)
        nf = join_table(a, b)
        nf['truth'] = t
        chk = check_selection(key, range(min(10, n_rep))) if check else (0, 0)
        out[key] = dict(tabs=tabs, noise_free=nf, check=chk, seconds=time.time() - t0)
        log('%s: %d replicates, %.1f s; selection check %d cases, %d mismatches'
            % (key, n_rep, time.time() - t0, chk[0], chk[1]))
    return out


def summarise(data, choices=ALL_CHOICES, n_cov=None, n_gauntlet=None):
    """{join: {choice: stats}} with the noise-free bias in median errors and
    the noise-free rung; ``n_*`` restrict the replicates (the C45 check)."""
    res, pulls = {}, {}
    for key, d in data.items():
        nmax = n_cov if key == COV else n_gauntlet
        tabs = d['tabs'][:nmax] if nmax else d['tabs']
        truth = [t['truth'] for t in tabs]
        res[key], pulls[key] = {}, {}
        for c in choices:
            est = [estimate(t, c) for t in tabs]
            s, pl = stats(est, truth)
            nf = estimate(d['noise_free'], c)
            s['noise_free_bias'] = ((nf[0] - d['noise_free']['truth']) / s['median_err']
                                    if nf is not None and s['median_err'] > 0 else math.nan)
            k = nf[2] if nf is not None else None
            if c == 'guard_off':
                s['noise_free_order'], s['noise_free_n_ext'] = 4, N_EXT
            elif k is not None:
                s['noise_free_order'], s['noise_free_n_ext'] = d['noise_free']['ladder'][k]
            else:
                s['noise_free_order'], s['noise_free_n_ext'] = '', ''
            res[key][c], pulls[key][c] = s, pl
    return res, pulls


def c45_check(data):
    """C45's committed numbers (default, guard_off, guard_0.01) against the
    stored-rung reproduction, field by field at the CSV's precision."""
    if not os.path.isfile(C45_CSV):
        return None, ['C45 CSV not found']
    if any(len(data[k]['tabs']) < 400 for k in BIASED) or len(data[COV]['tabs']) < 300:
        return None, ['fewer than 400 replicates (300 seeds): not checked']
    res, _ = summarise(data, ('guard_p0.3', 'guard_off', 'guard_p0.01'), n_cov=300, n_gauntlet=400)
    name = {'default': 'guard_p0.3', 'guard_off': 'guard_off', 'guard_0.01': 'guard_p0.01'}
    fields = ('n', 'failed', 'mean_pull', 'pull_sd', 'bias_delta', 'rms_delta', 'median_err', 'noise_free_bias',
              'noise_free_order', 'noise_free_n_ext')
    n = 0
    diffs = []
    with open(C45_CSV) as f:
        for row in csv.DictReader(f):
            if row['variant'] not in name:
                continue
            mine = res[row['join']][name[row['variant']]]
            for fl in fields:
                v = mine[fl]
                s = '%.6g' % v if isinstance(v, float) else str(v)
                n += 1
                if s != row[fl]:
                    diffs.append('%s %s %s: C45 %s, now %s' % (row['join'], row['variant'], fl, row[fl], s))
    return n, diffs


# ------------------------------------------------------------------ CSV and plotting helpers

def write_csv(path, rows, fmt='%.6g'):
    if not rows:
        return
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (fmt % v if isinstance(v, float) else v) for k, v in r.items()})


def _plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 9, 'axes.titlesize': 9, 'axes.labelsize': 9, 'legend.fontsize': 8,
                         'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': False,
                         'savefig.facecolor': 'white'})
    return plt


def _save(fig, out, name):
    fig.savefig(os.path.join(out, name + '.png'), dpi=DPI, metadata={'Software': None})
    import matplotlib.pyplot as plt
    plt.close(fig)


def _f(x, fmt='%.2f'):
    try:
        return fmt % x if np.isfinite(x) else '—'
    except TypeError:
        return str(x)


def _rung_label(t, k, inflated=False):
    o, e = t['ladder'][k]
    return 'o%d ±%d%s' % (o, e, ' (none adequate)' if inflated else '')


# ------------------------------------------------------------------ A1: what the fit sees

def fig_a1(out, n_show=6):
    plt = _plt()
    fig, axes = plt.subplots(3, n_show, figsize=(2.9 * n_show, 9.2), sharey='row')
    rows = []
    for i, (kind, key) in enumerate(A1_TYPES):
        for j in range(n_show):
            ax = axes[i, j]
            a, b, truth, r, m = draw_join(key, j)
            t = join_table(a, b)
            est = estimate(t, 'guard_p0.3')
            k, inf = guard_pick(t, 0.3)
            o, e = t['ladder'][k]
            rf = patching.rung_fit(a, b, o, e)
            off = patching.rung_fit(a, b, 4, N_EXT)
            lo, hi = float(b.q.min()), float(a.q.max())
            ia2, ib2 = patching.window(a.q, b.q, N_EXT)          # the largest window: the same x range in a row
            w0, w1 = float(min(a.q[ia2].min(), b.q[ib2].min())), float(max(a.q[ia2].max(), b.q[ib2].max()))
            q_own = np.concatenate([a.q[rf.ia], b.q[rf.ib]])
            pad = 0.25 * (w1 - w0)
            ax.axvspan(lo, hi, color='#e8e6df', zorder=0, lw=0)
            sa = r.scans[r.order[m - 1]].scale
            qq = np.linspace(w0 - pad, w1 + pad, 300)
            tr = np.log(r.truth(qq) / sa / patching.fresnel(qq))
            ax.plot(qq, tr, color='#0b0b0b', lw=1.0, label='truth')
            qf = np.linspace(w0, w1, 200)
            ax.plot(qf, off.curve(qf), color=COLOR['guard_off'], lw=1.2, ls='--', label='guard off (o4 ±2)')
            qf = np.linspace(q_own.min(), q_own.max(), 200)
            ax.plot(qf, rf.curve(qf), color=COLOR['guard_p0.3'], lw=2.0, label='p 0.3 (default): chosen rung')
            fb = math.exp(est[0])
            for sc, idx, col, scale, lab in ((a, rf.ia, '#52514e', 1.0, 'scan a'), (b, rf.ib, '#eb6834', fb,
                                                                                    r'scan b $\times\,\hat f$')):
                sel = (sc.q >= w0 - pad) & (sc.q <= w1 + pad) & (sc.y > 0)
                inwin = np.zeros(len(sc.q), bool)
                inwin[idx] = True
                yy = np.log(sc.y * scale / patching.fresnel(sc.q))
                ee = sc.sigma / np.abs(sc.y)
                ax.errorbar(sc.q[sel & inwin], yy[sel & inwin], ee[sel & inwin], fmt='o', ms=4, color=col, lw=0.8,
                            capsize=0, label=lab, zorder=3)
                ax.plot(sc.q[sel & ~inwin], yy[sel & ~inwin], 'o', ms=4, mfc='none', mec=col, mew=0.8, zorder=3)
            pull = (est[0] - truth) / est[1]
            ax.text(0.03, 0.04, '%s, p=%.2f\npull %+.2f' % (_rung_label(t, k, inf), _p(t['rungs'][k]), pull),
                    transform=ax.transAxes, fontsize=8, va='bottom',
                    bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='#c3c2b7', lw=0.6))
            ax.set_xlim(w0 - pad, w1 + pad)
            if j == 0:
                ax.set_ylabel('%s join: %s\nln(R/R_F), scan a\'s scale' % (kind, SHORT[key].replace(' (smooth)', '')))
            if i == 2:
                ax.set_xlabel('Qz (Å⁻¹)')
            ax.set_title('replicate %d' % j)
            rows.append(dict(join_type=kind, join=key, replicate=j, order=o, n_ext=e, inflated=inf,
                             p_chi2=_p(t['rungs'][k]), delta=est[0], err=est[1], truth=truth, pull=pull,
                             off_delta=off.delta, overlap_lo=lo, overlap_hi=hi,
                             coef=';'.join('%.8g' % c for c in rf.coef), centre=rf.centre, half_width=rf.half_width))
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc='upper center', ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.suptitle('What the fit sees: the default\'s chosen polynomial in ln(R/R_F) near the overlap (shaded); '
                 'open points lie outside the fit\'s window', y=0.965, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, out, 'A1_what_the_fit_sees')
    write_csv(os.path.join(out, 'A1_what_the_fit_sees.csv'), rows)
    return rows


# ------------------------------------------------------------------ A2: pull histograms and QQ

def fig_a2(out, res, pulls):
    plt = _plt()
    fig, axes = plt.subplots(len(JOINS), len(CHOICES), figsize=(2.05 * len(CHOICES), 1.75 * len(JOINS)),
                             sharex=True)
    xg = np.linspace(-5, 5, 200)
    bins = np.linspace(-5, 5, 41)
    rows = []
    for i, key in enumerate(JOINS):
        for j, c in enumerate(CHOICES):
            ax = axes[i, j]
            pl = pulls[key][c]
            s = res[key][c]
            outside = int(np.sum(np.abs(pl) > 5))
            ax.hist(np.clip(pl, -4.99, 4.99), bins=bins, density=True, color=COLOR[c], alpha=0.85, lw=0)
            ax.plot(xg, norm.pdf(xg), color='#0b0b0b', lw=0.9)
            ax.text(0.03, 0.95, 'mean %+.2f\nSD %.2f%s' % (s['mean_pull'], s['pull_sd'],
                                                           '\n%d beyond ±5' % outside if outside else ''),
                    transform=ax.transAxes, fontsize=7, va='top')
            ax.set_yticks([])
            ax.set_xlim(-5, 5)
            if i == 0:
                ax.set_title(LABEL[c])
            if j == 0:
                ax.set_ylabel(SHORT[key].replace(' (', '\n('), fontsize=8)
            if i == len(JOINS) - 1:
                ax.set_xlabel(r'pull $(\hat\delta - \delta)/\hat\sigma$')
            rows.append(dict(join=key, choice=c, n=s['n'], failed=s['failed'], mean_pull=s['mean_pull'],
                             pull_sd=s['pull_sd'], beyond_5=outside))
    fig.suptitle('Pulls per join (rows) and choice (columns), %d replicates; black: N(0, 1)'
                 % len(pulls[JOINS[0]]['guard_p0.3']), fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    _save(fig, out, 'A2_pull_histograms')
    write_csv(os.path.join(out, 'A2_pull_histograms.csv'), rows)
    # every pull, for later figures
    prow = []
    for key in JOINS:
        for c in CHOICES:
            for r_, v in enumerate(pulls[key][c]):
                prow.append(dict(join=key, choice=c, index=r_, pull=float(v)))
    write_csv(os.path.join(out, 'A2_pulls_all.csv'), prow)
    # QQ
    fig, axes = plt.subplots(2, 3, figsize=(10.5, 7), sharex=True, sharey=True)
    for ax, key in zip(axes.flat, JOINS):
        for c, ms in (('guard_p0.3', 6), ('guard_off', 4), ('average', 2.5)):       # sizes: coinciding sets stay visible
            pl = np.sort(pulls[key][c])
            n = len(pl)
            th = norm.ppf((np.arange(1, n + 1) - 0.5) / n)
            ax.plot(th, pl, '.', ms=ms, color=COLOR[c], label='%s (SD %.2f)' % (LABEL[c], res[key][c]['pull_sd']))
        ax.plot([-3.5, 3.5], [-3.5, 3.5], color='#0b0b0b', lw=0.8)
        ax.set_title(SHORT[key])
        ax.legend(loc='upper left', frameon=False, fontsize=7)
        ax.set_xlim(-3.5, 3.5)
        ax.set_ylim(-5, 5)
    for ax in axes[1]:
        ax.set_xlabel('N(0, 1) quantile')
    for ax in axes[:, 0]:
        ax.set_ylabel('pull quantile')
    fig.suptitle('Pull quantiles against N(0, 1): the default, the guard off and the AICc average', fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save(fig, out, 'A2_qq')


# ------------------------------------------------------------------ A3: noise-free bias

def fig_a3(out, res):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.axvspan(-1, 1, color='#efeee9', lw=0, zorder=0)
    ax.axvline(0, color='#c3c2b7', lw=0.8, zorder=0)
    rows = []
    offs = np.linspace(-0.3, 0.3, len(CHOICES))
    for i, key in enumerate(JOINS):
        for o, c in zip(offs, CHOICES):
            s = res[key][c]
            v = s['noise_free_bias']
            ax.plot(np.clip(v, -3, 3), i + o, MARK[c], color=COLOR[c], ms=7, mec='white', mew=0.8,
                    label=LABEL[c] if i == 0 else None)
            if abs(v) > 3:
                ax.annotate('%+.1f' % v, (np.clip(v, -3, 3), i + o), fontsize=7, xytext=(4, -3),
                            textcoords='offset points')
            rows.append(dict(join=key, choice=c, noise_free_bias=v, median_err=s['median_err'],
                             noise_free_order=s['noise_free_order'], noise_free_n_ext=s['noise_free_n_ext']))
    ax.set_yticks(range(len(JOINS)))
    ax.set_yticklabels([SHORT[k] for k in JOINS])
    ax.invert_yaxis()
    ax.set_xlim(-3.2, 3.2)
    ax.set_xlabel(r'noise-free bias $(\hat\delta - \delta)$ / median $\hat\sigma$ (errors); shaded: ±1')
    ax.set_title('Model bias: each choice fitted to noise-free scans (no noise, no selection by noise)')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=8, ncol=4)
    fig.tight_layout()
    _save(fig, out, 'A3_noise_free_bias')
    write_csv(os.path.join(out, 'A3_noise_free_bias.csv'), rows)
    return rows


# ------------------------------------------------------------------ A4: rung choices

def rung_choices(data, p):
    out = {}
    for key in JOINS:
        d = data[key]
        acc = defaultdict(list)
        for t in d['tabs']:
            est = estimate(t, 'guard_p%g' % p)
            if est is None:
                continue
            acc[(t['ladder'][est[2]], est[3])].append((est[0] - t['truth']) / est[1])
        tot = sum(len(v) for v in acc.values())
        out[key] = sorted([dict(order=k[0][0], n_ext=k[0][1], inflated=k[1], share=len(v) / tot,
                                mean_pull=float(np.mean(v)), pull_sd=float(np.std(v, ddof=1)) if len(v) > 1 else math.nan,
                                n=len(v)) for k, v in acc.items()],
                          key=lambda r: (-r['n_ext'], r['inflated'], r['order']))
    return out


def fig_a4(out, data):
    plt = _plt()
    from matplotlib import cm, colors
    import matplotlib
    cmap = matplotlib.colormaps['RdBu_r']
    nrm = colors.Normalize(-1.5, 1.5)
    ps = (0.3, 0.01)
    ch = {p: rung_choices(data, p) for p in ps}
    fig, ax = plt.subplots(figsize=(11, 5.6))
    width = 0.38
    rows = []
    for i, key in enumerate(JOINS):
        for jp, p in enumerate(ps):
            x = i + (jp - 0.5) * (width + 0.04)
            bottom = 0.0
            for r in ch[p][key]:
                ax.bar(x, r['share'], width, bottom=bottom, color=cmap(nrm(r['mean_pull'])), edgecolor='white',
                       lw=1.0, hatch='///' if r['inflated'] else None)
                if r['share'] >= 0.06:
                    ax.text(x, bottom + r['share'] / 2, 'o%d ±%d' % (r['order'], r['n_ext']), ha='center',
                            va='center', fontsize=6.5, color='white' if abs(r['mean_pull']) > 0.8 else '#0b0b0b')
                bottom += r['share']
                rows.append(dict(join=key, guard_p=p, **r))
            ax.text(x, 1.01, 'p %g' % p, ha='center', va='bottom', fontsize=7)
    ax.set_xticks(range(len(JOINS)))
    ax.set_xticklabels([SHORT[k].replace(' (', '\n(') for k in JOINS], fontsize=8)
    ax.set_ylabel('share of replicates')
    ax.set_ylim(0, 1.07)
    sm = cm.ScalarMappable(norm=nrm, cmap=cmap)
    cb = fig.colorbar(sm, ax=ax, pad=0.01)
    cb.set_label('mean pull of the replicates that chose this rung')
    ax.set_title('What the guard chooses: rung shares per join at p 0.3 (left bar) and p 0.01 (right bar); '
                 'hatched: no rung adequate, the best one inflated')
    fig.tight_layout()
    _save(fig, out, 'A4_rung_choices')
    write_csv(os.path.join(out, 'A4_rung_choices.csv'), rows)
    return rows


# ------------------------------------------------------------------ A5: the decision curve

def decision_points(res, pulls):
    rows = []
    for c in ['guard_p%g' % p for p in GUARD_PS] + ['guard_off', 'legacy', 'average']:
        x = res[COV][c]['pull_sd']
        y = float(np.mean([abs(res[k][c]['mean_pull']) for k in BIASED]))
        xe = _boot(pulls[COV][c], lambda v: np.std(v, ddof=1))
        # bootstrap of the mean |mean pull|: each join resampled on its own
        rng = np.random.default_rng(54321)
        ys = []
        for _ in range(500):
            ys.append(np.mean([abs(np.mean(pulls[k][c][rng.integers(0, len(pulls[k][c]), len(pulls[k][c]))]))
                               for k in BIASED]))
        # paired with the guard off (the same replicates): the difference of the first join's pull SDs
        a_, b_ = pulls[COV][c], pulls[COV]['guard_off']
        if len(a_) == len(b_) and len(a_) > 2:
            rng = np.random.default_rng(97531)
            dd = []
            for _ in range(500):
                ix = rng.integers(0, len(a_), len(a_))
                dd.append(np.std(a_[ix], ddof=1) - np.std(b_[ix], ddof=1))
            dse = float(np.std(dd, ddof=1))
        else:
            dse = math.nan
        rows.append(dict(choice=c, first_join_pull_sd=x, first_join_pull_sd_se=xe, biased_mean_abs_pull_mean=y,
                         biased_mean_abs_pull_mean_se=float(np.std(ys, ddof=1)),
                         biased_mean_pull_sd=float(np.mean([res[k][c]['pull_sd'] for k in BIASED])),
                         first_join_sd_minus_off=x - res[COV]['guard_off']['pull_sd'], first_join_sd_minus_off_se=dse,
                         replicates=len(pulls[COV][c])))
    return rows


def fig_a5(out, res, pulls, prec=None):
    """The decision curve from the figure's replicates and, when given, the
    precision run's (``prec``: decision_points rows), drawn as the main curve."""
    plt = _plt()
    rows = decision_points(res, pulls)
    write_csv(os.path.join(out, 'A5_decision_curve.csv'), rows)
    fig, ax = plt.subplots(figsize=(8.4, 6.0))
    ax.axvline(1.0, color='#c3c2b7', lw=0.8, zorder=0)
    XMAX, YMAX = 1.25, 0.75
    sets = [(rows, prec is None)] + ([(prec, True)] if prec is not None else [])
    for rr, main in sets:
        by = {r['choice']: r for r in rr}
        gp = [by['guard_p%g' % p] for p in GUARD_PS]
        alpha = 1.0 if main else 0.4
        n = rr[0]['replicates']
        ax.plot([r['first_join_pull_sd'] for r in gp], [r['biased_mean_abs_pull_mean'] for r in gp],
                '-' if main else '--', color=COLOR['guard_p0.3'], lw=1.2, alpha=alpha, zorder=1,
                label='guard p sweep, %d replicates per join%s' % (n, '' if main else ' (C45\'s seeds; A2–A6)'))
        for p, r in zip(GUARD_PS, gp):
            today = p == patching.GUARD_P
            ax.errorbar(r['first_join_pull_sd'], r['biased_mean_abs_pull_mean'], xerr=r['first_join_pull_sd_se'],
                        yerr=r['biased_mean_abs_pull_mean_se'], fmt='o', ms=(10 if today else 6) * (1 if main else 0.8),
                        color=COLOR['guard_p0.3'], alpha=alpha, mec='#0b0b0b' if today else 'white',
                        mew=1.4 if today else 0.8, elinewidth=0.6, capsize=0, zorder=3)
            if main:
                ax.annotate('p %g%s' % (p, ' (today)' if today else ''),
                            (r['first_join_pull_sd'], r['biased_mean_abs_pull_mean']), xytext=(7, 4),
                            textcoords='offset points', fontsize=8, fontweight='bold' if today else None)
        for c in ('guard_off', 'average', 'legacy'):
            r = by[c]
            x, y = min(r['first_join_pull_sd'], XMAX - 0.01), min(r['biased_mean_abs_pull_mean'], YMAX - 0.01)
            ax.errorbar(x, y, xerr=r['first_join_pull_sd_se'], yerr=r['biased_mean_abs_pull_mean_se'], fmt=MARK[c],
                        ms=8 if main else 6, color=COLOR[c], alpha=alpha, mec='white', mew=0.8, elinewidth=0.6,
                        capsize=0, zorder=3)
            if main:
                clip = '' if (x, y) == (r['first_join_pull_sd'], r['biased_mean_abs_pull_mean']) else \
                    ' (off the axes: %.2f, %.2f)' % (r['first_join_pull_sd'], r['biased_mean_abs_pull_mean'])
                ax.annotate(LABEL[c] + clip + '\nbiased joins\' pull SD %.2f' % r['biased_mean_pull_sd'], (x, y),
                            xytext={'guard_off': (-9, -3), 'average': (-9, 8)}.get(c, (-9, -12)),
                            textcoords='offset points', fontsize=8, ha='right')
    if prec is not None:
        ax.text(0.99, 0.02, 'The shift between the two curves is sampling: the first %d seeds of the smooth join\n'
                'give pull SDs above the later ones (data_summary.md, A5)' % rows[0]['replicates'],
                transform=ax.transAxes, ha='right', va='bottom', fontsize=7.5, color='#52514e')
    ax.set_xlim(0.85, XMAX)
    ax.set_ylim(0.0, YMAX)
    ax.legend(loc='upper right', frameon=False, fontsize=8)
    ax.set_xlabel('pull SD at the smooth first join (covariance study; ideal 1)')
    ax.set_ylabel('mean |pull mean| over the five biased joins (ideal 0)')
    ax.set_title('The decision curve: the guard\'s p from 0.001 to 0.9 (bars: ±1 bootstrap SE)')
    fig.tight_layout()
    _save(fig, out, 'A5_decision_curve')
    return rows


# ------------------------------------------------------------------ A6: coverage

def fig_a6(out, res, pulls):
    plt = _plt()
    groups = ['pooled'] + list(JOINS)
    rows = []
    fig, axes = plt.subplots(1, len(groups), figsize=(2.2 * len(groups), 4.0), sharey=True)
    x = np.arange(len(CHOICES))
    for ax, g in zip(axes, groups):
        c1, c2 = [], []
        for c in CHOICES:
            pl = np.concatenate([pulls[k][c] for k in JOINS]) if g == 'pooled' else pulls[g][c]
            a, b = float(np.mean(np.abs(pl) < 1)), float(np.mean(np.abs(pl) < 2))
            c1.append(a)
            c2.append(b)
            rows.append(dict(group=g, choice=c, n=len(pl), share_lt1=a, share_lt2=b))
        ax.bar(x, c2, 0.75, color=[COLOR[c] for c in CHOICES], alpha=0.35, lw=0, label='|pull| < 2')
        ax.bar(x, c1, 0.75, color=[COLOR[c] for c in CHOICES], lw=0, label='|pull| < 1')
        ax.axhline(0.683, color='#0b0b0b', lw=0.8, ls='--')
        ax.axhline(0.954, color='#0b0b0b', lw=0.8, ls=':')
        ax.set_xticks(x)
        ax.set_xticklabels([LABEL[c] for c in CHOICES], rotation=70, fontsize=7, ha='right')
        ax.set_title(SHORT.get(g, 'pooled, six joins').replace(' (', '\n('), fontsize=8)
        ax.set_ylim(0, 1.02)
    axes[0].set_ylabel('share of replicates: dark |pull| < 1, light |pull| < 2\n(dashed 68.3 %, dotted 95.4 %)')
    fig.suptitle('Coverage of the reported errors', fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    _save(fig, out, 'A6_coverage')
    write_csv(os.path.join(out, 'A6_coverage.csv'), rows)
    return rows


# ------------------------------------------------------------------ A7: downstream thickness and roughness

A7_CASES = {
    'nx25': dict(name='A7_downstream', what='25 Å film, NX-like plan (the covariance study)',
                 truth=COV_TRUTH),
    'film150': dict(name='A7b_downstream_film150',
                    what='150 Å film, the gauntlet\'s layer_film150 (biased join j2)',
                    truth=(150.0, xrr.FILM_RHO, xrr.SIGMA_WATER)),
}


def _a7_task(args):
    """One seed of the downstream fit: each choice's joins chained, stitched,
    finished and fitted with the full covariance (as covariance_pulls)."""
    case, seed = args
    warnings.simplefilter('ignore')
    from lss_core import covariance_export as ce, gls
    truth = np.array(A7_CASES[case]['truth'])
    if case == 'nx25':
        bl, res_ = xs.Beamline(**xs.REAL_MONITOR), None
        r = xs.measure(xrr.film(*truth), xs.nx_like_plan(), beamline=bl, seed=seed, errors='counting+monitor')
    else:
        conds = designed()
        ci, cond = list(conds).index('layer_film150'), conds['layer_film150']
        bl, res_ = cond.beamline, cond.resolution
        r = gauntlet.replicate(cond, 1000 * (seed + 1) + 7919 * ci)[0]
    sc = biased.scans_of(r)
    tabs = [join_table(sc[m - 1], sc[m]) for m in range(1, len(sc))]
    wl = bl.wavelength

    def model(q, d, rho, sig):
        return xrr.film(d, rho, sig).reflectivity(q, wl, res_)
    out = {}
    for c in A7_CHOICES:
        est = [estimate(t, c) for t in tabs]
        if any(e is None for e in est):
            out[c] = None
            continue
        phi, S = unc.steps_to_phi([e[0] for e in est], np.diag([e[1] ** 2 for e in est]))
        st = patching.PatchResult(phi, S, [], c).stitch(sc, merge='coincident')
        cd = ce.from_stitched(st, ['S%s' % k for k in r.order], {'method': c})
        try:
            ref, _ = ce.finish(cd, QC, 0.0, None, False)
            f = gls.fit(gls.load(ce.sidecar_dict(ref)), model, truth * [1.02, 0.99, 1.03])
            out[c] = (list(map(float, f.params)), list(map(float, f.errors)), float(f.chi2 / f.dof))
        except Exception:
            out[c] = None
    return out


def fig_a7(out, seeds, procs, log, case='nx25'):
    plt = _plt()
    t0 = time.time()
    spec = A7_CASES[case]
    res = _pmap(_a7_task, [(case, s_) for s_ in range(seeds)], procs, chunk=4)
    log('%s: %d seeds, %.1f s' % (spec['name'], seeds, time.time() - t0))
    truth = np.array(spec['truth'])
    rows, every = [], []
    vals = {}
    for c in A7_CHOICES:
        v = [x for x in res if x[c] is not None]
        P = np.array([x[c][0] for x in v])
        E = np.array([x[c][1] for x in v])
        X = np.array([x[c][2] for x in v])
        vals[c] = P
        row = dict(case=case, choice=c, seeds=seeds, failed=seeds - len(v))
        for i, nm in enumerate(('d', 'rho', 'sigma')):
            dv = P[:, i] - truth[i]
            row['bias_' + nm] = float(dv.mean())
            row['sd_' + nm] = float(dv.std(ddof=1))
            row['rms_' + nm] = float(np.sqrt(np.mean(dv ** 2)))
            row['pull_mean_' + nm] = float(np.mean(dv / E[:, i]))
            row['pull_sd_' + nm] = float(np.std(dv / E[:, i], ddof=1))
        row['chi2_dof'] = float(X.mean())
        rows.append(row)
    for s, x in enumerate(res):
        for c in A7_CHOICES:
            if x[c] is not None:
                every.append(dict(seed=s, choice=c, d=x[c][0][0], rho=x[c][0][1], sigma=x[c][0][2],
                                  d_err=x[c][1][0], rho_err=x[c][1][1], sigma_err=x[c][1][2], chi2_dof=x[c][2]))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    by = {r['choice']: r for r in rows}
    for ax, i, nm, unit in ((axes[0], 0, 'd', 'thickness'), (axes[1], 2, 'sigma', 'roughness')):
        data = [vals[c][:, i] - truth[i] for c in A7_CHOICES]
        parts = ax.violinplot(data, showextrema=False, widths=0.8)
        for b, c in zip(parts['bodies'], A7_CHOICES):
            b.set_facecolor(COLOR[c])
            b.set_alpha(0.55)
            b.set_edgecolor('none')
        for k, c in enumerate(A7_CHOICES, start=1):
            r = by[c]
            ax.errorbar(k, r['bias_' + nm], yerr=r['sd_' + nm], fmt='o', color='#0b0b0b', ms=4, capsize=3, lw=1)
            ax.text(k, 0.98, 'bias %+.4f\nSD %.4f' % (r['bias_' + nm], r['sd_' + nm]), ha='center', va='top',
                    fontsize=7, transform=ax.get_xaxis_transform())
        ax.axhline(0, color='#c3c2b7', lw=0.8)
        ax.set_xticks(range(1, len(A7_CHOICES) + 1))
        ax.set_xticklabels([LABEL[c] for c in A7_CHOICES], fontsize=8)
        ax.set_ylabel('fitted %s − truth (Å)' % unit)
        ax.set_title('%s (truth %.2f Å)' % (unit, truth[i]))
        lo = min(np.min(dv) for dv in data)
        hi = max(np.max(dv) for dv in data)
        ax.set_ylim(lo - 0.05 * (hi - lo), hi + 0.25 * (hi - lo))
    fig.suptitle('Downstream fit (%s; full covariance, %d seeds): mean ± SD in black' % (spec['what'], seeds),
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, out, spec['name'])
    write_csv(os.path.join(out, spec['name'] + '.csv'), rows)
    write_csv(os.path.join(out, spec['name'] + '_seeds.csv'), every, '%.10g')
    return rows


# ------------------------------------------------------------------ A8: NX school

def nx_joins():
    from lss_core import absorbers, reflectivity as refl
    from lss_core.experiment import Experiment
    exp = Experiment(NX)
    r = exp.reflectivity([6, 7, 8, 9], errors='budget')
    order = r.order
    sc = patching.scans_from_reflectivity(r, order)
    meta = []
    for n in order:
        p, cols = exp.scans[n].parameters, exp.scans[n].columns
        meta.append(dict(scan=n, absorber=p.get('Absorber'),
                         energy=absorbers.energy_kev(p['Wavelength']) if p.get('Wavelength') else None,
                         monc=cols.get('Monc'), monp=cols.get('Monp'), qz=cols.get('L')))
    foils = absorbers.calibrated(meta[0]['energy'])
    rows = []
    for m in range(1, len(sc)):
        a, b = sc[m - 1], sc[m]
        ma, mb = meta[m - 1], meta[m]
        q_lo = float(b.q.min())
        ratio, rel = foils.step(ma['absorber'], mb['absorber'], qz=q_lo)
        mon = refl.monitor_change(ma['qz'], ma['monc'], ma['monp'], mb['qz'], mb['monc'], mb['monp'])
        t = join_table(a, b)
        for c in CHOICES:
            est = estimate(t, c)
            row = dict(join=m, scan_a=order[m - 1], scan_b=order[m], absorber_a=ma['absorber'],
                       absorber_b=mb['absorber'], q_lo=q_lo, q_hi=float(a.q.max()), monc_monp_ratio=mon,
                       foil_ratio=ratio, foil_rel_err=rel, choice=c)
            if est is not None:
                z = (est[0] - math.log(ratio)) / math.hypot(est[1], rel)
                row.update(factor=math.exp(est[0]), factor_err=math.exp(est[0]) * est[1], delta=est[0], err=est[1],
                           rung=_rung_label(t, est[2], est[3]) if est[2] is not None else '',
                           z_vs_foil=z, within_1=abs(z) < 1, within_2=abs(z) < 2,
                           foil_applies=mon is not None and abs(mon - 1) < refl.MONITOR_TOLERANCE)
            rows.append(row)
    return rows


def fig_a8(out):
    plt = _plt()
    rows = nx_joins()
    joins = sorted({r['join'] for r in rows})
    fig, axes = plt.subplots(1, len(joins), figsize=(4.2 * len(joins), 4.2), sharey=True)
    for ax, m in zip(axes, joins):
        rr = [r for r in rows if r['join'] == m]
        r0 = rr[0]
        rel = r0['foil_rel_err']
        ax.axvspan(-200 * rel, 200 * rel, color='#efeee9', lw=0)
        ax.axvspan(-100 * rel, 100 * rel, color='#dcdad2', lw=0)
        ax.axvline(0, color='#0b0b0b', lw=0.8)
        for i, r in enumerate(rr):
            if 'factor' not in r:
                continue
            x = 100 * (r['factor'] / r['foil_ratio'] - 1)
            xe = 100 * r['factor_err'] / r['foil_ratio']
            ax.errorbar(x, i, xerr=xe, fmt=MARK[r['choice']], color=COLOR[r['choice']], ms=7, mec='white', mew=0.8,
                        capsize=0, lw=1.2)
            ax.annotate('%.5f ± %.5f%s' % (r['factor'], r['factor_err'], ('  ' + r['rung']) if r['rung'] else ''),
                        (x, i), xytext=(0, 6), textcoords='offset points', fontsize=6.5, ha='center')
        ax.set_yticks(range(len(rr)))
        ax.set_yticklabels([LABEL[r['choice']] for r in rr])
        ax.invert_yaxis()
        applies = r0['monc_monp_ratio'] is not None and abs(r0['monc_monp_ratio'] - 1) < 0.03
        ax.set_title('join %d: S#%d → S#%d, absorbers %d → %d\nfoil ratio %.4f ± %.2f %%; Monc/Monp ×%.3f%s'
                     % (m, r0['scan_a'], r0['scan_b'], r0['absorber_a'], r0['absorber_b'], r0['foil_ratio'],
                        100 * rel, r0['monc_monp_ratio'], '' if applies else '\n(slits changed: foils not independent)'),
                     fontsize=8)
        ax.set_xlabel('factor / foil ratio − 1 (%); shaded ±1, ±2 foil σ')
    fig.suptitle('NX school 20260923, scans 6–9: each join\'s factor under each choice beside the calibrated foil ratio',
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _save(fig, out, 'A8_nx_school')
    write_csv(os.path.join(out, 'A8_nx_school.csv'), rows)
    return rows


# ------------------------------------------------------------------ R: robustness map

def r_cell(ip, iflux, phase):
    """(profile, plan, beamline, points per fringe) of one cell and phase."""
    period = 2 * math.pi / R_D0
    step = period / R_PPF[ip]
    plan = xs.chain_plan([(0.01, 0.04, 0.0025), (0.0, R_Q0, step / 2), (0.0, 0.45, step)], overlap=4, grid=R_GRID)
    q_mid = float(np.mean(plan[1].qz[-4:]))
    d = R_D0 + (phase + 0.5 - R_PHASES / 2) / R_PHASES * (2 * math.pi / q_mid)
    bl = xs.Beamline(flux=gauntlet.FLUX * R_FLUX[iflux], **xs.REAL_MONITOR)
    return xrr.film(d), plan, bl, 2 * math.pi / d / step, d


def _r_task(args):
    ip, iflux, phase, rep, expected = args
    warnings.simplefilter('ignore')
    prof, plan, bl, ppf, d = r_cell(ip, iflux, phase)
    cell = ip * len(R_FLUX) + iflux
    if expected:
        r = xs.measure(prof, plan, beamline=bl, errors='counting+monitor', expected=True)
    else:
        r = xs.measure(prof, plan, beamline=bl, seed=7000000 + 100000 * cell + 10000 * phase + rep,
                       errors='counting+monitor')
    sc = biased.scans_of(r)
    tab = join_table(sc[1], sc[2])
    tab['truth'] = math.log(list(r.true_steps().values())[1])
    est = {c: estimate(tab, c) for c in R_CHOICES}
    return dict(truth=tab['truth'], est=est)


def _win_share(by, ip, ifl, n_boot=200, seed=2468):
    """Share of bootstrap resamples (replicates resampled within each phase,
    the same draw for every choice) in which each choice has the smallest
    criterion: how firmly the cell's winner wins."""
    rng = np.random.default_rng(seed + 31 * ip + ifl)
    P = []                                    # per phase: (n, choices) pulls, NaN where a fit failed
    for ph in range(R_PHASES):
        reps = by[(ip, ifl, ph)]
        P.append(np.array([[(x['est'][c][0] - x['truth']) / x['est'][c][1] if x['est'][c] is not None else np.nan
                            for c in R_CHOICES] for x in reps]))
    wins = Counter()
    for _ in range(n_boot):
        crit = np.zeros(len(R_CHOICES))
        for M in P:
            S = M[rng.integers(0, len(M), len(M))]
            crit += np.nanmean(S, axis=0) ** 2 + (np.nanstd(S, axis=0, ddof=1) - 1) ** 2
        crit = np.where(np.isfinite(crit), crit, np.inf)
        wins[R_CHOICES[int(np.argmin(crit))]] += 1
    return {c: wins[c] / n_boot for c in R_CHOICES}


def robustness(n_per_cell, procs, log):
    t0 = time.time()
    per_phase = max(1, n_per_cell // R_PHASES)
    tasks = [(ip, ifl, ph, rep, False) for ip in range(len(R_PPF)) for ifl in range(len(R_FLUX))
             for ph in range(R_PHASES) for rep in range(per_phase)]
    res = _pmap(_r_task, tasks, procs, chunk=16)
    nf = _pmap(_r_task, [(ip, ifl, ph, 0, True) for ip in range(len(R_PPF)) for ifl in range(len(R_FLUX))
                         for ph in range(R_PHASES)], procs, chunk=4)
    log('R: %d replicates (%d per phase), %.1f s' % (len(tasks), per_phase, time.time() - t0))
    by = defaultdict(list)
    for t, r in zip(tasks, res):
        by[t[:3]].append(r)
    nfb = {(ip, ifl, ph): r for (ip, ifl, ph, _, _), r in
           zip([(ip, ifl, ph, 0, True) for ip in range(len(R_PPF)) for ifl in range(len(R_FLUX))
                for ph in range(R_PHASES)], nf)}
    phase_rows, cell_rows = [], []
    for ip in range(len(R_PPF)):
        for ifl in range(len(R_FLUX)):
            crit = defaultdict(list)
            sds = defaultdict(list)
            means = defaultdict(list)
            ppfs = []
            for ph in range(R_PHASES):
                prof, plan, bl, ppf, d = r_cell(ip, ifl, ph)
                ppfs.append(ppf)
                reps = by[(ip, ifl, ph)]
                truth = [x['truth'] for x in reps]
                for c in R_CHOICES:
                    s, _ = stats([x['est'][c] for x in reps], truth)
                    n0 = nfb[(ip, ifl, ph)]['est'][c]
                    nfbias = (n0[0] - nfb[(ip, ifl, ph)]['truth']) / s['median_err'] if n0 is not None else math.nan
                    phase_rows.append(dict(ppf_target=R_PPF[ip], flux=R_FLUX[ifl], phase=ph, thickness=d, ppf=ppf,
                                           choice=c, noise_free_bias=nfbias, **s))
                    crit[c].append(s['mean_pull'] ** 2 + (s['pull_sd'] - 1) ** 2)
                    sds[c].append(s['pull_sd'])
                    means[c].append(s['mean_pull'])
            rms = {c: float(math.sqrt(np.mean(crit[c]) / 2)) for c in R_CHOICES}
            win = min(R_CHOICES, key=lambda c: rms[c] if np.isfinite(rms[c]) else np.inf)
            share = _win_share(by, ip, ifl)
            for c in R_CHOICES:
                cell_rows.append(dict(ppf_target=R_PPF[ip], flux=R_FLUX[ifl], ppf_min=min(ppfs), ppf_max=max(ppfs),
                                      choice=c, rms_criterion=rms[c], mean_pull_sd=float(np.mean(sds[c])),
                                      rms_pull_mean=float(np.sqrt(np.mean(np.square(means[c])))),
                                      replicates=per_phase * R_PHASES, winner=c == win, bootstrap_win_share=share[c]))
    return phase_rows, cell_rows, time.time() - t0


def fig_r(out, n_per_cell, procs, log, tag='R'):
    plt = _plt()
    from matplotlib import colors
    phase_rows, cell_rows, secs = robustness(n_per_cell, procs, log)
    write_csv(os.path.join(out, tag + '_phases.csv'), phase_rows)
    write_csv(os.path.join(out, tag + '_cells.csv'), cell_rows)
    nP, nF = len(R_PPF), len(R_FLUX)
    win = np.empty((nP, nF), object)
    rmsw = np.zeros((nP, nF))
    for r in cell_rows:
        if r['winner']:
            i, j = R_PPF.index(r['ppf_target']), R_FLUX.index(r['flux'])
            win[i, j], rmsw[i, j] = r['choice'], r['rms_criterion']
    look = {(r['ppf_target'], r['flux'], r['choice']): r['rms_criterion'] for r in cell_rows}
    shr = {(r['ppf_target'], r['flux'], r['choice']): r['bootstrap_win_share'] for r in cell_rows}
    fig, axes = plt.subplots(1, len(R_CHOICES), figsize=(2.15 * len(R_CHOICES) + 0.8, 3.9), sharey=True)
    vmax = 1.0
    nrm = colors.Normalize(0.0, vmax)
    for ax, c in zip(axes, R_CHOICES):
        m = np.array([[look[(R_PPF[i], R_FLUX[j], c)] for j in range(nF)] for i in range(nP)])
        im = ax.imshow(np.minimum(m, vmax), cmap='Blues', norm=nrm, aspect='auto', origin='lower')
        for i in range(nP):
            for j in range(nF):
                best = win[i, j] == c
                ax.text(j, i, ('★ %.2f\n%.0f %%' % (m[i, j], 100 * shr[(R_PPF[i], R_FLUX[j], c)])) if best
                        else '%.2f' % m[i, j], ha='center', va='center', fontsize=7.5,
                        fontweight='bold' if best else None, color='white' if m[i, j] > 0.55 * vmax else '#0b0b0b')
        ax.set_xticks(range(nF))
        ax.set_xticklabels(['×%g' % f for f in R_FLUX], fontsize=8)
        ax.set_title(LABEL[c], fontsize=8.5)
        ax.set_xlabel('flux', fontsize=8)
    axes[0].set_yticks(range(nP))
    axes[0].set_yticklabels(['%d' % p for p in R_PPF])
    axes[0].set_ylabel('points per Kiessig period\n(coarser scan at the join)')
    fig.subplots_adjust(left=0.07, right=0.925, bottom=0.17, top=0.83, wspace=0.12)
    cb = fig.colorbar(im, cax=fig.add_axes([0.94, 0.17, 0.008, 0.66]))
    cb.set_label('RMS of (pull mean, pull SD − 1)')
    fig.suptitle('Robustness map: the criterion per choice over fringe sampling and counts (four fringe phases, %d '
                 'replicates per cell); ★ the best choice in the cell and the share of bootstrap resamples it wins'
                 % cell_rows[0]['replicates'], fontsize=9.5)
    _save(fig, out, tag + '_winner')
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.4), sharey=True)
    fig.subplots_adjust(left=0.09, right=0.86, bottom=0.14, top=0.86, wspace=0.08)
    nrm = colors.TwoSlopeNorm(vmin=0.2, vcenter=1.0, vmax=1.8)
    for ax, c in zip(axes, ('guard_p0.3', 'guard_off')):
        m = np.zeros((nP, nF))
        for r in cell_rows:
            if r['choice'] == c:
                m[R_PPF.index(r['ppf_target']), R_FLUX.index(r['flux'])] = r['mean_pull_sd']
        im = ax.imshow(m, cmap='RdBu_r', norm=nrm, aspect='auto', origin='lower')
        for i in range(nP):
            for j in range(nF):
                ax.text(j, i, '%.2f' % m[i, j], ha='center', va='center', fontsize=9,
                        color='white' if abs(m[i, j] - 1) > 0.4 else '#0b0b0b')
        ax.set_xticks(range(nF))
        ax.set_xticklabels(['×%g' % f for f in R_FLUX])
        ax.set_yticks(range(nP))
        ax.set_yticklabels(['%d' % p for p in R_PPF])
        ax.set_xlabel('flux relative to the NX-like default')
        ax.set_title(LABEL[c])
    axes[0].set_ylabel('points per Kiessig period')
    cb = fig.colorbar(im, cax=fig.add_axes([0.88, 0.14, 0.015, 0.72]))
    cb.set_label('pull SD (mean over four fringe phases; ideal 1)')
    fig.suptitle('Pull SD of the default and of the guard off over fringe sampling and counts', fontsize=10)
    _save(fig, out, tag + '_pull_sd')
    return cell_rows, secs


# ------------------------------------------------------------------ data summary

def _rs_section(cell_rows):
    """The staggered-grid robustness map (RS) as a section of data_summary.md."""
    by = defaultdict(dict)
    for r in cell_rows:
        by[(r['ppf_target'], r['flux'])][r['choice']] = r
    L = ['## RS. Robustness map on staggered grids', '',
         'As R, with the two scans sharing no Qz at the join (`xs.chain_plan(grid=\'staggered\')`). RMS of (pull mean, '
         'pull SD − 1) per choice; the winner and the share of bootstrap resamples it wins.', '']
    rows = []
    for (p, fl) in sorted(by):
        d = by[(p, fl)]
        w = [c for c in R_CHOICES if d[c]['winner']][0]
        rows.append(['%d' % p, '×%g' % fl, '%s (%.0f %%)' % (LABEL[w], 100 * d[w]['bootstrap_win_share'])]
                    + ['%.2f / %.2f' % (d[c]['rms_criterion'], d[c]['mean_pull_sd']) for c in R_CHOICES])
    L += _table(['points per period', 'flux', 'best'] + ['%s: RMS / pull SD' % LABEL[c] for c in R_CHOICES], rows)
    return L


def _table(header, rows):
    L = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    L += ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows]
    return L


def write_summary(out, a, info, res=None, a1=None, a3=None, a4=None, a5=None, a6=None, a7=None, a8=None, rc=None,
                  a5p=None):
    L = ['# Study A, reflectivity guard: the numbers behind the figures', '',
         'Made by `tests/tools/ref_guard_study.py` (its docstring says what each choice is). '
         'All numbers below are measured by that run; nothing here is read from elsewhere except the C45 check.', '',
         '## How this was made', '',
         'Command line: `%s`' % info['command'], '',
         '- Replicates per join: %d (gauntlet seeds for the five biased joins; seeds 0 … %d for the first join of the '
         'covariance study).' % (a.replicates, a.replicates - 1),
         '- Processes: %d. Total wall time: %.0f s.' % (a.procs, info['total']),
         '- The AICc average (a candidate, never a default): Akaike weights w_k ∝ exp(−ΔAICc_k/2), AICc = χ² + 2K + '
         '2K(K+1)/(n−K−1), K = order + 2, over the rungs of the ladder\'s largest window (the same points); '
         'δ̄ = Σ w_k δ_k, σ² = Σ w_k (σ_k² + (δ_k − δ̄)²): Burnham & Anderson 2002 (eq. 6.12), the revised form of '
         'Buckland et al. 1997.', '']
    for k, v in info['times'].items():
        L.append('- %s: %.1f s' % (k, v))
    L.append('')
    if res is not None:
        L += ['## C45 reproduced first', '']
        n, diffs = info['c45']
        if n is None:
            L.append('Not checked: %s.' % '; '.join(diffs))
        elif not diffs:
            L.append('C45 reproduced exactly: %d of %d committed values (default, guard_off, guard_0.01: n, failed, mean '
                     'pull, pull SD, bias, RMS, median error, noise-free bias and rung, six joins; the first join over '
                     'its 300 seeds) agree to all six printed digits '
                     '(docs/comparisons_data/ref_patch_biased_joins/joins.csv).' % (n, n))
        else:
            L.append('C45 NOT reproduced exactly: %d of %d values differ:' % (len(diffs), n))
            L += ['- ' + d for d in diffs[:40]]
        L += ['', 'The stored-rung selection against `patching.joint_factor` itself (the first 10 replicates of each '
              'join, every p of the sweep and the guard off):', '']
        L += _table(['join', 'cases', 'mismatches'], [[SHORT[k], *info['checks'][k]] for k in JOINS])
        L += ['', '## A2. Pulls per join and choice', '',
              'Mean pull / pull SD (n = %d per join; failures in brackets when any).' % a.replicates, '']
        cols = list(CHOICES)
        rows = []
        for k in JOINS:
            rows.append([SHORT[k]] + ['%s / %s%s' % (_f(res[k][c]['mean_pull'], '%+.2f'), _f(res[k][c]['pull_sd']),
                                                    ' [%d]' % res[k][c]['failed'] if res[k][c]['failed'] else '')
                                      for c in cols])
        L += _table(['join'] + [LABEL[c] for c in cols], rows)
        L += ['', 'The rest of the p sweep, and two forms of the average for comparison only: the same Akaike weights '
              'with Buckland et al. 1997\'s own σ = Σ w_k √(σ_k² + (δ_k − δ̄)²), and the average over every window '
              '(its weights compare χ² of different data):', '']
        extra = [c for c in ALL_CHOICES if c not in CHOICES]
        rows = [[SHORT[k]] + ['%s / %s' % (_f(res[k][c]['mean_pull'], '%+.2f'), _f(res[k][c]['pull_sd'])) for c in extra]
                for k in JOINS]
        L += _table(['join'] + [LABEL.get(c, c.replace('guard_p', 'p ')) for c in extra], rows)
        L += ['', 'Bias of δ (×10⁻³) and median error σ̂ (×10⁻³):', '']
        rows = [[SHORT[k]] + ['%s / %s' % (_f(1e3 * res[k][c]['bias_delta'], '%+.2f'),
                                           _f(1e3 * res[k][c]['median_err'])) for c in cols] for k in JOINS]
        L += _table(['join'] + [LABEL[c] for c in cols], rows)
    if a1 is not None:
        L += ['', '## A1. What the fit sees', '',
              'Replicates 0–5 of each join type; the default\'s chosen rung (p 0.3) and its pull.', '']
        L += _table(['type', 'join', 'replicate', 'rung', 'p', 'pull', 'f̂ (default)', 'f̂ (guard off)'],
                    [[r['join_type'], SHORT[r['join']], r['replicate'],
                      'o%d ±%d%s' % (r['order'], r['n_ext'], ' inflated' if r['inflated'] else ''),
                      _f(r['p_chi2']), _f(r['pull'], '%+.2f'), _f(math.exp(r['delta']), '%.5f'),
                      _f(math.exp(r['off_delta']), '%.5f')] for r in a1])
    if a3 is not None:
        L += ['', '## A3. Noise-free bias', '', 'In median errors of each choice, with the rung chosen on noise-free '
              'data (order, points either side).', '']
        by = defaultdict(dict)
        for r in a3:
            by[r['join']][r['choice']] = r
        rows = [[SHORT[k]] + ['%s (%s, %s)' % (_f(by[k][c]['noise_free_bias'], '%+.2f'), by[k][c]['noise_free_order'],
                                              by[k][c]['noise_free_n_ext']) for c in CHOICES] for k in JOINS]
        L += _table(['join'] + [LABEL[c] for c in CHOICES], rows)
    if a4 is not None:
        L += ['', '## A4. The guard\'s rung choices', '', 'Share, mean pull and pull SD of the replicates on each rung '
              '(shares ≥ 2 %).', '']
        L += _table(['join', 'p', 'rung', 'inflated', 'share', 'mean pull', 'pull SD'],
                    [[SHORT[r['join']], r['guard_p'], 'o%d ±%d' % (r['order'], r['n_ext']), 'yes' if r['inflated'] else '',
                      '%.3f' % r['share'], _f(r['mean_pull'], '%+.2f'), _f(r['pull_sd'])]
                     for r in a4 if r['share'] >= 0.02])
        if res is not None:
            L += ['', 'Mean Akaike weight of each rung in the AICc average (largest window), and of each window in '
                  'the average over all windows (comparison only):', '']
            L += _table(['join', 'AICc average: weight per rung', 'all windows: weight per window (points either side)'],
                        [[SHORT[k], info['avg_weights'][k], info['avg_all_windows'][k]] for k in JOINS])
    def a5_table(rows):
        return _table(['choice', 'first-join pull SD', 'minus the guard off\'s (paired)', 'mean |pull mean| (biased)',
                       'mean pull SD (biased)'],
                      [[LABEL.get(r['choice'], r['choice'].replace('guard_p', 'p ')),
                        '%.3f ± %.3f' % (r['first_join_pull_sd'], r['first_join_pull_sd_se']),
                        '%+.3f ± %.3f' % (r['first_join_sd_minus_off'], r['first_join_sd_minus_off_se']),
                        '%.3f ± %.3f' % (r['biased_mean_abs_pull_mean'], r['biased_mean_abs_pull_mean_se']),
                        '%.3f' % r['biased_mean_pull_sd']] for r in rows])
    if a5 is not None:
        L += ['', '## A5. The decision curve', '',
              'x: pull SD at the smooth first join; y: mean |pull mean| over the five biased joins; ± bootstrap SE '
              '(500 resamples of the replicates; the difference from the guard off resamples the same replicates for '
              'both). Also the mean pull SD over the biased joins. %d replicates per join (the figure).'
              % a5[0]['replicates'], '']
        L += a5_table(a5)
    if a5p is not None:
        L += ['', '### The same with %d replicates per join (precision check)' % a5p[0]['replicates'], '',
              'The same seeds continued (the first %d are the figure\'s). With 300 seeds C45 found the first join\'s '
              'pull SD 1.13 at p 0.3 and 1.05 with the guard off; the table shows how much of that was sampling.'
              % a5[0]['replicates'] if a5 is not None else '', '']
        L += a5_table(a5p)
        if info.get('blocks'):
            L += ['', 'The first join\'s pull SD in consecutive blocks of %d seeds (the first block is the figure\'s):'
                  % a.replicates, '']
            L += _table(['choice'] + ['seeds %d–%d' % (i * a.replicates, (i + 1) * a.replicates - 1)
                                      for i in range(len(info['blocks']['guard_off']))],
                        [[LABEL[c]] + ['%.3f' % v for v in info['blocks'][c]] for c in ('guard_off', 'guard_p0.3')])
        if info.get('off_counting'):
            sd, sh, mf = info['off_counting']
            L += ['', 'Why the guard off\'s pull SD is below 1 there: with its counting error alone (no inflation) it '
                  'is %.3f; the inflate-only rule max(1, √(χ²/dof)) enlarges the error in %.0f %% of the replicates, by '
                  '×%.3f on average among those (%d replicates).' % (sd, 100 * sh, mf, a.precision)]
    if a6 is not None:
        L += ['', '## A6. Coverage', '', 'Share of |pull| < 1 / share of |pull| < 2 (targets 0.683 / 0.954).', '']
        by = defaultdict(dict)
        for r in a6:
            by[r['group']][r['choice']] = r
        rows = [[SHORT.get(g, 'pooled')] + ['%.3f / %.3f' % (by[g][c]['share_lt1'], by[g][c]['share_lt2'])
                                            for c in CHOICES] for g in ['pooled'] + list(JOINS)]
        L += _table(['group'] + [LABEL[c] for c in CHOICES], rows)
    if a7 is not None:
        L += ['', '## A7. Downstream fit', '',
              'Two cases, seeds 0 … %d each. **A7** (as asked): NX-like plan, 25 Å film (ρ 0.39 e/Å³, σ 3.5 Å), the '
              'owner\'s monitor, the covariance study\'s seeds. **A7b** (added: a case where the join choice matters): '
              'the gauntlet\'s layer_film150 (150 Å film, ρ %.3f e/Å³, σ %.1f Å, four coinciding scans; its join 2 is '
              'one of the biased joins), the gauntlet\'s seeds. Each choice\'s join factors and errors are chained '
              '(`uncertainty.steps_to_phi`), stitched (`PatchResult.stitch`, coincident points merged), finished and '
              'fitted by `gls.fit` with the full covariance and a free scale, as `tests/tools/covariance_pulls.py`, '
              'starting from truth × (1.02, 0.99, 1.03). Bias, SD and RMS in Å; pulls against the fit\'s own errors.'
              % (a7[0]['seeds'] - 1, xrr.FILM_RHO, xrr.SIGMA_WATER), '']
        L += _table(['case', 'choice', 'failed', 'd bias', 'd SD', 'd RMS', 'd pull mean / SD', 'σ bias', 'σ SD', 'σ RMS',
                     'σ pull mean / SD', 'ρ pull SD', 'χ²/dof'],
                    [['A7 (25 Å)' if r['case'] == 'nx25' else 'A7b (150 Å)', LABEL[r['choice']], r['failed'],
                      '%+.4f' % r['bias_d'], '%.4f' % r['sd_d'], '%.4f' % r['rms_d'],
                      '%+.2f / %.2f' % (r['pull_mean_d'], r['pull_sd_d']), '%+.4f' % r['bias_sigma'],
                      '%.4f' % r['sd_sigma'], '%.4f' % r['rms_sigma'],
                      '%+.2f / %.2f' % (r['pull_mean_sigma'], r['pull_sd_sigma']), '%.2f' % r['pull_sd_rho'],
                      '%.3f' % r['chi2_dof']] for r in a7])
    if a8 is not None:
        L += ['', '## A8. NX school, scans 6–9', '',
              'Factor ± error per choice beside the calibrated foil ratio (`absorbers.calibrated`, `Foils.step` at the '
              'overlap\'s lowest Qz). z = (ln f̂ − ln f_foil)/√(σ̂² + σ_foil²). The foil ratio is independent of the '
              'data only where Monc/Monp stays within 3 % across the join (P29); joins 2 and 3 open the slits.', '']
        L += _table(['join', 'absorbers', 'Monc/Monp', 'foil ratio', 'choice', 'factor', 'rung', 'z', 'within 1σ',
                     'within 2σ'],
                    [[r['join'], '%s → %s' % (r['absorber_a'], r['absorber_b']), _f(r['monc_monp_ratio'], '%.3f'),
                      '%.5f ± %.2f %%' % (r['foil_ratio'], 100 * r['foil_rel_err']), LABEL[r['choice']],
                      '%.5f ± %.5f' % (r['factor'], r['factor_err']) if 'factor' in r else 'failed', r.get('rung', ''),
                      _f(r.get('z_vs_foil', math.nan), '%+.2f'), 'yes' if r.get('within_1') else 'no',
                      'yes' if r.get('within_2') else 'no'] for r in a8])
    if rc is not None:
        L += ['', '## R. Robustness map', '',
              'A %g Å film (four phases: ±1/8 and ±3/8 of a fringe at the join), three scans from `xs.chain_plan` with '
              'the join at Qz ≈ %g Å⁻¹; the coarser scan\'s step sets the points per Kiessig period (the actual range '
              'over the phases in brackets); flux relative to the NX-like default. Criterion: '
              '√(mean over phases of (pull mean² + (pull SD − 1)²)/2). %d replicates per cell.'
              % (R_D0, R_Q0, rc[0]['replicates']), '']
        by = defaultdict(dict)
        for r in rc:
            by[(r['ppf_target'], r['flux'])][r['choice']] = r
        rows = []
        for (p, fl), d in sorted(by.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
            w = [c for c in R_CHOICES if d[c]['winner']][0]
            rows.append(['%d (%.1f–%.1f)' % (p, d[w]['ppf_min'], d[w]['ppf_max']), '×%g' % fl, LABEL[w],
                         ', '.join('%s %.0f %%' % (LABEL[c], 100 * d[c]['bootstrap_win_share']) for c in R_CHOICES
                                   if d[c]['bootstrap_win_share'] >= 0.05)]
                        + ['%.2f' % d[c]['rms_criterion'] for c in R_CHOICES])
        L += _table(['points per period', 'flux', 'best', 'wins (share of 200 bootstrap resamples)']
                    + ['RMS ' + LABEL[c] for c in R_CHOICES], rows)
        L += ['', 'Pull SD (mean over the four phases):', '']
        rows = [['%d' % p, '×%g' % fl] + ['%.2f' % d[c]['mean_pull_sd'] for c in R_CHOICES]
                for (p, fl), d in sorted(by.items(), key=lambda kv: (kv[0][0], -kv[0][1]))]
        L += _table(['points per period', 'flux'] + [LABEL[c] for c in R_CHOICES], rows)
        L += ['', 'RMS over phases of the pull mean:', '']
        rows = [['%d' % p, '×%g' % fl] + ['%.2f' % d[c]['rms_pull_mean'] for c in R_CHOICES]
                for (p, fl), d in sorted(by.items(), key=lambda kv: (kv[0][0], -kv[0][1]))]
        L += _table(['points per period', 'flux'] + [LABEL[c] for c in R_CHOICES], rows)
    L += ['', '## Files', '', 'Each figure `X.png` has its numbers in `X.csv` (A2 also `A2_pulls_all.csv`, every pull; '
          'A7 also `A7_downstream_seeds.csv`; R `R_cells.csv` and `R_phases.csv`). The quick variant of the tool '
          '(`--quick`) is a smoke run with few replicates, for tests only.', '']
    with open(os.path.join(out, 'data_summary.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=OUT_DEFAULT, help='output folder (default %(default)s)')
    ap.add_argument('--replicates', type=int, default=400,
                    help='replicates per join (C45 used 400; the first join\'s 300 seeds are its first 300)')
    ap.add_argument('--figures', default=','.join(FIGURES), help='comma-separated, of ' + ','.join(FIGURES))
    ap.add_argument('--quick', action='store_true',
                    help='a small run for testing (24 replicates per join and per cell, 12 seeds for A7)')
    ap.add_argument('--a7-seeds', type=int, default=200, help='seeds of the downstream fits (A7, A7b)')
    ap.add_argument('--precision', type=int, default=2000,
                    help='A5\'s points again with this many replicates per join (a table in data_summary.md; 0: no)')
    ap.add_argument('--r-replicates', type=int, default=800,
                    help='replicates per robustness cell, split over its four fringe phases (R)')
    ap.add_argument('--procs', type=int, default=min(4, os.cpu_count() or 1), help='worker processes')
    a = ap.parse_args(argv)
    if a.quick:
        a.replicates, a.a7_seeds, a.r_replicates, a.precision = 24, 12, 24, 0
    figs = [f.strip() for f in a.figures.split(',') if f.strip()]
    bad = [f for f in figs if f not in FIGURES]
    if bad:
        ap.error('unknown figures: %s' % ', '.join(bad))
    os.chdir(ROOT)
    os.makedirs(a.out, exist_ok=True)
    warnings.simplefilter('ignore')
    t_start = time.time()
    times = {}
    info = dict(command=('python tests/tools/ref_guard_study.py ' + ' '.join(argv if argv is not None else sys.argv[1:])).strip(),
                times=times)

    def log(msg):
        print(msg, flush=True)
    kw = {}
    if any(f in figs for f in ('A2', 'A3', 'A4', 'A5', 'A6')):
        t0 = time.time()
        data = six_joins(a.replicates, a.procs, log)
        info['checks'] = {k: data[k]['check'] for k in JOINS}
        info['c45'] = c45_check(data)
        res, pulls = summarise(data)
        avg_w = {}
        for k in JOINS:
            acc = defaultdict(float)
            for t in data[k]['tabs']:
                av = average(t)
                if av is not None:
                    for idx, w in av[2].items():
                        acc[t['ladder'][idx]] += w / len(data[k]['tabs'])
            avg_w[k] = ', '.join('o%d ±%d: %.2f' % (o, e, w) for (o, e), w in sorted(acc.items(), key=lambda kv: -kv[1])
                                 if w >= 0.005)
        info['avg_weights'] = avg_w
        win_w = {}
        for k in JOINS:
            acc = defaultdict(float)
            for t in data[k]['tabs']:
                av = average(t, all_windows=True)
                if av is not None:
                    for idx, w in av[2].items():
                        acc[t['ladder'][idx][1]] += w / len(data[k]['tabs'])
            win_w[k] = ', '.join('±%d: %.2f' % (e, w) for e, w in sorted(acc.items(), key=lambda kv: -kv[0]))
        info['avg_all_windows'] = win_w
        rows = [dict(join=k, choice=c, **res[k][c]) for k in JOINS for c in ALL_CHOICES]
        write_csv(os.path.join(a.out, 'joins.csv'), rows)
        times['six joins (draws, rung tables, checks)'] = time.time() - t0
        kw['res'] = res
        n, diffs = info['c45']
        log('C45 check: %s' % ('not checked' if n is None else ('exact (%d values)' % n if not diffs
                                                                else '%d of %d differ' % (len(diffs), n))))
        if 'A2' in figs:
            fig_a2(a.out, res, pulls)
        if 'A3' in figs:
            kw['a3'] = fig_a3(a.out, res)
        if 'A4' in figs:
            kw['a4'] = fig_a4(a.out, data)
        if 'A5' in figs:
            if a.precision > a.replicates:
                t1 = time.time()
                dp = six_joins(a.precision, a.procs, log, check=False)
                rp, pp = summarise(dp, ['guard_p%g' % p for p in GUARD_PS] + ['guard_off', 'legacy', 'average'])
                kw['a5p'] = decision_points(rp, pp)
                offs = [(t['off'], t['truth']) for t in dp[COV]['tabs'] if isinstance(t['off'], tuple)]
                infl = np.array([max(1.0, math.sqrt(r[2] / r[3])) for r, _ in offs])
                info['off_counting'] = (float(np.std([(r[0] - tr) / r[1] for r, tr in offs], ddof=1)),
                                        float(np.mean(infl > 1)), float(np.mean(infl[infl > 1])))
                info['blocks'] = {c: [float(np.std(pp[COV][c][i:i + a.replicates], ddof=1))
                                      for i in range(0, len(pp[COV][c]) - a.replicates + 1, a.replicates)]
                                  for c in ('guard_off', 'guard_p0.3')}
                write_csv(os.path.join(a.out, 'A5_precision.csv'), kw['a5p'])
                times['A5 precision run (%d replicates per join)' % a.precision] = time.time() - t1
            kw['a5'] = fig_a5(a.out, res, pulls, kw.get('a5p'))
        if 'A6' in figs:
            kw['a6'] = fig_a6(a.out, res, pulls)
        times['A2–A6 figures'] = (time.time() - t0 - times['six joins (draws, rung tables, checks)']
                                  - sum(v for k, v in times.items() if k.startswith('A5 precision')))
    if 'A1' in figs:
        t0 = time.time()
        kw['a1'] = fig_a1(a.out)
        times['A1'] = time.time() - t0
    if 'A7' in figs:
        t0 = time.time()
        kw['a7'] = fig_a7(a.out, a.a7_seeds, a.procs, log) + fig_a7(a.out, a.a7_seeds, a.procs, log, 'film150')
        times['A7 and A7b (%d seeds each)' % a.a7_seeds] = time.time() - t0
    if 'A8' in figs:
        t0 = time.time()
        kw['a8'] = fig_a8(a.out)
        times['A8'] = time.time() - t0
    if 'R' in figs:
        t0 = time.time()
        kw['rc'], _ = fig_r(a.out, a.r_replicates, a.procs, log)
        times['R (%d replicates per cell)' % a.r_replicates] = time.time() - t0
    rs = None
    if 'RS' in figs:
        global R_GRID
        t0, R_GRID = time.time(), 'staggered'
        rs, _ = fig_r(a.out, a.r_replicates, a.procs, log, tag='RS')
        R_GRID = 'coincide'
        times['RS, staggered grids (%d replicates per cell)' % a.r_replicates] = time.time() - t0
    info['total'] = time.time() - t_start
    write_summary(a.out, a, info, **kw)
    if rs is not None:
        with open(os.path.join(a.out, 'data_summary.md'), 'a') as f:
            f.write('\n'.join([''] + _rs_section(rs)) + '\n')
    log('done: %.0f s' % info['total'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
