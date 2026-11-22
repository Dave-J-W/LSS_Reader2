"""The reader's Tools menu: every entry of ``lss_tools.registry``.

- Demonstrations open their window inside the reader's process, as a
  separate, non-modal window owned by the main window (closed with it).
- Generators and checks open a small dialog (cheap: nothing runs until
  Run is pressed): what the tool makes, the run (a documented job or your
  own arguments), the output folder, Run/Stop, and the tool's output as it
  comes. The tool runs as its own process (``QProcess``, the documented
  command), so the reader stays responsive and a crash of the tool cannot
  take the reader down. Progress goes to the status bar and the dialog;
  the result to the Messages pane (``MainWindow.notify``); the whole
  output to a file in the log folder.

A packaged build has no Python to run scripts with and no repository to
write documentation into: there the generators and checks are shown
disabled, and the demonstrations work if their modules were bundled
(``packaging/lss_reader.spec``).
"""
import os
import re
import shlex
import sys
import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from . import registry as reg

ROOT = reg.ROOT
FROZEN = bool(getattr(sys, 'frozen', False))


def can_run(tool):
    """(True, '') or (False, why) for a generator or check."""
    if FROZEN:
        return False, ('Needs a source checkout of the repository and Python: the packaged program has '
                       'neither (run %s there).' % tool.command)
    if tool.script and not os.path.isfile(os.path.join(ROOT, tool.script)):
        return False, '%s is not in this copy of the program.' % tool.script
    return True, ''


def _inside(path, folder):
    p, f = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(folder))
    return p == f or p.startswith(f + os.sep)


def output_refusal(tool, job, out):
    """Why ``out`` may not receive this tool's outputs, or ''. Never
    sample_data/, except sample_data/private/figures/ for tools that read
    private data; private jobs never write elsewhere in the repository."""
    if not out:
        return ''
    sample = os.path.join(ROOT, 'sample_data')
    private_fig = os.path.join(ROOT, *reg.PRIVATE_FIGURES.split('/'))
    if _inside(out, sample) and not (tool.data in ('mixed', 'private') and _inside(out, private_fig)):
        return ('Outputs never go into sample_data/ (the data stay as measured); only figures of private '
                'data go under %s.' % reg.PRIVATE_FIGURES)
    if job is not None and job.private and _inside(out, ROOT) and not _inside(out, private_fig):
        return 'Figures of private data stay under %s or outside the repository.' % reg.PRIVATE_FIGURES
    return ''


def default_out(tool):
    """A folder for runs that are not a documented job."""
    return os.path.join(os.path.expanduser('~'), 'LSS_Reader tools', tool.id)


# ---------------------------------------------------------------- the menu

def build_menu(window):
    """Insert the Tools menu before Help; return it."""
    bar = window.ui.menuBar
    menu = QtWidgets.QMenu('Tools', bar)
    menu.setObjectName('menuTools')
    menu.setToolTipsVisible(True)
    help_menu = getattr(window.ui, 'menuHelp', None)
    if help_menu is not None:
        bar.insertMenu(help_menu.menuAction(), menu)
    else:
        bar.addMenu(menu)
    window.toolRuns = {}
    window.toolWindows = []
    window.toolDialogs = {}
    for kind, title in reg.KINDS:
        tools = [t for t in reg.TOOLS if t.kind == kind]
        if not tools:
            continue
        sub = menu.addMenu(title)
        sub.setObjectName('menuTools_' + kind)
        sub.setToolTipsVisible(True)
        for t in tools:
            act = QtWidgets.QAction(t.title + ('' if kind == 'demo' else '...'), window)
            act.setObjectName('actionTool_' + t.id)
            tip = t.summary + '\n' + reg.DATA.get(t.data, '') + ('; ' + t.seconds if t.seconds else '')
            if kind == 'demo':
                act.triggered.connect(lambda _=False, t=t: open_demo(window, t))
            else:
                ok, why = can_run(t)
                act.setEnabled(ok)
                if not ok:
                    tip += '\n' + why
                act.triggered.connect(lambda _=False, t=t: open_dialog(window, t))
            act.setToolTip(tip)
            act.setStatusTip(t.summary)
            sub.addAction(act)
    return menu


def open_demo(window, tool):
    """Build the demonstration's window (a second or two) and show it."""
    tests = os.path.join(ROOT, 'tests')
    if os.path.isdir(tests) and tests not in sys.path:
        sys.path.append(tests)                       # demonstrator, synthetic (as in the test suite)
    mod, _, name = tool.demo.partition(':')
    window.ui.statusBar.showMessage('Tools: opening %s...' % tool.title)
    QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        build = getattr(__import__(mod, fromlist=[name]), name)
        w = build(parent=window, **tool.demo_kwargs)       # shown; deletes itself when closed
    except Exception as e:
        window.notify('Tools: %s could not be opened: %s: %s' % (tool.title, type(e).__name__, e), title='Tools')
        return None
    finally:
        QtWidgets.QApplication.restoreOverrideCursor()
        window.ui.statusBar.clearMessage()
    w.setObjectName('toolWindow_' + tool.id)        # a QMainWindow: its own window, owned by the reader
    window.toolWindows = [x for x in window.toolWindows if _alive(x)] + [w]
    window.notify('Tools: %s opened (synthetic data; the space bar draws a new replicate).' % tool.title,
                  title='Tools', level='info')
    return w


def _alive(obj):
    try:
        obj.objectName()
        return True
    except RuntimeError:
        return False


def open_dialog(window, tool):
    """Show the tool's dialog (built once per window); nothing runs yet."""
    d = window.toolDialogs.get(tool.id)
    if d is None or not _alive(d):
        d = ToolDialog(window, tool)
        window.toolDialogs[tool.id] = d
    d.show()
    d.raise_()
    return d


def stop_all(window):
    """Stop every running tool and close the demonstrations (the window closes)."""
    for run in list(getattr(window, 'toolRuns', {}).values()):
        run.stop(kill=True)
    for w in getattr(window, 'toolWindows', []):
        if _alive(w):
            w.close()
    window.toolWindows = []


# ---------------------------------------------------------------- one run

class ToolRun(QtCore.QObject):
    """One tool running as a process; owned by the main window, so it goes
    on when its dialog is closed."""
    line = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(int)

    def __init__(self, window, tool, argv, out, stdout_file=None):
        super().__init__(window)
        self.window, self.tool, self.argv, self.out = window, tool, list(argv), out
        self.started = time.time()
        self.stopped = False
        self.lines = []
        logs = None
        try:
            import reader_log
            logs = reader_log.log_dir()
        except Exception:
            pass
        folder = os.path.join(logs or os.path.expanduser('~'), 'tools')
        os.makedirs(folder, exist_ok=True)
        self.log_path = os.path.join(folder, '%s-%s.txt' % (tool.id, time.strftime('%Y%m%d-%H%M%S')))
        self.log_file = open(self.log_path, 'w', encoding='utf-8')
        self.log_file.write('$ %s\n' % self.command_text())
        self.before = _snapshot(out) if out else {}
        p = self.proc = QtCore.QProcess(self)
        p.setWorkingDirectory(ROOT)
        env = QtCore.QProcessEnvironment.systemEnvironment()
        for k, v in (('MPLBACKEND', 'Agg'), ('QT_QPA_PLATFORM', 'offscreen'), ('PYTHONUNBUFFERED', '1'),
                     ('PYTHONIOENCODING', 'utf-8')):
            env.insert(k, v)
        p.setProcessEnvironment(env)
        if stdout_file:
            os.makedirs(os.path.dirname(stdout_file) or '.', exist_ok=True)
            p.setStandardOutputFile(stdout_file)
            p.readyReadStandardError.connect(self._read)
        else:
            p.setProcessChannelMode(QtCore.QProcess.MergedChannels)
            p.readyReadStandardOutput.connect(self._read)
        p.finished.connect(self._finished)
        p.errorOccurred.connect(self._error)
        self.stdout_file = stdout_file

    def program(self):
        return sys.executable, (['-m', self.tool.module] if self.tool.module
                                else [os.path.join(ROOT, self.tool.script)]) + self.argv

    def command_text(self):
        cmd = ' '.join([self.tool.command] + [_q(a) for a in self.argv])
        return cmd + (' > ' + self.stdout_file if getattr(self, 'stdout_file', None) else '')

    def start(self):
        prog, args = self.program()
        self.proc.start(prog, args)

    def running(self):
        return self.proc.state() != QtCore.QProcess.NotRunning

    def stop(self, kill=False):
        if not self.running():
            return
        self.stopped = True
        if kill:
            self.proc.kill()
            self.proc.waitForFinished(3000)
        else:
            self.proc.terminate()                    # regenerate stops its own job on SIGTERM
            QtCore.QTimer.singleShot(5000, self._kill_late)

    def _kill_late(self):
        try:
            if self.running():
                self.proc.kill()
        except RuntimeError:                         # the window, and this run, are gone
            pass

    def _read(self):
        data = self.proc.readAllStandardError() if self.stdout_file else self.proc.readAllStandardOutput()
        text = bytes(data).decode('utf-8', 'replace')
        for ln in text.splitlines():
            self.lines.append(ln)
            self.log_file.write(ln + '\n')
            self.line.emit(ln)
            if ln.strip():
                try:
                    self.window.ui.statusBar.showMessage('%s: %s' % (self.tool.title, ln.strip()[:160]))
                except RuntimeError:
                    pass
        del self.lines[:-200]

    def _error(self, err):
        if err == QtCore.QProcess.FailedToStart:
            self._report(-1, 'could not be started (%s)' % self.proc.errorString())

    def _finished(self, code, status):
        try:
            self._read()
        except RuntimeError:
            pass
        if status == QtCore.QProcess.CrashExit and not self.stopped:
            code = code or -1
        self._report(code, '')

    def _report(self, code, why):
        try:
            self.log_file.close()
        except Exception:
            pass
        runs = getattr(self.window, 'toolRuns', {})
        if runs.get(self.tool.id) is self:
            del runs[self.tool.id]
        secs = time.time() - self.started
        if self.stopped:
            text = 'Tools: %s stopped after %.0f s.' % (self.tool.title, secs)
        elif why or code != 0:
            tail = [ln for ln in self.lines if ln.strip()][-3:]
            text = 'Tools: %s %s%s. Last lines: %s. Full output: %s' % (
                self.tool.title, why or 'failed (exit status %d)' % code,
                ' after %.0f s' % secs if not why else '', ' | '.join(tail) or '(none)', self.log_path)
        else:
            changed = _changed(self.before, _snapshot(self.out)) if self.out else []
            where = (' %d file(s) written or changed in %s.' % (len(changed), self.out)) if self.out else ''
            text = 'Tools: %s finished in %.0f s.%s Full output: %s' % (self.tool.title, secs, where, self.log_path)
        try:
            self.window.notify(text, title='Tools', level='info' if code == 0 and not why else 'warning')
            self.window.ui.statusBar.clearMessage()
        except RuntimeError:
            pass
        self.done.emit(code)


def _snapshot(folder):
    out = {}
    if folder and os.path.isdir(folder):
        for dirpath, _, names in os.walk(folder):
            for n in names:
                p = os.path.join(dirpath, n)
                try:
                    st = os.stat(p)
                    out[p] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    pass
    return out


def _changed(before, after):
    return sorted(p for p, s in after.items() if before.get(p) != s)


# ---------------------------------------------------------------- the dialog

class ToolDialog(QtWidgets.QDialog):
    """What the tool makes, which run, where to, Run/Stop and its output."""

    def __init__(self, window, tool):
        super().__init__(window)
        self.window, self.tool = window, tool
        self.setObjectName('toolDialog_' + tool.id)
        self.setWindowTitle('Tools: ' + tool.title)
        self.setModal(False)
        self.resize(760, 520)
        self.jobs = list(tool.jobs)
        lay = QtWidgets.QVBoxLayout(self)
        about = QtWidgets.QLabel(tool.summary, self)
        about.setWordWrap(True)
        about.setToolTip('\n'.join(x for x in (
            tool.details, 'Data: ' + reg.DATA.get(tool.data, tool.data),
            'Typical run time: ' + tool.seconds if tool.seconds else '',
            'Discussed in: ' + tool.doc if tool.doc else '', 'Command: ' + tool.command) if x))
        lay.addWidget(about)
        form = QtWidgets.QFormLayout()
        self.preset = None
        if self.jobs:
            self.preset = QtWidgets.QComboBox(self)
            self.preset.setObjectName('toolPresetComboBox')
            for j in self.jobs:
                ok = all(os.path.exists(os.path.join(ROOT, *r.split('/'))) for r in j.requires)
                self.preset.addItem(j.title + (' (private data)' if j.private else '') + ('' if ok else ' - data absent'))
            self.preset.addItem('Your own arguments')
            self.preset.setToolTip('A documented run (its outputs are committed documentation, or for private data '
                                   'kept under %s), or your own arguments. docs/TOOLS.md lists them.'
                                   % reg.PRIVATE_FIGURES)
            self.preset.currentIndexChanged.connect(self.choosePreset)
            form.addRow('Run', self.preset)
        self.args = QtWidgets.QLineEdit(self)
        self.args.setObjectName('toolArgsLineEdit')
        self.args.setToolTip('Arguments after the command, as on a shell command line. {out} stands for the output '
                             'folder; when the arguments do not name it, the folder is passed with %s.'
                             % (tool.out_flag or 'no option (this tool has none)'))
        self.args.textChanged.connect(self.showCommand)
        form.addRow('Arguments', self.args)
        self.out = None
        if self.jobs or tool.out_flag:
            row = QtWidgets.QHBoxLayout()
            self.out = QtWidgets.QLineEdit(self)
            self.out.setObjectName('toolOutLineEdit')
            self.out.setToolTip('Where the outputs go. Default: where the documentation keeps them (the documented '
                                'run), which rewrites committed files: git shows what changed, and python -m '
                                'lss_tools.regenerate records the run in docs/figures/MANIFEST.json. Never '
                                'sample_data/, except %s for private data.' % reg.PRIVATE_FIGURES)
            self.out.textChanged.connect(self.showCommand)
            pick = QtWidgets.QPushButton('Folder...', self)
            pick.setObjectName('toolOutPushButton')
            pick.setToolTip('Choose the output folder.')
            pick.clicked.connect(self.chooseFolder)
            row.addWidget(self.out)
            row.addWidget(pick)
            form.addRow('Output folder', row)
        lay.addLayout(form)
        self.commandLabel = QtWidgets.QLabel(self)
        self.commandLabel.setWordWrap(True)
        self.commandLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.commandLabel.setToolTip('The command that Run starts, from the repository root (the same as in a shell).')
        lay.addWidget(self.commandLabel)
        self.runButton = QtWidgets.QPushButton('Run', self)
        self.runButton.setObjectName('toolRunPushButton')
        self.runButton.setToolTip('Start the tool as its own process (the reader stays usable); while it runs: stop '
                                  'it. Progress shows below and in the status bar; the result in the Messages pane.')
        self.runButton.clicked.connect(self.runOrStop)
        lay.addWidget(self.runButton)
        self.view = QtWidgets.QPlainTextEdit(self)
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(5000)
        self.view.setToolTip("The tool's output as it runs (also kept in a file in the log folder).")
        lay.addWidget(self.view, 1)
        box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close, self)
        box.rejected.connect(self.close)
        box.button(QtWidgets.QDialogButtonBox.Close).setToolTip('Close this dialog; a run goes on, and its result '
                                                                'still reaches the Messages pane.')
        lay.addWidget(box)
        if self.preset is not None:
            self.choosePreset(0)
        else:
            self.args.setText(' '.join(_q(a) for a in tool.args))
        self.showCommand()
        run = window.toolRuns.get(tool.id)
        if run is not None:
            self.attach(run)

    # -- state
    def currentJob(self):
        if self.preset is None:
            return None
        k = self.preset.currentIndex()
        return self.jobs[k] if 0 <= k < len(self.jobs) else None

    def choosePreset(self, k):
        job = self.currentJob()
        if job is None:
            if self.out is not None and not self.out.text():
                self.out.setText(default_out(self.tool))
            return
        self.args.setText(' '.join(_q(a) for a in job.args))
        if self.out is not None:
            self.out.setText(os.path.join(ROOT, *job.out.split('/')) if job.out else '')

    def chooseFolder(self):
        start = self.out.text() if self.out is not None else ROOT
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Output folder', start)
        if d and self.out is not None:
            self.out.setText(d)

    def outFolder(self):
        return os.path.abspath(os.path.expanduser(self.out.text().strip())) if self.out is not None and \
            self.out.text().strip() else ''

    def argv(self):
        """The arguments Run passes, or raise ValueError."""
        args = shlex.split(self.args.text(), posix=os.name != 'nt')
        out = self.outFolder()
        job = self.currentJob()
        if any('{out}' in a for a in args):
            if not out:
                raise ValueError('the arguments name {out} but no output folder is given')
            args = [a.replace('{out}', out) for a in args]
        elif out and self.tool.out_flag and not job_default(job, out) and self.tool.out_flag not in args:
            args += [self.tool.out_flag, out]
        return args

    def stdoutFile(self):
        job = self.currentJob() or (self.jobs[0] if self.jobs else None)
        if job is None or not job.stdout:
            return None
        return os.path.join(self.outFolder() or os.path.join(ROOT, *job.out.split('/')),
                            os.path.basename(job.stdout))

    def showCommand(self, *_):
        try:
            argv = self.argv()
            cmd = ' '.join([self.tool.command] + [_q(_short(a)) for a in argv])
            out = self.stdoutFile()
            self.commandLabel.setText(cmd + (' > ' + _short(out) if out else ''))
        except ValueError as e:
            self.commandLabel.setText('(%s)' % e)

    # -- running
    def runOrStop(self):
        run = self.window.toolRuns.get(self.tool.id)
        if run is not None and run.running():
            run.stop()
            return
        job = self.currentJob()
        try:
            argv = self.argv()
        except ValueError as e:
            self.window.notify('Tools: %s: %s.' % (self.tool.title, e), title='Tools')
            return
        out = self.outFolder()
        why = output_refusal(self.tool, job, out) or output_refusal(self.tool, job, self.stdoutFile() or '')
        if job is not None:
            missing = [r for r in job.requires if not os.path.exists(os.path.join(ROOT, *r.split('/')))]
            if missing:
                why = why or 'its data are not here: %s' % ', '.join(missing)
        if why:
            self.window.notify('Tools: %s not run: %s' % (self.tool.title, why), title='Tools')
            return
        if out:
            try:
                os.makedirs(out, exist_ok=True)
            except OSError as e:
                self.window.notify('Tools: %s not run: cannot make %s (%s).' % (self.tool.title, out, e), title='Tools')
                return
        run = ToolRun(self.window, self.tool, argv, out, self.stdoutFile())
        self.window.toolRuns[self.tool.id] = run
        self.view.clear()
        self.attach(run)
        self.window.notify('Tools: %s started: %s' % (self.tool.title, run.command_text()), title='Tools', level='info')
        run.start()

    def attach(self, run):
        self.view.appendPlainText('$ ' + run.command_text())
        for ln in run.lines:
            self.view.appendPlainText(ln)
        run.line.connect(self._line)
        run.done.connect(self._done)
        self.runButton.setText('Stop')

    def _line(self, ln):
        try:
            self.view.appendPlainText(ln)
        except RuntimeError:
            pass

    def _done(self, code):
        try:
            self.view.appendPlainText('(finished, exit status %d)' % code)
            self.runButton.setText('Run')
        except RuntimeError:
            pass


def job_default(job, out):
    """True when ``out`` is the job's documented folder (nothing to pass)."""
    return job is not None and bool(job.out) and \
        os.path.normcase(os.path.abspath(out)) == os.path.normcase(os.path.join(ROOT, *job.out.split('/')))


def _q(a):
    """Quote an argument for the command line only when it needs it."""
    if re.fullmatch(r'[\w@%+=:,./{}-]+', a):
        return a
    return '"%s"' % a if os.name == 'nt' else shlex.quote(a)


def _short(path):
    """Paths inside the repository relative to it (as in the documentation)."""
    try:
        if os.path.isabs(path) and _inside(path, ROOT):
            return os.path.relpath(path, ROOT).replace(os.sep, '/')
    except ValueError:
        pass
    return path
