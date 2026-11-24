"""The beam-energy story of the MCA line fit (F90 wrap-up, Main 2026-11-24;
``docs/reports/mca_fit_demo.md``): the same Zn spectrum under beams of
10, 11 and 12 keV, its parts stacked, the ±2 FWHM box, one drawn spectrum
with P1's fit, and P1's bias over replicate series written on each panel
(the window sum's beside it, for contrast).

    python tests/tools/mca_fit_demo.py --out docs/figures/mca_fit_demo     # about 1 min on 3 CPUs
    python tests/tools/mca_fit_demo.py --out DIR --beams 10,12,14          # other beam energies (keV)
    python tests/tools/mca_fit_demo.py --out DIR --wing 0.5                # the O 1s Compton wing × water's
    python tests/tools/mca_fit_demo.py --out DIR --escape 3                # the Si escapes × Reed's fraction
    python tests/tools/mca_fit_demo.py --out DIR --photons 1e4             # the line's photons per spectrum
    python tests/tools/mca_fit_demo.py --out DIR --element Fe              # Fe Kα, far from the scatter

The spectrum is study B's hard case (``mca_fit_gauntlet.core()['hard']``
with the 'shells' Compton model: water's Compton scatter shell by shell,
Reed's escapes, a 1 % tail and a 0.2 % shelf; 1e3 line photons on 1e6
elastic). The line's photons and the elastic's are the same at every beam
energy. In fact the Zn K excitation falls by about 40 % from 10 to 12 keV
(the document says so). P1 is the reader's "Fit lines" with Poisson
weights (its default since 2026-11-24), as the gauntlet runs it: a
Gaussian on a quadratic over the box, ten spectra fitted together. The
bias is the mean of estimate / true line − 1 over the series that did not
fail, ± its standard error.

Outputs: ``beam_energy.png``, ``beam_energy.csv`` (bias, error and
failures per beam and estimator) and ``numbers.json``. All synthetic, so
public.
"""
import argparse
import csv
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
sys.path.insert(0, os.path.join(os.getcwd(), 'tests', 'tools'))

import matplotlib                                         # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                           # noqa: E402

from lss_core import peaks                                # noqa: E402
from synthetic import mca                                 # noqa: E402
import mca_fit_gauntlet as g                              # noqa: E402

METHODS = ('window', 'p1')
NAMES = {'window': 'window sum', 'p1': 'P1 (Poisson fit)'}


def condition(beam, element='Zn', photons=1e3, wing=1.0, escape=1.0):
    """Study B's hard case at a beam of ``beam`` keV (``mca_fit_gauntlet.hard_case``)."""
    return g.hard_case(beam, element, photons, wing, escape)


excited = g.excited


def bias(rows):
    """(mean relative bias, its standard error, failed, series) of one
    estimator's rows from ``mca_fit_gauntlet.run_condition``."""
    good = [r for r in rows if r[-1] is not None and len(r) > 2]
    rel = np.array([r[-4] / r[-1] - 1 for r in good])
    n = len(good)
    se = float(rel.std(ddof=1) / math.sqrt(n)) if n > 1 else math.nan
    return (float(rel.mean()) if n else math.nan), se, len(rows) - n, len(rows)


def _run(args):
    k, cond, reps = args
    _, rows, ka, stopped, secs = g.run_condition(('demo%d' % k, cond, reps, list(METHODS), 900 + k))
    return k, {m: bias(rows.get(m, [])) for m in METHODS}, ka, secs


def _fit(cond, spec, seed):
    """One series of ``cond.series`` drawn spectra, fitted by P1: (counts of
    the first, its fitted model or None)."""
    rng = np.random.default_rng([2026, 11, 24, seed])
    counts = [spec.draw(rng) for _ in range(cond.series)]
    data = [g.normalise(c, spec.calib) for c in counts]
    x = data[0][:, 0]
    try:
        ref, each = peaks.fit_series(x, [d[:, 1] for d in data], [d[:, 2] for d in data],
                                     g.fit_options(cond, [cond.line]), weights='poisson')
    except Exception:
        each = []
    return counts[0], (each[0] if each else None)


def parts(s, element):
    return [('background', s.part(['background']), '0.8'),
            ('detector tails and shelves', s.part(None, ['tail', 'shelf']), 'C4'),
            ('Si escape peaks', s.part(None, ['escape']), 'C2'),
            ('Compton, O 1s (core)', s.part(['Compton core'], ['peak']), 'C1'),
            ('Compton, valence', s.part(['Compton valence'], ['peak']), 'C9'),
            ('Rayleigh (elastic)', s.part(['Rayleigh'], ['peak']), 'C0'),
            ('%s Kβ' % element, s.photopeak(element, 'Kb'), 'C5'),
            ('%s Kα (the line)' % element, s.photopeak(element), 'C3')]


def _pct(v, se=None):
    if not np.isfinite(v):
        return 'all failed'
    return '%+.1f %%' % (100 * v) if se is None or not np.isfinite(se) else '%+.1f ± %.1f %%' % (100 * v, 100 * se)


def figure(conds, results, out, reps):
    n = len(conds)
    fig, axes = plt.subplots(2, n, figsize=(5.4 * n, 8.6), squeeze=False,
                             gridspec_kw=dict(height_ratios=(1.15, 1), hspace=0.28, wspace=0.22, bottom=0.11))
    e_hi = max(c.beam.energy for c in conds) + 0.6
    e_lo = min(c.line for c in conds) - 1.6
    for k, cond in enumerate(conds):
        top, low = axes[0, k], axes[1, k]
        s = cond.spectrum()
        e = s.energy
        lo, hi = cond.box_range()
        sel = (e > e_lo) & (e < e_hi)
        base = np.full(sel.sum(), 1e-2)
        for lab, v, col in parts(s, cond.element):
            t = base + v[sel]
            top.fill_between(e[sel], base, t, color=col, alpha=0.75, lw=0, label=lab)
            base = t
        top.plot(e[sel], s.expected[sel], 'k', lw=0.7, label='total (expected)')
        top.axvspan(lo, hi, color='k', alpha=0.08, lw=0, label='box ±%g FWHM' % cond.box)
        top.set_yscale('log')
        top.set_ylim(0.1, s.expected[sel].max() * 3)
        top.set_xlim(e_lo, e_hi)
        top.set_title('%g keV beam' % cond.beam.energy, fontsize=11)
        top.set_xlabel('energy (keV)', fontsize=8)
        if k == 0:
            top.set_ylabel('expected counts per 10 eV channel', fontsize=8)
            top.legend(fontsize=6.5, ncol=2, loc='upper left')
        top.tick_params(labelsize=7)

        counts, r = _fit(cond, s, k)
        zoom = (e > lo - 0.35) & (e < hi + 0.35)
        low.step(e[zoom], counts[zoom], where='mid', color='0.6', lw=0.7, label='one drawn spectrum')
        low.plot(e[zoom], s.expected[zoom], 'k', lw=0.8, label='expected total')
        low.fill_between(e[zoom], 0, s.photopeak(cond.element)[zoom], color='C3', alpha=0.35, lw=0,
                         label='the true line (%s Kα)' % cond.element)
        if r is not None:
            xx = np.linspace(lo, hi, 300)
            low.plot(xx, r.model(xx) * g.scale(), color='C0', lw=1.6, label='P1\'s fit (line + quadratic)')
        low.axvspan(lo, hi, color='k', alpha=0.06, lw=0)
        low.set_xlim(e[zoom][0], e[zoom][-1])
        low.set_ylim(0, None)
        low.set_xlabel('energy (keV)', fontsize=8)
        if k == 0:
            low.set_ylabel('counts per channel', fontsize=8)
        low.tick_params(labelsize=7)
        res = results[k]
        bx = float(s.photopeak(cond.element)[(e >= lo) & (e <= hi)].sum())
        b1, se1, f1, n1 = res['p1']
        bw = res['window'][0]
        ns, fs = n1 // cond.series, f1 // cond.series
        if fs * 2 > ns:                                         # most failed: the survivors' bias says little
            text = ['P1: %d of %d series failed' % (fs, ns),
                    '    (the %d left: %s)' % (ns - fs, _pct(b1))]
        else:
            text = ['P1: bias %s' % _pct(b1, se1),
                    '    (%d series of %d; %d failed)' % (ns, cond.series, fs)]
        text += ['window sum: %s' % _pct(bw), 'true line in the box: %.0f counts' % bx]
        low.text(0.02, 0.97, '\n'.join(text), transform=low.transAxes, fontsize=8.5, va='top', family='monospace',
                 bbox=dict(facecolor='white', alpha=0.85, edgecolor='0.7'))
        if k == n - 1:
            h, lab = low.get_legend_handles_labels()
            fig.legend(h, lab, loc='lower center', ncol=len(lab), fontsize=8, bbox_to_anchor=(0.5, 0.0))
    c0 = conds[0]
    fig.suptitle('The beam-energy story: %s Kα (%g photons) on %g elastic photons, the same spectrum under each beam '
                 '(O 1s wing × %g, escapes × %g); P1 judged on %d series of %d spectra'
                 % (c0.element, c0.photons, c0.elastic, c0.beam.core_scale, c0.detector.escape, reps, c0.series),
                 fontsize=10)
    fig.savefig(os.path.join(out, 'beam_energy.png'), dpi=100, bbox_inches='tight')
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True, help='folder for beam_energy.png, beam_energy.csv, numbers.json')
    ap.add_argument('--beams', default='10,11,12', help='beam energies (keV), comma-separated: one panel each')
    ap.add_argument('--element', default='Zn', choices=sorted(mca.ELEMENTS), help='the fluorescing element')
    ap.add_argument('--photons', type=float, default=1e3, help="the line's K photons per spectrum (1e6 elastic)")
    ap.add_argument('--wing', type=float, default=1.0, help="the O 1s Compton wing, × water's (0: none)")
    ap.add_argument('--escape', type=float, default=1.0, help="the Si escape peaks, × Reed's fraction (0: none)")
    ap.add_argument('--replicates', type=int, default=200, help='series of 10 spectra per beam for the bias')
    ap.add_argument('--workers', type=int, default=min(3, os.cpu_count() or 1))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    conds = [condition(float(b), a.element, a.photons, a.wing, a.escape) for b in a.beams.split(',') if b.strip()]
    skipped = [c.beam.energy for c in conds if not excited(c)]
    conds = [c for c in conds if excited(c)]
    for b in skipped:
        print('%g keV is below the %s K edge (%.3f keV): no line, no panel' % (b, a.element, mca.ELEMENTS[a.element][0]))
    if not conds:
        return 1
    jobs = [(k, c, a.replicates) for k, c in enumerate(conds)]
    results, secs = {}, 0.0
    if a.workers > 1:
        with ProcessPoolExecutor(a.workers) as ex:
            got = list(ex.map(_run, jobs))
    else:
        got = [_run(j) for j in jobs]
    for k, res, ka, s in got:
        results[k] = res
        secs += s
    figure(conds, results, a.out, a.replicates)
    rows = []
    for k, c in enumerate(conds):
        for m in METHODS:
            b, se, f, n = results[k][m]
            rows.append(dict(beam_keV=c.beam.energy, element=c.element, photons=c.photons, wing=a.wing,
                             escape=a.escape, method=m, rel_bias=b, se=se, failed=f, spectra=n))
    with open(os.path.join(a.out, 'beam_energy.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    numbers = dict(settings=dict(beams=[c.beam.energy for c in conds], element=a.element, photons=a.photons,
                                 wing=a.wing, escape=a.escape, replicates=a.replicates, series=conds[0].series),
                   bias={'%g' % c.beam.energy: {m: dict(zip(('rel_bias', 'se', 'failed', 'spectra'), results[k][m]))
                                                for m in METHODS} for k, c in enumerate(conds)},
                   seconds=round(secs, 1))
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(numbers, f, indent=1)
    for r in rows:
        print('%5g keV  %-8s bias %s  failed %d of %d spectra' % (r['beam_keV'], r['method'],
                                                                  _pct(r['rel_bias'], r['se']), r['failed'],
                                                                  r['spectra']))
    print('wrote %s' % os.path.join(a.out, 'beam_energy.png'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
