"""Synthesising the excitation scatter of an MCA spectrum at a beam energy that was never measured
(prototype and leave-one-energy-out validation; design memo ``docs/studies/xrf_models/scatter_energy.md``).

    python tests/tools/xrf_scatter_energy.py --out sample_data/private/xrf_models [--jobs 8]
        [--bundle sample_data/private/mca_scatter_cloud/mca_spectra]
        [--stage all|cases|fits|loo|readout_a|figures]

About 15 minutes on 8 processes (fits 6 min, leave-one-out 6 min, figures 1 min).

**Private.** It reads the owner's private spectra bundle (``README_HANDOFF.md`` there) and writes
only under ``--out``, which must be a private folder (``sample_data/private/...``), and figures to
``sample_data/private/figures/xrf_models/``: its tables hold per-case numbers and its figures show
private spectra. The memo quotes derived numbers only.

Stages (each caches its result in ``--out``; a later stage rebuilds what is missing):

1. **cases** (``cases.pkl``, ``cases.csv``): readout B pre-edge sums: the study's
   (``interest.json`` ``public_preedge_sums``, the ones that fitted) and four more at 6.9 keV
   (``EXTRA``), each one detector element of one energy-scan file, members aligned on their mean
   beam energy with ``mca_scatter.rebin_shift`` and summed. Plus readout B's three 10 keV sums
   (E10-d, E10-e, E10-i) and readout A's (E10-f, E10-j, E10-k), which are only predicted, never
   used to predict.
2. **fits** (``fits.pkl``, ``fits.csv``): every case fitted with ``mca_scatter.ScatterModel``
   over E0 − 2.6 … E0 + 0.6 keV (the study's model, every axis free). Only new cases are refitted.
3. **loo** (``loo.csv``, ``loo_summary.txt``): leave one energy group out. Each held-out case is
   predicted from the cases of the other energies only, by each method in ``METHODS``; only an
   overall scale and the calibration offset are then fitted to it. The truth is the held-out
   spectrum minus the nuisance lines of its own free fit (lines are not scatter). Scores over
   E0 − 2.5 … E0: deviance/dof; χ²/dof with the template's own Poisson noise counted (for the
   shifted-spectrum methods); the relative error of the counts in ±2 FWHM windows at
   E0 − 0.6, 1.0, 1.37, 1.74 and 2.0 keV; the false line that a fixed-centre, fixed-width
   Gaussian on a quadratic, fitted by Poisson likelihood in each window (the reader's P1 with
   P2, ``lss_core.peaks.fit_series``), finds on the real and on the predicted scatter; and the
   predicted/real counts in a deep band E0 − 4 … E0 − 2.5 keV, where the crop (from 3 keV)
   reaches, away from known lines. ``same_energy_ref`` is not a predictor: it is another
   measured case at the held-out energy, the floor that real spectra set.
4. **readout_a** (``readout_a.csv``, ``readout_a_summary.txt``): readout A's 10 keV sets carried
   to lower energies, and how much the window counts move under each assumption that has to be
   made there. Computed only.
5. **figures** (private): predicted against real for every held-out case, per energy; the error
   of one transported set against the energy step.
"""
import os

for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):    # one BLAS thread per worker
    os.environ.setdefault(_v, '1')

import argparse
import csv
import json
import math
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.optimize import minimize_scalar

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))                  # tests/
sys.path.insert(0, HERE)                                   # tests/tools/
sys.path.insert(0, ROOT)
from synthetic import mca                                  # noqa: E402
import mca_scatter as ms                                   # noqa: E402

BUNDLE = os.path.join('sample_data', 'private', 'mca_scatter_cloud', 'mca_spectra')
B_GAIN = 0.009992            # readout B keV per channel: the committed blanks' header (gain from the elastic across energies)
FIT_LO, FIT_HI = 2.6, 0.6    # free fits: E0 − 2.6 … E0 + 0.6 keV
EVAL = (2.5, 0.0)            # scores: E0 − 2.5 … E0
DEEP = (4.0, 2.5)            # deep band: E0 − 4 … E0 − 2.5 (from 3.05 keV, the crop)
WINDOWS = (0.6, 1.0, 1.37, 1.74, 2.0)
# extra pre-edge sums: (id, run, escan centre keV, file, element)
# A second run at 7.4 keV was tried and dropped: a sample line near 6.4 keV holds 20 % of the elastic
# peak's height there, so those sums are not scatter-only. The files of EXTRA are private (bundle file ids):
# sample_data/private/xrf_models/probes.json, 'scatter_energy_extra'.
PROBES = os.path.join('sample_data', 'private', 'xrf_models', 'probes.json')


def extra_sums(path=PROBES):
    with open(path, encoding='utf-8') as f:
        return [tuple(x) for x in json.load(f)['scatter_energy_extra']]
# (the 6.9 keV scans were all counted at 0.1–5 kcps; these four are the highest, about 2e5 counts each)
FIXED = ('E10-d', 'E10-e', 'E10-i', 'E10-f', 'E10-j', 'E10-k')
METHODS = ('gen_default', 'gen_hard', 'shift_nearest', 'shift_rate', 'morph_nearest', 'morph_rate',
           'morph_nearest_resid', 'morph_bracket', 'bank_mean',
           'physics', 'physics_resid', 'physics_samerun', 'physics_const', 'physics_local', 'physics_element')


# ================================================================== cases

def _bundle(folder):
    sys.path.insert(0, folder)
    import load                                            # the bundle's own loader
    return load.Bundle(folder)


def _sum_aligned(B, ids):
    """Members of one file and element aligned on their mean beam energy and summed (rebin_shift)."""
    rows = [B.spectra[int(i)] for i in ids]
    e0s = np.array([float(r['e0_keV']) for r in rows])
    e0 = float(e0s.mean())
    c0 = int(rows[0]['first_channel'])
    assert all(int(r['first_channel']) == c0 for r in rows)
    b = float(rows[0]['calib_b_keV'])
    m = min(int(r['n_channels']) for r in rows)
    tot = np.zeros(m)
    for r, e in zip(rows, e0s):
        _, n, _ = B.spectrum(int(r['spectrum']), refined=False)
        tot += ms.rebin_shift(n[:m], 0.0, b, e0 - e)
    real = float(sum(float(r['real_s']) for r in rows))
    return e0, c0, tot, real, rows


def build_cases(bundle_dir):
    B = _bundle(bundle_dir)
    pre = B.interest['public_preedge_sums']
    out = []

    def add(cid, ids, kind):
        e0, c0, tot, real, rows = _sum_aligned(B, ids) if kind == 'preedge' else _sum_fixed(B, ids)
        f = B.files[rows[0]['file']]
        readout = f['readout'][0]
        gain = B_GAIN if readout == 'B' else float(rows[0]['refined_b_keV'] or rows[0]['calib_b_keV'])
        a0 = float(rows[0]['refined_a_keV'] or rows[0]['calib_a_keV']) if readout == 'A' else 0.0
        out.append(dict(id=cid, group=round(e0, 1) if kind == 'preedge' else 10.0, e0=e0, readout=readout,
                        run=f['run'], element=rows[0]['element'], file=rows[0]['file'], n_members=len(ids),
                        real_s=real, c0=c0, calib=(a0 + gain * (c0 - 1), gain, 0.0), counts=tot,
                        rate_cps=float(tot.sum() / real), kind=kind))

    for cid, v in pre.items():
        if v['fit_ok'] == 'True':
            add(cid, v['spectra'], 'preedge')
    by_file = {}
    EXTRA = extra_sums()
    for sid, r in B.spectra.items():
        if r['file'] in {x[1] for x in EXTRA}:
            by_file.setdefault((r['file'], r['element']), []).append(r)
    for cid, fn, el in EXTRA:
        centre = float(B.files[fn]['escan_centre_keV'])
        ids = [int(r['spectrum']) for r in by_file[(fn, el)]
               if r['e0_keV'] and centre - 0.16 <= float(r['e0_keV']) <= centre - 0.03]
        add(cid, ids, 'preedge')
    for cid in FIXED:
        add(cid, B.interest['public_fixed_sums'][cid]['spectra'], 'fixed')
    return out


def _sum_fixed(B, ids):
    rows = [B.spectra[int(i)] for i in ids]
    readout = B.files[rows[0]['file']]['readout'][0]
    e, tot = B.summed(ids, refined=(readout == 'A'))
    e0 = float(rows[0]['e0_keV'] or 10.0)
    real = float(sum(float(r['real_s']) for r in rows))
    return e0, int(rows[0]['first_channel']), tot, real, rows


# ================================================================== fits

def _model(case, lo=FIT_LO, hi=FIT_HI):
    return ms.ScatterModel(case['counts'], case['calib'], case['e0'], lo=lo, hi=hi)


def fit_case(case):
    sm = _model(case)
    p, perr, dev, dof = sm.fit()
    return dict(id=case['id'], file=case['file'], e0=case['e0'], names=list(sm.names), lines=sm.lines, p=p, perr=perr,
                dev=dev, dof=dof)


def P(fit):
    """The fitted parameters by name."""
    return dict(zip(fit['names'], fit['p']))


# ================================================================== physics forms in E0

def water_cr_factor(e0, angle):
    """Compton / Rayleigh differential cross-sections of water (independent atoms; xraylib
    DCS_Compt, DCS_Rayl) at ``e0`` keV and 2θ = ``angle``: how the ratio scales with the beam
    energy at a fixed geometry. Polarisation is the same factor for both, to first order."""
    import xraylib as xl
    t = math.radians(angle)
    c = sum(n * xl.AtomicWeight(z) * xl.DCS_Compt(z, e0, t) for z, n in ((1, 2), (8, 1)))
    r = sum(n * xl.AtomicWeight(z) * xl.DCS_Rayl(z, e0, t) for z, n in ((1, 2), (8, 1)))
    return c / r


def fwhm_from(p, e):
    return mca.Detector(noise=p['noise']).fwhm(e)


def noise_for(fwhm, e):
    """Electronic noise that gives ``fwhm`` at ``e`` with Fano 0.115 (ScatterModel's)."""
    d = mca.Detector(noise=0.0)
    return math.sqrt(max(fwhm ** 2 - d.fwhm(e) ** 2, 1e-6))


def _wmean(v, w):
    v, w = np.asarray(v, float), np.asarray(w, float)
    return float(np.sum(v * w) / np.sum(w))


def _linear(x, y, xt, w=None, clip=None):
    """Weighted straight line through (x, y), evaluated at xt (a constant if the x do not spread)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    w = np.ones_like(x) if w is None else np.asarray(w, float)
    if np.ptp(x) < 0.2:
        v = _wmean(y, w)
    else:
        A = np.vstack([np.ones_like(x), x - xt]).T * np.sqrt(w)[:, None]
        coef, *_ = np.linalg.lstsq(A, y * np.sqrt(w), rcond=None)
        v = float(coef[0])
    if clip:
        v = min(max(v, clip[0]), clip[1])
    return v


SETUP = ('angle', 'core', 'doppler')
DETECTOR = ('escape', 'tail', 'tail_slope', 'shelf')
BOUNDS = dict(escape=(0.3, 3.0), tail=(0.0, 0.3), tail_slope=(0.05, 1.5), shelf=(0.0, 0.05), rtail=(0.0, 0.3),
              rtail_slope=(0.02, 1.0), core=(0.0, 2.0), doppler=(0.5, 2.5), angle=(40.0, 160.0))


def predict_params(target, train, fits, mode='physics'):
    """Parameters for ``target`` (a case) from the free fits of ``train`` (cases of other energies).

    mode 'physics' (the recommended form):
      - resolution: FWHM² linear in E across every training case (noise² + 8 ln2 ε F E), given
        to the model as the noise that gives that FWHM with Fano 0.115;
      - geometry (angle, O 1s wing, Doppler width): the mean of the same run's cases where
        there are any, else of all; the angle weighted by its inverse variance (the high
        energies, where elastic and Compton are resolved, weigh most);
      - Compton/Rayleigh: each training case's ratio × water's cross-section ratio at the target's
        energy over its own (``water_cr_factor``), then the same run's (or all) geometric mean;
      - detector tails, shelf and escape × Reed: a straight line in E0 through every training case;
      - high-energy tail (pile-up): a straight line in the count rate; its slope the median;
      - flat background per elastic photon: the same run's median.
    'physics_samerun': the same, but tails, shelf and escape from the same run only (a line in E0
    when the run spans energies, else its mean). 'physics_const': every parameter the mean of
    all training cases (no energy dependence except the Compton kinematics, Reed and Fano).
    """
    e0 = target['e0']
    pp = [P(fits[c['id']]) for c in train]
    E = np.array([c['e0'] for c in train])
    same = np.array([c['run'] == target['run'] for c in train])
    use = same if same.any() else np.ones(len(train), bool)
    out = {}
    fw2 = np.array([fwhm_from(p, c['e0']) ** 2 for p, c in zip(pp, train)])
    if mode == 'physics_const':
        out['noise'] = float(np.mean([p['noise'] for p in pp]))
    else:
        out['noise'] = noise_for(math.sqrt(_linear(E, fw2, e0)), e0)
    aerr = np.array([max(fits[c['id']]['perr'][fits[c['id']]['names'].index('angle')], 1.0) for c in train])
    aerr = np.where(np.isfinite(aerr), aerr, 30.0)
    sel = use if mode != 'physics_const' else np.ones(len(train), bool)
    out['angle'] = _wmean([p['angle'] for p in pp], sel / aerr ** 2)
    for k in ('core', 'doppler'):
        out[k] = _wmean([p[k] for p in pp], sel.astype(float))
    if mode == 'physics_const':
        out['logR'] = float(np.mean([p['logR'] for p in pp]))
    else:
        lr = [p['logR'] + math.log(water_cr_factor(e0, out['angle']) / water_cr_factor(c['e0'], out['angle']))
              for p, c in zip(pp, train)]
        out['logR'] = _wmean(lr, sel.astype(float))
    for k in DETECTOR:
        y = [p[k] for p in pp]
        if mode in ('physics_local', 'physics_element'):
            el = np.array([c['element'] == target['element'] for c in train])
            pick = el if (mode == 'physics_element' and el.any()) else np.ones(len(train), bool)
            out[k] = _piecewise(np.array([c['group'] for c in train])[pick], np.array(y)[pick], e0, BOUNDS[k])
            continue
        if mode == 'physics_const':
            out[k] = float(np.mean(y))
        elif mode == 'physics_samerun' and same.any():
            out[k] = _linear(E[same], np.array(y)[same], e0, clip=BOUNDS[k])
        else:
            out[k] = _linear(E, y, e0, clip=BOUNDS[k])
    rate = np.array([c['rate_cps'] for c in train])
    if mode == 'physics_const':
        out['rtail'] = float(np.mean([p['rtail'] for p in pp]))
    else:
        out['rtail'] = _linear(rate / 1e5, [p['rtail'] for p in pp], target['rate_cps'] / 1e5, clip=BOUNDS['rtail'])
    out['rtail_slope'] = float(np.median([p['rtail_slope'] for p in pp]))
    bg = [p['bg0'] / math.exp(p['logA']) for p in pp]
    out['bg_rel'] = float(np.median(np.array(bg)[sel]))
    return out


def _piecewise(groups, y, xt, clip):
    """Straight lines between the medians of the energy groups (constant beyond the ends)."""
    gs = np.array(sorted(set(groups.tolist())))
    med = np.array([np.median(y[groups == g]) for g in gs])
    v = float(np.interp(xt, gs, med))
    return min(max(v, clip[0]), clip[1])


def params_at_new_energy(p_src, src, target):
    """Template morphing in model space: one measured case's own fitted parameters carried to the
    target energy (Compton kinematics, Reed's escape and Fano are already the model's; the
    resolution keeps its noise; Compton/Rayleigh scaled by water's cross-sections)."""
    out = {k: p_src[k] for k in ('angle', 'core', 'doppler', 'noise') + DETECTOR + ('rtail', 'rtail_slope')}
    out['logR'] = p_src['logR'] + math.log(water_cr_factor(target['e0'], p_src['angle'])
                                           / water_cr_factor(src['e0'], p_src['angle']))
    out['bg_rel'] = p_src['bg0'] / math.exp(p_src['logA'])
    return out


# ================================================================== predictions as shapes

class Target:
    """A held-out case: its free fit, its scatter-only truth (counts minus the fit's nuisance
    lines), and the model on its channels for predicted parameters."""

    def __init__(self, case, fit):
        self.case = case
        self.sm = ms.ScatterModel(case['counts'], case['calib'], case['e0'], lo=max(DEEP[0], FIT_LO), hi=FIT_HI)
        names = self.sm.names
        p = np.zeros(len(names))
        fp = P(fit)
        for i, k in enumerate(names):
            p[i] = fp.get(k, 0.0)
        self.p_fit = p
        parts = self.sm.parts(p)
        self.lines = sum((sum(v.values()) for k, v in parts.items() if k.startswith('line')),
                         np.zeros(len(self.sm.ch)))
        self.truth = self.sm.n - self.lines
        self.offset_fit = fp['offset']
        a, b, q = case['calib']
        self.e_nom = a + b * self.sm.ch

    def mu(self, pdict, offset, scale=None):
        """Model counts per channel for parameter dict ``pdict`` (no lines), elastic photons
        exp(logA) = 1 unless ``scale``."""
        names = self.sm.names
        p = np.zeros(len(names))
        d = dict(pdict)
        d.setdefault('logA', 0.0)
        d['offset'] = offset
        d['bg0'] = d.pop('bg_rel', 0.0) * math.exp(d['logA'])
        for i, k in enumerate(names):
            p[i] = d.get(k, 0.0)
        return self.sm.mu(p) - 1e-9 * 0


def _scale_offset(target, shape_of_offset, win):
    """Poisson ML of an overall scale (closed form) and the calibration offset (1-D search)."""
    n = target.truth[win]

    def dev_at(off):
        m = shape_of_offset(off)[win]
        s = n.sum() / max(m.sum(), 1e-30)
        mu = np.maximum(s * m, 1e-9)
        with np.errstate(divide='ignore', invalid='ignore'):
            t = np.where(n > 0, n * np.log(np.maximum(n, 1e-30) / mu), 0.0)
        return float(np.sum(2 * (mu - n + t)))
    o0 = target.offset_fit
    r = minimize_scalar(dev_at, bounds=(o0 - 0.04, o0 + 0.04), method='bounded', options=dict(xatol=2e-4))
    m = shape_of_offset(r.x)
    s = n.sum() / max(m[win].sum(), 1e-30)
    return r.x, s, s * m


def shape_physics(target, pdict):
    return lambda off: target.mu(pdict, off)


def shape_generator(target, det):
    """The generator as it stands (``mca_more.spectrum``: Biggs profiles, Beam() at 90° with
    Compton/Rayleigh 1, ``det``), on the target's channels, one elastic photon."""
    from synthetic import mca_more as mm
    c = target.case

    def f(off):
        s = mm.spectrum({}, elastic=1.0, beam=mca.Beam(energy=c['e0']), detector=det, calib=c['calib'],
                        channels=len(c['counts']), offset=off)
        return np.maximum(s.expected[target.sm.sel], 1e-12)
    return f


def shape_template(target, src_case, src_target, resid=None):
    """Shift-nearest: the source's scatter-only counts on its own fitted energy axis, moved by
    ΔE0 and integrated onto the target's channels (cumulative counts)."""
    a, b, _ = src_case['calib']
    s_edges = (a + src_target.offset_fit) + b * np.concatenate([src_target.sm.ch - 0.5, [src_target.sm.ch[-1] + 0.5]])
    cum = np.concatenate([[0.0], np.cumsum(src_target.truth)])
    de0 = target.case['e0'] - src_case['e0']

    def f(off):
        t_edges = target.sm.edges(off)
        c = np.interp(t_edges - de0, s_edges, cum, left=np.nan, right=np.nan)
        return np.diff(c)
    return f


def residual_template(src_case, src_target, fit_src, smooth=0.1):
    """(data − lines − free-fit model) of a training case per elastic photon, against E0 − E,
    smoothed over ``smooth`` keV: the empirical part the physics misses."""
    pf = src_target.p_fit.copy()
    names = src_target.sm.names
    for i, k in enumerate(names):
        if k.startswith('line_'):
            pf[i] = 0.0
    model = src_target.sm.mu(pf)
    r = (src_target.truth - model) / math.exp(P(fit_src)['logA'])
    a, b, _ = src_case['calib']
    e = (a + src_target.offset_fit) + b * src_target.sm.ch
    k = max(1, int(round(smooth / b)))
    rs = np.convolve(r, np.ones(k) / k, mode='same')
    rs[src_case['e0'] - e > FIT_LO] = 0.0             # below the free fit's range the residual is not the model's
    return src_case['e0'] - e, rs


# ================================================================== scores

def false_line(x, y, centre, fwhm):
    """A fixed-centre, fixed-width Gaussian on a quadratic by Poisson likelihood in ±2 FWHM (the
    reader's P1 with P2, ``peaks.fit_series``): the 'line' it finds on scatter alone, as photons
    per 100 counts in the box, with its error."""
    from lss_core import peaks
    lo, hi = centre - 2 * fwhm, centre + 2 * fwhm
    o = peaks.FitOptions(shape='gaussian', background='quadratic', n_peaks=1, centres=(centre,), fix_centres=True,
                         fwhm=fwhm, x_range=(lo, hi), window=50.0)
    y = np.maximum(np.asarray(y, float), 0.0)
    ref, each = peaks.fit_series(x, [y], [np.sqrt(np.maximum(y, 1.0))], o, weights='poisson')
    if not each:
        return float('nan'), float('nan')
    step = float(np.median(np.diff(x)))
    box = (x >= lo) & (x <= hi)
    bgc = max(float(y[box].sum()), 1.0)
    pk = each[0].peaks[0]
    return 100.0 * pk.area / step / bgc, 100.0 * pk.area_err / step / bgc


def score(target, pred, var_template=None, offset=0.0):
    """Scores of predicted counts ``pred`` (already scaled) against the truth."""
    c = target.case
    a, b, _ = c['calib']
    e = (a + offset) + b * target.sm.ch                      # true energies under the fitted offset
    e0 = c['e0']
    win = (e > e0 - EVAL[0]) & (e < e0 - EVAL[1])
    n, m = target.truth, np.maximum(pred, 1e-9)
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(n > 0, n * np.log(np.maximum(n, 1e-30) / m), 0.0)
    dev = 2 * (m - n + t)
    var = np.maximum(m, 1.0) + (0.0 if var_template is None else var_template)
    chi = (n - m) ** 2 / var
    out = dict(dev_dof=float(dev[win].sum() / (win.sum() - 2)), chi_dof=float(chi[win].sum() / (win.sum() - 2)))
    fwhm_of = lambda x: mca.Detector(noise=P_noise(target)).fwhm(x)      # noqa: E731
    for d in WINDOWS:
        x0 = e0 - d
        fw = fwhm_of(x0)
        w = (e > x0 - 2 * fw) & (e < x0 + 2 * fw)
        tr, pr = float(n[w].sum()), float(m[w].sum())
        out['win%.2f' % d] = (pr - tr) / tr
        out['win%.2f_err' % d] = math.sqrt(max(float(target.sm.n[w].sum()), 1.0) + (
            0.0 if var_template is None else float(np.sum(var_template[w])))) / tr
        out['win%.2f_lines' % d] = float(target.lines[w].sum()) / tr
        fr, fre = false_line(e, n, x0, fw)
        fp, _ = false_line(e, m, x0, fw)
        out['fl%.2f_real' % d], out['fl%.2f_real_err' % d], out['fl%.2f_pred' % d] = fr, fre, fp
    deep = (e > e0 - DEEP[0]) & (e < e0 - DEEP[1]) & (e > 3.05)
    if deep.sum() > 20:
        far = deep & ~_near_lines(e)
        out['deep_ratio'] = float(m[far].sum() / max(n[far].sum(), 1.0))
        out['deep_lo_keV'] = float(e0 - e[deep].min())
    return out


def P_noise(target):
    return dict(zip(target.sm.names, target.p_fit))['noise']


KNOWN = (2.957, 3.190, 3.313, 3.590, 3.691, 4.013, 4.509, 4.932, 5.411, 5.947, 5.895, 6.490, 6.400, 7.058)


def _near_lines(e, half=0.1):
    """Channels within ``half`` keV of a K line that turns up in these spectra (Ar to Fe, from
    ``mca_scatter.KLINES``), and of their Si escapes."""
    m = np.zeros(len(e), bool)
    for x in KNOWN:
        m |= np.abs(e - x) < half
        m |= np.abs(e - (x - mca.SI_KA_KEV)) < half
    return m


# ================================================================== leave one energy out

def _neighbours(target, train):
    """Training cases ranked for template use: nearest energy, then same element and run."""
    return sorted(train, key=lambda c: (abs(c['e0'] - target['e0']), c['element'] != target['element'],
                                        c['run'] != target['run']))


def _nearest_same(target, train):
    """The nearest-energy training case, preferring the same detector element (and run)."""
    rk = _neighbours(target, train)
    near_e = abs(rk[0]['e0'] - target['e0'])
    pool = [c for c in rk if abs(abs(c['e0'] - target['e0']) - near_e) < 0.25] or rk[:1]
    pool.sort(key=lambda c: (c['element'] != target['element'], c['run'] != target['run']))
    return pool[0]


def set_distance(target, c):
    """How far a measured set is from the wanted conditions: 1 per keV of beam energy, 1 per factor
    3 in count rate, 0.5 for another detector element, 0.5 for another run (setup). Declared
    before it was scored; not tuned."""
    return (abs(c['e0'] - target['e0']) + abs(math.log10(c['rate_cps'] / target['rate_cps'])) / math.log10(3.0)
            + 0.5 * (c['element'] != target['element']) + 0.5 * (c['run'] != target['run']))


def nearest_set(target, train):
    return min(train, key=lambda c: set_distance(target, c))


def loo_one(args):
    tcase, train, fits, targets_src, peers = args
    T = Target(tcase, fits[tcase['id']])
    rows = []
    det0 = mca.Detector()
    a, b, _ = tcase['calib']

    def emit(method, shape, var=None, src=''):
        win_e = lambda off: (a + off) + b * T.sm.ch      # noqa: E731
        try:
            off, s, pred = _scale_offset(T, shape, (lambda e: (e > tcase['e0'] - EVAL[0]) & (e < tcase['e0']))(
                win_e(T.offset_fit)))
            if not np.all(np.isfinite(pred[(win_e(off) > tcase['e0'] - EVAL[0]) & (win_e(off) < tcase['e0'])])):
                raise ValueError('template does not cover the range')
            vt = None if var is None else var(off) * s ** 2
            r = score(T, pred, vt, off)
        except Exception as exc:                          # recorded, not hidden
            r = dict(error=repr(exc)[:80])
        r.update(id=tcase['id'], group=tcase['group'], e0=tcase['e0'], run=tcase['run'], element=tcase['element'],
                 readout=tcase['readout'], method=method, source=src)
        rows.append(r)
        return r

    # 0. the free fit itself (a floor: everything fitted)
    pf = dict(zip(T.sm.names, T.p_fit))
    pf_nolines = {k: v for k, v in pf.items() if not k.startswith('line_')}
    pf_nolines['bg_rel'] = pf['bg0'] / math.exp(pf['logA'])
    pf_nolines['logA'] = 0.0
    emit('free_fit', shape_physics(T, pf_nolines))
    # 1. the generator's defaults, and study B's hard case (biggs Compton is not in ScatterModel; the
    #    'shells' model it uses is the generator's own)
    emit('gen_default', shape_generator(T, det0))
    emit('gen_hard', shape_generator(T, mca.Detector(noise=0.12, tail=0.01, tail_slope=0.15, shelf=2e-3)))
    # 2. shift the nearest measured spectrum by ΔE0
    src = _nearest_same(tcase, train)
    S = targets_src[src['id']]
    st = shape_template(T, src, S)
    emit('shift_nearest', st, var=lambda off: st(off) * 0 + _template_var(T, src, S, off), src=src['id'])
    # 2b. reference, not a predictor: another measured case at the same energy (same run first, then
    #     another element): how far two real spectra of one energy differ, the floor for any method
    if peers:
        pr = sorted(peers, key=lambda c: (c['run'] != tcase['run'], c['file'] == tcase['file'],
                                          c['element'] != tcase['element']))[0]
        Sp = targets_src[pr['id']]
        sp = shape_template(T, pr, Sp)
        emit('same_energy_ref', sp, var=lambda off: _template_var(T, pr, Sp, off), src=pr['id'])
    # 3. morphing in model space from the same nearest case, with and without its residual
    pm = params_at_new_energy(P(fits[src['id']]), src, tcase)
    emit('morph_nearest', shape_physics(T, pm), src=src['id'])
    src_r = nearest_set(tcase, train)
    emit('morph_rate', shape_physics(T, params_at_new_energy(P(fits[src_r['id']]), src_r, tcase)), src=src_r['id'])
    Sr = targets_src[src_r['id']]
    sr = shape_template(T, src_r, Sr)
    emit('shift_rate', sr, var=lambda off: _template_var(T, src_r, Sr, off), src=src_r['id'])
    de, rr = residual_template(src, S, fits[src['id']])
    emit('morph_nearest_resid', _with_resid(T, shape_physics(T, pm), de, rr), src=src['id'])
    # 4. the physics forms in E0
    for mode in ('physics', 'physics_samerun', 'physics_const', 'physics_local', 'physics_element'):
        pp = predict_params(tcase, train, fits, mode)
        emit(mode, shape_physics(T, pp))
        if mode == 'physics':
            emit('physics_resid', _with_resid(T, shape_physics(T, pp), de, rr), src=src['id'])
            rows[-1]['params'] = json.dumps({k: round(v, 5) for k, v in pp.items()})
            rows[-2]['params'] = rows[-1]['params']
    # 4b. the bank: every training case's own parameter set carried to the target energy.
    #     'morph_bracket': the nearest set below and above (same element first), weighted by
    #     distance in E0; 'bank_mean': the mean of all sets, with the spread of the members' window
    #     counts (each member scaled to the truth like any prediction) as its uncertainty.
    shapes = {}
    for c in train:
        shapes[c['id']] = shape_physics(T, params_at_new_energy(P(fits[c['id']]), c, tcase))
    below = [c for c in train if c['e0'] < tcase['e0']]
    above = [c for c in train if c['e0'] > tcase['e0']]
    pick = lambda pool: sorted(pool, key=lambda c: (abs(c['e0'] - tcase['e0']) > min(  # noqa: E731
        abs(x['e0'] - tcase['e0']) for x in pool) + 0.25, c['element'] != tcase['element'], c['run'] != tcase['run']))[0]
    if below and above:
        lo_c, hi_c = pick(below), pick(above)
        wl = (hi_c['e0'] - tcase['e0']) / (hi_c['e0'] - lo_c['e0'])
        f_lo, f_hi = shapes[lo_c['id']], shapes[hi_c['id']]
        emit('morph_bracket', lambda off: wl * f_lo(off) + (1 - wl) * f_hi(off), src=lo_c['id'] + '+' + hi_c['id'])
    else:
        emit('morph_bracket', shape_physics(T, pm), src=src['id'])
    fl = list(shapes.values())
    r_mean = emit('bank_mean', lambda off: sum(f(off) for f in fl) / len(fl), src='%d sets' % len(fl))
    member = []
    for cid, f in shapes.items():
        try:
            off, sc, pred = _scale_offset(T, f, (lambda e: (e > tcase['e0'] - EVAL[0]) & (e < tcase['e0']))(
                (a + T.offset_fit) + b * T.sm.ch))
            ee = (a + off) + b * T.sm.ch
            fw = lambda x: mca.Detector(noise=P_noise(T)).fwhm(x)      # noqa: E731
            member.append([(pred[(ee > tcase['e0'] - d - 2 * fw(tcase['e0'] - d)) & (ee < tcase['e0'] - d + 2 * fw(
                tcase['e0'] - d))].sum()) for d in WINDOWS])
        except Exception:
            pass
    member = np.array(member)
    for j, d in enumerate(WINDOWS):
        ee = (a + T.offset_fit) + b * T.sm.ch
        fw = mca.Detector(noise=P_noise(T)).fwhm(tcase['e0'] - d)
        tr = float(T.truth[(ee > tcase['e0'] - d - 2 * fw) & (ee < tcase['e0'] - d + 2 * fw)].sum())
        r_mean['win%.2f_bank_sd' % d] = float(np.std(member[:, j]) / tr)
        r_mean['win%.2f_bank_z' % d] = float((tr - member[:, j].mean()) / max(np.std(member[:, j]), 1e-9))
    # 5. one source energy at a time (same element first, then same run): error against ΔE0
    for g in sorted({c['group'] for c in train}):
        pool = sorted([c for c in train if c['group'] == g],
                      key=lambda c: (c['element'] != tcase['element'], c['run'] != tcase['run']))
        sc = pool[0]
        Sg = targets_src[sc['id']]
        emit('morph_from_%.1f' % g, shape_physics(T, params_at_new_energy(P(fits[sc['id']]), sc, tcase)), src=sc['id'])
        sg = shape_template(T, sc, Sg)
        emit('shift_from_%.1f' % g, sg, var=lambda off, sc=sc, Sg=Sg: _template_var(T, sc, Sg, off), src=sc['id'])
    return rows


def _template_var(T, src, S, off):
    """Poisson variance of the shifted template on the target's channels, per unit scale."""
    a, b, _ = src['calib']
    s_edges = (a + S.offset_fit) + b * np.concatenate([S.sm.ch - 0.5, [S.sm.ch[-1] + 0.5]])
    cum = np.concatenate([[0.0], np.cumsum(np.maximum(S.sm.n, 0))])
    de0 = T.case['e0'] - src['e0']
    c = np.interp(T.sm.edges(off) - de0, s_edges, cum)
    return np.nan_to_num(np.diff(c))


def _with_resid(T, shape, de, rr):
    a, b, _ = T.case['calib']

    def f(off):
        m = shape(off)
        e = (a + off) + b * T.sm.ch
        add = np.interp(T.case['e0'] - e, de[::-1], rr[::-1], left=0.0, right=0.0)
        return np.maximum(m + add, 1e-9)
    return f


# ================================================================== driver

def _save(obj, path):
    with open(path, 'wb') as fh:
        pickle.dump(obj, fh)


def _load(path):
    with open(path, 'rb') as fh:
        return pickle.load(fh)


def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        w = csv.DictWriter(fh, keys, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True, help='a private folder (sample_data/private/...)')
    ap.add_argument('--bundle', default=BUNDLE)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--stage', default='all', choices=('all', 'cases', 'fits', 'loo', 'readout_a', 'figures'))
    a = ap.parse_args(argv)
    if 'private' not in os.path.abspath(a.out).replace('\\', '/').split('/'):
        raise SystemExit('--out must be a private folder: these outputs hold private spectra')
    os.makedirs(a.out, exist_ok=True)
    pc, pf = os.path.join(a.out, 'cases.pkl'), os.path.join(a.out, 'fits.pkl')
    if a.stage in ('all', 'cases') or not os.path.exists(pc):
        cases = build_cases(a.bundle)
        _save(cases, pc)
        write_csv(os.path.join(a.out, 'cases.csv'), [{k: v for k, v in c.items() if k not in ('counts', 'calib')}
                                                      for c in cases])
        print('cases', len(cases))
    cases = _load(pc)
    if a.stage in ('all', 'fits') or not os.path.exists(pf):
        old = _load(pf) if os.path.exists(pf) else {}
        todo = [c for c in cases if c['id'] not in old or old[c['id']].get('file') != c['file']
                or abs(old[c['id']].get('e0', 0) - c['e0']) > 1e-9]
        with ProcessPoolExecutor(a.jobs) as ex:
            fl = list(ex.map(fit_case, todo))
        fits = {c['id']: old[c['id']] for c in cases if c['id'] in old}
        fits.update({f['id']: f for f in fl})
        _save(fits, pf)
        rows = []
        for c in cases:
            f = fits[c['id']]
            r = dict(id=c['id'], group=c['group'], e0=c['e0'], run=c['run'], element=c['element'], readout=c['readout'],
                     rate_cps=c['rate_cps'], dev_dof=f['dev'] / f['dof'])
            r.update({k: float(v) for k, v in P(f).items()})
            r['fwhm_e0'] = fwhm_from(P(f), c['e0'])
            r['cr'] = math.exp(P(f)['logR'])
            rows.append(r)
        write_csv(os.path.join(a.out, 'fits.csv'), rows)
        print('fits', len(fits))
    fits = _load(pf)
    if a.stage in ('all', 'loo'):
        run_loo(cases, fits, a.out, a.jobs)
    if a.stage in ('all', 'readout_a'):
        readout_a(cases, fits, a.out)
    if a.stage in ('all', 'figures'):
        figures(cases, fits, a.out, a.jobs)


def run_loo(cases, fits, out, jobs):
    pre = [c for c in cases if c['kind'] == 'preedge' and c['readout'] == 'B']
    groups = sorted({c['group'] for c in pre})
    tgt = {c['id']: Target(c, fits[c['id']]) for c in pre}
    jobsl = []
    for g in groups:
        train = [c for c in pre if c['group'] != g]
        for c in pre:
            if c['group'] == g:
                peers = [x for x in pre if x['group'] == g and x['id'] != c['id']]
                jobsl.append((c, train, fits, tgt, peers))
    fixed = [c for c in cases if c['kind'] == 'fixed']
    for c in fixed:                                        # 10 keV: extrapolated from every pre-edge sum
        tgt[c['id']] = Target(c, fits[c['id']])
    for c in fixed:
        peers = [x for x in fixed if x['readout'] == c['readout'] and x['id'] != c['id']]
        jobsl.append((c, pre, fits, tgt, peers))
    with ProcessPoolExecutor(jobs) as ex:
        res = list(ex.map(loo_one, jobsl))
    rows = [r for rr in res for r in rr]
    write_csv(os.path.join(out, 'loo.csv'), rows)
    summarise(rows, out)


def summarise(rows, out):
    keys = ['dev_dof', 'chi_dof'] + ['win%.2f' % d for d in WINDOWS]
    lines = []
    for g in sorted({r['group'] for r in rows}):
        for ro in ('B', 'A'):
            sub = [r for r in rows if r['group'] == g and r['readout'] == ro and 'error' not in r]
            if not sub:
                continue
            lines.append('== %s keV, readout %s (%d cases)' % (g, ro, len({r['id'] for r in sub})))
            for m in ('free_fit', 'same_energy_ref') + METHODS:
                s = [r for r in sub if r['method'] == m]
                if not s:
                    continue
                vals = ['%s %6.2f' % (k[:7], np.median([r[k] for r in s])) if 'dof' in k else
                        '%s %+6.1f%%' % (k[3:], 100 * np.median([abs(r[k]) for r in s]) * np.sign(
                            np.median([r[k] for r in s]))) for k in keys]
                lines.append('  %-20s %s' % (m, '  '.join(vals)))
    lines += overall(rows)
    txt = '\n'.join(lines)
    print(txt)
    with open(os.path.join(out, 'loo_summary.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(txt + '\n')


def overall(rows):
    """Readout B pre-edge sums, every energy held out in turn: per method the median, rms and
    worst |window error| over cases × windows, the median deviance/dof, and the median
    |false line predicted − real| per window (photons per 100 counts in the box)."""
    rows = [r for r in rows if 'error' not in r and r['readout'] == 'B' and r['group'] < 10]
    groups = sorted({r['group'] for r in rows})
    out = ['', '== readout B, all pre-edge energies held out in turn (%d cases)' % len(
        {r['id'] for r in rows}),
        '  %-20s %s | med|w|  rms|w|  max|w|  dev/dof | |dFL| %s' % (
            'method', ' '.join('%5.1f' % g for g in groups), ' '.join('%.2f' % d for d in WINDOWS))]
    for m in ('free_fit', 'same_energy_ref') + METHODS:
        s = [r for r in rows if r['method'] == m]
        if not s:
            continue
        per = [np.median([abs(r['win%.2f' % d]) for r in s if r['group'] == g for d in WINDOWS]) for g in groups]
        w = np.array([abs(r['win%.2f' % d]) for r in s for d in WINDOWS])
        fl = [np.median([abs(r['fl%.2f_pred' % d] - r['fl%.2f_real' % d]) for r in s]) for d in WINDOWS]
        out.append('  %-20s %s | %5.1f%%  %5.1f%%  %5.0f%%  %7.1f | %s' % (
            m, ' '.join('%4.0f%%' % (100 * p) for p in per), 100 * np.median(w), 100 * math.sqrt(np.mean(w ** 2)),
            100 * w.max(), np.median([r['dev_dof'] for r in s]), ' '.join('%4.1f' % v for v in fl)))
    return out


# ================================================================== readout A at other energies

A_ENERGIES = (6.1, 7.2, 8.3, 9.2, 9.6)
A_VARIANTS = {                     # what has to be assumed for readout A away from 10 keV (computed, not measured)
    'as_at_10keV': {},
    'tail_x1.5': {'tail': 1.5}, 'tail_x0.67': {'tail': 0.67},
    'tail_slope_x0.6': {'tail_slope': 0.6},
    'escape_x1.25': {'escape': 1.25}, 'escape_x0.8': {'escape': 0.8},
    'shelf_+0.01': {'shelf_add': 0.01},
    'doppler_x1.2': {'doppler': 1.2}, 'core_x0.5': {'core': 0.5},
}


def _blank_model(e0, calib=(0.0, 0.01, 0.0)):
    channels = int((e0 + 1.0) / calib[1])
    return ms.ScatterModel(np.ones(channels), calib, e0, lo=EVAL[0] + 0.3, hi=FIT_HI)


def window_counts(sm, pdict, e0):
    """Counts per keV per elastic photon in the ±2 FWHM windows (the study's window_counts view)."""
    d = dict(pdict, logA=0.0, offset=0.0)
    d['bg0'] = d.pop('bg_rel', 0.0)
    p = np.array([d.get(k, 0.0) for k in sm.names])
    mu = sm.mu(p)
    a, b, _ = sm.calib
    e = a + b * sm.ch
    out = []
    for dd in WINDOWS:
        fw = mca.Detector(noise=d['noise']).fwhm(e0 - dd)
        w = (e > e0 - dd - 2 * fw) & (e < e0 - dd + 2 * fw)
        out.append(float(mu[w].sum()) / (4 * fw))
    return out


def readout_a(cases, fits, out):
    """Readout A's three 10 keV sets carried to lower beam energies, and how much the window counts
    move under each assumption that has to be made there (``A_VARIANTS``). Computed only: there is
    no readout A spectrum away from 10 keV to check it against."""
    rows = []
    for c in cases:
        if c['readout'] != 'A':
            continue
        p10 = P(fits[c['id']])
        for e0 in A_ENERGIES:
            sm = _blank_model(e0)
            base = params_at_new_energy(p10, c, dict(e0=e0))
            ref = window_counts(sm, base, e0)
            for name, var in A_VARIANTS.items():
                pv = dict(base)
                for k, f in var.items():
                    if k == 'shelf_add':
                        pv['shelf'] = pv['shelf'] + f
                    else:
                        pv[k] = pv[k] * f
                wc = window_counts(sm, pv, e0)
                r = dict(id=c['id'], e0=e0, variant=name)
                for dd, v, v0 in zip(WINDOWS, wc, ref):
                    r['win%.2f' % dd] = v
                    r['win%.2f_rel' % dd] = v / v0 - 1.0
                rows.append(r)
    write_csv(os.path.join(out, 'readout_a.csv'), rows)
    lines = ['readout A carried from 10 keV: change of window counts per variant (median over the 3 sets);',
             'as_at_10keV: counts per keV per elastic photon']
    for e0 in A_ENERGIES:
        for name in A_VARIANTS:
            s = [r for r in rows if r['e0'] == e0 and r['variant'] == name]
            if name == 'as_at_10keV':
                vals = '  '.join('%.4f' % np.median([r['win%.2f' % dd] for r in s]) for dd in WINDOWS)
            else:
                vals = '  '.join('%+6.1f%%' % (100 * np.median([r['win%.2f_rel' % dd] for r in s])) for dd in WINDOWS)
            lines.append('%4.1f %-16s %s' % (e0, name, vals))
    txt = '\n'.join(lines)
    print(txt)
    with open(os.path.join(out, 'readout_a_summary.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(txt + '\n')


# ================================================================== figures (private)

FIG_METHODS = (('morph_nearest', 'C0', 'transported set (recommended)'), ('physics', 'C2', 'smooth in E0'),
               ('shift_nearest', 'C1', 'nearest, shifted'), ('gen_default', 'C3', 'generator defaults'))


def _fig_preds(args):
    tcase, train, fits, tgt = args
    T = tgt[tcase['id']]
    a, b, _ = tcase['calib']
    src = _nearest_same(tcase, train)
    S = tgt[src['id']]
    shapes = dict(morph_nearest=shape_physics(T, params_at_new_energy(P(fits[src['id']]), src, tcase)),
                  physics=shape_physics(T, predict_params(tcase, train, fits, 'physics')),
                  shift_nearest=shape_template(T, src, S), gen_default=shape_generator(T, mca.Detector()))
    win = lambda e: (e > tcase['e0'] - EVAL[0]) & (e < tcase['e0'])     # noqa: E731
    res = {}
    for k, f in shapes.items():
        off, sc, pred = _scale_offset(T, f, win((a + T.offset_fit) + b * T.sm.ch))
        res[k] = pred
    e = (a + T.offset_fit) + b * T.sm.ch
    return tcase['id'], tcase['e0'], e, T.truth, res, src['id']


def figures(cases, fits, out, jobs=8):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figdir = os.path.join(os.path.dirname(os.path.abspath(out)), 'figures', 'xrf_models')
    if 'private' not in figdir.replace('\\', '/').split('/'):
        raise SystemExit('figures must go under a private folder')
    os.makedirs(figdir, exist_ok=True)
    pre = [c for c in cases if c['kind'] == 'preedge' and c['readout'] == 'B']
    tgt = {c['id']: Target(c, fits[c['id']]) for c in pre}
    groups = sorted({c['group'] for c in pre})
    jl = [(c, [x for x in pre if x['group'] != c['group']], fits, tgt) for c in pre]
    with ProcessPoolExecutor(jobs) as ex:
        res = {r[0]: r for r in ex.map(_fig_preds, jl)}
    for g in groups:
        ids = [c['id'] for c in pre if c['group'] == g]
        fig, ax = plt.subplots(2, len(ids), figsize=(4.2 * len(ids), 7), sharex=True,
                               gridspec_kw=dict(height_ratios=(3, 1.4)), squeeze=False)
        for j, cid in enumerate(ids):
            _, e0, e, tr, pr, src = res[cid]
            x = e0 - e
            k = 5                                            # 50 eV bins for the ratio panel
            n = len(x) // k * k
            ax[0, j].plot(x, np.maximum(tr, 0.5), color='k', lw=0.7, label='real (lines taken off)')
            for m, col, lab in FIG_METHODS:
                ax[0, j].plot(x, pr[m], color=col, lw=0.9, label=lab)
                rr = pr[m][:n].reshape(-1, k).sum(1) / np.maximum(tr[:n].reshape(-1, k).sum(1), 1.0)
                ax[1, j].plot(x[:n].reshape(-1, k).mean(1), rr, color=col, lw=0.9)
            ax[0, j].set_yscale('log')
            ax[0, j].set_title('%s (%.2f keV) from %s' % (cid, e0, src), fontsize=9)
            ax[1, j].axhline(1, color='k', lw=0.5)
            ax[1, j].set_ylim(0, 2)
            ax[1, j].set_xlim(3.0, -0.3)
            for d in WINDOWS:
                ax[1, j].axvline(d, color='0.8', lw=0.5)
            ax[1, j].set_xlabel('E0 - E (keV)')
        ax[0, 0].set_ylabel('counts per channel')
        ax[1, 0].set_ylabel('predicted / real')
        ax[0, 0].legend(fontsize=7)
        fig.suptitle('PRIVATE. Readout B, leave %.1f keV out: predicted from the other energies, scale and offset '
                     'fitted' % g, fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(figdir, 'loo_%.1fkeV_private.png' % g), dpi=90)
        plt.close(fig)
    # error against the energy step, by where the source set came from (derived numbers only)
    with open(os.path.join(out, 'loo.csv'), encoding='utf-8') as fh:
        rows = [r for r in csv.DictReader(fh) if not r.get('error')]
    cd = {c['id']: c for c in cases}
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for kind, mk in (('morph', 'o'), ('shift', 'x')):
        for lab, col, cond in (('same run', 'C0', True), ('other run', 'C3', False)):
            xs, ys = [], []
            for r in rows:
                if r['readout'] == 'B' and r['method'].startswith(kind + '_from_') and float(r['group']) < 10:
                    sc = cd[r['source']]
                    if (sc['run'] == r['run']) == cond:
                        xs.append(float(r['e0']) - sc['e0'])
                        ys.append(100 * np.mean([abs(float(r['win%.2f' % d])) for d in WINDOWS]))
            ax.plot(xs, ys, mk, color=col, ms=4, alpha=0.7, label='%s, %s' % (
                'transported set' if kind == 'morph' else 'shifted spectrum', lab))
    ax.set_xlabel('target E0 - source E0 (keV)')
    ax.set_ylabel('mean |window error| (%)')
    ax.set_title('Readout B: prediction from one measured case at another energy')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(figdir, 'loo_error_vs_dE_private.png'), dpi=90)
    plt.close(fig)
    print('figures in', figdir)


if __name__ == '__main__':
    main()
