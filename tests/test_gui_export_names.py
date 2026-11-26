"""A name typed in an Export dialog with the export's own ending, or with
'.txt', is not given the ending twice ('run_flu.txt' does not become
'run_flu.txt_flu.txt'); the dialogs' captions say what each export adds,
and the GID and GISAXS exports no longer say "GIOXS" (release push,
2026-11-26: the export workflow first)."""
import os

import pytest

import sweep
import synth
from mainwindow import MainWindow

pytestmark = pytest.mark.gui


@pytest.mark.parametrize('name, endings, stem', [
    ('/d/run_flu.txt', ('_flu_xeray.txt', '_flu.txt'), '/d/run'),
    ('/d/run_flu_xeray.txt', ('_flu_xeray.txt', '_flu.txt'), '/d/run'),
    ('/d/run.txt', ('_flu.txt',), '/d/run'),
    ('/d/run', ('_flu.txt',), '/d/run'),
    ('/d/run_ref.txt', ('_ref.txt', '_rrf.txt'), '/d/run'),
    ('/d/run.dat', (), '/d/run.dat'),
])
def test_export_stem(name, endings, stem):
    assert MainWindow.exportStem(name, endings) == stem


def test_fluorescence_export_with_a_typed_ending(window, qapp, recorder, tmp_path):
    spec, truth = synth.make_xfntr_dataset(tmp_path / 'xf')
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    w.prefs['auto_save'] = False
    qapp.processEvents()
    sweep._select_scans(w, qapp, None)
    sweep._select_images(w, qapp, None)
    w.mcaFitLinesPushButton.click()
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'run_flu.txt')                 # typed with the ending
    w.mcaSaveIntData()
    names = sorted(n for n in os.listdir(str(tmp_path)) if n.startswith('run'))
    assert names == ['run_flu.txt', 'run_flu_xeray.txt']
    assert recorder.exceptions == []


def test_the_fit_exports_with_typed_endings(window, qapp, recorder, tmp_path):
    import numpy as np
    x = np.linspace(-1.0, 1.0, 41)
    y = 300.0 * np.exp(-x ** 2 / 2 / 0.2 ** 2) + 10.0
    f = tmp_path / 'peak.txt'
    np.savetxt(f, np.column_stack([x, y, np.sqrt(y)]))
    w = window
    w.directory = str(tmp_path)
    w.plotfiles = [str(f)]
    w.updatePlotFile()
    w.ui.plotFileListWidget.item(0).setSelected(True)
    qapp.processEvents()
    w.updateSelectedPlotFile()
    w.ui.plotPFPushButton.click()
    qapp.processEvents()
    d = w.uipeakfit
    d.rangeLineEdit.setText('-1:1')
    d.peakTW.selectAll()
    d.bgTW.selectAll()
    d.fitPushButton.click()
    qapp.processEvents()
    recorder.save_name = str(tmp_path / 'p_fit.txt')
    d.exportFitPushButton.click()
    recorder.save_name = str(tmp_path / 'p_par.txt')
    d.exportParaPushButton.click()
    qapp.processEvents()
    names = sorted(n for n in os.listdir(str(tmp_path)) if n.startswith('p_'))
    assert names == ['p_fit.txt', 'p_par.txt']
    assert recorder.exceptions == []


def test_no_export_caption_says_gioxs_except_gioxs():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mainwindow.py'),
               encoding='utf-8').read()
    assert src.count("caption='Export GIOXS data'") == 1                    # pilGioxsSave, the GIOXS export itself
    assert 'Export the GID map (the name gets' in src and 'Export the GISAXS map (the name gets' in src


def test_a_map_cut_is_written_to_the_name_as_typed(loaded, qapp, recorder, tmp_path):
    """A cut on a GID or GISAXS map is written to exactly the typed name (it
    adds no ending), so the typed '.txt' must stay."""
    import numpy as np
    w = loaded
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp)
    assert w.det == 'Pilatus'
    w.pilGIDshow, w.pilGISAXSshow = 1, 0
    w.cutData = np.array([[0.1, 1.0, 0.1], [0.2, 2.0, 0.2]])
    recorder.save_name = str(tmp_path / 'gidcut.txt')
    w.saveCutData()
    assert os.path.exists(str(tmp_path / 'gidcut.txt')) and not os.path.exists(str(tmp_path / 'gidcut'))
    assert recorder.exceptions == []
