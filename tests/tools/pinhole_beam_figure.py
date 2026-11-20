"""The beam profile the "beam" response measures from GID data (figure).

    python tests/tools/pinhole_beam_figure.py                      # NX scan 11 -> docs/figures/pinhole_beam/
    python tests/tools/pinhole_beam_figure.py --spec PATH --scans 163 --out DIR

Through the S4 pinhole each column of a frame looks at one point x on the
beam axis (``pinhole.ray_geometry``); the response 'beam' (``pinhole.
beam_response``) estimates how much light comes from each x, shared by all
frames of a Qz level. A beam of vertical profile h(z) meeting the surface at
α lights the surface along the beam as h(x·sin α), so the profile's width
along x times sin α is the beam's vertical width (an upper bound: S4's
opening and the beam's horizontal width also smear it). Left: R(x), with
its centre, FWHM and the footprint S1v / sin α the reader assumes; the top
axis converts x to height in the beam. Right: the same light seen per
column ('fit', one factor per column) at three Det_Th: the column that
looks at a given x changes with Det_Th, which a per-column factor cannot
follow (physics_notes 2026-11-19). Uses lss_core only.
Run from the repository root; private data go to an --out outside docs/.
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

from lss_core import gid as gm, pinhole as ph          # noqa: E402
from lss_core.experiment import Experiment             # noqa: E402

NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')
OUT = os.path.join('docs', 'figures', 'pinhole_beam')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', default=NX)
    ap.add_argument('--scans', type=int, nargs='+', default=[11])
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    e = Experiment(a.spec)
    frames, _ = e.gid_frames(a.scans)
    level = gm.pinhole_frames(frames, gm.GIDParams())[0]
    f0 = level[0]
    alpha = f0.geom.alpha
    ftp = ph.footprint_length(f0.geom, f0.areainfo[1], f0.s1_to_sample_mm)
    beam = e.gid(a.scans, params=gm.GIDParams(response='beam')).info['levels'][0]['beam']
    fit = e.gid(a.scans, params=gm.GIDParams(response='fit')).info['levels'][0]['response']
    x, r = np.asarray(beam['x_mm']), np.asarray(beam['response'])
    lit = r > 0
    x, r = x[lit], r[lit]
    c, w = beam['centre_mm'], beam['fwhm_mm']
    um = 1e3 * math.sin(alpha)                        # µm of beam height per mm along the beam

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw=dict(width_ratios=[1.25, 1]))
    ax.plot(x, r, 'o-', ms=3, lw=1, color='#1f6fb4', label='R(x): light from each point of the beam axis')
    half = 0.5 * r.max()
    lo, hi = c - w / 2, c + w / 2
    ax.axhline(half, color='#1f6fb4', lw=0.6, ls=':')
    ax.annotate('', xy=(lo, half), xytext=(hi, half), arrowprops=dict(arrowstyle='<->', color='#c0392b', lw=1.4))
    ax.text(c, half * 1.04, 'FWHM %.0f mm along the beam\n× sin α (%.4f°) = %.0f µm of beam height'
            % (w, math.degrees(alpha), w * um), ha='center', va='bottom', color='#c0392b', fontsize=9)
    ax.axvline(c, color='#c0392b', lw=0.8)
    ax.text(c, 0.03 * r.max(), ' centre %+.1f mm\n (downstream of the\n sample centre)' % c, color='#c0392b',
            fontsize=8, va='bottom')
    down = x > c
    floor = float(np.min(r[down])) if down.any() else 0.0      # light that is not the beam (P40a)
    above = r >= floor + 0.5 * (r.max() - floor)
    w2 = float(x[above][-1] - x[above][0]) if above.any() else float('nan')
    ax.axhline(floor, color='#7f7f7f', lw=0.8, ls='--')
    ax.text(x.max(), floor * 0.93, 'floor %.2f: light not from the beam?\n(beyond-footprint light, P40a)' % floor,
            ha='right', va='top', fontsize=8, color='#555555')
    ax.text(c, r.max() * 1.07, 'above that floor: FWHM %.0f mm = %.0f µm' % (w2, w2 * um), ha='center',
            fontsize=9, color='#555555')
    ax.axvspan(-ftp / 2, ftp / 2, color='#999999', alpha=0.15,
               label='footprint the reader assumes: S1v / sin α = %.0f mm (uniform)' % ftp)
    ax.set_xlabel('x along the beam (mm; 0 = sample centre, + downstream)')
    ax.set_ylabel('R(x), mean 1 over the lit points')
    ax.set_ylim(0, r.max() * 1.45)
    ax.legend(loc='upper left', fontsize=8, frameon=False)
    top = ax.secondary_xaxis('top', functions=(lambda v: v * um, lambda v: v / um))
    top.set_xlabel('height in the beam, x · sin α (µm)')
    ax.set_title('Scan%s %s, response "beam"' % ('s' if len(a.scans) > 1 else '', ', '.join(map(str, a.scans))),
                 fontsize=10, pad=30)

    ncols = f0.counts.shape[1]
    picks = [level[0], level[len(level) // 2], level[-1]]
    for f, col in zip(picks, ('#2a9d8f', '#e9a03b', '#8e44ad')):
        cols = ph.frame_columns(f, ncols)
        xs = np.array([ph.ray_geometry(f.geom, f.geom.r0, cc).source[0] for cc in cols])
        bx.plot(cols, np.interp(xs, x, r, left=np.nan, right=np.nan), color=col, lw=1.5,
                label='R(x) seen per column, Det_Th %.1f°' % math.degrees(f.geom.dth))
    rr = np.asarray(fit, float)
    cols = np.arange(len(rr))
    use = rr != 1.0
    bx.plot(cols[use], rr[use], 'k.', ms=4, label='"fit": one factor per column (all frames)')
    bx.set_xlabel('detector column')
    bx.set_ylabel('relative light')
    bx.set_title('The same light per column: it moves with Det_Th', fontsize=10, pad=30)
    bx.legend(fontsize=8, frameon=False, loc='lower center')
    fig.text(0.01, 0.01, 'Made by tests/tools/pinhole_beam_figure.py from lss_core.pinhole (beam_response, '
             'ray_geometry, footprint_length). The width is an upper bound on the beam\'s vertical FWHM: S4\'s '
             'opening and the horizontal beam width also spread the light along x.', fontsize=7, color='#555555')
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fn = os.path.join(a.out, 'beam_response_%s.png' % '_'.join(map(str, a.scans)))
    fig.savefig(fn, dpi=130)
    print('wrote', fn, '| centre %.1f mm, FWHM %.1f mm, %.0f um vertical; above the floor %.2f: %.1f mm, %.0f um'
          % (c, w, w * um, floor, w2, w2 * um))


if __name__ == '__main__':
    main()
