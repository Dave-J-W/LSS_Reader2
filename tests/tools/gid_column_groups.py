"""Column groups in the pinhole GID patch: each Qz level's map and the level
join, made from groups of detector columns.

Asked for in docs/physics_notes.md (2026-11-19, "Beam response built":
"TODO: maps from column groups per level; the β-overlap cells of the
join"; then "Outer-column diagnosis"): on the owner's private pairs the
level join factor changed by about a tenth when the outer columns were
added, because the light per column (the illumination along the beam)
differs between the levels' scans. This tool makes those maps and cells for
any GID scans; by default for the public NX school scans 11 (low Qz level,
arm level) and 12 (high level, arm raised to β0 = 6.5°, aborted after 4
frames).

    python tests/tools/gid_column_groups.py                  # NX 11 + 12, 3 groups -> docs/figures/gid_column_groups/
    python tests/tools/gid_column_groups.py --groups 2 --response beam --out DIR
    python tests/tools/gid_column_groups.py --columns common --out DIR
    python tests/tools/gid_column_groups.py --spec FILE --scans "386,387" --out sample_data/private/figures/cg

**Column groups.** ``--columns`` sets the range of detector columns that is
split into ``--groups`` contiguous groups of (nearly) equal width: 'all'
(default) every column some frame uses (the union of the frames' usable
columns, S5 ∩ footprint, as ``lss_core.pinhole.frame_columns`` gives
them), so that one group is exactly the reader's patch; 'common' the
columns every Qz level has (per level the union over its frames, then the
intersection over the levels); or 'LO:HI'. A group is fixed detector
columns: within it each frame keeps its own usable columns.

**How a patch is restricted to a group** (lss_core has no column-window
setting). The S5 opening is the patch's column window: in lss_core it
enters only through ``pinhole.frame_columns`` (``usable_columns`` = the S5
window ∩ the footprint window). For each frame the tool narrows S5L and S5R
in a copy of the frame's SPEC header values (``GIDFrame.params``), so that
S5's column window, as ``pinhole.s5_window`` computes it, becomes
[LO − ½, HI + ½] ∩ the real window; it checks, frame by frame, that
``frame_columns`` then gives exactly the frame's usable columns within the
group, and calls ``lss_core.gid.pinhole_patch`` unchanged (the call
``Experiment.gid`` makes): weights, response, binning, scan and level joins
are the core's. A group's 2θ and β grids are therefore its own
(``shared_edges`` and ``level_map`` derive them from the columns used) and
differ from the other groups' by a fraction of a bin, so groups are
compared over ranges, never cell by cell.

**What the tool computes besides the core's results.** The cells of the β
overlap (2θ bin × β bin that both levels have) are recomputed from the level
infos the core returns (``all_counts``, ``all_weights``, ``keep``, ``beta``,
``edges``) with ``join_levels``' own rules (one β grid, nearest bin, equal
weight per cell); the tool stops unless their inverse-variance mean equals
the core's factor to 1e-9. From those cells: the ratio per cell, per β bin
and per 2θ bin; the *pooled* ratio Σ⟨I_lower⟩ / Σ⟨I_upper⟩ over the β bins
(the same cells and the same per-β-bin means, summed instead of weighted;
not the reader's estimator: the inverse-variance mean of ratios whose
errors scale with the ratio is biased low when a β bin holds few counts,
and the pooled ratio shows by how much); and the all-columns cells' pooled
ratio on the 2θ range of a group's overlap (to tell a column effect from a
2θ effect). Scales between maps are means of the cell intensities ΣN/ΣW
over a range: the group's map over the all-columns map, same 2θ and β
ranges.

Figures (``<label>_S<scans>_<what>.png``):

- ``maps``: one row per Qz level and one for the joined map; one column for
  all columns and one per group; the patched maps as the window shows them
  (``lss_core.gid.products``; Qxy–Qz, or 2θ–β with ``--axes Angles``), all
  on one logarithmic colour scale (ΣN/ΣW: counts per monitor count with the
  area, polarisation and response weights). Each panel gives its columns,
  frames and counts; level panels their scale against the all-columns map
  over the β overlap and the group's 2θ range; joined panels the factor and
  how the intensity above the overlap, relative to below it, compares with
  the all-columns map's on the same 2θ range.
- ``join``: (a) the column response R(c) of each level from the all-columns
  patch (the core's estimate of the light per column), and each group's own
  response scaled to the all-columns one's mean over the group; (b) the
  level factor of each group ± its error, its pooled ratio, and the pooled
  ratio of the all-columns cells on the group's 2θ range, against the
  all-columns factor; (c) for all columns and each group, the cells of the
  β overlap against β: ratio lower ÷ upper per cell and per β bin, with the
  factors; (d) the same cells against 2θ (per 2θ bin, mean over the
  overlap's β bins).

Also ``<label>_S<scans>_factors.csv`` (one row per set of columns) and
``<label>_S<scans>_summary.json`` (every number on the figures, and the
core's own factor next to the recomputed one). The factor is the core's:
lower ÷ upper, the number the upper level's intensities are multiplied by
(``pinhole.join_levels``).

**Measured or assumed.** Measured: everything on the figures, from the
frames through lss_core. Assumed: that a split by fixed detector columns is
a split along the beam (each column sees its own part of the footprint;
the ``x`` given per group is ``pinhole.ray_geometry``'s source point for its
end columns at the direct-beam row of level 1's middle frame). On NX the
high level's 4 frames span Det_Th 14.0–14.3°, so each group sees its own
narrow 2θ strip there and the overlap with the low level is that strip:
column group and 2θ cannot be separated on these data (the figures say so).

Runs headless (matplotlib's Figure, no pyplot) from anywhere (it changes to the repository root); no
dates or revisions are drawn, so a rerun on unchanged code gives the same
pixels. Private data (a --spec other than the NX file): --out must be under
sample_data/private/ (git-ignored) or outside the repository.
"""
import argparse
import csv
import dataclasses
import json
import math
import os
import sys
import textwrap

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import matplotlib                                    # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, LogNorm   # noqa: E402
from matplotlib.figure import Figure                 # noqa: E402  (no pyplot: no backend, no global state)
from matplotlib.gridspec import GridSpec             # noqa: E402
from matplotlib.lines import Line2D                  # noqa: E402

from lss_core import gid as gm                       # noqa: E402
from lss_core import pinhole as ph                   # noqa: E402
from lss_core.experiment import Experiment           # noqa: E402

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
OUT = os.path.join('docs', 'figures', 'gid_column_groups')
RESPONSES = ('fit', 'beam', 'none', 'physical', 'physical+fit')

# reference palette (dataviz skill): categorical slots in fixed order (the first
# three validate all-pairs; aqua is below 3:1, so every series is also labelled),
# ink for "all columns", the blue ramp for the maps
SLOTS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
MARKERS = ['s', '^', 'D', 'v', 'P', 'X', '*', 'h']
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#898781'
GRID, AXIS, SURFACE, NODATA = '#e1e0d9', '#c3c2b7', '#fcfcfb', '#efeeea'
ALL_C = '#3d3c38'
RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
CMAP = LinearSegmentedColormap.from_list('blue_ramp', RAMP).with_extremes(under='#eef4fc', bad=NODATA)

STYLE = {
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'axes.edgecolor': AXIS, 'axes.labelcolor': INK2, 'axes.titlecolor': INK, 'axes.titlesize': 9.5,
    'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'axes.labelsize': 9,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.labelcolor': INK2, 'ytick.labelcolor': INK2,
    'xtick.labelsize': 8, 'ytick.labelsize': 8, 'axes.grid': True, 'grid.color': GRID,
    'grid.linewidth': 0.6, 'axes.axisbelow': True, 'font.size': 8.5, 'legend.frameon': False,
    'legend.fontsize': 8, 'axes.spines.top': False, 'axes.spines.right': False,
    'lines.linewidth': 1.6, 'text.color': INK}

QXY, QZ, INVA = r'$Q_{xy}$', r'$Q_z$', r'$\AA^{-1}$'


# ---------------------------------------------------------------- column groups

def parse_scans(text):
    return [int(s) for s in str(text).replace(',', ' ').split()]


def level_keys(frames, gp):
    """Qz level of every frame, 0 = lowest, as lss_core.gid.pinhole_frames groups them."""
    fmt = '.%df' % gp.qz_decimals
    qz = sorted({float(format(f.qz, fmt)) for f in frames})
    return [qz.index(float(format(f.qz, fmt))) for f in frames]


def usable(frames, gp):
    """(PinholeFrame, usable columns) of every frame, in the order of ``frames``."""
    out = []
    for f in frames:
        pf = gm.pinhole_frames([f], gp)[0][0]
        out.append((pf, ph.frame_columns(pf, pf.counts.shape[1])))
    return out


def column_range(cols, levels, how):
    """(lo, hi) of the columns to split: 'all', 'common' or 'LO:HI'."""
    if how == 'all':
        return int(min(c.min() for c in cols if len(c))), int(max(c.max() for c in cols if len(c)))
    if how == 'common':
        lo, hi = -math.inf, math.inf
        for k in sorted(set(levels)):
            cs = [c for c, l in zip(cols, levels) if l == k and len(c)]
            lo, hi = max(lo, min(c.min() for c in cs)), min(hi, max(c.max() for c in cs))
        if lo > hi:
            raise SystemExit('the Qz levels have no usable column in common')
        return int(lo), int(hi)
    try:
        lo, hi = (int(v) for v in how.split(':'))
    except ValueError:
        raise SystemExit("--columns: 'all', 'common' or LO:HI, not %r" % how)
    return lo, hi


def split(lo, hi, n):
    """``n`` contiguous groups (a, b) of (nearly) equal width covering lo..hi."""
    if n < 1 or n > hi - lo + 1:
        raise SystemExit('--groups must be between 1 and %d (columns %d-%d)' % (hi - lo + 1, lo, hi))
    b = np.round(np.linspace(lo, hi + 1, n + 1)).astype(int)
    return [(int(b[k]), int(b[k + 1] - 1)) for k in range(n)]


def restrict(frames, gp, lo, hi, use):
    """Copies of ``frames`` whose S5 openings (S5L, S5R in a copy of the SPEC
    header values) make S5's column window [lo − ½, hi + ½] ∩ the real one.
    ``pinhole.s5_window`` is linear in the openings, so the columns per mm on
    each side are read from it at 1 mm. Checks that ``frame_columns`` of
    every copy is the frame's usable columns within [lo, hi]; returns the
    copies and those columns."""
    out, cols = [], []
    for f, (pf, c) in zip(frames, use):
        g = pf.geom
        lo1, hi1 = ph.s5_window(g, 1.0, 1.0)
        p = dict(f.params)
        p['S5L'] = min(float(p['S5L']), (g.c0 - (lo - 0.5)) / (g.c0 - lo1))
        p['S5R'] = min(float(p['S5R']), (hi + 0.5 - g.c0) / (hi1 - g.c0))
        f2 = dataclasses.replace(f, params=p)
        pf2 = gm.pinhole_frames([f2], gp)[0][0]
        got = ph.frame_columns(pf2, pf2.counts.shape[1])
        want = c[(c >= lo) & (c <= hi)]
        if not np.array_equal(got, want):
            raise RuntimeError('restricting scan %d to columns %d-%d gave columns %s, not %s'
                               % (f.scan, lo, hi, got[[0, -1]] if len(got) else '[]',
                                  want[[0, -1]] if len(want) else '[]'))
        out.append(f2)
        cols.append(want)
    return out, cols


def beam_x(pf, cols):
    """Where on the beam axis (mm, + downstream) columns ``cols`` of frame
    ``pf`` look through S4 (``pinhole.ray_geometry``'s source point at the
    direct-beam row)."""
    out = []
    for c in cols:
        try:
            out.append(float(ph.ray_geometry(pf.geom, pf.geom.r0, float(c)).source[0]))
        except ValueError:
            out.append(math.nan)
    return out


# ---------------------------------------------------------------- the cells of the join

def join_cells(level_info, labels, apply=True):
    """The cells of each level join, recomputed from the core's level infos
    with ``pinhole.join_levels``' rules (one β grid, nearest bin; levels in
    order of their lowest β, each against everything joined below it). One
    dict per join with the cells' summed counts and weights of both sides."""
    edges = level_info[0]['edges']
    nb = len(edges) - 1
    bstep = max(float(np.max(np.abs(np.diff(lv['beta'])))) for lv in level_info)
    blo = min(float(lv['beta'].min()) for lv in level_info)
    bhi = max(float(lv['beta'].max()) for lv in level_info)
    bedges = blo - bstep / 2 + bstep * np.arange(int(math.ceil((bhi - blo) / bstep)) + 2)
    nbeta = len(bedges) - 1
    reb = []
    for lv in level_info:
        j = np.clip(np.digitize(lv['beta'], bedges) - 1, 0, nbeta - 1)
        n, w = np.zeros((nb, nbeta)), np.zeros((nb, nbeta))
        kept = lv['keep']
        for r in range(len(j)):
            n[kept, j[r]] += lv['all_counts'][kept, r]
            w[kept, j[r]] += lv['all_weights'][kept, r]
        reb.append((n, w, kept))
    order = sorted(range(len(level_info)), key=lambda k: float(level_info[k]['beta'].min()))
    nc, wc = reb[order[0]][0].copy(), reb[order[0]][1].copy()
    have = reb[order[0]][2].copy()
    out = []
    for k in order[1:]:
        n, w, kept = reb[k]
        cells = (have & kept)[:, None] & (wc > 0) & (w > 0)
        J = dict(label=labels[k], below=[labels[i] for i in order[:order.index(k)]], cells=cells,
                 na=nc.copy(), wa=wc.copy(), nb=n.copy(), wb=w.copy(),
                 tt=0.5 * (edges[:-1] + edges[1:]), beta=0.5 * (bedges[:-1] + bedges[1:]), bstep=bstep)
        J.update(overlap_factor(J))
        out.append(J)
        if apply and math.isfinite(J['factor']):
            w = w / J['factor']
        nc, wc, have = nc + n, wc + w, have | kept
    return out


def overlap_factor(J, tmask=None):
    """The level factor from the cells of join ``J`` (only the 2θ bins in
    ``tmask``, if given), as ``join_levels`` fits it: per β bin the mean
    intensities of the two sides over the same cells, their ratio, and the
    inverse-variance mean of the ratios. Also the pooled ratio (sum of the
    per-β-bin means of one side over the other's), and the ratio per cell and
    per 2θ bin."""
    cells = J['cells'] if tmask is None else J['cells'] & np.asarray(tmask)[:, None]
    m = cells.sum(axis=0)
    with np.errstate(invalid='ignore', divide='ignore'):
        sa, sb = np.where(cells, J['wa'], 1.0), np.where(cells, J['wb'], 1.0)
        ia, ib = np.where(cells, J['na'] / sa, 0.0), np.where(cells, J['nb'] / sb, 0.0)
        qa, qb = np.where(cells, J['na'] / sa ** 2, 0.0), np.where(cells, J['nb'] / sb ** 2, 0.0)
        pa, pb = ia.sum(axis=0) / np.maximum(m, 1), ib.sum(axis=0) / np.maximum(m, 1)
        va, vb = qa.sum(axis=0) / np.maximum(m, 1) ** 2, qb.sum(axis=0) / np.maximum(m, 1) ** 2
    ok = (m > 0) & (pa > 0) & (pb > 0)
    if not ok.any():
        return dict(factor=math.nan, error=math.nan, chi2=math.nan, points=0, ncells=0, pooled=math.nan,
                    pooled_error=math.nan)
    ratio = pa[ok] / pb[ok]
    err = ratio * np.sqrt(va[ok] / pa[ok] ** 2 + vb[ok] / pb[ok] ** 2)
    wt = 1 / err ** 2
    fac = float(np.sum(wt * ratio) / np.sum(wt))
    pooled = float(np.sum(pa[ok]) / np.sum(pb[ok]))
    perr = pooled * math.sqrt(float(np.sum(va[ok])) / float(np.sum(pa[ok])) ** 2
                              + float(np.sum(vb[ok])) / float(np.sum(pb[ok])) ** 2)
    used = cells & ok[None, :]
    ti, bi = np.nonzero(used)
    with np.errstate(invalid='ignore', divide='ignore'):
        cr = ia[ti, bi] / ib[ti, bi]
        mt = used.sum(axis=1)
        ta = np.where(used, ia, 0.0).sum(axis=1) / np.maximum(mt, 1)
        tb = np.where(used, ib, 0.0).sum(axis=1) / np.maximum(mt, 1)
        tva = np.where(used, qa, 0.0).sum(axis=1) / np.maximum(mt, 1) ** 2
        tvb = np.where(used, qb, 0.0).sum(axis=1) / np.maximum(mt, 1) ** 2
        tok = (mt > 0) & (ta > 0) & (tb > 0)
        tr = ta[tok] / tb[tok]
        terr = tr * np.sqrt(tva[tok] / ta[tok] ** 2 + tvb[tok] / tb[tok] ** 2)
    na_b = np.where(used, J['na'], 0.0).sum(axis=0)[ok]
    nb_b = np.where(used, J['nb'], 0.0).sum(axis=0)[ok]
    return dict(factor=fac, error=float(np.sum(wt) ** -0.5),
                chi2=float(np.sum(wt * (ratio - fac) ** 2) / max(int(ok.sum()) - 1, 1)),
                points=int(ok.sum()), ncells=int(used.sum()), pooled=pooled, pooled_error=perr,
                counts_per_beta_bin=(float(np.median(na_b)), float(np.median(nb_b))),
                beta_bins=J['beta'][ok], beta_ratio=ratio, beta_err=err,
                tt_bins=J['tt'][tok], tt_ratio=tr, tt_err=terr,
                cell_tt=J['tt'][ti], cell_beta=J['beta'][bi], cell_ratio=cr,
                tt_range=(float(J['tt'][ti].min()), float(J['tt'][ti].max())),
                beta_range=(float(J['beta'][ok].min()), float(J['beta'][ok].max())))


# ---------------------------------------------------------------- one patch

def level_map(li):
    """(2θ centres, β, I, σ) of one level as the core made it (ΣN/ΣW; I and
    σ indexed [2θ, β])."""
    c = 0.5 * (li['edges'][:-1] + li['edges'][1:])[li['keep']]
    with np.errstate(invalid='ignore', divide='ignore'):
        return c, li['beta'], li['sum_counts'] / li['sum_weights'], np.sqrt(li['sum_counts']) / li['sum_weights']


def patch_arrays(patch, scale=1.0):
    """(2θ, β, I, σ) of a patch (the list of [2θ, β, I, σ] columns
    ``pinhole_patch`` returns), I and σ indexed [2θ, β] and divided by
    ``scale``."""
    tt = np.array([p[0, 0] for p in patch])
    return tt, patch[0][:, 1].copy(), np.array([p[:, 2] for p in patch]) / scale, \
        np.array([p[:, 3] for p in patch]) / scale


def products(arrays, axes, alpha, wavelength):
    """The window's map of (2θ, β, I, σ): ``lss_core.gid.products`` on the
    meshes ``gid.map_arrays`` would make."""
    tt, beta, I, S = arrays
    X, Y = np.meshgrid(tt, beta)
    with np.errstate(invalid='ignore', divide='ignore'):
        return gm.products(X, Y, I.T, S.T, axes, alpha, wavelength)


def region_mean(tt, beta, I, trange, brange, tstep, bstep):
    """Mean of the cell intensities whose centres lie in the 2θ and β ranges
    (half a bin of margin on each side); I indexed [2θ, β]."""
    ts = (tt >= trange[0] - tstep / 2) & (tt <= trange[1] + tstep / 2)
    bs = (beta >= brange[0] - bstep / 2) & (beta <= brange[1] + bstep / 2)
    v = I[np.ix_(ts, bs)]
    v = v[np.isfinite(v)]
    return float(np.mean(v)) if v.size else math.nan


def run(frames, gp):
    """``lss_core.gid.pinhole_patch`` on ``frames`` and what the figures need."""
    log = []
    patch, levels, level_info, jinfo = gm.pinhole_patch(frames, gp, log=log)
    mean_m = float(np.mean([li['mean_monitor'] for li in level_info]))
    labels = [li['level'] for li in level_info]
    joins = join_cells(level_info, labels, gp.apply_joins) if len(level_info) > 1 else []
    for J in joins:
        core, core_err = jinfo['factors'][J['label']]
        if not abs(J['factor'] - core) <= 1e-9 * abs(core):
            raise RuntimeError('the recomputed join (%.12g) differs from lss_core.pinhole.join_levels (%.12g)'
                               % (J['factor'], core))
        J.update(recomputed_factor=J['factor'], factor=float(core), error=float(core_err))   # show the core's own
    return dict(levels=levels, level_info=level_info, join=jinfo, log=log, joins=joins, labels=labels,
                maps=[level_map(li) for li in level_info], joined=patch_arrays(patch, mean_m))


# ---------------------------------------------------------------- everything

def compute(spec, scans, ngroups=3, columns='all', response='fit', footprint='exact', axes='Q'):
    """Frames, groups, one patch per set of columns (all, then each group),
    the comparisons and the maps."""
    gp = gm.GIDParams(response=response, footprint=footprint)
    exp = Experiment(spec)
    frames, _ = exp.gid_frames(scans)
    lev = level_keys(frames, gp)
    nlev = max(lev) + 1
    use = usable(frames, gp)
    cols = [c for _, c in use]
    lo, hi = column_range(cols, lev, columns)
    groups = split(lo, hi, ngroups)
    alpha, wl = float(frames[0].true_alpha), float(frames[0].wavelength)
    of = [[i for i, l in enumerate(lev) if l == k] for k in range(nlev)]
    mid = [use[ix[len(ix) // 2]][0] for ix in of]

    def span(cs, k):
        c = [cs[i] for i in of[k] if len(cs[i])]
        return (int(min(x.min() for x in c)), int(max(x.max() for x in c))) if c else (-1, -1)

    sets = [dict(name='all columns', cols=(int(min(c.min() for c in cols if len(c))),
                                           int(max(c.max() for c in cols if len(c)))),
                 level_cols=[span(cols, k) for k in range(nlev)], status='ok', **run(frames, gp))]
    for g, (a, b) in enumerate(groups):
        fr, gc = restrict(frames, gp, a, b, use)
        s = dict(name='group %d' % (g + 1), cols=(a, b), level_cols=[span(gc, k) for k in range(nlev)])
        empty = [k + 1 for k in range(nlev) if s['level_cols'][k][0] < 0]
        if empty:
            s['status'] = 'no usable column at level %s' % ', '.join(map(str, empty))
        else:
            try:                                       # frames that see none of the group's columns are left out
                s.update(run([fr[i] for i in range(len(fr)) if len(gc[i])], gp), status='ok')
            except (gm.GIDError, ValueError) as e:
                s['status'] = 'patch failed: %s' % e
        sets.append(s)
    for s in sets:
        s['x_mm'] = [beam_x(mid[k], s['level_cols'][k]) if s['level_cols'][k][0] >= 0 else [math.nan, math.nan]
                     for k in range(nlev)]
    compare(sets)
    for s in sets:
        if s['status'] == 'ok':
            s['q_levels'] = [products(m, axes, alpha, wl) for m in s['maps']]
            s['q_joined'] = products(s['joined'], axes, alpha, wl) if nlev > 1 else None
    return dict(spec=spec, scans=scans, params=gp, axes=axes, levels=lev, nlev=nlev, range=(lo, hi),
                columns=columns, groups=groups, sets=sets, alpha=alpha, wavelength=wl,
                scans_per_level=[sorted({frames[i].scan for i in ix}) for ix in of],
                frames_per_level=[len(ix) for ix in of],
                dth_per_level=[(min(math.degrees(frames[i].dth) for i in ix),
                                max(math.degrees(frames[i].dth) for i in ix)) for ix in of],
                beta0_per_level=[math.degrees(m.geom.beta0) for m in mid])


def compare(sets):
    """Each group against all columns, over the same ranges: the all-columns
    cells' factor and pooled ratio on the group's 2θ range; each level map's
    scale over the β overlap and the group's 2θ range; the joined map's mean
    intensity one overlap width above the overlap over that one width below,
    the group's over the all-columns map's (same 2θ range)."""
    ref = sets[0]
    for s in sets:
        s['compare'] = []
    if not ref['joins']:
        return
    for s in sets[1:]:
        if s['status'] != 'ok':
            continue
        for jn, J in enumerate(s['joins']):
            R = ref['joins'][jn]
            tr = J['tt_range']
            step = float(R['tt'][1] - R['tt'][0])
            same = overlap_factor(R, (R['tt'] >= tr[0] - step / 2) & (R['tt'] <= tr[1] + step / 2))
            br = R['beta_range']
            scale = [region_mean(*s['maps'][k][:3], tr, br, step, R['bstep'])
                     / region_mean(*ref['maps'][k][:3], tr, br, step, R['bstep'])
                     for k in (s['labels'].index(J['below'][-1]), s['labels'].index(J['label']))]
            width = br[1] - br[0]
            below, above = (br[0] - width, br[0] - R['bstep']), (br[1] + R['bstep'], br[1] + width)
            ul = [region_mean(*x['joined'][:3], tr, above, step, R['bstep'])
                  / region_mean(*x['joined'][:3], tr, below, step, R['bstep']) for x in (s, ref)]
            s['compare'].append(dict(join=J['label'], two_theta_range=tr, beta_range=br,
                                     all_columns_on_range=same['factor'], all_columns_on_range_error=same['error'],
                                     all_columns_on_range_pooled=same['pooled'],
                                     all_columns_on_range_pooled_error=same['pooled_error'],
                                     scale_lower=scale[0], scale_upper=scale[1],
                                     joined_above_over_below=ul[0], all_columns_above_over_below=ul[1],
                                     joined_relative=ul[0] / ul[1], beta_windows=(below, above)))


# ---------------------------------------------------------------- figures

def colour(i):
    return ALL_C if i == 0 else SLOTS[(i - 1) % len(SLOTS)]


def marker(i):
    return 'o' if i == 0 else MARKERS[(i - 1) % len(MARKERS)]


def set_title(C, i):
    s = C['sets'][i]
    return 'all columns %d–%d' % s['cols'] if i == 0 else 'group %d: columns %d–%d' % (i, *s['cols'])


def level_name(C, k):
    return 'level %d (scan %s, β0 %.2f°)' % (k + 1, ', '.join(map(str, C['scans_per_level'][k])),
                                             C['beta0_per_level'][k])


def level_scale(s, k):
    """Scale of level ``k``'s map of set ``s`` against the all-columns map,
    from the first join it takes part in (upper side, else lower side)."""
    name = s['labels'][k] if s.get('labels') else None
    for c, J in zip(s.get('compare', []), s.get('joins', [])):
        if J['label'] == name:
            return c['scale_upper']
        if J['below'] and J['below'][-1] == name:
            return c['scale_lower']
    return None


def caveat(C):
    """The data's limits, from the data: a level with few frames sees each
    2θ through few columns."""
    out = []
    for k in range(C['nlev']):
        n = C['frames_per_level'][k]
        if n < 10 and C['nlev'] > 1:
            out.append('Level %d (scan %s) has only %d frames (Det_Th %.1f–%.1f°): there each column group sees its '
                       'own narrow 2θ strip, so column group and 2θ cannot be separated, and the overlap with the '
                       'other level is that strip.'
                       % (k + 1, ', '.join(map(str, C['scans_per_level'][k])), n, *C['dth_per_level'][k]))
    return ' '.join(out)


def wrap(text, width_in, size):
    """Lines of ``text`` that fit ``width_in`` inches at ``size`` points."""
    return '\n'.join(textwrap.wrap(text, max(int(width_in * 72 / (0.52 * size)), 20)))


def box(ax, lines, size=7.2):
    ax.text(0.02, 0.97, '\n'.join(lines), transform=ax.transAxes, ha='left', va='top', fontsize=size, color=INK,
            zorder=7, bbox=dict(boxstyle='round,pad=0.3', fc=SURFACE, ec=AXIS, lw=0.6, alpha=0.9))


def axis_labels(C):
    if C['axes'] == 'Q':
        return '%s (%s)' % (QXY, INVA), '%s (%s)' % (QZ, INVA)
    return '2θ (°)', 'β (°)'


def fig_maps(C, path):
    with matplotlib.rc_context(STYLE):
        _fig_maps(C, path)


def fig_join(C, path):
    with matplotlib.rc_context(STYLE):
        _fig_join(C, path)


def _fig_maps(C, path):
    sets = C['sets']
    ok = [s for s in sets if s['status'] == 'ok']
    rows = C['nlev'] + (1 if C['nlev'] > 1 else 0)
    ncol = len(sets)
    W, H = 3.3 * ncol + 1.3, 2.9 * rows + 1.6
    top, bottom = 1.25 / H, 0.62 / H
    vals = []
    for s in ok:
        for q in s['q_levels'] + ([s['q_joined']] if s['q_joined'] is not None else []):
            d = q['data']
            vals.append(d[np.isfinite(d) & (d > 0)])
    pos = np.concatenate(vals)
    norm = LogNorm(vmin=float(np.percentile(pos, 2)), vmax=float(np.percentile(pos, 99.7)))
    xs = [q['x'] for s in ok for q in s['q_levels']]
    xlim = (min(float(np.nanmin(x)) for x in xs), max(float(np.nanmax(x)) for x in xs))
    pad = 0.02 * (xlim[1] - xlim[0])
    xlim = (xlim[0] - pad, xlim[1] + pad)
    xl, yl = axis_labels(C)
    fig = Figure(figsize=(W, H))
    gs = GridSpec(rows, ncol, figure=fig, left=0.075, right=0.905, top=1 - top, bottom=bottom, wspace=0.07,
                  hspace=0.3)
    im = None
    for r in range(rows):
        joined = r == C['nlev']
        qs = [s['q_joined'] if joined else s['q_levels'][r] for s in ok]
        ylim = (min(float(np.nanmin(q['y'])) for q in qs), max(float(np.nanmax(q['y'])) for q in qs))
        for i, s in enumerate(sets):
            ax = fig.add_subplot(gs[r, i])
            ax.set_xlim(*xlim)
            ax.set_ylim(*ylim)
            ax.grid(False)
            ax.set_facecolor(NODATA)
            if r == 0:
                ax.set_title(set_title(C, i), color=INK, fontsize=9)
                ax.plot([0.0, 0.18], [1.11, 1.11], transform=ax.transAxes, color=colour(i), lw=3, clip_on=False)
            if i == 0:
                ax.set_ylabel('%s\n%s' % ('joined map' if joined else level_name(C, r), yl), fontsize=8.5)
            else:
                ax.tick_params(labelleft=False)
            if r == rows - 1:
                ax.set_xlabel(xl)
            if s['status'] != 'ok':
                ax.text(0.5, 0.5, wrap(s['status'], 2.6, 8), transform=ax.transAxes, ha='center', va='center',
                        fontsize=8, color=INK2)
                continue
            q = s['q_joined'] if joined else s['q_levels'][r]
            d = np.where(np.isfinite(q['data']) & (q['data'] <= 0), norm.vmin * 1e-3, q['data'])
            im = ax.pcolormesh(q['x'], q['y'], d, cmap=CMAP, norm=norm, shading='nearest', rasterized=True)
            txt = []
            if joined:
                for c, J in zip(s['compare'] or [None] * len(s['joins']), s['joins']):
                    txt.append('factor %.3f ± %.3f' % (J['factor'], J['error']))
                    if c is not None:
                        txt.append('above ÷ below the overlap:\n× %.3f of all columns' % c['joined_relative'])
            else:
                li = s['level_info'][r]
                txt.append('columns %d–%d, %d frames' % (*s['level_cols'][r], len(li['columns'])))
                txt.append('%.3g counts' % li['counts_used'])
                v = level_scale(s, r) if i else None
                if v is not None:
                    txt.append('× %.3f of all columns\n(β overlap, same 2θ)' % v)
            box(ax, txt)
    cax = fig.add_axes([0.92, bottom, 0.012, 1 - top - bottom])
    cb = fig.colorbar(im, cax=cax, extend='both')
    cb.set_label('ΣN/ΣW (counts per monitor count, weighted; log)', color=INK2)
    cb.outline.set_edgecolor(AXIS)
    fig.text(0.075, 1 - 0.22 / H, '%s scans %s: GID maps from groups of detector columns (response %r)'
             % (C['label'], ' + '.join(map(str, C['scans'])), C['params'].response),
             ha='left', va='top', fontsize=11.5, fontweight='bold')
    sub = ('One colour scale; grey: no data. Each group is a patch of only its columns (lss_core.gid.pinhole_patch '
           'with the S5 window narrowed to the group). ' + caveat(C))
    fig.text(0.075, 1 - 0.5 / H, wrap(sub, 0.83 * W, 7.8), ha='left', va='top', fontsize=7.8, color=INK2)
    fig.savefig(path, dpi=110)


def _fig_join(C, path):
    sets = C['sets']
    ref = sets[0]
    J0 = ref['joins'][0]
    ok = [i for i, s in enumerate(sets) if s['status'] == 'ok']
    ncol = len(sets)
    W, H = max(3.4 * ncol, 12.5), 13.2
    fig = Figure(figsize=(W, H))
    gtop = GridSpec(1, 2, figure=fig, left=0.06, right=0.985, top=1 - 1.05 / H, bottom=1 - 4.0 / H,
                    wspace=0.16, width_ratios=[1.2, 1])
    gcell = GridSpec(2, ncol, figure=fig, left=0.06, right=0.985, top=1 - 5.75 / H, bottom=1.25 / H,
                     hspace=0.36, wspace=0.08)
    # (a) the light per column
    ax = fig.add_subplot(gtop[0, 0])
    styles = ['-', (0, (4, 2)), ':', '-.']
    top = 0.0
    for k, li in enumerate(ref['level_info']):
        a, b = ref['level_cols'][k]
        r = li['response'][a:b + 1]
        top = max(top, float(np.max(r)))
        ax.plot(np.arange(a, b + 1), r, color=INK if k == 0 else INK2, ls=styles[k % 4], lw=1.6, zorder=4,
                label='%s, all columns' % level_name(C, k))
    for i in range(1, ncol):
        s = sets[i]
        a, b = s['cols']
        ax.axvspan(a - 0.5, b + 0.5, color=colour(i), alpha=0.10, lw=0)
        if s['status'] == 'ok':
            for k, li in enumerate(s['level_info']):
                c0, c1 = s['level_cols'][k]
                r = li['response'][c0:c1 + 1] * float(np.mean(ref['level_info'][k]['response'][c0:c1 + 1]))
                top = max(top, float(np.max(r)))
                ax.plot(np.arange(c0, c1 + 1), r, color=colour(i), ls=styles[k % 4], lw=1.1, zorder=3)
        x = s['x_mm'][0]
        ax.text(0.5 * (a + b), 0.02, 'group %d\nx %.0f…%.0f mm' % (i, x[0], x[1]), transform=ax.get_xaxis_transform(),
                ha='center', va='bottom', fontsize=7.2, color=INK)
    ax.plot([], [], color=MUTED, lw=1.1, label="each group's own response, scaled to the all-columns mean over "
                                               "its columns (colour: group)")
    ax.set_xlabel('detector column')
    ax.set_ylabel('column response R (mean 1 per level)')
    ax.set_title("(a) Light per column: each level's response R(c) (%r)" % C['params'].response)
    ax.legend(loc='upper right', fontsize=7.2)
    ax.set_ylim(0, top * 1.32)
    # (b) the factors
    ax = fig.add_subplot(gtop[0, 1])
    fa, ea = J0['factor'], J0['error']
    ax.axhspan(fa - ea, fa + ea, color=ALL_C, alpha=0.12, lw=0)
    ax.axhline(fa, color=ALL_C, lw=1.2, ls='--')
    ax.axhline(J0['pooled'], color=ALL_C, lw=0.9, ls=':')
    for i in ok:
        s = sets[i]
        J = s['joins'][0]
        ax.errorbar([i], [J['factor']], [J['error']], fmt=marker(i), color=colour(i), ms=7, lw=1.4, capsize=3,
                    zorder=5)
        ax.errorbar([i + 0.18], [J['pooled']], [J['pooled_error']], fmt=marker(i), mfc=SURFACE, mec=colour(i),
                    color=colour(i), ms=6, lw=1.0, capsize=2, zorder=5)
        ax.annotate('%.3f ± %.3f' % (J['factor'], J['error']), (i, J['factor']), xytext=(-9, 0),
                    textcoords='offset points', fontsize=7.4, va='center', ha='right', color=INK, zorder=6,
                    bbox=dict(boxstyle='round,pad=0.15', fc=SURFACE, ec='none', alpha=0.85))
        if i:
            c = s['compare'][0]
            ax.errorbar([i + 0.36], [c['all_columns_on_range_pooled']], [c['all_columns_on_range_pooled_error']],
                        fmt='D', mfc=SURFACE, mec=ALL_C, color=ALL_C, ms=5, lw=0.8, capsize=2, zorder=4)
    handles = [Line2D([], [], color=ALL_C, marker='o', ls='none', ms=6,
                      label="the reader's level factor ± error (join_levels)"),
               Line2D([], [], color=ALL_C, marker='o', mfc=SURFACE, ls='none', ms=6,
                      label='pooled: Σ⟨I_lower⟩ / Σ⟨I_upper⟩ over the β bins (same cells)'),
               Line2D([], [], color=ALL_C, marker='D', mfc=SURFACE, ls='none', ms=5,
                      label="all columns' cells on the group's 2θ range, pooled"),
               Line2D([], [], color=ALL_C, ls='--', lw=1.2, label='all columns: %.3f ± %.3f' % (fa, ea)),
               Line2D([], [], color=ALL_C, ls=':', lw=0.9, label='all columns, pooled: %.3f' % J0['pooled'])]
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(-0.02, -0.15), ncol=2, fontsize=7.2,
              columnspacing=1.2, handletextpad=0.4)
    ax.set_xticks(range(ncol))
    ax.set_xticklabels(['all\n%d–%d' % sets[0]['cols']] + ['group %d\n%d–%d' % (i, *sets[i]['cols'])
                                                          for i in range(1, ncol)])
    ax.set_xlim(-0.75, ncol - 0.45)
    vals = [v for i in ok for v in (sets[i]['joins'][0]['factor'], sets[i]['joins'][0]['pooled'])]
    vals += [sets[i]['compare'][0]['all_columns_on_range_pooled'] for i in ok if i]
    lo_, hi_ = min(vals), max(vals)
    ax.set_ylim(lo_ - 0.12 * (hi_ - lo_) - 0.05, hi_ + 0.12 * (hi_ - lo_) + 0.05)
    ax.set_ylabel('level factor, lower ÷ upper')
    ax.set_title('(b) Level factor of each column group (level 1 + level 2)' if C['nlev'] == 2
                 else '(b) Level factor of each column group (first join)')
    # (c), (d): the cells
    per = np.concatenate([np.r_[sets[i]['joins'][0]['beta_ratio'], sets[i]['joins'][0]['tt_ratio']] for i in ok])
    per = per[np.isfinite(per)]
    lo, hi = np.percentile(per, [2, 98])
    lo, hi = min(lo, min(vals)), max(hi, max(vals))
    ylim = (max(lo - 0.25 * (hi - lo), 0.0), hi + 0.35 * (hi - lo))
    for row, key in ((0, 'beta'), (1, 'tt')):
        for i, s in enumerate(sets):
            ax = fig.add_subplot(gcell[row, i])
            ax.set_ylim(*ylim)
            if i:
                ax.tick_params(labelleft=False)
            else:
                ax.set_ylabel('lower ÷ upper')
            ax.set_xlabel('β (°)' if key == 'beta' else '2θ (°)')
            ax.set_title(('(c) ' if row == 0 else '(d) ') * (i == 0) + set_title(C, i)
                         + (', against β' if row == 0 else ', against 2θ'), color=INK, fontsize=8.8)
            if s['status'] != 'ok':
                ax.text(0.5, 0.5, wrap(s['status'], 2.6, 8), transform=ax.transAxes, ha='center', va='center',
                        fontsize=8, color=INK2)
                continue
            J = s['joins'][0]
            x = J['cell_beta'] if key == 'beta' else J['cell_tt']
            ax.plot(x, J['cell_ratio'], 'o', ms=1.4, color=colour(i), alpha=0.22, mew=0, rasterized=True, zorder=2)
            xb = J['beta_bins'] if key == 'beta' else J['tt_bins']
            yb = J['beta_ratio'] if key == 'beta' else J['tt_ratio']
            eb = J['beta_err'] if key == 'beta' else J['tt_err']
            ax.fill_between(xb, yb - eb, yb + eb, color=colour(i), alpha=0.25, lw=0, step='mid', zorder=3)
            ax.plot(xb, yb, color=colour(i), lw=1.0, drawstyle='steps-mid', zorder=4)
            ax.axhline(J['factor'], color=INK, lw=1.5, zorder=5)
            ax.axhline(J['pooled'], color=INK, lw=1.0, ls=':', zorder=5)
            if i:
                ax.axhline(fa, color=ALL_C, lw=0.9, ls='--', zorder=5)
            cr = J['cell_ratio']
            nout = int(np.sum((cr < ylim[0]) | (cr > ylim[1]) | ~np.isfinite(cr)))
            if key == 'beta':
                lines = ['factor %.3f ± %.3f, χ²/dof %.2f, pooled %.3f' % (J['factor'], J['error'], J['chi2'],
                                                                          J['pooled']),
                         '%d β bins × ~%d cells; median counts per β bin %d | %d'
                         % (J['points'], round(J['ncells'] / max(J['points'], 1)), *J['counts_per_beta_bin']),
                         '%d of %d cells off the scale' % (nout, J['ncells'])]
            else:
                lines = ['%d 2θ bins, %.2f–%.2f°' % (len(xb), *J['tt_range'])]
            box(ax, lines, size=6.8)
    fig.text(0.06, 1 - 0.2 / H, '%s scans %s: the level join from groups of detector columns (response %r)'
             % (C['label'], ' + '.join(map(str, C['scans'])), C['params'].response),
             ha='left', va='top', fontsize=11.5, fontweight='bold')
    sub = ('Factor = lower ÷ upper, the number the upper level is multiplied by (lss_core.pinhole.join_levels); the '
           "cells are recomputed from the core's level infos and checked against its factor. x: where a group's end "
           "columns look along the beam (level 1's middle frame, + downstream).")
    fig.text(0.06, 1 - 0.48 / H, wrap(sub, 0.92 * W, 7.8), ha='left', va='top', fontsize=7.8, color=INK2)
    cap = ('(c) Dots: ratio per cell (a few counts each); step line ± 1σ: per β bin, the ratio of the mean '
           "intensities over the cells both levels have; solid: the reader's factor, their inverse-variance mean; "
           'dotted: the pooled ratio; dashed: the all-columns factor. (d) The same cells per 2θ bin, mean over the '
           'β bins. The inverse-variance mean of ratios whose errors scale with the ratio is biased low when a '
           'β bin holds few counts: compare filled and open markers in (b). ' + caveat(C))
    fig.text(0.06, 0.012, wrap(cap, 0.92 * W, 7.6), ha='left', va='bottom', fontsize=7.6, color=INK2)
    fig.savefig(path, dpi=110)


# ---------------------------------------------------------------- output

def rows_of(C):
    """One CSV row per set of columns."""
    out = []
    for i, s in enumerate(C['sets']):
        r = dict(set=s['name'], col_lo=s['cols'][0], col_hi=s['cols'][1], status=s['status'])
        for k in range(C['nlev']):
            r['level%d_cols' % (k + 1)] = '%d-%d' % tuple(s['level_cols'][k])
            r['level%d_x_mm' % (k + 1)] = '%.1f..%.1f' % tuple(s['x_mm'][k])
            if s['status'] == 'ok':
                r['level%d_counts' % (k + 1)] = s['level_info'][k]['counts_used']
        if s['status'] == 'ok' and s['joins']:
            J = s['joins'][0]
            r.update(factor=J['factor'], error=J['error'], chi2=J['chi2'], pooled=J['pooled'],
                     pooled_error=J['pooled_error'], beta_bins=J['points'], cells=J['ncells'],
                     lower_counts_per_beta_bin=J['counts_per_beta_bin'][0],
                     upper_counts_per_beta_bin=J['counts_per_beta_bin'][1],
                     tt_from=J['tt_range'][0], tt_to=J['tt_range'][1], beta_from=J['beta_range'][0],
                     beta_to=J['beta_range'][1])
            if s['compare']:
                c = s['compare'][0]
                r.update(all_columns_on_range=c['all_columns_on_range'],
                         all_columns_on_range_pooled=c['all_columns_on_range_pooled'],
                         scale_lower=c['scale_lower'], scale_upper=c['scale_upper'],
                         joined_relative=c['joined_relative'])
        out.append(r)
    return out


def _clean(v):
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (float, np.floating)):
        v = float(v)
        return v if math.isfinite(v) else None
    return v


def summary(C):
    gp = C['params']
    out = dict(spec=C['spec'] if C['public'] else os.path.basename(C['spec']), scans=C['scans'], label=C['label'],
               response=gp.response, footprint=gp.footprint, axes=C['axes'], columns=C['columns'],
               split_range=C['range'], groups=C['groups'],
               levels=[dict(level=k + 1, scans=C['scans_per_level'][k], frames=C['frames_per_level'][k],
                            det_th_deg=C['dth_per_level'][k], beta0_deg=C['beta0_per_level'][k])
                       for k in range(C['nlev'])],
               caveat=caveat(C), sets=[])
    for s in C['sets']:
        d = dict(name=s['name'], columns=s['cols'], status=s['status'], level_columns=s['level_cols'],
                 beam_x_mm=s['x_mm'])
        if s['status'] == 'ok':
            d['counts'] = [li['counts_used'] for li in s['level_info']]
            d['joins'] = [dict(label=J['label'], factor=J['factor'], error=J['error'],
                               core_factor=s['join']['factors'][J['label']][0],
                               core_error=s['join']['factors'][J['label']][1],
                               recomputed_factor=J['recomputed_factor'], chi2=J['chi2'], pooled=J['pooled'],
                               pooled_error=J['pooled_error'], beta_bins=J['points'], cells=J['ncells'],
                               median_counts_per_beta_bin=J['counts_per_beta_bin'],
                               two_theta_range=J['tt_range'], beta_range=J['beta_range'])
                          for J in s['joins']]
            d['against_all_columns'] = s['compare']
        out['sets'].append(d)
    return _clean(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', default=NX, help='SPEC file (default: the public NX school file)')
    ap.add_argument('--scans', default='11,12', help='GID scans, comma-separated (default %(default)s)')
    ap.add_argument('--groups', type=int, default=3, help='number of column groups (default %(default)s)')
    ap.add_argument('--columns', default='all',
                    help="columns to split: 'all' (every usable column), 'common' (those every Qz level has) or "
                         "LO:HI (default %(default)s)")
    ap.add_argument('--response', default='fit', choices=RESPONSES,
                    help='column response of the pinhole patch, GIDParams.response (default %(default)s)')
    ap.add_argument('--footprint', default='exact', choices=ph.FOOTPRINT_WINDOWS,
                    help='footprint window of the usable columns, GIDParams.footprint (default %(default)s)')
    ap.add_argument('--axes', default='Q', choices=('Q', 'Angles'),
                    help="map axes: 'Q' (Qxy-Qz, regridded as the window does) or 'Angles' (2θ-β, the cells "
                         "themselves; faster) (default %(default)s)")
    ap.add_argument('--out', default=OUT, help='output folder (default %(default)s)')
    ap.add_argument('--label', default=None,
                    help='file and title label (default: NX for the NX file, else the SPEC file name)')
    a = ap.parse_args(argv)
    public = os.path.abspath(a.spec) == os.path.abspath(NX)
    out = os.path.abspath(a.out)

    def inside(d):
        return out == d or out.startswith(d + os.sep)
    if not public and inside(ROOT) and not inside(os.path.join(ROOT, 'sample_data', 'private')):
        sys.exit('private data: give an --out under sample_data/private/ or outside the repository')
    scans = parse_scans(a.scans)
    label = a.label or ('NX' if public else os.path.basename(a.spec))
    C = compute(a.spec, scans, a.groups, a.columns, a.response, a.footprint, a.axes)
    C.update(label=label, public=public)
    os.makedirs(out, exist_ok=True)
    stem = os.path.join(out, '%s_S%s' % (label, '_'.join(map(str, scans))))
    written = [stem + '_maps.png']
    fig_maps(C, written[-1])
    if C['nlev'] > 1 and C['sets'][0]['joins']:
        written.append(stem + '_join.png')
        fig_join(C, written[-1])
    rows = rows_of(C)
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    written.append(stem + '_factors.csv')
    with open(written[-1], 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})
    S = summary(C)
    written.append(stem + '_summary.json')
    with open(written[-1], 'w') as f:
        json.dump(S, f, indent=1, ensure_ascii=False)
        f.write('\n')
    for r in rows:
        if 'factor' in r:
            print('%-12s columns %3d-%3d  factor %.4f ± %.4f (pooled %.4f)  χ²/dof %.2f  %d β bins, %d cells, '
                  '2θ %.2f-%.2f°%s' % (r['set'], r['col_lo'], r['col_hi'], r['factor'], r['error'], r['pooled'],
                                       r['chi2'], r['beta_bins'], r['cells'], r['tt_from'], r['tt_to'],
                                       ('  all columns there, pooled: %.4f; maps × %.3f | × %.3f; joined × %.3f'
                                        % (r['all_columns_on_range_pooled'], r['scale_lower'], r['scale_upper'],
                                           r['joined_relative'])) if 'joined_relative' in r else ''))
        else:
            print('%-12s columns %3d-%3d  %s' % (r['set'], r['col_lo'], r['col_hi'], r['status']))
    for p in written:
        print('wrote', os.path.relpath(p, ROOT) if inside(ROOT) else p)
    S['files'] = written
    return S


if __name__ == '__main__':
    main()
