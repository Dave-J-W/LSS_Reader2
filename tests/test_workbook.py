"""The per-SPEC workbook (owner, 2026-11-21): settings, saved results and
fits in one Excel file with 4–8 sheets, tied to scans, sortable, versioned."""
import math

import numpy as np
import pytest

from lss_core import peaks, workbook


def _peak_cut():
    x = np.linspace(1.3, 1.6, 121)
    y = 10 + 200 * np.exp(-0.5 * ((x - 1.466) / (0.016 / (2 * math.sqrt(2 * math.log(2))))) ** 2)
    return np.column_stack([x, y, np.sqrt(y)])


def test_sheets_and_headers(tmp_path):
    wb = workbook.Workbook(str(tmp_path / 'f_reader.xlsx'))
    wb.save()
    import openpyxl
    book = openpyxl.load_workbook(tmp_path / 'f_reader.xlsx')
    assert book.sheetnames == list(workbook.SHEETS) and 4 <= len(book.sheetnames) < 8
    for name in workbook.SHEETS:
        ws = book[name]
        assert [c.value for c in ws[1]] == workbook.HEADERS[name] and ws.freeze_panes == 'A2'


def test_results_are_tied_to_scans_versioned_and_read_back(tmp_path):
    p = str(tmp_path / 'f_reader.xlsx')
    wb = workbook.Workbook(p)
    cut = _peak_cut()
    fit = peaks.fit(cut[:, 0], cut[:, 1], cut[:, 2])
    r1 = wb.add_result('line cut', [11], cut, ['Qxy', 'I', 'dI'], label='S# 11 F# 20', note='first look',
                       settings={'direction': 'Q H'}, fits=[('S# 11 F# 20', fit)], program='test')
    r2 = wb.add_result('line cut', [11], cut * [1, 2, 2], ['Qxy', 'I', 'dI'], label='S# 11 F# 20', program='test')
    r3 = wb.add_result('reflectivity', [6, 7, 8, 9], cut, ['Qz', 'R', 'dR'], program='test')
    wb.save()
    wb = workbook.Workbook(p)                                   # read back from the file
    assert [r['id'] for r in wb.results()] == [r1, r2, r3] == ['R0001', 'R0002', 'R0003']
    assert [r['version'] for r in wb.results(kind='line cut')] == [1, 2]
    assert wb.results(scan=8)[0]['kind'] == 'reflectivity' and wb.results(scan=8)[0]['first_scan'] == 6
    assert wb.results(kind='line cut')[0]['note'] == 'first look'
    assert wb.data(r2) == pytest.approx(cut * [1, 2, 2])
    f = wb.fits(rid=r1)
    assert len(f) == 1 and f[0]['centre'] == pytest.approx(1.466, abs=1e-3) and f[0]['scans'] == '11'
    assert wb.fits(scan=11) == f


def test_settings_sections_replace_and_round_trip(tmp_path):
    p = str(tmp_path / 'f_reader.xlsx')
    wb = workbook.Workbook(p)
    o = peaks.FitOptions(shape='pseudo-voigt', centres=(6.4, 7.06), x_range=(5.0, 8.0))
    wb.set_settings('peak_fit', peaks.options_to_dict(o))
    wb.set_settings('peak_fit', peaks.options_to_dict(o))          # replaced, not doubled
    wb.save()
    back = workbook.Workbook(p).settings('peak_fit')
    assert peaks.options_from_dict(back) == o
    assert sum(1 for r in workbook.Workbook(p)._rows('Settings') if r['key'] == 'shape') == 1


def test_maps_and_too_many_columns(tmp_path):
    wb = workbook.Workbook(str(tmp_path / 'f_reader.xlsx'))
    X, Y = np.meshgrid(np.arange(3.0), np.arange(2.0))
    V = X + Y
    V[0, 0] = np.nan
    rid = wb.add_result('gid map', [11, 12], map_xyz=(X, Y, V, V * 0.1), program='test')
    rows = [r for r in wb._rows('Maps') if r['id'] == rid]
    assert len(rows) == 5                                         # NaN cells are not stored
    assert workbook.MAX_VALUES == 8                               # 6 until the burn tests (2026-11-21): time + 3 × (value, error)
    with pytest.raises(ValueError):
        wb.add_result('other', [1], np.zeros((3, workbook.MAX_VALUES + 1)))


def test_scan_rows_label_experiment_kinds():
    """NX school: reflectivity 3, 6–9; GID 11–12; alignment scans marked."""
    import os
    from PyQt5.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import spec_routines
    spec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'sample_data', 'NX_school', '2026sep', '20260923')
    if not os.path.exists(spec):
        pytest.skip('NX school data not present')
    s = spec_routines.specread(spec)
    rows = {r['scan']: r for r in workbook.scan_rows(s.Data, s.Par)}
    assert rows[6]['kind'] == 'reflectivity' and rows[9]['kind'] == 'reflectivity'
    assert rows[11]['kind'] == 'gid' and rows[12]['kind'] == 'gid'
    assert rows[4]['kind'] == 'alignment'


def test_fit_options_round_trip_and_bad_values():
    o = peaks.FitOptions(shape='lorentzian', n_peaks=2, fwhm=0.1, fix_centres=True)
    assert peaks.options_from_dict(peaks.options_to_dict(o)) == o
    assert peaks.options_from_dict({'shape': 'nonsense'}) == peaks.FitOptions()
    assert peaks.options_from_dict({'n_peaks': 'x', 'unknown': 1}).n_peaks == 0


def test_an_older_workbook_gains_the_trends_sheet_and_wider_data(tmp_path):
    """A workbook written before the burn trends (six sheets, Data v1–v6)
    is opened, extended and keeps its rows."""
    import openpyxl
    p = str(tmp_path / 'old_reader.xlsx')
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name in ('Scans', 'Saved', 'Data', 'Fits', 'Maps', 'Settings'):
        ws = book.create_sheet(name)
        head = workbook.HEADERS[name][:13] if name == 'Data' else workbook.HEADERS[name]
        ws.append(head)
    book['Saved'].append(['R0001', 'then', 'scan', 4, '4', '', 1, '', 2, 'x, y', '{}', 'old'])
    book['Data'].append(['R0001', 'scan', 4, '4', '', 1, 0, 1.0, 2.0])
    book.save(p)
    wb = workbook.Workbook(p)
    assert wb.wb.sheetnames == list(workbook.SHEETS)
    assert [c.value for c in wb.wb['Data'][1]] == workbook.HEADERS['Data']
    assert wb.data('R0001').tolist() == [[1.0, 2.0]]
    from lss_core import trends
    t = np.arange(10.0)
    comp = trends.compare(t, 5 - 0.1 * t + 0.01 * np.cos(t), np.full(10, 0.01))
    rid = wb.add_result('burn test', [4], np.column_stack([t] * 7), ['c%d' % k for k in range(7)],
                        trends=[('intensity', comp)], time_axis='exposure')
    wb.save()
    wb = workbook.Workbook(p)
    assert wb.data(rid).shape == (10, 7)
    rows = wb.trends(rid=rid)
    assert len(rows) == 4 and sum(bool(r['best']) for r in rows) == 1
    assert {r['model'] for r in rows if r['change_time'] is not None} == {comp.change.model}
    assert wb.trends(scan=4) == rows and wb.trends(scan=5) == []


def test_results_tied_to_their_series_and_marked_stale(tmp_path):
    """Review R3 (owner, 2026-11-21): a saved result records its series
    (id, kind, data scans and status then) and the call that remakes it;
    when the series gains scans or changes status, mark_stale says why."""
    from lss_core.series import Series
    s1 = Series('inferred-6', 'reflectivity', None, {1: 6, 2: 7}, status='complete', inferred=True)
    s2 = Series('g1', 'gid', 3, {1: 11, 2: 12}, status='in_progress')
    p = str(tmp_path / 'f_reader.xlsx')
    wb = workbook.Workbook(p)
    assert workbook.series_for([6, 7], [s1, s2])['id'] == 'inferred-6'
    assert workbook.series_for([11], [s1, s2]) == dict(id='g1', kind='gid', scans=[11, 12], status='in_progress')
    assert workbook.series_for([99], [s1, s2]) is None
    r1 = wb.add_result('reflectivity', [6, 7], np.ones((3, 3)), ['Qz', 'R', 'dR'],
                       series=workbook.series_for([6, 7], [s1, s2]), recipe="ref = exp.reflectivity([6, 7])")
    r2 = wb.add_result('gid map', [11, 12], series=workbook.series_for([11, 12], [s1, s2]))
    r3 = wb.add_result('scan', [1], np.ones((2, 2)), ['x', 'y'])            # not in a series
    wb.save()
    wb = workbook.Workbook(p)
    row = wb.results(kind='reflectivity')[0]
    assert row['series'] == 'inferred-6' and row['series_scans'] == '6,7' and row['series_status'] == 'complete'
    assert row['recipe'].startswith('ref = exp.reflectivity')
    assert wb.mark_stale([s1, s2]) == {} and wb.stale() == []               # nothing changed
    grown = Series('inferred-6', 'reflectivity', None, {1: 6, 2: 7, 3: 8}, status='complete', inferred=True)
    done = Series('g1', 'gid', 3, {1: 11, 2: 12, 3: 13}, status='complete')
    stale = wb.mark_stale([grown, done])
    assert stale[r1] == 'series inferred-6 gained scans 8'
    assert stale[r2] == 'series g1 gained scans 13; status in_progress → complete'
    assert r3 not in stale
    wb.save()
    assert {r['id'] for r in workbook.Workbook(p).stale()} == {r1, r2}
    # a guessed series renamed (its first scan changed) is found by the result's first scan
    moved = Series('inferred-5', 'reflectivity', None, {1: 5, 2: 6, 3: 7}, status='complete', inferred=True)
    assert 'gained scans 5' in wb.mark_stale([moved, done])[r1]
    assert 'no longer found' in wb.mark_stale([done])[r1]
