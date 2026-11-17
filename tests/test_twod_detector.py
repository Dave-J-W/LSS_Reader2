"""TwoDDetector: image reading, normalisation, ROI sums and line cuts."""
import numpy as np
import pytest

import synth
from TwoDDetector import TwoDDetector


@pytest.fixture
def det():
    return TwoDDetector('Pilatus')


def test_tif_round_trip(det, tmp_path):
    rng = np.random.default_rng(0)
    a = rng.integers(0, 50, size=(synth.PIL_W, synth.PIL_H))
    path = synth.write_pilatus_tif(str(tmp_path / 'a.tif'), a)
    det.openFile(path)
    assert (det.NROWS, det.NCOLS) == (synth.PIL_W, synth.PIL_H)
    assert np.array_equal(det.imageData, a)
    assert np.array_equal(det.errorData, np.sqrt(a))
    assert det.hroi == [0, synth.PIL_H - 1]
    assert det.vroi == [0, synth.PIL_W - 1]


def test_missing_file_returns_minus_one(det, tmp_path):
    assert det.openFile(str(tmp_path / 'nope.tif')) == -1


def test_bad_pixel_correction_leaves_flat_image_alone(det):
    flat = np.full((40, 30), 7.0)
    out, bad = det.removeBadPix(flat, iteration=1)
    assert np.array_equal(out, flat)
    assert len(bad) == 0


def test_bad_pixel_correction_replaces_hot_pixel(det):
    img = np.full((40, 30), 7.0)
    img[20, 15] = 1.0e5
    out, bad = det.removeBadPix(img, iteration=1)
    assert out[20, 15] == pytest.approx(7.0)
    assert [list(b) for b in bad] == [[20, 15]]
    img[20, 15] = 7.0
    assert np.array_equal(out, img)


def test_sum_files_normalisation_and_error(det):
    det.NROWS, det.NCOLS = 4, 3
    absfac = 1.42
    data = {0: np.full((4, 3), 100.0), 1: np.full((4, 3), 400.0)}
    err = {k: np.sqrt(v) for k, v in data.items()}
    mon, absnum = [1000.0, 2000.0], [0, 2]
    det.sumFiles(data, err, absfac=absfac, absnum=absnum, mon=mon)
    norm = [100.0 / 1000.0, 400.0 * absfac ** 2 / 2000.0]
    assert det.imageData == pytest.approx(np.full((4, 3), np.mean(norm)))
    # per frame: sigma^2 = (sigma_I^2/M^2 + I^2/M^3) * absfac^(2 n)
    var = [(100.0 / 1000.0 ** 2 + 100.0 ** 2 / 1000.0 ** 3),
           (400.0 / 2000.0 ** 2 + 400.0 ** 2 / 2000.0 ** 3) * absfac ** 4]
    assert det.errorData == pytest.approx(np.full((4, 3), np.sqrt(sum(var)) / 2))


def test_poisson_relative_error_identity(det):
    # for Poisson counts I and monitor M: (sigma/R)^2 = 1/I + 1/M
    det.NROWS, det.NCOLS = 1, 1
    counts, mon = 2500.0, 4.0e4
    det.sumFiles({0: np.array([[counts]])}, {0: np.array([[np.sqrt(counts)]])},
                 absfac=1, absnum=[0], mon=[mon])
    rel2 = (det.errorData / det.imageData) ** 2
    assert rel2[0, 0] == pytest.approx(1 / counts + 1 / mon)


def test_sum_files_without_monitor_is_pass_through(det):
    a, e = np.ones((2, 2)), np.ones((2, 2)) * 3
    det.sumFiles(a, e)
    assert det.imageData is a and det.errorData is e


@pytest.mark.parametrize('direction', ['H', 'V'])
def test_roi_signal_minus_background_is_zero_on_flat_image(det, direction):
    det.imageData = np.full((200, 150), 5.0)
    det.errorData = np.sqrt(det.imageData)
    sig, sigerr, b1, b1err, b2, b2err = det.sumROI(
        slit=[11, 21], cen=[75, 100], bg=2.0, dir=direction)
    assert sig - (b1 + b2) / 2 == 0
    assert sigerr == pytest.approx(np.sqrt(sig))
    assert b1err == pytest.approx(sigerr) and b2err == pytest.approx(sigerr)


def test_roi_size_as_coded(det):
    # sumROI shrinks each slit dimension by 2 before summing; with slit
    # [11, 21] the summed box is 11 columns by 21 rows.
    det.imageData = np.ones((200, 150))
    det.errorData = np.ones((200, 150))
    sig, sigerr = det.sumROI(slit=[11, 21], cen=[75, 100])
    assert sig == 11 * 21
    assert sigerr == pytest.approx(np.sqrt(11 * 21))


def test_roi_picks_up_peak_only_in_signal_box(det):
    img = synth.pilatus_image(peak=(97, 100), background=0.0, amplitude=1000.0)
    det.imageData, det.errorData = img, np.sqrt(img)
    sig, _, lb, _, rb, _ = det.sumROI(slit=[11, 21], cen=[97, 100], bg=3.0,
                                      dir='H')
    assert lb == 0 and rb == 0
    assert sig == pytest.approx(img.sum(), rel=0.02)


def test_peak_locate_finds_shifted_peak(det):
    img = synth.pilatus_image(peak=(99, 102), background=0.0)
    assert det.peakLocate(img, np.sqrt(img), cen=[97, 100], mon=1.0) == (99, 102)


def test_peak_locate_normalises_by_monitor(det):
    img = synth.pilatus_image(peak=(97, 100))
    mon = 250.0
    det.peakLocate(img, np.sqrt(img), cen=[97, 100], mon=mon)
    assert det.imageData == pytest.approx(img / mon)
    assert det.errorData == pytest.approx(np.sqrt(img / mon ** 2 + img ** 2 / mon ** 3))


def _cut_args():
    lam, dist = synth.WAVELENGTH, synth.S2D
    alpha = np.arcsin(0.05 * lam / 4 / np.pi)
    return dict(wavelength=lam, s2d_dist=dist, alpha=alpha, truealpha=alpha)


def test_hint_sums_columns_and_propagates_errors(det):
    det.NROWS, det.NCOLS = 60, 40
    img = np.arange(60 * 40, dtype=float).reshape(60, 40)
    det.plotHint(img, np.sqrt(img), hroi=[10, 19], vroi=[5, 54])
    y, s, e = det.hintData.T
    assert np.array_equal(y, np.arange(5, 55))
    assert s == pytest.approx(img[5:55, 10:20].sum(axis=1))
    assert e == pytest.approx(np.sqrt(img[5:55, 10:20].sum(axis=1)))


def test_hint_q_axis_gives_specular_qz_at_beam_centre(det):
    # at the direct-beam row with alpha = alpha_true the exit angle is alpha,
    # so Qz = 4 pi sin(alpha) / lambda
    det.NROWS, det.NCOLS = 201, 40
    img = np.ones((201, 40))
    kw = _cut_args()
    det.plotHint(img, img, hroi=[0, 39], vroi=[0, 200], cen=[20, 100],
                 ax_type='Q', **kw)
    qz = det.hintData[:, 0]
    assert qz[100] == pytest.approx(0.05)
    assert np.all(np.diff(qz) > 0)


def test_hint_angle_axis_is_arctan_of_pixel_offset(det):
    det.NROWS, det.NCOLS = 201, 40
    img = np.ones((201, 40))
    kw = _cut_args()
    det.plotHint(img, img, hroi=[0, 39], vroi=[0, 200], cen=[20, 100],
                 ax_type='Angles', **kw)
    beta = np.deg2rad(det.hintData[:, 0])
    expect = np.arctan((np.arange(201) - 100) * 0.172 / synth.S2D) + kw['alpha']
    assert beta == pytest.approx(expect)


def test_vint_q_axis_is_zero_at_beam_centre_for_zero_dth(det):
    det.NROWS, det.NCOLS = 60, 101
    img = np.ones((60, 101))
    det.plotVint(img, img, hroi=[0, 100], vroi=[0, 59], cen=[50, 30],
                 dth=0.0, wavelength=synth.WAVELENGTH, s2d_dist=synth.S2D,
                 ax_type='Q')
    qxy, s, e = det.vintData.T
    assert qxy[50] == pytest.approx(0.0, abs=1e-12)
    assert qxy == pytest.approx(-qxy[::-1])
    assert s == pytest.approx(np.full(101, 60.0))
    two_theta = np.arctan(50 * 0.172 / synth.S2D)
    assert qxy[100] == pytest.approx(4 * np.pi * np.sin(two_theta / 2) / synth.WAVELENGTH)


def test_gaussian_peak_fit_recovers_parameters(det):
    det.NROWS, det.NCOLS = synth.PIL_W, synth.PIL_H
    img = synth.pilatus_image(peak=(98, 101), background=3.0, amplitude=800.0,
                              sigma=2.5)
    par = det.peakFind(img, np.sqrt(img), slit=[21, 21], cen=[97, 100], fac=1)
    amp, xc, sx, yc, sy, bg = par
    assert (xc, yc) == pytest.approx((98, 101), abs=0.05)
    assert (abs(sx), abs(sy)) == pytest.approx((2.5, 2.5), rel=0.03)
    assert amp == pytest.approx(800.0, rel=0.03)
    assert bg == pytest.approx(3.0, abs=1.0)


@pytest.mark.parametrize('direction', ['H', 'V'])
def test_roi_errors_add_in_quadrature(det, direction):
    """Invariant I4: each box error is the root-sum-square of its pixels,
    so the background-subtracted signal S - (L+R)/2 has
    sigma^2 = sigma_S^2 + (sigma_L^2 + sigma_R^2)/4."""
    rng = np.random.default_rng(1)
    det.imageData = rng.uniform(1, 9, size=(200, 150))
    det.errorData = rng.uniform(0.5, 2, size=(200, 150))
    slit, cen, bg = [11, 21], [75, 100], 2.0
    sig, sigerr, b1, b1err, b2, b2err = det.sumROI(slit=slit, cen=cen, bg=bg,
                                                   dir=direction)
    half_x, half_y = (slit[0] - 2 + 1) // 2, (slit[1] - 2 + 1) // 2
    rows = slice(cen[1] - half_y, cen[1] + half_y + 1)
    cols = slice(cen[0] - half_x, cen[0] + half_x + 1)
    assert sig == pytest.approx(det.imageData[rows, cols].sum())
    assert sigerr == pytest.approx(np.sqrt((det.errorData[rows, cols] ** 2).sum()))
    if direction == 'H':
        shift = int(bg * (slit[0] - 2))
        boxes = [(rows, slice(cols.start - shift, cols.stop - shift)),
                 (rows, slice(cols.start + shift, cols.stop + shift))]
    else:
        shift = int(bg * (slit[1] - 2))
        boxes = [(slice(rows.start + shift, rows.stop + shift), cols),
                 (slice(rows.start - shift, rows.stop - shift), cols)]
    for (r, c), val, err in zip(boxes, (b1, b2), (b1err, b2err)):
        assert val == pytest.approx(det.imageData[r, c].sum())
        assert err == pytest.approx(np.sqrt((det.errorData[r, c] ** 2).sum()))


def test_roi_error_treats_monitor_noise_as_independent_per_pixel_as_coded(det):
    """Characterisation, and a question for the owner (physics_notes.md).

    Each pixel gets sigma^2 = I/M^2 + I^2/M^3 and a region of interest adds
    its pixels in quadrature. All pixels of one frame share one monitor
    reading, so the monitor part of a sum S = sum(I) should be S^2/M^3, not
    sum(I^2)/M^3. The coded error is smaller; the gap grows with the number
    of pixels and with S/M.
    """
    det.NROWS, det.NCOLS = 200, 150
    counts, mon = 400.0, 1.0e5
    raw = np.full((200, 150), counts)
    det.sumFiles({0: raw}, {0: np.sqrt(raw)}, absfac=1, absnum=[0], mon=[mon])
    sig, sigerr = det.sumROI(slit=[11, 21], cen=[75, 100])
    n = 11 * 21
    total = n * counts
    assert sig == pytest.approx(total / mon)
    coded = np.sqrt(n * (counts / mon ** 2 + counts ** 2 / mon ** 3))
    shared_monitor = np.sqrt(total / mon ** 2 + total ** 2 / mon ** 3)
    assert sigerr == pytest.approx(coded)
    assert shared_monitor / coded == pytest.approx(1.385, abs=1e-3)


def test_bad_pixel_factor_reaches_the_reader(det, tmp_path):
    """Defect 14 (fixed): the factor set in the window is passed to the
    reader. A pixel 5 times its neighbours is replaced at factor 1 (the
    threshold is 4 times the neighbour mean) and kept at factor 2."""
    img = np.full((synth.PIL_W, synth.PIL_H), 100)
    img[200, 80] = 500
    path = synth.write_pilatus_tif(str(tmp_path / 'hot.tif'), img)
    det.openFile(path, bad_pix=1, bad_fac=1)
    assert det.imageData[200, 80] == 100
    assert [list(b) for b in det.imbadPix] == [[200, 80]]
    det.openFile(path, bad_pix=1, bad_fac=2)
    assert det.imageData[200, 80] == 500
    assert len(det.imbadPix) == 0
    det.openFile(path, bad_pix=0)                  # the default: no correction
    assert det.imageData[200, 80] == 500
