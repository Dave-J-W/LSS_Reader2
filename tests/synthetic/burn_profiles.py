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

The shoulder (P44, 2026-11-27): ``shoulder_change`` makes its height
× (1 + shoulder_change·f), on top of any ``change`` (the owner, 2026-11-26:
whether a real shoulder changes under the beam is not known);
``shoulder_shape`` is its form, all of the same height and FWHM about
1.47 Å⁻¹ (SHOULDER_SHAPES): 'gaussian' (the default, σ 0.04), 'lorentzian',
'asymmetric' (σ 0.025 below its centre, 0.055 above), 'two' (the Gaussian
and a narrower one, 0.6 of its height, σ 0.012, at 1.455: close beside the
peak), 'none'. ``BurnTruth.shoulder_profile(k)`` is frame k's.
``area_change``: the peak's area × (1 + area_change·f) on top of
``change`` (NX scan 15 broadens by about 20 % and, read by the split
estimator, fades by 13 %: ``change='broaden', area_change=-0.13``).

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
SHOULDER_SHAPES = ('gaussian', 'lorentzian', 'asymmetric', 'two', 'none')


def shoulder_curve(kind='gaussian', height=SHOULDER[0], x=X):
    """The shoulder of ``kind`` (SHOULDER_SHAPES) and ``height`` on ``x``."""
    m, s = SHOULDER[1], SHOULDER[2]
    if kind == 'gaussian':
        return height * np.exp(-0.5 * ((x - m) / s) ** 2)
    if kind == 'lorentzian':                     # the Gaussian's FWHM
        g = s * G / 2
        return height * g ** 2 / ((x - m) ** 2 + g ** 2)
    if kind == 'asymmetric':
        return height * np.exp(-0.5 * ((x - m) / np.where(x < m, 0.025, 0.055)) ** 2)
    if kind == 'two':
        return height * (np.exp(-0.5 * ((x - m) / s) ** 2) + 0.6 * np.exp(-0.5 * ((x - 1.455) / 0.012) ** 2))
    if kind == 'none':
        return np.zeros_like(x)
    raise ValueError('shoulder_shape %r: one of %s' % (kind, ', '.join(SHOULDER_SHAPES)))


@dataclass
class BurnTruth:
    t: np.ndarray
    area: np.ndarray       # the peak's integrated intensity (per monitor count × Å⁻¹)
    centre: np.ndarray
    fwhm: np.ndarray
    floor: np.ndarray
    shoulder: float        # shoulder height (before ``shoulder_change``)
    change: str
    shoulder_height: np.ndarray = None      # per frame
    shoulder_kind: str = 'gaussian'

    def relative(self, quantity):
        """The quantity over its value at t = 0 (extrapolated: the first frame's f = ½/n)."""
        v = getattr(self, quantity)
        return v / v[0]

    def shoulder_profile(self, k, x=X):
        """Frame k's shoulder on ``x`` (inside the lit columns; 0 outside them on X)."""
        h = self.shoulder if self.shoulder_height is None else self.shoulder_height[k]
        return shoulder_curve(self.shoulder_kind, h, x)


def profiles(n=21, change='fade', amount=0.2, tau=None, ctime=10.0, monitor=1e7, seed=0,
             shoulder_scale=3.0, shoulder_shape='gaussian', shoulder_change=0.0, area_change=0.0):
    """(list of n profiles, BurnTruth). See the module docstring."""
    if change not in CHANGES:
        raise ValueError('change %r: one of %s' % (change, ', '.join(CHANGES)))
    if shoulder_shape not in SHOULDER_SHAPES:
        raise ValueError('shoulder_shape %r: one of %s' % (shoulder_shape, ', '.join(SHOULDER_SHAPES)))
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
    if area_change:
        area = area * (1 + area_change * f)
    lit = ((X > LIT[0]) & (X < LIT[1])).astype(float)
    height = sh * (1 + shoulder_change * f)
    rng = np.random.default_rng(seed) if seed is not None else None
    out = []
    for k in range(n):
        shoulder = shoulder_curve(shoulder_shape, sh if shoulder_change == 0 else height[k])
        s = fwhm[k] / G
        peak = area[k] / (s * math.sqrt(2 * math.pi)) * np.exp(-0.5 * ((X - centre[k]) / s) ** 2)
        mu = lit * (floor[k] + shoulder + peak)
        if rng is None:
            y, e = mu, np.sqrt(np.maximum(mu, 1.0 / monitor) / monitor)
        else:
            c = rng.poisson(mu * monitor).astype(float)
            y, e = c / monitor, np.sqrt(np.maximum(c, 1.0)) / monitor
        out.append(np.column_stack([X, y, e]))
    return out, BurnTruth(t, area, centre, fwhm, floor, sh, change, height, shoulder_shape)
