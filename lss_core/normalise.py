"""Monitor (and absorber) normalisation of a detector frame.

The first reduction step (PROJECT_CONTEXT.md): counts divided by the
monitor count and multiplied by the absorber transmission factor
``absfac ** absnum``, with Poisson errors on counts and monitor:

    R = I · a / M,   σ_R² = (σ_I²/M² + I²/M³) · a²,   a = absfac ** absnum

Bit for bit what ``TwoDDetector.sumFiles`` does for one frame. (How the
monitor's uncertainty should really be treated is open:
PHYSICS_ISSUES P2/P3.)
"""
import numpy as np


def normalise_frame(counts, errors, monitor, absfac=1.0, absnum=0):
    """(R, sigma_R) for one frame; same operations, in the same order, as
    TwoDDetector.sumFiles with a single frame."""
    value = np.array(np.zeros(np.shape(counts)) + counts * absfac ** absnum / monitor) / 1
    error = np.sqrt(np.zeros(np.shape(counts)) + (errors ** 2 / monitor ** 2 + counts ** 2 / monitor ** 3)
                    * absfac ** (2.0 * absnum)) / 1
    return value, error
