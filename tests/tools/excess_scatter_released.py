"""Real-data figures for the excess-scatter study (C63) from released reflectivity runs (before 2019).

The owner released reflectivity data from before 2019 for figures (2026-11-25, AGENTS.md): reduced curves,
fits and frames, minimal and anonymous. The committed extract in ``docs/studies/excess_scatter/released/``
(made privately by ``sample_data/private/old/scripts/released_export.py``) holds four cherry-picked series
A-D, every 6-point window of the 96 reduced released series (derived numbers), and two cropped frames.
This tool draws from those files only, so it runs anywhere:

    python tests/tools/excess_scatter_released.py [--out docs/studies/excess_scatter/released]

R1 two frames with the reader's boxes; R2 the four series and their window pulls; R3 single windows, their
weights, where the big ones sit and why six points; R4 every released window pooled, against the 18 private runs.
"""
import argparse
import csv
import json
import math
import os
import sys
import textwrap
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [p for p in (ROOT, HERE, os.path.join(ROOT, 'tests')) if p not in sys.path]

import excess_scatter as E          # noqa: E402

STUDY = os.path.join(ROOT, 'docs', 'studies', 'excess_scatter')
DATA = os.path.join(STUDY, 'released')
INK = '0.15'
C_A, C_B, C_X, C_R = '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'
SCAN_COLOURS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#8c564b', '#e377c2', '#17becf']
WHAT = {'A': 'seven scans, a smooth curve', 'B': 'clean: scatter as the error bars say',
        'C': 'a real excess, no wild points', 'D': 'a sharp minimum: shape, not scatter'}
COUNT_EDGES = [0, 1e3, 1e4, 1e5, 1e12]
NOTE_BOX = dict(boxstyle='round,pad=0.35', fc='#fff8e1', ec='#d9b54a', lw=0.8)


def _style():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.3, 'text.color': INK,
                         'axes.labelcolor': INK})
    return plt


def _read(name, data=DATA):
    with open(os.path.join(data, name), encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_series(data=DATA):
    """{series: [(q, y, s, counts) arrays per scan, in order]}"""
    out = {}
    for r in _read('series.csv', data):
        out.setdefault(r['series'], {}).setdefault(int(r['scan']), []).append(
            (float(r['qz']), float(r['y']), float(r['sigma']), float(r['counts'])))
    return {k: [np.array(v[n]).T for n in sorted(v)] for k, v in out.items()}


def load_windows(data=DATA):
    w = _read('windows.csv', data)
    f = lambda k: np.array([float(r[k]) for r in w])
    return dict(series=np.array([r['series'] for r in w]), scan=np.array([int(r['scan']) for r in w]),
                q=f('qz'), d=f('d'), sd=f('sigma_d'), counts=f('counts'), bg=f('bg_share'))


def terms_of(win, mask=None):
    """windows.csv rows as one estimator term (d, a = σ_d², b = 1), optionally a subset."""
    m = np.ones(len(win['d']), bool) if mask is None else mask
    return [dict(d=win['d'][m], a=win['sd'][m] ** 2, b=np.ones(int(m.sum())))]


def foot(fig, text, width=210):
    fig.text(0.01, 0.01, textwrap.fill(text, width), fontsize=7.5, color='0.4', ha='left', va='bottom')


# ------------------------------------------------------------------------------------------ R1 frames
def _boxes(centre, slit, bg_px):
    """The reader's three boxes (TwoDDetector.sumROI, direction H) as (row slice, column slice)."""
    cx, cy = int(round(centre[0])), int(round(centre[1]))
    hx, hy = (slit[0] - 2 + 1) // 2, (slit[1] - 2 + 1) // 2
    box = lambda x: (slice(cy - hy, cy + hy + 1), slice(x - hx, x + hx + 1))
    off = int(bg_px)
    return {'signal': box(cx), 'left background': box(int(cx - bg_px)), 'right background': box(int(cx + bg_px))}


def r1(out, plt, data=DATA):
    meta = json.load(open(os.path.join(data, 'frames.json'), encoding='utf-8'))['frames']
    px = {}
    for r in _read('frames.csv', data):
        px.setdefault(int(r['frame']), []).append((int(r['row']), int(r['col']), float(r['counts'])))
    from matplotlib.colors import LogNorm
    from matplotlib.patches import Rectangle
    fig, axs = plt.subplots(2, 2, figsize=(13, 7.4), gridspec_kw=dict(width_ratios=(1.25, 1)))
    for k, m in enumerate(meta):
        img = np.zeros(m['shape'])
        for y, x, v in px[m['frame']]:
            img[y, x] = v
        bx = _boxes(m['centre'], m['slit'], m['bg_offset_px'])
        sums = {n: float(img[b].sum()) for n, b in bx.items()}
        want = {'signal': m['signal'], 'left background': m['left_bg'], 'right background': m['right_bg']}
        ok = all(abs(sums[n] - want[n]) <= 0.5 + 1e-6 * want[n] for n in sums)
        ax = axs[k, 0]
        im = ax.imshow(np.maximum(img, 0.5), norm=LogNorm(vmin=0.5, vmax=max(img.max(), 1)), cmap='magma',
                       origin='upper', aspect='equal')
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01, label='counts per pixel (log)')
        for (n, b), c in zip(bx.items(), ('#7fdbff', '#ffffff', '#ffffff')):
            ax.add_patch(Rectangle((b[1].start - 0.5, b[0].start - 0.5), b[1].stop - b[1].start,
                                   b[0].stop - b[0].start, fill=False, ec=c, lw=1.4))
            ax.text(0.5 * (b[1].start + b[1].stop) - 0.5, b[0].start - 1.2, '%s\n%s counts' % (n, format(int(sums[n]), ',')),
                    ha='center', va='bottom', fontsize=7.5, color='white',
                    bbox=dict(boxstyle='round,pad=0.2', fc='0.1', ec='none', alpha=0.7))
        ax.set_title('Frame %d, %s, Qz %.3f Å⁻¹: the frame as recorded, cropped' % (m['frame'], m['label'], m['qz']),
                     fontsize=9)
        ax.set_xlabel('detector column (pixels, crop)')
        ax.set_ylabel('detector row (pixels, crop)')
        ax.grid(False)
        ax = axs[k, 1]
        rows = bx['signal'][0]
        prof = img[rows].sum(axis=0)
        ax.step(np.arange(len(prof)), np.maximum(prof, 0.5), where='mid', color=INK, lw=1)
        for n, b in bx.items():
            ax.axvspan(b[1].start - 0.5, b[1].stop - 0.5, color=C_A if n == 'signal' else '0.6', alpha=0.18)
        ax.set_yscale('log')
        ax.set_xlabel('detector column (pixels, crop)')
        ax.set_ylabel('counts summed over the box rows (log)')
        bgm = 0.5 * (sums['left background'] + sums['right background'])
        share = bgm / max(sums['signal'], 1)
        ax.set_title('Across the beam: signal box (blue) and background boxes (grey)', fontsize=9)
        txt = ('net = signal − mean background = %s − %s = %s counts\nbackground is %.0f %% of the signal box\n'
               '÷ monitor %s → y = %.4g ± %.2g (%.2f %%)' %
               (format(int(sums['signal']), ','), format(int(bgm), ','), format(int(sums['signal'] - bgm), ','),
                share * 100, format(int(m['monitor']), ','), m['net'], m['sigma'], 100 * m['sigma'] / m['net']))
        if not ok:
            txt = 'BOX SUMS DO NOT MATCH THE READER\'S: not drawn as a reduction'
        ax.text(0.02, 0.97, txt, transform=ax.transAxes, ha='left', va='top', fontsize=8, bbox=NOTE_BOX)
        ax.set_ylim(top=ax.get_ylim()[1] * 30)
    fig.suptitle('R1. Two real reflectivity frames: bright near the edge, faint at high Qz where the background '
                 'is almost as large as the signal', x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'Released data (before 2019, 10 keV, series A; owner, 2026-11-25). Pilatus frames cropped around the '
         'reflected beam. Boxes as the reader draws them (lss_core.reflectivity.frame_row, TwoDDetector.sumROI; '
         'slit 21 × 11 pixels, 5 pixels tall for the first scan\'s points at 0.02 < Qz < 0.03; background boxes '
         '0.5° to either side). The box sums are recomputed here from the pixels and checked against the reader\'s. '
         'The error bar of y is √counts through the subtraction and the division, plus the monitor term '
         '("budget" model).')
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(os.path.join(out, 'R1_frames.png'), dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------------------------------ R2 series
def r2(out, plt, data=DATA):
    ser, win = load_series(data), load_windows(data)
    labs = sorted(ser)
    fig, axs = plt.subplots(2, len(labs), figsize=(4.3 * len(labs), 7.4), gridspec_kw=dict(height_ratios=(2.2, 1)),
                            sharex='col')
    for col, lab in enumerate(labs):
        ax = axs[0, col]
        for k, (q, y, s, c) in enumerate(ser[lab]):
            rf = E._fresnel(q)
            ax.errorbar(q, y / rf, yerr=s / rf, fmt='o', ms=2.8, capsize=1.5, color=SCAN_COLOURS[k % 7],
                        label='scan %d' % (k + 1))
        ax.set_yscale('log')
        m = win['series'] == lab
        z = win['d'][m] / win['sd'][m]
        mx = E.estimate_mixture('curvature', terms_of(win, m), profile=False)
        ax.set_title('Series %s: %s\n%d windows · χ²/n %.2f · core X %.2f %% · %d beyond 5σ'
                     % (lab, WHAT.get(lab, ''), m.sum(), float(np.mean(z ** 2)), mx['x'] * 100,
                        int(np.sum(np.abs(z) > 5))), fontsize=8.5)
        if col == 0:
            ax.set_ylabel('R / R_F (each scan as reduced, before the joins)')
        ax.legend(frameon=False, fontsize=7, ncol=2, loc='lower left')
        ax = axs[1, col]
        ax.axhspan(-1, 1, color=C_A, alpha=0.08)
        ax.axhline(0, color=INK, lw=0.8)
        for v in (-3, 3):
            ax.axhline(v, color='0.5', ls=':', lw=0.8)
        big = np.abs(z) > 5
        ax.plot(win['q'][m][~big], z[~big], 'o', ms=3, color=C_A, label='|d/σ_d| ≤ 5')
        ax.plot(win['q'][m][big], np.clip(z[big], -12, 12), '^', ms=5, color=C_R, label='beyond 5σ (clipped at 12)')
        ax.set_ylim(-13, 13)
        if lab == 'D':
            ax.text(0.02, 0.04, 'the large values: the sharp minimum near 0.055', transform=ax.transAxes,
                    fontsize=7, color='0.3')
        ax.set_xlabel('Qz (Å⁻¹, window centre)')
        if col == 0:
            ax.set_ylabel('window d / σ_d\n(shaded: ±1, dotted: ±3)')
        ax.legend(frameon=False, fontsize=7, loc='upper right')
    fig.suptitle('R2. Four real series chosen to show the range: clean, a real excess, and a curve too sharp for '
                 'the windows', x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'Released data (before 2019, 10 keV, anonymous series A–D, cherry-picked from 96 released series for '
         'what they show; owner, 2026-11-25). Top: each scan as the reader reduces it (budget errors), divided by '
         'the Fresnel curve of water (Qc 0.0217 Å⁻¹), before the scans are joined. Bottom: every 6-point window\'s '
         'difference over its stated error (W2 in walkthrough.md): honest error bars put two thirds inside ±1 and '
         'almost none beyond ±3. Core X: the core + outlier fit of tests/tools/excess_scatter.py on that series '
         'alone. Series D: its large window differences sit at a deep minimum near 0.055 Å⁻¹, where the curve bends '
         'faster than a quartic over six points can follow; most released series show the same minimum.', 230)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    fig.savefig(os.path.join(out, 'R2_series.png'), dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------------------------------ R3 windows
def _windows_of(ser):
    """Recompute every window of the series A-D from their points (checks windows.csv)."""
    out = []
    for lab, scans in ser.items():
        for k, (q, y, s, c) in enumerate(scans):
            o = np.argsort(q)
            q, y, s, c = q[o], y[o], s[o], c[o]
            ok = E._ok(y, s) & (q >= E.Q_MIN)
            q, y, s, c = q[ok], y[ok], s[ok], c[ok]
            t = E.curvature_terms(q, y, s)
            if t is None:
                continue
            for i, (d, a, qm) in enumerate(zip(t['d'], t['a'], t['q'])):
                j = int(np.argmin(np.abs(q - qm)))
                lo = j - E.DIFF_ORDER // 2 - 1 + (E.DIFF_ORDER + 1) % 2
                out.append(dict(series=lab, scan=k + 1, q=q, y=y, s=s, c=c, d=d, sd=math.sqrt(a), qm=qm,
                                start=max(0, j - (E.DIFF_ORDER + 1) // 2)))
    return out


def r3(out, plt, data=DATA):
    ser = load_series(data)
    ws = _windows_of(ser)
    z = lambda w: w['d'] / w['sd']
    pick = []
    b = [w for w in ws if w['series'] == 'B']
    pick.append(('a typical window (series B)', sorted(b, key=lambda w: abs(abs(z(w)) - 0.674))[0]))
    a = [w for w in ws if w['series'] == 'A']
    pick.append(('the most photons (series A)', max(a, key=lambda w: w['c'][w['start']])))
    pick.append(('the fewest photons (series A)', min(a, key=lambda w: w['c'][w['start']])))
    cc = [w for w in ws if w['series'] == 'C' and abs(z(w)) < 5]
    pick.append(('a real excess (series C)', max(cc, key=lambda w: abs(z(w)))))
    dd = [w for w in ws if w['series'] == 'D']
    worst = max(dd, key=lambda w: abs(z(w)))
    pick.append(('a sharp minimum (series D)', worst))
    same = sorted([w for w in dd if w['scan'] == worst['scan'] and w['qm'] > worst['qm']], key=lambda w: w['qm'])
    pick.append(('one window further on (series D)', same[2] if len(same) > 2 else same[-1]))
    pick = pick[:5]                     # the sixth ("one window further on") argued from a quartic bending
                                        # through an edge point, which any quartic can do: dropped (owner, 2026-11-26)
    n = E.DIFF_ORDER + 1
    fig, axs = plt.subplots(2, 4, figsize=(14.5, 8.0))
    _r3_weights(axs[0, 0], n)
    slots = [axs[0, 1], axs[0, 2], axs[0, 3], axs[1, 0], axs[1, 1]]
    for ax, (title, w) in zip(slots, pick):
        j = int(np.argmin(np.abs(w['q'] - w['qm'])))
        i0 = max(0, min(len(w['q']) - n, j - n // 2))
        ctx = slice(max(0, i0 - 4), min(len(w['q']), i0 + n + 4))
        win = slice(i0, i0 + n)
        lr = lambda sl_: (np.log(w['y'][sl_] / E._fresnel(w['q'][sl_])), w['s'][sl_] / w['y'][sl_])
        ly, sl = lr(ctx)
        ax.errorbar(w['q'][ctx], ly, yerr=sl, fmt='o', color='0.7', capsize=2, ms=3.5,
                    label='neighbours in the same scan')
        ly, sl = lr(win)
        ax.errorbar(w['q'][win], ly, yerr=sl, fmt='o', color=C_A, capsize=3, ms=5, label='the six points, ±1σ')
        ax.set_title('%s\nQz %.3f Å⁻¹, ~%s counts per point\nd / σ_d = %+.1f: %s'
                     % (title, w['qm'], format(int(np.median(w['c'][win])), ','), z(w), _r3_verdict(z(w))),
                     fontsize=9)
        ax.set_xlabel('Qz (Å⁻¹)', fontsize=8)
        ax.set_ylabel('ln(R / R_F)', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.margins(y=0.25)
    slots[0].legend(frameon=False, fontsize=7, loc='upper right')
    nums = _r3_same_qz(axs[1, 2], load_windows(data), pick[4][1]['qm'])
    _r3_window_size(axs[1, 3])
    fig.suptitle('R3. Single real windows: the six points, the one number they give, and why six', x=0.01,
                 ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'Released data (before 2019, 10 keV; series A–D of R2), divided by the Fresnel curve. No curve is drawn '
         'through a window: one with five parameters (a quartic) passes near six points whatever they do, and its six '
         'residuals are the one number d in a fixed pattern, so drawing them would show nothing more. The weights '
         '(first panel) cancel any curve up to a quartic and keep what is left over: d / σ_d is about ±1 when the error '
         'bars are honest. Grey: the scan\'s neighbouring points, for the eye. A deep minimum sampled by one point '
         'gives a huge d, exactly as a wild point would; what says it is the curve is that such windows pile up at the '
         'same Qz across the released series (seventh panel). Last panel: known truth with no excess at all (synthetic, '
         'tests/tools/excess_scatter.py): shorter windows read the curve\'s own shape as scatter; six is the shortest '
         'that does not on a monolayer; a film\'s fringes still leak in a little.', 215)
    fig.tight_layout(rect=(0, 0.075, 1, 0.95))
    fig.savefig(os.path.join(out, 'R3_windows.png'), dpi=200)
    plt.close(fig)
    return nums


R3_BAND = 0.010     # a window's middle this close to the minimum: its six points (about ±0.006 Å⁻¹) reach it


def _r3_verdict(zv):
    a = abs(zv)
    if a < 2:
        return 'within the error bars'
    if a < 5:
        return 'more scatter than the error bars say'
    return 'far off (a wild point, or a sharp curve)'


def _r3_weights(ax, n):
    """The window's weights on an even grid, as tests/tools/excess_scatter.curvature_terms builds them."""
    x = np.linspace(-0.5, 0.5, n)
    w = np.linalg.svd(np.vstack([x ** m for m in range(n - 1)]))[2][-1]
    w = w / np.abs(w).max() * 10
    w = w if w[0] < 0 else -w
    ax.bar(np.arange(1, n + 1), w, color=C_A, width=0.6)
    for k, v in enumerate(w):
        ax.text(k + 1, v + (1 if v > 0 else -1), '%+.0f' % v, ha='center', va='bottom' if v > 0 else 'top',
                fontsize=8.5)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_ylim(-14, 27)
    ax.set_xticks(range(1, n + 1))
    ax.set_xlabel('point in the window', fontsize=8)
    ax.set_ylabel('weight w (scaled)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title('What one window gives: d = Σ w · ln(R/R_F)\n(even grid; the code finds them for any grid)',
                 fontsize=9)
    ax.text(0.5, 0.97, 'Any straight line, parabola, cubic or quartic\nthrough the six points gives d = 0.\n'
            'What is left is noise: σ_d is the same sum\nover the error bars, so d / σ_d ≈ ±1.',
            transform=ax.transAxes, ha='center', va='top', fontsize=7.5, bbox=NOTE_BOX)


def _r3_same_qz(ax, win, qmin_):
    zz = np.abs(win['d'] / win['sd'])
    m = (win['q'] > 0.04) & (win['q'] < 0.10)
    big = zz > 10
    ax.scatter(win['q'][m & ~big], zz[m & ~big], s=5, color='0.6', label='a window')
    ax.scatter(win['q'][m & big], zz[m & big], s=9, color=C_R, label='a window beyond 10σ')
    near = np.abs(win['q'] - qmin_) <= R3_BAND + 1e-9
    nb, nn = int(np.sum(big & near)), int(np.sum(big))
    nser = len(np.unique(win['series'][big & near]))
    share = float(np.mean(near))
    ax.axvspan(qmin_ - R3_BAND, qmin_ + R3_BAND, color=C_B, alpha=0.15, lw=0)
    ax.axhline(10, color=INK, lw=0.8, ls='--')
    ax.set_yscale('log')
    ax.set_xlabel('Qz of the window (Å⁻¹)', fontsize=8)
    ax.set_ylabel('|d / σ_d|', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title('Is it the curve? The big windows of all\n%d released series pile up at one Qz'
                 % len(np.unique(win['series'])), fontsize=9)
    ax.set_ylim(top=zz[m].max() * 40)
    ax.text(0.97, 0.97, '%d of the %d windows beyond 10σ (%.0f %%) have their\nmiddle within ±%.3f Å⁻¹ of %.3f '
            '(shaded),\nin %d series; the band holds %.0f %% of all windows'
            % (nb, nn, 100 * nb / nn, R3_BAND, qmin_, nser, 100 * share), transform=ax.transAxes, ha='right',
            va='top', fontsize=7.5, bbox=NOTE_BOX)
    ax.legend(frameon=False, fontsize=7, loc='lower right')
    allt, rest = terms_of(win), terms_of(win, ~near)
    mx_all, mx_rest = (E.estimate_mixture('curvature', t, profile=False) for t in (allt, rest))
    s_all, s_rest = (E.estimate_scale('curvature', t)['s'] for t in (allt, rest))
    return dict(minimum_qz=float(qmin_), band=R3_BAND, beyond10_near=nb, beyond10_all=nn, series_near=nser,
                share_of_windows_in_band=share,
                outliers_all=mx_all['pi'], outliers_without_band=mx_rest['pi'],
                core_x_all=mx_all['x'], core_x_without_band=mx_rest['x'], s_all=s_all, s_without_band=s_rest)


def _r3_window_size(ax, n_series=24, seed=11):
    """Known truth, no excess: the spread of d / σ_d for windows of 3-7 points on three synthetic curves."""
    rng = np.random.default_rng(seed)
    pts = [3, 4, 5, 6, 7]
    cols = {'water': C_A, 'DPPC': C_B, 'film 100 Å': C_X}
    for name, prof in E._curves().items():
        sers = [E.synth_series(prof, 0.0, 0.0, rng) for _ in range(n_series)]
        sd = []
        for p in pts:
            zs = []
            for scans in sers:
                for q, y, s in scans:
                    t = E.curvature_terms(q, y, s, order=p - 1)
                    if t is not None:
                        zs += list(t['d'] / np.sqrt(t['a']))
            sd.append(float(np.std(zs)))
        ax.plot(pts, sd, 'o-', color=cols[name], label=name)
        ax.annotate('%.2f' % sd[pts.index(E.DIFF_ORDER + 1)], (E.DIFF_ORDER + 1, sd[pts.index(E.DIFF_ORDER + 1)]),
                    textcoords='offset points', xytext={'water': (-26, 5), 'DPPC': (5, -11)}.get(name, (6, 4)),
                    fontsize=7.5, color=cols[name])
    ax.axhline(1, color=INK, lw=0.8, ls='--')
    ax.axvline(E.DIFF_ORDER + 1, color='0.6', lw=0.8, ls=':')
    ax.text(E.DIFF_ORDER + 1, 0.98, ' used', transform=ax.get_xaxis_transform(), fontsize=7.5, va='top')
    ax.set_yscale('log')
    ax.set_yticks([0.9, 1, 1.5, 2, 3, 4])
    ax.set_yticklabels(['0.9', '1', '1.5', '2', '3', '4'])
    ax.minorticks_off()
    ax.set_xticks(pts)
    ax.set_xlabel('points in a window', fontsize=8)
    ax.set_ylabel('spread of d / σ_d (1 = honest)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_title('Why six points: with no excess at all (known\ntruth), shorter windows see the curve as scatter',
                 fontsize=9)
    ax.legend(frameon=False, fontsize=7, loc='center right')


# ------------------------------------------------------------------------------------------ R4 the pool
def _bins(win, nboot, rng):
    series = np.unique(win['series'])
    rows = []
    for lo, hi in zip(COUNT_EDGES[:-1], COUNT_EDGES[1:]):
        m = (win['counts'] >= lo) & (win['counts'] < hi)
        if m.sum() < 30:
            rows.append(dict(lo=lo, hi=hi, n=int(m.sum()), x=math.nan, xlo=math.nan, xhi=math.nan, s=math.nan))
            continue
        x = E.estimate_mixture('curvature', terms_of(win, m), profile=False)['x']
        s = E.estimate_scale('curvature', terms_of(win, m))['s']
        bs = []
        for _ in range(nboot):
            pickd = rng.choice(series, len(series))
            mm = np.zeros(len(m), bool)
            cnt = np.zeros(len(m), int)
            for sid in pickd:
                cnt += (win['series'] == sid)
            sel = np.repeat(np.nonzero(m & (cnt > 0))[0], cnt[m & (cnt > 0)])
            if len(sel) >= 30:
                bs.append(E.estimate_mixture('curvature', [dict(d=win['d'][sel], a=win['sd'][sel] ** 2,
                                                                b=np.ones(len(sel)))], profile=False)['x'])
        rows.append(dict(lo=lo, hi=hi, n=int(m.sum()), x=x, xlo=float(np.percentile(bs, 16)) if bs else math.nan,
                         xhi=float(np.percentile(bs, 84)) if bs else math.nan, s=s))
    return rows


def r4(out, plt, data=DATA, nboot=40):
    win = load_windows(data)
    rng = np.random.default_rng(63)
    allt = terms_of(win)
    z = win['d'] / win['sd']
    mx = E.estimate_mixture('curvature', allt, profile=False)
    sc = E.estimate_scale('curvature', allt)
    g = E.estimate('curvature', allt)
    rows = _bins(win, nboot, rng)
    priv = [r for r in _read('real_by.csv', STUDY) if r['estimator'] == 'within' and r['by'] == 'counts per point']
    pscale = [r for r in _read('real_scale.csv', STUDY) if r['estimator'] == 'within' and r['by'] == 'counts per point']
    pall = [r for r in _read('real_scale.csv', STUDY) if r['estimator'] == 'within' and r['by'] == 'all'][0]
    pov = [r for r in _read('real_overall.csv', STUDY) if r['estimator'] == 'within'][0]
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.2))
    ax = axs[0]
    bins = np.linspace(-12, 12, 97)
    ax.hist(np.clip(z, -12, 12), bins=bins, density=True, color='0.75', label='released windows, d / σ_d (clipped ±12)')
    zz = np.linspace(-12, 12, 600)
    gauss = lambda w: np.exp(-zz ** 2 / (2 * w * w)) / (w * math.sqrt(2 * math.pi))
    ax.plot(zz, gauss(1.0), color=C_A, label='honest error bars: N(0, 1)')
    ax.plot(zz, gauss(sc['s']), color=C_B, ls='--', label='error bars × s = %.2f' % sc['s'])
    v0 = float(np.median(win['sd'] ** 2))
    vc, vo = v0 + mx['x'] ** 2, v0 + mx['x'] ** 2 + mx['tau'] ** 2
    w0 = math.sqrt(vc / v0)
    mix = (1 - mx['pi']) * gauss(w0) + mx['pi'] * gauss(math.sqrt(vo / v0))
    ax.plot(zz, mix, color=C_X, lw=1.3, label='fitted core + outliers')
    ax.set_yscale('log')
    ax.set_ylim(1e-5, 3)
    ax.set_xlabel('window difference / stated σ')
    ax.set_ylabel('probability density (log)')
    ax.set_title('All %s released windows: a slightly wide core and long tails' % format(len(z), ','), fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, loc='upper right')
    ax.text(0.02, 0.97, 'median |d/σ_d| %.2f (honest: 0.67)\nbeyond 3σ: %.1f %% (honest: 0.27 %%)\n'
            'beyond 10σ: %.1f %%\none Gaussian would say X = %.1f %%'
            % (np.median(np.abs(z)), 100 * np.mean(np.abs(z) > 3), 100 * np.mean(np.abs(z) > 10), g['x_ml'] * 100),
            transform=ax.transAxes, ha='left', va='top', fontsize=7.5, bbox=NOTE_BOX)
    labels = ['< 10³', '10³–10⁴', '10⁴–10⁵', '≥ 10⁵']
    for ax, key, ylab in ((axs[1], 'x', 'core excess X (% of R)'), (axs[2], 's', 'error scale s (real error ÷ stated)')):
        xs = np.arange(len(rows))
        if key == 'x':
            v = np.array([r['x'] for r in rows]) * 100
            lo = np.array([r['xlo'] for r in rows]) * 100; hi = np.array([r['xhi'] for r in rows]) * 100
            pv = np.array([float(r['core_x']) for r in priv]) * 100
            plo = np.array([float(r['core_x_lo']) for r in priv]) * 100
            phi = np.array([float(r['core_x_hi']) for r in priv]) * 100
            floor = 0.03                                    # % of R: the axis bottom; bars below it are clipped
            lo_c = np.maximum(np.nan_to_num(lo, nan=floor), floor)
            ax.errorbar(xs - 0.1, v, yerr=[v - lo_c, np.nan_to_num(hi - v)], fmt='o', color=C_A,
                        capsize=3, label='released runs (before 2019), %d series' % len(np.unique(win['series'])))
            ax.errorbar(xs + 0.1, pv, yerr=[pv - plo, phi - pv], fmt='s', color=C_B, capsize=3,
                        label='the 18 private runs (real_by.csv)')
            for x, l in zip(xs, lo):
                if not np.isfinite(l) or l < floor:
                    ax.annotate('16th percentile\nat ~0 (clipped)', (x - 0.1, floor), xytext=(4, 4),
                                textcoords='offset points', fontsize=6.5, color='0.35', va='bottom')
            ax.set_yscale('log')
            ax.set_ylim(floor, 10)
            ax.set_title('Core excess by counts: released %.0f× and private %.0f× smaller at the most counts'
                         % (v[0] / v[-1], pv[0] / pv[-1]), fontsize=9)
        else:
            v = np.array([r['s'] for r in rows])
            pv = np.array([float(r['s']) for r in pscale])
            ax.plot(xs - 0.1, v, 'o', color=C_A, label='released runs (s = %.2f overall)' % sc['s'])
            ax.plot(xs + 0.1, pv, 's', color=C_B, label='the 18 private runs (s = %.2f overall)' % float(pall['s']))
            ax.axhline(1, color='0.5', ls=':', lw=1)
            ax.set_ylim(0.9, max(np.nanmax(v), np.nanmax(pv)) + 0.15)
            ax.set_title('Error scale by counts: about constant, a little above 1', fontsize=9)
        for x, val in zip(xs, v):
            if np.isfinite(val):
                ax.annotate(('%.2f %%' if key == 'x' else '%.2f') % val, (x - 0.1, val), xytext=(-6, 6),
                            textcoords='offset points', ha='right', fontsize=7.5)
        ax.set_xticks(xs)
        ax.set_xticklabels(['%s\n%s windows' % (l, format(r['n'], ',')) for l, r in zip(labels, rows)], fontsize=7.5)
        ax.set_xlabel('effective counts per point, (y / σ)², released windows')
        ax.set_ylabel(ylab)
        ax.legend(frameon=False, fontsize=7.5, loc='upper right')
    fig.suptitle('R4. Every released window pooled: error bars %.0f %% too small (s %.2f), core X %.2f %% of R, '
                 '%.1f %% of windows wild; the 18 private runs: s %.2f, X %.2f %%, %.1f %%'
                 % ((sc['s'] - 1) * 100, sc['s'], mx['x'] * 100, mx['pi'] * 100, float(pall['s']),
                    float(pov['core_x']) * 100, float(pov['outlier_share']) * 100),
                 x=0.01, ha='left', fontweight='bold', fontsize=11)
    foot(fig, 'Released data (before 2019, 10 keV; windows.csv: every 6-point window of the 96 reduced released '
         'series, derived numbers). The fits are those of tests/tools/excess_scatter.py (core + outliers, and the '
         'error-scale model with outliers), the same code as the private numbers. Released bars: 16th–84th '
         'percentiles of %d bootstrap resamples of the series; private bars: of runs. The private runs are '
         'newer and from other samples, so agreement is a check, not a requirement.' % nboot, 220)
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    fig.savefig(os.path.join(out, 'R4_pool.png'), dpi=200)
    plt.close(fig)
    numbers = dict(windows=int(len(z)), series=int(len(np.unique(win['series']))), core_x=mx['x'], pi=mx['pi'],
                   tau=mx['tau'], s=sc['s'], gauss_x=g['x_ml'], median_abs_z=float(np.median(np.abs(z))),
                   beyond3=float(np.mean(np.abs(z) > 3)), beyond10=float(np.mean(np.abs(z) > 10)),
                   by_counts=rows)
    json.dump(numbers, open(os.path.join(out, 'numbers.json'), 'w'), indent=1, default=float)
    return numbers


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=DATA)
    ap.add_argument('--boot', type=int, default=40, help='bootstrap resamples of the series for R4')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    warnings.simplefilter('ignore')
    plt = _style()
    r1(a.out, plt)
    r2(a.out, plt)
    m3 = r3(a.out, plt)
    n = r4(a.out, plt, nboot=a.boot)
    n['minimum'] = m3
    json.dump(n, open(os.path.join(a.out, 'numbers.json'), 'w'), indent=1, default=float)
    print('released pool: %d windows, s %.3f, core X %.4f, outliers %.3f' % (n['windows'], n['s'], n['core_x'], n['pi']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
