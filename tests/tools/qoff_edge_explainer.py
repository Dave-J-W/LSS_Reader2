"""What the words of the Qoff and resolution studies mean, in one figure:
the plateau, the critical edge Qc, the angle offset Qoff, the resolution
width σ_Q, the absorption β, and why Qoff matters for R/R_F far above the
edge. Bare water at 10 keV from ``lss_core.fresnel`` (no data, nothing
private); sizes are the real ones found on the owner's edges
(docs/studies/qoff_resolution_real/summary.md).

    python tests/tools/qoff_edge_explainer.py --out docs/studies/qoff_resolution_real
"""
import argparse
import os
import textwrap
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np                                    # noqa: E402
import matplotlib                                     # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402
from lss_core import fresnel as F                     # noqa: E402

INK, GREY, LIGHT = '#222222', '#8a8a8a', '#d9d9d9'
BLUE, ORANGE, AQUA, YELLOW = '#1f77b4', '#ff7f0e', '#17becf', '#bcbd22'
E = 10.0
QC = F.QC_WATER
BETA = F.subphase_beta(F.subphase('water'), E)
QOFF = -2.0e-4          # a typical angle offset (the owner's edges: median −1.6 × 10⁻⁴)
SIG = 3.8e-4            # the median resolution width on the owner's edges
STEP, START = 0.001, 0.016
SPREAD = 7.8e-5         # Qoff's typical spread between series of a run


def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#ececec',
                         'axes.edgecolor': INK, 'axes.labelcolor': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'axes.titlesize': 10, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left'})


def measured(q):
    """R at the recorded Qz: the true Qz is the recorded one + Qoff, blurred by σ_Q."""
    return F.fresnel_smeared(q + QOFF, QC, SIG, BETA, E)


def main(out):
    style()
    fig = plt.figure(figsize=(13, 10.2))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 0.62], hspace=0.42, wspace=0.18,
                          left=0.06, right=0.98, top=0.895, bottom=0.03)

    # ---- A: the whole curve
    a = fig.add_subplot(gs[0, 0])
    q = np.geomspace(0.005, 0.5, 3000)
    a.loglog(q, F.fresnel_smeared(q, QC, SIG, BETA, E), color=BLUE, lw=1.8)
    a.axvspan(0.0185, 0.0265, color=LIGHT, alpha=0.7, lw=0)
    a.text(0.0221, 2e-9, 'close-up\nin panel B', fontsize=7.5, color=GREY, ha='center', va='bottom')
    a.axvline(QC, color=INK, lw=0.8, ls=':')
    a.text(0.0058, 0.25, 'the plateau: the water\nreflects (almost) all\nof the beam, R = 1',
           fontsize=8, color=INK, va='top')
    a.annotate('the edge: the critical angle Qc,\n0.0217 Å⁻¹ for water. Below it,\ntotal reflection; above it, R falls',
               (QC * 1.02, 0.3), xytext=(0.034, 0.05), fontsize=8, color=INK,
               arrowprops=dict(arrowstyle='->', color=INK, lw=0.8))
    a.annotate('far above the edge R falls as Qz⁻⁴.\nA layer on the surface adds wiggles,\nseen in R/R_F (panel D)',
               (0.2, F.fresnel(0.2, QC)), xytext=(0.06, 1e-8), fontsize=8, color=INK,
               arrowprops=dict(arrowstyle='->', color=INK, lw=0.8))
    a.set(xlim=(0.005, 0.5), ylim=(1e-9, 5), xlabel='Qz (Å⁻¹), set by the angle of the beam on the surface (log scale)',
          ylabel='reflectivity R', title='A. A reflectivity curve of bare water, end to end')
    a.set_xticks([0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5])
    a.set_xticklabels(['0.005', '0.01', '0.02', '0.05', '0.1', '0.2', '0.5'])

    # ---- B: the close-up: Qoff and σ_Q
    b = fig.add_subplot(gs[0, 1])
    qq = np.linspace(0.0185, 0.0265, 2000)
    b.plot(qq, F.fresnel(qq, QC), color=GREY, lw=1.4, ls='--', label='the ideal edge: sharp, at Qc')
    b.plot(qq, F.fresnel(qq + QOFF, QC), color=ORANGE, lw=1.4,
           label='shifted by the angle offset Qoff')
    b.plot(qq, measured(qq), color=BLUE, lw=2.0,
           label='and blurred by the resolution σ_Q (and β): what is measured')
    pts = np.round(np.arange(START, 0.0305, STEP), 6)
    pts = pts[(pts >= qq[0]) & (pts <= qq[-1])]
    b.plot(pts, measured(pts), 'o', color=BLUE, ms=6, mec='white', mew=0.8, zorder=5,
           label='the scan\'s points, one every 0.001 Å⁻¹')
    e = QC - QOFF
    near = pts[np.argsort(np.abs(pts - e))[:2]]
    b.plot(near, measured(near), 'o', ms=15, mfc='none', mec=INK, mew=1.0, zorder=6)
    b.text(0.02265, 0.80, 'only the two points either side\nof the edge feel the blur, so\nσ_Q rests on them',
           fontsize=8, color=INK)
    b.annotate('', (e, 1.04), xytext=(QC, 1.04), arrowprops=dict(arrowstyle='->', color=ORANGE, lw=1.4))
    b.text(QC - 0.0001, 1.04, 'Qoff', color=INK, ha='right', va='center', fontsize=9)
    b.annotate('', (e - SIG, 0.5), xytext=(e + SIG, 0.5), arrowprops=dict(arrowstyle='<->', color=BLUE, lw=1.2))
    b.text(e - SIG - 0.0001, 0.5, '±σ_Q', color=INK, fontsize=9, ha='right', va='center')
    b.set(xlim=(qq[0], qq[-1]), ylim=(0, 1.1), xlabel='recorded Qz (Å⁻¹)', ylabel='reflectivity R (linear)',
          title='B. Close up of the edge: what Qoff and σ_Q do')
    b.legend(fontsize=7.5, frameon=False, loc='lower left')

    # ---- C: absorption β
    c = fig.add_subplot(gs[1, 0])
    qc_ = np.linspace(0.0205, 0.0235, 2000)
    for k, col, lw in ((0, GREY, 1.2), (1, BLUE, 1.6), (3, AQUA, 1.6)):
        lab = ('no absorption: a sharp corner' if k == 0 else
               'water\'s own absorption β (known)' if k == 1 else
               '3 × water\'s β: the rounder edge the real data prefer')
        c.plot(qc_, F.fresnel_absorbing(qc_, QC, k * BETA, E), color=col, lw=lw, ls='--' if k == 0 else '-', label=lab)
    c.plot(qc_, F.fresnel_smeared(qc_, QC, SIG, BETA, E), color=ORANGE, lw=1.4, ls=':',
           label='for scale: water\'s β with the resolution blur σ_Q')
    c.axvline(QC, color=INK, lw=0.8, ls=':')
    c.set(xlim=(qc_[0], qc_[-1]), ylim=(0.3, 1.04), xlabel='true Qz (Å⁻¹)', ylabel='reflectivity R (linear)',
          title='C. Absorption β also rounds the edge, but only right at Qc')
    c.legend(fontsize=7.5, frameon=False, loc='lower left')

    # ---- D: why Qoff matters
    d = fig.add_subplot(gs[1, 1])
    q4 = np.linspace(QC + 0.002, 0.5, 3000)
    for dl, col, lab in ((SPREAD, BLUE, 'Qoff wrong by %.1f × 10⁻⁵ Å⁻¹ (its spread between series)' % (SPREAD * 1e5)),
                         (1e-4, ORANGE, 'Qoff wrong by 1.0 × 10⁻⁴ (today\'s Propose button vs the new fit)')):
        err = 100 * (F.fresnel(q4 + dl, QC) / F.fresnel(q4, QC) - 1)
        d.loglog(q4, np.abs(err), color=col, lw=1.6, label=lab)
    d.loglog(q4, 400 * SPREAD / q4, color=GREY, lw=1, ls='--', label='rule of thumb: 4 × error / Qz')
    for x in (0.05, 0.2):
        y = 400 * SPREAD / x
        d.plot(x, y, 'o', color=BLUE, ms=4)
        d.text(x * 1.06, y * 1.12, '%.2f %% at Qz %.2g' % (y, x), fontsize=8, color=INK)
    d.set_xticks([0.03, 0.05, 0.1, 0.2, 0.5]); d.set_xticklabels(['0.03', '0.05', '0.1', '0.2', '0.5']); d.minorticks_off()
    d.set(xlim=(0.022, 0.5), ylim=(0.03, 30), xlabel='Qz (Å⁻¹, log scale)', ylabel='error in R/R_F (%)',
          title='D. Why Qoff matters: a wrong offset tilts R/R_F')
    d.legend(fontsize=7.5, frameon=False, loc='upper right')

    # ---- glossary
    g = fig.add_subplot(gs[2, :])
    g.axis('off')
    g.set_title('The words used in the studies', loc='left')
    terms = [
        ('R/R_F', 'the measured reflectivity R divided by R_F, the ideal (Fresnel) curve of a bare, flat surface. '
                  'It shows what the surface layer adds.'),
        ('the edge, Qc', 'the critical angle, where total reflection ends (panel A). Its position is fixed by the '
                         'subphase: 0.0217 Å⁻¹ for water.'),
        ('Qoff', 'the angle offset: how far the recorded Qz scale is shifted from the true one (panel B). Found from '
                 'where the measured edge sits relative to Qc.'),
        ('σ_Q', 'the resolution width: the spread of angles in the beam, which blurs the edge (panel B). FWHM = 2.355 σ_Q.'),
        ('β', 'the subphase\'s absorption; it rounds the corner of the edge a little (panel C).'),
        ('edge scan', 'the first scan of a reflectivity series, the only one that crosses the edge. Series: one '
                      'full reflectivity measurement; run: one beamtime\'s set of series.'),
        ('Propose today', 'the reader\'s Propose button: finds Qoff assuming a perfectly sharp edge (no σ_Q).'),
        ('new fit', 'tools man\'s fit: finds Qoff and σ_Q together from the points around the edge.'),
        ('χ²/dof', 'how far the points sit from the fitted curve, in units of their error bars: about 1 when the '
                   'model describes the data.'),
    ]
    half = (len(terms) + 1) // 2
    for col, chunk in enumerate((terms[:half], terms[half:])):
        y = 0.92
        for t, txt in chunk:
            body = textwrap.fill(txt, 82)
            g.text(0.0 + 0.51 * col, y, t, fontsize=8.5, fontweight='bold', color=INK, va='top', transform=g.transAxes)
            g.text(0.095 + 0.51 * col, y, body, fontsize=8, color=INK, va='top', transform=g.transAxes,
                   linespacing=1.25)
            y -= 0.085 * (body.count('\n') + 1) + 0.05
    fig.suptitle('The pieces of the puzzle: the edge of a reflectivity curve tells you the angle offset Qoff '
                 'and the beam\'s resolution σ_Q', x=0.06, ha='left', fontsize=12.5, fontweight='bold', color=INK)
    fig.text(0.06, 0.932, 'Bare water at 10 keV, calculated (no data). Sizes are those found on the owner\'s edges: '
             'Qoff −2 × 10⁻⁴ Å⁻¹, σ_Q 3.8 × 10⁻⁴ Å⁻¹, points every 0.001 Å⁻¹.', fontsize=8.5, color=GREY)
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, 'Q0_the_pieces.png')
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(p)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/qoff_resolution_real')
    main(ap.parse_args().out)
