"""F76 on real burns: ``reciprocity.dose_or_time_rates`` on C54's 19 series,
with the strip scatter fitted from its six repeat groups (tools man,
2026-11-25, for main man: "compare reciprocity.dose_or_time with C54's 19
real series ... C54 needs its own ρ, given its measured 88 %/h strip
scatter").

Input: the non-cloud agent's public, anonymised tables
(``docs/studies/xr_burns/burns.csv``: one row per burn, its flux and the
drift rate of I/I(0) in % per hour with frame 1 left out; and
``series_dose_or_time.csv``: C54's own verdicts). Nothing private is read.

1. The strip scatter, from the burns that repeat an absorber within a
   series (``strip_scatter_fit``, REML): additive τ (C54's form) and
   relative ρ (a share of the rate, the reciprocity study's better form).
2. Each series' verdict and β under counting errors only, ⊕ τ and ⊕ ρ,
   beside C54's "drop1" and "drop1+strip" rows.

3. How many strips per flux would tell dose from time at that ρ
   (synthetic, ``design.csv``).

Writes ``comparison.csv`` (per series), ``numbers.json`` (the fits, the
tallies, the design) and ``R6_real_beta.png`` (β with its interval per
series, three error models, C54's β) to ``--out``.

    python tests/tools/reciprocity_real.py --out docs/studies/reciprocity/c54
"""
import argparse
import csv
import io
import json
import os
import sys
from collections import Counter, OrderedDict, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import numpy as np                                    # noqa: E402

from lss_core import reciprocity as R                  # noqa: E402

BURNS = 'docs/studies/xr_burns/burns.csv'
SERIES = 'docs/studies/xr_burns/series_dose_or_time.csv'
C54_WORDS = {'dose (beam damage)': 'dose', 'time (the sample changes by itself)': 'time',
             'both fit: cannot tell': 'cannot tell', 'neither fits (p < 0.05 at beta 0 and 1)': 'neither',
             'rises and falls: neither one process': 'opposite signs',
             'no burn changes by 3 sigma: cannot tell': 'no change'}


def read_table(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return list(csv.DictReader(io.StringIO(''.join(ln for ln in f if not ln.startswith('"#')))))


def repeat_groups(burns):
    """Burns that repeat an absorber within a series, on another strip: all
    six of C54's groups (two are in series with one absorber only, which
    the dose-or-time test leaves out but the strip scatter uses, as C54
    did)."""
    by = defaultdict(list)
    for b in burns:
        by[(b['series_id'], b['absorber'])].append((float(b['rate_t_drop1']), float(b['rate_t_drop1_err'])))
    return OrderedDict((k, v) for k, v in by.items() if len(v) > 1)


def nll(groups, t, relative):
    """−log L (REML) of the strip scatter t on the repeat groups."""
    tot = 0.0
    for g in groups:
        a = np.asarray(g, float)
        r, sg = a[:, 0], a[:, 1]
        v = sg ** 2 + (t * np.mean(np.abs(r))) ** 2 if relative else sg ** 2 + t ** 2
        w = 1.0 / v
        mu = np.sum(w * r) / np.sum(w)
        tot += 0.5 * (np.sum(np.log(v)) + np.log(np.sum(w)) + np.sum((r - mu) ** 2 * w))
    return float(tot)


def run(out, tau_c54=88.0, design_replicates=200):
    burns = read_table(BURNS)
    c54 = read_table(SERIES)
    ids = list(OrderedDict.fromkeys(r['series_id'] for r in c54))
    groups = repeat_groups(burns)
    gl = list(groups.values())
    tau, tau_ci = R.strip_scatter_fit(gl)
    rho, rho_ci = R.strip_scatter_fit(gl, relative=True)
    likelihood = OrderedDict(none=nll(gl, 0.0, False), tau=nll(gl, tau, False), rho=nll(gl, rho, True))
    models = OrderedDict([('counting', {}), ('tau', {'strip_scatter': tau}), ('tau_c54', {'strip_scatter': tau_c54}),
                          ('rho', {'strip_relative': rho})])
    rows, tallies = [], {m: Counter() for m in list(models) + ['c54_drop1', 'c54_strip']}
    for sid in ids:
        bs = [b for b in burns if b['series_id'] == sid]
        phi = [float(b['flux']) for b in bs]
        r = [float(b['rate_t_drop1']) for b in bs]
        s = [float(b['rate_t_drop1_err']) for b in bs]
        mine = {m: R.dose_or_time_rates(phi, r, s, [b['burn'] for b in bs], **kw) for m, kw in models.items()}
        theirs = {r_['tag']: r_ for r_ in c54 if r_['series_id'] == sid}
        row = OrderedDict(series_id=sid, burns=len(bs), flux_span=round(max(phi) / min(phi), 2),
                          c54_drop1=C54_WORDS[theirs['drop1']['verdict']],
                          c54_strip=C54_WORDS[theirs['drop1+strip']['verdict']],
                          c54_beta_strip=float(theirs['drop1+strip']['beta']))
        for m, v in mine.items():
            row['%s_verdict' % m] = v.verdict
            row['%s_beta' % m] = round(v.beta, 2)
            row['%s_lo' % m] = round(v.beta_ci[0], 2)
            row['%s_hi' % m] = round(v.beta_ci[1], 2)
            row['%s_weight_dose' % m] = round(v.weight_dose, 3)
            tallies[m][v.verdict] += 1
        tallies['c54_drop1'][row['c54_drop1']] += 1
        tallies['c54_strip'][row['c54_strip']] += 1
        rows.append(row)
    agree = {'counting vs C54 drop1': sum(r['counting_verdict'] == r['c54_drop1'] for r in rows),
             'tau_c54 vs C54 drop1+strip': sum(r['tau_c54_verdict'] == r['c54_strip'] for r in rows)}
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'comparison.csv'), 'w', newline='', encoding='utf-8') as f:
        f.write('# F76 on C54\'s real series (tools man, 2026-11-25): reciprocity.dose_or_time_rates under counting '
                'errors, the additive strip scatter tau (fitted here; tau_c54 = C54\'s 88 %/h) and the relative rho, '
                'beside C54\'s own verdicts (drop1, drop1+strip). Rates: % of I(0) per h, frame 1 left out. '
                'beta_lo/hi: delta chi2 = 1.\n')
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    numbers = OrderedDict(
        groups=[dict(series_id=k[0], absorber=k[1], rates=[list(p) for p in v]) for k, v in groups.items()],
        tau=tau, tau_ci=tau_ci, rho=rho, rho_ci=rho_ci, tau_c54=tau_c54, minus_log_likelihood=likelihood,
        tallies={m: dict(sorted(c.items())) for m, c in tallies.items()}, agreement=agree, series=len(rows))
    with open(os.path.join(out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(numbers, f, indent=1)
    figure(rows, out, tau, rho)
    if design_replicates:
        numbers['design'] = design(out, rho, design_replicates)
        with open(os.path.join(out, 'numbers.json'), 'w', encoding='utf-8') as f:
            json.dump(numbers, f, indent=1)
    return numbers


STRIPS = (2, 4, 8, 12, 16)


def design(out, rho, replicates, spans=(10.0,), strips=STRIPS):
    """How many strips per flux tell dose from time at the measured ρ:
    synthetic series (``synthetic.burn_pairs``, 21 frames, 1 % noise, a 10 %
    change at the lower flux), ``strips`` burns at each of two fluxes
    ``span`` apart, each strip's rate off by ρ (relative), analysed with
    ``strip_relative=ρ``. Writes design.csv; returns its rows."""
    sys.path.insert(0, os.path.join(ROOT, 'tests'))
    from synthetic import burn_pairs as bp
    rows = []
    for span in spans:
        for k in strips:
            fl = tuple(np.repeat([1.0, float(span)], k))
            row = OrderedDict(span=span, strips_per_flux=k, replicates=replicates)
            for beta, want, other in ((1.0, 'dose', 'time'), (0.0, 'time', 'dose')):
                calls = [R.dose_or_time(bp.series(beta=beta, fluxes=fl, change=0.1, noise=0.01, strip=rho,
                                                  seed=seed)[0], strip_relative=rho).verdict
                         for seed in range(replicates)]
                row['%s_right' % want] = round(calls.count(want) / replicates, 3)
                row['%s_wrong' % want] = round(calls.count(other) / replicates, 3)
            rows.append(row)
            print('design ×%g, %d strips per flux: dose %.2f, time %.2f right' % (span, k, row['dose_right'],
                                                                                  row['time_right']), flush=True)
    with open(os.path.join(out, 'design.csv'), 'w', newline='', encoding='utf-8') as f:
        f.write('# strips per flux needed at the measured relative strip scatter rho = %.3f (synthetic, %d replicates '
                'per cell; right = the truth called, wrong = the other law called)\n' % (rho, replicates))
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def figure(rows, out, tau, rho):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 6.2))
    order = sorted(rows, key=lambda r: r['flux_span'])
    y = np.arange(len(order))
    styles = (('counting', 'counting errors', '#888888', -0.22), ('tau', 'τ = %.0f %%/h (additive)' % tau, '#1f6fb4', 0.0),
              ('rho', 'ρ = %.2f (relative)' % rho, '#c0392b', 0.22))
    for m, label, col, dy in styles:
        b = np.array([r['%s_beta' % m] for r in order])
        lo = np.array([r['%s_lo' % m] for r in order])
        hi = np.array([r['%s_hi' % m] for r in order])
        ax.errorbar(b, y + dy, xerr=[b - lo, hi - b], fmt='o', ms=4, color=col, capsize=2, lw=1, label=label)
    ax.plot([r['c54_beta_strip'] for r in order], y, 'k|', ms=12, label='C54, 88 %/h')
    for v, t in ((0, 'time'), (1, 'dose')):
        ax.axvline(v, color='k', ls=':', lw=0.8)
        ax.text(v, len(order) - 0.3, t, ha='center', fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(['%s (%d burns, ×%.1f)' % (r['series_id'], r['burns'], r['flux_span']) for r in order],
                       fontsize=7.5)
    ax.set_xlim(R.BETA_GRID[0] - 0.1, R.BETA_GRID[-1] + 0.1)
    ax.set_xlabel('β: drift rate ∝ flux^β, with its Δχ² = 1 interval (1 = the dose, 0 = time)')
    ax.set_title('C54\'s 19 real series under three error models (rates from burns.csv, frame 1 left out)', fontsize=10)
    fig.legend(*ax.get_legend_handles_labels(), fontsize=8, loc='lower center', ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(out, 'R6_real_beta.png'), dpi=150)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/reciprocity/c54', help='output folder')
    ap.add_argument('--tau-c54', type=float, default=88.0,
                    help='C54\'s additive strip scatter (%%/h), run beside the one fitted here')
    ap.add_argument('--design-replicates', type=int, default=200,
                    help='replicates per cell of the strips-per-flux design at the fitted rho (0: skip; about 3 min '
                         'at 200)')
    a = ap.parse_args(argv)
    n = run(a.out, a.tau_c54, a.design_replicates)
    print('tau %.1f (%.1f-%.1f) %%/h; rho %.2f (%.2f-%.2f)' % (n['tau'], *n['tau_ci'], n['rho'], *n['rho_ci']))
    for m, c in n['tallies'].items():
        print('%-10s %s' % (m, c))
    print(n['agreement'])
    print('-log L on the repeats: %s' % ', '.join('%s %.1f' % kv for kv in n['minus_log_likelihood'].items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
