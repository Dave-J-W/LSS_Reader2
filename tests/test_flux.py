"""Photons/s from monitor counts (F54; lss_core/flux.py), checked against the
worked examples of the xray_fluxor hand-off (docs/handoff/
xray_fluxor_counts_to_photons.md §3: 500 nA/V, dark 200 Hz, 98.99 kPa,
24.9 °C), which the hand-off says its route-B arithmetic reproduces."""
import pytest

from lss_core import flux


@pytest.mark.parametrize('lane, kev, rate, best, low, high', [
    ('MonP', 10.0, 224.0e3, 9.776e11, 9.424e11, 10.128e11),
    ('MonP', 30.0, 75.2e3, 6.320e12, 5.077e12, 7.784e12),
    ('MonC', 30.0, 75.2e3, 4.916e12, 4.182e12, 5.811e12),
])
def test_reproduces_the_handoff_examples(lane, kev, rate, best, low, high):
    b, lo, hi, flags = flux.photons_per_second(rate, 1.0, kev, 500e-9, lane, dark_hz=200.0,
                                               temp_c=24.9, pressure_kpa=98.99)
    assert b == pytest.approx(best, rel=2e-3)          # table rounding (3 figures)
    assert lo == pytest.approx(low, rel=2e-3) and hi == pytest.approx(high, rel=2e-3)


def test_scalings_and_flags():
    a = flux.photons_per_second(1e5, 1.0, 10.0, 500e-9)
    b = flux.photons_per_second(1e5, 1.0, 10.0, 5e-6)
    assert b[0] / a[0] == pytest.approx(10.0)          # x10 at 5 uA/V (hand-off §5)
    assert len(a[3]) == 3 and a[3][0] == 'dark not known: 50 Hz used'   # MonC dark 50 Hz (owner); T, P assumed
    assert flux.photons_per_second(1e5, 1.0, 10.0, 5e-6, lane='MonP')[3][0] == 'dark not known: 0 Hz used'
    warm = flux.photons_per_second(1e5, 1.0, 10.0, 5e-6, temp_c=25.9, pressure_kpa=98.99, dark_hz=0)
    cold = flux.photons_per_second(1e5, 1.0, 10.0, 5e-6, temp_c=24.9, pressure_kpa=98.99, dark_hz=0)
    assert warm[0] / cold[0] == pytest.approx(1.0034)
    assert flux.per_hz(10.0, 'MonC') == pytest.approx(4.37e6) and flux.per_hz(10.0, 'MonP') == pytest.approx(4.37e6)   # same below 18 keV
    assert flux.per_hz(20.0, 'MonC') == pytest.approx(2.02e7 * 1.02)
    with pytest.raises(ValueError):
        flux.per_hz(40.0)
    assert flux.photons_per_second(1e5, 0.0, 10.0, 5e-6)[3] == ['count time <= 0']
