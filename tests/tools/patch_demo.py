"""Fit demonstrator on synthetic data (owner, 2026-11-22): reflectivity
patching by every method, and burn line cuts by every estimator, with the
truth beside them. Report: docs/reports/patch_demo.md.

    python tests/tools/patch_demo.py                     # the window (space bar: new replicate)
    python tests/tools/patch_demo.py --mode burn --seed 5
    python tests/tools/patch_demo.py --save docs/figures/patch_demo   # the report's figures, headless (Agg)
    python tests/tools/patch_demo.py --save DIR --quick  # the same with few replicates (a smoke run)
    python tests/tools/patch_demo.py --views DIR         # only the two default views as PNG
    python tests/tools/patch_demo.py --set truth=water --set plan=edge      # a documented variation
    python tests/tools/patch_demo.py --mode burn --set change=fade --set monitor=1e5

``--survey N`` prints a survey over N replicates instead of opening the
window (reflectivity: every method's pull mean and SD per join; burn:
every estimator's bias, scatter and stable fraction per quantity).

``--set KEY=VALUE`` (repeatable) sets a field of the demonstration's
settings before the window opens or the views are drawn: reflectivity
fields of ``demonstrator.refl.Config`` (truth, plan, counts, thickness,
foil_error, errors, monitor), burn fields of ``demonstrator.burnmode.Config``
(change, amount, n, monitor, ctime, shoulder_scale). A key belongs to the
mode's settings first, then to the other's; ``refl.monitor=poisson`` or
``burn.monitor=1e5`` names them. The report figures (``--save``) keep
their own fixed settings.

Run from the repository root (or anywhere: the paths are set from this
file). The computation is in tests/demonstrator/ (GUI-free, used by the
tests); the window in tests/demonstrator/window.py. All data are
synthetic, so the figures are public. ``--save`` also writes
``numbers.json`` (every number the report quotes) and per-method summary
CSVs into DIR; ``--rows DIR2`` adds the per-replicate CSVs (large).
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))


def configs(pairs, mode='refl'):
    """(refl.Config, burnmode.Config) with the ``KEY=VALUE`` pairs applied,
    each value converted to the type of the field's default. A key goes to
    the settings of ``mode`` when they have it, else to the other's;
    ``refl.KEY`` or ``burn.KEY`` says which (``monitor`` is in both)."""
    import dataclasses
    from demonstrator import burnmode as bm, refl
    cfgs = {'refl': refl.Config(), 'burn': bm.Config()}
    for pair in pairs or ():
        if '=' not in pair:
            raise SystemExit('--set needs KEY=VALUE, not %r' % pair)
        key, text = (x.strip() for x in pair.split('=', 1))
        where, _, name = key.rpartition('.')
        order = [where] if where else [mode, 'burn' if mode == 'refl' else 'refl']
        cfg = next((cfgs[k] for k in order if k in cfgs and name in {f.name for f in dataclasses.fields(cfgs[k])}),
                   None)
        if cfg is None:
            raise SystemExit('--set %s: not a setting of the demonstrator (refl.Config or burnmode.Config)' % key)
        old = getattr(cfg, name)
        try:
            if isinstance(old, bool):
                value = text.lower() in ('1', 'true', 'yes', 'on')
            elif isinstance(old, int):
                value = int(float(text))
            elif isinstance(old, float) or old is None:
                value = None if text.lower() == 'none' else float(text)
            else:
                value = text
        except ValueError:
            raise SystemExit('--set %s=%s: the value does not fit the setting' % (key, text))
        setattr(cfg, name, value)
    return cfgs['refl'], cfgs['burn']


def survey(a, rc, bc):
    """The demonstrator's survey over replicates, as a table (2026-11-23:
    the documents' "refl.survey(Config(plan='staggered'), range(200))" and
    "lower monitor until each estimator fails" as command lines)."""
    seeds = range(a.seed, a.seed + a.survey)
    if a.mode == 'refl':
        from demonstrator import refl
        names = (list(refl.DEFAULT_METHODS) if a.methods == 'default' else
                 list(refl.METHODS) if a.methods == 'all' else [m.strip() for m in a.methods.split(',')])
        out, _ = refl.survey(rc, seeds, names)
        print('reflectivity survey: %d replicates (seeds %d..%d), %s' % (a.survey, seeds[0], seeds[-1], rc))
        print('%-22s %4s %8s %8s %8s %6s' % ('method', 'join', 'bias', 'pull', 'pull SD', 'failed'))
        for n in names:
            for j, p in sorted(out[n]['joins'].items()):
                print('%-22s %4d %+8.4f %+8.3f %8.3f %6d' % (n, j, p['bias'], p['pull_mean'], p['pull_sd'],
                                                            out[n]['failed']))
    else:
        from demonstrator import burnmode as bm
        out, _ = bm.survey(bc, seeds)
        print('burn survey: %d replicates (seeds %d..%d), %s' % (a.survey, seeds[0], seeds[-1], bc))
        print('%-10s %-10s %10s %10s %10s %10s %7s' % ('estimator', 'quantity', 'true', 'mean', 'bias', 'sd', 'stable'))
        for n, per in out.items():
            for q, d in per.items():
                print('%-10s %-10s %+10.4g %+10.4g %+10.4g %10.4g %7.2f' % (n, q, d['true'], d['mean'], d['bias'],
                                                                         d['sd'], d['stable']))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--mode', choices=('refl', 'burn'), default='refl')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--save', metavar='DIR', help='write the report figures and numbers (no display needed)')
    ap.add_argument('--views', metavar='DIR', help='write the two default views as PNG (no display needed)')
    ap.add_argument('--replicates', type=int, default=200, help='replicates per reflectivity survey (--save)')
    ap.add_argument('--burn-replicates', type=int, default=30, help='replicates per burn survey (--save)')
    ap.add_argument('--rows', metavar='DIR2', help='also write the per-replicate CSVs (large) into DIR2 (--save)')
    ap.add_argument('--quick', action='store_true', help='few replicates (smoke run)')
    ap.add_argument('--survey', type=int, default=0, metavar='N',
                    help='print a survey over N replicates (from --seed) instead of opening the window: '
                         'reflectivity, every method\'s pull mean and SD per join; burn, every estimator\'s '
                         'bias, scatter and stable fraction per quantity')
    ap.add_argument('--methods', default='default',
                    help="--survey, reflectivity: 'default' (the window's four), 'all', or a comma-separated list")
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE',
                    help='a setting of the window or of --views, e.g. truth=water, plan=edge, '
                         'counts=100, monitor=poisson, change=fade (repeatable)')
    a = ap.parse_args(argv)
    rc, bc = configs(a.set, a.mode)
    if a.survey:
        return survey(a, rc, bc)
    if a.save or a.views:
        import matplotlib
        matplotlib.use('Agg')
        from demonstrator import figures
        if a.views:
            figures.views(a.views, seed=a.seed, refl_config=rc, burn_config=bc)
        if a.save:
            n, nb = (6, 3) if a.quick else (a.replicates, a.burn_replicates)
            figures.report(a.save, replicates=n, burn_replicates=nb, log=print, rows_out=a.rows)
        return 0
    from PyQt5 import QtWidgets
    from demonstrator.window import open_demo
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    w = open_demo(mode=a.mode, seed=a.seed, refl_config=rc, burn_config=bc)  # noqa: F841 (kept alive)
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
