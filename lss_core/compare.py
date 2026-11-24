"""Comparing saved reduced curves (F80, F105): the reflectivities of one
SPEC file's workbook, ordered by series, time or sample position, and their
ratios to a reference curve. No Qt: the window's Compare tab draws them.

Owner, 2026-11-23:
- F80: "We continue to take reflect data and compare the processed/reduced
  data together in reader from different sample areas or just as time goes
  by, to check stability of sample". Overlay the saved reflectivities by
  series, time or sx in one action, with their ratios to the first.
- F105 (Q-REF-5): a tab only for comparing reduced data, fed by the
  workbook, "provided the new data auto-update".

The ratio of two curves is taken on the reference's Qz points inside the
range both cover. The other curve is interpolated linearly in log R
against log Qz: above the critical edge reflectivity falls about as Qz⁻⁴
(the Fresnel law, R ≈ (Qc/2Qz)⁴), which that interpolation follows
exactly (measured: a power law on a coarse grid, 4 % off with log R
against Qz, 1e-12 against log Qz). The ratio's error adds the two relative
errors in quadrature: σ_r = r √((σ₁/R₁)² + (σ₂/R₂)²), the standard
propagation for a quotient of independent values (e.g. Bevington and
Robinson, *Data Reduction and Error Analysis*, 3rd ed., ch. 3; from
memory). It ignores the correlation the interpolation brings between
neighbouring points, so the errors of adjacent ratio points are not
independent.
"""
from dataclasses import dataclass, field

import numpy as np

ORDERS = ('series', 'time', 'sx')


@dataclass
class Entry:
    """One saved reduced curve: its workbook row and its data (columns Qz,
    R, dR, ...)."""
    rid: str
    version: int
    scans: list
    label: str
    saved: str
    note: str = ''
    series: str = ''
    stale: bool = False
    origin: str = ''
    sx: float = None
    data: np.ndarray = field(default=None, repr=False)

    def title(self):
        s = _scans_text(self.scans)
        return '%s v%d  S# %s%s' % (self.rid, self.version, s, '  (out of date)' if self.stale else '')


def _scans_text(scans):
    """'6–9' for a run of scans, '6, 8' otherwise."""
    if not scans:
        return ''
    scans = sorted(scans)
    if scans == list(range(scans[0], scans[-1] + 1)) and len(scans) > 2:
        return '%d–%d' % (scans[0], scans[-1])
    return ', '.join(str(s) for s in scans)


def entries(wb, kind='reflectivity', label='R', positions=None):
    """The saved curves of ``kind`` and ``label`` in workbook ``wb``
    (lss_core.workbook.Workbook), in the order saved. ``positions``: {scan:
    sx} to attach the sample position of each curve's first scan."""
    out = []
    for r in wb.results(kind):
        if label is not None and str(r.get('label') or '') != label:
            continue
        scans = [int(s) for s in str(r.get('scans') or '').split(',') if s.strip()]
        sx = None
        if positions and scans:
            v = positions.get(scans[0])
            sx = float(v) if isinstance(v, (int, float)) else None
        data = wb.data(r['id'])
        out.append(Entry(str(r['id']), int(r.get('version') or 0), scans, str(r.get('label') or ''),
                         str(r.get('saved') or ''), str(r.get('note') or ''), str(r.get('series') or ''),
                         bool(r.get('stale')), str(r.get('origin') or ''), sx, data))
    return out


def order(items, by='series'):
    """``items`` sorted by series (then first scan and version), by time
    saved, or by sx (curves without an sx last)."""
    if by not in ORDERS:
        raise ValueError('order by one of %s, not %r' % (ORDERS, by))
    if by == 'series':
        return sorted(items, key=lambda e: (e.series or '~', e.scans[:1], e.version))
    if by == 'time':
        return sorted(items, key=lambda e: e.saved)
    return sorted(items, key=lambda e: (e.sx is None, e.sx if e.sx is not None else 0.0, e.saved))


def ratio(ref, other):
    """(Qz, ratio, σ) of ``other`` over ``ref`` (arrays with columns Qz, R,
    dR) on ``ref``'s Qz points inside the range both cover; the other curve
    interpolated linearly in log R against log Qz. Points where either R or
    Qz is not positive are left out. Empty arrays when the ranges do not
    overlap."""
    a, b = np.asarray(ref, float), np.asarray(other, float)
    empty = (np.zeros(0),) * 3
    if a.ndim != 2 or b.ndim != 2 or len(a) < 1 or len(b) < 2 or a.shape[1] < 3 or b.shape[1] < 3:
        return empty
    b = b[np.argsort(b[:, 0])]
    b = b[(b[:, 1] > 0) & np.isfinite(b[:, 1]) & (b[:, 0] > 0)]
    if len(b) < 2:
        return empty
    inside = (a[:, 0] >= b[0, 0]) & (a[:, 0] <= b[-1, 0]) & (a[:, 1] > 0) & (a[:, 0] > 0)
    a = a[inside]
    if not len(a):
        return empty
    q = a[:, 0]
    lq, lqb = np.log(q), np.log(b[:, 0])
    y2 = np.exp(np.interp(lq, lqb, np.log(b[:, 1])))
    rel2 = np.interp(lq, lqb, b[:, 2] / b[:, 1])
    r = y2 / a[:, 1]
    s = np.abs(r) * np.sqrt((a[:, 2] / a[:, 1]) ** 2 + rel2 ** 2)
    return q, r, s
