"""Finding and fitting peaks in one-dimensional data: line cuts, GID profiles,
fluorescence spectra (owner, 2026-11-21: "build that into a module that can
be reused, perhaps also with MCA data").

    from lss_core import peaks
    res = peaks.fit(x, y, sigma)                         # automatic: find, then fit
    res = peaks.fit(x, y, sigma, peaks.FitOptions(shape='pseudo-voigt', background='quadratic', n_peaks=2))
    res.peaks[0].centre, res.peaks[0].fwhm, res.peaks[0].area, res.chi2_dof, res.model(x)
    series = peaks.fit_series(energy, spectra, sigmas, peaks.FitOptions(centres=(6.40,)))   # EXAFS / XFNTR

Finding: the data minus a running median (a background that follows slow
changes but not peaks), divided by the noise σ (given, or estimated from
the scatter of neighbouring points); peaks are local maxima whose three
central points together stand ``min_prominence`` σ above the background
(√3 × their mean excess in σ; pure noise of 200 points rarely reaches 5),
strongest first, with a first
estimate of their width at half height (``scipy.signal``).

Fitting: all peaks of a group together (peaks closer than about three
widths share one window) with a polynomial background (none, constant,
linear, quadratic, cubic) on the window, least squares weighted by σ when
given (``absolute_sigma``; the χ²/dof then says whether σ describes the
scatter), unweighted otherwise (errors scaled by the residual). Starting
values come from the data; the centre is bounded to the window, the width
to [the point spacing, the window], the height to ≥ 0. A fit that fails or
whose result is implausible (centre at the window's edge, width at a
bound) is reported with ``ok`` False and a ``message`` instead of numbers
that look fine.

Areas: Gaussian h·FWHM·√(π / 4 ln 2) (= h σ √(2π)), Lorentzian h·π·FWHM/2,
pseudo-Voigt the η-weighted sum; errors from the fit's covariance.

Series (``fit_series``): the owner's rule for MCA spectra (2026-11-19):
"when it comes to fitting a series of MCA spectra it can mostly assume the
width and location of the peak is constant (just sum all the spectra, fit
that, then fit all the individuals)". The sum fixes the centres, widths
and shape; each spectrum is then a linear least-squares problem for the
heights and the background, which cannot fail to converge.
"""
import math
from dataclasses import dataclass, field, replace

import numpy as np

SHAPES = ('gaussian', 'lorentzian', 'pseudo-voigt')
BACKGROUNDS = {'none': -1, 'constant': 0, 'linear': 1, 'quadratic': 2, 'cubic': 3}
_G = 2 * math.sqrt(2 * math.log(2))           # FWHM / σ of a Gaussian
_GAREA = math.sqrt(math.pi / (4 * math.log(2)))   # Gaussian area / (height · FWHM)
MISFIT_CHI2 = 10.0       # a weighted fit above this χ²/dof is reported as not describing the data


@dataclass
class FitOptions:
    """How to find and fit. ``n_peaks`` 0: as many as are found (up to
    ``max_peaks``); ``centres``: start (or, with ``fix_centres``, fix) the
    peaks there instead of finding them; ``min_prominence``: how far above
    the background, in noise σ, a peak must stand to be found; ``window``:
    half width of a peak's fit window in x units (0: 3 × its estimated
    FWHM, at least 6 points); ``x_range``: (low, high) of x to use (None:
    all); ``fwhm``: a fixed FWHM for every peak (0: fitted);
    ``scale_errors``: scale the errors by √(χ²/dof) even when σ is given
    (when the model may not describe every point; the distance calibration
    uses it, so that a frame whose own fit is poor weighs less)."""
    shape: str = 'gaussian'
    background: str = 'linear'
    n_peaks: int = 0
    max_peaks: int = 3
    min_prominence: float = 5.0
    window: float = 0.0
    x_range: tuple = None
    centres: tuple = ()
    fix_centres: bool = False
    fwhm: float = 0.0
    scale_errors: bool = False

    def check(self):
        if self.shape not in SHAPES:
            raise ValueError('shape %r: use one of %s' % (self.shape, ', '.join(SHAPES)))
        if self.background not in BACKGROUNDS:
            raise ValueError('background %r: use one of %s' % (self.background, ', '.join(BACKGROUNDS)))
        return self


@dataclass
class Peak:
    """One fitted peak: centre, FWHM, height above the background, area (in
    x units × y units), each with its error; ``eta`` the Lorentzian fraction
    of a pseudo-Voigt (0 Gaussian, 1 Lorentzian)."""
    centre: float
    centre_err: float
    fwhm: float
    fwhm_err: float
    height: float
    height_err: float
    area: float
    area_err: float
    shape: str = 'gaussian'
    eta: float = 0.0


@dataclass
class FitResult:
    """``peaks`` (strongest first); ``background`` coefficients of the
    polynomial in (x − ``x0``) / ``xs``; ``chi2_dof`` (weighted fits:
    against the given σ); ``window`` the x range fitted; ``points`` used;
    ``ok`` and ``message``; ``found``: what the search found (centre,
    height, fwhm, prominence in σ)."""
    peaks: list
    background: np.ndarray
    x0: float
    xs: float
    chi2_dof: float
    window: tuple
    points: int
    ok: bool
    message: str = ''
    options: FitOptions = None
    found: list = field(default_factory=list)

    def background_at(self, x):
        x = np.asarray(x, float)
        if not len(self.background):
            return np.zeros_like(x)
        return np.polyval(self.background[::-1], (x - self.x0) / self.xs)

    def model(self, x):
        """The fitted curve (all peaks plus background) at ``x``."""
        x = np.asarray(x, float)
        y = self.background_at(x)
        for p in self.peaks:
            y = y + _profile(x, p.centre, p.fwhm, p.eta, p.shape) * p.height
        return y

    def table(self):
        """Rows (index, centre, ±, FWHM, ±, height, ±, area, ±) for display
        and export."""
        return [(k + 1, p.centre, p.centre_err, p.fwhm, p.fwhm_err, p.height, p.height_err, p.area, p.area_err)
                for k, p in enumerate(self.peaks)]

    def summary(self, fmt='%.5g'):
        if not self.peaks:
            return self.message
        parts = []
        for k, p in enumerate(self.peaks):
            parts.append(('peak %d: centre ' + fmt + ' ± %.2g, FWHM ' + fmt + ' ± %.2g, area ' + fmt + ' ± %.2g')
                         % (k + 1, p.centre, p.centre_err, p.fwhm, p.fwhm_err, p.area, p.area_err))
        return '; '.join(parts) + '; chi2/dof %.2f' % self.chi2_dof + (' (%s)' % self.message if self.message else '')


def _profile(x, c, fwhm, eta, shape):
    """Unit-height profile."""
    fwhm = max(abs(fwhm), 1e-300)
    g = np.exp(-0.5 * ((x - c) / (fwhm / _G)) ** 2)
    if shape == 'gaussian':
        return g
    lor = 1.0 / (1.0 + ((x - c) / (fwhm / 2)) ** 2)
    if shape == 'lorentzian':
        return lor
    return eta * lor + (1 - eta) * g


def _area(h, fwhm, eta, shape):
    ga, la = h * fwhm * _GAREA, h * math.pi * fwhm / 2
    return {'gaussian': ga, 'lorentzian': la}.get(shape, eta * la + (1 - eta) * ga)


def noise_sigma(y, sigma=None):
    """σ per point: ``sigma`` where given and > 0, otherwise the scatter of
    neighbouring points (median absolute second difference / √6 / 0.6745),
    which a smooth signal does not inflate."""
    y = np.asarray(y, float)
    if sigma is not None:
        s = np.asarray(sigma, float)
        good = np.isfinite(s) & (s > 0)
        if good.any():
            return np.where(good, s, np.median(s[good]))
    d2 = np.diff(y, 2) if len(y) > 2 else np.diff(y)
    est = np.median(np.abs(d2 - np.median(d2))) / 0.6745 / math.sqrt(6) if len(d2) else 0.0
    if not est > 0:
        est = max(np.std(y), 1e-300)
    return np.full(len(y), est)


def baseline(y, width):
    """Running median over ``width`` points (odd): a background that
    follows slow changes but not peaks narrower than about width / 3."""
    y = np.asarray(y, float)
    h = max(int(width) // 2, 1)
    pad = np.concatenate([np.full(h, y[0]), y, np.full(h, y[-1])])
    return np.array([np.median(pad[i:i + 2 * h + 1]) for i in range(len(y))])


def find_peaks(x, y, sigma=None, max_peaks=3, min_prominence=5.0, x_range=None):
    """Peaks standing out of the data, strongest first: dicts with centre,
    height (above the running-median background), fwhm (first estimate, at
    half height) and prominence (in noise σ). ``x`` must be monotonic."""
    from scipy.signal import find_peaks as sp_find
    x, y = np.asarray(x, float), np.asarray(y, float)
    s = noise_sigma(y, sigma)
    sel = np.isfinite(x) & np.isfinite(y)
    if x_range is not None:
        sel &= (x >= min(x_range)) & (x <= max(x_range))
    idx = np.flatnonzero(sel)
    if len(idx) < 5:
        return []
    order = np.argsort(x[idx])
    idx = idx[order]
    xx, yy, ss = x[idx], y[idx], s[idx]
    base = baseline(yy, max(len(yy) // 4, 9) | 1)
    z = (yy - base) / ss
    zs = np.convolve(z, np.ones(3) / 3, 'same')                # a 3-point average: single noisy points do not count
    pk, props = sp_find(zs, height=min_prominence / math.sqrt(3) * 1.0, prominence=min_prominence / 2)
    pk = np.array([k for k in pk if z[max(k - 1, 0):k + 2].mean() * math.sqrt(min(3, len(z[max(k - 1, 0):k + 2])))
                   >= min_prominence], int)
    if not len(pk):
        return []
    ex = np.convolve(yy - base, np.ones(5) / 5, 'same')          # smoothed excess: noise does not cut the width short
    out = []
    for k in pk:
        lo_, hi_ = max(k - 3, 0), min(k + 4, len(ex))
        m = lo_ + int(np.argmax(ex[lo_:hi_]))                    # the smoothed maximum near the found point
        half = ex[m] / 2
        i = m
        while i > 0 and ex[i] > half:
            i -= 1
        j = m
        while j < len(ex) - 1 and ex[j] > half:
            j += 1
        fw = abs(xx[j] - xx[i]) if j > i else abs(xx[min(m + 1, len(xx) - 1)] - xx[max(m - 1, 0)])
        out.append(dict(centre=float(xx[m]), height=float(yy[m] - base[m]), fwhm=float(fw), prominence=float(z[k])))
    out.sort(key=lambda d: -d['prominence'])
    return out[:max_peaks]


def _groups(found, window_of):
    """Peaks whose windows overlap are fitted together."""
    found = sorted(found, key=lambda d: d['centre'])
    groups, cur = [], []
    for d in found:
        if cur and d['centre'] - window_of(d) > max(c['centre'] + window_of(c) for c in cur):
            groups.append(cur)
            cur = []
        cur.append(d)
    if cur:
        groups.append(cur)
    return groups


def fit(x, y, sigma=None, options=None):
    """Find (unless ``options.centres``) and fit peaks; returns a
    ``FitResult`` with every peak found. Peaks are fitted in groups that
    share a window; with several groups each has its own background, and
    the result's background is the strongest group's (``results``: use
    ``fit_all`` for one result per group)."""
    res = fit_all(x, y, sigma, options)
    if len(res) == 1:
        return res[0]
    good = [r for r in res if r.ok]
    if not good:
        return res[0]
    best = max(good, key=lambda r: max(p.height for p in r.peaks))
    pk = sorted([p for r in good for p in r.peaks], key=lambda p: -p.height)
    bad = [r.message for r in res if not r.ok]
    return replace(best, peaks=pk, message='; '.join(bad), found=res[0].found)


def fit_all(x, y, sigma=None, options=None):
    """Like ``fit``, one ``FitResult`` per group of peaks sharing a window."""
    o = (options or FitOptions()).check()
    x, y = np.asarray(x, float), np.asarray(y, float)
    given = sigma is not None and np.any(np.asarray(sigma, float) > 0)
    s = noise_sigma(y, sigma)
    sel = np.isfinite(x) & np.isfinite(y) & np.isfinite(s)
    if o.x_range is not None:
        sel &= (x >= min(o.x_range)) & (x <= max(o.x_range))
    xx, yy, ss = x[sel], y[sel], s[sel]
    order = np.argsort(xx)
    xx, yy, ss = xx[order], yy[order], ss[order]
    step = float(np.median(np.diff(xx))) if len(xx) > 1 else 1.0
    empty = lambda msg, found=(): [FitResult([], np.zeros(0), 0.0, 1.0, float('nan'), (float('nan'),) * 2, 0, False,
                                             msg, o, list(found))]
    if len(xx) < 5:
        return empty('too few points to fit (%d)' % len(xx))
    found = find_peaks(xx, yy, ss, max_peaks=max(o.max_peaks, o.n_peaks, len(o.centres), 1),
                       min_prominence=o.min_prominence)
    if o.centres:
        seeds = []
        for c in o.centres:
            near = [d for d in found if abs(d['centre'] - c) < 3 * d['fwhm']]
            fw = o.fwhm or (near[0]['fwhm'] if near else 5 * step)
            k = int(np.argmin(np.abs(xx - c)))
            seeds.append(dict(centre=float(c), height=float(max(yy[k] - np.median(yy), 0.0)), fwhm=fw, prominence=0.0))
    else:
        n = o.n_peaks if o.n_peaks > 0 else o.max_peaks
        seeds = found[:n]
        if o.n_peaks > len(seeds):                      # asked for more than stand out: take the next maxima
            base = baseline(yy, max(len(yy) // 4, 9) | 1)
            ex = yy - base
            for k in np.argsort(ex)[::-1]:
                if len(seeds) >= o.n_peaks:
                    break
                if all(abs(xx[k] - d['centre']) > 3 * d['fwhm'] for d in seeds):
                    seeds.append(dict(centre=float(xx[k]), height=float(ex[k]), fwhm=o.fwhm or 5 * step,
                                      prominence=float(ex[k] / np.median(ss))))
    if not seeds:
        return empty('no peak stands %.1f sigma above the background (Fit options: lower the threshold, or give '
                     'the number of peaks or their centres)' % o.min_prominence, found)
    if o.fwhm:
        for d in seeds:
            d['fwhm'] = o.fwhm
    half = (lambda d: o.window) if o.window > 0 else (lambda d: max(3 * d['fwhm'], 6 * abs(step)))
    out = []
    for grp in _groups(seeds, half):
        lo = min(d['centre'] - half(d) for d in grp)
        hi = max(d['centre'] + half(d) for d in grp)
        w = (xx >= lo) & (xx <= hi)
        out.append(_fit_group(xx[w], yy[w], ss[w], given, grp, o, abs(step)))
        out[-1].found = found
    return out


def _fit_group(x, y, s, weighted, seeds, o, step):
    from scipy.optimize import curve_fit
    nb = BACKGROUNDS[o.background] + 1
    npk = len(seeds)
    x0 = float(0.5 * (x.min() + x.max())) if len(x) else 0.0
    xs = float(max(0.5 * (x.max() - x.min()), 1e-300)) if len(x) else 1.0
    nfree = npk * (1 + (not o.fix_centres) + (not o.fwhm) + (o.shape == 'pseudo-voigt')) + nb
    if len(x) < nfree + 2:
        return FitResult([], np.zeros(0), x0, xs, float('nan'), (float(x.min()) if len(x) else float('nan'),
                         float(x.max()) if len(x) else float('nan')), len(x), False,
                         'too few points in the window (%d) for %d parameters' % (len(x), nfree), o)
    u = (x - x0) / xs
    if nb:
        edge = np.r_[np.arange(min(3, len(x))), np.arange(max(len(x) - 3, 0), len(x))]
        b0 = np.polyfit(u[edge], y[edge], min(nb - 1, 1))[::-1].tolist() + [0.0] * max(nb - 2, 0)
        b0 = b0[:nb]
    else:
        b0 = []
    span = float(x.max() - x.min())

    def unpack(p):
        i, pks = 0, []
        for d in seeds:
            h = p[i]; i += 1
            c = d['centre'] if o.fix_centres else p[i]
            i += 0 if o.fix_centres else 1
            fw = o.fwhm if o.fwhm else p[i]
            i += 0 if o.fwhm else 1
            eta = p[i] if o.shape == 'pseudo-voigt' else (1.0 if o.shape == 'lorentzian' else 0.0)
            i += 1 if o.shape == 'pseudo-voigt' else 0
            pks.append((h, c, fw, eta))
        return pks, np.asarray(p[i:])

    def model(xv, *p):
        pks, b = unpack(p)
        yv = np.polyval(b[::-1], (xv - x0) / xs) if len(b) else np.zeros_like(xv)
        for h, c, fw, eta in pks:
            yv = yv + h * _profile(xv, c, fw, eta, o.shape)
        return yv

    p0, lo, hi = [], [], []
    bg0 = np.polyval(np.asarray(b0)[::-1], u) if b0 else np.zeros_like(x)
    for d in seeds:
        k = int(np.argmin(np.abs(x - d['centre'])))
        h0 = max(float(y[k] - bg0[k]), 1e-12 * max(np.abs(y).max(), 1e-300))
        p0.append(h0); lo.append(0.0); hi.append(np.inf)
        if not o.fix_centres:
            p0.append(float(np.clip(d['centre'], x.min(), x.max())))
            lo.append(float(x.min())); hi.append(float(x.max()))
        if not o.fwhm:
            p0.append(float(np.clip(d['fwhm'], step, span))); lo.append(float(step) * 0.5); hi.append(span * 2)
        if o.shape == 'pseudo-voigt':
            p0.append(0.5); lo.append(0.0); hi.append(1.0)
    p0 += b0
    lo += [-np.inf] * nb
    hi += [np.inf] * nb
    notes = []
    unw = None
    if weighted:                           # an unweighted fit first: a good start where the error bars span orders
        try:                               # of magnitude, and a fallback if the weighted fit does not converge
            unw = curve_fit(model, x, y, p0=p0, bounds=(lo, hi), x_scale='jac', max_nfev=5000)
            p0 = unw[0]
        except (RuntimeError, ValueError):
            unw = None
    try:
        popt, pcov = curve_fit(model, x, y, p0=p0, sigma=s, absolute_sigma=bool(weighted) and not o.scale_errors,
                               bounds=(lo, hi), x_scale='jac', max_nfev=20000)
    except (RuntimeError, ValueError) as e:
        if unw is None:
            return FitResult([], np.zeros(0), x0, xs, float('nan'), (float(x.min()), float(x.max())), len(x), False,
                             'the fit did not converge (%s)' % str(e).split('\n')[0][:80], o)
        popt, pcov = unw
        notes.append('the weighted fit did not converge: unweighted result, errors from the scatter')
    perr = np.sqrt(np.clip(np.diag(pcov), 0, None)) if np.all(np.isfinite(pcov)) else np.full(len(popt), np.nan)
    resid = (y - model(x, *popt)) / s
    dof = max(len(x) - len(popt), 1)
    chi2 = float(np.sum(resid ** 2) / dof)
    pks, b = unpack(popt)
    _, berr = unpack(perr)
    out, i, msgs = [], 0, []
    for d, (h, c, fw, eta) in zip(seeds, pks):
        he = perr[i]; i += 1
        ce = 0.0
        if not o.fix_centres:
            ce = perr[i]; i += 1
        fe = 0.0
        if not o.fwhm:
            fe = perr[i]; i += 1
        if o.shape == 'pseudo-voigt':
            i += 1
        area = _area(h, fw, eta, o.shape)
        ae = abs(area) * math.sqrt((he / h) ** 2 + (fe / fw) ** 2) if h > 0 and fw > 0 else float('nan')
        out.append(Peak(float(c), float(ce), float(abs(fw)), float(fe), float(h), float(he), float(area), float(ae),
                        o.shape, float(eta)))
        tol = 0.02 * span
        if not o.fix_centres and (c - x.min() < tol or x.max() - c < tol):
            msgs.append('peak at %.5g is at the edge of its window' % c)
        if not o.fwhm and (fw <= 0.51 * step or fw >= 1.99 * span):
            msgs.append('peak at %.5g has a width at its limit (%.3g)' % (c, fw))
        if h <= 0:
            msgs.append('peak at %.5g has no height' % c)
    out.sort(key=lambda p: -p.height)
    if weighted and not o.scale_errors and chi2 > MISFIT_CHI2:
        notes.append('the model does not describe the data (chi2/dof %.3g): try another shape or background' % chi2)
    return FitResult(out, np.asarray(b, float), x0, xs, chi2, (float(x.min()), float(x.max())), len(x), not msgs,
                     '; '.join(msgs + notes), o)


def fit_lines(energy, counts, lines, sigma=None, options=None):
    """Fluorescence lines at known energies ``lines`` (centres start there;
    ``options.fix_centres`` to keep them): ``fit`` with those centres."""
    o = replace(options or FitOptions(), centres=tuple(float(v) for v in lines), n_peaks=len(lines))
    return fit(energy, counts, sigma, o)


def line_index(result, centres=()):
    """Index in ``result.peaks`` of the line asked for: the peak nearest the
    first of ``centres`` (the element's line, placed first; F90), or the
    strongest (index 0) when no centre is given. None when nothing was
    fitted. ``fit_series`` keeps its results' peaks in its sum's order, so
    the same index serves every spectrum."""
    if not result.peaks:
        return None
    if not centres:
        return 0
    c = float(centres[0])
    return int(np.argmin([abs(p.centre - c) for p in result.peaks]))


def fit_series(x, spectra, sigmas=None, options=None):
    """A series of spectra with the same lines (MCA, EXAFS, XFNTR): the sum
    of all spectra is fitted (``fit``) for the centres, widths and shape;
    each spectrum is then fitted with those fixed, its heights and
    background by linear least squares (weighted by its σ when given).
    Returns (the sum's FitResult, [FitResult per spectrum])."""
    o = (options or FitOptions()).check()
    Y = np.asarray(spectra, float)
    S = None if sigmas is None else np.asarray(sigmas, float)
    tot = Y.sum(axis=0)
    st = None if S is None else np.sqrt(np.sum(S ** 2, axis=0))
    ref = fit(x, tot, st, o)
    if not ref.ok or not ref.peaks:
        return ref, []
    x = np.asarray(x, float)
    lo, hi = ref.window
    w = (x >= lo) & (x <= hi) & np.isfinite(x)
    xw = x[w]
    nb = BACKGROUNDS[o.background] + 1
    u = (xw - ref.x0) / ref.xs
    cols = [_profile(xw, p.centre, p.fwhm, p.eta, p.shape) for p in ref.peaks] + [u ** j for j in range(nb)]
    A = np.column_stack(cols)
    out = []
    for k in range(len(Y)):
        y = Y[k][w]
        s = noise_sigma(y, None if S is None else S[k][w])
        Aw = A / s[:, None]
        coef, *_ = np.linalg.lstsq(Aw, y / s, rcond=None)
        cov = np.linalg.pinv(Aw.T @ Aw)
        dof = max(len(y) - A.shape[1], 1)
        chi2 = float(np.sum(((y - A @ coef) / s) ** 2) / dof)
        err = np.sqrt(np.clip(np.diag(cov), 0, None))
        if S is None:                                     # unweighted: scale errors by the residual
            err = err * math.sqrt(chi2)
        pk = []
        for j, p in enumerate(ref.peaks):
            h, he = float(coef[j]), float(err[j])
            pk.append(Peak(p.centre, 0.0, p.fwhm, 0.0, h, he, _area(h, p.fwhm, p.eta, p.shape),
                           abs(_area(he, p.fwhm, p.eta, p.shape)), p.shape, p.eta))
        out.append(FitResult(pk, coef[len(ref.peaks):], ref.x0, ref.xs, chi2, ref.window, int(w.sum()), True,
                             'centres and widths from the sum of %d spectra' % len(Y), o))
    return ref, out


# ---- edges and plateaus: alignment scans, half-cuts (owner, 2026-11-21; F22a, F43) ----

def _step(x, c, fwhm):
    """Rising unit step whose derivative is a Gaussian of this FWHM (an
    error function): a half-cut through a Gaussian beam."""
    from scipy.special import erf
    return 0.5 * (1 + erf((x - c) / (max(abs(fwhm), 1e-300) / _G * math.sqrt(2))))


# Evaluations allowed to the final edge or box fit. Converged fits on the NX
# school scans used at most 166 (2026-11-23); a box fitted to a Gaussian (any
# alignment peak) cannot converge, and the former 20000 took 9.5 s for
# 21 points on every plot of such a scan before failing all the same.
SHAPE_FIT_MAX_NFEV = 2000


def _shape_fit(x, y, s, weighted, model, p0, lo, hi, kind, unpack, background_n):
    """Shared least squares for edges and boxes; ``unpack`` turns the fitted
    parameters (and their errors) into (Peak, background)."""
    from scipy.optimize import curve_fit
    try:
        if weighted:
            try:
                p0 = curve_fit(model, x, y, p0=p0, bounds=(lo, hi), x_scale='jac', max_nfev=5000)[0]
            except (RuntimeError, ValueError):
                pass
        popt, pcov = curve_fit(model, x, y, p0=p0, sigma=s, absolute_sigma=bool(weighted), bounds=(lo, hi),
                               x_scale='jac', max_nfev=SHAPE_FIT_MAX_NFEV)
    except (RuntimeError, ValueError) as e:
        return None, 'the %s fit did not converge (%s)' % (kind, str(e).split('\n')[0][:60])
    perr = np.sqrt(np.clip(np.diag(pcov), 0, None)) if np.all(np.isfinite(pcov)) else np.full(len(popt), np.nan)
    dof = max(len(x) - len(popt), 1)
    rss = float(np.sum(((y - model(x, *popt)) / s) ** 2))
    pk, b = unpack(popt, perr)
    return (pk, b, rss / dof, rss, len(popt)), ''


def fit_edge(x, y, sigma=None, background='linear'):
    """One step, rising or falling (a half-cut, a knife edge, a slit
    blade): returns a FitResult whose one Peak has ``centre`` (the edge),
    ``fwhm`` (the width of the edge: for a half-cut through a Gaussian beam,
    the beam's FWHM in x units) and ``height`` (the step, signed); shape
    'edge'."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    weighted = sigma is not None and np.any(np.asarray(sigma, float) > 0)
    s = noise_sigma(y, sigma)
    o = np.argsort(x)
    x, y, s = x[o], y[o], s[o]
    nb = BACKGROUNDS[background] + 1
    x0, xs = float(0.5 * (x.min() + x.max())), float(max(0.5 * (x.max() - x.min()), 1e-300))
    if len(x) < nb + 5:
        return FitResult([], np.zeros(0), x0, xs, float('nan'), (float(x.min()), float(x.max())), len(x), False,
                         'too few points for an edge', FitOptions(background=background))
    ys = np.convolve(y, np.ones(3) / 3, 'same')
    g = np.gradient(ys[1:-1], x[1:-1])
    k = int(np.argmax(np.abs(g))) + 1
    step = float(np.median(np.diff(x)))
    n4 = max(len(y) // 4, 2)
    h0 = float(np.mean(y[-n4:]) - np.mean(y[:n4]))
    w0 = max(abs(h0 / g[k - 1]) * 0.94 if g[k - 1] else 3 * step, 2 * step)
    b0 = [float(np.mean(y[:n4]))] + [0.0] * (nb - 1) if nb else []

    def model(xv, c, w, h, *b):
        bg = np.polyval(np.asarray(b)[::-1], (xv - x0) / xs) if b else 0.0
        return bg + h * _step(xv, c, w)

    span = float(x.max() - x.min())

    def unpack(p, e):
        return (Peak(float(p[0]), float(e[0]), float(abs(p[1])), float(e[1]), float(p[2]), float(e[2]), float('nan'),
                     float('nan'), 'edge'), np.asarray(p[3:], float))
    r, msg = _shape_fit(x, y, s, weighted, model, [float(x[k]), w0, h0] + b0,
                        [float(x.min()), 0.3 * step, -np.inf] + [-np.inf] * nb,
                        [float(x.max()), 2 * span, np.inf] + [np.inf] * nb, 'edge', unpack, nb)
    if r is None:
        return FitResult([], np.zeros(0), x0, xs, float('nan'), (float(x.min()), float(x.max())), len(x), False, msg,
                         FitOptions(background=background))
    pk, b, chi2, rss, npar = r
    res = FitResult([pk], b, x0, xs, chi2, (float(x.min()), float(x.max())), len(x), True, '',
                    FitOptions(background=background))
    res.model = lambda xv, _p=pk, _r=res: _r.background_at(xv) + _p.height * _step(np.asarray(xv, float), _p.centre, _p.fwhm)
    res.kind, res.rss, res.npar = 'edge', rss, npar
    return res


def fit_box(x, y, sigma=None, background='linear'):
    """A plateau between two edges (a slit scan, a box-shaped beam):
    ``centre`` the midpoint, ``fwhm`` the distance between the edges,
    ``height`` the plateau; ``edges`` on the result: ((centre, width) of
    the rising edge, (centre, width) of the falling one)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    weighted = sigma is not None and np.any(np.asarray(sigma, float) > 0)
    s = noise_sigma(y, sigma)
    o = np.argsort(x)
    x, y, s = x[o], y[o], s[o]
    nb = BACKGROUNDS[background] + 1
    x0, xs = float(0.5 * (x.min() + x.max())), float(max(0.5 * (x.max() - x.min()), 1e-300))
    fail = lambda msg: FitResult([], np.zeros(0), x0, xs, float('nan'), (float(x.min()), float(x.max())), len(x),
                                 False, msg, FitOptions(background=background))
    if len(x) < nb + 7:
        return fail('too few points for a box')
    step = float(np.median(np.diff(x)))
    span = float(x.max() - x.min())
    base = float(np.median(np.r_[y[:2], y[-2:]]))
    top = float(np.max(y))
    above = np.flatnonzero(y > base + 0.5 * (top - base))
    c1, c2 = (float(x[above[0]]), float(x[above[-1]])) if len(above) >= 2 else (x0 - xs / 2, x0 + xs / 2)
    b0 = [base] + [0.0] * (nb - 1) if nb else []
    edges = []

    def model(xv, a, b_, w1, w2, h, *bb):
        bg = np.polyval(np.asarray(bb)[::-1], (xv - x0) / xs) if bb else 0.0
        return bg + h * (_step(xv, a, w1) - _step(xv, b_, w2))

    def unpack(p, e):
        (a, wa), (b_, wb) = sorted(((p[0], abs(p[2])), (p[1], abs(p[3]))))
        edges[:] = [(float(a), float(wa)), (float(b_), float(wb))]
        return (Peak(float(0.5 * (a + b_)), float(0.5 * math.hypot(e[0], e[1])), float(b_ - a),
                     float(math.hypot(e[0], e[1])), float(p[4]), float(e[4]), float(p[4] * (b_ - a)), float('nan'),
                     'box'), np.asarray(p[5:], float))
    r, msg = _shape_fit(x, y, s, weighted, model, [c1, c2, 2 * step, 2 * step, top - base] + b0,
                        [float(x.min()), float(x.min()), 0.3 * step, 0.3 * step, -np.inf] + [-np.inf] * nb,
                        [float(x.max()), float(x.max()), span, span, np.inf] + [np.inf] * nb, 'box', unpack, nb)
    if r is None:
        return fail(msg)
    pk, b, chi2, rss, npar = r
    res = FitResult([pk], b, x0, xs, chi2, (float(x.min()), float(x.max())), len(x), True, '',
                    FitOptions(background=background))
    (a, wa), (b_, wb) = edges
    res.model = lambda xv: res.background_at(xv) + pk.height * (_step(np.asarray(xv, float), a, wa) -
                                                                 _step(np.asarray(xv, float), b_, wb))
    res.kind, res.rss, res.npar, res.edges = 'box', rss, npar, tuple(edges)
    return res


# A scan whose background alone fits it this well (χ² p-value above FLAT_P)
# shows no peak, edge or plateau, and fit_scan does not look for one. 0.05:
# a feature needs only weak evidence (5 %) to be fitted; 95 % of truly flat
# scans skip the fits (owner, 2026-11-23; OUTPUT_DECISIONS).
FLAT_P = 0.05


def is_flat(x, y, s, background='linear'):
    """(flat, χ², dof) of the background polynomial alone, fitted by
    weighted linear least squares to (x, y) with errors ``s``; ``flat``
    when its χ² p-value exceeds FLAT_P. Too few points: never flat."""
    from scipy.stats import chi2 as chi2_dist
    x, y, s = np.asarray(x, float), np.asarray(y, float), np.asarray(s, float)
    order = BACKGROUNDS[background]
    dof = len(x) - (order + 1)
    good = np.isfinite(x) & np.isfinite(y) & np.isfinite(s) & (s > 0)
    if dof < 3 or not good.all():
        return False, float('nan'), max(dof, 1)
    if order < 0:
        r = y / s
    else:
        x0, xs = 0.5 * (x.min() + x.max()), max(0.5 * (x.max() - x.min()), 1e-300)
        u = (x - x0) / xs
        A = np.vander(u, order + 1, increasing=True) / s[:, None]
        coef = np.linalg.lstsq(A, y / s, rcond=None)[0]
        r = y / s - A @ coef
    chi2 = float(np.sum(r ** 2))
    return bool(chi2_dist.sf(chi2, dof) > FLAT_P), chi2, dof


# Sample-height scans (owner, 2026-11-23): "not a tough scan to do, we always
# get good signal, and the FWHM is always greater than 20 microns". sh is in
# mm (NX school: 8 µm steps, fitted widths 47-82 µm).
HEIGHT_SCAN_MIN_FWHM = 0.020
# (highest - lowest) / lowest of the 3-point smoothed curve: the NX school
# height scans give 7-10, the stopped scan 4 (noise) 0.6.
HEIGHT_SCAN_MIN_SIGNAL_TO_BACKGROUND = 2.0


def is_height_scan(command):
    """True for a sample-height scan: ascan, a2scan, dscan or d2scan whose
    first motor is sh, over a range (start != end). ``command`` with or
    without its leading '#S n'."""
    w = str(command).split()
    if w and w[0] == '#S':
        w = w[2:]
    return len(w) > 3 and w[0] in ('ascan', 'a2scan', 'dscan', 'd2scan') and w[1] == 'sh' and w[2] != w[3]


def height_scan_options():
    """The keyword arguments of fit_scan for a sample-height scan."""
    return dict(min_fwhm=HEIGHT_SCAN_MIN_FWHM, min_signal_to_background=HEIGHT_SCAN_MIN_SIGNAL_TO_BACKGROUND)


def signal_to_background(y):
    """(highest - lowest) / lowest of y smoothed over 3 points: a peak, a
    plateau and an edge alike, and one spike does not count. Infinite when
    the lowest level is not positive (background-subtracted data)."""
    y = np.asarray(y, float)
    ys = np.convolve(y, np.ones(3) / 3, 'valid') if len(y) >= 3 else y
    lo, hi = float(np.min(ys)), float(np.max(ys))
    return (hi - lo) / lo if lo > 0 else float('inf')


def fit_scan(x, y, sigma=None, background='linear', min_fwhm=None, min_signal_to_background=None):
    """The shape of an alignment or half-cut scan: a peak (Gaussian), an
    edge (``fit_edge``) or a box (``fit_box``), whichever the data support
    best by the Akaike criterion (χ² + 2 × parameters); returns the
    FitResult with ``kind`` 'peak', 'edge' or 'box' and ``candidates``
    (kind → FitResult) for the others. Replaces the window's tanh box model
    (P9), which reported 0.406 for a Gaussian of FWHM 0.471.

    A scan with no structure above its noise (``is_flat``: the background
    alone fits it, χ² p-value above FLAT_P) is not fitted: ``kind`` 'flat',
    ``ok`` False (owner, 2026-11-23: no point hammering a flat noisy line
    with fits).

    ``min_signal_to_background``: below it (``signal_to_background``) the
    scan is not fitted either, ``kind`` 'weak'. ``min_fwhm``: shapes
    narrower than this (in x units) are dropped as implausible. The window
    passes both for sample-height scans (``height_scan_options``)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    weighted = sigma is not None and np.any(np.asarray(sigma, float) > 0)
    s = noise_sigma(y, sigma)
    flat, chi2, dof = is_flat(x, y, s, background)
    if flat:
        res = FitResult([], np.zeros(0), 0.0, 1.0, chi2 / dof, (float(np.nanmin(x)), float(np.nanmax(x))), len(x),
                        False, 'flat: the %s background alone fits it (χ²/dof %.2f)' % (background, chi2 / dof),
                        FitOptions(background=background))
        res.kind, res.rss, res.npar, res.candidates = 'flat', chi2, BACKGROUNDS[background] + 1, {}
        return res
    if min_signal_to_background is not None:
        sb = signal_to_background(y)
        if not sb >= min_signal_to_background:
            res = FitResult([], np.zeros(0), 0.0, 1.0, float('nan'), (float(np.nanmin(x)), float(np.nanmax(x))),
                            len(x), False, 'weak: signal/background %.2g, below %g' % (sb, min_signal_to_background),
                            FitOptions(background=background))
            res.kind, res.rss, res.npar, res.candidates = 'weak', float('nan'), 0, {}
            return res
    out = {}
    span = float(np.nanmax(x) - np.nanmin(x)) if len(x) else 1.0
    pk = fit(x, y, sigma, FitOptions(n_peaks=1, background=background, window=span, min_prominence=3.0))
    if pk.peaks:
        r = (y - pk.model(x)) / s
        pk.kind, pk.rss, pk.npar = 'peak', float(np.sum(r ** 2)), 3 + BACKGROUNDS[background] + 1
        out['peak'] = pk
    for kind, f in (('edge', fit_edge), ('box', fit_box)):
        r = f(x, y, sigma, background)
        if r.ok:
            out[kind] = r
    if min_fwhm is not None:
        out = {k: r for k, r in out.items() if r.peaks and r.peaks[0].fwhm >= min_fwhm}
    if not out:
        return FitResult([], np.zeros(0), 0.0, 1.0, float('nan'), (float('nan'),) * 2, len(x), False,
                         'no peak, edge or plateau could be fitted' +
                         ('' if min_fwhm is None else ' wider than %g' % min_fwhm), FitOptions(background=background))
    n = len(x)

    def aic(r):
        if weighted:
            return r.rss + 2 * r.npar
        return n * math.log(max(r.rss, 1e-300) / n) + 2 * r.npar
    best = min(out.values(), key=aic)
    best.candidates = out
    return best


def options_to_dict(o):
    """FitOptions as a plain dict (for preferences and the workbook)."""
    from dataclasses import asdict
    d = asdict(o)
    d['x_range'] = None if o.x_range is None else list(o.x_range)
    d['centres'] = list(o.centres)
    return d


def options_from_dict(d, default=None):
    """FitOptions from a stored dict; unknown keys and bad values fall back
    to ``default`` (or the module's defaults)."""
    from dataclasses import fields
    base = default or FitOptions()
    kw = {}
    names = {f.name for f in fields(FitOptions)}
    for k, v in (d or {}).items():
        if k not in names:
            continue
        if k == 'x_range':
            v = None if v in (None, [], ()) else tuple(float(t) for t in v)[:2]
        elif k == 'centres':
            v = tuple(float(t) for t in (v or ()))
        else:
            ref = getattr(base, k)
            try:
                v = type(ref)(v) if not isinstance(ref, bool) else bool(v)
            except (TypeError, ValueError):
                continue
        kw[k] = v
    try:
        return replace(base, **kw).check()
    except ValueError:
        return base
