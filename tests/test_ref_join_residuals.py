"""F74 at the Ref Patch join (owner, 2026-11-22: "a small residuals plot
above every plot that shows a fit"): the joint fit's curve and residuals,
lss_core.reflectivity.join_fit_residuals, and their panel in the Ref Patch
window behind View > Residuals above fits (hidden by default).

Known truth: the synthetic data set's two scans follow one smooth curve,
scan 2 attenuated by synth.ABSFAC. The residuals use the fit's own
variance, so their squares add up to the χ² it reports (an identity, I45)."""
import numpy as np
import pytest

import sweep
import synth
from lss_core import patching, reflectivity
from lss_core.experiment import Experiment


def _scans(dataset):
    r = Experiment(dataset).reflectivity([1, 2])
    return r.per_scan[1][:, :3], r.per_scan[2][:, :3]


def test_the_residuals_add_up_to_the_fits_chi2(dataset):
    a, b = _scans(dataset)
    fit = reflectivity.join_fit_residuals(a, b)
    f, e, _ = reflectivity.join_factor(a, b)
    assert fit['factor'] == pytest.approx(f, rel=1e-12)                  # the factor Ref Patch uses
    r = np.concatenate([fit['a'][1], fit['b'][1]])
    assert np.sum(r ** 2) == pytest.approx(fit['chi2'], rel=1e-9)         # I45
    assert len(r) == fit['dof'] + fit['order'] + 2                         # the points used, minus the parameters
    assert fit['factor'] == pytest.approx(synth.ABSFAC, rel=0.02)         # known truth: the foil
    qa = fit['a'][0]
    assert np.interp(qa, fit['q'], fit['mu_a']) == pytest.approx(a[np.isin(a[:, 0], qa), 1], rel=0.03)


def test_a_wrong_point_stands_out_in_the_residuals(dataset):
    a, b = _scans(dataset)
    clean = reflectivity.join_fit_residuals(a, b)
    bad = b.copy()
    bad[1, 1] *= 1.3                                                       # one point of scan 2, 30 % high
    fit = reflectivity.join_fit_residuals(a, bad)
    qb, rb = fit['b']
    k = int(np.argmin(abs(qb - b[1, 0])))
    assert abs(rb[k]) == max(abs(np.concatenate([fit['a'][1], rb])))      # the worst residual is that point
    assert fit['chi2'] > 10 * max(clean['chi2'], 1.0)


def test_none_where_the_join_falls_back_on_the_legacy_fit():
    a = np.array([[0.01, 1.0, 0.01], [0.02, 0.5, 0.01]])
    b = np.array([[0.02, 0.25, 0.01], [0.03, 0.1, 0.01]])
    assert reflectivity.join_fit_residuals(a, b) is None


@pytest.mark.gui
def test_the_ref_patch_window_shows_the_fit_behind_the_switch(loaded, qapp, recorder):
    from lss_core import residuals
    w = loaded
    w.prefs['auto_save'] = False
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    ax = w.uirefpatch.plotWidget.canvas.ax
    assert getattr(ax, '_lss_residuals', None) is None                    # hidden by default
    assert not [l for l in ax.lines if l.get_gid() == 'joint fit']
    w.fitResidualsAction.setChecked(True)                                  # View > Residuals above fits
    qapp.processEvents()
    ax = w.uirefpatch.plotWidget.canvas.ax
    rax = ax._lss_residuals
    assert rax is not None and rax.get_ylabel() == '(y−fit)/σ'
    curve = [l for l in ax.lines if l.get_gid() == 'joint fit']
    assert len(curve) == 1 and 'χ²/dof' in curve[0].get_label()
    fit = w.refDrawJoinFit(ax)
    pts = [l for l in rax.lines if not getattr(l, '_lss_zero', False)]
    assert [len(l.get_xdata()) for l in pts] == [len(fit['a'][0]), len(fit['b'][0])]
    w.fitResidualsAction.setChecked(False)
    qapp.processEvents()
    ax = w.uirefpatch.plotWidget.canvas.ax
    assert getattr(ax, '_lss_residuals', None) is None
    assert not [l for l in ax.lines if l.get_gid() == 'joint fit']
    w.fitResidualsAction.setChecked(True)
    w.uirefpatch.nextPushButton.click()                                    # Finish: the patch ends, nothing redrawn
    qapp.processEvents()
    w.fitResidualsAction.setChecked(False)
    qapp.processEvents()
    assert recorder.exceptions == []
