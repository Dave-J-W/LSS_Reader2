"""tests/tools/gid_column_groups.py on the public NX school GID scans 11 + 12:
it writes its figures and tables, every group gives a finite level factor
that is the core's own (the tool's recomputed cells reproduce
lss_core.pinhole.join_levels), and one group is exactly the reader's patch.

Kinds of assertion (docs/TESTING.md): invariants. The tool restricts a patch
to a group of columns by narrowing the S5 opening in a copy of each frame's
header values; S5 enters lss_core only through pinhole.frame_columns, and the
tool checks that every frame then keeps exactly its usable columns within the
group. With one group spanning every usable column, pinhole_patch therefore
receives the same frames, columns, weights and grids as Experiment.gid, so the
factor must agree to rounding: 1e-12 relative (the arithmetic is the same,
so in practice it is bit for bit). Maps in 2θ–β (--axes Angles) keep the
test fast: the Q regridding (scipy griddata) is the window's and is not
what is tested here."""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import gid_column_groups as tool  # noqa: E402

from lss_core.experiment import Experiment  # noqa: E402


def test_writes_its_files_and_every_group_has_a_finite_factor(tmp_path):
    S = tool.main(['--out', str(tmp_path), '--axes', 'Angles'])
    names = sorted(os.listdir(tmp_path))
    assert names == ['NX_S11_12_factors.csv', 'NX_S11_12_join.png', 'NX_S11_12_maps.png', 'NX_S11_12_summary.json']
    for n in names:
        assert os.path.getsize(tmp_path / n) > 0
    sets = S['sets']
    assert [s['name'] for s in sets] == ['all columns', 'group 1', 'group 2', 'group 3']
    assert [tuple(s['columns']) for s in sets[1:]] == [tuple(g) for g in S['groups']]
    assert S['groups'][0][0] == sets[0]['columns'][0] and S['groups'][-1][1] == sets[0]['columns'][1]
    for s in sets:
        assert s['status'] == 'ok'
        (j,) = s['joins']
        for k in ('factor', 'error', 'pooled', 'pooled_error', 'chi2'):
            assert j[k] is not None and math.isfinite(j[k]), (s['name'], k)
        assert j['error'] > 0 and j['cells'] > 0
        assert j['factor'] == j['core_factor']          # what the figures show is the core's factor
    for s in sets[1:]:
        c = s['against_all_columns'][0]
        assert all(math.isfinite(c[k]) for k in ('scale_lower', 'scale_upper', 'joined_relative',
                                                 'all_columns_on_range_pooled'))
    with open(tmp_path / 'NX_S11_12_factors.csv') as f:
        rows = list(csv.DictReader(f))
    assert [r['set'] for r in rows] == [s['name'] for s in sets]
    assert all(math.isfinite(float(r['factor'])) for r in rows)


def test_one_group_is_the_readers_patch(tmp_path):
    S = tool.main(['--groups', '1', '--out', str(tmp_path), '--axes', 'Angles'])
    every, one = S['sets']
    assert tuple(one['columns']) == tuple(every['columns'])
    assert one['level_columns'] == every['level_columns']
    reader = [j for j in Experiment(tool.NX).gid([11, 12]).joins if j['kind'].startswith('vertical')]
    assert len(reader) == 1
    for s in (every, one):
        (j,) = s['joins']
        assert math.isclose(j['factor'], reader[0]['factor'], rel_tol=1e-12, abs_tol=0)
        assert math.isclose(j['error'], reader[0]['error'], rel_tol=1e-12, abs_tol=0)
        assert j['cells'] == every['joins'][0]['cells'] and j['beta_bins'] == reader[0]['points']


def test_private_data_may_not_be_written_into_the_repository(tmp_path):
    other = tmp_path / 'other_spec'
    other.write_text('')
    for out in ('docs/figures/gid_column_groups', 'tests'):
        try:
            tool.main(['--spec', str(other), '--out', out])
        except SystemExit as e:
            assert 'private data' in str(e)
        else:
            raise AssertionError('wrote private data into %s' % out)
