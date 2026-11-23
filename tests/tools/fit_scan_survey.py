"""The scan-shape fit (lss_core.peaks.fit_scan, what the SpecPlot shows)
on every (scan, column) of a SPEC file, as CSV (C37 in docs/COMPARISONS.md).

    python tests/tools/fit_scan_survey.py                          # NX school, new rules
    python tests/tools/fit_scan_survey.py --old                    # before 2026-11-23: no flat test, 20000 evaluations
    python tests/tools/fit_scan_survey.py --spec FILE --out FILE.csv

x is the scan's first column (the motor), y each other column with at least
8 finite, non-constant points; errors √|y| as the window gives them when it
does not normalise; for a sample-height scan the height rules
(``peaks.height_scan_options``), as the window applies them. Columns: scan, column, points, kind (peak, edge, box,
flat, weak, or '' when nothing fitted), centre, fwhm, height, χ²/dof of the
background alone, seconds. Private data: write outside the repository.
"""
import argparse
import csv
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from lss_core import peaks  # noqa: E402
from lss_core.experiment import Experiment  # noqa: E402

HEIGHT_RULES = True
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


def survey(spec):
    rows = []
    for n, sc in Experiment(spec).scans.items():
        cols = list(sc.columns)
        if not cols:
            continue
        x = np.asarray(sc.columns[cols[0]], float)
        if len(x) < 8 or np.ptp(x) == 0:
            continue
        for c in cols[1:]:
            y = np.asarray(sc.columns[c], float)
            if len(y) != len(x) or not np.all(np.isfinite(y)) or np.ptp(y) == 0:
                continue
            e = np.sqrt(np.abs(y))
            e = e if np.all(e > 0) else None
            _, chi2, dof = peaks.is_flat(x, y, peaks.noise_sigma(y, e))
            t = time.perf_counter()
            kw = peaks.height_scan_options() if (HEIGHT_RULES and peaks.is_height_scan(sc.command)) else {}
            res = peaks.fit_scan(x, y, e, **kw)
            secs = time.perf_counter() - t
            p = res.peaks[0] if res.peaks else None
            rows.append([n, c, len(x), getattr(res, 'kind', '') if (res.ok or getattr(res, 'kind', '') in ('flat', 'weak')) else '',
                         '' if p is None else repr(p.centre), '' if p is None else repr(p.fwhm),
                         '' if p is None else repr(p.height), '%.4g' % (chi2 / dof), '%.3f' % secs])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--spec', default=NX)
    ap.add_argument('--out', default=None, help='CSV file (default docs/comparisons_data/C37_fit_scan_<old|new>_nx.csv)')
    ap.add_argument('--old', action='store_true', help='the rules before 2026-11-23')
    a = ap.parse_args(argv)
    if a.old:
        global HEIGHT_RULES
        HEIGHT_RULES = False
        peaks.FLAT_P = 2.0                 # a p-value never exceeds it: nothing is flat
        peaks.SHAPE_FIT_MAX_NFEV = 20000
    out = a.out or os.path.join(ROOT, 'docs', 'comparisons_data',
                                'C37_fit_scan_%s_nx.csv' % ('old' if a.old else 'new'))
    rows = survey(a.spec)
    with open(out, 'w', newline='') as f:
        f.write('# C37 scan-shape fit (lss_core.peaks.fit_scan), %s rules, %s; x = first column, height rules on sh scans (new), '
                'errors sqrt|y|; chi2dof_background = the background alone; seconds = wall time\n'
                % ('old (no flat test, 20000 evaluations)' if a.old else 'new (flat test p > %g, %d evaluations)'
                   % (peaks.FLAT_P, peaks.SHAPE_FIT_MAX_NFEV), os.path.relpath(a.spec, ROOT)))
        w = csv.writer(f)
        w.writerow(['scan', 'column', 'points', 'kind', 'centre', 'fwhm', 'height', 'chi2dof_background', 'seconds'])
        w.writerows(rows)
    print('%d fits, %.1f s in fit_scan -> %s' % (len(rows), sum(float(r[-1]) for r in rows), out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
