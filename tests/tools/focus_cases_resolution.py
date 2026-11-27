"""Where is the beam focused, and how much of the critical edge's width σ_Q does the beam itself explain?
Calculated only (no data); the beam's widths are the pooled medians measured at S1 (the S1 slit scans) and at
the sample (the height scans' images), docs/studies/focus_and_resolution/summary.md.

Two cases, with S1 a distance D before the sample:
  focus at S1:     the slit cuts heights at the waist, not angles; the beam grows from S1 to the sample;
  focus at sample: the slit sits upstream of the waist, where height and angle are tied, so it cuts angles;
                   the beam shrinks from S1 to the sample.
With the focus at S1 the beam's angular spread follows from the two widths: sigma_theta = sqrt(s_sample^2 -
s_S1^2) / D, for the core and the tail separately.  The edge is then blurred by a core + tail resolution;
fitting it with one Gaussian (lss_core.fresnel.fit_edge_resolution, as on the real edges) gives the sigma_Q the
beam alone would produce, and the residual pattern that comes with it.

    python tests/tools/focus_cases_resolution.py --out docs/studies/focus_and_resolution
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
from lss_core import fresnel as F                     # noqa: E402

INK, GREY, LIGHT = '#222222', '#8a8a8a', '#d9d9d9'
BLUE, ORANGE, AQUA, YELLOW, PURPLE = '#1f77b4', '#ff7f0e', '#17becf', '#bcbd22', '#9467bd'
E = 10.0
K = 4 * np.pi / (12.39842 / E)          # 1/A
QC = F.QC_WATER
BETA = F.subphase_beta(F.subphase('water'), E)
D = 0.678               # m, S1 to the sample centre (scan headers: g_l2 - g_l1 = 1238 - 560 mm)
# pooled medians at 10 keV (docs/studies/focus_and_resolution/summary.md); um
S1 = dict(core=11.0, tail=26.9, frac=0.17)        # S1 slit scans, slit gap <= 5 um
SAMPLE = dict(core=13.4, tail=55.8, frac=0.21)    # height-scan images with S1 at 0.04 mm (the edges' slit)
SIGQ_REAL = 3.8e-4      # median sigma_Q on the real edges (qz_resolution, qoff_resolution_real)
STEP, Q0, Q1 = 0.001, 0.016, 0.030


def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#ececec',
                         'axes.edgecolor': INK, 'axes.labelcolor': INK, 'xtick.color': INK, 'ytick.color': INK,
                         'axes.titlesize': 10, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
                         'savefig.dpi': 200})


def theta_at_s1_focus(s1, ss, d=D):
    """Angular spread (urad) of a component whose waist is at S1: sqrt(ss^2 - s1^2)/d; NaN if it shrank."""
    v = ss ** 2 - s1 ** 2
    return float(np.sqrt(v) / d) if v >= 0 else float('nan')


def theta_at_sample_focus(s1, ss, d=D):
    v = s1 ** 2 - ss ** 2
    return float(np.sqrt(v) / d) if v >= 0 else float('nan')


def beam_resolution(s1=S1, ss=SAMPLE, d=D):
    """Core + tail angular resolution of the beam with the focus at S1: (frac, sigma_core, sigma_tail) in urad."""
    return dict(frac=ss['frac'], core=theta_at_s1_focus(s1['core'], ss['core'], d),
                tail=theta_at_s1_focus(s1['tail'], ss['tail'], d))


def reflect(q, qoff, res, extra=0.0, beta=BETA):
    """R_F blurred by the core + tail resolution (urad), each also widened by an extra Gaussian (1/A)."""
    out = 0.0
    for w, th in ((1 - res['frac'], res['core']), (res['frac'], res['tail'])):
        sq = np.hypot(K * th * 1e-6, extra)
        out = out + w * F.fresnel_smeared(q + qoff, QC, sq, beta, E)
    return out


def clip_cases(gaps_mm, theta0=37.0, spot=11.0, n=200000, seed=1):
    """sigma_theta (urad) passing S1 of gap g, and the core's size at the sample (um), for both cases.
    One Gaussian beam: angular spread theta0, waist size spot; straight rays."""
    rng = np.random.default_rng(seed)
    th = rng.normal(0, theta0, n)
    y0 = rng.normal(0, spot, n)
    out = []
    for g in gaps_mm:
        h = g * 1e3 / 2
        # focus at S1: the waist is at S1, so y(S1) = y0
        m1 = np.abs(y0) < h
        ys1 = y0[m1] + th[m1] * D
        # focus at the sample: the waist is at the sample, y(S1) = y0 - theta * D
        m2 = np.abs(y0 - th * D) < h
        out.append(dict(gap_mm=g, theta_s1focus=float(np.std(th[m1])), size_s1focus=float(np.std(ys1)),
                        theta_samplefocus=float(np.std(th[m2])), size_samplefocus=float(np.std(y0[m2]))))
    return out


def rel_error(q):
    """Counting error per point like the real edges' median: 0.1 % on the plateau, rising above the edge to
    0.43 % at 0.030 1/A (docs/studies/focus_and_resolution/summary.md)."""
    return np.where(q <= 0.022, 0.0010, 0.0010 + (q - 0.022) / 0.008 * 0.0033)


def simulate_fits(res, extra=0.0, n=120, seed=3, rel_err=None, beta_fit=BETA, beta_true=BETA):
    """Edges sampled like the real ones (0.016-0.030 in steps of 0.001, random offset), fitted with one
    Gaussian resolution as on the real edges.  Returns sigma_q fits, chi2/dof and the residual pattern."""
    rng = np.random.default_rng(seed)
    q = np.arange(Q0, Q1 + 1e-9, STEP)
    if rel_err is None:
        rel_err = rel_error(q)
    sq, chi, pat = [], [], {}
    for _ in range(n):
        qoff = -2e-4 + rng.uniform(-5e-4, 5e-4)
        r = reflect(q, qoff, res, extra, beta_true)
        rr = r * (1 + rng.normal(0, rel_err, len(q)))
        fit = F.fit_edge_resolution(q, rr, rr * rel_err, beta=beta_fit, bootstrap=0)
        if not fit.ok or not np.isfinite(fit.sigma_q):
            continue
        sq.append(fit.sigma_q)
        chi.append(fit.chi2_dof)
        edge = QC - fit.qoff
        sc = np.sqrt(max(fit.chi2_dof, 1e-12))
        for p, rs in zip(fit.points, fit.residuals):
            pos = np.floor((p - edge) / STEP) + 0.5
            pat.setdefault(float(pos), []).append(rs / sc)
    pos = sorted(pat)
    return dict(sigma_q=np.array(sq), chi2=np.array(chi), pos=np.array(pos),
                pattern=np.array([np.mean(pat[p]) for p in pos]), n_pat=np.array([len(pat[p]) for p in pos]))


def note(fig, y, text, width=175):
    fig.text(0.04, y, textwrap.fill(text, width), fontsize=7.8, color=GREY, va='top')


def rays(ax, waist_z, title, color):
    rng = np.random.default_rng(4)
    z = np.linspace(-1.0, 0.25, 60)
    spot, th = 5.0, 37.0
    zs1 = -D
    for _ in range(45):
        y0, t = rng.normal(0, spot), rng.normal(0, th)
        y = y0 + t * (z - waist_z)
        ys1 = y0 + t * (zs1 - waist_z)
        passed = abs(ys1) < 20
        ax.plot(z, y, color=color if passed else LIGHT, lw=0.7 if passed else 0.5, alpha=0.8, zorder=2 if passed else 1)
    for zz, lab in ((zs1, 'S1 slit'), (0.0, 'sample')):
        ax.axvline(zz, color=INK, lw=1.0, ls='--')
        ax.text(zz + 0.01, 70, lab, fontsize=8.5, color=INK, va='top')
    ax.plot([zs1, zs1], [20, 80], color=INK, lw=4, solid_capstyle='butt')
    ax.plot([zs1, zs1], [-80, -20], color=INK, lw=4, solid_capstyle='butt')
    ax.set(xlim=(-1.0, 0.25), ylim=(-80, 80), xlabel='distance along the beam from the sample (m)',
           ylabel='height (µm)')
    ax.set_title(title, fontsize=9.5)


def figure_cases(out):
    gaps = np.array([0.01, 0.016, 0.02, 0.03, 0.04, 0.06, 0.08, 0.1, 0.15, 0.2])
    cc = clip_cases(gaps)
    fig = plt.figure(figsize=(13.5, 10.5))
    gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.25, left=0.07, right=0.97, top=0.85, bottom=0.12)
    fig.suptitle('Focus at S1 or at the sample? The slit cuts heights in one case and angles in the other, '
                 'and what was measured\nfits a focus at S1', fontsize=12.5, fontweight='bold', color=INK,
                 x=0.04, ha='left')
    fig.text(0.04, 0.895, 'Calculated: straight rays, a Gaussian beam of 37 µrad angular spread. S1 is %.0f mm '
             'before the sample (scan headers). Grey rays are stopped by a 0.04 mm slit.' % (D * 1e3),
             fontsize=9, color=GREY)
    rays(fig.add_subplot(gs[0, 0]), -D, 'A. Focus at S1: the slit trims heights at the waist; every angle '
         'passes,\nand the beam widens on its way to the sample', BLUE)
    rays(fig.add_subplot(gs[0, 1]), 0.0, 'B. Focus at the sample: the slit sits where height and angle are tied,\n'
         'so it trims the steep rays; the beam narrows to the sample', ORANGE)

    ax = fig.add_subplot(gs[1, 0])
    ax.plot(gaps, [K * c['theta_s1focus'] * 1e-2 for c in cc], 'o-', color=BLUE, label='focus at S1 (prediction)')
    ax.plot(gaps, [K * c['theta_samplefocus'] * 1e-2 for c in cc], 's-', color=ORANGE,
            label='focus at the sample (prediction)')
    ax.errorbar([0.04, 0.2], [3.38, 3.41], yerr=[0.08, 0.75], fmt='D', color=INK, ms=7, capsize=4,
                label='measured, one run with both slits (qz_resolution)')
    ax.set(xscale='log', xlabel='S1 vertical gap (mm)', ylabel='σ_Q of the edge (10⁻⁴ Å⁻¹)', ylim=(0, 4.6))
    ax.legend(fontsize=7.5, loc='lower right', frameon=False)
    ax.set_title('C. If the focus were at the sample, opening S1 from 0.04 to 0.2 mm\nwould widen the edge '
                 '%.1f×; the measured edge did not change' % (cc[-1]['theta_samplefocus'] / cc[4]['theta_samplefocus']),
                 fontsize=9.5)

    ax = fig.add_subplot(gs[1, 1])
    lab = ['core', 'tail']
    x = np.arange(2)
    ax.bar(x - 0.18, [S1['core'], S1['tail']], 0.34, color=LIGHT, edgecolor=INK, label='at S1 (S1 slit scans)')
    ax.bar(x + 0.18, [SAMPLE['core'], SAMPLE['tail']], 0.34, color=BLUE, label='at the sample (height-scan images)')
    for i, k in enumerate(('core', 'tail')):
        ax.text(i, max(S1[k], SAMPLE[k]) + 2, '× %.2f' % (SAMPLE[k] / S1[k]), ha='center', fontsize=9, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(['core of the beam (%.0f %% of it)' % (100 * (1 - SAMPLE['frac'])),
                        'tail of the beam (%.0f %%)' % (100 * SAMPLE['frac'])])
    ax.set(ylabel='rms height σ (µm)', ylim=(0, 70))
    ax.legend(fontsize=7.5, loc='upper left', frameon=False)
    ax.set_title('D. Both parts of the beam are wider at the sample than at S1:\nthe beam widens after S1, as '
                 'a focus at S1 makes it (B would shrink it)', fontsize=9.5)
    note(fig, 0.06, 'Measured widths are pooled medians at 10 keV: S1 slit scans with a slit of 5 µm or less '
         '(core %.1f µm, tail %.1f µm, tail fraction %.2f), and the height scans\' images with S1 at 0.04 mm, the '
         'slit of the edges (core %.1f µm, tail %.1f µm, tail fraction %.2f). Measured σ_Q: '
         'docs/studies/qz_resolution/ (S1 0.02 mm was not determined there).'
         % (S1['core'], S1['tail'], S1['frac'], SAMPLE['core'], SAMPLE['tail'], SAMPLE['frac']))
    p = os.path.join(out, 'F0_two_focus_cases.png')
    fig.savefig(p)
    plt.close(fig)
    return p, cc


def variants():
    base = beam_resolution()
    v = [('the beam as measured (focus at S1)', base, 0.0)]
    v.append(('tail fraction 0.37 (the images at S1 0.02 mm)', dict(base, frac=0.37), 0.0))
    v.append(('S1 40 mm further away (the surface cuts the beam downstream)',
              beam_resolution(d=D + 0.04), 0.0))
    v.append(('core only (no tail)', dict(base, frac=0.0), 0.0))
    return v


def figure_budget(out, n):
    res = beam_resolution()
    runs = []
    for lab, r, ex in variants():
        s = simulate_fits(r, ex, n=n)
        runs.append(dict(label=lab, res=r, sim=s))
    # the extra Gaussian needed on top of the beam to reach the real median
    extras = np.array([0.0, 1.0, 1.5, 2.0, 2.5, 3.0]) * 1e-4
    ext = [float(np.median(simulate_fits(res, e, n=max(30, n // 4), seed=9)['sigma_q'])) for e in extras]
    need = float(np.interp(SIGQ_REAL, ext, extras))
    gauss = simulate_fits(dict(frac=0.0, core=SIGQ_REAL / K * 1e6, tail=0.0), 0.0, n=max(30, n // 4), seed=5)
    beam_sq = float(np.median(runs[0]['sim']['sigma_q']))

    fig = plt.figure(figsize=(13.5, 11))
    gs = fig.add_gridspec(2, 2, hspace=0.5, wspace=0.42, left=0.11, right=0.97, top=0.82, bottom=0.13)
    fig.suptitle('With the focus at S1, an edge blurred by the beam alone reads σ_Q %.1f × 10⁻⁴ Å⁻¹ in a one-Gaussian '
                 'fit: %.0f %% of the measured %.1f\n(%.0f %% of its square). If the rest were one more Gaussian, it '
                 'would be %.1f × 10⁻⁴; figure 2 tests that on the real edges'
                 % (beam_sq * 1e4, 100 * beam_sq / SIGQ_REAL, SIGQ_REAL * 1e4, 100 * (beam_sq / SIGQ_REAL) ** 2,
                    need * 1e4), fontsize=12, fontweight='bold', color=INK, x=0.04, ha='left')
    fig.text(0.04, 0.89, 'Calculated from the measured widths (figure 0). Edges sampled like the real ones '
             '(0.016–0.030 Å⁻¹ in steps of 0.001, random offset), fitted with one Gaussian as on the real edges.',
             fontsize=9, color=GREY)

    ax = fig.add_subplot(gs[0, 0])
    t = np.linspace(-200, 200, 801)
    def gpdf(s):
        return np.exp(-0.5 * (t / s) ** 2) / (s * np.sqrt(2 * np.pi))
    beam = (1 - res['frac']) * gpdf(res['core']) + res['frac'] * gpdf(res['tail'])
    ax.semilogy(t, beam, color=BLUE, lw=1.8, label='the beam: core %.0f µrad (%.0f %%) + tail %.0f µrad (%.0f %%)'
                % (res['core'], 100 * (1 - res['frac']), res['tail'], 100 * res['frac']))
    ax.semilogy(t, gpdf(SIGQ_REAL / K * 1e6), color=INK, ls='--', lw=1.2,
                label='one Gaussian of the measured σ_Q (%.0f µrad)' % (SIGQ_REAL / K * 1e6))
    ax.set(xlabel='angle of incidence about the set angle (µrad)', ylabel='share of rays per µrad', ylim=(1e-5, 0.1))
    sec = ax.secondary_xaxis('top', functions=(lambda x: x * K * 1e-2, lambda q: q / (K * 1e-2)))
    sec.set_xlabel('the same in Qz (10⁻⁴ Å⁻¹)', fontsize=8)
    ax.legend(fontsize=7.5, loc='lower center', frameon=False)
    ax.set_title('A. The beam\'s spread of angles, from its widths at S1 and at the\nsample: a narrow core and a '
                 'wide tail, not one Gaussian', fontsize=9.5)

    ax = fig.add_subplot(gs[0, 1])
    q = np.linspace(0.017, 0.028, 400)
    rf = F.fresnel_absorbing(q, QC, BETA, E)
    ax.plot(q, F.fresnel_absorbing(q, QC, BETA, E) / rf, color=GREY, lw=1, label='perfect resolution')
    ax.plot(q, reflect(q, 0.0, res) / rf, color=BLUE, lw=1.8, label='blurred by the beam alone')
    ax.plot(q, F.fresnel_smeared(q, QC, SIGQ_REAL, BETA, E) / rf, color=INK, ls='--', lw=1.2,
            label='blurred by one Gaussian of the measured σ_Q')
    ax.axvline(QC, color=INK, lw=0.6)
    ax.set(xlabel='Qz (Å⁻¹)', ylabel='R / R_F (sharp edge)', ylim=(0.75, 1.25))
    ax.legend(fontsize=7.5, frameon=False, loc='upper left')
    ax.set_title('B. What each does to the edge (bare water, no offset):\nthe beam blurs less near Qc but '
                 'reaches further above it', fontsize=9.5)

    ax = fig.add_subplot(gs[1, 0])
    for i, r in enumerate(runs):
        s = r['sim']['sigma_q'] * 1e4
        jit = np.random.default_rng(i).uniform(-0.22, 0.22, len(s))
        ax.plot(s, i + jit, '.', color=BLUE, ms=4, alpha=0.6)
        ax.plot([np.median(s)] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
        ax.text(5.95, i - 0.32, '%.0f %% at 0' % (100 * np.mean(s < 0.05)), fontsize=7.5, color=INK, ha='right')
    ax.axvspan(2.7, 5.3, color=LIGHT, alpha=0.6, lw=0)
    ax.axvline(SIGQ_REAL * 1e4, color=INK, ls='--')
    ax.text(SIGQ_REAL * 1e4 + 0.05, len(runs) - 0.6, 'measured median %.1f' % (SIGQ_REAL * 1e4), fontsize=8,
            color=INK)
    ax.set_yticks(range(len(runs)))
    ax.set_yticklabels([textwrap.fill(r['label'], 24) for r in runs], fontsize=7.5)
    ax.invert_yaxis()
    ax.set(xlabel='σ_Q fitted with one Gaussian (10⁻⁴ Å⁻¹)', xlim=(0, 6))
    ax.set_title('C. σ_Q the beam alone would give (black: median), and how it\nmoves with what is assumed; often the fit falls to 0 (grey: the real run medians)',
                 fontsize=9.5)

    ax = fig.add_subplot(gs[1, 1])
    real = 'docs/studies/qoff_resolution_real/residual_pattern.csv'
    if os.path.exists(real):
        rows = [r for r in csv.DictReader(open(real, encoding='utf-8')) if r['data'] == 'private']
        ax.plot([float(r['position']) for r in rows], [float(r['mean_scaled']) for r in rows], 'o-', color=INK,
                ms=4, lw=1.2, label='real edges (qoff_resolution_real)')
    s0 = runs[0]['sim']
    ax.plot(s0['pos'], s0['pattern'], 's-', color=BLUE, ms=4, lw=1.2, label='edges blurred by the beam alone')
    ax.plot(gauss['pos'], gauss['pattern'], '^-', color=GREY, ms=3, lw=1, label='edges blurred by one Gaussian')
    both = simulate_fits(res, need, n=max(30, n // 2), seed=13)
    ax.plot(both['pos'], both['pattern'], 'v-', color=ORANGE, ms=4, lw=1.2,
            label='the beam plus %.1f × 10⁻⁴ of other causes' % (need * 1e4))
    ax.axhline(0, color=INK, lw=0.6)
    ax.set(xlabel='point position from the fitted edge (steps of 0.001 Å⁻¹)', ylabel='mean residual / √(χ²/dof)',
           xlim=(-7, 9))
    ax.legend(fontsize=7.5, frameon=False, loc='lower left')
    ax.set_title('D. The real edges\' residual pattern, against edges blurred by\nthe beam, by one Gaussian, and by both', fontsize=9.5)
    note(fig, 0.065, 'Model: the beam\'s angular spread from its widths, focus at S1: σ_θ = √(σ_sample² − σ_S1²) / '
         'D for the core and the tail, D = %.0f mm. "Other causes" is the Gaussian that, added to both parts of the '
         'beam, brings the fitted median up to the measured one: for instance a moving or curved surface, or the '
         'edge model (absorption, the smooth factor). Water, β %.2g, counting errors as on the real edges (0.1 %% on the plateau, 0.43 %% at '
         '0.030 Å⁻¹), %d edges per variant.'
         % (D * 1e3, BETA, n))
    p = os.path.join(out, 'F1_how_much_the_beam_explains.png')
    fig.savefig(p)
    plt.close(fig)
    nums = dict(distance_s1_sample_m=D, widths_at_s1_um=S1, widths_at_sample_um=SAMPLE, beam_resolution_urad=res,
                beam_sigma_q_fit=beam_sq, measured_sigma_q=SIGQ_REAL, share_of_width=beam_sq / SIGQ_REAL,
                share_of_square=(beam_sq / SIGQ_REAL) ** 2, other_causes_sigma_q=need,
                variants=[dict(label=r['label'], resolution_urad=r['res'],
                               sigma_q_median=float(np.median(r['sim']['sigma_q'])),
                               sigma_q_p10=float(np.percentile(r['sim']['sigma_q'], 10)),
                               sigma_q_p90=float(np.percentile(r['sim']['sigma_q'], 90)),
                               chi2_median=float(np.median(r['sim']['chi2']))) for r in runs],
                extra_curve=dict(extra=list(map(float, extras)), sigma_q_median=ext),
                beam_pattern=dict(pos=list(map(float, s0['pos'])), mean_scaled=list(map(float, s0['pattern']))),
                beam_plus_other_pattern=dict(pos=list(map(float, both['pos'])), mean_scaled=list(map(float, both['pattern']))),
                beam_plus_other_sigma_q=float(np.median(both['sigma_q'])), beam_plus_other_chi2=float(np.median(both['chi2'])),
                beam_share_at_zero=float(np.mean(runs[0]['sim']['sigma_q'] < 5e-6)))
    return p, nums


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/focus_and_resolution')
    ap.add_argument('--n', type=int, default=120, help='simulated edges per variant')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    style()
    p0, cc = figure_cases(a.out)
    p1, nums = figure_budget(a.out, a.n)
    nums['clip_cases'] = cc
    with open(os.path.join(a.out, 'calculated.json'), 'w', encoding='utf-8') as fh:
        json.dump(nums, fh, indent=1, ensure_ascii=False)
    for p in (p0, p1):
        print('wrote', p)
    print('beam alone: sigma_q %.3g (%.0f %% of %.2g); other causes %.3g' % (
        nums['beam_sigma_q_fit'], 100 * nums['share_of_width'], SIGQ_REAL, nums['other_causes_sigma_q']))


if __name__ == '__main__':
    main()
