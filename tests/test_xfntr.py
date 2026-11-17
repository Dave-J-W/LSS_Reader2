"""Fluorescence (XFNTR) reduction: MCA spectra -> line intensity vs Qz.

Synthetic data with a known number of counts in the fluorescence line per
frame (synth.make_xfntr_dataset), reduced through the MCA tab: select the
scans, select all spectra, sum over an energy window, export.
"""
import hashlib
import json
import os

import numpy as np
import pytest

import sweep
import synth

pytestmark = pytest.mark.gui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, 'tests', 'reference', 'legacy_export')
HASHES = os.path.join(ROOT, 'tests', 'reference', 'private_hashes.json')
BU = os.path.join(ROOT, 'sample_data', 'bu', '2026sep', '20260902')
UPDATE = bool(os.environ.get('LSS_UPDATE_GOLDEN'))

LIVE = synth.XF_REAL / synth.XF_LIVE          # real / live time
WINDOW = '5.6:7.2'                            # keV, +-6.7 sigma about 6.40


@pytest.fixture
def xf(window, qapp, tmp_path):
    spec, truth = synth.make_xfntr_dataset(tmp_path / 'xf')
    window.openSpecFile(fname=spec)
    window.directory = str(tmp_path)
    qapp.processEvents()
    sweep._select_scans(window, qapp, None)
    sweep._select_images(window, qapp, None)
    return window, truth


def _sum(w, qapp, window_text=WINDOW):
    w.ui.mcaRanLineEdit.setText(window_text)
    w.ui.mcaSumAllPushButton.click()
    qapp.processEvents()
    return np.array(w.mcaIntData)


def test_spectra_are_listed_and_normalised(xf, recorder):
    w, truth = xf
    assert recorder.exceptions == []
    assert w.ui.imageListWidget.count() == len(synth.XF_QZ)
    assert sorted(w.nomMcaData) == list(range(len(synth.XF_QZ)))
    energy, y, err = w.nomMcaData[0].T
    raw, _ = synth.xfntr_spectrum(synth.XF_QZ[0])
    assert energy == pytest.approx(0.02 * np.arange(1, synth.XF_CHANNELS + 1))
    # counts / monitor * (real / live)
    assert y == pytest.approx(raw / synth.XF_MONITOR * LIVE)
    # sigma^2 = (N + N^2/M) / M^2, times the same live-time factor
    assert err == pytest.approx(
        np.sqrt(raw + raw ** 2 / synth.XF_MONITOR) / synth.XF_MONITOR * LIVE)


def test_window_sum_recovers_known_line_counts(xf, qapp, recorder):
    """Known counts in, same counts (per monitor, live-time corrected) out."""
    w, truth = xf
    data = _sum(w, qapp)
    assert recorder.exceptions == []
    # selecting fluorescence scans is routine and must not produce a message
    assert recorder.messages == []
    frame, qz, energy, inten, err = data.T
    assert frame == pytest.approx(np.arange(1, len(synth.XF_QZ) + 1))
    assert qz == pytest.approx(synth.XF_QZ)
    assert energy == pytest.approx(10.0)
    lo, hi = 280, 360                         # channels inside 5.6..7.2 keV
    for i, n in enumerate(sorted(truth)):
        raw, line = synth.xfntr_spectrum(synth.XF_QZ[i])
        counts = raw[lo - 1:hi].sum()         # line + flat background of 2
        assert counts == line.sum() + 2 * (hi - lo + 1)
        assert inten[i] == pytest.approx(counts / synth.XF_MONITOR * LIVE)
        var = (raw[lo - 1:hi] + raw[lo - 1:hi] ** 2 / synth.XF_MONITOR).sum()
        assert err[i] == pytest.approx(np.sqrt(var) / synth.XF_MONITOR * LIVE)
    # shape of the curve follows the generating yield: peak at Qc
    assert qz[np.argmax(inten)] == synth.XF_QZ[np.argmax(synth.xfntr_yield(synth.XF_QZ))]


def test_error_is_larger_than_pure_poisson_of_the_sum_as_coded(xf, qapp):
    """Characterisation. Each channel carries N^2/M as monitor variance and
    the channels are then added in quadrature, as if the monitor error were
    independent per channel. For one frame all channels share one monitor
    reading, so the monitor term of the sum should be (sum N)^2/M. With the
    synthetic numbers the coded error is below the fully correlated one."""
    w, truth = xf
    data = _sum(w, qapp)
    raw, _ = synth.xfntr_spectrum(synth.XF_QZ[0])
    n = raw[279:360]
    coded = np.sqrt((n + n ** 2 / synth.XF_MONITOR).sum()) / synth.XF_MONITOR * LIVE
    correlated = np.sqrt(n.sum() + n.sum() ** 2 / synth.XF_MONITOR) / synth.XF_MONITOR * LIVE
    assert data[0, 4] == pytest.approx(coded)
    assert coded < correlated


def test_export_against_qz_is_byte_identical(xf, qapp, recorder, tmp_path):
    w, truth = xf
    _sum(w, qapp)
    w.ui.mcaXAxisComboBox.setCurrentIndex(1)          # x axis: Qz
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'out')
    w.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    with open(str(tmp_path / 'out_flu.txt'), 'rb') as f:
        produced = f.read()
    golden = os.path.join(GOLDEN, 'xfntr_flu.txt')
    if UPDATE:
        with open(golden, 'wb') as f:
            f.write(produced)
    with open(golden, 'rb') as f:
        assert produced == f.read()
    lines = produced.decode().splitlines()
    # first line records the operation; then Qz, intensity, error
    assert lines[0].startswith('#Flu Sum, scans=[')
    assert lines[0].endswith('], energy range=[5.6:7.2]')
    assert len(lines) == 1 + len(synth.XF_QZ)
    assert all(len(l.split('\t')) == 3 for l in lines[1:])
    got = np.loadtxt(str(tmp_path / 'out_flu.txt'))
    assert got[:, 0] == pytest.approx(synth.XF_QZ)
    assert got[:, 1] == pytest.approx(np.array(w.mcaIntData)[:, 3])


@pytest.mark.xfail(strict=True, reason='NumPy 2 prints scalars as '
                   '"np.int64(1)"; scan lists built with str([...]) of NumPy '
                   'integers now read that way in the export header, the '
                   'command line and plot titles')
def test_scan_numbers_are_written_as_plain_integers(xf, qapp, recorder,
                                                    tmp_path):
    w, truth = xf
    _sum(w, qapp)
    assert w.ui.commandLineEdit.text() == (
        'Flu Sum, scans=[1, 2, 3, 4, 5, 6, 7, 8, 9], energy range=[5.6:7.2]')


def test_merge_of_repeated_points_as_coded(xf, qapp, recorder):
    """Characterisation of "Merge": points closer than the resolution in x
    are combined with weights 1/sigma^2. As coded the combined value is
    sum(y^2/s^2) / sum(y/s^2), not the usual sum(y/s^2) / sum(1/s^2); the
    two agree only when the merged values are equal."""
    w, truth = xf
    data = _sum(w, qapp)
    w.ui.mcaXAxisComboBox.setCurrentIndex(1)
    w.ui.mcaMergePushButton.click()
    qapp.processEvents()
    w.uimcamerge.resLineEdit.setText('0.0031')         # pairs 3 mÅ^-1 apart merge
    w.uimcamerge.okPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    merged = np.array(w.mcaIntData)
    assert len(merged) < len(data)
    y1, s1, y2, s2 = data[0, 3], data[0, 4], data[1, 3], data[1, 4]
    a, b = y1 ** 2 / s1 ** 2 + y2 ** 2 / s2 ** 2, y1 / s1 ** 2 + y2 / s2 ** 2
    assert merged[0, 3] == pytest.approx(a / b)
    assert merged[0, 4] == pytest.approx(np.sqrt(a / b ** 2))
    usual = (y1 / s1 ** 2 + y2 / s2 ** 2) / (1 / s1 ** 2 + 1 / s2 ** 2)
    assert merged[0, 3] != pytest.approx(usual, rel=1e-3)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(BU), reason='private bu data not present')
def test_real_xfntr_export_matches_stored_hash(window, qapp, recorder, tmp_path):
    """Scans 74-79 of bu/2026sep/20260902. The data are private, so only a
    SHA-256 of the exported file is kept in the repository."""
    window.openSpecFile(fname=BU)
    window.directory = str(tmp_path)
    qapp.processEvents()
    lw = window.ui.scanListWidget
    rows = [i for i in range(lw.count())
            if lw.item(i).text().split()[1] in ('74', '75', '76', '77', '78', '79')]
    assert len(rows) == 6
    sweep._select_scans(window, qapp, rows)
    sweep._select_images(window, qapp, None)
    data = _sum(window, qapp, '1:1000')
    assert recorder.exceptions == [] and len(data) == 6
    window.ui.mcaXAxisComboBox.setCurrentIndex(1)
    recorder.save_name = str(tmp_path / 'out')
    window.ui.mcaExportIntPushButton.click()
    qapp.processEvents()
    with open(str(tmp_path / 'out_flu.txt'), 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    stored = {}
    if os.path.exists(HASHES):
        with open(HASHES) as f:
            stored = json.load(f)
    key = 'bu/2026sep/20260902 scans 74-79 _flu.txt (sum 1:1000, x = Qz)'
    if UPDATE:
        stored[key] = digest
        with open(HASHES, 'w') as f:
            json.dump(stored, f, indent=1, sort_keys=True)
            f.write('\n')
    assert stored.get(key) == digest


# ---- peak fitting of the fluorescence line (MCA "Fit") ---------------------

def _fit_one(w, qapp, row, guess=(6.3, 1e-2, 0.1)):
    sweep._select_images(w, qapp, [row])
    w.ui.mcaFitPushButton.click()
    qapp.processEvents()
    d = w.uipeakfit
    d.rangeLineEdit.setText(WINDOW)
    for j, v in enumerate(guess):
        d.peakTW.item(0, j).setText(str(v))
    qapp.processEvents()
    d.fitPushButton.click()
    qapp.processEvents()
    return d


def test_peak_fit_recovers_the_known_line(xf, qapp, recorder):
    """One Gaussian plus constant background fitted to one frame."""
    w, truth = xf
    recorder.messages.clear()
    d = _fit_one(w, qapp, 4)
    assert recorder.exceptions == [] and recorder.messages == []
    location, height, width = w.fitpeakpara[0]
    raw, line = synth.xfntr_spectrum(synth.XF_QZ[4])
    assert location == pytest.approx(0.02 * synth.XF_PEAK_CHANNEL, abs=1e-4)
    assert width == pytest.approx(0.02 * synth.XF_PEAK_SIGMA, rel=1e-3)
    assert height == pytest.approx(line.max() / synth.XF_MONITOR * LIVE, rel=1e-3)
    # flat background of 2 counts per channel
    assert w.fitbgpara[0] == pytest.approx(2 / synth.XF_MONITOR * LIVE, rel=0.05)
    assert float(d.chiLineEdit.text()) < 1.0      # noise-free synthetic data


def test_accepted_fit_intensity_is_height_times_width_as_coded(xf, qapp,
                                                              recorder):
    """Characterisation (PHYSICS_ISSUES P20). "Accept" stores
    height * sigma, i.e. the Gaussian area divided by sqrt(2 pi), with an
    error built from the two parameter errors without their covariance."""
    w, truth = xf
    _fit_one(w, qapp, 4)
    w.mcaIntData = []
    w.ui.mcaAcceptPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    frame, qz, energy, inten, err = w.mcaIntData[0]
    raw, line = synth.xfntr_spectrum(synth.XF_QZ[4])
    area = line.sum() / synth.XF_MONITOR * LIVE * 0.02      # keV * normalised
    assert inten == pytest.approx(area / np.sqrt(2 * np.pi), rel=2e-3)
    location, height, width = w.fitpeakpara[0]
    assert err == pytest.approx(np.sqrt(height ** 2 * w.fiterror[2] ** 2
                                        + width ** 2 * w.fiterror[1] ** 2))
    # as coded: the frame number and Qz stored are those of the first
    # selected spectrum
    assert (frame, qz) == (5, pytest.approx(synth.XF_QZ[4]))


def test_fit_all_gives_the_same_curve_shape_as_the_window_sum(xf, qapp,
                                                              recorder):
    """"Fit All" fits every selected frame with the parameters of the last
    fit as the start, and accepts each. Its intensity-vs-Qz curve must have
    the shape of the window-sum curve once the flat background is removed."""
    w, truth = xf
    _fit_one(w, qapp, 4)                       # leaves good starting values
    w.uipeakfit.close()
    sweep._select_images(w, qapp, None)
    w.ui.mcaFitAllPushButton.click()
    qapp.processEvents()
    w.uipeakfit.fitPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    fitted = np.array(w.mcaIntData)
    assert len(fitted) == len(synth.XF_QZ)
    assert fitted[:, 1] == pytest.approx(synth.XF_QZ)
    lines = np.array([synth.xfntr_spectrum(q)[1].sum() for q in synth.XF_QZ])
    assert fitted[:, 3] / fitted[:, 3].max() == pytest.approx(
        lines / lines.max(), rel=5e-3)
