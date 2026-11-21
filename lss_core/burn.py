"""Burn tests: does the sample change while the same spot stays in the beam?
(owner, 2026-11-21; F22a 3-4, P30).

A burn scan repeats one point (same Qz, same detector angle) and takes a
frame each time. The reader measures per frame

- reflectivity geometry (Det_Th ≈ 0): the reflected intensity, background-
  subtracted ROI per monitor count (the Ref Patch arithmetic,
  ``Experiment.reflectivity`` on the one scan);
- GID geometry: the strongest peak of the frame's horizontal profile (all
  rows summed, per monitor, x in Qxy with the pinhole distance), fitted
  with ``lss_core.peaks``: its integrated intensity, position and FWHM. The
  peak is found automatically on the mean of the frames (F22a 4: "largest
  peak by default"), or taken in a typed Qxy range (the override);

and fits each quantity over time with ``lss_core.trends`` (constant,
linear, exponential, double exponential, compared by AICc).

Errors: for GID the trends use the frames' errors only as relative
weights, their scale from the scatter of the frames about the most
general model (``trends.compare(errors='scatter')``): a relative change is
what matters, and the absolute σ of a sum, centroid or width is not
trusted (owner, 2026-11-21). Reflectivity keeps the counting errors.

Time: since the first frame's exposure began, at the middle of each
frame's exposure. ``time='exposure'`` (default): the counting time
accumulated, Σ Seconds of the earlier frames + half the frame's own, i.e.
the time the spot was certainly in the beam; ``time='clock'``: measured
start times (Tstart, or Epoch differences in older files) + half the
count time, which includes the overhead between frames (shutter state
during it not recorded). Without per-point times, clock falls back to
exposure and says so.

What the change is measured against: the intensity and the width
relative to their own value at t = 0; the position against the peak's
width (a shift of 5 % of the FWHM), since a relative change of a Qxy near
1.5 Å⁻¹ means nothing.
"""
import math
from dataclasses import dataclass, field, replace

import numpy as np

from . import peaks as peakmod
from . import trends

QUANTITIES = {'reflectivity': ('intensity',), 'gid': ('intensity', 'centre', 'fwhm')}
LABELS = {'intensity': 'Intensity', 'centre': 'Position', 'fwhm': 'FWHM'}
DEFAULT_FIT = peakmod.FitOptions(shape='gaussian', background='linear', n_peaks=1)


@dataclass
class BurnResult:
    """One burn scan: per-frame values and their trend comparisons.
    ``values``: {quantity: (y, sigma)}; ``trends``: {quantity:
    trends.TrendComparison}; ``window``: the Qxy range fitted (GID);
    ``reference``: the fit of the mean profile that chose it."""
    scan: int
    kind: str                     # 'reflectivity' or 'gid'
    t: np.ndarray
    time: str
    points: list
    values: dict = field(default_factory=dict)
    trends: dict = field(default_factory=dict)
    window: tuple = None
    reference: object = None
    frame_fits: list = field(default_factory=list)
    profiles: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    threshold: float = 0.05
    seconds: np.ndarray = None    # count time of each frame

    def safe_time(self):
        """(time, quantity): the shortest confident time to a ``threshold``
        change over the quantities (math.inf: none within the horizon)."""
        best = (math.inf, '')
        for q, c in self.trends.items():
            if c.change is not None and np.isfinite(c.change.confident) and c.change.confident < best[0]:
                best = (c.change.confident, q)
        return best

    def duration(self):
        """Seconds from the first exposure's start to the last one's end
        (each t is the middle of its exposure, the first begins at 0)."""
        if not len(self.t):
            return 0.0
        half = self.seconds[-1] / 2 if self.seconds is not None else self.t[0]
        return float(self.t[-1] + half)

    def stable(self):
        """True when every quantity is better described by a constant."""
        v = [c.stable for c in self.trends.values() if c.stable is not None]
        return bool(v) and all(v)

    def summary(self):
        lines = ['Burn test, scan %d (%s), %d frames over %.0f s (%s time)'
                 % (self.scan, self.kind, len(self.t), self.duration(), self.time)]
        for q, c in self.trends.items():
            lines.append(c.summary())
        t, q = self.safe_time()
        if q:
            lines.append('limit: %s, %.0f%% change in ≥ %.3g s (%.0f%% confidence)'
                         % (LABELS.get(q, q), 100 * self.threshold, t, 100 * self.trends[q].change.confidence))
        return '\n'.join(lines)

    def table(self):
        """Rows for the workbook's Fits sheet: one per quantity and model."""
        rows = []
        for q, c in self.trends.items():
            for r in c.table():
                r = dict(r, quantity=q, best=(r['model'] == c.best), stable=c.stable)
                if c.change is not None and r['model'] == c.change.model:
                    r.update(change_threshold=c.change.threshold, change_time=c.change.best,
                             change_time_confident=c.change.confident, confidence=c.change.confidence)
                rows.append(r)
        return rows

    def data(self):
        """(columns, array): time and each quantity with its error."""
        cols = ['time_s']
        arr = [self.t]
        for q, (y, s) in self.values.items():
            cols += [q, q + '_err']
            arr += [y, s]
        return cols, np.column_stack(arr)


def frame_times(columns, point_times, points, time='exposure'):
    """(t, note): seconds since the first selected frame's exposure began,
    at the middle of each frame's exposure (module docstring)."""
    points = list(points)
    sec = columns.get('Seconds')
    sec = np.asarray(sec, float) if sec is not None else None
    if time not in ('exposure', 'clock'):
        raise ValueError("time %r: 'exposure' or 'clock'" % time)
    if sec is None:
        return np.arange(len(points), dtype=float), 'no Seconds column: frame number used as time'
    s = sec[points]
    if (time == 'clock' and point_times is not None and point_times.format in ('new', 'old')
            and point_times.start is not None):
        st = np.asarray(point_times.start, float)[points]
        return st - st[0] + s / 2, 'clock: measured start times + half the count time (%s)' % point_times.format
    note = 'exposure: counting time accumulated, at the middle of each frame'
    if time == 'clock':
        note = 'clock asked, but the scan has no per-point times: ' + note
    return np.concatenate([[0.0], np.cumsum(s)[:-1]]) + s / 2, note


def is_gid(dth_deg):
    return abs(float(dth_deg)) > 0.001


ESTIMATORS = ('template', 'moments', 'fit')


def _illuminated(y, frac=0.05, inset=2):
    """(first, last) index of the lit part of a profile: above ``frac`` of
    its maximum, ``inset`` points in from the edges of the frame's shadow."""
    idx = np.flatnonzero(y > frac * np.nanmax(y))
    if idx.size < 2 * inset + 5:
        return 0, len(y) - 1
    return int(idx[0] + inset), int(idx[-1] - inset)


def _baseline(x, y, k=3):
    """The straight line through the means of the first and last ``k``
    points (the legacy burn test's background)."""
    xl, xr = np.mean(x[:k]), np.mean(x[-k:])
    yl, yr = np.mean(y[:k]), np.mean(y[-k:])
    return yl + (yr - yl) * (x - xl) / (xr - xl) if xr != xl else np.full_like(x, yl)


def _half_width(x, y):
    """FWHM of a peak-only profile by walking down from its maximum."""
    k = int(np.argmax(y))
    half = y[k] / 2
    i = k
    while i > 0 and y[i] > half:
        i -= 1
    j = k
    while j < len(y) - 1 and y[j] > half:
        j += 1
    xl = x[i] + (half - y[i]) * (x[i + 1] - x[i]) / (y[i + 1] - y[i]) if y[i + 1] != y[i] else x[i]
    xr = x[j - 1] + (y[j - 1] - half) * (x[j] - x[j - 1]) / (y[j - 1] - y[j]) if y[j - 1] != y[j] else x[j]
    return float(xr - xl)


def choose_window(x, mean, err, qxy_range=None, options=None):
    """(low, high) of Qxy around the strongest peak of the mean profile
    (3 FWHM each side, kept inside the lit columns), or ``qxy_range``."""
    lo_i, hi_i = _illuminated(mean)
    if qxy_range is not None:
        return (min(qxy_range), max(qxy_range)), None
    o = options or DEFAULT_FIT
    found = peakmod.find_peaks(x[lo_i:hi_i + 1], mean[lo_i:hi_i + 1], err[lo_i:hi_i + 1],
                               max_peaks=3, min_prominence=o.min_prominence)
    if not found:
        raise ValueError('no peak stands %.1f sigma above the background in the mean profile'
                         % o.min_prominence)
    pk = max(found, key=lambda d: d['height'])
    lo = max(pk['centre'] - 3 * pk['fwhm'], x[lo_i])
    hi = min(pk['centre'] + 3 * pk['fwhm'], x[hi_i])
    return (float(lo), float(hi)), pk


def _template(x, y, s, xt, mt, c):
    """Fit y ≈ A·mt(c + (x − c − δ)/w) + b0 + b1(x − c): (A, δ, w) with errors and χ²/dof."""
    from scipy.interpolate import CubicSpline
    from scipy.optimize import curve_fit
    spline = CubicSpline(xt, mt, bc_type='natural', extrapolate=False)     # smooth in δ and w: a usable covariance

    def ev(u, nu=0):
        v = spline(u, nu)
        return np.where(np.isfinite(v), v, 0.0)

    def model(xx, A, d, w, b0, b1):
        return A * ev(c + (xx - c - d) / w) + b0 + b1 * (xx - c)

    def jac(xx, A, d, w, b0, b1):          # analytic: a numerical step in δ near 0 is too small to trust
        u = c + (xx - c - d) / w
        dv = ev(u, 1)
        return np.column_stack([ev(u), -A * dv / w, -A * dv * (xx - c - d) / w ** 2,
                                np.ones_like(xx), xx - c])
    step = float(np.median(np.diff(xt)))
    p, cov = curve_fit(model, x, y, p0=[1.0, 0.0, 1.0, 0.0, 0.0], sigma=s, absolute_sigma=True, jac=jac,
                       bounds=([0, -20 * step, 0.3, -np.inf, -np.inf], [np.inf, 20 * step, 3.0, np.inf, np.inf]),
                       maxfev=20000)
    chi2 = float(np.sum(((y - model(x, *p)) / s) ** 2)) / max(len(x) - 5, 1)
    return p, np.sqrt(np.maximum(np.diag(cov), 0)), chi2, cov


def measure_gid(profiles, qxy_range=None, options=None, estimator='template'):
    """Per-frame intensity, position and FWHM of the strongest peak of the
    profiles ((N, 3) arrays x, I, σ on one x grid).

    The window: 3 FWHM either side of the strongest peak of the mean
    profile, inside the lit columns, or ``qxy_range`` (the legacy test
    worked well once its range was constrained like this; owner,
    2026-11-21). Estimators:

    - ``template`` (default): the mean profile less its straight baseline
      (the legacy background) is the peak's shape; each frame is fitted as
      A × that shape shifted by δ and stretched by w, on its own straight
      background: every frame measured relative to the mean of the frames.
      Integrated intensity = A·w × the shape's area, position = the shape's
      centroid + δ, FWHM = w × the shape's FWHM;
    - ``moments`` (the legacy burn test's arithmetic): the straight line
      through the first and last three points of the window removed, then
      the sum (× point spacing), the centroid and 2.355 × the r.m.s. width.
      Its position and width are those of everything in the window, so a
      steady shoulder under the peak dilutes a peak's shift (synthetic:
      0.004 Å⁻¹ read as 0.0023) and the 5 % time comes out too long;
    - ``fit``: ``lss_core.peaks.fit`` with ``options`` (one peak), its area,
      centre and FWHM. A single Gaussian does not describe a pinhole
      frame's peak (sharp, on a broad shoulder; χ²/dof 10–40 on NX).

    On NX scans 14 and 15 template and moments agree on intensity (stable)
    and width; the template is about 3 × more precise in position.

    Returns (values, reference, window, per-frame details)."""
    if estimator not in ESTIMATORS:
        raise ValueError('estimator %r: one of %s' % (estimator, ', '.join(ESTIMATORS)))
    o = DEFAULT_FIT if options is None else options
    x = profiles[0][:, 0]
    mean = np.mean([p[:, 1] for p in profiles], axis=0)
    err = np.sqrt(np.sum([p[:, 2] ** 2 for p in profiles], axis=0)) / len(profiles)
    window, found = choose_window(x, mean, err, qxy_range, o)
    sel = (x >= window[0]) & (x <= window[1])
    if np.sum(sel) < 8:
        raise ValueError('the Qxy window %.4g:%.4g holds %d points (at least 8 needed)'
                         % (window[0], window[1], int(np.sum(sel))))
    xw = x[sel]
    step = float(np.median(np.abs(np.diff(xw))))
    shape = mean[sel] - _baseline(xw, mean[sel])
    c_ref = float(np.sum(shape * xw) / np.sum(shape)) if np.sum(shape) > 0 else float(np.mean(xw))
    reference = dict(centre=c_ref, fwhm=_half_width(xw, shape), area=float(np.sum(shape) * step),
                     window=window, found=found, estimator=estimator)
    vals = {k: ([], []) for k in ('intensity', 'centre', 'fwhm')}
    details = []

    def put(a, ae, c, ce, w, we):
        for k, v, e in (('intensity', a, ae), ('centre', c, ce), ('fwhm', w, we)):
            vals[k][0].append(v)
            vals[k][1].append(e)
    for prof in profiles:
        y, s = prof[sel, 1], prof[sel, 2]
        s = np.where(s > 0, s, np.nan)
        s = np.where(np.isfinite(s), s, np.nanmax(s) if np.any(np.isfinite(s)) else 1.0)
        if estimator == 'template':
            try:
                p, pe, chi2, cov = _template(xw, y, s, xw, shape, c_ref)
                # the stretched shape's area is w × the shape's: integrated intensity A·w·area
                aw = p[0] * p[2]
                aw_e = math.sqrt(max((p[2] * pe[0]) ** 2 + (p[0] * pe[2]) ** 2 + 2 * p[0] * p[2] * cov[0, 2], 0.0))
                put(aw * reference['area'], aw_e * reference['area'], c_ref + p[1], pe[1],
                    p[2] * reference['fwhm'], pe[2] * reference['fwhm'])
                details.append(dict(ok=True, chi2_dof=chi2, params=p, errors=pe))
            except (RuntimeError, ValueError) as e:
                put(math.nan, math.nan, math.nan, math.nan, math.nan, math.nan)
                details.append(dict(ok=False, message=str(e)))
        elif estimator == 'fit':
            fo = replace(o, n_peaks=1, x_range=window, centres=(reference['centre'],), fix_centres=False,
                         window=0.5 * (window[1] - window[0]))
            r = peakmod.fit(prof[:, 0], prof[:, 1], prof[:, 2], fo)
            pk = r.peaks[0] if (r.peaks and r.ok) else None
            if pk is None:
                put(math.nan, math.nan, math.nan, math.nan, math.nan, math.nan)
            else:
                put(pk.area, pk.area_err, pk.centre, pk.centre_err, pk.fwhm, pk.fwhm_err)
            details.append(dict(ok=pk is not None, chi2_dof=r.chi2_dof, message=r.message, result=r))
        else:
            yb = y - _baseline(xw, y)
            tot = float(np.sum(yb))
            var = s ** 2
            cen = float(np.sum(yb * xw) / tot)
            cen_e = math.sqrt(float(np.sum((xw - cen) ** 2 * var))) / abs(tot)
            m2 = float(np.sum(yb * (xw - cen) ** 2) / tot)
            m2_e = math.sqrt(float(np.sum(((xw - cen) ** 2 - m2) ** 2 * var))) / abs(tot)
            g = 2 * math.sqrt(2 * math.log(2))
            ok = m2 > 0
            put(tot * step, math.sqrt(float(np.sum(var))) * step, cen, cen_e,
                g * math.sqrt(m2) if ok else math.nan, g * m2_e / (2 * math.sqrt(m2)) if ok else math.nan)
            details.append(dict(ok=ok))
    values = {k: (np.array(a, float), np.array(b, float)) for k, (a, b) in vals.items()}
    return values, reference, window, details


def analyse(t, values, models=trends.MODELS, threshold=0.05, confidence=0.95, overdispersion=True,
            errors='given'):
    """trends.compare for each quantity; the position against the mean
    FWHM; ``errors`` as trends.compare ('scatter' for GID burns)."""
    out = {}
    width = None
    if 'fwhm' in values:
        w = values['fwhm'][0]
        width = float(np.nanmean(w)) if np.any(np.isfinite(w)) else None
    for q, (y, s) in values.items():
        scale = width if q == 'centre' else None
        if q == 'centre' and scale is None:
            continue
        out[q] = trends.compare(t, y, s, models=models, threshold=threshold, scale=scale,
                                confidence=confidence, label=LABELS.get(q, q), overdispersion=overdispersion,
                                t0=0.0, errors=errors)
    return out
