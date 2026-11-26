"""A one-point scan whose row is shorter than its #L (Local yokel's survey,
#79: KeyError 'monc' on one-point Det_Th scans of four private sets).

The SPEC reader keeps a column only when every row has a value for it, so a
single row shorter than #L (a half-written one-point scan, or a label with a
space) loses the later columns, Monc among them. Experiment.frames now says
which column is missing and why, instead of raising KeyError: 'monc'."""
import numpy as np
import pytest

import synth
from lss_core.experiment import Experiment

COLS = ['H', 'K', 'L', 'Seconds', 'Monc', 'Monp', 'Pilatus']


def _file(tmp_path):
    row = np.array([[0, 0, 0.05, 1, 1e5, 2e5, 1000]])
    full = synth.spec_scan(1, 'x', COLS, row, command='ascan Det_Th 5 5 0 1')
    short = synth.spec_scan(2, 'x', COLS, row, command='ascan Det_Th 5 5 0 1')
    lines = short.rstrip('\n').split('\n')
    lines[-1] = ' '.join(lines[-1].split()[:4])              # the one row holds 4 values for 7 labels
    return synth.write_spec(str(tmp_path / 'x'), [full, '\n'.join(lines) + '\n\n'])


def test_a_short_one_point_scan_says_what_is_missing(tmp_path):
    exp = Experiment(_file(tmp_path))
    assert exp.frames([1]) == []                              # a whole one-point scan: no image here, no error
    assert 'Monc' not in exp.scans[2].columns
    with pytest.raises(ValueError) as e:
        exp.frames([2])
    msg = str(e.value)
    assert 'scan 2 has no Monc column' in msg and '#L names 7 columns but its rows hold 4 values' in msg
    assert not isinstance(e.value, KeyError)
