"""The figures and numbers of docs/reports/patch_demo.md, made with the
same code the window uses (``refl``, ``burnmode``, ``draw``). Headless
(Agg). Entry point: ``python tests/tools/patch_demo.py --save DIR``.

Every number the report quotes is written to ``DIR/numbers.json``, the
per-method summaries to ``DIR/*_summary*.csv``; the per-replicate values
only with ``--rows DIR2`` (hundreds of kB).
"""
import csv
import json
import math
import os

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from lss_core import patching

from . import burnmode as bm
from . import draw, refl

FIG1 = dict(config=refl.Config(truth='film', plan='nx', thickness=100.0), seed=1, join=3,
            methods=('legacy', 'reader', 'interp_log', 'fixed_o4_e4', 'joint', 'joint_prior'))
SURVEYS = {'film100_nx': refl.Config(truth='film', plan='nx', thickness=100.0),
           'film100_nx_staggered': refl.Config(truth='film', plan='nx_staggered', thickness=100.0),
           'water_nx': refl.Config(truth='water', plan='nx')}
SURVEY_TITLES = {'film100_nx': '100 Å film, NX-like grids', 'film100_nx_staggered': '100 Å film, staggered overlaps',
                 'water_nx': 'water, NX-like grids'}
# figure 3: realistic joins, and the critical edge as an aside (owner, 2026-11-22: no patching there)
WATER_J1 = dict(config=refl.Config(truth='water', plan='standard'), join=1,
                methods=('legacy', 'joint', 'joint_e4', 'fixed_o4_e4'))
FILM_STAG = dict(config=refl.Config(truth='film', plan='nx_staggered', thickness=100.0), join=3,
                 methods=('legacy', 'joint', 'joint_e4', 'fixed_o2_e4', 'fixed_o4_e4'))
EDGE = dict(config=refl.Config(truth='water', plan='edge'), join=1,
            methods=('legacy', 'interp_log', 'joint', 'joint_raw'))
BANDS = dict(config=refl.Config(truth='dppc', plan='nx'), seed=1, method='joint')
BURN = dict(config=bm.Config(change='broaden'), seed=1, frame=20)
BURN_CHANGES = ('none', 'fade', 'broaden', 'shift', 'shoulder', 'background')


def _save(fig, path):
    FigureCanvasAgg(fig)
    fig.savefig(path, dpi=110)


def _pct(x):
    return None if x is None or not np.isfinite(x) else round(100 * float(x), 3)


def _r(x, n=4):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def views(out, seed=0):
    """The window's two default views as PNG."""
    os.makedirs(out, exist_ok=True)
    rep = refl.replicate(refl.Config(), seed)
    fig = Figure(figsize=(12, 8))
    draw.refl_figure(fig, rep, refl.run_all(rep), draw.REFL_DEFAULT, list(refl.DEFAULT_METHODS), 'rrf', 1,
                     refl.run_all(refl.denoised(rep)))
    _save(fig, os.path.join(out, 'view_refl.png'))
    brep = bm.replicate(bm.Config(), seed)
    fig = Figure(figsize=(12, 8))
    draw.burn_figure(fig, brep, bm.run_all(brep), draw.BURN_DEFAULT)
    _save(fig, os.path.join(out, 'view_burn.png'))


# ---- figure 1: the film, every method ----------------------------------------------------

def figure1(out, numbers):
    rep = refl.replicate(FIG1['config'], FIG1['seed'])
    res = refl.run_all(rep)
    clean = refl.run_all(refl.denoised(rep))
    fig = Figure(figsize=(12.5, 8.5))
    draw.refl_figure(fig, rep, res, draw.REFL_DEFAULT, list(FIG1['methods']), 'rrf', FIG1['join'], clean,
                     title='100 Å film on water (Kiessig fringes), NX-like scans, one replicate (seed %d): '
                           'stitched curves, factors vs truth, pulls, join 3' % FIG1['seed'])
    _save(fig, os.path.join(out, '01_film_methods.png'))
    d = {}
    for n in FIG1['methods']:
        r, c = res[n], clean[n]
        chi = refl.chi2_vs_truth(rep, r) if r.stitched is not None else (math.nan, math.nan)
        d[n] = dict(dev_pct=[_pct(f / t - 1) for f, t in zip(r.factors, rep.true_steps)],
                    err_pct=[_pct(e) for e in r.step_err],
                    noise_free_dev_pct=[_pct(f / t - 1) for f, t in zip(c.factors, rep.true_steps)],
                    chi2_diag=_r(chi[0], 3), chi2_full=_r(chi[1], 3), notes=r.notes)
    numbers['figure1'] = dict(config=repr(FIG1['config']), seed=FIG1['seed'], true_steps=list(map(float, rep.true_steps)),
                              absorbers=[s.absorber for s in rep.scans],
                              monitor_ratios=[_r(m) for m in rep.monitor_ratios], methods=d)


# ---- figure 2: factors over many replicates ----------------------------------------------

def figure2(out, numbers, replicates, rows_out=None):
    fig = Figure(figsize=(15, 9))
    names = list(refl.METHODS)
    ncol = len(SURVEYS)
    allres = {}
    for col, (key, cfg) in enumerate(SURVEYS.items()):
        summ, rows = refl.survey(cfg, range(replicates), names)
        allres[key] = summ
        with open(os.path.join(out, 'factor_summary_%s.csv' % key), 'w', newline='') as fh:
            cols = ['n', 'bias', 'sd', 'rmse', 'pull_mean', 'pull_sd', 'coverage68', 'coverage95']
            w = csv.writer(fh)
            w.writerow(['method', 'join'] + [c + ('_ln' if c in ('bias', 'sd', 'rmse') else '') for c in cols])
            for n, d in summ.items():
                for j, v in d['joins'].items():
                    w.writerow([n, j] + ['%.6g' % v[c] for c in cols])
        if rows_out:
            with open(os.path.join(rows_out, 'factors_%s.csv' % key), 'w', newline='') as fh:
                w = csv.DictWriter(fh, ['seed', 'method', 'join', 'delta', 'err', 'true'])
                w.writeheader()
                w.writerows(rows)
        axb = fig.add_subplot(2, ncol, 1 + col)
        axp = fig.add_subplot(2, ncol, 1 + ncol + col, sharey=axb)
        y = np.arange(len(names))[::-1]
        joins = sorted(next(iter(summ.values()))['joins'])
        for k, j in enumerate(joins):
            off = (k - (len(joins) - 1) / 2) * 0.22
            b = [summ[n]['joins'][j]['bias'] for n in names]
            s = [summ[n]['joins'][j]['sd'] for n in names]
            p = [summ[n]['joins'][j]['pull_sd'] for n in names]
            axb.errorbar(100 * np.array(b), y + off, xerr=100 * np.array(s), fmt='o', ms=3, lw=0.8, capsize=1.5,
                         color='C%d' % k, label='join %d' % j)
            axp.plot(p, y + off, 'o', ms=3.5, color='C%d' % k)
        axb.axvline(0, color='k', lw=0.6)
        axp.axvline(1, color='k', lw=0.6)
        axb.set_yticks(y)
        axb.set_yticklabels([refl.METHODS[n]['label'] if col == 0 else '' for n in names], fontsize=6.5)
        axp.set_yticks(y)
        axp.set_yticklabels([refl.METHODS[n]['label'] if col == 0 else '' for n in names], fontsize=6.5)
        axb.set_xlabel('bias of f̂ ± SD over replicates [%]', fontsize=8)
        axp.set_xlabel('pull SD of (δ̂ − δ)/σ_reported (1 = honest)', fontsize=8)
        axp.set_xscale('log')
        axb.tick_params(labelsize=7)
        axp.tick_params(labelsize=7)
        axb.set_title('%s: %d replicates' % (SURVEY_TITLES[key], replicates), fontsize=8)
        axb.legend(fontsize=6, frameon=False, loc='lower right')
        lim = max(abs(v) for v in axb.get_xlim())
        axb.set_xlim(-min(lim, 8), min(lim, 8))
    fig.suptitle('Factor of each join over many noise replicates: bias, scatter and honesty of the reported error',
                 fontsize=9)
    fig.subplots_adjust(left=0.15, right=0.98, wspace=0.12, hspace=0.3)
    _save(fig, os.path.join(out, '02_factor_survey.png'))
    numbers['figure2'] = {key: {n: {str(j): dict(bias_pct=_pct(v['bias']), sd_pct=_pct(v['sd']),
                                                 pull_sd=_r(v['pull_sd'], 3), coverage68=_r(v['coverage68'], 3))
                                    for j, v in d['joins'].items()} | dict(failed=d['failed'])
                                for n, d in summ.items()}
                          for key, summ in allres.items()}
    numbers['figure2']['replicates'] = replicates
    return allres


# ---- figure 3: join close-ups ---------------------------------------------------------------

def _close_up(ax, case, view, title):
    rep = refl.denoised(refl.replicate(case['config'], 0))
    res = {n: refl.run_method(rep, n) for n in case['methods']}
    draw._join(ax, rep, res, list(case['methods']), {'join', 'truth'}, view, case['join'])
    m = case['join']
    ax.set_title('%s\njoin %d, overlap %.4g–%.4g Å⁻¹ (no noise)' % (title, m, rep.scans[m].q.min(),
                                                                    rep.scans[m - 1].q.max()), fontsize=7.5)
    dev = {n: res[n].factors[m - 1] / rep.true_steps[m - 1] - 1 for n in case['methods']}
    win = {n: (res[n].joins[m - 1].order, res[n].joins[m - 1].n_ext) for n in case['methods'] if res[n].joins}
    return rep, dev, win, {n: [x for x in res[n].notes if x.startswith('join %d' % m)] for n in case['methods']}


def figure3(out, numbers, replicates):
    fig = Figure(figsize=(13, 9.5))
    gs = fig.add_gridspec(2, 2, wspace=0.28, hspace=0.38)
    ax1, ax2, ax3, ax4 = (fig.add_subplot(gs[i // 2, i % 2]) for i in range(4))
    cases = [('water_j1', WATER_J1, ax1, 'rrf', 'Water, first join, coinciding points (standard plan)'),
             ('film_staggered_j3', FILM_STAG, ax2, 'rrf', '100 Å film, staggered overlap on the fringes'),
             ('edge_aside', EDGE, ax3, 'r', 'Aside: a staggered overlap across Qc (not done in practice)')]
    out_n, labels, nf, mean, sd = {}, [], [], [], []
    for key, case, ax, view, title in cases:
        rep, dev, win, notes = _close_up(ax, case, view, title)
        if key == 'edge_aside':
            ax.axvline(patching.QC, color='0.6', lw=0.8, ls=':')
            ax.set_xlim(0.0185, 0.031)
            ax.set_ylim(0.0, 4.2)
        summ, _ = refl.survey(case['config'], range(replicates), list(case['methods']))
        m = case['join']
        out_n[key] = dict(config=repr(case['config']), join=m, noise_free_dev_pct={n: _pct(v) for n, v in dev.items()},
                          final_window=win, notes=notes, replicates=replicates,
                          noisy_bias_pct={n: _pct(summ[n]['joins'][m]['bias']) for n in case['methods']},
                          noisy_sd_pct={n: _pct(summ[n]['joins'][m]['sd']) for n in case['methods']},
                          pull_sd={n: _r(summ[n]['joins'][m]['pull_sd'], 3) for n in case['methods']})
        for n in case['methods']:
            labels.append('%s: %s' % ({'water_j1': 'water j1', 'film_staggered_j3': 'film j3',
                                       'edge_aside': 'edge (aside)'}[key], n))
            nf.append(100 * dev[n])
            mean.append(100 * summ[n]['joins'][m]['bias'])
            sd.append(100 * summ[n]['joins'][m]['sd'])
    y = np.arange(len(labels))[::-1]
    ax4.barh(y, nf, color='0.75', label='no noise')
    ax4.errorbar(mean, y, xerr=sd, fmt='o', ms=3.5, color='k', lw=0.8, capsize=2,
                 label='mean ± SD, %d replicates' % replicates)
    ax4.axvline(0, color='k', lw=0.6)
    ax4.set_yticks(y)
    ax4.set_yticklabels(labels, fontsize=6.5)
    ax4.set_xlabel('f̂ / f$_{true}$ − 1 [%] (edge bars clipped at ±6 %)', fontsize=8)
    ax4.set_xlim(-6, 6)
    ax4.tick_params(labelsize=7)
    ax4.legend(fontsize=6, frameon=False, loc='lower left')
    fig.subplots_adjust(left=0.06, right=0.98, bottom=0.06, top=0.92)
    fig.suptitle('Join close-ups: the legacy spline against the joint fit\'s one curve through both scans '
                 '(default: 2 points either side, guard ladder; fixed = one fit, no guard)', fontsize=9)
    _save(fig, os.path.join(out, '03_join_closeups.png'))
    numbers['figure3'] = out_n


# ---- figure 4: error bands, diagonal vs full covariance -------------------------------------

def _level_check(rep, r):
    """Offset of the last scan's stitched level from the truth (weighted mean
    of ln y − ln truth over its points) and its predicted SD with σ_total as
    independent (diagonal) and with the full covariance."""
    st = r.stitched
    t = rep.truth(st.q) / rep.scale0
    last = st.W[:, -1] > 0.5
    ok = last & (st.y > 0)
    res = np.log(st.y[ok]) - np.log(t[ok])
    rel = r.sigma_total[ok] / st.y[ok]
    w = 1 / rel ** 2
    off = float(np.sum(w * res) / np.sum(w))
    C = st.covariance('log')[np.ix_(ok, ok)]
    pred_diag = float(np.sum(w) ** -0.5)
    pred_full = float(math.sqrt(w @ C @ w) / np.sum(w))
    return off, pred_diag, pred_full


def figure4(out, numbers, replicates):
    cfg, name = BANDS['config'], BANDS['method']
    rep = refl.replicate(cfg, BANDS['seed'])
    r = refl.run_method(rep, name)
    st = r.stitched
    fig = Figure(figsize=(13, 4.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.5, 0.9, 1.0], wspace=0.32)
    ax, axc, axh = (fig.add_subplot(gs[0, i]) for i in range(3))
    q = st.q
    rf = patching.fresnel(q)
    y = st.y * rep.scale0
    ax.fill_between(q, (y - r.sigma_total * rep.scale0) / rf, (y + r.sigma_total * rep.scale0) / rf,
                    color='C0', alpha=0.25, lw=0, label='± σ_total (factors folded in)')
    ax.fill_between(q, (y - st.sigma_meas * rep.scale0) / rf, (y + st.sigma_meas * rep.scale0) / rf,
                    color='C0', alpha=0.6, lw=0, label='± σ_meas (counting only)')
    qq = np.linspace(q.min(), q.max(), 600)
    ax.plot(qq, rep.truth(qq) / patching.fresnel(qq), 'k:', lw=1.1, label='truth')
    C = st.covariance('log')
    L = np.linalg.cholesky(C)
    rng = np.random.default_rng(7)
    tq = rep.truth(q)
    for i in range(4):
        ax.plot(q, tq * np.exp(L @ rng.standard_normal(len(q))) / rf, '-', lw=0.6, color='C3', alpha=0.7,
                label='draws from the full covariance' if i == 0 else None)
    ax.plot(q, y / rf, 'o', ms=2, color='C0', label='stitched (%s)' % name)
    ax.set_yscale('log')
    ax.set_xlabel(r'$Q_z$ [$\AA^{-1}$]', fontsize=8)
    ax.set_ylabel('R / R$_F$', fontsize=8)
    ax.legend(fontsize=6, frameon=False, loc='lower left')
    ax.tick_params(labelsize=7)
    ax.set_title('DPPC on water, NX-like scans, seed %d' % BANDS['seed'], fontsize=8)
    sd = np.sqrt(np.diag(C))
    im = axc.imshow(C / np.outer(sd, sd), cmap='RdBu_r', vmin=-1, vmax=1, origin='lower')
    axc.set_title('correlation of ln y (stitched points, by Qz)', fontsize=8)
    axc.tick_params(labelsize=6)
    fig.colorbar(im, ax=axc, fraction=0.046, pad=0.04).ax.tick_params(labelsize=6)
    diag, full, offs, pd, pf, legacy = [], [], [], [], [], []
    for s in range(replicates):
        rp = refl.replicate(cfg, s)
        rr = refl.run_method(rp, name)
        a, b = refl.chi2_vs_truth(rp, rr)
        diag.append(a)
        full.append(b)
        o, x1, x2 = _level_check(rp, rr)
        offs.append(o)
        pd.append(x1)
        pf.append(x2)
        lg = refl.run_method(rp, 'legacy')
        lq, ly, ls = lg.curve
        lt = rp.truth(lq) / rp.scale0
        legacy.append(float(np.mean(((ly - lt) / ls) ** 2)))
    bins = np.linspace(0, max(4.0, np.nanpercentile(diag, 98)), 40)
    axh.hist(diag, bins, histtype='step', color='C1', lw=1.2, label='diagonal σ_total: mean %.2f, SD %.2f'
             % (np.mean(diag), np.std(diag, ddof=1)))
    axh.hist(full, bins, histtype='step', color='C0', lw=1.2, label='full covariance: mean %.2f, SD %.2f'
             % (np.mean(full), np.std(full, ddof=1)))
    axh.hist(legacy, bins, histtype='step', color='C3', lw=1.0, ls='--',
             label='legacy curve, its error column: mean %.2f' % np.mean(legacy))
    n_pts = len(q)
    axh.axvline(1, color='k', lw=0.6)
    axh.set_xlabel('χ²/N of the stitched curve against the truth', fontsize=8)
    axh.set_ylabel('replicates', fontsize=8)
    axh.legend(fontsize=6, frameon=False, loc='upper right')
    axh.tick_params(labelsize=7)
    axh.set_title('%d replicates, N = %d points (χ² SD expected √(2/N) = %.2f)'
                  % (replicates, n_pts, math.sqrt(2 / n_pts)), fontsize=7.5)
    fig.subplots_adjust(left=0.05, right=0.98, bottom=0.13, top=0.86)
    fig.suptitle('Error bands of the stitched curve: the same diagonal, but the full covariance moves whole scans '
                 'together', fontsize=9)
    _save(fig, os.path.join(out, '04_error_bands.png'))
    numbers['figure4'] = dict(config=repr(cfg), method=name, replicates=replicates, n_points=n_pts,
                              chi2_diag_mean=_r(np.mean(diag), 3), chi2_diag_sd=_r(np.std(diag, ddof=1), 3),
                              chi2_full_mean=_r(np.mean(full), 3), chi2_full_sd=_r(np.std(full, ddof=1), 3),
                              chi2_sd_expected=_r(math.sqrt(2 / n_pts), 3),
                              legacy_chi2_mean=_r(np.mean(legacy), 3), legacy_chi2_sd=_r(np.std(legacy, ddof=1), 3),
                              last_level_observed_sd_pct=_pct(np.std(offs, ddof=1)),
                              last_level_mean_pct=_pct(np.mean(offs)),
                              last_level_predicted_diag_pct=_pct(np.mean(pd)),
                              last_level_predicted_full_pct=_pct(np.mean(pf)),
                              sqrt_sigma_last_pct=_pct(math.sqrt(st.Sigma[-1, -1])))


# ---- figures 5 and 6: burn line cuts -----------------------------------------------------

def figure5(out, numbers):
    rep = bm.replicate(BURN['config'], BURN['seed'])
    res = bm.run_all(rep)
    fig = Figure(figsize=(12.5, 8))
    draw.burn_figure(fig, rep, res, draw.BURN_DEFAULT | {'frame0'}, None, BURN['frame'],
                     title='Burn line cuts, P44 case: the peak broadens by 30 %% at constant area on a broad '
                           'shoulder (seed %d, last frame)' % BURN['seed'])
    _save(fig, os.path.join(out, '05_burn_linecuts.png'))
    d = {}
    for n, r in res.items():
        d[n] = dict(change={q: _r(bm.measured_change(r, q, rep.duration()), 5) for q in bm.QUANTITIES},
                    best={q: c.best for q, c in r.trends.items()},
                    stable={q: bool(c.stable) if c.stable is not None else None for q, c in r.trends.items()},
                    median_chi2_dof=_r(np.median([x.get('chi2_dof', math.nan) for x in r.details
                                                  if x.get('chi2_dof') is not None]), 2)
                    if n != 'moments' else None)
    numbers['figure5'] = dict(config=repr(BURN['config']), seed=BURN['seed'],
                              true_change={q: _r(bm.true_change(rep, q), 5) for q in bm.QUANTITIES}, estimators=d)


def figure6(out, numbers, replicates, rows_out=None):
    fig = Figure(figsize=(12.5, 4.6))
    axes = [fig.add_subplot(1, 3, i + 1) for i in range(3)]
    summary = {}
    rows_all = []
    for ci, ch in enumerate(BURN_CHANGES):
        summ, rows = bm.survey(bm.Config(change=ch), range(replicates))
        summary[ch] = summ
        rows_all += [dict(r, change=ch) for r in rows]
        for ax, q in zip(axes, bm.QUANTITIES):
            tv = summ['template'][q]['true']
            scale = 1.0 if q == 'centre' else 100.0
            ax.plot([ci - 0.35, ci + 0.35], [scale * tv] * 2, 'k-', lw=1.6, label='truth' if ci == 0 else None)
            for k, e in enumerate(bm.ESTIMATORS):
                s = summ[e][q]
                ax.errorbar(ci + (k - 1) * 0.22, scale * s['mean'], scale * s['sd'], fmt='o', ms=3.5,
                            color=bm.COLOURS[e], lw=0.9, capsize=1.5, label=e if ci == 0 else None)
    for ax, q in zip(axes, bm.QUANTITIES):
        ax.set_xticks(range(len(BURN_CHANGES)))
        ax.set_xticklabels(BURN_CHANGES, fontsize=7, rotation=20)
        ax.set_ylabel({'intensity': 'intensity change over the test [%]', 'centre': r'position shift [$\AA^{-1}$]',
                       'fwhm': 'FWHM change over the test [%]'}[q], fontsize=8)
        ax.axhline(0, color='0.6', lw=0.5)
        ax.tick_params(labelsize=7)
    axes[0].legend(fontsize=6.5, frameon=False, loc='lower left')
    fig.suptitle('What each burn estimator reads (linear trend over the 210 s test), mean ± SD over %d replicates '
                 'per change' % replicates, fontsize=9)
    fig.subplots_adjust(left=0.06, right=0.99, bottom=0.17, top=0.88, wspace=0.35)
    _save(fig, os.path.join(out, '06_burn_estimators.png'))
    with open(os.path.join(out, 'burn_estimator_summary.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['change', 'estimator', 'quantity', 'n', 'true', 'mean', 'sd', 'bias', 'stable_fraction'])
        for ch, summ in summary.items():
            for e, d in summ.items():
                for q, v in d.items():
                    w.writerow([ch, e, q, v['n']] + ['%.6g' % v[c] for c in ('true', 'mean', 'sd', 'bias', 'stable')])
    if rows_out:
        with open(os.path.join(rows_out, 'burn_estimators.csv'), 'w', newline='') as fh:
            w = csv.DictWriter(fh, ['change', 'seed', 'estimator', 'quantity', 'true', 'measured', 'stable'])
            w.writeheader()
            w.writerows(rows_all)
    numbers['figure6'] = dict(replicates=replicates, changes={
        ch: {e: {q: dict(true=_r(v['true'], 5), mean=_r(v['mean'], 5), sd=_r(v['sd'], 5),
                         stable=_r(v['stable'], 3)) for q, v in d.items()} for e, d in summ.items()}
        for ch, summ in summary.items()})


def report(out, replicates=200, burn_replicates=30, log=None, rows_out=None):
    """Every figure of the report, numbers.json and the summary CSVs into
    ``out``; the per-replicate CSVs into ``rows_out`` (if given: large)."""
    os.makedirs(out, exist_ok=True)
    if rows_out:
        os.makedirs(rows_out, exist_ok=True)
    log = log or (lambda *a: None)
    numbers = {}
    figure1(out, numbers)
    log('figure 1 done')
    figure2(out, numbers, replicates, rows_out)
    log('figure 2 done')
    figure3(out, numbers, max(replicates // 2, 3))
    log('figure 3 done')
    figure4(out, numbers, replicates)
    log('figure 4 done')
    figure5(out, numbers)
    log('figure 5 done')
    figure6(out, numbers, burn_replicates, rows_out)
    log('figure 6 done')
    with open(os.path.join(out, 'numbers.json'), 'w') as fh:
        json.dump(numbers, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    return numbers
