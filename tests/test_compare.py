"""lss_core.compare (F80, F105): the saved reflectivities of a workbook,
ordered, and the ratio of two curves."""
import numpy as np
import pytest

from lss_core import compare, workbook


def _curve(scale=1.0, q=None):
    q = np.linspace(0.02, 0.3, 40) if q is None else q
    r = scale * (0.0217 / q) ** 4
    return np.column_stack([q, r, 0.02 * r])


def _book(tmp_path):
    wb = workbook.Workbook(str(tmp_path / 'b.xlsx'))
    a = wb.add_result('reflectivity', [6, 7, 8, 9], data=_curve(), columns=['Qz', 'R', 'dR'], label='R',
                      series={'id': 'S2', 'kind': 'reflectivity', 'scans': [6, 7, 8, 9], 'status': 'complete'})
    wb.add_result('reflectivity', [6, 7, 8, 9], data=_curve(), columns=['Qz', 'R/RF', 'd'], label='R/RF')
    b = wb.add_result('reflectivity', [16, 17], data=_curve(1.1), columns=['Qz', 'R', 'dR'], label='R',
                      series={'id': 'S1', 'kind': 'reflectivity', 'scans': [16, 17], 'status': 'complete'})
    wb.save()
    return workbook.Workbook(str(tmp_path / 'b.xlsx')), a, b


def test_entries_and_orders(tmp_path):
    wb, a, b = _book(tmp_path)
    got = compare.entries(wb, positions={6: 16.0, 16: 10.0})
    assert [e.rid for e in got] == [a, b] and [e.sx for e in got] == [16.0, 10.0]
    assert got[0].data.shape == (40, 3) and got[0].series == 'S2'
    assert [e.rid for e in compare.order(got, 'series')] == [b, a]          # S1 before S2
    assert [e.rid for e in compare.order(got, 'sx')] == [b, a]              # 10 mm before 16 mm
    assert [e.rid for e in compare.order(got, 'time')] == [a, b]
    assert len(compare.entries(wb, label='R/RF')) == 1
    assert got[0].title().startswith('%s v1  S# 6–9' % a)
    with pytest.raises(ValueError):
        compare.order(got, 'colour')


def test_the_ratio_of_two_curves():
    q, r, s = compare.ratio(_curve(), _curve(1.1))
    assert len(q) == 40 and r == pytest.approx(1.1, rel=1e-12)
    assert s == pytest.approx(1.1 * np.sqrt(2) * 0.02, rel=1e-9)            # relative errors in quadrature
    # another grid: log R against log Qz, so the Fresnel power law is followed exactly
    q2 = np.linspace(0.025, 0.25, 23)
    q, r, s = compare.ratio(_curve(), _curve(2.0, q2))
    assert q.min() >= 0.025 and q.max() <= 0.25 and r == pytest.approx(2.0, rel=1e-9)
    assert compare.ratio(_curve(q=np.linspace(0.02, 0.05, 5)), _curve(q=np.linspace(0.1, 0.2, 5)))[0].size == 0
