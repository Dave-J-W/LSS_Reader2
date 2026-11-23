"""tests/tools/foil_fit_from_joins.py on synthetic joins: it recovers six
known foil thicknesses from the joins across which Monc/Monp did not
change, and a join whose monitor under-reads a slit change by a factor g
gets residual ln(g)/μ with F = the true change of the beam (synthetic;
the real result is in docs/physics_notes.md, 2026-11-18)."""
import csv
import math
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import foil_fit_from_joins as ff  # noqa: E402

TRUE = np.array([54.7, 112.2, 218.0, 432.1, 862.7, 1725.1])
PAIRS = [(42, 33), (39, 32), (30, 20), (26, 20), (26, 24), (20, 18), (18, 16), (17, 16),
         (33, 21), (40, 33), (30, 22), (20, 14), (25, 22), (17, 12)]


def _write(path, monitor_fault=None):
    fields = ['n_a', 'n_b', 'E_keV', 'step', 'step_err', 'monc_monp_b_over_a', 'chi2_dof', 'excluded']
    rng = np.random.default_rng(1)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        for rep in range(3):
            for a, b in PAIRS:
                d = np.array([((a >> k) & 1) - ((b >> k) & 1) for k in range(6)])
                step = math.exp(-ff.MU_10KEV * d @ TRUE) * (1 + 0.002 * rng.standard_normal())
                w.writerow(dict(n_a=a, n_b=b, E_keV=10, step=step, step_err=0.002 * step,
                                monc_monp_b_over_a=1.0, chi2_dof=1.0, excluded=''))
        if monitor_fault:   # slit opened x2.27, monitor sees only x1.55: r_b too high by 1.465
            a, b = monitor_fault
            d = np.array([((a >> k) & 1) - ((b >> k) & 1) for k in range(6)])
            step = math.exp(-ff.MU_10KEV * d @ TRUE) / (2.27 / 1.55)
            w.writerow(dict(n_a=a, n_b=b, E_keV=10, step=step, step_err=0.002 * step,
                            monc_monp_b_over_a=1.55, chi2_dof=1.0, excluded=''))
        w.writerow(dict(n_a=20, n_b=26, E_keV=10, step=1.0, step_err=0.01,      # adds absorber: unused
                        monc_monp_b_over_a=1.0, chi2_dof=1.0, excluded=''))
        w.writerow(dict(n_a=42, n_b=33, E_keV=30, step=1.0, step_err=0.01,      # Cu energy: unused
                        monc_monp_b_over_a=1.0, chi2_dof=1.0, excluded=''))


def test_recovers_foils_and_flags_a_monitor_that_missed_a_slit_change(tmp_path):
    p = str(tmp_path / 'joins.csv')
    _write(p, monitor_fault=(26, 20))
    rows = ff.load(p)
    assert len(rows) == 3 * len(PAIRS) + 1
    f = ff.fit(rows)
    assert f['rank'] == 6
    assert f['t'] == pytest.approx(TRUE, abs=0.5)
    assert f['kept'].sum() == 3 * len(PAIRS)
    assert f['res'][-1] == pytest.approx(math.log(2.27 / 1.55) / ff.MU_10KEV, abs=0.5)   # ≈ +54 µm
    assert f['F'][-1] == pytest.approx(2.27, rel=0.005)


def test_the_cuts_are_options_and_default_to_the_documented_ones(capsys):
    """The cuts as command-line options (2026-11-23, so that the Tools menu
    can rerun physics_notes' sensitivity check): the defaults print exactly
    what main() prints; the strict cuts keep fewer joins and move each foil
    by under 1 µm (measured: 409 -> 337 joins, at most 0.4 µm)."""
    joins = os.path.join(os.path.dirname(HERE), 'docs', 'handoff_out', '03-answer', 'joins.csv')
    ff.main(joins)
    plain = capsys.readouterr().out
    assert ff.cli([joins]) == 0
    assert capsys.readouterr().out == plain
    loose = ff.fit(ff.load(joins))
    strict = ff.fit(ff.load(joins), monc_tol=0.01, chi2_max=5.0, floor=0.0)
    assert strict['clean'].sum() < loose['clean'].sum()
    assert np.max(np.abs(strict['t'] - loose['t'])) < 0.9
    ff.cli([joins, '--monc-tol', '0.01', '--chi2-max', '5', '--floor', '0'])
    assert 'chi2/dof >= 5)' in capsys.readouterr().out
