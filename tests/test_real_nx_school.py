"""Regression on real beamline data: sample_data/NX_school (DPPC monolayer).

Scans 6-9 are a four-part specular reflectivity measurement. The reference
file was produced by this program at the commit that introduced this test,
so it protects against unintended numerical change; it is not an independent
check of correctness. (extracted_data/dppc_ref.txt in the sample folder
covers a different Qz range and was not made from these scans.)

Takes about two minutes; run with ``pytest -m slow``.
"""
import os

import numpy as np
import pytest

import sweep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
REFERENCE = os.path.join(ROOT, 'tests', 'reference',
                         'nx_school_ref_scans_6-9.txt')

pytestmark = [pytest.mark.gui, pytest.mark.slow,
              pytest.mark.skipif(not os.path.exists(SPEC),
                                 reason='NX_school sample data not present')]


@pytest.fixture
def nx(window, qapp, tmp_path):
    window.openSpecFile(fname=SPEC)
    window.directory = str(tmp_path)     # keep temp_ref.txt out of the repo
    qapp.processEvents()
    return window


def test_spec_file_inventory(nx, recorder):
    assert recorder.exceptions == []
    assert nx.ui.scanListWidget.count() == 15
    assert [nx.specPar[i]['Detector'] for i in range(1, 16)] == \
        ['Monitor'] + ['Pilatus'] * 14
    p = nx.specPar[6]
    assert p['Wavelength'] == 1.23984
    assert p['DBPos'] == [53, 147]
    assert (p['S2D_Dist'], p['S7D_Dist']) == (551.0, 271.0)
    assert p['Absorber'] == 41
    assert p['g_l2'] == 1238.0


def test_every_scan_opens_and_shows_its_first_frame(nx, qapp, recorder):
    frames = {}
    for row in range(15):
        sweep._select_scans(nx, qapp, [row])
        n = nx.ui.imageListWidget.count()
        frames[row + 1] = n
        if n:
            sweep._select_images(nx, qapp, [0])
        assert recorder.exceptions == [], 'scan %d' % (row + 1)
    assert frames == {1: 0, 2: 2, 3: 11, 4: 15, 5: 21, 6: 19, 7: 27, 8: 21,
                      9: 29, 10: 21, 11: 41, 12: 4, 13: 21, 14: 21, 15: 21}


def test_reflectivity_scans_6_to_9_match_reference(nx, qapp, recorder):
    sweep._select_scans(nx, qapp, [5, 6, 7, 8])
    sweep._select_images(nx, qapp)
    assert len(nx.selectedPilFramesNums) == 96
    nx.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    assert nx.pilrefsort == [6, 7, 8, 9]
    for _ in range(3):                          # three overlaps to accept
        nx.uirefpatch.nextPushButton.click()
        qapp.processEvents()
    assert recorder.exceptions == []
    assert nx.ui.PlotWidget.currentIndex() == 3
    got = nx.normRefData
    ref = np.loadtxt(REFERENCE)
    assert got.shape == ref.shape == (87, 3)
    assert got[:, 0] == pytest.approx(ref[:, 0], rel=1e-9)
    assert got[:, 1] == pytest.approx(ref[:, 1], rel=1e-6)
    assert got[:, 2] == pytest.approx(ref[:, 2], rel=1e-6)
    # physical sanity: plateau near 1 below Qc, monotonic fall to the first
    # minimum of the lipid layer near 0.23 1/Angstrom
    assert got[0, 1] == pytest.approx(1.0, abs=0.02)
    window = (got[:, 0] > 0.15) & (got[:, 0] < 0.35)
    qmin = got[window][np.argmin(got[window, 1]), 0]
    assert 0.23 < qmin < 0.26


def _gid_patch(nx, qapp, rows):
    sweep._select_scans(nx, qapp, rows)
    sweep._select_images(nx, qapp)
    i = nx.ui.gidComboBox.findText('GID Patch')
    nx.ui.gidComboBox.setCurrentIndex(i)
    nx.ui.gidComboBox.activated.emit(i)
    qapp.processEvents()


def test_gid_scan_11_matches_reference(nx, qapp, recorder):
    """Scan 11 is the low-Qz half of a DPPC GID measurement (41 frames).

    Self-reference, as for the reflectivity test. The shipped
    extracted_data/dppc_*_gid.txt were made from a low + high Qz pair with
    more points and cannot be compared directly.
    """
    _gid_patch(nx, qapp, [10])
    assert recorder.exceptions == []
    assert recorder.messages == []
    assert nx.pilGIDData.shape == (472, 41)
    ref_h = np.loadtxt(os.path.join(ROOT, 'tests', 'reference',
                                    'nx_school_gid_scan_11_qxy.txt'))
    ref_v = np.loadtxt(os.path.join(ROOT, 'tests', 'reference',
                                    'nx_school_gid_scan_11_qz.txt'))
    assert nx.gid_h == pytest.approx(ref_h, rel=1e-6, abs=1e-9)
    assert nx.gid_v == pytest.approx(ref_v, rel=1e-6, abs=1e-9)
    # physical sanity: the DPPC chain peak lies in the scanned Qxy range
    qxy_peak = nx.gid_h[np.argmax(nx.gid_h[:, 1]), 0]
    assert 1.3 < qxy_peak < 1.55


def test_gid_low_and_high_qz_scans_can_be_patched(nx, qapp, recorder, tmp_path):
    """Scans 11 (low Qz, 41 frames) and 12 (high Qz, stopped after 4 frames)
    patched into one map and saved.

    The reference files were written by this program under Python 3.11 with
    SciPy 1.13.1 and NumPy 1.26.4, where scipy's interp2d still existed.
    The program now uses interp_compat.interp2d_linear instead, which must
    reproduce these files on any SciPy (defect 1, fixed 2026-11-17).
    """
    _gid_patch(nx, qapp, [10, 11])
    assert recorder.exceptions == []
    assert not [m for m in recorder.messages if 'patching' in m]
    assert nx.pilGIDData.shape == (833, 41)
    recorder.save_name = str(tmp_path / 'out')
    i = nx.ui.gidComboBox.findText('Save GID')
    nx.ui.gidComboBox.setCurrentIndex(i)
    nx.ui.gidComboBox.activated.emit(i)
    qapp.processEvents()
    assert recorder.exceptions == []
    for kind in ('qxy', 'qz'):
        got = np.loadtxt(str(tmp_path / ('out_%s_gid.txt' % kind)))
        ref = np.loadtxt(os.path.join(
            ROOT, 'tests', 'reference',
            'nx_school_gid_scans_11-12_scipy113_%s_gid.txt' % kind))
        assert got.shape == ref.shape
        assert got == pytest.approx(ref, rel=2e-4, abs=1e-6, nan_ok=True)


@pytest.mark.parametrize('index,text,name', [
    (0, '0.0:0.2', 'qz_0.0-0.2_vs_qxy'),     # Bragg peak profile along Qxy
    (1, '1.40:1.50', 'qxy_1.40-1.50_vs_qz'),  # Bragg rod along Qz
])
def test_gid_line_cuts_match_reference(index, text, name, nx, qapp, recorder):
    """Line cuts through the patched GID map of scan 11 (self-reference)."""
    _gid_patch(nx, qapp, [10])
    nx.ui.pilCutDirComboBox.setCurrentIndex(index)
    nx.ui.pilIntRangeLineEdit.setText(text)
    nx.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == [] and recorder.messages == []
    cut = np.array(nx.cutData)
    path = os.path.join(ROOT, 'tests', 'reference',
                        'nx_school_gid_scan_11_cut_%s.txt' % name)
    if os.environ.get('LSS_UPDATE_GOLDEN'):
        np.savetxt(path, cut)
    ref = np.loadtxt(path)
    assert cut == pytest.approx(ref, rel=1e-6, abs=1e-9, nan_ok=True)
    peak = cut[np.nanargmax(cut[:, 1]), 0]
    if index == 0:
        assert 1.44 < peak < 1.49           # DPPC chain peak in Qxy
    else:
        assert -0.01 < peak < 0.05          # rod maximum near the horizon


def test_gid_map_refuses_pixel_cuts_with_a_message(nx, qapp, recorder):
    _gid_patch(nx, qapp, [10])
    nx.ui.pilCutDirComboBox.setCurrentIndex(2)
    nx.ui.pilLineAreaPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert recorder.messages == ['Please use one of Q cuts for GID data']


def test_line_cuts_on_a_real_reflectivity_frame(nx, qapp, recorder):
    """Scan 7, first frame (Qz = 0.035). Pixel cuts are exact sums of the
    image. Two beams are on the frame: the reflected beam at the position
    recorded in the SPEC header, and, 2*alpha below it and much brighter at
    this reflectivity, the direct beam. The Q axis of the cut must put the
    reflected beam at the frame's Qz and the direct beam at Qz = 0."""
    sweep._select_scans(nx, qapp, [6])
    sweep._select_images(nx, qapp, [0])
    from lss_core.normalise import normalise_frame
    img, _ = normalise_frame(nx.pilData[0], nx.pilErrorData[0], nx.pilMonc[0],
                             nx.absfac, nx.pil_AbsNum[0])
    assert img.shape == (487, 195)

    def cut(index, text):
        nx.ui.pilCutDirComboBox.setCurrentIndex(index)
        nx.ui.pilIntRangeLineEdit.setText(text)
        nx.ui.pilLineAreaPushButton.click()
        qapp.processEvents()
        assert recorder.exceptions == [] and recorder.messages == []
        return np.array(nx.cutData[0])

    h = cut(2, '0:485')                      # sum over rows -> profile in x
    assert h[:, 1] == pytest.approx(img[0:487].sum(axis=0))
    v = cut(3, '0:193')                      # sum over columns -> profile in y
    assert v[:, 1] == pytest.approx(img[:, 0:195].sum(axis=1))
    # SPEC header #B1: beam at y = 53, x = 147 (x is mirrored on reading)
    col = int(h[np.argmax(h[:, 1]), 0])
    assert abs(col - (195 - 147 - 1)) <= 2
    qz_cut = cut(1, '-0.01:0.01')
    assert len(qz_cut) == 487
    one_pixel = qz_cut[54, 0] - qz_cut[53, 0]
    # direct beam: the global maximum, at Qz = 0 within about a pixel
    direct = np.argmax(qz_cut[:, 1])
    assert qz_cut[direct, 0] == pytest.approx(0.0, abs=1.5 * one_pixel)
    # reflected beam: local maximum near the recorded row, at the frame's Qz
    near = slice(53 - 8, 53 + 9)
    reflected = near.start + np.argmax(qz_cut[near, 1])
    assert qz_cut[reflected, 0] == pytest.approx(0.035, abs=1.5 * one_pixel)
    # their separation is 2*alpha: Qz = (4 pi / lambda) sin(alpha)
    alpha = np.arcsin(0.035 * 1.23984 / 4 / np.pi)
    assert (reflected - direct) * 0.172 / 551.0 == pytest.approx(2 * alpha, rel=0.08)
    qxy_cut = cut(0, '0.03:0.04')
    assert qxy_cut[np.argmax(qxy_cut[:, 1]), 0] == pytest.approx(0.0, abs=2e-3)


def test_gid_save_cancelled_writes_nothing(nx, qapp, recorder, tmp_path):
    _gid_patch(nx, qapp, [10])
    before = (set(os.listdir(ROOT)), set(os.listdir(str(tmp_path))))
    recorder.save_name = ''
    i = nx.ui.gidComboBox.findText('Save GID')
    nx.ui.gidComboBox.setCurrentIndex(i)
    nx.ui.gidComboBox.activated.emit(i)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert (set(os.listdir(ROOT)), set(os.listdir(str(tmp_path)))) == before
