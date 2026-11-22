"""The fit demonstrator (tests/demonstrator/, tests/tools/patch_demo.py;
report docs/reports/patch_demo.md): replicates reproducible from their
seed, every patching method near the truth at high counts, the rebuilt
fit curves equal to what the core fitted, the burn mode reading a known
shift and broadening, and the window's controls (space bar, checkboxes,
mode switch) without exceptions.

Kinds of assertion (docs/TESTING.md): invariants unless marked "as coded"
(characterisations of the methods on synthetic truth, measured
2026-11-22)."""
import os

import numpy as np
import pytest

from demonstrator import burnmode as bm
from demonstrator import refl
from lss_core import patching

FAST = refl.Config(truth='water', plan='nx')


# ---- reflectivity mode ---------------------------------------------------------------------

def test_a_replicate_is_reproducible_from_its_seed():
    a, b, c = refl.replicate(FAST, 4), refl.replicate(FAST, 4), refl.replicate(FAST, 5)
    for sa, sb in zip(a.scans, b.scans):
        assert np.array_equal(sa.y, sb.y) and np.array_equal(sa.sigma, sb.sigma)
    assert np.array_equal(a.true_steps, b.true_steps)
    assert not np.array_equal(a.scans[1].y, c.scans[1].y)
    # the foils' truth is drawn per replicate; the prior offered is the calibration, the same for all
    assert not np.array_equal(a.true_steps, c.true_steps)
    assert np.array_equal(a.prior[0], c.prior[0])


def test_the_denoised_scans_are_the_truth_on_each_scans_scale():
    rep = refl.replicate(FAST, 0)
    for m, e in enumerate(rep.expected):
        assert np.allclose(e.y * rep.scale(m), rep.truth(e.q), rtol=1e-12)


def test_without_foil_errors_the_prior_is_the_truth():
    rep = refl.replicate(refl.Config(truth='water', plan='standard', foil_error=False), 0)
    assert np.allclose(np.exp(rep.prior[0]), rep.true_steps, rtol=1e-12)


def test_every_method_is_near_the_truth_at_high_counts():
    """Water, NX-like grids, ×100 the NX counts (errors ≈ 0.05 %): every
    method within 0.15 % and 3 reported σ of the true factor of each join
    (measured: within 0.08 %, |pull| ≤ 1.6, seeds 0–2)."""
    rep = refl.replicate(refl.Config(truth='water', plan='nx', counts=100.0), 0)
    for name, r in refl.run_all(rep).items():
        assert r.ok, (name, r.error)
        dev = np.log(r.factors / rep.true_steps)
        assert np.all(np.abs(dev) < 0.0015), (name, dev)
        assert np.all(np.abs(dev / r.step_err) < 3), (name, dev / r.step_err)


def test_the_rebuilt_join_curve_is_the_joint_fit():
    """``refl._window_fit`` with δ free reproduces ``patching.joint_factor``
    (no guard) exactly, so the curve drawn at δ̂ is the fitted one."""
    rep = refl.replicate(refl.Config(truth='film', plan='nx'), 3)
    for lik in ('poisson', 'log'):
        for space in ('rrf', 'raw'):
            for m in range(1, len(rep.scans)):
                a, b = rep.scans[m - 1], rep.scans[m]
                j = patching.joint_factor(a, b, likelihood=lik, space=space, guard_p=0)
                _, d, _ = refl._window_fit(a, b, j.order, j.ia, j.ib, j.space, j.likelihood)
                assert d == pytest.approx(j.delta, abs=1e-10)
                # the curve at the window's points gives back the fit's χ²
                _, ma = refl.join_curve(a, b, j, q=a.q[j.ia])
                _, mb = refl.join_curve(a, b, j, q=b.q[j.ib])
                mu = np.concatenate([ma, mb / j.factor])
                y = np.concatenate([a.y[j.ia], b.y[j.ib]])
                s = np.concatenate([a.sigma[j.ia], b.sigma[j.ib]])
                if lik == 'poisson':
                    chi2 = np.sum((y - mu) ** 2 / (s ** 2 / np.maximum(np.abs(y), s) * mu))
                else:
                    chi2 = np.sum((y / s) ** 2 * (np.log(y) - np.log(mu)) ** 2)
                assert chi2 == pytest.approx(j.chi2, rel=1e-6)


def test_legacy_and_spline_ratio_agree_on_the_first_join():
    """The legacy chain's first factor is the spline ratio against scan 1
    (the same estimator; the weights differ slightly, the legacy patch
    interpolating scan b's errors with a cubic, interp_factor linearly)."""
    rep = refl.replicate(FAST, 2)
    leg, sp = refl.run_method(rep, 'legacy'), refl.run_method(rep, 'interp')
    assert leg.factors[0] == pytest.approx(sp.factors[0], rel=1e-4)


def test_the_p1_case_as_coded():
    """As coded (2026-11-22), noise-free water, a staggered overlap that
    straddles Qc: legacy −13.7 %, spline in ln y −1.1 %, the default joint
    fit (R/R_F; the χ² guard steps down to the overlap at order 2) +2.0 %."""
    rep = refl.denoised(refl.replicate(refl.Config(truth='water', plan='edge'), 0))
    dev = {n: refl.run_method(rep, n).factors[0] / rep.true_steps[0] - 1
           for n in ('legacy', 'interp_log', 'joint_o4_e4')}
    assert -0.16 < dev['legacy'] < -0.11
    assert abs(dev['interp_log']) < 0.015
    assert 0.015 < dev['joint_o4_e4'] < 0.025


def test_global_fit_has_no_guard_as_coded():
    """As coded: on a 100 Å film (NX-like grids, no noise) the last join's
    window spans more than a fringe; the guarded joint fit steps down and
    stays within 0.2 %, the global fit (no guard) is 3 % off."""
    rep = refl.denoised(refl.replicate(refl.Config(truth='film', plan='nx'), 0))
    j = refl.run_method(rep, 'joint_o4_e4').factors[2] / rep.true_steps[2] - 1
    g = refl.run_method(rep, 'global').factors[2] / rep.true_steps[2] - 1
    assert abs(j) < 0.002
    assert -0.04 < g < -0.02


def test_coincident_fails_on_staggered_grids_and_says_so():
    rep = refl.replicate(refl.Config(truth='water', plan='staggered'), 0)
    r = refl.run_method(rep, 'coincident')
    assert not r.ok and 'no factor' in r.error


def test_chi2_against_the_truth_with_the_full_covariance_is_near_one():
    vals = [refl.chi2_vs_truth(rep, refl.run_method(rep, 'joint_o4_e4'))[1]
            for rep in (refl.replicate(FAST, s) for s in range(4))]
    assert 0.6 < np.mean(vals) < 1.4


# ---- burn line-cut mode ------------------------------------------------------------------------

def test_a_burn_replicate_is_reproducible_from_its_seed():
    a, b = bm.replicate(bm.Config(change='shift'), 3), bm.replicate(bm.Config(change='shift'), 3)
    c = bm.replicate(bm.Config(change='shift'), 4)
    assert all(np.array_equal(p, q) for p, q in zip(a.profiles, b.profiles))
    assert not np.array_equal(a.profiles[5], c.profiles[5])
    assert np.allclose(a.parts(5)['total'], a.clean[5][:, 1], rtol=1e-12)


def test_the_burn_mode_recovers_a_shift():
    """True shift 0.004 Å⁻¹ over the test: template and Gaussian fit within
    10 %; the moments read about half (as coded: the steady shoulder in the
    window dilutes the centroid, P44 / hand-off 07)."""
    rep = bm.replicate(bm.Config(change='shift'), 1)
    res = bm.run_all(rep, models=('constant', 'linear'))
    true = bm.true_change(rep, 'centre')
    assert true == pytest.approx(0.004, rel=1e-9)
    for n in ('template', 'fit'):
        assert bm.measured_change(res[n], 'centre', rep.duration()) == pytest.approx(true, rel=0.10)
        assert not res[n].trends['centre'].stable
    assert 0.3 < bm.measured_change(res['moments'], 'centre', rep.duration()) / true < 0.6


def test_the_burn_mode_reads_a_broadening():
    """FWHM +30 % at constant area: template and fit see a change of 20–40 %
    (as coded: 24 % and 39 %); the template also reads an intensity gain
    (P44, as coded +14 %), the moments barely see the broadening."""
    rep = bm.replicate(bm.Config(change='broaden'), 1)
    res = bm.run_all(rep, models=('constant', 'linear'))
    T = rep.duration()
    assert bm.true_change(rep, 'fwhm') == pytest.approx(0.3, rel=1e-9)
    for n in ('template', 'fit'):
        assert 0.2 < bm.measured_change(res[n], 'fwhm', T) < 0.42
    assert bm.measured_change(res['template'], 'intensity', T) > 0.08
    assert bm.measured_change(res['moments'], 'fwhm', T) < 0.05


def test_the_rebuilt_frame_curves_are_the_fitted_ones():
    """The template and Gaussian curves drawn for a frame give back the χ²
    that measure_gid reported for that frame."""
    rep = bm.replicate(bm.Config(change='broaden'), 2)
    for n in ('template', 'fit'):
        r = bm.run_estimator(rep, n, models=('constant',))
        for k in (0, 10, 20):
            x, y = bm.frame_curve(rep, r, k, n=4000)
            p = rep.profiles[k]
            sel = (p[:, 0] >= r.window[0]) & (p[:, 0] <= r.window[1])
            if n == 'template':
                xx = p[sel, 0]
                A, d, w, b0, b1 = r.details[k]['params']
                from scipy.interpolate import CubicSpline
                xs, shape = r.shape
                c = r.reference['centre']
                v = CubicSpline(xs, shape, bc_type='natural', extrapolate=False)(c + (xx - c - d) / w)
                model = A * np.where(np.isfinite(v), v, 0.0) + b0 + b1 * (xx - c)
                chi2 = np.sum(((p[sel, 1] - model) / p[sel, 2]) ** 2) / (sel.sum() - 5)
                assert chi2 == pytest.approx(r.details[k]['chi2_dof'], rel=1e-9)
            # the drawn curve (on its own grid) through the data: the same misfit within interpolation
            yi = np.interp(p[sel, 0], x, y)
            chi = np.sum(((p[sel, 1] - yi) / p[sel, 2]) ** 2) / sel.sum()
            ref = r.details[k]['chi2_dof']
            assert chi == pytest.approx(ref, rel=0.25), (n, k, chi, ref)


# ---- drawings and the window -------------------------------------------------------------------

def test_the_default_views_are_written_headless(tmp_path):
    from demonstrator import figures
    figures.views(str(tmp_path), seed=1)
    for f in ('view_refl.png', 'view_burn.png'):
        assert os.path.getsize(tmp_path / f) > 20000


def test_every_item_can_be_drawn():
    from matplotlib.figure import Figure
    from demonstrator import draw
    rep = refl.replicate(refl.Config(truth='film', plan='staggered'), 1)
    res = refl.run_all(rep)
    fig = Figure()
    keys = {k for k, _, _ in draw.REFL_ITEMS}
    draw.refl_figure(fig, rep, res, keys, list(refl.METHODS), 'r', 2, refl.run_all(refl.denoised(rep)))
    draw.refl_figure(fig, rep, res, set(), [], 'rrf', 9)
    brep = bm.replicate(bm.Config(change='shoulder'), 1)
    bres = bm.run_all(brep, models=('constant', 'linear'))
    draw.burn_figure(fig, brep, bres, {k for k, _, _ in draw.BURN_ITEMS}, list(bm.ESTIMATORS), 0)
    draw.burn_figure(fig, brep, bres, set(), [], 99)


@pytest.mark.gui
def test_the_window_space_bar_checkboxes_and_modes(qapp, recorder):
    from PyQt5 import QtCore
    from PyQt5.QtTest import QTest
    from demonstrator.window import DemoWindow
    w = DemoWindow(mode='refl', seed=0, refl_config=refl.Config(truth='water', plan='nx'))
    try:
        w.show()
        first = w.rep.scans[1].y.copy()
        QTest.keyClick(w, QtCore.Qt.Key_Space)
        assert w.seed == 1 and not np.array_equal(first, w.rep.scans[1].y)
        box = w.refl_items['bands']
        was = box.isChecked()
        box.setFocus()
        QTest.keyClick(box, QtCore.Qt.Key_Space)           # space on a checkbox: a new replicate, not a toggle
        assert w.seed == 2 and box.isChecked() == was
        box.click()
        assert box.isChecked() != was
        w.method_boxes['joint_o2_e4'].click()
        w.view.setCurrentIndex(1)
        w.join.setValue(3)
        w.plan.setCurrentIndex(w.plan.findData('edge'))
        assert w.rep.config.plan == 'edge' and w.join.maximum() == 2
        w.mode.setCurrentIndex(1)
        assert isinstance(w.rep, bm.Replicate)
        QTest.keyClick(w, QtCore.Qt.Key_Space)
        assert w.seed == 3 and w.rep.seed == 3
        w.frame.setValue(4)
        w.estimator_boxes['moments'].click()
        w.burn_items['all_models'].click()
        w.change.setCurrentIndex(w.change.findData('shift'))
        assert w.rep.config.change == 'shift' and w.amount.value() == pytest.approx(0.004)
        assert 'template' in w.notes.toPlainText()
    finally:
        w.close()
        w.deleteLater()
    assert recorder.exceptions == []


@pytest.mark.slow
def test_the_report_figures_are_written_headless(tmp_path):
    """The figure writer with few replicates (16 s): every figure, the
    numbers and the summaries."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
    import patch_demo
    assert patch_demo.main(['--save', str(tmp_path / 'out'), '--quick', '--rows', str(tmp_path / 'rows')]) == 0
    names = os.listdir(tmp_path / 'out')
    assert sum(n.endswith('.png') for n in names) == 6
    assert 'numbers.json' in names and 'burn_estimator_summary.csv' in names
    assert sorted(os.listdir(tmp_path / 'rows')) == ['burn_estimators.csv', 'factors_film100_nx.csv',
                                                     'factors_water_nx.csv']
