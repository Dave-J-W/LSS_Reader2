"""Fresnel reflectivity as coded in MainWindow.fresnel (no absorption)."""
import numpy as np
import pytest

QC = 0.0217


@pytest.fixture(scope='module')
def fresnel(qapp):
    from mainwindow import MainWindow
    return lambda q, qc=QC: MainWindow.fresnel(None, np.asarray(q, float), qc)


def test_total_reflection_below_qc(fresnel):
    q = np.linspace(1e-4, QC * 0.999, 50)
    assert np.all(fresnel(q) == 1)


def test_continuous_at_qc(fresnel):
    assert fresnel([QC])[0] == pytest.approx(1.0)
    assert fresnel([QC * (1 + 1e-9)])[0] == pytest.approx(1.0, abs=1e-3)


def test_monotonic_decreasing_above_qc(fresnel):
    r = fresnel(np.linspace(QC, 0.7, 500))
    assert np.all(np.diff(r) < 0)


def test_large_q_asymptote(fresnel):
    # R_F -> (qc / 2q)^4, with relative correction of order (qc/q)^2
    q = np.array([0.3, 0.5, 0.7])
    assert fresnel(q) == pytest.approx((QC / 2 / q) ** 4, rel=2 * (QC / 0.3) ** 2)


def test_depends_only_on_q_over_qc(fresnel):
    q = np.linspace(0.5, 20, 40)
    assert fresnel(q * 0.01, 0.01) == pytest.approx(fresnel(q * 0.03, 0.03))


def test_matches_closed_form(fresnel):
    q = np.linspace(QC * 1.01, 0.6, 30)
    s = np.sqrt(q ** 2 - QC ** 2)
    assert fresnel(q) == pytest.approx(((q - s) / (q + s)) ** 2, rel=1e-12)
