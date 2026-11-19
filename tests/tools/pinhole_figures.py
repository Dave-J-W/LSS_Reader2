"""Six isometric figures of the pinhole GID geometry (docs/figures/pinhole).

    python tests/tools/pinhole_figures.py [--out DIR]

Every point, vector and angle drawn is computed by the reader's own code
(lss_core.pinhole): ``ray_geometry`` (lab-frame ray, footprint → S4 slit →
pixel), ``pixel_angles`` (Mati Meron's IMG_COO_CONV transform, ported),
``column_two_theta`` / ``row_beta`` (the per-axis approximation),
``footprint_length`` / ``footprint_window`` / ``s5_window`` /
``usable_columns``; the frame parameters are read from the public NX school
SPEC file by tests/tools/pinhole_frames.py. This script only draws: it adds
drawing offsets, arc interpolation between two directions the reader
returned, and clipping to a close-up box, nothing that changes a number.
Writes case1_*.png … case6_*.png into the output folder and nothing else.
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
# dataviz palette validator: 4 hues, all-pairs normal-vision ΔE ≥ 15, contrast ≥ 3:1)
C = dict(lab='#6E6E6E', beam='#D0481E', arm='#2A6FD0', det='#0E8C5A', comp='#B5338A',
         ray='#1A1A1A', approx='#7A7A7A')
FILL = dict(footprint='#F5CDB3', seen='#C0652A', detector='#CFE1F3', ghost='#EDEDED', slit='#333333')
HALO = [pe.withStroke(linewidth=3.2, foreground='white')]
Z = np.array([0.0, 0.0, 1.0])
X = np.array([1.0, 0.0, 0.0])


# ---- the frames and the reader's numbers ----------------------------------------

@lru_cache(maxsize=None)
def _frames(scan):
    return tuple(frames_for(NX, [scan]))


def frame(scan, dth_deg):
    """The NX frame of ``scan`` whose Det_Th is nearest ``dth_deg``."""
    return min(_frames(scan), key=lambda f: abs(math.degrees(f.geom.dth) - dth_deg))


def usable(f):
    """The frame's usable columns (``usable_columns``: S5 and footprint windows)."""
    return ph.usable_columns(f.geom, NC, f.s5[0], f.s5[1], f.areainfo[1], f.s1_to_sample_mm)


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


def column_at_source(g, x, row, lo=-400.0, hi=600.0):
    """The (fractional) column whose ray starts at x on the beam axis
    (bisection on ``ray_geometry``'s source point, which grows with the column)."""
    f = lambda c: ph.ray_geometry(g, row, c).source[0] - x
    a, b = lo, hi
    assert f(a) * f(b) < 0, 'no sign change of the source point in the bracket'
    for _ in range(80):
        m = 0.5 * (a + b)
        if f(a) * f(m) <= 0:
            b = m
        else:
            a = m
    return 0.5 * (a + b)


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
              leader=False):
        if self.box is not None and not (np.all(p >= self.box[0]) and np.all(p <= self.box[1])):
            return
        self.ax.plot(*np.asarray(p, float)[:, None], 'o', color=color, ms=ms, zorder=z, mec='white', mew=0.8,
                     clip_on=False)
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
                    kw['arrowprops'] = dict(arrowstyle='-', color='#888888', lw=0.7, shrinkA=2, shrinkB=0)
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


def caption(fig, title, text, source):
    fig.text(0.02, 0.985, title, fontsize=13.5, fontweight='bold', va='top', ha='left', color='#111111')
    text = re.sub(r'(?<![\w.])-(?=\d)', '−', text)                  # minus signs
    wrapped = '\n'.join(textwrap.fill(p, 178) for p in text.split('\n'))
    fig.text(0.02, 0.012, wrapped, fontsize=9, va='bottom', ha='left', color='#222222', linespacing=1.35)
    fig.text(0.02, 0.955, source, fontsize=7.5, va='top', ha='left', color='#555555')


def text_overlaps(fig):
    """Pairs of texts whose boxes overlap, and texts outside the figure."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    ticks = set()
    for ax in fig.axes:
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


def save(fig, isos, path):
    for iso in isos:
        iso.fit()                                      # fixes the projections
    for iso in isos:
        iso.place_labels()
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
    return ('tests/tools/pinhole_figures.py · lss_core %s · NX school 20260923 scan %d, Det_Th %.1f°'
            % (rev, f.scan, deg(f.geom.dth)))


def mag_note(main, close):
    return '×%.0f vs (a)' % (close.scale() / main.scale())


TOP = [0.0, 0.53, 1.0, 0.39]             # panel (a): the whole set-up, full width
BOT = 0.20                               # the lower band starts here, above the caption


def new_fig():
    return plt.figure(figsize=(13, 10), dpi=DPI)


# ---- the six cases ---------------------------------------------------------------

def case1(out):
    """The lab frame and the detector's own coordinates."""
    f = frame(11, 16.0)
    g = f.geom
    P = (300, int(usable(f)[-1]))                    # a pixel that gets light: the last usable column
    rp = ph.ray_geometry(g, *P)
    corners = [ph.ray_geometry(g, r, c) for r, c in ((0, 0), (NR - 1, NC - 1))]
    D, Dp = ph.vertical_distance(g), ph.pinhole_distance(g)
    fig = new_fig()
    a = Iso(fig, TOP, '(a) set-up, true scale')
    scene(a, g, f, [rp] + corners)
    lab_axes(a, 60, origin=(-150, 120, 0))
    a.line([np.zeros(3), rp.centre], C['arm'], lw=1.0, ls=(0, (5, 3)))
    a.arrow(28 * rp.e_v, rp.centre + 28 * rp.e_v, C['arm'], r'$D$', where=0.3, side=1, both=True, lw=1.0)
    a.arrow(rp.slit_centre - 28 * rp.e_v, rp.centre - 28 * rp.e_v, C['arm'], r'$D_p$', where=0.5, side=-1,
            both=True, lw=1.0)
    ray_line(a, rp, 'ray', where=0.5, side=1)
    a.point(rp.source, C['ray'], 'F', dx=4, dy=-14, ha='left')
    a.point(rp.slit, C['ray'], 'S4', dx=-6, dy=8, ha='right')
    a.point(rp.pixel, C['ray'], 'P', dx=6, dy=4)
    a.finish()

    lo = rp.centre - np.array([50, 50, 50])
    hi = rp.centre + np.array([50, 50, 50])
    b = Iso(fig, [0.0, BOT, 1.0, 0.29], None, box=(lo, hi))
    b.poly(module_corners(g), FILL['detector'], '#4A6F96', z=1, lw=0.9)
    U = 20.0
    b.arrow(rp.centre, rp.centre + U * rp.n, C['arm'], r'$\mathbf{n}$', where=0.8, side=-1)
    b.arrow(rp.centre, rp.centre + U * rp.e_h, C['det'], r'$\mathbf{e}_h$', where=0.75, side=-1)
    b.arrow(rp.centre, rp.centre + U * rp.e_v, C['det'], r'$\mathbf{e}_v$', where=0.8, side=-1)
    corner = rp.centre + rp.wx * rp.e_h
    b.arrow(rp.centre, corner, C['comp'], r'$w_x$', where=0.6, side=-1, lw=2.0, off=13)
    b.arrow(corner, rp.pixel, C['comp'], r'$w_y$', where=0.5, side=1, lw=2.0)
    ray_line(b, rp, 'ray', where=0.5, side=1)
    b.line([rp.slit_centre, rp.centre], C['arm'], lw=1.0, ls=(0, (5, 3)))
    b.point(rp.centre, C['arm'], r'$(r_0, c_0)$', dx=45, dy=10, ha='left', va='bottom', leader=True)
    b.point(rp.pixel, C['ray'], 'P', dx=7, dy=2)
    b.finish()
    b.title = lambda: '(b) detector, close-up (%s), true geometry; unit vectors drawn %.0f mm long' % (mag_note(a, b), U)
    caption(fig, 'Case 1 — Lab frame, arm and the detector\'s coordinates',
            'Lab frame: x along the incident beam (k_in), y horizontal in the sample plane, z up; origin at the '
            'sample centre. The footprint (orange, %.1f × %.1f mm: footprint_length = S1v / sin α, S1h) lies on the '
            'beam axis. The arm points along n = (cos β0 cos δ, cos β0 sin δ, sin β0), δ = Det_Th = %.1f°, '
            'β0 = %.2f°; the flat detector is perpendicular to n at D = vertical_distance = %.1f mm; the S4 slit '
            '(black bar) is a line along e_v at D − D_p, D_p = %.0f mm. Pixel P = (row %d, column %d) sits at '
            'D·n + wx·e_h + wy·e_v with wx = −(c − c0)·p = %.2f mm (negative: towards higher 2θ, e_h points to '
            'lower 2θ) and wy = (r − r0)·p = %.2f mm, p = %.3f mm. Its ray starts at F on the beam axis '
            '(x = %.1f mm, inside the footprint: column %d is the last of usable_columns %d…%d), crosses the slit '
            'and ends on P: 2θ = %.3f°, β = %.3f° (pixel_angles: %.3f°, %.3f°).\n'
            'Every point and vector: lss_core.pinhole.ray_geometry (n, e_h, e_v, centre, pixel, slit, source); '
            'outline: ray_geometry at the module\'s corner pixels; footprint: footprint_length. '
            'Transform after Mati Meron\'s IMG_COO_CONV.'
            % (ph.footprint_length(g, f.areainfo[1], f.s1_to_sample_mm), f.areainfo[0], deg(g.dth), deg(g.beta0),
               D, Dp, P[0], P[1], rp.wx, rp.wy, ph.PIXEL_MM, rp.source[0], P[1], usable(f)[0], usable(f)[-1],
               deg(rp.two_theta), deg(rp.beta),
               *(deg(x[0, 0]) for x in ph.pixel_angles(g, [P[0]], [P[1]]))),
            provenance(f))
    save(fig, [a, b], os.path.join(out, 'case1_lab_frame_and_detector.png'))


def case2(out):
    """Where the per-axis formulas are exact: the direct-beam row and column."""
    f = frame(11, 16.0)
    g = f.geom
    A, B = (int(g.r0), int(usable(f)[-1])), (400, int(g.c0))     # both in usable_columns
    ra, rb = ph.ray_geometry(g, *A), ph.ray_geometry(g, *B)
    fig = new_fig()
    a = Iso(fig, [0.0, BOT, 0.66, 0.72], '(a) true scale')
    scene(a, g, f, [ra, rb, ph.ray_geometry(g, NR - 1, 0)])
    lab_axes(a, 60)
    a.line([ph.ray_geometry(g, g.r0, -0.5).pixel, ph.ray_geometry(g, g.r0, NC - 0.5).pixel], C['det'], lw=2.2, z=2)
    a.line([ph.ray_geometry(g, -0.5, g.c0).pixel, ph.ray_geometry(g, NR - 0.5, g.c0).pixel], C['det'], lw=2.2, z=2)
    ray_line(a, ra, 'ray A', where=0.55, side=-1)
    ray_line(a, rb, 'ray B', where=0.55, side=1)
    a.point(ra.pixel, C['ray'], 'A', dx=7, dy=-6, va='top')
    a.point(rb.pixel, C['ray'], 'B', dx=7, dy=2)
    a.point(ra.source, C['ray'], r'$F_A$', dx=6, dy=-14)
    a.point(rb.source, C['ray'], r'$F_B$', dx=-6, dy=-14, ha='right')
    hb = np.array([rb.direction[0], rb.direction[1], 0.0])
    hb /= np.linalg.norm(hb)
    ha_ = np.array([ra.direction[0], ra.direction[1], 0.0])
    ha_ /= np.linalg.norm(ha_)
    a.line([ra.source, ra.source + 260 * X], C['lab'], lw=0.8, ls=(0, (3, 3)))
    a.arc(ra.source, X, ha_, 230, C['ray'], r'$2\theta_A$', out=14)
    a.line([rb.source, rb.source + 420 * hb], C['lab'], lw=0.8, ls=(0, (3, 3)))
    a.arc(rb.source, hb, rb.direction, 400, C['ray'])
    a.point(rb.source + 400 * rb.direction, C['ray'], r'$\beta_B$', dx=-2, dy=10, ha='center', va='bottom',
            size=11, ms=0.1)
    a.finish()

    # (b) per-axis minus exact β over the module: zero along the direct-beam row and column
    rows, cols = np.arange(NR), np.arange(NC)
    tt, bb = ph.pixel_angles(g, rows, cols)
    tpa, bpa = per_axis(g, rows, cols)
    db = np.degrees(bpa[:, None] - bb)
    dt = np.degrees(tpa[None, :] - tt)
    bx = fig.add_axes([0.70, 0.25, 0.2, 0.64])
    lim = np.abs(db).max()
    im = bx.imshow(db, origin='lower', cmap='coolwarm', vmin=-lim, vmax=lim, aspect='equal',
                   extent=(-0.5, NC - 0.5, -0.5, NR - 0.5))
    bx.axhline(g.r0, color=C['det'], lw=1.5)
    bx.axvline(g.c0, color=C['det'], lw=1.5)
    bx.plot([A[1]], [A[0]], 'o', color=C['ray'], ms=5, mec='white')
    bx.plot([B[1]], [B[0]], 'o', color=C['ray'], ms=5, mec='white')
    bx.annotate('A', (A[1], A[0]), xytext=(5, 5), textcoords='offset points', fontsize=10, path_effects=HALO)
    bx.annotate('B', (B[1], B[0]), xytext=(5, 5), textcoords='offset points', fontsize=10, path_effects=HALO)
    bx.text(NC - 4, g.r0 - 8, r'row $r_0$', color=C['det'], ha='right', va='top', fontsize=9, path_effects=HALO)
    bx.text(g.c0 + 4, NR - 10, r'column $c_0$', color=C['det'], ha='left', va='top', fontsize=9,
            rotation=90, path_effects=HALO)
    bx.set_xlabel('column', fontsize=9)
    bx.set_ylabel('row', fontsize=9)
    bx.tick_params(labelsize=8)
    bx.set_title('(b) β per-axis − exact (°), this module', fontsize=10, loc='left')
    cb = fig.colorbar(im, ax=bx, fraction=0.08, pad=0.03)
    cb.ax.tick_params(labelsize=8)
    def row_err(fr):                                  # max |per-axis − exact| on the direct-beam row
        gg = fr.geom
        cols_, use_ = np.arange(NC), usable(fr)
        t_, b_ = ph.pixel_angles(gg, [gg.r0], cols_)
        tp_, bp_ = per_axis(gg, [gg.r0], cols_)
        db_ = np.degrees(np.abs(bp_[0] - b_[0]))
        return db_.max(), db_[use_].max(), np.degrees(np.abs(tp_ - t_[0])).max()
    hi_f = frame(12, 14.0)
    rlo, rhi = row_err(f), row_err(hi_f)
    tc, bc = ph.pixel_angles(g, np.arange(NR), [g.c0])
    tcp, bcp = per_axis(g, np.arange(NR), np.array([int(g.c0)]))
    tch, bch = ph.pixel_angles(hi_f.geom, np.arange(NR), [hi_f.geom.c0])
    tchp, bchp = per_axis(hi_f.geom, np.arange(NR), np.array([int(hi_f.geom.c0)]))
    col_err = max(np.degrees(np.abs(bc[:, 0] - bcp)).max(), np.degrees(np.abs(bch[:, 0] - bchp)).max(),
                  np.degrees(np.abs(tc[:, 0] - tcp[0])).max(), np.degrees(np.abs(tch[:, 0] - tchp[0])).max())
    ea = (deg(ra.two_theta), deg(per_axis(g, A[0], A[1])[0][0]), deg(ra.beta), deg(per_axis(g, A[0], A[1])[1][0]))
    eb = (deg(rb.two_theta), deg(per_axis(g, B[0], B[1])[0][0]), deg(rb.beta), deg(per_axis(g, B[0], B[1])[1][0]))
    caption(fig, 'Case 2 — Per-axis angles: exact on the direct-beam column, on the row only at β0 = 0',
            'The reader used to give every column one 2θ (column_two_theta: Det_Th + atan((c − c0)p/D_p)) and every '
            'row one β (row_beta: β0 + atan((r − r0)p/D)); the cuts and the image axes still do (P38). On the '
            'direct-beam column c0 = %d they are exact at any β0 (largest difference %.1e° over the column, here '
            'and at β0 = 6.5°). On the direct-beam row r0 = %d they are exact only at β0 = 0: here (β0 = %.2f°) β is '
            'off by up to %.3f° along the row (2θ %.1e°); on the high level (scan 12, β0 = 6.5°) by %.2f° over the '
            'module, %.2f° inside the usable columns, and 2θ by %.3f°. Pixel A (row r0, column %d): 2θ exact '
            '%.4f°, per-axis %.4f°; β %.4f° vs %.4f°. Pixel B (row %d, column c0): 2θ %.4f° vs %.4f°; β %.4f° vs '
            '%.4f°. The arcs are the ray\'s own angles, 2θ from the beam axis in the horizontal plane and β from '
            'the horizontal (dashed grey: the reference directions). A and B are in usable_columns. Away from that '
            'cross the per-axis β is off by up to %.2f° (b; 2θ by at most %.4f° on this level arm, case 5 for a raised arm), because each column '
            'sees another footprint point F (case 3, case 4).\n'
            'Rays, points and arcs: ray_geometry (source, slit, pixel, direction, two_theta, beta); map (b): '
            'pixel_angles (exact, IMG_COO_CONV by Mati Meron) minus column_two_theta/row_beta. Arc radii 230 and '
            '400 mm are drawing choices.'
            % (g.c0, col_err, g.r0, deg(g.beta0), rlo[0], rlo[2], rhi[0], rhi[1], rhi[2], A[1], *ea, B[0], *eb,
               np.abs(db).max(), np.abs(dt).max()),
            provenance(f))
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


def case3(out):
    """Top view of the pinhole: each column sees its own footprint point."""
    f = frame(11, 16.0)
    g = f.geom
    r0 = g.r0
    ftp = ph.footprint_length(g, f.areainfo[1], f.s1_to_sample_mm)
    use = usable(f)
    flo, fhi = ph.footprint_window(g, f.areainfo[1], f.s1_to_sample_mm)
    s5lo, s5hi = ph.s5_window(g, *f.s5)
    cend = [column_at_source(g, -ftp / 2, r0), column_at_source(g, ftp / 2, r0)]
    exact = {c: ph.ray_geometry(g, r0, c) for c in (cend[0], g.c0, cend[1])}
    idl = {c: ph.ray_geometry(g, r0, c) for c in (flo, fhi)}
    ends = {c: ph.ray_geometry(g, r0, c) for c in (use[0], use[-1])}
    seen = [ends[use[0]].source, ends[use[-1]].source]
    fig = new_fig()
    a = Iso(fig, TOP, '(a) true scale, rays to the direct-beam row')
    scene(a, g, f, list(exact.values()) + [ph.ray_geometry(g, NR - 1, 0)], beam_from=-150)
    lab_axes(a, 50)
    a.line(seen, FILL['seen'], lw=4.0, z=2)
    for c, r in exact.items():
        ray_line(a, r, 'ray' if c == g.c0 else None, where=0.5, side=1)
    for r in idl.values():
        ray_line(a, r, color=C['approx'], ls=(0, (4, 3)), lw=1.0)
    a.point(exact[g.c0].slit, C['ray'], 'S4', dx=-6, dy=10, ha='right')
    a.finish()

    # (b) plan view in the arm's frame: along h (the arm's azimuth) and
    # towards higher 2θ (−e_h), the second exaggerated by K (affine: rays stay straight)
    K = 5.0
    r = exact[g.c0]
    st = lambda p: (float(np.dot(p, r.h)), K * float(np.dot(p, -r.e_h)))
    bx = fig.add_axes([0.05, BOT + 0.01, 0.84, 0.28])
    for c, rr in exact.items():
        pts = [st(rr.source), st(rr.pixel)]
        bx.plot(*zip(*pts), color=C['ray'], lw=1.1)
    for c, rr in idl.items():
        bx.plot(*zip(st(rr.source), st(rr.pixel)), color=C['approx'], lw=1.0, ls=(0, (4, 3)))
    beam = [st(-X * (ftp / 2 + 60)), st(X * (ftp / 2 + 20))]
    bx.annotate('', xy=st(-X * (ftp / 2 + 8)), xytext=beam[0],
                arrowprops=dict(arrowstyle='-|>', color=C['beam'], lw=2.0, shrinkA=0, shrinkB=0))
    (bx0, by0), (bx1, by1) = st(-X * (ftp / 2 + 60)), st(-X * (ftp / 2 + 8))
    bx.text(0.5 * (bx0 + bx1), 0.5 * (by0 + by1), r'$\mathbf{k}_\mathrm{in}$', color=C['beam'], fontsize=11,
            rotation=math.degrees(math.atan2(by1 - by0, bx1 - bx0)), rotation_mode='anchor', ha='center',
            va='bottom', transform_rotates_text=True, path_effects=HALO)
    bx.plot(*zip(st(-X * ftp / 2), st(X * ftp / 2)), color=FILL['footprint'], lw=5, solid_capstyle='butt')
    (fx0, fy0), (fx1, fy1) = st(-X * ftp / 2), st(X * ftp / 2)
    bx.annotate('footprint', st(X * 0.0), xytext=(9, 9), textcoords='offset points', fontsize=9, color='#8A4A20',
                rotation=math.degrees(math.atan2(fy1 - fy0, fx1 - fx0)), rotation_mode='anchor', ha='left',
                va='center', transform_rotates_text=True)
    bx.plot(*zip(st(seen[0]), st(seen[1])), color=FILL['seen'], lw=5, solid_capstyle='butt')
    det = [st(ph.ray_geometry(g, r0, c).pixel) for c in (-0.5, NC - 0.5)]
    bx.plot(*zip(*det), color='#4A6F96', lw=2)
    bx.plot(*zip(st(ph.ray_geometry(g, r0, use[0]).pixel), st(ph.ray_geometry(g, r0, use[-1]).pixel)),
            color='#9DC3E6', lw=9, solid_capstyle='butt', zorder=1)
    bx.plot(*st(r.slit), 'o', color=C['ray'], ms=5, mec='white')
    bx.annotate('S4', st(r.slit), xytext=(0, 10), textcoords='offset points', ha='center', fontsize=10)
    # column labels: solid rays beyond the detector, dashed ones beside their source
    keys = list(exact)
    ys = spread_labels([st(exact[c].pixel)[1] for c in keys], 7.0)
    for c, y in zip(keys, ys):
        x0, y0 = st(exact[c].pixel)
        bx.annotate(('c = %.1f' % c) if c != g.c0 else 'c = c0 = %d' % c, (x0, y0), xytext=(x0 + 12, y),
                    textcoords='data', fontsize=9, va='center', ha='left', color=C['ray'],
                    arrowprops=dict(arrowstyle='-', color='#999999', lw=0.6, shrinkA=0, shrinkB=2))
    for c, rr in idl.items():
        x0, y0 = st(rr.source)
        bx.annotate(('c = %.1f' % c).replace('-', '−'), (x0, y0), xytext=(-8, -4) if c < g.c0 else (10, -12),
                    textcoords='offset points', fontsize=8.5, ha='right' if c < g.c0 else 'left', va='center', color=C['approx'],
                    path_effects=HALO)
    lo = st(-X * (ftp / 2 + 62))
    bx.set_xlim(lo[0] - 5, det[0][0] + 70)
    yall = [st(p)[1] for p in (exact[cend[0]].pixel, exact[cend[1]].pixel, -X * ftp / 2, X * ftp / 2,
                               -X * (ftp / 2 + 60))]
    bx.set_xlabel('along the arm, h (mm)', fontsize=9)
    bx.set_ylabel('towards higher 2θ, −e_h\n(mm, drawn ×%.0f)' % K, fontsize=9)
    yt = bx.get_yticks()
    bx.set_yticks(yt)
    bx.set_yticklabels(['%g' % (v / K) for v in yt])
    bx.set_ylim(min(yall) - 16, max(yall) + 12)
    bx.tick_params(labelsize=8)
    for sp in ('top', 'right'):
        bx.spines[sp].set_visible(False)
    bx.set_title('(b) plan view in the arm\'s frame; across the arm magnified ×%.0f' % K, fontsize=10, loc='left')
    caption(fig, 'Case 3 — The pinhole seen from above: every column sees its own footprint point',
            'S4 is a narrow vertical slit D_p = %.0f mm in front of the detector, so a column receives light '
            'along one line only: from the point F on the beam axis that lies on the plane through the slit and '
            'the pixel. At Det_Th = %.1f° the footprint (%.1f mm long, footprint_length = S1v / sin α) is seen by '
            'columns %.1f to %.1f (black: the rays from its two ends, found by solving ray_geometry\'s source = '
            '±%.1f mm). The reader\'s footprint_window (PD_PIN_RANGE) gives %.1f to %.1f (dashed grey; their rays '
            'start at x = %.1f and %.1f mm): the same width, but centred on c0 = %d, while the true window is '
            'not symmetric. S5 (s5_window) passes columns %.1f to %.1f; usable_columns, the intersection, is '
            '%d…%d (pale blue on the detector); the darker part of the footprint is what those columns see '
            '(x = %.1f … %.1f mm). The ray to column %.1f passes S4 but S5 stops it before the detector; it is '
            'drawn to show where the footprint\'s end would land. In (b) the distance across the arm is magnified ×%.0f so the fan can be seen; '
            'rays stay straight under that scaling.\n'
            'Rays and points: ray_geometry(g, r0, c).source/.slit/.pixel/.h/.e_h; windows: footprint_window, '
            's5_window, usable_columns; footprint: footprint_length.'
            % (g.d_pinhole, deg(g.dth), ftp, cend[0], cend[1], ftp / 2, flo, fhi, idl[flo].source[0],
               idl[fhi].source[0], g.c0, s5lo, s5hi, use[0], use[-1], seen[0][0], seen[1][0], cend[0], K),
            provenance(f))
    save(fig, [a], os.path.join(out, 'case3_pinhole_top_view.png'))


def case4(out):
    """β depends on the column: two pixels of one row, two footprint points."""
    f = frame(11, 16.0)
    g = f.geom
    use = usable(f)
    row = NR - 1
    c1, c2 = int(use[0]), int(use[-1])
    r1, r2 = ph.ray_geometry(g, row, c1), ph.ray_geometry(g, row, c2)
    fig = new_fig()
    a = Iso(fig, TOP, '(a) true scale')
    scene(a, g, f, [r1, r2, ph.ray_geometry(g, 0, 0)], beam_from=-150)
    lab_axes(a, 50)
    ray_line(a, r1, 'c = %d' % c1, where=0.55, side=-1, size=9.5)
    ray_line(a, r2, 'c = %d' % c2, where=0.55, side=1, size=9.5)
    a.point(r1.source, C['ray'], r'$F_1$', dx=-5, dy=-14, ha='right')
    a.point(r2.source, C['ray'], r'$F_2$', dx=5, dy=-14)
    a.finish()

    mid = 0.5 * (r1.slit + r2.slit)
    half = 6.0
    b = Iso(fig, [0.0, BOT, 0.5, 0.29], None, box=(mid - half, mid + half))
    b.line([r1.slit_centre + (np.dot(mid - r1.slit_centre, r1.e_v) - 2 * half) * r1.e_v,
            r1.slit_centre + (np.dot(mid - r1.slit_centre, r1.e_v) + 2 * half) * r1.e_v], FILL['slit'], lw=3, z=2)
    upper = 1 if r1.slit[2] > r2.slit[2] else -1          # label each ray on its outer side
    for r, c, side in ((r1, c1, upper), (r2, c2, -upper)):
        b.line([r.source, r.slit], C['ray'], lw=1.2)
        b.arrow(r.slit, r.pixel, C['ray'], 'c = %d' % c, where=0.75, side=side, lw=1.2, size=9.5)
        b.point(r.slit, C['ray'])
    b.arrow(r2.slit, r1.slit, C['arm'], '%.2f mm' % np.linalg.norm(r1.slit - r2.slit), where=0.5, side=-1,
            both=True, lw=1.0, size=9, off=10)
    b.finish()
    b.title = lambda: '(b) at the slit (%s)' % mag_note(a, b)

    # (c) β along the row: exact against per-axis
    cx = fig.add_axes([0.58, BOT + 0.03, 0.38, 0.23])
    cols = np.arange(NC)
    _, bb = ph.pixel_angles(g, [row], cols)
    _, bpa = per_axis(g, [row], cols)
    cx.axvspan(use[0], use[-1], color=FILL['detector'], lw=0)
    cx.plot(cols, np.degrees(bb[0]), color=C['ray'], lw=1.6)
    cx.plot(cols, np.degrees(np.full(NC, bpa[0])), color=C['approx'], lw=1.4, ls=(0, (4, 3)))
    cx.annotate('exact (pixel_angles)', (3 * NC // 4, np.degrees(bb[0, 3 * NC // 4])), xytext=(-6, 8), textcoords='offset points',
                color=C['ray'], ha='right', va='bottom', fontsize=9)
    cx.text(cols[3], np.degrees(bpa[0]), 'per-axis (row_beta)', color=C['approx'], ha='left', va='bottom',
            fontsize=8.5)
    for c in (c1, c2):
        cx.plot([c], [np.degrees(bb[0, c])], 'o', color=C['ray'], ms=5, mec='white')
        cx.annotate('%.3f°' % np.degrees(bb[0, c]), (c, np.degrees(bb[0, c])), xytext=(6, -12),
                    textcoords='offset points', fontsize=8.5, ha='left')
    cx.text(0.5 * (use[0] + use[-1]), np.degrees(bb[0]).min(), 'usable\ncolumns', ha='center', va='bottom',
            fontsize=8, color='#4A6F96')
    cx.set_xlabel('column', fontsize=9)
    cx.set_ylabel('β (°), row %d' % row, fontsize=9)
    cx.tick_params(labelsize=8)
    cx.set_title('(c) β along the top row', fontsize=10, loc='left')
    for s in ('top', 'right'):
        cx.spines[s].set_visible(False)
    dmax = np.abs(np.degrees(bpa[0] - bb[0, use])).max()
    caption(fig, 'Case 4 — Why β depends on the column',
            'Two pixels on the top row (%d) at the ends of the usable columns (%d and %d, usable_columns). Through '
            'the slit they see different footprint points, F1 at x = %.1f mm and F2 at x = %.1f mm, at different '
            'distances from the detector; their rays cross the slit line %.2f mm apart in height (b) and leave the '
            'surface at β = %.3f° and %.3f°, a difference of %.3f°. The per-axis formula (row_beta) gives the row one '
            'β, %.3f°: off by up to %.3f° inside the usable columns on this row (c). In (a), at true scale, the '
            'difference at the slit cannot be seen; (b), a %.0f mm box around the slit crossings '
            '(magnification stated on the panel), drawn from the same ray_geometry points, shows that they pass '
            'it at different heights.\n'
            'Rays, slit points, F1, F2: ray_geometry; (c): pixel_angles (IMG_COO_CONV, Mati Meron) and row_beta.'
            % (row, c1, c2, r1.source[0], r2.source[0], np.linalg.norm(r1.slit - r2.slit), deg(r1.beta),
               deg(r2.beta), deg(r2.beta - r1.beta), np.degrees(bpa[0]), dmax, 2 * half),
            provenance(f))
    save(fig, [a, b], os.path.join(out, 'case4_beta_depends_on_column.png'))


def case5(out):
    """Raised arm: the (u, v, w) of IMG_COO_CONV; 2θ depends on the row."""
    f = frame(12, 14.0)
    g = f.geom
    use = usable(f)
    col = int(use[-1])                               # (a): a column that gets light
    edge = NC - 1                                    # (b) also shows the module's edge column
    rt, rb_ = ph.ray_geometry(g, NR - 1, col), ph.ray_geometry(g, 0, col)
    fig = new_fig()
    a = Iso(fig, TOP, '(a) true scale, β0 = %.1f°' % deg(g.beta0))
    scene(a, g, f, [rt, rb_], beam_from=-120)
    lab_axes(a, 50)
    a.line([np.zeros(3), rt.centre], C['arm'], lw=1.0, ls=(0, (4, 3)))
    a.arrow(np.zeros(3), 90 * rt.n, C['arm'], r'$\mathbf{n}$', where=0.6, side=1)
    a.arrow(rt.slit, rt.slit + rt.u * rt.e_h, C['comp'], r'$u$', where=0.5, side=1, lw=2.0, off=13)
    p1 = rt.slit + rt.u * rt.e_h
    a.arrow(p1, p1 + rt.v * rt.h, C['comp'], r'$v$', where=0.5, side=-1, lw=2.0)
    p2 = p1 + rt.v * rt.h
    a.arrow(p2, p2 + rt.w * Z, C['comp'], r'$w$', where=0.5, side=1, lw=2.0)
    ray_line(a, rt, 'ray, row %d' % (NR - 1), where=0.45, side=1, size=9.5)
    ray_line(a, rb_, 'row 0', where=0.45, side=-1, size=9.5)
    a.point(rt.slit, C['ray'], 'S', dx=-8, dy=-4, ha='right', va='top')
    a.point(rt.pixel, C['ray'], 'P', dx=6, dy=2)
    a.finish()

    # (b) 2θ − Det_Th along columns, against the row
    bx = fig.add_axes([0.07, BOT + 0.03, 0.78, 0.24])
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
        bx.plot(rows, y, color=C['ray'], lw=1.5)
        ends.append((y[-1], 'c = %d%s' % (c, '' if use[0] <= c <= use[-1] else ' (no light)'), C['ray']))
    y11 = np.degrees(t11 - per_axis(g11, rows, np.array([edge]))[0][0])
    bx.plot(rows, y11, color=C['approx'], lw=1.3, ls=(0, (4, 3)))
    ends.append((y11[-1], 'c = %d, arm level (scan 11)' % edge, C['approx']))
    span = max(e[0] for e in ends) - min(e[0] for e in ends)
    for (y, text, colour), yl in zip(ends, spread_labels([e[0] for e in ends], 0.2 * span)):
        bx.annotate(text, (NR - 1, y), xytext=(NR + 8, yl), textcoords='data', fontsize=8.5, va='center',
                    ha='left', color=colour, arrowprops=dict(arrowstyle='-', color='#BBBBBB', lw=0.6))
    bx.set_xlim(0, NR + 150)
    ylo, yhi = bx.get_ylim()
    bx.set_ylim(ylo - 0.2 * (yhi - ylo), yhi)
    bx.set_xlabel('row', fontsize=9)
    bx.set_ylabel('2θ exact − per-axis (°)', fontsize=9)
    bx.tick_params(labelsize=8)
    bx.set_title('(b) 2θ exact (pixel_angles) − per-axis (column_two_theta), against the row; β0 = %.1f°'
                 % deg(g.beta0), fontsize=10, loc='left')
    for s in ('top', 'right'):
        bx.spines[s].set_visible(False)
    d = np.degrees(tt[:, -1] - tpa[-1])                       # the edge column
    dc = np.degrees(tt[:, 3] - tpa[3])                        # the last usable column
    flo, fhi = ph.footprint_window(g, f.areainfo[1], f.s1_to_sample_mm)
    s5lo, s5hi = ph.s5_window(g, *f.s5)
    caption(fig, 'Case 5 — Raised arm: the (u, v, w) decomposition, and 2θ depends on the row',
            'High-Qz level (scan %d): β0 = %.2f°, Det_Th = %.1f°, D = vertical_distance = %.1f mm (the arm term '
            'g_l3(1/cos β0 − 1) adds %.1f mm). IMG_COO_CONV (Mati Meron) writes the ray from the slit point S to '
            'the pixel P as u·e_h + v·h + w·z, h the arm\'s horizontal direction: here u = %.2f, v = %.2f, '
            'w = %.2f mm for P = (row %d, column %d); then 2θ = Det_Th − atan2(u, v) = %.3f° and '
            'β = atan2(w, √(u² + v²)) = %.3f°. Column %d is the last usable column (usable_columns %d…%d). With the '
            'arm raised, e_v leans back, so the top and bottom of one column lie at different horizontal angles: in '
            'column %d, 2θ goes from %.4f° (row 0) to %.4f° (row %d), while the per-axis column_two_theta gives %.4f° '
            'to the whole column; exact − per-axis spans %.3f° along it (b). The module\'s edge column %d shows the '
            'largest effect, a span of %.3f° (%.3f…%.3f°) against %.4f° (%.4f…%.4f°) for the same column with the '
            'arm level (scan 11, Det_Th 14°); it gets no light, since S5 (%.1f…%.1f) and the footprint window '
            '(%.1f…%.1f) both block it, and is shown in (b) only.\n'
            'u, v, w, h, S, P, rays: ray_geometry; (b): pixel_angles and column_two_theta. The incident beam lies '
            'along x (the reader\'s frame); α = %.2f° is not drawn.'
            % (f.scan, deg(g.beta0), deg(g.dth), ph.vertical_distance(g), ph.vertical_distance(g) - g.d_sample,
               rt.u, rt.v, rt.w, NR - 1, col, deg(rt.two_theta), deg(rt.beta), col, use[0], use[-1], col,
               deg(rb_.two_theta), deg(rt.two_theta), NR - 1, np.degrees(tpa[3]), np.ptp(dc), edge, np.ptp(d),
               d.min(), d.max(), np.ptp(y11), y11.min(), y11.max(), s5lo, s5hi, flo, fhi, deg(g.alpha)),
            provenance(f))
    save(fig, [a], os.path.join(out, 'case5_raised_arm_uvw.png'))


def case6(out):
    """Where a second module would be: the per-axis error, and what it sees."""
    f = frame(12, 14.0)
    g = f.geom
    ftp = ph.footprint_length(g, f.areainfo[1], f.s1_to_sample_mm)
    (llo, lhi), (rlo, rhi) = SECOND['low'], SECOND['high']
    mods = [(llo, lhi, 'left'), (0, NC - 1, 'module'), (rlo, rhi, 'right')]
    ends = (llo, lhi, rlo, rhi)
    fig = new_fig()
    a = Iso(fig, [0.0, 0.53, 0.62, 0.39], '(a) true scale: rays to the modules\' end columns (row r0)')
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
        a.line([r.source, r.slit, r.pixel], C['ray'], lw=0.9)
        a.point(r.source, C['ray'], ('c = %d' % c).replace('-', '−'), dx=0, dy=-14 if c > 0 else 9,
                ha='center', va='top' if c > 0 else 'bottom', size=8.5)
    a.point(X * 0.0, '#8A4A20', 'footprint', dx=-10, dy=-8, ha='right', va='top', size=9, ms=0.1)
    for lo, hi, name in mods:
        a.poly(module_corners(g, lo, hi), FILL['detector'] if name == 'module' else FILL['ghost'], '#333333',
               z=2, lw=0.8, ls='-' if name == 'module' else '--')
        box_pts += module_corners(g, lo, hi)
    a.finish()

    # (b) close-up of the three modules, coloured cell by cell
    box_pts = np.array(box_pts)
    mid = 0.5 * (box_pts.min(axis=0) + box_pts.max(axis=0))
    half = 0.5 * (box_pts.max(axis=0) - box_pts.min(axis=0)).max() * 1.15
    b = Iso(fig, [0.0, BOT + 0.03, 0.55, 0.25], None, box=(mid - half, mid + half))
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
        where = {'left': ((NR - 0.5, lo - 0.5), dict(dx=-6, dy=0, ha='right', va='center')),
                 'module': ((-0.5, 0.5 * (lo + hi)), dict(dx=40, dy=-26, ha='left', va='top', leader=True)),
                 'right': ((-0.5, hi + 0.5), dict(dx=6, dy=0, ha='left', va='center'))}[name]
        b.point(ph.ray_geometry(g, *where[0]).pixel, '#333333',
                {'module': 'this module', 'left': ('c %d…%d' % (lo, hi)).replace('-', '−'),
                 'right': 'c %d…%d' % (lo, hi)}[name], size=9, ms=0.1, **where[1])
    b.finish()
    b.title = lambda: '(b) the three modules (%s), coloured by β per-axis − exact' % mag_note(a, b)
    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    cax = fig.add_axes([0.08, BOT + 0.005, 0.25, 0.01])
    cb = fig.colorbar(sm, cax=cax, orientation='horizontal')
    cb.set_label('β per-axis − exact (°)', fontsize=8.5)
    cb.ax.tick_params(labelsize=8)

    for k, (arr, name, unit) in enumerate(((db, 'β', '°'), (dt, '2θ', '°'))):
        bx = fig.add_axes([0.66, 0.62 - 0.36 * k, 0.31, 0.26])
        for lo, hi, mname in mods:
            bx.axvspan(lo - 0.5, hi + 0.5, color=FILL['detector'] if mname == 'module' else FILL['ghost'], lw=0)
            if k == 0:
                bx.text(0.5 * (lo + hi), 1.01, {'module': 'this module', 'left': 'module 2 here?',
                                                'right': 'or here?'}[mname],
                        transform=bx.get_xaxis_transform(), ha='center', va='bottom', fontsize=8.5)
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
        bx.set_ylabel('%s per-axis − exact (%s)' % (name, unit), fontsize=8.5)
        bx.tick_params(labelsize=8)
        for sp in ('top', 'right'):
            bx.spines[sp].set_visible(False)
        if k == 1:
            bx.set_xlabel('column', fontsize=9)
        bx.set_title('(%s) %s error, top (solid) and bottom (dashed) rows' % ('cd'[k], name), fontsize=9.5,
                     loc='left', pad=18 if k == 0 else 6)
    flo, fhi = ph.footprint_window(g, f.areainfo[1], f.s1_to_sample_mm)
    s5lo, s5hi = ph.s5_window(g, *f.s5)
    src = {c: ph.ray_geometry(g, f.geom.r0, c).source[0] for c in ends}
    other = (allc < 0) | (allc >= NC)
    caption(fig, 'Case 6 — Where the 200K\'s second module would be',
            'The 200K is one detector of two %d × %d modules with a %d-pixel gap; the module not used would sit at '
            'columns %d…%d (lower 2θ) or %d…%d (higher 2θ) in this module\'s numbering, on the same flat detector '
            'plane. High-Qz level (scan %d, β0 = %.1f°, Det_Th = %.1f°). The per-axis angles are off by up to '
            '%.1f° in β and %.2f° in 2θ there (b, c, d), against %.1f° and %.2f° on this module: the exact transform '
            'is a precondition for using it. With the present slits it would get no light: S5 passes columns '
            '%.1f…%.1f only, and through the S4 pinhole those columns look at beam-axis points far outside the '
            '%.1f mm footprint, x = %.0f…%.0f mm (low side) and %.0f…%.0f mm (high side) against ±%.1f mm '
            '(footprint_window: columns %.1f…%.1f). Whether S4 and S5 would be opened for it is not in this '
            'geometry; the rays in (a) are drawn to show where those columns look.\n'
            'Module surfaces: ray_geometry at a 24 × 10 grid of pixel corners, coloured by pixel_angles minus '
            'column_two_theta/row_beta; rays and source labels: ray_geometry (row r0, the modules\' end columns).'
            % (NR, NC, GAP, llo, lhi, rlo, rhi, f.scan, deg(g.beta0), deg(g.dth), np.abs(db[:, other]).max(),
               np.abs(dt[:, other]).max(), np.abs(db[:, ~other]).max(), np.abs(dt[:, ~other]).max(), s5lo, s5hi,
               ftp, src[lhi], src[llo], src[rlo], src[rhi], ftp / 2, flo, fhi),
            provenance(f))
    save(fig, [a, b], os.path.join(out, 'case6_second_module.png'))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--out', default=os.path.join(ROOT, 'docs', 'figures', 'pinhole'))
    p.add_argument('--only', type=int, nargs='*', help='case numbers to draw (default: all)')
    args = p.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    cases = [case1, case2, case3, case4, case5, case6]
    for k, fn in enumerate(cases, 1):
        if not args.only or k in args.only:
            fn(args.out)


if __name__ == '__main__':
    main()
