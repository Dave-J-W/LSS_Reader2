"""File names whatever the separator (lss_core.paths; TODO area L,
2026-11-24): the reader split paths on '/' or '\\' by hand and names on
'.', which gave a whole path as a plot legend on Linux and macOS and hid
the images of a SPEC file named with a dot."""
import os

import numpy as np
import pytest

import synth
from lss_core import paths
from spec_routines import specread


@pytest.mark.parametrize('path', ['/data/2026nov/run.v2', 'C:\\data\\2026nov\\run.v2', 'C:/data/2026nov/run.v2',
                                  'data\\2026nov/run.v2'])
def test_names_whatever_the_separator(path):
    assert paths.base(path) == 'run.v2'
    assert paths.parent(path) == '2026nov'
    assert paths.short(path) == '2026nov' + ('\\' if '\\' in path else '/') + 'run.v2'
    assert paths.stem(path) == 'run' and paths.ext(path) == '.v2'


def test_image_names():
    name = 'run.v2_SCAN-6_00001.TIF'
    assert paths.ext(name) == '.tif' and paths.stem(name).split('_')[-1] == '00001'
    assert paths.base('lone') == 'lone' and paths.parent('lone') == '' and paths.short('lone') == 'lone'


@pytest.mark.parametrize('name', ['sample', 'run.v2'])
def test_a_spec_name_with_a_dot_keeps_its_images(tmp_path, name):
    """Before: '#B0 run.v2_SCAN-1_0000.tif' split on '.' left the scan a
    'Monitor' scan (Main, reproduced 2026-11-24)."""
    spec = synth.make_dataset(str(tmp_path), name=name)
    sf = specread(spec)
    assert sf.Par[1]['Detector'] == 'Pilatus' and sf.Par[2]['Detector'] == 'Pilatus'
    assert sf.Par[1]['ImageNumber'] == 4


def test_a_windows_line_end_keeps_the_images(tmp_path):
    spec = synth.make_dataset(str(tmp_path))
    with open(spec, 'rb') as f:                       # LF first: on Windows text mode has written CRLF already,
        data = f.read().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')   # and doubling it gave CR CR LF
    with open(spec, 'wb') as f:
        f.write(data)
    assert specread(spec).Par[1]['Detector'] == 'Pilatus'


def test_plot_files_are_listed_and_labelled_by_name(window, qapp, recorder, tmp_path):
    """The plot tab's list shows '<folder>/<name>' and the legend '<name>',
    not the whole path (it did on Linux and macOS)."""
    d = tmp_path / 'curves'
    d.mkdir()
    f = d / 'film.v2_ref.txt'
    np.savetxt(f, np.column_stack([np.linspace(0.01, 0.1, 5), np.ones(5), 0.1 * np.ones(5)]))
    window.plotfiles = [str(f)]
    window.updatePlotFile()
    sep = '\\' if '\\' in str(f) else '/'                # paths.short keeps the path's own separator (Windows: '\\')
    assert window.ui.plotFileListWidget.item(0).text() == '#1' + window.halftab + 'curves' + sep + 'film.v2_ref.txt'
    window.ui.plotFileListWidget.item(0).setSelected(True)
    qapp.processEvents()
    window.updateSelectedPlotFile()
    ax = window.ui.PlotMplWidget.canvas.ax
    labels = [c.get_label() for c in ax.containers] + [l.get_label() for l in ax.get_lines()]
    assert '#1 film.v2_ref.txt' in labels, labels
    assert recorder.exceptions == []
