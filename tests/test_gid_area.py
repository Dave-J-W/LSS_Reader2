"""MainWindow.calArea: fraction of the beam footprint seen by the detector.

areainfo = [S1 horizontal, S1 vertical, S4 horizontal, S5 horizontal,
            incident angle (rad), sample-detector distance, slit-detector
            distance]; lengths in mm. The second argument is 2-theta in
            degrees. The function also reads the "H slit" pixel count from
            the Pilatus tab.
"""
import pytest

NARROW = [1.0, 0.02, 1.0, 1.0, 0.002, 600.0, 300.0]
WIDE = [1.0, 0.02, 50.0, 50.0, 0.002, 600.0, 300.0]

pytestmark = pytest.mark.gui


def test_whole_footprint_seen_at_small_angle(window):
    for dth in (0, 0.5, 5):
        assert window.calArea(NARROW, dth) == pytest.approx(1.0)


def test_fraction_is_between_zero_and_one(window):
    for dth in (0, 1, 5, 10, 20, 30, 45, 60, 90):
        assert 0.0 < window.calArea(NARROW, dth) <= 1.0 + 1e-12


def test_fraction_falls_with_angle_once_clipped(window):
    values = [window.calArea(NARROW, dth) for dth in (20, 45, 90)]
    assert values == sorted(values, reverse=True)


def test_values_as_coded(window):
    assert window.calArea(NARROW, 20) == pytest.approx(0.735518255583043)
    assert window.calArea(NARROW, 45) == pytest.approx(0.35581816664135324)
    assert window.calArea(NARROW, 90) == pytest.approx(0.2515998322667002)


def test_detector_slit_setting_caps_s5(window):
    # the default "H slit" of 3 pixels (0.516 mm) replaces any wider S5, so
    # opening S4/S5 to 50 mm still only widens S4
    assert window.ui.pilHSlitLineEdit.text() == '3'
    assert window.calArea(WIDE, 60) == pytest.approx(1.0)


@pytest.mark.xfail(strict=True, reason='calArea(-2theta) differs from '
                   'calArea(+2theta) by 2 % for a symmetric geometry')
def test_symmetric_in_two_theta(window):
    assert window.calArea(NARROW, -20) == pytest.approx(window.calArea(NARROW, 20))
