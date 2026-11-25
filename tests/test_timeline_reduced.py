"""The timeline's reduced lane (F83 phase 1d, research §4): the workbook's
saved results at their scans' times, with placeholders for series not yet
reduced; Workbook.all_data reads every result's data in one pass."""
import os

import numpy as np
import pytest

from lss_core import timeline as T
from lss_core import workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
needs_nx = pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')


def _tl():
    spans = [T.ScanSpan(n, 'x', 100.0 * n, 100.0 * n + 80, 5, False, k)
             for n, k in ((1, 'reflectivity'), (2, 'reflectivity'), (3, 'gid'), (4, 'burn'), (5, 'other'))]
    return T.Timeline(spans=spans, series=[('s1', 'reflectivity', [1, 2]), ('s2', 'gid', [3]), ('s3', 'burn', [4]),
                                           ('s4', 'other', [5])])


def test_results_sit_at_their_scans_and_series_without_one_get_a_placeholder():
    rows = [dict(id='R0001', kind='reflectivity', label='R', version=1, scans='1,2', saved='t1'),
            dict(id='R0002', kind='reflectivity', label='R/RF', version=1, scans='1,2'),    # R/RF: not drawn twice
            dict(id='R0003', kind='reflectivity', label='R', version=2, scans='1,2', stale=True, note='hi'),
            dict(id='N0001', kind='note', label='x', version=1, scans='1'),               # notes have their own lane
            dict(id='G0001', kind='gid map', label='', version=1, scans='3,9')]           # scan 9: no time, ignored
    data = {'R0003': np.array([[0.01, 1.0], [0.02, 0.1]])}
    items = T.reduced_items(_tl(), rows, data)
    got = [(i.rid, i.kind, i.scans, i.placeholder) for i in items]
    assert got == [('R0003', 'reflectivity', [1, 2], ''), ('G0001', 'gid map', [3, 9], ''),
                   ('', 'burn', [4], 'not reduced')]                    # the latest version only; 'other' is not reducible
    r = items[0]
    assert (r.t0, r.t1, r.version, r.stale, r.note) == (100.0, 280.0, 2, True, 'hi')
    assert r.data is data['R0003'] and items[1].data is None


def test_all_data_is_data_for_every_result(tmp_path):
    wb = workbook.Workbook(str(tmp_path / 'w.xlsx'))
    a = wb.add_result('reflectivity', scans=[1], data=np.array([[1.0, 2.0, 0.1], [2.0, 3.0, 0.2]]),
                      columns=['Qz', 'R', 'dR'], label='R')
    b = wb.add_result('line cut', scans=[2], data=np.array([[5.0, np.nan], [6.0, 7.0], [8.0, 9.0]]),
                      columns=['x', 'y'], label='cut')
    c = wb.add_result('note', scans=[3], label='n')
    wb.save()
    wb = workbook.Workbook(str(tmp_path / 'w.xlsx'))
    every = wb.all_data()
    for rid in (a, b):
        assert np.array_equal(every[rid], wb.data(rid), equal_nan=True)
    assert c not in every and wb.data(c).shape == (0, 0)


@needs_nx
def test_nx_series_are_known_to_the_timeline():
    from lss_core.experiment import Experiment
    tl = T.build(Experiment(NX))
    assert [(k, s) for _i, k, s in tl.series] == [('reflectivity', [3]), ('reflectivity', [6, 7, 8, 9]),
                                                  ('gid', [11, 12]), ('burn', [14]), ('burn', [15])]
    assert [i.placeholder for i in T.reduced_items(tl, [])] == ['not reduced'] * 5
