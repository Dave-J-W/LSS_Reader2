"""Eight figures of the pinhole GID geometry (docs/figures/pinhole).

    python tests/tools/pinhole_figures.py [--out DIR] [--only N ...]

Every point, vector and angle drawn is computed by the reader's own code
(lss_core.pinhole): ``ray_geometry`` (lab-frame ray, footprint → S4 slit →
pixel, also through any point of the S4 opening), ``pixel_angles`` (Mati
Meron's IMG_COO_CONV transform, ported), ``column_two_theta`` /
``row_beta`` (the per-axis approximation), ``footprint_length`` /
``footprint_window`` / ``footprint_columns`` / ``s5_window`` /
``usable_columns``, and for the finite S4 ``column_acceptance`` /
``s4_window`` / ``area_fraction``; the frame parameters are read from the
public NX school SPEC file by tests/tools/pinhole_frames.py. This script
only draws: it adds drawing offsets, arc interpolation between two
directions the reader returned, where a ray crosses the S5 plane (a point
on a ray the reader returned), clipping to a close-up box and convex hulls
for shading, nothing that changes a number. Writes case1_*.png …
case8_*.png into the output folder and nothing else; prints any text that
overlaps other text or leaves the figure.
"""
import argparse
import math
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import replace
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))

import matplotlib                                                    # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                      # noqa: E402
import matplotlib.patheffects as pe                                  # noqa: E402
from matplotlib.patches import FancyArrowPatch                       # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection              # noqa: E402
import numpy as np                                                   # noqa: E402

from lss_core import pinhole as ph                                   # noqa: E402
from pinhole_frames import frames_for                                # noqa: E402

NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
ELEV, AZIM = math.degrees(math.atan(1 / math.sqrt(2))), -45.0       # isometric (35.264°)
DPI = 220

# one colour per kind of vector, the same in every figure (checked with the
# dataviz palette validator: 4 hues, all-pairs normal-vision ΔE ≥ 15, contrast ≥ 3:1);
# S5 and what it lets through: purple (ΔE76 ≥ 28 from every other hue)
C = dict(lab='#6E6E6E', beam='#D0481E', arm='#2A6FD0', det='#0E8C5A', comp='#B5338A',
         ray='#1A1A1A', approx='#7A7A7A', s5='#5E3C99', fp='#8A4A20')
FILL = dict(footprint='#F5CDB3', seen='#C0652A', detector='#CFE1F3', ghost='#EDEDED', slit='#333333',
            s5='#D9CFEA')
HALO = [pe.withStroke(linewidth=3.2, foreground='white')]
Z = np.array([0.0, 0.0, 1.0])
X = np.array([1.0, 0.0, 0.0])


# ---- the frames and the reader's numbers ----------------------------------------

# the data drawn: the public NX file by default; ``--spec``, ``--low``, ``--high``
# choose another file and its low- and high-Qz GID scans (they stand in for NX 11, 12)
DATA = dict(spec=NX, label='NX school 20260923', scans={11: 11, 12: 12})


@lru_cache(maxsize=None)
def _frames(scan):
    return tuple(frames_for(DATA['spec'], [DATA['scans'].get(scan, scan)]))


def frame(scan, dth_deg):
    """The frame of ``scan`` (11: the low-Qz scan, 12: the high-Qz one) whose
    Det_Th is nearest ``dth_deg``."""
    return min(_frames(scan), key=lambda f: abs(math.degrees(f.geom.dth) - dth_deg))


def usable(f):
    """The frame's usable columns (``usable_columns``: S5 and footprint windows)."""
    return ph.usable_columns(f.geom, NC, f.s5[0], f.s5[1], f.areainfo[1], f.s1_to_sample_mm)


def ftp_of(f):
    """Footprint length (mm) of frame ``f`` (``footprint_length``)."""
    return ph.footprint_length(f.geom, f.areainfo[1], f.s1_to_sample_mm)


def true_window(f):
    """The exact footprint window of frame ``f`` (``footprint_columns``, row r0)."""
    return ph.footprint_columns(f.geom, f.areainfo[1], f.s1_to_sample_mm)


def s4_open(f):
    """S4's opening (S4L + S4R, mm) from the header, as two halves (low, high)."""
    return f.areainfo[2] / 2, f.areainfo[2] / 2


NR, NC = _frames(11)[0].counts.shape    # one module, rows × columns, from the NX images (487 × 195)
GAP = 17                                # DECTRIS 200K: 487 × 407 = two 487 × 195 modules and a 17-pixel gap
SECOND = {'low': (-(NC + GAP), -GAP - 1),          # where the 200K's second module would be, in this
          'high': (NC + GAP, 2 * NC + GAP - 1)}     # module's column numbering: −212…−18 or 212…406


def per_axis(g, rows, cols):
    """(2θ, β) in radians by the per-axis formulas (``column_two_theta``,
    ``row_beta``) for any rows and columns, also negative ones (the origin
    of the numbering is shifted; the formulas see the same c − c0)."""
    rows, cols = np.atleast_1d(rows), np.atleast_1d(cols)
    k = int(max(0, -cols.min()))
    tt = ph.column_two_theta(int(cols.max()) + k + 1, replace(g, c0=g.c0 + k))[cols + k]
    bb = ph.row_beta(int(rows.max()) + 1, g)[rows]
    return tt, bb


def module_corners(g, c_lo=0, c_hi=None):
    """The four outer corners of a module (pixel edges), lab frame."""
    c_hi = NC - 1 if c_hi is None else c_hi
    return [ph.ray_geometry(g, r, c).pixel for r, c in
            ((-0.5, c_lo - 0.5), (-0.5, c_hi + 0.5), (NR - 0.5, c_hi + 0.5), (NR - 0.5, c_lo - 0.5))]


def slit_segment(rays, margin=0.15):
    """The part of the S4 slit line the given rays cross, widened by ``margin``."""
    r0 = rays[0]
    t = [np.dot(r.slit - r0.slit_centre, r0.e_v) for r in rays]
    lo, hi = min(t), max(t)
    pad = margin * max(hi - lo, 10.0)
    return r0.slit_centre + (lo - pad) * r0.e_v, r0.slit_centre + (hi + pad) * r0.e_v


def column_at_source(g, x, row=None):
    return ph.column_at_source(g, x, row)


def deg(x):
    return math.degrees(x)


# ---- drawing ---------------------------------------------------------------------

class Arrow3D(FancyArrowPatch):
    def __init__(self, a, b, **kw):
        super().__init__((0, 0), (0, 0), **kw)
        self._ab = (np.asarray(a, float), np.asarray(b, float))

    def do_3d_projection(self, renderer=None):
        M = self.axes.get_proj()
        p = [M @ np.r_[v, 1.0] for v in self._ab]
        self.set_positions(*[(q[0] / q[3], q[1] / q[3]) for q in p])
        return min(q[2] / q[3] for q in p)


def _clip(a, b, lo, hi):
    """Segment a-b clipped to the box [lo, hi] (Liang-Barsky); None if outside."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    t0, t1 = 0.0, 1.0
    for i in range(3):
        for p, q in ((-d[i], a[i] - lo[i]), (d[i], hi[i] - a[i])):
            if abs(p) < 1e-15:
                if q < 0:
                    return None
            else:
                t = q / p
                if p < 0:
                    t0 = max(t0, t)
                else:
                    t1 = min(t1, t)
    if t0 > t1:
        return None
    return a + t0 * d, a + t1 * d


class Iso:
    """One isometric (orthographic) 3D panel at true scale. Labels are placed
    after the projection is fixed: along their vector, parallel to its
    projected direction on screen, in the vector's colour."""

    def __init__(self, fig, rect, title=None, box=None):
        self.fig = fig
        self.rect = rect                       # where the drawing goes (figure fraction); see fit()
        self.ax = fig.add_axes(rect, projection='3d', proj_type='ortho')
        self.ax.view_init(elev=ELEV, azim=AZIM, roll=0)
        self.ax.set_axis_off()
        self.ax.computed_zorder = False
        self.box = None if box is None else (np.asarray(box[0], float), np.asarray(box[1], float))
        self.pts, self.labels = [], []
        self.title = title

    def _seg(self, a, b):
        if self.box is None:
            return np.asarray(a, float), np.asarray(b, float)
        return _clip(a, b, *self.box)

    def line(self, pts, color, lw=1.2, ls='-', z=3, alpha=1.0):
        pts = np.asarray(pts, float)
        for a, b in zip(pts[:-1], pts[1:]):
            s = self._seg(a, b)
            if s is None:
                continue
            self.ax.plot(*np.array(s).T, color=color, lw=lw, ls=ls, zorder=z, alpha=alpha, solid_capstyle='round',
                         clip_on=False)
            self.pts.extend(s)

    def arrow(self, a, b, color, label=None, where=0.5, side=1, off=8, lw=1.7, both=False, z=4, size=11,
              ls='-', head=True):
        s = self._seg(a, b)
        if s is None:
            return
        tip_inside = np.allclose(s[1], b)
        style = ('<|-|>' if both else '-|>') if head and tip_inside else '-'
        self.ax.add_artist(Arrow3D(s[0], s[1], arrowstyle=style, mutation_scale=13, color=color, lw=lw, ls=ls,
                                   shrinkA=0, shrinkB=0, zorder=z, clip_on=False))
        self.pts.extend(s)
        if label:
            self.labels.append(('along', s[0], s[1], label, color, where, side, off, size))

    def poly(self, corners, face, edge, z=1, alpha=1.0, ls='-', lw=1.0):
        pc = Poly3DCollection([np.asarray(corners, float)], facecolor=face, edgecolor=edge, linewidths=lw,
                              linestyles=ls, alpha=alpha, zorder=z)
        self.ax.add_collection3d(pc)
        pc.set_clip_on(False)
        self.pts.extend(np.asarray(corners, float))

    def point(self, p, color, label=None, dx=6, dy=6, ms=4.5, ha='left', va='bottom', size=10, z=6,
              leader=False, marker='o'):
        if self.box is not None and not (np.all(p >= self.box[0]) and np.all(p <= self.box[1])):
            return
        self.ax.plot(*np.asarray(p, float)[:, None], marker, color=color, ms=ms, zorder=z,
                     mec=color if marker in 'x+' else 'white', mew=1.6 if marker in 'x+' else 0.8, clip_on=False)
        self.pts.append(np.asarray(p, float))
        if label:
            self.labels.append(('point', p, None, label, color, (dx, dy), (ha, va), leader, size))

    def arc(self, centre, a, b, radius, color, label=None, n=60, lw=1.4, dx=0, dy=0, size=11, out=12):
        """Arc from direction a to direction b (unit vectors), at ``radius``."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        om = math.acos(np.clip(np.dot(a, b), -1, 1))
        t = np.linspace(0, 1, n)
        dirs = [(math.sin((1 - s) * om) * a + math.sin(s * om) * b) / math.sin(om) for s in t]
        pts = [centre + radius * d for d in dirs]
        self.line(pts, color, lw=lw)
        if label:
            mid = dirs[n // 2]
            self.labels.append(('radial', centre, centre + radius * mid, label, color, (dx, dy), out, 0, size))

    def finish(self, pad=0.06, zoom=1.0):
        if self.box is not None:
            lo, hi = self.box
        else:
            p = np.array(self.pts)
            lo, hi = p.min(axis=0), p.max(axis=0)
            lo, hi = lo - pad * (hi - lo).max() * 0.3, hi + pad * (hi - lo).max() * 0.3
        self.ax.set_xlim(lo[0], hi[0])
        self.ax.set_ylim(lo[1], hi[1])
        self.ax.set_zlim(lo[2], hi[2])
        self.ax.set_box_aspect(tuple(hi - lo), zoom=zoom)
        self.lo, self.hi, self._zoom = lo, hi, zoom

    def fit(self, fill=0.9):
        """Scale (the box zoom) and move the panel so that its drawing fills
        ``self.rect``: a 3D axes is square and its scene would otherwise use a
        fraction of a wide panel. Artists are not clipped to the axes."""
        fig = self.fig
        W, H = fig.bbox.width, fig.bbox.height
        x0, y0, w, h = self.rect
        if self.title:
            h -= 0.035                                 # keep the panel title's line free
        tc = np.array([(x0 + w / 2) * W, (y0 + h / 2) * H])
        for _ in range(3):
            fig.canvas.draw()
            d = np.array([self.to_display(p) for p in self.pts])
            lo, hi = d.min(axis=0), d.max(axis=0)
            pos = self.ax.get_position()
            ac = np.array([(pos.x0 + pos.width / 2) * W, (pos.y0 + pos.height / 2) * H])
            k = fill * min(w * W / max(hi[0] - lo[0], 1), h * H / max(hi[1] - lo[1], 1))
            self._zoom *= k
            self.ax.set_box_aspect(tuple(self.hi - self.lo), zoom=self._zoom)
            c = 0.5 * (lo + hi)
            shift = tc - (ac + k * (c - ac))
            p0 = self.ax.get_position(original=True)
            self.ax.set_position([p0.x0 + shift[0] / W, p0.y0 + shift[1] / H, p0.width, p0.height])
        fig.canvas.draw()

    def to_display(self, p):
        M = self.ax.get_proj()
        q = M @ np.r_[np.asarray(p, float), 1.0]
        return self.ax.transData.transform((q[0] / q[3], q[1] / q[3]))

    def to_data2d(self, p):
        M = self.ax.get_proj()
        q = M @ np.r_[np.asarray(p, float), 1.0]
        return q[0] / q[3], q[1] / q[3]

    def scale(self):
        """Display pixels per mm (the same along every axis: equal aspect)."""
        c = 0.5 * (self.lo + self.hi)
        return np.linalg.norm(self.to_display(c + Z * 10) - self.to_display(c)) / 10

    def place_labels(self):
        ax = self.ax
        for kind, a, b, text, color, p1, p2, off, size in self.labels:
            kw = dict(color=color, fontsize=size, annotation_clip=False, zorder=20, path_effects=HALO)
            if kind == 'along':
                da, db = self.to_display(a), self.to_display(b)
                d = db - da
                L = np.hypot(*d)
                u = d / L if L > 0 else np.array([1.0, 0.0])
                ang = math.degrees(math.atan2(u[1], u[0]))
                if len(re.sub(r'\\math\w+|[${}_\\]', '', text)) <= 2:
                    ang = 0.0                                    # n, x, w_y, e_v …: rotated they read as other letters
                elif ang > 95:                                     # keep text upright (near-vertical: bottom to top)
                    ang -= 180
                elif ang <= -85:
                    ang += 180
                nrm = np.array([-u[1], u[0]])
                if nrm[1] < 0 or (abs(nrm[1]) < 1e-9 and nrm[0] < 0):
                    nrm = -nrm                                   # side +1: above the vector on screen
                anchor = a + p1 * (np.asarray(b) - np.asarray(a))
                o = p2 * off * nrm if p2 else off * u            # side 0: beyond the tip, on the vector's line
                ax.annotate(text, xy=self.to_data2d(anchor), xycoords='data', xytext=(o[0], o[1]),
                            textcoords='offset points', rotation=ang, rotation_mode='anchor',
                            ha='center', va='center', **kw)
            elif kind == 'point':
                if off:
                    kw['arrowprops'] = dict(arrowstyle='-', color=color, lw=0.6, alpha=0.6, shrinkA=2, shrinkB=2)
                ax.annotate(text, xy=self.to_data2d(a), xycoords='data', xytext=p1, textcoords='offset points',
                            ha=p2[0], va=p2[1], **kw)
            elif kind == 'radial':
                dc, dm = self.to_display(a), self.to_display(b)
                u = (dm - dc) / max(np.hypot(*(dm - dc)), 1e-9)
                o = u * p2 + np.array(p1)
                ax.annotate(text, xy=self.to_data2d(b), xycoords='data', xytext=(o[0], o[1]),
                            textcoords='offset points', ha='center', va='center', **kw)
        if self.title:
            t = self.title() if callable(self.title) else self.title
            self.fig.text(self.rect[0] + 0.01, self.rect[1] + self.rect[3], t, fontsize=10.5, va='top', ha='left',
                          color='#222222')


def lab_axes(iso, length, origin=(-150, 120, 0), labels=True):
    """The lab x, y, z directions, drawn as a triad beside the set-up."""
    o = np.asarray(origin, float)
    for v, s in ((X, 'x'), (np.array([0, 1.0, 0]), 'y'), (Z, 'z')):
        iso.arrow(o, o + length * v, C['lab'], s if labels else None, where=1.0, side=0, off=8, lw=1.1, size=10)


def scene(iso, g, f, rays, det=True, beam_from=-180.0, slit=True):
    """Footprint (``footprint_length`` × S1h), incoming beam, arm, S4 slit
    line (the part ``rays`` cross) and the module outline."""
    ftp = ph.footprint_length(g, f.areainfo[1], f.s1_to_sample_mm)
    s1h = f.areainfo[0]
    iso.poly([(-ftp / 2, -s1h / 2, 0), (ftp / 2, -s1h / 2, 0), (ftp / 2, s1h / 2, 0), (-ftp / 2, s1h / 2, 0)],
             FILL['footprint'], '#B0602E', z=1, lw=0.8)
    if beam_from is not None:
        iso.arrow(X * beam_from, X * (-ftp / 2), C['beam'], r'$\mathbf{k}_\mathrm{in}$', where=0.45, side=1,
                  lw=2.2)
        iso.line([X * (-ftp / 2), X * (ftp / 2)], C['beam'], lw=1.0, ls=(0, (2, 2)))
    if slit:
        a, b = slit_segment(rays)
        iso.line([a, b], FILL['slit'], lw=3.0, z=5)
    if det:
        iso.poly(module_corners(g), FILL['detector'], '#4A6F96', z=1, lw=0.9)
    return ftp


def ray_line(iso, r, label=None, where=0.35, side=1, lw=1.1, ls='-', color=None, off=8, size=10):
    """The ray drawn as source → slit → pixel (a straight line through the slit)."""
    color = color or C['ray']
    iso.line([r.source, r.slit], color, lw=lw, ls=ls, z=3)
    iso.arrow(r.slit, r.pixel, color, label, where=where, side=side, lw=lw, ls=ls, off=off, size=size)


def caption(fig, title, what, source, src_line=None):
    """Title and provenance at the top; at the bottom at most two short
    lines: what the figure shows, and the functions its numbers come from.
    Longer explanations are in docs/figures/pinhole/README.md."""
    fig.text(0.02, 0.985, title, fontsize=13.5, fontweight='bold', va='top', ha='left', color='#111111')
    fig.text(0.02, 0.955, src_line, fontsize=7.5, va='top', ha='left', color='#555555')
    minus = lambda t: re.sub(r'(?<![\w.])-(?=\d)', '−', t)
    fig.text(0.02, 0.034, minus(what), fontsize=9.5, va='bottom', ha='left', color='#222222')
    fig.text(0.02, 0.012, 'Numbers from lss_core.pinhole: ' + source, fontsize=8.5, va='bottom', ha='left',
             color='#555555')


def text_overlaps(fig):
    """Pairs of texts whose boxes overlap, and texts outside the figure."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    ticks = set()
    for ax in fig.findobj(matplotlib.axes.Axes):                   # also insets and secondary axes
        for axis in (ax.xaxis, ax.yaxis):
            ticks.update(id(t) for t in axis.get_ticklabels(which='both'))
    texts = [t for t in fig.findobj(matplotlib.text.Text)
             if t.get_visible() and t.get_text().strip() and id(t) not in ticks]
    boxes = [(t, matplotlib.text.Text.get_window_extent(t, r)) for t in texts]     # text only, not leaders
    W, H = fig.bbox.width, fig.bbox.height
    out = []
    for i, (t, b) in enumerate(boxes):
        if b.x0 < 0 or b.y0 < 0 or b.x1 > W or b.y1 > H:
            out.append(('outside', t.get_text()[:30], ''))
        for t2, b2 in boxes[i + 1:]:
            if b.overlaps(b2):
                out.append(('overlap', t.get_text()[:30], t2.get_text()[:30]))
    return out


def name_scans(fig):
    """Fill the placeholders <LOW>, <HIGH>, <DATA> in the figure's texts with
    the data drawn (NX scan 11, 12 by default)."""
    from matplotlib.text import Text
    low = '%s scan %d' % (DATA['label'], DATA['scans'][11])
    high = 'scan %d' % DATA['scans'][12]
    for t in fig.findobj(Text):
        txt = t.get_text()
        if '<' in txt:
            t.set_text(txt.replace('<LOW>', low).replace('<HIGH>', high).replace('<DATA>', DATA['label']))


def save(fig, isos, path, late=()):
    name_scans(fig)
    for iso in isos:
        iso.fit()                                      # fixes the projections
    for iso in isos:
        iso.place_labels()
    for fn in late:                                    # labels that need the final layout
        fn()
    name_scans(fig)
    problems = text_overlaps(fig)
    for p in problems:
        print('  %s: %r %r' % p)
    fig.savefig(path, dpi=DPI, facecolor='white')
    plt.close(fig)
    print('wrote', os.path.relpath(path, ROOT))


def provenance(f):
    try:
        rev = subprocess.run(['git', 'describe', '--always', '--dirty'], cwd=ROOT, capture_output=True,
                             text=True).stdout.strip()
    except OSError:
        rev = '?'
    return ('tests/tools/pinhole_figures.py · lss_core %s · %s scan %d, Det_Th %.1f°'
            % (rev, DATA['label'], f.scan, deg(f.geom.dth)))


def mag_note(main, close):
    return '×%.0f vs (a)' % (close.scale() / main.scale())


def plan_magnification(ax):
    """How much more a plan view's vertical axis is stretched than its
    horizontal one (both in mm): the drawing's exaggeration across the arm."""
    fig = ax.figure
    pos = ax.get_position()
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    return (pos.height * fig.bbox.height / abs(y1 - y0)) / (pos.width * fig.bbox.width / abs(x1 - x0))


TOP = [0.0, 0.50, 1.0, 0.42]             # panel (a): the whole set-up, full width
BOT = 0.08                               # the lower band starts here, above the two-line caption


def new_fig():
    return plt.figure(figsize=(13, 10), dpi=DPI)


# ---- S5 and the footprint's reach, drawn in any panel ----------------------------

BLADE = 10.0          # mm of each S5 blade drawn beyond its edge (a drawing choice)
ALLOW_GAP = 4.0       # the S5 allowance is drawn this far (mm) beside the footprint's edge (a drawing offset)


def at_s5(r, d5=ph.S5_TO_DETECTOR_MM):
    """Where the ray ``r`` (from ray_geometry) crosses the S5 plane, d5 in
    front of the detector and perpendicular to the arm: a point on the ray."""
    d = r.pixel - r.slit
    return r.pixel - d * (d5 / d.dot(r.n))


def s5_point(g, lateral, wy=0.0, d5=ph.S5_TO_DETECTOR_MM):
    """A point of the S5 plane: ``lateral`` mm towards higher columns (−e_h)
    from the arm's axis, ``wy`` mm along e_v (ray_geometry's frame)."""
    r = ph.ray_geometry(g, g.r0, g.c0)
    return r.centre - d5 * r.n - lateral * r.e_h + wy * r.e_v


def s5_blades(iso, g, f, blade=BLADE):
    """The two S5 blades (S5L towards low columns, S5R towards high ones, as
    s5_window), as tall as the module."""
    lo, hi = -f.s5[0], f.s5[1]
    ylo, yhi = (-0.5 - g.r0) * ph.PIXEL_MM, (NR - 0.5 - g.r0) * ph.PIXEL_MM
    for a, b in ((lo - blade, lo), (hi, hi + blade)):
        iso.poly([s5_point(g, a, ylo), s5_point(g, b, ylo), s5_point(g, b, yhi), s5_point(g, a, yhi)],
                 FILL['s5'], C['s5'], z=2, lw=0.8, alpha=0.9)


def allowance_offset(f):
    return np.array([0.0, -(f.areainfo[0] / 2 + ALLOW_GAP), 0.0])


def reach(iso, g, f, allowance=True, blades=True, lw=1.0, edges=True):
    """The footprint's reach against the S5 allowance, on row r0: the rays
    from the footprint's two ends through S4 (footprint_columns; stopped at
    S5, marked ×, when S5 does not pass their column), the S5 blades, the
    rays through S5's edges (s5_window) back to the beam axis, and there the
    stretch S5 lets through (drawn beside the footprint)."""
    ends = true_window(f)
    s5lo, s5hi = ph.s5_window(g, *f.s5)
    if blades:
        s5_blades(iso, g, f)
    info = dict(ends=ends, s5=(s5lo, s5hi), rays={}, stops={}, src={})
    for c in ends:
        r = ph.ray_geometry(g, g.r0, c)
        info['rays'][c] = r
        iso.line([r.source, r.slit], C['ray'], lw=lw)
        if s5lo <= c <= s5hi:
            iso.arrow(r.slit, r.pixel, C['ray'], lw=lw)
        else:
            stop = at_s5(r)
            iso.line([r.slit, stop], C['ray'], lw=lw)
            iso.line([stop, r.pixel], C['ray'], lw=0.7, ls=(0, (1, 2)), alpha=0.6)
            iso.point(stop, C['s5'], ms=6, marker='x', z=7)
            info['stops'][c] = stop
        iso.point(r.source, C['ray'], ms=3.5)
    for c in (s5lo, s5hi):
        r = ph.ray_geometry(g, g.r0, c)
        if edges:
            iso.line([r.source, r.slit, r.pixel], C['s5'], lw=0.9, ls=(0, (4, 2)), z=3)
        info['src'][c] = r.source
    if allowance:
        off = allowance_offset(f)
        a, b = info['src'][s5lo] + off, info['src'][s5hi] + off
        iso.line([a, b], C['s5'], lw=3.0, z=2)
        for e in (a, b):
            iso.line([e - off, e], C['s5'], lw=0.6, ls=(0, (1, 1.5)))
        info['allow'] = (a, b)
    return info


def signed(v, fmt='%.1f'):
    return (fmt % v).replace('-', '−')


def fmt_cols(a, b, fmt='%.1f'):
    return signed(a, fmt) + '…' + signed(b, fmt)


# ---- the cases ---------------------------------------------------------------------

def case1(out):
    """The lab frame and the detector's own coordinates."""
    f = frame(11, 16.0)
    g = f.geom
    use = usable(f)
    P = (300, int(use[-1]))                          # a pixel that gets light: the last usable column
    rp = ph.ray_geometry(g, *P)
    corners = [ph.ray_geometry(g, r, c) for r, c in ((0, 0), (NR - 1, NC - 1))]
    D, Dp = ph.vertical_distance(g), ph.pinhole_distance(g)
    ftp = ftp_of(f)
    fig = new_fig()
    a = Iso(fig, TOP, '(a) true scale — a ray starts on the footprint, passes the S4 pinhole and lands on one pixel')
    scene(a, g, f, [rp] + corners)
    info = reach(a, g, f, allowance=False, edges=False)
    lab_axes(a, 60, origin=(-150, 120, 0))
    a.line([np.zeros(3), rp.centre], C['arm'], lw=1.0, ls=(0, (5, 3)))
    a.arrow(28 * rp.e_v, rp.centre + 28 * rp.e_v, C['arm'], r'$D$ = %.1f mm' % D, where=0.3, side=1, both=True,
            lw=1.0)
    a.arrow(rp.slit_centre - 34 * rp.e_v, rp.centre - 34 * rp.e_v, C['arm'], r'$D_p$ = %.0f mm' % Dp, where=0.5,
            side=-1, both=True, lw=1.0)
    ray_line(a, rp, 'ray to P: 2θ %.3f°, β %.3f°' % (deg(rp.two_theta), deg(rp.beta)), where=0.42, side=1,
             size=9)
    a.point(rp.source, C['ray'], 'F', dx=2, dy=8, ha='left', va='bottom')
    a.point(rp.slit, C['ray'], 'S4', dx=-6, dy=8, ha='right')
    a.point(rp.pixel, C['ray'], 'P', dx=6, dy=4)
    a.point(X * (-ftp / 4), C['fp'], 'footprint %.1f × %.1f mm' % (ftp, f.areainfo[0]), dx=-20, dy=-40,
            ha='right', va='top', size=9, ms=0.1, leader=True)
    lo_c, hi_c = info['ends']
    a.point(info['rays'][hi_c].source, C['ray'], 'downstream end → column %.1f' % hi_c, dx=24, dy=-44,
            ha='left', va='top', size=8.5, ms=0.1, leader=True)
    a.point(info['stops'][lo_c], C['s5'], 'upstream end → column %.1f:\nstopped by S5' % lo_c, dx=-14, dy=-34,
            ha='right', va='top', size=8.5, ms=0.1, leader=True)
    a.point(s5_point(g, f.s5[1] + BLADE, (NR - 0.5 - g.r0) * ph.PIXEL_MM), C['s5'],
            'S5: %.1f | %.1f mm' % f.s5, dx=4, dy=6, ha='left', size=9, ms=0.1)
    a.finish()

    lo = rp.centre - np.array([50, 50, 50])
    hi = rp.centre + np.array([50, 50, 50])
    b = Iso(fig, [0.0, BOT, 1.0, 0.34], None, box=(lo, hi))
    b.poly(module_corners(g), FILL['detector'], '#4A6F96', z=1, lw=0.9)
    U = 20.0
    b.arrow(rp.centre, rp.centre + U * rp.n, C['arm'], r'$\mathbf{n}$', where=0.8, side=-1)
    b.arrow(rp.centre, rp.centre + U * rp.e_h, C['det'], r'$\mathbf{e}_h$', where=0.75, side=-1)
    b.arrow(rp.centre, rp.centre + U * rp.e_v, C['det'], r'$\mathbf{e}_v$', where=0.8, side=-1)
    corner = rp.centre + rp.wx * rp.e_h
    b.arrow(rp.centre, corner, C['comp'], r'$w_x$', where=0.6, side=-1, lw=2.0, off=13)
    b.arrow(corner, rp.pixel, C['comp'], r'$w_y$', where=0.5, side=1, lw=2.0)
    b.point(0.5 * (rp.centre + corner), C['comp'], r'$w_x = -(c - c_0)\,p$ = %s mm' % signed(rp.wx, '%.2f'),
            dx=-70, dy=-34, ha='right', va='top', size=9.5, ms=0.1, leader=True)
    b.point(corner + 0.6 * (rp.pixel - corner), C['comp'], r'$w_y = (r - r_0)\,p$ = %.2f mm' % rp.wy,
            dx=-60, dy=0, ha='right', va='center', size=9.5, ms=0.1, leader=True)
    ray_line(b, rp, 'ray', where=0.5, side=1)
    b.line([rp.slit_centre, rp.centre], C['arm'], lw=1.0, ls=(0, (5, 3)))
    b.point(rp.centre, C['arm'], r'direct beam $(r_0, c_0)$ = (%d, %d)' % (g.r0, g.c0), dx=60, dy=14, ha='left',
            va='bottom', leader=True, size=9.5)
    b.point(rp.pixel, C['ray'], 'P (row %d, column %d)' % P, dx=8, dy=2, size=9.5)
    b.point(module_corners(g)[2], '#4A6F96', 'module %d × %d pixels, p = %.3f mm' % (NR, NC, ph.PIXEL_MM), dx=10,
            dy=0, ha='left', va='center', size=9, ms=0.1)
    b.finish()
    b.title = lambda: ('(b) close-up (%s) — P = D·n + wx·e_h + wy·e_v; wx < 0 because e_h points to lower 2θ '
                       '(unit vectors drawn %.0f mm)' % (mag_note(a, b), U))
    caption(fig, 'Case 1 — Lab frame, arm and the detector\'s coordinates',
            'x along the beam (k_in), z up, origin at the sample centre; arm at Det_Th = %.1f°, β0 = %.2f°. '
            'Purple: the S5 slit (× where it stops the ray from the footprint\'s upstream end).' % (deg(g.dth), deg(g.beta0)),
            'ray_geometry (every point and vector), footprint_length, footprint_columns, s5_window, '
            'pixel_angles (2θ, β of P agree).', provenance(f))
    save(fig, [a, b], os.path.join(out, 'case1_lab_frame_and_detector.png'))


def case2(out):
    """Where the per-axis formulas are exact: the direct-beam row and column."""
    f = frame(11, 16.0)
    g = f.geom
    A, B = (int(g.r0), int(usable(f)[-1])), (400, int(g.c0))     # both in usable_columns
    ra, rb = ph.ray_geometry(g, *A), ph.ray_geometry(g, *B)
    fig = new_fig()
    a = Iso(fig, [0.0, BOT + 0.04, 0.64, 0.80], '(a) true scale — rays to A (row r0) and B (column c0)')
    scene(a, g, f, [ra, rb, ph.ray_geometry(g, NR - 1, 0)])
    s5_blades(a, g, f)
    lab_axes(a, 60)
    a.line([ph.ray_geometry(g, g.r0, -0.5).pixel, ph.ray_geometry(g, g.r0, NC - 0.5).pixel], C['det'], lw=2.2, z=2)
    a.line([ph.ray_geometry(g, -0.5, g.c0).pixel, ph.ray_geometry(g, NR - 0.5, g.c0).pixel], C['det'], lw=2.2, z=2)
    ray_line(a, ra, 'ray A', where=0.55, side=-1)
    ray_line(a, rb, 'ray B', where=0.78, side=1)
    tpa_a, bpa_a = (deg(v[0]) for v in per_axis(g, A[0], A[1]))
    tpa_b, bpa_b = (deg(v[0]) for v in per_axis(g, B[0], B[1]))
    a.point(ra.pixel, C['ray'], 'A: row r0, column %d\nβ exact %.4f°, per-axis %.4f°' % (A[1], deg(ra.beta), bpa_a),
            dx=-60, dy=-70, ha='right', va='top', size=8.5, leader=True)
    a.point(rb.pixel, C['ray'], 'B: column c0, row %d\nβ exact = per-axis = %.4f°' % (B[0], deg(rb.beta)),
            dx=-30, dy=70, ha='right', va='bottom', size=8.5, leader=True)
    a.point(ra.source, C['ray'], r'$F_A$', dx=6, dy=-14)
    a.point(rb.source, C['ray'], r'$F_B$', dx=-6, dy=-14, ha='right')
    a.point(ph.ray_geometry(g, g.r0, -0.5).pixel, C['det'], 'row r0, column c0:\nthe green cross', dx=-270, dy=-50,
            ha='right', va='top', size=8.5, ms=0.1, leader=True)
    a.point(s5_point(g, f.s5[1] + BLADE, (NR - 0.5 - g.r0) * ph.PIXEL_MM), C['s5'], 'S5', dx=4, dy=4, size=9,
            ms=0.1)
    hb = np.array([rb.direction[0], rb.direction[1], 0.0])
    hb /= np.linalg.norm(hb)
    ha_ = np.array([ra.direction[0], ra.direction[1], 0.0])
    ha_ /= np.linalg.norm(ha_)
    a.line([ra.source, ra.source + 260 * X], C['lab'], lw=0.8, ls=(0, (3, 3)))
    a.arc(ra.source, X, ha_, 230, C['ray'], r'$2\theta_A$ = %.3f°' % deg(ra.two_theta), out=30, size=10)
    a.line([rb.source, rb.source + 420 * hb], C['lab'], lw=0.8, ls=(0, (3, 3)))
    a.arc(rb.source, hb, rb.direction, 400, C['ray'])
    a.point(rb.source + 400 * rb.direction, C['ray'], r'$\beta_B$ = %.3f°' % deg(rb.beta), dx=-2, dy=10,
            ha='center', va='bottom', size=10, ms=0.1)
    a.finish()

    # (b) per-axis minus exact β over the module: zero along the direct-beam row and column
    rows, cols = np.arange(NR), np.arange(NC)
    tt, bb = ph.pixel_angles(g, rows, cols)
    tpa, bpa = per_axis(g, rows, cols)
    db = np.degrees(bpa[:, None] - bb)
    bx = fig.add_axes([0.70, 0.17, 0.2, 0.70])
    lim = np.abs(db).max()
    im = bx.imshow(db, origin='lower', cmap='coolwarm', vmin=-lim, vmax=lim, aspect='equal',
                   extent=(-0.5, NC - 0.5, -0.5, NR - 0.5))
    bx.axhline(g.r0, color=C['det'], lw=1.5)
    bx.axvline(g.c0, color=C['det'], lw=1.5)
    bx.axvspan(usable(f)[0] - 0.5, usable(f)[-1] + 0.5, ymin=0, ymax=0.012, color='#4A6F96', lw=0)
    for (r, c), name in ((A, 'A'), (B, 'B')):
        bx.plot([c], [r], 'o', color=C['ray'], ms=5, mec='white')
        bx.annotate(name, (c, r), xytext=(5, 5) if name == 'A' else (-6, 5), textcoords='offset points',
                    fontsize=10, ha='left' if name == 'A' else 'right', path_effects=HALO)
    bx.text(0.5 * (usable(f)[0] + usable(f)[-1]), 8, 'usable', color='#4A6F96', fontsize=8, ha='center',
            va='bottom', path_effects=HALO)
    bx.text(NC - 4, g.r0 - 8, r'row $r_0$: 0', color=C['det'], ha='right', va='top', fontsize=9, path_effects=HALO)
    bx.text(g.c0 + 4, 0.62 * NR, r'column $c_0$: 0', color=C['det'], ha='left', va='top', fontsize=9,
            rotation=90, path_effects=HALO)
    hf = frame(12, 14.0)                              # the raised arm: row r0 is no longer exact
    hg = hf.geom
    _, bh = ph.pixel_angles(hg, [hg.r0], cols)
    _, bhp = per_axis(hg, [hg.r0], cols)
    dh = np.degrees(np.abs(bhp[0] - bh[0]))
    fig.text(0.03, 0.80, 'With the arm raised (<HIGH>, β0 = %.1f°) row r0 is no longer exact:\n'
             'β per-axis is off by up to %.2f° along it (%.2f° inside the usable columns).'
             % (deg(hg.beta0), dh.max(), dh[usable(hf)].max()), fontsize=9, color=C['det'], va='top')
    k = np.unravel_index(np.argmax(np.abs(db)), db.shape)
    bx.annotate('%s°' % signed(db[k], '%.2f'), (k[1], k[0]), xytext=(-30, -40), textcoords='offset points',
                fontsize=9, ha='right', va='top', path_effects=HALO,
                arrowprops=dict(arrowstyle='-', color='#333333', lw=0.6))
    bx.set_xlabel('column', fontsize=9)
    bx.set_ylabel('row', fontsize=9)
    bx.tick_params(labelsize=8)
    bx.set_title('(b) β per-axis − exact (°):\nzero only on the green cross', fontsize=10, loc='left')
    cb = fig.colorbar(im, ax=bx, fraction=0.08, pad=0.03)
    cb.ax.tick_params(labelsize=8)
    caption(fig, 'Case 2 — Per-axis angles: exact on the direct-beam column, on the row only with the arm level',
            'Per-axis angles (one 2θ per column, one β per row) against the exact ones, <LOW> (β0 = %.2f°). '
            'Elsewhere each column sees another footprint point (cases 3, 4).' % deg(g.beta0),
            'ray_geometry (rays, F, arcs), pixel_angles (exact; IMG_COO_CONV, Mati Meron) minus '
            'column_two_theta / row_beta.', provenance(f))
    save(fig, [a], os.path.join(out, 'case2_direct_beam_row_and_column.png'))


def spread_labels(ys, gap):
    """Label heights near ``ys`` (any order), at least ``gap`` apart."""
    order = np.argsort(ys)
    out = np.array(ys, float)
    for k in range(1, len(order)):
        a, b = order[k - 1], order[k]
        out[b] = max(out[b], out[a] + gap)
    shift = (np.mean(out) - np.mean(ys))
    return out - shift


class Plan:
    """A plan view in the arm's frame for a 2D axes: along the arm (h) and
    across it towards higher columns (−e_h), true millimetres on both axes;
    the axes' aspect stretches the second, and ``plan_magnification`` says by
    how much (rays stay straight under that stretch)."""

    def __init__(self, g):
        r = ph.ray_geometry(g, g.r0, g.c0)
        self.h, self.e = r.h, -r.e_h

    def __call__(self, p):
        p = np.asarray(p, float)
        return float(np.dot(p, self.h)), float(np.dot(p, self.e))

    def line(self, ax, pts, **kw):
        xy = np.array([self(p) for p in pts])
        return ax.plot(xy[:, 0], xy[:, 1], **kw)


def plan_s5(ax, st, g, f, blade=4.0, lw=3.0):
    """The S5 blades in a plan view, ``blade`` mm long each."""
    for a, b in ((-f.s5[0] - blade, -f.s5[0]), (f.s5[1], f.s5[1] + blade)):
        st.line(ax, [s5_point(g, a), s5_point(g, b)], color=C['s5'], lw=lw, solid_capstyle='butt', zorder=4)


def label_on_line(ax, p0, p1, text, color, frac=0.5, dy=6, size=9, va='bottom'):
    """Text along the screen direction of the segment p0-p1 (data coords), at ``frac``."""
    d0, d1 = ax.transData.transform(p0), ax.transData.transform(p1)
    ang = math.degrees(math.atan2(d1[1] - d0[1], d1[0] - d0[0]))
    if ang > 90:
        ang -= 180
    elif ang < -90:
        ang += 180
    m = (1 - frac) * np.asarray(p0) + frac * np.asarray(p1)
    ax.annotate(text, m, xytext=(0, dy), textcoords='offset points', rotation=ang, rotation_mode='anchor',
                ha='center', va=va, fontsize=size, color=color, path_effects=HALO)


def case3(out):
    """Top view of the pinhole: each column sees its own footprint point."""
    f = frame(11, 16.0)
    g = f.geom
    r0 = g.r0
    ftp = ftp_of(f)
    use = usable(f)
    flo, fhi = ph.footprint_window(g, f.areainfo[1], f.s1_to_sample_mm)
    s5lo, s5hi = ph.s5_window(g, *f.s5)
    cend = list(true_window(f))
    exact = {c: ph.ray_geometry(g, r0, c) for c in (cend[0], g.c0, cend[1])}
    idl = {c: ph.ray_geometry(g, r0, c) for c in (flo, fhi)}
    ends = {c: ph.ray_geometry(g, r0, c) for c in (use[0], use[-1])}
    s5r = {c: ph.ray_geometry(g, r0, c) for c in (s5lo, s5hi)}
    seen = [ends[use[0]].source, ends[use[-1]].source]
    fig = new_fig()
    a = Iso(fig, [0.0, 0.53, 1.0, 0.39], '(a) true scale — every column looks through S4 at its own point of the '
            'footprint')
    scene(a, g, f, list(exact.values()) + [ph.ray_geometry(g, NR - 1, 0)], beam_from=-150)
    info = reach(a, g, f)
    lab_axes(a, 50)
    a.line(seen, FILL['seen'], lw=4.0, z=2)
    ray_line(a, exact[g.c0], 'ray to c0', where=0.5, side=1, size=9)
    for r in idl.values():
        ray_line(a, r, color=C['approx'], ls=(0, (4, 3)), lw=1.0)
    a.point(exact[g.c0].slit, C['ray'], 'S4', dx=-6, dy=10, ha='right')
    a.point(X * (-ftp / 4), C['fp'], 'footprint %.1f × %.1f mm' % (ftp, f.areainfo[0]), dx=-40, dy=-30,
            ha='right', va='top', size=9, ms=0.1, leader=True)
    m = 0.5 * (info['allow'][0] + info['allow'][1])
    a.point(m, C['s5'], 'S5 lets through x = %s mm' % fmt_cols(*(p[0] for p in info['allow'])), dx=40, dy=-70,
            ha='left', va='top', size=8.5, ms=0.1, leader=True)
    a.point(s5_point(g, f.s5[1] + BLADE, (NR - 0.5 - g.r0) * ph.PIXEL_MM), C['s5'], 'S5', dx=4, dy=4, size=9,
            ms=0.1)
    a.finish()

    # (b) plan view in the arm's frame, true millimetres; the axes stretch the across-arm direction
    st = Plan(g)
    bx = fig.add_axes([0.07, BOT + 0.05, 0.80, 0.33])
    det = [st(ph.ray_geometry(g, r0, c).pixel) for c in (-0.5, NC - 0.5)]
    bx.plot(*zip(st(ph.ray_geometry(g, r0, use[0] - 0.5).pixel), st(ph.ray_geometry(g, r0, use[-1] + 0.5).pixel)),
            color='#9DC3E6', lw=9, solid_capstyle='butt', zorder=1)
    bx.plot(*zip(*det), color='#4A6F96', lw=2, zorder=2)
    for c, rr in exact.items():
        if s5lo <= c <= s5hi:
            st.line(bx, [rr.source, rr.pixel], color=C['ray'], lw=1.1, zorder=3)
        else:                                        # stopped by S5
            stop = at_s5(rr)
            st.line(bx, [rr.source, stop], color=C['ray'], lw=1.1, zorder=3)
            st.line(bx, [stop, rr.pixel], color=C['ray'], lw=0.8, ls=(0, (1, 2)), alpha=0.6, zorder=3)
            bx.plot(*st(stop), 'x', color=C['s5'], ms=8, mew=2, zorder=6)
            bx.annotate('stopped by S5', st(stop), xytext=(-10, -10), textcoords='offset points', ha='right',
                        va='top', fontsize=8.5, color=C['s5'], path_effects=HALO)
    for c, rr in idl.items():
        st.line(bx, [rr.source, rr.pixel], color=C['approx'], lw=1.0, ls=(0, (4, 3)), zorder=2)
    for c, rr in s5r.items():
        st.line(bx, [rr.source, rr.pixel], color=C['s5'], lw=1.0, ls=(0, (6, 2)), zorder=2)
    plan_s5(bx, st, g, f)
    beam0 = -X * (ftp / 2 + 60)
    bx.annotate('', xy=st(-X * (ftp / 2 + 8)), xytext=st(beam0),
                arrowprops=dict(arrowstyle='-|>', color=C['beam'], lw=2.0, shrinkA=0, shrinkB=0))
    st.line(bx, [-X * ftp / 2, X * ftp / 2], color=FILL['footprint'], lw=6, solid_capstyle='butt', zorder=2)
    st.line(bx, seen, color=FILL['seen'], lw=6, solid_capstyle='butt', zorder=2)
    al = [s5r[s5lo].source, s5r[s5hi].source]                  # on the beam axis, over the footprint
    st.line(bx, al, color=C['s5'], lw=2, solid_capstyle='butt', zorder=3)
    bx.plot(*st(exact[g.c0].slit), 'o', color=C['ray'], ms=5, mec='white', zorder=6)
    bx.annotate('S4', st(exact[g.c0].slit), xytext=(0, 9), textcoords='offset points', ha='center', fontsize=10)
    xs = [st(p)[0] for p in (beam0, exact[g.c0].pixel)]
    bx.set_xlim(xs[0] - 5, xs[1] + 95)
    yall = [st(p)[1] for p in (exact[cend[0]].pixel, exact[cend[1]].pixel, -X * ftp / 2, X * ftp / 2, beam0,
                               s5_point(g, f.s5[1] + 4), s5_point(g, -f.s5[0] - 4), al[1])]
    bx.set_ylim(min(yall) - 5.0, max(yall) + 1.5)
    bx.set_xlabel('along the arm, h (mm)', fontsize=9)
    bx.set_ylabel('across the arm, towards\nhigher 2θ (mm)', fontsize=9)
    bx.tick_params(labelsize=8)
    for sp in ('top', 'right'):
        bx.spines[sp].set_visible(False)

    def late():
        label_on_line(bx, st(beam0), st(-X * (ftp / 2 + 8)), r'$\mathbf{k}_\mathrm{in}$', C['beam'], size=11)
        label_on_line(bx, st(-X * ftp / 2), st(X * ftp / 2), 'footprint %.1f mm' % ftp, C['fp'], frac=0.3,
                      dy=-8, va='top')
        bx.annotate('S5 lets through x = %s mm\n(purple, on the beam axis)' % fmt_cols(al[0][0], al[1][0]),
                    st(al[1]), xytext=(30, -2), textcoords='offset points', ha='left', va='top', fontsize=8.5,
                    color=C['s5'], path_effects=HALO,
                    arrowprops=dict(arrowstyle='-', color=C['s5'], lw=0.5, alpha=0.6))
        keys = [cend[0], g.c0, cend[1]]
        ys = spread_labels([st(exact[c].pixel)[1] for c in keys], 2.2)
        for c, y in zip(keys, ys):
            x0, y0 = st(exact[c].pixel)
            bx.annotate(('column %.1f' % c) if c != g.c0 else 'c0 = %d' % c, (x0, y0), xytext=(x0 + 14, y),
                        textcoords='data', fontsize=9, va='center', ha='left', color=C['ray'],
                        arrowprops=dict(arrowstyle='-', color=C['ray'], lw=0.5, alpha=0.6, shrinkA=0, shrinkB=2))
        for c, rr in s5r.items():
            x0, y0 = st(at_s5(rr))
            bx.annotate('S5 edge → column %.1f' % c, (x0, y0), xytext=(-40, 14 if c > g.c0 else -14),
                        textcoords='offset points', fontsize=8.5, ha='right', va='center', color=C['s5'],
                        path_effects=HALO, arrowprops=dict(arrowstyle='-', color=C['s5'], lw=0.5, alpha=0.6))
        for c, rr in idl.items():
            bx.annotate(('reader (P39): %.1f' % c).replace('-', '−'), st(rr.source),
                        xytext=(10, 6) if c < g.c0 else (8, -6), textcoords='offset points', fontsize=8.5,
                        ha='left', va='bottom' if c < g.c0 else 'top', color=C['approx'],
                        path_effects=HALO)
        u0, u1 = st(ph.ray_geometry(g, r0, use[0]).pixel), st(ph.ray_geometry(g, r0, use[-1]).pixel)
        bx.annotate('usable %d–%d' % (use[0], use[-1]), (u0[0], 0.55 * u1[1]), xytext=(u0[0] + 14, 0.55 * u1[1]),
                    textcoords='data', ha='left', va='center', fontsize=8.5, color='#4A6F96', path_effects=HALO)
        bx.set_title('(b) plan view — the footprint reaches columns %s, S5 passes %s, usable %d–%d '
                     '(across the arm drawn ×%.0f)' % (fmt_cols(*cend), fmt_cols(s5lo, s5hi), use[0], use[-1],
                                                      plan_magnification(bx)), fontsize=10, loc='left')
    caption(fig, 'Case 3 — The pinhole seen from above: every column sees its own footprint point',
            'Rays to the direct-beam row, <LOW>, Det_Th %.1f°. Black: from the footprint\'s ends; dashed grey: '
            'the reader\'s footprint window (P39); purple: S5\'s edges traced back to the beam.' % deg(g.dth),
            'ray_geometry, footprint_columns, footprint_window, s5_window, usable_columns, footprint_length.',
            provenance(f))
    save(fig, [a], os.path.join(out, 'case3_pinhole_top_view.png'), late=[late])


def case4(out):
    """β depends on the column: two pixels of one row, two footprint points."""
    f = frame(11, 16.0)
    g = f.geom
    use = usable(f)
    row = NR - 1
    c1, c2 = int(use[0]), int(use[-1])
    r1, r2 = ph.ray_geometry(g, row, c1), ph.ray_geometry(g, row, c2)
    ftp = ftp_of(f)
    fig = new_fig()
    a = Iso(fig, [0.0, 0.50, 1.0, 0.42], '(a) true scale — two pixels of the top row look at two footprint points')
    scene(a, g, f, [r1, r2, ph.ray_geometry(g, 0, 0)], beam_from=-150)
    info = reach(a, g, f)
    lab_axes(a, 50)
    ray_line(a, r1, 'c = %d' % c1, where=0.55, side=-1, size=9.5)
    ray_line(a, r2, 'c = %d' % c2, where=0.55, side=1, size=9.5)
    a.point(r1.source, C['ray'], r'$F_1$: x = %s mm' % signed(r1.source[0]), dx=-30, dy=-26, ha='right',
            va='top', size=9.5, leader=True)
    a.point(r2.source, C['ray'], r'$F_2$: x = %s mm' % signed(r2.source[0]), dx=40, dy=8, ha='left', size=9.5,
            leader=True)
    a.point(X * (-ftp / 2.5), C['fp'], 'footprint %.1f × %.1f mm' % (ftp, f.areainfo[0]), dx=-150, dy=-62,
            ha='right', va='top', size=9, ms=0.1, leader=True)
    m = 0.5 * (info['allow'][0] + info['allow'][1])
    a.point(m, C['s5'], 'S5 lets through x = %s mm' % fmt_cols(*(p[0] for p in info['allow'])), dx=40, dy=-70,
            ha='left', va='top', size=8.5, ms=0.1, leader=True)
    a.point(s5_point(g, f.s5[1] + BLADE, (NR - 0.5 - g.r0) * ph.PIXEL_MM), C['s5'], 'S5', dx=4, dy=4, size=9,
            ms=0.1)
    a.finish()

    mid = 0.5 * (r1.slit + r2.slit)
    half = 6.0
    b = Iso(fig, [0.0, BOT + 0.02, 0.5, 0.33], None, box=(mid - half, mid + half))
    b.line([r1.slit_centre + (np.dot(mid - r1.slit_centre, r1.e_v) - 2 * half) * r1.e_v,
            r1.slit_centre + (np.dot(mid - r1.slit_centre, r1.e_v) + 2 * half) * r1.e_v], FILL['slit'], lw=3, z=2)
    upper = 1 if r1.slit[2] > r2.slit[2] else -1          # label each ray on its outer side
    for r, c, side in ((r1, c1, upper), (r2, c2, -upper)):
        b.line([r.source, r.slit], C['ray'], lw=1.2)
        b.arrow(r.slit, r.pixel, C['ray'], 'c = %d' % c, where=0.75, side=side, lw=1.2, size=9.5)
        b.point(r.slit, C['ray'])
    b.arrow(r2.slit, r1.slit, C['arm'], '%.2f mm' % np.linalg.norm(r1.slit - r2.slit), where=0.5, side=-1,
            both=True, lw=1.0, size=9, off=10)
    b.point(r1.slit_centre + (np.dot(mid - r1.slit_centre, r1.e_v) + 0.9 * half) * r1.e_v, FILL['slit'],
            'S4 slit line', dx=8, dy=0, ha='left', va='center', size=9, ms=0.1)
    b.finish()
    b.title = lambda: '(b) at S4 (%s) — the two rays cross the slit %.2f mm apart in height' % (
        mag_note(a, b), np.linalg.norm(r1.slit - r2.slit))

    # (c) β along the row: exact against per-axis
    cx = fig.add_axes([0.58, BOT + 0.06, 0.38, 0.26])
    cols = np.arange(NC)
    _, bb = ph.pixel_angles(g, [row], cols)
    _, bpa = per_axis(g, [row], cols)
    cx.axvspan(use[0], use[-1], color=FILL['detector'], lw=0)
    cx.plot(cols, np.degrees(bb[0]), color=C['ray'], lw=1.6)
    cx.plot(cols, np.degrees(np.full(NC, bpa[0])), color=C['approx'], lw=1.4, ls=(0, (4, 3)))
    cx.annotate('exact (pixel_angles)', (3 * NC // 4, np.degrees(bb[0, 3 * NC // 4])), xytext=(-6, 8),
                textcoords='offset points', color=C['ray'], ha='right', va='bottom', fontsize=9)
    cx.text(cols[-1], np.degrees(bpa[0]) - 0.03, 'per-axis (row_beta): %.3f°' % np.degrees(bpa[0]),
            color=C['approx'], ha='right', va='top', fontsize=8.5)
    for c in (c1, c2):
        cx.plot([c], [np.degrees(bb[0, c])], 'o', color=C['ray'], ms=5, mec='white')
        cx.annotate('%.3f°' % np.degrees(bb[0, c]), (c, np.degrees(bb[0, c])), xytext=(6, -12),
                    textcoords='offset points', fontsize=8.5, ha='left')
    dmax_i = int(np.argmax(np.abs(np.degrees(bpa[0] - bb[0, use]))))
    cm = int(use[dmax_i])
    cx.annotate('', xy=(cm, np.degrees(bb[0, cm])), xytext=(cm, np.degrees(bpa[0])),
                arrowprops=dict(arrowstyle='<|-|>', color=C['arm'], lw=1.0, shrinkA=0, shrinkB=0,
                                mutation_scale=9))
    cx.text(cm + 3, 0.5 * (np.degrees(bb[0, cm]) + np.degrees(bpa[0])),
            'off by %.2f°' % abs(np.degrees(bb[0, cm] - bpa[0])), color=C['arm'], fontsize=8.5, ha='left',
            va='center', path_effects=HALO)
    cx.text(0.5 * (use[0] + use[-1]), np.degrees(bb[0]).min(), 'usable\ncolumns', ha='center', va='bottom',
            fontsize=8, color='#4A6F96')
    cx.set_xlabel('column', fontsize=9)
    cx.set_ylabel('β (°), row %d' % row, fontsize=9)
    cx.tick_params(labelsize=8)
    cx.set_title('(c) β along the top row: %.3f° apart between columns %d and %d' % (
        deg(r2.beta - r1.beta), c1, c2), fontsize=10, loc='left')
    for s in ('top', 'right'):
        cx.spines[s].set_visible(False)
    caption(fig, 'Case 4 — Why β depends on the column',
            'Top row (%d), the usable columns\' ends (%d, %d), <LOW>, Det_Th %.1f°: different footprint '
            'points, different heights at S4, different β; per-axis gives the row one β.' % (row, c1, c2, deg(g.dth)),
            'ray_geometry (rays, F, slit points), pixel_angles (IMG_COO_CONV, Mati Meron), row_beta, '
            'footprint_columns, s5_window, usable_columns.', provenance(f))
    save(fig, [a, b], os.path.join(out, 'case4_beta_depends_on_column.png'))


def case5(out):
    """Raised arm: the (u, v, w) of IMG_COO_CONV; 2θ depends on the row."""
    f = frame(12, 14.0)
    g = f.geom
    use = usable(f)
    col = int(use[-1])                               # (a): a column that gets light
    edge = NC - 1                                    # (b) also shows the module's edge column
    rt, rb_ = ph.ray_geometry(g, NR - 1, col), ph.ray_geometry(g, 0, col)
    ftp = ftp_of(f)
    fig = new_fig()
    a = Iso(fig, TOP, '(a) true scale, β0 = %.1f° — the ray S → P split as u·e_h + v·h + w·z (IMG_COO_CONV)'
            % deg(g.beta0))
    scene(a, g, f, [rt, rb_], beam_from=-120)
    info = reach(a, g, f)
    lab_axes(a, 50)
    a.line([np.zeros(3), rt.centre], C['arm'], lw=1.0, ls=(0, (4, 3)))
    a.arrow(np.zeros(3), 90 * rt.n, C['arm'], r'$\mathbf{n}$', where=0.6, side=1)
    a.arrow(rt.slit, rt.slit + rt.u * rt.e_h, C['comp'], r'$u$', where=0.5, side=1, lw=2.0, off=13)
    p1 = rt.slit + rt.u * rt.e_h
    a.arrow(p1, p1 + rt.v * rt.h, C['comp'], r'$v$', where=0.5, side=1, lw=2.0)
    p2 = p1 + rt.v * rt.h
    a.point(p1 + 0.45 * rt.v * rt.h, C['comp'], 'v = %.2f mm' % rt.v, dx=10, dy=70, ha='left', size=9, ms=0.1,
            leader=True)
    a.arrow(p2, p2 + rt.w * Z, C['comp'], r'$w$', where=0.5, side=1, lw=2.0)
    ray_line(a, rt, 'ray, row %d' % (NR - 1), where=0.45, side=1, size=9.5)
    ray_line(a, rb_, 'row 0', where=0.45, side=-1, size=9.5)
    a.point(rt.slit, C['ray'], 'S', dx=-8, dy=-4, ha='right', va='top')
    a.point(rt.pixel, C['ray'], 'P (row %d, column %d)\n2θ %.3f°, β %.3f°' % (NR - 1, col, deg(rt.two_theta),
                                                                           deg(rt.beta)),
            dx=14, dy=30, size=9, leader=True)
    a.point(p1, C['comp'], 'u = %s mm' % signed(rt.u, '%.2f'), dx=-6, dy=26, ha='right', size=9, ms=0.1,
            leader=True)
    a.point(p2 + 0.5 * rt.w * Z, C['comp'], 'w = %.2f mm' % rt.w, dx=40, dy=-6, ha='left', va='top', size=9,
            ms=0.1, leader=True)
    a.point(X * (-ftp / 4), C['fp'], 'footprint %.1f × %.1f mm' % (ftp, f.areainfo[0]), dx=-40, dy=-30,
            ha='right', va='top', size=9, ms=0.1, leader=True)
    m = 0.5 * (info['allow'][0] + info['allow'][1])
    a.point(m, C['s5'], 'S5 lets through x = %s mm' % fmt_cols(*(p[0] for p in info['allow'])), dx=20, dy=-34,
            ha='left', va='top', size=8.5, ms=0.1, leader=True)
    a.finish()

    # (b) 2θ − Det_Th along columns, against the row
    bx = fig.add_axes([0.07, BOT + 0.05, 0.66, 0.30])
    rows = np.arange(NR)
    show = [0, int(use[0]), int(g.c0), col, edge]
    tt, _ = ph.pixel_angles(g, rows, show)
    tpa, _ = per_axis(g, rows, np.array(show))
    g11 = frame(11, 14.0).geom
    t11 = ph.pixel_angles(g11, rows, [edge])[0][:, 0]
    bx.axhline(0, color='#999999', lw=0.6)
    ends = []
    for j, c in enumerate(show):
        y = np.degrees(tt[:, j] - tpa[j])
        lit = use[0] <= c <= use[-1]
        bx.plot(rows, y, color=C['ray'], lw=1.5 if lit else 1.0, alpha=1.0 if lit else 0.55)
        ends.append((y[-1], 'c = %d%s: spans %.3f°' % (c, '' if lit else ' (no light)', np.ptp(y)),
                     C['ray'] if lit else '#666666'))
    y11 = np.degrees(t11 - per_axis(g11, rows, np.array([edge]))[0][0])
    bx.plot(rows, y11, color=C['approx'], lw=1.3, ls=(0, (4, 3)))
    ends.append((y11[-1], 'c = %d, arm level (<LOW>): %.4f°' % (edge, np.ptp(y11)), C['approx']))
    span = max(e[0] for e in ends) - min(e[0] for e in ends)
    for (y, text, colour), yl in zip(ends, spread_labels([e[0] for e in ends], 0.17 * span)):
        bx.annotate(text, (NR - 1, y), xytext=(NR + 10, yl), textcoords='data', fontsize=8.5, va='center',
                    ha='left', color=colour, arrowprops=dict(arrowstyle='-', color=colour, alpha=0.5, lw=0.6))
    bx.set_xlim(0, NR - 1)
    bx.set_xlabel('row', fontsize=9)
    bx.set_ylabel('2θ exact − per-axis (°)', fontsize=9)
    bx.tick_params(labelsize=8)
    bx.set_title('(b) with the arm raised, a column\'s 2θ changes along it (exact − per-axis, against the row)',
                 fontsize=10, loc='left')
    for s in ('top', 'right'):
        bx.spines[s].set_visible(False)
    caption(fig, 'Case 5 — Raised arm: the (u, v, w) decomposition, and 2θ depends on the row',
            'High-Qz level, <DATA> scan %d: β0 = %.2f°, Det_Th %.1f°, D = %.1f mm (the arm term adds %.1f mm); '
            'e_v leans back, so one column\'s top and bottom lie at different 2θ.'
            % (f.scan, deg(g.beta0), deg(g.dth), ph.vertical_distance(g), ph.vertical_distance(g) - g.d_sample),
            'ray_geometry (u, v, w, h, S, P, rays), pixel_angles, column_two_theta, vertical_distance, '
            'usable_columns, footprint_columns, s5_window.', provenance(f))
    save(fig, [a], os.path.join(out, 'case5_raised_arm_uvw.png'))


def case6(out):
    """Where a second module would be: the per-axis error, and what it sees."""
    f = frame(12, 14.0)
    g = f.geom
    ftp = ftp_of(f)
    (llo, lhi), (rlo, rhi) = SECOND['low'], SECOND['high']
    mods = [(llo, lhi, 'left'), (0, NC - 1, 'module'), (rlo, rhi, 'right')]
    ends = (llo, lhi, rlo, rhi)
    s5lo, s5hi = ph.s5_window(g, *f.s5)
    fig = new_fig()
    a = Iso(fig, [0.0, 0.53, 0.62, 0.39], '(a) true scale — the second module\'s columns look far off the footprint')
    rays = {c: ph.ray_geometry(g, g.r0, c) for c in ends}
    edge_rays = [ph.ray_geometry(g, r, c) for r in (0, NR - 1) for c in (llo, rhi)]
    scene(a, g, f, edge_rays, det=False, beam_from=None)
    lab_axes(a, 50)
    rows = np.arange(NR)
    allc = np.arange(llo, rhi + 1)
    tt, bb = ph.pixel_angles(g, rows, allc)
    tpa, bpa = per_axis(g, rows, allc)
    db = np.degrees(bpa[:, None] - bb)
    dt = np.degrees(tpa[None, :] - tt)
    lim = math.ceil(np.abs(db).max())
    cmap = plt.get_cmap('coolwarm')
    norm = matplotlib.colors.Normalize(-lim, lim)
    box_pts = []
    for c, r in rays.items():
        a.line([r.source, r.slit], C['ray'], lw=0.9)
        if s5lo <= c <= s5hi:
            a.line([r.slit, r.pixel], C['ray'], lw=0.9)
        else:
            stop = at_s5(r)
            a.line([r.slit, stop], C['ray'], lw=0.9)
            a.line([stop, r.pixel], C['ray'], lw=0.6, ls=(0, (1, 2)), alpha=0.6)
            a.point(stop, C['s5'], ms=5, marker='x', z=7)
        a.point(r.source, C['ray'], ('c = %d: x = %.0f mm' % (c, r.source[0])).replace('-', '−'),
                dx=-4 if c == llo else 0, dy=-14 if c > 0 else 9, ha='left' if c == llo else 'center',
                va='top' if c > 0 else 'bottom', size=8.5)
    a.point(X * 0.0, C['fp'], 'footprint ±%.1f mm' % (ftp / 2), dx=-10, dy=-8, ha='right', va='top', size=9, ms=0.1)
    for lo, hi, name in mods:
        a.poly(module_corners(g, lo, hi), FILL['detector'] if name == 'module' else FILL['ghost'], '#333333',
               z=2, lw=0.8, ls='-' if name == 'module' else '--')
        box_pts += module_corners(g, lo, hi)
    s5_blades(a, g, f, blade=25.0)
    a.point(s5_point(g, -f.s5[0] - 25.0, (-0.5 - g.r0) * ph.PIXEL_MM), C['s5'],
            'S5 (×: rays it stops)', dx=-8, dy=-10, ha='right', va='top', size=9, ms=0.1)
    a.finish()

    # (b) close-up of the three modules, coloured cell by cell
    box_pts = np.array(box_pts)
    mid = 0.5 * (box_pts.min(axis=0) + box_pts.max(axis=0))
    half = 0.5 * (box_pts.max(axis=0) - box_pts.min(axis=0)).max() * 1.15
    b = Iso(fig, [0.0, BOT + 0.07, 0.55, 0.30], None, box=(mid - half, mid + half))
    for lo, hi, name in mods:
        rs = np.linspace(-0.5, NR - 0.5, 25)
        cs = np.linspace(lo - 0.5, hi + 0.5, 11)
        P = np.array([[ph.ray_geometry(g, r, c).pixel for c in cs] for r in rs])
        rc = np.clip(np.round(0.5 * (rs[:-1] + rs[1:])).astype(int), 0, NR - 1)
        cc = np.round(0.5 * (cs[:-1] + cs[1:])).astype(int) - llo     # index into allc
        quads = [[P[i, j], P[i, j + 1], P[i + 1, j + 1], P[i + 1, j]] for i in range(len(rs) - 1)
                 for j in range(len(cs) - 1)]
        colours = [cmap(norm(db[rc[i], cc[j]])) for i in range(len(rs) - 1) for j in range(len(cs) - 1)]
        pc = Poly3DCollection(quads, facecolors=colours, edgecolors=colours, linewidths=0.3, zorder=1)
        b.ax.add_collection3d(pc)
        pc.set_clip_on(False)
        b.pts.extend(np.array(quads).reshape(-1, 3))
        b.poly(module_corners(g, lo, hi), 'none', '#333333', z=2, lw=1.0,
               ls='-' if name == 'module' else '--')
        sel = (allc >= lo) & (allc <= hi)
        where = {'left': ((NR - 0.5, lo - 0.5), dict(dx=-6, dy=0, ha='right', va='center')),
                 'module': ((-0.5, 0.5 * (lo + hi)), dict(dx=40, dy=-26, ha='left', va='top', leader=True)),
                 'right': ((-0.5, hi + 0.5), dict(dx=6, dy=0, ha='left', va='center'))}[name]
        b.point(ph.ray_geometry(g, *where[0]).pixel, '#333333',
                {'module': 'this module: β up to %.1f°' % np.abs(db[:, sel]).max(),
                 'left': ('c %d…%d:\nβ up to %.1f°' % (lo, hi, np.abs(db[:, sel]).max())).replace('-', '−'),
                 'right': 'c %d…%d:\nβ up to %.1f°' % (lo, hi, np.abs(db[:, sel]).max())}[name], size=9, ms=0.1,
                **where[1])
    b.finish()
    b.title = lambda: '(b) the three modules (%s), coloured by β per-axis − exact' % mag_note(a, b)
    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    cax = fig.add_axes([0.08, BOT + 0.03, 0.25, 0.01])
    cb = fig.colorbar(sm, cax=cax, orientation='horizontal')
    cb.set_label('β per-axis − exact (°)', fontsize=8.5)
    cb.ax.tick_params(labelsize=8)

    for k, (arr, name, unit) in enumerate(((db, 'β', '°'), (dt, '2θ', '°'))):
        bx = fig.add_axes([0.66, 0.60 - 0.40 * k, 0.31, 0.27])
        for lo, hi, mname in mods:
            bx.axvspan(lo - 0.5, hi + 0.5, color=FILL['detector'] if mname == 'module' else FILL['ghost'], lw=0)
            if k == 0:
                bx.text(0.5 * (lo + hi), 1.01, {'module': 'this module', 'left': 'module 2 here?',
                                                'right': 'or here?'}[mname],
                        transform=bx.get_xaxis_transform(), ha='center', va='bottom', fontsize=8.5)
        bx.axvspan(s5lo, s5hi, ymin=0, ymax=0.03, color=C['s5'], lw=0)
        j = len(allc) - 45
        for r, ls in ((NR - 1, "-"), (0, (0, (4, 2)))):
            bx.plot(allc, arr[r], color=C['ray'], lw=1.3, ls=ls)
        upper = 0 if arr[0, j] > arr[NR - 1, j] else NR - 1
        for r in (0, NR - 1):                            # beside its own curve, on the side away from the other
            bx.annotate('row %d' % r, (allc[j], arr[r, j]), xytext=(-6, 12 if r == upper else -12),
                        textcoords='offset points', fontsize=8, ha='right', va='bottom' if r == upper else 'top',
                        path_effects=HALO)
        bx.axhline(0, color='#999999', lw=0.6)
        ylo, yhi = bx.get_ylim()
        bx.set_ylim(ylo - 0.08 * (yhi - ylo), yhi)
        if k == 1:
            bx.text(0.5 * (s5lo + s5hi), ylo - 0.04 * (yhi - ylo), 'S5', color=C['s5'], ha='center', va='bottom',
                    fontsize=8)
        bx.set_ylabel('%s per-axis − exact (%s)' % (name, unit), fontsize=8.5)
        bx.tick_params(labelsize=8)
        for sp in ('top', 'right'):
            bx.spines[sp].set_visible(False)
        if k == 1:
            bx.set_xlabel('column', fontsize=9)
        bx.set_title('(%s) %s per-axis − exact: up to %.2f° on module 2'
                     % ('cd'[k], name, np.abs(arr[:, (allc < 0) | (allc >= NC)]).max()), fontsize=9.5,
                     loc='left', pad=18 if k == 0 else 6)
    caption(fig, 'Case 6 — Where the 200K\'s second module would be',
            'Two %d × %d modules with a %d-pixel gap: the unused one would sit at columns %d…%d or %d…%d of this '
            'numbering (<DATA> scan %d, β0 = %.1f°): per-axis angles fail there, and S5 gives it no light.'
            % (NR, NC, GAP, llo, lhi, rlo, rhi, f.scan, deg(g.beta0)),
            'ray_geometry (rays, sources, module surfaces), pixel_angles minus column_two_theta / row_beta, '
            's5_window, footprint_length.', provenance(f))
    save(fig, [a, b], os.path.join(out, 'case6_second_module.png'))


def case7(out):
    """The footprint at the usual GID α, and what makes a column usable."""
    f = frame(11, 16.0)
    g = f.geom
    s1v, s1h, s1s = f.areainfo[1], f.areainfo[0], f.s1_to_sample_mm
    t_lo, t_hi = true_window(f)
    ftp = ftp_of(f)
    c_lo, c_hi = ph.footprint_window(g, s1v, s1s)
    s5lo, s5hi = ph.s5_window(g, *f.s5)
    (o_lo, o_hi), (i_lo, i_hi) = ph.s4_window(g, s1v, *s4_open(f), s1s)
    use = usable(f)
    src = {c: ph.ray_geometry(g, g.r0, c).source[0] for c in (use[0], use[-1], s5lo, s5hi)}
    sec = {k: (ph.ray_geometry(g, g.r0, a).source[0], ph.ray_geometry(g, g.r0, b).source[0])
           for k, (a, b) in SECOND.items()}
    acc = ph.column_acceptance(g, g.c0, *s4_open(f), n=11)
    fig = new_fig()

    # (a) the sample plane, true scale along the beam
    ax = fig.add_axes([0.06, 0.70, 0.88, 0.19])
    ax.add_patch(plt.Rectangle((-ftp / 2, -s1h / 2), ftp, s1h, color=FILL['footprint'], lw=0, zorder=1))
    ax.add_patch(plt.Rectangle((src[use[0]], -s1h / 2), src[use[-1]] - src[use[0]], s1h, color=FILL['seen'],
                               lw=0, zorder=2))
    ya = -s1h / 2 - 1.1                                   # the S5 allowance, drawn below the footprint
    ax.plot([src[s5lo], src[s5hi]], [ya, ya], color=C['s5'], lw=4, solid_capstyle='butt')
    ax.text(src[s5hi] + 2, ya, 'S5 lets through x = %s mm' % fmt_cols(src[s5lo], src[s5hi]), color=C['s5'],
            fontsize=8.5, ha='left', va='center')
    xa0, xa1 = acc.source_x.min(), acc.source_x.max()     # one column's stretch through S4 and its pixel
    yb = s1h / 2 + 0.5
    ax.plot([xa0, xa1], [yb, yb], color=C['ray'], lw=3, solid_capstyle='butt')
    ax.annotate('column c0 sees %.1f mm\n(S4 %.1f mm + its pixel)' % (xa1 - xa0, f.areainfo[2]), (xa1, yb),
                xytext=(14, 6), textcoords='offset points', fontsize=8, ha='left', va='bottom', color=C['ray'],
                arrowprops=dict(arrowstyle='-', color=C['ray'], lw=0.5, alpha=0.6))
    ax.annotate('', xy=(-ftp / 2 - 4, 0), xytext=(-ftp / 2 - 40, 0),
                arrowprops=dict(arrowstyle='-|>', color=C['beam'], lw=2.0))
    ax.text(-ftp / 2 - 22, 0.45 * s1h, r'$\mathbf{k}_\mathrm{in}$', color=C['beam'], ha='center', fontsize=11)
    for x0 in (-ftp / 2, ftp / 2):
        ax.plot([x0, x0], [-s1h / 2, s1h / 2], color='#555555', lw=0.6)
        ax.text(x0, s1h / 2 + 0.15, signed(x0), ha='center', va='bottom', fontsize=8, color=C['fp'])
    for x0 in (src[use[0]], src[use[-1]]):
        ax.text(x0, 0, signed(x0), ha='left' if x0 < 0 else 'right', va='center', fontsize=8, color='white')
    ax.text(-ftp / 2 - 3, -s1h / 2, 'footprint\n%.1f × %.1f mm' % (ftp, s1h), ha='right', va='top', fontsize=9,
            color=C['fp'])
    ax.text(0.5 * (src[use[0]] + src[use[-1]]), 0, 'seen by the\nusable columns', ha='center', va='center',
            fontsize=8, color='white')
    for k, (xa, xb) in sec.items():
        lo, hi = sorted((xa, xb))
        x_edge = -ftp / 2 - 48 if hi < 0 else ftp / 2 + 60
        ax.annotate('module-2 columns (%s side)\nlook at x = %s…%s mm' % (k, signed(lo, '%.0f'), signed(hi, '%.0f')),
                    xy=(x_edge, 0), xytext=(x_edge + (-4 if hi < 0 else 4), 0), fontsize=8,
                    ha='right' if hi < 0 else 'left', va='center', color=C['approx'])
    ax.set_xlim(-ftp / 2 - 130, ftp / 2 + 130)
    ax.set_ylim(ya - 0.8, s1h / 2 + 2.3)
    ax.set_xlabel('x along the beam on the sample (mm, true scale)', fontsize=9)
    ax.set_yticks([-s1h / 2, 0, s1h / 2])
    ax.set_ylabel('y (mm,\nnot to scale)', fontsize=8)
    ax.tick_params(labelsize=8)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
    ax.set_title('(a) the footprint on the sample (α = %.4f°, S1 %.2f × %.1f mm) against what S5 lets through'
                 % (deg(g.alpha), s1v, s1h), fontsize=10, loc='left')

    # (b) the column axis: what limits the usable columns
    bx = fig.add_axes([0.06, 0.41, 0.88, 0.21])
    bars = [('this module', 0 - 0.5, NC - 0.5, FILL['detector']),
            ('module 2 (low side)?', SECOND['low'][0] - 0.5, SECOND['low'][1] + 0.5, FILL['ghost']),
            ('module 2 (high side)?', SECOND['high'][0] - 0.5, SECOND['high'][1] + 0.5, FILL['ghost'])]
    for lab, a0, a1, col in bars:
        bx.barh(4, a1 - a0, left=a0, height=0.7, color=col, edgecolor='#4A6F96' if col == FILL['detector'] else '#999999')
        bx.text(0.5 * (a0 + a1), 4, lab, ha='center', va='center', fontsize=8)
    rows = [(3, 'S5 window (slit size)', s5lo, s5hi, C['s5']),
            (2, 'footprint seen through S4 (exact)', t_lo, t_hi, FILL['seen']),
            (1, 'reader\'s footprint window (centred on c0)', c_lo, c_hi, 'white'),
            (0, 'usable = S5 ∩ reader\'s window', use[0] - 0.5, use[-1] + 0.5, '#2A6FD0')]
    for y, lab, a0, a1, col in rows:
        bx.barh(y, a1 - a0, left=a0, height=0.55, color=col, alpha=0.85 if col != C['s5'] else 0.55,
                edgecolor=FILL['seen'] if col == 'white' else 'none', hatch='////' if col == 'white' else None)
        bx.text(min(a0, a1) - 6, y, lab, ha='right', va='center', fontsize=8, color='#222222')
        ends = (use[0], use[-1]) if y == 0 else (a0, a1)
        for xe, v in zip((a0, a1), ends):
            bx.text(xe, y - 0.42, ('%d' % v) if y == 0 else signed(v), ha='center', va='top', fontsize=7,
                    color='#333333')
    for a0, a1 in ((o_lo, i_lo), (i_hi, o_hi)):           # S4's ramps at the footprint window's edges
        bx.barh(2, a1 - a0, left=a0, height=0.55, color='white', alpha=0.55, lw=0)
    bx.annotate('S4 %.1f mm: ramps %s and %s' % (f.areainfo[2], fmt_cols(o_lo, i_lo), fmt_cols(i_hi, o_hi)),
                (o_hi, 2.0), xytext=(o_hi + 14, 2.0), textcoords='data', fontsize=8, color=C['ray'], ha='left',
                va='center', arrowprops=dict(arrowstyle='-', color=C['ray'], lw=0.5, alpha=0.6))
    bx.axvline(g.c0, color=C['det'], lw=1.0, ls=(0, (3, 2)))
    bx.text(g.c0, 4.55, 'c0 = %d (direct beam)' % g.c0, ha='center', va='bottom', fontsize=8, color=C['det'])
    bx.annotate('', xy=(t_hi, 1.5), xytext=(c_hi, 1.5),
                arrowprops=dict(arrowstyle='-|>', color='#C0652A', lw=1.2))
    bx.text(t_hi + 14, 1.45, 'P39: the reader\'s window is %.1f columns low' % (t_hi - c_hi), ha='left',
            va='center', fontsize=8, color='#C0652A')
    bx.set_xlim(SECOND['low'][0] - 230, SECOND['high'][1] + 10)
    bx.set_ylim(-0.9, 5.0)
    bx.set_yticks([])
    bx.set_xlabel('column (Det_Th = %.1f°)' % deg(g.dth), fontsize=9, labelpad=1)
    bx.tick_params(labelsize=8)
    for sp in ('top', 'right', 'left'):
        bx.spines[sp].set_visible(False)
    bx.set_title('(b) a column is usable when S5 passes it and it sees the footprint: low edge set by S5, '
                 'high edge by the footprint', fontsize=10, loc='left')

    # (c) footprint length against α; (d) the columns that see it
    alphas = np.radians(np.linspace(0.04, 0.30, 40))
    cx = fig.add_axes([0.07, 0.14, 0.38, 0.17])
    dx = fig.add_axes([0.56, 0.14, 0.38, 0.17])
    for sv, ls in ((0.04, ':'), (0.1, '-'), (0.2, '--')):
        L = [ph.footprint_length(replace(g, alpha=a), sv, s1s) for a in alphas]
        cx.plot(np.degrees(alphas), L, color=C['beam'], ls=ls, lw=1.3)
        cx.annotate('S1v %.2f mm' % sv, (np.degrees(alphas[-1]), L[-1]), xytext=(4, 0), textcoords='offset points',
                    fontsize=7.5, color=C['beam'], va='center', ha='left')
        if sv == 0.1:
            win = [ph.footprint_columns(replace(g, alpha=a), sv, s1s) for a in alphas]
            dx.fill_between(np.degrees(alphas), [w[0] for w in win], [w[1] for w in win], color=FILL['seen'],
                            alpha=0.6, lw=0)
    cx.axvline(deg(g.alpha), color=C['det'], lw=0.8, ls=(0, (3, 2)))
    cx.text(deg(g.alpha), cx.get_ylim()[1], ' NX α', color=C['det'], fontsize=7.5, ha='left', va='top')
    cx.set_yscale('log')
    cx.set_xlabel('α (°)', fontsize=9, labelpad=1)
    cx.set_ylabel('footprint length (mm)', fontsize=9)
    cx.set_title('(c) footprint length = S1v / sin α', fontsize=10, loc='left')
    dx.axhspan(s5lo, s5hi, color=C['s5'], alpha=0.18, lw=0)
    dx.axhline(SECOND['high'][0], color=C['approx'], lw=0.8, ls='--')
    dx.axhline(SECOND['low'][1], color=C['approx'], lw=0.8, ls='--')
    dx.text(np.degrees(alphas[-1]), s5hi, 'S5', ha='right', va='bottom', fontsize=8, color=C['s5'])
    dx.text(np.degrees(alphas[-1]), SECOND['high'][0] - 4, 'module 2 starts', ha='right', va='top', fontsize=8,
            color=C['approx'])
    dx.axvline(deg(g.alpha), color=C['det'], lw=0.8, ls=(0, (3, 2)))
    dx.set_xlabel('α (°)', fontsize=9, labelpad=1)
    dx.set_ylabel('column', fontsize=9)
    alpha_reach = None
    for a in np.radians(np.linspace(0.005, 0.04, 200))[::-1]:
        lo_c, hi_c = ph.footprint_columns(replace(g, alpha=a), s1v, s1s)
        if hi_c >= SECOND['high'][0]:
            alpha_reach = deg(a)
            break
    dx.set_title('(d) columns that see the footprint (S1v %.2f mm): module 2 only below α ≈ %s'
                 % (s1v, ('%.3f°' % alpha_reach) if alpha_reach else '?'), fontsize=10, loc='left')
    for axx in (cx, dx):
        axx.tick_params(labelsize=8)
        for sp in ('top', 'right'):
            axx.spines[sp].set_visible(False)
    caption(fig, 'Case 7 — The footprint at the usual GID angle, and what makes a column usable',
            '<LOW>, Det_Th %.1f°, α = %.4f°: the footprint against the S5 slit, on the sample (a) and on the '
            'column axis (b); how both change with α (c, d).' % (deg(g.dth), deg(g.alpha)),
            'footprint_length, footprint_columns, footprint_window, s5_window, usable_columns, s4_window, '
            'column_acceptance, ray_geometry(…).source.', provenance(f))
    save(fig, [], os.path.join(out, 'case7_footprint_and_usable_columns.png'))


def hull(pts):
    """Convex hull of 2D points (monotone chain), for shading a bundle of rays."""
    p = sorted(set(map(tuple, np.round(np.asarray(pts, float), 9))))
    if len(p) < 3:
        return np.array(p)
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for q in p:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    for q in reversed(p):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return np.array(lower[:-1] + upper[:-1])


def bundle(ax, st, g, col, s4, color, alpha=0.35, z=3):
    """Shade, in a plan view, every ray pixel ``col`` (its full width)
    accepts through the S4 opening ``s4`` = (low, high): from the pixel to
    the slit, and from the slit to the beam axis (the corner rays from
    ray_geometry; their hull)."""
    rays = [ph.ray_geometry(g, g.r0, c, t) for c in (col - 0.5, col + 0.5) for t in (-s4[0], s4[1])]
    det = hull([st(r.pixel) for r in rays] + [st(r.slit) for r in rays])
    beam = hull([st(r.slit) for r in rays] + [st(r.source) for r in rays])
    for poly in (det, beam):
        ax.add_patch(plt.Polygon(poly, closed=True, facecolor=color, edgecolor=color, lw=0.6, alpha=alpha,
                                 zorder=z))
    return rays


def plan_s4(ax, st, g, s4, blade=1.0, lw=3.0):
    """The two S4 blades in a plan view, ``blade`` mm long each."""
    r = ph.ray_geometry(g, g.r0, g.c0)
    pt = lambda t: r.slit_centre - t * r.e_h
    for a, b in ((-s4[0] - blade, -s4[0]), (s4[1], s4[1] + blade)):
        st.line(ax, [pt(a), pt(b)], color=FILL['slit'], lw=lw, solid_capstyle='butt', zorder=5)


def case8(out):
    """What S4's finite opening does: each column's acceptance, the ramps at
    the footprint window's edges, and a wider or narrower S4."""
    f = frame(11, 16.0)
    g = f.geom
    s1v, s1h, s1s = f.areainfo[1], f.areainfo[0], f.s1_to_sample_mm
    s4 = s4_open(f)
    w4 = sum(s4)
    ftp = ftp_of(f)
    use = usable(f)
    t_lo, t_hi = true_window(f)
    c_lo, c_hi = ph.footprint_window(g, s1v, s1s)
    s5lo, s5hi = ph.s5_window(g, *f.s5)
    (o_lo, o_hi), (i_lo, i_hi) = ph.s4_window(g, s1v, *s4, s1s)
    col_deg = deg(ph.PIXEL_MM / g.d_pinhole)                       # one column = one 2θ bin (p / D_p)
    acc = ph.column_acceptance(g, g.c0, *s4, n=11)
    fig = new_fig()

    # (a) plan view of the whole set-up, with the bundles three columns accept
    st = Plan(g)
    ax = fig.add_axes([0.07, 0.685, 0.86, 0.225])
    det = [st(ph.ray_geometry(g, g.r0, c).pixel) for c in (-0.5, NC - 0.5)]
    ax.plot(*zip(*det), color='#4A6F96', lw=2, zorder=2)
    beam0 = -X * (ftp / 2 + 60)
    ax.annotate('', xy=st(-X * (ftp / 2 + 8)), xytext=st(beam0),
                arrowprops=dict(arrowstyle='-|>', color=C['beam'], lw=2.0, shrinkA=0, shrinkB=0))
    st.line(ax, [-X * ftp / 2, X * ftp / 2], color=FILL['footprint'], lw=6, solid_capstyle='butt', zorder=2)
    plan_s5(ax, st, g, f)
    plan_s4(ax, st, g, s4, blade=1.5)
    show = (int(use[0]), int(g.c0), int(round(t_hi)))
    shades = {show[0]: C['arm'], show[1]: C['ray'], show[2]: C['beam']}
    brays = {c: bundle(ax, st, g, c, s4, shades[c]) for c in show}
    xs = [st(p)[0] for p in (beam0, ph.ray_geometry(g, g.r0, g.c0).pixel)]
    ax.set_xlim(xs[0] - 5, xs[1] + 175)
    yall = [st(p)[1] for p in (-X * ftp / 2, X * ftp / 2, beam0, s5_point(g, f.s5[1] + 4), s5_point(g, -f.s5[0] - 4))]
    ax.set_ylim(min(yall) - 1.5, max(yall) + 1.0)
    ax.set_xlabel('along the arm, h (mm)', fontsize=9, labelpad=1)
    ax.set_ylabel('across the arm,\ntowards higher 2θ (mm)', fontsize=9)
    ax.tick_params(labelsize=8)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
    # inset: the S4 opening, where every bundle narrows to the opening's width
    sl = st(ph.ray_geometry(g, g.r0, g.c0).slit_centre)
    ins = ax.inset_axes([0.40, 0.56, 0.22, 0.42])
    for c in show:
        bundle(ins, st, g, c, s4, shades[c])
    plan_s4(ins, st, g, s4, blade=0.25, lw=5)
    ins.set_xlim(sl[0] - 6, sl[0] + 6)
    ins.set_ylim(sl[1] - 0.42, sl[1] + 0.42)
    ins.tick_params(labelsize=7)
    ins.text(0.02, 0.97, 'at S4 (mm)', transform=ins.transAxes, fontsize=8, va='top', ha='left', color='#444444')
    ins.annotate('gap %.1f mm' % w4, (sl[0], sl[1] + s4[1]), xytext=(sl[0] + 1.2, sl[1] + 0.3), textcoords='data',
                 fontsize=8, color=FILL['slit'], ha='left', va='center', path_effects=HALO,
                 arrowprops=dict(arrowstyle='-', color=FILL['slit'], lw=0.5))
    ax.indicate_inset_zoom(ins, edgecolor='#888888', lw=0.6)

    def late_a():
        label_on_line(ax, st(beam0), st(-X * (ftp / 2 + 8)), r'$\mathbf{k}_\mathrm{in}$', C['beam'], size=11)
        label_on_line(ax, st(-X * ftp / 2), st(X * ftp / 2), 'footprint %.1f mm' % ftp, C['fp'], frac=0.25,
                      dy=-8, va='top')
        ys = spread_labels([st(ph.ray_geometry(g, g.r0, c).pixel)[1] for c in show], 4.0)
        for c, y in zip(show, ys):
            xs_ = [q.source[0] for q in brays[c]]
            p0 = st(ph.ray_geometry(g, g.r0, c).pixel)
            lit = ph.column_acceptance(g, c, *s4, n=15).lit_fraction(ftp)
            ax.annotate('c = %d sees x = %s…%s mm%s' % (c, signed(min(xs_)), signed(max(xs_)),
                                                        '' if lit > 0.999 else ',\n%.0f %% of it lit' % (100 * lit)),
                        p0, xytext=(p0[0] + 10, y), textcoords='data', fontsize=8.5, color=shades[c], ha='left',
                        va='center', path_effects=HALO,
                        arrowprops=dict(arrowstyle='-', color=shades[c], lw=0.5, alpha=0.6))
        ax.annotate('S4: %.1f mm (S4L %.1f + S4R %.1f)' % (w4, s4[0], s4[1]),
                    st(ph.ray_geometry(g, g.r0, g.c0).slit_centre - (s4[1] + 1.5) * ph.ray_geometry(g, g.r0, g.c0).e_h),
                    xytext=(0, 6), textcoords='offset points', ha='center', va='bottom', fontsize=9,
                    color=FILL['slit'], path_effects=HALO)
        ax.annotate('S5: %.1f | %.1f mm' % f.s5, st(s5_point(g, f.s5[1] + 4)), xytext=(-6, 4),
                    textcoords='offset points', ha='right', va='bottom', fontsize=9, color=C['s5'],
                    path_effects=HALO)
        ax.set_title('(a) plan view — each column accepts a bundle of rays through the %.1f mm S4 opening '
                     '(across the arm drawn ×%.0f)' % (w4, plan_magnification(ax)), fontsize=10, loc='left')

    # (b) one column's 2θ acceptance for several S4 openings
    bx = fig.add_axes([0.07, 0.375, 0.38, 0.185])
    widths = (0.1, 0.2, 0.4)
    greys = {0.1: '#9A9A9A', 0.2: C['ray'], 0.4: '#5A5A5A'}
    styles = {0.1: (0, (2, 1)), 0.2: '-', 0.4: (0, (5, 2))}
    bins = np.arange(-0.12, 0.12 + 1e-9, col_deg / 12)
    bx.axvspan(-col_deg / 2, col_deg / 2, color=FILL['detector'], lw=0)
    tc = deg(ph.ray_geometry(g, g.r0, g.c0).two_theta)
    ymax = 0.0
    for w in widths:
        a_ = ph.column_acceptance(g, g.c0, w / 2, w / 2, n=41)
        h, e = np.histogram(np.degrees(a_.two_theta.ravel()) - tc, bins=bins)
        h = h * (w / 41 / 41) / (e[1] - e[0])                      # each ray: its share of pixel × opening
        full = np.ptp(np.degrees(a_.two_theta))
        bx.step(0.5 * (e[:-1] + e[1:]), h, where='mid', color=greys[w], ls=styles[w], lw=2.0 if w == w4 else 1.3,
                label='S4 %.1f mm%s: %.3f° (%.1f columns)' % (w, ' (NX)' if w == w4 else '', full, full / col_deg))
        ymax = max(ymax, h.max())
    bx.legend(fontsize=7.5, frameon=False, loc='upper left', handlelength=2.2, title='full width',
              title_fontsize=7.5, alignment='left')
    bx.annotate('one column = one 2θ bin\n(%.4f°)' % col_deg, (col_deg / 2, 0.15 * ymax), xytext=(0.07, 0.3 * ymax),
                textcoords='data', ha='left', va='center', fontsize=7.5, color='#4A6F96',
                arrowprops=dict(arrowstyle='-', color='#4A6F96', lw=0.5))
    bx.set_xlim(bins[0], bins[-1])
    bx.set_ylim(0, ymax * 1.9)
    bx.set_xlabel('2θ − 2θ of the column (°)', fontsize=9, labelpad=1)
    bx.set_ylabel('accepted (∝ counts)', fontsize=9)
    bx.set_yticks([])
    top = bx.secondary_xaxis('top', functions=(lambda d: d / col_deg, lambda c: c * col_deg))
    top.tick_params(labelsize=7.5)
    bx.tick_params(labelsize=8)
    bx.spines['right'].set_visible(False)
    bx.set_title('(b) column c0 accepts 2θ over %.3f° = %.1f columns (top axis)' % (
        np.ptp(np.degrees(acc.two_theta)), np.ptp(np.degrees(acc.two_theta)) / col_deg), fontsize=10,
        loc='left', pad=24)

    # (c) how lit the columns near the footprint's downstream end are
    cx = fig.add_axes([0.56, 0.375, 0.38, 0.185])
    cols = np.arange(t_hi - 6, t_hi + 6.01, 0.25)
    curves = ((0.0, '#B0B0B0', (0, (2, 1))), (0.2, C['ray'], '-'), (0.4, '#7A7A7A', (0, (5, 2))),
              (1.0, '#4A4A4A', (0, (1, 1.5))))
    cx.axvspan(i_hi, o_hi, color=FILL['seen'], alpha=0.22, lw=0)
    for w, colr, ls in curves:
        lit = [ph.column_acceptance(g, c, w / 2, w / 2, n=15).lit_fraction(ftp) for c in cols]
        cx.plot(cols, lit, color=colr, ls=ls, lw=2.0 if w == w4 else 1.3,
                label='pixel only (S4 a line)' if w == 0 else 'S4 %.1f mm%s' % (w, ' (NX)' if w == w4 else ''))
    cx.legend(fontsize=7.5, frameon=False, loc='upper right', bbox_to_anchor=(1.0, 0.93), handlelength=2.2)
    cx.axvline(t_hi, color=C['ray'], lw=0.8, ls=(0, (2, 2)))
    cx.text(t_hi, 1.04, 'S4 as a line: edge at %.1f' % t_hi, ha='center', va='bottom', fontsize=8, color=C['ray'])
    cx.axvline(c_hi, color=C['approx'], lw=0.8, ls=(0, (4, 2)))
    cx.text(c_hi + 0.15, 0.5, 'reader\'s window\nends %.1f (P39)' % c_hi, ha='left', va='center', fontsize=8,
            color=C['approx'], path_effects=HALO)
    cx.set_xlim(cols[0], cols[-1])
    cx.set_ylim(-0.03, 1.14)
    cx.set_xlabel('column', fontsize=9, labelpad=1)
    cx.set_ylabel('share of the column lit', fontsize=9)
    cx.tick_params(labelsize=8)
    for sp in ('top', 'right'):
        cx.spines[sp].set_visible(False)
    cx.set_title('(c) the footprint\'s end is a ramp, %s (shaded), not a step' % fmt_cols(i_hi, o_hi),
                 fontsize=10, loc='left', pad=24)

    # (d) a wider or narrower S4: resolution and edge ramps (columns); (e) counts
    ws = np.geomspace(0.02, 1.0, 15)
    full, ramp, s5ramp, counts = [], [], [], []
    t_nx = ph.column_acceptance(g, g.c0, *s4, n=3).throughput(ftp)
    for w in ws:
        a_ = ph.column_acceptance(g, g.c0, w / 2, w / 2, n=3)
        full.append(np.ptp(a_.two_theta))
        (olo, ohi), (ilo, ihi) = ph.s4_window(g, s1v, w / 2, w / 2, s1s)
        ramp.append(ohi - ihi)
        s5ramp.append(abs(ph.s5_window(g, *f.s5, slit_offset=w / 2)[1] - ph.s5_window(g, *f.s5, slit_offset=-w / 2)[1]))
        counts.append(a_.throughput(ftp) / t_nx)
    colw = ph.PIXEL_MM / g.d_pinhole
    dx = fig.add_axes([0.07, 0.10, 0.38, 0.19])
    series = ((np.array(full) / colw, 'a column\'s 2θ acceptance', C['ray']),
              (np.array(ramp), 'footprint-edge ramp', C['fp']),
              (np.array(s5ramp), 'S5-edge ramp', C['s5']))
    for y, lab, colr in series:
        dx.plot(ws, y, color=colr, lw=1.4)
        dx.annotate(lab, (ws[-1], y[-1]), xytext=(4, 0), textcoords='offset points', fontsize=8, color=colr,
                    va='center', ha='left')
    k = int(np.argmin(np.abs(ws - w4)))
    dx.axvline(w4, color=C['det'], lw=0.8, ls=(0, (3, 2)))
    dx.text(w4, 1.0, ' NX %.1f mm' % w4, color=C['det'], fontsize=8, ha='left', va='top',
            transform=dx.get_xaxis_transform())
    dx.set_xscale('log')
    dx.set_yscale('log')
    dx.set_xlabel('S4 opening, S4L + S4R (mm)', fontsize=9, labelpad=1)
    dx.set_ylabel('full width (columns)', fontsize=9)
    dx.tick_params(labelsize=8)
    for sp in ('top', 'right'):
        dx.spines[sp].set_visible(False)
    dx.set_title('(d) a wider S4 blurs 2θ and the footprint\'s edges; S5\'s hardly', fontsize=10, loc='left')
    ex = fig.add_axes([0.66, 0.10, 0.27, 0.19])
    ex.plot(ws, counts, color=C['ray'], lw=1.4)
    ex.axvline(w4, color=C['det'], lw=0.8, ls=(0, (3, 2)))
    ex.axhline(1.0, color='#BBBBBB', lw=0.6)
    for w in (ws[0], ws[-1]):
        k = int(np.argmin(np.abs(ws - w)))
        ex.annotate('×%.2g at %.2g mm' % (counts[k], ws[k]), (ws[k], counts[k]),
                    xytext=(10, -2) if k == 0 else (-6, 0), textcoords='offset points',
                    ha='left' if k == 0 else 'right', va='top' if k == 0 else 'center', fontsize=8)
    ex.set_ylim(0.05, None)
    ex.set_xscale('log')
    ex.set_yscale('log')
    ex.set_xlabel('S4 opening (mm)', fontsize=9, labelpad=1)
    ex.set_ylabel('counts per column (× NX)', fontsize=9)
    ex.tick_params(labelsize=8)
    for sp in ('top', 'right'):
        ex.spines[sp].set_visible(False)
    ex.set_title('(e) …and passes light in proportion', fontsize=10, loc='left')
    caption(fig, 'Case 8 — What the finite S4 opening does',
            'S4 is a %.1f mm gap, not a line (<LOW>, Det_Th %.1f°, row r0): each column accepts a bundle of rays '
            '(a, b), the footprint\'s edges become ramps (c); a wider S4 trades resolution for counts (d, e).'
            % (w4, deg(g.dth)),
            'column_acceptance (and .lit_fraction, .throughput), s4_window, footprint_columns, footprint_window, '
            's5_window(slit_offset), ray_geometry.', provenance(f))
    save(fig, [], os.path.join(out, 'case8_s4_opening.png'), late=[late_a])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--out', default=os.path.join(ROOT, 'docs', 'figures', 'pinhole'))
    p.add_argument('--only', type=int, nargs='*', help='case numbers to draw (default: all)')
    p.add_argument('--spec', default=None, help='another SPEC file (default: the public NX file)')
    p.add_argument('--low', type=int, default=11, help='its low-Qz GID scan (stands in for NX 11)')
    p.add_argument('--high', type=int, default=12, help='its high-Qz GID scan (stands in for NX 12)')
    p.add_argument('--label', default=None, help='name of the data in the figure headers')
    args = p.parse_args(argv)
    if args.spec:
        spec = os.path.abspath(args.spec)
        DATA.update(spec=spec, label=args.label or os.path.basename(spec), scans={11: args.low, 12: args.high})
        _frames.cache_clear()                      # the NX frames read at import (module size) must not be reused
        private = os.path.join(ROOT, 'sample_data', 'private')
        out = os.path.abspath(args.out)
        if spec.startswith(private) and out.startswith(ROOT) and not out.startswith(private):
            raise SystemExit('private data: write the figures outside the repository or under sample_data/private/ '
                             '(git-ignored), not to %s' % args.out)
    os.makedirs(args.out, exist_ok=True)
    cases = [case1, case2, case3, case4, case5, case6, case7, case8]
    for k, fn in enumerate(cases, 1):
        if not args.only or k in args.only:
            fn(args.out)


if __name__ == '__main__':
    main()
