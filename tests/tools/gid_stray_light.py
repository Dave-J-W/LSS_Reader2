"""Stray light in pinhole GID frames: β profiles of column bands, per Qz level.

Diagnostic for P40 (docs/PHYSICS_ISSUES.md). For each Qz level of the GID
scans, the frames (counts per monitor count, mean over the level's frames)
are summed over bands of columns: inside the usable window (S5 ∩ footprint),
beyond the footprint but inside S5, and beyond S5 on either side; each
band's profile is drawn against β (β0 + atan((row − r0)·p/D), the
direct-beam column's β; good to a few tenths of a degree away from it). Light
beyond the footprint or beyond S5 cannot have come from the footprint
through the pinhole. Also draws three frames per level on a log scale with
the usable window marked, and the mean column profile.

    python tests/tools/gid_stray_light.py                       # NX school 11 + 12 -> docs/figures/gid_stray_light/
    python tests/tools/gid_stray_light.py --spec PATH --scans 386 387 388 389 --out DIR

Run from the repository root. Figures of private data go outside the
repository or under sample_data/private/ (git-ignored), never in docs/.
"""
import argparse
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())
import matplotlib                                      # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                        # noqa: E402
from matplotlib.colors import LogNorm                  # noqa: E402

from lss_core import gid as gm, pinhole as ph          # noqa: E402
from lss_core.experiment import Experiment             # noqa: E402

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
OUT = os.path.join('docs', 'figures', 'gid_stray_light')


def bands_for(frame, ncols):
    """Column bands (lo, hi, name) from the first frame's windows."""
    g = frame.geom
    cols = ph.frame_columns(frame, ncols)
    s5lo, s5hi = ph.s5_window(g, *frame.s5)
    lo, hi = int(cols.min()), int(cols.max())
    edges = np.linspace(lo, hi + 1, 4).astype(int)
    out = [(edges[k], edges[k + 1] - 1, 'usable %d-%d' % (edges[k], edges[k + 1] - 1)) for k in range(3)]
    a, b = hi + 8, int(math.floor(s5hi)) - 3
    if b > a:
        out.append((a, b, '%d-%d beyond footprint, inside S5' % (a, b)))
    a, b = int(math.ceil(s5hi)) + 3, ncols - 5
    if b > a:
        out.append((a, b, '%d-%d beyond S5 (high)' % (a, b)))
    a, b = 0, int(math.floor(s5lo)) - 3
    if b > a:
        out.append((a, b, '%d-%d beyond S5 (low)' % (a, b)))
    return cols, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', default=NX)
    ap.add_argument('--scans', type=int, nargs='+', default=[11, 12])
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    e = Experiment(a.spec)
    frames, _ = e.gid_frames(a.scans)
    levels = gm.pinhole_frames(frames, gm.GIDParams())
    ncols = levels[0][0].counts.shape[1]
    cols, bands = bands_for(levels[0][0], ncols)
    tag = '_'.join(map(str, a.scans))

    fig, axs = plt.subplots(1, len(bands), figsize=(3.0 * len(bands), 3.8), sharey=True)
    for k, level in enumerate(levels):
        g = level[0].geom
        rows = np.arange(level[0].counts.shape[0])
        beta = np.degrees(g.beta0 + np.arctan((rows - g.r0) * ph.PIXEL_MM / ph.vertical_distance(g)))
        mean = np.mean([f.counts / f.monitor for f in level], axis=0)
        for ax, (lo, hi, name) in zip(axs, bands):
            p = np.convolve(mean[:, lo:hi + 1].mean(axis=1), np.ones(9) / 9, 'same')
            ax.semilogy(beta[4:-4], p[4:-4], label='level %d, arm at β0 %.1f°' % (k + 1, math.degrees(g.beta0)))
            ax.set_title('columns ' + name, fontsize=8)
            ax.set_xlabel('β (°), direct-beam column')
    axs[0].set_ylabel('counts per pixel per monitor count')
    axs[0].legend(fontsize=7)
    fig.suptitle('Scans %s: light per column band against β, mean of each level\'s frames' % ', '.join(map(str, a.scans)),
                 fontsize=10)
    fig.tight_layout()
    fn = os.path.join(a.out, 'bands_%s.png' % tag)
    fig.savefig(fn, dpi=110)
    print('wrote', fn)

    fig, axs = plt.subplots(len(levels), 4, figsize=(15, 3.6 * len(levels)), squeeze=False)
    for k, level in enumerate(levels):
        g = level[0].geom
        s5lo, s5hi = ph.s5_window(g, *level[0].s5)
        for j, i in enumerate([0, len(level) // 2, len(level) - 1]):
            f = level[i]
            ax = axs[k, j]
            im = ax.imshow(np.maximum(f.counts, 0.5), norm=LogNorm(vmin=0.5, vmax=max(f.counts.max(), 10)),
                           aspect='auto', origin='lower', cmap='viridis')
            ax.axvspan(cols.min() - 0.5, cols.max() + 0.5, color='w', alpha=0.08)
            ax.axvline(s5hi, color='r', lw=0.7, ls=':')
            ax.set_title('level %d, scan %d, Det_Th %.2f°' % (k + 1, f.scan, math.degrees(f.geom.dth)), fontsize=8)
            ax.set_xlabel('column')
            ax.set_ylabel('row')
            fig.colorbar(im, ax=ax, fraction=0.04, label='counts')
        ax = axs[k, 3]
        prof = np.mean([f.counts.sum(axis=0) / f.monitor for f in level], axis=0)
        ax.semilogy(prof)
        ax.axvspan(cols.min() - 0.5, cols.max() + 0.5, color='g', alpha=0.12, label='usable (S5 ∩ footprint)')
        ax.axvline(s5hi, color='r', lw=0.7, ls=':', label='S5 high edge')
        ax.set_title('level %d: rows summed, mean per monitor count' % (k + 1), fontsize=8)
        ax.set_xlabel('column')
        ax.legend(fontsize=7)
    fig.tight_layout()
    fn = os.path.join(a.out, 'frames_%s.png' % tag)
    fig.savefig(fn, dpi=90)
    print('wrote', fn)


if __name__ == '__main__':
    main()
