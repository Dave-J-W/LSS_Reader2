"""Is the beam's height at the sample tied to the Qz resolution near the critical edge?  Calculated only
(no data): a focused beam in phase space (height, angle), what a sample-height scan and the critical edge each
measure of it, and five ways the beam could change from run to run, with the correlation each would show in
16 runs measured as often and as noisily as the owner's.  Also a known-truth check of the estimator that turns
the data into a distance between the sample and the focus.  The real data are in
docs/studies/beam_size_vs_resolution/summary.md (private generator).

    python tests/tools/beam_size_vs_resolution_synthetic.py --out docs/studies/beam_size_vs_resolution

The model (Gaussian beam at a waist, rays straight):
    height at the sample   y = y0 + theta * dz      (y0: spread sigma_f at the focus, theta: spread sigma_theta)
    so  sigma_beam^2 = sigma_f^2 + (sigma_theta * dz)^2,  and the angles are the same everywhere;
    the height scan's knife edge adds (sigma_theta * t)^2, t = 0.04 m (where the surface cuts the beam);
    sigma_Q = (4 pi / lambda) * sqrt(sigma_theta^2 + sigma_surface^2)    (10 keV: 4 pi / lambda = 10.14 1/A).
Units: heights in um, angles in urad, so um / urad = m.
"""
import argparse
import csv
import json
import os
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np                                    # noqa: E402
import matplotlib                                     # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                       # noqa: E402

INK, GREY, LIGHT = '#222222', '#8a8a8a', '#d9d9d9'
BLUE, ORANGE, AQUA, YELLOW, PURPLE = '#1f77b4', '#ff7f0e', '#17becf', '#bcbd22', '#9467bd'
K = 4 * np.pi / (12.39842 / 10.0)        # 4 pi / lambda at 10 keV, 1/A
SIZE0 = 15.9          # um, median beam sigma at the sample from the height scans (sh_beam_size study)
THETA0 = 37.0         # urad, median angular spread from the critical edge (qz_resolution study)
SPREAD = 0.15         # run-to-run spread of the angular spread (log sd), like the edges' run medians
T_KNIFE = 0.04        # m, distance of the surface's cut from the sample centre (sh_beam_size study)
NOISE_SH = 1.0        # um, scatter of one height scan's width about its run (sh_beam_size study)
NOISE_Q = 0.15        # fraction, scatter of one edge's sigma_Q about its run (qz_resolution study)
N_EDGES = (33, 4, 5, 24, 31, 4, 18, 33, 20, 37, 31, 24, 45, 18, 21, 19)   # edges per run, as measured
NSIM = 2000

SCEN = [
    ('A', 'The angles change; the sample sits at the focus', BLUE),
    ('B', 'The angles change; the sample sits 0.2 m from the focus', AQUA),
    ('C', 'The angles change; the sample sits 0.4 m from the focus', PURPLE),
    ('D', 'The focus moves along the beam; the angles stay', ORANGE),
    ('E', 'The surface adds angles; the beam stays', YELLOW),
]


def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#ececec',
                         'axes.edgecolor': INK, 'axes.labelcolor': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'axes.titlesize': 10, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
                         'savefig.dpi': 200})


def focus_size(dz, theta=THETA0, size=SIZE0):
    """The spot at the focus that gives the measured median size at distance dz."""
    s2 = size ** 2 - (theta * dz) ** 2 - (theta * T_KNIFE) ** 2
    return float(np.sqrt(max(s2, 1.0)))


def truth(scen, rng, n):
    """Per-run true (sigma_beam as the height scan sees it, um; sigma_theta of the edge, urad)."""
    if scen in 'ABC':
        dz = {'A': 0.0, 'B': 0.2, 'C': 0.4}[scen]
        th = THETA0 * np.exp(rng.normal(0, SPREAD, n))
        sf = focus_size(dz) + rng.normal(0, 0.8, n)
        size = np.sqrt(sf ** 2 + (th * dz) ** 2 + (th * T_KNIFE) ** 2)
        return size, th
    if scen == 'D':
        th = np.full(n, THETA0)
        dz = rng.uniform(0, 0.4, n)
        sf = focus_size(0.2)
        return np.sqrt(sf ** 2 + (th * dz) ** 2 + (th * T_KNIFE) ** 2), th
    if scen == 'E':
        tb = 30.0
        surf = np.sqrt(np.maximum((THETA0 * np.exp(rng.normal(0, SPREAD, n))) ** 2 - tb ** 2, 0))
        sf = focus_size(0.0, tb)
        size = np.sqrt((sf + rng.normal(0, 0.8, n)) ** 2 + (tb * T_KNIFE) ** 2)
        return size, np.sqrt(tb ** 2 + surf ** 2)
    raise ValueError(scen)


def measure(size, th, rng, n_edges=N_EDGES):
    """Run medians as measured: each run's median of n height scans and n edges."""
    n = np.asarray(n_edges, float)
    return (size + rng.normal(0, NOISE_SH / np.sqrt(n)),
            th * (1 + rng.normal(0, NOISE_Q / np.sqrt(n))))


def pearson(x, y):
    return float(np.corrcoef(x, y)[0, 1])


def fit_dz(size, th):
    """Distance from the focus, from sigma_beam^2 = a + dz^2 sigma_theta^2 (least squares, dz^2 >= 0), in m."""
    b, a = np.polyfit(th ** 2, size ** 2, 1)
    return float(np.sqrt(max(b, 0.0))), float(b), float(a)


def dz_upper(size, th, rng, nboot=2000, q=95):
    """Bootstrap over runs: the q-th percentile of dz."""
    n = len(size)
    v = []
    for _ in range(nboot):
        i = rng.integers(0, n, n)
        if np.ptp(th[i]) <= 0:
            continue
        v.append(fit_dz(size[i], th[i])[0])
    return float(np.percentile(v, q)), np.array(v)


def r_critical(n, alpha=0.05):
    """|r| needed for two-sided p < alpha with n points (t distribution)."""
    from scipy import stats
    t = stats.t.ppf(1 - alpha / 2, n - 2)
    return float(t / np.sqrt(n - 2 + t ** 2))


def simulate(nsim=NSIM, seed=7):
    rng = np.random.default_rng(seed)
    n = len(N_EDGES)
    out = {}
    for key, _, _ in SCEN:
        rs = []
        for _ in range(nsim):
            s, t = measure(*truth(key, rng, n), rng)
            rs.append(pearson(s, t))
        out[key] = np.array(rs)
    return out


def glossary(fig, y, items, width=150):
    lines = []
    for term, text in items:
        lines.append(textwrap.fill('%s: %s' % (term, text), width, subsequent_indent='    '))
    fig.text(0.04, y, '\n'.join(lines), fontsize=8, color=INK, va='top', family='DejaVu Sans', linespacing=1.35)


def phase_panel(ax, dz, rng, title, color):
    n = 1500
    sf = focus_size(0.3) if dz else focus_size(0.3)
    y0 = rng.normal(0, sf, n)
    th = rng.normal(0, THETA0, n)
    y = y0 + th * dz
    ax.scatter(y, th, s=2, color=color, alpha=0.35, lw=0)
    for k in (1, 2):
        a = np.linspace(0, 2 * np.pi, 200)
        ax.plot(k * sf * np.cos(a) + dz * k * THETA0 * np.sin(a), k * THETA0 * np.sin(a), color=INK, lw=0.7)
    ax.set(xlim=(-80, 80), ylim=(-130, 130), xlabel='height at the sample (µm)', ylabel='angle of the ray (µrad)')
    ax.set_title(title, fontsize=9.5)
    sy = np.sqrt(sf ** 2 + (THETA0 * dz) ** 2)
    top = ax.inset_axes([0, 1.02, 1, 0.22], sharex=ax)
    hy, e = np.histogram(y, 60, range=(-80, 80))
    top.fill_between(0.5 * (e[1:] + e[:-1]), hy, step='mid', color=BLUE, alpha=0.6, lw=0)
    top.axis('off')
    top.text(0.0, 0.95, 'the height scan sees this spread: σ_beam %.0f µm' % sy, transform=top.transAxes,
             fontsize=8, color=INK, va='top')
    right = ax.inset_axes([1.02, 0, 0.22, 1], sharey=ax)
    ht, e = np.histogram(th, 60, range=(-130, 130))
    right.fill_betweenx(0.5 * (e[1:] + e[:-1]), ht, step='mid', color=ORANGE, alpha=0.6, lw=0)
    right.axis('off')
    right.text(0.05, 0.99, 'the edge sees\nthis spread:\nσ_θ %.0f µrad\nσ_Q %.2f×10⁻⁴ Å⁻¹' % (THETA0, K * THETA0 * 1e-6 * 1e4),
               transform=right.transAxes, fontsize=7.5, color=INK, va='top')


def explainer(out):
    rng = np.random.default_rng(3)
    fig = plt.figure(figsize=(13.5, 11.0))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.25], hspace=0.75, wspace=0.85,
                          left=0.06, right=0.95, top=0.9, bottom=0.25)
    fig.suptitle('Beam size and Qz resolution are two views of one beam: they move together only if the sample '
                 'sits away from the focus', fontsize=12.5, fontweight='bold', color=INK, x=0.04, ha='left')
    fig.text(0.04, 0.925, 'Calculated, no data. A Gaussian beam focused by the mirror, with the sizes found at '
             '10 keV: σ_beam ≈ %.0f µm at the sample (height scans), σ_θ ≈ %.0f µrad (critical edge).'
             % (SIZE0, THETA0), fontsize=9, color=GREY)

    ax = fig.add_subplot(gs[0, :])
    sf = focus_size(0.3)
    z = np.linspace(-0.9, 0.6, 50)
    y0 = rng.normal(0, sf, 40)
    th = rng.normal(0, THETA0, 40)
    for a, b in zip(y0, th):
        ax.plot(z, a + b * z, color=BLUE, lw=0.6, alpha=0.55)
    env = 2 * np.sqrt(sf ** 2 + (THETA0 * z) ** 2)
    ax.fill_between(z, -env, env, color=BLUE, alpha=0.07, lw=0)
    for zz, lab in ((0.0, 'sample at the focus'), (0.3, 'sample 0.3 m past the focus')):
        ax.axvline(zz, color=INK, lw=1.2, ls='--')
        ax.text(zz + 0.01, 74, lab, fontsize=8.5, color=INK, va='top')
    ax.annotate('', xy=(-0.55, -48), xytext=(-0.85, -48), arrowprops=dict(arrowstyle='->', color=INK))
    ax.text(-0.85, -55, 'from the mirror (focusing)', fontsize=8, color=INK, va='top')
    ax.set(xlim=(-0.9, 0.6), ylim=(-80, 80), xlabel='distance along the beam from the focus (m)',
           ylabel='height (µm)')
    ax.set_title('A. Rays from the mirror cross at the focus: the beam is narrowest there, and its spread of angles '
                 'is the same at every distance')

    phase_panel(fig.add_subplot(gs[1, 0]), 0.0, rng, 'B. The beam of A at its focus:\nheight and angle are independent',
                BLUE)
    phase_panel(fig.add_subplot(gs[1, 1]), 0.3, rng, 'C. The same beam 0.3 m on: steep rays\nhave moved off, the '
                'beam is wider', AQUA)

    ax = fig.add_subplot(gs[1, 2])
    tt = np.linspace(20, 60, 100)
    for dz, c in ((0.0, BLUE), (0.1, AQUA), (0.2, YELLOW), (0.3, ORANGE), (0.4, PURPLE)):
        sf = focus_size(dz)
        ax.plot(tt, np.sqrt(sf ** 2 + (tt * dz) ** 2 + (tt * T_KNIFE) ** 2), color=c, lw=1.6,
                label='%.1f m from the focus (spot %.0f µm)' % (dz, sf))
    ax.axvspan(30, 55, color=LIGHT, alpha=0.5, lw=0)
    ax.text(31, 25.5, 'run-to-run range\nof σ_θ found', fontsize=7.5, color=INK, va='top')
    ax.set(xlabel='angular spread σ_θ (µrad)', ylabel='beam size σ_beam the height scan sees (µm)', ylim=(5, 27))
    sec = ax.secondary_xaxis('top', functions=(lambda x: x * K * 1e-2, lambda q: q / (K * 1e-2)))
    sec.set_xlabel('σ_Q (10⁻⁴ Å⁻¹, 10 keV)', fontsize=8)
    ax.legend(fontsize=7, loc='lower left', frameon=False)
    ax.set_title('D. Every curve passes %.0f µm at %.0f µrad;\nonly away from the focus does\nsize follow angle'
                 % (SIZE0, THETA0), fontsize=9.5)

    glossary(fig, 0.155, [
        ('Beam size σ_beam', 'the rms height of the beam where it meets the surface. The rising edge of every routine '
         'sample-height scan is a knife edge through the beam, and its erf width is σ_beam (docs/studies/sh_beam_size/).'),
        ('Angular spread σ_θ', 'the rms spread of the rays\' angles of incidence, set by the mirror\'s focusing. It '
         'blurs the critical edge: σ_Q = (4π/λ) σ_θ, the resolution width found by the edge fits '
         '(docs/studies/qz_resolution/, docs/studies/qoff_resolution_real/).'),
        ('Focus and distance from the focus Δz', 'where the rays cross (the beam\'s waist), and how far the sample '
         'sits from it along the beam. σ_beam² = σ_spot² + (σ_θ Δz)²; the angles do not change with Δz.'),
        ('Knife-edge blur', 'the surface cuts the beam about 40 mm from the sample centre, so even a sample at the '
         'focus sees σ_θ × 0.04 m ≈ 1.5 µm more: a small built-in tie between the two.'),
        ('Seen by one only', 'the size of the focal spot and the focus\'s position change σ_beam but not σ_Q; a '
         'wavy or tilted surface, or a wrong absorption in the fit, changes σ_Q but not σ_beam.'),
    ])
    path = os.path.join(out, 'B0_one_beam_two_views.png')
    fig.savefig(path)
    plt.close(fig)
    return path


def scenarios(out, rs):
    rng = np.random.default_rng(11)
    n = len(N_EDGES)
    rc = r_critical(n)
    fig = plt.figure(figsize=(13.5, 12.5))
    gs = fig.add_gridspec(3, 3, hspace=0.62, wspace=0.33, left=0.06, right=0.97, top=0.86, bottom=0.06)
    med = {k: float(np.median(v)) for k, v in rs.items()}
    fig.suptitle('Five ways the beam could change between runs: only a sample away from the focus ties beam '
                 'size to σ_Q,\nand 16 runs can see that tie only from about 0.2 m from the focus', fontsize=12, fontweight='bold',
                 color=INK, x=0.04, ha='left')
    fig.text(0.04, 0.905, 'Calculated, no data. Each panel is one draw of 16 runs, with as many height scans and '
             'edges per run as measured and their measured scatter (height scan %.1f µm, edge %.0f %%);\nthe '
             'grey band is |r| < %.2f, where 16 runs cannot tell a tie from chance (p > 0.05).'
             % (NOISE_SH, 100 * NOISE_Q, rc), fontsize=9, color=GREY)
    pos = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]
    for (key, desc, col), (i, j) in zip(SCEN, pos):
        ax = fig.add_subplot(gs[i, j])
        s, t = truth(key, rng, n)
        ms, mt = measure(s, t, rng)
        ax.plot(t * K * 1e-2, s, 'o', mfc='none', color=GREY, ms=4, label='true')
        ax.plot(mt * K * 1e-2, ms, 'o', color=col, ms=5, label='as measured')
        ax.set(xlabel='σ_Q of the run (10⁻⁴ Å⁻¹)', ylabel='beam size σ_beam (µm)', xlim=(2.4, 6.0), ylim=(12, 21))
        ax.set_title('%s. %s' % (key, textwrap.fill(desc, 38)), fontsize=9.5)
        ax.text(0.03, 0.96, 'this draw: r = %+.2f\n2000 draws: median r = %+.2f' % (pearson(ms, mt), med[key]),
                transform=ax.transAxes, fontsize=8, color=INK, va='top')
        if key == 'A':
            ax.legend(fontsize=7.5, loc='lower right', frameon=False)

    ax = fig.add_subplot(gs[1, 2])
    keys = [k for k, _, _ in SCEN]
    parts = ax.violinplot([rs[k] for k in keys], positions=range(len(keys)), orientation='horizontal', showmedians=True,
                          showextrema=False)
    for b, (_, _, col) in zip(parts['bodies'], SCEN):
        b.set_facecolor(col)
        b.set_alpha(0.6)
    parts['cmedians'].set_color(INK)
    ax.axvspan(-rc, rc, color=LIGHT, alpha=0.6, lw=0)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels(keys)
    ax.invert_yaxis()
    ax.set(xlim=(-1, 1), xlabel='correlation r between run medians (Pearson)')
    ax.set_title('F. What r 16 runs would give, per case\n(2000 draws each)', fontsize=9.5)

    ax = fig.add_subplot(gs[2, :2])
    true_dz = [0.0, 0.1, 0.2, 0.3, 0.4]
    rec = []
    for dz in true_dz:
        v, up = [], []
        for _ in range(300):
            th = THETA0 * np.exp(rng.normal(0, SPREAD, n))
            sf = focus_size(dz) + rng.normal(0, 0.8, n)
            s = np.sqrt(sf ** 2 + (th * dz) ** 2 + (th * T_KNIFE) ** 2)
            ms, mt = measure(s, th, rng)
            v.append(fit_dz(ms, mt)[0])
        v = np.array(v)
        rec.append(dict(true_dz_m=dz, median_m=float(np.median(v)), p5_m=float(np.percentile(v, 5)),
                        p95_m=float(np.percentile(v, 95)), share_zero=float(np.mean(v == 0))))
    x = np.array(true_dz)
    ax.plot([0, 0.45], [0, 0.45], color=GREY, lw=1, ls=':', label='perfect recovery')
    ax.errorbar(x, [r['median_m'] for r in rec], yerr=[[r['median_m'] - r['p5_m'] for r in rec],
                [r['p95_m'] - r['median_m'] for r in rec]], fmt='o', color=INK, capsize=4,
                label='recovered from 16 runs: median, 5–95 %')
    ax.axhline(T_KNIFE, color=GREY, lw=0.8)
    ax.text(0.49, T_KNIFE + 0.008, 'floor: the knife edge alone acts like 0.04 m', fontsize=7.5, color=INK, ha='right')
    for r in rec:
        ax.text(r['true_dz_m'] + 0.008, r['p95_m'], '%.0f %% of draws\nat 0' % (100 * r['share_zero']),
                fontsize=7.5, color=INK, va='bottom')
    ax.set(xlabel='true distance between the sample and the focus (m)', ylabel='recovered distance (m)',
           xlim=(-0.03, 0.5), ylim=(-0.02, 0.7))
    ax.legend(fontsize=8, loc='upper left', frameon=False)
    ax.set_title('G. Known truth: the distance from the focus fitted from 16 runs (σ_beam² = a + Δz² σ_θ²)\n'
                 'is found from about 0.2 m on; nearer the focus it reads as "small", not as a number', fontsize=9.5)

    ax = fig.add_subplot(gs[2, 2])
    ax.axis('off')
    ax.text(0, 1, textwrap.fill(
        'How to read this. The beam\'s size and its angular spread are tied only by geometry: away from the '
        'focus, steeper rays land further off, so a run with more angles has a wider beam (B, C). At the focus '
        '(A), when only the focus moves (D) or when the extra angles come from the surface (E), the two are '
        'independent and r scatters about 0. The measured scatter of the run medians limits what 16 runs '
        'can show: r beyond %.2f, which needs the sample about 0.2 m or more from the focus.' % rc, 52),
        fontsize=8.5, color=INK, va='top', transform=ax.transAxes)
    path = os.path.join(out, 'B1_synthetic_cases.png')
    fig.savefig(path)
    plt.close(fig)
    return path, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/beam_size_vs_resolution')
    ap.add_argument('--nsim', type=int, default=NSIM, help='draws of 16 runs per case')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    style()
    p0 = explainer(a.out)
    rs = simulate(a.nsim)
    p1, rec = scenarios(a.out, rs)
    rc = r_critical(len(N_EDGES))
    with open(os.path.join(a.out, 'synthetic_cases.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['case', 'what changes between runs', 'r_median', 'r_p5', 'r_p95', 'share_r_beyond_critical'])
        for key, desc, _ in SCEN:
            v = rs[key]
            w.writerow([key, desc, '%.3f' % np.median(v), '%.3f' % np.percentile(v, 5), '%.3f' % np.percentile(v, 95),
                        '%.3f' % np.mean(np.abs(v) > rc)])
    with open(os.path.join(a.out, 'synthetic_distance_recovery.json'), 'w', encoding='utf-8') as fh:
        json.dump(dict(r_critical_16_runs=rc, recovery=rec, model=dict(size0_um=SIZE0, theta0_urad=THETA0,
                  spread_log=SPREAD, knife_m=T_KNIFE, noise_sh_um=NOISE_SH, noise_q_frac=NOISE_Q,
                  edges_per_run=list(N_EDGES))), fh, indent=1)
    for p in (p0, p1):
        print('wrote', p)


if __name__ == '__main__':
    main()
