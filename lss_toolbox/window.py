"""The Tools window: one page per catalogue item, the home of every
demonstration and figure generator in the reader.

A page shows what the item demonstrates (the script's docstring in the
tooltip), the documents that explain it, whether its committed products
are older than their code, the documented variations, and a form built from
the script's own argparse parser. Run executes the script from the
repository in its own process into a run folder; the results pane shows the
run's figures and text, beside the committed products or an earlier run,
compared pixel by pixel. Window items (the demonstrators) start their own
window; the synthetic data set opens in the reader.

Works alone (``python -m lss_toolbox``) or inside the reader
(``lss_toolbox.menu.install``), which passes a ``Host``: the open SPEC
file, a way to open one, and its Messages pane. Labels are short; the
explanations are in tooltips (``texts.CONTROLS``).
"""
import datetime
import os
import shlex

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from . import ROOT, available, catalog, compare, introspect, runner, staleness, texts

# ---------------------------------------------------------------- parsers

_PARSERS = {}          # script -> (mtime, spec)


def _mtime(script):
    try:
        return os.path.getmtime(os.path.join(ROOT, script))
    except OSError:
        return None


def cached_parser(script):
    hit = _PARSERS.get(script)
    if hit and hit[0] == _mtime(script):
        return hit[1]
    return None


def store_parsers(specs):
    for script, spec in specs.items():
        _PARSERS[script] = (_mtime(script), spec)


def load_parsers(scripts=None):
    """Capture the parsers of ``scripts`` (default: every script of the
    catalogue) now, in one subprocess; fills the cache. Returns them."""
    scripts = [s for s in (scripts or catalog.scripts()) if cached_parser(s) is None]
    if scripts:
        store_parsers(introspect.capture_parsers(scripts))
    return {s: cached_parser(s) for s in (scripts or catalog.scripts())}


class ParserLoader(QtCore.QObject):
    """Captures the parsers of several scripts in a background process and
    emits ``loaded`` with {script: spec} (the cache is filled first)."""
    loaded = QtCore.pyqtSignal(dict)

    def __init__(self, scripts, parent=None):
        super().__init__(parent)
        self.scripts = list(scripts)
        self.proc = None

    def start(self):
        todo = [s for s in self.scripts if cached_parser(s) is None]
        if not todo:
            QtCore.QTimer.singleShot(0, lambda: self.loaded.emit({s: cached_parser(s) for s in self.scripts}))
            return
        self.proc = QtCore.QProcess(self)
        self.proc.setWorkingDirectory(ROOT)
        env = QtCore.QProcessEnvironment.systemEnvironment()
        env.insert('MPLBACKEND', 'Agg')
        env.insert('QT_QPA_PLATFORM', 'offscreen')
        self.proc.setProcessEnvironment(env)
        self.proc.finished.connect(lambda *a: self._done(todo))
        self.proc.start(runner.interpreter(), ['-m', 'lss_toolbox.introspect'] +
                        [os.path.join(ROOT, s) for s in todo])

    def _done(self, todo):
        import json
        out = bytes(self.proc.readAllStandardOutput()).decode('utf-8', 'replace').strip().splitlines()
        try:
            got = json.loads(out[-1])
            store_parsers({s: got.get(os.path.join(ROOT, s), {'error': 'not captured'}) for s in todo})
        except (ValueError, IndexError):
            err = bytes(self.proc.readAllStandardError()).decode('utf-8', 'replace').strip().splitlines()
            store_parsers({s: {'error': 'could not read the options: ' + (err[-1] if err else '?')} for s in todo})
        self.loaded.emit({s: cached_parser(s) for s in self.scripts})


# ---------------------------------------------------------------- helpers

class Host:
    """What the program around the Tools window offers (all optional):
    ``spec_file()`` the open SPEC file or None; ``open_spec(path)``;
    ``notify(text)`` a line in its messages."""

    def __init__(self, spec_file=None, open_spec=None, notify=None):
        self.spec_file = spec_file
        self.open_spec = open_spec
        self.notify = notify


def open_path(path):
    QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))


def doc_file(ref):
    """'docs/x.md#some text' -> absolute path of docs/x.md (catalog.locate
    finds the line)."""
    return os.path.join(ROOT, catalog.split_ref(ref)[0])


def compare_images(path_a, path_b):
    """(state, fraction of pixels that differ, difference QImage or None);
    state 'same', 'differ' or 'size' (``compare.compare``)."""
    d = compare.compare(path_a, path_b)
    if d.state != 'differ':
        return ('differ' if d.state == 'unreadable' else d.state), d.fraction, None
    rgb = compare.difference_rgb(path_a, d.mask)
    img = QtGui.QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.shape[1] * 3, QtGui.QImage.Format_RGB888).copy()
    return 'differ', d.fraction, img


def file_set(item, source):
    return runner.product_files(item, source)


class ImageView(QtWidgets.QScrollArea):
    """An image scaled to the width of the pane, or a message."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.label.setWordWrap(True)
        self.setWidget(self.label)
        self.setWidgetResizable(True)
        self.image = None

    def show_image(self, image, text=''):
        if isinstance(image, str):
            image = QtGui.QImage(image) if os.path.exists(image) else None
        self.image = image if image is not None and not image.isNull() else None
        self.label.setToolTip(text)
        if self.image is None:
            self.label.setPixmap(QtGui.QPixmap())
            self.label.setText(text)
        else:
            self._rescale()

    def _rescale(self):
        if self.image is None:
            return
        w = max(50, self.viewport().width() - 4)
        pm = QtGui.QPixmap.fromImage(self.image)
        if pm.width() > w:
            pm = pm.scaledToWidth(w, Qt.SmoothTransformation)
        self.label.setPixmap(pm)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._rescale()


_LIVE = set()          # workers still running: kept here so that no thread is destroyed while it runs


class _Worker(QtCore.QThread):
    """Runs ``fn`` in a thread and emits ``done`` with its result (or the
    exception). Parentless and kept in ``_LIVE`` until finished, so closing
    a page never destroys a running thread."""
    done = QtCore.pyqtSignal(object)

    def __init__(self, fn):
        super().__init__(None)
        self.fn = fn
        _LIVE.add(self)
        self.finished.connect(lambda: _LIVE.discard(self))

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:                # noqa: BLE001 (shown, not raised)
            self.done.emit(e)


def wait_workers(timeout_ms=30000, events=True):
    """Wait for every background check to finish (closing, tests);
    ``events``: then deliver their results (not from inside a close, where
    handling events could delete the window being closed)."""
    for w in list(_LIVE):
        w.wait(timeout_ms)
    if events:
        QtWidgets.QApplication.processEvents()


def _tip(widget, name):
    widget.setToolTip(texts.TIPS[name])
    return widget


# ---------------------------------------------------------------- page

class ToolPage(QtWidgets.QWidget):
    """The home of one catalogue item."""

    finishedRun = QtCore.pyqtSignal(str, int)       # run folder, exit code

    def __init__(self, item, host=None, parent=None):
        super().__init__(parent)
        self.item = item
        self.host = host or Host()
        self.spec = None             # the script's parser, once read
        self.fields = {}             # option -> widget
        self.proc = None
        self.current = None          # the run in progress
        self.last_spec_file = None   # SPEC written by a synthetic data set run
        self._workers = []
        self._build()

    # ---- layout
    def _build(self):
        it = self.item
        lay = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel('<b>%s</b>' % it.title)
        title.setTextFormat(Qt.RichText)
        doc = introspect.docstring(os.path.join(ROOT, it.script)) if it.script else ''
        title.setToolTip(doc or it.demonstrates)
        lay.addWidget(title)
        what = QtWidgets.QLabel(it.demonstrates)
        what.setWordWrap(True)
        what.setToolTip(doc or it.demonstrates)
        lay.addWidget(what)
        facts = QtWidgets.QHBoxLayout()
        bits = [texts.DATA.get(it.data, it.data)]
        if it.seconds is not None:
            bits.append('about %s' % ('%.0f s' % it.seconds if it.seconds >= 1 else '1 s'))
        if it.script:
            bits.append(it.script)
        self.factsLabel = QtWidgets.QLabel(' · '.join(bits))
        self.factsLabel.setToolTip('%s\nKind: %s' % (it.script or 'no script', catalog.KINDS[it.kind]))
        facts.addWidget(self.factsLabel)
        facts.addStretch(1)
        self.docsBox = QtWidgets.QWidget()
        _tip(self.docsBox, 'docsBox')
        dl = QtWidgets.QHBoxLayout(self.docsBox)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.addWidget(QtWidgets.QLabel(texts.LABELS['docsBox'] + ':'))
        self.docButtons = []
        for ref in it.docs + ((it.script,) if it.script else ()):
            b = QtWidgets.QToolButton()
            b.setText(os.path.basename(ref))
            b.setToolTip('Open %s' % ref)
            b.clicked.connect(lambda _=False, r=ref: open_path(doc_file(r)))
            dl.addWidget(b)
            self.docButtons.append(b)
        facts.addWidget(self.docsBox)
        lay.addLayout(facts)
        self.statusLabel = _tip(QtWidgets.QLabel(''), 'statusLabel')
        self.statusLabel.setWordWrap(True)
        lay.addWidget(self.statusLabel)

        split = QtWidgets.QSplitter(Qt.Horizontal)
        lay.addWidget(split, 1)
        left = QtWidgets.QWidget()
        ll = QtWidgets.QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        split.addWidget(left)
        self.settingsBox = QtWidgets.QWidget()
        sl = QtWidgets.QVBoxLayout(self.settingsBox)
        sl.setContentsMargins(0, 0, 0, 0)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(texts.LABELS['variationCombo']))
        self.variationCombo = _tip(QtWidgets.QComboBox(), 'variationCombo')
        self.variationCombo.addItem('Defaults')
        self.variationCombo.setItemData(0, 'The settings the committed products were made with (where there are '
                                           'any).', Qt.ToolTipRole)
        for i, v in enumerate(it.variations, start=1):
            self.variationCombo.addItem(v.label)
            self.variationCombo.setItemData(i, '%s\n(%s)' % (v.shows, v.source), Qt.ToolTipRole)
        row.addWidget(self.variationCombo, 1)
        self.sourceButton = _tip(QtWidgets.QToolButton(), 'sourceButton')
        self.sourceButton.setText(texts.LABELS['sourceButton'])
        row.addWidget(self.sourceButton)
        sl.addLayout(row)
        self.shows = QtWidgets.QLabel('')
        self.shows.setWordWrap(True)
        sl.addWidget(self.shows)
        self.formHost = QtWidgets.QWidget()
        self.formLayout = QtWidgets.QFormLayout(self.formHost)
        self.form = self.formHost
        _tip(self.formHost, 'form')
        self.formLayout.addRow(QtWidgets.QLabel('Reading the script\'s options…'))
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self.formHost)
        scroll.setWidgetResizable(True)
        sl.addWidget(scroll, 1)
        self.freeEdit = _tip(QtWidgets.QLineEdit(it.free), 'freeEdit')
        if it.free_help:
            self.freeEdit.setPlaceholderText(it.free_help)
            self.freeEdit.setToolTip(texts.TIPS['freeEdit'] + '\n' + it.free_help)
        self.freeRow = QtWidgets.QWidget()
        fr = QtWidgets.QHBoxLayout(self.freeRow)
        fr.setContentsMargins(0, 0, 0, 0)
        fr.addWidget(QtWidgets.QLabel(texts.LABELS['freeEdit']))
        fr.addWidget(self.freeEdit, 1)
        self.specButton = _tip(QtWidgets.QPushButton(texts.LABELS['specButton']), 'specButton')
        fr.addWidget(self.specButton)
        sl.addWidget(self.freeRow)
        self.freeRow.setVisible(False)
        self.commandEdit = _tip(QtWidgets.QLineEdit(), 'commandEdit')
        self.commandEdit.setReadOnly(True)
        sl.addWidget(self.commandEdit)
        buttons = QtWidgets.QHBoxLayout()
        label = {'window': 'Open window', 'dataset': 'Make and open' if self.host.open_spec else 'Make'}
        self.runButton = _tip(QtWidgets.QPushButton(label.get(it.kind, 'Run')), 'runButton')
        self.stopButton = _tip(QtWidgets.QPushButton(texts.LABELS['stopButton']), 'stopButton')
        self.stopButton.setEnabled(False)
        self.repoCheck = _tip(QtWidgets.QCheckBox(texts.LABELS['repoCheck']), 'repoCheck')
        buttons.addWidget(self.runButton)
        buttons.addWidget(self.stopButton)
        buttons.addWidget(self.repoCheck)
        buttons.addStretch(1)
        sl.addLayout(buttons)
        ll.addWidget(self.settingsBox, 2)
        self.log = _tip(QtWidgets.QPlainTextEdit(), 'log')
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(20000)
        self.log.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        ll.addWidget(self.log, 1)

        right = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        split.addWidget(right)
        split.setStretchFactor(1, 2)
        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(QtWidgets.QLabel(texts.LABELS['runCombo']))
        self.runCombo = _tip(QtWidgets.QComboBox(), 'runCombo')
        bar.addWidget(self.runCombo, 1)
        bar.addWidget(QtWidgets.QLabel(texts.LABELS['compareCombo']))
        self.compareCombo = _tip(QtWidgets.QComboBox(), 'compareCombo')
        bar.addWidget(self.compareCombo, 1)
        self.diffCheck = _tip(QtWidgets.QCheckBox(texts.LABELS['diffCheck']), 'diffCheck')
        bar.addWidget(self.diffCheck)
        self.compareAllButton = _tip(QtWidgets.QPushButton(texts.LABELS['compareAllButton']), 'compareAllButton')
        bar.addWidget(self.compareAllButton)
        self.openFolderButton = _tip(QtWidgets.QPushButton(texts.LABELS['openFolderButton']), 'openFolderButton')
        bar.addWidget(self.openFolderButton)
        self.openSpecButton = _tip(QtWidgets.QPushButton(texts.LABELS['openSpecButton']), 'openSpecButton')
        self.openSpecButton.setVisible(it.kind == 'dataset')
        self.openSpecButton.setEnabled(False)
        bar.addWidget(self.openSpecButton)
        rl.addLayout(bar)
        rsplit = QtWidgets.QSplitter(Qt.Horizontal)
        self.fileList = _tip(QtWidgets.QListWidget(), 'fileList')
        rsplit.addWidget(self.fileList)
        self.viewStack = QtWidgets.QStackedWidget()
        imgs = QtWidgets.QSplitter(Qt.Horizontal)
        self.viewA = ImageView()
        self.viewB = ImageView()
        imgs.addWidget(self.viewA)
        imgs.addWidget(self.viewB)
        self.viewStack.addWidget(imgs)
        self.textView = QtWidgets.QPlainTextEdit()
        self.textView.setReadOnly(True)
        self.textView.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.viewStack.addWidget(self.textView)
        rsplit.addWidget(self.viewStack)
        rsplit.setStretchFactor(1, 4)
        rl.addWidget(rsplit, 1)
        self.compareSummary = QtWidgets.QLabel('')
        self.compareSummary.setWordWrap(True)
        rl.addWidget(self.compareSummary)
        self.resultsBox = right

        if it.kind == 'external':
            self.settingsBox.setVisible(False)
            self.log.setVisible(False)
        if it.kind == 'window':
            right.setVisible(False)

        ok, why = available()
        if not ok and it.runnable:
            self.runButton.setEnabled(False)
            self.runButton.setToolTip(why)
        self.specButton.setVisible(bool(it.spec_option and self.host.spec_file))
        self.variationCombo.currentIndexChanged.connect(self.apply_variation)
        self.sourceButton.clicked.connect(self.open_source)
        self.freeEdit.textChanged.connect(self.update_command)
        self.specButton.clicked.connect(self.use_open_spec)
        self.runButton.clicked.connect(self.run)
        self.stopButton.clicked.connect(self.stop)
        self.repoCheck.toggled.connect(self.update_command)
        self.runCombo.currentIndexChanged.connect(self.fill_files)
        self.compareCombo.currentIndexChanged.connect(self.fill_files)
        self.diffCheck.toggled.connect(self.show_file)
        self.fileList.currentRowChanged.connect(self.show_file)
        self.compareAllButton.clicked.connect(self.compare_all)
        self.openFolderButton.clicked.connect(self.open_folder)
        self.openSpecButton.clicked.connect(self.open_written_spec)
        self.refresh_runs()
        self.apply_variation()

    # ---- options
    def set_parser(self, spec):
        """Build the form from the script's parser (or the free-text row)."""
        self.spec = spec or {'actions': []}
        while self.formLayout.rowCount():
            self.formLayout.removeRow(0)
        self.fields = {}
        if not self.item.runnable:
            return
        err = self.spec.get('error')
        if err and err != 'no argparse parser':
            self.formLayout.addRow(QtWidgets.QLabel('Options not read: %s' % err))
        if err:
            self.spec = {'actions': []}
        try:
            self.spec = runner.effective(self.spec, self.item.subcommand)
        except KeyError as e:
            self.formLayout.addRow(QtWidgets.QLabel(str(e)))
            self.spec = {'actions': []}
        for a in self.spec['actions']:
            key = a['options'][0] if a['options'] else a['dest']
            label = key
            tip = a['help'] or ''
            d = runner.default_text(a)
            if a['kind'] in ('flag', 'flag_false', 'const'):
                w = QtWidgets.QCheckBox()
                w.setChecked(False)
                w.toggled.connect(self.update_command)
            elif a['choices']:
                w = QtWidgets.QComboBox()
                if a['default'] is None:
                    w.addItem('')
                for c in a['choices']:
                    w.addItem(str(c))
                w.currentIndexChanged.connect(self.update_command)
            else:
                w = QtWidgets.QLineEdit()
                w.setPlaceholderText(d)
                w.textChanged.connect(self.update_command)
            extra = ('default: %s' % (d if d != '' else 'none')) if a['kind'] not in ('flag', 'flag_false') else ''
            if a['required']:
                extra = 'required'
            w.setToolTip('\n'.join(x for x in (tip, extra, texts.TIPS['form']) if x))
            self.fields[key] = w
            self.formLayout.addRow(label, w)
        self.freeRow.setVisible(not self.spec['actions'] or bool(self.item.free) or self.item.spec_option == 'free')
        if self.item.spec_option and self.item.spec_option != 'free' and self.item.spec_option in self.fields:
            self.specButton.setVisible(bool(self.host.spec_file))
            self.freeRow.setVisible(self.freeRow.isVisible() or bool(self.host.spec_file))
        self.apply_variation()

    def _merged(self, index=None):
        index = self.variationCombo.currentIndex() if index is None else index
        args = dict(self.item.defaults)
        if index > 0:
            args.update(self.item.variations[index - 1].args)
        return args

    def apply_variation(self, *_):
        i = self.variationCombo.currentIndex()
        v = self.item.variations[i - 1] if i > 0 else None
        self.shows.setText(v.shows if v else '')
        self.sourceButton.setEnabled(bool(v and v.source))
        args = self._merged(i)
        for a in (self.spec or {}).get('actions', []):
            key = a['options'][0] if a['options'] else a['dest']
            w = self.fields.get(key)
            if w is None:
                continue
            given = args.get(key, None)
            w.blockSignals(True)
            if isinstance(w, QtWidgets.QCheckBox):
                w.setChecked(bool(given) if given is not None else False)
            elif isinstance(w, QtWidgets.QComboBox):
                text = str(given) if given is not None else runner.default_text(a)
                k = w.findText(text)
                w.setCurrentIndex(k if k >= 0 else 0)
            else:
                if isinstance(given, (list, tuple)):
                    given = ' '.join(shlex.quote(str(x)) for x in given)
                w.setText('' if given is None else str(given))
            w.blockSignals(False)
        self.update_command()

    def values(self):
        out = {}
        for key, w in self.fields.items():
            if isinstance(w, QtWidgets.QCheckBox):
                out[key] = w.isChecked()
            elif isinstance(w, QtWidgets.QComboBox):
                out[key] = w.currentText()
            else:
                out[key] = w.text()
        return out

    def _default_values(self, committed=False):
        args = self.item.committed_args() if committed else self._merged(0)
        out = {}
        for a in (self.spec or {}).get('actions', []):
            key = a['options'][0] if a['options'] else a['dest']
            if key not in self.fields:
                continue
            given = args.get(key)
            if a['kind'] in ('flag', 'flag_false', 'const'):
                out[key] = bool(given)
            elif a['choices']:
                out[key] = str(given) if given is not None else runner.default_text(a)
            else:
                out[key] = '' if given is None else (' '.join(shlex.quote(str(x)) for x in given)
                                                     if isinstance(given, (list, tuple)) else str(given))
        return out

    def at_defaults(self, committed=False):
        """Whether the form holds the defaults (``committed``: the settings
        that made the committed products)."""
        return (self.values() == self._default_values(committed)
                and self.freeEdit.text().strip() == self.item.free.strip())

    def repo_allowed(self):
        it = self.item
        return (it.repo_ok and bool(it.committed) and it.runnable and it.data != 'private'
                and available()[0] and self.at_defaults(committed=True))

    def _build_args(self, out_dir):
        values = self.values()
        # without a parser (a packaged build, or a script whose options could not be read) there is no
        # option to set: the scratch settings are left out rather than raising
        if out_dir is not None and self.item.scratch_args and self.spec and self.spec.get('actions'):
            values.update(runner.values_from(self.spec, self.item.scratch_args))
        return runner.build_args(self.spec or {'actions': []}, values, out_dir, free=self.freeEdit.text())

    def update_command(self, *_):
        allowed = self.repo_allowed()
        self.repoCheck.setEnabled(allowed)
        if not allowed and self.repoCheck.isChecked():
            self.repoCheck.setChecked(False)
            return
        if not self.item.runnable:
            return
        if self.into_repo():
            out = os.path.join(ROOT, self.item.repo_out) if self.item.repo_out else None
        else:
            out = os.path.join(runner.runs_root(), self.item.id, '<date-time>')
        self.commandEdit.setText(runner.command_text(self.item.script, self._build_args(out)))

    def into_repo(self):
        return self.repoCheck.isChecked() and self.repoCheck.isEnabled()

    def open_source(self):
        i = self.variationCombo.currentIndex()
        if i > 0 and self.item.variations[i - 1].source:
            open_path(doc_file(self.item.variations[i - 1].source))

    def use_open_spec(self):
        path = self.host.spec_file() if self.host.spec_file else None
        if not path:
            self.log.appendPlainText('No SPEC file is open in the reader.')
            return
        opt = self.item.spec_option
        if opt == 'free':
            rest = shlex.split(self.freeEdit.text())[1:] if self.item.free else []
            self.freeEdit.setText(' '.join(shlex.quote(x) for x in [path] + rest))
        elif opt in self.fields:
            self.fields[opt].setText(path)

    # ---- staleness
    def refresh_status(self):
        if not self.item.committed:
            self.statusLabel.setText('No committed products: each run goes to a folder of its own.'
                                     if self.item.runnable else '')
            return
        if self.item.kind == 'external':
            self.statusLabel.setText('Made outside this repository; shown as committed, not regenerated here.')
            return
        self.statusLabel.setText('Checking the committed products against git history…')
        w = _Worker(lambda item=self.item: staleness.product_status(item))
        w.done.connect(self._status_done)
        self._workers.append(w)
        w.start()

    def _status_done(self, st):
        if isinstance(st, Exception):
            self.statusLabel.setText('Freshness not known (%s).' % st)
            return
        self.status = st
        colour = {'stale': '#a05a00', 'current': '#2a6a2a'}.get(st.state, '#444444')
        self.statusLabel.setText('<span style="color:%s">%s</span>' % (colour, st.line()))
        self.statusLabel.setToolTip(texts.TIPS['statusLabel'] + '\n\n' + st.details())

    # ---- running
    def run(self):
        it = self.item
        if self.proc is not None or not it.runnable:
            return
        ok, why = available()
        if not ok:
            self.log.appendPlainText(why)
            return
        if self.spec is None:
            self.set_parser(load_parsers([it.script])[it.script])
        into_repo = self.into_repo()
        run_dir = runner.new_run_dir(it.id)
        if into_repo:
            out = os.path.join(ROOT, it.repo_out) if it.repo_out else None
        else:
            out = run_dir
        values = self.values()
        missing = [k for k in runner.missing_required(self.spec, values) if runner.OUT not in str(values.get(k, ''))]
        if missing:
            self.log.appendPlainText('Fill in first: %s' % ', '.join(missing))
            return
        args = self._build_args(out)
        started = datetime.datetime.now().isoformat(timespec='seconds')
        self.current = dict(run_dir=run_dir, args=args, started=started, into_repo=into_repo,
                            stdout=open(os.path.join(run_dir, runner.STDOUT), 'w', encoding='utf-8'), text=[])
        runner.write_record(run_dir, it.id, it.script, args, started, into_repo=into_repo)
        self.proc = QtCore.QProcess(self)
        self.proc.setWorkingDirectory(ROOT)
        env = QtCore.QProcessEnvironment()
        for k, v in runner.environment(run_dir, gui=(it.kind == 'window')).items():
            env.insert(k, v)
        self.proc.setProcessEnvironment(env)
        self.proc.readyReadStandardOutput.connect(self._read_out)
        self.proc.readyReadStandardError.connect(self._read_err)
        self.proc.finished.connect(self._finished)
        self.proc.errorOccurred.connect(self._error)
        self.log.appendPlainText('$ %s' % runner.command_text(it.script, args))
        if into_repo:
            self.log.appendPlainText('Writing into the repository (%s).' % (it.repo_out or 'the script\'s default'))
        self.log.appendPlainText('')
        self.runButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.proc.start(runner.interpreter(), [os.path.join(ROOT, it.script)] + args)

    def _read_out(self):
        if self.proc is None:
            return
        text = bytes(self.proc.readAllStandardOutput()).decode('utf-8', 'replace')
        if self.current:
            self.current['stdout'].write(text)
            self.current['text'].append(text)
        self.log.moveCursor(QtGui.QTextCursor.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QtGui.QTextCursor.End)

    def _read_err(self):
        if self.proc is None:
            return
        text = bytes(self.proc.readAllStandardError()).decode('utf-8', 'replace')
        self.log.moveCursor(QtGui.QTextCursor.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QtGui.QTextCursor.End)

    def _error(self, err):
        if err == QtCore.QProcess.FailedToStart:
            self.log.appendPlainText('Could not start %s' % runner.interpreter())
            self._finished(-1, QtCore.QProcess.CrashExit)

    def _finished(self, code, status=None):
        if self.proc is None:
            return
        self._read_out()
        self._read_err()
        cur, it = self.current, self.item
        if status == QtCore.QProcess.CrashExit and code == 0:
            code = -1
        cur['stdout'].close()
        finished = datetime.datetime.now().isoformat(timespec='seconds')
        runner.write_record(cur['run_dir'], it.id, it.script, cur['args'], cur['started'], finished, code,
                            cur['into_repo'])
        if cur['into_repo'] and it.repo_stdout and code == 0:
            with open(os.path.join(ROOT, it.repo_stdout), 'w', encoding='utf-8', newline='\n') as f:
                f.write(''.join(cur['text']))
        self.log.appendPlainText('Finished (exit code %d) in %s' % (code, cur['run_dir']))
        self.proc.deleteLater()
        self.proc = None
        self.current = None
        self.runButton.setEnabled(available()[0])
        self.stopButton.setEnabled(False)
        if it.kind == 'dataset' and code == 0:
            spec = None
            for line in ''.join(cur['text']).splitlines():
                if line.startswith('SPEC '):
                    spec = line[5:].strip()
            self.last_spec_file = spec
            self.openSpecButton.setEnabled(bool(spec and self.host.open_spec))
            if spec and self.host.open_spec:
                self.host.open_spec(spec)
        if self.host.notify:
            self.host.notify('Tools: %s finished (exit code %d); output in %s'
                             % (it.title, code, it.repo_out if cur['into_repo'] and it.repo_out else cur['run_dir']))
        self.refresh_runs(select=('committed' if cur['into_repo'] else cur['run_dir']))
        if cur['into_repo']:
            self.refresh_status()
        self.finishedRun.emit(cur['run_dir'], code)

    def stop(self):
        if self.proc is not None:
            self.log.appendPlainText('Stopping…')
            self.proc.kill()

    # ---- results
    def _sources(self):
        out = [('Run %s' % os.path.basename(d) + self._run_note(d), d) for d in runner.past_runs(self.item.id)]
        if self.item.committed:
            out.insert(0 if not out else 1, ('Committed (repository)', 'committed'))
        return out

    @staticmethod
    def _run_note(d):
        rec = runner.read_record(d)
        if not rec:
            return ''
        if rec.get('exit_code') is None:
            return ' (running or stopped)'
        return ' (exit %s%s)' % (rec['exit_code'], ', into the repository' if rec.get('into_repository') else '')

    def refresh_runs(self, select=None):
        srcs = self._sources()
        for combo, first in ((self.runCombo, None), (self.compareCombo, ('Nothing', ''))):
            keep = select if combo is self.runCombo and select else combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            if first:
                combo.addItem(*first)
            for label, data in srcs:
                combo.addItem(label, data)
            k = combo.findData(keep) if keep else -1
            if combo is self.compareCombo and k < 0:
                k = combo.findData('committed') if self.runCombo.currentData() != 'committed' else 0
                if k < 0:
                    k = 0
            combo.setCurrentIndex(max(k, 0))
            combo.blockSignals(False)
        if self.runCombo.currentData() == self.compareCombo.currentData():
            self.compareCombo.setCurrentIndex(0)
        self.fill_files()

    def fill_files(self, *_):
        self.setA = file_set(self.item, self.runCombo.currentData())
        self.setB = file_set(self.item, self.compareCombo.currentData()) if self.compareCombo.currentData() else {}
        self.marks = {}
        self.fileList.blockSignals(True)
        self.fileList.clear()
        names = sorted(self.setA, key=lambda n: (os.path.splitext(n)[1].lower() not in runner.IMAGES, n))
        for n in names:
            self.fileList.addItem(n)
        self.fileList.blockSignals(False)
        self.compareSummary.setText('')
        if names:
            self.fileList.setCurrentRow(0)
        else:
            self.viewA.show_image(None, 'Nothing to show yet: Run makes a set.' if self.item.runnable
                                  else 'No files.')
            self.viewB.show_image(None, '')
            self.viewStack.setCurrentIndex(0)

    def _mark(self, name):
        if name in self.marks:
            return self.marks[name]
        if not self.setB:
            return None
        if name not in self.setB:
            m = ('+', None, None)
        else:
            state, frac, img = compare_images(self.setA[name], self.setB[name])
            m = ({'same': '=', 'differ': '≠', 'size': '≠'}[state], frac, img)
        self.marks[name] = m
        row = sorted(self.setA, key=lambda n: (os.path.splitext(n)[1].lower() not in runner.IMAGES, n)).index(name)
        item = self.fileList.item(row)
        if item is not None:
            item.setText('%s %s' % (m[0], name))
        return m

    def current_name(self):
        item = self.fileList.currentItem()
        if item is None:
            return None
        text = item.text()
        return text[2:] if text[:2] in ('= ', '≠ ', '+ ') else text

    def show_file(self, *_):
        name = self.current_name()
        if name is None:
            return
        path = self.setA.get(name)
        if os.path.splitext(name)[1].lower() in runner.IMAGES:
            self.viewStack.setCurrentIndex(0)
            self.viewA.show_image(path, path)
            if self.setB:
                m = self._mark(name)
                other = self.setB.get(name)
                if m and m[0] == '+':
                    self.viewB.show_image(None, 'Not in the compared set.')
                elif self.diffCheck.isChecked() and m and m[2] is not None:
                    self.viewB.show_image(m[2], 'Pixels that differ (white): %.3f %%' % (100 * m[1]))
                elif m and m[0] == '=':
                    self.viewB.show_image(other, 'Identical, pixel for pixel: ' + other)
                else:
                    self.viewB.show_image(other, other or '')
                self.viewB.setVisible(True)
            else:
                self.viewB.setVisible(False)
        else:
            self.viewStack.setCurrentIndex(1)
            try:
                with open(path, encoding='utf-8', errors='replace') as f:
                    text = f.read(400000)
            except OSError as e:
                text = str(e)
            self.textView.setPlainText(text)

    def compare_all(self):
        if not self.setB:
            self.compareSummary.setText('Choose a set to compare with first.')
            return
        same, differ, new = [], [], []
        for name in self.setA:
            if os.path.splitext(name)[1].lower() not in runner.IMAGES:
                continue
            m = self._mark(name)
            (same if m[0] == '=' else new if m[0] == '+' else differ).append((name, m[1]))
        missing = [n for n in self.setB if n not in self.setA and os.path.splitext(n)[1].lower() in runner.IMAGES]
        parts = ['%d same' % len(same), '%d differ' % len(differ)]
        if new:
            parts.append('%d new' % len(new))
        if missing:
            parts.append('%d not made' % len(missing))
        detail = '; '.join('%s %s' % (n, ('%.2f %%' % (100 * f)) if f is not None else 'size')
                           for n, f in differ[:8])
        self.compareSummary.setText('Images: ' + ', '.join(parts) + ('. Differ: ' + detail if detail else '.'))
        self.show_file()
        return dict(same=[n for n, _ in same], differ=[n for n, _ in differ], new=[n for n, _ in new],
                    missing=missing)

    def open_folder(self):
        d = self.runCombo.currentData()
        if d == 'committed' and self.item.committed:
            d = os.path.join(ROOT, self.item.committed[0])
            if not os.path.isdir(d):
                d = os.path.dirname(d)
        if d:
            open_path(d)

    def open_written_spec(self):
        if self.last_spec_file and self.host.open_spec:
            self.host.open_spec(self.last_spec_file)


# ---------------------------------------------------------------- window

class ToolsWindow(QtWidgets.QMainWindow):
    """The tree of items on the left, the page of the chosen item on the
    right (pages are made when first shown and kept)."""

    def __init__(self, parent=None, host=None):
        super().__init__(parent)
        if parent is not None:
            self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setObjectName('toolsWindow')
        self.setWindowTitle('LSS Reader tools: demonstrations and figure generators')
        self.host = host or Host()
        self.pages = {}
        split = QtWidgets.QSplitter(Qt.Horizontal)
        self.tree = _tip(QtWidgets.QTreeWidget(), 'tree')
        self.tree.setHeaderHidden(True)
        self.items = {}
        for cat, name in catalog.CATEGORIES:
            members = catalog.in_category(cat)
            if not members:
                continue
            top = QtWidgets.QTreeWidgetItem([name])
            top.setFlags(top.flags() & ~Qt.ItemIsSelectable)
            self.tree.addTopLevelItem(top)
            for t in members:
                child = QtWidgets.QTreeWidgetItem([t.title])
                child.setData(0, Qt.UserRole, t.id)
                child.setToolTip(0, t.demonstrates)
                top.addChild(child)
                self.items[t.id] = child
            top.setExpanded(True)
        split.addWidget(self.tree)
        self.stack = QtWidgets.QStackedWidget()
        self.overview = QtWidgets.QTextBrowser()
        self.overview.setOpenExternalLinks(False)
        self.overview.setOpenLinks(False)
        self.overview.anchorClicked.connect(self._anchor)
        self._load_overview()
        self.stack.addWidget(self.overview)
        split.addWidget(self.stack)
        split.setStretchFactor(1, 4)
        split.setSizes([300, 1100])
        self.setCentralWidget(split)
        self.tree.currentItemChanged.connect(self._tree_changed)
        self.loader = None
        self.parsers_ready = False
        ok, why = available()
        if not ok:
            self.parsers_ready = True
        if ok:
            self.loader = ParserLoader(catalog.scripts(), self)
            self.loader.loaded.connect(self._parsers_loaded)
            self.loader.start()
        self.statusBar().showMessage('' if ok else why)

    def _load_overview(self):
        from . import render
        self.overview.setMarkdown(render.page())

    def _anchor(self, url):
        frag = url.fragment() or url.toString().lstrip('#')
        item_id = frag.replace('-', '_')
        if item_id in catalog.BY_ID:
            self.show_item(item_id)

    def _tree_changed(self, cur, prev=None):
        if cur is None:
            return
        item_id = cur.data(0, Qt.UserRole)
        if item_id:
            self.show_item(item_id)

    def page(self, item_id):
        if item_id not in self.pages:
            item = catalog.get(item_id)
            p = ToolPage(item, self.host, self)
            self.pages[item_id] = p
            self.stack.addWidget(p)
            if item.runnable:
                spec = cached_parser(item.script)
                if spec is not None:
                    p.set_parser(spec)
                elif self.loader is None:
                    p.set_parser({'error': available()[1]})
            else:
                p.set_parser(None)
            p.refresh_status()
        return self.pages[item_id]

    def show_item(self, item_id):
        """Show the page of ``item_id`` (None or '': the overview)."""
        if not item_id:
            self.stack.setCurrentWidget(self.overview)
            return None
        p = self.page(item_id)
        self.stack.setCurrentWidget(p)
        tree_item = self.items.get(item_id)
        if tree_item is not None and self.tree.currentItem() is not tree_item:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(tree_item)
            self.tree.blockSignals(False)
        return p

    def _parsers_loaded(self, specs):
        for item_id, p in self.pages.items():
            if p.item.runnable and p.spec is None:
                p.set_parser(specs.get(p.item.script) or cached_parser(p.item.script))
        self.parsers_ready = True

    def closeEvent(self, e):
        wait_workers(events=False)
        super().closeEvent(e)

    def wait_parsers(self, timeout=60.0):
        """Process events until the options of every script are read (tests)."""
        import time
        end = time.time() + timeout
        while not getattr(self, 'parsers_ready', False) and time.time() < end:
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)
        return getattr(self, 'parsers_ready', False)
