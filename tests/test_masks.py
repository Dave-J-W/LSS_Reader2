"""Dropped points as a mask over raw points, kept in the workbook (F92's
core, 2026-11-24; D2, F16; lss_core.masks, reflectivity.drop_points,
Experiment.reflectivity(mask=...)).

Invariant (I40): every row of a patched curve sits at the Qz of one raw
point (its origin), and a drop of a point that no earlier join has used
gives the same curve, value for value, as masking that point from the
start."""
import numpy as np
import pytest

import synth
from lss_core import masks, reflectivity as refl
from lss_core.workbook import Workbook


def _scans():
    q = {1: np.linspace(0.01, 0.05, 9), 2: np.linspace(0.04, 0.10, 13), 3: np.linspace(0.09, 0.20, 12)}
    scale = {1: 1.0, 2: 0.37, 3: 0.052}
    per_scan = {}
    rng = np.random.default_rng(5)
    for k, qz in q.items():           # 2 % noise of its own per scan: the factor depends on which points are used
        r = synth.reflectivity(qz) * scale[k] * (1 + 0.01 * np.sin(97 * qz)) * (1 + 0.02 * rng.standard_normal(qz.size))
        per_scan[k] = np.column_stack([qz, r, 0.02 * r])
    points = {1: list(range(9)), 2: list(range(100, 113)), 3: list(range(12))}
    return per_scan, [1, 2, 3], points


def _masked(per_scan, points, removed):
    out, pts = {}, {}
    for k, rows in per_scan.items():
        keep = [i for i, p in enumerate(points[k]) if (k, p) not in removed]
        out[k], pts[k] = rows[keep], [points[k][i] for i in keep]
    return out, pts


def test_the_mask_is_a_set_of_raw_points():
    m = masks.Mask([(7, 3), [7, 1], (8, 0), (7, 3)])
    assert len(m) == 3 and m.pairs() == [[7, 1], [7, 3], [8, 0]] and (7, 1) in m
    assert m.of_scan(7) == [1, 3] and m.scans() == [7, 8]
    m.remove([(7, 1)])
    assert m.pairs() == [[7, 3], [8, 0]] and eval(repr(m), {'masks': masks}) == m
    assert len(m.restore_all()) == 0


def test_masks_are_kept_in_the_workbook(tmp_path):
    path = str(tmp_path / 'x_reader.xlsx')
    wb = Workbook(path)
    assert len(masks.load(wb)) == 0
    masks.save(wb, masks.Mask([(2, 5), (1, 0)]))
    wb.set_settings('fit', {'shape': 'gaussian'})
    wb.save()
    again = Workbook(path)
    assert masks.load(again).pairs() == [[1, 0], [2, 5]]
    assert again.settings('fit') == {'shape': 'gaussian'}          # other sections untouched
    masks.save(again, masks.load(again).restore_all())
    again.save()
    assert len(masks.load(Workbook(path))) == 0
    assert len(Workbook(path).wb.sheetnames) == 7                  # the owner's limit: fewer than eight
    with pytest.raises(ValueError):
        masks.save(again, masks.Mask(), kind='gid')


def test_every_patched_row_sits_at_its_origin_point():
    per_scan, order, points = _scans()
    drops = {0: [1, -2], 1: [[1], [-1, 3]]}             # two presses at join 1
    removed, origins = refl.drop_points(per_scan, order, points, drops)
    patched = refl.patch(per_scan, order, drops, method='legacy')
    assert len(origins) == len(patched)
    qz = {(k, p): per_scan[k][i, 0] for k in per_scan for i, p in enumerate(points[k])}
    assert np.array_equal(patched[:, 0], [qz[o] for o in origins])
    assert not set(removed) & set(origins) and len(set(removed)) == len(removed) == 5


@pytest.mark.parametrize('method', ['legacy', 'joint'])
def test_a_drop_of_a_point_no_earlier_join_used_is_its_mask(method):
    per_scan, order, points = _scans()
    # join 0: a point of scan 2 and one of scan 1 (not yet used); join 1: two of scan 3
    drops = {0: [2, -1], 1: [0, 4]}
    removed, _ = refl.drop_points(per_scan, order, points, drops)
    assert removed == [(2, 102), (1, 8), (3, 4), (3, 0)]
    m_scan, _ = _masked(per_scan, points, set(removed))
    assert np.array_equal(refl.patch(per_scan, order, drops, method=method), refl.patch(m_scan, order, method=method))


def test_a_drop_from_the_curve_so_far_at_a_later_join_is_not_its_mask():
    """D2: the mask is over the raw data, so the point leaves the earlier
    join's fit too; the drop left it there. Same points, other numbers.
    (A point no earlier fit used, e.g. scan 2's at Qz 0.09, far from join
    0's overlap, gives the same curve either way.)"""
    per_scan, order, points = _scans()
    drops = {1: [-12]}                       # scan 1's point at Qz 0.045, in join 0's overlap: its fit used it
    removed, origins = refl.drop_points(per_scan, order, points, drops)
    assert removed == [(1, 7)]
    m_scan, m_pts = _masked(per_scan, points, set(removed))
    a, b = refl.patch(per_scan, order, drops, method='legacy'), refl.patch(m_scan, order, method='legacy')
    assert np.array_equal(a[:, 0], b[:, 0]) and not np.allclose(a[:, 1], b[:, 1], rtol=1e-9, atol=0)
    _, m_origins = refl.drop_points(m_scan, order, m_pts, None)
    assert m_origins == origins


def test_drop_points_says_what_does_not_fit():
    per_scan, order, points = _scans()
    with pytest.raises(ValueError, match='points for'):
        refl.drop_points(per_scan, order, {**points, 2: [0, 1]}, None)
    far = {**per_scan, 3: per_scan[3] + [1.0, 0, 0]}
    with pytest.raises(ValueError, match='does not overlap'):
        refl.drop_points(far, order, points, None)


def test_reflectivity_leaves_the_masked_points_out(dataset):
    from lss_core.experiment import Experiment
    exp = Experiment(dataset)
    full = exp.reflectivity([1, 2])
    assert full.points == {1: list(range(9)), 2: list(range(7))} and full.masked == [] and full.settings['mask'] is None
    r = exp.reflectivity([1, 2], mask=[(1, 3), (2, 6), (9, 0)])          # scan 9 is not in the reduction
    assert r.masked == [(1, 3), (2, 6)] and r.settings['mask'] == [[1, 3], [2, 6]]
    assert r.points[1] == [0, 1, 2, 4, 5, 6, 7, 8] and r.points[2] == list(range(6))
    by_points = exp.reflectivity([1, 2], points={1: [0, 1, 2, 4, 5, 6, 7, 8], 2: list(range(6))})
    assert np.array_equal(r.patched, by_points.patched)
    # the window's drops turned into a mask give the same curve (drops of points no earlier join used)
    drops = {0: [1, -2]}
    removed, _ = refl.drop_points(full.per_scan, full.order, full.points, drops)
    assert np.array_equal(exp.reflectivity([1, 2], drops=drops).patched, exp.reflectivity([1, 2], mask=removed).patched)


def test_a_masked_point_of_a_repeat_masks_the_merged_point(tmp_path):
    from lss_core.experiment import Experiment
    exp = Experiment(synth.make_identical_scans_dataset(tmp_path / 'same'))
    full = exp.reflectivity(sorted(exp.scans), merge_repeats=True)
    merged_into = {s for s in full.per_scan}
    gone = [s for s in sorted(exp.scans) if s not in merged_into and exp.scans[s].detector == 'Pilatus']
    assert gone, 'the dataset has a repeat merged away'
    rep = gone[0]
    first = [s for s in full.per_scan if len(full.per_scan[s]) == len(exp.reflectivity([rep]).per_scan[rep])
             and s < rep][0]
    a = exp.reflectivity(sorted(exp.scans), merge_repeats=True, mask=[(rep, 2)])
    b = exp.reflectivity(sorted(exp.scans), merge_repeats=True, mask=[(first, 2)])
    assert a.masked == b.masked == [(first, 2)] and np.array_equal(a.patched, b.patched)
