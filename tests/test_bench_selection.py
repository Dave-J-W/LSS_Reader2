"""Wall-clock timing of what a user waits for, on the real sample data.

Not a pass/fail test: it writes a table (docs/timings.md by default, or the
path in LSS_BENCH_OUT) so that later speed work has a baseline. Run with

    pytest -m bench -s

Each step is timed from the action until Qt has processed its events. The
biggest step is also profiled so the time can be attributed to reading,
bad-pixel correction, plotting and the rest.
"""
import cProfile
import os
import platform
import pstats
import time

import pytest

import sweep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
BU_SEP = os.path.join(ROOT, 'sample_data', 'bu', '2026sep', '20260902')
OUT = os.environ.get('LSS_BENCH_OUT', os.path.join(ROOT, 'docs', 'timings.md'))

pytestmark = [pytest.mark.gui, pytest.mark.bench]


class Timer:
    def __init__(self, app):
        self.app, self.rows = app, []

    def __call__(self, label, fn, note=''):
        t0 = time.perf_counter()
        fn()
        self.app.processEvents()
        dt = time.perf_counter() - t0
        self.rows.append((label, dt, note))
        return dt


GROUPS = (('matplotlib (layout, text, drawing)', '/matplotlib/'),
          ('image reader (TwoDDetector.py)', '/TwoDDetector.py'),
          ('MCA reader (mca_routines.py)', '/mca_routines.py'),
          ('SPEC reader (spec_routines.py)', '/spec_routines.py'),
          ('window code (mainwindow.py)', '/mainwindow.py'),
          ('PIL', '/PIL/'),
          ('numpy and scipy', '/numpy/'), ('numpy and scipy', '/scipy/'))


def _attribute(profile):
    """Split profiled own-time by where the code lives (no overlap)."""
    stats = pstats.Stats(profile)
    total = stats.total_tt
    sums = {}
    for (fname, _line, func), v in stats.stats.items():
        f = fname.replace('\\', '/')
        label = 'built-ins and everything else'
        for name, key in GROUPS:
            if key in f:
                label = name
                break
        else:
            if 'numpy' in func or 'numpy' in f:
                label = 'numpy and scipy'
        sums[label] = sums.get(label, 0.0) + v[2]
    return total, sorted(sums.items(), key=lambda kv: -kv[1])


def _profiled(app, fn):
    pr = cProfile.Profile()
    pr.enable()
    fn()
    app.processEvents()
    pr.disable()
    if os.environ.get('LSS_BENCH_TOP'):
        pstats.Stats(pr).sort_stats('cumulative').print_stats(25)
    return _attribute(pr)


@pytest.mark.skipif(not os.path.exists(NX), reason='NX_school data not present')
def test_timings(qapp, recorder, tmp_path):
    from mainwindow import MainWindow
    t = Timer(qapp)
    sections = []

    # ---- reflectivity, Pilatus 100K (NX school) -------------------------
    w = MainWindow()
    w.show()
    t('open SPEC file (15 scans)', lambda: w.openSpecFile(fname=NX))
    w.directory = str(tmp_path)
    t('select one scan (27 frames listed)', lambda: sweep._select_scans(w, qapp, [6]))
    t('select 1 frame (read + show)', lambda: sweep._select_images(w, qapp, [0]))
    t('select the same frame again', lambda: sweep._select_images(w, qapp, [0]),
      'nothing is cached')
    t('select all 27 frames of the scan', lambda: sweep._select_images(w, qapp),
      'only the first 10 are drawn')

    def one_by_one():
        w.ui.imageListWidget.clearSelection()
        for r in range(27):
            w.ui.imageListWidget.item(r).setSelected(True)
            qapp.processEvents()
    t('add the same 27 frames one click at a time', one_by_one,
      'every click re-reads all selected frames')
    t('select 4 scans (96 frames listed)',
      lambda: sweep._select_scans(w, qapp, [5, 6, 7, 8]))
    t('select all 96 frames', lambda: sweep._select_images(w, qapp))
    total, parts = _profiled(qapp, lambda: sweep._select_images(w, qapp))
    sections.append(('Where the time goes: selecting 96 Pilatus 100K frames',
                     total, parts))
    t('reflectivity patch: integrate 96 frames',
      lambda: w.ui.pilRefPatchPushButton.click())

    def finish():
        for _ in range(3):
            w.uirefpatch.nextPushButton.click()
            qapp.processEvents()
    t('reflectivity patch: accept 3 overlaps', finish)
    w.close()

    # ---- fluorescence, Vortex (bu, private) -----------------------------
    if os.path.exists(BU_SEP):
        w = MainWindow()
        w.show()
        t('open SPEC file (142 scans)', lambda: w.openSpecFile(fname=BU_SEP))
        w.directory = str(tmp_path)
        rows = [i for i in range(w.ui.scanListWidget.count())
                if w.ui.scanListWidget.item(i).text().split()[1] in
                ('74', '75', '76', '77', '78', '79')]
        t('select 6 fluorescence scans (MCA files read)',
          lambda: sweep._select_scans(w, qapp, rows))
        n = w.ui.imageListWidget.count()
        t('select all %d spectra' % n, lambda: sweep._select_images(w, qapp))
        total, parts = _profiled(qapp, lambda: sweep._select_images(w, qapp))
        sections.append(('Where the time goes: selecting %d MCA spectra' % n,
                         total, parts))
        w.close()

    recorder.exceptions.clear()
    lines = ['# Timings', '',
             'Written by `pytest -m bench` (`tests/test_bench_selection.py`).',
             'Local disk, offscreen Qt, %s, Python %s. Single run; expect'
             % (platform.machine(), platform.python_version()),
             'run-to-run variation of 10-20 %. Production reads from a',
             'network drive, which these numbers do not include.', '',
             '| Step | Seconds | Note |', '|---|---|---|']
    lines += ['| %s | %.2f | %s |' % r for r in t.rows]
    for title, total, parts in sections:
        lines += ['', '## ' + title, '',
                  'Own time by where the code lives, from a profiled repeat of',
                  'the step. The profiler slows everything, so only the shares',
                  'are meaningful.', '',
                  '| Part | Share |', '|---|---|']
        lines += ['| %s | %.0f %% |' % (p, 100 * s / total) for p, s in parts]
    with open(OUT, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
