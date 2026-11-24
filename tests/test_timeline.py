"""The sample timeline's model (F83 phase 1b, lss_core.timeline): scan
spans, events from dated comments, motor steps, sample-height scans and
the mnemonic table. The NX school file (public) gives the measured facts
of docs/gui/timeline/research.md sections 1-3; a small synthetic file
gives the cases NX lacks (header comments, a session restart, a reset to
0 of another motor, no time zone).
"""
import calendar
import os
import time

import numpy as np
import pytest

import synth
from lss_core import timeline
from lss_core.experiment import Experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
needs_nx = pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
CDT = 5 * 3600                          # the NX file's #E/#D: local time is UTC − 5 h


def _utc(hms, day='2026-09-23'):
    return calendar.timegm(time.strptime('%s %s' % (day, hms), '%Y-%m-%d %H:%M:%S'))


@pytest.fixture(scope='module')
def nx():
    return timeline.build(Experiment(NX))


@needs_nx
def test_the_nx_file_gives_the_resets_of_the_research(nx):
    (zero,) = nx.of_kind('set-zero')
    assert zero.after_scan == 4 and zero.motor == 'Sample_H' and zero.old == -0.61 and zero.new == 0.0
    assert zero.t == _utc('10:37:39') + CDT and 'new sample?' in zero.text
    resets = nx.of_kind('reset')
    assert [r.after_scan for r in resets] == [5, 10, 13]
    assert [round(r.shift * 1000, 1) for r in resets] == [5.5, -1.0, 0.5]           # µm: re-referencing
    spans = {s.scan: s for s in nx.spans}
    for r in resets:                                                                 # each 1-2 min after its sh scan
        assert 0 < r.t - spans[r.after_scan].t1 < 180, r


@needs_nx
def test_the_nx_file_gives_aborts_macros_steps_and_kinds(nx):
    assert [e.after_scan for e in nx.of_kind('abort')] == [2, 4, 12, 13]
    macros = nx.of_kind('macro')
    assert len(macros) == 29 and sum(e.after_scan == 0 for e in macros) == 3      # 3 in the file header
    assert macros[0].text == 'do do_files/dppc_burn.do'
    assert nx.of_kind('session') == [] and nx.notes == []
    assert [(s.scan, s.old, s.new) for s in nx.steps] == [(4, 19.9999, 18.0), (5, 18.0, 16.0), (10, 16.0, 14.0),
                                                          (12, 14.0, 12.0), (13, 12.0, 9.99997)]
    kinds = {s.scan: s.kind for s in nx.spans}
    assert [n for n, k in kinds.items() if k == 'height'] == [4, 5, 10, 13]
    assert kinds[3] == kinds[6] == 'reflectivity' and kinds[11] == 'gid' and kinds[14] == 'burn'
    aborted = {s.scan for s in nx.spans if s.aborted}
    assert aborted == {4, 12}                     # scan 13's "aborted after 21 points" is its full 21 (series rule)
    assert nx.mnemonics == {'oh': 'Out_Ht', 'sh': 'Sample_H', 'dth': 'Det_Th', 'ih': 'In_Ht'}
    t0, t1 = nx.range()
    assert t0 < t1 and all(s.t0 <= s.t1 for s in nx.spans)


@needs_nx
def test_the_nx_height_scans_carry_their_fits(nx):
    h = {x.scan: x for x in nx.heights}
    assert sorted(h) == [4, 5, 10, 13]
    assert not h[4].fit.ok and 'no reflected beam' in h[4].fit.message
    assert [round(h[n].fit.fwhm * 1000, 1) for n in (5, 10, 13)] == [82.1, 81.1, 81.4]
    assert [h[n].sx for n in (5, 10, 13)] == [16, 14, 9.99997]


# ---- synthetic: what NX does not have ---------------------------------------

def _dated(text, local):
    return text.replace('#D Sat Nov 14 12:00:00 2026', '#D ' + local, 1)


def _spec(tmp_path, zone=True):
    """Header comments, three scans; a reset to 0 of Out_Ht after scan 1; a
    second SPEC session (#E) and a 50 min gap before scan 3."""
    cols = ['Sample_H', 'Epoch', 'Seconds', 'Monc', 'Pilatus']
    x = np.linspace(-0.2, 0.2, 21)

    def rows(t0):
        y = 5000 * np.exp(-np.abs(x / 0.045) ** 3.4) + 20
        return np.column_stack([x, t0 + np.arange(21) * 2.0, x * 0 + 1, x * 0 + 1e5, y])
    s1 = _dated(synth.spec_scan(1, 'tl', cols, rows(0), command='ascan sh -0.2 0.2 20 1',
                                motors={'Sample_X': 5.0}), 'Fri Nov 14 09:00:00 2025')
    s1 += '#C Fri Nov 14 09:02:00 2025.  Out_Ht reset from 1.5 to 0.\n\n'
    s2 = _dated(synth.spec_scan(2, 'tl', cols, rows(0), command='ascan sh -0.2 0.2 20 1',
                                motors={'Sample_X': 7.0}), 'Fri Nov 14 09:05:00 2025')
    s3 = _dated(synth.spec_scan(3, 'tl', cols, rows(0), command='ascan sh -0.2 0.2 20 1',
                                motors={'Sample_X': 7.0}), 'Fri Nov 14 10:00:00 2025')
    epoch = calendar.timegm(time.strptime('2025-11-14 08:59:00', '%Y-%m-%d %H:%M:%S')) + 6 * 3600   # local UTC−6
    head = '#F tl\n#E %d\n#D Fri Nov 14 08:59:00 2025\n#C Fri Nov 14 08:59:30 2025.  do start.mac.\n\n' % (
        epoch if zone else 0)
    again = '#E %d\n#D Fri Nov 14 09:55:00 2025\n\n' % ((epoch + 56 * 60) if zone else 0)
    path = str(tmp_path / 'tl')
    with open(path, 'w') as f:
        f.write(head + s1 + s2 + again + s3)
    return path


def test_header_comments_sessions_gaps_and_other_motors(tmp_path):
    tl = timeline.build(Experiment(_spec(tmp_path)))
    assert tl.notes == []
    (macro,) = tl.of_kind('macro')
    assert macro.after_scan == 0 and macro.text == 'do start.mac'
    assert macro.t == _utc('08:59:30', '2025-11-14') + 6 * 3600
    (reset,) = tl.of_kind('reset')                      # a reset to 0, but not of the sample height
    assert reset.motor == 'Out_Ht' and reset.new == 0.0 and tl.of_kind('set-zero') == []
    (session,) = tl.of_kind('session')
    assert session.after_scan == 2
    (gap,) = tl.of_kind('gap')
    assert gap.after_scan == 2 and 50 * 60 < gap.duration < 56 * 60
    assert [(s.scan, s.old, s.new) for s in tl.steps] == [(2, 5.0, 7.0)]
    assert [h.fit.ok for h in tl.heights] == [True, True, True]
    assert tl.mnemonics == {'sh': 'Sample_H'}
    assert [e.t for e in tl.events] == sorted(e.t for e in tl.events)


def test_without_a_time_zone_dates_are_read_as_utc_and_said(tmp_path):
    tl = timeline.build(Experiment(_spec(tmp_path, zone=False)))
    assert any('read as UTC' in n for n in tl.notes)
    (macro,) = tl.of_kind('macro')
    assert macro.t == _utc('08:59:30', '2025-11-14')


def test_a_set_zero_of_the_height_is_a_new_sample_guess():
    ev = timeline.comment_event(3, 0.0, 'Sample_H reset from -0.61 to 0.')
    assert ev.kind == 'set-zero' and ev.text == 'set Sample_H 0: new sample?'
    ev = timeline.comment_event(3, 0.0, 'Sample_H reset from -2.204 to -2.1985.')
    assert ev.kind == 'reset' and ev.shift == pytest.approx(0.0055)
    assert timeline.comment_event(3, 0.0, 'Scan aborted after 2 points.').kind == 'abort'
    assert timeline.comment_event(3, 0.0, 'something else entirely') is None


def test_notes_round_trip_through_saved_rows(tmp_path):
    """Notes and "new sample?" answers are Saved rows of kind 'note'
    (research §5); the latest answer to an event wins."""
    from lss_core import workbook
    wb = workbook.Workbook(str(tmp_path / 'b.xlsx'))
    wb.add_result('note', **timeline.note_item(100.0, 'same sample', 'set sh 0 at …', scans=[4],
                                              event='set-zero', answer='same sample'))
    wb.add_result('note', **timeline.note_item(100.4, 'new sample', 'set sh 0 at …', scans=[4],
                                              event='set-zero', answer='new sample'))
    wb.add_result('note', **timeline.note_item(250.0, 'Trough cleaned', 'Trough cleaned\nwith ethanol', scans=[6],
                                              t1=400.0))
    wb.save()
    notes = timeline.notes_from_rows(workbook.Workbook(str(tmp_path / 'b.xlsx')).results('note'))
    assert [n.label for n in notes] == ['same sample', 'new sample', 'Trough cleaned']
    assert notes[2].t1 == 400.0 and notes[2].scans == [6] and 'ethanol' in notes[2].text
    of = timeline.answers(notes)
    assert of(timeline.Event(100.0, 'set-zero', 4, '')) == 'new sample'       # the later one
    assert of(timeline.Event(500.0, 'set-zero', 9, '')) == ''
    assert timeline.notes_from_rows([{'kind': 'note', 'settings': '{}'}, {'kind': 'reflectivity'}]) == []
