"""Survey of the GID patching methods over many data sets (owner, 2026-11-21:
"commit your comparison work such that another agent can pick up what you
were doing with a much larger dataset for a final judgment"). Hand-off:
docs/handoff_out/06-gid-method-comparison.md.

    python tests/tools/gid_method_survey.py --spec FILE [--spec FILE ...] --out DIR
    python tests/tools/gid_method_survey.py --list sets.csv --out DIR      # spec,scans[,label[,peak]]
    python tests/tools/gid_method_survey.py --spec sample_data/NX_school/2026sep/20260923 \\
        --out docs/comparisons_data/gid_survey_nx                       # the public example

A GID set is one inferred GID series of a SPEC file (``lss_core.series.
infer``: consecutive ``ascan dth`` scans with images), reduced to the scans
whose frames are on disk; ``--list`` gives sets by hand. For every set:

1. every method (legacy; pinhole with response fit, beam, physical,
   physical+fit, none; joins applied), at the header S4–detector distance;
2. the single-frame distance calibration of each Qz level
   (``pinhole.calibrate_distance``: the strongest peak that single frames
   fit, the distance where they agree);
3. at the calibrated distance (first reliable level), the pinhole methods
   again, and the peak of the patched map against the single frames
   (centre and width: the unpatched frames are the ground truth);
4. with ``--split``: each level of one scan with at least 30 frames split
   into two overlapping scans, the second's counts × 0.8, and the scale
   each method recovers (true 1.25).

Writes, in DIR: ``methods.csv`` (one row per set, distance, method, level:
frames-agree χ²/dof, counts used, beam found), ``joins.csv`` (one row per
fitted join: kind, factor, error, χ²/dof), ``calibration.csv`` (one row per
set and level), ``truth.csv`` (patched peak vs single frames), ``split.csv``
and ``summary.md`` (per set: the method with the lowest frames-agree χ²/dof
per level, the calibrated distances). Column meanings: the hand-off.

Private data: DIR must be under sample_data/private/ or outside the
repository (checked). Runs headless; about 2–4 min per set.
"""
import argparse
import csv
import dataclasses
import math
import os
import sys
import time
import traceback

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")          # headless (SPEC reader needs a QApplication)
ROOT = os.getcwd()
sys.path.insert(0, ROOT)
from lss_core import gid as gm, pinhole as ph, series            # noqa: E402
from lss_core.experiment import Experiment                       # noqa: E402

METHODS = [('legacy', dict(pinhole=False)), ('fit', dict(response='fit')), ('beam', dict(response='beam')),
           ('physical', dict(response='physical')), ('physical+fit', dict(response='physical+fit')),
           ('none', dict(response='none'))]
PEAK_HALF = 0.4
PEAK_BETA = (-0.1, 2.0)


def _guard(specs, out):
    o = os.path.abspath(out)
    private = any(os.path.join(ROOT, 'sample_data', p) in os.path.abspath(s) for s in specs for p in ('private', 'bu'))
    safe = os.path.join(ROOT, 'sample_data', 'private')
    if private and (o == ROOT or o.startswith(ROOT + os.sep)) and not o.startswith(safe + os.sep):
        sys.exit('Private data: --out must be under sample_data/private/ or outside the repository.')


def discover(spec):
    """GID sets of a SPEC file: inferred GID series, scans with frames only."""
    from PyQt5.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import spec_routines
    s = spec_routines.specread(spec)
    e = Experiment(spec)
    sets = []
    for x in series.infer(series.scan_info(s.Data, s.Par)):
        if x.kind != 'gid':
            continue
        have = []
        for num in sorted(x.scans.values()):
            try:
                e.gid_frames([num])
                have.append(num)
            except Exception:
                pass
        if have:
            sets.append(dict(spec=spec, scans=have, label='%s S%s' % (os.path.basename(spec), '+'.join(map(str, have))),
                             peak=None))
    return sets


def read_list(path):
    sets = []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith('#'):
                continue
            spec, scans = row[0].strip(), [int(v) for v in row[1].replace(';', ',').split(',') if v.strip()]
            label = row[2].strip() if len(row) > 2 and row[2].strip() else '%s S%s' % (os.path.basename(spec), '+'.join(map(str, scans)))
            peak = float(row[3]) if len(row) > 3 and row[3].strip() else None
            sets.append(dict(spec=spec, scans=scans, label=label, peak=peak))
    return sets


def peak_of_map(r, peak, half=PEAK_HALF, beta=PEAK_BETA):
    """(centre, error, FWHM) of the peak in a patched map (rows summed over β)."""
    from scipy.optimize import curve_fit
    x, y, d, s = map(np.asarray, (r.x, r.y, r.data, r.err))
    ax = 0 if np.allclose(x[:, 0], x[:, -1]) else 1
    tt = x[:, 0] if ax == 0 else x[0]
    b = (y >= beta[0]) & (y <= beta[1])
    prof = np.nansum(np.where(b & np.isfinite(d), d, 0), axis=1 - ax)
    pe = np.sqrt(np.nansum(np.where(b & np.isfinite(s), s ** 2, 0), axis=1 - ax))
    sel = (tt > peak - half) & (tt < peak + half) & (pe > 0)
    if sel.sum() < 8:
        return None
    try:
        p, c = curve_fit(ph._gauss_line, tt[sel], prof[sel], sigma=pe[sel], maxfev=20000,
                         p0=[prof[sel].max() - np.median(prof[sel]), peak, 0.06, np.median(prof[sel]), 0.0])
    except (RuntimeError, ValueError):
        return None
    return float(p[1]), float(math.sqrt(max(c[1][1], 0))), float(2.3548 * abs(p[2]))


def run_methods(e, st, distance, rows_m, rows_j, tag):
    for name, kw in METHODS:
        if distance and name == 'legacy':
            continue                                   # the legacy patch does not use the distance
        t = time.time()
        try:
            r = e.gid(st['scans'], params=gm.GIDParams(pinhole_distance_mm=distance, **kw), axes='Angles')
        except Exception as ex:
            rows_m.append(dict(set=st['label'], distance=tag, method=name, level='', error=repr(ex)[:200]))
            continue
        dt = time.time() - t
        levels = (r.info or {}).get('levels') or [None] * len(r.levels)
        for k, (lv, inf) in enumerate(zip(r.levels, levels)):
            phys = (inf or {}).get('physical') or {}
            rows_m.append(dict(set=st['label'], distance=tag, method=name, level=k + 1, scans='+'.join(map(str, lv[1])),
                               frames=lv[2], two_theta_from=round(lv[3], 4), two_theta_to=round(lv[4], 4),
                               consistency_chi2=(inf or {}).get('consistency_chi2', ''),
                               counts_used=(inf or {}).get('counts_used', ''),
                               beam_centre_mm=phys.get('centre_mm', ''), beam_fwhm_um=phys.get('fwhm_um', ''),
                               beam_fit_chi2=phys.get('chi2_dof', ''), seconds=round(dt, 1), error=''))
        for j in r.joins:
            rows_j.append(dict(set=st['label'], distance=tag, method=name, label=j['label'], kind=j['kind'],
                               x_from=round(j['x_from'], 4), x_to=round(j['x_to'], 4), points=j['points'],
                               factor=j['factor'], error=j['error'], chi2=j['chi2']))
        yield name, r


def split_test(e, st, rows_s):
    frames, det = e.gid_frames(st['scans'])
    levels = gm.pinhole_frames(frames, gm.GIDParams())
    for k, lv in enumerate(levels):
        scans = sorted({f.scan for f in lv})
        if len(scans) != 1 or len(lv) < 30:
            continue
        sub = [f for f in frames if f.scan == scans[0]]       # the level's one scan, in measured order
        n = len(sub)
        a, b0 = sub[:n // 2 + 1], sub[n // 2 - 5:]          # two halves sharing six frames, as the NX test

        def mk(s):
            return a + [dataclasses.replace(f, scan=f.scan + 100000, data=np.asarray(f.data, float) * s,
                                            error=np.asarray(f.error, float) * s) for f in b0]
        for name, kw in METHODS:
            fs = []
            for s in (1.0, 0.8):
                log = []
                try:
                    if name == 'legacy':
                        gm.legacy_patch(mk(s), gm.GIDParams(pinhole=False), det, log=log)
                    else:
                        gm.pinhole_patch(mk(s), gm.GIDParams(**kw), log=log)
                except Exception:
                    fs = None
                    break
                h = [x for x in log if x.get('kind') == 'horizontal (2theta)']
                fs.append(h[0]['factor'] if h else float('nan'))
            rows_s.append(dict(set=st['label'], level=k + 1, method=name, halves=fs[0] if fs else '',
                               recovered=(fs[1] / fs[0]) if fs else '', true=1.25))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', action='append', default=[])
    ap.add_argument('--list', help='CSV: spec,scans[,label[,peak]]; scans separated by ; or ,')
    ap.add_argument('--out', required=True)
    ap.add_argument('--split', action='store_true', help='also the scale-recovery test on long single-scan levels')
    ap.add_argument('--no-calibration', action='store_true')
    a = ap.parse_args()
    sets = read_list(a.list) if a.list else []
    for spec in a.spec:
        sets += discover(spec)
    _guard([s['spec'] for s in sets], a.out)
    os.makedirs(a.out, exist_ok=True)
    rows_m, rows_j, rows_c, rows_t, rows_s = [], [], [], [], []
    for st in sets:
        print('set %s (%d scans)' % (st['label'], len(st['scans'])), flush=True)
        try:
            e = Experiment(st['spec'])
            list(run_methods(e, st, 0.0, rows_m, rows_j, 'header'))
            cal_d, cal_level = None, 0
            if not a.no_calibration:
                frames, _ = e.gid_frames(st['scans'])
                for k, lv in enumerate(gm.pinhole_frames(frames, gm.GIDParams())):
                    try:
                        c = ph.calibrate_distance(lv, peak_deg=st['peak'])
                        rows_c.append(dict(set=st['label'], level=k + 1, distance_mm=c.distance_mm, error_mm=c.error_mm,
                                           header_mm=c.header_mm, reliable=c.reliable, why=c.why, peak_deg=c.peak_deg,
                                           frames=c.frames, chi2_dof=c.chi2_dof, drift=c.drift,
                                           chi2_dof_header=c.chi2_dof_header, drift_header=c.drift_header,
                                           centre_deg=c.centre_deg, fwhm_deg=c.fwhm_deg))
                        if c.reliable and cal_d is None:
                            cal_d, cal_level = c, k
                    except ValueError as ex:
                        rows_c.append(dict(set=st['label'], level=k + 1, reliable=False, why=str(ex)))
            if cal_d is not None:
                list(run_methods(e, st, round(cal_d.distance_mm, 1), rows_m, rows_j, 'calibrated'))
                levels = gm.pinhole_frames(e.gid_frames(st['scans'])[0], gm.GIDParams())
                lv0 = levels[cal_level]
                lscans = sorted({f.scan for f in lv0})              # the calibrated level's own map: a joined
                for tag, dist in (('header', None), ('calibrated', cal_d.distance_mm)):   # map is cut to the
                    sf = ph.single_frame_peaks(lv0, cal_d.peak_deg, PEAK_HALF, cal_d.rows, dist)  # levels' common 2θ
                    if len(sf) < 3:
                        continue
                    m, me, chi, drift, fw = ph.frames_agree(sf)
                    for name, kw in METHODS:
                        r = e.gid(lscans, params=gm.GIDParams(pinhole_distance_mm=round(dist, 1) if dist else 0.0, **kw),
                                  axes='Angles')
                        pk = peak_of_map(r, cal_d.peak_deg)
                        rows_t.append(dict(set=st['label'], level=cal_level + 1, distance=tag, method=name, single_centre=m,
                                           single_centre_err=me, single_fwhm=fw, single_chi2=chi, single_frames=len(sf),
                                           patched_centre=pk[0] if pk else '', patched_centre_err=pk[1] if pk else '',
                                           patched_fwhm=pk[2] if pk else '',
                                           width_ratio=(pk[2] / fw) if pk else ''))
            if a.split:
                split_test(e, st, rows_s)
        except Exception:
            traceback.print_exc()
    for name, rows in (('methods', rows_m), ('joins', rows_j), ('calibration', rows_c), ('truth', rows_t),
                       ('split', rows_s)):
        if not rows:
            continue
        keys = []
        for r in rows:
            keys += [k for k in r if k not in keys]
        with open(os.path.join(a.out, name + '.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, keys)
            w.writeheader()
            w.writerows(rows)
    with open(os.path.join(a.out, 'summary.md'), 'w') as f:
        f.write('# GID method survey\n\nMade by `tests/tools/gid_method_survey.py`; columns: '
                '`docs/handoff_out/06-gid-method-comparison.md`.\n\n')
        f.write('| set | level | lowest frames-agree χ²/dof (header distance) | calibrated distance |\n|---|---|---|---|\n')
        for st in sets:
            lv = sorted({r['level'] for r in rows_m if r['set'] == st['label'] and r.get('level')})
            for k in lv:
                cand = [(r['consistency_chi2'], r['method']) for r in rows_m
                        if r['set'] == st['label'] and r.get('level') == k and r['distance'] == 'header'
                        and r.get('consistency_chi2') not in ('', None)]
                best = min(cand) if cand else None
                cal = [r for r in rows_c if r['set'] == st['label'] and r['level'] == k]
                calt = ('%.1f ± %.1f mm%s' % (cal[0]['distance_mm'], cal[0]['error_mm'], '' if cal[0]['reliable'] else ' (unreliable)')
                        if cal and 'distance_mm' in cal[0] else (cal[0]['why'] if cal else ''))
                f.write('| %s | %d | %s | %s |\n' % (st['label'], k, '%s %.2f' % (best[1], best[0]) if best else '—', calt))
    print('wrote', a.out)


if __name__ == '__main__':
    main()
