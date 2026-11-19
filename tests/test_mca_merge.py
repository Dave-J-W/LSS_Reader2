"""MCA Merge (P7 kept, owner 2026-11-19) with the owner's XFNTR rule, without
the edge check (F65 steps 2 and 5): default window 0.1 × the Qz grid step,
Qz jitter 3e-5 1/Å added to the errors on the Qz axis; values unchanged.
Which scans to merge is the user's choice."""
import numpy as np
import pytest

import sweep
from lss_core import fluorescence as fl
from lss_core.experiment import Experiment
from test_monitor_gain import MCA, xf  # noqa: F401  (fixture)
from test_script_console import _run_script


def _legacy_merge(rows, index, resolution):
    """The window's mcaIntMerge before 2026-11-19, verbatim arithmetic."""
    d0 = np.array(rows)
    d0 = d0[np.argsort(d0[:, index])]
    data = [d0[0]]
    for i in range(1, len(d0)):
        if np.abs(d0[i][index] - data[-1][index]) <= resolution:
            a = data[-1][3] ** 2 / data[-1][4] ** 2
            b = d0[i][3] ** 2 / d0[i][4] ** 2
            c = data[-1][3] / data[-1][4] ** 2
            d = d0[i][3] / d0[i][4] ** 2
            data[-1][3] = (a + b) / (c + d)
            data[-1][4] = np.sqrt((a + b) / (c + d) ** 2)
        else:
            data = np.vstack((data, d0[i]))
    return np.array(data)


def _rows(rng, repeats=3, n=20, step=0.001):
    rows = []
    for rep in range(repeats):
        for k in range(n):
            q = 0.01 + k * step + rng.normal(0, 3e-5)
            counts = rng.poisson(200 * (1 + np.tanh((q - 0.02) / 0.002)) + 20)
            mon = 1e5 * (1 + 0.1 * rep)
            rows.append([k + 1 + rep * n, q, 10.0, counts / mon, max(np.sqrt(counts), 1) / mon])
    return rows


@pytest.mark.parametrize('x', ['frame', 'qz', 'energy'])
@pytest.mark.parametrize('window', [0.0, 1e-4, 5e-4, 2.0])
def test_values_and_counting_errors_are_the_windows_merge(x, window):
    rows = _rows(np.random.default_rng(1))
    old = _legacy_merge(rows, {'frame': 0, 'qz': 1, 'energy': 2}[x], window)
    new = fl.merge_rows(rows, x, window, jitter=0)
    assert np.array_equal(old, new)


def test_default_window_is_a_tenth_of_the_qz_step():
    rows = _rows(np.random.default_rng(2))
    assert fl.grid_step([r[1] for r in rows]) == pytest.approx(0.001, rel=0.1)
    assert fl.default_merge_window(rows, 'qz') == pytest.approx(1e-4, rel=0.1)
    assert fl.default_merge_window(rows, 'frame') == 0.0
    merged = fl.merge_rows(rows, 'qz')
    # repeats of one target merge; never two targets. A repeat can miss its group
    # when its Qz is > 1e-4 from the group's first point (jitter 3e-5 each)
    targets = np.round((merged[:, 1] - 0.01) / 0.001)
    assert 20 <= len(merged) <= 24 and set(targets) == set(range(20))
    assert np.allclose(merged[:, 1], 0.01 + 0.001 * targets, atol=1.5e-4)
    assert fl.grid_step([0.01, 0.012, 0.014]) == pytest.approx(0.002)   # no repeats: the plain spacing


def test_jitter_is_added_to_the_errors_only():
    rows = _rows(np.random.default_rng(3))
    plain = fl.merge_rows(rows, 'qz', jitter=0)
    jit = fl.merge_rows(rows, 'qz')
    assert np.array_equal(plain[:, :4], jit[:, :4])          # values unchanged
    q, v = plain[:, 1], plain[:, 3]
    slope = np.gradient(np.log(v), q)
    extra = np.sqrt(jit[:, 4] ** 2 - plain[:, 4] ** 2)
    # σ_j = I |d ln I/dQz| 3e-5 √Σw²/Σw: between 1/√n and 1 of one point's jitter (n repeats merged)
    one = np.abs(v * slope) * 3e-5
    ok = one > 0
    ratio = extra[ok] / one[ok]
    assert (ratio > 1 / np.sqrt(3) - 0.05).all() and (ratio <= 1 + 1e-12).all()
    assert np.median(ratio) == pytest.approx(1 / np.sqrt(3), rel=0.1)   # mostly three repeats of similar weight
    edge = np.argmax(np.abs(slope))
    assert extra[edge] / plain[edge, 4] > 5 * np.median(extra / plain[:, 4])   # matters near the edge only
    assert np.array_equal(fl.merge_rows(rows, 'frame'), fl.merge_rows(rows, 'frame', jitter=0))   # Qz axis only


@pytest.mark.gui
def test_window_merge_default_and_script(window, qapp, recorder, xf, tmp_path):
    w = window
    w.openSpecFile(fname=xf)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, list(range(1, 1 + len(MCA))))
    sweep._select_images(w, qapp, None)
    w.ui.mcaXAxisComboBox.setCurrentIndex(1)                 # Qz
    w.ui.mcaRanLineEdit.setText('5.6:7.2')
    w.ui.mcaSumAllPushButton.click()
    qapp.processEvents()
    rows = [list(r) for r in w.mcaIntData]
    w.ui.mcaMergePushButton.click()
    qapp.processEvents()
    assert float(w.uimcamerge.resLineEdit.text()) == pytest.approx(fl.default_merge_window(rows, 'qz'), rel=1e-5)
    assert 'jitter' in w.uimcamerge.resLineEdit.toolTip()
    w.uimcamerge.resLineEdit.setText('0.03')                 # merge neighbours, to exercise the plumbing
    w.uimcamerge.okPushButton.click()
    qapp.processEvents()
    expect = fl.merge_rows(rows, 'qz', 0.03)
    assert np.array_equal(np.array(w.mcaIntData), expect) and len(expect) < len(rows)
    gui = str(tmp_path / 'gui')
    recorder.save_name = gui
    w.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    text = w.scriptView.toPlainText()
    assert "flu.merge(0.03, x='qz')" in text
    script = str(tmp_path / 'script')
    _run_script(text.replace(repr(gui), repr(script)), tmp_path)
    assert open(gui + '_flu.txt', 'rb').read() == open(script + '_flu.txt', 'rb').read()
    assert recorder.exceptions == []


def test_merge_of_poisson_points_is_pooled_counts_over_pooled_monitor():
    """Invariant I22: for points y = N·a/M with σ = √N·a/M, the Merge on the
    frame axis (no jitter) gives ΣN/Σ(M/a) with σ = √ΣN/Σ(M/a), exactly,
    also when the points are merged one after another."""
    rng = np.random.default_rng(3)
    n = rng.poisson(40, 6).astype(float) + 1
    m = rng.uniform(5e4, 2e5, 6)
    a = rng.uniform(0.5, 3.0, 6)
    rows = [[0.0, 0.1, 5.0, n[k] * a[k] / m[k], np.sqrt(n[k]) * a[k] / m[k]] for k in range(6)]
    out = fl.merge_rows(rows, x='frame', window=0.5, jitter=0.0)
    assert len(out) == 1
    pooled = n.sum() / (m / a).sum()
    assert out[0][3] == pytest.approx(pooled, rel=1e-12)
    assert out[0][4] == pytest.approx(np.sqrt(n.sum()) / (m / a).sum(), rel=1e-12)
