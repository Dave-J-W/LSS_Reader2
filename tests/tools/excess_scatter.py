"""Reflectivity points scattered beyond counting statistics: estimators, and their check on known truth.

DATA_NEEDS row 15 (main man's MQ-3; C61 found that 1 % of hidden per-point scatter reproduces the real
joins' 24 % too-small errors). The owner, 2026-11-25: "I don't know the size; measure it from data".
The model, as in C61: each point is y_true × (1 + X·z), z ~ N(0, 1), with the stated (counting) error σ
unchanged. X is the excess, a fraction of R. Two estimators, both on ln y, so that X adds a variance X²
per point:

* **pairs**: points of two scans at the same Qz (the shared points of a join, or a repeated scan).
  Per pair of scans, r_i = ln y_a,i − ln y_b,i = c + e_i with var(e_i) = v_i + 2X², v_i the two points'
  counting variances of ln y. c (the scans' factor) is removed by REML. Model-free: no curve is assumed.
* **within a scan**: over every 6 neighbouring points of one scan, the difference d = Σ w_k ln(y_k/R_F,k)
  whose weights (|w| = 1) cancel any polynomial in Qz up to degree 4, so a smooth curve gives d ≈ 0 and
  var(d) = Σ w_k² (v_k + X²). A curve's own shape left over biases it up: shorter differences (3 to 5
  points) leave 0.3–1.9 % on DPPC, and a 100 Å film's fringes leave about 1.2 % even at 6 (known truth).

Each estimator gives X by Gaussian maximum likelihood over all its terms and a robust value (the median
of the terms' χ²₁ set to 0.455), so that a few glitches or fringes cannot make it.

    python tests/tools/excess_scatter.py --out <dir> [--trials 40] [--workers 6]

Writes ``known_truth.csv``, ``numbers.json`` and figure X1 (recovered against true X, per estimator and
curve) to ``--out``. The real-data run (private) imports ``pair_terms``, ``curvature_terms`` and
``estimate`` from here, so the real numbers come from the code checked here.
"""
import argparse
import csv
import json
import math
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

CHI2_1_MEDIAN = 0.454936          # median of a χ² with 1 degree of freedom
QC_WATER = 0.0217
Q_MIN = 0.04                      # leave out the critical edge, where ln R/R_F changes fastest
SNR_MIN = 5.0                     # y/σ: ln y is linear in the noise only where the noise is small
GRID = np.concatenate([[0.0], np.geomspace(1e-4, 0.2, 400)])


# ---------------------------------------------------------------------------------------- estimators
def _ok(y, s):
    return np.isfinite(y) & np.isfinite(s) & (y > 0) & (s > 0) & (y > SNR_MIN * s)


def pair_terms(qa, ya, sa, qb, yb, sb, tol=1e-6):
    """Shared Qz of two scans -> (r, v) of ln y_a − ln y_b, or None with fewer than 2 pairs."""
    qa, ya, sa, qb, yb, sb = map(lambda x: np.asarray(x, float), (qa, ya, sa, qb, yb, sb))
    ia, ib = [], []
    for i, q in enumerate(qa):
        j = np.nonzero(np.abs(qb - q) <= tol * max(abs(q), 1e-3))[0]
        if len(j):
            ia.append(i); ib.append(j[0])
    if len(ia) < 2:
        return None
    ia, ib = np.array(ia), np.array(ib)
    ok = _ok(ya[ia], sa[ia]) & _ok(yb[ib], sb[ib]) & (qa[ia] >= Q_MIN)
    ia, ib = ia[ok], ib[ok]
    if len(ia) < 2:
        return None
    r = np.log(ya[ia]) - np.log(yb[ib])
    v = (sa[ia] / ya[ia]) ** 2 + (sb[ib] / yb[ib]) ** 2
    return dict(r=r, v=v, q=qa[ia], ia=ia, ib=ib)


def _fresnel(q, qc=QC_WATER):
    from lss_core import fresnel
    return fresnel.fresnel(q, qc)


DIFF_ORDER = 5                    # 6 neighbouring points; orders 2-4 leave a curve's own shape in (known truth)


def curvature_terms(q, y, s, qc=QC_WATER, order=DIFF_ORDER):
    """Every ``order`` + 1 neighbouring points of one scan -> the difference d = Σ w_k ln(y_k/R_F,k) whose
    weights cancel every polynomial in Qz below degree ``order`` (|w| = 1), a = Σw²v, b = Σw² and the
    middle index."""
    q, y, s = map(lambda x: np.asarray(x, float), (q, y, s))
    o = np.argsort(q)
    q, y, s = q[o], y[o], s[o]
    ok = _ok(y, s) & (q >= Q_MIN)
    q, y, s, idx = q[ok], y[ok], s[ok], o[ok]
    n = order + 1
    if len(q) < n:
        return None
    ly = np.log(y / _fresnel(q, qc))
    v = (s / y) ** 2
    d, a, b, mid, qm = [], [], [], [], []
    for i in range(len(q) - order):
        qq = q[i:i + n]
        h = np.diff(qq)
        if np.any(h <= 0) or h.max() > 2.5 * h.min():
            continue
        x = (qq - qq.mean()) / np.ptp(qq)
        w = np.linalg.svd(np.vstack([x ** m for m in range(order)]))[2][-1]
        w = w / np.linalg.norm(w)
        d.append(w @ ly[i:i + n]); a.append(w ** 2 @ v[i:i + n]); b.append(1.0)
        mid.append(idx[i + n // 2]); qm.append(qq[n // 2])
    if not d:
        return None
    return dict(d=np.array(d), a=np.array(a), b=np.array(b), q=np.array(qm), mid=np.array(mid))


def _pairs_loglik(groups, x2):
    ll = 0.0
    for g in groups:
        w = 1.0 / (g['v'] + 2 * x2)
        c = np.sum(w * g['r']) / np.sum(w)
        ll += -0.5 * (np.sum(np.log(1 / w)) + math.log(np.sum(w)) + np.sum(w * (g['r'] - c) ** 2))
    return ll


def _pairs_z2(groups, x2):
    z = []
    for g in groups:
        w = 1.0 / (g['v'] + 2 * x2)
        c = np.sum(w * g['r']) / np.sum(w)
        h = w / np.sum(w)
        z.append(w * (g['r'] - c) ** 2 / np.maximum(1 - h, 1e-9))
    return np.concatenate(z) if z else np.array([])


def _curv_loglik(t, x2):
    var = t['a'] + t['b'] * x2
    return -0.5 * np.sum(np.log(var) + t['d'] ** 2 / var)


def _robust(z2_of_x2):
    """The X where the median of the terms' z² is χ²₁'s median (0 when it is below already)."""
    if np.median(z2_of_x2(0.0)) <= CHI2_1_MEDIAN:
        return 0.0
    lo, hi = 0.0, 0.5 ** 2
    if np.median(z2_of_x2(hi)) > CHI2_1_MEDIAN:
        return math.nan
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if np.median(z2_of_x2(mid)) > CHI2_1_MEDIAN:
            lo = mid
        else:
            hi = mid
    return math.sqrt(0.5 * (lo + hi))


def estimate(kind, terms):
    """kind 'pairs': terms = list of pair_terms dicts; 'curvature': list of curvature_terms dicts.
    Returns dict(x_ml, x_robust, n_terms, chi2_dof0 (χ²/dof with X = 0))."""
    terms = [t for t in terms if t is not None]
    if kind == 'pairs':
        if not terms:
            return dict(x_ml=math.nan, x_lo=math.nan, x_hi=math.nan, x_robust=math.nan, n_terms=0, chi2_dof0=math.nan)
        ll = np.array([_pairs_loglik(terms, x ** 2) for x in GRID])
        n = sum(len(g['r']) for g in terms)
        dof = n - len(terms)
        z0 = _pairs_z2(terms, 0.0)
        chi0 = float(np.sum([np.sum((g['r'] - np.sum(g['r'] / g['v']) / np.sum(1 / g['v'])) ** 2 / g['v'])
                             for g in terms])) / max(dof, 1)
        xr = _robust(lambda x2: _pairs_z2(terms, x2))
        nterm = dof
    else:
        if not terms:
            return dict(x_ml=math.nan, x_lo=math.nan, x_hi=math.nan, x_robust=math.nan, n_terms=0, chi2_dof0=math.nan)
        t = {k: np.concatenate([x[k] for x in terms]) for k in ('d', 'a', 'b')}
        ll = np.array([_curv_loglik(t, x ** 2) for x in GRID])
        chi0 = float(np.mean(t['d'] ** 2 / t['a']))
        xr = _robust(lambda x2: t['d'] ** 2 / (t['a'] + t['b'] * x2))
        nterm = len(t['d'])
    lo, hi = _interval(ll)
    return dict(x_ml=float(GRID[int(np.argmax(ll))]), x_lo=lo, x_hi=hi, x_robust=xr, n_terms=int(nterm),
                chi2_dof0=chi0)


def _interval(ll, drop=0.5):
    """The 68 % profile-likelihood interval of X on GRID (ln L within 0.5 of its maximum)."""
    ok = np.nonzero(ll >= ll.max() - drop)[0]
    return float(GRID[ok[0]]), float(GRID[ok[-1]])


# ---------------------------------------------------------------------------------------- core + outliers
def _mix_ll(d, a, b, x, pi, tau):
    vc = a + b * x * x
    vo = vc + tau * tau
    lc = -0.5 * (np.log(2 * np.pi * vc) + d * d / vc)
    lo = -0.5 * (np.log(2 * np.pi * vo) + d * d / vo)
    m = np.maximum(lc, lo)
    return m + np.log((1 - pi) * np.exp(lc - m) + pi * np.exp(lo - m))


TAU_MIN = 0.1    # an outlier is at least 10 % of R off; without a floor the outlier part can take over the core


def _mix_fit(d, a, b, x=None, start=(0.005, 0.02, 0.3)):
    """Maximum likelihood of (X, π, τ ≥ TAU_MIN), or of (π, τ) at a fixed X, from two starting shares of
    outliers (the better one is kept). Returns (x, pi, tau, lnL)."""
    from scipy.optimize import minimize
    def unpack(p):
        if x is None:
            return abs(p[0]), 1 / (1 + math.exp(-p[1])), TAU_MIN + abs(p[2])
        return x, 1 / (1 + math.exp(-p[0])), TAU_MIN + abs(p[1])
    f = lambda p: -np.sum(_mix_ll(d, a, b, *unpack(p)))
    best = None
    for pi0 in (min(max(start[1], 1e-3), 0.5), 0.005):
        p0 = [start[0], math.log(pi0 / (1 - pi0)), max(start[2] - TAU_MIN, 0.05)]
        if x is not None:
            p0 = p0[1:]
        r = minimize(f, p0, method='Nelder-Mead', options=dict(xatol=1e-6, fatol=1e-4, maxiter=4000))
        if best is None or r.fun < best.fun:
            best = r
    xx, pi, tau = unpack(best.x)
    return xx, pi, tau, -best.fun


def _pair_resid(groups, x, pi, tau):
    """Each shared point's residual from its pair's core-weighted mean, scaled by √(1 − h): d, a = v, b = 2."""
    d, a = [], []
    for g in groups:
        v = g['v'] + 2 * x * x
        w = 1 / v
        gam = np.ones(len(v))
        for _ in range(3):
            c = np.sum(w * gam * g['r']) / np.sum(w * gam)
            e = g['r'] - c
            lc = math.log(max(1 - pi, 1e-12)) - 0.5 * (e * e / v + np.log(v))
            lo = math.log(max(pi, 1e-12)) - 0.5 * (e * e / (v + tau * tau) + np.log(v + tau * tau))
            gam = np.maximum(1 / (1 + np.exp(np.clip(lo - lc, -700, 700))), 1e-6)   # a core weight, never 0
        h = w * gam / np.sum(w * gam)
        d.append(e / np.sqrt(np.maximum(1 - h, 0.05)))
        a.append(g['v'])
    return np.concatenate(d), np.concatenate(a)


def estimate_mixture(kind, terms, profile=True):
    """Core excess X with an outlier share π of scale τ (both fractions of R), by maximum likelihood.
    Returns dict(x, x_lo, x_hi (68 % profile interval), pi, tau, n)."""
    terms = [t for t in terms if t is not None]
    if not terms:
        return dict(x=math.nan, x_lo=math.nan, x_hi=math.nan, pi=math.nan, tau=math.nan, n=0)
    if kind == 'pairs':
        x, pi, tau = 0.005, 0.02, 0.3
        for _ in range(3):
            d, a = _pair_resid(terms, x, pi, tau)
            b = np.full(len(d), 2.0)
            x, pi, tau, ll = _mix_fit(d, a, b, start=(max(x, 1e-3), min(max(pi, 1e-3), 0.5), max(tau, 0.05)))
    else:
        d = np.concatenate([t['d'] for t in terms]); a = np.concatenate([t['a'] for t in terms])
        b = np.concatenate([t['b'] for t in terms])
        x, pi, tau, ll = _mix_fit(d, a, b)
    lo = hi = math.nan
    if profile:
        grid = np.unique(np.concatenate([np.linspace(0, 3 * x + 0.002, 31), [x]]))
        pl = np.array([_mix_fit(d, a, b, x=g, start=(g, min(max(pi, 1e-3), 0.5), max(tau, 0.05)))[3] for g in grid])
        ok = grid[pl >= pl.max() - 0.5]
        lo, hi = float(ok.min()), float(ok.max())
    return dict(x=float(x), x_lo=lo, x_hi=hi, pi=float(pi), tau=float(tau), n=int(len(d)))


def _scale_ll(d, a, b, sc, x, pi, tau):
    vc = sc * sc * a + b * x * x
    vo = vc + tau * tau
    lc = -0.5 * (np.log(vc) + d * d / vc)
    lo = -0.5 * (np.log(vo) + d * d / vo)
    m = np.maximum(lc, lo)
    return m + np.log((1 - pi) * np.exp(lc - m) + pi * np.exp(lo - m))


def estimate_scale(kind, terms):
    """Two ways for the stated errors to be too small at once: σ × s (the counting error understated, or
    scatter that grows like √counts) and a proportional X; with outliers as in estimate_mixture.
    Returns dict(s, x, pi, tau, dlnl_x (vs s only), dlnl_s (vs X only), n)."""
    from scipy.optimize import minimize
    terms = [t for t in terms if t is not None]
    if kind == 'pairs':
        m = estimate_mixture('pairs', terms, profile=False)
        d, a = _pair_resid(terms, m['x'], m['pi'], m['tau'])
        b = np.full(len(d), 2.0)
    else:
        d = np.concatenate([t['d'] for t in terms]); a = np.concatenate([t['a'] for t in terms])
        b = np.concatenate([t['b'] for t in terms])

    def fit(fix_s=None, fix_x=None):
        def un(p):
            i = 0
            sc = fix_s if fix_s is not None else abs(p[i]); i += fix_s is None
            x = fix_x if fix_x is not None else abs(p[i]); i += fix_x is None
            return sc, x, 1 / (1 + math.exp(-p[i])), TAU_MIN + abs(p[i + 1])
        p0 = ([] if fix_s is not None else [1.1]) + ([] if fix_x is not None else [0.002]) + [-3.5, 0.3]
        best = None
        for pi0 in (-3.5, -6.0):
            p0[-2] = pi0
            r = minimize(lambda p: -np.sum(_scale_ll(d, a, b, *un(p))), p0, method='Nelder-Mead',
                         options=dict(maxiter=6000, xatol=1e-7, fatol=1e-5))
            if best is None or r.fun < best.fun:
                best = r
        return un(best.x), -best.fun
    (sc, x, pi, tau), ll = fit()
    _, ll_s = fit(fix_x=0.0)
    _, ll_x = fit(fix_s=1.0)
    return dict(s=float(sc), x=float(x), pi=float(pi), tau=float(tau), dlnl_x=float(ll - ll_s),
                dlnl_s=float(ll - ll_x), n=int(len(d)))


# ---------------------------------------------------------------------------------------- known truth
RES = (8.9e-4, 0.0)
SCANS = [(0.030, 0.062, 0.002), (0.056, 0.124, 0.004), (0.112, 0.250, 0.006), (0.232, 0.452, 0.010),
         (0.422, 0.650, 0.012)]       # (first Qz, last Qz, step); each starts on the previous scan's grid
TOP_COUNTS = 2e4                       # counts at each scan's first point
X_TRUE = [0.0, 0.005, 0.01, 0.02, 0.03]
CASES = ['per-point X', 'per-point X + slow drift 2 %', 'per-point X + 3 % outliers']
OUTLIER_SHARE, OUTLIER_SCALE = 0.03, 0.4    # a share of points off by exp(0.4·z): beam misses, glitches
SERIES_PER_ESTIMATE = 50               # about as many shared-point joins as a few real files


def _curves():
    from synthetic import xrr
    return {'water': xrr.bare_water(), 'DPPC': xrr.dppc(), 'film 100 Å': xrr.film(100.0)}


def _grids():
    out, prev = [], None
    for q0, q1, h in SCANS:
        if prev is not None:
            pq = prev[prev >= q0 - 1e-9]
            g = np.concatenate([pq[:3], pq[2] + h * np.arange(1, int(round((q1 - pq[2]) / h)) + 1)])
        else:
            g = q0 + h * np.arange(int(round((q1 - q0) / h)) + 1)
        g = np.round(g, 10)
        out.append(g)
        prev = g
    return out


def synth_series(prof, x, drift, rng, outliers=0.0, sigma_scale=1.0):
    from synthetic import xrr
    scans = []
    grids = _grids()
    for k, q in enumerate(grids + [grids[3]]):            # the last one repeats scan 4
        rt = xrr.smear(q, lambda z: xrr.parratt(z, prof), RES)
        expo = TOP_COUNTS / rt[0]
        mult = 1 + x * rng.standard_normal(len(q))
        if drift:
            mult = mult * (1 + drift * np.sin(2 * np.pi * (q - q[0]) / (q[-1] - q[0] + 1e-12) + rng.uniform(0, 6.3)))
        if outliers:
            bad = rng.random(len(q)) < outliers
            mult = mult * np.where(bad, np.exp(OUTLIER_SCALE * rng.standard_normal(len(q))), 1.0)
        c = rng.poisson(np.maximum(rt * expo * mult, 0)).astype(float)
        f = 10.0 ** k
        scans.append((q, c / expo / f, np.sqrt(np.maximum(c, 1)) / expo / f / sigma_scale))   # stated σ ÷ s
    return scans


def series_terms(scans):
    """All pairs of scans with ≥ 2 shared Qz, and every scan's curvature terms."""
    pairs, curv = [], []
    for i in range(len(scans)):
        for j in range(i + 1, len(scans)):
            t = pair_terms(*scans[i], *scans[j])
            if t is not None:
                pairs.append(t)
        curv.append(curvature_terms(*scans[i]))
    return pairs, curv


def one(args):
    cname, x, case, rep = args
    rng = np.random.default_rng(zlib.crc32(('%s|%s|%s|%d' % (cname, x, case, rep)).encode()))
    prof = _curves()[cname]
    pairs, curv = [], []
    for _ in range(SERIES_PER_ESTIMATE):
        p, c = series_terms(synth_series(prof, x, 0.02 if 'drift' in case else 0.0, rng,
                                         OUTLIER_SHARE if 'outliers' in case else 0.0))
        pairs += p; curv += c
    ep, ec = estimate('pairs', pairs), estimate('curvature', curv)
    mp = estimate_mixture('pairs', pairs, profile=False)
    return dict(curve=cname, x_true=x, case=case, rep=rep,
                pairs_ml=ep['x_ml'], pairs_robust=ep['x_robust'], pairs_n=ep['n_terms'],
                pairs_cover=float(ep['x_lo'] <= x <= ep['x_hi']),
                curv_ml=ec['x_ml'], curv_robust=ec['x_robust'], curv_n=ec['n_terms'],
                curv_cover=float(ec['x_lo'] <= x <= ec['x_hi']),
                pairs_mix=mp['x'], pairs_mix_pi=mp['pi'], pairs_mix_tau=mp['tau'])


def summarise(rows):
    out = []
    keys = sorted({(r['case'], r['curve'], r['x_true']) for r in rows})
    for case, cname, x in keys:
        rs = [r for r in rows if (r['case'], r['curve'], r['x_true']) == (case, cname, x)]
        d = dict(case=case, curve=cname, x_true=x, reps=len(rs))
        for est in ('pairs_mix', 'pairs_mix_pi', 'pairs_ml', 'pairs_robust', 'curv_ml', 'curv_robust'):
            v = np.array([r[est] for r in rs], float)
            v = v[np.isfinite(v)]
            d[est + '_median'] = float(np.median(v)) if len(v) else math.nan
            d[est + '_p16'] = float(np.percentile(v, 16)) if len(v) else math.nan
            d[est + '_p84'] = float(np.percentile(v, 84)) if len(v) else math.nan
        for est in ('pairs', 'curv'):
            d[est + '_coverage68'] = float(np.mean([r[est + '_cover'] for r in rs]))
        d['pairs_n'] = int(np.median([r['pairs_n'] for r in rs]))
        d['curv_n'] = int(np.median([r['curv_n'] for r in rs]))
        out.append(d)
    return out


def headline(summ):
    """The figure's headline, from the numbers: the worst miss of the recommended estimator."""
    worst = max(abs(d['pairs_mix_median'] - d['x_true']) for d in summ if 'drift' not in d['case'])
    return ('Shared Qz with an outlier term recovers the excess within %.2f %% of R on every curve, with or '
            'without outliers; a slow drift adds to it' % (worst * 100))


def figure(summ, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.3})
    curves = ['water', 'DPPC', 'film 100 Å']
    colours = {'water': '#1f77b4', 'DPPC': '#ff7f0e', 'film 100 Å': '#2ca02c'}
    est = [('pairs_mix', 'shared Qz, core + outliers (recommended)'), ('pairs_ml', 'shared Qz, one Gaussian'),
           ('curv_robust', 'within a scan (6-point difference), median'), ('curv_ml', 'within a scan, one Gaussian')]
    fig, axs = plt.subplots(3, 4, figsize=(15, 10.2), sharex=True)
    for row, case in enumerate(CASES):
        for col, (e, title) in enumerate(est):
            ax = axs[row, col]
            ax.plot([0, 3.2], [0, 3.2], color='0.2', lw=1, ls='--', label='truth')
            for k, cname in enumerate(curves):
                s = [d for d in summ if d['case'] == case and d['curve'] == cname]
                xt = np.array([d['x_true'] for d in s]) * 100 + (k - 1) * 0.06
                m = np.array([d[e + '_median'] for d in s]) * 100
                lo = np.array([d[e + '_p16'] for d in s]) * 100
                hi = np.array([d[e + '_p84'] for d in s]) * 100
                ax.errorbar(xt, m, yerr=[m - lo, hi - m], fmt='o', ms=4, color=colours[cname], capsize=2,
                            label=cname)
            top = 4.5
            ax.set_ylim(0, top)
            off = [d[e + '_median'] * 100 for d in summ if d['case'] == case and d[e + '_median'] * 100 > top]
            if off:
                ax.text(0.5, 0.97, 'off scale: %d of 15 medians, %.0f–%.0f %%' % (len(off), min(off), max(off)),
                        transform=ax.transAxes, ha='center', va='top', fontsize=8,
                        bbox=dict(boxstyle='round', fc='white', ec='0.6'))
            ax.set_title(title if row == 0 else '', fontsize=9)
            if col == 0:
                ax.set_ylabel('%s\nrecovered X (%% of R)' %['per-point X only', 'X + a slow 2 % drift per scan',
                                                            'X + 3 % of points off by ~40 %'][row])
            if row == len(CASES) - 1:
                ax.set_xlabel('true X (% of R)')
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc='upper right', ncol=4, frameon=False, bbox_to_anchor=(0.99, 0.995))
    fig.suptitle(headline(summ), x=0.01, ha='left', y=0.995, fontsize=11, fontweight='bold')
    import textwrap
    fig.text(0.01, 0.005, textwrap.fill('Each point: the median and 16th–84th percentiles of %s estimates, each from %d '
             'synthetic series (5 scans, 3 shared Qz per join, one repeated scan; Poisson counts, %d at each '
             'scan\'s top; resolution FWHM 8.9e-4 Å⁻¹). Points: y_true × (1 + X·z), stated errors counting '
             'only; outliers (bottom row): 3 %% of points × exp(0.4·z). Qz ≥ %.2f, y/σ ≥ %d. tests/tools/excess_scatter.py.' %
             ('the', SERIES_PER_ESTIMATE, TOP_COUNTS, Q_MIN, SNR_MIN), 230), fontsize=7.5, color='0.35')
    fig.tight_layout(rect=(0, 0.025, 1, 0.96))
    fig.savefig(path, dpi=200)
    plt.close(fig)


PULL_CASES = {'no excess': (0.0, 0.0, 0.0), 'core 0.4 %': (0.004, 0.0, 0.0), 'core 1 %': (0.01, 0.0, 0.0),
              'core 0.4 % + 3 % outliers': (0.004, 0.03, 0.7), '3 % outliers only': (0.0, 0.03, 0.7)}


def _pull_task(args):
    """One of C61's synthetic joins (ref_guard_study) with a core excess and outliers: today's joint fit."""
    import warnings
    import ref_guard_study as A
    from lss_core import patching
    key, rep, cname = args
    warnings.simplefilter('ignore')
    x, pi, tau = PULL_CASES[cname]
    a, b, t, _r, _m = A.draw_join(key, rep)
    out = []
    for k, sc in enumerate((a, b)):
        rng = np.random.default_rng(zlib.crc32(('%s|%d|%s|%d' % (key, rep, cname, k)).encode()))
        m = 1 + x * rng.standard_normal(len(sc.y))
        m = m * np.where(rng.random(len(sc.y)) < pi, np.exp(tau * rng.standard_normal(len(sc.y))), 1.0)
        out.append(patching.Scan(sc.q, sc.y * m, sc.sigma))
    tab = A.join_table(*out)
    tab['truth'] = t
    return key, cname, tab


def pull_check(reps, workers):
    """Pull SD of today's joint fit (guard p 0.7, its own χ² inflation) on C61's six synthetic joins, with
    the excess found on real data: does it reproduce C56's real pull SD of 1.24?"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ref_guard_study as A
    import guard_error_study as G
    jobs = [(k, r, c) for c in PULL_CASES for k in A.JOINS for r in range(reps)]
    with Pool(workers) as p:
        res = p.map(_pull_task, jobs)
    rows = []
    for c in PULL_CASES:
        per = {}
        for k in A.JOINS:
            tabs = [t for kk, cc, t in res if kk == k and cc == c]
            st = A.stats([G.rule_estimate(t, 'own') for t in tabs], [t['truth'] for t in tabs])[0]
            per[k] = st['pull_sd']
        biased = [v for k, v in per.items() if k != G.SMOOTH]
        rows.append(dict(case=c, core_x=PULL_CASES[c][0], outlier_share=PULL_CASES[c][1],
                         outlier_scale=PULL_CASES[c][2], smooth_pull_sd=per[G.SMOOTH],
                         biased_mean_pull_sd=float(np.mean(biased)), reps=reps))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--trials', type=int, default=40, help='estimates per curve, X and case')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--pulls', type=int, default=200, help='replicates per join for the pull check (0: skip)')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    jobs = [(c, x, case, r) for case in CASES for c in _curves() for x in X_TRUE for r in range(a.trials)]
    with Pool(a.workers) as p:
        rows = p.map(one, jobs)
    summ = summarise(rows)
    with open(os.path.join(a.out, 'known_truth.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0].keys()))
        w.writeheader()
        for d in summ:
            w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in d.items()})
    json.dump(dict(trials=a.trials, series_per_estimate=SERIES_PER_ESTIMATE, x_true=X_TRUE, q_min=Q_MIN,
                   snr_min=SNR_MIN, top_counts=TOP_COUNTS, scans=SCANS, outlier_share=OUTLIER_SHARE,
                   outlier_scale=OUTLIER_SCALE, headline=headline(summ)), open(os.path.join(a.out, 'numbers.json'), 'w'),
              indent=1)
    figure(summ, os.path.join(a.out, 'X1_known_truth.png'))
    if a.pulls:
        pr = pull_check(a.pulls, a.workers)
        with open(os.path.join(a.out, 'pulls.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(pr[0].keys()))
            w.writeheader()
            for d in pr:
                w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()})
        for d in pr:
            print('pulls: %-28s smooth %.2f  biased %.2f' % (d['case'], d['smooth_pull_sd'], d['biased_mean_pull_sd']))
    for d in summ:
        print('%-28s %-10s X %.3f  mix %.4f pi %.3f  pairs %.4f/%.4f  within %.4f/%.4f' % (d['case'], d['curve'],
              d['x_true'], d['pairs_mix_median'], d['pairs_mix_pi_median'], d['pairs_ml_median'],
              d['pairs_robust_median'], d['curv_ml_median'], d['curv_robust_median']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
