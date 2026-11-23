"""A data line with fewer values than the others (the fragility audit,
2026-11-23, TODO area L row 1).

Before: numpy could not stack rows of unequal length, so one short line
(a file SPEC is still writing: live updates) made every column of its
scan None, and the scan read as empty. Now that line is left out, noted
in the scan's parameters ('DroppedRows': [(row index, values)]), and the
window says so once."""
import pytest

from lss_core.experiment import Experiment
from spec_routines import complete_rows


def _cut_last_line(path, keep=2):
    lines = open(path).read().rstrip('\n').split('\n')
    lines[-1] = ' '.join(lines[-1].split()[:keep])           # the writer stopped after `keep` numbers
    open(path, 'w').write('\n'.join(lines))                  # and before the end of the line


def test_complete_rows_keeps_the_usual_width():
    rows = [[1, 2, 3], [4, 5, 6], [7, 8]]
    assert complete_rows(rows) == ([[1, 2, 3], [4, 5, 6]], [(2, 2)])
    assert complete_rows([[1, 2, 3], [4]]) == ([[1, 2, 3]], [(1, 1)])   # a tie: the longer rows
    assert complete_rows([]) == ([], [])


def test_a_half_written_last_line_loses_only_itself(dataset):
    full = Experiment(dataset).scans[4]
    _cut_last_line(dataset)
    scan = Experiment(dataset).scans[4]
    assert sorted(scan.columns) == ['Apex2', 'Monc', 'Seconds', 'sh']                    # was: no columns
    assert len(scan.columns['sh']) == len(full.columns['sh']) - 1
    assert list(scan.columns['Apex2']) == list(full.columns['Apex2'][:-1])
    assert scan.parameters['DroppedRows'] == [(len(full.columns['sh']) - 1, 2)]
    assert 'DroppedRows' not in full.parameters


def test_a_blank_looking_line_inside_a_scan(dataset):
    """A line of spaces inside the data block (it is not the empty line that
    ends a scan) read as a row with no values: the same loss."""
    text = open(dataset).read()
    i = text.index('#S 4')
    j = text.index('\n', text.index('#L', i)) + 1
    j = text.index('\n', j) + 1                                           # after the first data row
    open(dataset, 'w').write(text[:j] + '   \n' + text[j:])
    scan = Experiment(dataset).scans[4]
    assert len(scan.columns['sh']) == 21
    assert scan.parameters['DroppedRows'] == [(1, 0)]


@pytest.mark.gui
def test_the_window_reads_the_scan_and_says_so(window, dataset, qapp, recorder):
    _cut_last_line(dataset)
    window.openSpecFile(fname=dataset)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert len(window.specData[4]['sh']) == 20
    said = [m for m in recorder.messages if 'left out' in m]
    assert len(said) == 1 and 'Scan(s) 4' in said[0]
