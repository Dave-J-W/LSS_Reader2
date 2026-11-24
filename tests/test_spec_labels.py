"""#L labels against the data rows' width (TODO area L, 2026-11-24).

Labels are split on spaces, which is right for these macros (NX writes
"PSD Seconds" with one space and its rows hold 18 values), but a label
with a space in it ("Two Theta") shifts every later column by one,
silently. The columns are still matched by position, as before; when the
counts differ the scan's parameters say so ('LabelMismatch': (labels,
values per row)) and the window says it once."""
import numpy as np

from lss_core.experiment import Experiment


def _relabel(path, scan, extra):
    lines = open(path).read().split('\n')
    s = [k for k, l in enumerate(lines) if l.startswith('#S %d ' % scan)][0]
    k = next(k for k in range(s, len(lines)) if lines[k].startswith('#L'))
    labels = lines[k][3:].split()
    lines[k] = '#L ' + '  '.join(labels[:1] + extra + labels[1:])
    open(path, 'w').write('\n'.join(lines))
    return labels


def test_matching_labels_say_nothing(dataset):
    for scan in Experiment(dataset).scans.values():
        assert 'LabelMismatch' not in scan.parameters


def test_a_label_with_a_space_is_noted_and_the_columns_stay(dataset):
    before = Experiment(dataset).scans[4]
    labels = _relabel(dataset, 4, ['Two', 'Theta'])          # "Two Theta" read as two labels: one too many
    scan = Experiment(dataset).scans[4]
    assert scan.parameters['LabelMismatch'] == (len(labels) + 2, len(labels))
    assert np.array_equal(scan.columns[labels[0]], before.columns[labels[0]])
    assert np.array_equal(scan.columns['Two'], before.columns[labels[1]])      # by position, as before


def test_the_window_says_it_once(window, dataset, qapp, recorder):
    _relabel(dataset, 4, ['Two', 'Theta'])
    window.openSpecFile(fname=dataset)
    window.directory = str(dataset) + '_out'
    qapp.processEvents()
    said = [m for m in recorder.messages if '#L names' in str(m)]
    assert len(said) == 1 and 'Scan(s) 4' in str(said[0])
    assert recorder.exceptions == []
