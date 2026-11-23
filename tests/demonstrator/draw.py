"""Drawings of the demonstrator into a matplotlib ``Figure`` (Agg or Qt).

``refl_figure(fig, rep, results, show, ...)`` and ``burn_figure(fig, rep,
results, show, ...)`` clear the figure and draw the panels; ``show`` is a
set of item keys (``REFL_ITEMS``, ``BURN_ITEMS``) choosing what is plotted.
No pyplot: the window and the figure writer pass their own figures.
"""

import numpy as np

from lss_core import patching

from . import burnmode as bm
from . import refl

REFL_ITEMS = (
    ('raw', 'scans as measured', 'Each scan per Monc count, before any factor: the absorber jumps.'),
    ('scans', 'scans × true factors', 'The noisy scans multiplied by their true scale: the noise alone.'),
    ('denoised', 'denoised scans', 'The same scans at the expected counts (no noise), × true scale.'),
    ('truth', 'truth R(Qz)', 'The curve the scans were drawn from (Parratt, Névot–Croce).'),
    ('stitched', 'stitched curves', "Each selected method's stitched points on the anchor's scale × the anchor's true scale."),
    ('bands', 'σ_total bands', 'Per point √(σ_meas² + y² diag(W Σ Wᵀ)): the factors\' uncertainty folded in.'),
    ('meas_bands', 'σ counting bands', 'Per point counting error only (σ_meas).'),
    ('draws', 'draws from Σ', 'Three draws of the stitched curve from its full covariance (first selected method): whole scans move together.'),
    ('pulls', 'residual pulls', '(stitched − truth) / σ_total per point; ±1 and ±2 marked.'),
    ('factors', 'factors vs truth', 'f̂ / f_true − 1 of each join with its reported error.'),
    ('denoised_fits', 'factors, denoised data', 'Hollow markers: the same method on the noise-free scans: its bias alone.'),
    ('prior', 'foil prior', 'Grey square: the calibrated-foil ratio of the join and its error (the prior).'),
    ('join', 'join close-up', 'Scan a, scan b with the true factor, and each method\'s curve through the join.'),
)
REFL_DEFAULT = {'scans', 'truth', 'stitched', 'bands', 'pulls', 'factors', 'denoised_fits', 'prior', 'join'}
BURN_ITEMS = (
    ('data', 'noisy line cut', 'The frame\'s horizontal profile with its counting errors.'),
    ('truth', 'denoised line cut', 'The same frame without noise.'),
    ('parts', 'truth parts', 'Peak, shoulder and floor of the true line cut.'),
    ('frame0', 'first frame (truth)', 'The true line cut of frame 0, to see the change.'),
    ('fits', 'estimator curves', "Each selected estimator's curve on this frame (moments: baseline + Gaussian of the same area, centroid and width)."),
    ('window', 'fit window', 'The Qxy window measure_gid chose (3 FWHM either side of the peak of the mean frame).'),
    ('residuals', 'residuals', '(data − curve) / σ in the window per estimator.'),
    ('trends', 'trends', 'Per-frame values relative to t = 0 (position: shift) with the best trend model.'),
    ('all_models', 'all trend models', 'Every trend model fitted (thin), not only the best.'),
    ('true_trend', 'true trend', 'The truth of each quantity over time.'),
)
BURN_DEFAULT = {'data', 'truth', 'parts', 'fits', 'window', 'residuals', 'trends', 'true_trend'}


def _yview(q, y, view):
    return y / patching.fresnel(q) if view == 'rrf' else y


def refl_figure(fig, rep, results, show=REFL_DEFAULT, methods=None, view='rrf', join=1, clean_results=None,
                title=None):
    """The reflectivity mode: curve (top left), factors (top right), pulls
    (bottom left), join close-up (bottom right). ``results``: {name:
    MethodResult} (``refl.run_all``); ``methods``: the names drawn (default
    all in ``results``); ``clean_results``: the same on ``refl.denoised(rep)``
    for the hollow markers; ``view``: 'rrf' (R/R_F) or 'r'. Returns the axes."""
    fig.clf()
    methods = [m for m in (methods or list(results)) if m in results]
    gs = fig.add_gridspec(2, 2, width_ratios=[1.55, 1.0], height_ratios=[1.6, 1.0], hspace=0.28, wspace=0.22)
    ax = fig.add_subplot(gs[0, 0])
    axf = fig.add_subplot(gs[0, 1])
    axr = fig.add_subplot(gs[1, 0], sharex=ax)
    axj = fig.add_subplot(gs[1, 1])
    qq = np.linspace(min(s.q.min() for s in rep.scans), max(s.q.max() for s in rep.scans), 800)
    tr = rep.truth(qq)
    scan_cols = ['0.35', '0.55', '0.25', '0.65', '0.45']
    for m, (s, e) in enumerate(zip(rep.scans, rep.expected)):
        sc = rep.scale(m)
        c = scan_cols[m % len(scan_cols)]
        if 'raw' in show:
            ax.plot(s.q, _yview(s.q, s.y, view), 'x', color=c, ms=3, lw=0, label='as measured' if m == 0 else None)
        if 'scans' in show:
            ax.errorbar(s.q, _yview(s.q, s.y * sc, view), _yview(s.q, s.sigma * sc, view), fmt='o', ms=2.5,
                        color=c, mfc='none', lw=0.6, label='scans × true factors' if m == 0 else None)
        if 'denoised' in show:
            ax.plot(e.q, _yview(e.q, e.y * sc, view), '-', color=c, lw=1.0, alpha=0.8,
                    label='denoised scans' if m == 0 else None)
    if 'truth' in show:
        ax.plot(qq, _yview(qq, tr, view), 'k:', lw=1.2, label='truth')
    first_ok = None
    for name in methods:
        r = results[name]
        if not r.ok or r.curve is None:
            continue
        col = refl.COLOURS.get(name, 'C0')
        q, y, _ = r.curve
        y = y * rep.scale0
        st = r.sigma_total * rep.scale0
        if 'stitched' in show:
            ax.plot(q, _yview(q, y, view), '.-', color=col, ms=3, lw=0.8, label=r.label)
        if 'bands' in show:
            ax.fill_between(q, _yview(q, y - st, view), _yview(q, y + st, view), color=col, alpha=0.18, lw=0)
        if 'meas_bands' in show and r.stitched is not None:
            sm = r.stitched.sigma_meas * rep.scale0
            ax.fill_between(q, _yview(q, y - sm, view), _yview(q, y + sm, view), color=col, alpha=0.35, lw=0,
                            hatch='///')
        if r.stitched is not None and (first_ok is None or name == 'joint'):
            first_ok = name
        if 'pulls' in show:
            axr.plot(q, (y - rep.truth(q)) / st, '.', color=col, ms=4, label=r.label)
    if 'draws' in show and first_ok is not None:
        r = results[first_ok]
        st = r.stitched
        C = st.covariance('log')
        rng = np.random.default_rng(rep.seed)
        L = np.linalg.cholesky(C + 1e-30 * np.eye(len(C)))
        t = rep.truth(st.q)
        for i in range(3):
            d = t * np.exp(L @ rng.standard_normal(len(C)))
            ax.plot(st.q, _yview(st.q, d, view), '-', color=refl.COLOURS.get(first_ok), lw=0.6, alpha=0.6,
                    label='draws from Σ (%s)' % first_ok if i == 0 else None)
    ax.set_yscale('log')
    ax.set_ylabel('R / R$_F$' if view == 'rrf' else 'R', fontsize=8)
    ax.tick_params(labelsize=7, labelbottom=False)
    if ax.get_legend_handles_labels()[0]:
        ax.legend(fontsize=6, frameon=False, loc='best', ncol=2)
    axr.axhline(0, color='0.5', lw=0.6)
    for v in (-2, -1, 1, 2):
        axr.axhline(v, color='0.8', lw=0.5, ls='--')
    axr.set_xlabel(r'$Q_z$ [$\AA^{-1}$]', fontsize=8)
    axr.set_ylabel('(stitched − truth) / σ$_{total}$', fontsize=7)
    axr.tick_params(labelsize=7)
    if 'pulls' not in show:
        axr.text(0.5, 0.5, 'pulls hidden', transform=axr.transAxes, ha='center', color='0.6', fontsize=7)
    _factors(axf, rep, results, methods, show, clean_results)
    _join(axj, rep, results, methods, show, view, join)
    if title is None:
        title = '%s, %s, counts ×%g, seed %d' % (refl.TRUTH_LABELS.get(rep.config.truth, rep.config.truth)
                                                + (' %g Å' % rep.config.thickness if rep.config.truth == 'film' else ''),
                                                refl.PLAN_LABELS.get(rep.config.plan, rep.config.plan),
                                                rep.config.counts, rep.seed)
    fig.suptitle(title, fontsize=9)
    return dict(curve=ax, factors=axf, pulls=axr, join=axj)


def _factors(axf, rep, results, methods, show, clean_results):
    K = len(rep.true_steps)
    n = max(len(methods), 1)
    if 'factors' not in show:
        axf.text(0.5, 0.5, 'factors hidden', transform=axf.transAxes, ha='center', color='0.6', fontsize=7)
    else:
        for i, name in enumerate(methods):
            r = results[name]
            if not r.ok:
                continue
            x = np.arange(1, K + 1) + (i - (n - 1) / 2) * 0.6 / n
            dev = 100 * (r.factors / rep.true_steps - 1)
            col = refl.COLOURS.get(name, 'C0')
            axf.errorbar(x, dev, 100 * r.step_err, fmt='o', ms=3.5, color=col, lw=0.9, capsize=1.5, label=r.label)
            if 'denoised_fits' in show and clean_results and clean_results.get(name) is not None \
                    and clean_results[name].ok:
                cr = clean_results[name]
                axf.plot(x, 100 * (cr.factors / rep.true_steps - 1), 'o', ms=6, mfc='none', color=col, mew=0.9)
        if 'prior' in show and rep.prior is not None:
            mean, C = rep.prior
            ok = np.diag(C) > 0
            x = np.arange(1, K + 1)
            axf.errorbar(x[ok] - 0.42, 100 * (np.exp(mean[ok]) / rep.true_steps[ok] - 1), 100 * np.sqrt(np.diag(C)[ok]),
                         fmt='s', ms=3.5, color='0.55', lw=0.9, capsize=1.5, label='foil prior')
        axf.axhline(0, color='k', lw=0.6)
        axf.set_xticks(range(1, K + 1))
        axf.set_xticklabels(['join %d\nQ %.3g' % (m, rep.scans[m].q.min()) for m in range(1, K + 1)], fontsize=7)
        axf.set_ylabel('f̂ / f$_{true}$ − 1 [%]', fontsize=8)
        axf.tick_params(labelsize=7)
        if axf.get_legend_handles_labels()[0]:
            axf.legend(fontsize=5.5, frameon=False, loc='best')


def _join(axj, rep, results, methods, show, view, join):
    if 'join' not in show:
        axj.text(0.5, 0.5, 'join close-up hidden', transform=axj.transAxes, ha='center', color='0.6', fontsize=7)
        return
    m = int(min(max(join, 1), len(rep.scans) - 1))
    a, b = rep.scans[m - 1], rep.scans[m]
    f_true = rep.true_steps[m - 1]
    ia, ib = patching.window(a.q, b.q, 4)
    lo, hi = min(a.q[ia].min(), b.q[ib].min()), max(a.q[ia].max(), b.q[ib].max())
    pad = 0.04 * (hi - lo)
    sa = (a.q >= lo - pad) & (a.q <= hi + pad)
    sb = (b.q >= lo - pad) & (b.q <= hi + pad)
    axj.errorbar(a.q[sa], _yview(a.q[sa], a.y[sa], view), _yview(a.q[sa], a.sigma[sa], view), fmt='o', ms=3,
                 color='k', lw=0.7, label='scan a')
    axj.errorbar(b.q[sb], _yview(b.q[sb], b.y[sb] * f_true, view), _yview(b.q[sb], b.sigma[sb] * f_true, view),
                 fmt='s', ms=3, color='0.55', mfc='none', lw=0.7, label='scan b × f$_{true}$')
    qq = np.linspace(lo - pad, hi + pad, 300)
    if 'truth' in show:
        axj.plot(qq, _yview(qq, rep.truth(qq) / rep.scale(m - 1), view), 'k:', lw=1.0, label='truth')
    lines = []
    for name in methods:
        r = results[name]
        if not r.ok:
            continue
        col = refl.COLOURS.get(name, 'C0')
        f = r.factors[m - 1]
        cur = None
        if r.joins is not None and r.joins[m - 1].method == 'joint':
            cur = refl.join_curve(a, b, r.joins[m - 1])
            ls = '-'
        elif name in ('legacy', 'interp'):
            cur = refl.spline_curve(a, b, f)
            ls = '--'
        elif name == 'interp_log':
            cur = refl.spline_curve(a, b, f, log=True)
            ls = '-.'
        if cur is not None:
            axj.plot(cur[0], _yview(cur[0], cur[1], view), ls, color=col, lw=1.1, label=r.label)
        lines.append('%s %+.2f %%' % (name, 100 * (f / f_true - 1)))
    axj.axvspan(b.q.min(), a.q.max(), color='0.9', zorder=0)
    axj.set_xlim(lo - pad, hi + pad)
    axj.set_xlabel(r'$Q_z$ [$\AA^{-1}$]', fontsize=8)
    axj.set_ylabel(('R/R$_F$' if view == 'rrf' else 'R') + ', scan a scale', fontsize=7)
    axj.set_title('join %d: overlap %.4g–%.4g (shaded)' % (m, b.q.min(), a.q.max()), fontsize=7)
    axj.tick_params(labelsize=7)
    axj.text(0.02, 0.02, '\n'.join(lines[:8]), transform=axj.transAxes, fontsize=5.5, family='monospace',
             va='bottom')
    if axj.get_legend_handles_labels()[0]:
        axj.legend(fontsize=5.5, frameon=False, loc='upper right')


# ---- burn line cuts --------------------------------------------------------------------

def burn_figure(fig, rep, results, show=BURN_DEFAULT, estimators=None, frame=None, title=None):
    """The burn line-cut mode: frame ``frame``'s line cut with every
    estimator's curve (left, residuals below), the three trends (right)."""
    fig.clf()
    estimators = [e for e in (estimators or list(results)) if e in results]
    k = rep.config.n - 1 if frame is None else int(min(max(frame, 0), rep.config.n - 1))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.35, 1.0], height_ratios=[1, 1, 1], hspace=0.12, wspace=0.25)
    ax = fig.add_subplot(gs[0:2, 0])
    axr = fig.add_subplot(gs[2, 0], sharex=ax)
    axt = [fig.add_subplot(gs[i, 1]) for i in range(3)]
    x = rep.x
    p = rep.profiles[k]
    win = [results[e].window for e in estimators if results[e].ok]
    lo, hi = (win[0] if win else (x.min(), x.max()))
    span = hi - lo
    view = (x >= lo - 0.8 * span) & (x <= hi + 0.8 * span)
    if 'data' in show:
        ax.errorbar(x[view], p[view, 1], p[view, 2], fmt='o', ms=2.5, color='0.3', lw=0.6, label='frame %d' % k)
    parts = rep.parts(k)
    if 'truth' in show:
        ax.plot(x[view], rep.clean[k][view, 1], 'k-', lw=1.2, label='denoised')
    if 'parts' in show:
        ax.plot(x[view], parts['peak'][view] + parts['floor'][view], ':', color='k', lw=0.9, label='peak + floor')
        ax.plot(x[view], parts['shoulder'][view] + parts['floor'][view], '--', color='0.5', lw=0.9,
                label='shoulder + floor')
    if 'frame0' in show:
        ax.plot(x[view], rep.parts(0)['total'][view], '-', color='0.7', lw=1.0, label='frame 0 (truth)')
    if 'window' in show and win:
        ax.axvspan(lo, hi, color='0.93', zorder=0)
    for e in estimators:
        r = results[e]
        col = bm.COLOURS.get(e, 'C0')
        cur = bm.frame_curve(rep, r, k)
        if cur is None:
            continue
        if 'fits' in show:
            ax.plot(cur[0], cur[1], '-', color=col, lw=1.3, label=e)
        if 'residuals' in show:
            sel = (x >= r.window[0]) & (x <= r.window[1])
            yi = np.interp(x[sel], cur[0], cur[1])
            axr.plot(x[sel], (p[sel, 1] - yi) / p[sel, 2], '.-', color=col, ms=3, lw=0.6)
    ax.set_ylabel('I / monitor', fontsize=8)
    ax.tick_params(labelsize=7, labelbottom=False)
    if ax.get_legend_handles_labels()[0]:
        ax.legend(fontsize=6, frameon=False, loc='upper right')
    ax.set_title('line cut, frame %d of %d (t = %.0f s)' % (k, rep.config.n, rep.t[k]), fontsize=8)
    axr.axhline(0, color='0.5', lw=0.6)
    for v in (-2, 2):
        axr.axhline(v, color='0.8', lw=0.5, ls='--')
    axr.set_xlabel(r'$Q_{xy}$ [$\AA^{-1}$]', fontsize=8)
    axr.set_ylabel('(data − curve)/σ', fontsize=7)
    axr.tick_params(labelsize=7)
    tt = np.linspace(0, rep.duration(), 200)
    for ax_q, q in zip(axt, bm.QUANTITIES):
        ax_q.tick_params(labelsize=7)
        ax_q.axvline(rep.t[k], color='0.85', lw=0.8)
        if 'trends' not in show:
            continue
        v0 = rep.truth_at(q, 0.0)
        span = []
        if 'true_trend' in show:
            tv = rep.truth_at(q, tt)
            tv = tv - v0 if q == 'centre' else tv / v0
            ax_q.plot(tt, tv, 'k--', lw=1.1, label='truth')
            span += [tv.min(), tv.max()]
        for e in estimators:
            r = results[e]
            if not r.ok or q not in (r.trends or {}):
                continue
            col = bm.COLOURS.get(e, 'C0')
            y, s, ref, lab = r.relative(q)
            ax_q.errorbar(rep.t, y, s, fmt='o', ms=2.5, color=col, lw=0.6, label=e)
            ok = np.isfinite(y)
            if ok.any():
                span += [np.min(y[ok]), np.max(y[ok])]
            c = r.trends[q]
            for mname, fit in c.fits.items():
                if not fit.ok:
                    continue
                best = mname == c.best
                if not best and 'all_models' not in show:
                    continue
                fv = fit(tt)
                ax_q.plot(tt, fv - ref if q == 'centre' else fv / ref, '-', color=col, lw=1.6 if best else 0.6,
                          alpha=1.0 if best else 0.5)
        if span:                       # the data and the truth set the range, not a wild model near t = 0
            lo_, hi_ = min(span), max(span)
            pad = 0.12 * (hi_ - lo_) or (1e-4 if q == 'centre' else 0.01)
            ax_q.set_ylim(lo_ - pad, hi_ + pad)
        ax_q.set_ylabel({'intensity': 'intensity / I(0)', 'centre': r'shift [$\AA^{-1}$]',
                         'fwhm': 'FWHM / FWHM(0)'}[q], fontsize=7)
        if q != 'fwhm':
            ax_q.tick_params(labelbottom=False)
    if axt[0].get_legend_handles_labels()[0]:
        axt[0].legend(fontsize=6, frameon=False, loc='best')
    axt[-1].set_xlabel('time [s]', fontsize=8)
    if title is None:
        c = rep.config
        title = 'Burn line cuts: %s (amount %g), monitor %.0e, seed %d' % (
            bm.CHANGE_LABELS.get(c.change, c.change), c.amount_used, c.monitor, rep.seed)
    fig.suptitle(title, fontsize=9)
    return dict(cut=ax, residuals=axr, trends=axt)
