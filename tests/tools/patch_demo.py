"""Fit demonstrator on synthetic data (owner, 2026-11-22): reflectivity
patching by every method, and burn line cuts by every estimator, with the
truth beside them. Report: docs/reports/patch_demo.md.

    python tests/tools/patch_demo.py                     # the window (space bar: new replicate)
    python tests/tools/patch_demo.py --mode burn --seed 5
    python tests/tools/patch_demo.py --save docs/figures/patch_demo   # the report's figures, headless (Agg)
    python tests/tools/patch_demo.py --save DIR --quick  # the same with few replicates (a smoke run)
    python tests/tools/patch_demo.py --views DIR         # only the two default views as PNG

Run from the repository root (or anywhere: the paths are set from this
file). The computation is in tests/demonstrator/ (GUI-free, used by the
tests); the window in tests/demonstrator/window.py. All data are
synthetic, so the figures are public. ``--save`` also writes
``numbers.json`` (every number the report quotes) and the per-replicate
CSVs into DIR.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--mode', choices=('refl', 'burn'), default='refl')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--save', metavar='DIR', help='write the report figures and numbers (no display needed)')
    ap.add_argument('--views', metavar='DIR', help='write the two default views as PNG (no display needed)')
    ap.add_argument('--replicates', type=int, default=200, help='replicates per reflectivity survey (--save)')
    ap.add_argument('--burn-replicates', type=int, default=30, help='replicates per burn survey (--save)')
    ap.add_argument('--quick', action='store_true', help='few replicates (smoke run)')
    a = ap.parse_args(argv)
    if a.save or a.views:
        import matplotlib
        matplotlib.use('Agg')
        from demonstrator import figures
        if a.views:
            figures.views(a.views, seed=a.seed)
        if a.save:
            n, nb = (6, 3) if a.quick else (a.replicates, a.burn_replicates)
            figures.report(a.save, replicates=n, burn_replicates=nb, log=print)
        return 0
    from PyQt5 import QtWidgets
    from demonstrator.window import DemoWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    w = DemoWindow(mode=a.mode, seed=a.seed)
    w.resize(1500, 950)
    w.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
