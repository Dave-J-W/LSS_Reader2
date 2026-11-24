"""SPEC and MCA readers on synthetic files (see synth.py for the caveat)."""
import numpy as np
import pytest

import synth


@pytest.fixture
def spec(qapp, dataset):
    from spec_routines import specread
    return specread(dataset, data={}, par={})


def test_scan_inventory(spec):
    assert spec.Data['ScanNums'] == [1, 2, 3, 4]
    assert spec.Data['NumOfScans'] == 4
    assert spec.Data['Error'] is False
    assert spec.Data[1]['ScanLine'].startswith('#S 1 ')


def test_detector_classification(spec):
    assert [spec.Par[i]['Detector'] for i in (1, 2, 3, 4)] == \
        ['Pilatus', 'Pilatus', 'Vortex', 'Monitor']


def test_header_parameters(spec):
    p = spec.Par[2]
    assert p['Wavelength'] == synth.WAVELENGTH
    assert p['Absorber'] == 1
    assert (p['g_l1'], p['g_l2'], p['g_l3']) == (100.0, 200.0, 300.0)
    assert p['DBPos'] == [synth.DB_Y, synth.DB_X]
    assert (p['S2D_Dist'], p['S7D_Dist']) == (synth.S2D, synth.S7D)
    assert p['ImageNumber'] == 4
    for k, v in synth.MOTORS.items():
        assert p[k] == v
    assert p['Q'] == [0, 0, 0.04]


def test_data_columns(spec):
    d = spec.Data[1]
    assert d['ScanVar'] == synth.REF_COLUMNS
    assert d['L'] == pytest.approx(np.linspace(0.01, 0.05, 9))
    assert d['Monc'] == pytest.approx(np.full(9, synth.MONITOR))
    assert spec.Data[4]['ScanVar'] == ['sh', 'Seconds', 'Monc', 'Apex2']
    assert len(spec.Data[4]['Apex2']) == 21


def test_mca_scan_has_no_columns(spec):
    assert spec.Data[3]['ScanVar'] == 'Empty'


def test_not_a_spec_file(qapp, tmp_path):
    from spec_routines import specread
    p = tmp_path / 'junk'
    p.write_text('hello\nworld\n')
    s = specread(str(p), data={}, par={})
    assert s.Data['NumOfScans'] == 0
    assert 'not a valid specfile' in s.Data['Message']


def test_default_dicts_are_not_shared_between_readers(qapp, dataset):
    from spec_routines import specread
    a = specread(dataset)
    b = specread(dataset)
    assert a.Data is not b.Data


def test_mca_reader(tmp_path):
    from mca_routines import mcaread
    y1 = np.arange(40)
    y2 = np.arange(40) * 3
    path = synth.write_mca(str(tmp_path / 's_1_mca'), [y1, y2], monitor=5e4,
                           qz=0.03, energy=12.0)
    m = mcaread(path)
    assert m.Data['NumOfScans'] == 2
    assert m.Data[0]['Vortex'] == list(y1)
    assert m.Data[1]['Vortex'] == list(y2)
    assert m.Data[0]['Monc'] == 5e4
    assert m.Par[0]['Q'] == [0, 0, 0.03]
    assert m.Par[0]['Calib'] == [0.0, 0.01, 0.0]
    assert m.Par[0]['Time'] == [1.0, 1.0, 0.9]
    assert m.Par[0]['Energy'] == 12.0


@pytest.mark.gui
def test_repeated_scan_numbers_open_gracefully(window, qapp, recorder, tmp_path):
    """F27: a SPEC file in which a scan number occurs twice (SPEC was
    restarted and numbering began again) opens, says so once, lists each
    number once, and its image scans can still be selected."""
    import os
    import sweep
    root = tmp_path / 'dup'
    os.makedirs(str(root / 'pilatus'))
    rows = synth.ref_rows([0.02, 0.03])
    scans = [synth.spec_scan(1, 'dup', synth.REF_COLUMNS, rows),
             synth.spec_scan(2, 'dup', synth.REF_COLUMNS, rows),
             '#S 1  getandsave_mca 1\n#Q 0 0 0.02\n#W x 1.24\n#A x 0\n\n']
    spec = synth.write_spec(str(root / 'dup'), scans)
    for j in range(2):
        synth.write_pilatus_tif(str(root / 'pilatus' / ('dup_SCAN-2_%04d.tif' % j)),
                                synth.pilatus_image(peak=(97, 100)))
    window.openSpecFile(fname=spec)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert [m for m in recorder.messages if 'more than once' in m] == [
        'Scan number(s) 1 appear more than once in this SPEC file. '
        'The last scan with each number is shown.']
    assert window.ui.scanListWidget.count() == 2
    sweep._select_scans(window, qapp, [1])            # scan 2, a Pilatus scan
    sweep._select_images(window, qapp, [0])
    assert recorder.exceptions == []
    assert window.ui.imageListWidget.count() == 2
    assert 0 in window.pilData


def test_only_15idc_files_are_read(qapp, dataset, tmp_path):
    """9-ID-C support was removed (owner, 2026-11-17)."""
    from spec_routines import specread
    from mca_routines import mcaread
    with pytest.raises(ValueError, match='only APS-15IDC'):
        specread(dataset, beamline='APS-9IDC')
    path = synth.write_mca(str(tmp_path / 's_1_mca'), [np.arange(40)])
    with pytest.raises(ValueError, match='only APS-15IDC'):
        mcaread(path, beamline='APS-9IDC')


@pytest.mark.gui
def test_the_beamline_is_15idc_and_has_no_menu(window, recorder):
    """One beamline is supported (owner, 2026-11-17); the Beamlines menu,
    which offered nothing to choose, was removed (owner, 2026-11-23, Q14)."""
    assert window.beamline == 'APS-15IDC'
    titles = [a.text() for a in window.menuBar().actions()]
    assert 'Beamlines' not in titles and titles[0] == 'File'
    assert not hasattr(window.ui, 'actionAPS_15IDC') and not hasattr(window.ui, 'actionAPS_9IDC')
    assert recorder.exceptions == []
