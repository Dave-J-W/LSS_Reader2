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
    assert set(e for e, _ in a) == set(S.ESTIMATORS) and ('split', 'shoulder') in a
    assert ('template', 'shoulder') not in a and ('split_fixed', 'shoulder') not in a
    assert a['split', 'intensity']['truth'] == pytest.approx(-0.13, abs=1e-9)
    assert a['split', 'fwhm']['truth'] == pytest.approx(0.2, abs=1e-9)
    # an NX 15-like burn (broadens 20 %, fades 13 %): the split reads the fade, the template nearly none
    assert abs(a['split', 'intensity']['bias']) < 0.01 and abs(a['split_fixed', 'intensity']['bias']) < 0.01
    assert a['template', 'intensity']['bias'] > 0.1
    assert a['split', 'intensity']['right'] == 1.0 and a['split', 'intensity']['n'] == 2


def test_the_nx_monitors_give_an_nx_frames_error():
    """NX_MONITORS: at these monitors a synthetic frame's template
    intensity has the error of an NX school frame (3.8 % on burn 14, 2.0 %
    on 15: the slow test below measures them); as measured, 3.9 % and 2.1 %."""
    from lss_core import burn
    from synthetic import burn_profiles as bp
    for scan, nx in ((14, 0.038), (15, 0.020)):
        rel = []
        for seed in range(4):
            prof, _ = bp.profiles(change='none', seed=seed, monitor=S.NX_MONITORS[scan])
            i, s = burn.measure_gid(prof, estimator='template')[0]['intensity']
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
    """--core (the OUTPUT_DECISIONS row of SPLIT_CORE): 1.0 and 2.0 FWHM read a broadening as 1.5 does."""
    from lss_core import burn
    for core in (1.0, 2.0):
        rows = S.run(parts=('A',), replicates=2, workers=1, cases=['broaden'], shapes=['gaussian'], core=core)
        r = [x for x in rows if x['estimator'] == 'split' and x['quantity'] == 'intensity'][0]
        assert abs(r['bias']) < 0.01
    assert burn.SPLIT_CORE == 1.5          # set back after the run


def test_read_with_reference_is_measure_gid_with_the_frames_mean():
    """Part R measures each frame against a chosen mean frame; with the
    frames' own mean it must give the reader's numbers exactly."""
    from lss_core import burn
    from synthetic import burn_profiles as bp
    prof, _ = bp.profiles(change='broaden', seed=4, monitor=S.NX_MONITORS[15])
    window = burn.measure_gid(prof, estimator='template')[2]
    mean = np.mean([p[:, 1] for p in prof], axis=0)
    for e in ('template', 'split'):
        want = burn.measure_gid(prof, qxy_range=window, estimator=e)[0]['intensity'][0]
        assert np.allclose(S.read_with_reference(prof, mean, window, e)[0], want, rtol=1e-12, atol=0)
        # the reader's own window and found peak (no typed range)
        v, ref, win, _ = burn.measure_gid(prof, estimator=e)
        got = S.read_with_reference(prof, mean, win, e, ref['found'])
        assert np.allclose(got[0], v['intensity'][0], rtol=1e-12, atol=0)
        assert np.allclose(got[1], v['intensity'][1], rtol=1e-12, atol=0)


def test_part_r_runs(tmp_path):
    rows, nx = S.reference_check(str(tmp_path), replicates=2, workers=1, monitors=(1e7,), cases=('fade',))
    assert nx == []
    assert {(r['estimator'], r['reference']) for r in rows} == {(e, k) for e in ('template', 'split')
                                                                for k in S.REFERENCES}
    assert all(r['n'] == 2 for r in rows)
    split = {r['reference']: r for r in rows if r['estimator'] == 'split'}
    assert all(abs(r['bias']) < 0.01 for r in split.values())       # at high counts no reference matters
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
    stable; the split's shoulder is steady (−6 % ± 3 %). Burn 15 (×4.7 the
    flux): the template reads the intensity stable (−1.5 % ± 1.5 %) while
    the width grows 18 %; the split reads a fade of 13 % (split_fixed 15 %)
    with the width +21 %, and fits the frames better (χ²/dof 2.2 against
    4.2); the shoulder is steady (−3 % ± 3 %)."""
    rows = S.nx_check(str(tmp_path), NX)
    got = {(r['scan'], r['estimator'], r['quantity']): r for r in rows}
    for e in ('template', 'moments', 'split', 'split_fixed'):
        assert got[14, e, 'intensity']['verdict'] == 'stable' and got[14, e, 'fwhm']['verdict'] == 'stable'
    assert got[14, 'split', 'shoulder']['verdict'] == 'stable'
    assert got[14, 'split', 'shoulder']['change'] == pytest.approx(-0.06, abs=0.02)
    t15, s15, f15 = got[15, 'template', 'intensity'], got[15, 'split', 'intensity'], got[15, 'split_fixed', 'intensity']
    assert t15['verdict'] == 'stable' and t15['change'] == pytest.approx(-0.015, abs=0.01)
    assert s15['verdict'] == 'changing' and s15['change'] == pytest.approx(-0.133, abs=0.01)
    assert f15['verdict'] == 'changing' and f15['change'] == pytest.approx(-0.152, abs=0.01)
    assert got[15, 'split', 'fwhm']['change'] == pytest.approx(0.21, abs=0.02)
    assert got[15, 'template', 'fwhm']['change'] == pytest.approx(0.18, abs=0.02)
    assert got[15, 'split', 'shoulder']['verdict'] == 'stable'
    assert got[15, 'split', 'intensity']['frame_chi2_dof'] < 0.6 * got[15, 'template', 'intensity']['frame_chi2_dof']
    # a frame's intensity error (the study's NX_MONITORS match it)
    assert got[14, 'template', 'intensity']['frame_rel_error'] == pytest.approx(0.038, abs=0.002)
    assert got[15, 'template', 'intensity']['frame_rel_error'] == pytest.approx(0.020, abs=0.001)
    assert os.path.exists(tmp_path / 'S5_nx.png') and os.path.exists(tmp_path / 'nx.csv')


@pytest.mark.slow
@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_nx_school_burns_against_a_smoothed_reference():
    """Part R on NX (the summary's section 6, as measured 2026-11-27): read
    against the frames' mean, each burn gives the reader's own number. Read
    against the mean smoothed, burn 15's split fade moves by −0.3 pp only
    (−13.3 % to −13.6 %, still "changing"), not by the +1 to +2 pp the
    synthetic burns predict at its counts; burn 14 moves by −5.5 pp and
    stays "stable" (as coded: a pin of what was measured, not a truth)."""
    rows = S.reference_nx(NX)
    got = {(r['scan'], r['estimator'], r['reference']): r for r in rows}
    for r in rows:
        if r['reference'] == 'mean':
            assert r['change'] == pytest.approx(r['reader'], abs=1e-9)
    assert got[15, 'split', 'spline']['verdict'] == 'changing'
    assert got[15, 'split', 'spline']['change'] == pytest.approx(-0.136, abs=0.005)
    assert got[14, 'split', 'spline']['verdict'] == 'stable' and got[14, 'template', 'spline']['verdict'] == 'stable'
    assert got[14, 'split', 'spline']['change'] == pytest.approx(-0.055, abs=0.005)


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
    assert got['G02', 'split', 'intensity']['smoothed_change'] == pytest.approx(-0.136, abs=0.005)
    assert got['G02', 'split', 'intensity']['mean_frame_noise'] == pytest.approx(0.0029, abs=0.0002)
    assert got['G01', 'split', 'intensity']['mean_frame_noise'] == pytest.approx(0.0051, abs=0.0002)
    assert got['G02', 'split', 'intensity']['b_mean'] == pytest.approx(1.05, abs=0.02)
    text = (tmp_path / 'real.csv').read_text()
    assert 'NX_school' not in text and '20260923' not in text and 'spec' not in text.split('\n')[0]
    assert 'scan' not in text.split('\n')[0].split(',')
    assert 'NX_school' in (tmp_path / 'real_key.csv').read_text()
