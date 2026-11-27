"""Burn tests against dose as well as time: beam damage or a changing
sample? (F76; docs/handoff_out/07-burn-trends.md, "Dose instead of time";
docs/physics_notes.md 2026-11-23, "Damage or a changing sample".)

    python tests/tools/burn_dose_figure.py                          # NX scans 14, 15 -> docs/figures/burn_dose/
    python tests/tools/burn_dose_figure.py --absorbers nominal      # 1.4247 per foil (the docs' "4.1x")
    python tests/tools/burn_dose_figure.py --join                   # one spot: 15's dose and time follow 14's
    python tests/tools/burn_dose_figure.py --spec PATH --scans 23 35 --out DIR

A change caused by the beam follows the absorbed dose, flux x time; a
sample changing by itself follows time alone. Two burns of one kind of
spot at absorbers n_a, n_b (flux ratio r) should therefore have the same
drift rate against dose in the first case and against time in the second.
For each scan the reader's burn estimator (``Experiment.burn``, the
template by default) gives the GID peak's integrated intensity, position
and FWHM per frame; the dose of frame k is

    D_k = sum over frames j <= k of Monc_j * T(n),

T(n) the foils' transmission at the scan's absorber setting (the reader's
calibrated foils at the scan's energy, ``lss_core.absorbers``, or the
nominal 1.4247 per unit): Monc is upstream of the foils, so Monc * T is
proportional to the photons on the sample. Units: 10^6 Monc counts at no
absorber. Each quantity's slope is fitted (weighted, straight line) against
time and against dose; the figure shows both, the table their ratios
(scan b over scan a). Reading: a dose effect gives a dose-slope ratio near
1 and a time-slope ratio near r; a changing sample the reverse. Two scans
cannot prove either (they also differ in when they were taken).

Writes ``dose_<scans>.png``, ``dose_<scans>.csv`` (per frame) and
``summary_<scans>.json``. Uses lss_core only. Private data: an --out
outside docs/ (refused otherwise).
"""
import argparse
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import matplotlib                                      # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                        # noqa: E402

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
OUT = os.path.join('docs', 'figures', 'burn_dose')
QUANTITIES = (('intensity', 'integrated intensity (relative)'), ('centre', 'position (Å⁻¹)'),
              ('fwhm', 'FWHM (Å⁻¹)'))
HC = 12.398419843320026                                 # keV Å


def transmission(n, energy_kev, model='calibrated'):
    """T(n) of the foils at absorber setting n (1/attenuation)."""
    from lss_core import absorbers
    if model == 'nominal' or n == 0:
        return absorbers.ABSFAC_10KEV ** (-n) if model == 'nominal' else 1.0
    cal = absorbers.calibrated(energy_kev)
    if cal is None:
        cal = absorbers.Foils(energy_kev=energy_kev)
    return 1.0 / absorbers.attenuation(cal, n)


def slope(x, y, s):
    """Weighted straight-line slope of y on x and its error (errors scaled
    by the scatter when it exceeds them)."""
    x, y, s = (np.asarray(v, float) for v in (x, y, s))
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(s) & (s > 0)
    x, y, s = x[ok], y[ok], s[ok]
    if len(x) < 3:
        return math.nan, math.nan
    w = 1.0 / s ** 2
    A = np.column_stack([np.ones_like(x), x])
    cov = np.linalg.inv(A.T @ (A * w[:, None]))
    p = cov @ (A.T @ (w * y))
    chi2 = float(np.sum(w * (y - A @ p) ** 2)) / (len(x) - 2)
    return float(p[1]), float(math.sqrt(cov[1, 1] * max(chi2, 1.0)))


def scan_series(exp, scan, estimator, absorber_model):
    res = exp.burn(scan, estimator=estimator)
    sc = exp.scans[scan]
    n = int(sc.parameters.get('Absorber', 0) or 0)
    energy = HC / float(sc.parameters['Wavelength'])
    monc = np.asarray(sc.columns['Monc'], float)[:len(res.t)]
    T = transmission(n, energy, absorber_model)
    dose = np.cumsum(monc * T) / 1e6
    return dict(scan=scan, absorber=n, energy_kev=energy, transmission=T, t=np.asarray(res.t, float), dose=dose,
                values={q: (np.asarray(res.values[q][0], float), np.asarray(res.values[q][1], float))
                        for q, _ in QUANTITIES if q in res.values}, kind=res.kind)


def analyse(series, join=False):
    """Slopes per scan and quantity against time and dose; ratios b/a."""
    if join:
        for prev, cur in zip(series, series[1:]):
            cur['t'] = cur['t'] - cur['t'][0] + prev['t'][-1] + (prev['t'][-1] - prev['t'][-2])
            cur['dose'] = cur['dose'] + prev['dose'][-1]
    out = {'scans': [s['scan'] for s in series], 'join': join,
           'absorbers': [s['absorber'] for s in series], 'transmission': [s['transmission'] for s in series],
           'slopes': {}, 'ratios': {}}
    if len(series) >= 2:
        out['flux_ratio'] = series[1]['transmission'] / series[0]['transmission']
    for q, _ in QUANTITIES:
        per = []
        for s in series:
            if q not in s['values']:
                continue
            y, e = s['values'][q]
            per.append({'scan': s['scan'], 'vs_time': slope(s['t'], y, e), 'vs_dose': slope(s['dose'], y, e)})
        out['slopes'][q] = per
        if len(per) >= 2:
            a, b = per[0], per[1]
            r = {k: (b[k][0] / a[k][0] if a[k][0] else math.nan) for k in ('vs_time', 'vs_dose')}
            z = [abs(x['vs_time'][0] / x['vs_time'][1]) if x['vs_time'][1] else 0.0 for x in (a, b)]
            r['significant'] = bool(min(z) >= 3.0)          # both scans change: a ratio means something
            for k in ('vs_time', 'vs_dose'):
                d = math.hypot(a[k][1], b[k][1])
                r[k + '_differ_sigma'] = abs(b[k][0] - a[k][0]) / d if d else math.nan
            out['ratios'][q] = r
    return out


def draw(series, summary, path, title):
    fig, axs = plt.subplots(len(QUANTITIES), 2, figsize=(11.0, 8.5), sharex='col')
    colours = ('#1f77b4', '#d62728', '#2ca02c', '#9467bd')
    for i, (q, label) in enumerate(QUANTITIES):
        for j, xkey in enumerate(('t', 'dose')):
            ax = axs[i, j]
            for k, s in enumerate(series):
                if q not in s['values']:
                    continue
                y, e = s['values'][q]
                ref = y[0] if q == 'intensity' and y[0] else 1.0
                ax.errorbar(s[xkey], y / ref, yerr=e / abs(ref), fmt='o', ms=3, lw=0.8, color=colours[k % 4],
                            label='scan %d, absorber %d (T = %.3g)' % (s['scan'], s['absorber'], s['transmission']))
            if j == 0:
                ax.set_ylabel(label if q != 'intensity' else 'intensity / first frame')
            if i == 0:
                ax.set_title('against clock time' if j == 0 else 'against dose (Σ Monc·T)')
            ax.grid(alpha=0.3)
        r = summary['ratios'].get(q)
        if r:
            text = ('slope ratio %d/%d: vs time %.2f, vs dose %.2f (flux ratio %.2f); dose slopes %.1fσ apart'
                    % (summary['scans'][1], summary['scans'][0], r['vs_time'], r['vs_dose'], summary['flux_ratio'],
                       r['vs_dose_differ_sigma'])) if r['significant'] else \
                'no significant change in both scans: no ratio'
            axs[i, 1].text(0.02, 0.04, text, transform=axs[i, 1].transAxes, fontsize=8.5)
    axs[-1, 0].set_xlabel('time (s)')
    axs[-1, 1].set_xlabel('dose (10⁶ Monc counts at no absorber)')
    axs[0, 0].legend(fontsize=8, loc='best')
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', default=NX)
    ap.add_argument('--scans', type=int, nargs='+', default=[14, 15])
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--estimator', default='stretched', help="the burn estimator: template (default), moments or fit")
    ap.add_argument('--absorbers', choices=('calibrated', 'nominal'), default='calibrated',
                    help='foil transmission: the calibrated foils at the energy (default) or 1.4247 per unit')
    ap.add_argument('--join', action='store_true',
                    help='one spot measured twice: each scan\'s time and dose follow the previous scan\'s')
    a = ap.parse_args(argv)
    public = os.path.abspath(a.spec) == os.path.abspath(os.path.join(ROOT, NX)) or os.path.abspath(a.spec) == \
        os.path.abspath(NX)
    if not public and os.path.abspath(a.out).startswith(os.path.join(ROOT, 'docs')):
        sys.exit('private data: give an --out outside docs/ (e.g. under sample_data/private/figures/)')
    os.makedirs(a.out, exist_ok=True)
    from lss_core.experiment import Experiment
    exp = Experiment(a.spec)
    series = [scan_series(exp, s, a.estimator, a.absorbers) for s in a.scans]
    summary = analyse(series, a.join)
    summary.update(estimator=a.estimator, absorber_model=a.absorbers)
    tag = '_'.join(map(str, a.scans)) + ('_joined' if a.join else '') + ('_nominal' if a.absorbers == 'nominal' else '')
    draw(series, summary, os.path.join(a.out, 'dose_%s.png' % tag),
         '%s scans %s: burn quantities against time and against dose (%s estimator, %s foils%s)'
         % (os.path.basename(a.spec), ', '.join(map(str, a.scans)), a.estimator, a.absorbers,
            ', joined' if a.join else ''))
    cols, arr = ['scan', 'time_s', 'dose_1e6'], []
    for s in series:
        block = [np.full(len(s['t']), s['scan']), s['t'], s['dose']]
        for q, _ in QUANTITIES:
            y, e = s['values'].get(q, (np.full(len(s['t']), np.nan),) * 2)
            block += [y, e]
        arr.append(np.column_stack(block))
    for q, _ in QUANTITIES:
        cols += [q, q + '_err']
    np.savetxt(os.path.join(a.out, 'dose_%s.csv' % tag), np.vstack(arr), delimiter=',', header=','.join(cols),
               comments='', fmt='%.10g')
    with open(os.path.join(a.out, 'summary_%s.json' % tag), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=1)
    print('flux ratio %.3f (%s foils)' % (summary.get('flux_ratio', math.nan), a.absorbers))
    for q, r in summary['ratios'].items():
        if not r['significant']:
            print('%-9s no significant change in both scans: no ratio' % q)
            continue
        print('%-9s slope ratio %s/%s: against time %.2f (%.1f sigma apart), against dose %.2f (%.1f sigma apart)'
              % (q, summary['scans'][1], summary['scans'][0], r['vs_time'], r['vs_time_differ_sigma'],
                 r['vs_dose'], r['vs_dose_differ_sigma']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
