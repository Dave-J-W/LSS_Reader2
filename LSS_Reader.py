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


def main(argv=None):
    app, w = create_app(argv)
    w.showMaximized()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
