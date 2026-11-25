"""The dose-or-time test (F76) from the raw frames to the judgment, step by
step, for the walkthrough (docs/studies/reciprocity/walkthrough.md; the
owner's standing order of 2026-11-25: "the entire chain of data
processing, ending with the statistics and judgment ... data fit examples,
explanations of statistics, all ELI5").

Public data only: the NX school GID burns 14 and 15 (frames, line cuts,
per-frame positions, drift fits, the rates against flux), C54's public,
anonymised table of real reflectivity burn rates (the strip scatter and one
real series), and synthetic burns with a known truth (calibration).

Figures (``--out``):
- W1 the raw data: one detector frame of burn 14 with the rows summed, and
  the line cut of the first and last frame with the window;
- W2 one number per frame: the peak position of every frame of 14 and 15,
  with its error bar;
- W3 the drift of one burn: the straight line through those positions, its
  slope and the residuals (in error bars);
- W4 across burns: the two rates against flux with the two pure laws and
  the best β, and χ²(β) with its interval;
- W5 the strip scatter: C54's six repeat groups (rates that should agree
  and do not) and the likelihood of τ and ρ;
- W6 calibration: 60 synthetic replicates' intervals against the truth.

    python tests/tools/reciprocity_walkthrough.py --out docs/studies/reciprocity/walkthrough
"""
import argparse
import csv
import io
import json
import math
import os
import sys
from collections import OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
os.chdir(ROOT)

import numpy as np                                    # noqa: E402

from lss_core import reciprocity as R                  # noqa: E402

NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
BURNS = os.path.join(ROOT, 'docs', 'studies', 'xr_burns', 'burns.csv')
C14, C15 = '#1f6fb4', '#c0392b'


def plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as p
    return p


def nx_burns():
    from lss_core.experiment import Experiment
    e = Experiment(NX)
    return e, e.burn(14), e.burn(15)


def w1(out, e, r14):
    """The raw data: frame 0 of burn 14, the summed rows, the line cuts."""
    from lss_core import images
    p = plt()
    fr = [f for f in e.frames([14]) if f.index == 0][0]
    img = np.asarray(images.read_pilatus(fr.path), float)
    fig, (a, b) = p.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1]))
    a.imshow(np.log10(np.maximum(img, 0.5)), origin='lower', aspect='auto', cmap='viridis')
    lo, hi = r14.rows
    a.axhline(lo, color='w', lw=1)
    a.axhline(hi, color='w', lw=1)
    a.set_title('(a) Burn 14, frame 0: counts per pixel (log scale)\nrows %d–%d between the white lines are summed' %
                (lo, hi), fontsize=9)
    a.set_xlabel('detector column')
    a.set_ylabel('detector row')
    p0, p1 = r14.profiles[0], r14.profiles[-1]
    b.errorbar(p0[:, 0], p0[:, 1], p0[:, 2], fmt='.', ms=3, color='0.4', label='frame 0 (first)')
    b.errorbar(p1[:, 0], p1[:, 1], p1[:, 2], fmt='.', ms=3, color=C14, label='frame %d (last)' % (len(r14.profiles) - 1))
    w0, w1_ = r14.window
    b.axvspan(w0, w1_, color='orange', alpha=0.15, label='window: 3 FWHM either side of the peak')
    b.set_yscale('log')
    b.set_xlabel('Qxy (Å⁻¹)')
    b.set_ylabel('counts per monitor (summed rows)')
    b.set_title('(b) The line cut: each column summed over the rows, ± √counts', fontsize=9)
    b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W1_raw_frame_and_cut.png'), dpi=130)
    p.close(fig)
    return dict(rows=[int(lo), int(hi)], window=[float(w0), float(w1_)], frames=len(r14.profiles))


def w2_w3(out, r14, r15):
    """One number per frame (the position), and the straight line through it."""
    p = plt()
    burns = [R.from_result(r, 'centre') for r in (r14, r15)]
    fig, axes = p.subplots(2, 2, figsize=(12, 6.4), gridspec_kw=dict(height_ratios=[3, 1.2]), sharex='col')
    info = []
    for col, (b, r, c, name) in enumerate(((burns[0], r14, C14, 'burn 14 (absorber 12)'),
                                           (burns[1], r15, C15, 'burn 15 (absorber 8, ×4.68 the flux)'))):
        ax, res = axes[0, col], axes[1, col]
        rate, sr = R.drift_rate(b)
        A = np.vstack([np.ones_like(b.t), b.t]).T
        w = 1 / b.sigma ** 2
        coef = np.linalg.solve(A.T @ (A * w[:, None]), A.T @ (w * b.y))
        fit = A @ coef
        chi2 = float(np.sum(((b.y - fit) / b.sigma) ** 2))
        dof = len(b.t) - 2
        ax.errorbar(b.t, b.y, b.sigma, fmt='o', ms=4, color=c, capsize=2, label='each frame: peak position ± σ')
        ax.plot(b.t, fit, 'k-', label='straight line, weighted by 1/σ²')
        ax.set_title('%s: slope %.3g ± %.2g Å⁻¹ per s\nχ²/dof = %.2f/%d = %.2f%s' % (
            name, rate, sr, chi2, dof, chi2 / dof, ' → σ ×√%.2f' % (chi2 / dof) if chi2 / dof > 1 else ''), fontsize=9)
        ax.set_ylabel('peak position (Å⁻¹)')
        ax.legend(fontsize=8, loc='upper left')
        res.axhline(0, color='k', lw=0.8)
        res.bar(b.t, (b.y - fit) / b.sigma, width=0.6 * np.median(np.diff(b.t)), color=c)
        res.set_ylabel('residual / σ')
        res.set_xlabel('time since the burn began (s)')
        info.append(dict(burn=name, rate=rate, sigma=sr, chi2=chi2, dof=dof, flux=b.flux))
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W3_drift_fits.png'), dpi=130)
    p.close(fig)
    # W2: the per-frame values alone, both burns on one time axis, before any fit
    fig, ax = p.subplots(figsize=(8, 4.2))
    for b, c, name in ((burns[0], C14, 'burn 14'), (burns[1], C15, 'burn 15 (×4.68 the flux)')):
        ax.errorbar(b.t, b.y, b.sigma, fmt='o', ms=4, color=c, capsize=2, label=name)
    ax.set_xlabel('time since each burn began (s)')
    ax.set_ylabel('peak position (Å⁻¹)')
    ax.set_title('One number per frame: the template fit\'s peak position, with its error', fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W2_per_frame_positions.png'), dpi=130)
    p.close(fig)
    return burns, info


def w4(out, burns):
    """Across burns: rate ∝ flux^β, the two laws, χ²(β)."""
    p = plt()
    v = R.dose_or_time(burns)
    phi = np.array([x[1] for x in v.rates])
    r = np.array([x[2] for x in v.rates])
    s = np.array([x[3] for x in v.rates])
    gm = float(np.exp(np.mean(np.log(phi))))
    x = phi / gm
    fig, (a, b) = p.subplots(1, 2, figsize=(12, 4.6))
    a.errorbar(phi / phi.min(), r, s, fmt='o', color='k', capsize=3, ms=6, label='the two drift rates (W3)')
    xx = np.linspace(0.8, 5.5, 100)
    for beta, col, lab in ((1.0, C15, 'β = 1: rate ∝ flux (the dose)'), (0.0, C14, 'β = 0: the same rate (time)'),
                           (v.beta, 'k', 'β̂ = %.2f (best)' % v.beta)):
        k = float(R._profile(x, r, s, np.array([beta]))[1][0])
        a.plot(xx, k * (xx * phi.min() / gm) ** beta, color=col, ls='--' if col == 'k' else '-', label=lab)
    a.set_xlabel('flux (burn 14 = 1)')
    a.set_ylabel('drift rate of the position (Å⁻¹ per s)')
    a.set_title('(a) Each law fitted to the two rates (its one free number k)', fontsize=9)
    a.legend(fontsize=8)
    c = v.chi2 - v.chi2.min()
    b.plot(v.grid, c, 'k')
    for lev, ls, lab in ((1.0, '--', 'Δχ² = 1: the 68 % interval'), (3.84, ':', 'Δχ² = 3.84: the 95 % interval')):
        b.axhline(lev, color='0.4', ls=ls, label=lab)
    b.axvline(0, color=C14, lw=0.8)
    b.axvline(1, color=C15, lw=0.8)
    b.set_ylim(0, 30)
    b.set_xlim(-0.5, 2.0)
    b.set_xlabel('β')
    b.set_ylabel('χ²(β) − its minimum')
    b.set_title('(b) How badly each β fits: β̂ %.2f [%.2f, %.2f]; p(β=1) %.2g, p(β=0) %.1e' % (
        v.beta, v.beta_ci[0], v.beta_ci[1], v.p_dose, v.p_time), fontsize=9)
    b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W4_rates_and_beta.png'), dpi=130)
    p.close(fig)
    tau = 0.1 * r[1]
    vs = R.dose_or_time(burns, strip_scatter=tau)
    return dict(verdict=v.verdict, beta=v.beta, ci=list(v.beta_ci), ci95=list(v.beta_ci95), p_dose=v.p_dose,
                p_time=v.p_time, weight_dose=v.weight_dose, chi2_at_1=float(v.chi2[np.argmin(abs(v.grid - 1))]),
                chi2_at_0=float(v.chi2[np.argmin(abs(v.grid))]), with_strip=dict(tau=tau, verdict=vs.verdict,
                                                                                beta=vs.beta, ci=list(vs.beta_ci),
                                                                                p_dose=vs.p_dose, p_time=vs.p_time))


def read_burns():
    with open(BURNS, encoding='utf-8') as f:
        return list(csv.DictReader(io.StringIO(''.join(ln for ln in f if not ln.startswith('"#')))))


def w5(out):
    """C54's six repeat groups and the likelihood of τ and ρ."""
    import reciprocity_real as RR
    p = plt()
    rows = read_burns()
    groups = RR.repeat_groups(rows)
    gl = list(groups.values())
    fig, (a, b, c) = p.subplots(1, 3, figsize=(15, 4.6), gridspec_kw=dict(width_ratios=[1.4, 1, 1]))
    for i, ((sid, ab), g) in enumerate(groups.items()):
        g = np.array(g)
        xs = i + np.linspace(-0.15, 0.15, len(g))
        a.errorbar(xs, g[:, 0], g[:, 1], fmt='o', capsize=3)
    a.axhline(0, color='k', lw=0.6)
    a.set_xticks(range(len(groups)))
    a.set_xticklabels(['%s\nabs. %s' % k for k in groups], fontsize=7)
    a.set_yscale('symlog', linthresh=30)
    a.set_ylabel('drift rate (% of I(0) per h), ± counting σ')
    a.set_title('(a) Same sample, same flux, different strips:\nthe rates should agree within their error bars',
                fontsize=9)
    tau_grid = np.linspace(0, 300, 301)
    rho_grid = np.linspace(0.01, 3, 300)
    lt = np.array([RR.nll(gl, t, False) for t in tau_grid])
    lr = np.array([RR.nll(gl, t, True) for t in rho_grid])
    tau, tci = R.strip_scatter_fit(gl)
    rho, rci = R.strip_scatter_fit(gl, relative=True)
    b.plot(tau_grid, lt, 'C0')
    b.axvline(tau, color='C0', ls='--')
    b.axhline(lt.min() + 0.5, color='0.5', ls=':')
    b.set_xlabel('τ: one extra scatter for every strip (% per h)')
    b.set_ylabel('−log likelihood (lower fits better)')
    b.set_title('(b) Additive: best τ = %.0f %%/h (%.0f–%.0f)\nminimum %.1f' % (tau, tci[0], tci[1], lt.min()),
                fontsize=9)
    c.plot(rho_grid, lr, 'C3')
    c.axvline(rho, color='C3', ls='--')
    c.axhline(lr.min() + 0.5, color='0.5', ls=':')
    c.set_xlabel('ρ: extra scatter as a share of the rate')
    c.set_title('(c) Relative: best ρ = %.2f (%.2f–%.2f)\nminimum %.1f: lower by %.1f' % (
        rho, rci[0], rci[1], lr.min(), lt.min() - lr.min()), fontsize=9)
    lim = (min(lt.min(), lr.min()) - 5, max(lt.max(), lr.max()) + 5)       # one scale: the two minima compared
    b.set_ylim(lim)
    c.set_ylim(lim)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W5_strip_scatter.png'), dpi=130)
    p.close(fig)
    return dict(tau=tau, tau_ci=list(tci), rho=rho, rho_ci=list(rci), nll_tau=float(lt.min()), nll_rho=float(lr.min()),
                nll_none=RR.nll(gl, 0.0, False), groups=len(gl))


def w5b(out, rho, tau, series='R05-S1'):
    """One real series under the three error models."""
    p = plt()
    rows = [b for b in read_burns() if b['series_id'] == series]
    phi = np.array([float(b['flux']) for b in rows])
    r = np.array([float(b['rate_t_drop1']) for b in rows])
    s = np.array([float(b['rate_t_drop1_err']) for b in rows])
    fig, axes = p.subplots(1, 3, figsize=(15, 4.4), sharey=True)
    out_v = {}
    for ax, (name, kw, err) in zip(axes, (('counting errors', {}, s),
                                          ('⊕ τ = %.0f %%/h' % tau, {'strip_scatter': tau}, np.sqrt(s ** 2 + tau ** 2)),
                                          ('⊕ ρ = %.2f of the rate' % rho, {'strip_relative': rho}, None))):
        v = R.dose_or_time_rates(phi, r, s, **kw)
        gm = float(np.exp(np.mean(np.log(phi))))
        k = v.k
        model = k * (phi / gm) ** v.beta
        e = err if err is not None else np.sqrt(s ** 2 + (rho * model) ** 2)
        ax.errorbar(phi / phi.min(), r, e, fmt='o', color='k', capsize=3)
        xx = np.geomspace(0.9, phi.max() / phi.min() * 1.1, 80)
        ax.plot(xx, k * (xx * phi.min() / gm) ** v.beta, 'k--')
        ax.set_xscale('log')
        ax.set_xlabel('flux (lowest = 1)')
        ax.set_title('%s: %s\nβ̂ %.2f [%.2f, %.2f]' % (name, v.verdict, v.beta, v.beta_ci[0], v.beta_ci[1]), fontsize=9)
        out_v[name] = dict(verdict=v.verdict, beta=v.beta, ci=list(v.beta_ci))
    axes[0].set_ylabel('drift rate (% of I(0) per h)')
    fig.suptitle('One real series (%s, C54\'s public rates): the error bars decide what can be told' % series, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W5b_one_real_series.png'), dpi=130)
    p.close(fig)
    return out_v


def w6(out, n=60, rho=0.3):
    """Calibration: do the intervals hold the truth as often as they say?"""
    from synthetic import burn_pairs as bp
    p = plt()
    fig, ax = p.subplots(figsize=(8, 7))
    hit = 0
    for seed in range(n):
        burns, _ = bp.series(beta=1.0, fluxes=(1.0, 2.0, 4.0, 8.0), change=0.1, noise=0.001, strip=rho, seed=seed)
        v = R.dose_or_time(burns, strip_relative=rho)
        ok = v.beta_ci[0] <= 1.0 <= v.beta_ci[1]
        hit += ok
        ax.plot(v.beta_ci, [seed, seed], color='k' if ok else C15, lw=2)
        ax.plot(v.beta, seed, 'o', ms=3, color='k' if ok else C15)
    ax.axvline(1.0, color=C14, lw=1.5, label='the truth, β = 1')
    ax.set_xlabel('β̂ and its 68 % interval')
    ax.set_ylabel('replicate (a new draw of the noise and the strips)')
    ax.set_title('%d replicates, 4 burns over ×8, %d %% strip scatter: %d of %d intervals hold the truth (%.0f %%; '
                 '68 %% promised)\nred: the ones that miss' % (n, 100 * rho, hit, n, 100 * hit / n), fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'W6_calibration.png'), dpi=130)
    p.close(fig)
    cover = {}
    for r_ in (0.3, 1.0):                               # the coverage the text quotes, over more replicates
        c68 = c95 = 0
        for seed in range(300):
            burns, _ = bp.series(beta=1.0, fluxes=(1.0, 2.0, 4.0, 8.0), change=0.1, noise=0.001, strip=r_, seed=seed)
            v = R.dose_or_time(burns, strip_relative=r_)
            c68 += v.beta_ci[0] <= 1.0 <= v.beta_ci[1]
            c95 += v.beta_ci95[0] <= 1.0 <= v.beta_ci95[1]
        cover['rho %.1f' % r_] = dict(replicates=300, coverage68=c68 / 300, coverage95=c95 / 300)
    return dict(replicates=n, rho=rho, covered=hit, coverage=cover)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/reciprocity/walkthrough', help='output folder')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))
    e, r14, r15 = nx_burns()
    n = OrderedDict()
    n['W1'] = w1(a.out, e, r14)
    burns, n['W3'] = w2_w3(a.out, r14, r15)
    n['W4'] = w4(a.out, burns)
    n['W5'] = w5(a.out)
    n['W5b'] = w5b(a.out, n['W5']['rho'], n['W5']['tau'])
    n['W6'] = w6(a.out)
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(n, f, indent=1, default=float)
    print(json.dumps(n, indent=1, default=float))
    return 0


if __name__ == '__main__':
    sys.exit(main())
