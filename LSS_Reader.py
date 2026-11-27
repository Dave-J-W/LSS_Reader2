import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

import reader_log
from lss_core.resources import resource


def create_app(argv=None):
    """Build the application and the main window, with logging and the
    process-wide error handler in place. Returns (app, window)."""
    reader_log.start_session()
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    app.setApplicationName('LSS-Reader')
    reader_log.install_qt_message_handler()
    from mainwindow import MainWindow        # needs the QApplication
    w = MainWindow()
    w.setWindowTitle('LSS-Reader')
    w.setWindowIcon(QIcon(resource('logo.png')))
    # From here on an exception in any button handler is logged and shown
    # in the Messages pane; the program keeps running.
    reader_log.install_excepthook(context=w.sessionContext, report=w.reportFailure)
    path = reader_log.session_log_path()
    if path is None:
        w.notify('No log file could be opened; errors will only be shown here.', title='Log')
    else:
        w.log.info('window ready; session log %s', path)
    return app, w


def self_test(specfile, reference_prefix):
    """Check a build (F46): the window opens (its .ui files and icons are
    found), and NX school scans 6-9 reduce to the reference files byte for
    byte (tests/reference/legacy_export/nx_scans_6-9_ref.txt, _rrf.txt),
    reduced with the legacy patch: those files are the legacy reduction and
    never change (AGENTS.md rule 3), while the default patch is the joint
    fit since 2026-11-22 (COMPARISONS C36). Returns 0 when both hold. Needs no display with QT_QPA_PLATFORM=offscreen.
    The report goes to stdout and, if $LSS_SELFTEST_REPORT is set, to that
    file (a Windows build has no console)."""
    import os
    import tempfile
    lines = []

    def say(text):
        lines.append(text)
        print(text)
    app, w = create_app(['LSS-Reader'])
    say('window: %s, %d tabs' % (w.windowTitle(), w.ui.PlotWidget.count()))
    from lss_core.experiment import Experiment
    out = os.path.join(tempfile.mkdtemp(prefix='lss_selftest_'), 'nx')
    exp = Experiment(specfile)
    res = exp.reflectivity([6, 7, 8, 9], method='legacy')
    res.save(out)
    ok = True
    for kind in ('_ref.txt', '_rrf.txt'):
        with open(out + kind, 'rb') as f1, open(reference_prefix + kind, 'rb') as f2:
            same = f1.read() == f2.read()
        say('%s: %s' % (kind, 'identical' if same else 'DIFFERENT'))
        ok = ok and same
    try:        # the ORSO export (F25, #148): orsopy must be bundled, and its file must read back
        from lss_core import orso
        from orsopy import fileio
        orso.write_ort(out + '.ort', res.ref, specfile, [6, 7, 8, 9], exp.scans[6].parameters['Wavelength'])
        n = len(fileio.load_orso(out + '.ort')[0].data)
        same = n == len(res.ref)
        say('ORSO: %s (%d points)' % ('written and read back' if same else 'DIFFERENT', n))
        ok = ok and same
    except Exception as e:
        say('ORSO: FAILED (%s)' % e)
        ok = False
    w.close()
    say('self-test %s' % ('passed' if ok else 'FAILED'))
    if os.environ.get('LSS_SELFTEST_REPORT'):
        with open(os.environ['LSS_SELFTEST_REPORT'], 'w') as f:
            f.write('\n'.join(lines) + '\n')
    return 0 if ok else 1


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if '--self-test' in argv:
        k = argv.index('--self-test')
        return self_test(argv[k + 1], argv[k + 2])
    app, w = create_app(argv)
    w.showMaximized()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
