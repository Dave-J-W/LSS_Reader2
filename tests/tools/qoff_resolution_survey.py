"""Qoff and the Qz resolution fitted together on every real edge scan of
many SPEC files (hand-off 09: tools man builds it, the local data agent runs
it on the owner's private edges). The method:
``lss_core.fresnel.fit_edge_resolution``; the study and its known truth:
``tests/tools/qoff_resolution_study.py`` (``--truth`` reruns it at a given
Qoff, σ_Q, counts and Qz step); the plan: docs/handoff_out/09-qoff-resolution-fit.md.

    python tests/tools/qoff_resolution_survey.py --spec FILE [--spec FILE ...] --out DIR
    python tests/tools/qoff_resolution_survey.py --list scans.csv --out DIR [--subphase NAME] [--beta-scale 2]

Run from the repository root. ``--spec`` finds the scans of a SPEC file that
cross the edge: a reflectivity scan (``lss_core.series``) whose Qz runs from
below 0.875 Qc to above 1.2 Qc (``--below``, ``--above``; row 13's selection,
below 0.019 and above 0.026 Å⁻¹ for water: the hand-off's 0.8 Qc would miss
NX school scan 6, which starts at 0.806 Qc). Only the first scan of a series
usually crosses. ``--list`` gives them by hand (CSV lines ``spec,scan[,label]``).
Each is reduced alone (``Experiment.reflectivity([scan], errors='budget')``,
the window's Ref Patch arithmetic) and fitted at the subphase's Qc and β
(``--subphase``, default water; ``--qc`` overrides Qc; ``--beta-scale``
multiplies β, for row 13's absorption check; ``--roughness`` puts a fixed
Névot–Croce roughness in R_F, 0 by default as the hand-off's model). Today's ``propose_qoff``
(sharp R_F) is read beside it on the same scan. Reads only. Private data:
``--out`` must be under ``sample_data/private/`` or outside the repository
(checked; the public NX school file may write anywhere).

Outputs: ``edges.csv``, one row per scan, with the hand-off's columns:
``spec`` (the file's name), ``scan``, ``label``, ``energy_kev``, ``qc``,
``beta``, ``roughness``, ``n_points``, ``n_below``, ``n_above`` (points below and above the
fitted edge Qc − Qoff, inside the fit's range), ``qoff``, ``qoff_err``,
``sigma_q``, ``sigma_q_err``, ``corr``, ``chi2_dof``, ``flags``,
``qoff_sharp``, ``qoff_sharp_err``; and also ``qoff_err_counting``,
``sigma_q_err_counting`` (before the √(χ²/dof) scaling), ``fwhm``,
``sigma_alpha_urad``, ``qoff_deg``, ``q_lo``, ``q_hi``, ``step`` (the median
Qz step), ``n_scan`` (points in the scan), ``seconds`` (the error, if it
failed: ``error``). ``summary.md``: counts and medians. ``log.txt``.
"""
import argparse
import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.getcwd())

from lss_core import absorbers, fresnel as F, series as sermod      # noqa: E402

COLS = ['spec', 'scan', 'label', 'energy_kev', 'qc', 'beta', 'roughness', 'n_points', 'n_below', 'n_above', 'qoff', 'qoff_err',
        'sigma_q', 'sigma_q_err', 'corr', 'chi2_dof', 'flags', 'qoff_sharp', 'qoff_sharp_err', 'qoff_err_counting',
        'sigma_q_err_counting', 'fwhm', 'sigma_alpha_urad', 'qoff_deg', 'q_lo', 'q_hi', 'step', 'n_scan', 'seconds',
        'error']


BELOW, ABOVE = 0.875, 1.2      # × Qc: row 13's selection (below 0.019, above 0.026 Å⁻¹ for water)


def crosses(qz, qc, below=BELOW, above=ABOVE):
    q = np.asarray(qz, float)
    q = q[np.isfinite(q)]
    return len(q) > 0 and q.min() < below * qc and q.max() > above * qc


def find_edges(spec, qc, below=BELOW, above=ABOVE):
    """(label, spec, scan) of every reflectivity scan of ``spec`` that crosses the edge."""
    import spec_routines
    from lss_core.experiment import Experiment
    s = spec_routines.specread(spec)
    exp = Experiment(spec)
    out = []
    for x in sermod.all_series(sermod.scan_info(s.Data, s.Par)):
        if x.kind != 'reflectivity':
            continue
        for n in x.data_scans:
            qz = exp.scans[n].columns.get('L')
            if qz is not None and crosses(qz, qc, below, above):
                out.append(('%s:%s' % (os.path.basename(spec), n), spec, int(n)))
    return out


def survey_scan(label, spec, scan, qc, sub, beta_scale, bootstrap, exps, roughness=0.0):
    from lss_core.experiment import Experiment
    t0 = time.time()
    row = dict(spec=os.path.basename(spec), scan=scan, label=label)
    exp = exps.get(spec) or exps.setdefault(spec, Experiment(spec))
    lam = exp.scans[scan].parameters.get('Wavelength')
    energy = absorbers.energy_kev(lam) if lam else 10.0
    beta = F.subphase_beta(sub, energy) * beta_scale
    d = np.asarray(exp.reflectivity([scan], errors='budget').per_scan[scan], float)
    q, r, s = d[:, 0], d[:, 1], d[:, 2]
    j = F.fit_edge_resolution(q, r, s, qc=qc, beta=beta, energy_kev=energy, bootstrap=bootstrap, roughness=roughness)
    p = F.propose_qoff(q, r, s, qc=qc, method='edge', bootstrap=bootstrap)
    row.update(energy_kev=energy, qc=qc, beta=beta, roughness=roughness, n_points=j.n_points, n_below=j.n_below, n_above=j.n_above,
               qoff=j.qoff if j.ok else None, qoff_err=j.qoff_err, sigma_q=j.sigma_q, sigma_q_err=j.sigma_q_err,
               corr=j.corr, chi2_dof=j.chi2_dof, flags=';'.join(j.flags) if j.ok else 'not fitted: ' + j.note,
               qoff_sharp=p.qoff if p.ok else None, qoff_sharp_err=p.sigma, qoff_err_counting=j.qoff_err_counting,
               sigma_q_err_counting=j.sigma_q_err_counting, fwhm=j.fwhm if j.ok else None,
               sigma_alpha_urad=j.sigma_alpha_urad if j.ok else None, qoff_deg=j.qoff_deg if j.ok else None,
               q_lo=float(np.nanmin(q)), q_hi=float(np.nanmax(q)), step=float(np.median(np.diff(np.sort(q)))),
               n_scan=len(q), seconds=round(time.time() - t0, 2), error='')
    return row


def write_csv(path, rows, cols=None):
    if not rows:
        return
    cols = cols or list(dict.fromkeys(k for r in rows for k in r))
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def summary(rows, out):
    ok = [r for r in rows if r.get('qoff') is not None and not r.get('error')]
    med = lambda k: float(np.nanmedian([float(r[k]) for r in ok if r.get(k) is not None])) if ok else float('nan')
    lines = ['# Qoff and the Qz resolution at the edge: survey', '',
             '%d scans, %d fitted, %d flagged, %d failed.' % (
                 len(rows), len(ok), sum(1 for r in ok if r['flags']), sum(1 for r in rows if r.get('error'))), '',
             '| median | value |', '|---|---|',
             '| Qoff (joint) | %.3g Å⁻¹ |' % med('qoff'), '| Qoff (sharp, today) | %.3g Å⁻¹ |' % med('qoff_sharp'),
             '| σ_Q | %.3g Å⁻¹ |' % med('sigma_q'), '| FWHM | %.3g Å⁻¹ |' % med('fwhm'),
             '| σ_α | %.3g µrad |' % med('sigma_alpha_urad'), '| χ²/dof | %.3g |' % med('chi2_dof'),
             '| corr(Qoff, σ_Q) | %.2f |' % med('corr')]
    with open(out, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', action='append', default=[])
    ap.add_argument('--list')
    ap.add_argument('--out', required=True)
    ap.add_argument('--subphase', default='water', help='a name of lss_core.fresnel.SUBPHASES')
    ap.add_argument('--qc', type=float, default=None, help='Qc (Å⁻¹); default: the subphase\'s')
    ap.add_argument('--beta-scale', type=float, default=1.0)
    ap.add_argument('--bootstrap', type=int, default=200)
    ap.add_argument('--below', type=float, default=BELOW, help='× Qc: a scan must start below this')
    ap.add_argument('--above', type=float, default=ABOVE, help='× Qc: and reach above this')
    ap.add_argument('--roughness', type=float, default=0.0, help='Å, a fixed Névot–Croce roughness in R_F (0: none)')
    a = ap.parse_args(argv)
    repo = os.path.abspath(os.getcwd())
    out = os.path.abspath(a.out)
    public = all(os.path.abspath(s).startswith(os.path.join(repo, 'sample_data', 'NX_school')) for s in a.spec) \
        and not a.list
    if out.startswith(repo) and not public and not out.startswith(os.path.join(repo, 'sample_data', 'private')):
        sys.exit('private data: --out must be under sample_data/private/ or outside the repository')
    sub = F.subphase(a.subphase)
    qc = sub.qc if a.qc is None else a.qc
    os.makedirs(out, exist_ok=True)
    scans, log = [], []
    for s in a.spec:
        try:
            scans += find_edges(s, qc, a.below, a.above)
        except Exception as e:
            log.append('%s: not read: %s: %s' % (s, type(e).__name__, e))
    if a.list:
        with open(a.list) as f:
            for line in csv.reader(f):
                if line and not line[0].startswith('#'):
                    n = int(line[1])
                    scans.append((line[2] if len(line) > 2 else '%s:%d' % (os.path.basename(line[0]), n), line[0], n))
    rows, exps = [], {}
    for label, spec, n in scans:
        try:
            rows.append(survey_scan(label, spec, n, qc, sub, a.beta_scale, a.bootstrap, exps, a.roughness))
        except Exception as e:
            rows.append(dict(spec=os.path.basename(spec), scan=n, label=label, error='%s: %s' % (type(e).__name__, e)))
            log.append('%s: failed: %s: %s' % (label, type(e).__name__, e))
    write_csv(os.path.join(out, 'edges.csv'), rows, COLS)
    summary(rows, os.path.join(out, 'summary.md'))
    with open(os.path.join(out, 'log.txt'), 'w') as f:
        f.write('\n'.join(log) + '\n')
    print('%d edge scans; %s' % (len(rows), '; '.join(log) if log else 'no failures'))
    return rows


if __name__ == '__main__':
    main()
