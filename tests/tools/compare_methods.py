"""Old and new methods side by side, as CSV files for figures
(docs/COMPARISONS.md; owner, 2026-11-19).

    python tests/tools/compare_methods.py                        # NX school, into docs/comparisons_data/
    python tests/tools/compare_methods.py --out DIR --spec FILE --ref 6,7,8,9 --gid "11;11,12"

Every CSV has a header line naming the comparison (C-number in
COMPARISONS.md), the method, the data set and the columns with units; and
``manifest.json`` lists them all with the command that made them. Uses
only the scripting API (lss_core.experiment), i.e. the same code as the
window. Private data (sample_data/bu, sample_data/private): pass --out to
a folder outside the repository; never commit what it writes.

Comparisons written:
- C2/C3 error models on a reflectivity: Qz, R, σ for legacy, budget
  (Gaussian 0.04 %, default) and budget (Student t); the values are the
  same to < 5e-6 relative, the errors differ.
- C10/C14 GID legacy 3-column patch vs pinhole geometry: Qxy and Qz
  integrals of each map, and each map (Qxy, Qz, I, σ) on its own grid
  (maps are large and not committed). On NX school use scan 11 alone for a
  like-for-like comparison: scan 12 stopped after 4 frames (2θ 13.4–15.8°),
  so the pinhole join keeps only that common range (IDL rule, F62) and the
  DPPC peak at 16.65° falls outside it, while the legacy join fills the
  rest with copies of scan 12's edge (P33).
- C11 pinhole distance: the pinhole map's Qxy integral at 258, 271 (header)
  and 280 mm, the range the distance fit gave on NX scan 11.
- C21 the pinhole map binned on exact per-pixel angles (the default) vs
  per-axis angles (the column's 2θ, the row's β: the method before
  2026-11-19), ``GIDParams(angles=...)``: Qxy and Qz integrals (written by
  hand once on 2026-11-20; by this tool since 2026-11-23).
- C6 absorber factor per setting n = 0…63 at 10 keV: nominal 1.4247^n vs
  calibrated foils, with the calibrated error.
"""
import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
NX = os.path.join('sample_data', 'NX_school', '2026sep', '20260923')


def _write(out, manifest, name, cid, method, data, columns, rows, note=''):
    path = os.path.join(out, name)
    head = ('%s | %s | data: %s | columns: %s%s' % (cid, method, data, ', '.join(columns),
                                                     (' | ' + note) if note else ''))
    np.savetxt(path, np.asarray(rows, float), delimiter=',', header=head, fmt='%.8e')
    manifest.append(dict(file=name, comparison=cid, method=method, data=data, columns=columns, note=note))


def reflectivity(exp, scans, label, out, manifest):
    models = (('legacy', None), ('budget_gaussian', {'mode': 'budget', 'kind': 'gaussian'}),
              ('budget_student_t', {'mode': 'budget', 'kind': 'student_t'}))
    for name, errors in models:
        r = exp.reflectivity(scans, errors=errors)
        _write(out, manifest, 'C2_ref_%s_%s.csv' % (label, name), 'C2/C3', 'error model: ' + name,
               '%s scans %s' % (label, scans), ['Qz (1/A)', 'R', 'sigma_R'], np.asarray(r.ref)[:, :3],
               'exp.reflectivity(%r, errors=%r)' % (scans, errors))


def gid(exp, scans, label, out, manifest, maps=True):
    label = '%s_S%s' % (label, '-'.join(map(str, scans)))
    from lss_core.gid import GIDParams
    for name, params in (('legacy', GIDParams(pinhole=False)), ('pinhole', GIDParams())):
        res = exp.gid(scans, params=params)
        prod = res.products('Q')
        call = 'exp.gid(%r, params=GIDParams(pinhole=%r)).products("Q")' % (scans, params.pinhole)
        _write(out, manifest, 'C10_gid_%s_%s_qxy.csv' % (label, name), 'C10/C14', 'GID ' + name,
               '%s scans %s' % (label, scans), ['Qxy (1/A)', 'I integrated over Qz', 'sigma'], prod['h'], call)
        _write(out, manifest, 'C10_gid_%s_%s_qz.csv' % (label, name), 'C10/C14', 'GID ' + name,
               '%s scans %s' % (label, scans), ['Qz (1/A)', 'I integrated over Qxy', 'sigma'], prod['v'], call)
        if maps:
            rows = np.column_stack([prod['x'].ravel(), prod['y'].ravel(), prod['data'].ravel(), prod['err'].ravel()])
            _write(out, manifest, 'C10_gid_%s_%s_map.csv' % (label, name), 'C10/C14', 'GID ' + name,
                   '%s scans %s' % (label, scans), ['Qxy (1/A)', 'Qz (1/A)', 'I', 'sigma'], rows,
                   call + '; NaN where the map has no data')
        if name == 'pinhole':
            for kind in ('exact', 'per_axis'):              # C21: the map's angles exact per pixel vs per axis
                p = exp.gid(scans, params=GIDParams(angles=kind)).products('Q')
                what = ('exact per-pixel angles (IMG_COO_CONV)' if kind == 'exact'
                        else 'per-axis angles (the method before 2026-11-19)')
                tag = kind.replace('_', '')
                _write(out, manifest, 'C21_gid_%s_pinhole_%s_qxy.csv' % (label, tag), 'C21', what,
                       '%s scans %s' % (label, scans), ['Qxy (1/A)', 'I integrated over Qz', 'sigma'], p['h'],
                       'GIDParams(angles=%r)' % kind)
                _write(out, manifest, 'C21_gid_%s_pinhole_%s_qz.csv' % (label, tag), 'C21', what,
                       '%s scans %s' % (label, scans), ['Qz (1/A)', 'I integrated over Qxy', 'sigma'], p['v'],
                       'GIDParams(angles=%r)' % kind)
            for d in (258.0, 271.0, 280.0):
                p = exp.gid(scans, params=GIDParams(pinhole_distance_mm=d)).products('Q')
                _write(out, manifest, 'C11_gid_%s_pinhole_%dmm_qxy.csv' % (label, d), 'C11',
                       'pinhole distance %g mm' % d, '%s scans %s' % (label, scans),
                       ['Qxy (1/A)', 'I integrated over Qz', 'sigma'], p['h'],
                       'GIDParams(pinhole_distance_mm=%g)' % d)


def absorbers(out, manifest):
    from lss_core import absorbers as ab
    cal = ab.calibrated(10.0)
    rows = []
    for n in range(64):
        k = ab.attenuation(cal, n)
        rel = cal.step(0, n)[1] if n else 0.0
        rows.append([n, ab.ABSFAC_10KEV ** n, k, k * rel])
    _write(out, manifest, 'C6_absorber_factors_10keV.csv', 'C6', 'nominal 50 um Al vs calibrated foils', '10 keV',
           ['n (#A)', 'nominal 1.4247^n', 'calibrated', 'calibrated sigma (low Qz)'], rows,
           'lss_core.absorbers.calibrated(10.0); step error from Foils.step(0, n)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=os.path.join('docs', 'comparisons_data'))
    ap.add_argument('--spec', default=NX)
    ap.add_argument('--label', default=None, help='data-set name in file names (default: from the SPEC file)')
    ap.add_argument('--ref', default='6,7,8,9', help='reflectivity scans ("" to skip)')
    ap.add_argument('--gid', default='11;11,12', help='GID scan sets, separated by ";" ("" to skip)')
    ap.add_argument('--no-maps', action='store_true', help='skip the 2D GID maps (large)')
    a = ap.parse_args()
    from lss_core.experiment import Experiment
    os.makedirs(a.out, exist_ok=True)
    label = a.label or ('nx' if os.path.abspath(a.spec) == os.path.abspath(NX) else os.path.basename(a.spec))
    exp = Experiment(a.spec)
    manifest = []
    if a.ref:
        reflectivity(exp, [int(s) for s in a.ref.split(',')], label, a.out, manifest)
    for group in filter(None, a.gid.split(';')):
        gid(exp, [int(s) for s in group.split(',')], label, a.out, manifest, maps=not a.no_maps)
    absorbers(a.out, manifest)
    path = os.path.join(a.out, 'manifest.json')
    if os.path.exists(path):                     # keep entries for files written otherwise
        mine = set(m['file'] for m in manifest)
        with open(path) as f:
            manifest += [m for m in json.load(f).get('files', [])
                         if m['file'] not in mine and os.path.exists(os.path.join(a.out, m['file']))]
    with open(path, 'w') as f:
        json.dump(dict(command=' '.join(['python', 'tests/tools/compare_methods.py'] + sys.argv[1:]),
                       spec=a.spec, files=manifest), f, indent=1)
    print('%d files in %s' % (len(manifest), a.out))


if __name__ == '__main__':
    main()
