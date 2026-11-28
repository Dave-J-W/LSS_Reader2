"""The GID burn estimators on a peak with a shoulder (P44), from the raw
frames to the judgment, step by step, for the walkthrough
(docs/studies/burn_shoulder/walkthrough.md; the owner's standing order of
2026-11-25: "the entire chain of data processing, ending with the
statistics and judgment ... data fit examples, explanations of
statistics, all ELI5").

Public data only: the NX school GID burn 15 (and 14 for the verdicts),
and synthetic burns with a known truth (calibration).

Figures (``--out``):
- BW1 the raw data: frame 0 of burn 15 with the rows summed, and the line
  cut of the first and last frame with the window;
- BW2 separated: the mean frame in the window, less its chord; the
  Gaussian and line fitted beside the peak; the shoulder and the peak;
- BW3 one frame fitted: the last frame of burn 15 under stretched and
  under separated, each over its data, with the residuals in error bars;
- BW4 one number per frame: burn 15's intensity and FWHM per frame under
  both, with the constant and the line through them, and separated's
  shoulder amplitude per frame;
- BW5 the verdict: how much better a sloped line describes each
  estimator's intensities than a flat one (ΔAICc), burns 14 and 15;
- BW6 calibration: 60 synthetic NX 15-like burns (FWHM +20 %, intensity
  −13 %), each estimator's 95 % interval of the intensity change against
  the truth.

    python tests/tools/burn_shoulder_walkthrough.py --out docs/studies/burn_shoulder/walkthrough
"""
import argparse
import json
import math
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))
os.chdir(ROOT)

import numpy as np                                    # noqa: E402

from lss_core import burn, trends                      # noqa: E402

NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
CT, CS = '#1f6fb4', '#c0392b'           # stretched, separated
SCAN = 15


def plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as p
    return p


def nx_burns():
    import tempfile
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp())
    from lss_core.experiment import Experiment
    e = Experiment(NX)
    return e, {(s, est): e.burn(s, estimator=est) for s in (14, 15) for est in ('stretched', 'separated')}


def bw1(out, e, r):
    """The raw data: frame 0 of burn 15, the summed rows, the line cuts."""
    from lss_core import images
    p = plt()
    fr = [f for f in e.frames([SCAN]) if f.index == 0][0]
    img = np.asarray(images.read_pilatus(fr.path), float)
    fig, (a, b) = p.subplots(2, 1, figsize=(8, 10))
    a.imshow(np.log10(np.maximum(img, 0.5)), origin='lower', aspect='auto', cmap='viridis')
    lo, hi = r.rows
    for y in (lo, hi):
        a.axhline(y, color='w', lw=1)
    a.set_title('(a) Burn %d, frame 0: counts per pixel (log scale)\nrows %d–%d between the white lines are summed'
                % (SCAN, lo, hi), fontsize=9)
    a.set_xlabel('detector column')
    a.set_ylabel('detector row')
    p0, p1 = r.profiles[0], r.profiles[-1]
    b.errorbar(p0[:, 0], p0[:, 1], p0[:, 2], fmt='.', ms=3, color='0.4', label='frame 0 (first)')
    b.errorbar(p1[:, 0], p1[:, 1], p1[:, 2], fmt='.', ms=3, color=CS, label='frame %d (last)' % (len(r.profiles) - 1))
    w0, w1 = r.window
    b.axvspan(w0, w1, color='orange', alpha=0.15, label='window: 3 FWHM either side of the peak')
    b.set_yscale('log')
    b.set_xlabel('Qxy (Å⁻¹)')
    b.set_ylabel('counts per monitor (summed rows)')
    b.set_title('(b) The line cut: each column summed over the rows, ± √counts', fontsize=9)
    b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW1_raw_frame_and_cut.png'), dpi=130)
    p.close(fig)
    sel = (p0[:, 0] >= w0) & (p0[:, 0] <= w1)
    k = int(np.argmax(np.where(sel, p0[:, 1], -np.inf)))
    peak_counts = float((p0[k, 1] / p0[k, 2]) ** 2)          # counts = (value / σ)² for counting noise
    return dict(rows=[int(lo), int(hi)], window=[float(w0), float(w1)], frames=len(r.profiles),
                points_in_window=int(np.sum(sel)), peak_counts_frame0=peak_counts)


def bw2(out, r):
    """The separated of the mean frame: chord, shape, the shoulder fit beside the peak, S and P."""
    p = plt()
    ref = r.reference
    x = ref['x']
    mean = np.mean([q[:, 1] for q in r.profiles], axis=0)
    sel = (r.profiles[0][:, 0] >= r.window[0]) & (r.profiles[0][:, 0] <= r.window[1])
    mw = mean[sel]
    chord = mw - ref['shape']
    h, m, sg = ref['shoulder']
    c0, w0 = (ref['found']['centre'], ref['found']['fwhm']) if ref['found'] else (ref['centre'], ref['fwhm'])
    beside = np.abs(x - c0) > burn.SEPARATE_CORE * w0
    S = h * np.exp(-0.5 * ((x - m) / sg) ** 2)
    line = ref['shape'] - S - ref['peak']
    fig, (a, b, c) = p.subplots(3, 1, figsize=(8, 12.5), sharex=True)
    a.plot(x, mw, 'k.', ms=4, label='mean of the %d frames' % len(r.profiles))
    a.plot(x, chord, '--', color='0.5', label='chord: the straight line through\nthe first and last 3 points')
    a.set_title('(a) The mean frame in the window, and its chord', fontsize=9)
    b.plot(x[~beside], ref['shape'][~beside], '.', color='0.7', ms=4, label='shape = mean − chord (the core)')
    b.plot(x[beside], ref['shape'][beside], 'o', color='C2', ms=3.5,
           label='beside the peak (> %.1f FWHM away):\nfitted by a Gaussian + a line' % burn.SEPARATE_CORE)
    b.plot(x, S + line, '-', color='C2', lw=1.2, label='the fitted Gaussian + line')
    b.set_title('(b) The shoulder is fitted where the peak is not', fontsize=9)
    c.plot(x, ref['shape'], '.', color='0.6', ms=4, label='shape')
    c.plot(x, S, '-', color='C2', lw=1.5, label='S: the shoulder (σ %.4f Å⁻¹)' % sg)
    c.plot(x, ref['peak'], '-', color=CS, lw=1.5,
           label='P: the peak = shape − S − line\n(FWHM %.4f Å⁻¹)' % ref['peak_fwhm'])
    c.plot(x, line, '--', color='0.4', lw=1.0, label="the line: goes to each frame's\nown straight background")
    c.set_title('(c) The two parts separated fits to each frame', fontsize=9)
    for ax in (a, b, c):
        ax.set_xlabel('Qxy (Å⁻¹)')
        ax.legend(fontsize=7)
        ax.tick_params(labelsize=8)
    a.set_ylabel('counts per monitor')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW2_shoulder_and_peak.png'), dpi=130)
    p.close(fig)
    return dict(shoulder_height=h, shoulder_centre=m, shoulder_sigma=sg,
                shoulder_fwhm=sg * 2 * math.sqrt(2 * math.log(2)),
                peak_fwhm=ref['peak_fwhm'], peak_centre=ref['peak_centre'], stretched_fwhm=ref['fwhm'],
                points_beside=int(np.sum(beside)), shoulder_share_of_shape=float(np.sum(S) / np.sum(ref['shape'])))


def bw3(out, rt, rs, k=-1):
    """One frame (the last of burn 15) under stretched and separated: fit over data, residuals."""
    p = plt()
    k = k % len(rt.profiles)
    prof = rt.profiles[k]
    fig, axes = p.subplots(4, 1, figsize=(8, 13), sharex=True, gridspec_kw=dict(height_ratios=[2.2, 1, 2.2, 1]))
    axes = axes.reshape(2, 2).T
    nums = {}
    for col, (r, name, colour) in enumerate(((rt, 'stretched', CT), (rs, 'separated', CS))):
        ref, d = r.reference, r.frame_fits[k]
        x = ref['x']
        sel = (prof[:, 0] >= r.window[0]) & (prof[:, 0] <= r.window[1])
        y, s = prof[sel, 1], prof[sel, 2]
        drawn = burn.frame_model(ref, d, x)
        total = drawn[0] if name == 'separated' else drawn
        a, b = axes[0, col], axes[1, col]
        a.errorbar(x, y, s, fmt='.', color='k', ms=3, lw=0.6, label='frame %d, ± √counts' % k)
        a.plot(x, total, '-', color=colour, lw=1.6, label='%s: the fit' % NAME[name])
        if name == 'separated':
            pk, sh, bg = drawn[1]
            a.plot(x, pk + bg, ':', color=CS, lw=1, label='peak (stretched) + background')
            a.plot(x, sh + bg, '--', color='C2', lw=1, label='shoulder (not stretched) + background')
        res = (y - total) / s
        b.bar(x, res, width=0.8 * float(np.median(np.diff(x))), color=colour)
        b.axhline(0, color='k', lw=0.6)
        for v in (-2, 2):
            b.axhline(v, color='0.6', lw=0.5, ls='--')
        P = d['params']
        dof = len(x) - len(P)
        a.set_title('%s: χ²/dof = %.2f (%d points, %d parameters)' % (NAME[name], d['chi2_dof'], len(x), len(P)), fontsize=9)
        a.legend(fontsize=7)
        b.set_xlabel('Qxy (Å⁻¹)')
        b.set_ylabel('(data − fit) / σ', fontsize=8)
        nums[name] = dict(chi2_dof=d['chi2_dof'], dof=dof, A=float(P[0]), delta=float(P[1]), w=float(P[2]),
                          B=float(P[3]) if name == 'separated' else None,
                          worst=float(np.max(np.abs(res))), beyond_2sigma=int(np.sum(np.abs(res) > 2)))
    axes[0, 0].set_ylabel('counts per monitor')
    fig.suptitle('BW3. The last frame of burn %d, fitted two ways (residuals: each point\'s miss in its own error bars)'
                 % SCAN, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW3_one_frame_fitted.png'), dpi=130)
    p.close(fig)
    nums['frame'] = k
    nums['mean_chi2_dof'] = {n: float(np.mean([d['chi2_dof'] for d in r.frame_fits if d.get('ok')]))
                             for n, r in (('stretched', rt), ('separated', rs))}
    return nums


def _change(c, T, relative=True):
    from burn_shoulder_study import change_of
    return change_of(c.fits.get('linear'), T, relative)


def bw4(out, rt, rs):
    """Burn 15 per frame: intensity and FWHM (stretched and separated, each relative to its line at t = 0), B."""
    p = plt()
    fig, axes = p.subplots(3, 1, figsize=(8, 12.5), sharex=True)
    tt = np.linspace(0, rt.duration(), 100)
    nums = {}
    for ax, q in zip(axes[:2], ('intensity', 'fwhm')):
        for r, name, colour in ((rt, 'stretched', CT), (rs, 'separated', CS)):
            c = r.trends[q]
            lin, con = c.fits['linear'], c.fits['constant']
            ref = float(lin(np.array([0.0]))[0])
            y, s = c.y / ref, c.sigma / ref
            ax.errorbar(c.t, y, s, fmt='o', ms=3, color=colour, lw=0.7, label='%s (errors from the scatter)' % NAME[name])
            ax.plot(tt, lin(tt) / ref, '-', color=colour, lw=1.4)
            ax.plot(tt, con(tt) / ref, ':', color=colour, lw=1.0)
            v, e = _change(c, r.duration())
            nums['%s_%s' % (name, q)] = dict(change=v, sigma=e, stable=bool(c.stable),
                                             delta_aicc=float(c.delta_constant_linear),
                                             scatter_factor=float(c.scatter_factor or math.nan))
        ax.set_xlabel('time by the clock (s)')
        ax.set_ylabel('%s / the line\'s value at t = 0' % ('intensity' if q == 'intensity' else 'FWHM'))
        ax.set_title('(%s) %s per frame: lines (solid) and constants (dotted)'
                     % ('a' if q == 'intensity' else 'b', 'Intensity' if q == 'intensity' else 'FWHM'), fontsize=9)
        ax.legend(fontsize=7)
    b = np.array([d['shoulder'] for d in rs.frame_fits])
    ax = axes[2]
    ax.errorbar(rs.t, b[:, 0], b[:, 1], fmt='o', ms=3, color='C2', lw=0.7)
    ax.axhline(1, color='k', lw=0.6, ls='--')
    ax.set_xlabel('time by the clock (s)')
    ax.set_ylabel('B: the shoulder\'s amplitude (1 = the mean frame\'s)')
    ax.set_title('(c) Separated\'s shoulder per frame (± counting σ)', fontsize=9)
    c = rs.trends['shoulder']
    v, e = _change(c, rs.duration())
    nums['separated_shoulder'] = dict(change=v, sigma=e, stable=bool(c.stable), b_min=float(b[:, 0].min()),
                                  b_max=float(b[:, 0].max()))
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW4_per_frame.png'), dpi=130)
    p.close(fig)
    return nums


def bw5(out, runs):
    """ΔAICc (constant − line) of the intensity, burns 14 and 15, each estimator."""
    p = plt()
    fig, ax = p.subplots(figsize=(7, 6.5))
    nums = {}
    for i, s in enumerate((14, 15)):
        for j, (name, colour) in enumerate((('stretched', CT), ('separated', CS))):
            c = runs[s, name].trends['intensity']
            d = float(c.delta_constant_linear)
            ax.bar(i * 3 + j, d, color=colour, label=NAME[name] if i == 0 else None)
            ax.text(i * 3 + j, d + (0.4 if d >= 0 else -0.4), '%.1f' % d, ha='center',
                    va='bottom' if d >= 0 else 'top', fontsize=8)
            nums['%d_%s' % (s, name)] = d
    ax.axhline(trends.STABLE_DELTA, color='k', lw=0.8, ls='--',
               label='%g: above, "changing"' % trends.STABLE_DELTA)
    ax.axhline(0, color='k', lw=0.5)
    ax.set_xticks([0.5, 3.5])
    ax.set_xticklabels(['burn 14', 'burn 15 (×4.7 flux)'])
    ax.set_ylabel('AICc(constant) − AICc(line)')
    ax.set_title('BW5. Intensity: how much better a sloped line describes the frames than a flat one', fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW5_verdict.png'), dpi=130)
    p.close(fig)
    nums['threshold'] = trends.STABLE_DELTA
    return nums


def bw6(out, n=60):
    """60 synthetic NX 15-like burns at NX 15's counts (a frame's intensity
    error 2 %: the study's NX_MONITORS): 95 % intervals of the intensity
    change against the truth."""
    from burn_shoulder_study import change_of, CASES, NX_MONITORS
    from synthetic import burn_profiles as bp
    p = plt()
    T = 21 * 10.0
    got = {'stretched': [], 'separated': []}
    for seed in range(n):
        prof, tr = bp.profiles(seed=1000 + seed, monitor=NX_MONITORS[15], **CASES['nx15_like'])
        for name in got:
            values = burn.measure_gid(prof, estimator=name)[0]
            res = burn.analyse(tr.t, values, errors='scatter')
            got[name].append(change_of(res['intensity'].fits['linear'], T) + (res['intensity'].stable,))
    truth = -0.13
    fig, axes = p.subplots(2, 1, figsize=(9, 10), sharey=True)
    nums = {'truth': truth, 'replicates': n, 'monitor': NX_MONITORS[15]}
    for ax, (name, colour) in zip(axes, (('stretched', CT), ('separated', CS))):
        v = np.array([g[0] for g in got[name]])
        s = np.array([g[1] for g in got[name]])
        hit = np.abs(v - truth) < 1.96 * s
        for i in range(n):
            ax.plot([i, i], [100 * (v[i] - 1.96 * s[i]), 100 * (v[i] + 1.96 * s[i])], '-',
                    color=colour if hit[i] else '0.65', lw=1.4)
            ax.plot(i, 100 * v[i], '.', color='k', ms=3)
        ax.axhline(100 * truth, color='k', lw=1, ls='--', label='the truth: −13 %')
        ax.axhline(0, color='0.5', lw=0.5)
        ax.set_xlabel('replicate')
        ax.set_title('%s: %d of %d intervals hold the truth; %d of %d called "changing"'
                     % (NAME[name], int(hit.sum()), n, int(sum(not g[2] for g in got[name])), n), fontsize=9)
        ax.legend(fontsize=8, loc='upper right')
        nums[name] = dict(hits=int(hit.sum()), mean=float(np.mean(v)), sd=float(np.std(v)),
                          pull_sd=float(np.std((v - truth) / s)), changing=int(sum(not g[2] for g in got[name])))
    axes[0].set_ylabel('intensity change over the burn (%), with its 95 % interval')
    fig.suptitle('BW6. Calibration: %d synthetic burns like NX 15 (FWHM +20 %%, intensity −13 %%, NX 15\'s counts)'
                 % n, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'BW6_calibration.png'), dpi=130)
    p.close(fig)
    return nums


NAME = burn.ESTIMATOR_NAMES
CH = '#7d3c98'                           # shoulder separated and held


def chain(out, label, rt, rs, rh, note=''):
    """One burn's whole chain in one tall figure, two panels wide (owner,
    2026-11-27): the mean frame and its two parts, the first and last
    frames, one frame fitted each way with its residuals, intensity and
    FWHM per frame with their lines, B per frame, and the verdicts. Qxy is
    drawn relative to the peak's centre and intensities as a share of the
    mean frame's peak, so no peak position or absolute scale is shown
    (private burns P1-P4 are published this way, owner 2026-11-27). Writes
    BC_<label>.png; returns the derived numbers it shows (no position)."""
    p = plt()
    ref = rs.reference
    c0 = ref['peak_centre']
    x = ref['x']
    dx = x - c0
    sel = (rs.profiles[0][:, 0] >= rs.window[0]) & (rs.profiles[0][:, 0] <= rs.window[1])
    top = float(np.max(ref['shape']))
    nums = dict(frames=len(rs.profiles), duration_s=float(rs.duration()))
    fig = p.figure(figsize=(10, 17))
    gs = fig.add_gridspec(6, 2, height_ratios=[1.15, 1.15, 0.5, 1, 1, 0.9], hspace=0.75, wspace=0.25)
    # (a) the mean frame and its parts
    a = fig.add_subplot(gs[0, 0])
    a.plot(dx, ref['shape'] / top, '.', color='0.5', ms=4, label='mean frame less its chord')
    if ref.get('shoulder') is not None:
        h, m, sg = ref['shoulder']
        S = h * np.exp(-0.5 * ((x - m) / sg) ** 2)
        a.plot(dx, S / top, '-', color='C2', lw=1.5, label='shoulder (a broad Gaussian)')
        nums['shoulder_fwhm_over_peak'] = float(2.3548 * sg / ref['peak_fwhm'])
    a.plot(dx, ref['peak'] / top, '-', color=CS, lw=1.5, label='peak = the rest, near the centre')
    a.axvspan(-burn.SEPARATE_CORE * ref['peak_fwhm'], burn.SEPARATE_CORE * ref['peak_fwhm'], color='0.9', zorder=0,
              label='core: the shoulder is fitted outside it')
    a.set_title('(a) The mean frame, separated into two parts', fontsize=9)
    a.set_ylabel('share of the mean frame\'s peak')
    # (b) first and last frames
    b = fig.add_subplot(gs[0, 1], sharex=a)
    for k, col, lab in ((0, '0.45', 'first frame'), (-1, CS, 'last frame')):
        q = rs.profiles[k]
        b.errorbar(q[sel, 0] - c0, q[sel, 1] / top, q[sel, 2] / top, fmt='.', ms=3, lw=0.5, color=col, label=lab)
    b.set_title('(b) The raw line cuts: first and last frame (± √counts)', fontsize=9)
    # (c, d) one frame fitted each way, and (e) residuals
    k = len(rs.profiles) - 1
    prof = rs.profiles[k]
    y, s = prof[sel, 1], prof[sel, 2]
    for col, (r, est, colour) in enumerate(((rt, 'stretched', CT), (rs, 'separated', CS))):
        d = r.frame_fits[k]
        drawn = burn.frame_model(r.reference, d, x)
        total = drawn[0] if est == 'separated' else drawn
        ax = fig.add_subplot(gs[1, col], sharex=a)
        ax.errorbar(dx, y / top, s / top, fmt='.', ms=3, lw=0.5, color='k', label='last frame')
        ax.plot(dx, total / top, '-', color=colour, lw=1.5, label='the fit')
        if est == 'separated':
            pk, sh, bg = drawn[1]
            ax.plot(dx, (sh + bg) / top, '--', color='C2', lw=1, label='shoulder + background (not stretched)')
        ax.set_title('(%s) %s: χ²/dof %.2f' % ('cd'[col], NAME[est], d['chi2_dof']), fontsize=9)
        ax.legend(fontsize=7)
        rr = fig.add_subplot(gs[2, col], sharex=a)
        res = (y - total) / s
        rr.bar(dx, res, width=0.8 * float(np.median(np.diff(x))), color=colour)
        for v in (-2, 2):
            rr.axhline(v, color='0.6', lw=0.5, ls='--')
        rr.axhline(0, color='k', lw=0.6)
        rr.set_ylabel('miss / σ', fontsize=8)
        rr.set_xlabel('Qxy − the peak\'s centre (Å⁻¹)', fontsize=8)
        nums['chi2_dof_last_frame_' + est] = float(d['chi2_dof'])
    # (f, g) per-frame intensity and FWHM
    tt = np.linspace(0, rs.duration(), 100)
    for col, q in enumerate(('intensity', 'fwhm')):
        ax = fig.add_subplot(gs[3, col])
        for r, est, colour in ((rt, 'stretched', CT), (rs, 'separated', CS), (rh, 'separated_held', CH)):
            c = r.trends[q]
            lin = c.fits['linear']
            r0 = float(lin(np.array([0.0]))[0])
            ax.errorbar(c.t, c.y / r0, c.sigma / r0, fmt='o', ms=2.5, lw=0.5, color=colour, alpha=0.8)
            v, e = _change(c, r.duration())
            ax.plot(tt, lin(tt) / r0, '-', color=colour, lw=1.3,
                    label='%s: %+.1f %% ± %.1f, %s' % (NAME[est], 100 * v, 100 * e, 'stable' if c.stable else 'changing'))
            nums['%s_%s' % (est, q)] = dict(change=v, sigma=e, verdict='stable' if c.stable else 'changing',
                                           delta_aicc=float(c.delta_constant_linear))
        ax.set_title('(%s) %s per frame, ÷ its line at t = 0' % ('fg'[col], 'Intensity' if q == 'intensity' else 'FWHM'),
                     fontsize=9)
        c = rt.trends[q]
        r0 = float(c.fits['linear'](np.array([0.0]))[0])
        ax.annotate('first frame', (c.t[0], c.y[0] / r0), xytext=(12, -14), textcoords='offset points', fontsize=7,
                    arrowprops=dict(arrowstyle='->', lw=0.6))
        ax.set_xlabel('time from the burn\'s start (s)')
        ax.legend(fontsize=6.5, loc='upper left', bbox_to_anchor=(0, -0.28), frameon=False)
    # (h) B per frame, (i) the verdicts
    ax = fig.add_subplot(gs[4, 0])
    if ref.get('shoulder') is not None:
        bb = np.array([d['shoulder'] for d in rs.frame_fits if d.get('ok')])
        tb = np.array([t for t, d in zip(rs.t, rs.frame_fits) if d.get('ok')])
        ax.errorbar(tb, bb[:, 0], bb[:, 1], fmt='o', ms=2.5, lw=0.5, color='C2')
        nums['b_min'], nums['b_max'] = float(bb[:, 0].min()), float(bb[:, 0].max())
        if 'shoulder' in rs.trends:
            v, e = _change(rs.trends['shoulder'], rs.duration())
            nums['shoulder'] = dict(change=v, sigma=e, verdict='stable' if rs.trends['shoulder'].stable else 'changing')
            ax.set_title('(h) B per frame; the shoulder: %+.1f %% ± %.1f, %s'
                         % (100 * v, 100 * e, nums['shoulder']['verdict']), fontsize=9)
    else:
        ax.text(0.5, 0.5, 'no shoulder found: the separated reads\nare the stretched ones', ha='center',
                transform=ax.transAxes)
        ax.set_title('(h) B, the shoulder\'s amplitude per frame', fontsize=9)
    ax.axhline(1, color='k', lw=0.6, ls='--')
    ax.set_xlabel('time from the burn\'s start (s)')
    ax.set_ylabel('B (1 = the mean frame\'s shoulder)')
    ax = fig.add_subplot(gs[4, 1])
    for j, (r, est, colour) in enumerate(((rt, 'stretched', CT), (rs, 'separated', CS), (rh, 'separated_held', CH))):
        dd = float(r.trends['intensity'].delta_constant_linear)
        ax.bar(j, dd, color=colour)
        ax.text(j, dd, ' %.1f' % dd, ha='center', va='bottom' if dd >= 0 else 'top', fontsize=8)
    ax.axhline(trends.STABLE_DELTA, color='k', ls='--', lw=0.8)
    ax.text(-0.45, trends.STABLE_DELTA, ' above: "changing"', va='bottom', ha='left', fontsize=7)
    ax.set_xticks([0, 1, 2], ['stretched', 'separated', 'separated\nand held'], fontsize=8)
    ax.set_ylabel('AICc(flat) − AICc(sloped line)')
    ax.set_title('(i) Intensity: is a sloped line worth its extra parameter?', fontsize=9)
    # (j) the reading, in words
    ax = fig.add_subplot(gs[5, :])
    ax.axis('off')
    it, isep = nums['stretched_intensity'], nums['separated_intensity']
    words = ['%s over %d frames, %.0f s. %s' % (label, nums['frames'], nums['duration_s'], note),
             'Intensity: %s %+.1f %% ± %.1f (%s); %s %+.1f %% ± %.1f (%s).'
             % (NAME['stretched'], 100 * it['change'], 100 * it['sigma'], it['verdict'],
                NAME['separated'], 100 * isep['change'], 100 * isep['sigma'], isep['verdict']),
             'FWHM: %+.1f %% (stretched).  Last frame χ²/dof: %.2f stretched, %.2f separated.'
             % (100 * nums['stretched_fwhm']['change'], nums['chi2_dof_last_frame_stretched'],
                nums['chi2_dof_last_frame_separated'])]
    ax.text(0, 1, '\n'.join(words), va='top', fontsize=9, transform=ax.transAxes)
    a.legend(fontsize=6.5, loc='upper left', framealpha=0.85)
    b.legend(fontsize=7)
    fig.subplots_adjust(top=0.955)
    fig.suptitle('Burn %s: from the line cuts to the verdict (Qxy relative to the peak; intensities as a share of '
                 'the mean frame\'s peak)' % label, fontsize=10, y=0.995)
    fig.savefig(os.path.join(out, 'BC_%s.png' % label), dpi=110, bbox_inches='tight')
    p.close(fig)
    return nums


def chain_from_file(out, spec, scan, label, note=''):
    """``chain`` for one burn of a SPEC file (public or private): its three readings."""
    import tempfile
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp())
    from lss_core.experiment import Experiment
    e = Experiment(spec)
    rt, rs, rh = (e.burn(int(scan), estimator=k) for k in ('stretched', 'separated', 'separated_held'))
    return chain(out, label, rt, rs, rh, note)


FL_ESTIMATORS = ('stretched', 'separated', 'separated_held', 'fit')
FL_COLOURS = {'stretched': CT, 'separated': CS, 'separated_held': CH, 'fit': '#2e8b57'}


def _frame_curve(r, k, x):
    """The curve estimator result ``r`` fitted to frame k, on x (inside the window); for the separated
    readings also (peak + background, shoulder + background). None when that frame's fit failed."""
    d = r.frame_fits[k]
    if not d.get('ok'):
        return None, None
    est = burn.canonical(r.reference.get('estimator'))
    if est == 'fit':
        return d['result'].model(x), None
    drawn = burn.frame_model(r.reference, d, x)
    if est in burn.SEPARATED_ESTIMATORS:
        total, (pk, sh, bg) = drawn
        return total, (pk + bg, sh + bg)
    return drawn, None


def firstlast(out, label, runs, note=''):
    """The first and the last frame of one burn, fitted by every estimator (owner, 2026-11-27: "First
    and last frames of a burn fitted various ways make a good figure"). Two columns (first, last); per
    estimator a row with the frame, the fitted curve (and, separated, its two parts) and a row of
    residuals in each point's own error. The last column's titles give the intensity and FWHM as
    multiples of the same estimator's first frame: the change each estimator sees between the two
    frames. Qxy relative to the peak, intensities as a share of the mean frame's peak (as ``chain``).
    ``runs``: {estimator: BurnResult}. Writes FL_<label>.png; returns the ratios shown."""
    p = plt()
    ref = runs['separated'].reference
    c0, x = ref['peak_centre'], ref['x']
    dx = x - c0
    top = float(np.max(runs['stretched'].reference['shape']))
    sel = (runs['stretched'].profiles[0][:, 0] >= runs['stretched'].window[0]) & \
          (runs['stretched'].profiles[0][:, 0] <= runs['stretched'].window[1])
    n = len(runs['stretched'].profiles)
    fig = p.figure(figsize=(10, 20))
    hr = []
    for _ in FL_ESTIMATORS:
        hr += [2.2, 0.8]
    gs = fig.add_gridspec(2 * len(FL_ESTIMATORS), 2, height_ratios=hr, hspace=0.45, wspace=0.22)
    nums = {}
    for i, est in enumerate(FL_ESTIMATORS):
        r = runs[est]
        colour = FL_COLOURS[est]
        I, F = r.values['intensity'][0], r.values['fwhm'][0]
        nums[est] = dict(intensity_last_over_first=float(I[-1] / I[0]), fwhm_last_over_first=float(F[-1] / F[0]))
        first_ax = None
        for col, k in enumerate((0, n - 1)):
            prof = r.profiles[k]
            y, s = prof[sel, 1], prof[sel, 2]
            ax = fig.add_subplot(gs[2 * i, col], sharey=first_ax)      # one y scale per row: the change shows
            first_ax = first_ax or ax
            rr = fig.add_subplot(gs[2 * i + 1, col], sharex=ax)
            ax.errorbar(dx, y / top, s / top, fmt='.', ms=3, lw=0.5, color='k',
                        label='%s frame, ± √counts' % ('first' if k == 0 else 'last'))
            total, parts = _frame_curve(r, k, x)
            if total is None:
                ax.text(0.5, 0.5, 'this frame\'s fit failed', transform=ax.transAxes, ha='center')
            else:
                ax.plot(dx, total / top, '-', color=colour, lw=1.5, label='the fit')
                if parts is not None and r.reference.get('shoulder') is not None:
                    ax.plot(dx, parts[0] / top, ':', color=colour, lw=1, label='peak (stretched) + background')
                    ax.plot(dx, parts[1] / top, '--', color='C2', lw=1, label='shoulder (not stretched) + background')
                res = (y - total) / s
                rr.bar(dx, res, width=0.8 * float(np.median(np.diff(x))), color=colour)
            for v in (-2, 2):
                rr.axhline(v, color='0.6', lw=0.5, ls='--')
            rr.axhline(0, color='k', lw=0.6)
            chi = r.frame_fits[k].get('chi2_dof', math.nan)
            if k == 0:
                title = '%s, first frame: χ²/dof %.2f' % (NAME[est], chi)
            else:
                title = 'last frame: χ²/dof %.2f; intensity %.2f ×, FWHM %.2f × the first' % (
                    chi, nums[est]['intensity_last_over_first'], nums[est]['fwhm_last_over_first'])
            ax.set_title(title, fontsize=8.5)
            if i == 0:
                ax.legend(fontsize=6.5, loc='upper left')
            elif est == 'separated' and k == 0:
                ax.legend(fontsize=6.5, loc='upper left')
            if col == 0:
                ax.set_ylabel('share of the mean\nframe\'s peak', fontsize=8)
                rr.set_ylabel('miss / σ', fontsize=7)
            if i == len(FL_ESTIMATORS) - 1:
                rr.set_xlabel('Qxy − the peak\'s centre (Å⁻¹)', fontsize=8)
    refused = runs['separated'].reference.get('shoulder_refused')
    lines = ['%s: %d frames. %s' % (label, n, note),
             'Last ÷ first frame, intensity:',
             '    ' + ';   '.join('%s %.2f' % (NAME[e], nums[e]['intensity_last_over_first']) for e in FL_ESTIMATORS[:2]),
             '    ' + ';   '.join('%s %.2f' % (NAME[e], nums[e]['intensity_last_over_first']) for e in FL_ESTIMATORS[2:])]
    if refused or runs['separated'].reference.get('shoulder') is None:
        lines.append('No shoulder kept%s: the separated readings are the stretched one.'
                     % ((' (' + refused.split(':')[0] + ')') if refused else ''))
    fig.text(0.06, 0.075, '\n'.join(lines), fontsize=8.5, va='top')
    fig.suptitle('Burn %s: the first and last frames, fitted four ways (Qxy relative to the peak; '
                 'intensities as a share of the mean frame\'s peak)' % label, fontsize=10, y=0.995)
    fig.subplots_adjust(top=0.96, bottom=0.1)
    fig.savefig(os.path.join(out, 'FL_%s.png' % label), dpi=110, bbox_inches='tight')
    p.close(fig)
    return nums


def firstlast_from_file(out, spec, scan, label, note=''):
    """``firstlast`` for one burn of a SPEC file (public or private): its four readings."""
    import tempfile
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp())
    from lss_core.experiment import Experiment
    e = Experiment(spec)
    runs = {k: e.burn(int(scan), estimator=k) for k in FL_ESTIMATORS}
    return firstlast(out, label, runs, note)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/burn_shoulder/walkthrough', help='output folder')
    ap.add_argument('--replicates', type=int, default=60, help='BW6: synthetic burns')
    ap.add_argument('--chain', nargs=3, action='append', metavar=('SPEC', 'SCAN', 'LABEL'),
                    help='only BC_<LABEL>.png, the whole chain of one burn (repeatable; for private burns the '
                    'figure shows no position, file or scan)')
    ap.add_argument('--firstlast', nargs=3, action='append', metavar=('SPEC', 'SCAN', 'LABEL'),
                    help='only FL_<LABEL>.png: the first and last frames fitted by every estimator (repeatable)')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    if a.firstlast:
        got = {lab: firstlast_from_file(a.out, spec, scan, lab) for spec, scan, lab in a.firstlast}
        print(json.dumps(got, indent=1, default=float))
        return 0
    if a.chain:
        got = {lab: chain_from_file(a.out, spec, scan, lab) for spec, scan, lab in a.chain}
        with open(os.path.join(a.out, 'numbers_chain.json'), 'w', encoding='utf-8') as f:
            json.dump(got, f, indent=1, default=float)
        print(json.dumps(got, indent=1, default=float))
        return 0
    e, runs = nx_burns()
    rt, rs = runs[SCAN, 'stretched'], runs[SCAN, 'separated']
    n = OrderedDict()
    n['BW1'] = bw1(a.out, e, rt)
    n['BW2'] = bw2(a.out, rs)
    n['BW3'] = bw3(a.out, rt, rs)
    n['BW4'] = bw4(a.out, rt, rs)
    n['BW5'] = bw5(a.out, runs)
    n['BW6'] = bw6(a.out, a.replicates)
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(n, f, indent=1, default=float)
    print(json.dumps(n, indent=1, default=float))
    return 0


if __name__ == '__main__':
    sys.exit(main())
