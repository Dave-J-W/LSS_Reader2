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
    """The MCA Merge: rows ([frame, qz, energy, I, σ]) sorted on ``x`` and
    every row within ``window`` of the first row of a group merged into it
    with weights y/σ² (for counting errors ΣN/ΣM, pooled counts over pooled
    monitor; P7, kept by the owner). Values and the counting part of σ are
    the window's arithmetic exactly. On the Qz axis the Qz jitter is added
    to σ (owner's XFNTR rule, step 5): σ_j = I·|d ln I/dQz|·``jitter``,
    propagated through the same weights (√Σw²/Σw), d ln I/dQz from the
    merged curve by central differences. ``window`` None: the default
    (``default_merge_window``). Which scans to merge is the user's choice
    (one run, wavelength, sample and signal shape)."""
    index = {'frame': 0, 'qz': 1, 'energy': 2}[x]
    if window is None:
        window = default_merge_window(rows, x)
    data = np.array(rows, dtype=float)
    data = data[np.argsort(data[:, index])]
    out = [data[0]]
    wsum = [[data[0][3] / data[0][4] ** 2]]
    for i in range(1, len(data)):
        if np.abs(data[i][index] - out[-1][index]) <= window:
            a = out[-1][3] ** 2 / out[-1][4] ** 2
            b = data[i][3] ** 2 / data[i][4] ** 2
            c = out[-1][3] / out[-1][4] ** 2
            d = data[i][3] / data[i][4] ** 2
            out[-1][3] = (a + b) / (c + d)
            out[-1][4] = np.sqrt((a + b) / (c + d) ** 2)
            wsum[-1].append(d)
        else:
            out = np.vstack((out, data[i]))
            wsum.append([data[i][3] / data[i][4] ** 2])
    out = np.array(out, dtype=float)
    if index == 1 and jitter and len(out) > 1:
        v, q = out[:, 3], out[:, 1]
        with np.errstate(divide='ignore', invalid='ignore'):
            slope = np.gradient(np.log(np.where(v > 0, v, np.nan)), q)
        frac = np.array([np.sqrt(np.sum(np.square(w))) / np.sum(w) if np.sum(w) != 0 else 1.0 for w in wsum])
        sj = np.abs(v * np.nan_to_num(slope)) * jitter * frac
        out[:, 4] = np.sqrt(out[:, 4] ** 2 + sj ** 2)
    return out
