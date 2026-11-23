"""What does the SPEC "Epoch" column measure?

Run from the repository root:  python3 tests/tools/spec_epoch.py [specfile ...]

For every scan: (Epoch of the first point) - (scan header time #D - file
time #E). If Epoch were seconds since the file's #E this would be a small
constant (the time to take the first point), plus the local-time offset of
#D, which is written without a zone.
"""
import calendar
import glob
import sys
import time

import numpy as np


def analyse(path):
    file_epoch, n_e, scans, cur, cols = None, 0, [], None, None
    with open(path) as f:
        for line in f:
            if line.startswith('#E'):
                file_epoch, n_e = int(line.split()[1]), n_e + 1
            elif line.startswith('#S '):
                cur = {'n': int(line.split()[1]), 'D': None, 'ep': []}
                scans.append(cur)
                cols = None
            elif line.startswith('#D') and cur is not None and cur['D'] is None:
                cur['D'] = calendar.timegm(time.strptime(line[3:].strip(),
                                                         '%a %b %d %H:%M:%S %Y'))
            elif line.startswith('#L') and cur is not None:
                cols = line[3:].split()
            elif cur is not None and cols and 'Epoch' in cols and line[:1] not in '#\n':
                v = line.split()
                if len(v) == len(cols):
                    try:
                        cur['ep'].append(float(v[cols.index('Epoch')]))
                    except ValueError:
                        pass
    rows = [(s['n'], s['ep'][0] - (s['D'] - file_epoch)) for s in scans
            if s['ep'] and s['D']]
    off = np.array([r[1] for r in rows])
    zone = 3600 * np.round(np.median(off) / 3600)
    odd = [(n, int(o - zone)) for n, o in rows if abs(o - zone) > 60]
    near = [o - zone for o in off if abs(o - zone) <= 60]
    lag = ('%d..%d s' % (min(near), max(near))) if near else 'n/a'
    print('%-44s #E lines %d, %3d scans; zone offset %+d h; '
          'first point lags header by %s in %d scans; other scans '
          '(scan, seconds off): %s'
          % (path[-44:], n_e, len(rows), zone / 3600, lag,
             len(rows) - len(odd), odd[:5] or 'none'))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='What the SPEC "Epoch" column measures.')
    ap.add_argument('specs', nargs='*', help='SPEC files (default: NX school and, when present, the private '
                                             'bu files under sample_data/bu)')
    a = ap.parse_args(argv)
    targets = a.specs or (['sample_data/NX_school/2026sep/20260923']
                          + sorted(glob.glob('sample_data/bu/*/2026*')))
    for t in targets:
        analyse(t)
    return 0


if __name__ == '__main__':
    sys.exit(main())
