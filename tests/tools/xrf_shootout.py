"""XRF shootout: the reader's ways of measuring a fluorescence line against
the open-source XRF packages, on synthetic MCA spectra with known truth
(2026-11-25; questions in ``docs/studies/xrf_shootout/QUESTIONS.md``).

    python tests/tools/xrf_shootout.py --out docs/studies/xrf_shootout [--design all]
        [--replicates 100] [--jobs 30] [--methods all|a,b] [--conditions a,b]

Run from the repository root, in an environment with PyMca5, scikit-beam
and xraylarch (``docs/studies/xrf_shootout/README.md`` says how it was
built). A method whose package is missing is skipped and said so.

**The contestants.** The reader's (``lss_core``):

- ``window``: Sum All over the box (``fluorescence.window_sum``);
- ``fit_data``: "Fit lines" with data weights (the default until 2026-11-24);
- ``p1``: "Fit lines" by Poisson likelihood (the default since 2026-11-24);
- ``p1p2p3``: ``p1`` with the width fixed at the detector's resolution and
  the Si escape peaks stripped (the reader's options).

All four work in the **box**, the main line ± 2 FWHM of the detector; the
fits are a Gaussian on a quadratic, centres and widths from the sum of the
series, each spectrum linear (``peaks.fit_series``).

The others, each configured as its own documentation and GUI suggest, with
the same knowledge the reader's options get (nominal calibration, the
detector's noise and Fano factor, the beam energy, the elements present):

- ``xeray``: XeRay (Z. Gong, Lee group, U. Chicago;
  github.com/ZhiliangGong/xeray, MATLAB), ported line for line from
  ``functions/fluoCurveFit.m`` and ``XeLineshape.m``: one Gaussian on a
  straight line over the box, **unweighted** least squares
  (``lsqnonlin``, trust-region-reflective, its bounds), area A·σ·√(2π),
  error √(Σ counts in the box). Each spectrum alone.
- ``pymca``: PyMca (V. A. Solé et al., Spectrochim. Acta B 62, 63 (2007);
  github.com/silx-kit/pymca), ``ClassMcaTheory``: the whole spectrum from
  1.5 keV below the lowest line to 0.6 keV above the beam, every line of
  every element present at PyMca's own ratios, Rayleigh and Compton
  peaks, Si escape peaks, SNIP background (width 30 channels), Gaussian
  peaks, statistical weights; zero and gain refined, noise and Fano fixed
  at the detector's. Each spectrum alone.
- ``pymca_tails``: the same with PyMca's Hypermet peaks (short tail, long
  tail and step, all refined: ``hypermetflag`` 15).
- ``pymca_snip60``, ``pymca_snip100``, ``pymca_poly``: ``pymca`` with a
  wider SNIP background (60 or 100 channels: 4 and 6 FWHM), or with no
  strip and PyMca's linear polynomial continuum (order 5) instead. The
  figures' "best PyMca" picks, per condition, whichever of the five PyMca
  settings came closest to the truth: the most generous PyMca.
- ``pyxrf``: PyXRF's engine (NSLS-II; scikit-beam's ``xrf_model``,
  github.com/scikit-beam/scikit-beam, which github.com/NSLS2/PyXRF calls):
  as PyXRF does for a map, a nonlinear fit of the summed series (strategy
  ``fit_with_tail``: Compton width, tail and angle free; SNIP background),
  then each spectrum by weighted non-negative least squares with that
  model. No errors are reported.
- ``larch``: Larch (M. Newville; github.com/xraypy/xraylarch),
  ``larch.xrf.xrf_model``: Hypermet peaks for lines and scatter (each
  scatter peak with its own width factor, tail and step), Si escape, a
  nonlinear fit of the summed series, then each spectrum by its
  ``decompose_spectrum`` (least squares on the fitted components, as its
  map tools do). No errors are reported.
- ``larch_each``: Larch's nonlinear fit of each spectrum alone, with its
  standard error.

**The truth and the calibration.** Every method counts something
different (one line, a family at its own tabulated ratios, with or without
tails), so each is calibrated once per condition on its **clean twin**:
the same element, detector and beam, no scatter, no other element, a flat
1 count per channel, 1e5 photons, noise-free. k = estimate / photons
there; a method's calibrated estimate is estimate / k, and its truth is
the family's photons. This is how intensities are calibrated in practice
(on a standard); what remains is what the scatter, the neighbours, the
counts and the calibration errors do. Uncalibrated numbers are kept as
``raw_bias``.

Outputs (all synthetic, so public): ``conditions.csv``, ``estimates.csv``
(every estimate), ``scores.csv`` (condition × method), ``series.csv``
(XFNTR curves), ``timing.csv``, ``log.txt``.
"""
import os

for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):    # one BLAS thread per worker: 30
    os.environ.setdefault(_v, '1')     # workers × 32 OpenBLAS threads exhaust Windows' commit limit (measured)

import argparse
import copy
import csv
import logging
import math
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))

from lss_core import fluorescence as fluo, peaks           # noqa: E402
from synthetic import mca, mca_more as mm, xfntr            # noqa: E402

READER = ('window', 'fit_data', 'p1', 'p1p2p3')
OTHERS = ('xeray', 'pymca', 'pymca_tails', 'pyxrf', 'larch', 'larch_each', 'pymca_snip60', 'pymca_snip100', 'pymca_poly')
# PyMca's background settings: (strip with SNIP, SNIP width in channels, continuum). 'pymca' is SNIP 30 (2 FWHM),
# the variants a wider SNIP and no strip with PyMca's linear polynomial continuum (order 5) instead
PYMCA_BACKGROUND = {'pymca': (1, 30, 0), 'pymca_tails': (1, 30, 0), 'pymca_snip60': (1, 60, 0),
                    'pymca_snip100': (1, 100, 0), 'pymca_poly': (0, 30, 4)}
METHODS = READER + OTHERS
MONITOR = 1e7
TIME = (10.0, 10.0)
TWIN_PHOTONS = 1e5

SMOOTH_BEAM = mca.Beam(energy=10.0, angle=90.0, compton_ratio=1.0, core_scale=0.0)
HARD_BEAM = mca.Beam(energy=10.0, angle=90.0, compton_ratio=1.0, core_scale=1.0)
SMOOTH_DET = mca.Detector(tail=0.0, shelf=0.0, escape=0.0)
HARD_DET = mca.Detector(tail=0.01, tail_slope=0.15, shelf=2e-3, escape=1.0)
# Readout A at 10 keV, measured on real scatter-only blanks (docs/studies/mca_scatter/summary.md, medians):
# Fano 0.137 and noise 0.065 keV from the Ar Kα and elastic widths, tail 0.020 decaying over 0.64 keV,
# shelf 0, escape 0.82-1.02 x Reed (1 used), Compton/Rayleigh 2.0, O 1s wing 0.84 x water's.
MEASURED_DET = mca.Detector(noise=0.065, fano=0.137, tail=0.02, tail_slope=0.64, shelf=0.0, escape=1.0)
MEASURED_BEAM = mca.Beam(energy=10.0, angle=91.2, compton_ratio=2.0, core_scale=0.84)


@dataclass
class XCond:
    """One condition. ``target``: the family measured ('Zn K'); ``lines``:
    {family: photons} of everything present (the target included)."""
    describe: str
    factor: str
    target: str = 'Zn K'
    lines: dict = field(default_factory=lambda: {'Zn K': 1e3})
    elastic: float = 1e6
    beam: mca.Beam = SMOOTH_BEAM
    detector: mca.Detector = SMOOTH_DET
    background: float = 1.0
    slope: float = 0.0
    offset: float = 0.0
    gain: float = 0.0
    compton: str = 'biggs'
    box: float = 2.0
    series: int = 10

    def spectrum(self, scale_line=1.0, elastic=None):
        ls = {k: v * (scale_line if k == self.target else 1.0) for k, v in self.lines.items()}
        return mm.spectrum(ls, self.elastic if elastic is None else elastic, self.beam, self.detector,
                           self.background, self.slope, offset=self.offset, gain=self.gain, compton=self.compton)

    def twin(self):
        return replace(self, lines={self.target: TWIN_PHOTONS}, elastic=0.0, background=1.0, slope=0.0,
                       offset=0.0, gain=0.0)

    @property
    def line(self):
        return mm.main_line(self.target, self.beam.energy)[0]

    @property
    def fwhm(self):
        return self.detector.fwhm(self.line)

    def box_range(self):
        return self.line - self.box * self.fwhm, self.line + self.box * self.fwhm

    def fit_range(self):
        """The full-spectrum fitters' range: 1.5 keV below the lowest main
        line present to 0.6 keV above the beam."""
        lows = [mm.main_line(k, self.beam.energy)[0] for k in self.lines if mm.family_lines(k, self.beam.energy)]
        return max(1.0, min(lows) - 1.5), self.beam.energy + 0.6

    @property
    def elements(self):
        return [k for k in self.lines if mm.family_lines(k, self.beam.energy)]


def _c(describe, factor, **kw):
    return XCond(describe, factor, **kw)


def conditions():
    """Every condition, by design."""
    hard = dict(beam=HARD_BEAM, detector=HARD_DET)
    d = {}
    # core: study B's cases, with the tabulated lines and Compton profiles
    d['clean'] = _c('Zn 1e4 photons, no scatter: the sanity check', 'core', lines={'Zn K': 1e4}, elastic=0.0)
    d['smooth'] = _c('Zn 1e3 on 1e6 elastic, valence Compton only, ideal detector', 'core')
    d['hard'] = _c('the hard case: Zn 1e3 on 1e6 elastic, water\'s Compton with its O 1s wing, '
                   'Si escapes, tail 1 %, shelf 0.2 %', 'core', **hard)
    d['hard_strong'] = _c('the hard case, Zn 1e4 (1e-2 of the elastic)', 'core', lines={'Zn K': 1e4}, **hard)
    d['hard_low'] = _c('the hard case, Zn 300 on 3e5 elastic', 'core', lines={'Zn K': 300}, elastic=3e5, **hard)
    d['hard_11keV'] = _c('the hard case at an 11 keV beam', 'beam energy', beam=replace(HARD_BEAM, energy=11.0),
                         detector=HARD_DET)
    d['hard_12keV'] = _c('the hard case at a 12 keV beam', 'beam energy', beam=replace(HARD_BEAM, energy=12.0),
                         detector=HARD_DET)
    d['hard_14keV'] = _c('the hard case at a 14 keV beam', 'beam energy', beam=replace(HARD_BEAM, energy=14.0),
                         detector=HARD_DET)
    d['fe_easy'] = _c('Fe 1e3 on 1e6 elastic: far from the scatter', 'core', target='Fe K', lines={'Fe K': 1e3}, **hard)
    # counts: a clean line, for the weighting
    for n in (30, 60, 100, 200, 400, 1000, 3000, 10000):
        d['counts_%g' % n] = _c('clean Zn line, %g photons' % n, 'counts', lines={'Zn K': float(n)}, elastic=0.0)
    # neighbours and overlaps
    for f in (0.3, 1.0, 3.0):
        d['zn_cu_%g' % f] = _c('Zn under the hard scatter with Cu at %g x Zn (Cu Kb 8.905 keV)' % f, 'overlap',
                               lines={'Zn K': 1e3, 'Cu K': 1e3 * f}, **hard)
    d['ga_by_zn'] = _c('Ga 1e2 beside Zn 1e3 at 12 keV (Zn Kb 9.57 keV, Ga Ka 9.25 keV)', 'overlap',
                       target='Ga K', lines={'Ga K': 1e2, 'Zn K': 1e3}, beam=replace(HARD_BEAM, energy=12.0),
                       detector=HARD_DET)
    d['co_by_fe'] = _c('Co 1e2 beside Fe 1e3 (Fe Kb 7.06 keV, Co Ka 6.93 keV)', 'overlap', target='Co K',
                       lines={'Co K': 1e2, 'Fe K': 1e3}, **hard)
    d['fe_by_mn'] = _c('Fe 1e3 with Mn 1e3 (Mn Kb 6.49 keV under Fe Ka 6.40 keV)', 'overlap', target='Fe K',
                       lines={'Fe K': 1e3, 'Mn K': 1e3}, **hard)
    d['as_by_pb'] = _c('As 1e3 with Pb 1e3 at 14 keV (Pb La 10.55 keV on As Ka 10.54 keV)', 'overlap',
                       target='As K', lines={'As K': 1e3, 'Pb L': 1e3}, beam=replace(HARD_BEAM, energy=14.0),
                       detector=HARD_DET)
    # other elements and families
    d['br_13.6keV'] = _c('Br 1e3 on 1e6 elastic at 13.6 keV, just above its K edge (13.47)', 'element',
                         target='Br K', lines={'Br K': 1e3}, beam=replace(HARD_BEAM, energy=13.6), detector=HARD_DET)
    d['br_14keV'] = _c('Br 1e3 on 1e6 elastic at 14 keV', 'element', target='Br K', lines={'Br K': 1e3},
                       beam=replace(HARD_BEAM, energy=14.0), detector=HARD_DET)
    d['sr_16.2keV'] = _c('Sr 1e3 on 1e6 elastic at 16.2 keV (K edge 16.1)', 'element', target='Sr K',
                         lines={'Sr K': 1e3}, beam=replace(HARD_BEAM, energy=16.2), detector=HARD_DET)
    d['er_L_10keV'] = _c('Er L lines (La 6.95 keV and a dozen more) 1e3 on 1e6 elastic at 10 keV', 'element',
                         target='Er L', lines={'Er L': 1e3}, **hard)
    d['lu_L_10keV'] = _c('Lu L lines (La 7.66 keV) 1e3 on 1e6 elastic at 10 keV', 'element', target='Lu L',
                         lines={'Lu L': 1e3}, **hard)
    # detector and calibration
    for o in (-0.02, 0.02):
        d['offset_%+g' % o] = _c('the hard case, calibration offset %+g keV' % o, 'calibration', offset=o, **hard)
    for g in (-0.003, 0.003):
        d['gain_%+g' % g] = _c('the hard case, calibration gain %+g' % g, 'calibration', gain=g, **hard)
    d['tail_3pc'] = _c('the hard case, tail 3 %', 'detector', beam=HARD_BEAM, detector=replace(HARD_DET, tail=0.03))
    d['shelf_0.5pc'] = _c('the hard case, shelf 0.5 %', 'detector', beam=HARD_BEAM, detector=replace(HARD_DET, shelf=5e-3))
    d['escape_x3'] = _c('the hard case, Si escape 3 x Reed', 'detector', beam=HARD_BEAM,
                        detector=replace(HARD_DET, escape=3.0))
    d['fwhm_250'] = _c('the hard case at 250 eV FWHM', 'detector', beam=HARD_BEAM,
                       detector=replace(HARD_DET, noise=math.sqrt(0.25 ** 2 - 8 * math.log(2) * HARD_DET.eps
                                                                  * HARD_DET.fano * 8.63)))
    # the Compton model
    d['hard_shells'] = _c('the hard case with the shell-model Compton (study B)', 'Compton model', compton='shells', **hard)
    d['hard_wing0.5'] = _c('the hard case with half the O 1s wing', 'Compton model',
                           beam=replace(HARD_BEAM, core_scale=0.5), detector=HARD_DET)
    d['single'] = _c('the hard case, one spectrum alone', 'series length', series=1, **hard)
    # the detector and scatter measured on real blanks (docs/studies/mca_scatter, readout A at 10 keV)
    for name, kw in (('measured', {}), ('measured_strong', dict(lines={'Zn K': 1e4})),
                     ('measured_12keV', dict(beam=replace(MEASURED_BEAM, energy=12.0)))):
        args = dict(beam=MEASURED_BEAM, detector=MEASURED_DET)
        args.update(kw)
        d[name] = _c('Zn %g on 1e6 elastic at %g keV, with readout A\'s measured detector and scatter (tail 2 %% over '
                     '0.64 keV, no shelf, Fano 0.137, noise 0.065 keV, Compton/Rayleigh 2.0, O 1s wing 0.84 x water\'s)'
                     % (args.get('lines', {'Zn K': 1e3})['Zn K'], args['beam'].energy), 'measured', **args)
    return d


@dataclass
class SeriesCond:
    describe: str
    cond: XCond
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
        c = self.cond
        out = []
        for a, b in zip(n_line, n_el):
            ls = {k: (a if k == c.target else v * a / self.photons) for k, v in c.lines.items()}
            out.append(mm.spectrum(ls, b, c.beam, c.detector, c.background, c.slope, offset=c.offset, gain=c.gain,
                                   compton=c.compton))
        return out, n_line


def series_conditions():
    base = dict(factor='series', series=1)
    s = XCond('smooth', **base)
    h = XCond('hard', beam=HARD_BEAM, detector=HARD_DET, **base)
    return {
        'xfntr_smooth': SeriesCond('Zn at the surface, smooth scatter, 2e4 at Qc', s),
        'xfntr_smooth_weak': SeriesCond('the same, 2e3 at Qc', s, photons=2e3),
        'xfntr_hard': SeriesCond('Zn at the surface, the hard scatter', h),
        'xfntr_hard_12keV': SeriesCond('the hard series at a 12 keV beam', replace(h, beam=replace(HARD_BEAM, energy=12.0))),
        'xfntr_hard_cu': SeriesCond('the hard series with Cu at 30 % of Zn', replace(h, lines={'Zn K': 1e3, 'Cu K': 300})),
        'xfntr_br_14keV': SeriesCond('Br at the surface at 14 keV, the hard scatter', replace(
            h, target='Br K', lines={'Br K': 1e3}, beam=replace(HARD_BEAM, energy=14.0))),
        'xfntr_er_L': SeriesCond('Er L at the surface, 10 keV, the hard scatter', replace(h, target='Er L', lines={'Er L': 1e3})),
        'xfntr_measured': SeriesCond('Zn at the surface, 10 keV, readout A\'s measured detector and scatter',
                                     replace(h, beam=MEASURED_BEAM, detector=MEASURED_DET)),
    }


# ---- the reader's methods ------------------------------------------------------------

def _normalise(counts, cal):
    return fluo.normalise_spectrum(counts, {'Time': [0.0, TIME[0], TIME[1]]}, MONITOR, cal)


SCALE = MONITOR / (TIME[0] / TIME[1])


def reader(method, cond, spectra, counts):
    cal = spectra[0].calib
    data = [_normalise(c, cal) for c in counts]
    x = data[0][:, 0]
    step = float(np.median(np.abs(np.diff(x))))
    lo, hi = cond.box_range()
    if method == 'window':
        return [(v * SCALE, e * SCALE) for v, e, _, _ in (fluo.window_sum(d, lo, hi) for d in data)]
    kw = {}
    if method == 'p1p2p3':
        data = [fluo.strip_escape(d, cond.detector.escape) for d in data]
        kw['fwhm'] = fluo.detector_fwhm(cond.line, cond.detector.noise)
    o = peaks.FitOptions(shape='gaussian', background='quadratic', n_peaks=1, centres=(cond.line,),
                         x_range=(lo, hi), window=50.0, **kw)
    Y = [d[:, 1] for d in data]
    S = [d[:, 2] for d in data]
    ref, each = peaks.fit_series(x, Y, S, o, weights='data' if method == 'fit_data' else 'poisson')
    if not each:
        return [None] * len(counts)
    j = int(np.argmin([abs(p.centre - cond.line) for p in ref.peaks]))
    return [(r.peaks[j].area / step * SCALE, r.peaks[j].area_err / step * SCALE) for r in each]


# ---- XeRay (port) --------------------------------------------------------------------

def xeray(cond, spectra, counts):
    from scipy.optimize import least_squares
    e = spectra[0].energy
    lo, hi = cond.box_range()
    box = (e >= lo) & (e <= hi)
    x = e[box]
    step = float(np.median(np.diff(e)))
    out = []
    for c in counts:
        y = c[box]
        peak = cond.line
        base = np.mean([np.mean(y[:5]), np.mean(y[-5:])])
        rng = float(np.ptp(y))
        lb = np.array([0.0, peak - 0.2, 0.0, -np.inf, float(np.min(y))])
        ub = np.array([max(rng * 3, 1e-9), peak + 0.2, float(np.ptp(x)) / 2, np.inf, max(float(np.mean(y)), float(np.min(y)) + 1e-9)])
        a0 = np.array([rng, peak, float(np.ptp(x)) / 6, 0.0, base])
        span = np.where(np.isfinite(ub - lb), ub - lb, 1.0)
        a0 = np.clip(a0, lb + 1e-9 * span, ub - 1e-9 * span)      # lsqnonlin projects a start onto the bounds

        def f(a):
            return a[0] * np.exp(-((x - a[1]) / a[2]) ** 2 / 2) + a[3] * x + a[4] - y
        try:
            r = least_squares(f, a0, bounds=(lb, ub), method='trf')
            a = r.x
            area = a[0] * a[2] * math.sqrt(2 * math.pi) / step
            out.append((float(area), float(math.sqrt(max(np.sum(y), 1.0)))))
        except Exception:
            out.append(None)
    return out


# ---- PyMca ---------------------------------------------------------------------------

_PYMCA = {}


def _pymca_theory(cond, tails, background=(1, 30, 0)):
    from PyMca5.PyMcaPhysics.xrf import ClassMcaTheory
    key = (tuple(sorted(cond.elements)), cond.beam.energy, cond.detector.noise, cond.detector.fano, tails,
           cond.fit_range(), background)
    if key in _PYMCA:
        return _PYMCA[key]
    m = ClassMcaTheory.McaTheory()
    c = m.configure()
    c['peaks'] = {k.split()[0]: k.split()[1] for k in cond.elements}
    lo, hi = cond.fit_range()
    a, b, _ = mca.CALIB
    xmin, xmax = int(round((lo - a) / b)), int(round((hi - a) / b))
    c['fit'].update(energy=[cond.beam.energy], energyweight=[1.0], energyflag=[1], energyscatter=[1], scatterflag=1,
                    escapeflag=1, sumflag=0, stripflag=background[0], stripalgorithm=1, snipwidth=background[1],
                    continuum=background[2], linpolorder=5,
                    hypermetflag=15 if tails else 1, fitweight=1, xmin=xmin, xmax=xmax)
    for k in c['attenuators']:
        c['attenuators'][k][0] = 0
    c['detector'].update(zero=a, gain=b, noise=cond.detector.noise, fano=cond.detector.fano, fixednoise=1, fixedfano=1,
                         fixedzero=0, fixedgain=0)
    m.configure(c)
    _PYMCA[key] = (m, xmin, xmax)
    return _PYMCA[key]


def pymca(cond, spectra, counts, tails=False, background=(1, 30, 0)):
    m, xmin, xmax = _pymca_theory(cond, tails, background)
    group = '%s %s' % tuple(cond.target.split())
    a, b, _ = mca.CALIB
    x = np.arange(1, len(counts[0]) + 1, dtype=float)
    out = []
    for y in counts:
        try:
            m.setData(x, y, xmin=xmin, xmax=xmax, calibration=[a, b, 0.0])
            m.estimate()
            m.startfit(digest=0)
            r = m.digestresult()
            out.append((float(r[group]['fitarea']), float(r[group]['sigmaarea'])))
        except Exception:
            out.append(None)
    return out


# ---- PyXRF (scikit-beam) ---------------------------------------------------------------

def _sk_params(cond):
    from skbeam.core.fitting.base.parameter_data import get_para
    p = copy.deepcopy(get_para())
    a, b, _ = mca.CALIB
    p['e_offset']['value'], p['e_linear']['value'], p['e_quadratic']['value'] = a, b, 0.0
    p['fwhm_offset']['value'] = cond.detector.noise
    p['fwhm_fanoprime']['value'] = cond.detector.eps * cond.detector.fano / p['non_fitting_values']['epsilon']
    p['coherent_sct_energy']['value'] = cond.beam.energy
    p['coherent_sct_energy']['min'] = cond.beam.energy - 1
    p['coherent_sct_energy']['max'] = cond.beam.energy + 1
    p['compton_angle']['value'] = cond.beam.angle
    lo, hi = cond.fit_range()
    p['non_fitting_values']['energy_bound_low']['value'] = lo
    p['non_fitting_values']['energy_bound_high']['value'] = hi
    return p


def pyxrf(cond, spectra, counts):
    from skbeam.core.fitting import xrf_model as xm
    from skbeam.core.fitting.background import snip_method
    e = spectra[0].energy
    lo, hi = cond.fit_range()
    sel = (e >= lo) & (e <= hi)
    ch = np.arange(1, len(e) + 1, dtype=float)[sel]
    names = [k.replace(' ', '_') for k in cond.elements]
    target = cond.target.replace(' ', '_')
    p = _sk_params(cond)
    xm.set_parameter_bound(p, 'fit_with_tail')
    for k in ('e_offset', 'e_linear', 'e_quadratic', 'fwhm_offset', 'fwhm_fanoprime', 'coherent_sct_energy'):
        p[k]['bound_type'] = 'fixed'
    tot = np.sum(counts, axis=0)[sel]
    try:
        ms = xm.ModelSpectrum(p, names)
        ms.assemble_models()
        bg = snip_method(tot, p['e_offset']['value'], p['e_linear']['value'], 0.0,
                         width=p['non_fitting_values']['background_width'])
        r = ms.model_fit(ch, tot - bg, weights=1 / np.sqrt(np.maximum(tot, 1)))
        xm.update_parameter_dict(p, r)
    except Exception:
        return [None] * len(counts)
    out = []
    for y in counts:
        try:
            _, _, area = xm.linear_spectrum_fitting(ch, y[sel], p, elemental_lines=names, weights=1 / np.maximum(y[sel], 1))
            out.append((float(area.get(target, 0.0)), math.nan))
        except Exception:
            out.append(None)
    return out


# ---- Larch ---------------------------------------------------------------------------

def _larch_model(cond):
    from larch.xrf.xrf_model import xrf_model
    lo, hi = cond.fit_range()
    a, b, _ = mca.CALIB
    m = xrf_model(xray_energy=1000.0 * cond.beam.energy, count_time=1.0, energy_min=lo, energy_max=hi)
    m.set_detector(thickness=0.45, material='Si', cal_offset=a + b, cal_slope=b, vary_cal_offset=False,
                   vary_cal_slope=False, peak_step=1e-3, vary_peak_step=True, peak_tail=0.01, vary_peak_tail=True,
                   noise=cond.detector.noise / (2 * math.sqrt(2 * math.log(2))), vary_noise=False)
    m.add_scatter_peak(name='elastic', center=cond.beam.energy, amplitude=1e5, step=0.01, tail=0.5, sigmax=1.0,
                       vary_center=False)
    m.add_scatter_peak(name='compton1', center=cond.beam.compton, amplitude=1e5, step=0.01, tail=0.5, sigmax=1.5)
    for k in cond.elements:
        m.add_element(k.split()[0])
    m.add_escape(scale=1.0, vary=True)
    return m


def _larch_fit(cond, energy, y):
    m = _larch_model(cond)
    lo, hi = cond.fit_range()
    res = m.fit_spectrum(SimpleNamespace(energy=energy, counts=np.asarray(y, float)), energy_min=lo, energy_max=hi,
                         max_nfev=3000)
    return m, res


def larch(cond, spectra, counts, each=False):
    e = spectra[0].energy
    sym = 'amp_' + cond.target.split()[0].lower()
    if each:
        out = []
        for y in counts:
            try:
                m, _ = _larch_fit(cond, e, y)
                p = m.result.params[sym]
                out.append((float(p.value), float(p.stderr) if p.stderr else math.nan))
            except Exception:
                out.append(None)
        return out
    try:
        m, res = _larch_fit(cond, e, np.sum(counts, axis=0))
    except Exception:
        return [None] * len(counts)
    key = cond.target.split()[0]
    names = list(m.eigenvalues.keys())
    j = names.index(key)
    lo, hi = cond.fit_range()
    sel = (e >= lo) & (e <= hi)
    T = np.asarray(m.transfer_matrix, float)[sel]
    out = []
    for y in counts:
        # Larch's own decompose_spectrum multiplies the counts, not the components, by its Hanning fit
        # window; this is the same least-squares step on the fit range alone, weighted by the counts
        try:
            yy = np.asarray(y, float)[sel]
            w = 1.0 / np.sqrt(np.maximum(yy, 1.0))
            coef = np.linalg.lstsq(T * w[:, None], yy * w, rcond=None)[0]
            out.append((float(coef[j]), math.nan))          # columns are component / amplitude
        except Exception:
            out.append(None)
    return out


def run_method(method, cond, spectra, counts):
    if method in READER:
        return reader(method, cond, spectra, counts)
    if method == 'xeray':
        return xeray(cond, spectra, counts)
    if method == 'pymca':
        return pymca(cond, spectra, counts)
    if method == 'pymca_tails':
        return pymca(cond, spectra, counts, tails=True)
    if method in PYMCA_BACKGROUND:
        return pymca(cond, spectra, counts, background=PYMCA_BACKGROUND[method])
    if method == 'pyxrf':
        return pyxrf(cond, spectra, counts)
    if method == 'larch':
        return larch(cond, spectra, counts)
    if method == 'larch_each':
        return larch(cond, spectra, counts, each=True)
    raise ValueError(method)


def available(methods):
    """The methods whose packages import, and a note for each missing one."""
    need = {'pymca': 'PyMca5', 'pymca_tails': 'PyMca5', 'pymca_snip60': 'PyMca5', 'pymca_snip100': 'PyMca5',
            'pymca_poly': 'PyMca5', 'pyxrf': 'skbeam', 'larch': 'larch', 'larch_each': 'larch'}
    ok, notes = [], []
    for m in methods:
        mod = need.get(m)
        if mod:
            try:
                __import__(mod)
            except Exception as exc:          # pragma: no cover - depends on the environment
                notes.append('%s skipped: %s does not import (%s)' % (m, mod, exc))
                continue
        ok.append(m)
    return ok, notes


def _quiet():
    logging.disable(logging.WARNING)
    warnings.filterwarnings('ignore')


# ---- running -------------------------------------------------------------------------

def calibrate(name, cond, methods):
    """k per method from the clean twin (noise-free; a series of 3 for the
    series methods). Returns {method: (k, seconds)}."""
    _quiet()
    t = cond.twin()
    s = t.spectrum()
    n = max(3, 1)
    counts = [s.expected.copy() for _ in range(n)]
    out = {}
    for m in methods:
        t0 = time.time()
        try:
            r = run_method(m, t, [s] * n, counts)
            v = [x[0] for x in r if x is not None]
            k = float(np.mean(v)) / TWIN_PHOTONS if v else math.nan
        except Exception:
            k = math.nan
        out[m] = (k, time.time() - t0)
    return name, out


def run_block(args):
    """``reps`` replicates of one condition. Returns rows (name, rep, k_spec,
    method, estimate, error, truth, seconds per spectrum)."""
    _quiet()
    name, cond, methods, reps, ci = args
    spec = cond.spectrum()
    truth = mm.family_photons(spec, cond.target)
    rows = []
    for rep in reps:
        rng = np.random.default_rng([20261125, ci, rep])
        counts = [spec.draw(rng) for _ in range(cond.series)]
        for m in methods:
            t0 = time.time()
            try:
                r = run_method(m, cond, [spec] * cond.series, counts)
            except Exception:
                r = [None] * cond.series
            dt = (time.time() - t0) / cond.series
            for k, v in enumerate(r):
                rows.append((name, rep, k, m, None if v is None else v[0], None if v is None else v[1], truth, dt))
    return rows


def run_series(args):
    _quiet()
    name, sc, methods, reps, ci = args
    spectra, n_line = sc.spectra()
    truth = [mm.family_photons(s, sc.cond.target) for s in spectra]
    rows = []
    for rep in reps:
        rng = np.random.default_rng([20261126, ci, rep])
        counts = [s.draw(rng) for s in spectra]
        for m in methods:
            try:
                r = run_method(m, sc.cond, spectra, counts)
            except Exception:
                r = [None] * len(spectra)
            for k, v in enumerate(r):
                rows.append((name, rep, k, m, None if v is None else v[0], None if v is None else v[1], truth[k], sc.qz[k]))
    return rows


def score(est_rows, ks, conds, methods):
    """scores per condition × method."""
    by = {}
    for name, rep, k, m, est, err, truth, dt in est_rows:
        by.setdefault((name, m), []).append((est, err, truth, dt))
    out = []
    for name, c in conds.items():
        for m in methods:
            rows = by.get((name, m), [])
            if not rows:
                continue
            kk = ks[name][m][0]
            good = [(e, s, t) for e, s, t, _ in rows if e is not None and np.isfinite(e)]
            n, nf = len(rows), len(rows) - len(good)
            r = dict(condition=name, factor=c.factor, method=m, n=n, failed=nf, k=kk,
                     sec_per_spectrum=float(np.mean([d for *_, d in rows])))
            if len(good) >= 3 and np.isfinite(kk) and kk > 0:
                est = np.array([g[0] for g in good]) / kk
                err = np.array([g[1] for g in good], float) / kk
                tru = np.array([g[2] for g in good])
                rel = est / tru - 1
                raw = np.array([g[0] for g in good]) / tru
                r.update(bias=float(rel.mean()), bias_se=float(rel.std(ddof=1) / math.sqrt(len(rel))),
                         rmse=float(math.sqrt(np.mean(rel ** 2))), sd=float(rel.std(ddof=1)), raw_ratio=float(raw.mean()))
                if np.all(np.isfinite(err)) and np.all(err > 0):
                    pull = (est - tru) / err
                    r.update(pull_mean=float(pull.mean()), pull_sd=float(pull.std(ddof=1)),
                             err_ratio=float(np.median(err / tru) / rel.std(ddof=1)) if rel.std(ddof=1) > 0 else math.nan)
            out.append(r)
    return out


def series_score(rows, ks, sconds, methods):
    """Per series × method: the mean curve over replicates divided by the
    truth, normalised by one free scale (weighted to the strong points);
    the worst point and χ²/dof of the per-replicate ratios."""
    out, curves = [], []
    for name, sc in sconds.items():
        for m in methods:
            r = [x for x in rows if x[0] == name and x[3] == m]
            if not r:
                continue
            npts = len(sc.qz)
            reps = sorted(set(x[1] for x in r))
            R = np.full((len(reps), npts), np.nan)
            E = np.full((len(reps), npts), np.nan)
            T = np.zeros(npts)
            for rep, k, est, err, tru in ((x[1], x[2], x[4], x[5], x[6]) for x in r):
                T[k] = tru
                if est is not None and np.isfinite(est):
                    R[reps.index(rep), k] = est / tru
                    E[reps.index(rep), k] = (err / tru) if err is not None and np.isfinite(err) else np.nan
            fails = int(np.isnan(R).sum())
            mean = np.nanmean(R, axis=0)
            se = np.nanstd(R, axis=0, ddof=1) / np.sqrt(np.sum(np.isfinite(R), axis=0))
            strong = T >= 100
            w = np.where(strong & np.isfinite(mean) & (se > 0), 1 / np.maximum(se, 1e-12) ** 2, 0)
            scale = float(np.sum(w * mean) / np.sum(w)) if np.sum(w) > 0 else math.nan
            ratio = mean / scale
            worst = float(np.nanmax(np.abs(ratio[strong] - 1))) if strong.any() else math.nan
            chi = (ratio - 1) / (se / scale)
            chi2 = float(np.nansum(chi[strong] ** 2) / max(np.sum(strong) - 1, 1))
            out.append(dict(series=name, method=m, failed=fails, scale=scale, worst=worst, chi2_dof=chi2,
                            reps=len(reps)))
            for k in range(npts):
                curves.append(dict(series=name, method=m, qz=sc.qz[k], truth=T[k], ratio=ratio[k], se=se[k] / scale))
    return out, curves


def write_csv(path, rows):
    if not rows:
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ('%.6g' % v if isinstance(v, float) else v) for k, v in r.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--design', default='all', help='all, conditions or series')
    ap.add_argument('--replicates', type=int, default=100)
    ap.add_argument('--series-replicates', type=int, default=40)
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument('--methods', default='all')
    ap.add_argument('--conditions', default=None, help='comma-separated names (default: all)')
    ap.add_argument('--chunk', type=int, default=10, help='replicates per task')
    ap.add_argument('--rows', action='store_true', help='also write estimates.csv: every estimate (tens of MB)')
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    methods = list(METHODS) if a.methods == 'all' else a.methods.split(',')
    methods, notes = available(methods)
    conds = conditions()
    sconds = series_conditions()
    if a.conditions:
        want = set(a.conditions.split(','))
        conds = {k: v for k, v in conds.items() if k in want}
        sconds = {k: v for k, v in sconds.items() if k in want}
    if a.design == 'series':
        conds = {}
    if a.design == 'conditions':
        sconds = {}
    log = open(os.path.join(a.out, 'log.txt'), 'w', encoding='utf-8', newline='\n')

    def say(s):
        print(s, flush=True)
        log.write(s + '\n')
        log.flush()
    say('xrf_shootout %s: %d conditions, %d series, methods %s, %d replicates (%d for series), %d jobs'
        % (time.strftime('%Y-%m-%d %H:%M:%S'), len(conds), len(sconds), ','.join(methods), a.replicates,
           a.series_replicates, a.jobs))
    for n in notes:
        say(n)
    t0 = time.time()
    allc = dict(conds)
    allc.update({k: v.cond for k, v in sconds.items()})
    ks = {}
    with ProcessPoolExecutor(a.jobs) as ex:
        for name, k in ex.map(calibrate, allc.keys(), allc.values(), [methods] * len(allc)):
            ks[name] = k
        say('calibrated %d conditions in %.0f s' % (len(ks), time.time() - t0))
        futs = []
        for ci, (name, c) in enumerate(conds.items()):
            for start in range(0, a.replicates, a.chunk):
                futs.append(ex.submit(run_block, (name, c, methods, range(start, min(start + a.chunk, a.replicates)), ci)))
        for ci, (name, sc) in enumerate(sconds.items()):
            for start in range(0, a.series_replicates, max(1, a.chunk // 2)):
                futs.append(ex.submit(run_series, (name, sc, methods,
                                                   range(start, min(start + max(1, a.chunk // 2), a.series_replicates)), ci)))
        est, ser = [], []
        done = 0
        for f in as_completed(futs):
            rows = f.result()
            if rows and len(rows[0]) == 8 and rows[0][0] in sconds:
                ser += rows
            else:
                est += rows
            done += 1
            if done % max(1, len(futs) // 20) == 0:
                say('%d/%d tasks, %.0f s' % (done, len(futs), time.time() - t0))
    crow = [dict(condition=n, factor=c.factor, target=c.target, describe=c.describe, line_kev=c.line,
                 fwhm_kev=c.fwhm, box=c.box, series=c.series, beam_kev=c.beam.energy, compton=c.compton,
                 fit_range='%.2f-%.2f' % c.fit_range()) for n, c in conds.items()]
    write_csv(os.path.join(a.out, 'conditions.csv'), crow)
    write_csv(os.path.join(a.out, 'calibration.csv'),
              [dict(condition=n, method=m, k=v[0], seconds=v[1]) for n, d in ks.items() for m, v in d.items()])
    if a.rows:
        write_csv(os.path.join(a.out, 'estimates.csv'),
                  [dict(condition=r[0], rep=r[1], spectrum=r[2], method=r[3], estimate=r[4], error=r[5], truth=r[6],
                        sec=r[7]) for r in est])
    sc = score(est, ks, conds, methods)
    write_csv(os.path.join(a.out, 'scores.csv'), sc)
    if sconds:
        sv, curves = series_score(ser, ks, sconds, methods)
        write_csv(os.path.join(a.out, 'series_scores.csv'), sv)
        write_csv(os.path.join(a.out, 'series.csv'), curves)
    say('done in %.0f s' % (time.time() - t0))
    log.close()


if __name__ == '__main__':
    main()
