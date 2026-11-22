"""Scan series, "scan i of N" (F39, Stage 3): the proposed '#U Series' line
(docs/handoff_out/05-scan-series-syntax.md), SPEC's abort comment, and the
guess for files without the line. Every row of the proposal's table of
cancellation cases has a test here."""
import os

import numpy as np
import pytest

import synth
from lss_core import series
from spec_routines import specread

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')


def _scan(num, npts=5, planned=5, sid=None, i=None, n=None, kind='reflectivity', role=None, aborted=None,
          end=None, command=None, header='', macro=None):
    qz = np.linspace(0.02 * num, 0.02 * num + 0.03, npts)
    text = synth.spec_scan(num, 's', synth.REF_COLUMNS, synth.ref_rows(qz),
                           command=command or 'hklscan 0 0 0 0 %g %g %d 1' % (qz[0], qz[0] + 0.03, planned - 1))
    head, body = text.split('\n', 1)
    extra = ''
    if sid is not None:
        words = ['id=%s' % sid, 'kind=%s' % kind] + (['i=%d' % i] if i else []) + (['n=%d' % n] if n else [])
        words += ['role=%s' % role] if role else []
        extra = '#U Series ' + ' '.join(words) + '\n'
    if macro is not None:
        extra += '#U SeriesMacro %s\n' % macro
    extra += header
    if '#V' in header:              # a fluorescence scan (fluo_p) has no image line
        body = ''.join(l for l in body.splitlines(True) if not l.startswith('#B0'))
    tail = ''
    if aborted is not None:
        tail += '#C Thu Nov 19 10:00:00 2026.  Scan aborted after %d points.\n' % aborted
    if end is not None:
        tail += '#C Series id=%s end %s\n' % (sid, end)
    return head + '\n' + extra + body.rstrip('\n') + '\n' + tail + '\n'


def _groups(tmp_path, scans, growing=False):
    spec = synth.write_spec(str(tmp_path / 's'), scans)
    r = specread(spec, data={}, par={})
    info = series.scan_info(r.Data, r.Par)
    return series.group(info, growing=growing), info


def test_parsing_the_line_and_the_command():
    assert series.parse_series('id=6-17 i=2 n=4 kind=gid level=1 junk'.split()) == \
        dict(id='6-17', i=2, n=4, kind='gid', level='1')
    assert series.planned_points('ascan dth 14 18 40 7') == 41
    assert series.planned_points('hklscan 0 0 0 0 0.0175 0.04 18 2') == 19
    assert series.planned_points('getandsave_mca 10') is None
    assert series.aborted_after('#C Wed Sep 23 11:12:13 2026.  Scan aborted after 4 points.') == 4


def test_reader_keeps_series_macro_and_abort(tmp_path):
    scans = [_scan(1, sid='a', i=1, n=2), _scan(2, npts=3, sid='a', i=2, n=2, aborted=3, end='status=aborted after=2')]
    scans[0] = scans[0].replace('#U Series', '#U SeriesMacro xr_ref 0.02 0.1\n#U Series')
    r = specread(synth.write_spec(str(tmp_path / 's'), scans), data={}, par={})
    assert r.Par[1]['Series'] == dict(id='a', kind='reflectivity', i=1, n=2)
    assert r.Par[1]['SeriesMacro'] == 'xr_ref 0.02 0.1'
    assert r.Par[2]['AbortedAfter'] == 3 and r.Par[2]['SeriesEnd'] == dict(id='a', status='aborted', after=2)
    assert len(r.Data[2]['L']) == 3                      # the data are still read in full


def test_complete(tmp_path):
    (s,), _ = _groups(tmp_path, [_scan(k, sid='a', i=k, n=3) for k in (1, 2, 3)])
    assert (s.status, s.data_scans, s.missing, s.label()) == ('complete', [1, 2, 3], [], 'reflectivity 3/3')


def test_partial_when_a_scan_is_short(tmp_path):
    (s,), _ = _groups(tmp_path, [_scan(1, sid='a', i=1, n=2), _scan(2, npts=2, sid='a', i=2, n=2, aborted=2)])
    assert s.status == 'partial' and 'scan 2 (2 of 2) aborted after 2 of 5 points' in s.why


def test_stopped_at_the_last_point_is_complete(tmp_path):
    (s,), _ = _groups(tmp_path, [_scan(1, sid='a', i=1, n=1, aborted=5)])      # NX scan 13: 21 of 21
    assert s.status == 'complete'


def test_aborted_by_the_macros_end_line(tmp_path):
    (s,), _ = _groups(tmp_path, [_scan(1, sid='a', i=1, n=3), _scan(2, sid='a', i=2, n=3, end='status=aborted after=2')],
                      growing=True)
    assert s.status == 'aborted' and s.missing == [3] and 'aborted after scan 2 of 3' in s.why


def test_aborted_when_another_scan_follows(tmp_path):
    groups, _ = _groups(tmp_path, [_scan(1, sid='a', i=1, n=3), _scan(2, sid='a', i=2, n=3),
                                   _scan(3, command='ascan sh -1 1 4 1')], growing=True)
    assert groups[0].status == 'aborted' and 'other scans follow it' in groups[0].why
    groups, _ = _groups(tmp_path, [_scan(1, sid='a', i=1, n=3), _scan(2, sid='b', i=1, n=1)], growing=True)
    assert [g.status for g in groups] == ['aborted', 'complete']


def test_aborted_when_the_last_scan_is_short(tmp_path):
    (s,), _ = _groups(tmp_path, [_scan(1, sid='a', i=1, n=3), _scan(2, npts=2, sid='a', i=2, n=3, aborted=2)],
                      growing=True)
    assert s.status == 'aborted' and 'missing' in s.why and 'aborted after 2' in s.why


def test_in_progress_only_while_the_file_grows(tmp_path):
    scans = [_scan(1, sid='a', i=1, n=3), _scan(2, sid='a', i=2, n=3)]
    (s,), _ = _groups(tmp_path, scans, growing=True)
    assert s.status == 'in_progress' and s.label() == 'reflectivity 2/3 (in progress)'
    (s,), _ = _groups(tmp_path, scans, growing=False)
    assert s.status == 'aborted' and 'not growing' in s.why


def test_alignment_scans_and_a_resumed_series(tmp_path):
    scans = [_scan(1, sid='a', i=1, n=3), _scan(2, sid='a', role='align', command='a2scan sh -1 1 oh -1 1 4 1'),
             _scan(3, sid='a', i=2, n=3), _scan(4, sid='b', i=1, n=1), _scan(5, sid='a', i=3, n=3)]
    groups, _ = _groups(tmp_path, scans)
    a = groups[0]
    assert a.data_scans == [1, 3, 5] and a.aux == [(2, 'align')] and a.status == 'complete'


def test_inference_on_files_without_the_line(tmp_path):
    scans = [_scan(1), _scan(2, command='a2scan sh -1 1 oh -1 1 4 1'), _scan(2 + 1), _scan(4),
             _scan(5, command='ascan ih 0 0 4 10'), _scan(6)]
    spec = synth.write_spec(str(tmp_path / 's'), scans)
    r = specread(spec, data={}, par={})
    got = series.infer(series.scan_info(r.Data, r.Par))
    # scans 1, 3, 4 move up in Qz and overlap (0.02k .. 0.02k+0.03); 5 is a fixed position, not alignment:
    # a burn scan (ascan ih without movement, the beamline's standard; owner, 2026-11-21)
    assert [(g.kind, g.data_scans, g.aux) for g in got] == [('reflectivity', [1], [(2, 'align')]),
                                                            ('reflectivity', [3, 4], []),
                                                            ('burn', [5], []),
                                                            ('reflectivity', [6], [])]
    assert all(g.inferred and g.n is None for g in got)


@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school sample data not present')
def test_inference_on_the_nx_school_file():
    r = specread(NX, data={}, par={})
    info = series.scan_info(r.Data, r.Par)
    assert [(x.num, x.points, x.planned) for x in info if x.aborted] == [(4, 15, 21), (12, 4, 41)]
    got = [(g.kind, g.data_scans, [a for a, _ in g.aux], g.status) for g in series.infer(info)]
    assert got == [('reflectivity', [3], [4, 5], 'complete'), ('reflectivity', [6, 7, 8, 9], [10], 'complete'),
                   ('gid', [11, 12], [13], 'partial'), ('burn', [14], [], 'complete'),
                   ('burn', [15], [], 'complete')]          # burn scans: ascan ih without movement (2026-11-21)
    assert series.group(info) == []                      # no '#U Series' lines in this file


def test_a_scan_without_parameters_is_still_said_to_have_none(tmp_path):
    """Reading the abort comment must not hide 'No parameters!!' (the
    'parameters' check counts header values only; seen on a bu file)."""
    text = '#S 1  getandsave_mca 10\n\n#C Thu Nov 19 10:00:00 2026.  Scan aborted after 0 points.\n\n'
    r = specread(synth.write_spec(str(tmp_path / 's'), [text]), data={}, par={})
    assert r.Par[1]['Message'] == 'No parameters!!' and r.Par[1]['AbortedAfter'] == 0


# ---- the review of 2026-11-21 (section 3, step R1) ------------------------------

def test_xfntr_and_energy_scans_are_not_reflectivity(tmp_path):
    """Measured for the review: every `fluo_p` scan (an hklscan with a '#V'
    line) of the owner's XFNTR file was inferred as reflectivity. Now:
    consecutive '#V' hklscans are one xfntr series, escans an energy
    series, plain hklscans still reflectivity."""
    v = '#V 1\n'
    scans = [_scan(1, header=v), _scan(2, header=v), _scan(3, command='a2scan sh -1 1 oh -1 1 4 1'),
             _scan(4, header=v), _scan(5), _scan(6),
             _scan(7, command='escan 10 9.9 10.1 1 0 3 6 0.5'), _scan(8, command='escan 10 9.9 10.1 1 0 3 6 0.5')]
    spec = synth.write_spec(str(tmp_path / 's'), scans)
    r = specread(spec, data={}, par={})
    got = [(g.kind, g.data_scans, g.aux) for g in series.infer(series.scan_info(r.Data, r.Par))]
    assert got == [('xfntr', [1, 2, 4], [(3, 'align')]), ('reflectivity', [5, 6], []), ('energy', [7, 8], [])]


def test_lined_and_plain_scans_together(tmp_path):
    """A file whose later scans have '#U Series' lines and earlier ones not:
    both kinds of series (before: `group(info) or infer(info)` dropped the
    guessed ones); '#U SeriesMacro' reaches the series."""
    scans = [_scan(1), _scan(2), _scan(3, sid='r9', i=1, n=2, macro='refl_run 0.02 0.5'),
             _scan(4, sid='r9', i=2, n=2)]
    spec = synth.write_spec(str(tmp_path / 's'), scans)
    r = specread(spec, data={}, par={})
    info = series.scan_info(r.Data, r.Par)
    allof = series.all_series(info)
    assert [(g.id, g.kind, g.data_scans, g.inferred) for g in allof] == [
        ('inferred-1', 'reflectivity', [1, 2], True), ('r9', 'reflectivity', [3, 4], False)]
    assert allof[1].macro == 'refl_run 0.02 0.5' and allof[1].status == 'complete'
    assert series.all_series([]) == []


def test_an_update_lists_each_scan_once(tmp_path):
    """"Update Specfile" re-reads the last scan (it may have grown); its
    number was appended again, so every update warned of a repeated scan
    and the series guess split (found 2026-11-22 while tying saved results
    to series)."""
    spec = synth.write_spec(str(tmp_path / 's'), [_scan(1), _scan(2)])
    r = specread(spec, data={}, par={})
    with open(spec, 'a') as f:
        f.write(_scan(3))
    r2 = specread(spec, startLineNum=r.endLineNum, endScanNum=r.Data['NumOfScans'], data=r.Data, par=r.Par)
    assert r2.Data['ScanNums'] == [1, 2, 3]
    got = series.infer(series.scan_info(r2.Data, r2.Par))
    assert [(g.kind, g.data_scans) for g in got] == [('reflectivity', [1, 2, 3])]
