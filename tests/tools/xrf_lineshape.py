"""Is a Gaussian enough for a real fluorescence line? The shape of real
lines on both detectors, by a ladder of shapes (2026-11-25;
``docs/studies/xrf_models/README.md``, part 2).

    python tests/tools/xrf_lineshape.py --out sample_data/private/xrf_models/lines \\
        --public docs/studies/xrf_models/lines

The spectra are private (``sample_data/private/mca_scatter_cloud/
mca_spectra``, decrypted). ``--out`` gets the fits and the figures (private:
spectra and peak positions); ``--public`` gets ``line_shapes.csv``, derived
numbers only: no spectrum, no peak position, no element (each probe's line
family is identified from the data at run time and never written).

**The probes** (anonymous bundle file ids):

* ``A-L*``: readout A (the single-element detector), five files of 16
  spectra at 10 keV holding one L family (Ll, Lα, Lβ, Lγ lines) at
  10⁵–10⁶ counts, summed per file;
* ``A-K``: readout A, the burn series' line near 8 keV (``p1_series``), the
  nine series with 3·10⁴–8·10⁴ line counts summed;
* ``B-K<e>``: readout B (one element ``e`` of the seven-element detector),
  two files where all seven elements saw one K family at S/B ≈ 70, each
  element alone (elements 1-7, 2 spectra each), and the seven summed: raw
  channel by raw channel (``sum7raw``, what summing the elements' channels
  gives) and each first put on one energy axis by its header calibration
  (``sum7hdr``). Every element is fitted on element 1's calibration by raw
  channel: in file 2 the header's gain for elements 5-7 is 8.6 % off.

**The shapes**, every line of the family through the same response
(``synthetic.mca._response``), tabulated energies and intensities
(``synthetic.mca_more``) with one free amplitude per subshell (K: Kα, Kβ;
L: L1, L2, L3), a free energy offset and gain, a quadratic background and,
where they fall in the window, free Gaussians for the elastic's and the
Compton peak's Si escape:

* ``gauss_res``: Gaussian, width fixed to the readout's resolution as
  measured on the scatter (``docs/studies/mca_scatter``: A noise 0.065 keV,
  Fano 0.137; B 0.105 keV, 0.107);
* ``gauss``: Gaussian, width free (the noise; Fano fixed);
* ``elastic``: the shape measured on the readout's elastic line (A: tail 2 %
  over 0.64 keV, no shelf; B: the medians of the B blanks), width free;
* ``tail``: one low-energy exponential tail (fraction, decay), width free;
* ``tail_shelf``: and a flat shelf;
* ``hypermet``: and a second, short tail.

The Si escape of each line is Reed's fraction × the readout's measured
factor (the medians of the scatter fits: A 0.87, B 1.10).
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
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from synthetic import mca, mca_more as mm                     # noqa: E402

BUNDLE = os.path.join('sample_data', 'private', 'mca_scatter_cloud', 'mca_spectra')
RESOLUTION = {'A': (0.065, 0.137), 'B': (0.105, 0.107)}       # noise keV FWHM, Fano (mca_scatter summary)
# tail, slope keV, shelf: medians of the good fits in docs/studies/mca_scatter/scatter_fits.csv (A 7, B 23)
ELASTIC_SHAPE = {'A': (0.0197, 0.636, 0.0), 'B': (0.052, 0.338, 0.008)}
ESCAPE = {'A': 0.87, 'B': 1.10}                                # × Reed, the same fits' medians
SUBSHELL = {'Ka1': 'Ka', 'Ka2': 'Ka', 'Kb1': 'Kb', 'Kb3': 'Kb', 'Kb2': 'Kb', 'Kb5': 'Kb',
            'La1': 'L3', 'La2': 'L3', 'Lb2': 'L3', 'Lb15': 'L3', 'Ll': 'L3', 'Lb6': 'L3', 'Lb5': 'L3', 'Ls': 'L3',
            'Lb1': 'L2', 'Lg1': 'L2', 'Leta': 'L2', 'Lg5': 'L2', 'Lg6': 'L2',
            'Lb3': 'L1', 'Lb4': 'L1', 'Lg2': 'L1', 'Lg3': 'L1', 'Lb9': 'L1', 'Lb10': 'L1'}
SHAPES = ('gauss_res', 'gauss', 'elastic', 'tail', 'tail_shelf', 'hypermet')
PN = ['offset', 'gain', 'bg0', 'bg1', 'bg2', 'noise', 'tail', 'tail_slope', 'shelf', 'tail2', 'tail2_slope']
PROBES = os.path.join('sample_data', 'private', 'xrf_models', 'probes.json')


def private_probes(path=PROBES):
    """Which bundle files the study reads. Bundle file ids are private, so the list lives beside the
    decrypted bundle (git-ignored), not here; the owner's local session has it."""
    import json
    with open(path, encoding='utf-8') as f:
        return json.load(f)
A_K_SERIES = ('S10-k', 'S10-l', 'S10-m', 'S10-n', 'S10-o', 'S10-p', 'S10-q', 'S10-r', 'S10-s')
ELASTIC_E0 = 10.0
COMPTON_A = mca.compton_energy(10.0, 91.2)                      # readout A's measured angle


class LineFit:
    """One spectrum, one family, one shape."""

    def __init__(self, e, n, family, readout, shape, beam=ELASTIC_E0):
        self.family, self.readout, self.shape = family, readout, shape
        lines = [(nm, en, i) for nm, en, i in mm.family_lines(family, beam) if i > 0]
        tot = sum(i for *_, i in lines)
        strong = [en for _, en, i in lines if i / tot > 0.01]
        lo = min(strong) - 0.9
        hi = min(max(strong) + 0.35, beam - 1.25)
        sel = (e > lo) & (e < hi)
        self.e, self.n = e[sel], n[sel]
        b = float(np.median(np.diff(e)))
        self.edges = np.r_[self.e - b / 2, self.e[-1] + b / 2]
        self.lines = lines
        self.groups = sorted({SUBSHELL.get(nm, 'other') for nm, *_ in lines})
        self.gsum = {g: sum(i for nm, _, i in lines if SUBSHELL.get(nm, 'other') == g) for g in self.groups}
        self.ec = 0.5 * (lo + hi)
        self.window = (float(self.e[0]), float(self.e[-1]))
        self.nuis = [(x, w) for x, w in ((beam - mca.SI_KA_KEV, 0.0), (COMPTON_A - mca.SI_KA_KEV, 0.28))
                     if lo + 0.05 < x < hi - 0.05]
        self.names = PN + ['amp_' + g for g in self.groups] + ['nuis%d' % k for k in range(len(self.nuis))]
        noise0, self.fano = RESOLUTION[readout]
        t, s, sh = ELASTIC_SHAPE[readout]
        fix = {'tail2': 0.0, 'tail2_slope': 0.05}
        if shape in ('gauss_res', 'gauss'):
            fix.update(tail=0.0, tail_slope=0.3, shelf=0.0)
        if shape == 'gauss_res':
            fix['noise'] = noise0
        if shape == 'elastic':
            fix.update(tail=t, tail_slope=s, shelf=sh)
        if shape == 'tail':
            fix['shelf'] = 0.0
        if shape == 'hypermet':
            fix.pop('tail2')
            fix.pop('tail2_slope')
        self.fix = fix

    def model(self, p):
        P = dict(zip(self.names, p))
        P.update(self.fix)
        det = mca.Detector(noise=P['noise'], fano=self.fano, tail=P['tail'], tail_slope=P['tail_slope'],
                           shelf=P['shelf'], escape=ESCAPE[self.readout])
        es, ns = [], []
        for nm, en, i in self.lines:
            g = SUBSHELL.get(nm, 'other')
            es.append(en + P['offset'] + P['gain'] * (en - self.ec))
            ns.append(math.exp(P['amp_' + g]) * i / self.gsum[g])
        acc = {k: np.zeros(len(self.e)) for k in ('peak', 'tail', 'shelf', 'escape')}
        mca._response(self.edges, es, ns, det, acc)
        t2 = P['tail2']
        if t2 > 0:
            keep = 1.0 - P['tail'] - P['shelf'] - det.escape_fraction(es[0])
            acc['peak'] *= max(keep - t2, 0.0) / max(keep, 1e-9)
            a2 = {k: np.zeros(len(self.e)) for k in ('peak', 'tail', 'shelf', 'escape')}
            mca._response(self.edges, es, ns, mca.Detector(noise=P['noise'], fano=self.fano, tail=t2,
                                                           tail_slope=P['tail2_slope'], escape=0.0), a2)
            acc['tail2'] = a2['tail']
        x = 0.5 * (self.edges[:-1] + self.edges[1:]) - self.ec
        acc['bg'] = P['bg0'] + P['bg1'] * x + P['bg2'] * x ** 2
        for k, (c, w) in enumerate(self.nuis):
            fw = math.hypot(det.fwhm(c), w)
            sg = fw / 2.3548
            acc['nuis%d' % k] = P['nuis%d' % k] * np.diff(0.5 * (1 + _erf((self.edges - c) / (sg * math.sqrt(2)))))
        return acc

    def mu(self, p):
        return np.maximum(sum(self.model(p).values()), 1e-9)

    def resid(self, p):
        mu, n = self.mu(p), self.n
        with np.errstate(divide='ignore', invalid='ignore'):
            t = np.where(n > 0, n * np.log(n / mu), 0.0)
        return np.sign(n - mu) * np.sqrt(np.maximum(2 * (mu - n + t), 0))

    def start(self, prev=None):
        bg = max(float(np.percentile(self.n, 5)), 0.5)
        tot = max(float(self.n.sum() - bg * len(self.n)), 10.0)
        p = dict(offset=0.0, gain=0.0, bg0=bg, bg1=0.0, bg2=0.0, noise=RESOLUTION[self.readout][0], tail=0.03,
                 tail_slope=0.4, shelf=0.003, tail2=0.03, tail2_slope=0.06)
        lo = dict(offset=-0.25, gain=-0.03, bg0=-1e7, bg1=-1e8, bg2=-1e8, noise=0.02, tail=0.0, tail_slope=0.03,
                  shelf=0.0, tail2=0.0, tail2_slope=0.01)
        hi = dict(offset=0.25, gain=0.03, bg0=1e8, bg1=1e8, bg2=1e8, noise=0.4, tail=0.95, tail_slope=3.0, shelf=0.3,
                  tail2=0.5, tail2_slope=0.2)
        for g in self.groups:
            p['amp_' + g], lo['amp_' + g], hi['amp_' + g] = math.log(tot * self.gsum[g]), math.log(tot) - 15, math.log(tot) + 5
        for k in range(len(self.nuis)):
            p['nuis%d' % k], lo['nuis%d' % k], hi['nuis%d' % k] = tot * 1e-3, 0.0, tot
        if prev is not None:
            p.update({k: v for k, v in prev.items() if k in p})
        v = [np.clip(p[k], lo[k], hi[k]) for k in self.names]
        return np.array(v, float), np.array([lo[k] for k in self.names]), np.array([hi[k] for k in self.names])

    def fit(self, prev=None):
        p, lo, hi = self.start(prev)
        free = [i for i, k in enumerate(self.names) if k not in self.fix]
        pf = p.copy()

        def r(x):
            q = pf.copy()
            q[free] = x
            return self.resid(q)
        best = None
        for off in ((0.0,) if prev is not None else (-0.08, 0.0, 0.08)):
            x0 = p[free].copy()
            x0[free.index(0)] = off if prev is None else x0[free.index(0)]
            sol = least_squares(r, x0, bounds=(lo[free], hi[free]), x_scale='jac', max_nfev=600)
            if best is None or sol.cost < best.cost:
                best = sol
        pf[free] = best.x
        P = dict(zip(self.names, pf))
        P.update(self.fix)
        dev = float(np.sum(self.resid(pf) ** 2))
        return P, pf, dev, len(self.n) - len(free)


def _erf(x):
    from scipy.special import erf
    return erf(x)


def identify(e, n, readout, beam=ELASTIC_E0):
    """The tabulated family that fits the spectrum best as Gaussians at the
    readout's resolution. Returned only, never written."""
    from scipy.ndimage import uniform_filter1d
    m = (e > 3.5) & (e < beam - 1.3)
    peak = float(e[m][np.argmax(uniform_filter1d(n[m], 5))])
    best = None
    for fam, v in mm.TABLES['lines'].items():
        ls = mm.family_lines(fam, beam)
        if v['edge'] >= beam or not ls:
            continue
        tot = sum(i for *_, i in ls)
        if not any(abs(en - peak) < 0.12 and i / tot > 0.05 for _, en, i in ls):
            continue                                       # it must explain the strongest peak
        lf = LineFit(e, n, fam, readout, 'gauss', beam)
        P, p, dev, dof = lf.fit()
        if best is None or dev / dof < best[1]:
            best = (fam, dev / dof)
    return best[0]


def fit_probe(args):
    """Every shape on one probe: rows (derived numbers only) and the private
    arrays for the figures."""
    label, readout, e, n, family = args
    rows, arrays, prev = [], {}, None
    for sh in SHAPES:
        lf = LineFit(e, n, family, readout, sh)
        P, p, dev, dof = lf.fit(prev)
        if sh == 'gauss':
            prev = {k: P[k] for k in P}
        parts = lf.model(p)
        line = sum(v for k, v in parts.items() if k in ('peak', 'tail', 'shelf', 'escape', 'tail2'))
        main = max(lf.lines, key=lambda t: t[2])
        det = mca.Detector(noise=P['noise'], fano=lf.fano)
        fw = det.fwhm(main[1])
        res = mca.Detector(noise=RESOLUTION[readout][0], fano=lf.fano).fwhm(main[1])
        ntail = sum(float(parts[k].sum()) for k in ('tail', 'shelf', 'tail2') if k in parts)
        rows.append(dict(probe=label, readout=readout, kind=family.split()[1], shape=sh, counts_in_window=float(lf.n.sum()),
                         line_counts=float(line.sum()), deviance=dev, dof=dof, dev_per_dof=dev / dof,
                         fwhm_main_keV=fw, resolution_fwhm_keV=res, fwhm_over_resolution=fw / res,
                         noise_keV=P['noise'], tail=P['tail'], tail_slope_keV=P['tail_slope'], shelf=P['shelf'],
                         tail2=P['tail2'], tail2_slope_keV=P['tail2_slope'],
                         non_gaussian_fraction_in_window=ntail / max(float(line.sum()), 1e-9),
                         window_width_keV=lf.window[1] - lf.window[0], gain=P['gain']))
        arrays[sh] = dict(e=lf.e, n=lf.n, mu=lf.mu(p), parts={k: v for k, v in parts.items()},
                          resid=lf.resid(p), offset=P['offset'])
    best = min(r['deviance'] for r in rows)
    for r in rows:
        r['ddev_vs_best'] = r['deviance'] - best
    return label, rows, arrays


def probes(folder=BUNDLE):
    """[(label, readout, e, n)] from the private bundle."""
    sys.path.insert(0, folder)
    import load
    B = load.Bundle(folder)

    def at10(fn, el=''):
        return [s for s, r in B.spectra.items() if r['file'] == fn and r['element'] == el and r['e0_keV']
                and abs(float(r['e0_keV']) - 10.0) < 0.05]
    out = []
    P = private_probes()
    for k, fn in enumerate(P['lineshape_a_l_files']):
        e, n = B.summed(at10(fn))
        out.append(('A-L%d' % (k + 1), 'A', e, n))
    tot, e0 = None, None
    for name in A_K_SERIES:
        v = B.interest['p1_series'][name]
        v = v['spectra'] if isinstance(v, dict) else v
        e, n = B.summed(list(range(v[0], v[-1] + 1)))
        if tot is None:
            e0, tot = e, n.copy()
        else:
            tot += np.interp(e0, e, n)
    out.append(('A-K', 'A', e0, tot))
    for k, fn in enumerate(P['lineshape_b_k_files']):
        per, raw = {}, {}
        for el in range(1, 8):                               # the elements are numbered 1 to 7
            ii = at10(fn, str(el))
            if ii:
                per[el] = B.summed(ii)
                r = B.spectra[ii[0]]
                raw[el] = (int(r['first_channel']), per[el][1])
        # Every element on element 1's calibration by raw channel. In file 2 the header gives elements 5-7 a
        # gain 8.6 % above the others, which puts their K alpha 8.6 % too high; their raw channels line up
        # with elements 1-4 (README, part 2), so the header gain is wrong there.
        ref = min(per)
        c0 = raw[ref][0]
        e7 = per[ref][0]
        a1, b1 = float(e7[0]) - float(np.median(np.diff(e7))) * c0, float(np.median(np.diff(e7)))
        for el, (c, n) in raw.items():
            out.append(('B-K%d-e%d' % (k + 1, el), 'B', a1 + b1 * np.arange(c, c + len(n)), n))
        n7 = np.zeros_like(e7)
        for el, (c, n) in raw.items():
            lo = c - c0
            for i, v in enumerate(n):
                if 0 <= lo + i < len(n7):
                    n7[lo + i] += v
        out.append(('B-K%d-sum7raw' % (k + 1), 'B', e7, n7))
        # each element first put on element 1's energy axis by its header calibration (cumulative counts): what
        # trusting the header gives
        nc = np.zeros_like(e7)
        b7 = float(np.median(np.diff(e7)))
        ed = np.r_[e7 - b7 / 2, e7[-1] + b7 / 2]
        for el, (e, n) in per.items():
            b = float(np.median(np.diff(e)))
            cum = np.r_[0.0, np.cumsum(n)]
            nc += np.diff(np.interp(ed, np.r_[e - b / 2, e[-1] + b / 2], cum))
        out.append(('B-K%d-sum7hdr' % (k + 1), 'B', e7, nc))
    return out


def probe_key(label):
    """The probe a label belongs to: 'B-K1-e3' and 'B-K1-sum7raw' are 'B-K1'."""
    return label.split('-e')[0].split('-sum')[0]


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


def figure(arrays, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labs = [k for k in arrays if k in ('A-L1', 'A-K', 'B-K2-e1', 'B-K2-e6', 'B-K2-sum7raw', 'B-K2-sum7hdr')]
    fig, axes = plt.subplots(2, len(labs), figsize=(4.2 * len(labs), 6.5), sharex='col',
                             gridspec_kw=dict(height_ratios=(2.2, 1)))
    cols = {'gauss_res': '#b8b8b8', 'gauss': '#d1495b', 'elastic': '#edae49', 'tail_shelf': '#00798c',
            'hypermet': '#30638e'}
    for j, lab in enumerate(labs):
        A = arrays[lab]
        ax, rx = axes[0, j], axes[1, j]
        e, n = A['gauss']['e'], A['gauss']['n']
        ax.semilogy(e, np.maximum(n, 0.5), '.', ms=2, color='k', label='data')
        for sh, c in cols.items():
            ax.semilogy(e, A[sh]['mu'], color=c, lw=1, label=sh)
            rx.plot(e, A[sh]['resid'], color=c, lw=0.8)
        ax.set_title(lab, fontsize=9)
        rx.axhline(0, color='k', lw=0.5)
        rx.set_ylim(-12, 12)
        rx.set_xlabel('keV')
    axes[0, 0].legend(fontsize=7)
    axes[1, 0].set_ylabel('deviance residual')
    fig.suptitle('PRIVATE. Real lines against the shape ladder (tests/tools/xrf_lineshape.py)', fontsize=9, x=0.01,
                 ha='left')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'L1_line_fits_private.png'), dpi=110)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--bundle', default=BUNDLE)
    ap.add_argument('--out', required=True, help='private folder: fits and figures')
    ap.add_argument('--public', default=None, help='public folder: line_shapes.csv (derived numbers only)')
    ap.add_argument('--jobs', type=int, default=10)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    P = probes(a.bundle)
    fams = {}
    for lab, ro, e, n in P:
        key = probe_key(lab)
        if key not in fams:
            fams[key] = identify(e, n, ro)
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(fit_probe, [(lab, ro, e, n, fams[probe_key(lab)]) for lab, ro, e, n in P]))
    rows, arrays = [], {}
    for lab, r, arr in res:
        rows += r
        arrays[lab] = arr
    write_csv(os.path.join(a.out, 'line_fits_private.csv'), [dict(r, family=fams[probe_key(r['probe'])])
                                                             for r in rows])
    np.save(os.path.join(a.out, 'arrays_private.npy'), arrays, allow_pickle=True)
    if a.public:
        os.makedirs(a.public, exist_ok=True)
        write_csv(os.path.join(a.public, 'line_shapes.csv'), rows)
    figure(arrays, a.out)
    for r in rows:
        print('%-11s %-10s D/dof %7.2f dD %8.1f  fwhm/res %.3f  tail %.3f/%.2f shelf %.4f t2 %.3f/%.3f ng %.3f' % (
            r['probe'], r['shape'], r['dev_per_dof'], r['ddev_vs_best'], r['fwhm_over_resolution'], r['tail'],
            r['tail_slope_keV'], r['shelf'], r['tail2'], r['tail2_slope_keV'], r['non_gaussian_fraction_in_window']))


if __name__ == '__main__':
    main()
