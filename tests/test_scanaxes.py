"""SpecPlot's default x axis (lss_core.scanaxes; TODO area L, 2026-11-24).
An hklscan used to be plotted against L whatever moved, so a scan along H
or K was drawn against a constant."""
import numpy as np

import sweep
from lss_core import scanaxes

HKL = ['H', 'K', 'L', 'Epoch', 'Monc', 'Det']


def test_the_command_decides():
    assert scanaxes.default_x(HKL, None, '#S 6  hklscan  0 0  0 0  0.0175 0.04  18 2') == 2
    assert scanaxes.default_x(HKL, None, 'hklscan 0.1 0.5 0 0 0.02 0.02 20 1') == 0
    assert scanaxes.default_x(HKL, None, 'hklscan 0 0 -0.2 0.2 0.02 0.03 20 1') == 1   # the larger move


def test_else_the_column_that_varies():
    cols = {'H': np.zeros(5), 'K': np.linspace(0, 1, 5), 'L': np.full(5, 0.02)}
    assert scanaxes.default_x(HKL, cols, 'ascan th 0 1 4 1') == 1
    assert scanaxes.default_x(HKL, {'H': np.zeros(3), 'K': np.zeros(3), 'L': np.zeros(3)}) == 2   # nothing moves: L
    assert scanaxes.default_x(HKL) == 2


def test_other_scans_keep_their_first_column():
    assert scanaxes.default_x(['dth', 'Epoch', 'Det'], None, 'ascan dth 14 18 40 7') == 0


def test_the_window_plots_an_h_scan_against_h(window, dataset, qapp, recorder):
    lines = open(dataset).read().split('\n')
    k = [i for i, l in enumerate(lines) if l.startswith('#S 1 ')][0]
    lines[k] = '#S 1  hklscan 0.01 0.1 0 0 0.02 0.02 5 1'       # along H
    open(dataset, 'w').write('\n'.join(lines))
    sweep.state_spec_loaded(window, qapp, dataset)
    sweep._select_scans(window, qapp, [0])
    assert window.ui.spXComboBox.currentText() == 'H'
    sweep._select_scans(window, qapp, [1])                         # along L, as before
    assert window.ui.spXComboBox.currentText() == window.specData[2]['ScanVar'][2] == 'L'
    assert recorder.exceptions == []
