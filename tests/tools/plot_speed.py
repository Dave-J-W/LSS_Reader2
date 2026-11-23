"""Time the window's plots and image displays on synthetic data (2026-11-23).

    python tests/tools/plot_speed.py mca --spectra 10 50 100 --channels 2048
    python tests/tools/plot_speed.py images --frames 1 9 --log

``mca``: an MCA file of N spectra (C channels: an elastic peak, two lines,
a flat background of about 0.3 counts, so many channels hold 0) behind the
synthetic data set's fluorescence scan; times selecting all of them (the
plot and its draw) with linear and with log y, and switching log y on with
the spectra already plotted. ``images``: the synthetic Pilatus frames,
times showing N frames at once, linear and log. Prints one line per case;
the window is the real one, on the offscreen Qt platform.
"""
import argparse
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import numpy as np  # noqa: E402

_TMP = None


def _setup():
    """Offscreen Qt, logs and preferences in a temporary folder (removed at
    exit), the repository as working directory: for running as a script."""
    global _TMP
    import atexit
    import shutil
    _TMP = tempfile.mkdtemp(prefix='lss_plot_speed_')
    atexit.register(shutil.rmtree, _TMP, ignore_errors=True)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('MPLBACKEND', 'Agg')
    os.environ.setdefault('LSS_READER_LOG_DIR', os.path.join(_TMP, 'logs'))
    os.environ.setdefault('LSS_READER_PREFS', os.path.join(_TMP, 'prefs.json'))
    os.environ.setdefault('LSS_READER_SELECTION_DELAY_MS', '0')
    os.chdir(ROOT)


def spectra(n, channels, seed=0):
    rng = np.random.default_rng(seed)
    ch = np.arange(1, channels + 1)
    out = []
    for k in range(n):
        mu = (0.3 + 3000 * np.exp(-(ch - 0.8 * channels) ** 2 / 2 / 6 ** 2)
              + (50 + 10 * k) * np.exp(-(ch - 0.3 * channels) ** 2 / 2 / 5 ** 2)
              + 20 * np.exp(-(ch - 0.35 * channels) ** 2 / 2 / 5 ** 2))
        out.append(rng.poisson(mu))
    return out


def window(spec):
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(['plot-speed'])
    import mainwindow
    w = mainwindow.MainWindow()
    w.show()
    app.processEvents()
    w.openSpecFile(fname=spec)
    w.directory = _TMP
    app.processEvents()
    return app, w


def timed(fn, app):
    t = time.perf_counter()
    fn()
    app.processEvents()
    return time.perf_counter() - t


def run_mca(counts, channels):
    import synth
    import sweep
    for n in counts:
        root = tempfile.mkdtemp(dir=_TMP)
        spec = synth.make_dataset(os.path.join(root, 'data'))
        synth.write_mca(os.path.join(os.path.dirname(spec), 'vortex', 'sample_3_mca'), spectra(n, channels))
        app, w = window(spec)
        sweep._select_scans(w, app, [2])
        w.ui.mcaLogYCheckBox.setChecked(False)
        lin = timed(lambda: sweep._select_images(w, app), app)
        logon = timed(lambda: w.ui.mcaLogYCheckBox.setChecked(True), app)
        w.ui.imageListWidget.clearSelection()
        app.processEvents()
        log = timed(lambda: sweep._select_images(w, app), app)
        print('mca  %4d spectra x %d channels: plot linear %6.2f s | log y switched on %6.2f s | plot with log y %6.2f s'
              % (n, channels, lin, logon, log), flush=True)
        sweep.dispose(w, app)


def run_images(counts, log):
    import synth
    import sweep
    root = tempfile.mkdtemp(dir=_TMP)
    spec = synth.make_dataset(os.path.join(root, 'data'))
    app, w = window(spec)
    sweep._select_scans(w, app, [0])
    for n in counts:
        for lg in ((False, True) if log else (False,)):
            w.ui.imageListWidget.clearSelection()
            app.processEvents()
            box = getattr(w.ui, 'pilLogIntCheckBox', None)
            if box is not None:
                box.setChecked(lg)
            t = timed(lambda: sweep._select_images(w, app, list(range(n))), app)
            print('image %2d frame(s) %-6s %6.2f s' % (n, 'log' if lg else 'linear', t), flush=True)
    sweep.dispose(w, app)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='what', required=True)
    m = sub.add_parser('mca')
    m.add_argument('--spectra', type=int, nargs='+', default=[10, 50, 100])
    m.add_argument('--channels', type=int, default=2048)
    i = sub.add_parser('images')
    i.add_argument('--frames', type=int, nargs='+', default=[1, 9])
    i.add_argument('--log', action='store_true')
    a = ap.parse_args(argv)
    _setup()
    if a.what == 'mca':
        run_mca(a.spectra, a.channels)
    else:
        run_images(a.frames, a.log)
    return 0


if __name__ == '__main__':
    sys.exit(main())
