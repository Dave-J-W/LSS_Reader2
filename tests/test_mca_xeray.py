"""MCA "Fit lines" two ways (F110; owner, 2026-11-26): "xeray should be
default for mca fitting, but it tends to undercount error so include our
best method (poisson fixed width etc) as well, and report both fits and
errors". Revised by the owner the same day, after the real-data results
(C66, C69) and a known-truth case where the fixed width reads 0.68: the
reader's fit is the default, its width from the sum of the series.

The reader's Poisson fit (Si escapes stripped, the width from the sum) is
the value plotted, merged and exported in _flu.txt; XeRay
(lss_core.fluorescence.xeray_fit, ported from the Lee group's MATLAB tool in
the XRF shootout) sits beside it in every row, the list, the plot and
_flu_xeray.txt."""
import math
import os

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
    assert both['options'].fwhm == o.fwhm == 0 and both['width_at'] is None          # the width from the sum
    assert len(both['each']) == 3 and both['j'] is not None
    for f, r in zip(both['xeray'], both['each']):
        assert abs(f.area / (r.peaks[both['j']].area / both['step']) - 1) < 0.1          # the two agree on a clean line
    fixed = fl.fit_line_series(data, o, detector_width=True)                          # the option
    assert fixed['options'].fwhm == pytest.approx(fl.detector_fwhm(6.40, 0.12)) and fixed['width_at'] == 6.40
    plain = fl.fit_line_series(data, o, strip_escapes=False)
    assert plain['options'].fwhm == o.fwhm and plain['width_at'] is None
    free = fl.fit_line_series(data, peaks.FitOptions(n_peaks=1, x_range=(6.0, 6.8)), detector_width=True)
    assert free['width_at'] == pytest.approx(6.40, abs=0.01)                          # no energy: the line XeRay found
    assert free['options'].fwhm == pytest.approx(fl.detector_fwhm(free['width_at'], 0.12))


def test_the_default_reads_a_line_wider_than_the_detector_model():
    """Known truth (GUI manager, #123; reproduced by main man, 2026-11-26):
    the synthetic XFNTR line is σ = 6 channels = 0.12 keV, 1.65 × the width
    the detector model gives at 6.4 keV with 0.12 keV noise. The default
    (width from the sum) reads every frame's true area; the fixed width reads
    0.68 of it, the reason the owner turned the fixed width off."""
    import synth
    step = 0.02
    e = np.arange(1, synth.XF_CHANNELS + 1) * step
    data, truth = [], []
    for q in synth.XF_QZ:
        n, line = synth.xfntr_spectrum(q)
        data.append(np.column_stack([e, n, np.sqrt(np.maximum(n, 1))]))
        truth.append(line.sum())
    pk = synth.XF_PEAK_CHANNEL * step
    o = peaks.FitOptions(background='quadratic', n_peaks=1, x_range=(pk - 0.6, pk + 0.6))
    for kw, want, tol in (({}, 1.0, 0.005), (dict(detector_width=True), 0.68, 0.01)):
        b = fl.fit_line_series(data, o, **kw)
        ours = np.array([r.peaks[b['j']].area / b['step'] for r in b['each']]) / truth
        assert np.allclose(ours, want, atol=tol), (kw, ours)
        assert np.allclose([f.area for f in b['xeray']], truth, rtol=0.005)     # XeRay reads it too


def test_merge_keeps_the_pairs_together():
    rows = [[1, 0.010, 10, 100.0, 10.0], [2, 0.0101, 10, 110.0, 10.5], [3, 0.020, 10, 50.0, 7.0]]
    m5 = fl.merge_rows(rows, 'qz', 0.001)
    m7 = fl.merge_rows([r + [r[3] * 1.1, r[4] * 1.3] for r in rows], 'qz', 0.001)
    assert np.array_equal(m7[:, :5], m5)                                             # the first pair as before
    m_alone = fl.merge_rows([r[:3] + [r[3] * 1.1, r[4] * 1.3] for r in rows], 'qz', 0.001)
    assert np.allclose(m7[:, 5:], m_alone[:, 3:])                                     # the second by the same rule


def test_merge_skips_a_missing_value():
    """Issue #151: one missing value (an accepted single fit has no XeRay
    value; NaN) made its whole group NaN for that pair. It now adds nothing,
    and the group merges the values it has; the other pair is untouched."""
    nan = float('nan')
    full = [[1, 0.010, 10, 100.0, 10.0, 90.0, 9.0], [2, 0.0101, 10, 110.0, 10.5, 99.0, 9.5],
            [3, 0.020, 10, 50.0, 7.0, 45.0, 6.5]]
    holed = [r[:] for r in full] + [[4, 0.0102, 10, 105.0, 10.2, nan, nan]]
    m = fl.merge_rows(holed, 'qz', 0.001)
    ref = fl.merge_rows(full, 'qz', 0.001)
    four = fl.merge_rows([r[:5] for r in holed], 'qz', 0.001)
    assert len(m) == 2 and np.all(np.isfinite(m))
    assert np.allclose(m[:, 5:], ref[:, 5:])                      # the second pair as if the row were not there
    assert np.array_equal(m[:, :5], four)                         # the first pair merges all four rows, as before
    first = [[0, 0.0099, 10, 104.0, 10.1, nan, nan]] + [r[:] for r in full]
    assert np.allclose(fl.merge_rows(first, 'qz', 0.001)[:, 5:], ref[:, 5:])   # missing in the group's first row
    alone = fl.merge_rows([[1, 0.01, 10, 100.0, 10.0, nan, nan], [2, 0.0101, 10, 110.0, 10.5, nan, 0.0]], 'qz', 0.001)
    assert np.isnan(alone[0, 5]) and np.isfinite(alone[0, 3])     # nothing usable: NaN stays


def test_window_fit_lines_reports_both_and_exports_both(loaded, qapp, dataset, recorder, tmp_path):
    sweep.state_mca_frames(loaded, qapp, dataset)
    loaded.mcaFitLinesPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    rows = loaded.mcaIntData
    assert len(rows) == 2 and all(len(r) == 7 for r in rows)
    xr, nums = loaded.mcaXeRayFits
    for r, f in zip(rows, xr):
        assert f.ok and r[5] == pytest.approx(f.area) and r[6] == pytest.approx(f.area_err)   # XeRay beside
    ref, each, _ = loaded.mcaLineFits
    j = 0
    for r, fit in zip(rows, each):
        assert r[3] == pytest.approx(fit.peaks[j].area / float(np.median(np.diff(
            loaded.nomMcaData[loaded.selectedMcaScanNums[0]][:, 0]))))                  # the reader's fit first
    assert rows[1][3] == pytest.approx(2 * rows[0][3], rel=0.02)                    # the second spectrum is × 2
    assert rows[1][5] == pytest.approx(2 * rows[0][5], rel=0.05)
    assert 'XeRay ' in loaded.ui.mcaDataListWidget.item(0).text()
    assert "the reader's fit (default)" in loaded.command and 'width from the sum' in loaded.command
    assert 'XeRay' in loaded.command and 'XeRay' in recorder.messages[-1]
    name = str(tmp_path / 'out')
    recorder.save_name = name
    loaded.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    a = np.loadtxt(name + '_flu.txt', comments='#')
    b = np.loadtxt(name + '_flu_xeray.txt', comments='#')
    assert a.shape == b.shape == (2, 3)                                              # the same three columns
    assert np.allclose(a[:, 1], [r[3] for r in rows]) and np.allclose(b[:, 1], [r[5] for r in rows])
    assert "XeRay's fit" in open(name + '_flu_xeray.txt').readline()
    assert not os.path.exists(name + '_flu_fit.txt')
    assert recorder.exceptions == []
