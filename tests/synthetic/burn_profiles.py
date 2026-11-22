"""GID burn tests with known truth: horizontal profiles of one spot measured
repeatedly, as ``lss_core.burn.measure_gid`` takes them ((N, 3) arrays Qxy,
I per monitor count, σ on one grid).

Generalises ``_gid_profiles`` of tests/test_burn_trends.py (whose numbers
it keeps as defaults: Qxy 1.30–1.92 Å⁻¹ on 195 points, lit columns
1.39–1.74, a sharp peak at 1.466 of FWHM 0.016 on a broad shoulder at 1.47
of σ 0.04, a flat floor 0.003) and states the truth frame by frame, for
the hand-off's open items (docs/handoff_out/07-burn-trends.md, items 3–4:
which estimator reads which change, and where each becomes unusable as
the counts fall).

Changes (``change``), each over the test, f = t / t_end:

- ``'fade'``: the peak's area × (1 − amount·f) (or × exp(−t/τ) with ``tau``);
- ``'broaden'``: FWHM × (1 + amount·f) at constant area;
- ``'shift'``: centre + amount·f (Å⁻¹);
- ``'shoulder'``: the peak fades as 'fade' under a steady shoulder made
  ``shoulder_scale`` times stronger;
- ``'background'``: the flat floor × (1 + amount·f);
- ``'none'``: nothing changes (false alarms).

Noise: Poisson on counts = value × ``monitor`` (``counts`` sets the noise
floor: lower ``monitor``, fewer counts), σ = √counts / monitor; or no noise
(``seed=None``). Times: t_k = (k + ½)·ctime, the middle of each exposure.
"""
import math
from dataclasses import dataclass

import numpy as np

G = 2 * math.sqrt(2 * math.log(2))      # FWHM / σ of a Gaussian
X = np.linspace(1.30, 1.92, 195)
LIT = (1.39, 1.74)
CENTRE, FWHM, AREA = 1.466, 0.016, 0.02 * 0.016 / G * math.sqrt(2 * math.pi)   # area of the default peak
SHOULDER = (0.008, 1.47, 0.04)          # height, centre, σ
FLOOR = 0.003
CHANGES = ('none', 'fade', 'broaden', 'shift', 'shoulder', 'background')


@dataclass
class BurnTruth:
    t: np.ndarray
    area: np.ndarray       # the peak's integrated intensity (per monitor count × Å⁻¹)
    centre: np.ndarray
    fwhm: np.ndarray
    floor: np.ndarray
    shoulder: float        # shoulder height
    change: str

    def relative(self, quantity):
        """The quantity over its value at t = 0 (extrapolated: the first frame's f = ½/n)."""
        v = getattr(self, quantity)
        return v / v[0]


def profiles(n=21, change='fade', amount=0.2, tau=None, ctime=10.0, monitor=1e7, seed=0,
             shoulder_scale=3.0):
    """(list of n profiles, BurnTruth). See the module docstring."""
    if change not in CHANGES:
        raise ValueError('change %r: one of %s' % (change, ', '.join(CHANGES)))
    t = (np.arange(n) + 0.5) * ctime
    f = t / (n * ctime)
    area = np.full(n, AREA)
    centre = np.full(n, CENTRE)
    fwhm = np.full(n, FWHM)
    floor = np.full(n, FLOOR)
    sh = SHOULDER[0]
    if change in ('fade', 'shoulder'):
        area = AREA * (np.exp(-t / tau) if tau else 1 - amount * f)
        if change == 'shoulder':
            sh = SHOULDER[0] * shoulder_scale
    elif change == 'broaden':
        fwhm = FWHM * (1 + amount * f)
    elif change == 'shift':
        centre = CENTRE + amount * f
    elif change == 'background':
        floor = FLOOR * (1 + amount * f)
    lit = ((X > LIT[0]) & (X < LIT[1])).astype(float)
    shoulder = sh * np.exp(-0.5 * ((X - SHOULDER[1]) / SHOULDER[2]) ** 2)
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for k in range(n):
        s = fwhm[k] / G
        peak = area[k] / (s * math.sqrt(2 * math.pi)) * np.exp(-0.5 * ((X - centre[k]) / s) ** 2)
        mu = lit * (floor[k] + shoulder + peak)
        if rng is None:
            y, e = mu, np.sqrt(np.maximum(mu, 1.0 / monitor) / monitor)
        else:
            c = rng.poisson(mu * monitor).astype(float)
            y, e = c / monitor, np.sqrt(np.maximum(c, 1.0)) / monitor
        out.append(np.column_stack([X, y, e]))
    return out, BurnTruth(t, area, centre, fwhm, floor, sh, change)
