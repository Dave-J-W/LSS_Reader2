"""Per-point times (F37; owner's guidance, 2026-11-19): new files (#L has
Tstart and Tend, #U SeriesT0) and old files (#L has Epoch; #D anchor plus
Epoch differences, never #E + Epoch), told apart by #L alone, both read
without complaint."""
import calendar
import functools
import os
import time

import numpy as np
import pytest

import sweep
import synth
from lss_core import timing
from lss_core.experiment import Experiment

# Unix times are ~1.8e9 s: np.allclose's default rtol (1e-5) would allow ±18 000 s
close = functools.partial(np.allclose, rtol=0, atol=1e-6)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
E0 = 1790173797                         # 2026-09-23 14:29:57 UTC
D0 = 'Wed Sep 23 09:29:57 2026'         # the same moment at the beamline (UTC-5, as the NX file)


def _file(path, scans, head=True):
    with open(path, 'w') as f:
        f.write('#F s\n' + ('#E %d\n#D %s\n' % (E0, D0) if head else '') + '\n')
        for s in scans:
            f.write(s)
    return str(path)


def _scan(num, columns, rows, date, extra=()):
    text = synth.spec_scan(num, 's', columns, np.array(rows, float), command='ascan sh -1 1 %d 1' % (len(rows) - 1),
                           image=False, fmt='%.2f')
    lines = text.split('\n')
    lines = [('#D ' + date) if l.startswith('#D ') else l for l in lines]
    return '\n'.join(lines[:1] + list(extra) + lines[1:])


def test_format_from_the_l_line_alone():
    assert timing.time_format(['H', 'Tstart', 'Tend', 'Seconds']) == 'new'
    assert timing.time_format(['H', 'Epoch', 'Seconds']) == 'old'
    assert timing.time_format(['H', 'Seconds']) == 'none'
    assert timing.time_format(['Epoch', 'Tstart', 'Tend']) == 'new'      # Tstart/Tend win if both are there


def test_new_format(tmp_path):
    t0 = E0 + 3600.0
    rows = [[k, 2.0, t0 + 5 + 3 * k, t0 + 5 + 3 * k + 2.4, 1e5] for k in range(4)]   # 2 s count, 0.4 s overhead
    spec = _file(tmp_path / 'new', [_scan(1, ['sh', 'Seconds', 'Tstart', 'Tend', 'Monc'], rows,
                                          'Wed Sep 23 10:30:03 2026', ['#U SeriesT0 %.2f' % t0])])
    t = Experiment(spec).point_times(1)
    assert t.format == 'new' and t.precision_s == 0.01
    assert close(t.start, [r[2] for r in rows]) and close(t.end, [r[3] for r in rows])
    assert close(t.overhead, 0.4)
    assert close(t.since_series, [5, 8, 11, 14])


def test_new_format_without_series_t0_says_so(tmp_path):
    rows = [[k, 1.0, E0 + k, E0 + k + 1.1, 1e5] for k in range(3)]
    spec = _file(tmp_path / 'n', [_scan(1, ['sh', 'Seconds', 'Tstart', 'Tend', 'Monc'], rows, D0)])
    t = Experiment(spec).point_times(1)
    assert t.since_series is None and any('SeriesT0' in n for n in t.notes)


def test_old_format_uses_the_scan_date_not_e_plus_epoch(tmp_path):
    # Epoch's base is wrong (here 5000 s off #E); its steps are right
    rows1 = [[k, 2.0, 5000.0 + 4 * k, 1e5] for k in range(5)]
    rows2 = [[k, 2.0, 5300.0 + 4 * k, 1e5] for k in range(5)]
    cols = ['L', 'Seconds', 'Epoch', 'Monc']
    rows1 = [[0.01 + 0.005 * k] + r[1:] for k, r in enumerate(rows1)]
    rows2 = [[0.025 + 0.005 * k] + r[1:] for k, r in enumerate(rows2)]
    s1 = synth.spec_scan(1, 's', cols, np.array(rows1), command='hklscan 0 0 0 0 0.01 0.03 4 2', image=False, fmt='%.4f')
    s2 = synth.spec_scan(2, 's', cols, np.array(rows2), command='hklscan 0 0 0 0 0.025 0.045 4 2', image=False, fmt='%.4f')
    s1 = s1.replace('#D Sat Nov 14 12:00:00 2026', '#D Wed Sep 23 10:00:00 2026')
    s2 = s2.replace('#D Sat Nov 14 12:00:00 2026', '#D Wed Sep 23 10:05:00 2026')
    exp = Experiment(_file(tmp_path / 'old', [s1, s2]))
    t = exp.point_times(2)
    anchor = calendar.timegm(time.strptime('Wed Sep 23 15:05:00 2026', '%a %b %d %H:%M:%S %Y'))   # UTC
    assert t.format == 'old' and t.precision_s == 1.0
    assert close(t.start, anchor + 4 * np.arange(5))
    assert not close(t.start[0], E0 + 5300.0)                        # never #E + Epoch
    # scans 1 and 2 are one inferred reflectivity series: since its first scan's #D
    assert close(t.since_series, 300 + 4 * np.arange(5))


def test_no_times_and_no_zone_are_noted_not_errors(tmp_path):
    rows = [[k, 1.0, 1e5] for k in range(3)]
    t = Experiment(_file(tmp_path / 'x', [_scan(1, ['sh', 'Seconds', 'Monc'], rows, D0)])).point_times(1)
    # no Epoch, no Tstart: the scan's #D plus the count times before each point (owner: as
    # accurate as feasible; overhead ignored). Was 'no times' until 2026-11-19.
    assert t.format == 'none' and close(t.start, E0 + np.array([0.0, 1.0, 2.0])) and t.notes
    rows = [[k, 1.0, 100.0 + k, 1e5] for k in range(3)]
    t = Experiment(_file(tmp_path / 'z', [_scan(1, ['sh', 'Seconds', 'Epoch', 'Monc'], rows, D0)], head=False)).point_times(1)
    assert any('read as UTC' in n for n in t.notes) and close(np.diff(t.start), 1.0)
    assert timing.utc_offset(0, 'Sat Nov 14 12:00:00 2026') is None        # #E 0: not one moment


@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school sample data not present')
def test_nx_school_steps_never_go_back_or_undercut_the_count_time():
    """The owner's check on c51_surface (189,439 steps), here on NX: Epoch
    steps within a scan never go backwards and are never shorter than the
    count time (1 s resolution). Zone from the file header: UTC-5."""
    exp = Experiment(NX)
    assert timing.utc_offset(exp.scans[1].parameters['FileEpoch'], exp.scans[1].parameters['FileDate']) == -5 * 3600
    steps = 0
    for n, s in exp.scans.items():
        t = exp.point_times(n)
        assert t.format == 'old'
        d = np.diff(t.start)
        steps += len(d)
        assert (d >= 0).all() and (d >= s.columns['Seconds'][1:] - 1).all()
    assert steps == 261


@pytest.mark.gui
@pytest.mark.parametrize('fmt', ['new', 'old'])
def test_window_opens_both_formats_without_complaint(window, qapp, recorder, tmp_path, fmt):
    if fmt == 'new':
        cols = ['sh', 'Seconds', 'Tstart', 'Tend', 'Monc', 'Apex2']
        rows = [[k, 1.0, E0 + 2 * k, E0 + 2 * k + 1.2, 1e5, 10.0] for k in range(5)]
        extra = ['#U SeriesT0 %d' % E0]
    else:
        cols = ['sh', 'Seconds', 'Epoch', 'Monc', 'Apex2']
        rows = [[k, 1.0, 900.0 + 2 * k, 1e5, 10.0] for k in range(5)]
        extra = []
    spec = _file(tmp_path / fmt, [_scan(1, cols, rows, D0, extra)])
    w = window
    w.openSpecFile(fname=spec)
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0])
    w.ui.spXComboBox.setCurrentIndex(w.ui.spXComboBox.findText('Tstart' if fmt == 'new' else 'Epoch'))
    w.ui.spYComboBox.setCurrentIndex(w.ui.spYComboBox.findText('Apex2'))
    qapp.processEvents()
    assert recorder.exceptions == []
    assert not [m for m in recorder.messages if 'Epoch' in m or 'Tstart' in m or 'time' in m.lower()]


@pytest.mark.gui
def test_time_is_an_x_axis_of_the_spec_plot(window, qapp, recorder, tmp_path):
    """Owner, 2026-11-19: time as an x axis on any plot. Two old-format scans
    5 min apart: Time_s is seconds since the first scan's first point."""
    cols = ['sh', 'Seconds', 'Epoch', 'Monc', 'Apex2']
    s1 = _scan(1, cols, [[k, 1.0, 900.0 + 2 * k, 1e5, 10.0] for k in range(4)], 'Wed Sep 23 10:00:00 2026')
    s2 = _scan(2, cols, [[k, 1.0, 1200.0 + 3 * k, 1e5, 10.0] for k in range(4)], 'Wed Sep 23 10:05:00 2026')
    w = window
    w.openSpecFile(fname=_file(tmp_path / 'two', [s1, s2]))
    w.directory = str(tmp_path)
    sweep._select_scans(w, qapp, [0, 1])
    k = w.ui.spXComboBox.findText('Time_s')
    assert k >= 0 and 'Epoch' in str(w.ui.spXComboBox.itemData(k, 3))     # tooltip says how
    w.ui.spXComboBox.setCurrentIndex(k)
    w.ui.spYComboBox.setCurrentIndex(w.ui.spYComboBox.findText('Apex2'))
    qapp.processEvents()
    assert close(w.specData[1]['Time_s'], [0, 2, 4, 6]) and close(w.specData[2]['Time_s'], [300, 303, 306, 309])
    # each scan from its own start, to compare scans as if they started together
    assert w.ui.spXComboBox.findText('Time_from_start_s') >= 0
    assert close(w.specData[1]['Time_from_start_s'], [0, 2, 4, 6]) and close(w.specData[2]['Time_from_start_s'], [0, 3, 6, 9])
    sweep._select_scans(w, qapp, [1])                         # scan 2 alone: its own first point is 0
    assert close(w.specData[2]['Time_s'], [0, 3, 6, 9])
    assert recorder.exceptions == []
