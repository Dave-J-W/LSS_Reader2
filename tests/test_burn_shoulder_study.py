"""The P44 shoulder study (tests/tools/burn_shoulder_study.py): a tiny run
of the tool, and the NX school numbers its summary quotes."""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tests', 'tools'))
import burn_shoulder_study as S          # noqa: E402

NX = os.path.join(ROOT, S.NX)


def test_a_tiny_run_reads_the_truth():
    rows = S.run(parts=('A', 'B'), replicates=2, workers=1, cases=['nx15_like'], shapes=['gaussian'])
    assert {(r['part'], r['monitor']) for r in rows} == {('A', 1e7)} | {('B', m) for m in S.PART_B['monitors']}
    a = {(r['estimator'], r['quantity']): r for r in rows if r['part'] == 'A'}
    assert set(e for e, _ in a) == set(S.ESTIMATORS) and ('separated', 'shoulder') in a
    assert ('stretched', 'shoulder') not in a and ('separated_held', 'shoulder') not in a
    assert a['separated', 'intensity']['truth'] == pytest.approx(-0.13, abs=1e-9)
    assert a['separated', 'fwhm']['truth'] == pytest.approx(0.2, abs=1e-9)
    # an NX 15-like burn (broadens 20 %, fades 13 %): separated reads the fade, stretched nearly none
    assert abs(a['separated', 'intensity']['bias']) < 0.01 and abs(a['separated_held', 'intensity']['bias']) < 0.01
    assert a['stretched', 'intensity']['bias'] > 0.1
    assert a['separated', 'intensity']['right'] == 1.0 and a['separated', 'intensity']['n'] == 2


def test_the_nx_monitors_give_an_nx_frames_error():
    """NX_MONITORS: at these monitors a synthetic frame's stretched
    intensity has the error of an NX school frame (3.8 % on burn 14, 2.0 %
    on 15: the slow test below measures them); as measured, 3.9 % and 2.1 %."""
    from lss_core import burn
    from synthetic import burn_profiles as bp
    for scan, nx in ((14, 0.038), (15, 0.020)):
        rel = []
        for seed in range(4):
            prof, _ = bp.profiles(change='none', seed=seed, monitor=S.NX_MONITORS[scan])
            i, s = burn.measure_gid(prof, estimator='stretched')[0]['intensity']
            rel.append(np.mean(s / i))
        assert np.mean(rel) == pytest.approx(nx, rel=0.12), scan
    assert set(S.NX_MONITORS.values()) <= set(S.PART_B['monitors'])


def test_the_mean_frames_noise():
    """mean_frame_noise on synthetic NX 15-like burns (the summary's section 6
    and hand-off 10 quote these): 0.03 %, 0.35 % and 0.85 % of the peak at
    monitor 1e7, 6e4 and 1e4."""
    from lss_core import burn
    from synthetic import burn_profiles as bp
    for monitor, want in ((1e7, 0.00027), (6e4, 0.0035), (1e4, 0.0085)):
        prof, _ = bp.profiles(seed=0, monitor=monitor, **S.CASES['nx15_like'])
        window = burn.measure_gid(prof)[2]
        assert S.mean_frame_noise(prof, window) == pytest.approx(want, rel=0.1), monitor


def test_the_core_can_be_varied():
    """--core (the OUTPUT_DECISIONS row of SEPARATE_CORE): 1.0 and 2.0 FWHM read a broadening as 1.5 does."""
    from lss_core import burn
    for core in (1.0, 2.0):
        rows = S.run(parts=('A',), replicates=2, workers=1, cases=['broaden'], shapes=['gaussian'], core=core)
        r = [x for x in rows if x['estimator'] == 'separated' and x['quantity'] == 'intensity'][0]
        assert abs(r['bias']) < 0.01
    assert burn.SEPARATE_CORE == 1.5          # set back after the run


def test_read_with_reference_is_measure_gid_with_the_frames_mean():
    """Part R measures each frame against a chosen mean frame; with the
    frames' own mean it must give the reader's numbers exactly."""
    from lss_core import burn
    from synthetic import burn_profiles as bp
    prof, _ = bp.profiles(change='broaden', seed=4, monitor=S.NX_MONITORS[15])
    window = burn.measure_gid(prof, estimator='stretched')[2]
    mean = np.mean([p[:, 1] for p in prof], axis=0)
    for e in ('stretched', 'separated'):
        want = burn.measure_gid(prof, qxy_range=window, estimator=e)[0]['intensity'][0]
        assert np.allclose(S.read_with_reference(prof, mean, window, e)[0], want, rtol=1e-12, atol=0)
        # the reader's own window and found peak (no typed range)
        v, ref, win, _ = burn.measure_gid(prof, estimator=e)
        got = S.read_with_reference(prof, mean, win, e, ref['found'])
        assert np.allclose(got[0], v['intensity'][0], rtol=1e-12, atol=0)
        assert np.allclose(got[1], v['intensity'][1], rtol=1e-12, atol=0)


def test_a_frame_that_will_not_fit_is_nan_not_the_end(monkeypatch):
    """A real GID burn (private survey, 2026-11-27) stopped the runner: one
    frame's fit against the smoothed mean ran out of evaluations. As
    measure_gid does, that frame is NaN and the others are read."""
    from lss_core import burn
    from synthetic import burn_profiles as bp
    prof, _ = bp.profiles(change='broaden', seed=4, monitor=S.NX_MONITORS[15])
    window = burn.measure_gid(prof, estimator='stretched')[2]
    mean = np.mean([p[:, 1] for p in prof], axis=0)
    want = S.read_with_reference(prof, mean, window, 'stretched')[0]
    real, calls = burn._stretch_fit, []

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) == 3:
            raise RuntimeError('Optimal parameters not found: The maximum number of function evaluations is exceeded.')
        return real(*a, **k)
    monkeypatch.setattr(burn, '_stretch_fit', flaky)
    got, err = S.read_with_reference(prof, mean, window, 'stretched')
    assert np.isnan(got[2]) and np.isnan(err[2])
    keep = np.arange(len(got)) != 2
    assert np.allclose(got[keep], want[keep], rtol=1e-12, atol=0)


def test_the_published_real_burns_give_section_8s_counts(tmp_path):
    """Section 8's figures come from the published per-burn summary alone
    (no private data): its counts are the section's."""
    got = S.real_figures(str(tmp_path), os.path.join(ROOT, S.REAL_CSV),
                         os.path.join(ROOT, 'docs', 'studies', 'burn_shoulder', 'reference_noise.csv'))
    assert got == dict(well_measured=119, read=155, failed=79, wide=5, differ=12)
    assert (tmp_path / 'R1_stretched_vs_separated.png').exists() and (tmp_path / 'R2_reference_shift.png').exists()


def test_the_explaining_figures_give_section_8s_counts(tmp_path):
    """R3-R7 (how section 8's numbers are made) from the published
    summaries alone: each states the counts the section quotes."""
    got = S.explain_figures(str(tmp_path))
    assert got == dict(cut_frame_rel_error=10, cut_change=7, cut_chi2=20, cut_nan=8, q1_z_over_2=20,
                       q1_verdicts_differ=12, q2_three=15, q2_with_shoulder=54, q3_split_lower=39, q3_with_shoulder=54,
                       q5_series=14, q5_changed=3)
    for name in ('R3_selection', 'R4_q1_disagreement', 'R5_q2_shoulder', 'R6_q3_fit_quality', 'R7_q5_dose_or_time'):
        assert (tmp_path / (name + '.png')).exists()


def test_part_r_runs(tmp_path):
    rows, nx = S.reference_check(str(tmp_path), replicates=2, workers=1, monitors=(1e7,), cases=('fade',))
    assert nx == []
    assert {(r['estimator'], r['reference']) for r in rows} == {(e, k) for e in ('stretched', 'separated')
                                                                for k in S.REFERENCES}
    assert all(r['n'] == 2 for r in rows)
    separated = {r['reference']: r for r in rows if r['estimator'] == 'separated'}
    assert all(abs(r['bias']) < 0.01 for r in separated.values())       # at high counts no reference matters
    assert (tmp_path / 'S6_reference.png').exists() and (tmp_path / 'reference_noise.csv').exists()


def test_change_of_a_linear_fit():
    from lss_core import trends
    t = np.arange(21) * 10.0 + 5
    y = 2.0 * (1 - 0.2 * t / 210)
    c = trends.compare(t, y + 1e-4 * np.sin(t), np.full(21, 1e-3), models=('constant', 'linear'))
    v, s = S.change_of(c.fits['linear'], 210.0)
    assert v == pytest.approx(-0.2, abs=1e-3) and 0 < s < 1e-2
    v, s = S.change_of(c.fits['linear'], 210.0, relative=False)
    assert v == pytest.approx(-0.4, abs=2e-3)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_nx_school_burns_under_every_estimator(tmp_path):
    """As measured 2026-11-27 (the summary's section 5). Burn 14: every
    estimator but the one-Gaussian fit reads the intensity and width
    stable; separated's shoulder is steady (−6 % ± 3 %). Burn 15 (×4.7 the
    flux): stretched reads the intensity stable (−1.5 % ± 1.5 %) while
    the width grows 18 %; separated reads a fade of 13 % (separated & held 15 %)
    with the width +21 %, and fits the frames better (χ²/dof 2.2 against
    4.2); the shoulder is steady (−3 % ± 3 %)."""
    rows = S.nx_check(str(tmp_path), NX)
    got = {(r['scan'], r['estimator'], r['quantity']): r for r in rows}
    for e in ('stretched', 'moments', 'separated', 'separated_held'):
        assert got[14, e, 'intensity']['verdict'] == 'stable' and got[14, e, 'fwhm']['verdict'] == 'stable'
    assert got[14, 'separated', 'shoulder']['verdict'] == 'stable'
    assert got[14, 'separated', 'shoulder']['change'] == pytest.approx(-0.06, abs=0.02)
    t15, s15, f15 = got[15, 'stretched', 'intensity'], got[15, 'separated', 'intensity'], got[15, 'separated_held', 'intensity']
    assert t15['verdict'] == 'stable' and t15['change'] == pytest.approx(-0.015, abs=0.01)
    assert s15['verdict'] == 'changing' and s15['change'] == pytest.approx(-0.133, abs=0.01)
    assert f15['verdict'] == 'changing' and f15['change'] == pytest.approx(-0.152, abs=0.01)
    assert got[15, 'separated', 'fwhm']['change'] == pytest.approx(0.21, abs=0.02)
    assert got[15, 'stretched', 'fwhm']['change'] == pytest.approx(0.18, abs=0.02)
    assert got[15, 'separated', 'shoulder']['verdict'] == 'stable'
    assert got[15, 'separated', 'intensity']['frame_chi2_dof'] < 0.6 * got[15, 'stretched', 'intensity']['frame_chi2_dof']
    # a frame's intensity error (the study's NX_MONITORS match it)
    assert got[14, 'stretched', 'intensity']['frame_rel_error'] == pytest.approx(0.038, abs=0.002)
    assert got[15, 'stretched', 'intensity']['frame_rel_error'] == pytest.approx(0.020, abs=0.001)
    assert os.path.exists(tmp_path / 'S5_nx.png') and os.path.exists(tmp_path / 'nx.csv')


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_nx_school_burns_against_a_smoothed_reference():
    """Part R on NX (the summary's section 6, as measured 2026-11-27): read
    against the frames' mean, each burn gives the reader's own number. Read
    against the mean smoothed, burn 15's separated fade moves by −0.3 pp only
    (−13.3 % to −13.6 %, still "changing"), not by the +1 to +2 pp the
    synthetic burns predict at its counts; burn 14 moves by −5.5 pp and
    stays "stable" (as coded: a pin of what was measured, not a truth)."""
    rows = S.reference_nx(NX)
    got = {(r['scan'], r['estimator'], r['reference']): r for r in rows}
    for r in rows:
        if r['reference'] == 'mean':
            assert r['change'] == pytest.approx(r['reader'], abs=1e-9)
    assert got[15, 'separated', 'spline']['verdict'] == 'changing'
    assert got[15, 'separated', 'spline']['change'] == pytest.approx(-0.136, abs=0.005)
    assert got[14, 'separated', 'spline']['verdict'] == 'stable' and got[14, 'stretched', 'spline']['verdict'] == 'stable'
    assert got[14, 'separated', 'spline']['change'] == pytest.approx(-0.055, abs=0.005)


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_the_real_data_runner_on_nx(tmp_path):
    """--real (hand-off 10): finds NX burns 14 and 15 by their command,
    reads them as the summary does, and writes nothing that names them
    into real.csv (the key, private, maps the labels)."""
    rows, key = S.real_check(str(tmp_path), [NX])
    assert [(k['scan'], k['error']) for k in key] == [(14, ''), (15, '')]
    got = {(r['burn'], r['estimator'], r['quantity']): r for r in rows}
    nx = {(r['scan'], r['estimator'], r['quantity']): r for r in S.nx_check(str(tmp_path), NX)}
    for (label, scan) in (('G01', 14), ('G02', 15)):
        for e in S.REAL_ESTIMATORS:
            assert got[label, e, 'intensity']['change'] == pytest.approx(nx[scan, e, 'intensity']['change'], rel=1e-9)
            assert got[label, e, 'intensity']['verdict'] == nx[scan, e, 'intensity']['verdict']
    assert got['G02', 'separated', 'intensity']['smoothed_change'] == pytest.approx(-0.136, abs=0.005)
    assert got['G02', 'separated', 'intensity']['mean_frame_noise'] == pytest.approx(0.0029, abs=0.0002)
    assert got['G01', 'separated', 'intensity']['mean_frame_noise'] == pytest.approx(0.0051, abs=0.0002)
    assert got['G02', 'separated', 'intensity']['b_mean'] == pytest.approx(1.05, abs=0.02)
    text = (tmp_path / 'real.csv').read_text()
    assert 'NX_school' not in text and '20260923' not in text and 'spec' not in text.split('\n')[0]
    assert 'scan' not in text.split('\n')[0].split(',')
    assert 'NX_school' in (tmp_path / 'real_key.csv').read_text()


def test_one_burns_whole_chain_on_nx_15(tmp_path):
    """The chain figure (walkthrough tool, --chain) reads NX burn 15 as section 5 does, and its numbers
    carry no peak position (the same function draws the private burns P1-P4)."""
    import burn_shoulder_walkthrough as W
    got = W.chain_from_file(str(tmp_path), NX, 15, 'NX15')
    assert round(100 * got['stretched_intensity']['change'], 1) == -1.5
    assert round(100 * got['separated_intensity']['change'], 1) == -13.3
    assert round(100 * got['separated_held_intensity']['change'], 1) == -15.2
    assert got['stretched_intensity']['verdict'] == 'stable' and got['separated_intensity']['verdict'] == 'changing'
    assert not any('centre' in k or 'position' in k for k in got)
    assert (tmp_path / 'BC_NX15.png').exists()
