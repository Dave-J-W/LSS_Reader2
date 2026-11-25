"""XRF shootout on real blanks: synthetic fluorescence lines of known
photons injected into the real, scatter-only MCA spectra committed in
``tests/reference/mca_scatter/`` (2026-11-25; the shootout's question Q13
in ``docs/studies/xrf_shootout/QUESTIONS.md``).

    python tests/tools/xrf_blanks.py --out docs/studies/xrf_shootout/run_blanks
        [--replicates 50] [--jobs 30] [--methods all|a,b] [--blanks E10-k,...]

Run from the repository root, in the shootout's environment
(``docs/studies/xrf_shootout/README.md``).

**Why.** The shootout's spectra are synthetic from end to end: the scatter
under the line is the generator's, however well its settings were fitted to
the owner's blanks. Here the scatter, the background, the escape peaks and
whatever else a real detector adds are **measured**: they are the blanks
themselves, count for count. Only the line is synthetic, and its photons are
known.

**How each spectrum is made.**

1. A blank (``energy_keV,counts``, its beam energy and readout in the
   header) is **thinned**: every count kept with probability p (a binomial
   draw), so that its counts in the line's box are ``--background`` (1000 or
   3000). A thinned Poisson spectrum is a Poisson spectrum with p times the
   mean, so each thinning is a fresh real-shaped spectrum. Two thinnings of
   one blank share a fraction p of their counts; p is at most 0.23 here and
   is written to ``conditions.csv``.
2. A line family (``synthetic.mca_more``: xraylib's lines and ratios at the
   blank's beam energy) of N photons is added, as Poisson counts, with the
   detector response **measured on that blank** (``docs/studies/mca_scatter/
   scatter_fits.csv``: the elastic width, the low tail and its slope, the
   shelf, the Si escape × Reed; the Fano factor from the Ar Kα and elastic
   widths where that blank has it, else the readout's median, and the noise
   that gives the blank's elastic width with that Fano factor). N is
   0.1, 0.3, 1 or 3 times the box's background counts.
3. Every method is told what a user would know: the calibration (fitted to
   the file's energy column), the beam energy, the measured scattering angle
   and detector, and the element. Each method is calibrated on its clean
   twin (``xrf_shootout``: the same line and detector on a flat 1 count per
   channel, noise-free), and its truth is the family's photons.

The blanks used are the ten with no line in their region (E10-k, E10-f,
readout A; E9.2-a…d and E6.1-a…d, readout B, pre-edge sums). E10-d, E10-i and
E10-j hold traces of Cu and Zn (``scatter_fits.csv``, ``lines_in_region``), so
a Cu or Zn line injected there has no known truth; they are not used.

The lines, per beam energy: 10 keV, Zn K (Kα 8.64 keV, on the Compton
shoulder) and Cu K (8.05 keV); 9.2 keV, Cu K (Kβ under the Compton peak)
and Ni K (7.48 keV); 6.1 keV, Cr K (Kβ under the scatter), Ti K (4.51 keV)
and La L (4.65 keV, with Lβ lines at 5.0–5.4 keV).

**Also measured: the false signal.** Each method is run on the thinned blank
with nothing injected (``zero`` conditions). What it reports there, in
photons per 100 background counts in the box, is the line it would report on
pure scatter.

Outputs: ``conditions.csv``, ``calibration.csv``, ``scores.csv`` (as the
shootout's, one row per condition × method), ``zero.csv`` (the false
signal), ``log.txt``.
"""
import os

for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):    # one BLAS thread per worker
    os.environ.setdefault(_v, '1')

import argparse
import csv
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
sys.path.insert(0, os.path.join(os.getcwd(), 'tests', 'tools'))

import xrf_shootout as xs                                   # noqa: E402
from synthetic import mca, mca_more as mm                    # noqa: E402

BLANKS = os.path.join('tests', 'reference', 'mca_scatter')
FITS = os.path.join('docs', 'studies', 'mca_scatter', 'scatter_fits.csv')
QUANTITIES = os.path.join('docs', 'studies', 'mca_scatter', 'quantities.csv')
CLEAN = ('E10-k', 'E10-f', 'E9.2-a', 'E9.2-b', 'E9.2-c', 'E9.2-d', 'E6.1-a', 'E6.1-b', 'E6.1-c', 'E6.1-d')
TARGETS = {10.0: ('Zn K', 'Cu K'), 9.2: ('Cu K', 'Ni K'), 6.1: ('Cr K', 'Ti K', 'La L')}
READOUT_FANO = {'A': 0.137, 'B': 0.107}        # medians, docs/studies/mca_scatter/summary.md (two widths)
BACKGROUND = (1000, 3000)                      # counts of the thinned blank in the line's box
RATIOS = (0.1, 0.3, 1.0, 3.0)                  # line photons / those counts
# larch_each is left out by default: 1.2 s a spectrum (the shootout's X8), 60 CPU hours here
DEFAULT_METHODS = tuple(m for m in xs.METHODS if m != 'larch_each')


def load_blank(path):
    """{'id', 'beam', 'readout', 'energy', 'counts', 'calib', 'header'}."""
    head = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            if not line.startswith('#'):
                break
            if ':' in line:
                k, v = line[1:].split(':', 1)
                head[k.strip()] = v.strip()
    with open(path, encoding='utf-8') as f:
        rows = [ln.split(',') for ln in f if ln.strip() and not ln.startswith('#') and not ln.startswith('energy')]
    d = np.array(rows, float)
    e, c = d[:, 0], d[:, 1]
    ch = np.arange(1, len(e) + 1, dtype=float)
    b, a = np.polyfit(ch, e, 1)                    # keV = a + b·channel, channel 1 first (the reader's convention)
    return dict(id=os.path.splitext(os.path.basename(path))[0], beam=float(head['beam_keV']),
                readout=head['readout'], energy=e, counts=c, calib=(float(a), float(b), 0.0), header=head,
                calib_residual=float(np.max(np.abs(a + b * ch - e))))


def _table(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def measured(blank_id):
    """(Detector, Beam, notes) measured on the blank (mca_scatter's fits)."""
    fit = {r['id']: r for r in _table(FITS)}[blank_id]
    q = {r['quantity']: r for r in _table(QUANTITIES) if r['example'] == blank_id}
    beam = float(fit['beam_keV'])
    fano_row = q.get('fano_from_ArKa_and_elastic')
    if fano_row and fano_row['value']:
        fano, fano_from = float(fano_row['value']), 'this blank (Ar Ka and elastic widths)'
    else:
        fano, fano_from = READOUT_FANO[fit['readout']], 'readout %s median' % fit['readout']
    fw = float(fit['elastic_fwhm_keV'])
    stat = (2 * math.sqrt(2 * math.log(2))) ** 2 * mca.xfntr.EPS_SI_KEV * fano * beam
    noise = math.sqrt(max(fw ** 2 - stat, 0.03 ** 2))
    det = mca.Detector(noise=noise, fano=fano, tail=float(fit['tail_fraction']),
                       tail_slope=float(fit['tail_slope_keV']), shelf=float(fit['shelf_fraction']),
                       escape=float(fit['escape_fit_x_reed']))
    bm = mca.Beam(energy=beam, angle=float(fit['angle_2theta_deg']),
                  compton_ratio=float(fit['compton_over_rayleigh']), core_scale=float(fit['o1s_core_scale']))
    return det, bm, dict(fano_from=fano_from, elastic_fwhm=fw, high_tail=float(fit['high_tail_fraction'] or 0))


class BlankCond:
    """One blank, one line, one level. ``cond`` is the shootout's condition
    the methods see (the line alone on the blank's channels); ``p`` the
    thinning; ``photons`` the line's photons (0: the false-signal run)."""

    def __init__(self, blank, target, background, ratio):
        det, bm, self.notes = measured(blank['id'])
        self.blank = blank
        e = blank['energy']
        self.photons = ratio * background
        self.cond = xs.XCond('%s on blank %s' % (target, blank['id']), blank['id'], target=target,
                             lines={target: self.photons}, elastic=0.0, beam=bm, detector=det, background=0.0,
                             calib=blank['calib'], channels=len(e), e_range=(float(e[0]), float(e[-1])))
        lo, hi = self.cond.box_range()
        box = (e >= lo) & (e <= hi)
        self.box_counts = float(blank['counts'][box].sum())
        self.p = background / self.box_counts
        self.background, self.ratio = background, ratio

    def spectra(self):
        if self.photons > 0:
            return self.cond.spectrum()
        return replace(self.cond, lines={self.cond.target: 1.0}).spectrum()    # the same channels, line ignored

    def draw(self, spec, rng):
        thin = rng.binomial(self.blank['counts'].astype(np.int64), self.p).astype(float)
        if self.photons > 0:
            thin = thin + rng.poisson(spec.expected)
        return thin


def design(blanks=CLEAN):
    out = {}
    for bid in blanks:
        b = load_blank(os.path.join(BLANKS, bid + '.csv'))
        for t in TARGETS[b['beam']]:
            for bg in BACKGROUND:
                for r in (0.0,) + RATIOS:
                    name = '%s|%s|%d|%g' % (bid, t, bg, r)
                    out[name] = BlankCond(b, t, bg, r)
    return out


def run_blank(args):
    xs._quiet()
    name, bc, methods, reps, ci = args
    spec = bc.spectra()
    truth = mm.family_photons(spec, bc.cond.target) if bc.photons > 0 else 0.0
    n = bc.cond.series
    rows = []
    for rep in reps:
        rng = np.random.default_rng([20261125, 13, ci, rep])
        counts = [bc.draw(spec, rng) for _ in range(n)]
        for m in methods:
            t0 = time.time()
            try:
                r = xs.run_method(m, bc.cond, [spec] * n, counts)
            except Exception:
                r = [None] * n
            dt = (time.time() - t0) / n
            for k, v in enumerate(r):
                rows.append((name, rep, k, m, None if v is None else v[0], None if v is None else v[1], truth, dt))
    return rows


def zero_score(rows, ks, conds, methods):
    """The false signal: calibrated estimate on the bare thinned blank, in
    photons per 100 box counts, its mean, spread and failures."""
    by = {}
    for name, rep, k, m, est, err, truth, dt in rows:
        by.setdefault((name, m), []).append(est)
    out = []
    for name, bc in conds.items():
        for m in methods:
            v = by.get((name, m))
            if v is None:
                continue
            kk = ks[name][m][0]
            good = np.array([x for x in v if x is not None and np.isfinite(x)], float)
            r = dict(condition=name, blank=bc.blank['id'], target=bc.cond.target, background=bc.background, method=m,
                     n=len(v), failed=len(v) - len(good))
            if len(good) >= 3 and np.isfinite(kk) and kk > 0:
                g = good / kk / bc.background * 100
                r.update(false_per100=float(g.mean()), false_se=float(g.std(ddof=1) / math.sqrt(len(g))),
                         false_sd=float(g.std(ddof=1)))
            out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--replicates', type=int, default=50, help='series of 10 spectra per condition')
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--methods', default='all', help="'all' (every method but larch_each) or a,b")
    ap.add_argument('--blanks', default=None, help='comma-separated blank ids (default: the ten clean ones)')
    ap.add_argument('--chunk', type=int, default=10)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    methods = list(DEFAULT_METHODS) if a.methods == 'all' else a.methods.split(',')
    methods, notes = xs.available(methods)
    conds = design(tuple(a.blanks.split(',')) if a.blanks else CLEAN)
    log = open(os.path.join(a.out, 'log.txt'), 'w', encoding='utf-8', newline='\n')

    def say(s):
        print(s, flush=True)
        log.write(s + '\n')
        log.flush()
    say('xrf_blanks %s: %d conditions on %d blanks, methods %s, %d replicates of 10, %d jobs'
        % (time.strftime('%Y-%m-%d %H:%M:%S'), len(conds), len({c.blank['id'] for c in conds.values()}),
           ','.join(methods), a.replicates, a.jobs))
    for n in notes:
        say(n)
    t0 = time.time()
    ks = {}
    twins = {}
    for name, bc in conds.items():     # one twin per blank × line (the level does not change it)
        twins.setdefault(name.rsplit('|', 2)[0], (name, bc))
    with ProcessPoolExecutor(a.jobs) as ex:
        got = dict(ex.map(xs.calibrate, [v[0] for v in twins.values()], [v[1].cond for v in twins.values()],
                          [methods] * len(twins)))
        for name in conds:
            ks[name] = got[twins[name.rsplit('|', 2)[0]][0]]
        say('calibrated %d blank × line twins in %.0f s' % (len(twins), time.time() - t0))
        futs = []
        for ci, (name, bc) in enumerate(conds.items()):
            for start in range(0, a.replicates, a.chunk):
                futs.append(ex.submit(run_blank, (name, bc, methods, range(start, min(start + a.chunk, a.replicates)),
                                                  ci)))
        rows = []
        done = 0
        for f in as_completed(futs):
            rows += f.result()
            done += 1
            if done % max(1, len(futs) // 20) == 0:
                say('%d/%d tasks, %.0f s' % (done, len(futs), time.time() - t0))
    crow = [dict(condition=n, blank=c.blank['id'], readout=c.blank['readout'], beam_kev=c.blank['beam'],
                 target=c.cond.target, line_kev=c.cond.line, fwhm_kev=c.cond.fwhm, background=c.background,
                 ratio=c.ratio, photons=c.photons, box_counts_full=c.box_counts, p=c.p,
                 noise_kev=c.cond.detector.noise, fano=c.cond.detector.fano, fano_from=c.notes['fano_from'],
                 tail=c.cond.detector.tail, tail_slope=c.cond.detector.tail_slope, shelf=c.cond.detector.shelf,
                 escape_x_reed=c.cond.detector.escape, angle=c.cond.beam.angle, high_tail_not_injected=c.notes['high_tail'],
                 calib_a=c.blank['calib'][0], calib_b=c.blank['calib'][1], calib_residual_kev=c.blank['calib_residual'],
                 fit_range='%.2f-%.2f' % c.cond.fit_range()) for n, c in conds.items()]
    xs.write_csv(os.path.join(a.out, 'conditions.csv'), crow)
    xs.write_csv(os.path.join(a.out, 'calibration.csv'),
                 [dict(condition=n, method=m, k=v[0], seconds=v[1]) for n, d in ks.items() if n in
                  {t[0] for t in twins.values()} for m, v in d.items()])
    inj = {n: c for n, c in conds.items() if c.photons > 0}
    zero = {n: c for n, c in conds.items() if c.photons == 0}
    sc = xs.score([r for r in rows if r[0] in inj], ks, {n: c.cond for n, c in inj.items()}, methods)
    for r in sc:
        c = inj[r['condition']]
        r.update(blank=c.blank['id'], beam_kev=c.blank['beam'], target=c.cond.target, background=c.background,
                 ratio=c.ratio)
    xs.write_csv(os.path.join(a.out, 'scores.csv'), sc)
    xs.write_csv(os.path.join(a.out, 'zero.csv'), zero_score([r for r in rows if r[0] in zero], ks, zero, methods))
    say('done in %.0f s' % (time.time() - t0))
    log.close()


if __name__ == '__main__':
    main()
