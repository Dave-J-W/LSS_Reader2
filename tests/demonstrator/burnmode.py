"""GID burn line cuts on synthetic replicates: every estimator, with the truth.

A **replicate** is one Poisson draw (seed) of a burn test
(``synthetic.burn_profiles``: one spot measured ``n`` times, the horizontal
profile of each frame, a sharp peak on a broad shoulder and a flat floor,
with a stated change over the test). The truth kept beside it: the
noise-free profiles (``seed=None``), the peak's area, centre and FWHM per
frame, and its parts (peak, shoulder, floor).

Each estimator of ``lss_core.burn.measure_gid`` (``template``, the
default; ``moments``, the legacy burn test's arithmetic; ``fit``, a
Gaussian on a straight background by ``lss_core.peaks``) gives per frame
an intensity, a position and a width, and ``frame_curve`` rebuilds the
curve it fitted to that frame's line cut:

- template: A × the mean frame's shape (less its straight baseline),
  shifted by δ and stretched by w, on a straight background (the
  parameters ``measure_gid`` returns per frame);
- fit: ``FitResult.model``;
- moments: no curve is fitted; shown as its straight baseline plus the
  Gaussian of the same area, centroid and r.m.s. width (a display of what
  the three numbers mean, not a fit).

The values over time go through ``lss_core.burn.analyse`` (the four
trend models of ``lss_core.trends``, compared by AICc, K. P. Burnham and
D. R. Anderson, *Model Selection and Multimodel Inference*, Springer 2002,
https://doi.org/10.1007/b97636; errors from the scatter, as the reader's
GID burns).
"""
import math
from dataclasses import dataclass, field

import numpy as np

from lss_core import burn, trends

from synthetic import burn_profiles as bp

CHANGES = bp.CHANGES
ESTIMATORS = burn.ESTIMATORS
DEFAULT_AMOUNTS = {'none': 0.0, 'fade': 0.2, 'broaden': 0.3, 'shift': 0.004, 'shoulder': 0.2, 'background': 0.5}
CHANGE_LABELS = {'none': 'nothing changes', 'fade': 'peak fades', 'broaden': 'broadens at constant area (P44)',
                 'shift': 'peak shifts', 'shoulder': 'fades under a 3× shoulder', 'background': 'floor rises'}
COLOURS = {'stretched': '#1f77b4', 'moments': '#d62728', 'fit': '#2ca02c'}
QUANTITIES = ('intensity', 'centre', 'fwhm')


@dataclass
class Config:
    """``change`` and ``amount`` as ``burn_profiles.profiles`` (``amount``
    None: ``DEFAULT_AMOUNTS``); ``monitor`` sets the counts (1e7: the
    generator's default, about 2e5 counts at the peak's top per frame);
    ``models``: trend models fitted."""
    change: str = 'broaden'
    amount: float = None
    n: int = 21
    monitor: float = 1e7
    ctime: float = 10.0
    shoulder_scale: float = 3.0
    models: tuple = trends.MODELS

    @property
    def amount_used(self):
        return DEFAULT_AMOUNTS[self.change] if self.amount is None else float(self.amount)

    def draw(self, seed):
        return bp.profiles(self.n, self.change, self.amount_used, ctime=self.ctime, monitor=self.monitor,
                           seed=seed, shoulder_scale=self.shoulder_scale)


@dataclass
class Replicate:
    config: Config
    seed: int
    profiles: list           # noisy (N, 3) Qxy, I, σ per frame
    clean: list              # the same without noise
    truth: object            # burn_profiles.BurnTruth

    @property
    def t(self):
        return self.truth.t

    @property
    def x(self):
        return self.profiles[0][:, 0]

    def duration(self):
        return float(self.config.n * self.config.ctime)

    def truth_at(self, quantity, tt):
        """The true quantity at times ``tt``: every change of the generator
        is linear in t (no ``tau`` here), so a straight line through the
        per-frame truth is exact, t = 0 included. 'intensity' is the peak's
        area."""
        v = getattr(self.truth, 'area' if quantity == 'intensity' else quantity)
        p = np.polyfit(self.truth.t, v, 1)
        return np.polyval(p, np.asarray(tt, float))

    def parts(self, k):
        """The true line cut of frame k in parts: {'peak', 'shoulder',
        'floor', 'total'} on the Qxy grid (lit columns only)."""
        x = bp.X
        lit = ((x > bp.LIT[0]) & (x < bp.LIT[1])).astype(float)
        s = self.truth.fwhm[k] / bp.G
        peak = self.truth.area[k] / (s * math.sqrt(2 * math.pi)) * np.exp(-0.5 * ((x - self.truth.centre[k]) / s) ** 2)
        sh = self.truth.shoulder * np.exp(-0.5 * ((x - bp.SHOULDER[1]) / bp.SHOULDER[2]) ** 2)
        out = dict(peak=lit * peak, shoulder=lit * sh, floor=lit * self.truth.floor[k])
        out['total'] = out['peak'] + out['shoulder'] + out['floor']
        return out


def replicate(config=None, seed=0):
    """Draw replicate ``seed`` of ``config``; the same seed gives the same
    profiles."""
    cfg = config or Config()
    prof, truth = cfg.draw(int(seed))
    clean, _ = cfg.draw(None)
    return Replicate(cfg, int(seed), prof, clean, truth)


@dataclass
class EstimatorResult:
    """One estimator on one replicate: ``values`` {quantity: (y, σ)},
    ``trends`` {quantity: TrendComparison}, the window, the reference fit of
    the mean frame, per-frame details; ``shape``: (x, shape) the template
    (mean frame less its baseline in the window)."""
    name: str
    values: dict = None
    trends: dict = None
    window: tuple = None
    reference: dict = None
    details: list = None
    shape: tuple = None
    error: str = ''
    notes: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.error

    def relative(self, quantity):
        """(y, σ, reference, label): intensity and FWHM over the best trend
        model's value at t = 0; the position as its shift from it (Å⁻¹)."""
        y, s = self.values[quantity]
        c = self.trends.get(quantity) if self.trends else None
        if c is not None and c.fits.get(c.best) is not None and c.fits[c.best].ok:
            ref = float(c.fits[c.best](np.array([0.0]))[0])
        else:
            ref = float(np.nanmean(y))
        if quantity == 'centre':
            return y - ref, s, ref, 'shift (Å⁻¹)'
        return y / ref, s / abs(ref), ref, 'relative to t = 0'


def run_estimator(rep, name, models=None):
    """``EstimatorResult`` of estimator ``name`` on replicate ``rep``; a
    failure is recorded, not raised."""
    out = EstimatorResult(name)
    try:
        values, ref, window, details = burn.measure_gid(rep.profiles, estimator=name)
    except (ValueError, RuntimeError) as e:
        out.error = '%s: %s' % (type(e).__name__, e)
        return out
    out.values, out.reference, out.window, out.details = values, ref, window, details
    x = rep.x
    sel = (x >= window[0]) & (x <= window[1])
    mean = np.mean([p[:, 1] for p in rep.profiles], axis=0)
    xw = x[sel]
    out.shape = (xw, mean[sel] - burn._baseline(xw, mean[sel]))
    bad = sum(1 for d in details if not d.get('ok'))
    if bad:
        out.notes.append('%d frames not fitted' % bad)
    try:
        out.trends = burn.analyse(rep.t, values, models=models or rep.config.models, errors='scatter')
    except (ValueError, RuntimeError, np.linalg.LinAlgError) as e:
        out.trends = {}
        out.notes.append('trends: %s' % e)
    return out


def run_all(rep, names=ESTIMATORS, models=None):
    return {n: run_estimator(rep, n, models) for n in names}


def frame_curve(rep, res, k, n=300):
    """(x, y) of the curve estimator ``res`` fitted to frame k's line cut,
    over its window (module docstring; moments: baseline + the Gaussian of
    the same area, centroid and r.m.s. width). None when the frame failed."""
    if not res.ok or not res.details[k].get('ok', False):
        return None
    lo, hi = res.window
    xx = np.linspace(lo, hi, n)
    if res.name == 'stretched':
        from scipy.interpolate import CubicSpline
        xw, shape = res.shape
        spline = CubicSpline(xw, shape, bc_type='natural', extrapolate=False)
        A, d, w, b0, b1 = res.details[k]['params']
        c = res.reference['centre']
        v = spline(c + (xx - c - d) / w)
        return xx, A * np.where(np.isfinite(v), v, 0.0) + b0 + b1 * (xx - c)
    if res.name == 'fit':
        return xx, res.details[k]['result'].model(xx)
    x = rep.x
    sel = (x >= lo) & (x <= hi)
    xw, y = x[sel], rep.profiles[k][sel, 1]
    k3 = 3
    xl, xr = np.mean(xw[:k3]), np.mean(xw[-k3:])
    yl, yr = np.mean(y[:k3]), np.mean(y[-k3:])
    base = yl + (yr - yl) * (xx - xl) / (xr - xl)
    area, cen, fw = (res.values[q][0][k] for q in QUANTITIES)
    s = fw / bp.G
    return xx, base + area / (s * math.sqrt(2 * math.pi)) * np.exp(-0.5 * ((xx - cen) / s) ** 2)


def true_change(rep, quantity):
    """The true change over the test (t = 0 to its end): relative for
    intensity and FWHM, in Å⁻¹ for the position."""
    v0, v1 = rep.truth_at(quantity, [0.0, rep.duration()])
    return v1 - v0 if quantity == 'centre' else v1 / v0 - 1


def measured_change(res, quantity, T):
    """The change over [0, T] read from the linear trend model: relative for
    intensity and FWHM, Å⁻¹ for the position (NaN without a linear fit)."""
    c = (res.trends or {}).get(quantity)
    if c is None or 'linear' not in c.fits or not c.fits['linear'].ok:
        return math.nan
    v0, v1 = c.fits['linear'](np.array([0.0, T]))
    return float(v1 - v0) if quantity == 'centre' else float(v1 / v0 - 1)


def survey(config=None, seeds=range(30), names=ESTIMATORS):
    """The change over the test read by each estimator (linear model) over
    many replicates, against the truth; and how often each called the
    quantity stable. Returns {estimator: {quantity: dict(true, mean, sd,
    bias, stable)}} and the rows."""
    cfg = config or Config()
    rows = []
    for s in seeds:
        rep = replicate(cfg, s)
        for n in names:
            r = run_estimator(rep, n, models=('constant', 'linear'))
            for q in QUANTITIES:
                c = (r.trends or {}).get(q)
                rows.append(dict(seed=s, estimator=n, quantity=q, true=true_change(rep, q),
                                 measured=measured_change(r, q, rep.duration()) if r.ok else math.nan,
                                 stable=bool(c.stable) if c is not None and c.stable is not None else None))
    out = {}
    for n in names:
        out[n] = {}
        for q in QUANTITIES:
            d = [r for r in rows if r['estimator'] == n and r['quantity'] == q]
            m = np.array([r['measured'] for r in d], float)
            ok = np.isfinite(m)
            st = [r['stable'] for r in d if r['stable'] is not None]
            out[n][q] = dict(true=d[0]['true'], mean=float(np.mean(m[ok])) if ok.any() else math.nan,
                             sd=float(np.std(m[ok], ddof=1)) if ok.sum() > 1 else math.nan,
                             bias=float(np.mean(m[ok]) - d[0]['true']) if ok.any() else math.nan,
                             stable=float(np.mean(st)) if st else math.nan, n=int(ok.sum()))
    return out, rows
