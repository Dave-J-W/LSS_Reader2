"""F81: repeated reflectivity scans merged by counts and monitors (owner,
2026-11-23: "repeat the macro (multiple scans) and have reader handle
summing the ROIs").

Before: the identical-scans "Merge" averaged the per-monitor curves, each
repeat weighted equally. Now each point's counts and monitors are summed
and normalised once: R = Σ M R / Σ M, σ = √Σ(M σ)² / Σ M (ΣN/ΣM). With
equal monitors that is the old average. The old average stays as the
preference 'repeats_legacy_average' and as ``repeats='mean'`` in
scripts."""
import numpy as np
import pytest

import sweep
import synth
from lss_core import reflectivity as refl
from lss_core.experiment import Experiment


def _rows(qz, n, m):
    return np.column_stack([qz, n / m, np.sqrt(n) / m])


def test_merge_identical_is_the_counts_over_the_monitors():
    qz = np.array([0.04, 0.05, 0.06])
    N = {2: np.array([900.0, 400.0, 100.0]), 3: np.array([2000.0, 790.0, 210.0]), 4: np.array([1300.0, 610.0, 140.0])}
    M = {2: np.full(3, 1e5), 3: np.full(3, 2e5), 4: np.array([1.4e5, 1.5e5, 1.6e5])}
    per_scan = {k: _rows(qz, N[k], M[k]) for k in N}
    mons = {k: v.copy() for k, v in M.items()}
    refl.merge_identical(per_scan, [2, 3, 4], mons)
    sn, sm = sum(N.values()), sum(M.values())
    assert sorted(per_scan) == [2] and sorted(mons) == [2]
    assert per_scan[2][:, 1] == pytest.approx(sn / sm, rel=1e-12)
    assert per_scan[2][:, 2] == pytest.approx(np.sqrt(sn) / sm, rel=1e-12)
    assert mons[2] == pytest.approx(sm)
    # merging one repeat at a time gives the same (the first scan keeps the summed monitors)
    step = {k: _rows(qz, N[k], M[k]) for k in N}
    smons = {k: v.copy() for k, v in M.items()}
    refl.merge_identical(step, [2, 3], smons)
    refl.merge_identical(step, [2, 4], smons)
    assert step[2] == pytest.approx(per_scan[2], rel=1e-12)
    # legacy: the plain mean, as before
    old = {k: _rows(qz, N[k], M[k]) for k in N}
    refl.merge_identical(old, [2, 3, 4])
    ys = [N[k] / M[k] for k in (2, 3, 4)]
    assert old[2][:, 1] == pytest.approx(sum(ys) / 3, rel=1e-12)
    assert old[2][:, 2] == pytest.approx(np.sqrt(sum(N[k] / M[k] ** 2 for k in N)) / 3, rel=1e-12)
    with pytest.raises(ValueError):
        refl.merge_identical({2: _rows(qz, N[2], M[2]), 3: _rows(qz, N[3], M[3])}, [2, 3], {2: M[2], 3: M[3][:2]})


def _repeat_with_more_monitor(spec, factor=1.5):
    """Scan 3 (the repeat of scan 2) with its Monc column scaled."""
    out, cur = [], None
    for line in open(spec).read().split('\n'):
        if line.startswith('#S '):
            cur = line.split()[1]
        elif cur == '3' and line.strip() and not line.startswith('#'):
            v = line.split()
            v[4] = repr(float(v[4]) * factor)
            line = ' '.join(v)
        out.append(line)
    open(spec, 'w').write('\n'.join(out))


@pytest.fixture
def repeats(tmp_path):
    spec = synth.make_identical_scans_dataset(tmp_path / 'same')
    _repeat_with_more_monitor(spec)
    return spec


def test_the_scripted_merge_weighs_each_repeat_by_its_monitor(repeats):
    exp = Experiment(repeats)
    alone = exp.reflectivity([1, 2, 3]).per_scan
    new = exp.reflectivity([1, 2, 3], merge=[[2, 3]]).per_scan[2]
    old = exp.reflectivity([1, 2, 3], merge=[[2, 3]], repeats='mean').per_scan[2]
    m2 = np.array([f.monitor for f in exp.frames([2])])
    m3 = np.array([f.monitor for f in exp.frames([3])])
    assert m3 == pytest.approx(1.5 * m2)
    r2, r3 = alone[2][:, 1], alone[3][:, 1]
    assert new[:, 1] == pytest.approx((m2 * r2 + m3 * r3) / (m2 + m3), rel=1e-10)
    assert old[:, 1] == pytest.approx((r2 + r3) / 2, rel=1e-10)
    assert not np.allclose(new[:, 1], old[:, 1])
    with pytest.raises(ValueError):
        exp.reflectivity([1, 2, 3], merge=[[2, 3]], repeats='sum')


def _patch(window, qapp, spec, tmp_path):
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    sweep._select_scans(window, qapp, [0, 1, 2])
    sweep._select_images(window, qapp)
    window.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    return window.scanqzframe[2].copy(), window.scanqzframe[3].copy()


@pytest.mark.gui
def test_the_windows_merge_is_the_scripts(window, qapp, recorder, repeats, tmp_path):
    s2, s3 = _patch(window, qapp, repeats, tmp_path)
    d = window.uirefpatchsamescan
    assert 'ΣN/ΣM' in d.mergePushButton.toolTip()
    d.mergePushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    exp = Experiment(repeats)
    m2 = np.array([f.monitor for f in exp.frames([2])])
    assert np.array(window.scanqzmon[2]) == pytest.approx(2.5 * m2)      # the summed monitors: 1 + 1.5 of scan 2's
    script = exp.reflectivity([1, 2, 3], merge=[[2, 3]]).per_scan[2]
    assert window.scanqzframe[2] == pytest.approx(script, rel=1e-10)
    assert window.scanqzframe[2][:, 1] == pytest.approx((s2[:, 1] + 1.5 * s3[:, 1]) / 2.5, rel=1e-10)
    assert "repeats=" not in window.reflectivityScript('x')               # the default needs no keyword


@pytest.mark.gui
def test_the_legacy_preference_averages(window, qapp, recorder, repeats, tmp_path):
    window.prefs['repeats_legacy_average'] = True
    s2, s3 = _patch(window, qapp, repeats, tmp_path)
    window.uirefpatchsamescan.mergePushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert window.scanqzframe[2][:, 1] == pytest.approx((s2[:, 1] + s3[:, 1]) / 2, rel=1e-12)
    window.uirefpatchsamescan.nextPushButton.click()
    window.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert "repeats='mean'" in window.reflectivityScript('x')
    assert recorder.exceptions == []
