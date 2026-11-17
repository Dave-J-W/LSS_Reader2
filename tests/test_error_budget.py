"""The budget error model (lss_core.errors; owner, 2026-11-17).

The monitor's uncertainty is applied to each whole sum of a frame (box,
line, energy window, background-subtracted net signal), not pixel by
pixel; frames' monitor errors are independent. Formulas:
docs/reports/error_propagation.md. The legacy model must give the old
numbers exactly (test_api, test_ref_export_golden and the tests below).
"""
import os

import numpy as np
import pytest

from lss_core import fluorescence, normalise
from lss_core.errors import ErrorModel, MonitorModel, MonitorTerms, as_model, script_kw
from TwoDDetector import TwoDDetector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')

BUDGET = ErrorModel('budget')                 # default monitor model: Gaussian, 0.04 %
POISSON = ErrorModel('budget', MonitorModel('counting'))
U0 = 4e-4


def _frame(seed=1, peak=5e4, bg=20.0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:195, 0:487]
    lam = bg + peak * np.exp(-((xx - 240) ** 2 + (yy - 100) ** 2) / 2 / 3.0 ** 2)
    img = rng.poisson(lam).astype(float)
    return img, np.sqrt(img)


def _det(model):
    d = TwoDDetector('Pilatus')
    d.NROWS, d.NCOLS = 195, 487
    d.errors = as_model(model)
    return d


def _box(cx, cy, slit):
    sx, sy = slit[0] - 2, slit[1] - 2
    return np.s_[cy - (sy + 1) // 2:cy + (sy + 1) // 2 + 1, cx - (sx + 1) // 2:cx + (sx + 1) // 2 + 1]


# --- the monitor model -------------------------------------------------------

def test_default_monitor_model_is_gaussian_0p04_percent_at_every_count():
    # owner, 2026-11-17: sigma 0.04 %, constant across counting level
    m = MonitorModel()
    assert m.kind == 'gaussian'
    assert m.relative([1e2, 1e4, 1e7]) == pytest.approx([U0] * 3)
    assert 'SR570' in m.describe()


def test_student_t_propagates_its_standard_deviation():
    t = MonitorModel('student_t', sigma=U0, nu=3.6)
    assert t.relative(1e5) == pytest.approx(U0 * np.sqrt(3.6 / 1.6))
    with pytest.raises(ValueError):
        MonitorModel('student_t', nu=2.0)       # infinite variance


def test_counting_monitor_model():
    m = MonitorModel('counting')
    assert m.relative(1e4) == pytest.approx(1e-2)          # Poisson on the counts
    assert MonitorModel('counting', g=100).relative(1e4) == pytest.approx(1e-3)
    assert MonitorModel('counting', f=0.003, g=1e30).relative(1e6) == pytest.approx(0.003)
    assert MonitorModel('counting', sigma_dark=50, g=1e30).relative(1e4) == pytest.approx(5e-3)


@pytest.mark.parametrize('monitor', [MonitorModel(), MonitorModel('student_t', sigma=3e-4, nu=4.0),
                                     MonitorModel('counting', f=0.001, sigma_dark=2.0, g=10.0)])
def test_model_from_script_keyword_round_trips(monitor):
    m = ErrorModel('budget', monitor)
    kw = script_kw(m)
    assert as_model(eval(kw.split('=', 1)[1])) == m
    assert script_kw(ErrorModel('legacy')) == ''
    with pytest.raises(ValueError):
        ErrorModel('poisson')


# --- one frame: a box, and background subtraction ----------------------------

def test_box_sum_carries_monitor_term_on_the_whole_sum():
    img, err = _frame()
    M = 2e5
    d = _det(BUDGET)
    cx, cy = d.peakLocate(img, err, cen=[240, 100], mon=M)
    sig, sigerr = d.sumROI(slit=[11, 11], cen=[cx, cy])
    b = _box(cx, cy, [11, 11])
    S = img[b].sum()
    u = U0
    assert sig == pytest.approx(S / M)
    # invariant: var(S/M) = sum(sigma_i^2)/M^2 + (S/M)^2 u_M^2
    assert sigerr ** 2 == pytest.approx(S / M ** 2 + (S / M) ** 2 * u ** 2, rel=1e-12)


def test_net_signal_monitor_term_is_on_the_net_not_the_boxes():
    img, err = _frame()
    M = 2e5
    model = ErrorModel('budget', MonitorModel(sigma=0.004))
    d = _det(model)
    cx, cy = d.peakLocate(img, err, cen=[240, 100], mon=M)
    d.sumROI(slit=[11, 11], cen=[cx, cy], dir='H', bg=2.0)
    net, neterr = d.netROI()
    S, L, R = (v * M for v in d.roiParts['values'][0::2])
    cnt = (S + (L + R) / 4) / M ** 2
    assert net == pytest.approx((S - (L + R) / 2) / M)
    assert neterr ** 2 == pytest.approx(cnt + net ** 2 * 0.004 ** 2, rel=1e-10)


def test_legacy_net_is_the_old_expression():
    img, err = _frame()
    d = _det('legacy')
    cx, cy = d.peakLocate(img, err, cen=[240, 100], mon=2e5)
    sig, sigerr, lbg, lbgerr, rbg, rbgerr = d.sumROI(slit=[11, 11], cen=[cx, cy], dir='H', bg=2.0)
    net, neterr = d.netROI()
    assert net == sig - (lbg + rbg) / 2.0
    assert neterr == np.sqrt(sigerr ** 2 + (lbgerr ** 2 + rbgerr ** 2) / 4)


def test_budget_error_matches_monte_carlo_scatter_legacy_does_not():
    """Bright flat box, monitor 1 % noisy: the scatter of S/M over repeated
    frames is what the budget model predicts; the legacy model (per-pixel
    monitor term) is far too small."""
    rng = np.random.default_rng(7)
    M0, u = 1e4, 0.01
    lam = np.full((195, 487), 1e4)
    model = ErrorModel('budget', MonitorModel(sigma=u))
    values, budget_err, legacy_err = [], [], []
    for _ in range(400):
        img = rng.poisson(lam).astype(float)
        M = M0 * (1 + u * rng.standard_normal())
        for mode, out in ((model, budget_err), ('legacy', legacy_err)):
            d = _det(mode)
            d.imageData = img / M
            d.errorData = np.sqrt(img) / M if mode is model else np.sqrt(img / M ** 2 + img ** 2 / M ** 3)
            d.monitorTerms = MonitorTerms()
            if mode is model:
                d.monitorTerms.add('f', d.imageData, 1.0, u)
            v, e = d.sumROI(slit=[12, 12], cen=[240, 100])
            out.append(e)
        values.append(v)
    scatter = np.std(values, ddof=1) / np.mean(values)
    assert np.mean(budget_err) / np.mean(values) == pytest.approx(scatter, rel=0.1)
    assert np.mean(legacy_err) / np.mean(values) < scatter / 3


# --- profiles and several frames ---------------------------------------------

def test_line_profile_points_each_carry_their_monitor_term():
    img, err = _frame()
    M = 1e5
    d = _det(BUDGET)
    d.plotVint({0: img}, {0: err}, absfac=1, absnum=[0], hroi=[200, 280], vroi=[90, 110], mon=[M])
    prof = d.vintData
    u = U0
    counts = img[90:111, 200:281].sum(axis=0)
    assert prof[:, 1] == pytest.approx(counts / M)
    assert prof[:, 2] ** 2 == pytest.approx(counts / M ** 2 + (counts / M) ** 2 * u ** 2, rel=1e-10)


def test_mean_of_frames_adds_monitor_terms_in_quadrature_across_frames():
    a, ea = _frame(seed=1)
    b, eb = _frame(seed=2, peak=2e4)
    Ma, Mb = 1e5, 4e5
    absfac = 2.5
    d = _det(POISSON)
    d.sumFiles({0: a, 1: b}, {0: ea, 1: eb}, absfac=absfac, absnum=[0, 1], mon=[Ma, Mb])
    box = np.s_[95:106, 235:246]
    v = d.imageData[box].sum()
    cnt = np.sum(d.errorData[box] ** 2)
    Sa, Sb = a[box].sum(), b[box].sum()
    assert v == pytest.approx((Sa / Ma + absfac * Sb / Mb) / 2)
    assert cnt == pytest.approx((Sa / Ma ** 2 + absfac ** 2 * Sb / Mb ** 2) / 4)
    expect = (Sa / Ma / 2) ** 2 / Ma + (absfac * Sb / Mb / 2) ** 2 / Mb
    assert d.monitorTerms.variance(box) == pytest.approx(expect, rel=1e-12)


def test_background_subtraction_terms_keep_their_signs():
    """Frame minus a background from another frame: amplitudes of different
    frames add in quadrature; a frame subtracted from itself cancels."""
    x = np.ones((4, 4))
    t = MonitorTerms()
    t.add('s', x, 1.0, 0.01)
    bg = MonitorTerms()
    bg.add('b', x * 0.5, 1.0, 0.02)
    t.extend(bg, -1.0)
    assert t.variance() == pytest.approx((16 * 0.01) ** 2 + (8 * 0.02) ** 2)
    self_sub = MonitorTerms()
    self_sub.add('s', x, 1.0, 0.01)
    self_sub.add('s', x, -1.0, 0.01)
    assert self_sub.variance() == pytest.approx(0.0)


def test_normalise_frame_budget_is_counting_only():
    img, err = _frame()
    v, e = normalise.normalise_frame(img, err, 1e5, 2.0, 1, model=BUDGET)
    lv, le = normalise.normalise_frame(img, err, 1e5, 2.0, 1)
    assert np.array_equal(v, lv)
    assert e ** 2 == pytest.approx(img * 4 / 1e10)
    assert np.all(e <= le)
    t = normalise.frame_terms('k', v, 1e5, BUDGET)
    assert t.variance(np.s_[0:5, 0:5]) == pytest.approx((v[0:5, 0:5].sum()) ** 2 * U0 ** 2)


# --- fluorescence -------------------------------------------------------------

def test_window_sum_monitor_term_on_the_sum():
    rng = np.random.default_rng(3)
    counts = rng.poisson(200, 1000).astype(float)
    par = {'Time': [0, 10.0, 8.0]}
    M = 5e4
    tc = 10.0 / 8.0
    spec = fluorescence.normalise_spectrum(counts, par, M, (0.0, 0.01, 0.0), BUDGET)
    u = float(BUDGET.monitor.relative(M))
    Y, err, lo, hi = fluorescence.window_sum(spec, 2.0, 5.0, u)
    part = (spec[:, 0] >= 2.0) & (spec[:, 0] <= 5.0)
    assert Y == pytest.approx(np.sum(counts[part]) / M * tc)
    assert err ** 2 == pytest.approx(np.sum(counts[part]) * tc ** 2 / M ** 2 + Y ** 2 * u ** 2, rel=1e-9)
    legacy = fluorescence.normalise_spectrum(counts, par, M, (0.0, 0.01, 0.0))
    assert np.array_equal(legacy[:, 1], spec[:, 1])
    assert fluorescence.window_sum(legacy, 2.0, 5.0)[0] == Y


# --- real data ------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX school data not present')
def test_nx_reflectivity_budget_changes_only_errors():
    from lss_core.experiment import Experiment
    exp = Experiment(NX)
    leg = exp.reflectivity([6, 7, 8, 9])
    bud = exp.reflectivity([6, 7, 8, 9], errors='budget')
    for k in leg.per_scan:
        a, b = leg.per_scan[k], bud.per_scan[k]
        assert np.array_equal(a[:, [0, 1, 3, 5, 6]], b[:, [0, 1, 3, 5, 6]])
        monc = np.array([f.monitor for f in exp.frames([k])])
        # budget: error^2 = counting + (net u)^2 with u = 0.04 %
        cnt = b[:, 2] ** 2 - (b[:, 1] * U0) ** 2
        assert np.all(cnt > 0)
        # counting part = (S + (L+R)/4)/M^2 in counts
        S, L, R = b[:, 3] * monc, b[:, 5] * monc, b[:, 6] * monc
        assert cnt == pytest.approx((S + (L + R) / 4) / monc ** 2, rel=1e-6)
