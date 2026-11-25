"""The Qoff proposal (F79) from the raw frames to the judgment, step by
step, for docs/studies/qoff/walkthrough.md (the owner's standing order of
2026-11-25, AGENTS.md rule 13). Public data: NX school scans 6-9 (DPPC
on water, 10 keV); synthetic Fresnel curves for the resolution step.

Figures (``--out``):
- QW1 the raw data: one Pilatus frame below the edge, with the ROI that is
  counted;
- QW2 the reflectivity of the four joined scans, and R/R_F near the edge at
  Qoff 0 and at the proposal;
- QW3 the edge fit drawn over its data, with its residuals;
- QW4 the bootstrap: 200 redraws of the counting noise, and the spread of
  their proposals (σ);
- QW5 resolution: a sharp and a smeared edge, and what the edge fit reads
  as Qoff for each resolution.

    python tests/tools/qoff_walkthrough.py --out docs/studies/qoff/walkthrough
"""
import argparse
import json
import math
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np                                    # noqa: E402

from lss_core import fresnel as F                     # noqa: E402

NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
QC = 0.0217


def plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as p
    return p


def qw1(out, e):
    """One frame of scan 6, below the edge, and the counted box."""
    from lss_core import images
    p = plt()
    frames = e.frames([6])
    fr = min(frames, key=lambda f: abs(f.qz - 0.8 * QC))
    img = np.asarray(images.read_pilatus(fr.path), float)
    by, bx = np.unravel_index(int(np.argmax(img)), img.shape)   # below the edge the reflected beam is brightest
    fig, ax = p.subplots(figsize=(7.5, 4.8))
    ax.imshow(np.log10(np.maximum(img, 0.5)), origin='lower', aspect='auto', cmap='viridis')
    w, h = 21, 11                                      # the Ref Patch's default slit (columns, rows)
    ax.add_patch(p.Rectangle((bx - w / 2, by - h / 2), w, h, fill=False, color='w', lw=1.5))
    ax.set_xlim(bx - 60, bx + 60)
    ax.set_ylim(by - 40, by + 40)
    ax.set_title('Scan 6, frame %d (Qz %.4f Å⁻¹, below the edge %.4f): counts per pixel, log scale\n'
                 'the white box (21 × 11 pixels about the reflected beam) is what is counted' % (fr.index, fr.qz, QC),
                 fontsize=9)
    ax.set_xlabel('detector column')
    ax.set_ylabel('detector row')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'QW1_raw_frame.png'), dpi=130)
    p.close(fig)
    box = img[int(by - h / 2):int(by + h / 2) + 1, int(bx - w / 2):int(bx + w / 2) + 1]
    return dict(frame=fr.index, qz=fr.qz, box_counts=float(box.sum()), monitor=fr.monitor, beam=[int(bx), int(by)])


def qw2(out, q, r, s, prop):
    p = plt()
    fig, (a, b) = p.subplots(1, 2, figsize=(12, 4.6))
    a.errorbar(q, r, s, fmt='.', ms=3, color='k', elinewidth=0.6)
    a.plot(q, F.fresnel(q, QC), color='C0', lw=1, label='R_F: a perfectly sharp water surface (Qc %.4f)' % QC)
    a.set_yscale('log')
    a.set_xlabel('Qz (Å⁻¹)')
    a.set_ylabel('R (reflected / incident)')
    a.set_title('(a) The four scans joined (Ref Patch): R ± its counting error', fontsize=9)
    a.legend(fontsize=8)
    sel = q < 0.06
    b.plot(q[sel], F.rrf(q, r, QC, 0.0)[sel], 'x', color='0.4', label='Qoff 0 (the GUI\'s preset)')
    b.plot(q[sel], F.rrf(q, r, QC, prop.qoff)[sel], 'o', ms=4, color='C3',
           label='Qoff %+.5f (the edge fit\'s proposal)' % prop.qoff)
    b.axvline(QC, color='0.6', lw=0.8)
    b.set_yscale('log')
    b.set_xlabel('Qz (Å⁻¹)')
    b.set_ylabel('R / R_F')
    b.set_title('(b) R divided by R_F near the edge: a spike at Qoff 0, smooth at the proposal', fontsize=9)
    b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'QW2_reflectivity_and_rrf.png'), dpi=130)
    p.close(fig)
    i = int(np.argmax(q > QC))
    return dict(points=len(q), first_above=float(q[i]), spike_at_0=float(F.rrf(q, r, QC, 0.0)[i] /
                                                                          F.rrf(q, r, QC, 0.0)[i + 1]))


def qw3(out, q, r, s):
    """The edge fit over its data."""
    p = plt()
    qq, ly, sl = F._prepare(q, r, s, 2.5 * QC, None)
    res = F._edge_estimate(qq, ly, sl, QC, False)
    model = F._edge_model(res.x, qq, QC, False)
    z = (ly - model) / sl
    chi2 = float(np.sum(z ** 2))
    dof = len(qq) - 4
    fig, (a, b) = p.subplots(2, 1, figsize=(8, 6.2), gridspec_kw=dict(height_ratios=[3, 1.2]), sharex=True)
    a.errorbar(qq, ly, sl, fmt='o', ms=4, color='k', capsize=2, label='ln R of each point ± σ (up to 2.5 Qc)')
    fine = np.linspace(qq.min(), qq.max(), 400)
    a.plot(fine, F._edge_model(res.x, fine, QC, False), 'C3',
           label='ln A + ln R_F(Qz + Qoff) + b(Qz − Qc) + c(Qz − Qc)²')
    a.axvline(QC, color='0.6', lw=0.8)
    a.set_ylabel('ln R')
    a.set_title('The edge fit: Qoff %+.5f, ln A %.3f, b %.2f, c %.0f; χ²/dof %.1f/%d = %.2f' % (
        res.x[3], res.x[0], res.x[1], res.x[2], chi2, dof, chi2 / dof), fontsize=9)
    a.legend(fontsize=8)
    b.bar(qq, z, width=0.6 * np.median(np.diff(qq)), color='C3')
    b.axhline(0, color='k', lw=0.8)
    b.set_ylabel('residual / σ')
    b.set_xlabel('Qz (Å⁻¹)')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'QW3_edge_fit.png'), dpi=130)
    p.close(fig)
    return dict(qoff=float(res.x[3]), ln_a=float(res.x[0]), b=float(res.x[1]), c=float(res.x[2]), chi2=chi2,
                dof=dof, points=len(qq), worst_residual=float(np.max(np.abs(z))))


def qw4(out, q, r, s, prop, n=200, seed=0):
    """The bootstrap: redraw each point within its error, propose again."""
    p = plt()
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        rr = r + rng.normal(0.0, s)
        ok = rr > 0
        vals.append(F.propose_qoff(q[ok], rr[ok], s[ok], qc=QC, bootstrap=0).qoff)
    vals = np.array(vals)
    fig, ax = p.subplots(figsize=(8, 4.4))
    ax.hist(vals * 1e4, bins=25, color='C3', alpha=0.7)
    ax.axvline(prop.qoff * 1e4, color='k', label='the proposal on the real data')
    ax.axvline(0, color='0.4', ls='--', label='the GUI\'s preset, 0')
    ax.set_xlabel('Qoff (10⁻⁴ Å⁻¹)')
    ax.set_ylabel('replicates')
    ax.set_title('%d redraws of the counting noise: Qoff %+.2f ± %.2f (×10⁻⁴); the spread is the error' % (
        n, 1e4 * vals.mean(), 1e4 * vals.std()), fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'QW4_bootstrap.png'), dpi=130)
    p.close(fig)
    return dict(replicates=n, mean=float(vals.mean()), sd=float(vals.std()), proposal_sigma=prop.sigma)


def smeared(q, qc, fwhm):
    """R_F convolved with a Gaussian of this FWHM (fine grid, constant ΔQ)."""
    if fwhm <= 0:
        return F.fresnel(q, qc)
    sg = fwhm / (2 * math.sqrt(2 * math.log(2)))
    u = np.linspace(-4 * sg, 4 * sg, 161)
    w = np.exp(-0.5 * (u / sg) ** 2)
    w /= w.sum()
    return np.array([np.sum(w * F.fresnel(np.abs(x + u), qc)) for x in q])


def qw5(out, q_nx, rel_nx, fwhms=(0.0, 2e-4, 5e-4, 6.5e-4, 8.9e-4, 1.2e-3, 1.26e-3)):
    """What a resolution does to the edge, and to the proposal, on NX's own
    Qz points and relative errors (the reading depends on the grid: on a
    fine grid of 0.0005 with 0.5 % errors, 8.9e-4 reads as -0.95e-4)."""
    p = plt()
    q = q_nx
    reads = []
    fig, (a, b) = p.subplots(1, 2, figsize=(12, 4.4))
    for fw in fwhms:
        r = smeared(q, QC, fw)
        prop = F.propose_qoff(q, r, rel_nx * r, qc=QC, bootstrap=0)
        reads.append(dict(fwhm=fw, qoff=prop.qoff))
        if fw in (0.0, 8.9e-4):
            a.plot(q, r, label='ΔQ %s' % ('0 (sharp)' if fw == 0 else '%.1e FWHM (measured, #68)' % fw))
    a.set_yscale('log')
    a.set_xlim(0.015, 0.035)
    a.axvline(QC, color='0.6', lw=0.8)
    a.set_xlabel('Qz (Å⁻¹)')
    a.set_ylabel('R_F, sharp and smeared')
    a.set_title('(a) A finite resolution rounds the edge', fontsize=9)
    a.legend(fontsize=8)
    b.plot([x['fwhm'] * 1e4 for x in reads], [x['qoff'] * 1e4 for x in reads], 'o-', color='C3')
    b.axvline(8.9, color='0.5', ls=':', label='the beamline\'s ΔQ (8.9 × 10⁻⁴)')
    b.set_xlabel('resolution ΔQ FWHM (10⁻⁴ Å⁻¹)')
    b.set_ylabel('Qoff the edge fit proposes (10⁻⁴ Å⁻¹)')
    b.set_title('(b) Noise-free water, no angle offset, on NX\'s Qz points and errors:\nthe rounding reads as a negative Qoff', fontsize=9)
    b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'QW5_resolution.png'), dpi=130)
    p.close(fig)
    return reads


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='docs/studies/qoff/walkthrough', help='output folder')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    from lss_core.experiment import Experiment
    e = Experiment(NX)
    ref = e.reflectivity([6, 7, 8, 9]).ref
    q, r, s = ref[:, 0], ref[:, 1], ref[:, 2]
    prop = F.propose_qoff(q, r, s, qc=QC)
    n = OrderedDict()
    n['proposal'] = dict(qoff=prop.qoff, sigma=prop.sigma, note=prop.note)
    n['QW1'] = qw1(a.out, e)
    n['QW2'] = qw2(a.out, q, r, s, prop)
    n['QW3'] = qw3(a.out, q, r, s)
    n['QW4'] = qw4(a.out, q, r, s, prop)
    keep = q < 2.5 * QC
    n['QW5'] = qw5(a.out, q[keep], (s / r)[keep])
    with open(os.path.join(a.out, 'numbers.json'), 'w', encoding='utf-8') as f:
        json.dump(n, f, indent=1, default=float)
    print(json.dumps(n, indent=1, default=float))
    return 0


if __name__ == '__main__':
    sys.exit(main())
