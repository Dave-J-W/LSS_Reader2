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


@pytest.mark.xfail(strict=True, reason='defect 1: joining the low and high '
                   'Qz scans calls scipy interp2d (removed); the error is '
                   'caught and shown as "not enough points"')
def test_gid_low_and_high_qz_scans_can_be_patched(nx, qapp, recorder):
    _gid_patch(nx, qapp, [10, 11])
    assert recorder.exceptions == []
    assert not [m for m in recorder.messages if 'patching' in m]
