"""Reflectivity patching methods compared on many data sets (owner,
2026-11-22: "prepare for later work by a third agent where they compare
methods with a larger dataset, like will be done with GID"). Plan and
judgement: docs/handoff_out/08-ref-patch-comparison.md; methods:
lss_core/patching.py, docs/reports/ref_patch_joint_fit.md.

    python tests/tools/ref_patch_survey.py --spec FILE [--spec FILE ...] --out DIR [--split] [--repeats]
    python tests/tools/ref_patch_survey.py --list sets.csv --out DIR [--split] [--repeats]

Run from the repository root. ``--spec`` finds the reflectivity series of a
SPEC file (lss_core.series, guessed or from series lines; scans with frames
only); ``--list`` gives them by hand (CSV lines ``spec,scans[,label]``,
scans separated by ';'). Every set is reduced once
(``Experiment.reflectivity(..., errors='budget')``) and every method run
at every join. Reads only. Private data: ``--out`` must be under
``sample_data/private/`` or outside the repository (checked).

Outputs: ``joins.csv`` (set × join × method), ``sets.csv`` (set × method),
``split.csv`` (``--split``: each scan of ≥ 20 points split into two
halves overlapping over 8 points, interleaved or shared, the second × 0.8:
known truth on real curves),
``repeats.csv`` (``--repeats``: repeated scans joined to the same scan),
``summary.md``. Column meanings: hand-off 08.
"""
import argparse
import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.getcwd())

from lss_core import absorbers, patching, reflectivity as refl, series as sermod, stitching     # noqa: E402
from lss_core import uncertainty as unc                                                          # noqa: E402
from lss_core.patching import Scan                                                               # noqa: E402

METHODS = {
    'legacy': dict(kind='legacy'),
    'interp': dict(kind='interp'),
    'interp_log': dict(kind='interp', log=True),
    'coincident': dict(kind='coincident'),
    'joint_o2_e0': dict(kind='joint', order=2, n_ext=0),
    'joint_o4_e2': dict(kind='joint', order=4, n_ext=2),
    'joint_o4_e4': dict(kind='joint', order=4, n_ext=4),
    'joint_o4_e4_raw': dict(kind='joint', order=4, n_ext=4, space='raw'),
    'joint_o4_e4_log': dict(kind='joint', order=4, n_ext=4, likelihood='log'),
}
PRIOR_METHOD = 'joint_o4_e4_prior'
JOIN_COLS = ['set', 'join', 'scan_a', 'scan_b', 'method', 'energy_kev', 'n_a', 'n_b', 'q_lo', 'q_hi', 'q_class',
             'points_a', 'points_b', 'coincident', 'n_ext', 'order', 'space', 'likelihood', 'window_reduced',
             'delta', 'factor', 'err', 'err_counting', 'chi2_dof', 'dof', 'p_chi2', 'd_legacy_sigma', 'known',
             'known_err', 'z_known', 'prior_used', 'why', 'monc_monp_ratio', 'flags', 'seconds', 'error']


def q_class(q):
    return '<0.05' if q < 0.05 else ('0.05-0.25' if q < 0.25 else '>=0.25')


def fit_join(a, b, spec):
    kind = spec['kind']
    kw = {k: v for k, v in spec.items() if k != 'kind'}
    if kind == 'legacy':
        f, e = stitching.fitted_factor(np.column_stack([a.q, a.y, a.sigma]), np.column_stack([b.q, b.y, b.sigma]))
        return patching.JoinFit(math.log(f), e / f, e / f, math.nan, 0, 0, 0, 'raw', 'ratio', 'legacy')
    if kind == 'interp':
        return patching.interp_factor(a, b, **kw)
    if kind == 'coincident':
        return patching.coincident_factor(a, b)
    return patching.joint_factor(a, b, **kw)


def reduce_set(spec, scans):
    from lss_core.experiment import Experiment
    exp = Experiment(spec)
    r = exp.reflectivity(scans, errors='budget')
    order = r.order
    out = patching.scans_from_reflectivity(r, order)
    meta = []
    for n, s in zip(order, out):
        p = exp.scans[n].parameters
        cols = exp.scans[n].columns
        s.absorber = p.get('Absorber')
        meta.append(dict(scan=n, energy=absorbers.energy_kev(p['Wavelength']) if p.get('Wavelength') else None,
                         monc=cols.get('Monc'), monp=cols.get('Monp'), qz=cols.get('L')))
    return exp, order, out, meta


def monitor_ratio(ma, mb):
    if ma['monp'] is None or mb['monp'] is None:
        return None
    return refl.monitor_change(ma['qz'], ma['monc'], ma['monp'], mb['qz'], mb['monc'], mb['monp'])


def survey_set(label, spec, scans, rows, set_rows, log):
    t0 = time.time()
    exp, order, sc, meta = reduce_set(spec, scans)
    energy = meta[0]['energy']
    foils = absorbers.calibrated(energy) if energy else None
    mr = [monitor_ratio(meta[m], meta[m + 1]) for m in range(len(sc) - 1)]
    results = {}
    for name, spec_m in METHODS.items():
        joins = []
        for m in range(1, len(sc)):
            a, b = sc[m - 1], sc[m]
            row = dict(set=label, join=m, scan_a=order[m - 1], scan_b=order[m], method=name, energy_kev=energy,
                       n_a=a.absorber, n_b=b.absorber, q_lo=float(b.q.min()), q_hi=float(a.q.max()),
                       q_class=q_class(float(b.q.min())), points_a=int(np.sum(a.q >= b.q.min() - 1e-9)),
                       points_b=int(np.sum(b.q <= a.q.max() + 1e-9)),
                       coincident=int(sum(np.any(np.abs(b.q - x) < 1e-6) for x in a.q)), monc_monp_ratio=mr[m - 1])
            t = time.time()
            try:
                j = fit_join(a, b, spec_m)
                if j is None:
                    raise ValueError('no coinciding points')
                row.update(n_ext=j.n_ext, order=j.order, space=j.space, likelihood=j.likelihood,
                           window_reduced=any('reduced' in f for f in j.flags), delta=j.delta, factor=j.factor,
                           err=j.err, err_counting=j.err_counting,
                           chi2_dof=j.chi2 / j.dof if j.dof else math.nan, dof=j.dof, p_chi2=j.p_chi2 if j.dof else math.nan,
                           flags='; '.join(j.flags))
                joins.append(j)
            except Exception as e:                    # recorded, the survey goes on
                row['error'] = '%s: %s' % (type(e).__name__, e)
                joins.append(None)
            if foils is not None and a.absorber is not None and b.absorber is not None:
                ratio, rel = foils.step(a.absorber, b.absorber, qz=row['q_lo'])
                row.update(known=ratio, known_err=rel)
                if joins[-1] is not None and rel > 0:
                    row['z_known'] = (joins[-1].delta - math.log(ratio)) / math.hypot(joins[-1].err, rel)
            row['seconds'] = round(time.time() - t, 4)
            rows.append(row)
        results[name] = joins
    # the prior variant of the default method, and the legacy differences
    if foils is not None and all(s.absorber is not None for s in sc):
        try:
            prior = patching.known_steps(foils, [s.absorber for s in sc], [s.q.min() for s in sc[1:]])
            res = patching.chain(sc, prior=prior, monitor_ratios=mr)
            for m, j in enumerate(res.joins, start=1):
                rows.append(dict(set=label, join=m, scan_a=order[m - 1], scan_b=order[m], method=PRIOR_METHOD,
                                 delta=float(res.steps[m - 1]), factor=math.exp(res.steps[m - 1]),
                                 err=float(math.sqrt(res.C_steps[m - 1, m - 1])), prior_used=j.prior_used, why=j.why,
                                 z_known=j.z, monc_monp_ratio=mr[m - 1], q_class=q_class(float(sc[m].q.min()))))
            results[PRIOR_METHOD] = res
        except Exception as e:
            log.append('%s: prior variant failed: %s' % (label, e))
    leg = {r['join']: r for r in rows if r['set'] == label and r['method'] == 'legacy' and 'delta' in r}
    for r in rows:
        if r['set'] == label and r.get('delta') is not None and r['join'] in leg and r.get('err'):
            r['d_legacy_sigma'] = (r['delta'] - leg[r['join']]['delta']) / r['err']
    for name, joins in results.items():
        if isinstance(joins, patching.PatchResult):
            phi, S = joins.phi, joins.Sigma
        elif all(j is not None for j in joins):
            phi, S = unc.steps_to_phi([j.delta for j in joins], np.diag([j.err ** 2 for j in joins]))
        else:
            set_rows.append(dict(set=label, method=name, scans=';'.join(map(str, order)), K=len(sc), error='a join failed'))
            continue
        st = patching.PatchResult(phi, S, [], name).stitch(sc)
        set_rows.append(dict(set=label, method=name, scans=';'.join(map(str, order)), K=len(sc),
                             phi=';'.join('%.6g' % v for v in phi),
                             sqrt_sigma=';'.join('%.4g' % v for v in np.sqrt(np.diag(S))),
                             sqrt_sigma_last=float(np.sqrt(S[-1, -1])),
                             max_total_over_meas=float(np.max(st.sigma_total() / st.sigma_meas)),
                             flagged=sum(1 for j in (joins.joins if isinstance(joins, patching.PatchResult) else joins)
                                         if j is not None and j.flags)))
    log.append('%s: %d scans, %.1f s' % (label, len(sc), time.time() - t0))
    return sc, order


def split_rows(label, sc, order, out):
    """Each scan of ≥ 20 points split into two halves that overlap over 8
    points, the second half's values × 0.8 (truth: f = 1.25), real curve
    shape, noise and background. ``interleaved``: the overlap's points go
    alternately to a and b, so the halves have independent noise on a
    staggered grid: bias **and** pulls are meaningful. ``shared``: both
    halves hold the same overlap points (the same noise): only the bias
    is meaningful (a method that compares the points directly is exact)."""
    for n, s in zip(order, sc):
        if len(s.q) < 20:
            continue
        h = len(s.q) // 2
        ov = np.arange(h - 4, h + 4)
        for variant in ('interleaved', 'shared'):
            if variant == 'interleaved':
                ia = np.concatenate([np.arange(0, h - 4), ov[0::2]])
                ib = np.concatenate([ov[1::2], np.arange(h + 4, len(s.q))])
            else:
                ia = np.arange(0, h + 4)
                ib = np.arange(h - 4, len(s.q))
            a = Scan(s.q[ia], s.y[ia], s.sigma[ia])
            b = Scan(s.q[ib], 0.8 * s.y[ib], 0.8 * s.sigma[ib])
            for name, spec_m in METHODS.items():
                row = dict(set=label, scan=n, variant=variant, method=name, truth=1.25)
                try:
                    j = fit_join(a, b, spec_m)
                    if j is None:
                        raise ValueError('no coinciding points')
                    row.update(factor=j.factor, err=j.err, pull=(j.delta - math.log(1.25)) / j.err if j.err else math.nan,
                               chi2_dof=j.chi2 / j.dof if j.dof else math.nan)
                except Exception as e:
                    row['error'] = '%s: %s' % (type(e).__name__, e)
                out.append(row)


def repeat_rows(label, spec, exp_scans, out):
    """Where a scan was repeated (identical Qz points), each repeat joined to
    the scan before it: the two factors' difference against their errors."""
    from lss_core.experiment import Experiment
    exp = Experiment(spec)
    r = exp.reflectivity(exp_scans, errors='budget')
    for group in refl.identical_groups(r.per_scan):
        g = sorted(group)
        before = [n for n in r.order if n not in g and n < min(g)]
        if not before:
            continue
        prev = before[-1]
        a = patching.scans_from_reflectivity(r, [prev])[0]
        reps = patching.scans_from_reflectivity(r, g)
        for name, spec_m in METHODS.items():
            try:
                js = [fit_join(a, b, spec_m) for b in reps]
                d = js[1].delta - js[0].delta
                out.append(dict(set=label, scan_a=prev, repeats=';'.join(map(str, g)), method=name, d=d,
                                err=math.hypot(js[0].err, js[1].err), pull=d / math.hypot(js[0].err, js[1].err)))
            except Exception as e:
                out.append(dict(set=label, scan_a=prev, repeats=';'.join(map(str, g)), method=name,
                                error='%s: %s' % (type(e).__name__, e)))


def find_sets(spec):
    import spec_routines
    s = spec_routines.specread(spec)
    out = []
    for x in sermod.all_series(sermod.scan_info(s.Data, s.Par)):
        if x.kind == 'reflectivity' and len(x.data_scans) >= 2:
            out.append(('%s:%s' % (os.path.basename(spec), x.data_scans[0]), spec, list(x.data_scans)))
    return out


def write_csv(path, rows, cols=None):
    if not rows:
        return
    cols = cols or sorted({k for r in rows for k in r})
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def summary(rows, split, out):
    lines = ['# Reflectivity patching survey', '', '| method | joins | median err | median χ²/dof | flagged |', '|---|---|---|---|---|']
    for name in list(METHODS) + [PRIOR_METHOD]:
        r = [x for x in rows if x['method'] == name and x.get('delta') is not None]
        if not r:
            continue
        err = np.median([x['err'] for x in r])
        c2 = [x['chi2_dof'] for x in r if x.get('chi2_dof') is not None and np.isfinite(x['chi2_dof'])]
        lines.append('| %s | %d | %.3g | %s | %d |' % (name, len(r), err, '%.2f' % np.median(c2) if c2 else '',
                                                    sum(1 for x in r if x.get('flags'))))
    if split:
        lines += ['', '## Split truth (f = 1.25; pull SD meaningful for interleaved only)', '',
                  '| method | variant | n | bias | pull SD |', '|---|---|---|---|---|']
        for name in METHODS:
            for v in ('interleaved', 'shared'):
                r = [x for x in split if x['method'] == name and x['variant'] == v and x.get('factor')]
                if r:
                    p = unc.pulls([math.log(x['factor']) for x in r], math.log(1.25), [x['err'] for x in r])
                    lines.append('| %s | %s | %d | %.4f | %.2f |' % (name, v, p['n'], p['bias'], p['pull_sd']))
    with open(out, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', action='append', default=[])
    ap.add_argument('--list')
    ap.add_argument('--out', required=True)
    ap.add_argument('--split', action='store_true')
    ap.add_argument('--repeats', action='store_true')
    a = ap.parse_args(argv)
    repo = os.path.abspath(os.getcwd())
    out = os.path.abspath(a.out)
    public = all(os.path.abspath(s).startswith(os.path.join(repo, 'sample_data', 'NX_school')) for s in a.spec) and not a.list
    if out.startswith(repo) and not public and not out.startswith(os.path.join(repo, 'sample_data', 'private')):
        sys.exit('private data: --out must be under sample_data/private/ or outside the repository')
    os.makedirs(out, exist_ok=True)
    sets = []
    for s in a.spec:
        sets += find_sets(s)
    if a.list:
        with open(a.list) as f:
            for line in csv.reader(f):
                if line and not line[0].startswith('#'):
                    scans = [int(x) for x in line[1].replace(',', ';').split(';') if x.strip()]
                    sets.append((line[2] if len(line) > 2 else '%s:%d' % (os.path.basename(line[0]), scans[0]), line[0], scans))
    rows, set_rows, split, reps, log = [], [], [], [], []
    for label, spec, scans in sets:
        try:
            sc, order = survey_set(label, spec, scans, rows, set_rows, log)
            if a.split:
                split_rows(label, sc, order, split)
            if a.repeats:
                repeat_rows(label, spec, scans, reps)
        except Exception as e:
            log.append('%s: failed: %s: %s' % (label, type(e).__name__, e))
    write_csv(os.path.join(out, 'joins.csv'), rows, JOIN_COLS)
    write_csv(os.path.join(out, 'sets.csv'), set_rows)
    write_csv(os.path.join(out, 'split.csv'), split)
    write_csv(os.path.join(out, 'repeats.csv'), reps)
    summary(rows, split, os.path.join(out, 'summary.md'))
    with open(os.path.join(out, 'log.txt'), 'w') as f:
        f.write('\n'.join(log) + '\n')
    print('\n'.join(log))


if __name__ == '__main__':
    main()
