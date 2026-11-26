"""MCA "Fit lines" two ways (F110; owner, 2026-11-26): "xeray should be
default for mca fitting, but it tends to undercount error so include our
best method (poisson fixed width etc) as well, and report both fits and
errors".

XeRay (lss_core.fluorescence.xeray_fit, ported from the Lee group's MATLAB
tool in the XRF shootout) is the value plotted, merged and exported in
_flu.txt; the reader's Poisson fit with the detector's width and the Si
escapes stripped (the shootout's honest method) sits beside it in every row,
the list, the plot and _flu_fit.txt."""
import math

import numpy as np
import pytest

import sweep
from lss_core import fluorescence as fl, peaks


def _spectrum(seed=0, amp=400.0, centre=6.40, sig=0.07, bg=20.0, slope=-2.0):
    e = np.linspace(5.5, 7.5, 400)
    true = amp * np.exp(-((e - centre) / sig) ** 2 / 2) + bg + slope * (e - centre)
    n = np.random.default_rng(seed).poisson(true).astype(float)
    step = e[1] - e[0]
    return e, n, amp * sig * math.sqrt(2 * math.pi) / step


def test_xeray_recovers_a_line_on_a_straight_background_and_reports_its_own_error():
    errs = []
    for seed in range(20):
        e, n, area = _spectrum(seed)
        r = fl.xeray_fit(e, n, np.sqrt(np.maximum(n, 1)), (6.0, 6.8), 6.40)
        assert r.ok and abs(r.area / area - 1) < 0.05 and abs(r.centre - 6.40) < 0.01
        box = (e >= 6.0) & (e <= 6.8)
        assert r.area_err == pytest.approx(math.sqrt(np.sum(np.maximum(n, 1)[box])))   # √(counts in the window)
        errs.append(r.area / area - 1)
    assert abs(np.mean(errs)) < 0.01                                                   # unbiased on a clean line
    assert r.model(np.array([6.40]))[0] == pytest.approx(r.slope * 6.40 + r.const + r.area * r.step /
                                                         (r.fwhm / 2.3548 * math.sqrt(2 * math.pi)), rel=1e-3)
    e, n, _ = _spectrum(1)
    assert not fl.xeray_fit(e, n, None, (6.40, 6.405)).ok                              # too few channels
    assert fl.xeray_fit(e, n * 1e-6, np.sqrt(n) * 1e-6, (6.0, 6.8), 6.40).area == pytest.approx(
        fl.xeray_fit(e, n, np.sqrt(n), (6.0, 6.8), 6.40).area * 1e-6, rel=1e-3)       # any scale (normalised data)


def test_fit_line_series_gives_both_fits():
    data = []
    for seed in range(3):
        e, n, area = _spectrum(seed)
        data.append(np.column_stack([e, n, np.sqrt(np.maximum(n, 1))]))
    o = peaks.FitOptions(centres=(6.40,), n_peaks=1, x_range=(6.0, 6.8))
    both = fl.fit_line_series(data, o)
    assert len(both['xeray']) == 3 and all(f.ok for f in both['xeray'])
    assert both['options'].fwhm == pytest.approx(fl.detector_fwhm(6.40, 0.12))     # the detector's width
    assert len(both['each']) == 3 and both['j'] is not None
    for f, r in zip(both['xeray'], both['each']):
        assert abs(f.area / (r.peaks[both['j']].area / both['step']) - 1) < 0.1          # the two agree on a clean line
    assert both['width_at'] == 6.40
    plain = fl.fit_line_series(data, o, detector_width=False, strip_escapes=False)
    assert plain['options'].fwhm == o.fwhm and plain['width_at'] is None
    free = fl.fit_line_series(data, peaks.FitOptions(n_peaks=1, x_range=(6.0, 6.8)))   # no energy given
    assert free['width_at'] == pytest.approx(6.40, abs=0.01)                          # the line XeRay found
    assert free['options'].fwhm == pytest.approx(fl.detector_fwhm(free['width_at'], 0.12))


def test_merge_keeps_the_pairs_together():
    rows = [[1, 0.010, 10, 100.0, 10.0], [2, 0.0101, 10, 110.0, 10.5], [3, 0.020, 10, 50.0, 7.0]]
    m5 = fl.merge_rows(rows, 'qz', 0.001)
    m7 = fl.merge_rows([r + [r[3] * 1.1, r[4] * 1.3] for r in rows], 'qz', 0.001)
    assert np.array_equal(m7[:, :5], m5)                                             # the first pair as before
    m_alone = fl.merge_rows([r[:3] + [r[3] * 1.1, r[4] * 1.3] for r in rows], 'qz', 0.001)
    assert np.allclose(m7[:, 5:], m_alone[:, 3:])                                     # the second by the same rule


def test_window_fit_lines_reports_both_and_exports_both(loaded, qapp, dataset, recorder, tmp_path):
    sweep.state_mca_frames(loaded, qapp, dataset)
    loaded.mcaFitLinesPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    rows = loaded.mcaIntData
    assert len(rows) == 2 and all(len(r) == 7 for r in rows)
    xr, nums = loaded.mcaXeRayFits
    for r, f in zip(rows, xr):
        assert f.ok and r[3] == pytest.approx(f.area) and r[4] == pytest.approx(f.area_err)
    ref, each, _ = loaded.mcaLineFits
    assert rows[1][5] == pytest.approx(2 * rows[0][5], rel=0.02)                    # the second spectrum is × 2
    assert rows[1][3] == pytest.approx(2 * rows[0][3], rel=0.05)
    assert 'fit ' in loaded.ui.mcaDataListWidget.item(0).text()
    assert 'XeRay' in loaded.command and 'XeRay' in recorder.messages[-1]
    name = str(tmp_path / 'out')
    recorder.save_name = name
    loaded.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    a = np.loadtxt(name + '_flu.txt', comments='#')
    b = np.loadtxt(name + '_flu_fit.txt', comments='#')
    assert a.shape == b.shape == (2, 3)                                              # the same three columns
    assert np.allclose(a[:, 1], [r[3] for r in rows]) and np.allclose(b[:, 1], [r[5] for r in rows])
    assert 'XeRay' in open(name + '_flu_fit.txt').readline()
    assert recorder.exceptions == []
