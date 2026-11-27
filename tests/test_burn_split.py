"""The split estimators of the GID burn test (P44, 2026-11-27;
lss_core.burn.split_shoulder, measure_gid estimator 'split' and
'split_fixed'): the template with the broad shoulder split off and held
unstretched, so that a broadening peak or a fading one is not read through
the shoulder. Known truth from tests/synthetic/burn_profiles.py; each
change over the test read from a straight line through the frames, as the
study (tests/tools/burn_shoulder_study.py) does."""
import numpy as np
import pytest

from lss_core import burn
from synthetic import burn_profiles as bp

SPLITS = burn.SPLIT_ESTIMATORS


def change(t, v):
    """Relative change over the test from a straight line: slope × t_end / value at 0."""
    a, b = np.polyfit(t, v, 1)
    return a * (t[-1] + 0.5 * (t[1] - t[0])) / b


def read(prof, truth, estimator, quantity='intensity', **kw):
    values = burn.measure_gid(prof, estimator=estimator, **kw)[0]
    return change(truth.t, values[quantity][0])


def test_split_finds_the_shoulder_it_was_given():
    prof, truth = bp.profiles(change='fade', seed=0)
    values, ref, window, details = burn.measure_gid(prof, estimator='split')
    h, m, s = ref['shoulder']
    assert h == pytest.approx(bp.SHOULDER[0], rel=0.02) and m == pytest.approx(bp.SHOULDER[1], abs=5e-4)
    assert s == pytest.approx(bp.SHOULDER[2], rel=0.02)
    assert set(values) == {'intensity', 'centre', 'fwhm', 'shoulder'}
    # the peak's own numbers: the mean frame's peak (its area over the test's mean) and width
    assert ref['peak_fwhm'] == pytest.approx(bp.FWHM, rel=0.03)
    assert ref['peak_area'] == pytest.approx(np.mean(truth.area), rel=0.01)
    assert ref['peak_centre'] == pytest.approx(bp.CENTRE, abs=2e-4)
    assert all(d['ok'] for d in details) and np.mean([d['chi2_dof'] for d in details]) < 1.1
    fixed = burn.measure_gid(prof, estimator='split_fixed')
    assert 'shoulder' not in fixed[0] and all(d['shoulder'] == (1.0, 0.0) for d in fixed[3])


@pytest.mark.parametrize('case, amount', [('broaden', 0.3), ('fade', 0.2), ('shoulder', 0.2)])
def test_split_reads_the_peak_where_the_template_reads_the_shoulder(case, amount):
    """Gaussian shoulder, 3 seeds: the split is within 1 % of the truth on
    the intensity (the template: +15 %, +6 % and +11 %, as coded; the reason
    for P44) and within 2 % on the FWHM."""
    for seed in range(3):
        prof, truth = bp.profiles(change=case, amount=amount, seed=seed)
        true_i, true_w = change(truth.t, truth.area), change(truth.t, truth.fwhm)
        for e in SPLITS:
            assert read(prof, truth, e) == pytest.approx(true_i, abs=0.01), (e, seed)
            assert read(prof, truth, e, 'fwhm') == pytest.approx(true_w, abs=0.02), (e, seed)
        assert read(prof, truth, 'template') - true_i > {'broaden': 0.12, 'fade': 0.04, 'shoulder': 0.08}[case]


def test_a_changing_shoulder_is_read_by_split_and_misleads_split_fixed():
    """The shoulder grows 50 % under a steady peak (the owner, 2026-11-26:
    whether a real one can is not known). 'split' reads the peak steady and
    the shoulder's +50 %; 'split_fixed', which assumes a steady shoulder,
    reads a false +24 % in intensity and +16 % in width (as coded): a
    disagreement between the two is the sign of a changing shoulder."""
    prof, truth = bp.profiles(change='none', shoulder_change=0.5, seed=0)
    true_sh = change(truth.t, truth.shoulder_height)
    assert true_sh == pytest.approx(0.5, abs=1e-9)
    values = burn.measure_gid(prof, estimator='split')[0]
    assert change(truth.t, values['intensity'][0]) == pytest.approx(0.0, abs=0.01)
    assert change(truth.t, values['shoulder'][0]) == pytest.approx(true_sh, abs=0.02)
    res = burn.analyse(truth.t, values, errors='scatter')
    assert res['intensity'].stable and not res['shoulder'].stable
    assert read(prof, truth, 'split_fixed') > 0.15 and read(prof, truth, 'split_fixed', 'fwhm') > 0.1
    assert read(prof, truth, 'template') > 0.1


def test_a_steady_shoulder_amplitude_is_one_within_its_errors():
    """B per frame on a steady shoulder: mean 1, pulls (B − 1)/σ_B of SD
    about 1 (1.08 over 6 seeds: the template, the mean of the same frames,
    shares their noise)."""
    pulls = []
    for seed in range(4):
        prof, _ = bp.profiles(change='fade', seed=seed)
        b = np.array([d['shoulder'] for d in burn.measure_gid(prof, estimator='split')[3]])
        assert np.mean(b[:, 0]) == pytest.approx(1.0, abs=0.002)
        pulls += list((b[:, 0] - 1) / b[:, 1])
    assert 0.8 < np.std(pulls) < 1.3 and abs(np.mean(pulls)) < 0.3


def test_without_a_shoulder_the_split_is_the_template():
    prof, truth = bp.profiles(change='fade', shoulder_shape='none', seed=1)
    tv = burn.measure_gid(prof, estimator='template')[0]
    for e in SPLITS:
        v, ref, _, _ = burn.measure_gid(prof, estimator=e)
        assert ref['shoulder'] is None and 'shoulder' not in v
        for q in ('intensity', 'centre', 'fwhm'):
            assert np.array_equal(v[q][0], tv[q][0]) and np.array_equal(v[q][1], tv[q][1])


@pytest.mark.parametrize('shape', ['lorentzian', 'asymmetric', 'two'])
def test_other_shoulder_shapes_are_read_better_than_by_the_template(shape):
    """A shoulder that is not a Gaussian (the split fits a Gaussian to it):
    the split's bias is smaller than the template's in every case (as
    measured, 2 seeds: by 2.0–7.9 × for a Lorentzian or a lopsided
    shoulder, 1.4–4.2 × for a narrow second component beside the peak,
    where no estimator copes: the split reads a 20 % fade as 15 %, and as
    8 % under a shoulder three times stronger)."""
    for case, amount in (('broaden', 0.3), ('fade', 0.2), ('shoulder', 0.2)):
        prof, truth = bp.profiles(change=case, amount=amount, seed=0, shoulder_shape=shape)
        true_i = change(truth.t, truth.area)
        tb = abs(read(prof, truth, 'template') - true_i)
        for e in SPLITS:
            factor = 0.8 if shape == 'two' else 0.6
            assert abs(read(prof, truth, e) - true_i) < factor * tb, (shape, case, e)


def test_a_typed_range_and_the_drawn_fit():
    prof, truth = bp.profiles(change='fade', seed=1)
    values, ref, window, details = burn.measure_gid(prof, qxy_range=(1.40, 1.55), estimator='split')
    assert window == (1.40, 1.55) and ref['found'] is None and ref['shoulder'] is not None
    assert change(truth.t, values['intensity'][0]) == pytest.approx(-0.2, abs=0.01)
    for e in ('template',) + SPLITS:
        v, ref, window, details = burn.measure_gid(prof, estimator=e)
        x = ref['x']
        sel = (prof[3][:, 0] >= window[0]) & (prof[3][:, 0] <= window[1])
        drawn = burn.frame_model(ref, details[3], x)
        total = drawn[0] if e in SPLITS else drawn
        r = (prof[3][sel, 1] - total) / prof[3][sel, 2]
        dof = len(x) - len(details[3]['params'])
        assert np.sum(r ** 2) / dof == pytest.approx(details[3]['chi2_dof'], rel=1e-6)
        if e in SPLITS:
            assert np.allclose(sum(drawn[1]), total)
    v, ref, _, details = burn.measure_gid(prof, estimator='moments')
    assert burn.frame_model(ref, details[0], ref['x']) is None
    with pytest.raises(ValueError, match='split_fixed'):
        burn.measure_gid(prof, estimator='halves')
