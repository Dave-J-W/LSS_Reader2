"""Burns of one kind of sample at several fluxes, with a known law of change
(F76: beam damage or a sample changing by itself; ``lss_core.reciprocity``).

Burn b at flux φ_b (relative to the lowest, 1) has frames of ``seconds``
at t_i = (i + ½)·seconds, i < ``frames``, and a relative quantity

    y(t) = exp(−λ_b t),   λ_b = λ₁ · φ_b^β · (1 + ε_b),

λ₁ set by ``change``, the total fall over the burn at the lowest flux
(1 − exp(−λ₁ T)); β the truth: 1 the dose, 0 time, 0.5 or 2 a dose-rate
effect, ``None`` no change at all. ε_b ~ N(0, ``strip``) is the strip-to-
strip scatter of the rate (C54 measured an additive 88 %/h on real
reflectivity burns; here it is relative to the rate). Noise: Gaussian,
``noise`` relative per frame. ``rise=True`` turns the fall into a rise.
``mixture=(w_dose, w_time)`` gives λ_b = λ₁ (w_dose φ_b + w_time): both
processes at once.

Returns (burns, truth): ``reciprocity.Burn`` objects (relative, flux in the
same unit) and a dict with β, the true rates (per second, the slope of y
at t = 0 over y(0), i.e. −λ_b) and the settings.
"""
import numpy as np

from lss_core.reciprocity import Burn


def series(beta=1.0, fluxes=(1.0, 4.68), frames=21, seconds=10.0, change=0.1, noise=0.01, strip=0.0,
           seed=0, rise=False, mixture=None):
    rng = np.random.default_rng(seed)
    T = frames * seconds
    lam1 = -np.log(1.0 - change) / T if change and beta is not None else 0.0
    t = (np.arange(frames) + 0.5) * seconds
    burns, rates = [], []
    for k, phi in enumerate(fluxes):
        if beta is None and mixture is None:
            lam = 0.0
        elif mixture is not None:
            lam = lam1 * (mixture[0] * phi + mixture[1])
        else:
            lam = lam1 * phi ** beta
        lam *= 1.0 + strip * rng.standard_normal() if strip else 1.0
        sign = -1.0 if rise else 1.0
        y0 = np.exp(-sign * lam * t)
        y = y0 * (1.0 + noise * rng.standard_normal(frames))
        burns.append(Burn(t.copy(), y, noise * y0, float(phi), True, 'burn %d (×%g)' % (k + 1, phi)))
        rates.append(-sign * lam)
    return burns, dict(beta=beta, rates=rates, fluxes=list(fluxes), frames=frames, change=change, noise=noise,
                       strip=strip, mixture=mixture)
