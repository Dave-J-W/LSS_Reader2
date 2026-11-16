"""How much of the monitors' scatter is beam variation, and how much is noise?

Run from the repository root:  python3 tests/tools/monitor_ratio.py [specfile]

Idea (from the owner, 2026-11-16): Monc and Monp both follow the incident
beam. Real beam variation moves them together and cancels in their ratio;
each monitor's own noise does not. So, per scan, after removing the slow
trend along the scan (the S1 slits make Monc fall with Qz):

  r        correlation of the two monitors' residuals
           (+1: all scatter is common beam variation; 0: all is independent noise)
  common   the common (beam) part of the relative scatter, sqrt(cov)
  own      what is left for each monitor once the common part is removed
  ratio    relative scatter of Monc/Monp, which bounds the two "own" parts:
           ratio^2 = own_c^2 + own_p^2

Scatter is the standard deviation of residuals from a quadratic in the point
number. Scans with fewer than 8 points, or with beam off (counts/s < 1000),
are skipped. "/P" columns divide by 1/sqrt(counts).
"""
import sys

import numpy as np


def scans(path):
    out, cur = [], None
    with open(path) as f:
        for line in f:
            if line.startswith('#S '):
                cur = {'num': int(line.split()[1]), 'cmd': ' '.join(line.split()[2:]),
                       'cols': None, 'rows': []}
                out.append(cur)
            elif cur is not None and line.startswith('#L '):
                cur['cols'] = line[3:].split()
            elif cur is not None and cur['cols'] and line.strip() and line[0] != '#':
                try:
                    row = [float(v) for v in line.split()]
                except ValueError:
                    continue
                if len(row) == len(cur['cols']):
                    cur['rows'].append(row)
    return out


def column(scan, name):
    # 'Monc' appears twice in some #L lines; take the last, the counter
    idx = [i for i, c in enumerate(scan['cols']) if c == name]
    return np.array(scan['rows'])[:, idx[-1]] if idx else None


def resid(y):
    x = np.arange(len(y), dtype=float)
    return y / np.polyval(np.polyfit(x, y, 2), x) - 1.0


def main(path):
    print('%4s %-28s %3s %4s | %9s %9s | %6s | %8s %8s %8s %8s | %5s %5s'
          % ('scan', 'command', 'n', 'T/s', 'sd Monc', 'sd Monp', 'r',
             'common', 'own_c', 'own_p', 'ratio', 'c/P', 'p/P'))
    for s in scans(path):
        if not s['rows'] or len(s['rows']) < 8:
            continue
        mc, mp, t = column(s, 'Monc'), column(s, 'Monp'), column(s, 'Seconds')
        if mc is None or mp is None or np.mean(mc / t) < 1000 or np.mean(mp / t) < 1000:
            continue
        rc, rp = resid(mc), resid(mp)
        dof = len(mc) - 3
        vc, vp = (rc ** 2).sum() / dof, (rp ** 2).sum() / dof
        cov = (rc * rp).sum() / dof
        r = cov / np.sqrt(vc * vp)
        common = np.sqrt(max(cov, 0.0))
        own_c, own_p = np.sqrt(max(vc - max(cov, 0), 0)), np.sqrt(max(vp - max(cov, 0), 0))
        ratio = np.sqrt((resid(mc / mp) ** 2).sum() / dof)
        print('%4d %-28s %3d %4g | %9.2e %9.2e | %+6.2f | %8.1e %8.1e %8.1e %8.1e | %5.2f %5.2f'
              % (s['num'], s['cmd'][:28], len(mc), t.mean(), np.sqrt(vc), np.sqrt(vp), r,
                 common, own_c, own_p, ratio,
                 own_c * np.sqrt(mc.mean()), own_p * np.sqrt(mp.mean())))


def detector_witness(path, scan_numbers=(6, 7, 8, 9), orders=(4, 6)):
    """Third witness: the detector signal itself.

    If Monc's scatter is real variation of the flux reaching the sample, the
    detector counts carry the same variation: their residuals correlate with
    Monc's, and dividing by Monc makes them quieter. If Monc's scatter is
    its own noise, dividing by it makes the detector signal noisier.
    Residuals are taken from a polynomial in log intensity along the scan,
    so only scans whose curve is smooth at that order can be judged.
    """
    print()
    print('Detector as witness (SPEC "Pilatus" column, relative scatter)')
    print('%4s %5s %3s %9s | %9s %9s %9s | %8s %6s'
          % ('scan', 'order', 'n', 'Poisson', 'raw', '/Monc', '/Monp',
             'sd Monc', 'r'))
    by_num = {s['num']: s for s in scans(path)}
    for n in scan_numbers:
        s = by_num.get(n)
        if s is None or not s['rows']:
            continue
        pil, mc, mp = column(s, 'Pilatus'), column(s, 'Monc'), column(s, 'Monp')
        if pil is None or np.any(pil <= 0):
            continue
        x = np.linspace(-1, 1, len(pil))
        for order in orders:
            dof = len(pil) - order - 1

            def res(y):
                return np.log(y) - np.polyval(np.polyfit(x, np.log(y), order), x)

            def sd(y):
                return np.sqrt((res(y) ** 2).sum() / dof)
            r = np.corrcoef(res(pil), res(mc))[0, 1]
            print('%4d %5d %3d %9.1e | %9.2e %9.2e %9.2e | %8.1e %+6.2f'
                  % (n, order, len(pil), np.sqrt(np.mean(1 / pil)), sd(pil),
                     sd(pil / mc), sd(pil / mp), sd(mc), r))


if __name__ == '__main__':
    target = (sys.argv[1] if len(sys.argv) > 1
              else 'sample_data/NX_school/2026sep/20260923')
    main(target)
    if len(sys.argv) <= 1:
        detector_witness(target)
