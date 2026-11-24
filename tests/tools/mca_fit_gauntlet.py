"""The MCA line-fit gauntlet: fitted fluorescence lines against the window
sum, on synthetic spectra with known truth (F90, owner 2026-11-23:
"fitted lines are the default, placed from the element, fit range shown as
an editable box. A gauntlet of true MCA spectra … must show the fit holds
against the direct-beam scatter (Rayleigh, Compton), the hard case being
Zn Kα (8637 eV) under 10 keV excitation. If it passes, summing windows is
no longer needed").

    python tests/tools/mca_fit_gauntlet.py --out DIR [--design core|grid|random|series|all]
        [--replicates 200] [--random 150 --random-replicates 40] [--series-replicates 60]
        [--methods key|all|a,b] [--conditions a,b] [--jobs N] [--rows]

Spectra come from ``tests/synthetic/mca.py``. They hold the element's
Kα1, Kα2 and Kβ; Rayleigh and Compton scatter (valence and O 1s core
Doppler profiles); the detector's Fano resolution, exponential tail, shelf
and Si escape peaks; background; a calibration error; Poisson counts. Each
is normalised as the reader does it (``fluorescence.normalise_spectrum``,
σ = √(N + N²/M)/M·τ). The **box** is the editable fit range of F90: the
line's energy (from the element) ± 2 FWHM of the detector there (1.5–4
in the grid, and −3/+1.5).

Estimators of the line's counts (``--methods``; ``key`` is the first eight):

- ``window``: ``fluorescence.window_sum`` over the box: the reader's Sum
  All. Truth: the Kα photopeak counts inside the box.
- ``sides``: the window sum minus a straight background through side bands
  one FWHM wide on either side of the box. A comparator, not a reader
  method.
- ``fit``: the reader's "Fit lines" (``peaks.fit_series``, the owner's
  rule): a Gaussian on a quadratic background over the box, its centre
  placed at the element's Kα and left free. The sum of the series fixes
  the centre and width; each spectrum is then a linear fit. Truth: the Kα
  photopeak counts.
- ``fit_fixed``: the same with the centre fixed at the element's energy.
- ``fit_width``: ``fit`` with the width fixed at the detector's resolution
  for the Kα1 + Kα2 blend (Fano formula; the condition's ``width_error``
  is how far off that is). The width is known from the detector, for
  example calibrated on the elastic peak.
- ``fit_strip``: Si escape stripping, then ``fit_width``. The escapes are
  y(E) − f(E + 1.740)·y(E + 1.740), with f Reed's fraction × the
  condition's ``escape_assumed`` (the detector's own by default: a
  calibrated fraction). This is the escape correction of AXIL and PyMca:
  the escape spectrum is the measured spectrum shifted down by Si Kα.
- ``fit_known``: ``fit_width`` plus every known peak inside the box,
  placed where it must be: the Si escape peaks of the elastic and Compton
  lines (when the detector has escapes) and the K lines of the other
  elements present. All share the fixed width. Their own flags (no height
  when absent) do not fail the line's result.
- ``fit_legacy``: ``fit`` with each spectrum's linear step weighted by
  the data's σ (``fit_series(weights='data')``), the reader's default
  until 2026-11-24. Weights from the data (Neyman's χ²) pull areas low at
  low counts; the reader's default is now the Poisson maximum likelihood
  of that step (F90 P1, the owner's decision on this gauntlet's
  evidence).
- ``fit_linear``, ``fit_cubic``: ``fit`` with another background.
- ``nonlinear``: one spectrum fitted alone (``peaks.fit_lines``), its own
  area and error. Diagnostic: that error leaves out the height–width
  covariance.

Designs:

- ``core``:
  - ``clean`` (no scatter);
  - ``smooth``: a Zn line at 1e-3 of the elastic, with only the valence
    Compton peak under it. This is the case the reader's model describes:
    a Gaussian on a smooth background;
  - ``hard``: every physical feature at its modelled size (O 1s core
    wing 20 %, Reed escapes, shelf 0.2 %, tail 1 %), with variants (Cu
    neighbour, 250 eV, one spectrum, fewer counts, Zn at 1e-2);
  - ``fe_easy``: Fe Kα, far from the scatter.
- ``grid``: one factor at a time from ``smooth``, each physical feature
  added alone. The factors are:
  - the line/elastic ratio, the counts, the resolution;
  - the Compton ratio, width and core wing, the angle;
  - the escape fraction (and the escape fraction assumed for stripping);
  - the tail, the shelf, the background;
  - the calibration, an error in the assumed width;
  - a Cu neighbour, Kβ;
  - the box, the series length.
- ``random``: conditions drawn over the same ranges, all features at once.
- ``series``: XFNTR curves. The line follows ``xfntr.yield_curve`` and the
  elastic the bulk scattering, over Qz, for the smooth and the hard
  detector. Each estimator's curve is divided by the truth.

The judging rules (proposed to Main 2026-11-23; the pull rule is hand-off
08's):

- **(a) honest**: |mean pull| < 0.2, pull SD within 0.90–1.15, and no
  failed fit. pull = (estimate − truth) / its error, where the truth is
  what the estimator should find: for the window sums, the Kα photopeak
  inside the box; for the fits, all of it.
- **(b) accurate**: |mean relative bias| < 1 %, and no failed fit. The bias,
  and the RMS error, are taken against the true line (all of its Kα
  photopeak counts) for every estimator, the window sum included: the
  owner's question is whether the sum distorts the curve.
- **(c) series**: the ratio curve's χ²/dof < 1.5 after one free scale,
  and every point with ≥ 100 true counts within 1 % of that scale. The
  mean over replicates is used, allowing two standard errors.
- **Verdict**: a method can replace the window sum in a condition if it
  passes (a) or (b), and its RMS error (relative to the truth) is no
  larger than the window sum's.
- **In range**: conditions with ≥ 100 Kα photopeak counts per spectrum,
  FWHM 150–250 eV at the line, and line/elastic ≥ 1e-3. F90 passes for a
  method if it passes in every in-range designed condition, in ≥ 95 % of
  the in-range random ones, and in the series.
- Random conditions, which have fewer replicates, are allowed two
  standard errors on every bound.
- A method that has failed in at least 10 spectra and at least 5 % of
  them, after 20 replicates, stops for that condition (``stopped_after``).
  It cannot pass there any more.

Outputs: ``conditions.csv``, ``verdict.csv`` (condition × method),
``pooled.csv`` (the random conditions together), ``series.csv`` and
``series_verdict.csv``, ``f90.csv``, ``summary.md``, ``hard_case.png`` (the
parts of the hard case, a draw, the box and the fits), ``series.png``,
``log.txt``; ``pulls.csv`` (every estimate; large) only with ``--rows``. All
the data are synthetic, so the outputs are public.
"""
import argparse
import csv
import math
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from lss_core import fluorescence as fluo, peaks          # noqa: E402
from synthetic import mca, xfntr, xrr                     # noqa: E402

PULL_BIAS_MAX = 0.2
PULL_SD = (0.9, 1.15)
REL_BIAS_MAX = 0.01
SERIES_CHI2_MAX = 1.5
SERIES_POINT_MAX = 0.01
SERIES_MIN_COUNTS = 100.0
IN_RANGE = dict(counts=100.0, fwhm=(0.150, 0.250), ratio=1e-3)
RANDOM_PASS = 0.95
STOP = dict(after=20, fails=10, fraction=0.05)
MONITOR = 1e7                # Monc of every spectrum: its N²/M term is negligible under the line
TIME = (10.0, 10.0)          # real, live (s)
KEY_METHODS = ('window', 'sides', 'fit', 'fit_fixed', 'fit_width', 'fit_strip', 'fit_known', 'fit_legacy')
METHODS = KEY_METHODS + ('fit_linear', 'fit_cubic', 'nonlinear')

SMOOTH_BEAM = mca.Beam(energy=10.0, angle=90.0, compton_ratio=1.0, compton_fwhm=0.19, compton_core=0.0)
SMOOTH_DET = mca.Detector(tail=0.0, shelf=0.0, escape=0.0)
HARD_BEAM = replace(SMOOTH_BEAM, compton_core=0.2)
HARD_DET = mca.Detector(tail=0.01, tail_slope=0.15, shelf=2e-3, escape=1.0)


@dataclass
class Cond:
    """One condition: the spectrum (``mca.spectrum``'s arguments) and how
    it is measured and judged."""
    describe: str
    factor: str = 'core'
    element: str = 'Zn'
    photons: float = 1e3              # the element's K photons per spectrum
    elastic: float = 1e6              # Rayleigh photons per spectrum
    beam: mca.Beam = SMOOTH_BEAM
    detector: mca.Detector = SMOOTH_DET
    background: float = 1.0           # counts per channel
    slope: float = 0.0
    offset: float = 0.0
    gain: float = 0.0
    others: tuple = ()                # ((element, photons as a fraction of the line's), ...)
    kb_scale: float = 1.0
    box: float = 2.0                  # half width of the box in FWHM of the line (below it)
    box_high: float = None            # above it, when different (None: ``box``)
    series: int = 10                  # spectra fitted together ("Fit lines" on a selection)
    width_error: float = 0.0          # relative error of the width that fit_width and the like assume
    escape_assumed: float = None      # escape fraction (× Reed) fit_strip assumes; None: the detector's own
    tolerant: bool = False            # few replicates: two standard errors allowed

    def spectrum(self, photons=None, elastic=None):
        n = self.photons if photons is None else photons
        lines = {self.element: n}
        lines.update({el: f * n for el, f in self.others})
        return mca.spectrum(lines, self.elastic if elastic is None else elastic, self.beam, self.detector,
                            self.background, self.slope, offset=self.offset, gain=self.gain,
                            kb_scale=self.kb_scale)

    @property
    def line(self):
        return mca.line_energy(self.element)

    @property
    def fwhm(self):
        return self.detector.fwhm(self.line)

    @property
    def line_fwhm(self):
        """FWHM of the Kα1 + Kα2 blend: the detector's, widened by the two
        lines' spread (Zn: +0.9 %)."""
        ls = [(e, i) for n, e, i in mca.ELEMENTS[self.element][1] if n in mca.KA]
        w = np.array([i for _, i in ls]) / sum(i for _, i in ls)
        e = np.array([v for v, _ in ls])
        var = float(np.sum(w * (e - np.sum(w * e)) ** 2))
        return math.sqrt(self.fwhm ** 2 + 8 * math.log(2) * var)

    @property
    def assumed_fwhm(self):
        return self.line_fwhm * (1.0 + self.width_error)

    @property
    def assumed_escape(self):
        return self.detector.escape if self.escape_assumed is None else self.escape_assumed

    def box_range(self):
        hi = self.box if self.box_high is None else self.box_high
        return self.line - self.box * self.fwhm, self.line + hi * self.fwhm

    def in_range(self, ka_counts):
        ratio = self.photons / self.elastic if self.elastic > 0 else math.inf
        return (ka_counts >= IN_RANGE['counts'] and IN_RANGE['fwhm'][0] <= self.fwhm <= IN_RANGE['fwhm'][1]
                and ratio >= IN_RANGE['ratio'])


def noise_for(fwhm_kev, e_kev, det=SMOOTH_DET):
    """Electronic noise (FWHM, keV) giving ``fwhm_kev`` at ``e_kev``."""
    return math.sqrt(max(fwhm_kev ** 2 - 8 * math.log(2) * det.eps * det.fano * e_kev, 1e-6))


def core():
    zn = mca.line_energy('Zn')
    hard = dict(beam=HARD_BEAM, detector=HARD_DET)
    return {
        'clean': Cond('Zn 1e4 photons, no scatter, 1 count per channel: the sanity check',
                      photons=1e4, elastic=0.0),
        'smooth': Cond('Zn 1e3 on 1e6 elastic (1e-3), valence Compton only, no escape, tail or shelf: the reader\'s '
                       'model is right (the grid\'s baseline)'),
        'hard': Cond('the hard case: Zn 1e3 on 1e6 elastic (1e-3), water-like Compton with the O 1s core wing (20 %), '
                     'Reed escapes, shelf 0.2 %, tail 1 %', **hard),
        'hard_strong': Cond('the hard case with Zn 1e4 (1e-2)', photons=1e4, **hard),
        'hard_low': Cond('the hard case with Zn 300 on 3e5 elastic (1e-3): fewer counts', photons=300, elastic=3e5, **hard),
        'hard_weak': Cond('the hard case with Zn 1e2 (1e-4): out of range', photons=1e2, **hard),
        'hard_core0': Cond('the hard case without the O 1s core wing', beam=SMOOTH_BEAM, detector=HARD_DET),
        'hard_cu': Cond('the hard case with Cu at 30 % of Zn (Cu Kα 8.048, Kβ 8.905 keV)', others=(('Cu', 0.3),), **hard),
        'hard_res250': Cond('the hard case at 250 eV FWHM', beam=HARD_BEAM,
                            detector=replace(HARD_DET, noise=noise_for(0.250, zn, HARD_DET))),
        'hard_single': Cond('the hard case, one spectrum fitted alone', series=1, **hard),
        'hard_box3': Cond('the hard case in a ±3 FWHM box', box=3.0, **hard),
        'smooth_box3': Cond('the smooth case in a ±3 FWHM box (the valence Compton tail curves across it)', box=3.0),
        'fe_easy': Cond('Fe Kα (6.40 keV) 1e3 on 1e6 elastic, hard detector and Compton: far from the scatter',
                        element='Fe', **hard),
    }


def grid():
    zn = mca.line_energy('Zn')
    g = {}

    def add(name, factor, describe, **kw):
        g[name] = Cond(describe, factor=factor, **kw)
    for n in (1e4, 3e3, 3e2, 1e2):
        add('ratio_%g' % (n / 1e6), 'line/elastic', 'Zn %g photons on 1e6 elastic' % n, photons=n)
    for f in (0.03, 0.1, 0.3, 3.0, 10.0):
        add('counts_x%g' % f, 'counts', 'Zn %g on %g elastic (1e-3)' % (1e3 * f, 1e6 * f), photons=1e3 * f,
            elastic=1e6 * f)
    for fw in (0.130, 0.150, 0.220, 0.250):
        add('fwhm_%d' % round(fw * 1000), 'resolution', 'FWHM %d eV at Zn Kα' % round(fw * 1000),
            detector=replace(SMOOTH_DET, noise=noise_for(fw, zn)))
    for r in (0.3, 3.0):
        add('compton_ratio_%g' % r, 'Compton', 'Compton/Rayleigh %g' % r, beam=replace(SMOOTH_BEAM, compton_ratio=r))
    for w in (0.1, 0.3, 0.4):
        add('compton_fwhm_%g' % w, 'Compton', 'valence Doppler FWHM %g keV' % w,
            beam=replace(SMOOTH_BEAM, compton_fwhm=w))
    for c in (0.02, 0.05, 0.1, 0.2):
        add('compton_core_%g' % c, 'Compton core', 'O 1s core Compton fraction %g' % c,
            beam=replace(SMOOTH_BEAM, compton_core=c))
    for a in (60.0, 120.0):
        add('angle_%d' % a, 'angle', 'scattering angle %d° (Compton at %.3f keV)' % (a, mca.compton_energy(10, a)),
            beam=replace(SMOOTH_BEAM, angle=a))
    for e in (0.3, 1.0, 5.0):
        add('escape_x%g' % e, 'escape', 'Si escape %g × Reed (%.2f %% at 10 keV)' % (e, 100 * e * mca.reed_escape(10)),
            detector=replace(SMOOTH_DET, escape=e))
    for e in (0.5, 2.0):
        add('escape_assumed_x%g' % e, 'escape', 'Reed escape; stripping assumes %g × that' % e,
            detector=replace(SMOOTH_DET, escape=1.0), escape_assumed=e)
    for t in (0.01, 0.03, 0.05):
        add('tail_%g' % t, 'tail', 'exponential tail %g %% (0.15 keV)' % (100 * t), detector=replace(SMOOTH_DET, tail=t))
    add('tail_slope_0.3', 'tail', 'tail 1 %, decay 0.3 keV', detector=replace(SMOOTH_DET, tail=0.01, tail_slope=0.3))
    for s in (0.002, 0.005, 0.01):
        add('shelf_%g' % s, 'shelf', 'shelf %g %%' % (100 * s), detector=replace(SMOOTH_DET, shelf=s))
    for b in (0.0, 5.0, 20.0):
        add('background_%g' % b, 'background', 'flat background %g per channel' % b, background=b)
    add('background_slope', 'background', 'background 1 + 2·E per channel (E in keV)', slope=2.0)
    for o in (-0.03, -0.01, 0.01, 0.03):
        add('offset_%+g' % o, 'calibration', 'calibration offset %+g keV' % o, offset=o)
    for gn in (-0.005, 0.005):
        add('gain_%+g' % gn, 'calibration', 'calibration gain %+g' % gn, gain=gn)
    for we in (-0.03, 0.03):
        add('width_error_%+g' % we, 'assumed width', 'the width assumed by fit_width and the like %+g %% off' % (100 * we),
            width_error=we)
    for c in (0.1, 0.3, 1.0):
        add('cu_%g' % c, 'neighbour', 'Cu at %g × Zn' % c, others=(('Cu', c),))
    add('kb_x1.25', 'Kβ', 'Kβ 25 % stronger than tabulated', kb_scale=1.25)
    for bx in (1.5, 3.0, 4.0):
        add('box_%g' % bx, 'box', 'box ±%g FWHM' % bx, box=bx)
    add('box_3_1.5', 'box', 'box −3 to +1.5 FWHM (short on the Compton side)', box=3.0, box_high=1.5)
    for n in (1, 3, 30):
        add('series_%d' % n, 'series length', '%d spectra fitted together' % n, series=n)
    return g


def random_conditions(n, seed=20261123):
    rng = np.random.default_rng(seed)
    zn = mca.line_energy('Zn')
    out = {}
    for k in range(n):
        lu = lambda lo, hi: float(10 ** rng.uniform(math.log10(lo), math.log10(hi)))
        det = mca.Detector(noise=noise_for(float(rng.uniform(0.13, 0.26)), zn), tail=float(rng.uniform(0, 0.05)),
                           tail_slope=float(rng.uniform(0.1, 0.3)), shelf=float(rng.uniform(0, 0.01)),
                           escape=float(rng.uniform(0, 5)))
        beam = mca.Beam(angle=float(rng.uniform(60, 120)), compton_ratio=lu(0.3, 3), compton_fwhm=float(rng.uniform(0.1, 0.4)),
                        compton_core=float(rng.uniform(0, 0.3)))
        photons = lu(30, 1e5)
        others = (('Cu', float(rng.uniform(0, 1))),) if rng.random() < 0.3 else ()
        c = Cond('random', factor='random', photons=photons, elastic=lu(1e4, 3e6), beam=beam, detector=det,
                 background=lu(0.1, 20), offset=float(rng.uniform(-0.03, 0.03)), gain=float(rng.uniform(-0.005, 0.005)),
                 others=others, box=float(rng.choice([1.5, 2.0, 3.0])), series=int(rng.choice([1, 3, 10, 30])),
                 width_error=float(rng.uniform(-0.03, 0.03)), tolerant=True)
        c.describe = ('Zn %.3g on %.3g elastic, FWHM %.0f eV, Compton %.2g×, w %.2f, core %.2f, %.0f°, escape %.1f×, '
                      'tail %.3f, shelf %.4f, bg %.2g, offset %+.3f, gain %+.4f, width %+.3f, box ±%g, series %d%s'
                      % (c.photons, c.elastic, 1000 * c.fwhm, beam.compton_ratio, beam.compton_fwhm, beam.compton_core,
                         beam.angle, det.escape, det.tail, det.shelf, c.background, c.offset, c.gain, c.width_error,
                         c.box, c.series, ', Cu %.2f × Zn' % others[0][1] if others else ''))
        out['random_%03d' % k] = c
    return out


@dataclass
class SeriesCond:
    """An XFNTR curve: the line's photons follow ``xfntr.yield_curve`` (peak
    ``photons``) and the elastic photons the bulk scattering (peak
    ``elastic``) plus a constant ``floor`` (scatter from elsewhere)."""
    describe: str
    cond: Cond
    sample: xfntr.Sample = field(default_factory=lambda: xfntr.Sample(surface=1.0, bulk=0.0))
    qz: tuple = tuple(np.round(np.linspace(0.006, 0.05, 23), 4))
    photons: float = 2e4
    elastic: float = 1e6
    floor: float = 2e4

    def spectra(self):
        qz = np.asarray(self.qz)
        y = xfntr.yield_curve(qz, self.sample)
        bulk = xfntr.yield_curve(qz, xfntr.Sample(0.0, 1.0, self.sample.escape))
        n_line = self.photons * y / y.max()
        n_el = self.elastic * bulk / bulk.max() + self.floor
        return [self.cond.spectrum(a, b) for a, b in zip(n_line, n_el)], n_line, n_el


def series_conditions():
    smooth = Cond('series', factor='series', series=1)
    hard = replace(smooth, beam=HARD_BEAM, detector=HARD_DET)
    return {
        'xfntr_smooth': SeriesCond('Zn at the surface only, smooth scatter: line 2e4 at Qc, elastic to 1e6 above Qc',
                                   smooth),
        'xfntr_smooth_weak': SeriesCond('the same, line 2e3 at Qc', smooth, photons=2e3),
        'xfntr_smooth_bulk': SeriesCond('Zn at the surface and in the bulk (c/Γ = 2e-4 per Å), smooth scatter', smooth,
                                        sample=xfntr.Sample(surface=1.0, bulk=2e-4)),
        'xfntr_hard': SeriesCond('Zn at the surface only, the hard detector and Compton', hard),
        'xfntr_hard_cu': SeriesCond('the hard series with a Cu neighbour at 30 %', replace(hard, others=(('Cu', 0.3),))),
    }


# ---- estimators -----------------------------------------------------------------

def normalise(counts, cal):
    par = {'Time': [0.0, TIME[0], TIME[1]]}
    return fluo.normalise_spectrum(counts, par, MONITOR, cal)


def scale():
    """Normalised units → counts: × M / (real/live)."""
    return MONITOR / (TIME[0] / TIME[1])


def fit_options(cond, centres, **kw):
    return peaks.FitOptions(shape='gaussian', background=kw.pop('background', 'quadratic'), n_peaks=len(centres),
                            centres=tuple(centres), x_range=cond.box_range(), window=50.0, **kw)


def strip_escape(d, factor=1.0):
    """Si escape stripping of a normalised spectrum (energy, value, σ): the
    escape of the photons at E + 1.740 keV, Reed's fraction × ``factor`` of
    what was measured there, comes off at E. σ gets the subtracted part's
    (tiny) error; a zero σ (zero counts) stays zero, as the reader leaves it."""
    e, y, s = d[:, 0], d[:, 1], d[:, 2]
    up = e + mca.SI_KA_KEV
    f = factor * np.array([mca.reed_escape(v) for v in up])
    out = d.copy()
    out[:, 1] = y - f * np.interp(up, e, y, right=0.0)
    out[:, 2] = np.where(s > 0, np.sqrt(s ** 2 + (f * np.interp(up, e, s, right=0.0)) ** 2), 0.0)
    return out


def linear_step(x, Y, S, ref, o, weights='data', iters=10):
    """``fit_series``'s per-spectrum step (heights and background by linear
    least squares, centres and widths from ``ref``); ``weights='model'``
    iterates σ² = k·model (k = σ²/y of the spectrum: τ/M), the Poisson
    maximum likelihood. Returns [(coef, err)] per spectrum."""
    lo, hi = ref.window
    w = (x >= lo) & (x <= hi) & np.isfinite(x)
    xw = x[w]
    nb = peaks.BACKGROUNDS[o.background] + 1
    u = (xw - ref.x0) / ref.xs
    A = np.column_stack([peaks._profile(xw, p.centre, p.fwhm, p.eta, p.shape) for p in ref.peaks]
                        + [u ** j for j in range(nb)])
    out = []
    for y, s in zip(Y, S):
        y = y[w]
        s = peaks.noise_sigma(y, s[w])
        coef = np.linalg.lstsq(A / s[:, None], y / s, rcond=None)[0]
        if weights == 'model':
            pos = y > 0
            k = float(np.median(s[pos] ** 2 / y[pos])) if pos.any() else float(np.median(s) ** 2)
            for _ in range(iters):
                mu = np.maximum(A @ coef, 0.1 * k)
                s = np.sqrt(k * mu)
                new = np.linalg.lstsq(A / s[:, None], y / s, rcond=None)[0]
                done = np.allclose(new, coef, rtol=1e-9, atol=1e-12 * max(np.abs(coef).max(), 1e-300))
                coef = new
                if done:
                    break
            s = np.sqrt(k * np.maximum(A @ coef, 0.1 * k))
        cov = np.linalg.pinv((A / s[:, None]).T @ (A / s[:, None]))
        out.append((coef, np.sqrt(np.clip(np.diag(cov), 0, None))))
    return out


def _ka_index(ref, energy):
    return int(np.argmin([abs(p.centre - energy) for p in ref.peaks]))


def _from_heights(ref, j, steps, step):
    p = ref.peaks[j]
    f = peaks._area(1.0, p.fwhm, p.eta, p.shape) / step * scale()
    return [(float(c[j] * f), float(e[j] * f)) for c, e in steps]


def known_centres(cond):
    """Centres of ``fit_known``: the line, then the escape peaks of the
    elastic and Compton lines (when the detector has escapes) and the other
    elements' K lines inside the box."""
    lo, hi = cond.box_range()
    extra = [cond.beam.energy - mca.SI_KA_KEV, cond.beam.compton - mca.SI_KA_KEV] if cond.assumed_escape > 0 else []
    for el, _ in cond.others:
        extra += [mca.line_energy(el, 'Ka'), mca.line_energy(el, 'Kb')]
    margin = 0.5 * cond.fwhm
    return [cond.line] + [e for e in extra if lo - margin < e < hi + margin and abs(e - cond.line) > 0.5 * cond.fwhm]


FIT_SERIES = {                       # methods that are peaks.fit_series with these options
    'fit': {}, 'fit_fixed': dict(fix_centres=True), 'fit_width': 'width', 'fit_strip': 'width',
    'fit_linear': dict(background='linear'), 'fit_cubic': dict(background='cubic'), 'fit_legacy': {},
}


def estimate(cond, spectra, counts, methods):
    """{method: [(estimate, error, truth for the pull, the true line) or None
    (failed) per spectrum]}. The pull's truth is what the estimator should
    find: the Kα photopeak inside the box for the window sums, all of it for
    the fits. Accuracy is judged against the true line, all of its
    photopeak counts, for every estimator (Main, 2026-11-23: "does the sum
    distort the curve" is answered against the true line)."""
    cal = spectra[0].calib
    data = [normalise(c, cal) for c in counts]
    x = data[0][:, 0]
    step = float(np.median(np.abs(np.diff(x))))
    Y = [d[:, 1] for d in data]
    S = [d[:, 2] for d in data]
    lo, hi = cond.box_range()
    box = (x >= lo) & (x <= hi)
    ka_total = [float(s.photopeak(cond.element).sum()) for s in spectra]
    ka_box = [float(s.photopeak(cond.element)[box].sum()) for s in spectra]
    out = {}
    n = len(spectra)
    fail = [None] * n
    refs = {}
    stripped = None
    for m in methods:
        try:
            if m == 'window':
                r = [fluo.window_sum(d, lo, hi) for d in data]
                out[m] = [(v * scale(), e * scale(), t) for (v, e, _, _), t in zip(r, ka_box)]
            elif m == 'sides':
                out[m] = [sides(d, lo, hi, cond.fwhm) + (t,) for d, t in zip(data, ka_box)]
            elif m in FIT_SERIES:
                kw = FIT_SERIES[m]
                kw = dict(fwhm=cond.assumed_fwhm) if kw == 'width' else dict(kw)
                YY, SS = Y, S
                if m == 'fit_strip':
                    if stripped is None:
                        sd = [strip_escape(d, cond.assumed_escape) for d in data]
                        stripped = ([d[:, 1] for d in sd], [d[:, 2] for d in sd])
                    YY, SS = stripped
                o = fit_options(cond, [cond.line], **kw)
                ref, each = peaks.fit_series(x, YY, SS, o, weights='data' if m == 'fit_legacy' else 'poisson')
                refs[m] = (ref, o)
                if not each:
                    out[m] = fail
                    continue
                j = _ka_index(ref, cond.line)
                out[m] = [(r.peaks[j].area / step * scale(), r.peaks[j].area_err / step * scale(), t)
                          for r, t in zip(each, ka_total)]
            elif m == 'fit_known':
                o = fit_options(cond, known_centres(cond), fwhm=cond.assumed_fwhm)
                tot = np.sum(Y, axis=0)
                st = np.sqrt(np.sum(np.square(S), axis=0))
                ref = peaks.fit(x, tot, st, o)
                if not ref.peaks:
                    out[m] = fail
                    continue
                j = _ka_index(ref, cond.line)
                p = ref.peaks[j]
                lo_w, hi_w = ref.window
                tol = 0.02 * (hi_w - lo_w)
                if p.height <= 0 or p.centre - lo_w < tol or hi_w - p.centre < tol or abs(p.centre - cond.line) > cond.fwhm:
                    out[m] = fail
                    continue
                got = _from_heights(ref, j, linear_step(x, Y, S, ref, o, 'model'), step)
                out[m] = [g + (t,) for g, t in zip(got, ka_total)]
            elif m == 'nonlinear':
                o = fit_options(cond, [cond.line])
                r = peaks.fit_lines(x, Y[0], [cond.line], S[0], o)
                if not (r.ok and r.peaks):
                    out[m] = [None]
                    continue
                p = r.peaks[_ka_index(r, cond.line)]
                out[m] = [(p.area / step * scale(), p.area_err / step * scale(), ka_total[0])]
        except Exception:                      # counted as a failure
            out[m] = fail if m != 'nonlinear' else [None]
    for m, rows in out.items():                # + the true line, which accuracy is judged against
        out[m] = [r + (ka_total[k],) if (r is not None and np.isfinite(r[0]) and np.isfinite(r[1]) and r[1] > 0)
                  else None for k, r in enumerate(rows)]
    return out


def sides(d, lo, hi, width):
    """Window sum minus a straight background through side bands ``width``
    wide on either side; error with the bands' own."""
    e, y, s = d[:, 0], d[:, 1], d[:, 2]
    box = (e >= lo) & (e <= hi)
    L = (e >= lo - width) & (e < lo)
    R = (e > hi) & (e <= hi + width)
    nL, nR, n = int(L.sum()), int(R.sum()), int(box.sum())
    xL, xR, xb = e[L].mean(), e[R].mean(), e[box].mean()
    t = (xb - xL) / (xR - xL)
    B = n * ((1 - t) * y[L].mean() + t * y[R].mean())
    vB = n ** 2 * ((1 - t) ** 2 * np.sum(s[L] ** 2) / nL ** 2 + t ** 2 * np.sum(s[R] ** 2) / nR ** 2)
    return (float((y[box].sum() - B) * scale()), float(math.sqrt(np.sum(s[box] ** 2) + vB) * scale()))


# ---- running and judging ---------------------------------------------------------

def _stop(rows, rep):
    """A method stops once it cannot pass any more (``STOP``)."""
    fails = sum(1 for r in rows if r[-1] is None)
    return rep + 1 >= STOP['after'] and fails >= max(STOP['fails'], STOP['fraction'] * len(rows))


def run_condition(args):
    """One condition: ``n_rep`` replicates. Returns (name, rows by method,
    ka photopeak per spectrum, stopped {method: replicates run}, seconds)."""
    name, cond, n_rep, methods, ci = args
    t0 = time.time()
    spec = cond.spectrum()
    rows = defaultdict(list)
    active, stopped = list(methods), {}
    for rep in range(n_rep):
        rng = np.random.default_rng([20261123, ci, rep])
        counts = [spec.draw(rng) for _ in range(cond.series)]
        for m, r in estimate(cond, [spec] * cond.series, counts, active).items():
            rows[m] += [(rep,) + v if v is not None else (rep, None) for v in r]
        for m in list(active):
            if m != 'window' and _stop(rows[m], rep):
                active.remove(m)
                stopped[m] = rep + 1
    return name, dict(rows), float(spec.photopeak(cond.element).sum()), stopped, time.time() - t0


def run_series(args):
    name, sc, n_rep, methods, ci = args
    t0 = time.time()
    spectra, n_line, n_el = sc.spectra()
    rows = defaultdict(list)            # method -> [(rep, point, est, err, truth) or (rep, point, None)]
    active = [m for m in methods if m != 'nonlinear']
    for rep in range(n_rep):
        rng = np.random.default_rng([20261124, ci, rep])
        counts = [s.draw(rng) for s in spectra]
        for m, r in estimate(sc.cond, spectra, counts, active).items():
            rows[m] += [(rep, k) + v if v is not None else (rep, k, None) for k, v in enumerate(r)]
    ka = [float(s.photopeak(sc.cond.element).sum()) for s in spectra]
    return name, dict(rows), ka, list(n_el), time.time() - t0


def judge(rows, tolerant):
    good = [r for r in rows if r[-1] is not None and len(r) > 2]
    n_fail = len(rows) - len(good)
    if len(good) < 3:
        return dict(n=len(rows), failed=n_fail, pull_mean=math.nan, pull_sd=math.nan, rel_bias=math.nan,
                    rel_rmse=math.nan, honest=False, accurate=False)
    est, err, tru, line = (np.array([r[k] for r in good]) for k in (-4, -3, -2, -1))
    pull = (est - tru) / err
    rel = est / line - 1
    bias, sd = float(pull.mean()), float(pull.std(ddof=1))
    rb, rmse = float(rel.mean()), float(math.sqrt(np.mean(rel ** 2)))
    n = len(good)
    se_m, se_sd, se_r = (sd / math.sqrt(n), sd / math.sqrt(2 * (n - 1)), float(rel.std(ddof=1)) / math.sqrt(n)) \
        if tolerant else (0.0, 0.0, 0.0)
    honest = (n_fail == 0 and abs(bias) < PULL_BIAS_MAX + 2 * se_m
              and PULL_SD[0] - 2 * se_sd <= sd <= PULL_SD[1] + 2 * se_sd)
    accurate = n_fail == 0 and abs(rb) < REL_BIAS_MAX + 2 * se_r
    return dict(n=len(rows), failed=n_fail, pull_mean=bias, pull_sd=sd, rel_bias=rb, rel_rmse=rmse,
                honest=honest, accurate=accurate)


def verdict(results, conds, methods):
    out = []
    for name, (rows, ka, stopped) in results.items():
        c = conds[name]
        j = {m: judge(rows.get(m, []), c.tolerant) for m in methods}
        w = j.get('window')
        for m in methods:
            r = j[m]
            ok = r['honest'] or r['accurate']
            replaces = '' if m == 'window' or w is None else bool(
                ok and np.isfinite(r['rel_rmse']) and (not np.isfinite(w['rel_rmse']) or r['rel_rmse'] <= w['rel_rmse']))
            out.append(dict(condition=name, factor=c.factor, method=m, in_range=c.in_range(ka), ka_counts=ka,
                            pull_against='Kα in the box' if m in ('window', 'sides') else 'Kα line', **r, passes=ok, replaces_window=replaces, stopped_after=stopped.get(m, '')))
    return out


def series_judge(results, sconds, methods):
    """Per series condition and method: the mean χ²/dof of the ratio curve
    after one free scale, and the worst point's mean deviation from it."""
    table, ver = [], []
    for name, (rows, ka, n_el) in results.items():
        for m in methods:
            rr = rows.get(m)
            if not rr:
                continue
            by_rep = defaultdict(dict)
            fails = 0
            for r in rr:
                if r[-1] is None:
                    fails += 1
                    continue
                rep, k, est, err, _, line = r
                by_rep[rep][k] = (est / line, err / line)
            n_pts = len(ka)
            chi2, dev = [], np.full((len(by_rep), n_pts), np.nan)
            for i, (rep, pts) in enumerate(sorted(by_rep.items())):
                if len(pts) < n_pts:
                    continue
                rat = np.array([pts[k][0] for k in range(n_pts)])
                sig = np.array([pts[k][1] for k in range(n_pts)])
                wts = 1 / sig ** 2
                sc = float(np.sum(wts * rat) / np.sum(wts))
                chi2.append(float(np.sum(((rat - sc) / sig) ** 2) / (n_pts - 1)))
                dev[i] = rat / sc - 1
            dev = dev[np.all(np.isfinite(dev), axis=1)]
            mean_dev = dev.mean(axis=0) if len(dev) else np.full(n_pts, np.nan)
            se_dev = dev.std(axis=0, ddof=1) / math.sqrt(len(dev)) if len(dev) > 1 else np.full(n_pts, np.nan)
            judged = np.array(ka) >= SERIES_MIN_COUNTS
            worst = float(np.nanmax(np.abs(mean_dev[judged]))) if judged.any() else math.nan
            pts_ok = bool(np.all(np.abs(mean_dev[judged]) <= SERIES_POINT_MAX + 2 * se_dev[judged]))
            c2 = float(np.mean(chi2)) if chi2 else math.nan
            c2_se = float(np.std(chi2, ddof=1) / math.sqrt(len(chi2))) if len(chi2) > 1 else 0.0
            ok = fails == 0 and np.isfinite(c2) and c2 < SERIES_CHI2_MAX + 2 * c2_se and pts_ok
            ver.append(dict(condition=name, method=m, replicates=len(dev), failed=fails, chi2_dof=c2,
                            worst_point=worst, passes=ok))
            for k in range(n_pts):
                table.append(dict(condition=name, method=m, point=k + 1, ka_counts=ka[k], elastic=n_el[k],
                                  mean_ratio=1 + mean_dev[k], se=se_dev[k]))
    return table, ver


def pooled(ver, methods):
    """The random conditions together: the fraction where each method passes
    and replaces the window sum, over all and over those in range."""
    out = []
    for m in methods:
        rows = [r for r in ver if r['factor'] == 'random' and r['method'] == m]
        if not rows:
            continue
        inr = [r for r in rows if r['in_range']]
        frac = lambda rs, key: (sum(1 for r in rs if r[key] is True) / len(rs)) if rs else math.nan
        out.append(dict(method=m, conditions=len(rows), in_range=len(inr), passes=frac(rows, 'passes'),
                        passes_in_range=frac(inr, 'passes'),
                        replaces_window_in_range=frac(inr, 'replaces_window') if m != 'window' else '',
                        honest_in_range=frac(inr, 'honest'), accurate_in_range=frac(inr, 'accurate')))
    return out


def f90_verdict(ver, pool, sver, methods):
    """Per fit method: designed in-range conditions all pass, random in-range
    ≥ 95 %, series all pass."""
    out = []
    for m in methods:
        if m == 'window':
            continue
        des = [r for r in ver if r['method'] == m and r['factor'] != 'random' and r['in_range']]
        bad = [r['condition'] for r in des if r['passes'] is not True or r['replaces_window'] is False]
        pr = next((p for p in pool if p['method'] == m), None)
        rnd = pr['passes_in_range'] if pr else math.nan
        ser = [r for r in sver if r['method'] == m]
        sbad = [r['condition'] for r in ser if not r['passes']]
        ok = (not bad) and (not ser or not sbad) and (pr is None or rnd >= RANDOM_PASS)
        out.append(dict(method=m, designed_in_range=len(des), designed_failed=';'.join(bad), random_in_range_pass=rnd,
                        series_failed=';'.join(sbad), f90_passes=ok))
    return out


# ---- outputs --------------------------------------------------------------------

def write_csv(path, rows):
    if not rows:
        return
    keys = list(rows[0])
    for r in rows[1:]:
        keys += [k for k in r if k not in keys]
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})


def _f(x, fmt='%.3f'):
    if isinstance(x, bool):
        return 'yes' if x else '**no**'
    if x == '' or x is None:
        return ''
    try:
        return fmt % x if np.isfinite(x) else '—'
    except TypeError:
        return str(x)


def summary(ver, pool, sver, f90, conds, sconds, args, out):
    methods = [m for m in METHODS if any(r['method'] == m for r in ver + sver)]
    L = ['# MCA line-fit gauntlet (F90)', '',
         'Generated by `tests/tools/mca_fit_gauntlet.py` (design %s, %d replicates per designed condition, %d random '
         'conditions × %d, %d series replicates). Synthetic spectra from `tests/synthetic/mca.py`; the rules are in the '
         'tool\'s docstring: (a) honest: |mean pull| < %.1f and pull SD %.2f–%.2f with no failure; (b) accurate: '
         '|relative bias| < %.0f %%; a method replaces the window sum where it passes (a) or (b) with an RMS error no '
         'larger than the window\'s. "In range": ≥ %d Kα counts, FWHM %d–%d eV, line/elastic ≥ %g.'
         % (args.design, args.replicates, args.random if args.design in ('random', 'all') else 0, args.random_replicates,
            args.series_replicates if args.design in ('series', 'all') else 0, PULL_BIAS_MAX, *PULL_SD,
            100 * REL_BIAS_MAX, IN_RANGE['counts'], 1000 * IN_RANGE['fwhm'][0], 1000 * IN_RANGE['fwhm'][1],
            IN_RANGE['ratio']), '']
    kinds = [('the reader\'s', ('window', 'fit', 'fit_fixed')), ('the reader\'s until 2026-11-24', ('fit_legacy',)),
             ('a comparator, not a reader method', ('sides',)),
             ('candidates, not defaults', ('fit_width', 'fit_strip', 'fit_known', 'fit_linear', 'fit_cubic')),
             ('a diagnostic', ('nonlinear',))]
    L += ['Estimators: ' + '; '.join('%s: %s' % (k, ', '.join('`%s`' % m for m in ms if m in methods))
                                     for k, ms in kinds if any(m in methods for m in ms)) + '.', '']
    if f90:
        L += ['## Verdict per method', '',
              '| Method | Designed in range | Designed that fail | Random in range passing | Series that fail | F90 passes |',
              '|---|---|---|---|---|---|']
        for r in f90:
            L.append('| %s | %d | %s | %s | %s | %s |' % (r['method'], r['designed_in_range'], r['designed_failed'] or '—',
                                                          _f(r['random_in_range_pass'], '%.2f'), r['series_failed'] or '—',
                                                          _f(r['f90_passes'])))
        L.append('')
    des = [n for n, c in conds.items() if c.factor != 'random']
    if des:
        L += ['## Designed conditions', '',
              'Each cell: mean pull / pull SD / relative bias (%). The pull is against what the estimator should find '
              '(window and sides: the Kα photopeak inside the box; the fits: all of it); the bias is against the true '
              'line (all of its photopeak counts) for every estimator. **Bold** where the method passes neither (a) nor '
              '(b); failures counted in brackets.', '',
              '| Condition | In range | Kα counts | ' + ' | '.join(methods) + ' |',
              '|---|---|---|' + '---|' * len(methods)]
        idx = {(r['condition'], r['method']): r for r in ver}
        for n in des:
            cells = []
            first = None
            for m in methods:
                r = idx.get((n, m))
                if r is None:
                    cells.append('')
                    continue
                first = first or r
                txt = '%s / %s / %s' % (_f(r['pull_mean'], '%+.2f'), _f(r['pull_sd'], '%.2f'), _f(100 * r['rel_bias'], '%+.2f'))
                if r['failed']:
                    txt += ' [%d]' % r['failed']
                cells.append(txt if r['passes'] else '**%s**' % txt)
            L.append('| %s | %s | %.0f | %s |' % (n, 'yes' if first and first['in_range'] else 'no',
                                                 first['ka_counts'] if first else math.nan, ' | '.join(cells)))
        L += ['', 'Conditions:', '']
        L += ['- `%s` (%s): %s' % (n, conds[n].factor, conds[n].describe) for n in des]
        L.append('')
    if pool:
        L += ['## Random conditions (pooled)', '',
              '| Method | Conditions | In range | Pass (all) | Pass (in range) | Honest (in range) | Accurate (in range) '
              '| Replaces window (in range) |', '|---|---|---|---|---|---|---|---|']
        for p in pool:
            L.append('| %s | %d | %d | %s | %s | %s | %s | %s |' % (
                p['method'], p['conditions'], p['in_range'], _f(p['passes'], '%.2f'), _f(p['passes_in_range'], '%.2f'),
                _f(p['honest_in_range'], '%.2f'), _f(p['accurate_in_range'], '%.2f'),
                _f(p['replaces_window_in_range'], '%.2f')))
        L.append('')
    if sver:
        L += ['## Series (XFNTR curves)', '',
              'Mean χ²/dof of estimate/truth after one free scale; the worst point\'s mean deviation from that scale '
              '(points with ≥ %d Kα counts).' % SERIES_MIN_COUNTS, '',
              '| Series | Method | χ²/dof | Worst point | Failed | Passes |', '|---|---|---|---|---|---|']
        for r in sver:
            L.append('| %s | %s | %s | %s | %d | %s |' % (r['condition'], r['method'], _f(r['chi2_dof'], '%.2f'),
                                                          _f(100 * r['worst_point'], '%.2f %%'), r['failed'],
                                                          _f(r['passes'])))
        L += ['', 'Series:', ''] + ['- `%s`: %s' % (n, s.describe) for n, s in sconds.items()] + ['']
    with open(os.path.join(out, 'summary.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')


def figure_hard_case(out, names=('smooth', 'smooth_box3', 'hard')):
    """The parts of the smooth and the hard case on a log scale, the mean of
    one series of draws, the box, and the fits of ``fit``, ``fit_width`` and
    ``fit_known`` to the series' sum (shown per spectrum)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    conds = core()
    fig, axes = plt.subplots(len(names), 1, figsize=(9, 4.6 * len(names)), squeeze=False)
    for ax, name in zip(axes[:, 0], names):
        cond = conds[name]
        s = cond.spectrum()
        e = s.energy
        sel = (e > 7.6) & (e < 10.4)
        rng = np.random.default_rng(7)
        counts = [s.draw(rng) for _ in range(cond.series)]
        ax.step(e[sel], np.mean(counts, axis=0)[sel], where='mid', color='0.6', lw=0.8,
                label='mean of %d draws' % cond.series)
        ax.plot(e[sel], s.expected[sel], color='k', lw=1.2, label='expected (all)')
        parts = [('Zn Kα photopeak', s.photopeak('Zn'), 'C3'), ('Zn Kβ photopeak', s.photopeak('Zn', 'Kb'), 'C1'),
                 ('Rayleigh + Compton photopeak', s.part(['Rayleigh', 'Compton'], ['peak']), 'C0'),
                 ('escape peaks', s.part(None, ['escape']), 'C2'),
                 ('tails + shelves', s.part(None, ['tail', 'shelf']), 'C4'),
                 ('background', s.part(['background']), 'C7')]
        for lab, v, col in parts:
            if np.any(v[sel] > 1e-3):
                ax.plot(e[sel], np.maximum(v[sel], 1e-3), color=col, lw=1, label=lab)
        lo, hi = cond.box_range()
        ax.axvspan(lo, hi, color='C3', alpha=0.08, label='box −%g/+%g FWHM' % (cond.box, cond.box_high or cond.box))
        data = [normalise(c, s.calib) for c in counts]
        x = data[0][:, 0]
        tot = np.sum([d[:, 1] for d in data], axis=0)
        st = np.sqrt(np.sum([d[:, 2] ** 2 for d in data], axis=0))
        ka = s.photopeak(cond.element).sum()
        for m, ls in (('fit', '--'), ('fit_width', ':'), ('fit_known', '-.')):
            cen = known_centres(cond) if m == 'fit_known' else [cond.line]
            o = fit_options(cond, cen, **({} if m == 'fit' else dict(fwhm=cond.assumed_fwhm)))
            r = peaks.fit(x, tot, st, o)
            if r.peaks:
                p = r.peaks[_ka_index(r, cond.line)]
                got = p.area / float(np.median(np.diff(x))) * scale() / len(data)
                xx = np.linspace(r.window[0], r.window[1], 400)
                ax.plot(xx, r.model(xx) * scale() / len(data), 'k' + ls, lw=1.3,
                        label='%s: Kα %.0f (true %.0f)%s' % (m, got, ka, '' if r.ok else ', not ok'))
        ax.set_yscale('log')
        ax.set_ylim(0.05, s.expected[sel].max() * 2)
        ax.set_xlabel('energy (keV, nominal calibration)')
        ax.set_ylabel('counts per 10 eV channel')
        ax.set_title('%s: %s' % (name, cond.describe), fontsize=8)
        ax.legend(fontsize=7, ncol=2, loc='upper left')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'hard_case.png'), dpi=110)
    plt.close(fig)


def figure_series(out, table, sconds):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names = list(sconds)
    fig, axes = plt.subplots(len(names), 1, figsize=(8, 2.6 * len(names)), sharex=True, squeeze=False)
    for ax, n in zip(axes[:, 0], names):
        qz = np.asarray(sconds[n].qz)
        for i, m in enumerate(KEY_METHODS):
            rows = [r for r in table if r['condition'] == n and r['method'] == m]
            if not rows:
                continue
            y = np.array([r['mean_ratio'] for r in rows])
            se = np.array([r['se'] for r in rows])
            ax.errorbar(qz[:len(y)], y, 2 * se, label=m, color='C%d' % i, lw=1, capsize=2, marker='.')
        ax.axhline(1, color='k', lw=0.6)
        ax.axvline(xrr.qc(xrr.RHO_WATER), color='0.5', ls=':', lw=0.8)
        ax.set_ylabel('estimate / truth\n(÷ fitted scale)')
        ax.set_title('%s: %s' % (n, sconds[n].describe), fontsize=8)
        lim = np.nanmax([abs(r['mean_ratio'] - 1) for r in table if r['condition'] == n] + [0.02])
        ax.set_ylim(1 - min(1.2 * lim, 0.5), 1 + min(1.2 * lim, 0.5))
    axes[0, 0].legend(fontsize=7, ncol=3)
    axes[-1, 0].set_xlabel('Qz (1/Å); dotted: Qc of water')
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'series.png'), dpi=110)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--design', default='core', choices=['core', 'grid', 'random', 'series', 'all'])
    ap.add_argument('--replicates', type=int, default=200, help='per designed condition (a replicate is one series)')
    ap.add_argument('--random', type=int, default=150, help='number of random conditions')
    ap.add_argument('--random-replicates', type=int, default=40)
    ap.add_argument('--series-replicates', type=int, default=60, help='replicates of each XFNTR curve')
    ap.add_argument('--methods', default='key', help="'key' (%s), 'all' or a comma-separated list" % ', '.join(KEY_METHODS))
    ap.add_argument('--conditions', default='', help='only these (comma-separated names)')
    ap.add_argument('--jobs', type=int, default=0, help='worker processes (0: one per CPU)')
    ap.add_argument('--rows', action='store_true', help='also write pulls.csv (every estimate; large)')
    a = ap.parse_args(argv)
    methods = list(METHODS) if a.methods == 'all' else (list(KEY_METHODS) if a.methods == 'key' else a.methods.split(','))
    for m in methods:
        if m not in METHODS:
            ap.error('unknown method %r (use %s)' % (m, ', '.join(METHODS)))
    if 'window' not in methods:
        methods.insert(0, 'window')               # the reference every verdict needs
    designed, randoms, sconds = {}, {}, {}
    if a.design in ('core', 'all'):
        designed.update(core())
    if a.design in ('grid', 'all'):
        designed.update(grid())
    if a.design in ('random', 'all'):
        randoms = random_conditions(a.random)
    if a.design in ('series', 'all'):
        sconds = series_conditions()
    if a.conditions:
        keep = set(a.conditions.split(','))
        designed = {k: v for k, v in designed.items() if k in keep}
        randoms = {k: v for k, v in randoms.items() if k in keep}
        sconds = {k: v for k, v in sconds.items() if k in keep}
    os.makedirs(a.out, exist_ok=True)
    logf = open(os.path.join(a.out, 'log.txt'), 'w')

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + '\n')
    conds = dict(designed, **randoms)
    names = list(conds)
    jobs = a.jobs or os.cpu_count() or 1
    tasks = [(n, conds[n], a.replicates if conds[n].factor != 'random' else a.random_replicates, methods, i)
             for i, n in enumerate(names)]
    stasks = [(n, sconds[n], a.series_replicates, methods, i) for i, n in enumerate(sconds)]
    results, sresults = {}, {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for name, rows, ka, stopped, sec in ex.map(run_condition, tasks):
            results[name] = (rows, ka, stopped)
            log('%s: %.0f s' % (name, sec))
        for name, rows, ka, n_el, sec in ex.map(run_series, stasks):
            sresults[name] = (rows, ka, n_el)
            log('%s (series): %.0f s' % (name, sec))
    log('all: %.0f s on %d workers' % (time.time() - t0, jobs))
    ver = verdict(results, conds, methods)
    pool = pooled(ver, methods)
    table, sver = series_judge(sresults, sconds, methods)
    f90 = f90_verdict(ver, pool, sver, methods)
    write_csv(os.path.join(a.out, 'conditions.csv'),
              [dict(condition=n, factor=c.factor, element=c.element, photons=c.photons, elastic=c.elastic,
                    fwhm_kev=c.fwhm, box=c.box, box_high=c.box_high if c.box_high is not None else c.box, series=c.series, background=c.background, offset=c.offset, gain=c.gain,
                    compton_ratio=c.beam.compton_ratio, compton_fwhm=c.beam.compton_fwhm, compton_core=c.beam.compton_core,
                    angle=c.beam.angle, escape=c.detector.escape, tail=c.detector.tail, shelf=c.detector.shelf,
                    others=';'.join('%s %g' % o for o in c.others), describe=c.describe) for n, c in conds.items()])
    write_csv(os.path.join(a.out, 'verdict.csv'), ver)
    write_csv(os.path.join(a.out, 'pooled.csv'), pool)
    write_csv(os.path.join(a.out, 'series.csv'), table)
    write_csv(os.path.join(a.out, 'series_verdict.csv'), sver)
    write_csv(os.path.join(a.out, 'f90.csv'), f90)
    if a.rows:
        rows = []
        for name, (rr, _, _) in results.items():
            for m, lst in rr.items():
                rows += [dict(condition=name, method=m, rep=r[0], estimate=r[1], error=r[2], truth=r[3], line=r[4])
                         if r[-1] is not None and len(r) > 2 else dict(condition=name, method=m, rep=r[0], failed=1)
                         for r in lst]
        write_csv(os.path.join(a.out, 'pulls.csv'), rows)
    summary(ver, pool, sver, f90, conds, sconds, a, a.out)
    if a.design in ('core', 'all'):
        figure_hard_case(a.out)
    if sconds:
        figure_series(a.out, table, sconds)
    logf.close()


if __name__ == '__main__':
    main()
