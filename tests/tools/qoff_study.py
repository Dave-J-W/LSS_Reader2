"""Study of the Qoff proposer (F79; lss_core.fresnel; Main 2026-11-24, rule 12):
synthetic reflectivity with a known angle offset δα, replicates, outliers,
joins, resolution and a wrong Qc; every estimator judged against the
truth; the NX school scans as the real check.

    python tests/tools/qoff_study.py --out docs/studies/qoff                 # about 4 min on 4 CPUs
    python tests/tools/qoff_study.py --out DIR --design offset,outliers --replicates 40
    python tests/tools/qoff_study.py --out DIR --only Q1,Q5                  # the figures that need no run

The truth (``tests/synthetic/xrr.py``, ``xrr_scans.measure`` with
``Beamline.angle_offset_deg``): the sample sees Qz_true = (4π/λ) sin(α + δα)
while the rows keep the recorded Qz, so the right Qoff is
(4π/λ) cos α δα (``xrr_scans.qoff_of``). The curve is stitched with the
true scan scales (so the joins add nothing) unless the design says
'joins' (the reader's own patch, ``reflectivity.patch``). Water's
absorption is in the truth and not in the reader's R_F, as in life.

Designs (``--design``, comma-separated, or 'all'):

- ``offset``: bare water at the NX school counts, δα from −0.01° to 0.01°;
- ``sample``: water, DPPC, a 100 Å film (Kiessig fringes) at δα 0.005°;
- ``counts``: water at 1, 0.1 and 0.01 of the NX counts;
- ``outliers``: one or two points near the edge off by ±30 %;
- ``resolution``: a Gaussian Qz resolution of FWHM 0.0002, 0.0005, 0.001 Å⁻¹;
- ``qc``: the subphase 1 M NaCl (Qc 0.0221) reduced at water's 0.0217,
  and water reduced at 0.0221;
- ``joins``: the reader's patch (joint fit) instead of the true scales.

Estimators: ``smooth`` (the roughness of ln R/R_F, Huber then Tukey loss),
``smooth_sq`` (the same, least squares), ``edge`` (a model fit of the edge,
soft L1; ``propose_qoff``'s default, from this study), ``edge_qc`` (the same
with Qc free).

Figures: Q1 the anatomy (R/R_F near the edge for Qoff wrong by ±, the two
losses against Qoff); Q2 bias ± SD per design and estimator; Q3 pulls;
Q4 the wrong Qc and the degeneracy (replicates of the joint fit on the
line Qc − Qoff = constant; the level error of R/R_F); Q5 NX school scans
6–9 (R/R_F at Qoff 0, the GUI's preset, and at the proposals; the
losses). Tables: ``results.csv`` (per design, condition and estimator),
``replicates.csv``, ``numbers.json``. All synthetic but Q5, which uses
the public NX school data.
"""
import argparse
import csv
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from lss_core import fresnel as F, reflectivity as refl     # noqa: E402
from synthetic import xrr, xrr_scans as xs                   # noqa: E402

NX = 'sample_data/NX_school/2026sep/20260923'
QC_WATER_TRUE = xrr.qc(xrr.RHO_WATER)                        # 0.02175, the generator's water
RHO_NACL_1M = F.subphase('NaCl 6 % (1.07 M)').rho_e          # 0.3452 e/Å³: Qc 0.0221
ESTIMATORS = ('smooth', 'smooth_sq', 'edge', 'edge_qc')
NAMES = {'smooth': 'smoothness (Tukey)', 'smooth_sq': 'smoothness, least squares',
         'edge': 'edge fit (soft L1), the default', 'edge_qc': 'edge fit, Qc free'}
COLOURS = {'smooth': 'C0', 'smooth_sq': 'C9', 'edge': 'C3', 'edge_qc': 'C1'}
DESIGNS = ('offset', 'sample', 'counts', 'outliers', 'resolution', 'qc', 'joins')


@dataclass
class Cond:
    design: str
    label: str
    offset_deg: float = 0.005
    sample: str = 'water'
    counts: float = 1.0
    outliers: int = 0
    resolution: float = 0.0          # FWHM Å⁻¹
    rho: float = xrr.RHO_WATER       # the subphase
    qc_assumed: float = None         # the Qc the reduction uses (None: the subphase's own)
    joins: bool = False

    @property
    def truth(self):
        return float(xs.qoff_of(self.offset_deg, 0.02))

    @property
    def qc_true(self):
        return xrr.qc(self.rho)

    @property
    def qc_used(self):
        return self.qc_true if self.qc_assumed is None else self.qc_assumed


def profile(c):
    p = {'water': xrr.bare_water(), 'dppc': xrr.dppc(), 'film': xrr.film(100.0)}[c.sample]
    return replace(p, rho=c.rho)


def conditions(designs):
    out = []
    for d in designs:
        if d == 'offset':
            out += [Cond(d, 'δα %+.3f°' % a, offset_deg=a) for a in (-0.01, -0.005, 0.0, 0.002, 0.005, 0.01)]
        elif d == 'sample':
            out += [Cond(d, s, sample=s) for s in ('water', 'dppc', 'film')]
        elif d == 'counts':
            out += [Cond(d, 'counts × %g' % k, counts=k) for k in (1.0, 0.1, 0.01)]
        elif d == 'outliers':
            out += [Cond(d, '%d outlier(s)' % n, outliers=n) for n in (0, 1, 2)]
            out += [Cond(d, 'edge point × 0.7', outliers=-1)]
        elif d == 'resolution':
            out += [Cond(d, 'ΔQ %g' % r, resolution=r) for r in (0.0, 0.0002, 0.0005, 0.001)]
        elif d == 'qc':
            out += [Cond(d, 'NaCl at 0.0217', rho=RHO_NACL_1M, qc_assumed=0.0217),
                    Cond(d, 'NaCl at its Qc', rho=RHO_NACL_1M),
                    Cond(d, 'water at 0.0221', qc_assumed=0.0221)]
        elif d == 'joins':
            out += [Cond(d, '%s, reader\'s patch' % s, sample=s, joins=True) for s in ('water', 'dppc')]
        else:
            raise SystemExit('unknown design %r: %s' % (d, ', '.join(DESIGNS)))
    return out


def curve(c, seed):
    """(q, R, σ) of one replicate: stitched with the true scales (or the
    reader's patch), outliers applied."""
    bl = replace(xs.Beamline(**xs.REAL_MONITOR, angle_offset_deg=c.offset_deg))
    bl = replace(bl, flux=bl.flux * c.counts, max_rate=bl.max_rate * c.counts)
    res = (c.resolution, 0.0) if c.resolution else None
    d = xs.measure(profile(c), xs.nx_like_plan(), beamline=bl, resolution=res, errors='counting+monitor', seed=seed)
    if c.joins:
        data = refl.patch(d.per_scan, d.order)[:, :3]
        q, r, s = data[:, 0], data[:, 1], data[:, 2]
    else:
        q = np.concatenate([rows[:, 0] for rows in d.per_scan.values()])
        r = np.concatenate([rows[:, 1] * d.scans[n].scale for n, rows in d.per_scan.items()])
        s = np.concatenate([rows[:, 2] * d.scans[n].scale for n, rows in d.per_scan.items()])
    if c.outliers < 0:                     # the worst case: the first point above the edge, 30 % low
        r = r.copy()
        k = int(np.flatnonzero(q > c.qc_true - c.truth)[0])
        r[k] *= 0.7
    elif c.outliers:
        rng = np.random.default_rng(list(seed) + [99])
        near = np.flatnonzero((q > c.qc_true) & (q < 3 * c.qc_true))
        for k in rng.choice(near, c.outliers, replace=False):
            r = r.copy()
            r[k] *= 1.3 if rng.random() < 0.5 else 0.7
    return q, r, s


def estimate(c, q, r, s, est, bootstrap):
    kw = dict(qc=c.qc_used, bootstrap=bootstrap, seed=1)
    if est == 'smooth':
        p = F.propose_qoff(q, r, s, method='smooth', **kw)
    elif est == 'smooth_sq':
        p = F.propose_qoff(q, r, s, method='smooth', loss='squared', **kw)
    elif est == 'edge':
        p = F.propose_qoff(q, r, s, method='edge', **kw)
    else:
        p = F.propose_qoff(q, r, s, method='edge', fit_qc=True, **kw)
    return p


def run_condition(args):
    k, c, reps, bootstrap = args
    rows = []
    for rep in range(reps):
        q, r, s = curve(c, [2026, 11, 24, k, rep])
        for est in ESTIMATORS:
            p = estimate(c, q, r, s, est, bootstrap)
            rows.append(dict(design=c.design, condition=c.label, rep=rep, estimator=est, truth=c.truth,
                             qoff=p.qoff if p.ok else math.nan, sigma=p.sigma if p.ok else math.nan,
                             qc=p.qc, qc_true=c.qc_true, qc_used=c.qc_used, ok=bool(p.ok), outliers=len(p.outliers)))
    return rows


def summarise(rows):
    out = []
    keys = []
    for r in rows:
        key = (r['design'], r['condition'], r['estimator'])
        if key not in keys:
            keys.append(key)
    for key in keys:
        g = [r for r in rows if (r['design'], r['condition'], r['estimator']) == key]
        good = [r for r in g if r['ok'] and np.isfinite(r['qoff'])]
        e = np.array([r['qoff'] for r in good])
        t = np.array([r['truth'] for r in good])
        sg = np.array([r['sigma'] for r in good])
        n = len(good)
        pull = (e - t) / sg if n else np.array([])
        pull = pull[np.isfinite(pull)]
        out.append(dict(design=key[0], condition=key[1], estimator=key[2], n=len(g), failed=len(g) - n,
                        truth=g[0]['truth'], bias=float(np.mean(e - t)) if n else math.nan,
                        sd=float(np.std(e, ddof=1)) if n > 1 else math.nan,
                        rmse=float(np.sqrt(np.mean((e - t) ** 2))) if n else math.nan,
                        mean_sigma=float(np.mean(sg)) if n else math.nan,
                        pull_mean=float(np.mean(pull)) if len(pull) else math.nan,
                        pull_sd=float(np.std(pull, ddof=1)) if len(pull) > 1 else math.nan,
                        qc_mean=float(np.mean([r['qc'] for r in good])) if n else math.nan))
    return out


def _write(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})


# ---- figures -----------------------------------------------------------------

def _plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    return plt


def q1(out):
    """The anatomy: R/R_F near the edge at Qoff wrong by ±Δ, and the losses."""
    plt = _plt()
    c = Cond('anatomy', 'water, δα 0.005°')
    q, r, s = curve(c, [2026, 1])
    qc, t = c.qc_used, c.truth
    fig, (a, b, d) = plt.subplots(1, 3, figsize=(16, 4.8))
    sel = q < 0.09
    for dq, col in ((-0.0005, 'C3'), (0.0, 'k'), (0.0005, 'C0')):
        y = F.rrf(q, r, qc, t + dq)
        a.errorbar(q[sel], y[sel], s[sel] / F.fresnel(q[sel] + t + dq, qc), fmt='o', ms=3, color=col,
                   label='Qoff = truth %+.4f' % dq if dq else 'Qoff = truth (%.5f)' % t)
    y0 = F.rrf(q, r, qc, 0.0)
    a.plot(q[sel], y0[sel], 'x', color='0.5', ms=4, label='Qoff = 0 (the preset)')
    a.set_yscale('log')
    a.set_xlabel('Qz recorded (Å⁻¹)')
    a.set_ylabel('R / R_F(Qz + Qoff)')
    a.set_title('R/R_F near the edge (water, δα 0.005°)', fontsize=10)
    a.axvline(qc, color='0.7', lw=0.8)
    a.legend(fontsize=7)
    p = F.propose_qoff(q, r, s, qc=qc, method='smooth')
    b.plot(p.grid * 1e4, p.objective, 'C0')
    b.axvline(t * 1e4, color='k', ls='--', lw=0.8, label='truth')
    b.axvline(p.qoff * 1e4, color='C0', ls=':', label='proposed %.5f' % p.qoff)
    b.set_xlabel('Qoff (10⁻⁴ Å⁻¹)')
    b.set_ylabel('Σ Tukey(second differences / σ)')
    b.set_title('The smoothness loss', fontsize=10)
    b.legend(fontsize=7)
    grid = np.linspace(-0.003, 0.003, 301)
    from lss_core.fresnel import _prepare, _edge_estimate
    qq, ly, ss = _prepare(q, r, s, 2.5 * qc, None)
    cost = []
    for g in grid:
        res = _edge_estimate(qq, ly, ss, qc, False, start=g)
        m = F._edge_model(np.r_[res.x[:3], g], qq, qc, False)
        z = (ly - m) / ss
        cost.append(float(np.sum(2 * (np.sqrt(1 + (z / 2) ** 2) - 1))))
    d.plot(grid * 1e4, cost, 'C3')
    d.axvline(t * 1e4, color='k', ls='--', lw=0.8)
    d.set_yscale('log')
    d.set_xlabel('Qoff (10⁻⁴ Å⁻¹)')
    d.set_ylabel('soft L1 cost (other parameters refitted)')
    d.set_title('The edge fit\'s cost', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'Q1_anatomy.png'), dpi=100)
    plt.close(fig)


def q2(summary, out):
    plt = _plt()
    designs = [d for d in DESIGNS if any(s['design'] == d for s in summary)]
    fig, axes = plt.subplots(1, len(designs), figsize=(3.4 * len(designs), 5), sharey=True, squeeze=False)
    for ax, d in zip(axes[0], designs):
        conds = []
        for s in summary:
            if s['design'] == d and s['condition'] not in conds:
                conds.append(s['condition'])
        for j, est in enumerate(ESTIMATORS):
            xs_ = [i + (j - 1.5) * 0.18 for i in range(len(conds))]
            ys = [next(s['bias'] for s in summary if s['design'] == d and s['condition'] == c and s['estimator'] == est)
                  * 1e4 for c in conds]
            es = [next(s['sd'] for s in summary if s['design'] == d and s['condition'] == c and s['estimator'] == est)
                  * 1e4 for c in conds]
            ax.errorbar(xs_, ys, es, fmt='o', ms=4, color=COLOURS[est], label=NAMES[est] if d == designs[0] else None)
        ax.axhline(0, color='k', lw=0.6)
        ax.set_xticks(range(len(conds)))
        ax.set_xticklabels(conds, rotation=40, ha='right', fontsize=7)
        ax.set_title(d, fontsize=10)
        ax.set_ylim(-12, 12)
    axes[0][0].set_ylabel('bias ± SD of Qoff (10⁻⁴ Å⁻¹; clipped at ±12)')
    fig.legend(loc='upper center', ncol=4, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(os.path.join(out, 'Q2_bias.png'), dpi=100)
    plt.close(fig)


def q3(rows, out):
    plt = _plt()
    fig, axes = plt.subplots(1, len(ESTIMATORS), figsize=(14, 3.6), sharey=True)
    base = [r for r in rows if r['design'] in ('offset', 'sample', 'counts') and r['ok']]
    for ax, est in zip(axes, ESTIMATORS):
        p = np.array([(r['qoff'] - r['truth']) / r['sigma'] for r in base if r['estimator'] == est
                      and np.isfinite(r['sigma']) and r['sigma'] > 0])
        p = p[np.abs(p) < 20]
        ax.hist(p, bins=40, range=(-10, 10), color=COLOURS[est], alpha=0.8)
        ax.set_title('%s\npull mean %.2f, SD %.2f' % (NAMES[est], np.mean(p), np.std(p)), fontsize=8)
        ax.set_xlabel('(estimate − truth) / σ')
    axes[0].set_ylabel('replicates (offset, sample, counts designs)')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'Q3_pulls.png'), dpi=100)
    plt.close(fig)


def q4(rows, out):
    plt = _plt()
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8))
    for lab, col in (('NaCl at 0.0217', 'C3'), ('NaCl at its Qc', 'C2'), ('water at 0.0221', 'C0')):
        g = [r for r in rows if r['design'] == 'qc' and r['condition'] == lab and r['estimator'] == 'edge_qc' and r['ok']]
        if g:
            a.plot([r['qc'] for r in g], [r['qoff'] for r in g], '.', color=col, ms=4, label=lab + ' (edge, Qc free)')
            t = g[0]
            a.plot([t['qc_true']], [t['truth']], '*', color=col, ms=12, mec='k')
    qq = np.linspace(0.0205, 0.0245, 10)
    t = Cond('x', 'x').truth
    for q0, col in ((QC_WATER_TRUE, 'C0'), (xrr.qc(RHO_NACL_1M), 'C3')):
        a.plot(qq, qq - q0 + t, ':', color=col, lw=0.8)
    a.set_xlabel('Qc fitted (Å⁻¹)')
    a.set_ylabel('Qoff fitted (Å⁻¹)')
    a.set_title('Qc and Qoff together: replicates lie on Qc − Qoff = constant (dotted)', fontsize=9)
    a.legend(fontsize=7)
    for lab, col in (('NaCl at 0.0217', 'C3'), ('water at 0.0221', 'C0')):
        g = [r for r in rows if r['design'] == 'qc' and r['condition'] == lab and r['estimator'] == 'smooth' and r['ok']]
        if not g:
            continue
        r0 = g[0]
        qz = np.linspace(0.023, 0.45, 300)
        lev = F.fresnel(qz + r0['truth'], r0['qc_true']) / F.fresnel(qz + np.mean([r['qoff'] for r in g]), r0['qc_used'])
        b.plot(qz, lev, color=col, label='%s, at the proposed Qoff' % lab)
    b.axhline(1, color='k', lw=0.6)
    b.set_xlabel('Qz (Å⁻¹)')
    b.set_ylabel('R/R_F reduced ÷ R/R_F true')
    b.set_title('What a wrong Qc does to R/R_F (Qoff from the data)', fontsize=9)
    b.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'Q4_qc.png'), dpi=100)
    plt.close(fig)


def nx_check(out, spec=NX):
    """Q5 and its numbers: the NX school scans 6–9 at the GUI's preset (Qoff 0) and at the proposals."""
    plt = _plt()
    from lss_core.experiment import Experiment
    e = Experiment(spec)
    ref = e.reflectivity([6, 7, 8, 9]).ref
    q, r, s = ref[:, 0], ref[:, 1], ref[:, 2]
    props = {m: estimate(Cond('nx', 'nx', rho=F.density_from_qc(0.0217)), q, r, s, m, 200) for m in ESTIMATORS}
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.8))
    sel = q < 0.1
    a.plot(q[sel], F.rrf(q, r, 0.0217, 0.0)[sel], 'x', color='0.4', label='Qoff 0 (the GUI\'s preset)')
    for m in ('smooth', 'edge'):
        p = props[m]
        a.plot(q[sel], F.rrf(q, r, 0.0217, p.qoff)[sel], 'o', ms=3, color=COLOURS[m], label='%s: %+.5f ± %.5f' % (NAMES[m], p.qoff, p.sigma))
    a.set_yscale('log')
    a.axvline(0.0217, color='0.7', lw=0.8)
    a.set_xlabel('Qz (Å⁻¹)')
    a.set_ylabel('R / R_F (Qc 0.0217)')
    a.set_title('NX school scans 6–9 near the edge', fontsize=10)
    a.legend(fontsize=7)
    p = props['smooth']
    b.plot(p.grid * 1e4, p.objective, 'C0')
    b.axvline(0, color='0.4', ls='--', label='preset 0')
    b.axvline(p.qoff * 1e4, color='C0', ls=':', label='proposed')
    b.set_xlabel('Qoff (10⁻⁴ Å⁻¹)')
    b.set_ylabel('smoothness loss')
    b.set_title('NX: the smoothness loss against Qoff', fontsize=10)
    b.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'Q5_nx.png'), dpi=100)
    plt.close(fig)
    lam = float(e.scans[6].parameters.get('Wavelength', 1.23984))
    return {m: dict(qoff=p.qoff, sigma=p.sigma, qc=p.qc, qc_sigma=p.qc_sigma, correlation=p.correlation,
                    outliers=p.outliers, note=p.note,
                    angle_deg=math.degrees(p.qoff / (4 * math.pi / lam))) for m, p in props.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--design', default='all', help='comma-separated: %s, or all' % ', '.join(DESIGNS))
    ap.add_argument('--replicates', type=int, default=60)
    ap.add_argument('--bootstrap', type=int, default=40, help='bootstrap replicates per proposal (σ)')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--only', default=None, help='figures only: Q1, Q5 (no run)')
    ap.add_argument('--spec', default=NX, help='the SPEC file of the real check (scans 6-9)')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    numbers = {}
    if a.only:
        want = set(a.only.split(','))
        if 'Q1' in want:
            q1(a.out)
        if 'Q5' in want:
            numbers['nx'] = nx_check(a.out, a.spec)
        with open(os.path.join(a.out, 'numbers_only.json'), 'w', encoding='utf-8') as f:
            json.dump(numbers, f, indent=1, default=str)
        return 0
    designs = DESIGNS if a.design == 'all' else tuple(a.design.split(','))
    conds = conditions(designs)
    jobs = [(k, c, a.replicates, a.bootstrap) for k, c in enumerate(conds)]
    if a.jobs > 1:
        with ProcessPoolExecutor(a.jobs) as ex:
            parts = list(ex.map(run_condition, jobs))
    else:
        parts = [run_condition(j) for j in jobs]
    rows = [r for p in parts for r in p]
    summary = summarise(rows)
    _write(os.path.join(a.out, 'replicates.csv'), rows)
    _write(os.path.join(a.out, 'results.csv'), summary)
    q1(a.out)
    q2(summary, a.out)
    q3(rows, a.out)
    if 'qc' in designs:
        q4(rows, a.out)
    if os.path.exists(a.spec):
        numbers['nx'] = nx_check(a.out, a.spec)
    numbers['settings'] = dict(designs=list(designs), replicates=a.replicates, bootstrap=a.bootstrap)
    numbers['summary'] = summary
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(numbers, f, indent=1, default=str)
    for s in summary:
        print('%-10s %-22s %-10s bias %+.2e sd %.2e pull %+.2f/%.2f failed %d' % (
            s['design'], s['condition'], s['estimator'], s['bias'], s['sd'], s['pull_mean'], s['pull_sd'], s['failed']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
