"""Before/after figures for GID patching: the legacy 3-column patch against
the pinhole-geometry patch (exact per-pixel angles, the default), on the
same scans (owner, 2026-11-19; docs/COMPARISONS.md C10, C14, C21, C22).

    python tests/tools/gid_compare_figures.py --spec sample_data/NX_school/2026sep/20260923 \\
        --scans 11 --out docs/figures/gid_compare
    python tests/tools/gid_compare_figures.py --spec FILE --scans "386,387,388,389" --out DIR

Three PNG files per scan set, named ``<label>_S<scans>_<what>.png``:

- ``maps``: the two Qxy–Qz maps side by side on the same axes and one
  logarithmic colour scale (the legacy map times k, the factor that
  matches it to the pinhole map over the lowest Qz level, because the two
  are in different units: a 3-column sum against a per-pixel mean);
  hatched = no data; the join overlaps and the legacy edge copies (P33)
  outlined.
- ``profiles``: the Qxy profile (integrated over Qz) and the Qz profile
  (integrated over Qxy), both over the Qz and Qxy ranges the two maps have
  in common, with ±1σ bands; the ratio pinhole / (k × legacy) on the legacy
  bins; σ/I per bin of each method, and of the pinhole map summed to the
  legacy bins (the gain in counts at equal resolution).
- ``joins``: where each 2θ join and each Qz join was fitted (overlap
  ranges), the fitted factors ± errors with χ²/dof, and a summary table.

and ``<label>_S<scans>_summary.json`` with the numbers of the table.
Uses only the scripting API (lss_core.experiment), i.e. the same code as
the window, and runs headless (Agg). Private data (sample_data/private,
sample_data/bu): --out must be outside the repository.
"""
import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import matplotlib                                    # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm   # noqa: E402
from matplotlib.patches import Patch, Rectangle      # noqa: E402
from scipy.optimize import curve_fit                 # noqa: E402

# reference palette (dataviz skill): categorical slots 1-2, blue ramp, chrome
PIN = '#2a78d6'          # pinhole (new): slot 1
LEG = '#eb6834'          # legacy (old): slot 2
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#898781'
GRID, AXIS, SURFACE = '#e1e0d9', '#c3c2b7', '#fcfcfb'
NODATA, NODATA_HATCH = '#efeeea', '#b9b8b1'
RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
CMAP = LinearSegmentedColormap.from_list('blue_ramp', RAMP)
CMAP.set_under('#e9f1fc')

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'axes.edgecolor': AXIS, 'axes.labelcolor': INK2, 'axes.titlecolor': INK, 'axes.titlesize': 11,
    'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'axes.labelsize': 9.5,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.labelcolor': INK2, 'ytick.labelcolor': INK2,
    'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5, 'axes.grid': True, 'grid.color': GRID,
    'grid.linewidth': 0.6, 'axes.axisbelow': True, 'font.size': 9, 'legend.frameon': False,
    'legend.fontsize': 8.5, 'axes.spines.top': False, 'axes.spines.right': False,
    'lines.linewidth': 1.6, 'text.color': INK})

QXY, QZ, INVA = r'$Q_{xy}$', r'$Q_z$', r'$\AA^{-1}$'


# ---------------------------------------------------------------- computing

def _steps(c):
    """Bin widths of a centre grid (half-distance to each neighbour)."""
    c = np.asarray(c, float)
    if len(c) < 2:
        return np.ones_like(c)
    return np.abs(np.gradient(c))


def _edges(c):
    c = np.asarray(c, float)
    m = 0.5 * (c[1:] + c[:-1])
    return np.concatenate(([c[0] - (m[0] - c[0])], m, [c[-1] + (c[-1] - m[-1])]))


def integrate(prod, axis, lo, hi):
    """Integral of the Q map along one axis over [lo, hi] of the other.
    axis 0: over Qz -> profile in Qxy; axis 1: over Qxy -> profile in Qz.
    Returns (centres, I, sigma); I per unit of the profile axis (map units
    times Å⁻¹)."""
    qxy, qz, d, e = prod['x'][0], prod['y'][:, 0], prod['data'], prod['err']
    if axis == 0:
        sel = (qz >= lo) & (qz <= hi)
        w = _steps(qz)[sel][:, None]
        dd, ee = d[sel], e[sel]
        return qxy, np.nansum(dd * w, axis=0), np.sqrt(np.nansum((ee * w) ** 2, axis=0))
    sel = (qxy >= lo) & (qxy <= hi)
    w = _steps(qxy)[sel][None, :]
    dd, ee = d[:, sel], e[:, sel]
    return qz, np.nansum(dd * w, axis=1), np.sqrt(np.nansum((ee * w) ** 2, axis=1))


def rebin(xf, yf, sf, xc):
    """A profile of densities (``xf``, ``yf`` ± ``sf``) on another grid
    ``xc``: each fine bin's integral is shared among the bins it overlaps in
    proportion to the overlap, and so is its variance (a fraction f of a
    Poisson count has variance f times the count's), so the errors stay
    those of the counts. Bins not covered to 98 % are NaN."""
    xf, yf, sf = (np.asarray(v, float) for v in (xf, yf, sf))
    ef, ec = _edges(xf), _edges(xc)
    if ef[0] > ef[-1]:
        ef, xf, yf, sf = ef[::-1], xf[::-1], yf[::-1], sf[::-1]
    df = np.abs(np.diff(ef))
    good = np.isfinite(yf) & np.isfinite(sf)
    y, s = np.full(len(xc), np.nan), np.full(len(xc), np.nan)
    for i in range(len(xc)):
        a, b = sorted((ec[i], ec[i + 1]))
        ov = np.clip(np.minimum(ef[1:], b) - np.maximum(ef[:-1], a), 0, None) * good
        if ov.sum() < 0.98 * (b - a):
            continue
        f = ov / df
        y[i] = np.sum(f * yf * df, where=good) / ov.sum()
        s[i] = np.sqrt(np.sum(f * (sf * df) ** 2, where=good)) / ov.sum()
    return y, s


def _gauss(x, a, x0, w, b0, b1):
    return a * np.exp(-0.5 * ((x - x0) / w) ** 2) + b0 + b1 * (x - x0)


def fit_peak(x, y, s, window):
    """Gaussian on a linear background in ``window``; centre, FWHM and their
    errors (Å⁻¹), and σ/I of the bin nearest the centre. None if it fails."""
    sel = (x >= window[0]) & (x <= window[1]) & np.isfinite(y) & (s > 0)
    if sel.sum() < 6:
        return None
    xs, ys, ss = x[sel], y[sel], s[sel]
    b = np.polyfit([xs[0], xs[-1]], [ys[0], ys[-1]], 1)
    i = np.argmax(ys - np.polyval(b, xs))
    p0 = [ys[i] - np.polyval(b, xs[i]), xs[i], (window[1] - window[0]) / 8, np.polyval(b, xs[i]), b[0]]
    try:
        p, c = curve_fit(_gauss, xs, ys, p0=p0, sigma=ss, absolute_sigma=True, maxfev=20000)
    except Exception:
        return None
    if not (window[0] < p[1] < window[1]) or p[0] <= 0:
        return None
    k = 2 * np.sqrt(2 * np.log(2))
    j = int(np.argmin(np.abs(x - p[1])))
    chi2 = float(np.sum(((ys - _gauss(xs, *p)) / ss) ** 2) / max(len(xs) - 5, 1))
    return dict(centre=float(p[1]), centre_err=float(np.sqrt(c[1, 1])), fwhm=float(k * abs(p[2])),
                fwhm_err=float(k * np.sqrt(c[2, 2])), rel_err_at_peak=float(s[j] / y[j]), chi2=chi2,
                params=[float(v) for v in p], window=[float(window[0]), float(window[1])])


def auto_window(x, y, lo, hi, min_half=0.0):
    """Fit window around the largest maximum of the profile above a straight
    line through the ends of [lo, hi] (± 3 half widths)."""
    sel = np.where((x >= lo) & (x <= hi))[0]
    xs, ys = x[sel], y[sel]
    base = np.interp(xs, [xs[0], xs[-1]], [ys[0], ys[-1]])
    r = ys - base
    i = int(np.argmax(r[2:-2])) + 2
    half = r[i] / 2
    a = i
    while a > 0 and r[a] > half:
        a -= 1
    b = i
    while b < len(r) - 1 and r[b] > half:
        b += 1
    hw = max(xs[b] - xs[a], 4 * abs(xs[1] - xs[0])) / 2
    h = max(3 * hw, min_half)
    return [max(lo, xs[i] - h), min(hi, xs[i] + h)]


def legacy_counts(exp, scans, params):
    """Raw counts in the legacy patch's window: ``columns`` around the direct
    beam, rows row_min..row_max, every frame (masked pixels count nothing)."""
    frames, _ = exp.gid_frames(scans)
    tot = 0.0
    h = float(params.columns)
    for f in frames:
        xc = f.centre[0]
        c0, c1 = int(xc - (h - 1) / 2), int(xc + (h - 1) / 2)
        tot += float(np.clip(np.asarray(f.data, float)[params.row_min:params.row_max + 1, c0:c1 + 1], 0, None).sum())
    return tot


def q_of(tt_deg, beta_deg, alpha, wavelength):
    k0 = 2 * np.pi / wavelength
    t, b = np.radians(tt_deg), np.radians(beta_deg)
    qxy = k0 * np.sqrt(np.cos(alpha) ** 2 + np.cos(b) ** 2 - 2 * np.cos(alpha) * np.cos(b) * np.cos(t))
    return qxy, k0 * (np.sin(alpha) + np.sin(b))


def compute(spec, scans, peak=None):
    from lss_core.experiment import Experiment
    from lss_core.gid import GIDParams
    exp = Experiment(spec)
    out = {}
    for name, p in (('legacy', GIDParams(pinhole=False)), ('pinhole', GIDParams())):
        r = exp.gid(scans, params=p)
        out[name] = dict(res=r, q=r.products('Q'))
    leg, pin = out['legacy'], out['pinhole']
    leg['counts'] = legacy_counts(exp, scans, leg['res'].params)
    pin['counts'] = float(sum(lv['counts_used'] for lv in pin['res'].info['levels']))
    qa = [(np.nanmin(m['q']['x']), np.nanmax(m['q']['x'])) for m in (leg, pin)]
    za = [(np.nanmin(m['q']['y']), np.nanmax(m['q']['y'])) for m in (leg, pin)]
    common_qxy = (max(qa[0][0], qa[1][0]), min(qa[0][1], qa[1][1]))
    common_qz = (max(za[0][0], za[1][0]), min(za[0][1], za[1][1]))
    # the lowest Qz level, which neither method rescales: below the first
    # vertical overlap of either method
    vj = [j for m in (leg, pin) for j in m['res'].joins if j['kind'].startswith('vertical')]
    alpha, wl = pin['res'].alpha, pin['res'].wavelength
    low_top = min([q_of(0, j['x_from'], alpha, wl)[1] for j in vj], default=common_qz[1])
    # k: legacy map units -> pinhole map units, over the low level and common Qxy
    tot = {}
    for name, m in (('legacy', leg), ('pinhole', pin)):
        x, y, s = integrate(m['q'], 0, common_qz[0], low_top)
        sel = (x >= common_qxy[0]) & (x <= common_qxy[1])
        tot[name] = float(np.sum(y[sel] * _steps(x)[sel]))
    k = tot['pinhole'] / tot['legacy']
    prof = {}
    for name, m in (('legacy', leg), ('pinhole', pin)):
        f = k if name == 'legacy' else 1.0
        xh, yh, sh = integrate(m['q'], 0, *common_qz)
        xv, yv, sv = integrate(m['q'], 1, *common_qxy)
        prof[name] = dict(h=(xh, yh * f, sh * f), v=(xv, yv * f, sv * f))
    # pinhole on the legacy bins (common ranges only)
    lx = prof['legacy']['h'][0]
    lsel = (lx >= common_qxy[0]) & (lx <= common_qxy[1])
    rh = rebin(*prof['pinhole']['h'], lx)
    rh = (np.where(lsel, rh[0], np.nan), np.where(lsel, rh[1], np.nan))
    lz = prof['legacy']['v'][0]
    zsel = (lz >= common_qz[0]) & (lz <= common_qz[1])
    rv = rebin(*prof['pinhole']['v'], lz)
    rv = (np.where(zsel, rv[0], np.nan), np.where(zsel, rv[1], np.nan))
    prof['pinhole_on_legacy'] = dict(h=(lx, *rh), v=(lz, *rv))
    gain = {}
    for key in ('h', 'v'):
        _, yl, sl = prof['legacy'][key]
        _, yr, sr = prof['pinhole_on_legacy'][key]
        with np.errstate(invalid='ignore', divide='ignore'):
            g = (sl / yl) / (sr / yr)
        g = g[np.isfinite(g)]
        gain[key] = float(np.median(g)) if len(g) else float('nan')
    # peak
    x, y, _ = prof['pinhole']['h']
    if peak == 'none':
        window, peaks = None, {}
    else:
        # at least 5 legacy bins on each side, so that the coarse profile can be fitted too
        window = peak or auto_window(x, y, *common_qxy, min_half=5 * float(np.median(np.abs(np.diff(lx)))))
        peaks = {n: fit_peak(*prof[n]['h'], window) for n in ('legacy', 'pinhole', 'pinhole_on_legacy')}
    return dict(exp=exp, scans=scans, legacy=leg, pinhole=pin, k=k, gain=gain, common_qxy=common_qxy,
                common_qz=common_qz, low_top=low_top, prof=prof, peaks=peaks, window=window,
                alpha=alpha, wavelength=wl)


# ---------------------------------------------------------------- drawing

def _nodata_background(ax, xlim, ylim):
    ax.add_patch(Rectangle((xlim[0], ylim[0]), xlim[1] - xlim[0], ylim[1] - ylim[0], facecolor=NODATA,
                           edgecolor=NODATA_HATCH, hatch='////', linewidth=0, zorder=0))


def _join_marks(ax, C, m, color_txt=INK):
    """Join overlaps of one method drawn on its map: the vertical (Qz)
    overlap as a band between two lines, the 2θ overlaps as two curves each
    over the Qz range of their level."""
    r = m['res']
    alpha, wl = C['alpha'], C['wavelength']
    vj = [j for j in r.joins if j['kind'].startswith('vertical')]
    hj = [j for j in r.joins if j['kind'].startswith('horizontal')]
    qzmin, qzmax = np.nanmin(m['q']['y']), np.nanmax(m['q']['y'])
    xl = ax.get_xlim()
    for j in vj:
        z0, z1 = q_of(0, j['x_from'], alpha, wl)[1], q_of(0, j['x_to'], alpha, wl)[1]
        for z in (z0, z1):
            ax.axhline(z, color=INK, lw=0.6, alpha=0.7, zorder=4)
        ax.text(xl[1] - 0.01 * (xl[1] - xl[0]), z1, 'Qz join overlap', ha='right', va='bottom',
                fontsize=7.5, color=color_txt, zorder=6,
                bbox=dict(boxstyle='round,pad=0.15', fc=SURFACE, ec='none', alpha=0.8))
    levels = [lv[0] for lv in r.levels]
    for j in hj:
        k = levels.index(j['label']) if j['label'] in levels else 0
        # Qz extent of that level: below the end of the first vertical overlap, or above its start
        if vj:
            if k == 0:
                zr = (qzmin, q_of(0, vj[0]['x_to'], alpha, wl)[1])
            else:
                zr = (q_of(0, vj[min(k, len(vj)) - 1]['x_from'], alpha, wl)[1], qzmax)
        else:
            zr = (qzmin, qzmax)
        zz = np.linspace(*zr, 60)
        bb = np.degrees(np.arcsin(np.clip(zz / (2 * np.pi / wl) - np.sin(alpha), -1, 1)))
        for t in (j['x_from'], j['x_to']):
            ax.plot(q_of(t, bb, alpha, wl)[0], zz, color=INK, lw=0.6, alpha=0.7, zorder=4)
    if hj:
        j = hj[0]
        zz = np.nanmin(m['q']['y']) + 0.03 * (qzmax - qzmin)
        ax.text(q_of(j['x_to'], 0, alpha, wl)[0], zz, ' 2θ join overlap', ha='left', va='bottom',
                fontsize=7.5, zorder=6, bbox=dict(boxstyle='round,pad=0.15', fc=SURFACE, ec='none', alpha=0.8))


def _edge_copies(ax, C):
    """Legacy (P33): the vertical join resamples each higher level onto the
    lowest level's 2θ grid; outside its own 2θ range it copies its edge
    column. Outline that region."""
    r = C['legacy']['res']
    alpha, wl = C['alpha'], C['wavelength']
    vj = [j for j in r.joins if j['kind'].startswith('vertical')]
    if not vj or len(r.levels) < 2:
        return False
    t_all = (r.levels[0][3], r.levels[0][4])
    drawn = False
    for lv, j in zip(r.levels[1:], vj):
        bmax = float(np.nanmax(r.y))
        for a, b in ((t_all[0], lv[3]), (lv[4], t_all[1])):
            if b - a <= 1e-6:
                continue
            bb = np.linspace(j['x_from'], bmax, 60)
            left = q_of(a, bb, alpha, wl)
            right = q_of(b, bb, alpha, wl)
            xs = np.concatenate((left[0], right[0][::-1], left[0][:1]))
            zs = np.concatenate((left[1], right[1][::-1], left[1][:1]))
            ax.fill(xs, zs, facecolor='none', edgecolor=(0.04, 0.04, 0.04, 0.55), hatch='\\\\', lw=1.2, zorder=5)
            cx, cz = np.mean(xs), np.mean(zs)
            ax.text(cx, cz, 'edge copies of\n%s (P33)' % ', '.join('S%d' % s for s in lv[1]), ha='center',
                    va='center', fontsize=8, zorder=6,
                    bbox=dict(boxstyle='round,pad=0.25', fc=SURFACE, ec=AXIS, lw=0.6))
            drawn = True
    return drawn


def fig_maps(C, title, path):
    leg, pin, k = C['legacy'], C['pinhole'], C['k']
    xs = [m['q']['x'] for m in (leg, pin)]
    ys = [m['q']['y'] for m in (leg, pin)]
    ds = [leg['q']['data'] * k, pin['q']['data']]
    xlim = (min(np.nanmin(x) for x in xs), max(np.nanmax(x) for x in xs))
    ylim = (min(np.nanmin(y) for y in ys), max(np.nanmax(y) for y in ys))
    pad = 0.015 * (xlim[1] - xlim[0])
    xlim = (xlim[0] - pad, xlim[1] + pad)
    pos = np.concatenate([d[np.isfinite(d) & (d > 0)] for d in ds])
    vmin, vmax = np.percentile(pos, 10), np.percentile(pos, 99.8)
    norm = LogNorm(vmin=vmin, vmax=vmax)
    fig, axs = plt.subplots(1, 2, figsize=(13.5, 6.4), sharex=True, sharey=True,
                            gridspec_kw=dict(wspace=0.06))
    fig.subplots_adjust(left=0.06, right=0.9, top=0.84, bottom=0.1)
    names = ('Legacy: 3 columns at the direct beam', 'Pinhole: every usable column, exact angles')
    for ax, m, d, name, lab in zip(axs, (leg, pin), ds, names, ('legacy', 'pinhole')):
        _nodata_background(ax, xlim, ylim)
        x, y = m['q']['x'], m['q']['y']
        nonpos = np.isfinite(d) & (d <= 0)
        dp = np.where(nonpos, vmin * 1e-3, d)
        im = ax.pcolormesh(x, y, dp, cmap=CMAP, norm=norm, shading='nearest', rasterized=True, zorder=1)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.grid(False)
        ax.set_title(name, fontsize=10.5)
        ax.set_xlabel('%s (%s)' % (QXY, INVA))
        _join_marks(ax, C, m)
        nbin = d.shape
        nan = int(np.sum(~np.isfinite(d)))
        q = m['q']['x'][0]
        txt = ['%d × %d bins (%s step %.4f %s)' % (nbin[1], nbin[0], QXY, np.median(np.abs(np.diff(q))), INVA),
               '%.3g counts used' % m['counts']]
        if lab == 'legacy':
            txt.append('map × k = %.3g (to pinhole units)' % k)
            txt.append('β per row, one 2θ per frame')
        else:
            txt.append('β, 2θ per pixel (P38 fixed)')
        if nan:
            txt.append('%d cells without data (hatched)' % nan)
        if nonpos.any():
            txt.append('%d cells ≤ 0 (palest blue)' % int(nonpos.sum()))
        ax.text(0.015, 0.985, '\n'.join(txt), transform=ax.transAxes, va='top', ha='left', fontsize=8,
                color=INK, zorder=7, bbox=dict(boxstyle='round,pad=0.35', fc=SURFACE, ec=AXIS, lw=0.6, alpha=0.92))
    axs[0].set_ylabel('%s (%s)' % (QZ, INVA))
    r = pin['res']
    if len(r.levels) > 1:
        own = (min(lv[3] for lv in r.levels), max(lv[4] for lv in r.levels))
        got = (float(np.nanmin(r.x)), float(np.nanmax(r.x)))
        if got[0] - own[0] > 0.5 or own[1] - got[1] > 0.5:
            qx = np.nanmax(pin['q']['x'])
            axs[1].text(0.5 * (qx + xlim[1]), ylim[0] + 0.3 * (ylim[1] - ylim[0]),
                        'pinhole keeps the 2θ\nrange every Qz level\nhas (IDL rule, F62):\n%.1f–%.1f° of %.1f–%.1f°'
                        % (got[0], got[1], own[0], own[1]), ha='center', va='center', fontsize=8, zorder=6,
                        bbox=dict(boxstyle='round,pad=0.3', fc=SURFACE, ec=AXIS, lw=0.6))
    _edge_copies(axs[0], C)
    cax = fig.add_axes([0.915, 0.1, 0.014, 0.74])
    cb = fig.colorbar(im, cax=cax, extend='both')
    cb.set_label('intensity (pinhole map units, log)', color=INK2)
    cb.outline.set_edgecolor(AXIS)
    cb.ax.tick_params(colors=MUTED, labelcolor=INK2, labelsize=8)
    fig.suptitle(title, x=0.06, ha='left', fontsize=13, fontweight='bold', color=INK, y=0.975)
    fig.text(0.06, 0.915, 'Same axes, same colour scale. Hatched: no data. Lines: overlaps where the '
             'join factors were fitted.', fontsize=9, color=INK2)
    fig.legend(handles=[Patch(facecolor=NODATA, edgecolor=NODATA_HATCH, hatch='////', label='no data')],
               loc='upper right', bbox_to_anchor=(0.9, 0.935), fontsize=8.5)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _band(ax, x, y, s, color, label, marker=None):
    ok = np.isfinite(y)
    ax.fill_between(x[ok], (y - s)[ok], (y + s)[ok], color=color, alpha=0.22, lw=0, zorder=2)
    ax.plot(x[ok], y[ok], color=color, lw=1.3 if not marker else 1.0, label=label, zorder=3,
            marker=marker, ms=3.5 if marker else 0)


def fig_profiles(C, title, path):
    P, k = C['prof'], C['k']
    fig, axs = plt.subplots(3, 2, figsize=(13.5, 10.5), sharex='col',
                            gridspec_kw=dict(height_ratios=[2.2, 1, 1.4], hspace=0.12, wspace=0.16))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.87, bottom=0.06)
    for col, key, xl in ((0, 'h', '%s (%s)' % (QXY, INVA)), (1, 'v', '%s (%s)' % (QZ, INVA))):
        a0, a1, a2 = axs[:, col]
        xL, yL, sL = P['legacy'][key]
        xP, yP, sP = P['pinhole'][key]
        _band(a0, xL, yL, sL, LEG, 'legacy × k', marker='o')
        _band(a0, xP, yP, sP, PIN, 'pinhole')
        if key == 'v':
            a0.set_yscale('log')
            pos = np.concatenate([yL[yL > 0], yP[yP > 0]])
            a0.set_ylim(np.percentile(pos, 0.5) / 2, pos.max() * 2)
        a0.set_ylabel('∫ I d%s' % ('Qz' if key == 'h' else 'Qxy'))
        rng = C['common_qz'] if key == 'h' else C['common_qxy']
        a0.set_title('%s profile, over %s %.3f to %.3f Å⁻¹ (common to both)'
                     % ('Qxy' if key == 'h' else 'Qz', 'Qz' if key == 'h' else 'Qxy', rng[0], rng[1]), fontsize=10)
        if key == 'h':
            top = np.nanmax(np.concatenate([yL + sL, yP + sP]))
            bot = np.nanmin(np.concatenate([yL - sL, yP - sP]))
            a0.set_ylim(bot - 0.05 * (top - bot), top + 0.45 * (top - bot))
        # ratio on the legacy bins, or on ~80 coarser bins when the legacy
        # grid is fine (Qz), so that the trend is readable
        xr, yr, sr = P['pinhole_on_legacy'][key]
        rng_c = C['common_qxy'] if key == 'h' else C['common_qz']
        if len(xL) > 120:
            xg = np.linspace(rng_c[0], rng_c[1], 81)
            xg = 0.5 * (xg[1:] + xg[:-1])
            gp, gps = rebin(xP, yP, sP, xg)
            gl, gls = rebin(xL, yL, sL, xg)
        else:
            xg, gp, gps, gl, gls = xr, yr, sr, yL, sL
        with np.errstate(invalid='ignore', divide='ignore'):
            ratio = gp / gl
            rerr = ratio * np.sqrt((gps / gp) ** 2 + (gls / gl) ** 2)
        ok = np.isfinite(ratio)
        xr_plot = xg
        a1.axhline(1, color=AXIS, lw=1, zorder=1)
        a1.errorbar(xr_plot[ok], ratio[ok], rerr[ok], fmt='o', ms=3.5, color=INK2, ecolor=MUTED, elinewidth=0.8,
                    capsize=0, zorder=3)
        if ok.any():
            lo, hi = np.nanpercentile(ratio[ok], [5, 95])
            spanr = max(hi - lo, 0.1)
            a1.set_ylim(lo - 0.3 * spanr, hi + 0.3 * spanr)
            off = int(np.sum((ratio[ok] < lo - 0.3 * spanr) | (ratio[ok] > hi + 0.3 * spanr)))
            if off:
                a1.text(0.99, 0.95, '%d point%s off scale' % (off, '' if off == 1 else 's'), transform=a1.transAxes,
                        ha='right', va='top', fontsize=7.5, color=MUTED)
        a1.set_ylabel('pinhole /\n(k × legacy)')
        # relative errors
        with np.errstate(invalid='ignore', divide='ignore'):
            a2.plot(xL, sL / yL, 'o-', color=LEG, ms=3.5, lw=1.0)
            a2.plot(xP, sP / yP, '-', color=PIN, lw=1.0)
            if len(xP) > 1.5 * len(xL):                    # only when the pinhole bins are finer
                a2.plot(xr, sr / yr, 's', color=PIN, ms=4.5, mfc=SURFACE, mew=1.3)
            g = (sL / yL) / (sr / yr)
        a2.set_yscale('log')
        a2.set_ylabel('σ / I per bin')
        a2.set_xlabel(xl)
        gg = g[np.isfinite(g)]
        a2.set_title('Relative error per bin' + ('; on equal bins legacy / pinhole = %.2f (median), ≈ %.0f× the counts'
                     % (np.median(gg), np.median(gg) ** 2) if len(gg) else ''), fontsize=9.5)
        # joins: vertical overlap in Qz
        if key == 'v':
            jl = []
            for m, c, lab in ((C['legacy'], LEG, 'legacy'), (C['pinhole'], PIN, 'pinhole')):
                for j in m['res'].joins:
                    if j['kind'].startswith('vertical'):
                        z0 = q_of(0, j['x_from'], C['alpha'], C['wavelength'])[1]
                        z1 = q_of(0, j['x_to'], C['alpha'], C['wavelength'])[1]
                        for ax in (a0, a1):
                            ax.axvspan(z0, z1, color=c, alpha=0.08, lw=0, zorder=0)
                        jl.append('%-8s %.3f–%.3f   × %.3f ± %.3f' % (lab, z0, z1, j['factor'], j['error']))
            if jl:
                a0.text(0.985, 0.04, 'Qz join (shaded), overlap Qz (Å⁻¹), factor on the higher level:\n'
                        + '\n'.join(jl), transform=a0.transAxes, ha='right', va='bottom', fontsize=7.8,
                        family='monospace', color=INK,
                        bbox=dict(boxstyle='round,pad=0.3', fc=SURFACE, ec=AXIS, lw=0.6, alpha=0.92))
    # peak annotation on the Qxy profile
    a0 = axs[0, 0]
    pk = C['peaks']
    lines = []
    for n, lab in (('legacy', 'legacy'), ('pinhole', 'pinhole'), ('pinhole_on_legacy', 'pinhole, legacy bins')):
        p = pk.get(n)
        if p:
            lines.append('%-22s %s %.4f ± %.4f   FWHM %.4f ± %.4f   σ/I %.2f %%'
                         % (lab, QXY, p['centre'], p['centre_err'], p['fwhm'], p['fwhm_err'], 100 * p['rel_err_at_peak']))
    if lines and C['window']:
        a0.axvspan(*C['window'], color=MUTED, alpha=0.06, lw=0, zorder=0)
        a0.text(0.015, 0.97, 'Largest maximum: Gaussian + line in the shaded window (Å⁻¹)\n' + '\n'.join(lines),
                transform=a0.transAxes, va='top', fontsize=7.8, family='monospace', color=INK,
                bbox=dict(boxstyle='round,pad=0.3', fc=SURFACE, ec=AXIS, lw=0.6, alpha=0.92))
    fig.suptitle(title, x=0.07, ha='left', fontsize=13, fontweight='bold', color=INK, y=0.975)
    fig.text(0.07, 0.935, 'Legacy scaled by k = %.3g, fitted over the lowest Qz level (Qz < %.3f Å⁻¹), '
             'which neither method rescales. Bands and bars: ±1σ.' % (k, C['low_top']), fontsize=9, color=INK2)
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=LEG, marker='o', ms=4, lw=1.2, label='legacy (× k), its bins'),
                        Line2D([], [], color=PIN, lw=1.6, label='pinhole, its bins'),
                        Line2D([], [], color=PIN, marker='s', ms=5, mfc=SURFACE, lw=0,
                               label='pinhole summed to the legacy bins'),
                        Line2D([], [], color=INK2, marker='o', ms=4, lw=0, label='ratio pinhole / (k × legacy), common bins')],
               loc='upper left', bbox_to_anchor=(0.07, 0.925), ncol=4, fontsize=8.5)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _join_key(j, idx):
    return ('2θ join, %s' % j['label']) if j['kind'].startswith('horizontal') else 'Qz join (levels)'


def summary_rows(C):
    leg, pin = C['legacy'], C['pinhole']
    rows = []

    def both(name, f):
        rows.append((name, f(leg, 'legacy'), f(pin, 'pinhole')))
    both('Q map bins (Qxy × Qz)', lambda m, n: '%d × %d' % (m['q']['data'].shape[1], m['q']['data'].shape[0]))
    both('Qxy range (Å⁻¹)', lambda m, n: '%.3f – %.3f' % (np.nanmin(m['q']['x']), np.nanmax(m['q']['x'])))
    both('Qxy step (Å⁻¹)', lambda m, n: '%.4f' % np.median(np.abs(np.diff(m['q']['x'][0]))))
    both('Qz range (Å⁻¹)', lambda m, n: '%.3f – %.3f' % (np.nanmin(m['q']['y']), np.nanmax(m['q']['y'])))
    both('2θ range (°)', lambda m, n: '%.2f – %.2f' % (np.nanmin(m['res'].x), np.nanmax(m['res'].x)))
    both('raw counts used', lambda m, n: '%.3g' % m['counts'])
    pk = C['peaks']
    if C['window']:
        rows.append(('peak fit window, Qxy (Å⁻¹)', *['%.3f – %.3f' % tuple(C['window'])] * 2))
    for key, lab in (('centre', 'peak Qxy (Å⁻¹)'), ('fwhm', 'peak FWHM (Å⁻¹)')) if C['window'] else ():
        rows.append((lab, *[('%.4f ± %.4f' % (pk[n][key], pk[n][key + '_err'])) if pk.get(n) else '—'
                            for n in ('legacy', 'pinhole')]))
    def pct(p):
        return ('%.2f %%' % (100 * p['rel_err_at_peak'])) if p and np.isfinite(p['rel_err_at_peak']) else '—'
    if C['window']:
        rows.append(('σ/I at the peak, own bins', pct(pk.get('legacy')), pct(pk.get('pinhole'))))
        rows.append(('σ/I at the peak, legacy bins', pct(pk.get('legacy')), pct(pk.get('pinhole_on_legacy'))))
    seen = {}
    for m in (leg, pin):
        for i, j in enumerate(m['res'].joins):
            key = _join_key(j, i)
            seen.setdefault(key, None)
    for key in seen:
        cells = []
        for m in (leg, pin):
            js = [j for i, j in enumerate(m['res'].joins) if _join_key(j, i) == key]
            cells.append('; '.join('%.3f ± %.3f (χ² %.2f)' % (j['factor'], j['error'], j['chi2']) for j in js) or '—')
        rows.append((key + ' factor', *cells))
    rows.append(('scale k (legacy → pinhole)', '%.3g' % C['k'], '1'))
    return rows


def fig_joins(C, title, path):
    leg, pin = C['legacy'], C['pinhole']
    keys = []
    for m in (leg, pin):
        for i, j in enumerate(m['res'].joins):
            if _join_key(j, i) not in keys:
                keys.append(_join_key(j, i))
    rows = summary_rows(C)
    fig = plt.figure(figsize=(13.5, 9.0 if keys else 6.2))
    if keys:
        gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.2], width_ratios=[1, 0.8, 1.25], hspace=0.3, wspace=0.42,
                              left=0.1, right=0.98, top=0.86, bottom=0.02)
        a_tt, a_b, a_f = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[0, 2])
        a_tab = fig.add_subplot(gs[1, :])
        # overlap ranges
        for ax, kind, xl in ((a_tt, 'horizontal', '2θ (°)'), (a_b, 'vertical', 'β (°)')):
            ylabels = []
            yy = 0
            for key in keys:
                for m, c, lab in ((leg, LEG, 'legacy'), (pin, PIN, 'pinhole')):
                    js = [j for i, j in enumerate(m['res'].joins) if _join_key(j, i) == key and j['kind'].startswith(kind)]
                    for j in js:
                        ax.plot([j['x_from'], j['x_to']], [yy, yy], color=c, lw=6, solid_capstyle='butt')
                        ax.text(j['x_to'], yy, '  %d pts' % j['points'], va='center', fontsize=8, color=INK2)
                        short = key.replace('2θ join, ', '') if kind == 'horizontal' else ''
                        ylabels.append((yy, ('%s · %s' % (short, lab)) if short else lab))
                        yy -= 1
            if ylabels:
                ax.set_yticks([y for y, _ in ylabels])
                ax.set_yticklabels([l for _, l in ylabels], fontsize=8)
                ax.set_ylim(yy + 0.4, 0.6)
                x0, x1 = ax.get_xlim()
                ax.set_xlim(x0, x1 + 0.25 * (x1 - x0))
            else:
                ax.axis('off')
                ax.text(0.5, 0.5, 'no join of this kind\n(one scan per Qz level)', transform=ax.transAxes,
                        ha='center', va='center', color=MUTED)
            ax.set_xlabel(xl)
            ax.grid(axis='y', visible=False)
        a_tt.set_title('Where: 2θ overlaps', fontsize=10)
        a_b.set_title('Where: β overlap of the Qz join', fontsize=10)
        # factors
        for yi, key in enumerate(keys):
            for m, c, lab, dy in ((leg, LEG, 'legacy', 0.15), (pin, PIN, 'pinhole', -0.15)):
                js = [j for i, j in enumerate(m['res'].joins) if _join_key(j, i) == key]
                for j in js:
                    a_f.errorbar(j['factor'], -yi + dy, xerr=j['error'], fmt='o', ms=6, color=c, ecolor=c,
                                 elinewidth=1.6, capsize=3, label=lab)
                    a_f.text(j['factor'] + j['error'], -yi + dy, '  %.3f ± %.3f, χ²/dof %.2f'
                             % (j['factor'], j['error'], j['chi2']), va='center', fontsize=7.8, color=INK2)
        a_f.set_yticks([-i for i in range(len(keys))])
        a_f.set_yticklabels(keys, fontsize=8.5)
        a_f.set_ylim(-len(keys) + 0.4, 0.6)
        a_f.axvline(1, color=AXIS, lw=1, zorder=0)
        x0, x1 = a_f.get_xlim()
        a_f.set_xlim(x0, x1 + 0.9 * (x1 - x0))
        a_f.set_xlabel('fitted factor applied to the later scan / level')
        a_f.grid(axis='y', visible=False)
        h, lab = a_f.get_legend_handles_labels()
        u = dict(zip(lab, h))
        a_f.legend(u.values(), u.keys(), loc='upper right')
        a_f.set_title('Factors ± error', fontsize=10)
    else:
        gs = fig.add_gridspec(2, 1, height_ratios=[0.1, 1], left=0.07, right=0.98, top=0.84, bottom=0.02)
        fig.add_subplot(gs[0]).axis('off')
        fig.text(0.07, 0.8, 'One scan at one Qz level: nothing is joined.', fontsize=10, color=INK2)
        a_tab = fig.add_subplot(gs[1])
    a_tab.axis('off')
    t = a_tab.table(cellText=[r[1:] for r in rows], rowLabels=[r[0] for r in rows],
                    colLabels=['legacy (3 columns)', 'pinhole (exact)'], loc='upper center', cellLoc='center',
                    colWidths=[0.33, 0.33])
    t.auto_set_font_size(False)
    t.set_fontsize(8.5)
    t.scale(1, 1.32)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_text_props(weight='bold', color=INK)
            cell.set_facecolor('#f3f2ee')
        elif c == -1:
            cell.set_text_props(color=INK2, ha='right')
        else:
            cell.set_facecolor(SURFACE)
    fig.suptitle(title, x=0.07, ha='left', fontsize=13, fontweight='bold', color=INK, y=0.975)
    fig.text(0.07, 0.94, 'Each factor multiplies the later scan (2θ join) or the higher Qz level (Qz join); '
             'error from the fit, χ²/dof of the ratio over the overlap.\nThe two methods normalise the raw levels '
             'differently, so their factors need not agree; compare the joined profiles (profiles figure, ratio panels).',
             fontsize=9, color=INK2, va='top')
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _check_private(spec, out):
    s = os.path.abspath(spec)
    if any(os.path.join(ROOT, 'sample_data', p) in s for p in ('private', 'bu')):
        o = os.path.abspath(out)
        if o == ROOT or o.startswith(ROOT + os.sep):
            sys.exit('Private data: --out must be outside the repository (%s).' % ROOT)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--spec', default=os.path.join('sample_data', 'NX_school', '2026sep', '20260923'))
    ap.add_argument('--scans', default='11', help='comma-separated scan numbers')
    ap.add_argument('--out', required=True, help='output folder')
    ap.add_argument('--label', default=None, help='file name prefix (default: nx for NX school, private otherwise)')
    ap.add_argument('--peak', default=None, help='Qxy fit window "lo,hi" (1/Å), or "none"; default: around the largest maximum')
    ap.add_argument('--title', default=None, help='data set name in the figure titles')
    ap.add_argument('--note', default='', help='short caveat appended to the titles, in brackets')
    a = ap.parse_args(argv)
    _check_private(a.spec, a.out)
    os.makedirs(a.out, exist_ok=True)
    scans = [int(s) for s in a.scans.split(',')]
    label = a.label or ('nx' if 'NX_school' in a.spec else 'private')
    peak = None if not a.peak else 'none' if a.peak == 'none' else [float(v) for v in a.peak.split(',')]
    C = compute(a.spec, scans, peak)
    consecutive = len(scans) > 2 and scans == list(range(scans[0], scans[-1] + 1))
    tag = '%s_S%s' % (label, ('%d-%d' % (scans[0], scans[-1])) if consecutive else '+'.join(str(s) for s in scans))
    name = a.title or ('NX school' if label == 'nx' else 'private data')
    stitle = '%s, scan%s %s' % (name, 's' if len(scans) > 1 else '', ' + '.join(str(s) for s in scans))
    if a.note:
        stitle += ' (%s)' % a.note
    paths = dict(maps=os.path.join(a.out, tag + '_maps.png'), profiles=os.path.join(a.out, tag + '_profiles.png'),
                 joins=os.path.join(a.out, tag + '_joins.png'))
    fig_maps(C, 'GID map before/after: %s' % stitle, paths['maps'])
    fig_profiles(C, 'GID profiles before/after: %s' % stitle, paths['profiles'])
    fig_joins(C, 'GID joins before/after: %s' % stitle, paths['joins'])
    summ = dict(spec=a.spec, scans=scans, k=C['k'],
                sigma_ratio_equal_bins_median=dict(qxy_profile=C['gain']['h'], qz_profile=C['gain']['v']), common_qxy=C['common_qxy'], common_qz=C['common_qz'],
                low_level_top_qz=C['low_top'], peaks=C['peaks'],
                counts=dict(legacy=C['legacy']['counts'], pinhole=C['pinhole']['counts']),
                joins=dict(legacy=C['legacy']['res'].joins, pinhole=C['pinhole']['res'].joins),
                levels=dict(legacy=[list(map(str, l)) for l in C['legacy']['res'].levels],
                            pinhole=[list(map(str, l)) for l in C['pinhole']['res'].levels]),
                table=summary_rows(C), command='python tests/tools/gid_compare_figures.py ' + ' '.join(
                    sys.argv[1:] if argv is None else argv))
    with open(os.path.join(a.out, tag + '_summary.json'), 'w') as f:
        json.dump(summ, f, indent=1, default=float)
    for p in paths.values():
        print(p)


if __name__ == '__main__':
    main()
