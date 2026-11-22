"""Live updates (owner, 2026-11-22; F1-F5, L1-L4): saved results remade
from their recipes when their series grows; recipes parsed, never executed."""
import os

import numpy as np
import pytest

import synth
from lss_core import live, workbook
from lss_core.experiment import Experiment


def test_recipes_are_parsed_not_executed():
    c = live.parse("from lss_core.gid import GIDParams\n"
                   "gid = exp.gid([11, 12], axes='Q', params=GIDParams(response='beam'), points={11: [0, 1]})\n"
                   "gid.save('result')")
    assert c.method == 'gid' and c.args == [[11, 12]] and c.kwargs['params'].response == 'beam'
    flu = live.parse("flu = exp.fluorescence([3, 4], window=(1, 1000))\nflu.merge(0.001, x='qz')\n"
                     "flu.save('result', x='qz')")
    assert flu.merges == [dict(window=0.001, x='qz')]
    for bad in ("import os\nref = exp.reflectivity([1])",
                "ref = exp.reflectivity([1], slit=__import__('os').system('true'))",
                "ref = exp.reflectivity([1])\nref.__class__",
                "x = open('f')",
                "ref = exp.reflectivity([1])\nref2 = exp.gid([2])",
                "# a comment only"):
        with pytest.raises(live.RecipeError):
            live.parse(bad)


def test_with_scans_rewrites_the_scans_and_drops_points():
    r = live.with_scans("ref = exp.reflectivity([6, 7], slit=(21, 11), points={7: [0, 1]})\nref.save('result')",
                        [6, 7, 8])
    assert "exp.reflectivity([6, 7, 8], slit=(21, 11))" in r and 'points' not in r
    assert live.with_scans("burn = exp.burn(14)\nprint(burn.summary())", [14]).startswith('burn = exp.burn(14)')


def test_a_burn_result_is_remade_on_the_grown_scan(tmp_path):
    spec = synth.make_burn_dataset(tmp_path / 'burn')
    exp = Experiment(spec)
    call, res, used = live.remake("burn = exp.burn(1, points=[0, 1, 2])\nprint(burn.summary())", [1], exp)
    assert used == [1] and len(res.t) == synth.BURN_FRAMES             # points dropped: the whole scan
    kind, items = live.item_for(call, res, used)
    assert kind == 'burn test' and items[0]['scans'] == [1] and items[0]['data'].shape[0] == synth.BURN_FRAMES


def test_stale_by_points_and_superseded(tmp_path):
    from lss_core.series import Series
    s = Series('inferred-1', 'burn', None, {1: 1}, status='complete', inferred=True)
    wb = workbook.Workbook(str(tmp_path / 'f_reader.xlsx'))
    rid = wb.add_result('burn test', [1], np.ones((8, 3)), ['t', 'I', 'dI'],
                        series=workbook.series_for([1], [s], {1: 8}), recipe='burn = exp.burn(1)')
    assert wb.results()[0]['series_points'] == 8
    assert wb.mark_stale([s], {1: 8}) == {}
    assert wb.mark_stale([s], {1: 21}) == {rid: 'points 8 → 21'}
    wb.supersede(rid, 'R0002')
    assert wb.results()[0]['stale'].startswith('superseded by R0002')
    assert wb.mark_stale([s], {1: 30}) == {}                            # a remade row is left alone
