"""The Ref Patch export's "+ covariance" option: the text files stay
byte-identical to the legacy fixtures, and the sidecars beside them load,
match their files point for point (hand-off 19 §2.3) and describe the patch
that was made (drops included)."""
import os

import numpy as np
import pytest

from lss_core import gls
from test_ref_export_golden import GOLDEN, NX, reduce_and_save

pytestmark = pytest.mark.gui


def _check(ref, rrf, case=None, rrf_written=True):
    for path in ((ref, rrf) if rrf_written else (ref,)):
        side = path[:-4] + '.cov.json'
        assert os.path.exists(side), side
        sc = gls.load(side)
        d = np.atleast_2d(np.loadtxt(path))
        assert not sc.match_problems(d[:, 0], d[:, 1])
        assert np.all(sc.sigma_meas > 0)
        t = sc.term('stitch')
        assert np.allclose(t.weights.sum(axis=1), 1.0)
        assert np.all(t.cov[0] == 0) and t.cov[-1, -1] > 0
        if case is not None:
            kind = 'ref' if path.endswith('_ref.txt') else 'rrf'
            with open(path, 'rb') as f, open(os.path.join(GOLDEN, '%s_%s.txt' % (case, kind)), 'rb') as g:
                assert f.read() == g.read(), 'the text file changed'


def test_option_is_off_by_default_and_writes_nothing(loaded, qapp, recorder, tmp_path):
    assert not loaded.refCovarianceCheckBox.isChecked()
    assert loaded.refCovarianceCheckBox.toolTip()
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'), [0, 1])
    assert not os.path.exists(ref[:-4] + '.cov.json') and not os.path.exists(rrf[:-4] + '.cov.json')


@pytest.mark.parametrize('case,kw', [('plain', {}), ('drops', {'drops': ['-1']}), ('qoff', {'qoff': 0.0005}),
                                     ('norm_factor', {'norm': 2.5}), ('qz2', {'qz2': True})])
def test_sidecars_beside_unchanged_files(case, kw, loaded, qapp, recorder, tmp_path):
    loaded.refCovarianceCheckBox.setChecked(True)
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'), [0, 1], **kw)
    assert recorder.exceptions == []
    _check(ref, rrf, case)
    assert any('Covariance written' in t for _, _, t in loaded.messages)


@pytest.mark.parametrize('kw', [{}, {'drops': ['-1']}, {'qoff': 0.0005, 'norm': 2.5}])
def test_default_joint_patch_gets_its_own_sidecar(kw, loaded, qapp, recorder, tmp_path):
    """The default patch (joint fit, since 2026-11-22): the replay follows
    the method used, so the sidecars match the files written (T10), and
    their Σ comes from the joint factors."""
    loaded.refCovarianceCheckBox.setChecked(True)
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'), [0, 1], method=None, **kw)
    assert recorder.exceptions == []
    assert loaded.refMethodUsed == 'joint'
    _check(ref, rrf)
    t = gls.load(ref[:-4] + '.cov.json').term('stitch')
    assert t.provenance['method'] == 'joint'
    assert any('Covariance written' in m for _, _, m in loaded.messages)


def test_no_rrf_sidecar_without_rrf(loaded, qapp, recorder, tmp_path):
    loaded.refCovarianceCheckBox.setChecked(True)
    ref, rrf = reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'out'), [0, 1], rrf=False)
    assert recorder.exceptions == []
    assert os.path.exists(ref[:-4] + '.cov.json')
    assert not os.path.exists(rrf[:-4] + '.cov.json')


def test_stale_patch_is_refused(loaded, qapp, recorder, tmp_path):
    """Hand-off T10: a sidecar is never written from another reduction's state."""
    loaded.refCovarianceCheckBox.setChecked(True)
    reduce_and_save(loaded, qapp, recorder, str(tmp_path / 'a'), [0, 1])
    loaded.refData = list(np.asarray(loaded.refData, float)[:-1])     # the patch on show is not the replayed one
    loaded.updateRefPlotData()
    recorder.save_name = str(tmp_path / 'b')
    loaded.ui.refExportPushButton.click()
    qapp.processEvents()
    assert recorder.exceptions == []
    assert not os.path.exists(str(tmp_path / 'b_ref.cov.json'))
    assert any('No covariance written' in t for _, _, t in loaded.messages)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
@pytest.mark.parametrize('case,kw', [('nx_scans_6-9', {}), ('nx_scans_6-9_drops', {'drops': ['0', '-1', '0,-1']}),
                                     (None, {'method': None})])
def test_real_sidecars(case, kw, window, qapp, recorder, tmp_path):
    window.openSpecFile(fname=NX)
    window.directory = str(tmp_path)
    qapp.processEvents()
    window.refCovarianceCheckBox.setChecked(True)
    ref, rrf = reduce_and_save(window, qapp, recorder, str(tmp_path / 'out'), [5, 6, 7, 8], **kw)
    _check(ref, rrf, case)
    sc = gls.load(ref[:-4] + '.cov.json')
    assert sc.term('stitch').labels == ['S6', 'S7', 'S8', 'S9']
