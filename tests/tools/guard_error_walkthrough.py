"""Walkthrough of C61 (the guard's error), for AGENTS.md rule 13: from two
reflectivity scans to the verdict, one example at a time.

W1  the input: two scans that overlap, and the factor between them read off
    the Qz points they share, clean and with 2 % hidden per-point scatter;
W2  the joint fit at that join (order 4, 2 points either side) drawn over its
    data, with its residuals, clean and noisy;
W3  the guard's ladder: each curve's χ² p-value against the 0.7 it asks for,
    on the clean and the noisy join;
W4  the pulls over many replicates: today's rule against honest per-point
    errors, with the coverage of ±1 and ±2 error bars;
W5  a fringed join: the unguarded order-4 curve misses the fringe, which is
    why inflating by its χ² overstates the error there;
W6  a real join with known truth: an NX school scan split into two
    interleaved halves, the second × 0.8, joined by today's default.

    python tests/tools/guard_error_walkthrough.py [--out docs/studies/guard_error/walkthrough] [--reps 400]

Synthetic data with known truth (study A's joins, ``ref_guard_study``) and the
public NX school file; numbers in ``numbers.json``.
"""
import argparse
import json
import math
import os
import sys
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (ROOT, HERE, os.path.join(ROOT, 'tests')) if p not in sys.path]

import guard_error_study as G                               # noqa: E402
import ref_guard_study as A                                  # noqa: E402
from lss_core import patching, uncertainty as unc            # noqa: E402

OUT_DEFAULT = os.path.join('docs', 'studies', 'guard_error', 'walkthrough')
SMOOTH, FRINGED = A.COV, 'layer_dppc:3'
X = 0.02                    # the hidden scatter of the noisy example
REP = 3                     # the replicate drawn in W1-W3 and W5
NX_SCAN = 9                 # the NX school scan of W6 (29 points)
BLUE, ORANGE, GREEN, GOLD, RED = '#2a78d6', '#eb6834', '#1baf7a', '#d4a017', '#d23'


def noisy(key, rep, x):
    a, b, t, _r, _m = A.draw_join(key, rep)
    return G.scatter(a, x, G._seed(key, rep, x, 'a')), G.scatter(b, x, G._seed(key, rep, x, 'b')), t


def curve(fit, q):
    """ln(μ_a/R_F) of a RungFit at q."""
    u = (np.asarray(q, float) - fit.centre) / fit.half_width
    return np.polyval(np.asarray(fit.coef)[::-1], u)


def rrf(q, y):
    return np.log(y / patching.fresnel(q, patching.QC))


def p_value(fit):
    return float(fit.p_chi2)


def draw_fit(ax, rax, a, b, fit, title, legend=False):
    """The fitted curve over both scans' points (scan b × the fitted factor) in
    ln(R/R_F), and the residuals in σ; returns χ²/dof."""
    ia, ib = np.asarray(fit.ia), np.asarray(fit.ib)
    qa, qb = a.q[ia], b.q[ib]
    la, lb = rrf(qa, a.y[ia]), rrf(qb, b.y[ib] * math.exp(fit.delta))
    ea, eb = a.sigma[ia] / a.y[ia], b.sigma[ib] / b.y[ib]
    ax.errorbar(qa, la, ea, fmt='o', ms=4, color=BLUE, label='scan a')
    ax.errorbar(qb, lb, eb, fmt='s', ms=4, color=ORANGE, label='scan b × the fitted factor')
    qq = np.linspace(min(qa.min(), qb.min()), max(qa.max(), qb.max()), 200)
    ax.plot(qq, curve(fit, qq), 'k-', lw=1.2, label='the fitted curve (order %d)' % fit.order)
    ax.set_title(title, fontsize=9)
    ax.set_ylabel('ln(R / R_F)')
    ax.tick_params(labelbottom=False)
    rax.axhline(0, color='k', lw=0.6)
    rax.plot(qa, (la - curve(fit, qa)) / ea, 'o', ms=3, color=BLUE)
    rax.plot(qb, (lb - curve(fit, qb)) / eb, 's', ms=3, color=ORANGE)
    rax.set_ylabel('residual / σ')
    rax.set_xlabel('Qz (Å⁻¹)')
    red = fit.chi2 / max(fit.dof, 1)
    rax.text(0.02, 0.92, 'χ²/dof %.2f (p %.2g)' % (red, p_value(fit)), transform=rax.transAxes, fontsize=8, va='top')
    if legend:
        ax.legend(fontsize=7, frameon=False)
    return float(red)


def fit_panels(plt, cases, title, path):
    fig = plt.figure(figsize=(10, 5.2))
    gs = fig.add_gridspec(2, len(cases), height_ratios=[3, 1.3], hspace=0.08)
    red = []
    for col, (a, b, f, sub) in enumerate(cases):
        ax = fig.add_subplot(gs[0, col])
        rax = fig.add_subplot(gs[1, col], sharex=ax)
        red.append(draw_fit(ax, rax, a, b, f, sub, legend=col == 0))
    fig.suptitle(title, fontsize=9)
    fig.savefig(path, dpi=A.DPI, bbox_inches='tight')
    plt.close(fig)
    return red


def shared_ratio(a, b):
    """(q, ln(R_a/R_b), its error) at the Qz points both scans measured."""
    ia, ib = np.nonzero(np.isclose(a.q[:, None], b.q[None, :], rtol=0, atol=1e-6))
    lr = np.log(a.y[ia] / b.y[ib])
    return a.q[ia], lr, np.hypot(a.sigma[ia] / a.y[ia], b.sigma[ib] / b.y[ib])


def ladder(a, b):
    """The guard's ladder [(order, n_ext)], each rung's p-value (nan where it
    could not be fitted), the index kept, whether it was inflated, the table."""
    tab = A.join_table(a, b)
    ps = [A._p(r) if isinstance(r, tuple) else np.nan for r in tab['rungs']]
    k, inflated = A.guard_pick(tab, G.GUARD)
    return [tuple(x) for x in tab['ladder']], ps, k, inflated, tab


def nx_split():
    """NX school scan NX_SCAN split as the survey splits it (``guard_error_study.run_nx``):
    scan a = the first half and the even overlap points, scan b = the odd overlap points
    and the second half, × 0.8; the true δ is ln 1.25."""
    from lss_core.experiment import Experiment
    r = Experiment(G.NX).reflectivity([6, 7, 8, 9], errors='budget')
    s = dict(zip(r.order, patching.scans_from_reflectivity(r)))[NX_SCAN]
    h = len(s.q) // 2
    ov = np.arange(h - 4, h + 4)
    ia = np.concatenate([np.arange(0, h - 4), ov[0::2]])
    ib = np.concatenate([ov[1::2], np.arange(h + 4, len(s.q))])
    return (s, patching.Scan(s.q[ia], s.y[ia], s.sigma[ia]),
            patching.Scan(s.q[ib], 0.8 * s.y[ib], 0.8 * s.sigma[ib]), math.log(1.25))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=OUT_DEFAULT)
    ap.add_argument('--reps', type=int, default=400, help='replicates of the smooth join in W4')
    ap.add_argument('--procs', type=int, default=os.cpu_count() or 1)
    o = ap.parse_args(argv)
    os.makedirs(o.out, exist_ok=True)
    patching.GUARD_P = G.GUARD
    warnings.simplefilter('ignore')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    nums = dict(guard_p=G.GUARD, hidden_scatter=X, replicate=REP, reps=o.reps)

    # W1: the input, and the factor read off the shared points
    a0, b0, t = noisy(SMOOTH, REP, 0.0)
    a2, b2, _ = noisy(SMOOTH, REP, X)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw=dict(width_ratios=[1.5, 1]))
    ax.errorbar(a0.q, a0.y, a0.sigma, fmt='o', ms=3, color=BLUE, label='scan a (lower Qz)')
    ax.errorbar(b0.q, b0.y, b0.sigma, fmt='s', ms=3, color=ORANGE, label='scan b (higher Qz, fewer absorbers)')
    ax.axvspan(max(a0.q.min(), b0.q.min()), min(a0.q.max(), b0.q.max()), color='0.9', label='the overlap')
    ax.set_yscale('log')
    ax.set_xlabel('Qz (Å⁻¹)')
    ax.set_ylabel('intensity per monitor count (arb. units)')
    ax.set_title('(a) the two scans as reduced (Poisson noise only)', fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    ratios = {}
    for (sa, sb, lab, col, dx) in ((a0, b0, 'Poisson noise only', BLUE, -0.0002),
                                   (a2, b2, '+ %.0f %% hidden scatter' % (100 * X), RED, 0.0002)):
        q, lr, er = shared_ratio(sa, sb)
        bx.errorbar(q + dx, lr, er, fmt='o', ms=4, color=col, capsize=2, label=lab)
        ratios[lab] = dict(q=q.tolist(), ln_ratio=lr.tolist(), err=er.tolist())
    bx.axhline(t, color='k', lw=0.8, ls='--', label='the true δ')
    bx.set_xlabel('Qz (Å⁻¹) of the points both scans measured')
    bx.set_ylabel('δ read off one point: ln(R_a / R_b)')
    bx.set_title('(b) the factor, point by point', fontsize=9)
    bx.legend(fontsize=7, frameon=False)
    fig.suptitle('W1. The join\'s input: scan b must be multiplied by e^δ to lie on scan a (true δ = %.4f, a factor %.4f)'
                 % (t, math.exp(t)), fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(o.out, 'W1_input_and_shared_points.png'), dpi=A.DPI)
    plt.close(fig)
    nums['w1'] = dict(true_delta=t, factor=math.exp(t), shared_points=ratios)

    # W2: the unguarded fit (order 4, 2 either side), clean and noisy
    f0 = patching.rung_fit(a0, b0, 4, patching.N_EXT)
    f2 = patching.rung_fit(a2, b2, 4, patching.N_EXT)
    red = fit_panels(plt, ((a0, b0, f0, 'Poisson noise only: the curve passes through both scans'),
                           (a2, b2, f2, '+ %.0f %% hidden scatter: the points stray beyond their bars' % (100 * X))),
                     'W2. The joint fit: one smooth curve in ln(R/R_F) through both scans at once, scan b scaled by the '
                     'fitted factor e^δ', os.path.join(o.out, 'W2_joint_fit.png'))
    nums['w2'] = dict(clean=dict(chi2_dof=red[0], p=p_value(f0), delta=f0.delta, err=f0.err_counting, dof=f0.dof),
                      noisy=dict(chi2_dof=red[1], p=p_value(f2), delta=f2.delta, err=f2.err_counting, dof=f2.dof))

    # W3: the guard's ladder on both: linear p for the clean join, log p for the noisy one
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    w3 = {}
    for ax, (sa, sb, lab, col, mk, log) in zip(axes, ((a0, b0, 'Poisson noise only', BLUE, 'o', False),
                                                      (a2, b2, '+ %.0f %% hidden scatter' % (100 * X), RED, 's', True))):
        lad, ps, k, inflated, tab = ladder(sa, sb)
        xs = np.arange(len(ps))
        plot = ax.semilogy if log else ax.plot
        plot(xs, np.maximum(ps, 1e-30), mk + '-', color=col, ms=5, lw=0.8)
        plot([k], [max(ps[k], 1e-30)], mk, ms=13, mfc='none', mec=GREEN, mew=2, label='the curve the guard keeps')
        ax.axhline(G.GUARD, color=RED, lw=1, label='the guard asks for p ≥ %.1f' % G.GUARD)
        ax.set_ylim((1e-22, 5) if log else (0, 1))
        ax.set_xticks(range(len(lad)))
        ax.set_xticklabels(['order %d, ±%d' % r for r in lad], rotation=35, ha='right', fontsize=7)
        d, ec, c2, dof = tab['rungs'][k]
        err = unc.inflate(ec, c2, dof)
        ax.set_title('%s: %s; kept order %d, ±%d,\nχ²/dof %.2f, error %.4f%s' % (
            lab, 'one curve passes' if not inflated else 'none reaches %.1f' % G.GUARD, lad[k][0], lad[k][1],
            c2 / dof, err, ' (inflated ×%.1f)' % (err / ec) if err > ec * 1.0001 else ' (not inflated)'), fontsize=8)
        w3[lab] = dict(p=ps, kept=list(lad[k]), kept_index=int(k), passed=not inflated, delta=d, err_counting=ec,
                       err_reported=err, chi2_dof=c2 / dof if dof else None)
    axes[0].set_ylabel('χ² p-value of that curve')
    axes[0].legend(fontsize=7, frameon=False, loc='lower left')
    fig.suptitle('W3. The guard\'s ladder: it tries the curves left to right and keeps the first with p ≥ %.1f, '
                 'or, if none, the best one, its error inflated by √(χ²/dof) when above 1' % G.GUARD, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(o.out, 'W3_ladder.png'), dpi=A.DPI)
    plt.close(fig)
    nums['w3'] = w3

    # W4: pulls over replicates, today's rule vs the honest per-point budget
    tabs = A._pmap(G._task, [(SMOOTH, rep, X) for rep in range(o.reps)], o.procs)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    xx = np.linspace(-5, 5, 200)
    for ax, rule, title, col in zip(axes, ('own', 'budget'), ('today\'s rule', 'honest per-point errors'), (BLUE, GOLD)):
        est = [G.rule_estimate(tb, rule) for tb in tabs]
        ok = [(e, tb) for e, tb in zip(est, tabs) if e is not None]
        pulls = np.array([(e[0] - tb['truth']) / e[1] for e, tb in ok])
        errs = np.array([e[1] for e, _ in ok])
        devs = np.array([e[0] - tb['truth'] for e, tb in ok])
        ax.hist(np.clip(pulls, -5, 5), bins=np.linspace(-5, 5, 41), density=True, color=col, alpha=0.85)
        ax.plot(xx, np.exp(-xx ** 2 / 2) / math.sqrt(2 * math.pi), 'k-', lw=1, label='honest errors: the standard normal')
        sd, c1, c2 = float(np.std(pulls, ddof=1)), float(np.mean(np.abs(pulls) < 1)), float(np.mean(np.abs(pulls) < 2))
        ax.set_title('%s: pull SD %.2f\ninside ±1 error: %.0f %% (honest: 68 %%); inside ±2: %.0f %% (95 %%)'
                     % (title, sd, 100 * c1, 100 * c2), fontsize=8)
        ax.set_xlabel('pull = (fitted δ − true δ) / the error it reports')
        nums['w4_' + rule] = dict(pull_sd=sd, cover1=c1, cover2=c2, n=int(len(pulls)),
                                  median_err=float(np.median(errs)), true_spread=float(np.std(devs, ddof=1)),
                                  mean_pull=float(np.mean(pulls)))
    nums['w4_climb'] = float(np.mean([(A.guard_pick(tb, G.GUARD)[0] or 0) > 0 for tb in tabs]))
    axes[0].set_ylabel('share of replicates (density)')
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle('W4. %d replicates of the smooth join with %.0f %% hidden scatter: how far is each fitted δ from the '
                 'truth, in units of its own error?' % (o.reps, 100 * X), fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(o.out, 'W4_pulls.png'), dpi=A.DPI)
    plt.close(fig)

    # W5: a fringed join, no hidden scatter: order 4 misses the fringe
    af, bf, tf, _r, _m = A.draw_join(FRINGED, REP)
    lad, ps, kf, inflated, tabf = ladder(af, bf)
    of, ef = lad[kf]
    f4 = patching.rung_fit(af, bf, 4, patching.N_EXT)
    fk = patching.rung_fit(af, bf, of, ef)
    red5 = fit_panels(plt, ((af, bf, f4, 'unguarded (order 4, ±2): the curve cannot follow the fringe'),
                            (af, bf, fk, 'the guard\'s choice (order %d, ±%d)' % (of, ef))),
                      'W5. A join that a Kiessig fringe crosses (Poisson noise only): the large χ² on the left is the '
                      'curve missing, not noise', os.path.join(o.out, 'W5_fringed_join.png'))
    infl4 = unc.inflate(1.0, f4.chi2, f4.dof)
    nums['w5'] = dict(true_delta=tf, order4=dict(chi2_dof=red5[0], delta=f4.delta, inflation=infl4),
                      kept=dict(rung=[of, ef], chi2_dof=red5[1], delta=fk.delta,
                                err=unc.inflate(fk.err_counting, fk.chi2, fk.dof), err_ref=fk.err_counting * infl4))

    # W6: a real join with known truth (NX school, public)
    s, an, bn, tn = nx_split()
    lad, ps, kn, inflated, tabn = ladder(an, bn)
    on, en = lad[kn]
    fn = patching.rung_fit(an, bn, on, en)
    errn = unc.inflate(fn.err_counting, fn.chi2, fn.dof)
    fig = plt.figure(figsize=(10, 5.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1.3], hspace=0.08, width_ratios=[1, 1.1])
    ax = fig.add_subplot(gs[:, 0])
    ax.errorbar(an.q, an.y, an.sigma, fmt='o', ms=3, color=BLUE, label='half a')
    ax.errorbar(bn.q, bn.y, bn.sigma, fmt='s', ms=3, color=ORANGE, label='half b, × 0.8')
    ax.set_yscale('log')
    ax.set_xlabel('Qz (Å⁻¹)')
    ax.set_ylabel('R (as reduced, errors from the budget)')
    ax.set_title('(a) NX school scan %d, %d points, split in two' % (NX_SCAN, len(s.q)), fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    rax = fig.add_subplot(gs[1, 1])
    fx = fig.add_subplot(gs[0, 1], sharex=rax)
    red6 = draw_fit(fx, rax, an, bn, fn, '(b) the join, by today\'s default (order %d, ±%d)' % (on, en))
    pull = (fn.delta - tn) / errn
    fx.text(0.02, 0.06, 'fitted δ %.4f ± %.4f; true δ = ln 1.25 = %.4f\npull %.2f' % (fn.delta, errn, tn, pull),
            transform=fx.transAxes, fontsize=8)
    fig.suptitle('W6. A real join with known truth: one public scan cut into two interleaved halves, the second '
                 'scaled by 0.8', fontsize=9)
    fig.savefig(os.path.join(o.out, 'W6_real_split.png'), dpi=A.DPI, bbox_inches='tight')
    plt.close(fig)
    nums['w6'] = dict(scan=NX_SCAN, points=int(len(s.q)), rung=[on, en], passed=not inflated, p=ps[kn], chi2_dof=red6,
                      delta=fn.delta, err=errn, true_delta=tn, pull=pull)

    with open(os.path.join(o.out, 'numbers.json'), 'w') as f:
        json.dump(nums, f, indent=1, default=float)
    print(json.dumps({k: v for k, v in nums.items() if k != 'w1'}, indent=1, default=float))


if __name__ == '__main__':
    main()
