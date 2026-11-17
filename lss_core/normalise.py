"""Monitor (and absorber) normalisation of a detector frame.

The first reduction step (PROJECT_CONTEXT.md): counts divided by the
monitor count and multiplied by the absorber transmission factor
``absfac ** absnum``, with Poisson errors on counts and monitor:

    R = I · a / M,   σ_R² = (σ_I²/M² + I²/M³) · a²,   a = absfac ** absnum

Bit for bit what ``TwoDDetector.sumFiles`` does for one frame. (How the
monitor's uncertainty should really be treated is open:
PHYSICS_ISSUES P2/P3.)

In the budget error model (lss_core.errors) σ_R is the counting part only,
σ_I·a/M, and the monitor part is returned separately as MonitorTerms, to
be applied to whole sums (``frame_terms``).
"""
import numpy as np

from .errors import as_model, MonitorTerms


def normalise_frame(counts, errors, monitor, absfac=1.0, absnum=0, model=None, gain=1.0):
    """(R, sigma_R) for one frame; same operations, in the same order, as
    TwoDDetector.sumFiles with a single frame. ``model``: error model;
    in budget mode sigma_R is the counting part only. ``gain``: monitor-gain
    factor S_ref/S (lss_core.monitor), on value and error."""
    value, error = _normalise_frame(counts, errors, monitor, absfac, absnum, model)
    if gain != 1.0:
        value, error = value * gain, error * gain
    return value, error


def _normalise_frame(counts, errors, monitor, absfac, absnum, model):
    value = np.array(np.zeros(np.shape(counts)) + counts * absfac ** absnum / monitor) / 1
    if as_model(model).budget:
        error = np.sqrt(np.zeros(np.shape(counts)) + errors ** 2 / monitor ** 2
                        * absfac ** (2.0 * absnum)) / 1
        return value, error
    error = np.sqrt(np.zeros(np.shape(counts)) + (errors ** 2 / monitor ** 2 + counts ** 2 / monitor ** 3)
                    * absfac ** (2.0 * absnum)) / 1
    return value, error


def frame_terms(key, normalised, monitor, model, scale=1.0):
    """MonitorTerms of one normalised frame (budget mode): every sum over
    it carries the amplitude scale · Σ normalised · u_M(monitor)."""
    t = MonitorTerms()
    t.add(key, normalised, scale, float(as_model(model).monitor.relative(monitor)))
    return t
