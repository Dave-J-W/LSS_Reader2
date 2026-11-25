"""The dose each spot has received, against a burn test's dose to a 5 %
change (F107; owner, 2026-11-24, Q-TL-7: "the sx trace ... coloured by the
radiation dose per area received at each position, scaled by the dose per
area of the relevant burn test"). lss_core.timeline.dose_track, with a stand-in
experiment whose scan n receives a dose of n (known truth).
"""
import math

import pytest

from lss_core import timeline as T


class _Dose:
    def __init__(self, total, unit='photons/mm2'):
        self._t, self.unit = total, unit

    def total(self):
        return self._t


class _Exp:
    def __init__(self, units=None, fail=()):
        self.units, self.fail, self.asked = units or {}, set(fail), []

    def dose(self, scan, unit='photons', beam_mm=None):
        self.asked.append((scan, beam_mm))
        if scan in self.fail:
            raise ValueError('no monitor')
        return _Dose(float(scan), self.units.get(scan, 'photons/mm2'))


def _tl(answer=''):
    """Scans 1-3 at sx 5 (3 at 5.3: the same spot within half a 1 mm beam),
    the burn 4 at sx 7, a "new sample?" set sh 0 at t 450, scan 5 at sx 5."""
    spans = [T.ScanSpan(n, 'ascan', t0, t0 + 100.0, 10, False, k)
             for n, t0, k in ((1, 0.0, 'reflectivity'), (2, 100.0, 'reflectivity'), (3, 200.0, 'gid'),
                              (4, 300.0, 'burn'), (5, 500.0, 'reflectivity'))]
    tl = T.Timeline(spans=spans, positions={'Sample_X': [(1, 0.0, 5.0), (2, 100.0, 5.0), (3, 200.0, 5.3),
                                                         (4, 300.0, 7.0), (5, 500.0, 5.0)]},
                    events=[T.Event(450.0, 'set-zero', 4, 'set Sample_H 0: new sample?')])
    notes = [T.Note(450.0, answer, '', None, 'set-zero', answer, 'N1', 1, [4])] if answer else []
    return tl, notes


def _scale(n):
    return T.DoseScale(n, 10.0, 'intensity'), 'photons/mm2'


def test_doses_add_up_by_spot_and_are_scaled_by_the_burn():
    tl, notes = _tl()
    tr = T.dose_track(_Exp(), tl, (1.0, 0.04), notes, scale_of=_scale)
    rows = {r.scan: r for r in tr.rows}
    assert [rows[n].spot for n in (1, 2, 3, 4, 5)] == [0, 0, 0, 1, 0]
    assert [rows[n].cumulative for n in (1, 2, 3, 4, 5)] == [1.0, 3.0, 6.0, 4.0, 11.0]
    assert [rows[n].fraction for n in (1, 2, 3, 4, 5)] == pytest.approx([0.1, 0.3, 0.6, 0.4, 1.1])
    assert tr.unit == 'photons/mm2' and set(tr.scales) == {4}
    assert [rows[n].own for n in (1, 2, 3, 4, 5)] == [True, True, True, True, False]   # 5: a new sample


def test_a_same_sample_answer_keeps_one_sample():
    tl, notes = _tl('same sample')
    tr = T.dose_track(_Exp(), tl, (1.0, 0.04), notes, scale_of=_scale)
    assert all(r.own for r in tr.rows)


def test_the_spot_tolerance_follows_the_beam():
    tl, notes = _tl()
    narrow = T.dose_track(_Exp(), tl, (0.4, 0.04), notes, scale_of=_scale)      # ±0.2 mm: 5.3 is another spot
    assert [r.spot for r in narrow.rows] == [0, 0, 1, 2, 0]
    wide = T.dose_track(_Exp(), tl, (0.4, 0.04), notes, same_spot_mm=1.0, scale_of=_scale)
    assert [r.spot for r in wide.rows] == [0, 0, 0, 1, 0]


def test_scans_without_a_dose_or_in_another_unit_are_left_out_and_said():
    tl, notes = _tl()
    tr = T.dose_track(_Exp(units={2: 'Monc counts/mm2'}, fail=[3]), tl, (1.0, 0.04), notes, scale_of=_scale)
    assert [r.scan for r in tr.rows] == [1, 4, 5]
    assert any('S# 3: no dose' in n for n in tr.notes) and any('S# 2: dose in Monc' in n for n in tr.notes)
    assert [r.cumulative for r in tr.rows] == [1.0, 4.0, 6.0]


def test_no_burn_no_scale_and_a_scale_in_another_unit_is_refused():
    tl, notes = _tl()
    tl.spans = [s for s in tl.spans if s.kind != 'burn']
    tr = T.dose_track(_Exp(), tl, (1.0, 0.04), notes, scale_of=_scale)
    assert all(r.fraction is None for r in tr.rows) and 'no burn test in this file: no scale' in tr.notes
    tl, notes = _tl()
    tr = T.dose_track(_Exp(), tl, (1.0, 0.04), notes, scale_of=lambda n: (T.DoseScale(n, 10.0, 'x'), 'Monc'))
    assert all(r.fraction is None for r in tr.rows) and any('not photons/mm2' in n for n in tr.notes)


class _Burn:
    def __init__(self, safe, total=3.0):
        self.safe, self.dose_total, self.dose_scale, self.dose_unit = safe, total, 1e12, '1e+12 photons/mm2'

    def safe_time(self):
        return self.safe


class _BurnExp:
    def __init__(self, safe):
        self.safe, self.kw = safe, None

    def burn(self, n, **kw):
        self.kw = kw
        return _Burn(self.safe)


def test_the_burns_scale_from_its_dose_axis():
    e = _BurnExp((2.5, 'intensity'))
    sc, unit = T.burn_scale(e, 4, (1.0, 0.04))
    assert (sc.dose, sc.quantity, sc.lower_bound, unit) == (2.5e12, 'intensity', False, 'photons/mm2')
    assert e.kw['axis'] == 'dose' and e.kw['beam_mm'] == (1.0, 0.04) and e.kw['threshold'] == T.CHANGE
    sc, _ = T.burn_scale(_BurnExp((math.inf, '')), 4, (1.0, 0.04))      # no change within the burn
    assert sc.lower_bound and sc.dose == 3.0e12 and '≥' in sc.describe('photons/mm2')


def test_colours_run_from_teal_to_dark_red():
    assert T.dose_colour(0) == (42, 157, 143) and T.dose_colour(1) == (231, 111, 81)
    assert T.dose_colour(3) == T.dose_colour(2) == (155, 34, 38) and T.dose_colour(None) == (140, 140, 140)
    r0, g0, _ = T.dose_colour(0.25)
    assert 42 < r0 < 233 and 157 < g0 < 196
