"""Fluorescence (XFNTR) from MCA spectra, without the window.

Reproduces the window's MCA tab: each spectrum is put on an energy axis
(calibration from the file), divided by the monitor and multiplied by
real/live time; σ = √(N + N²/M)/M × real/live. "Sum All" adds the
normalised counts over an energy window and the errors in quadrature
(PHYSICS_ISSUES P2/P8 for what that does to the monitor term).

With an error model in 'budget' mode (lss_core.errors) the channel error is
√(τ²N/M² + y²·u_M²) and a window sum gets the monitor term once, on the
sum: var = Σ τ²N_c/M² + (Σ y_c)²·u_M².
Normalised spectra are multiplied by the nominal absorber factor
absfac**n of their scan (n from SPEC ``#A``, or from the last ``#A`` above
a scan that records none; owner, 2026-11-17, F50).
``save_flu`` writes the window's ``_flu.txt`` byte for byte.
"""
from dataclasses import dataclass

import numpy as np

from .absorbers import Foils, attenuation
from .errors import as_model


def normalise_spectrum(counts, par, monitor_value, calibration, errors=None, absorber=1.0, gain=1.0):
    """(N, 3) energy, normalised counts, error, as ``updateMcaPlotData``.
    ``errors``: error model (None or 'legacy': as the window always did).
    ``absorber``: the nominal absorber factor absfac**n of the scan, applied
    to normalised spectra (value and error); the foils are before the sample
    and the monitor upstream of them (owner, 2026-11-17). ``gain``: the
    monitor-gain factor S_ref/S (lss_core.monitor), when that option is on."""
    y = np.array(counts, dtype='float')
    x = np.arange(1, len(y) + 1)
    con, lin, qua = calibration
    x = con + lin * x + qua * x ** 2
    if monitor_value is None:
        return np.vstack((x, y, np.sqrt(y))).transpose()
    n = monitor_value
    tc = par['Time'][1] / par['Time'][2]          # real / live time
    model = as_model(errors)
    if model.budget:
        u = model.monitor.relative(n)
        out = np.vstack((x, y / n * tc, np.sqrt(y / n ** 2 * tc ** 2 + (y / n * tc) ** 2 * u ** 2))).transpose()
    else:
        out = np.vstack((x, y / n * tc, np.sqrt(y + y ** 2 / n) / n * tc)).transpose()
    if absorber * gain != 1.0:   # 1.0 leaves the numbers untouched (legacy files)
        out[:, 1:] *= absorber * gain
    return out


def absorber_factor(absfac, absorber):
    """absfac**n for a scan's absorber setting n (None: unknown, no factor);
    for calibrated foils (lss_core.absorbers.Foils) their factor at n."""
    if absorber is None:
        return 1.0
    if isinstance(absfac, Foils):
        return attenuation(absfac, absorber)
    return float(absfac) ** absorber


def window_sum(data, lo, hi, u=None):
    """Sum over [lo, hi] (clipped to the spectrum), as ``mcaSumAll``.
    Returns (intensity, error, lo_used, hi_used). ``u``: the spectrum's
    relative monitor uncertainty, for a spectrum normalised in budget mode;
    its monitor term is then taken off each channel and put on the sum."""
    ini = max(float(lo), data[0][0])
    fin = min(float(hi), data[-1][0])
    idx = np.where(np.logical_and(data[:, 0] <= fin, data[:, 0] >= ini))
    part = data[idx[0][0]:idx[0][-1] + 1]
    if u is None:
        return np.sum(part[:, 1]), np.sqrt(np.sum(part[:, 2] ** 2)), ini, fin
    total = np.sum(part[:, 1])
    counting = np.sum(np.clip(part[:, 2] ** 2 - (part[:, 1] * u) ** 2, 0, None))
    return total, np.sqrt(counting + (total * u) ** 2), ini, fin


def save_flu(name, rows, command, x='qz'):
    """Write <name>_flu.txt as the window does. ``rows``: [frame, qz,
    energy, intensity, error]; ``x``: 'frame', 'qz' or 'energy'."""
    col = {'frame': 0, 'qz': 1, 'energy': 2}[x]
    with open(name + '_flu.txt', 'w') as fid:
        fid.write('#' + str(command) + '\n')
        for r in rows:
            fid.write(str(r[col]) + '\t' + str(r[3]) + '\t' + str(r[4]) + '\n')


# ---- Merge (the window's MCA "Merge"; owner's XFNTR rule, 2026-11-19) ------------

QZ_JITTER = 3e-5        # 1/Å: Qz jitter, added to merged errors on the Qz axis (owner, F65 step 5)
MATCH_FRACTION = 0.1    # default window: this fraction of the Qz grid step (F65 step 2)


def grid_step(values):
    """The grid step of a set of Qz values that may hold repeats with Qz
    jitter: the median of the spacings between sorted values, leaving out
    those under a fifth of the 90th percentile (the gaps between repeats of
    one target, ~3e-5 1/Å, against a step of ~1e-3). None with fewer than
    two distinct values."""
    v = np.sort(np.asarray(values, float))
    d = np.diff(v)
    d = d[d > 0]
    if not len(d):
        return None
    big = d[d >= 0.2 * np.percentile(d, 90)]
    return float(np.median(big))


def default_merge_window(rows, x='qz'):
    """0.1 × the Qz grid step for the Qz axis (1e-4 1/Å for a 0.001 step);
    0 for the frame and energy axes (only identical values merge)."""
    if x != 'qz':
        return 0.0
    step = grid_step([r[1] for r in rows])
    return MATCH_FRACTION * step if step else 0.0


def merge_rows(rows, x='qz', window=None, jitter=QZ_JITTER):
    """The MCA Merge: rows ([frame, qz, energy, I, σ], or with more (I, σ)
    pairs after them, such as the reader's fit beside XeRay's, F110) sorted
    on ``x`` and every row within ``window`` of the first row of a group
    merged into it with weights y/σ², each pair alone over the same groups
    (for counting errors ΣN/ΣM, pooled counts over pooled monitor; P7, kept
    by the owner). Values and the counting part of σ are the window's
    arithmetic exactly. On the Qz axis the Qz jitter is added to σ (owner's
    XFNTR rule, step 5): σ_j = I·|d ln I/dQz|·``jitter``, propagated through
    the same weights (√Σw²/Σw), d ln I/dQz from the merged curve by central
    differences. ``window`` None: the default (``default_merge_window``).
    Which scans to merge is the user's choice (one run, wavelength, sample
    and signal shape)."""
    index = {'frame': 0, 'qz': 1, 'energy': 2}[x]
    if window is None:
        window = default_merge_window(rows, x)
    data = np.array(rows, dtype=float)
    data = data[np.argsort(data[:, index])]
    pairs = [(k, k + 1) for k in range(3, data.shape[1] - 1, 2)]
    out = [data[0].copy()]
    wsum = [{p: [data[0][p[0]] / data[0][p[1]] ** 2] for p in pairs}]
    for i in range(1, len(data)):
        if np.abs(data[i][index] - out[-1][index]) <= window:
            for vi, si in pairs:
                a = out[-1][vi] ** 2 / out[-1][si] ** 2
                b = data[i][vi] ** 2 / data[i][si] ** 2
                c = out[-1][vi] / out[-1][si] ** 2
                d = data[i][vi] / data[i][si] ** 2
                out[-1][vi] = (a + b) / (c + d)
                out[-1][si] = np.sqrt((a + b) / (c + d) ** 2)
                wsum[-1][(vi, si)].append(d)
        else:
            out.append(data[i].copy())
            wsum.append({p: [data[i][p[0]] / data[i][p[1]] ** 2] for p in pairs})
    out = np.array(out, dtype=float)
    if index == 1 and jitter and len(out) > 1:
        q = out[:, 1]
        for vi, si in pairs:
            v = out[:, vi]
            with np.errstate(divide='ignore', invalid='ignore'):
                slope = np.gradient(np.log(np.where(v > 0, v, np.nan)), q)
            frac = np.array([np.sqrt(np.sum(np.square(w[(vi, si)]))) / np.sum(w[(vi, si)])
                             if np.sum(w[(vi, si)]) != 0 else 1.0 for w in wsum])
            sj = np.abs(v * np.nan_to_num(slope)) * jitter * frac
            out[:, si] = np.sqrt(out[:, si] ** 2 + sj ** 2)
    return out


# ---- line fits: the reader's Poisson fit (the default) and XeRay beside it (owner, 2026-11-26; F110) ----

@dataclass
class XeRayFit:
    """XeRay's fit of one spectrum: the line's ``area`` in counts (area /
    channel width, the reader's convention) and XeRay's error ``area_err``,
    the line's ``centre`` and ``fwhm`` (keV), the straight background
    (``slope``, ``const``) over the ``window``; ``ok`` False with ``message``
    when the fit failed; ``step`` the channel width (keV)."""
    area: float
    area_err: float
    centre: float
    fwhm: float
    slope: float
    const: float
    window: tuple
    ok: bool = True
    message: str = ''
    step: float = 1.0

    def model(self, x):
        x = np.asarray(x, float)
        s = self.fwhm / (2 * np.sqrt(2 * np.log(2)))
        amp = self.area * self.step / (s * np.sqrt(2 * np.pi)) if s > 0 else 0.0
        return amp * np.exp(-((x - self.centre) / s) ** 2 / 2) + self.slope * x + self.const


def xeray_fit(energy, y, sigma=None, x_range=None, centre=None):
    """XeRay's line fit (the Lee group's MATLAB tool for XFNTR,
    ``functions/fluoCurveFit.m`` and ``XeLineshape.m`` of
    github.com/ZhiliangGong/xeray, ported line for line in
    ``tests/tools/xrf_shootout.py``): a Gaussian on a straight line, fitted by
    unweighted least squares (scipy's 'trf', as MATLAB's lsqnonlin) inside
    ``x_range``, the centre within ±0.2 keV of ``centre`` (default: the
    highest channel). The area is in counts (area / channel width).

    XeRay's error is √(the counts in the window). For the reader's
    normalised spectra (σ_c = √N_c/k per channel) that is √(Σ σ_c²); without
    ``sigma``, √(Σ y). It leaves out the background's uncertainty, so it is
    too small where the background is large: the shootout's median pull SD
    1.92, up to 11.7 (``docs/studies/xrf_shootout/summary.md`` section 3).
    On the owner's real blanks it was accurate in 6 of 192 conditions (C66)
    and on real line shapes in 3 of 160 (C69), so since the owner's revision
    of F110 (2026-11-26) the reader's fit is the default and XeRay is
    reported beside it."""
    from scipy.optimize import least_squares
    e, y = np.asarray(energy, float), np.asarray(y, float)
    lo, hi = (float(np.min(e)), float(np.max(e))) if x_range is None else (min(x_range), max(x_range))
    box = (e >= lo) & (e <= hi)
    step = float(np.median(np.abs(np.diff(e)))) if len(e) > 1 else 1.0
    nan = float('nan')
    if box.sum() < 6:
        return XeRayFit(nan, nan, nan, nan, nan, nan, (lo, hi), False, 'too few channels in the window', step)
    x, yb = e[box], y[box]
    peak = float(x[int(np.argmax(yb))]) if centre is None else float(centre)
    base = float(np.mean([np.mean(yb[:5]), np.mean(yb[-5:])]))
    rng = float(np.ptp(yb))
    lb = np.array([0.0, peak - 0.2, 0.0, -np.inf, float(np.min(yb))])
    ub = np.array([max(rng * 3, 1e-9), peak + 0.2, float(np.ptp(x)) / 2, np.inf,
                   max(float(np.mean(yb)), float(np.min(yb)) + 1e-9)])
    a0 = np.array([rng, peak, float(np.ptp(x)) / 6, 0.0, base])
    span = np.where(np.isfinite(ub - lb), ub - lb, 1.0)
    a0 = np.clip(a0, lb + 1e-9 * span, ub - 1e-9 * span)       # lsqnonlin projects a start onto the bounds

    def f(a):
        return a[0] * np.exp(-((x - a[1]) / a[2]) ** 2 / 2) + a[3] * x + a[4] - yb
    try:
        a = least_squares(f, a0, bounds=(lb, ub), method='trf').x
    except (ValueError, np.linalg.LinAlgError) as err:
        return XeRayFit(nan, nan, nan, nan, nan, nan, (lo, hi), False, 'the fit failed (%s)' % err, step)
    area = float(a[0] * a[2] * np.sqrt(2 * np.pi) / step)
    if sigma is not None:
        err = float(np.sqrt(np.sum(np.square(np.asarray(sigma, float)[box]))))
    else:
        err = float(np.sqrt(max(float(np.sum(yb)), 1.0)))
    return XeRayFit(area, err, float(a[1]), float(2 * np.sqrt(2 * np.log(2)) * a[2]), float(a[3]), float(a[4]),
                    (lo, hi), True, '', step)


def fit_line_series(data, options, poisson=True, detector_width=False, noise_kev=0.12, strip_escapes=True):
    """Both line fits of a series of normalised spectra (``data``: arrays of
    energy, y, σ on one energy axis), F110 (owner, 2026-11-26): both fits
    and both errors are reported. Revised the same day by the owner: the
    reader's fit is the default (the value plotted, merged and exported),
    with its width from the sum, and XeRay is reported beside it.

    - **The reader's fit** (``peaks.fit_series``): Poisson likelihood
      (``poisson``), the Si escape spectrum stripped first
      (``strip_escapes``), the line's position and width fitted on the sum
      of the series and held for every spectrum, which then gets its height
      and background. On the owner's real data this is the most accurate:
      49 of 192 conditions on real blanks (C66, pull SD 1.08) and 34 of 160
      with real line shapes on the 7-element detector (C69, bias −1.3 %).
      ``detector_width`` fixes the width at the detector model's instead
      (Fano, ``noise_kev``), at the element's line (``options.centres[0]``)
      or, when no energy is given, at the median centre of XeRay's fits
      (``width_at`` says which energy was used): best on the synthetic
      shootout (C65), but about 6 % low with real line shapes (C69) and far
      off where the real width differs from the model's (0.68 of the area
      on the synthetic XFNTR set, whose line is 1.65 × the model's width).
    - **XeRay** (``xeray_fit``) on each spectrum as it is, in the window
      ``options.x_range`` around the element's line ``options.centres[0]``.

    Returns dict(xeray=[XeRayFit], ref, each, j (the element's line in each
    reader fit), step, options (as used by the reader's fit), width_at
    (keV; None when the width was left free))."""
    import dataclasses
    from . import peaks
    x = np.asarray(data[0], float)[:, 0]
    step = float(np.median(np.abs(np.diff(x))))
    centre = options.centres[0] if options.centres else None
    xr = [xeray_fit(x, d[:, 1], d[:, 2], options.x_range, centre) for d in data]
    fdata = [strip_escape(d) for d in data] if strip_escapes else list(data)
    o, width_at = options, None
    if detector_width:
        found = [f.centre for f in xr if f.ok]
        width_at = centre if centre is not None else (float(np.median(found)) if found else None)
        if width_at is not None:
            o = dataclasses.replace(o, fwhm=detector_fwhm(width_at, noise_kev))
    ref, each = peaks.fit_series(x, [d[:, 1] for d in fdata], [d[:, 2] for d in fdata], o,
                                 weights='poisson' if poisson else 'data')
    j = peaks.line_index(ref, o.centres) if each else None
    return dict(xeray=xr, ref=ref, each=each, j=j, step=step, options=o, width_at=width_at)


# ---- multi-element detectors (owner, 2026-11-19) ------------------------------------

def combine_channels(spectra, channels=None):
    """One spectrum per scan point from a multi-element file, summing the
    elements in ``channels`` (None or empty: all). ``spectra``: [(Data, Par)]
    of one MCA file in file order; a point's elements are consecutive blocks
    with ascending ``#@CHANNEL`` (a new point starts when the channel number
    does not increase). Monitor, times, Qz, energy and calibration are the
    first selected element's (the same for all elements of a point on the
    7-element Xspress3, which corrects its own dead time). Single-element
    files are returned unchanged. Owner: EXAFS sums all elements; XFNTR uses
    the central one."""
    chans = [p.get('Channel') for _, p in spectra]
    if all(c is None for c in chans) or len(set(c for c in chans if c is not None)) < 2:
        return list(spectra)
    groups, cur, last = [], [], None
    for d, p in spectra:
        c = p.get('Channel')
        if cur and (c is None or last is None or c <= last):
            groups.append(cur)
            cur = []
        cur.append((d, p))
        last = c
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        chosen = [(d, p) for d, p in g if not channels or p.get('Channel') in channels]
        if not chosen:
            continue
        d0, p0 = chosen[0]
        total = np.sum([np.asarray(d['Vortex'], float) for d, _ in chosen], axis=0)
        d = dict(d0)
        d['Vortex'] = list(total)
        p = dict(p0)
        p['Channels'] = [q.get('Channel') for _, q in chosen]
        if any(q.get('Calib') != p0.get('Calib') for _, q in chosen):
            p['CalibMismatch'] = True
        out.append((d, p))
    return out



# ---- line-fit options for silicon detectors (F90 P2, P3; the owner, 2026-11-24: options, not defaults) ----

SI_KA_KEV = 1.740            # Si Kα (X-ray Data Booklet Table 1-2: Kα1 1.73998 keV)
SI_K_EDGE_KEV = 1.8389
SI_EPS_KEV = 0.00365         # energy per electron-hole pair in Si
SI_FANO = 0.115              # Fano factor (from memory; 0.11-0.12 in the literature)


def detector_fwhm(e_kev, noise_kev=0.12, fano=SI_FANO, eps=SI_EPS_KEV):
    """FWHM (keV) of a silicon detector's photopeak at ``e_kev``:
    √(noise² + 8 ln2 ε F E), with ``noise_kev`` the electronic noise FWHM
    (calibrate it on a strong peak, e.g. the elastic line: noise² = FWHM² −
    8 ln2 ε F E0). P2: the "Fit lines" width fixed at this value at the
    element's line removes the trade-off of a free width against the
    background (C42)."""
    return float(np.sqrt(noise_kev ** 2 + 8 * np.log(2) * eps * fano * max(float(e_kev), 0.0)))


def si_escape_fraction(e_kev, omega=0.050, jump=0.90, mu_k=350.0):
    """Si K escape probability for a photon of ``e_kev`` absorbed in a thick
    detector at normal incidence (S. J. B. Reed and N. G. Ware, J. Phys. E 5,
    582, 1972): ½ ω_K (1 − 1/r) [1 − (μ_K/μ_E) ln(1 + μ_E/μ_K)], with
    ω_K(Si) = 0.050, 1 − 1/r = 0.90, μ_K = 350 cm²/g (Si Kα in Si) and
    μ_E = 33.9 (10/E)^2.75 cm²/g. The constants are from memory: about 0.10 %
    at 10 keV and 0.15 % at 8.6 keV. 0 below the Si K edge."""
    if e_kev <= SI_K_EDGE_KEV:
        return 0.0
    mu_e = 33.9 * (10.0 / e_kev) ** 2.75
    a = mu_k / mu_e
    return 0.5 * omega * jump * (1.0 - a * np.log1p(1.0 / a))


def strip_escape(data, scale=1.0):
    """Si escape stripping of a spectrum (N, 3: energy, value, σ), P3: the
    escape of what was measured at E + 1.740 keV, Reed's fraction × ``scale``
    of it, comes off at E (AXIL and PyMca correct escapes this way). σ gets
    the subtracted part's error; a zero σ (no counts) stays zero, as the
    reader leaves it. Under 10 keV the elastic's escape at 8.26 keV lies
    under Zn Kα: stripping cut its bias on "Fit lines" from +45 % to about
    4 % (C42). The fraction is the detector's; ``scale`` corrects Reed's."""
    d = np.array(data, dtype=float, copy=True)
    e, y, s = d[:, 0], d[:, 1], d[:, 2]
    up = e + SI_KA_KEV
    f = scale * np.array([si_escape_fraction(v) for v in up])
    order = np.argsort(e)
    yu = np.interp(up, e[order], y[order], right=0.0)
    su = np.interp(up, e[order], s[order], right=0.0)
    d[:, 1] = y - f * yu
    d[:, 2] = np.where(s > 0, np.sqrt(s ** 2 + (f * su) ** 2), 0.0)
    return d
