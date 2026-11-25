"""Study of the dose-or-time test (F76; lss_core.reciprocity; main man
2026-11-24, rule 12): synthetic burns at several fluxes with a known law
of change, how often each truth is called right; NX school burns 14 and
15 as the public real check.

    python tests/tools/reciprocity_study.py --out docs/studies/reciprocity          # about 1 min
    python tests/tools/reciprocity_study.py --out DIR --design span,strip --replicates 1000
    python tests/tools/reciprocity_study.py --out DIR --only R1,R5                   # the figures that need no run

The truth (``tests/synthetic/burn_pairs.py``): burn b at flux φ_b falls as
exp(−λ₁ φ_b^β t), λ₁ from ``change`` (the fall over the burn at the lowest
flux), Gaussian noise per frame, an optional strip-to-strip scatter of the
rate. Truths: ``dose`` (β = 1), ``time`` (β = 0), ``half`` (β = 0.5),
``steep`` (β = 2), ``mix`` (a dose and a time process, equal at the lowest
flux) and ``none`` (no change). The right call: 'dose', 'time', 'neither'
for half, steep and mix (no single pure law), 'no change' for none.

Designs (``--design``, comma-separated, or 'all'), each from the baseline
(two burns ×4.68 apart as NX 14 and 15, 21 frames of 10 s, 1 % noise per
frame, a 5 % fall at the lower flux, no strip scatter):

- ``span``: the flux ratio of two burns, ×2, ×4.68, ×10, ×20;
- ``burns``: 2, 3 or 4 burns over ×10;
- ``frames``: 11, 21, 41 frames;
- ``noise``: 0.3 %, 1 %, 3 % per frame;
- ``change``: a 2 %, 5 % or 20 % fall at the lower flux;
- ``strip``: a strip-to-strip scatter of the rate of 20 % and 50 % (four
  burns over ×8), analysed without it, as one constant τ (the scatter at
  the median rate) and as a relative ρ (the truth's own form).

Figures: R1 the anatomy (two burns against time and against dose, under a
dose truth and a time truth, and χ²(β)); R2 the share of each verdict per
truth and design; R3 β̂'s pulls and the coverage of its Δχ² = 1 interval;
R4 the strip scatter ignored and admitted; R5 NX school burns 14 and 15.
Tables: ``results.csv``, ``numbers.json``.
"""
import argparse
import csv
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from lss_core import reciprocity as R                 # noqa: E402
from synthetic import burn_pairs as bp                # noqa: E402

NX = 'sample_data/NX_school/2026sep/20260923'
TRUTHS = {'dose': dict(beta=1.0), 'time': dict(beta=0.0), 'half': dict(beta=0.5), 'steep': dict(beta=2.0),
          'mix': dict(beta=1.0, mixture=(0.5, 0.5)), 'none': dict(beta=None)}
RIGHT = {'dose': 'dose', 'time': 'time', 'half': 'neither', 'steep': 'neither', 'mix': 'neither', 'none': 'no change'}
BASE = dict(fluxes=(1.0, 4.68), frames=21, noise=0.01, change=0.05, strip=0.0)
DESIGNS = ('span', 'burns', 'frames', 'noise', 'change', 'strip')
COLOURS = {'dose': 'C3', 'time': 'C0', 'cannot tell': '0.75', 'neither': 'C1', 'no change': '0.45',
           'opposite signs': 'C4'}


def conditions(designs):
    out = []
    for d in designs:
        if d == 'span':
            out += [(d, '×%g' % r, dict(fluxes=(1.0, r)), False) for r in (2.0, 4.68, 10.0, 20.0)]
        elif d == 'burns':
            out += [(d, '%d burns' % n, dict(fluxes=tuple(np.round(np.geomspace(1, 10, n), 3))), False) for n in (2, 3, 4)]
        elif d == 'frames':
            out += [(d, '%d frames' % n, dict(frames=n), False) for n in (11, 21, 41)]
        elif d == 'noise':
            out += [(d, '%g %%' % (100 * n), dict(noise=n), False) for n in (0.003, 0.01, 0.03)]
        elif d == 'change':
            out += [(d, '%g %% fall' % (100 * c), dict(change=c), False) for c in (0.02, 0.05, 0.2)]
        elif d == 'strip':
            for s in (0.2, 0.5):
                out += [(d, 'strip %g, ignored' % s, dict(strip=s, fluxes=(1.0, 2.0, 4.0, 8.0)), False),
                        (d, 'strip %g, as τ' % s, dict(strip=s, fluxes=(1.0, 2.0, 4.0, 8.0)), 'tau'),
                        (d, 'strip %g, as ρ' % s, dict(strip=s, fluxes=(1.0, 2.0, 4.0, 8.0)), 'rho')]
        else:
            raise SystemExit('unknown design %r: %s' % (d, ', '.join(DESIGNS)))
    return out


def run(designs, reps):
    rows, summary = [], []
    for ci, (design, label, over, admit) in enumerate(conditions(designs)):
        kw = dict(BASE, **over)
        for ti, (truth, tk) in enumerate(TRUTHS.items()):
            calls = {v: 0 for v in R.VERDICTS}
            betas, pulls, cover = [], [], []
            for rep in range(reps):
                burns, tr = bp.series(seed=[2026, 11, 25, ci, ti, rep], **kw, **tk)
                tau = rho = 0.0
                if admit == 'tau' and kw['strip']:      # one constant: the strip scatter at the median rate
                    tau = kw['strip'] * float(np.median(np.abs(tr['rates']))) if any(tr['rates']) else 0.0
                elif admit == 'rho':                     # the true relative scatter
                    rho = kw['strip']
                v = R.dose_or_time(burns, strip_scatter=tau, strip_relative=rho)
                calls[v.verdict] += 1
                if tk.get('mixture') is None and tk['beta'] is not None and np.isfinite(v.beta):
                    lo, hi = v.beta_ci
                    betas.append(v.beta)
                    open_ = lo <= R.BETA_GRID[0] or hi >= R.BETA_GRID[-1]
                    if not open_ and hi > lo:
                        pulls.append((v.beta - tk['beta']) / ((hi - lo) / 2))
                    cover.append(lo <= tk['beta'] <= hi)
            row = dict(design=design, condition=label, truth=truth, n=reps, right=calls[RIGHT[truth]] / reps,
                       **{'share_' + k.replace(' ', '_'): calls[k] / reps for k in R.VERDICTS},
                       beta_mean=float(np.mean(betas)) if betas else math.nan,
                       beta_sd=float(np.std(betas, ddof=1)) if len(betas) > 1 else math.nan,
                       pull_mean=float(np.mean(pulls)) if pulls else math.nan,
                       pull_sd=float(np.std(pulls, ddof=1)) if len(pulls) > 1 else math.nan,
                       coverage=float(np.mean(cover)) if cover else math.nan)
            rows.append(row)
    return rows


def _write(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.4g' % v if isinstance(v, float) else v) for k, v in r.items()})


def _plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    return plt


def r1(out):
    plt = _plt()
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for row, (truth, title) in enumerate((('dose', 'damage by the beam (β = 1)'), ('time', 'the sample by itself (β = 0)'))):
        burns, tr = bp.series(seed=[2026, row], fluxes=(1.0, 4.68), change=0.1, noise=0.005, **TRUTHS[truth])
        v = R.dose_or_time(burns)
        for b, col in zip(burns, ('C0', 'C3')):
            axes[row, 0].errorbar(b.t, b.y, b.sigma, fmt='o', ms=3, color=col, label='flux ×%g' % b.flux)
            axes[row, 1].errorbar(b.t * b.flux, b.y, b.sigma, fmt='o', ms=3, color=col)
        axes[row, 0].set_title('%s: against time' % title, fontsize=9)
        axes[row, 1].set_title('the same against dose (flux × time)', fontsize=9)
        axes[row, 0].set_xlabel('time (s)')
        axes[row, 1].set_xlabel('dose (flux × s, lowest flux = 1)')
        axes[row, 0].set_ylabel('I / I(0)')
        axes[row, 0].legend(fontsize=7)
        axes[row, 2].plot(v.grid, v.chi2 - v.chi2.min(), 'k')
        axes[row, 2].axhline(1, color='0.6', ls=':')
        axes[row, 2].axhline(3.84, color='0.6', ls='--')
        for x, c in ((0, 'C0'), (1, 'C3')):
            axes[row, 2].axvline(x, color=c, lw=0.8)
        axes[row, 2].set_ylim(0, 30)
        axes[row, 2].set_xlabel('β (rate ∝ flux^β)')
        axes[row, 2].set_ylabel('χ²(β) − min')
        axes[row, 2].set_title('verdict: %s; β = %.2f [%.2f, %.2f]' % (v.verdict, v.beta, *v.beta_ci), fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R1_anatomy.png'), dpi=100)
    plt.close(fig)


def r2(rows, out):
    plt = _plt()
    designs = [d for d in DESIGNS if any(r['design'] == d for r in rows)]
    truths = list(TRUTHS)
    fig, axes = plt.subplots(len(truths), len(designs), figsize=(3.2 * len(designs), 2.2 * len(truths)), squeeze=False)
    for j, d in enumerate(designs):
        conds = []
        for r in rows:
            if r['design'] == d and r['condition'] not in conds:
                conds.append(r['condition'])
        for i, t in enumerate(truths):
            ax = axes[i][j]
            base = np.zeros(len(conds))
            for v in R.VERDICTS:
                h = np.array([next(r['share_' + v.replace(' ', '_')] for r in rows
                                   if r['design'] == d and r['condition'] == c and r['truth'] == t) for c in conds])
                ax.bar(range(len(conds)), h, bottom=base, color=COLOURS[v], label=v if (i == 0 and j == 0) else None)
                base += h
            ax.set_ylim(0, 1)
            ax.set_xticks(range(len(conds)))
            ax.set_xticklabels(conds if i == len(truths) - 1 else [], rotation=35, ha='right', fontsize=6)
            ax.tick_params(labelsize=6)
            if j == 0:
                ax.set_ylabel('truth: %s\n(right: %s)' % (t, RIGHT[t]), fontsize=7)
            if i == 0:
                ax.set_title(d, fontsize=9)
    fig.legend(loc='upper center', ncol=6, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(os.path.join(out, 'R2_calls.png'), dpi=100)
    plt.close(fig)


def r3(rows, out):
    plt = _plt()
    sel = [r for r in rows if r['truth'] in ('dose', 'time', 'half', 'steep') and np.isfinite(r['pull_sd'])]
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.2))
    lab = ['%s · %s' % (r['condition'], r['truth']) for r in sel]
    a.plot(range(len(sel)), [r['pull_sd'] for r in sel], 'o', ms=3)
    a.axhline(1, color='k', lw=0.6)
    a.set_ylabel('SD of (β̂ − β) / half-width of the Δχ² = 1 interval')
    b.plot(range(len(sel)), [r['coverage'] for r in sel], 'o', ms=3, color='C2')
    b.axhline(0.683, color='k', lw=0.6)
    b.set_ylabel('coverage of the Δχ² = 1 interval (0.683 ideal)')
    for ax in (a, b):
        ax.set_xticks(range(len(sel)))
        ax.set_xticklabels(lab, rotation=90, fontsize=4)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R3_beta_pulls.png'), dpi=100)
    plt.close(fig)


def r4(rows, out):
    plt = _plt()
    sel = [r for r in rows if r['design'] == 'strip']
    if not sel:
        return
    conds = []
    for r in sel:
        if r['condition'] not in conds:
            conds.append(r['condition'])
    fig, ax = plt.subplots(figsize=(10, 4))
    for k, t in enumerate(TRUTHS):
        ax.plot(range(len(conds)), [next(r['right'] for r in sel if r['condition'] == c and r['truth'] == t)
                                    for c in conds], 'o-', label='%s (right: %s)' % (t, RIGHT[t]))
    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels(conds, fontsize=8)
    ax.set_ylabel('share called right')
    ax.set_ylim(0, 1)
    ax.set_title('Four burns over ×8 with strip-to-strip scatter of the rate: ignored, as a constant τ, as a relative ρ',
                 fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R4_strip.png'), dpi=100)
    plt.close(fig)


def nx_check(out, spec=NX):
    plt = _plt()
    from lss_core.experiment import Experiment
    e = Experiment(spec)
    res = [e.burn(14), e.burn(15)]
    numbers = {}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    for ax, q in zip(axes, ('centre', 'fwhm', 'intensity')):
        burns = [R.from_result(r, q) for r in res]
        v = R.dose_or_time(burns)
        tau = 0.1 * max(abs(x[2]) for x in v.rates)
        v10 = R.dose_or_time(burns, strip_scatter=tau)
        numbers[q] = dict(verdict=v.verdict, beta=v.beta, beta_ci=v.beta_ci, weight_dose=v.weight_dose,
                          p_dose=v.p_dose, p_time=v.p_time, rates=v.rates, note=v.note,
                          with_10pc_strip=dict(verdict=v10.verdict, beta_ci=v10.beta_ci, note=v10.note))
        phi = np.array([x[1] for x in v.rates])
        rr = np.array([x[2] for x in v.rates])
        er = np.array([x[3] for x in v.rates])
        ax.errorbar(phi / phi.min(), rr, er, fmt='o', color='k')
        xx = np.linspace(1, phi.max() / phi.min(), 50)
        gm = float(np.exp(np.mean(np.log(phi / phi.min()))))
        for beta, col, lab in ((1.0, 'C3', 'β = 1 (the dose)'), (0.0, 'C0', 'β = 0 (time)'),
                               (v.beta, 'k', 'β̂ = %.2f' % v.beta)):
            k = float(R._profile((phi / phi.min()) / gm, rr, er, np.array([beta]))[1][0])
            ax.plot(xx, k * (xx / gm) ** beta, color=col, ls='--' if col == 'k' else '-', label=lab + ', fitted')
        ax.set_xlabel('flux (×, burn 14 = 1)')
        ax.set_ylabel('drift rate (per s%s)' % ('' if q != 'centre' else '; Å⁻¹'))
        ax.set_title('%s: %s, β = %.2f [%.2f, %.2f]' % (q, v.verdict, v.beta, *v.beta_ci), fontsize=9)
        ax.legend(fontsize=7)
    fig.suptitle('NX school burns 14 and 15 (absorbers 12 and 8; one spot, 15 after 14)', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'R5_nx.png'), dpi=100)
    plt.close(fig)
    return numbers


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--design', default='all', help='comma-separated: %s, or all' % ', '.join(DESIGNS))
    ap.add_argument('--replicates', type=int, default=300)
    ap.add_argument('--only', default=None, help='figures only: R1, R5 (no run)')
    ap.add_argument('--spec', default=NX, help='the SPEC file of the real check (burns 14 and 15)')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    numbers = {}
    if a.only:
        want = set(a.only.split(','))
        if 'R1' in want:
            r1(a.out)
        if 'R5' in want and os.path.exists(a.spec):
            numbers['nx'] = nx_check(a.out, a.spec)
        with open(os.path.join(a.out, 'numbers_only.json'), 'w', encoding='utf-8') as f:
            json.dump(numbers, f, indent=1, default=str)
        return 0
    designs = DESIGNS if a.design == 'all' else tuple(a.design.split(','))
    rows = run(designs, a.replicates)
    _write(os.path.join(a.out, 'results.csv'), rows)
    r1(a.out)
    r2(rows, a.out)
    r3(rows, a.out)
    r4(rows, a.out)
    if os.path.exists(a.spec):
        numbers['nx'] = nx_check(a.out, a.spec)
    numbers['settings'] = dict(designs=list(designs), replicates=a.replicates, base=BASE)
    numbers['results'] = rows
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(numbers, f, indent=1, default=str)
    for r in rows:
        print('%-7s %-20s %-6s right %.2f  dose %.2f time %.2f cannot %.2f neither %.2f none %.2f  β %.2f pull %.2f cov %.2f' % (
            r['design'], r['condition'], r['truth'], r['right'], r['share_dose'], r['share_time'], r['share_cannot_tell'],
            r['share_neither'], r['share_no_change'], r['beta_mean'], r['pull_sd'], r['coverage']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
