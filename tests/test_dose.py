"""The dose each point gives the sample, and burns against dose (F98's core;
2026-11-24; lss_core.dose).

Invariants (I39): a point's dose in monitor counts is its weight in "Sum
All", M/(A·g) (cuts.frame_normaliser); in photons, the flux route's
photons/s times its seconds, over A; a scan's dose is the sum of its
points'; at a constant monitor rate and absorber, the dose axis is the
exposure axis times that rate, so a burn's dose limit is its time limit
times the rate."""
import math
import os

import numpy as np
import pytest

import synth
from lss_core import absorbers, cuts, dose, flux, trends
from lss_core.monitor import gain_factor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
WL_10KEV = 1.23984

COLS = {'Monc': np.array([2.0e5, 2.1e5, 1.9e5, 2.0e5]), 'Seconds': np.array([10.0, 10.0, 10.0, 5.0]),
        'H': np.zeros(4), 'K': np.zeros(4), 'L': np.full(4, 0.05)}


def _params(absorber=0, gain=5e-6, wl=WL_10KEV, in_rot=0.1):
    p = {'Absorber': absorber, 'Wavelength': wl, 'In_Rot': in_rot}
    if gain is not None:
        p['MoncGain'] = gain
    return p


def test_monitor_dose_is_the_sum_all_weight():
    p = _params(absorber=3, gain=2e-6)
    d = dose.scan_dose(COLS, p, unit='monitor')
    foils = absorbers.calibrated(10.0)
    want = [cuts.frame_normaliser(m, foils, 3, gain_factor(2e-6)) for m in COLS['Monc']]
    assert d.unit == 'Monc counts' and np.allclose(d.per_point, want, rtol=1e-12)
    assert 'calibrated foils at 10.00 keV' in d.notes[0]


def test_photon_dose_is_the_flux_route_times_seconds_over_the_absorber():
    p = _params(absorber=2)
    d = dose.scan_dose(COLS, p)
    A = absorbers.attenuation(absorbers.calibrated(10.0), 2)
    e = absorbers.energy_kev(WL_10KEV)                   # 10.000016 keV
    want = [flux.photons_per_second(m, s, e, 5e-6, dark_hz=flux.DARK_MONC_HZ, temp_c=flux.TABLE_T_C,
                                    pressure_kpa=flux.TABLE_P_KPA)[0] * s / A
            for m, s in zip(COLS['Monc'], COLS['Seconds'])]
    assert d.unit == 'photons' and np.allclose(d.per_point, want, rtol=1e-12)
    assert d.bounds == pytest.approx((0.036, 0.036))
    # by hand: (2e4 Hz − 50 Hz dark) × 4.37e6 photons/s per Hz × (5 µA/V / 500 nA/V) × 10 s / A, A = 2.21 (112.2 µm Al)
    assert d.per_point[0] == pytest.approx(19950 * 4.37e6 * 10 * 10 / 2.21, rel=0.01)


def test_engineering_scale():
    assert dose.engineering_scale(3.2e12) == 1e12 and dose.engineering_scale(999.0) == 1.0
    assert dose.engineering_scale(1e6) == 1e6 and dose.engineering_scale(0.0) == 1.0
    assert dose.scaled_unit('photons', 1e12) == '1e+12 photons' and dose.scaled_unit('photons', 1.0) == 'photons'


def test_cumulative_at_the_middle_of_each_point_and_the_total():
    d = dose.scan_dose(COLS, _params())
    c = d.cumulative()
    assert c[0] == pytest.approx(d.per_point[0] / 2)
    assert np.allclose(np.diff(c), (d.per_point[:-1] + d.per_point[1:]) / 2)
    assert c[-1] + d.per_point[-1] / 2 == pytest.approx(d.total())
    some = dose.scan_dose(COLS, _params(), points=[1, 3])
    assert some.points == [1, 3] and np.allclose(some.per_point, d.per_point[[1, 3]])


def test_two_absorbers_differ_by_their_attenuation():
    a, b = dose.scan_dose(COLS, _params(absorber=0)), dose.scan_dose(COLS, _params(absorber=5))
    assert np.allclose(a.per_point / b.per_point, absorbers.calibrated(10.0).factor(5), rtol=1e-12)


def test_dose_per_area_uses_the_footprint():
    beam = (2.0, 0.1)
    flat = dose.scan_dose(COLS, _params(in_rot=0.1))
    fixed = dict(COLS, L=np.full(4, 0.05))            # L does not move: the header's In_Rot
    d = dose.scan_dose(fixed, _params(in_rot=0.1), beam_mm=beam)
    assert d.unit == 'photons/mm2'
    assert np.allclose(d.per_point, flat.per_point * math.sin(math.radians(0.1)) / 0.2, rtol=1e-12)
    spec = dict(COLS, L=np.array([0.02, 0.04, 0.06, 0.08]))   # a specular scan: α from L
    s = dose.scan_dose(spec, _params(in_rot=0.1), beam_mm=beam)
    alpha = np.arcsin(spec['L'] * WL_10KEV / 4 / np.pi)
    assert np.allclose(s.per_point, flat.per_point * np.sin(alpha) / 0.2, rtol=1e-12)
    with pytest.raises(dose.DoseError):
        dose.scan_dose(fixed, _params(in_rot=0.0), beam_mm=beam)


def test_fast_mode_adds_the_beam_between_points():
    """Owner, 2026-11-24: in fast mode the shutter stays open between frames."""
    from lss_core.timing import PointTimes
    closed = dose.scan_dose(COLS, _params())
    start = np.array([0.0, 12.0, 24.0, 36.0])                     # 2 s overhead after each 10 s point
    pt = PointTimes('old', start=start)
    fast = dose.scan_dose(COLS, _params(), shutter='open', point_times=pt)
    span = np.array([12.0, 12.0, 12.0, 5.0])                    # the last: its counting time (no end time)
    assert np.allclose(fast.per_point, closed.per_point * span / COLS['Seconds'], rtol=1e-12)
    rate = closed.per_point / COLS['Seconds']
    want = np.concatenate([[0.0], np.cumsum(rate[:-1] * span[:-1])]) + rate * COLS['Seconds'] / 2
    assert np.allclose(fast.cumulative(), want, rtol=1e-12)    # at the middle of each exposure
    no_gap = PointTimes('old', start=np.array([0.0, 10.0, 20.0, 30.0]))
    assert np.allclose(dose.scan_dose(COLS, _params(), shutter='open', point_times=no_gap).cumulative(),
                       closed.cumulative(), rtol=1e-12)        # no overhead: the same as closed
    with pytest.raises(dose.DoseError, match='start times'):
        dose.scan_dose(COLS, _params(), shutter='open')
    with pytest.raises(dose.DoseError, match='before the previous'):
        dose.scan_dose(COLS, _params(), shutter='open', point_times=PointTimes('old', start=np.array([0.0, 5.0, 20.0, 30.0])))
    with pytest.raises(ValueError):
        dose.scan_dose(COLS, _params(), shutter='ajar')


def test_what_is_not_known_is_said():
    d = dose.scan_dose(COLS, _params(gain=None))
    assert d.unit == 'Monc counts' and any('Monc gain unknown' in n for n in d.notes)
    assert np.allclose(d.per_point, COLS['Monc'])
    with pytest.raises(dose.DoseError, match='not known'):
        dose.scan_dose(COLS, _params(absorber=2, wl=12.39842 / 20.0))      # 20 keV: the foils are not known
    assert dose.scan_dose(COLS, _params(absorber=0, wl=12.39842 / 20.0)).unit == 'photons'
    dark = dict(COLS, Monc=np.array([2.0e5, 100.0, 2.0e5, 2.0e5]))      # 10 Hz: below Monc's dark
    d = dose.scan_dose(dark, _params())
    assert d.per_point[1] == 0 and any('dark rate' in n for n in d.notes)
    with pytest.raises(dose.DoseError):
        dose.scan_dose({'Seconds': COLS['Seconds']}, _params())
    with pytest.raises(ValueError):
        dose.scan_dose(COLS, _params(), unit='grays')


def test_burn_against_dose(tmp_path):
    """Synthetic reflectivity burn (constant monitor and counting time): the
    dose axis is the exposure axis times the rate M/(A·g·t), and the limit
    scales with it; the time axis's results are untouched."""
    from lss_core.experiment import Experiment
    exp = Experiment(synth.make_burn_dataset(tmp_path / 'burn'))
    t = exp.burn(1)
    d = exp.burn(1, axis='dose')
    assert t.axis == 'time' and t.x is t.t and t.dose is not None      # the dose is known on the time axis too
    assert d.axis == 'dose' and d.dose_unit == '1e+06 Monc counts'     # no #M gain line in the synthetic file
    assert d.dose_scale == 1e6
    rate = synth.MONITOR / synth.BURN_CTIME / d.dose_scale
    assert np.allclose(d.dose, t.t * rate, rtol=1e-12)
    assert d.dose_total == pytest.approx(t.duration() * rate, rel=1e-12)
    assert d.safe_time()[0] == pytest.approx(t.safe_time()[0] * rate, rel=1e-6)
    assert d.trends['intensity'].best == t.trends['intensity'].best
    cols, arr = d.data()
    assert cols == ['time_s', 'dose_1e+06_Monc_counts', 'intensity', 'intensity_err'] and np.allclose(arr[:, 1], d.dose)
    assert t.data()[0] == ['time_s', 'intensity', 'intensity_err']      # unchanged on the time axis
    assert 'against dose' in d.summary() and '1e+06 Monc counts' in burn_text(d)
    with pytest.raises(ValueError):
        exp.burn(1, axis='fluence')


def burn_text(res):
    from lss_core import burn
    return burn.summary_text(res)


def test_burn_plot_against_dose(tmp_path):
    from matplotlib.figure import Figure
    from lss_core import burn
    from lss_core.experiment import Experiment
    exp = Experiment(synth.make_burn_dataset(tmp_path / 'burn'))
    fig = Figure()
    axes = burn.plot(exp.burn(1, axis='dose'), fig)
    assert 'Dose since the first frame (1e+06 Monc counts)' in axes[-1].get_xlabel()


@pytest.mark.slow
def test_nx_burns_in_photons():
    """NX school's GID burns 14 and 15: the dose in photons, as coded
    (10 keV, 5 µA/V, the calibrated foils at the scans' absorber)."""
    from lss_core.experiment import Experiment
    exp = Experiment(NX)
    for n in (14, 15):
        d = exp.dose(n)
        assert d.unit == 'photons' and np.all(d.per_point > 0)
        r = exp.burn(n, axis='dose')
        assert r.dose_unit.endswith(' photons') and 1 <= r.dose_total < 1000
        assert r.dose_total * r.dose_scale == pytest.approx(d.total(), rel=1e-12)
        rt = exp.burn(n, time='exposure')
        rate = r.dose_total / rt.duration()
        # the monitor rate varies a little during a burn: the dose axis is the exposure axis × the mean rate to 1 %
        assert np.allclose(r.dose, rt.t * rate, rtol=0.01)
    print('NX 14 dose: %.4g photons over %.0f s, absorber %s' % (exp.dose(14).total(), exp.burn(14, time='exposure').duration(),
                                                                 exp.scans[14].parameters.get('Absorber')))
