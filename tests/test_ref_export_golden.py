"""Byte-level fixtures of today's reflectivity export (_ref.txt, _rrf.txt).

Purpose: acceptance test 1 of docs/handoff/19-lss-reader-covariance-contract.md
("legacy byte identity"). The files in tests/reference/legacy_export/ were
written by the unmodified reduction code. After the covariance work, the
program must still be able to write these bytes, as ``_ref_legacy.txt`` /
``_rrf_legacy.txt``; set LEGACY_SUFFIX below to ``'_legacy'`` at that point.
The only change the hand-off permits is the Qz-squared aliasing fix (trap
T8), which affects the ``qz2`` case alone.

Regenerate (only for a deliberate, recorded change):

    LSS_UPDATE_GOLDEN=1 pytest tests/test_ref_export_golden.py -m "slow or not slow"
"""
import os

import numpy as np
import pytest

import sweep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, 'tests', 'reference', 'legacy_export')
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
LEGACY_SUFFIX = ''          # becomes '_legacy' once the two-chain export exists
UPDATE = bool(os.environ.get('LSS_UPDATE_GOLDEN'))

pytestmark = pytest.mark.gui


def reduce_and_save(w, qapp, recorder, out, scan_rows, drops=(), rrf=True,
                    qz2=False, norm=None, qoff=None):
    """Patch the given scans, apply display options, press Export.

    ``drops`` holds one text per join (as typed into the patch dialog's drop
    box, e.g. '0,-1'), '' for none. Returns the two file paths.
    """
    sweep._select_scans(w, qapp, scan_rows)
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    joins = len(scan_rows) - 1
    for j in range(joins):
        text = drops[j] if j < len(drops) else ''
        if text:
            w.uirefpatch.dropLineEdit.setText(text)
            w.uirefpatch.dropPushButton.click()
            qapp.processEvents()
        w.uirefpatch.nextPushButton.click()
        qapp.processEvents()
    assert w.ui.PlotWidget.currentIndex() == 3, 'patch did not finish'
    if qoff is not None:
        w.ui.refQoffLineEdit.setText(str(qoff))
        w.ui.refQoffLineEdit.returnPressed.emit()
    if norm is not None:
        w.ui.refNormLineEdit.setText(str(norm))
        w.ui.refNormFacCheckBox.setChecked(True)
    if rrf:
        w.ui.refRRFCheckBox.setChecked(True)
    if qz2:
        w.ui.refQzSqrCheckBox.setChecked(True)
    qapp.processEvents()
    recorder.save_name = out
    w.ui.refExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    return out + '_ref.txt', out + '_rrf.txt'


SYNTHETIC_CASES = {
    'plain': {},
    'drops': {'drops': ['-1']},
    'norm_factor': {'norm': 2.5},
    'qoff': {'qoff': 0.0005},
    'qz2': {'qz2': True},
    'no_rrf': {'rrf': False},
}


def _compare(case, kind, path):
    golden = os.path.join(GOLDEN, '%s_%s%s.txt' % (case, kind, LEGACY_SUFFIX))
    if not os.path.exists(path):
        produced = None
    else:
        with open(path, 'rb') as f:
            produced = f.read()
    if UPDATE:
        os.makedirs(GOLDEN, exist_ok=True)
        if produced is None:
            if os.path.exists(golden):
                os.remove(golden)
        else:
            with open(golden, 'wb') as f:
                f.write(produced)
        return
    if not os.path.exists(golden):
        assert produced is None, '%s %s: file written but none expected' % (case, kind)
        return
    with open(golden, 'rb') as f:
        expected = f.read()
    assert produced is not None, '%s %s: no file written' % (case, kind)
    if produced != expected:        # give a useful message before failing
        a, b = np.loadtxt(path), np.loadtxt(golden)
        detail = ('shapes %s vs %s' % (a.shape, b.shape) if a.shape != b.shape
                  else 'max relative difference %.3g'
                  % np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300)))
        pytest.fail('%s %s is not byte-identical to the fixture (%s)'
                    % (case, kind, detail))


@pytest.mark.parametrize('case', list(SYNTHETIC_CASES))
def test_synthetic_export_is_byte_identical(case, loaded, qapp, recorder,
                                            tmp_path):
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'),
                               [0, 1], **SYNTHETIC_CASES[case])
    _compare(case, 'ref', ref)
    _compare(case, 'rrf', rrf)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
@pytest.mark.parametrize('case,kw', [
    ('nx_scans_6-9', {}),
    ('nx_scans_6-9_drops', {'drops': ['0', '-1', '0,-1']}),
])
def test_real_export_is_byte_identical(case, kw, window, qapp, recorder,
                                       tmp_path):
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    qapp.processEvents()
    ref, rrf = reduce_and_save(window, qapp, recorder, str(tmp_path / 'out'),
                               [5, 6, 7, 8], **kw)
    _compare(case, 'ref', ref)
    _compare(case, 'rrf', rrf)


# ---- what the files contain today (format part of the xmodfit interface) --

def test_export_format(loaded, qapp, recorder, tmp_path):
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'),
                               [0, 1])
    for path in (ref, rrf):
        with open(path) as f:
            lines = f.read().splitlines()
        assert len(lines) == 14
        for line in lines:
            fields = line.split('\t')
            assert len(fields) == 3
            for field in fields:       # %.4e: d.dddde[+-]dd
                assert len(field) == 10 and field[1] == '.' and field[6] == 'e'
    a, b = np.loadtxt(ref), np.loadtxt(rrf)
    assert np.all(np.diff(a[:, 0]) > 0)
    assert a[:, 0] == pytest.approx(b[:, 0])           # Qoff is 0 by default
    assert np.all(a[:, 2] > 0) and np.all(b[:, 2] > 0)


def test_rrf_q_column_is_shifted_by_qoff(loaded, qapp, recorder, tmp_path):
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'),
                               [0, 1], qoff=0.0005)
    a, b = np.loadtxt(ref), np.loadtxt(rrf)
    assert b[:, 0] - a[:, 0] == pytest.approx(0.0005, abs=6e-7)


def test_norm_factor_divides_both_columns(loaded, qapp, recorder, tmp_path):
    """As coded: the typed factor is applied on top of the automatic
    normalisation to the plateau below Qc, to value and error alike."""
    ref1, _ = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'a'),
                              [0, 1])
    plain = np.loadtxt(ref1)
    loaded.ui.refNormLineEdit.setText('2.5')
    loaded.ui.refNormFacCheckBox.setChecked(True)
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'b')
    loaded.ui.refExportPushButton.click()
    qapp.processEvents()
    scaled = np.loadtxt(str(tmp_path / 'b_ref.txt'))
    assert scaled[:, 1] == pytest.approx(plain[:, 1] / 2.5, rel=2e-4)
    assert scaled[:, 2] == pytest.approx(plain[:, 2] / 2.5, rel=2e-4)


@pytest.mark.xfail(strict=True, reason='hand-off trap T8: with the Qz^2 box '
                   'checked the saved _rrf.txt holds q squared in its q column')
def test_qz2_display_option_does_not_change_saved_q(loaded, qapp, recorder,
                                                    tmp_path):
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'),
                               [0, 1], qz2=True)
    a, b = np.loadtxt(ref), np.loadtxt(rrf)
    assert b[:, 0] == pytest.approx(a[:, 0], rel=2e-4)


def test_qz2_corruption_as_coded(loaded, qapp, recorder, tmp_path):
    """Characterisation of trap T8 so the legacy fixture is understood:
    _ref.txt keeps q, _rrf.txt gets q squared."""
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'),
                               [0, 1], qz2=True)
    a, b = np.loadtxt(ref), np.loadtxt(rrf)
    assert b[:, 0] == pytest.approx(a[:, 0] ** 2, rel=3e-4)


def test_merge_scales_the_new_scan_in_place_as_coded(window):
    """Hand-off trap T3: oneDjoin(mtype='merge') writes the scaled values
    back into the array it was given, so joining the same scan twice scales
    it twice. Two reduction chains must each work on their own copies."""
    import synth
    q1, q2 = np.linspace(0.01, 0.05, 9), np.linspace(0.04, 0.10, 13)
    mk = lambda q, f: np.column_stack(
        [q, 250 * synth.reflectivity(q) / f, 0.25 * synth.reflectivity(q) / f])
    new = mk(q2, 1.42)
    before = new.copy()
    window.oneDjoin(mk(q1, 1.0), new, mtype='merge')
    assert new[:, 1] == pytest.approx(before[:, 1] * 1.42)
    assert not np.allclose(new[:, 2], before[:, 2])
