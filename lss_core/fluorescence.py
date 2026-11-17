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
    """absfac**n for a scan's absorber setting n (None: unknown, no factor)."""
    return 1.0 if absorber is None else float(absfac) ** absorber


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
