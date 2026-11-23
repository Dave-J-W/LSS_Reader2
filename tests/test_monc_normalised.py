"""Every view of the detector data per Monc, and "Sum All" as ΣN/ΣM (owner,
2026-11-23: "finish f91 and make sure that all data is default normalized by
monc, even gisaxs"; F91: "sum the signals, sum the monitor/normalizer, then
do the normalization").

Before: "Sum All" averaged the normalised frames, GISAXS and the image
display showed raw counts (unless a background was selected). The legacy
behaviour stays as two preferences for the Reduction options page (F86):
'sum_all_legacy_average' and 'gisaxs_raw_counts'."""
import numpy as np
import pytest

import sweep
from lss_core import cuts
from lss_core.experiment import ABSFAC_10KEV, Experiment
from lss_core.normalise import attenuation


def test_sum_frames_is_the_counts_over_the_monitors():
    rng = np.random.default_rng(0)
    N = [rng.poisson(50.0, size=(5, 7)).astype(float) for _ in range(3)]
    M = [1e5, 3e5, 2e5]
    d = [n / m for n, m in zip(N, M)]
    e = [np.sqrt(n) / m for n, m in zip(N, M)]
    s, se = cuts.sum_frames(d, e, M)
    assert np.allclose(s, sum(N) / sum(M), rtol=1e-12)
    assert np.allclose(se, np.sqrt(sum(N)) / sum(M), rtol=1e-12)        # the Poisson error of ΣN, over ΣM
    eq = [n / 2e5 for n in N]
    assert np.allclose(cuts.sum_frames(eq, e, [2e5] * 3)[0], cuts.mean_frame(eq, e)[0], rtol=1e-12)
    assert cuts.sum_weights(M) == pytest.approx([1 / 6, 3 / 6, 2 / 6])
    assert cuts.sum_weights(M, legacy=True) == pytest.approx([1 / 3] * 3)
    with pytest.raises(ValueError):
        cuts.sum_frames(d, e, [1e5, 0.0, 2e5])


def test_frames_with_absorbers_are_summed_by_their_effective_monitors():
    """N_i has mean λ M_i / A_i: the pooled estimate is ΣN / Σ(M_i / A_i)."""
    N = [np.array([100.0, 40.0]), np.array([30.0, 12.0])]
    M, n_abs, absfac = [1e5, 2e5], [0, 2], 1.4247
    A = [attenuation(absfac, k) for k in n_abs]
    d = [n * a / m for n, a, m in zip(N, A, M)]
    w = [cuts.frame_normaliser(m, absfac, k) for m, k in zip(M, n_abs)]
    s, _ = cuts.sum_frames(d, [np.sqrt(n) for n in N], w)
    assert np.allclose(s, sum(N) / sum(m / a for m, a in zip(M, A)), rtol=1e-12)


def _unequal_monitors(dataset, factors=(1.0, 3.0)):
    """Scan 2's Monc multiplied point by point (scan 2: frames at one absorber)."""
    lines = open(dataset).read().split('\n')
    out, in2, k = [], False, 0
    for line in lines:
        if line.startswith('#S '):
            in2 = line.split()[1] == '2'
            k = 0
        elif in2 and line.strip() and not line.startswith('#'):
            v = line.split()
            v[4] = repr(float(v[4]) * factors[k % len(factors)])
            line, k = ' '.join(v), k + 1
        out.append(line)
    open(dataset, 'w').write('\n'.join(out))


def test_the_scripted_summed_cut_is_the_counts_over_the_monitors(dataset):
    _unequal_monitors(dataset)
    exp = Experiment(dataset)
    each = exp.cut([2], 'Pix V', (90, 104))
    new = exp.cut([2], 'Pix V', (90, 104), summed=True)
    old = exp.cut([2], 'Pix V', (90, 104), summed=True, sum_mode='mean')
    frames = exp.frames([2])
    w = np.array([cuts.frame_normaliser(f.monitor, ABSFAC_10KEV, f.absorber) for f in frames])
    assert len(set(np.round(w, 3))) > 1                                     # the monitors do differ
    ys = np.array([c[:, 1] for c in each.cuts])
    assert new.cuts[0][:, 1] == pytest.approx((w[:, None] * ys).sum(axis=0) / w.sum(), rel=1e-10)
    assert old.cuts[0][:, 1] == pytest.approx(ys.mean(axis=0), rel=1e-10)
    assert not np.allclose(new.cuts[0][:, 1], old.cuts[0][:, 1])


def _two_frames_unequal(w, qapp):
    sweep._select_scans(w, qapp, [1])
    sweep._select_images(w, qapp, [0, 1])
    w.pilMonc[0], w.pilMonc[1] = 1.0e5, 3.0e5
    return [0, 1]


@pytest.mark.gui
def test_the_windows_summed_cut_is_the_counts_over_the_monitors(loaded, qapp, recorder):
    w = loaded
    fr = _two_frames_unequal(w, qapp)
    w.ui.gixSumCheckBox.setChecked(True)
    w.ui.pilCutDirComboBox.setCurrentIndex(3)
    w.ui.pilIntRangeLineEdit.setText('90:104')
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    A = attenuation(w.absfac, w.pil_AbsNum[0])
    assert w.pil_AbsNum[0] == w.pil_AbsNum[1]
    sum_n_over_m = (w.pilData[0] + w.pilData[1]) * A / (w.pilMonc[0] + w.pilMonc[1])
    assert w.cutData[-1][:, 1] == pytest.approx(sum_n_over_m[:, 90:106].sum(axis=1), rel=1e-10)
    w.prefs['sum_all_legacy_average'] = True                                # the Reduction options' legacy mean
    w.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    mean = (w.pilData[0] / w.pilMonc[0] + w.pilData[1] / w.pilMonc[1]) * A / 2
    assert w.cutData[-1][:, 1] == pytest.approx(mean[:, 90:106].sum(axis=1), rel=1e-10)
    assert "sum_mode='mean'" in w.cutScript('x')
    assert recorder.exceptions == []


@pytest.mark.gui
def test_gisaxs_is_per_monc_and_its_sum_the_counts_over_the_monitors(loaded, qapp, recorder):
    w = loaded
    fr = _two_frames_unequal(w, qapp)
    A = attenuation(w.absfac, w.pil_AbsNum[0])
    one, _ = w.gisaxsData([0])
    assert np.allclose(one, w.pilData[0] * A / w.pilMonc[0], rtol=1e-12)    # a single frame per Monc
    both, _ = w.gisaxsData(fr)
    assert np.allclose(both, (w.pilData[0] + w.pilData[1]) * A / (w.pilMonc[0] + w.pilMonc[1]), rtol=1e-12)
    w.prefs['gisaxs_raw_counts'] = True                                     # the legacy raw counts
    raw, _ = w.gisaxsData(fr)
    assert np.allclose(raw, (w.pilData[0] + w.pilData[1]) / 2, rtol=1e-12)
    w.prefs['gisaxs_raw_counts'] = False
    w.ui.gixSumCheckBox.setChecked(True)
    i = w.ui.gisaxsComboBox.findText('Show GISAXS')
    w.ui.gisaxsComboBox.setCurrentIndex(i)
    w.ui.gisaxsComboBox.activated.emit(i)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert np.allclose(w.sumData, both, rtol=1e-12)


@pytest.mark.gui
def test_the_image_display_is_per_monc(loaded, qapp, recorder):
    w = loaded
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp, [0])
    w.ui.pilLogIntCheckBox.setChecked(False)
    w.updatePilPlotData()
    qapp.processEvents()
    assert recorder.exceptions == []
    expect = w.pilData[0] * attenuation(w.absfac, w.pil_AbsNum[0]) / w.pilMonc[0]
    assert np.allclose(w.Zdata, expect, rtol=1e-12)
    assert w.imageMax == pytest.approx(np.max(expect))
    assert not np.isclose(w.imageMax, np.max(w.pilData[0]))                 # not the raw counts


@pytest.mark.gui
def test_the_spec_plot_is_normalised_by_monc_wherever_its_column(window, qapp, recorder, tmp_path):
    """The normaliser was the column before the last: Monp in a scan whose
    columns end Monc, Monp, Pilatus (the patch data's); now Monc by name."""
    import synth
    spec = synth.make_absorber_patch_dataset(tmp_path / 'abs')
    window.openSpecFile(fname=spec)
    qapp.processEvents()
    sweep._select_scans(window, qapp, [0])
    assert window.specData[1]['ScanVar'][-2] == 'Monp'
    assert window.ui.spNComboBox.currentText() == 'Monc'
    assert window.ui.spNCheckBox.isChecked()
    assert recorder.exceptions == []
