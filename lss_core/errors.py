"""Error models: how the uncertainty of a reduced value is put together.

Two models, chosen per reduction (``ErrorModel.mode``):

``'legacy'``
    What the program has always done, kept byte for byte so that the
    legacy export files do not change: every pixel (or MCA channel) gets
    σ² = I/M² + I²/M³ after division by the monitor, and sums add these in
    quadrature. The monitor term is then Σ r_i²·(1/M) instead of (Σ r_i)²·u_M²
    (``docs/reports/error_propagation.md`` §4).

``'budget'``  (accepted by the owner, 2026-11-17)
    The variance of a reduced value is carried in two parts:

    * counting: the detector's variance, Σ σ_i² / M² (σ_i² = I_i, Poisson,
      unless a detector model says otherwise), adding in quadrature;
    * monitor: one amplitude per frame, value_k · u_M,k, where value_k is
      what that frame contributes to the result. Amplitudes of the same
      frame add **linearly** (its monitor error moves every pixel of the
      frame together); amplitudes of different frames add in quadrature.

    So for one frame, var(S/M) = Σσ_i²/M² + (S/M)²·u_M², and for a
    background-subtracted box var = [σ_S² + (σ_L²+σ_R²)/4]/M² + (N/M)²·u_M².

The monitor's relative uncertainty per frame, u_M = σ_M / M, comes from
``MonitorModel``, of one of three kinds:

``'gaussian'``  (the default; owner, 2026-11-17)
    A fixed relative σ, the same at every monitor count: σ = 0.04 %. The
    owner's value from an analysis of many data sets; it describes the
    present `Monc` electronics (SR570 current amplifier + V2F converter).
``'student_t'``  (owner and a separate analysis, 2026-11-17)
    A frame's monitor error is σ_scan · w · t_ν: a Student t with ν = 4
    degrees of freedom and scale s = w·σ_scan, where σ_scan is the scan's
    own `Monc` scatter (0.039 % when unknown) and the width w is about 0.94
    (0.86 to 1.01 across data sets), so s ≈ 0.037 % per frame. An upper
    bound: the analysis compared with `Monp`, which carries source
    fluctuations of its own. Propagation uses the t's standard deviation,
    u_M = s·√(ν/(ν−2)) (finite for ν > 2; √2·s for ν = 4); the shape is kept
    with the model for anything downstream that uses a likelihood. Like the
    Gaussian value, it belongs to the SR570 + V2F electronics.
    "width" is the t's scale parameter, not its standard deviation (owner,
    2026-11-17). The separate analysis estimated σ_scan as a robust standard
    deviation of the point-to-point changes of each scan; the owner prefers
    a fixed t, so σ_scan is a fixed value (0.039 %), not estimated per scan.
``'counting'``
    u_M² = f² + (σ_dark / M)² + 1 / (g · M): a fractional floor f, the
    scatter σ_dark of the dark counts in a frame, and g quanta per recorded
    count (g = 1: Poisson on the counts, the legacy assumption).

Method: first-order propagation, JCGM 100:2008 (GUM) §5.2,
https://www.bipm.org/en/doi/10.59161/JCGM100-2008E.

Absorbers: a nominal absorber factor a = absfac**n, where the window
applies one, multiplies value, counting and monitor parts alike; it
carries no uncertainty of its own (the scale between scans is measured in
patching; owner, 2026-11-17).
"""
from dataclasses import dataclass

import numpy as np

MODES = ('legacy', 'budget')


KINDS = ('gaussian', 'student_t', 'counting')
ELECTRONICS = 'SR570 current amplifier + V2F converter'


@dataclass
class MonitorModel:
    kind: str = 'gaussian'
    sigma: float = 4e-4      # gaussian: relative σ
    sigma_scan: float = 3.9e-4   # student_t: the scan's own relative Monc scatter
    width: float = 0.94      # student_t: scale = width · sigma_scan
    nu: float = 4.0          # student_t degrees of freedom
    f: float = 0.0           # counting: fractional floor
    sigma_dark: float = 0.0  # counting: dark-count scatter per frame, counts
    g: float = 1.0           # counting: quanta per recorded monitor count

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError('monitor model must be one of %s, not %r' % (KINDS, self.kind))
        if self.kind == 'student_t' and not self.nu > 2:
            raise ValueError('a Student t monitor model needs nu > 2 for a finite variance')
        if min(self.sigma, self.sigma_scan, self.width, self.f, self.sigma_dark) < 0 or not self.g > 0:
            raise ValueError('monitor model parameters must be >= 0 (g > 0)')

    def relative(self, monitor):
        """u_M = σ_M / M (a standard deviation) for monitor reading(s) ``monitor``."""
        m = np.asarray(monitor, dtype=float)
        if self.kind == 'gaussian':
            return np.zeros(np.shape(m)) + self.sigma
        if self.kind == 'student_t':
            return np.zeros(np.shape(m)) + self.scale * np.sqrt(self.nu / (self.nu - 2.0))
        return np.sqrt(self.f ** 2 + (self.sigma_dark / m) ** 2 + 1.0 / (self.g * m))

    @property
    def scale(self):
        """Scale of the Student t: width · sigma_scan."""
        return self.width * self.sigma_scan

    def describe(self):
        if self.kind == 'gaussian':
            return 'Monc Gaussian, sigma %.4g %% (%s)' % (100 * self.sigma, ELECTRONICS)
        if self.kind == 'student_t':
            return ('Monc Student t, nu %g, scale %g x %.4g %% = %.4g %% (SD %.4g %%; %s; an upper bound)'
                    % (self.nu, self.width, 100 * self.sigma_scan, 100 * self.scale,
                       100 * self.scale * np.sqrt(self.nu / (self.nu - 2.0)), ELECTRONICS))
        return 'Monc u_M^2 = %g^2 + (%g/M)^2 + 1/(%g M)' % (self.f, self.sigma_dark, self.g)

    def script(self):
        """The model as a dict literal for ``errors=``, only the fields its kind uses."""
        keys = {'gaussian': ('sigma',), 'student_t': ('sigma_scan', 'width', 'nu'),
                'counting': ('f', 'sigma_dark', 'g')}[self.kind]
        return '{' + ', '.join(["'mode': 'budget'", "'kind': %r" % self.kind]
                               + ['%r: %r' % (k, getattr(self, k)) for k in keys]) + '}'


@dataclass
class ErrorModel:
    mode: str = 'legacy'
    monitor: MonitorModel = None

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError('error model must be one of %s, not %r' % (MODES, self.mode))
        if self.monitor is None:
            self.monitor = MonitorModel()

    @property
    def budget(self):
        return self.mode == 'budget'

    def describe(self):
        if not self.budget:
            return 'legacy (per-pixel I/M^2 + I^2/M^3, summed in quadrature)'
        return 'budget (monitor on whole sums; %s)' % self.monitor.describe()


LEGACY = ErrorModel('legacy')


def as_model(errors):
    """Accept None, 'legacy', 'budget', an ErrorModel, or a dict such as
    {'mode': 'budget', 'kind': 'gaussian', 'sigma': 0.0004}."""
    if errors is None:
        return LEGACY
    if isinstance(errors, ErrorModel):
        return errors
    if isinstance(errors, dict):
        d = dict(errors)
        mode = d.pop('mode', 'budget')
        return ErrorModel(mode, MonitorModel(**d))
    return ErrorModel(str(errors))


def script_kw(model):
    """The ``errors=`` keyword a script needs for ``model`` ('' for legacy)."""
    if not model.budget:
        return ''
    return 'errors=' + model.monitor.script()


class MonitorTerms:
    """The monitor parts of a value built linearly from raw frames.

    Each term is (key, counts, coefficient): the value contains
    coefficient · counts, and the monitor amplitude of frame ``key`` over a
    region is coefficient · u_M,key · Σ_region counts. ``coefficient``
    already holds 1/M, the absorber factor and any averaging weight; its
    sign follows the value (negative for a subtracted background).
    """

    def __init__(self):
        self.terms = []          # (key, counts array, coefficient · u_M)

    def add(self, key, counts, coefficient, u):
        self.terms.append((key, counts, coefficient * u))

    def extend(self, other, scale=1.0):
        for key, counts, cu in other.terms:
            self.terms.append((key, counts, cu * scale))

    def __len__(self):
        return len(self.terms)

    def amplitudes(self, region=np.s_[...], axis=None):
        """{key: amplitude}, the amplitude of each frame for the sum of the
        value over ``region`` (along ``axis`` if given, giving profiles)."""
        out = {}
        for key, counts, cu in self.terms:
            a = cu * np.sum(counts[region], axis=axis)
            out[key] = out[key] + a if key in out else a
        return out

    def variance(self, region=np.s_[...], axis=None):
        """Monitor variance of the sum over ``region`` (profile if ``axis``)."""
        amps = self.amplitudes(region, axis)
        if not amps:
            return 0.0
        return np.sum([np.square(a) for a in amps.values()], axis=0)


def combine_amplitudes(parts):
    """Monitor variance of a linear combination. ``parts``: list of
    (weight, {key: amplitude}). Same keys add linearly, then square."""
    total = {}
    for w, amps in parts:
        for key, a in amps.items():
            total[key] = total.get(key, 0.0) + w * a
    return float(np.sum([a * a for a in total.values()])) if total else 0.0
