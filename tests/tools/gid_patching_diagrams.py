"""Diagrams for the manual's GID patching addendum (docs/manual/gid_patching.md).

    python tests/tools/gid_patching_diagrams.py [--out DIR] [--only N ...]

Six 2D diagrams (default folder docs/manual/figures/gid_patching/):

1. ``01_frame_anatomy.png``: one frame, its direct-beam pixel, rows used,
   sample horizon, and the column windows (S5, footprint exact and IDL's,
   usable columns, legacy column band).
2. ``02_columns_to_two_theta.png``: top view; three columns, their rays
   through the S4 pinhole, and the legacy band placed at Det_Th.
3. ``03_frames_cover_two_theta.png``: the 2θ range of every frame, frames
   per 2θ bin, map edges, a 2θ bin against the 2θ resolution.
4. ``04_pixels_to_cells.png``: exact per-pixel (2θ, β) over the cell grid,
   level and raised arm.
5. ``05_levels_and_overlaps.png``: the Qz levels in (2θ, β), the β overlap,
   the transverse range, and the legacy edge copies.
6. ``06_join_factor.png``: how the level join factor is fitted, with the
   NX 11 + 12 numbers.

Every number comes from lss_core (pinhole, gid, experiment) and the public
NX school data (sample_data/NX_school/2026sep/20260923, GID scans 11 and
12); nothing is typed. Only that file is read: the script takes no other
SPEC file, so no private data can reach the repository. Runs headless
(Agg) from anywhere (it changes to the repository root). Reads only; writes
the PNG files. Prints any text label that overlaps another or leaves the
figure.
"""
import argparse
import math
import os
import re
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import matplotlib                                    # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.patches import Polygon, Rectangle   # noqa: E402

from lss_core import pinhole as ph                   # noqa: E402
from lss_core.experiment import Experiment           # noqa: E402
from lss_core.gid import GIDParams, pinhole_frames   # noqa: E402

SPEC = 'sample_data/NX_school/2026sep/20260923'
LOW_SCAN, HIGH_SCAN = 11, 12
OUT = 'docs/manual/figures/gid_patching'
DPI = 130

# One colour per concept, the same in every diagram (checked with the dataviz
# validator: usable/S5/footprint/legacy and level 1/level 2/legacy pass the
# colour-vision checks as sets).
USABLE = '#2a78d6'       # usable columns
S5C = '#a8329b'          # S5 window
FPX = '#c98500'          # footprint window, exact (and the footprint itself)
FPX_T = '#a06a00'        # the same, darker, for text
IDL = '#6e6d68'          # IDL's footprint window (dashed)
LEG = '#d4380d'          # legacy column band, legacy patch, edge copies
LV1 = '#1a9a6c'          # Qz level 1 (scan 11, arm level)
LV2 = '#6250d6'          # Qz level 2 (scan 12, arm raised)
OVL = '#3d3c38'          # overlaps (hatched)
EDGE = '#b9b8b1'         # map edges (left out)
INK, INK2, MUTED, GRID = '#0b0b0b', '#52514e', '#898781', '#e1e0d9'

plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': 'white', 'savefig.facecolor': 'white',
    'axes.edgecolor': '#c3c2b7', 'axes.labelcolor': INK2, 'axes.titlesize': 10.5,
    'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'axes.labelsize': 9.5,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.labelcolor': INK2, 'ytick.labelcolor': INK2,
    'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5, 'font.size': 9, 'legend.frameon': False,
    'legend.fontsize': 8.5, 'axes.spines.top': False, 'axes.spines.right': False,
    'hatch.linewidth': 0.7, 'text.color': INK})


def deg(x):
    return math.degrees(x)


# ------------------------------------------------------------------ the data

class Data:
    """Frames, windows and results of the NX scans, from lss_core only."""

    def __init__(self):
        e = Experiment(SPEC)
        self.params = GIDParams()
        frames, _ = e.gid_frames([LOW_SCAN, HIGH_SCAN])
        self.levels = pinhole_frames(frames, self.params)          # [level 1 (scan 11), level 2 (scan 12)]
        assert [sorted({f.scan for f in L}) for L in self.levels] == [[LOW_SCAN], [HIGH_SCAN]]
        self.res = e.gid([LOW_SCAN, HIGH_SCAN], params=self.params)
        self.union = e.gid([LOW_SCAN, HIGH_SCAN], params=GIDParams(transverse='union'))
        self.legacy = e.gid([LOW_SCAN, HIGH_SCAN], params=GIDParams(pinhole=False), axes='Angles')
        self.legacy_levels = [e.gid([s], params=GIDParams(pinhole=False), axes='Angles')
                              for s in (LOW_SCAN, HIGH_SCAN)]
        self.ncols = self.levels[0][0].counts.shape[1]
        self.nrows = self.levels[0][0].counts.shape[0]
        mid = 0.5 * (deg(self.levels[0][0].geom.dth) + deg(self.levels[0][-1].geom.dth))
        self.f1 = min(self.levels[0], key=lambda f: abs(deg(f.geom.dth) - mid))   # the middle frame, Det_Th 16°
        self.f2 = self.levels[1][0]                                               # scan 12, first frame

    def windows(self, f):
        g = f.geom
        s1v, s4 = f.areainfo[1], f.areainfo[2]
        cols = ph.frame_columns(f, self.ncols)
        _, inner = ph.s4_window(g, s1v, s4 / 2, s4 / 2, f.s1_to_sample_mm)
        half = (self.params.columns - 1) / 2
        return dict(usable=(int(cols[0]), int(cols[-1])), s5=ph.s5_window(g, *f.s5), exact=inner,
                    idl=ph.footprint_window(g, s1v, f.s1_to_sample_mm),
                    legacy=(g.c0 - half, g.c0 + half))


D = None


def data():
    global D
    if D is None:
        D = Data()
    return D


def revision():
    try:
        return subprocess.run(['git', 'describe', '--always', '--dirty'], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
    except OSError:
        return '?'


# ------------------------------------------------------------- figure helpers

def caption(fig, text, source='NX school 20260923, scans %d and %d' % (LOW_SCAN, HIGH_SCAN)):
    fig.text(0.015, 0.038, text, fontsize=9.5, ha='left', va='bottom', color='#222222')
    fig.text(0.015, 0.012, 'Numbers from lss_core (pinhole, gid) on %s; tests/tools/gid_patching_diagrams.py %s'
             % (source, revision()), fontsize=7.5, ha='left', va='bottom', color='#777777')


def text_overlaps(fig):
    """Pairs of texts whose boxes overlap, and texts outside the figure."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    ticks = set()
    for ax in fig.findobj(matplotlib.axes.Axes):
        for axis in (ax.xaxis, ax.yaxis):
            ticks.update(id(t) for t in axis.get_ticklabels(which='both'))
            ticks.add(id(axis.label))
            ticks.add(id(axis.get_offset_text()))
    texts = [t for t in fig.findobj(matplotlib.text.Text)
             if t.get_visible() and t.get_text().strip() and id(t) not in ticks]
    boxes = [(t, matplotlib.text.Text.get_window_extent(t, r)) for t in texts]
    W, H = fig.bbox.width, fig.bbox.height
    out = []
    for i, (t, b) in enumerate(boxes):
        if b.x0 < -1 or b.y0 < -1 or b.x1 > W + 1 or b.y1 > H + 1:
            out.append(('outside', t.get_text()[:40], ''))
        for t2, b2 in boxes[i + 1:]:
            if b.overlaps(b2):
                out.append(('overlap', t.get_text()[:40], t2.get_text()[:40]))
    return out


def save(fig, out, name):
    for t in fig.findobj(matplotlib.text.Text):          # minus signs, not hyphens, before numbers
        t.set_text(re.sub(r'(?<![\w.])-(?=\d)', '−', t.get_text()))
    for p in text_overlaps(fig):
        print('  %s: %r %r' % p)
    path = os.path.join(out, name)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print('wrote', os.path.relpath(path, ROOT))


def hatch_rect(ax, x0, x1, y0, y1, color, hatch='////', alpha=1.0, fill=None, lw=0.0, **kw):
    if fill is not None:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=fill, edgecolor='none', **kw))
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor='none', edgecolor=color, hatch=hatch,
                           lw=lw, alpha=alpha, **kw))


def fmt_cols(a, b, d=1):
    f = '%%.%df' % d
    return (f + '–' + f) % (a, b)


# -------------------------------------------------------------- 1. the frame

def fig_frame_anatomy(out):
    d = data()
    f, gp = d.f1, d.params
    g = f.geom
    w = d.windows(f)
    nr, nc = d.nrows, d.ncols
    fig = plt.figure(figsize=(9.2, 9.6))
    ax = fig.add_axes([0.30, 0.40, 0.56, 0.50])
    axb = fig.add_axes([0.30, 0.13, 0.56, 0.235], sharex=ax)
    counts = np.clip(np.asarray(f.counts, float), 0, None)
    ax.imshow(np.log10(1 + counts), cmap='Greys', origin='lower', aspect='auto', alpha=0.45,
              extent=(-0.5, nc - 0.5, -0.5, nr - 0.5), interpolation='nearest')
    ax.set_xlim(-12, nc + 12)
    ax.set_ylim(-8, nr + 8)
    ax.add_patch(Rectangle((-0.5, -0.5), nc, nr, fill=False, edgecolor=INK2, lw=1.0))
    # usable columns and the legacy band, over the rows used
    u0, u1 = w['usable']
    ax.add_patch(Rectangle((u0 - 0.5, gp.row_min - 0.5), u1 - u0 + 1, gp.row_max - gp.row_min + 1,
                           facecolor=USABLE, alpha=0.10, edgecolor=USABLE, lw=1.0))
    l0, l1 = w['legacy']
    ax.add_patch(Rectangle((l0 - 0.5, gp.row_min - 0.5), l1 - l0 + 1, gp.row_max - gp.row_min + 1,
                           facecolor=LEG, alpha=0.55, edgecolor=LEG, lw=0.8))
    ax.annotate('legacy column band\n(columns %d–%d)' % (l0, l1), xy=(l1 + 0.5, 300), xytext=(62, 345),
                color=LEG, fontsize=9, ha='left', va='center',
                arrowprops=dict(arrowstyle='-', color=LEG, lw=0.9))
    ax.text(0.5 * (u0 + u1) + 14, 420, 'usable columns', color=USABLE, fontsize=9.5, ha='center',
            fontweight='bold')
    # rows not used (below row_min, above row_max)
    hatch_rect(ax, -0.5, nc - 0.5, -0.5, gp.row_min - 0.5, MUTED, hatch='xxx', lw=0)
    ax.text(nc - 14, gp.row_min / 2 - 0.5, 'rows < row_min: not used', color=INK2, fontsize=8, ha='right',
            va='center', bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
    if gp.row_max < nr - 1:
        hatch_rect(ax, -0.5, nc - 0.5, gp.row_max + 0.5, nr - 0.5, MUTED, hatch='xxx', lw=0)
    xb = nc - 8
    ax.annotate('', xy=(xb, gp.row_min - 0.5), xytext=(xb, gp.row_max + 0.5),
                arrowprops=dict(arrowstyle='|-|', color=INK2, lw=1.0, mutation_scale=4))
    ax.text(xb - 2, 0.5 * (gp.row_min + gp.row_max) + 60, 'rows used %d–%d' % (gp.row_min, gp.row_max),
            rotation=90, color=INK2, fontsize=9, ha='right', va='center',
            bbox=dict(facecolor='white', edgecolor='none', pad=1.0, alpha=0.8))
    # sample horizon: β = 0, exact angles (a contour across the module)
    rr = np.arange(nr)
    cc = np.arange(nc)
    _, B = ph.pixel_angles(g, rr, cc)
    ax.contour(cc, rr, np.degrees(B), levels=[0.0], colors=[INK], linewidths=1.2, linestyles='-.')
    hz = float(np.interp(0.0, np.degrees(B[:, nc - 1]), rr))
    ax.text(nc - 14, hz + 6, 'sample horizon (β = 0)', color=INK, fontsize=9, ha='right', va='bottom')
    # direct-beam pixel
    ax.plot([g.c0], [g.r0], marker='*', ms=13, color=INK, mec='white', mew=0.8, zorder=5)
    ax.annotate('direct-beam pixel\n(c0, r0) = (%g, %g)' % (g.c0, g.r0), xy=(g.c0, g.r0), xytext=(118, 125),
                color=INK, fontsize=9, ha='left', va='center',
                arrowprops=dict(arrowstyle='-', color=INK, lw=0.8))
    ax.set_ylabel('row')
    ax.tick_params(labelbottom=False)
    fig.text(0.015, 0.985, 'One frame: scan %d, Det_Th %.1f°, arm height β0 %.2f° (%d rows × %d columns)'
             % (f.scan, deg(g.dth), deg(g.beta0), nr, nc), fontsize=10.5, fontweight='bold', ha='left', va='top')
    # approximate angle axes (per-axis formulas, on row r0 / column c0)
    dp, dv = g.d_pinhole, ph.vertical_distance(g)
    top = ax.secondary_xaxis('top', functions=(
        lambda c: np.degrees(g.dth + np.arctan((np.asarray(c, float) - g.c0) * ph.PIXEL_MM / dp)),
        lambda t: g.c0 + np.tan(np.radians(np.asarray(t, float)) - g.dth) * dp / ph.PIXEL_MM))
    top.set_xlabel('≈ 2θ (deg), on row r0', color=INK2)
    right = ax.secondary_yaxis('right', functions=(
        lambda r: np.degrees(g.beta0 + np.arctan((np.asarray(r, float) - g.r0) * ph.PIXEL_MM / dv)),
        lambda b: g.r0 + np.tan(np.radians(np.asarray(b, float)) - g.beta0) * dv / ph.PIXEL_MM))
    right.set_ylabel('≈ β (deg), on column c0', color=INK2, labelpad=14)
    right.spines['right'].set_visible(True)
    top.spines['top'].set_visible(True)
    # the column windows, as bars
    bars = [('S5 window', w['s5'], S5C, '-', S5C),
            ('footprint window, exact', w['exact'], FPX, '-', FPX_T),
            ("footprint window, IDL's", w['idl'], IDL, (0, (4, 2)), IDL),
            ('usable columns', (u0, u1), USABLE, '-', USABLE),
            ('legacy column band', (l0, l1), LEG, '-', LEG)]
    for k, (name, (a, b), col, ls, tcol) in enumerate(bars):
        y = len(bars) - 1 - k
        a0, b0 = max(a, -11.5), min(b, nc + 11.5)
        axb.plot([a0, b0], [y, y], color=col, lw=6, ls=ls, solid_capstyle='butt')
        if name == 'usable columns' or name == 'legacy column band':
            lab = '%d–%d' % (a, b)
        else:
            lab = fmt_cols(a, b)
        if name == 'legacy column band':
            axb.text(b + 3, y, '%s (c0 ± %d)' % (lab, (gp.columns - 1) // 2), color=tcol, fontsize=8.5,
                     ha='left', va='center')
        elif b0 + 3 < nc + 4:
            axb.text(b0 + 3, y, lab, color=tcol, fontsize=8.5, ha='left', va='center')
        else:
            axb.text(a0 - 3, y, lab, color=tcol, fontsize=8.5, ha='right', va='center')
    axb.set_yticks(range(len(bars)))
    axb.set_yticklabels([b[0] for b in bars][::-1])
    for t, b in zip(axb.get_yticklabels(), bars[::-1]):
        t.set_color(b[4])
        t.set_fontsize(9.5)
    axb.set_ylim(-0.7, len(bars) - 0.3)
    axb.set_xlabel('column')
    axb.grid(axis='x', color=GRID, lw=0.6)
    axb.axvline(g.c0, color=INK, lw=0.8, ls=':')
    axb.text(g.c0, len(bars) - 0.35, 'c0', color=INK, fontsize=8.5, ha='center', va='bottom')
    axb.spines['left'].set_visible(False)
    axb.tick_params(axis='y', length=0)
    for x in (-0.5, nc - 0.5):
        axb.axvline(x, color=INK2, lw=0.8)
    caption(fig, 'Usable columns = S5 window ∩ exact footprint window; the legacy patch sums only the 3-column band '
                 'at c0. Counts in grey (log).', source='NX school 20260923, scan %d' % LOW_SCAN)
    save(fig, out, '01_frame_anatomy.png')


# ------------------------------------------------------- 2. columns to 2θ

def fig_columns_to_two_theta(out):
    """Schematic top view: positions drawn, not to scale; every number in a
    label is the reader's (ray_geometry, frame_columns)."""
    d = data()
    f = d.f1
    g = f.geom
    w = d.windows(f)
    u0, u1 = w['usable']
    l0, l1 = w['legacy']
    c0 = int(round(g.c0))
    cols = [u0, c0, u1]
    rays = {c: ph.ray_geometry(g, g.r0, c) for c in cols + [int(l0), int(l1)]}
    L = ph.footprint_length(g, f.areainfo[1], f.s1_to_sample_mm)
    # drawing geometry (schematic): arm at PHI, S4 at A, detector at DD (drawing units)
    PHI, A, DD, LF = math.radians(30.0), 6.0, 9.6, 2.6
    a = np.array([math.cos(PHI), math.sin(PHI)])
    e = np.array([math.sin(PHI), -math.cos(PHI)])          # across the arm, towards lower 2θ
    S = A * a
    def hit(x_true):                                          # drawn source → through S → detector line
        src = np.array([x_true * LF / (L / 2), 0.0])
        dvec = S - src
        # src + t dvec = DD a + v e
        t, v = np.linalg.solve(np.column_stack([dvec, -e]), DD * a - src)
        return src, src + t * dvec
    fig = plt.figure(figsize=(9.6, 5.9))
    ax = fig.add_axes([0.02, 0.09, 0.96, 0.83])
    ax.set_aspect('equal')
    ax.axis('off')
    # beam, footprint, sample
    ax.annotate('', xy=(-LF - 0.15, 0), xytext=(-LF - 3.2, 0),
                arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.6, mutation_scale=14))
    ax.text(-LF - 3.2, 0.18, 'incident beam (x)', color=INK, fontsize=9.5, ha='left', va='bottom')
    ax.plot([-LF, LF], [0, 0], color=FPX, lw=8, solid_capstyle='butt', zorder=2)
    ax.text(0, -0.62, 'footprint on the sample (%.1f mm long)' % L, color=FPX_T, fontsize=9.5, ha='center',
            va='top')
    ax.plot([LF, DD * a[0] + 1.0], [0, 0], color=MUTED, lw=0.6, ls=':', zorder=0)
    # arm centre line, Det_Th
    ax.plot([0, (DD + 0.6) * a[0]], [0, (DD + 0.6) * a[1]], color=MUTED, lw=1.0, ls=(0, (6, 3)), zorder=1)
    th = np.linspace(0, PHI, 30)
    ax.plot(4.6 * np.cos(th), 4.6 * np.sin(th), color=INK2, lw=0.9)
    ax.text(4.75, 0.45, 'Det_Th = %.1f° (drawn larger)' % deg(g.dth), color=INK2, fontsize=8.5, ha='left',
            va='center')
    ax.text((DD + 0.7) * a[0], (DD + 0.7) * a[1], 'arm', color=MUTED, fontsize=8.5, ha='left', va='bottom')
    # S4: two blades across the arm
    for sgn in (-1, 1):
        p, q = S + sgn * 0.07 * e, S + sgn * 0.75 * e
        ax.plot([p[0], q[0]], [p[1], q[1]], color=INK, lw=3.2, solid_capstyle='butt')
    ax.text(S[0] - 0.55, S[1] + 0.35, 'S4 pinhole\n(on the arm, S4 %.1f mm)' % f.areainfo[2], color=INK,
            fontsize=9.5, ha='right', va='bottom')
    # detector line, usable columns and the legacy band (their drawn ends from their sources)
    _, pa = hit(rays[u0].source[0])
    _, pb = hit(rays[u1].source[0])
    ends = [DD * a + 1.9 * e, DD * a - 2.3 * e]
    ax.plot([ends[0][0], ends[1][0]], [ends[0][1], ends[1][1]], color=INK2, lw=5, solid_capstyle='butt')
    ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color=USABLE, lw=5, solid_capstyle='butt')
    ax.text(ends[1][0] + 0.2, ends[1][1] + 0.05, 'detector: high columns, high 2θ', color=INK2,
            fontsize=8.5, ha='left', va='bottom')
    ax.text(ends[0][0] + 0.2, ends[0][1] - 0.05, 'low columns', color=INK2, fontsize=8.5,
            ha='left', va='top')
    mid = DD * a
    band = 0.12
    ax.plot([mid[0] - band * e[0], mid[0] + band * e[0]], [mid[1] - band * e[1], mid[1] + band * e[1]], color=LEG,
            lw=10, solid_capstyle='butt', zorder=4)
    # the three rays
    lab_off = {u0: (0.55, -0.55), c0: (0.45, 0.05), u1: (0.35, 0.15)}
    for c in cols:
        r = rays[c]
        src, p = hit(r.source[0])
        ax.plot([src[0], p[0]], [src[1], p[1]], color=INK, lw=1.1, zorder=3)
        ax.plot([src[0]], [src[1]], 'o', color=INK, ms=4.5, zorder=4)
        nm = 'column c0 = %d' % c if c == c0 else 'column %d' % c
        dx, dy = lab_off[c]
        ax.annotate('%s: 2θ = %.2f°' % (nm, deg(r.two_theta)), xy=(p[0], p[1]), xytext=(p[0] + dx + 0.1, p[1] + dy),
                    color=INK, fontsize=9.5, ha='left', va='center', zorder=6,
                    arrowprops=dict(arrowstyle='-', color=INK, lw=0.6, shrinkA=0, shrinkB=2))
        if c != c0:
            ax.text(src[0], -0.2, 'x = %.1f mm' % r.source[0], color=INK, fontsize=8.5, ha='center', va='top')
    ax.text(pb[0] - 0.6, pb[1] + 0.35, 'usable columns %d–%d' % (u0, u1), color=USABLE, fontsize=9.5,
            ha='right', va='bottom', fontweight='bold')
    # legacy: the band at Det_Th
    tl = [deg(rays[int(c)].two_theta) for c in (l0, c0, l1)]
    ax.annotate('legacy: the 3-column band (columns %d–%d)\nis placed at one 2θ = Det_Th = %.1f°;\n'
                'through the pinhole its columns are at\n%.2f°, %.2f°, %.2f°' % (l0, l1, deg(g.dth), *tl),
                xy=(mid[0] + 0.05, mid[1] - 0.12), xytext=(5.9, 2.3), color=LEG, fontsize=9.5,
                ha='left', va='top', arrowprops=dict(arrowstyle='-', color=LEG, lw=0.9))
    ax.text(-LF - 3.2, DD * a[1] + 0.2, 'Pinhole: every column sees its own\npoint of the footprint through S4,\n'
            'so every column has its own 2θ.', color=USABLE, fontsize=10, ha='left', va='top', fontweight='bold')
    ax.set_xlim(-LF - 3.4, DD * a[0] + 4.6)
    ax.set_ylim(-0.9, DD * a[1] + 2.3)
    fig.text(0.015, 0.975, 'Top view (in plane), schematic: positions not to scale; 2θ and x from ray_geometry '
             '(Det_Th %.1f°, row r0)' % deg(g.dth), fontsize=10.5, fontweight='bold', ha='left', va='top')
    caption(fig, 'Each column sees its own 2θ through the S4 pinhole; the legacy patch places its whole 3-column band '
                 'at Det_Th.', source='NX school 20260923, scan %d' % LOW_SCAN)
    save(fig, out, '02_columns_to_two_theta.png')


# --------------------------------------------------- 3. frames cover 2θ

def frames_per_bin(frames, edges, gp, ncols):
    """Frames whose usable pixels (rows used) fall in each 2θ bin, as
    lss_core.pinhole.level_map counts them for min_frames."""
    rows = np.arange(gp.row_min, gp.row_max + 1)
    n = np.zeros(len(edges) - 1, int)
    for f in frames:
        t = np.degrees(ph.pixel_angles(f.geom, rows, ph.frame_columns(f, ncols))[0])
        k = np.unique(np.digitize(t, edges) - 1)
        k = k[(k >= 0) & (k < len(n))]
        n[k] += 1
    return n


def fig_frames_cover(out):
    d = data()
    gp = d.params
    L1, L2 = d.levels
    info = d.res.info['levels']
    edges = info[0]['edges']
    step = info[0]['step_deg']
    fig = plt.figure(figsize=(9.6, 9.4))
    ax2 = fig.add_axes([0.10, 0.80, 0.62, 0.11])
    ax1 = fig.add_axes([0.10, 0.40, 0.62, 0.38], sharex=ax2)
    axh = fig.add_axes([0.10, 0.12, 0.62, 0.22], sharex=ax2)
    axr = fig.add_axes([0.79, 0.12, 0.19, 0.22])
    half = len(L1) // 2 + 1
    A, B = L1[:half], L1[half:]
    rA = [ph.frame_range(f, d.ncols) for f in A]
    rB = [ph.frame_range(f, d.ncols) for f in B]
    hb = 0.07
    for fs, rs, alpha in ((A, rA, 0.95), (B, rB, 0.45)):
        for f, (a, b) in zip(fs, rs):
            y = deg(f.geom.dth)
            ax1.add_patch(Rectangle((a, y - hb / 2), b - a, hb, facecolor=LV1, alpha=alpha, edgecolor='none'))
            ax1.plot([y], [y], 'o', color=LEG, ms=3.2, zorder=4)
    ov0, ov1 = min(a for a, _ in rB), max(b for _, b in rA)
    ymin, ymax = deg(L1[0].geom.dth) - 0.15, deg(L1[-1].geom.dth) + 0.15
    hatch_rect(ax1, ov0, ov1, ymin, ymax, OVL, hatch='\\\\\\', lw=0, alpha=0.55)
    ax1.set_ylim(ymin, ymax)
    yA, yB = deg(A[len(A) // 2].geom.dth), deg(B[len(B) // 2].geom.dth)
    ax1.text(rA[-1][1] + 1.6, deg(A[2].geom.dth), 'scan A (illustration):\nfirst %d frames' % len(A), color=LV1,
             fontsize=9, ha='left', va='center')
    ax1.text(rB[0][0] - 0.5, deg(B[len(B) // 2 + 3].geom.dth), 'scan B (illustration):\nlast %d frames' % len(B), color=LV1,
             fontsize=9, ha='right', va='center')
    ax1.text(0.5 * (ov0 + ov1), ymax + 0.04, '2θ overlap of scans A and B: scan join factor fitted here',
             color=OVL, fontsize=9, ha='center', va='bottom',
             bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
    ax1.set_ylabel('Det_Th of the frame (deg)')
    ax1.set_title('')
    ax1.text(0.005, 0.99, 'Qz level 1: scan %d, %d frames (arm level)' % (LOW_SCAN, len(L1)), color=LV1,
             fontsize=9.5, fontweight='bold', transform=ax1.transAxes, ha='left', va='top',
             bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
    for f in L2:
        a, b = ph.frame_range(f, d.ncols)
        y = deg(f.geom.dth)
        ax2.add_patch(Rectangle((a, y - hb / 2), b - a, hb, facecolor=LV2, alpha=0.9, edgecolor='none'))
        ax2.plot([y], [y], 'o', color=LEG, ms=3.2, zorder=4)
    ax2.set_ylim(deg(L2[0].geom.dth) - 0.1, deg(L2[-1].geom.dth) + 0.1)
    ax2.set_ylabel('Det_Th')
    ax2.text(0.995, 0.5, 'Qz level 2: scan %d, %d frames\n(arm raised, β0 %.1f°)'
             % (HIGH_SCAN, len(L2), deg(L2[0].geom.beta0)), color=LV2, fontsize=9.5, fontweight='bold',
             transform=ax2.transAxes, ha='right', va='center')
    ax2.set_title('Every frame covers the 2θ of its usable columns (bar); the legacy column band sits at Det_Th (dot)',
                  pad=8, fontsize=10)
    ax2.plot([], [], 's', color=LV1, ms=8, label="a frame's usable columns")
    ax2.plot([], [], 'o', color=LEG, ms=4, label='legacy column band (at Det_Th)')
    ax2.legend(loc='upper left', bbox_to_anchor=(1.01, 1.05), fontsize=8.5, handlelength=1.2)
    for a in (ax1, ax2):
        a.tick_params(labelbottom=False)
        a.grid(axis='x', color=GRID, lw=0.6)
    # frames per 2θ bin
    centres = 0.5 * (edges[:-1] + edges[1:])
    n1 = frames_per_bin(L1, edges, gp, d.ncols)
    n2 = frames_per_bin(L2, edges, gp, d.ncols)
    for n, col, lab in ((n1, LV1, 'level 1'), (n2, LV2, 'level 2')):
        k = np.flatnonzero(n > 0)
        k0, k1 = max(k[0] - 1, 0), min(k[-1] + 2, len(n))
        axh.stairs(n[k0:k1], edges[k0:k1 + 1], color=col, lw=1.4, label=lab)
    edge_bins = ((n1 > 0) & (n1 < gp.min_frames)) | ((n2 > 0) & (n2 < gp.min_frames))
    first = True
    for k in np.flatnonzero(edge_bins):
        axh.axvspan(edges[k], edges[k + 1], color=EDGE, alpha=0.9, lw=0, label='map edges (left out)' if first else None)
        first = False
    axh.axhline(gp.min_frames, color=INK, lw=1.0, ls='--')
    axh.text(centres[n1 > 0][-1] + 0.05, gp.min_frames + 0.5, 'min_frames = %d' % gp.min_frames, color=INK,
             fontsize=8.5, ha='left', va='bottom')
    e1 = np.flatnonzero((n1 > 0) & (n1 < gp.min_frames))
    e2 = np.flatnonzero((n2 > 0) & (n2 < gp.min_frames))
    lo_e, hi_e = edges[e1[0]], edges[e1[-1] + 1]
    axh.annotate('map edges', xy=(lo_e, gp.min_frames * 0.5), xytext=(lo_e + 0.45, n1.max() * 0.75),
                 color=INK2, fontsize=8.5, ha='left', arrowprops=dict(arrowstyle='-', color=INK2, lw=0.7))
    axh.annotate('', xy=(edges[e2[-1]], gp.min_frames * 0.5), xytext=(lo_e + 0.75, n1.max() * 0.72),
                 arrowprops=dict(arrowstyle='-', color=INK2, lw=0.7))
    axh.annotate('map edge', xy=(hi_e, gp.min_frames * 0.5), xytext=(hi_e - 0.3, n1.max() * 0.47),
                 color=INK2, fontsize=8.5, ha='right', arrowprops=dict(arrowstyle='-', color=INK2, lw=0.7))
    axh.set_ylabel('frames per 2θ bin')
    axh.set_xlabel('2θ (deg)')
    axh.legend(loc='upper right', fontsize=8, handlelength=1.4)
    axh.set_xlim(edges[0] - 0.55, edges[-1] + 0.55)
    axh.set_ylim(0, n1.max() * 1.15)
    axh.grid(axis='x', color=GRID, lw=0.6)
    # one 2θ bin against the 2θ resolution (column c0, middle frame)
    f = d.f1
    g = f.geom
    s4 = f.areainfo[2]
    acc = ph.column_acceptance(g, int(round(g.c0)), s4 / 2, s4 / 2, n=61)
    t = np.degrees(acc.two_theta - g.dth).ravel()
    wts = np.outer(ph._trapezoid(acc.two_theta.shape[0]), ph._trapezoid(acc.two_theta.shape[1])).ravel()
    res, _ = ph.two_theta_resolution(f)
    hist_e = np.linspace(-0.6 * res, 0.6 * res, 49)
    h, _ = np.histogram(t, hist_e, weights=wts)
    axr.stairs(h / h.max(), hist_e, color=INK, lw=1.2, fill=True, alpha=0.18)
    axr.stairs(h / h.max(), hist_e, color=INK, lw=1.2)
    axr.add_patch(Rectangle((-step / 2, 0), step, 1.0, facecolor=USABLE, alpha=0.3, lw=0))
    axr.annotate('', xy=(-step / 2, 1.06), xytext=(step / 2, 1.06),
                 arrowprops=dict(arrowstyle='|-|', color=USABLE, lw=0.9, mutation_scale=3))
    axr.text(0, 1.12, 'one 2θ bin %.4f°' % step, color=USABLE, fontsize=8.5, ha='center', va='bottom')
    axr.annotate('', xy=(-res / 2, 1.48), xytext=(res / 2, 1.48),
                 arrowprops=dict(arrowstyle='<->', color=INK, lw=0.9, mutation_scale=8))
    axr.text(0, 1.54, '2θ resolution\n%.3f° = %.2f columns' % (res, res / step), color=INK, fontsize=8.5,
             ha='center', va='bottom')
    axr.set_xlim(-0.6 * res, 0.6 * res)
    axr.set_ylim(0, 1.95)
    axr.set_yticks([])
    axr.spines['left'].set_visible(False)
    axr.set_xlabel('2θ − Det_Th (deg)')
    axr.set_title('column c0, Det_Th %.1f°, S4 %.1f mm' % (deg(g.dth), s4), fontsize=8.5, fontweight='normal',
                  color=INK2, loc='center')
    caption(fig, 'Scans A and B are the first and second halves of scan %d, an illustration of a 2θ overlap; '
                 'bins seen by < min_frames frames are left out.' % LOW_SCAN)
    save(fig, out, '03_frames_cover_two_theta.png')


# ------------------------------------------------------- 4. pixels to cells

def fig_pixels_to_cells(out):
    d = data()
    gp = d.params
    info = d.res.info['levels']
    fig = plt.figure(figsize=(9.6, 10.0))
    specs = [(d.f1, info[0], LV1, 'arm level'), (d.f2, info[1], LV2, 'arm raised')]
    for k, (f, li, col, what) in enumerate(specs):
        g = f.geom
        cols = ph.frame_columns(f, d.ncols)
        rows = np.arange(gp.row_min, gp.row_max + 1)
        rs = np.unique(np.r_[rows[::8], rows[-1]])
        cs = np.unique(np.r_[cols[::8], cols[-1]])
        ax = fig.add_axes([0.08 + 0.47 * k, 0.53, 0.40, 0.38])
        T, Bt = (np.degrees(a) for a in ph.pixel_angles(g, rs, cs))
        for i in range(len(rs)):
            ax.plot(T[i], Bt[i], color=col, lw=0.6)
        for j in range(len(cs)):
            ax.plot(T[:, j], Bt[:, j], color=col, lw=0.6, ls=(0, (3, 2)))
        ax.set_title('Scan %d, Det_Th %.1f°, β0 %.2f° (%s)' % (f.scan, deg(g.dth), deg(g.beta0), what),
                     color=col, fontsize=10)
        ax.set_xlabel('2θ (deg)')
        ax.set_ylabel('β (deg)')
        ax.grid(color=GRID, lw=0.5)
        # how far a row runs in β and a column in 2θ (exact)
        Ta, Ba = (np.degrees(a) for a in ph.pixel_angles(g, [rows[-1]], cols))
        Tc, _ = (np.degrees(a) for a in ph.pixel_angles(g, rows, [cols[-1]]))
        ax.text(0.02, 0.97, 'row %d: β %.2f–%.2f° across the usable columns\ncolumn %d: 2θ spans %.4f° '
                'from row %d to %d' % (rows[-1], Ba.min(), Ba.max(), cols[-1], np.ptp(Tc), rows[0], rows[-1]),
                transform=ax.transAxes, fontsize=8, color=INK2, ha='left', va='top',
                bbox=dict(facecolor='white', edgecolor='none', pad=1.5, alpha=0.9))
        ax.plot([], [], color=col, lw=0.8, label='pixels of one row (every 8th row)')
        ax.plot([], [], color=col, lw=0.8, ls=(0, (3, 2)), label='pixels of one column (every 8th)')
        ax.legend(loc='lower center', fontsize=8, handlelength=2.2, ncol=1)
        span = Bt.max() - Bt.min()
        ax.set_ylim(Bt.min() - 0.30 * span, Bt.max() + 0.25 * span)
        # zoom: the top rows, the high-column end, a few cells
        zr = np.arange(rows[-1] - 7, rows[-1] + 1)
        zc = np.arange(cols[-1] - 7, cols[-1] + 1)
        ZT, ZB = (np.degrees(a) for a in ph.pixel_angles(g, zr, zc))
        e, be = li['edges'], li['beta_edges']
        tc, bc = ZT[3, 3], ZB[3, 3]
        it = int(np.digitize(tc, e) - 1)
        ib = int(np.digitize(bc, be) - 1)
        x0, x1 = e[it - 3], e[it + 4]
        y0, y1 = be[ib - 4], be[ib + 6]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=INK, lw=1.2))
        ax.annotate('zoom below', xy=(x0, y0), xytext=(x0 - 0.25, y0 - 0.12 * span), fontsize=8.5, color=INK,
                    ha='right', va='top', arrowprops=dict(arrowstyle='-', color=INK, lw=0.7),
                    bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
        az = fig.add_axes([0.08 + 0.47 * k, 0.12, 0.40, 0.33])
        for x in e[it - 3:it + 5]:
            az.axvline(x, color='#9a9992', lw=0.8)
        for y in be[ib - 4:ib + 7]:
            az.axhline(y, color='#9a9992', lw=0.8)
        for i in range(len(zr)):
            az.plot(ZT[i], ZB[i], color=col, lw=0.8)
        for j in range(len(zc)):
            az.plot(ZT[:, j], ZB[:, j], color=col, lw=0.8, ls=(0, (3, 2)))
        inside = (np.digitize(ZT, e) - 1 == it) & (np.digitize(ZB, be) - 1 == ib)
        az.plot(ZT[~inside], ZB[~inside], 'o', color=col, ms=4, mfc='white', mew=1.0)
        az.plot(ZT[inside], ZB[inside], 'o', color=col, ms=5.5)
        az.add_patch(Rectangle((e[it], be[ib]), e[it + 1] - e[it], be[ib + 1] - be[ib], fill=False,
                               edgecolor=INK, lw=2.0, zorder=5))
        az.set_xlim(x0, x1)
        az.set_ylim(y0, y1)
        az.set_xlabel('2θ (deg)')
        az.set_ylabel('β (deg)')
        az.ticklabel_format(useOffset=False)
        az.annotate('cell', xy=(e[it + 1], be[ib + 1]), xytext=(e[it + 2] + 0.3 * (e[1] - e[0]), be[ib + 4]),
                    fontsize=9.5, fontweight='bold', color=INK, ha='left', va='center',
                    arrowprops=dict(arrowstyle='-', color=INK, lw=0.9),
                    bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
        yb = be[ib - 4] + 0.25 * (be[1] - be[0])
        az.annotate('', xy=(e[it - 2], yb), xytext=(e[it - 1], yb),
                    arrowprops=dict(arrowstyle='|-|', color=INK, lw=0.9, mutation_scale=3))
        az.text(0.5 * (e[it - 2] + e[it - 1]), yb + 0.3 * (be[1] - be[0]), '2θ bin', fontsize=9, color=INK,
                ha='center', va='bottom', bbox=dict(facecolor='white', edgecolor='none', pad=0.5))
        xb = e[it - 3] + 0.2 * (e[1] - e[0])
        az.annotate('', xy=(xb, be[ib + 4]), xytext=(xb, be[ib + 5]),
                    arrowprops=dict(arrowstyle='|-|', color=INK, lw=0.9, mutation_scale=3))
        az.text(xb + 0.15 * (e[1] - e[0]), 0.5 * (be[ib + 4] + be[ib + 5]), 'β bin', fontsize=9, color=INK,
                ha='left', va='center', bbox=dict(facecolor='white', edgecolor='none', pad=0.5))
        az.set_title('Rows %d–%d, columns %d–%d: every pixel (dot)' % (zr[0], zr[-1], zc[0], zc[-1]),
                     fontsize=9.5, color=col)
    caption(fig, 'Counts and weights of every pixel go to the cell its angles fall in; cell value = ΣN/ΣW. '
                 'Filled dots: the pixels of the outlined cell.')
    save(fig, out, '04_pixels_to_cells.png')


# ------------------------------------------------ 5. levels and overlaps

def level_box(li):
    c = 0.5 * (li['edges'][:-1] + li['edges'][1:])[li['keep']]
    s, bs = li['step_deg'], li['beta_step_deg']
    return c.min() - s / 2, c.max() + s / 2, li['beta'].min() - bs / 2, li['beta'].max() + bs / 2


def fig_levels(out):
    d = data()
    info = d.res.info['levels']
    join = d.res.joins[0]
    (a0, a1, b0, b1), (c0, c1, e0, e1) = level_box(info[0]), level_box(info[1])
    ix0, ix1 = d.res.x.min(), d.res.x.max()
    ux0, ux1 = d.union.x.min(), d.union.x.max()
    fig = plt.figure(figsize=(9.6, 7.4))
    ax = fig.add_axes([0.08, 0.13, 0.56, 0.72])
    ax.add_patch(Rectangle((a0, b0), a1 - a0, b1 - b0, facecolor=LV1, alpha=0.22, edgecolor=LV1, lw=1.6))
    ax.add_patch(Rectangle((c0, e0), c1 - c0, e1 - e0, facecolor=LV2, alpha=0.22, edgecolor=LV2, lw=1.6))
    bc1, bc2 = info[0]['beta'], info[1]['beta']
    ax.text(0.5 * (a0 + a1) + 0.6, 0.5 * (b0 + b1) - 1.5, 'Qz level 1\nscan %d (arm level)\nβ %.2f–%.2f°'
            % (LOW_SCAN, bc1.min(), bc1.max()), color=LV1, fontsize=10, ha='center', va='center', fontweight='bold')
    ax.text(0.5 * (c0 + c1), 0.5 * (join['x_to'] + e1) + 1.0, 'Qz level 2\nscan %d (arm raised)\nβ %.2f–%.2f°'
            % (HIGH_SCAN, bc2.min(), bc2.max()), color=LV2, fontsize=10, ha='center', va='center', fontweight='bold')
    # β overlap where the factor is fitted: the β bins of the join, over the 2θ bins both levels have
    ov0, ov1 = max(a0, c0), min(a1, c1)
    bs = d.res.info['join']['beta_step_deg']
    hatch_rect(ax, ov0, ov1, join['x_from'] - bs / 2, join['x_to'] + bs / 2, OVL, hatch='xxxx', lw=1.2)
    ax.annotate('β overlap: level join factor fitted here\n(β %.2f–%.2f°, %d β bins)'
                % (join['x_from'], join['x_to'], join['points']),
                xy=(ov1, 0.5 * (join['x_from'] + join['x_to'])), xytext=(ov1 + 0.5, 0.5 * (join['x_from'] + join['x_to']) + 0.2),
                color=OVL, fontsize=9.5, ha='left', va='center',
                arrowprops=dict(arrowstyle='-', color=OVL, lw=0.9),
                bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
    # with 'union', the 2θ range of level 1 alone above its top: no data
    hatch_rect(ax, c1, a1, b1, e1, MUTED, hatch='..', lw=0)
    ax.text(0.5 * (c1 + a1), 0.5 * (b1 + e1), "no data\n(NaN with 'union')", color=INK2, fontsize=9,
            ha='center', va='center', bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
    # transverse range brackets above
    ytop = e1 + 0.9
    for (x0, x1, lab, yy, col) in ((ix0, ix1, "transverse range 'intersection' (default, IDL)", ytop, INK),
                                    (ux0, ux1, "transverse range 'union'", ytop + 1.3, INK2)):
        ax.annotate('', xy=(x0, yy), xytext=(x1, yy),
                    arrowprops=dict(arrowstyle='|-|', color=col, lw=1.1, mutation_scale=5))
        ax.text(x0, yy + 0.2, '%s: 2θ %.2f–%.2f°' % (lab, x0, x1), color=col, fontsize=9, ha='left',
                va='bottom')
    ax.plot([ix1, ix1], [b0 - 0.6, ytop], color=INK, lw=0.9, ls='--')
    ax.text(ix1 + 0.05, b0 + 0.4, "'intersection' stops here:\nlevel 1 beyond it is left out", color=INK,
            fontsize=8.5, ha='left', va='bottom', bbox=dict(facecolor='white', edgecolor='none', pad=1.0, alpha=0.85))
    ax.set_xlim(a0 - 0.4, a1 + 0.4)
    ax.set_ylim(b0 - 0.6, ytop + 2.6)
    ax.set_xlabel('2θ (deg)')
    ax.set_ylabel('β (deg)')
    ax.set_title('Pinhole patch (the default): two Qz levels on one 2θ grid', pad=6)
    ax.grid(color=GRID, lw=0.5)
    # legacy edge copies, from the legacy patch of the same scans
    lv = d.legacy.levels
    l1, l2 = d.legacy_levels
    la0, la1 = lv[0][3], lv[0][4]
    lc0, lc1 = lv[1][3], lv[1][4]
    lb0, lb1 = l1.y.min(), l1.y.max()
    le0, le1 = l2.y.min(), l2.y.max()
    axl = fig.add_axes([0.72, 0.30, 0.26, 0.50])
    axl.add_patch(Rectangle((la0, lb0), la1 - la0, lb1 - lb0, facecolor=LV1, alpha=0.22, edgecolor=LV1, lw=1.2))
    axl.add_patch(Rectangle((lc0, le0), max(lc1 - lc0, 0.05), le1 - le0, facecolor=LV2, alpha=0.5,
                            edgecolor=LV2, lw=1.2))
    hatch_rect(axl, lc1, la1, le0, le1, LEG, hatch='////', lw=1.2)
    axl.text(0.5 * (lc1 + la1), 0.5 * (lb1 + le1) + 0.6, 'edge copies\n(legacy only,\nP33)', color=LEG,
             fontsize=9, ha='center', va='center', fontweight='bold',
             bbox=dict(facecolor='white', edgecolor='none', pad=1.0))
    axl.annotate('level 2 measured\n(Det_Th %.1f–%.1f°)' % (lc0, lc1), xy=(lc0 + 0.05, le1 - 0.6),
                 xytext=(lc0 + 0.25, le1 + 1.6), color=LV2, fontsize=8.5, ha='left', va='bottom',
                 arrowprops=dict(arrowstyle='-', color=LV2, lw=0.8))
    axl.text(0.5 * (la0 + la1), 0.5 * (lb0 + lb1), 'level 1', color=LV1, fontsize=9, ha='center',
             va='center', fontweight='bold')
    axl.set_xlim(la0 - 0.3, la1 + 0.3)
    axl.set_ylim(lb0 - 0.6, le1 + 4.2)
    axl.set_xlabel('2θ = Det_Th (deg)')
    axl.set_ylabel('β (deg)')
    axl.set_title('Legacy patch, same scans', fontsize=10, pad=6)
    axl.grid(color=GRID, lw=0.5)
    axl.text(0.0, -0.20, "The legacy vertical join extends\nlevel 2 over level 1's 2θ range\nby copying its "
             "edge column.", transform=axl.transAxes, fontsize=8.5, color=INK2, ha='left', va='top')
    caption(fig, "Each Qz level covers its own (2θ, β) region; the level join factor is fitted on the β overlap, "
                 "and the transverse range sets the map's 2θ range.")
    save(fig, out, '05_levels_and_overlaps.png')


# --------------------------------------------------------- 6. join factor

def join_ratios(levels):
    """Per β bin of the overlap: the mean intensities of the two levels over
    the cells both have (equal weight per cell), their ratio and its error,
    as lss_core.pinhole.join_levels computes them (two levels). Returns a
    dict; the factor must equal the reader's (checked by the caller)."""
    edges = levels[0]['edges']
    nb = len(edges) - 1
    bstep = max(float(np.max(np.abs(np.diff(lv['beta'])))) for lv in levels)
    blo = min(float(lv['beta'].min()) for lv in levels)
    bhi = max(float(lv['beta'].max()) for lv in levels)
    bedges = blo - bstep / 2 + bstep * np.arange(int(math.ceil((bhi - blo) / bstep)) + 2)
    nbeta = len(bedges) - 1
    reb = []
    for lv in levels:
        j = np.clip(np.digitize(lv['beta'], bedges) - 1, 0, nbeta - 1)
        n, w = np.zeros((nb, nbeta)), np.zeros((nb, nbeta))
        kept = lv['keep']
        for r in range(len(j)):
            n[kept, j[r]] += lv['all_counts'][kept, r]
            w[kept, j[r]] += lv['all_weights'][kept, r]
        reb.append((n, w, kept))
    order = sorted(range(len(levels)), key=lambda k: float(levels[k]['beta'].min()))
    (na, wa, ka), (nbb, wb, kb) = reb[order[0]], reb[order[1]]
    cells = (ka & kb)[:, None] & (wa > 0) & (wb > 0)
    m = cells.sum(axis=0)
    with np.errstate(invalid='ignore', divide='ignore'):
        sa, sb = np.where(cells, wa, 1.0), np.where(cells, wb, 1.0)
        pa = np.where(cells, na / sa, 0.0).sum(axis=0) / np.maximum(m, 1)
        pb = np.where(cells, nbb / sb, 0.0).sum(axis=0) / np.maximum(m, 1)
        va = np.where(cells, na / sa ** 2, 0.0).sum(axis=0) / np.maximum(m, 1) ** 2
        vb = np.where(cells, nbb / sb ** 2, 0.0).sum(axis=0) / np.maximum(m, 1) ** 2
    ok = (m > 0) & (pa > 0) & (pb > 0)
    ratio = pa[ok] / pb[ok]
    err = ratio * np.sqrt(va[ok] / pa[ok] ** 2 + vb[ok] / pb[ok] ** 2)
    wt = 1 / err ** 2
    fac = float(np.sum(wt * ratio) / np.sum(wt))
    ferr = float(np.sum(wt) ** -0.5)
    chi2 = float(np.sum(wt * (ratio - fac) ** 2) / max(ok.sum() - 1, 1))
    bc = 0.5 * (bedges[:-1] + bedges[1:])[ok]
    return dict(beta=bc, pa=pa[ok], pb=pb[ok], sa=np.sqrt(va[ok]), sb=np.sqrt(vb[ok]), ratio=ratio, err=err,
                factor=fac, error=ferr, chi2=chi2, cells=m[ok], bstep=bstep)


def fig_join_factor(out):
    d = data()
    info = d.res.info['levels']
    j = join_ratios(info)
    ref = d.res.joins[0]
    assert abs(j['factor'] - ref['factor']) < 1e-9 * ref['factor'] and len(j['beta']) == ref['points'], \
        'the recomputed join differs from lss_core.pinhole.join_levels'
    fig = plt.figure(figsize=(9.6, 8.6))
    # (a) schematic of the cells
    ax = fig.add_axes([0.03, 0.50, 0.45, 0.40])
    ax.set_aspect('equal')
    ax.axis('off')
    nx, ny = 7, 4
    have_a = np.ones((ny, nx), bool)
    have_b = np.zeros((ny, nx), bool)
    have_b[:, :4] = True
    have_a[3, 6] = False
    for iy in range(ny):
        for ix in range(nx):
            if have_a[iy, ix]:
                ax.add_patch(Polygon([(ix, iy), (ix + 1, iy), (ix, iy + 1)], facecolor=LV1, alpha=0.55,
                                     edgecolor='none'))
            if have_b[iy, ix]:
                ax.add_patch(Polygon([(ix + 1, iy), (ix + 1, iy + 1), (ix, iy + 1)], facecolor=LV2, alpha=0.55,
                                     edgecolor='none'))
            both = have_a[iy, ix] and have_b[iy, ix]
            ax.add_patch(Rectangle((ix, iy), 1, 1, fill=False, edgecolor=INK if both else '#9a9992',
                                   lw=1.6 if both else 0.8))
    for iy in range(ny):
        ax.annotate('', xy=(nx + 1.0, iy + 0.5), xytext=(nx + 0.1, iy + 0.5),
                    arrowprops=dict(arrowstyle='-|>', color=INK2, lw=0.9, mutation_scale=9))
        ax.text(nx + 1.15, iy + 0.5, 'r(β) = ⟨I_A⟩ / ⟨I_B⟩', fontsize=8.5, color=INK, va='center', ha='left')
    ax.text(nx / 2, -0.35, '2θ bins →', fontsize=9, color=INK2, ha='center', va='top')
    ax.text(-0.3, -1.1, '⟨I_A⟩, ⟨I_B⟩: mean of the cell values ΣN/ΣW over the outlined cells of that β bin',
            fontsize=8.5, color=INK, ha='left', va='top')
    ax.text(-0.3, ny / 2, 'β bins of the β overlap →', fontsize=9, color=INK2, rotation=90, ha='right', va='center')
    ax.add_patch(Polygon([(0, ny + 0.5), (0.6, ny + 0.5), (0, ny + 1.1)], facecolor=LV1, alpha=0.55))
    ax.text(0.75, ny + 0.8, 'level A (below) has the cell', color=LV1, fontsize=8.5, va='center')
    ax.add_patch(Polygon([(0.6, ny + 1.3), (0.6, ny + 1.9), (0, ny + 1.9)], facecolor=LV2, alpha=0.55))
    ax.text(0.75, ny + 1.6, 'level B (above) has the cell', color=LV2, fontsize=8.5, va='center')
    ax.add_patch(Rectangle((0, ny + 2.1), 0.6, 0.6, fill=False, edgecolor=INK, lw=1.6))
    ax.text(0.75, ny + 2.4, 'both: used, equal weight per cell', color=INK, fontsize=8.5, va='center')
    ax.set_xlim(-1.2, nx + 6.2)
    ax.set_ylim(-1.9, ny + 3.0)
    ax.set_title('(a) Cells of the β overlap (schematic)', fontsize=10, loc='left', x=0.02)
    # (b) the two mean profiles (real)
    axp = fig.add_axes([0.58, 0.55, 0.40, 0.33])
    sc = 10 ** -math.floor(math.log10(float(np.median(j['pa']))))
    ex = int(round(math.log10(sc)))
    axp.errorbar(j['beta'], j['pa'] * sc, j['sa'] * sc, fmt='o', ms=3, color=LV1, lw=0.8,
                 label='⟨I_A⟩ level 1 (scan %d)' % LOW_SCAN)
    axp.errorbar(j['beta'], j['pb'] * sc, j['sb'] * sc, fmt='s', ms=3, color=LV2, mfc='white', lw=0.8,
                 label='⟨I_B⟩ level 2 (scan %d), before the factor' % HIGH_SCAN)
    axp.set_xlabel('β (deg)')
    axp.set_ylabel('mean ΣN/ΣW per cell (10$^{-%d}$)' % ex)
    lo = float(np.min(np.r_[j['pa'] - j['sa'], j['pb'] - j['sb']])) * sc
    hi = float(np.max(np.r_[j['pa'] + j['sa'], j['pb'] + j['sb']])) * sc
    axp.set_ylim(lo - 0.45 * (hi - lo), hi + 0.05 * (hi - lo))
    axp.legend(loc='lower right', fontsize=8)
    axp.set_title('(b) NX %d + %d: mean intensities in the β overlap' % (LOW_SCAN, HIGH_SCAN), fontsize=10)
    axp.grid(color=GRID, lw=0.5)
    # (c) ratio per β bin and the factor
    axr = fig.add_axes([0.08, 0.13, 0.88, 0.28])
    axr.errorbar(j['beta'], j['ratio'], j['err'], fmt='o', ms=3.5, color=OVL, lw=0.8, label='r(β) per β bin ± σ')
    axr.axhspan(j['factor'] - j['error'], j['factor'] + j['error'], color=LV2, alpha=0.25, lw=0)
    axr.axhline(j['factor'], color=LV2, lw=1.8,
                label='level join factor = weighted mean = %.3f ± %.3f' % (j['factor'], j['error']))
    axr.axhline(1.0, color=MUTED, lw=0.8, ls=':')
    axr.set_xlabel('β (deg)')
    axr.set_ylabel('r(β) = ⟨I_A⟩ / ⟨I_B⟩')
    axr.set_title('(c) Ratio per β bin; factor = Σ r w / Σ w with w = 1/σ²;  χ²/dof = %.2f over %d β bins '
                  '(β %.2f–%.2f°)' % (j['chi2'], len(j['beta']), j['beta'].min(), j['beta'].max()), fontsize=10)
    lo, hi = float(np.min(j['ratio'] - j['err'])), float(np.max(j['ratio'] + j['err']))
    axr.set_ylim(lo - 0.05 * (hi - lo), hi + 0.25 * (hi - lo))
    axr.legend(loc='upper left', fontsize=8.5, ncol=2)
    axr.grid(color=GRID, lw=0.5)
    caption(fig, 'Level B is multiplied by the factor (its weights divided by it); the scan join fits its factor '
                 'the same way along 2θ, on rows-summed profiles.')
    save(fig, out, '06_join_factor.png')


FIGURES = {1: fig_frame_anatomy, 2: fig_columns_to_two_theta, 3: fig_frames_cover, 4: fig_pixels_to_cells,
           5: fig_levels, 6: fig_join_factor}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=OUT, help='output folder (default %(default)s)')
    ap.add_argument('--only', type=int, nargs='*', help='diagram numbers to draw (default: all)')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    for k in (a.only or sorted(FIGURES)):
        FIGURES[k](a.out)


if __name__ == '__main__':
    main()
