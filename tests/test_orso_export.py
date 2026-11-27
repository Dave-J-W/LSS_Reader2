"""ORSO export (F25, issue #148; the owner, 2026-11-27): Reflectivity Export
writes <name>.ort when "+ ORSO" is ticked, ticked by default; columns Qz, R,
sR and sQz (sQz only when the reduction records a resolution); the owner's
name and affiliation from Preferences, the sample's from the series macro.
The file is read back with orsopy, the format's reference implementation."""
import datetime
import os

import numpy as np
import pytest

from lss_core import orso

orsopy = pytest.importorskip('orsopy')
from orsopy import fileio as fo  # noqa: E402


def _curve(n=20, dq=False):
    q = np.linspace(0.01, 0.5, n)
    cols = [q, np.logspace(0, -8, n), np.logspace(-2, -9, n)]
    if dq:
        cols.append(np.full(n, 4e-4))
    return np.column_stack(cols)


def test_written_and_read_back(tmp_path):
    p = orso.write_ort(str(tmp_path / 'x.ort'), _curve(), '/data/20260923', [6, 7], 1.23984,
                       start_date=datetime.datetime(2026, 9, 23, 10, 40, 31), owner_name='A B',
                       owner_affiliation='Uni', sample_name='dppc', corrections=['frames normalised by the monitor'],
                       call='ref = exp.reflectivity([6, 7])', version='2.0')
    ds = fo.load_orso(p)
    assert len(ds) == 1 and ds[0].data.shape == (20, 3)
    info = ds[0].info
    assert [c.name for c in info.columns[:2]] == ['Qz', 'R'] and info.columns[2].error_of == 'R'
    assert info.data_source.sample.name == 'dppc' and info.data_source.owner.name == 'A B'
    assert info.data_source.experiment.probe == 'x-ray'
    assert info.data_source.measurement.data_files[0].file == '20260923'
    a = info.data_source.measurement.instrument_settings.incident_angle
    assert a.min == pytest.approx(np.degrees(np.arcsin(0.01 * 1.23984 / (4 * np.pi))), rel=1e-5)
    assert info.reduction.call == 'ref = exp.reflectivity([6, 7])' and info.reduction.software.version == '2.0'
    assert 'No Qz resolution' in (info.comment or '')
    assert np.allclose(ds[0].data, _curve())


def test_sqz_when_the_reduction_has_it(tmp_path):
    ds = fo.load_orso(orso.write_ort(str(tmp_path / 'y.ort'), _curve(dq=True), 'f', [1], 1.24))
    c = ds[0].info.columns[3]
    assert ds[0].data.shape == (20, 4) and c.error_of == 'Qz' and c.error_type == 'resolution'
    with pytest.raises(ValueError):
        orso.write_ort(str(tmp_path / 'z.ort'), np.ones((3, 2)), 'f', [1], 1.24)


@pytest.mark.gui
def test_the_window_writes_it_by_default(loaded, qapp, recorder, tmp_path):
    import sweep
    w = loaded
    w.directory = str(tmp_path)
    w.prefs['auto_save'] = False
    w.setPreference('orso_owner_name', 'A B')
    w.setPreference('orso_owner_affiliation', 'Uni')
    sweep._select_scans(w, qapp, [0, 1])
    sweep._select_images(w, qapp)
    w.ui.pilRefPatchPushButton.click()
    qapp.processEvents()
    w.uirefpatch.nextPushButton.click()
    qapp.processEvents()
    assert w.refOrsoCheckBox.isChecked()                                # on by default (owner)
    recorder.save_name = str(tmp_path / 'run')
    w.ui.refExportPushButton.click()
    qapp.processEvents()
    ds = fo.load_orso(str(tmp_path / 'run.ort'))
    ref = np.loadtxt(str(tmp_path / 'run_ref.txt'))
    assert np.allclose(ds[0].data[:, :3], ref, rtol=1e-3)               # the same curve as _ref.txt
    info = ds[0].info
    assert info.data_source.owner.name == 'A B' and info.data_source.owner.affiliation == 'Uni'
    assert info.reduction.call.startswith('ref = exp.reflectivity(') and info.reduction.corrections
    assert any('run.ort' in m for m in recorder.messages if m.startswith('Exported'))
    w.refOrsoCheckBox.setChecked(False)                                 # off: no .ort
    recorder.save_name = str(tmp_path / 'plain')
    w.ui.refExportPushButton.click()
    qapp.processEvents()
    assert not os.path.exists(str(tmp_path / 'plain.ort')) and w.prefs['export_orso'] is False
    assert recorder.exceptions == []
