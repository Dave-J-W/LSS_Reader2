"""Qoff and the Qz resolution fitted together at the critical edge
(hand-off 09 from the local data agent, the owner 2026-11-26: "Qoffset also
has to be fit, and this could be a useful ability to have in reader"):
known truth, and the NX school check. The method is
``lss_core.fresnel.fit_edge_resolution``; today's proposer
(``propose_qoff``, a sharp R_F) is read beside it on every edge.

    python tests/tools/qoff_resolution_study.py --out docs/studies/qoff_resolution     # K1-K4, about 15 min (4 CPUs)
    python tests/tools/qoff_resolution_study.py --out DIR --replicates 20               # a quick look
    python tests/tools/qoff_resolution_study.py --out DIR --only nx                     # NX only, a minute
    python tests/tools/qoff_resolution_study.py --out DIR --truth --qoff -2e-4 --sigma-q 3.8e-4 --counts 1 --step 0.001 --start 0.015

``--truth`` reruns the known truth at one point (hand-off 09, item 4): a
true Qoff, a true σ_Q, a count level (× the NX school beamline's), a Qz step
and first point. The local data agent uses it to check the method at its
own data's sampling; it writes ``truth.csv`` (one row per replicate) and
prints the summary.

**The synthetic edges** (``edge_scan``): one scan through the edge, as the
first scan of a reflectivity series, drawn by ``tests/synthetic/xrr_scans``
from bare water (Parratt, water's absorption at 10 keV) with the beamline
of NX school scan 6 (2 s per point, the absorber chosen to keep the ROI
below its rate limit, the monitor with 0.05 % noise). The resolution is a
Gaussian of σ_Q, smeared with the generator's 'fine' rule (the default
31-node Gauss–Hermite rule is off by about 1 % at the edge). An angle
offset δα makes the true Qz differ from the recorded one by Qoff.

**The estimators:** ``joint`` (``fit_edge_resolution``, the hand-off's model),
``joint_r3`` (the same with water's 3 Å Névot–Croce roughness in R_F: the
generator's water has it), ``sharp`` (today's ``propose_qoff``).

**The design** (``conditions``): the true Qoff (−5, −2, 0, +3 × 10⁻⁴), the
true σ_Q (0 to 8 × 10⁻⁴; the beamline's median is 3.8), the sampling (the
owner's: steps of 0.001 from 0.013 or from 0.019; NX's: 0.00125 from
0.0175), β wrong by × 2 and × 0.5, counts × 0.1 and × 0.01, the first point
above the edge × 0.7 (an outlier), and fringes near the edge (a 300 Å film
lighter than water, 0.30 e/Å³, period 0.021 Å⁻¹; a DPPC monolayer).

Outputs in ``--out``: ``results.csv`` (condition × estimator × quantity:
bias, SD, pull SD, 95 % coverage, median χ²/dof, flags), ``replicates.csv.gz``,
``nx.csv``, ``numbers.json``, figures K1–K4.
"""
import argparse
import csv
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace, asdict

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from lss_core import fresnel as F                            # noqa: E402
from synthetic import xrr, xrr_scans as xs                   # noqa: E402

NX = 'sample_data/NX_school/2026sep/20260923'
QC = xrr.qc(xrr.RHO_WATER)                                   # 0.02175: the generator's water
BETA = xrr.BETA_WATER_10KEV
K10 = 4 * math.pi / xrr.WAVELENGTH
SIGMA_BEAMLINE = 3.8e-4                                      # DATA_NEEDS row 13's median σ_Q at 10 keV
OWNER = dict(step=0.001, start=0.013)                        # row 13: steps of 0.001; 0.6 Qc
NX_SAMPLING = dict(step=0.00125, start=0.0175)               # NX school scan 6
ESTIMATORS = ('joint', 'joint_r3', 'sharp')
NAMES = {'joint': 'Qoff and σ_Q together (new)', 'joint_r3': 'the same, water\'s 3 Å roughness in R_F',
         'sharp': 'propose_qoff, sharp R_F (today)'}
COLOURS = {'joint': 'C3', 'joint_r3': 'C1', 'sharp': 'C0'}
JOINTS = ('joint', 'joint_r3')
ROUGHNESS = {'joint': 0.0, 'joint_r3': 3.0}             # Å; the generator's water is 3 Å (Névot–Croce)


@dataclass
class Cond:
    design: str
    label: str
    qoff: float = -2e-4
    sigma_q: float = SIGMA_BEAMLINE
    step: float = OWNER['step']
    start: float = OWNER['start']
    stop: float = 0.040                  # NX scan 6 runs to 0.040; the joint fit uses ≤ 0.030
    counts: float = 1.0
    beta_scale: float = 1.0              # the β the fit is given, × the truth's
    outlier: float = 1.0                 # the first point above the edge × this
    sample: str = 'water'


def conditions():
    out = []
    for q in (-5e-4, -2e-4, 0.0, 3e-4):
        out.append(Cond('qoff', 'Qoff %+g' % q, qoff=q))
    for s in (0.0, 1e-4, 2e-4, 3.8e-4, 6e-4, 8e-4):
        out.append(Cond('sigma', 'σ_Q %g' % s, sigma_q=s))
    out.append(Cond('sampling', 'owner: 0.001 from 0.019', start=0.019))
    out.append(Cond('sampling', 'NX: 0.00125 from 0.0175', **NX_SAMPLING))
    out.append(Cond('sampling', 'NX sampling, σ_Q 6e-4', sigma_q=6e-4, **NX_SAMPLING))
    out.append(Cond('beta', 'β × 2 in the fit', beta_scale=2.0))
    out.append(Cond('beta', 'β × 0.5 in the fit', beta_scale=0.5))
    out.append(Cond('counts', 'counts × 0.1', counts=0.1))
    out.append(Cond('counts', 'counts × 0.01', counts=0.01))
    out.append(Cond('outlier', 'first point above the edge × 0.7', outlier=0.7))
    out.append(Cond('sample', '300 Å film (fringes)', sample='film300'))
    out.append(Cond('sample', 'DPPC monolayer', sample='dppc'))
    return out


def profile(name):
    # the film is lighter than water (0.30 e/Å³), so the edge stays water's and a Kiessig fringe of period
    # 2π/300 Å = 0.021 Å⁻¹ crosses the fit's range (a film denser than water would move the edge itself)
    return {'water': xrr.bare_water(), 'dppc': xrr.dppc(), 'film300': xrr.film(300.0, rho=0.30)}[name]


def edge_scan(qoff=-2e-4, sigma_q=SIGMA_BEAMLINE, step=OWNER['step'], start=OWNER['start'], stop=0.040, counts=1.0,
              seed=0, sample='water', outlier=1.0, expected=False):
    """(q, R, σ) of one synthetic scan through the edge (module docstring);
    R per monitor count, as the reader's reduction gives it."""
    deg = math.degrees(qoff / K10)
    bl = xs.Beamline(**xs.REAL_MONITOR, angle_offset_deg=deg)
    bl = replace(bl, flux=bl.flux * counts, max_rate=bl.max_rate * counts)
    plan = [xs.ScanSpec(np.round(np.arange(start, stop + step / 2, step), 10), seconds=2.0)]
    res = (F.fwhm_of(sigma_q), 0.0, 'fine') if sigma_q > 0 else None
    d = xs.measure(profile(sample), plan, beamline=bl, resolution=res, errors='counting+monitor', seed=seed,
                   expected=expected)
    rows = d.per_scan[1]
    q, r, s = rows[:, 0].copy(), rows[:, 1].copy(), rows[:, 2].copy()
    if outlier != 1.0:
        k = int(np.flatnonzero(q > QC - qoff)[0])
        r[k] *= outlier
    return q, r, s


def true_qoff(qoff):
    """The Qoff the generator really applies at Qz 0.02 (an angle offset; constant to 0.2 %)."""
    return float(xs.qoff_of(math.degrees(qoff / K10), 0.02))


def read(q, r, s, beta, bootstrap, seed=1):
    """Every estimator on one edge: a dict of their numbers."""
    out = {}
    for e in JOINTS:
        j = F.fit_edge_resolution(q, r, s, qc=QC, beta=beta, energy_kev=xrr.ENERGY_KEV, bootstrap=bootstrap,
                                  seed=seed, roughness=ROUGHNESS[e])
        out.update({e + '_ok': j.ok, e + '_qoff': j.qoff, e + '_qoff_err': j.qoff_err, e + '_sigma_q': j.sigma_q,
                    e + '_sigma_q_err': j.sigma_q_err, e + '_corr': j.corr, e + '_chi2_dof': j.chi2_dof,
                    e + '_flags': ';'.join(j.flags), e + '_n': j.n_points, e + '_n_below': j.n_below})
    p = F.propose_qoff(q, r, s, qc=QC, method='edge', bootstrap=bootstrap, seed=seed)
    out.update(sharp_ok=p.ok, sharp_qoff=p.qoff, sharp_qoff_err=p.sigma)
    return out


def _one(job):
    c, seed, bootstrap = job
    q, r, s = edge_scan(c.qoff, c.sigma_q, c.step, c.start, c.stop, c.counts, seed=[7, seed], sample=c.sample,
                        outlier=c.outlier)
    out = dict(design=c.design, label=c.label, seed=seed, truth_qoff=true_qoff(c.qoff), truth_sigma_q=c.sigma_q)
    out.update(read(q, r, s, BETA * c.beta_scale, bootstrap))
    return out


def _stats(est, truth, err):
    est, err = np.asarray(est, float), np.asarray(err, float)
    ok = np.isfinite(est)
    e, s = est[ok], err[ok]
    d = dict(n=int(ok.sum()), mean=float(np.mean(e)) if len(e) else math.nan)
    d['bias'] = d['mean'] - truth
    d['sd'] = float(np.std(e, ddof=1)) if len(e) > 1 else math.nan
    d['median_err'] = float(np.nanmedian(s)) if len(s) else math.nan
    good = np.isfinite(s) & (s > 0)
    z = (e[good] - truth) / s[good]
    d['pull_sd'] = float(np.std(z, ddof=1)) if len(z) > 1 else math.nan
    d['cover95'] = float(np.mean(np.abs(z) < 1.96)) if len(z) else math.nan
    return d


def summarise(reps, c):
    rows = []
    t_q = true_qoff(c.qoff)
    for est in ESTIMATORS:
        r = [x for x in reps if x['%s_ok' % est]]
        base = dict(design=c.design, label=c.label, estimator=est, true_qoff=t_q, true_sigma_q=c.sigma_q,
                    step=c.step, start=c.start, counts=c.counts, beta_scale=c.beta_scale, outlier=c.outlier,
                    sample=c.sample, failed=len(reps) - len(r))
        d = _stats([x['%s_qoff' % est] for x in r], t_q, [x['%s_qoff_err' % est] for x in r])
        rows.append(dict(base, quantity='qoff', **d))
        if est in JOINTS:
            d = _stats([x[est + '_sigma_q'] for x in r], c.sigma_q, [x[est + '_sigma_q_err'] for x in r])
            d['median_chi2_dof'] = float(np.nanmedian([x[est + '_chi2_dof'] for x in r])) if r else math.nan
            d['flagged'] = float(np.mean([bool(x[est + '_flags']) for x in r])) if r else math.nan
            d['median_corr'] = float(np.nanmedian([x[est + '_corr'] for x in r])) if r else math.nan
            rows.append(dict(base, quantity='sigma_q', **d))
    return rows


def run(conds, replicates=200, bootstrap=50, workers=None):
    jobs = [(c, k, bootstrap) for c in conds for k in range(replicates)]
    if workers == 1:
        reps = [_one(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            reps = list(ex.map(_one, jobs, chunksize=4))
    rows = []
    for c in conds:
        rows += summarise([r for r in reps if r['label'] == c.label], c)
    return rows, reps


def known_truth(qoff=-2e-4, sigma_q=SIGMA_BEAMLINE, counts=1.0, step=OWNER['step'], start=OWNER['start'], stop=0.040,
                replicates=50, bootstrap=50, beta_scale=1.0, outlier=1.0, sample='water', workers=None):
    """The known truth at one point (hand-off 09, item 4): ``replicates``
    synthetic edges at the given true Qoff, σ_Q, counts (× NX's beamline)
    and sampling, read by both estimators. Returns (summary rows,
    replicate rows)."""
    c = Cond('truth', 'truth', qoff=qoff, sigma_q=sigma_q, step=step, start=start, stop=stop, counts=counts,
             beta_scale=beta_scale, outlier=outlier, sample=sample)
    return run([c], replicates, bootstrap, workers)


def _write(path, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def _write_gz(path, rows):
    """The replicates, gzipped, numbers to 6 significant figures (1.5 MB as plain CSV)."""
    import gzip
    import io
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys)
    w.writeheader()
    for r in rows:
        w.writerow({k: ('%.6g' % v) if isinstance(v, float) else v for k, v in r.items()})
    with gzip.GzipFile(path, 'wb', compresslevel=9, mtime=0) as f:
        f.write(buf.getvalue().encode())


def _plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    return plt


# ---- figures --------------------------------------------------------------------------------

def k1(out):
    """K1: one synthetic edge (σ_Q 3.8e-4, Qoff −2e-4, the owner's sampling) under both estimators."""
    plt = _plt()
    q, r, s = edge_scan(seed=[7, 0])
    j = F.fit_edge_resolution(q, r, s, qc=QC, beta=BETA, bootstrap=200)
    p = F.propose_qoff(q, r, s, qc=QC, bootstrap=200)
    sel = q <= F.EDGE_Q_MAX
    fine = np.linspace(q[sel][0], q[sel][-1], 400)
    # the sharp fit's curve, from its own model (lss_core.fresnel._edge_model)
    from scipy.optimize import least_squares  # noqa: F401  (the fit is propose_qoff's)
    qq, ly, sl = F._prepare(q, r, s, 2.5 * QC, None)
    res = F._edge_estimate(qq, ly, sl, QC, False, start=p.qoff)
    sharp_curve = np.exp(F._edge_model(res.x, fine, QC, False))
    sharp_pts = np.exp(F._edge_model(res.x, q[sel], QC, False))
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    a = ax[0]
    a.errorbar(q[sel], r[sel], s[sel], fmt='o', ms=3, color='k', label='synthetic edge (truth: Qoff −2e-4, σ_Q 3.8e-4)')
    a.plot(fine, sharp_curve, color=COLOURS['sharp'], label='sharp R_F: Qoff %+.2e ± %.1e' % (p.qoff, p.sigma))
    a.plot(fine, j.model(fine), color=COLOURS['joint'],
           label='smeared R_F: Qoff %+.2e ± %.1e,\nσ_Q %.2e ± %.1e' % (j.qoff, j.qoff_err, j.sigma_q, j.sigma_q_err))
    a.set_yscale('log')
    a.axvline(QC, color='0.7', lw=0.8)
    a.set_xlabel('Qz (Å⁻¹)')
    a.set_ylabel('R (per monitor count)')
    a.set_title('One edge, two models', fontsize=10)
    a.legend(fontsize=7)
    b = ax[1]
    b.plot(q[sel], (np.log(r[sel]) - np.log(sharp_pts)) / (s[sel] / r[sel]), 'o-', color=COLOURS['sharp'], ms=3,
           label='sharp: χ²/dof %.1f' % (np.sum(((np.log(r[sel]) - np.log(sharp_pts)) / (s[sel] / r[sel])) ** 2)
                                         / max(1, sel.sum() - 4)))
    b.plot(j.points, j.residuals, 'o-', color=COLOURS['joint'], ms=3, label='smeared: χ²/dof %.2f' % j.chi2_dof)
    b.axhline(0, color='0.5', lw=0.8)
    for v in (-2, 2):
        b.axhline(v, color='0.8', lw=0.8, ls=':')
    b.set_xlabel('Qz (Å⁻¹)')
    b.set_ylabel('residual / its error')
    b.set_title('Residuals: the sharp edge cannot follow the rounding', fontsize=10)
    b.legend(fontsize=7)
    c = ax[2]
    c.plot(q[sel], F.rrf(q, r, QC, p.qoff)[sel] / np.median(r[q < QC - 1e-3]), 'o', color=COLOURS['sharp'], ms=3,
           label='R/R_F at the sharp Qoff')
    c.plot(q[sel], F.rrf(q, r, QC, j.qoff)[sel] / np.median(r[q < QC - 1e-3]), 's', color=COLOURS['joint'], ms=3,
           mfc='none', label='R/R_F at the joint Qoff (the angle offset)')
    c.plot(q[sel], (r / F.fresnel_smeared(q + j.qoff, QC, j.sigma_q, BETA))[sel] / np.median(r[q < QC - 1e-3]),
           '^', color='C2', ms=3, label='R / smeared R_F at the joint fit')
    c.axvline(QC, color='0.7', lw=0.8)
    c.set_xlabel('Qz (Å⁻¹)')
    c.set_ylabel('R / R_F (plateau = 1)')
    c.set_title('What each Qoff does to R/R_F', fontsize=10)
    c.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'K1_anatomy.png'), dpi=100)
    plt.close(fig)
    return dict(joint=j.note, sharp=p.note)


def k2(rows, out):
    """K2: bias ± SD of Qoff (both estimators) and of σ_Q (joint), by condition."""
    plt = _plt()
    labels = list(dict.fromkeys(r['label'] for r in rows))
    fig, ax = plt.subplots(1, 2, figsize=(14, 0.32 * len(labels) + 1.8), sharey=True)
    y = np.arange(len(labels))
    for k, est in enumerate(ESTIMATORS):
        rr = {r['label']: r for r in rows if r['estimator'] == est and r['quantity'] == 'qoff'}
        ax[0].errorbar([rr[l]['bias'] * 1e4 for l in labels], y + (k - 1) * 0.25,
                       xerr=[rr[l]['sd'] * 1e4 for l in labels], fmt='o', ms=4, color=COLOURS[est], label=NAMES[est])
    ax[0].axvline(0, color='0.5', lw=0.8)
    ax[0].set_xlabel('Qoff: bias ± SD (10⁻⁴ Å⁻¹)')
    ax[0].legend(fontsize=7)
    for k, est in enumerate(JOINTS):
        rr = {r['label']: r for r in rows if r['estimator'] == est and r['quantity'] == 'sigma_q'}
        ax[1].errorbar([rr[l]['bias'] * 1e4 for l in labels], y + (k - 0.5) * 0.25,
                       xerr=[rr[l]['sd'] * 1e4 for l in labels], fmt='s', ms=4, color=COLOURS[est], label=NAMES[est])
    ax[1].axvline(0, color='0.5', lw=0.8)
    ax[1].set_xlabel('σ_Q: bias ± SD (10⁻⁴ Å⁻¹)')
    ax[0].set_yticks(y)
    ax[0].set_yticklabels(labels, fontsize=8)
    ax[0].invert_yaxis()
    fig.suptitle('K2. Known truth: bias of each estimator, by condition', fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'K2_bias.png'), dpi=100)
    plt.close(fig)


def k3(rows, out):
    """K3: are the errors honest? Pull SD and 95 % coverage by condition."""
    plt = _plt()
    labels = list(dict.fromkeys(r['label'] for r in rows))
    y = np.arange(len(labels))
    fig, ax = plt.subplots(1, 2, figsize=(14, 0.32 * len(labels) + 1.8), sharey=True)
    series = [('joint', 'qoff', 'o', 'Qoff, joint'), ('joint_r3', 'qoff', 'o', 'Qoff, joint with 3 Å'),
              ('sharp', 'qoff', 'o', 'Qoff, sharp'), ('joint', 'sigma_q', 's', 'σ_Q, joint'),
              ('joint_r3', 'sigma_q', 's', 'σ_Q, joint with 3 Å')]
    for k, (est, qty, m, name) in enumerate(series):
        rr = {r['label']: r for r in rows if r['estimator'] == est and r['quantity'] == qty}
        col = COLOURS[est]
        mfc = col if qty == 'qoff' else 'none'
        ax[0].plot([min(rr[l]['pull_sd'], 30) for l in labels], y + (k - 2) * 0.15, m, color=col, mfc=mfc, ms=4,
                   label=name)
        ax[1].plot([rr[l]['cover95'] * 100 for l in labels], y + (k - 2) * 0.15, m, color=col, mfc=mfc, ms=4,
                   label=name)
    ax[0].axvline(1, color='0.5', lw=0.8)
    ax[0].set_xscale('log')
    ax[0].set_xlabel('pull SD (1: the ± is honest; clipped at 30)')
    ax[1].axvline(95, color='0.5', lw=0.8)
    ax[1].set_xlabel('share of 95 % intervals holding the truth (%)')
    ax[0].set_yticks(y)
    ax[0].set_yticklabels(labels, fontsize=8)
    ax[0].invert_yaxis()
    ax[0].legend(fontsize=7)
    fig.suptitle('K3. Known truth: the errors, by condition', fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'K3_errors.png'), dpi=100)
    plt.close(fig)


ROW13_RUNS = (6.5e-4 / 2.3548, 12.6e-4 / 2.3548)        # row 13's run medians of the FWHM, as σ_Q


def profile_sigma(q, r, s, qc, beta, energy_kev, sigmas, roughness=0.0, f_scale=2.0):
    """The edge fit with σ_Q held at each of ``sigmas`` (N, Qoff, a, b free;
    the method's soft-L1 loss): Qoff and the plain χ²/dof (dof = points − 4)
    at each. Shows what a data set says about its own resolution, and how
    Qoff follows an assumed one."""
    from scipy.optimize import least_squares
    qq, ly, sl = F._prepare(q, r, s, F.EDGE_Q_MAX, F.EDGE_Q_MIN * qc)
    lnn0 = float(np.median(ly[qq < qc - 5e-4]))
    out = []
    for sg in sigmas:
        f = lambda p: (ly - F._edge_res_model([p[0], p[1], sg, p[2], p[3]], qq, qc, beta, energy_kev, True,
                                              roughness)) / sl
        best = None
        for q0 in (-6e-4, -3e-4, -1e-4, 1e-4):
            res = least_squares(f, [lnn0, q0, 0.0, 0.0], loss='soft_l1', f_scale=f_scale, x_scale=[1, 1e-4, 1, 1],
                                diff_step=1e-6, bounds=([-np.inf, F.QOFF_BOUNDS[0], -np.inf, -np.inf],
                                                        [np.inf, F.QOFF_BOUNDS[1], np.inf, np.inf]))
            if best is None or res.cost < best.cost:
                best = res
        out.append(dict(sigma_q=float(sg), qoff=float(best.x[1]),
                        chi2_dof=float(np.sum(best.fun ** 2) / max(1, len(qq) - 4))))
    return out


def nx_check(out, spec=NX, bootstrap=200):
    """K4 and its numbers: NX school scan 6 (the edge scan; its first two
    points lie below the edge), and scans 6–9 joined, as C50 read them."""
    plt = _plt()
    from lss_core.experiment import Experiment
    e = Experiment(spec)
    lam = float(e.scans[6].parameters.get('Wavelength', 1.23984))
    energy = F.HC_KEV_ANGSTROM / lam
    beta = F.subphase_beta(F.subphase('water'), energy)
    qc = F.QC_WATER
    rows, fits = [], {}
    sources = {'scan 6': e.reflectivity([6], errors='budget').per_scan[6],
               'scans 6-9': e.reflectivity([6, 7, 8, 9], errors='budget').ref}
    for name, d in sources.items():
        d = np.asarray(d, float)
        q, r, s = d[:, 0], d[:, 1], d[:, 2]
        j = F.fit_edge_resolution(q, r, s, qc=qc, beta=beta, energy_kev=energy, bootstrap=bootstrap)
        p = F.propose_qoff(q, r, s, qc=qc, bootstrap=bootstrap)
        qq, ly, sl = F._prepare(q, r, s, 2.5 * qc, None)
        res = F._edge_estimate(qq, ly, sl, qc, False, start=p.qoff)
        sharp_chi2 = float(np.sum(res.fun ** 2) / (len(qq) - 4))
        fits[name] = (q, r, s, j, p, res)
        rows.append(dict(data=name, energy_kev=energy, qc=qc, beta=beta, n_points=j.n_points, n_below=j.n_below,
                         n_above=j.n_above, qoff=j.qoff, qoff_err=j.qoff_err, qoff_err_counting=j.qoff_err_counting,
                         sigma_q=j.sigma_q, sigma_q_err=j.sigma_q_err, fwhm=j.fwhm, sigma_alpha_urad=j.sigma_alpha_urad,
                         qoff_deg=j.qoff_deg, corr=j.corr, chi2_dof=j.chi2_dof, flags=';'.join(j.flags),
                         qoff_sharp=p.qoff, qoff_sharp_err=p.sigma, sharp_chi2_dof=sharp_chi2,
                         sharp_points=len(qq), note=j.note))
    q, r, s, j, p, res = fits['scan 6']
    sel = q <= F.EDGE_Q_MAX
    fine = np.linspace(q[sel][0], q[sel][-1], 400)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    a = ax[0]
    a.errorbar(q[sel], r[sel], s[sel], fmt='o', ms=3, color='k', label='NX school scan 6')
    a.plot(fine, np.exp(F._edge_model(res.x, fine, qc, False)), color=COLOURS['sharp'],
           label='sharp R_F: Qoff %+.2e ± %.1e' % (p.qoff, p.sigma))
    a.plot(fine, j.model(fine), color=COLOURS['joint'],
           label='smeared R_F: Qoff %+.2e ± %.1e,\nσ_Q %.2e ± %.1e' % (j.qoff, j.qoff_err, j.sigma_q, j.sigma_q_err))
    a.set_yscale('log')
    a.axvline(qc, color='0.7', lw=0.8)
    a.set_xlabel('Qz (Å⁻¹)')
    a.set_ylabel('R (per monitor count)')
    a.set_title('NX school scan 6 through the edge', fontsize=10)
    a.legend(fontsize=7)
    b = ax[1]
    sharp_pts = np.exp(F._edge_model(res.x, q[sel], qc, False))
    zs = (np.log(r[sel]) - np.log(sharp_pts)) / (s[sel] / r[sel])
    b.plot(q[sel], zs, 'o-', color=COLOURS['sharp'], ms=3, label='sharp (its own range to 2.5 Qc: χ²/dof %.1f)'
           % rows[0]['sharp_chi2_dof'])
    b.plot(j.points, j.residuals, 'o-', color=COLOURS['joint'], ms=3, label='smeared: χ²/dof %.2f' % j.chi2_dof)
    b.axhline(0, color='0.5', lw=0.8)
    for v in (-2, 2):
        b.axhline(v, color='0.8', lw=0.8, ls=':')
    b.set_xlabel('Qz (Å⁻¹)')
    b.set_ylabel('residual / its error')
    b.set_title('Residuals', fontsize=10)
    b.legend(fontsize=7)
    c = ax[2]
    sigmas = np.array([0.0, 0.5e-4, 1e-4, 1.5e-4, 2e-4, 2.5e-4, 3e-4, 3.5e-4, 3.8e-4, 4.5e-4, 5.5e-4])
    prof = profile_sigma(q, r, s, qc, beta, energy, sigmas)
    c.plot(sigmas * 1e4, [x['chi2_dof'] for x in prof], 'o-', color=COLOURS['joint'], ms=4, label='χ²/dof at that σ_Q')
    c.axvspan(ROW13_RUNS[0] * 1e4, ROW13_RUNS[1] * 1e4, color='0.9', label='row 13: the run medians')
    c.axvline(SIGMA_BEAMLINE * 1e4, color='0.6', ls='--', lw=0.8, label='row 13: the beamline\'s median')
    c.set_xlabel('σ_Q held fixed (10⁻⁴ Å⁻¹)')
    c.set_ylabel('χ²/dof')
    c.set_title('NX scan 6: the fit at a fixed σ_Q', fontsize=10)
    c2 = c.twinx()
    c2.plot(sigmas * 1e4, [x['qoff'] * 1e4 for x in prof], 's--', color=COLOURS['sharp'], ms=3, label='Qoff at that σ_Q')
    c2.set_ylabel('Qoff (10⁻⁴ Å⁻¹)', color=COLOURS['sharp'])
    h1, l1 = c.get_legend_handles_labels()
    h2, l2 = c2.get_legend_handles_labels()
    c.legend(h1 + h2, l1 + l2, fontsize=7, loc='upper left')
    rows[0]['profile'] = ';'.join('%g:%.4g:%.4g' % (x['sigma_q'], x['qoff'], x['chi2_dof']) for x in prof)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'K4_nx.png'), dpi=100)
    plt.close(fig)
    _write(os.path.join(out, 'nx.csv'), rows)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--replicates', type=int, default=None, help='per condition (default 200; --truth 50)')
    ap.add_argument('--bootstrap', type=int, default=50)
    ap.add_argument('--workers', type=int, default=None)
    ap.add_argument('--only', choices=('nx', 'synthetic'), default=None)
    ap.add_argument('--designs', default=None, help='comma-separated: qoff, sigma, sampling, beta, counts, outlier, sample')
    ap.add_argument('--truth', action='store_true', help='rerun the known truth at one point (hand-off 09, item 4)')
    ap.add_argument('--qoff', type=float, default=-2e-4)
    ap.add_argument('--sigma-q', type=float, default=SIGMA_BEAMLINE)
    ap.add_argument('--counts', type=float, default=1.0)
    ap.add_argument('--step', type=float, default=OWNER['step'])
    ap.add_argument('--start', type=float, default=OWNER['start'])
    ap.add_argument('--stop', type=float, default=0.040)
    ap.add_argument('--beta-scale', type=float, default=1.0)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    if a.truth:
        rows, reps = known_truth(a.qoff, a.sigma_q, a.counts, a.step, a.start, a.stop, a.replicates or 50, a.bootstrap,
                                 a.beta_scale, workers=a.workers)
        _write(os.path.join(a.out, 'truth.csv'), reps)
        _write(os.path.join(a.out, 'truth_summary.csv'), rows)
        for r in rows:
            print('%-6s %-8s truth %+.3e  bias %+.2e  sd %.2e  pull %.2f  cover95 %.2f  n %d failed %d' % (
                r['estimator'], r['quantity'], r['true_qoff'] if r['quantity'] == 'qoff' else r['true_sigma_q'],
                r['bias'], r['sd'], r['pull_sd'], r['cover95'], r['n'], r['failed']))
        return rows
    numbers = {}
    if a.only != 'synthetic':
        numbers['nx'] = nx_check(a.out, bootstrap=200)
    if a.only != 'nx':
        conds = conditions()
        if a.designs:
            keep = set(a.designs.split(','))
            conds = [c for c in conds if c.design in keep]
        rows, reps = run(conds, a.replicates or 200, a.bootstrap, a.workers)
        _write(os.path.join(a.out, 'results.csv'), rows)
        _write_gz(os.path.join(a.out, 'replicates.csv.gz'), reps)
        numbers.update(replicates=a.replicates or 200, bootstrap=a.bootstrap, results=rows,
                       conditions=[asdict(c) for c in conds], k1=k1(a.out))
        k2(rows, a.out)
        k3(rows, a.out)
        for r in rows:
            print('%-34s %-6s %-8s bias %+.2e sd %.2e pull %.2f cov %.2f%s' % (
                r['label'], r['estimator'], r['quantity'], r['bias'], r['sd'], r['pull_sd'], r['cover95'],
                ('  chi2 %.2f flagged %.2f' % (r['median_chi2_dof'], r['flagged'])) if 'flagged' in r else ''))
    name = 'numbers.json' if a.only is None else 'numbers_%s.json' % a.only
    with open(os.path.join(a.out, name), 'w') as f:
        json.dump(numbers, f, indent=1, default=float)
    return numbers


if __name__ == '__main__':
    main()
