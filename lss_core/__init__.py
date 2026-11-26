"""GUI-free core of LSS_Reader: reading data files, caching, reduction.

Nothing in this package imports Qt, so it can be used from scripts and
notebooks (SCOPE.md, Stage 2). The window (mainwindow.py) is being moved
onto it step by step.
"""

__version__ = '2.0'      # the release this main is heading for (docs/RELEASE_PLAN.md); Help > About shows it
