"""Burn tests: does the sample change while the same spot stays in the beam?
(owner, 2026-11-21; F22a 3-4, P30).

A burn scan repeats one point (same Qz, same detector angle) and takes a
frame each time. The reader measures per frame

- reflectivity geometry (Det_Th ≈ 0): the reflected intensity, background-
  subtracted ROI per monitor count (the Ref Patch arithmetic,
  ``Experiment.reflectivity`` on the one scan);
- GID geometry: the strongest peak of the frame's horizontal profile (the
  rows where the mean frame's signal is summed, ``signal_rows``; all rows
  before 2026-11-24; per monitor, x in Qxy with the pinhole distance), fitted
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

Time (owner, 2026-11-21: the shutter closes between exposures by
default; wall time is better): ``time='clock'`` (default) measured start
times; ``time='exposure'`` the counting time alone. Details: since the first frame's exposure began, at the middle of each
frame's exposure. ``time='exposure'``: the counting time
accumulated, Σ Seconds of the earlier frames + half the frame's own, i.e.
the time the spot was certainly in the beam; ``time='clock'``: measured
start times (Tstart, or Epoch differences in older files) + half the
count time, which includes the overhead between frames (default) (shutter state
during it not recorded). Without per-point times, clock falls back to
exposure and says so.

What the change is measured against: the intensity and the width
relative to their own value at t = 0; the position against the peak's
width (a shift of 5 % of the FWHM), since a relative change of a Qxy near
1.5 Å⁻¹ means nothing. Whether a position change matters is the user's
judgment (owner, 2026-11-21): the position is shown, but it sets the
limit only when asked (``limit_quantities``).

Which scans are burn scans: by the standard of the beamline (owner,
2026-11-21), an ``ascan ih`` that does not move (start = end);
``lss_core.series.is_burn``.
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
    rows: tuple = None            # GID: the detector rows summed (first, last), both included
    limit_quantities: tuple = ('intensity', 'fwhm')   # what sets the limit (position: the user's choice)
    axis: str = 'time'            # what the trends are fitted against: 'time' or 'dose' (F98)
    dose: np.ndarray = None       # the dose since the first frame began, at the middle of each (lss_core.dose)
    dose_unit: str = ''
    dose_total: float = None      # to the end of the last frame
    dose_scale: float = 1.0       # dose and dose_total are in units of this many (dose.engineering_scale)
    dose_notes: list = field(default_factory=list)

    @property
    def x(self):
        """The axis the trends are fitted against: ``t``, or ``dose`` on the dose axis."""
        return self.dose if self.axis == 'dose' else self.t

    def x_unit(self):
        return self.dose_unit if self.axis == 'dose' else 's'

    def span(self):
        """The axis from 0 to the end of the last frame: ``duration()``, or the dose."""
        return float(self.dose_total) if self.axis == 'dose' else self.duration()

    def safe_time(self, quantities=None):
        """(time, quantity): the shortest confident time to a ``threshold``
        change over ``quantities`` (default ``limit_quantities``: intensity
        and width; the position only when the user asks) (math.inf: none
        within the horizon). On the dose axis, a dose (``x_unit()``)."""
        best = (math.inf, '')
        use = self.limit_quantities if quantities is None else quantities
        for q, c in self.trends.items():
            if q not in use:
                continue
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
        if self.axis == 'dose':
            lines[0] += ', %.3g %s (against dose)' % (self.dose_total, self.dose_unit)
        for q, c in self.trends.items():
            lines.append(c.summary())
        t, q = self.safe_time()
        if q:
            lines.append('limit: %s, %.0f%% change in ≥ %.3g %s (%.0f%% confidence)'
                         % (LABELS.get(q, q), 100 * self.threshold, t, self.x_unit(),
                            100 * self.trends[q].change.confidence))
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
        if self.axis == 'dose':          # the time axis's files are as before
            cols.append('dose_' + self.dose_unit.replace(' ', '_').replace('/', '_per_'))
            arr.append(self.dose)
        for q, (y, s) in self.values.items():
            cols += [q, q + '_err']
            arr += [y, s]
        return cols, np.column_stack(arr)


AXES = ('time', 'dose')


def frame_times(columns, point_times, points, time='clock'):
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
        note = 'exposure: clock asked, but the scan has no per-point times; counting time accumulated'
    return np.concatenate([[0.0], np.cumsum(s)[:-1]]) + s / 2, note


# A burn test is a GID burn above this detector angle, a reflectivity burn
# at or below it (owner, 2026-11-23, Q10/F87: "Det_Th > 2°", not the 1°
# proposed; until then any Det_Th above 0.001° counted as GID). A macro role
# indicator, when the beamline macros write one, is to take precedence.
GID_BURN_MIN_DTH_DEG = 2.0


def is_gid(dth_deg):
    """A GID burn: Det_Th (degrees) above GID_BURN_MIN_DTH_DEG."""
    return abs(float(dth_deg)) > GID_BURN_MIN_DTH_DEG


ESTIMATORS = ('template', 'moments', 'fit')

ROWS_FRACTION = 0.1        # signal_rows: the peak's row profile above this fraction of its maximum
ROWS_PAD = 2               # rows added on each side
ROWS_MIN_SIGNIFICANCE = 5.0   # the column peak and the row profile's maximum over their noise; below, no rows


def _noise(y):
    """Robust point-to-point noise of a profile: the median absolute
    difference of neighbours, as a standard deviation of one point."""
    d = np.diff(np.asarray(y, float))
    return float(1.4826 * np.median(np.abs(d - np.median(d))) / math.sqrt(2)) if d.size else 0.0


def _smooth(y, n=5):
    k = np.ones(n) / n
    return np.convolve(np.pad(y, n // 2, mode='edge'), k, mode='valid')


def signal_rows(mean, fraction=ROWS_FRACTION, pad=ROWS_PAD):
    """(first, last) detector rows of a GID burn where the mean frame's
    signal is (owner, 2026-11-23, Q-BURN-6: "GID-burn detector rows default
    from the mean frame"), both included; None when no peak stands out
    (then all rows are summed, as before).

    ``mean``: the mean of the burn's frames per monitor count, rows ×
    columns. The rule:

    1. a 3 × 3 median of the mean frame, so that a hot pixel is not a peak;
    2. the column profile (summed over rows) less its median: the peak's
       columns are the run around the strongest column above half its
       height, widened by that run's width on each side;
    3. the row profile of those columns less as many columns of each row's
       median (the background beside the peak), smoothed over 5 rows: the
       peak's own profile along the rows (β);
    4. the rows: the run around that profile's maximum where it stays above
       ``fraction`` of the maximum, widened by ``pad`` rows, inside the
       frame. For a rod falling exponentially with β, a fraction of 0.1
       keeps 90 % of its counts and leaves out rows of background only
       (below the horizon, above where the rod has faded).

    The peak is the strongest in the mean frame, as the burn's own
    automatic choice is; with a typed Qxy range the rows are still this
    peak's."""
    from scipy.ndimage import median_filter
    a = np.nan_to_num(np.asarray(mean, float))
    m = median_filter(a, size=3, mode='nearest')
    nrows, ncols = m.shape
    cp = m.sum(axis=0)
    cp = cp - np.median(cp)
    c = int(np.argmax(cp))
    cu = a.sum(axis=0)                  # noise from the unfiltered frame (the median correlates neighbours)
    if cp[c] <= 0 or cp[c] < ROWS_MIN_SIGNIFICANCE * _noise(cu):
        return None
    lo = c
    while lo > 0 and cp[lo - 1] > cp[c] / 2:
        lo -= 1
    hi = c
    while hi < ncols - 1 and cp[hi + 1] > cp[c] / 2:
        hi += 1
    w = hi - lo + 1
    cols = np.arange(max(lo - w, 0), min(hi + w, ncols - 1) + 1)
    rp = _smooth(m[:, cols].sum(axis=1) - len(cols) * np.median(m, axis=1))
    raw = a[:, cols].sum(axis=1) - len(cols) * np.median(a, axis=1)
    r = int(np.argmax(rp))
    if rp[r] <= 0 or rp[r] < ROWS_MIN_SIGNIFICANCE * _noise(raw) / math.sqrt(5):     # the 5-row mean's noise
        return None
    top = fraction * rp[r]
    a = r
    while a > 0 and rp[a - 1] > top:
        a -= 1
    b = r
    while b < nrows - 1 and rp[b + 1] > top:
        b += 1
    return max(a - pad, 0), min(b + pad, nrows - 1)


def _illuminated(y, frac=0.05, inset=2):
    """(first, last) index of the lit part of a profile: above ``frac`` of
    its maximum or half its median, whichever is lower, ``inset`` points in
    from the edges of the frame's shadow. The median term (2026-11-24) keeps
    the lit floor lit beside a peak more than 20 times stronger, which the
    maximum alone would leave out (the window then shrank to the peak); it
    changes nothing where the floor is above 10 % of the maximum (NX 14, 15:
    12-15 %)."""
    idx = np.flatnonzero(y > min(frac * np.nanmax(y), 0.5 * np.nanmedian(y)))
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


STYLES = {'constant': ':', 'linear': '--', 'exponential': '-.', 'double exponential': '-'}
COLOURS = {'intensity': 'C0', 'centre': 'C2', 'fwhm': 'C3'}
UNITS = {'reflectivity': {'intensity': 'Reflected intensity / Monc'},
         'gid': {'intensity': 'Intensity / Monc', 'centre': r'Position $Q_{xy}$ [$\AA^{-1}$]',
                 'fwhm': r'FWHM [$\AA^{-1}$]'}}
SHORT = {'constant': 'const', 'linear': 'lin', 'exponential': 'exp', 'double exponential': 'dbl'}


def normaliser(c, quantity):
    """(reference, scale, label) for the right-hand axis in percent:
    intensity and FWHM as % of the best model's value at t = 0; the
    position as its shift from t = 0 in % of the mean FWHM (the scale its
    5 % change is measured against)."""
    f = c.fits.get(c.best)
    ref = float(f(np.array([0.0]))[0]) if f is not None and f.ok else float(np.nanmean(c.y))
    if quantity == 'centre' and c.change is not None:
        return ref, c.change.scale, 'shift, % of FWHM'
    return ref, ref, '% of t = 0'


def summary_text(res):
    """The text beside the panels: per quantity the verdict, the best
    model, each model's Δ and the 5 % time; then the limit and the settings."""
    out = []
    for q, c in res.trends.items():
        out.append(LABELS.get(q, q))
        if c.stable is not None:
            out.append('  %s' % ('stable' if c.stable else 'changing'))
            out.append('  const − lin %+.1f' % c.delta_constant_linear)
        out.append('  best: %s' % SHORT[c.best])
        ds = ['%s %.1f' % (SHORT[m], f.delta) for m, f in c.fits.items() if f.ok]
        for i in range(0, len(ds), 2):
            out.append(('  Δ%s: ' % c.criterion if i == 0 else ' ' * (5 + len(c.criterion))) + ', '.join(ds[i:i + 2]))
        ch = c.change
        if ch is not None:
            u = res.x_unit() if hasattr(res, 'x_unit') else 's'
            t = '> %.3g %s' % (ch.horizon, u) if math.isinf(ch.confident) else '%.3g %s' % (ch.confident, u)
            out.append('  %.0f %% in ≥ %s' % (100 * ch.threshold, t))
            out.append('    (%s%s)' % (SHORT[ch.model], ', extrap.' if ch.extrapolated else ''))
        out.append('')
    t, q = res.safe_time()
    if q:
        out.append('Limit (%s): %s' % (', '.join(LABELS.get(x, x).lower() for x in res.limit_quantities
                                               if x in res.trends), LABELS.get(q, q).lower()))
        out.append('  %.0f %% in ≥ %.3g %s' % (100 * res.threshold, t, res.x_unit() if hasattr(res, 'x_unit') else 's'))
        out.append('  (%.0f %% confidence)' % (100 * res.trends[q].change.confidence))
    elif res.trends:
        out.append('No %.0f %% change' % (100 * res.threshold))
        out.append('  within the horizon')
    out.append('')
    out.append('%d frames, %.0f s' % (len(res.t), res.duration()))
    out.append('time: %s' % res.time)
    if getattr(res, 'axis', 'time') == 'dose':
        out.append('against dose: %.3g %s' % (res.dose_total, res.dose_unit))
    est = (res.reference or {}).get('estimator') if isinstance(res.reference, dict) else None
    if est:
        out.append('estimator: %s' % est)
    if getattr(res, 'trend_errors', None):
        out.append('errors: %s' % res.trend_errors)
    if res.window is not None:
        out.append('Qxy %.3f–%.3f' % tuple(res.window))
    if getattr(res, 'rows', None) is not None:
        out.append('rows %d–%d' % tuple(res.rows))
    return '\n'.join(out)


def _sizes(fontsize):
    """Text sizes (pt) of the burn plot: the compact ones it was drawn with
    (``fontsize`` None: the committed figures), or, given a base size (the
    window's, owner 2026-11-26: tick and axis labels at least the size of
    the tab labels), ticks and axis labels at the base and the rest in the
    same proportions as before."""
    if fontsize is None:
        return dict(axis=8, tick=7, second=7, legend=6, summary=7, title=9, resid=6)
    b = float(fontsize)
    return dict(axis=b, tick=b, second=b, legend=0.8 * b, summary=0.75 * b, title=1.1 * b, resid=0.8 * b)


def _residual_panel(ax, c, col, fs=None):
    """The best model's residuals above one burn panel (F74)."""
    fs = fs or _sizes(None)
    from lss_core import residuals as resid
    f = c.fits[c.best]
    rax = resid.panel(ax, True)
    resid.draw(rax, c.t, c.y, f(c.t), c.sigma, color=col)
    dof = max(int(f.n) - len(np.atleast_1d(f.params)), 1)
    rax.text(0.99, 0.92, resid.chi2_label('best: %s' % c.best, f.chi2 / dof), transform=rax.transAxes,
             ha='right', va='top', fontsize=fs['resid'])
    rax.tick_params(labelsize=fs['resid'])
    rax.yaxis.label.set_fontsize(fs['resid'])
    return rax


def plot(res, fig, title='', residuals=False, fontsize=None):
    """Draw a burn result into a matplotlib figure: one panel per quantity
    (GID: intensity, position, FWHM; reflectivity: intensity), the values
    with their errors and every fitted model (the best thick), a dotted
    vertical line at the confident change time; on the right of each panel
    the same quantity normalised, in percent (``normaliser``), with the
    threshold marked; the summary as text to the right of the panels.
    ``residuals``: above each panel, the residuals of its best model,
    (y − fit)/σ, with χ²/dof (F74, lss_core.residuals; off by default).
    ``fontsize``: the base text size (pt; ``_sizes``); None keeps the compact
    sizes of the committed figures. Returns the data axes."""
    fs = _sizes(fontsize)
    fig.clf()
    qs = [q for q in ('intensity', 'centre', 'fwhm') if q in res.values]
    gs = fig.add_gridspec(len(qs), 2, width_ratios=[3.4, 1.0], wspace=0.42, hspace=0.12)
    tt = np.linspace(0, res.span(), 300)
    axes = []
    for k, q in enumerate(qs):
        ax = fig.add_subplot(gs[k, 0], sharex=axes[0] if axes else None)
        axes.append(ax)
        col = COLOURS[q]
        y, s = res.values[q]
        ax.errorbar(res.x, y, s, fmt='o', color=col, ms=3, lw=0.8)
        ax.set_ylabel(UNITS[res.kind].get(q, q), color=col, fontsize=fs['axis'])
        ax.tick_params(axis='y', colors=col, labelsize=fs['tick'])
        ax.tick_params(axis='x', labelsize=fs['tick'])
        c = res.trends.get(q)
        if c is None:
            continue
        for m, f in c.fits.items():
            if f.ok:
                best = m == c.best
                ax.plot(tt, f(tt), STYLES[m], color=col, lw=2 if best else 1, alpha=1.0 if best else 0.45)
        if residuals and c.best in c.fits and c.fits[c.best].ok:
            _residual_panel(ax, c, col, fs)
        ch = c.change
        if ch is not None and np.isfinite(ch.confident) and ch.confident <= tt[-1]:
            ax.axvline(ch.confident, color=col, ls=(0, (1, 3)), lw=1)
        ref, scale, lab = normaliser(c, q)
        if np.isfinite(ref) and np.isfinite(scale) and scale != 0:
            if q == 'centre':
                fwd, inv = (lambda v, r=ref, sc=scale: 100 * (v - r) / sc), (lambda p, r=ref, sc=scale: r + p * sc / 100)
                marks = (-100 * res.threshold, 100 * res.threshold)
            else:
                fwd, inv = (lambda v, sc=scale: 100 * v / sc), (lambda p, sc=scale: p * sc / 100)
                marks = (100 * (1 - res.threshold), 100 * (1 + res.threshold))
            sec = ax.secondary_yaxis('right', functions=(fwd, inv))
            sec.set_ylabel(lab, fontsize=fs['second'], color='0.35')
            sec.tick_params(labelsize=fs['second'], colors='0.35')
            for mk in marks:
                ax.axhline(inv(mk), color='0.6', lw=0.6, ls=(0, (4, 4)))
        if k < len(qs) - 1:
            ax.tick_params(axis='x', labelbottom=False)
    if res.axis == 'dose':
        axes[-1].set_xlabel('Dose since the first frame (%s)' % res.dose_unit, fontsize=fs['axis'])
    else:
        axes[-1].set_xlabel('Time %s (s)' % ('under the beam' if res.time == 'exposure' else 'by the clock'),
                            fontsize=fs['axis'])
    from matplotlib.lines import Line2D
    axes[0].legend(handles=[Line2D([], [], color='k', ls=ls, lw=1, label=m) for m, ls in STYLES.items()
                            if any(m in c.fits and c.fits[m].ok for c in res.trends.values())],
                   fontsize=fs['legend'], frameon=False, ncol=4, loc='lower left', bbox_to_anchor=(0.0, 1.0))
    text = fig.add_subplot(gs[:, 1])
    text.axis('off')
    text.text(0.0, 1.0, summary_text(res), va='top', ha='left', fontsize=fs['summary'], family='monospace',
              transform=text.transAxes)
    if title:
        if fontsize is None:
            fig.suptitle(title, fontsize=fs['title'])
        else:                          # top right, above the summary, clear of the legend over the first panel
            fig.suptitle(title, fontsize=fs['title'], x=0.99, ha='right')
    return axes
