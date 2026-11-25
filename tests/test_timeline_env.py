"""The timeline's environment lane (F83 phase 2; F75): any column drawn over
the file, the names that look like the tensiometer, barrier or oxygen
readings offered first, with the owner's units (Q-TL-8: mN/m, cm², %).

The macros do not write such columns yet, so a synthetic file has them
(SurfPress, Barrier, O2) with known values; the public NX file has none,
and its Monc stands in for "any column"."""
import calendar
import os
import time

import numpy as np
import pytest

import synth
from lss_core import timeline as T
from lss_core.experiment import Experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
needs_nx = pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
PTS = 11


def env_spec(tmp_path):
    """Two scans of PTS points, 2 s each, 10 min apart; surface pressure
    rising 20 → 30.5 mN/m over the first, a barrier at 100 then 80 cm², O₂
    at 1 %; Epoch steps of 2 s."""
    cols = ['Sample_H', 'Epoch', 'Seconds', 'Monc', 'SurfPress', 'Barrier', 'O2', 'Pilatus']
    x = np.linspace(-0.1, 0.1, PTS)
    scans = []
    for n, when, press, barr in ((1, '09:00:00', 20.0 + np.arange(PTS) * 1.05, 100.0),
                                 (2, '09:10:00', np.full(PTS, 31.0), 80.0)):
        rows = np.column_stack([x, np.arange(PTS) * 2.0, x * 0 + 2.0, x * 0 + 1e5, press, x * 0 + barr,
                                x * 0 + 1.0, x * 0 + 50.0])
        s = synth.spec_scan(n, 'env', cols, rows, command='ascan sh -0.1 0.1 10 2', motors={'Sample_X': 5.0})
        scans.append(s.replace('#D Sat Nov 14 12:00:00 2026', '#D Fri Nov 14 %s 2025' % when, 1))
    epoch = calendar.timegm(time.strptime('2025-11-14 08:59:00', '%Y-%m-%d %H:%M:%S'))
    path = str(tmp_path / 'env')
    with open(path, 'w') as f:
        f.write('#F env\n#E %d\n#D Fri Nov 14 08:59:00 2025\n\n' % epoch + ''.join(scans))
    return path


def test_environment_names_come_first_with_their_units(tmp_path):
    e = Experiment(env_spec(tmp_path))
    cols = T.environment_columns(e)
    assert [c for c, _k, env in cols if env] == ['Barrier', 'O2', 'SurfPress']
    assert [c for c, _k, _e in cols[:3]] == ['Barrier', 'O2', 'SurfPress'] and all(k == 2 for _c, k, _e in cols)
    assert (T.env_unit('SurfPress'), T.env_unit('Barrier'), T.env_unit('O2'), T.env_unit('Monc')) == \
        ('mN/m', 'cm²', '%', '')


def test_a_column_over_the_file_at_the_middle_of_each_count(tmp_path):
    e = Experiment(env_spec(tmp_path))
    tr = T.column_track(e, 'SurfPress')
    assert len(tr.t) == 2 * PTS and list(np.unique(tr.scans)) == [1, 2] and tr.unit == 'mN/m'
    assert tr.y[:PTS] == pytest.approx(20.0 + np.arange(PTS) * 1.05) and np.all(tr.y[PTS:] == 31.0)
    first = e.point_times(1).start
    assert tr.t[:PTS] == pytest.approx(np.asarray(first) + 1.0)                  # start + half of Seconds 2
    assert tr.t[PTS] - tr.t[0] == pytest.approx(600.0, abs=1.0)                  # the second scan 10 min later
    none = T.column_track(e, 'NoSuchColumn')
    assert len(none.t) == 0 and none.notes == ['no scan has it']


@needs_nx
def test_nx_has_no_environment_column_and_monc_stands_in():
    e = Experiment(NX)
    assert not any(env for _c, _k, env in T.environment_columns(e))
    tr = T.column_track(e, 'Monc')
    assert len(tr.t) == sum(len(e.scans[n].columns['Monc']) for n in e.scans if 'Monc' in e.scans[n].columns)
    assert np.all(np.diff(tr.t[tr.scans == 6]) > 0)
