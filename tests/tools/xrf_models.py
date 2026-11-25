"""Can models stand in for the real scatter and the real lines? (2026-11-25;
``docs/studies/xrf_models/README.md``.)

    python tests/tools/xrf_models.py scatter --out docs/studies/xrf_models/scatter
    python tests/tools/xrf_blanks.py --blank-dir docs/studies/xrf_models/scatter/twins_full ...
    python tests/tools/xrf_models.py scatter --out docs/studies/xrf_models/scatter --models full --redraw
    python tests/tools/xrf_models.py compare --out docs/studies/xrf_models/scatter
    python tests/tools/xrf_models.py figures --out docs/studies/xrf_models

**Scatter.** Every public blank (``tests/reference/mca_scatter/``, readout A:
the single-element detector, readout B: one element of the seven-element
one) is fitted over its whole range (E0 − 2.5 to E0 + 0.7 keV) by a ladder
of models, all built on ``mca_scatter.ScatterModel`` (Poisson maximum
likelihood, the generator's physics):

* ``generator``: study B's hard case, the scatter the synthetic shootout
  used (noise 0.12 keV at Fano 0.115, tail 1 % over 0.15 keV, shelf 0.2 %,
  escape 1 × Reed, water's O 1s wing and Doppler widths); free: the elastic
  photons, Compton/Rayleigh, the angle, the offset, a flat background and
  nuisance lines;
* ``gaussian``: a Gaussian detector (no tail, shelf or high tail) with the
  noise, escape, O 1s wing and Doppler widths free: is a Gaussian response
  enough for the scatter?
* ``full``: the study's model, every axis free.

Each fit's expected **scatter** becomes a **model twin** of the blank: one
Poisson draw on the blank's channels of the elastic, Compton and background
parts, written as a blank file (``twins_<model>/``). The nuisance lines
the fit may add (K and L lines of elements whose lines fall in the region,
amplitude ≥ 0) are left out of the twin: a model of the scatter holds no
sample line. Their counts are in ``ladder.csv`` (``line_<el>_counts`` and
``line_<el>_box_fraction``, the share of the blank's counts within ±1 FWHM
of the line): a trace in a "clean" blank, or structure the model absorbed. ``xrf_blanks.py --blank-dir`` then runs the same
shootout on the twins as on the real blanks. Where the biases agree, the
model can replace the real scatter for testing line fits (``compare``).

**The floor.** One real blank is one Poisson draw, and so is its twin; the
shootout's replicates thin that one draw (p about 0.02), so both runs carry
their own draw's fluctuations and would differ even if the model were exact.
``--redraw`` writes a second, independent draw of the same model
(``twins_<model>_redraw/``); ``compare`` scores its run against the first
twin's (model ``<model>_redraw``), which is how far apart two draws of one
truth land. A model stands in for the real scatter where its twin is no
farther from the real blank than that.

The misfit is also given at the counts the shootout uses: a thinning p
(``xrf_blanks``: box counts 1000 or 3000) scales a systematic misfit's
deviance by p, so the deviance per dof at use is about 1 + p (D/dof − 1).
"""
import os

for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')

import argparse
import csv
import math
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import mca_scatter as ms                                       # noqa: E402
import xrf_blanks as xb                                        # noqa: E402

BLANKS = xb.BLANKS
ALL_BLANKS = ('E10-d', 'E10-f', 'E10-i', 'E10-j', 'E10-k', 'E6.1-a', 'E6.1-b', 'E6.1-c', 'E6.1-d',
              'E9.2-a', 'E9.2-b', 'E9.2-c', 'E9.2-d')
GEN_FIX = dict(noise=0.12, escape=1.0, tail=0.01, tail_slope=0.15, shelf=2e-3, rtail=0.0, rtail_slope=0.1,
               core=1.0, doppler=1.0)                         # ms.GENERATOR_HARD without its background
MODELS = {
    'generator': GEN_FIX,
    'gaussian': dict(tail=0.0, shelf=0.0, rtail=0.0, tail_slope=0.15, rtail_slope=0.1),
    'full': {},
}
# offsets below the beam (keV) of the boxes the residuals are read in: the study's windows
OFFSETS = (0.6, 1.0, 1.37, 1.74, 2.0, 2.3)


def fit_blank(args):
    """Every model of the ladder on one blank: {model: row} plus the
    expected counts on the blank's channels."""
    bid, models = args
    b = xb.load_blank(os.path.join(BLANKS, bid + '.csv'))
    e, n, e0 = b['energy'], b['counts'], b['beam']
    out = {}
    for m in models:
        sm = ms.ScatterModel(n, b['calib'], e0, lo=e0 - e[0] + 0.02, hi=e[-1] - e0 + 0.02, fix=dict(MODELS[m]))
        assert len(sm.sel) == len(e), (bid, len(sm.sel), len(e))
        p, perr, dev, dof = sm.fit()
        mu = sm.mu(p)
        r = sm.resid(p)
        parts = sm.parts(p)
        lines = {k[5:]: sum(v.values()) for k, v in parts.items() if k.startswith('line ')}
        mu_scatter = mu - sum(lines.values(), np.zeros(len(mu)))      # the scatter alone: what a twin is drawn from
        P = dict(zip(sm.names, p))
        P.update(sm.fix)
        low = e < e0 - 0.1
        nfree = len(sm.names) - len(sm.fix)
        dev_low = float(np.sum(r[low] ** 2))
        dof_low = int(low.sum()) - nfree
        row = dict(blank=bid, readout=b['readout'], beam_kev=e0, model=m, counts=float(n.sum()),
                   deviance=dev, dof=dof, dev_per_dof=dev / dof, dev_low=dev_low, dof_low=dof_low,
                   dev_per_dof_low=dev_low / dof_low)
        fw = mca_fwhm(P, e0)
        for d in OFFSETS:
            c = e0 - d
            w = (e > c - fw) & (e < c + fw)
            if w.sum() >= 3:
                row['box_%g' % d] = float(n[w].sum() / mu[w].sum() - 1)
                row['box_%g_z' % d] = float((n[w].sum() - mu[w].sum()) / math.sqrt(mu[w].sum()))
        for k in ('noise', 'tail', 'tail_slope', 'shelf', 'escape', 'core', 'doppler', 'angle', 'rtail', 'rtail_slope',
                  'bg0', 'offset'):
            row[k] = float(P[k])
        row['compton_over_rayleigh'] = math.exp(P['logR'])
        for el, v in lines.items():                    # nuisance lines the fit put in: traces, or misfit it absorbed
            ka = [c for c in sm.lines if c[0] == el][0][1]
            w = (e > ka - fw) & (e < ka + fw)
            row['line_%s_counts' % el] = float(v.sum())
            row['line_%s_box_fraction' % el] = float(v[w].sum() / max(n[w].sum(), 1.0)) if w.any() else 0.0
        out[m] = (row, mu, r, mu_scatter)
    return bid, b, out


def mca_fwhm(P, e0):
    from synthetic import mca
    return mca.Detector(noise=P['noise']).fwhm(e0 - 1.0)


def write_twin(path, blank, mu, model, rng):
    """A blank file whose counts are one Poisson draw of the model."""
    src = os.path.join(BLANKS, blank['id'] + '.csv')
    with open(src, encoding='utf-8') as f:
        head = [ln.rstrip('\n') for ln in f if ln.startswith('#')]
    head.insert(1, '# twin: one Poisson draw of the scatter (elastic, Compton, background; no fitted line) of the %s '
                   'model fitted to this blank (tests/tools/xrf_models.py)' % model)
    c = rng.poisson(mu)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(head) + '\nenergy_keV,counts\n')
        for e, v in zip(blank['energy'], c):
            f.write('%.4f,%d\n' % (e, v))


def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, keys, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})


def cmd_scatter(a):
    os.makedirs(a.out, exist_ok=True)
    rows, resid = [], []
    models = a.models.split(',') if a.models else list(MODELS)
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(fit_blank, [(bid, models) for bid in ALL_BLANKS]))
    if a.redraw:                                  # a second, independent draw of each twin: the floor
        for bid, b, out in res:
            for m, (row, mu, r, mus) in out.items():
                if bid in xb.CLEAN:
                    d = os.path.join(a.out, 'twins_%s_redraw' % m)
                    os.makedirs(d, exist_ok=True)
                    rng = np.random.default_rng([20261125, 15, ALL_BLANKS.index(bid), list(MODELS).index(m), 1])
                    write_twin(os.path.join(d, bid + '.csv'), b, mus, m, rng)
        return
    for bid, b, out in res:
        for m, (row, mu, r, mus) in out.items():
            rows.append(row)
            for e, nn, mm, rr, ss in zip(b['energy'], b['counts'], mu, r, mus):
                resid.append(dict(blank=bid, model=m, energy_keV=float(e), counts=float(nn), model_counts=float(mm),
                                  scatter_counts=float(ss), deviance_residual=float(rr)))
            if bid in xb.CLEAN:
                d = os.path.join(a.out, 'twins_' + m)
                os.makedirs(d, exist_ok=True)
                rng = np.random.default_rng([20261125, 15, ALL_BLANKS.index(bid), list(MODELS).index(m)])
                write_twin(os.path.join(d, bid + '.csv'), b, mus, m, rng)
    write_csv(os.path.join(a.out, 'ladder.csv'), rows)
    write_csv(os.path.join(a.out, 'residuals.csv'), resid)
    for r in rows:
        print('%-7s %s %-9s D/dof %8.2f  low %8.2f  %s' % (r['blank'], r['readout'], r['model'], r['dev_per_dof'],
              r['dev_per_dof_low'], ' '.join('%+.3f' % r.get('box_%g' % d, math.nan) for d in OFFSETS)))


# ---- compare: the blank shootout on twins against the real blanks --------------------------------------------

def _read(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


def accurate(bias, se):
    return abs(bias) <= max(0.02, 2 * se)


def cmd_compare(a):
    real = {}
    for d in a.real.split(','):
        for r in _read(os.path.join(d, 'scores.csv')):
            real[(r['condition'], r['method'])] = r
    zr = {}
    for d in a.real.split(','):
        for r in _read(os.path.join(d, 'zero.csv')):
            zr[(r['condition'], r['method'])] = r
    rows, zrows = [], []
    runs = [(m, m, real, zr) for m in MODELS]
    for m in MODELS:                              # the floor: a second draw of a twin against the first
        d0 = os.path.join(a.out, 'run_' + m)
        if os.path.exists(os.path.join(d0, 'scores.csv')):
            runs.append((m + '_redraw', m + '_redraw',
                         {(r['condition'], r['method']): r for r in _read(os.path.join(d0, 'scores.csv'))},
                         {(r['condition'], r['method']): r for r in _read(os.path.join(d0, 'zero.csv'))}))
    for m, run, real, zr in runs:
        d = os.path.join(a.out, 'run_' + run)
        if not os.path.exists(os.path.join(d, 'scores.csv')):
            print('no', d)
            continue
        for r in _read(os.path.join(d, 'scores.csv')):
            q = real.get((r['condition'], r['method']))
            if q is None:
                continue
            bt, st, br, sr = _num(r['bias']), _num(r['bias_se']), _num(q['bias']), _num(q['bias_se'])
            rows.append(dict(model=m, condition=r['condition'], blank=r['blank'], target=r['target'],
                             background=r['background'], ratio=r['ratio'], method=r['method'], bias_real=br,
                             bias_twin=bt, diff=bt - br, z=(bt - br) / math.hypot(st, sr) if st > 0 or sr > 0 else math.nan,
                             accurate_real=accurate(br, sr) if np.isfinite(br) else False,
                             accurate_twin=accurate(bt, st) if np.isfinite(bt) else False,
                             pull_sd_real=_num(q.get('pull_sd')), pull_sd_twin=_num(r.get('pull_sd'))))
        for r in _read(os.path.join(d, 'zero.csv')):
            q = zr.get((r['condition'], r['method']))
            if q is None:
                continue
            zrows.append(dict(model=m, condition=r['condition'], blank=r['blank'], target=r['target'],
                              method=r['method'], false_real=_num(q.get('false_per100')),
                              false_twin=_num(r.get('false_per100')), se_real=_num(q.get('false_se')),
                              se_twin=_num(r.get('false_se'))))
    write_csv(os.path.join(a.out, 'compare.csv'), rows)
    write_csv(os.path.join(a.out, 'compare_zero.csv'), zrows)
    summ = []
    for m in [r[0] for r in runs]:
        for meth in sorted({r['method'] for r in rows}):
            R = [r for r in rows if r['model'] == m and r['method'] == meth and np.isfinite(r['diff'])]
            Z = [r for r in zrows if r['model'] == m and r['method'] == meth and np.isfinite(r['false_twin'])
                 and np.isfinite(r['false_real'])]
            if not R:
                continue
            dd = np.array([r['diff'] for r in R])
            z = np.array([r['z'] for r in R if np.isfinite(r['z'])])
            summ.append(dict(model=m, method=meth, conditions=len(R),
                             median_abs_diff=float(np.median(np.abs(dd))), p90_abs_diff=float(np.percentile(np.abs(dd), 90)),
                             within_2pc=float(np.mean(np.abs(dd) <= 0.02)), within_2se=float(np.mean(np.abs(z) <= 2)),
                             verdict_agrees=float(np.mean([r['accurate_real'] == r['accurate_twin'] for r in R])),
                             accurate_real=int(sum(r['accurate_real'] for r in R)),
                             accurate_twin=int(sum(r['accurate_twin'] for r in R)),
                             false_median_abs_diff=float(np.median([abs(r['false_twin'] - r['false_real']) for r in Z]))
                             if Z else math.nan))
    write_csv(os.path.join(a.out, 'compare_summary.csv'), summ)
    for s in summ:
        print('%-9s %-12s n %3d |d| med %.3f p90 %.3f  <2%% %.2f <2se %.2f verdict %.2f  acc %3d/%3d  false %.2f' % (
            s['model'], s['method'], s['conditions'], s['median_abs_diff'], s['p90_abs_diff'], s['within_2pc'],
            s['within_2se'], s['verdict_agrees'], s['accurate_real'], s['accurate_twin'], s['false_median_abs_diff']))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scatter')
    s.add_argument('--out', required=True)
    s.add_argument('--jobs', type=int, default=13)
    s.add_argument('--models', default='', help='comma-separated models (default: all)')
    s.add_argument('--redraw', action='store_true',
                   help="only a second, independent draw of each twin (twins_<model>_redraw/): the compare's floor")
    c = sub.add_parser('compare')
    c.add_argument('--out', required=True)
    c.add_argument('--real', default=os.path.join('docs', 'studies', 'xrf_shootout', 'run_blanks') + ',' +
                   os.path.join('docs', 'studies', 'xrf_shootout', 'run_blanks_options'))
    a = ap.parse_args(argv)
    {'scatter': cmd_scatter, 'compare': cmd_compare}[a.cmd](a)


if __name__ == '__main__':
    main()
