"""Absorber setting of scans that record none (F50; owner, 2026-11-17).

getandsave_mca writes no #A line. The absorbers do not change during a
scan, so the reader takes the setting from the last #A above the scan in
the SPEC file and says which scan it came from (Par['AbsorberFrom']).
"""
import numpy as np

import synth
from spec_routines import specread


def _scan(num, absorber):
    x = np.linspace(-1, 1, 3)
    return synth.spec_scan(num, 'a', ['sh', 'Seconds', 'Monc', 'Apex2'],
                           np.column_stack([x, x * 0 + 1, x * 0 + 1e5, x * 0 + 10]),
                           command='ascan sh -1 1 2 1', image=False, absorber=absorber)


def _mca(num):
    return '#S %d  getandsave_mca 2\n#D Mon Sep 14 17:09:13 2026\n#V vortex data:./vortex/a_%d_mca\n\n' % (num, num)


def test_scan_without_a_takes_the_last_a_above_it(tmp_path):
    spec = synth.write_spec(str(tmp_path / 'a'),
                            [_mca(1), _scan(2, 52), _mca(3), _mca(4), _scan(5, 7), _mca(6)])
    p = specread(spec, data={}, par={}).Par
    assert 'Absorber' not in p[1]                  # no #A above it: unknown
    assert p[1]['Message'] == 'No parameters!!'
    assert (p[2]['Absorber'], 'AbsorberFrom' in p[2]) == (52, False)
    assert (p[3]['Absorber'], p[3]['AbsorberFrom']) == (52, 2)
    assert (p[4]['Absorber'], p[4]['AbsorberFrom']) == (52, 2)
    assert (p[5]['Absorber'], 'AbsorberFrom' in p[5]) == (7, False)
    assert (p[6]['Absorber'], p[6]['AbsorberFrom']) == (7, 5)


def test_refresh_of_a_growing_file_continues_from_the_last_a(tmp_path):
    """The window re-reads a growing file from the last scan on; the
    inference must not start again from nothing."""
    path = str(tmp_path / 'a')
    synth.write_spec(path, [_scan(1, 12), _mca(2)])
    r = specread(path, data={}, par={})
    data, par = r.Data, r.Par
    with open(path, 'a') as f:
        f.write(_mca(3))
    r2 = specread(path, startLineNum=r.endLineNum, endScanNum=data['NumOfScans'],
                  data=data, par=par)
    assert (r2.Par[2]['Absorber'], r2.Par[2]['AbsorberFrom']) == (12, 1)
    assert (r2.Par[3]['Absorber'], r2.Par[3]['AbsorberFrom']) == (12, 1)
