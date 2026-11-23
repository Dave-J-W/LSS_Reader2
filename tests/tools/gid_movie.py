"""A GID movie on one 2θ axis: the real peaks stand still, the junk moves.

docs/gui/image_display.md M7 (owner, 2026-11-23).

    python tests/tools/gid_movie.py                        # NX school scan 11 -> docs/figures/gid_movie/
    python tests/tools/gid_movie.py --pixels --out DIR     # also the movie on detector pixels
    python tests/tools/gid_movie.py --window 15.5,18 --beta=-0.5,3 --out DIR    # zoomed on the peak, in angle
    python tests/tools/gid_movie.py --spec PATH --scans 386 387 --out DIR       # private data: --out outside docs/

Why (docs/physics_notes.md, 2026-11-23): a Bragg rod scatters at a fixed
2θ (fixed Qxy), so as the detector arm steps its image moves across the
pixels with the arm; anything fixed relative to the detector or the slits
(hot pixels, stray light, window or slit scattering) stays on the same
pixels and so moves in 2θ. Drawn on one 2θ axis with the zoom held in
angle, the real peaks stand still and the junk moves; on detector pixels
it is the other way round.

Drawn, every frame with the same axes limits, the same colour scale and
the same colour mode (F69: nothing changes while the frames play):

- ``movie_<scans>.gif``: each frame's counts per pixel per monitor count on
  one fixed (2θ, β) window; light grey where the frame has no pixel. The
  dotted lines are the frame's usable columns (S5 ∩ footprint), which move
  with the arm; the triangle on the top edge is the peak's 2θ (``--peak``).
- ``pixels_<scans>.gif`` (``--pixels``): the same frames on detector
  columns and rows, the same colour scale; the triangle marks the column
  that sees the peak's 2θ in that frame.
- ``contact_<scans>.png``: up to 8 evenly spaced frames of the movie
  stacked on one 2θ axis (left: the peak a vertical line) and the same
  frames on detector pixels (right: the peak walks across the columns).
- ``peak_<scans>.csv``: per frame, the brightest column near the peak (rows
  of β −0.1…2°, usable columns, peak ± 0.3°), its 2θ, its counts against
  the median of that window, and the single-frame Gaussian centre where
  lss_core fits one. Printed: the spread of the peak's 2θ over the frames
  that hold it, against the travel of its column.

Computed by lss_core, only drawn here: the frame records and monitors
(``Experiment.frames``), the images (``images.read_pilatus``, through
tests/tools/pinhole_frames.py, which builds each frame's ``FrameGeometry``
from the SPEC header as the window does), every pixel's exact (2θ, β)
(``pinhole.pixel_angles``), the binning onto the common grid as
I = ΣN/ΣW with W the monitor (``pinhole.bin_counts_2d``; bins one column
wide in 2θ, ``--rows`` rows high in β), the usable columns
(``pinhole.frame_columns``), the peak's 2θ when not given
(``pinhole.strongest_peak``) and the single-frame fits
(``pinhole.single_frame_peaks``). Chosen here: the window (default the
scans' whole 2θ and β range), the colour limits (percentiles of all the
scans' binned frames together, so ``--every`` keeps the colours), the
brightest-column track (a check, not a reduction) and the drawing. Raw
frames per monitor count: no footprint, polarisation or column-response
correction. Pixels below zero (flagged by the detector) count nothing.

Deterministic: no dates or revisions are drawn, the sizes are fixed by the
window, and a rerun on unchanged code writes identical files. Run from the
repository root. Private data: give an --out outside docs/ (e.g. under
sample_data/private/figures/); the tool refuses docs/ for a --spec other
than NX. A window or β range starting with a minus sign needs "=":
``--beta=-0.5,3``.
"""
import argparse
import csv
import math
import os
import sys
import time
from dataclasses import dataclass, replace

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))
import matplotlib                                      # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                        # noqa: E402
from matplotlib.colors import LogNorm, Normalize       # noqa: E402
from matplotlib.ticker import FormatStrFormatter      # noqa: E402
from matplotlib.transforms import blended_transform_factory  # noqa: E402
from PIL import Image                                  # noqa: E402

from lss_core import pinhole as ph                     # noqa: E402
from lss_core.experiment import Experiment             # noqa: E402
from pinhole_frames import frames_for                  # noqa: E402

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
OUT = os.path.join('docs', 'figures', 'gid_movie')
BETA_BAND = (-0.1, 2.0)        # rows of the peak track, degrees (as pinhole.calibrate_distance)
HALF_DEG = 0.3                 # half width of the peak window, degrees
MIN_COLUMNS = 8                # usable columns inside the peak window for a frame to hold the peak
MIN_SIGNIFICANCE = 8.0         # (brightest − median) / √median of the window, in counting errors
SHEET_FRAMES = 8
CMAP_LEVELS = 64               # discrete colour levels: one GIF palette for every frame
PERCENTILES = (5.0, 99.9)      # colour limits (log: low, high; linear: 0, high)
SCALE = 1e6                    # drawn per 10⁶ monitor counts
UNIT = 'counts / pixel / 10⁶ monitor'
NODATA = '#d9d9d9'
GUIDE = '#ffffff'
MARK = '#d0481e'
PLOT_W, PLOT_H = 600, 380      # target size of the movie's data area, screen pixels
DPI = 100


@dataclass
class Shot:
    """One frame of the movie: its record, its pinhole frame and its angles."""
    scan: int
    point: int
    dth: float                 # Det_Th, degrees
    frame: object              # lss_core.pinhole.PinholeFrame
    tt: np.ndarray             # 2θ of every pixel, degrees (rows, cols)
    beta: np.ndarray           # β of every pixel, degrees
    cols: np.ndarray           # usable columns (S5 ∩ footprint)


def pair(text):
    """'a,b' -> (a, b) as floats, a < b."""
    try:
        a, b = (float(x) for x in text.split(','))
    except ValueError:
        raise argparse.ArgumentTypeError('give two numbers, "low,high"')
    if not a < b:
        raise argparse.ArgumentTypeError('low must be below high')
    return a, b


def load(spec, scans, pinhole_mm=0.0):
    """The frames of ``scans`` as Shots, in the reader's list order."""
    recs = Experiment(spec).frames(scans)
    frames = frames_for(spec, scans)
    if len(recs) != len(frames):
        raise RuntimeError('frame records and pinhole frames differ')
    out = []
    for r, f in zip(recs, frames):
        if pinhole_mm > 0:
            f = replace(f, geom=replace(f.geom, d_pinhole=float(pinhole_mm)),
                        areainfo=tuple(f.areainfo[:5]) + (float(pinhole_mm),))
        nr, nc = f.counts.shape
        tt, bb = ph.pixel_angles(f.geom, np.arange(nr), np.arange(nc))
        out.append(Shot(r.scan, r.index, math.degrees(f.geom.dth), f, np.degrees(tt), np.degrees(bb),
                        ph.frame_columns(f, nc)))
    if not out:
        raise SystemExit('no Pilatus frames in scans %s' % scans)
    return out


def counts_weights(f):
    """Counts and weights (the monitor) of every pixel; flagged pixels (< 0) count nothing."""
    good = f.counts >= 0
    return np.where(good, f.counts, 0.0), np.where(good, float(f.monitor), 0.0)


def grid(shots, window, beta_window, rows_per_bin):
    """Bin edges (2θ, β; degrees): one column wide in 2θ (p/D_p, as
    pinhole.shared_edges), ``rows_per_bin`` rows high in β."""
    g = shots[0].frame.geom
    step = math.degrees(ph.PIXEL_MM / g.d_pinhole)
    bstep = rows_per_bin * math.degrees(ph.PIXEL_MM / ph.vertical_distance(g))
    lo, hi = window or (min(s.tt.min() for s in shots) - step / 2, max(s.tt.max() for s in shots) + step / 2)
    blo, bhi = beta_window or (min(s.beta.min() for s in shots) - bstep / 2,
                               max(s.beta.max() for s in shots) + bstep / 2)
    edges = lo + step * np.arange(int(math.ceil((hi - lo) / step - 1e-9)) + 1)
    bedges = blo + bstep * np.arange(int(math.ceil((bhi - blo) / bstep - 1e-9)) + 1)
    return edges, bedges


def angle_image(s, edges, bedges):
    """The frame on the common grid, I = ΣN/ΣW (lss_core), β up the rows."""
    n, w = counts_weights(s.frame)
    return ph.bin_counts_2d(s.tt, s.beta, n, w, edges, bedges)[0].T * SCALE


def pixel_image(s, rows_per_bin):
    """The frame on detector pixels, ``rows_per_bin`` rows summed as ΣN/ΣW."""
    n, w = counts_weights(s.frame)
    starts = np.arange(0, n.shape[0], rows_per_bin)
    sn, sw = np.add.reduceat(n, starts, axis=0), np.add.reduceat(w, starts, axis=0)
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(sw > 0, sn / sw, np.nan) * SCALE


def colour_norm(images, log):
    """One colour scale for every frame, from all of them together."""
    v = np.concatenate([a[np.isfinite(a)].ravel() for a in images])
    hi = float(np.percentile(v, PERCENTILES[1]))
    if not log:
        return Normalize(0.0, hi)
    pos = v[v > 0]
    lo = float(np.percentile(pos, PERCENTILES[0])) if len(pos) else hi / 100
    return LogNorm(min(lo, hi / 10), hi)


def colour_map():
    cmap = plt.get_cmap('viridis').resampled(CMAP_LEVELS)
    return cmap.with_extremes(bad=(0, 0, 0, 0), under=cmap(0))     # zero counts: the bottom colour


def colour_bar(cb, norm, size):
    """Plain tick labels (1-2-5 on a log scale), the unit."""
    if isinstance(norm, LogNorm):
        e0, e1 = int(math.floor(math.log10(norm.vmin))), int(math.ceil(math.log10(norm.vmax)))
        ticks = [m * 10.0 ** e for e in range(e0, e1 + 1) for m in (1, 2, 5)]
        cb.set_ticks([t for t in ticks if norm.vmin <= t <= norm.vmax])
        cb.minorticks_off()
    cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%g'))
    cb.ax.tick_params(labelsize=size - 1)
    cb.set_label(UNIT, fontsize=size)
    return cb


def shown(a, norm):
    """Zero counts drawn at the bottom colour (a log scale has no zero); no pixel stays NaN."""
    if isinstance(norm, LogNorm):
        return np.where(np.isfinite(a) & (a <= 0), norm.vmin / 2, a)
    return a


def usable_edges(s):
    """The usable columns' outer edges (columns), NaN when there are none."""
    return (s.cols[0] - 0.5, s.cols[-1] + 0.5) if len(s.cols) else (np.nan, np.nan)


def column_angle(s, rows):
    """Each usable column's mean 2θ over ``rows`` (first, last), as pinhole.single_frame_peaks."""
    return s.tt[rows[0]:rows[1] + 1][:, s.cols].mean(axis=0)


def predicted_column(s, rows, peak):
    """The detector column whose mean 2θ over ``rows`` is nearest the peak (None: off the detector)."""
    x = s.tt[rows[0]:rows[1] + 1].mean(axis=0)
    c = int(np.argmin(np.abs(x - peak)))
    return c if abs(x[c] - peak) <= math.degrees(ph.PIXEL_MM / s.frame.geom.d_pinhole) else None


def peak_track(shots, peak, half_deg=HALF_DEG, beta_band=BETA_BAND):
    """Per frame: the brightest usable column within peak ± half_deg (rows of
    ``beta_band``), its 2θ, counts, the window's median, the significance,
    whether the frame holds the peak (enough columns in the window, the
    brightest standing ``MIN_SIGNIFICANCE`` counting errors above the median,
    not on the window's edge), and lss_core's single-frame Gaussian centre."""
    rows = ph.rows_for_beta(shots[0].frame, beta_band)
    fits = {}
    if peak is not None:
        for f in ph.single_frame_peaks([s.frame for s in shots], peak, half_deg=0.4, rows=rows):
            fits[round(f[0], 6)] = (f[1], f[2])
    out = []
    for s in shots:
        d = dict(scan=s.scan, point=s.point, det_th=s.dth, holds=False, column=None, two_theta=None,
                 counts=None, median=None, significance=None,
                 predicted=predicted_column(s, rows, peak) if peak is not None else None,
                 fit=fits.get(round(s.dth, 6), (None, None)))
        out.append(d)
        if peak is None:
            continue
        x = column_angle(s, rows)
        n = np.clip(s.frame.counts[rows[0]:rows[1] + 1][:, s.cols], 0, None).sum(axis=0)
        ok = np.flatnonzero(np.abs(x - peak) <= half_deg)
        if len(ok) >= MIN_COLUMNS:
            k = ok[int(np.argmax(n[ok]))]
            med = float(np.median(n[ok]))
            sig = (float(n[k]) - med) / math.sqrt(max(med, 1.0))
            d.update(column=int(s.cols[k]), two_theta=float(x[k]), counts=float(n[k]), median=med,
                     significance=sig,
                     holds=bool(sig >= MIN_SIGNIFICANCE and ok[0] < k < ok[-1]))
    return out, rows


def write_track(path, track):
    def fmt(v, spec):
        return '' if v is None else format(v, spec)
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['scan', 'point', 'det_th_deg', 'holds_peak', 'column', 'two_theta_deg', 'counts',
                    'window_median', 'significance', 'predicted_column', 'fit_centre_deg', 'fit_centre_err_deg'])
        for d in track:
            w.writerow([d['scan'], d['point'], '%.3f' % d['det_th'], int(d['holds']), fmt(d['column'], 'd'),
                        fmt(d['two_theta'], '.4f'), fmt(d['counts'], '.0f'), fmt(d['median'], '.1f'),
                        fmt(d['significance'], '.2f'), fmt(d['predicted'], 'd'), fmt(d['fit'][0], '.4f'),
                        fmt(d['fit'][1], '.4f')])


def summary(track, step):
    """Spread of the peak's 2θ over the frames that hold it, against the
    travel of its column (and of the arm), in degrees and in 2θ bins."""
    held = [d for d in track if d['holds']]
    if not held:
        return {'frames': 0}
    tt = np.array([d['two_theta'] for d in held])
    col = np.array([d['column'] for d in held])
    fit = np.array([d['fit'][0] for d in held if d['fit'][0] is not None])
    return dict(frames=len(held), det_th=(held[0]['det_th'], held[-1]['det_th']),
                tt_mean=float(tt.mean()), tt_range=(float(tt.min()), float(tt.max())), tt_std=float(tt.std()),
                max_dev_bins=float(np.max(np.abs(tt - tt.mean())) / step),
                columns=(int(col[0]), int(col[-1])), travel_columns=int(abs(col[-1] - col[0])),
                arm_columns=float(abs(held[-1]['det_th'] - held[0]['det_th']) / step),
                fit_frames=len(fit), fit_range=(float(fit.min()), float(fit.max())) if len(fit) else None,
                fit_std=float(fit.std()) if len(fit) else None)


# ---------------------------------------------------------------- the drawing

class Movie:
    """One figure whose image artist is updated with set_data, the limits
    and the norm fixed (M2, F69); frames rendered to one shared palette."""

    def __init__(self, shape, extent, norm, xlabel, ylabel, peak_x=None):
        ny, nx = shape
        self.sx, self.sy = max(1, int(round(PLOT_W / nx))), max(1, int(round(PLOT_H / ny)))
        aw, ah = nx * self.sx, ny * self.sy
        left, right, bottom, top = 72, 118, 52, 34
        W, H = left + aw + right, bottom + ah + top
        self.fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
        self.ax = self.fig.add_axes([left / W, bottom / H, aw / W, ah / H])
        self.ax.set_facecolor(NODATA)
        self.im = self.ax.imshow(np.full(shape, np.nan), origin='lower', extent=extent, aspect='auto',
                                 interpolation='nearest', cmap=colour_map(), norm=norm)
        self.ax.set_xlim(extent[0], extent[1])
        self.ax.set_ylim(extent[2], extent[3])
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        cax = self.fig.add_axes([(left + aw + 14) / W, bottom / H, 14 / W, ah / H])
        colour_bar(self.fig.colorbar(self.im, cax=cax, extend='min' if isinstance(norm, LogNorm) else 'neither'),
                   norm, 9)
        self.lines = [self.ax.axvline(np.nan, color=GUIDE, lw=1, ls=':', antialiased=False) for _ in range(2)]
        tr = blended_transform_factory(self.ax.transData, self.ax.transAxes)
        self.mark, = self.ax.plot([np.nan], [1.0], marker='v', ms=9, color=MARK, mec='white', mew=0.8,
                                  transform=tr, clip_on=False, ls='none')
        if peak_x is not None:
            self.mark.set_xdata([peak_x])
        self.title = self.ax.set_title('', loc='left', fontsize=10)
        self.palette = None

    def frame(self, image, title, edges=(np.nan, np.nan), mark_x=None):
        self.im.set_data(image)
        for ln, x in zip(self.lines, edges):
            ln.set_xdata([x, x])
        if mark_x is not None:
            self.mark.set_xdata([mark_x if np.isfinite(mark_x) else np.nan])
        self.title.set_text(title)
        self.fig.canvas.draw()
        rgb = Image.frombuffer('RGBA', self.fig.canvas.get_width_height(), self.fig.canvas.buffer_rgba(),
                               'raw', 'RGBA', 0, 1).convert('RGB')
        if self.palette is None:
            self.palette = gif_palette(self.im.cmap)
        return rgb.quantize(palette=self.palette, dither=Image.Dither.NONE)

    def close(self):
        plt.close(self.fig)


def gif_palette(cmap):
    """One fixed palette for every frame: the colour levels, then greys for
    text and axes, the no-data grey, the guides; nothing depends on a frame."""
    cols = [tuple(int(round(255 * c)) for c in cmap(i / (CMAP_LEVELS - 1))[:3]) for i in range(CMAP_LEVELS)]
    cols += [(v, v, v) for v in np.linspace(0, 255, 64).round().astype(int)]
    for h in (NODATA, GUIDE, MARK):
        cols.append(tuple(int(h[k:k + 2], 16) for k in (1, 3, 5)))
    # blends of the marker and the guides with white and with the colour levels (antialiased edges)
    m = np.array(cols[-1], float)
    cols += [tuple(int(round(v)) for v in m + (255 - m) * t) for t in (0.25, 0.5, 0.75)]
    flat = [v for c in cols for v in c]
    pal = Image.new('P', (1, 1))
    pal.putpalette(flat + [0] * (768 - len(flat)))
    return pal


def save_gif(path, frames, fps):
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(round(1000.0 / fps)),
                   loop=0, optimize=False, disposal=1)


def title_for(spec, s, k, n):
    return '%s  S# %d  pt %d   Det_Th %.3f°   (%d / %d)' % (os.path.basename(spec), s.scan, s.point, s.dth,
                                                         k + 1, n)


def edges_angle(s):
    """2θ of the usable columns' outer edges (mean over rows), for the dotted lines."""
    if not len(s.cols):
        return np.nan, np.nan
    t = s.tt.mean(axis=0)
    step = math.degrees(ph.PIXEL_MM / s.frame.geom.d_pinhole)
    return t[s.cols[0]] - step / 2, t[s.cols[-1]] + step / 2


def contact_sheet(path, spec, shots, angle_imgs, pixel_imgs, extent_a, extent_p, norm, peak, track,
                  rows_per_bin):
    """Up to SHEET_FRAMES evenly spaced frames: on one 2θ axis (left) and on pixels (right)."""
    n = len(shots)
    pick = sorted(set(np.linspace(0, n - 1, min(SHEET_FRAMES, n)).round().astype(int)))
    cmap = colour_map()
    h, top, bottom = 1.15, 0.45, 0.85                  # inches: panel row, above, below
    H = top + bottom + h * len(pick)
    fig, axs = plt.subplots(len(pick), 2, figsize=(11.0, H), dpi=DPI, sharex='col', squeeze=False,
                            gridspec_kw=dict(width_ratios=(1.55, 1.0), hspace=0.1, wspace=0.13,
                                             left=0.065, right=0.895, top=1 - top / H, bottom=bottom / H))
    tr_kw = dict(marker='v', ms=7, color=MARK, mec='white', mew=0.7, clip_on=False, ls='none')
    label = dict(fontsize=7.5, va='top', ha='left', color='black',
                 bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='none', alpha=0.85))
    for row, k in enumerate(pick):
        s, d = shots[k], track[k]
        for col, (img, ext) in enumerate(((angle_imgs[k], extent_a), (pixel_imgs[k], extent_p))):
            ax = axs[row, col]
            ax.set_facecolor(NODATA)
            im = ax.imshow(shown(img, norm), origin='lower', extent=ext, aspect='auto',
                           interpolation='antialiased', cmap=cmap, norm=norm)
            ax.set_xlim(ext[0], ext[1])
            ax.set_ylim(ext[2], ext[3])
            ax.tick_params(labelsize=7, length=2)
            tr = blended_transform_factory(ax.transData, ax.transAxes)
            if col == 0:
                for x in edges_angle(s):
                    if np.isfinite(x):
                        ax.axvline(x, color=GUIDE, lw=0.8, ls=':')
                if peak is not None and ext[0] < peak < ext[1]:
                    ax.plot([peak], [1.0], transform=tr, **tr_kw)
                ax.text(0.006, 0.95, 'pt %d   Det_Th %.2f°' % (s.point, s.dth), transform=ax.transAxes, **label)
            else:
                for c in usable_edges(s):
                    if np.isfinite(c):
                        ax.axvline(c, color=GUIDE, lw=0.8, ls=':')
                if d['predicted'] is not None:
                    ax.plot([d['predicted']], [1.0], transform=tr, **tr_kw)
    axs[0, 0].set_title('on one 2θ axis (lss_core.pinhole.pixel_angles): the peak stands still', fontsize=9,
                        loc='left')
    axs[0, 1].set_title('on detector pixels: the peak walks, the junk stays', fontsize=9, loc='left')
    axs[-1, 0].set_xlabel('2θ (°)', fontsize=8)
    axs[-1, 1].set_xlabel('detector column', fontsize=8)
    for col, text in ((0, 'β (°)'), (1, 'detector row')):
        p0 = axs[0, col].get_position()
        p1 = axs[-1, col].get_position()
        fig.text(p0.x0 - 0.04, 0.5 * (p0.y1 + p1.y0), text, rotation=90, va='center', ha='center', fontsize=8)
    p0, p1 = axs[0, 1].get_position(), axs[-1, 1].get_position()
    cax = fig.add_axes([p0.x1 + 0.012, p1.y0 + 0.25 * (p0.y1 - p1.y0), 0.012, 0.5 * (p0.y1 - p1.y0)])
    colour_bar(fig.colorbar(im, cax=cax, extend='min' if isinstance(norm, LogNorm) else 'neither'), norm, 8)
    scans = ' '.join(sorted({str(x.scan) for x in shots}, key=int))
    fig.text(0.065, 0.12 / H, '%s, scan %s: %d of %d frames, one colour scale (%s), rows binned by %d. '
             'Triangles: the peak\'s 2θ (left), the column that sees it (right). Dotted: the usable columns '
             '(S5 ∩ footprint).' % (os.path.basename(spec), scans, len(pick), n,
                                    'log' if isinstance(norm, LogNorm) else 'linear', rows_per_bin),
             fontsize=7, color='#444444')
    fig.savefig(path, dpi=DPI, metadata={'Software': None})
    plt.close(fig)


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', default=NX, help='SPEC file (default: the public NX school file)')
    ap.add_argument('--scans', nargs='+', default=['11'],
                    help='GID scans, e.g. 11 or 11 12 or 11,12 (default 11)')
    ap.add_argument('--out', default=OUT, help='output folder (default docs/figures/gid_movie)')
    ap.add_argument('--fps', type=float, default=5.0, help='frames per second of the GIFs (default 5)')
    scale = ap.add_mutually_exclusive_group()
    scale.add_argument('--log', dest='log', action='store_true', default=True,
                       help='log colour scale (the default)')
    scale.add_argument('--linear', dest='log', action='store_false', help='linear colour scale')
    ap.add_argument('--every', type=int, default=1, help='use every Nth frame (default 1: all)')
    ap.add_argument('--window', type=pair, default=None,
                    help='2θ window "low,high" in degrees (default: the scans\' whole 2θ range)')
    ap.add_argument('--beta', type=pair, default=None,
                    help='β window "low,high" in degrees (default: the whole detector); "--beta=-0.5,3"')
    ap.add_argument('--rows', type=int, default=4, help='detector rows per β bin (default 4)')
    ap.add_argument('--peak', type=float, default=None,
                    help='2θ of the peak to mark and track, degrees (default: lss_core.pinhole.strongest_peak)')
    ap.add_argument('--pinhole-mm', type=float, default=0.0,
                    help='S4-detector distance, mm (default 0: the header\'s, as the reader until Fit)')
    ap.add_argument('--pixels', action='store_true', help='also write the movie on detector pixels')
    a = ap.parse_args(argv)
    t0 = time.time()
    scans = [int(x) for x in ' '.join(a.scans).replace(',', ' ').split()]
    if a.every < 1 or a.rows < 1 or a.fps <= 0:
        ap.error('--every and --rows must be at least 1, --fps above 0')
    public = os.path.abspath(a.spec) == os.path.abspath(os.path.join(ROOT, NX)) or \
        os.path.abspath(a.spec) == os.path.abspath(NX)
    if not public and os.path.abspath(a.out).startswith(os.path.abspath(os.path.join(ROOT, 'docs'))):
        sys.exit('private data: give an --out outside docs/ (e.g. under sample_data/private/figures/)')
    os.makedirs(a.out, exist_ok=True)
    tag = '_'.join(map(str, scans))

    shots = load(a.spec, scans, a.pinhole_mm)
    edges, bedges = grid(shots, a.window, a.beta, a.rows)
    step = edges[1] - edges[0]
    angle_all = [angle_image(s, edges, bedges) for s in shots]
    pixel_all = [pixel_image(s, a.rows) for s in shots]
    norm = colour_norm(angle_all, a.log)              # all the scans' frames: --every keeps the colours
    peak = a.peak
    if peak is None:
        try:
            peak = float(ph.strongest_peak([s.frame for s in shots if s.scan == shots[0].scan],
                                           ph.rows_for_beta(shots[0].frame, BETA_BAND)))
        except ValueError as e:                       # too little 2θ for a peak window: no peak marked
            print('no peak: %s' % e)
    track, _ = peak_track(shots, peak)
    pick = list(range(0, len(shots), a.every))
    shots, track = [shots[k] for k in pick], [track[k] for k in pick]
    angle_imgs, pixel_imgs = [angle_all[k] for k in pick], [pixel_all[k] for k in pick]

    extent_a = (edges[0], edges[-1], bedges[0], bedges[-1])
    nr, nc = shots[0].frame.counts.shape
    extent_p = (-0.5, nc - 0.5, -0.5, pixel_imgs[0].shape[0] * a.rows - 0.5)
    inside = peak is not None and edges[0] < peak < edges[-1]
    mv = Movie(angle_imgs[0].shape, extent_a, norm, '2θ (°)', 'β (°)', peak_x=peak if inside else None)
    gif = [mv.frame(shown(img, norm), title_for(a.spec, s, k, len(shots)), edges_angle(s))
           for k, (s, img) in enumerate(zip(shots, angle_imgs))]
    mv.close()
    paths = [os.path.join(a.out, 'movie_%s.gif' % tag)]
    save_gif(paths[0], gif, a.fps)
    if a.pixels:
        pm = Movie(pixel_imgs[0].shape, extent_p, norm, 'detector column', 'detector row')
        gif = [pm.frame(shown(img, norm), title_for(a.spec, s, k, len(shots)), usable_edges(s),
                        mark_x=float(d['predicted']) if d['predicted'] is not None else np.nan)
               for k, (s, img, d) in enumerate(zip(shots, pixel_imgs, track))]
        pm.close()
        paths.append(os.path.join(a.out, 'pixels_%s.gif' % tag))
        save_gif(paths[-1], gif, a.fps)
    paths.append(os.path.join(a.out, 'contact_%s.png' % tag))
    contact_sheet(paths[-1], a.spec, shots, angle_imgs, pixel_imgs, extent_a, extent_p, norm, peak, track,
                  a.rows)
    paths.append(os.path.join(a.out, 'peak_%s.csv' % tag))
    write_track(paths[-1], track)

    sm = summary(track, step)
    print('%d frames (every %d), window 2θ %.3f–%.3f°, β %.3f–%.3f°; bins %.4f° × %.4f°; colour %s %.3g–%.3g %s'
          % (len(shots), a.every, edges[0], edges[-1], bedges[0], bedges[-1], step, bedges[1] - bedges[0],
             'log' if a.log else 'linear', norm.vmin, norm.vmax, UNIT))
    if peak is not None:
        print('peak %.3f° (%s); S4-detector %.1f mm' % (peak, 'given' if a.peak is not None else 'strongest_peak',
                                                         shots[0].frame.geom.d_pinhole))
    if sm['frames']:
        print('frames holding the peak: %d (Det_Th %.2f–%.2f°, the arm moved %.1f bins of %.4f°)'
              % (sm['frames'], sm['det_th'][0], sm['det_th'][1], sm['arm_columns'], step))
        print('  brightest column\'s 2θ: mean %.4f°, range %.4f–%.4f°, std %.4f°, largest deviation %.2f bins'
              % (sm['tt_mean'], sm['tt_range'][0], sm['tt_range'][1], sm['tt_std'], sm['max_dev_bins']))
        print('  its column: %d -> %d (%d columns)' % (sm['columns'][0], sm['columns'][1], sm['travel_columns']))
        if sm['fit_frames']:
            print('  single-frame Gaussian centres (lss_core.pinhole.single_frame_peaks), %d of them: %.4f–%.4f°, '
                  'std %.4f°' % (sm['fit_frames'], sm['fit_range'][0], sm['fit_range'][1], sm['fit_std']))
    elif peak is not None:
        print('no frame holds the peak at %.3f°' % peak)
    for p in paths:
        print('wrote %s (%.0f kB)' % (p, os.path.getsize(p) / 1024))
    print('%.1f s' % (time.time() - t0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
