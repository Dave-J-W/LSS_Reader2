"""Ref Patch with the known absorber ratio (owner, 2026-11-18, F57).

At a join the scale between two scans is either fitted at the overlap (the
patch) or known from the calibrated foils (lss_core.absorbers.Foils.step).
The known ratio is suggested when it is more precise, and used
automatically when the fit's error is above the threshold (Preferences),
the ratio is at least twice as precise, Monc/Monp shows no slit change
(P29) and the two agree within 3 sigma.
"""
import math
import os

import numpy as np
import pytest

import sweep
import synth
from lss_core import absorbers, preferences, reflectivity, stitching
from test_ref_export_golden import reduce_and_save


# ---- core -------------------------------------------------------------------

def _curves(seed=3, noise=0.05):
    rng = np.random.default_rng(seed)
    q1, q2 = np.linspace(0.01, 0.05, 9), np.linspace(0.04, 0.10, 7)
    r1, r2 = synth.reflectivity(q1) * 100, synth.reflectivity(q2) * 7
    r1, r2 = r1 * (1 + noise * rng.standard_normal(9)), r2 * (1 + noise * rng.standard_normal(7))
    return np.column_stack([q1, r1, noise * r1]), np.column_stack([q2, r2, noise * r2])


def test_fitted_factor_is_the_factor_merge_uses():
    d1, d2 = _curves()
    fac, err = stitching.fitted_factor(d1, d2)
    merged = stitching.join(d1.copy(), d2.copy(), mtype='merge')
    same = stitching.join(d1.copy(), d2.copy(), mtype='merge', factor=(fac, err))
    assert merged.tobytes() == same.tobytes()       # identical arithmetic
    assert err > 0      # (fac itself is biased here by the legacy cubic interpolation, P1)


def test_imposed_factor_scales_the_new_scan():
    d1, d2 = _curves(noise=0.0)
    d1[:, 2] = d2[:, 2] = 1e-9
    out = stitching.join(d1.copy(), d2.copy(), mtype='merge', factor=(14.0, 0.0))
    tail = out[out[:, 0] > 0.05]
    assert tail[:, 1] == pytest.approx(d2[d2[:, 0] > 0.05, 1] * 14.0)
    per = {1: d1, 2: d2}
    a = reflectivity.patch(per, [1, 2])
    b = reflectivity.patch(per, [1, 2], factors={0: (14.0, 0.0)})
    assert not np.allclose(a[:, 1], b[:, 1]) and b[-1, 1] == pytest.approx(d2[-1, 1] * 14.0)


@pytest.mark.parametrize('patch, known, monitor, auto, use, suggest, why', [
    ((10.0, 0.5), (10.1, 0.01), 1.0, True, True, True, 'more precise'),          # 5 % fit, 1 % known
    ((10.0, 0.2), (10.1, 0.01), 1.0, True, False, True, 'more precise'),         # 2 % < 3 % threshold
    ((10.0, 0.5), (10.1, 0.01), 1.0, False, False, True, 'more precise'),        # auto off: suggestion only
    ((10.0, 0.5), (10.1, 0.03), 1.0, True, False, True, 'more precise'),         # known not 2x better
    ((10.0, 0.05), (10.1, 0.01), 1.0, True, False, False, 'patch is more precise'),
    ((10.0, 0.5), (10.1, 0.01), 1.58, True, False, False, 'slits changed'),      # P29
    ((10.0, 0.5), (10.1, 0.01), None, True, False, False, 'no Monp'),
    ((10.0, 0.5), (14.0, 0.01), 1.0, True, False, False, 'sigma from the patch'),
    ((10.0, 0.5), None, 1.0, True, False, False, 'no known ratio'),
])
def test_patch_choice(patch, known, monitor, auto, use, suggest, why):
    c = reflectivity.patch_choice(patch, known, monitor, auto=auto, threshold=0.03)
    assert (c['use'], c['suggest']) == (use, suggest)
    assert why in c['why']


def test_monitor_change_at_the_overlap():
    qa, qb = np.linspace(0.01, 0.05, 9), np.linspace(0.04, 0.10, 7)
    ones_a, ones_b = np.ones(9), np.ones(7)
    assert reflectivity.monitor_change(qa, ones_a, ones_a, qb, ones_b, ones_b) == pytest.approx(1.0)
    assert reflectivity.monitor_change(qa, ones_a, ones_a, qb, 1.6 * ones_b, ones_b) == pytest.approx(1.6)
    assert reflectivity.monitor_change(qa, ones_a, None, qb, ones_b, ones_b) is None
    assert reflectivity.monitor_change(qa, ones_a, ones_a, qb + 1, ones_b, ones_b) is None   # no overlap


def test_preferences_store(tmp_path, monkeypatch):
    monkeypatch.setenv(preferences.ENV, str(tmp_path / 'p.json'))
    assert preferences.load() == preferences.DEFAULTS
    p = dict(preferences.DEFAULTS, patch_threshold_percent=5, calibrated_foils=False)
    assert preferences.save(p) is None
    assert preferences.load() == dict(preferences.DEFAULTS, patch_threshold_percent=5.0, calibrated_foils=False)
    (tmp_path / 'p.json').write_text('{"calibrated_foils": "yes", "nonsense": 1')
    assert preferences.load() == preferences.DEFAULTS          # unreadable: defaults


# ---- window -----------------------------------------------------------------

def _patch(w, qapp, recorder, tmp_path, name='out'):
    out = str(tmp_path / name)
    reduce_and_save(w, qapp, recorder, out, [0, 1])
    return out


def _open(window, qapp, tmp_path, **kw):
    spec = synth.make_absorber_patch_dataset(tmp_path / 'data', **kw)
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    return window


def test_poor_patch_uses_the_known_ratio_and_the_script_reproduces_it(window, qapp, recorder, tmp_path):
    w = _open(window, qapp, tmp_path)
    out = _patch(w, qapp, recorder, tmp_path)
    k, rel = absorbers.calibrated(10.0).step(6, 2, qz=0.04)      # overlap starts at Qz 0.04
    assert w.refFactors == {0: (pytest.approx(k), pytest.approx(k * rel))}
    info = w.refInfoShown
    assert info['choice']['patch_rel'] > 0.03 and info['choice']['use']
    assert any('known absorber ratio' in m and 'used instead of the fitted' in m for m in recorder.messages)
    script = w.reflectivityScript(str(tmp_path / 'scripted'))
    assert 'factors={0: (' in script
    from lss_core.experiment import Experiment     # noqa: F401  (used by the script)
    exec(compile('exp = Experiment(%r)\n' % w.specFileName + script, 'script', 'exec'), {'Experiment': Experiment})
    for kind in ('_ref.txt', '_rrf.txt'):
        assert open(out + kind, 'rb').read() == open(str(tmp_path / 'scripted') + kind, 'rb').read()
    assert recorder.exceptions == []


def test_slit_change_keeps_the_patch(window, qapp, recorder, tmp_path):
    w = _open(window, qapp, tmp_path, monp_jump=1.6)
    _patch(w, qapp, recorder, tmp_path)
    assert w.refFactors == {}
    assert 'slits changed' in w.refInfoShown['choice']['why']
    assert 'slits changed' in w.uirefpatch.knownRatioCheckBox.toolTip()
    assert recorder.exceptions == []


def test_auto_off_only_suggests_and_the_box_applies_it(window, qapp, recorder, tmp_path):
    w = _open(window, qapp, tmp_path)
    w.setPreference('patch_auto_known_ratio', False)
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    box, lab = w.uirefpatch.knownRatioCheckBox, w.uirefpatch.knownRatioLabel
    assert box.isEnabled() and not box.isChecked()
    assert 'try known ratio' in lab.text()
    box.setChecked(True)                    # the user takes the suggestion
    qapp.processEvents()
    assert 'try known ratio' not in lab.text()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert 0 in w.refFactors
    assert recorder.exceptions == []


def test_legacy_data_without_monp_are_unchanged(loaded, qapp, recorder, tmp_path):
    """make_dataset has no Monp: the known ratio is never applied."""
    w = loaded
    w.directory = str(tmp_path)
    _patch(w, qapp, recorder, tmp_path)
    assert w.refFactors == {}
    assert 'factors=' not in w.reflectivityScript('x')
    assert recorder.exceptions == []
