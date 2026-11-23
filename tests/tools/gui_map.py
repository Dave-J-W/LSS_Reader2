"""Check and render the GUI workflow map and control inventory (F67).

The map (``docs/gui/workflows.yaml``) and the inventory
(``docs/gui/inventory/*.yaml``) are hand-written YAML; the schema is in
``docs/gui/README.md``. This tool

* **checks** them:
  - every inventory entry has an id, and its ``workflows`` come from the
    fixed list of workflow ids;
  - every workflow id is from the fixed list; every ``uses:`` names a
    shared step and every ``goto:`` target a step of the same workflow;
  - every control id named in a workflow step exists in the inventory
    (dialog widgets may be written ``<dialog>.<widget>``; a match on the
    widget part alone is accepted and reported as *loose*);
  - question ids named in the map appear in ``docs/gui/questions*.md``
    or ``docs/gui/questions/*.md`` (a warning only);
  - with ``--window``: every inventory id resolves to a widget or QAction
    of a live offscreen ``MainWindow`` (its code-built dialogs are built
    for the purpose), to an attribute of ``window.ui`` or the window, or to
    an objectName in a ``.ui`` file (``<stem>.<widget>`` against
    ``<stem>.ui``); an id found only in ``mainwindow.py`` text is reported
    as such; and, the other way, every named interactive control of that
    window (buttons, check boxes, combos, line edits, spin boxes, sliders,
    lists, text boxes) is in the inventory, so a control added to the
    window without an entry is a problem (``tests/test_gui_map.py`` runs
    this check in the quick suite);
* **renders** ``docs/gui/workflows.md`` (per workflow: a summary, a steps
  table and a Mermaid ``flowchart TD``; then a control x workflow matrix per
  tab) and ``docs/gui/inventory.md`` (one table per area).

The inventory is written by other hands while the map is written; missing
or partial files are tolerated (a file that does not parse is reported and
skipped). Missing control ids are listed, never invented.

Usage (from anywhere; the tool changes to the repository root)::

    python tests/tools/gui_map.py              # check (report only) and render
    python tests/tools/gui_map.py --check      # exit 1 when there are problems
    python tests/tools/gui_map.py --window     # also resolve ids in a live window
    python tests/tools/gui_map.py --no-render  # check only

Map extensions understood here (documented at the top of workflows.yaml):
``uses: <shared step id>`` in a step, and ``decision: "<question>"`` with
``goto: {<answer>: <step id>}`` for decision points.
"""
import argparse
import glob
import os
import re
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GUI = os.path.join(ROOT, 'docs', 'gui')

WORKFLOW_IDS = ('burn-ref', 'burn-gid', 'burn-fluo', 'reflectivity', 'gid', 'xfntr', 'exafs', 'gisaxs',
                'cuts', 'alignment', 'mca-look', 'flex-plot', 'session', 'general')
STEP_FIELDS = ('do', 'where', 'controls', 'user_decides', 'automatic', 'could_be_automatic', 'known_from', 'issues')


# ---------------------------------------------------------------- loading

def load_yaml(path, report):
    try:
        with open(path, encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        report.warn('%s: not found' % rel(path))
    except yaml.YAMLError as e:
        report.problem('%s: does not parse (%s)' % (rel(path), str(e).replace('\n', ' ')))
    return None


def load_inventory(report):
    """{id: entry} and the entries in file order, each with '_file'."""
    entries = []
    files = sorted(glob.glob(os.path.join(GUI, 'inventory', '*.yaml')) + glob.glob(os.path.join(GUI, 'inventory', '*.yml')))
    if not files:
        report.warn('docs/gui/inventory/: no inventory files yet')
    for path in files:
        data = load_yaml(path, report)
        if data is None:
            continue
        if isinstance(data, dict):           # tolerate {'controls': [...]} or {area: [...]}
            lists = [v for v in data.values() if isinstance(v, list)]
            data = [e for v in lists for e in v]
        if not isinstance(data, list):
            report.problem('%s: expected a list of entries' % rel(path))
            continue
        for k, e in enumerate(data):
            if not isinstance(e, dict) or not e.get('id'):
                report.problem('%s: entry %d has no id' % (rel(path), k + 1))
                continue
            e = dict(e)
            e['_file'] = os.path.basename(path)
            entries.append(e)
    by_id = {}
    for e in entries:
        if e['id'] in by_id:
            report.warn('inventory id %r appears in %s and %s' % (e['id'], by_id[e['id']]['_file'], e['_file']))
        by_id.setdefault(e['id'], e)
    return by_id, entries


def load_map(report):
    data = load_yaml(os.path.join(GUI, 'workflows.yaml'), report) or {}
    shared = {s['id']: s for s in (data.get('shared_steps') or []) if isinstance(s, dict) and 'id' in s}
    flows = [w for w in (data.get('workflows') or []) if isinstance(w, dict)]
    return shared, flows


def resolved_steps(flow, shared):
    """The workflow's steps with ``uses:`` filled in from the shared steps."""
    out = []
    for s in flow.get('steps') or []:
        base = dict(shared.get(s.get('uses'), {})) if s.get('uses') else {}
        base.update(s)
        base['id'] = s.get('id', base.get('id'))
        if isinstance(base.get('automatic'), bool):      # YAML reads yes/no as booleans
            base['automatic'] = 'yes' if base['automatic'] else 'no'
        for k in ('controls', 'issues'):
            v = base.get(k)
            base[k] = [] if v in (None, '') else (v if isinstance(v, list) else [v])
        out.append(base)
    return out


def question_ids():
    ids = set()
    for path in glob.glob(os.path.join(GUI, 'questions*.md')) + glob.glob(os.path.join(GUI, 'questions', '*.md')):
        with open(path, encoding='utf-8') as f:
            ids.update(re.findall(r'\bQ-[A-Z]+-\d+\b', f.read()))
    return ids


# ---------------------------------------------------------------- checking

class Report:
    def __init__(self):
        self.problems, self.warnings, self.info = [], [], []

    def problem(self, text):
        self.problems.append(text)

    def warn(self, text):
        self.warnings.append(text)

    def note(self, text):
        self.info.append(text)

    def text(self):
        lines = ['GUI map check', '=============', '']
        lines += self.info + ['']
        lines.append('Problems: %d' % len(self.problems))
        lines += ['  - ' + p for p in self.problems]
        lines.append('Warnings: %d' % len(self.warnings))
        lines += ['  - ' + w for w in self.warnings]
        return '\n'.join(lines)


def match_control(cid, inv):
    """(inventory id, how) for a control id named in the map, or (None, None)."""
    if cid in inv:
        return cid, 'exact'
    tail = cid.split('.')[-1]
    cands = [i for i in inv if i.split('.')[-1] == tail]
    if len(cands) == 1:
        return cands[0], 'loose'
    if len(cands) > 1:
        head = cid.split('.')[0] if '.' in cid else ''
        best = [c for c in cands if head and c.startswith(head)]
        return (best or cands)[0], 'loose'
    return None, None


def check(inv, entries, shared, flows, report):
    report.note('Inventory: %d entries in %d file(s); map: %d workflows, %d shared steps'
                % (len(entries), len({e['_file'] for e in entries}), len(flows), len(shared)))
    for e in entries:
        wf = e.get('workflows') or []
        if not isinstance(wf, list):
            wf = [wf]
        bad = [w for w in wf if w not in WORKFLOW_IDS]
        if bad:
            report.problem('inventory %s (%s): unknown workflow id(s) %s' % (e['id'], e['_file'], ', '.join(map(str, bad))))
    seen = set()
    for flow in flows:
        fid = flow.get('id')
        if fid not in WORKFLOW_IDS:
            report.problem('workflow id %r is not in the fixed list' % fid)
        if fid in seen:
            report.problem('workflow %r appears twice' % fid)
        seen.add(fid)
        steps = resolved_steps(flow, shared)
        ids = [s.get('id') for s in steps]
        for s in flow.get('steps') or []:
            if s.get('uses') and s['uses'] not in shared:
                report.problem('%s: uses unknown shared step %r' % (s.get('id'), s['uses']))
        for s in steps:
            for target in (s.get('goto') or {}).values():
                if target not in ids:
                    report.problem('%s: goto target %r is not a step of %s' % (s.get('id'), target, fid))
    missing, loose = {}, {}
    for flow in flows:
        for s in resolved_steps(flow, shared):
            for cid in s['controls']:
                got, how = match_control(str(cid), inv)
                if got is None:
                    missing.setdefault(str(cid), set()).add(flow.get('id'))
                elif how == 'loose':
                    loose[str(cid)] = got
    for cid in sorted(missing):
        report.problem('control %s (in %s) is not in the inventory' % (cid, ', '.join(sorted(missing[cid]))))
    for cid in sorted(loose):
        report.warn('control %s matched the inventory id %s loosely (by widget name)' % (cid, loose[cid]))
    known_q = question_ids()
    for flow in flows:
        for q in flow.get('questions') or []:
            if q not in known_q:
                report.warn('%s: question %s not found in docs/gui/questions*' % (flow.get('id'), q))
    report.missing_controls = missing
    return missing


def check_window(entries, report):
    """Resolve every inventory id in a live offscreen MainWindow or a .ui file."""
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('MPLBACKEND', 'Agg')
    os.environ.setdefault('LSS_READER_LOG_DIR', tempfile.mkdtemp(prefix='lss_guimap_logs_'))
    os.environ.setdefault('LSS_READER_PREFS', os.path.join(tempfile.mkdtemp(prefix='lss_guimap_prefs_'), 'p.json'))
    sys.path.insert(0, ROOT)
    from PyQt5.QtWidgets import QApplication, QWidget, QAction
    from PyQt5.QtCore import QObject
    app = QApplication.instance() or QApplication([])
    import mainwindow
    w = mainwindow.MainWindow()
    w.messageBox = lambda *a, **k: None
    for build in ('buildPreferences', 'buildGIDWorksheet', 'buildBurnDialog'):
        try:                                 # code-built dialogs: their widgets exist once built
            getattr(w, build)()
        except Exception as e:               # noqa: BLE001 (a dialog that needs data is skipped)
            report.note('--window: %s() not built without data (%s)' % (build, type(e).__name__))
    for which in ('cut', 'mca'):
        try:
            w.buildCutFitDialog(which)
        except Exception:                    # noqa: BLE001
            pass
    names = {o.objectName() for o in w.findChildren(QObject) if o.objectName()}
    for top in app.allWidgets():
        if top.objectName():
            names.add(top.objectName())
        names.update(o.objectName() for o in top.findChildren(QObject) if o.objectName())
    with open(os.path.join(ROOT, 'mainwindow.py'), encoding='utf-8') as f:
        code = f.read()
    ui_names = {}
    for path in glob.glob(os.path.join(ROOT, '*.ui')):
        with open(path, encoding='utf-8') as f:
            ui_names[os.path.splitext(os.path.basename(path))[0]] = set(re.findall(r'name="([^"]+)"', f.read()))
    found = code_only = 0
    for e in entries:
        cid = str(e['id'])
        head, _, tail = cid.rpartition('.')
        stem = re.sub(r'^ui', '', head) if head else ''
        ok = (cid in names or hasattr(w.ui, cid) or isinstance(getattr(w, cid, None), (QWidget, QAction))
              or (tail in names if head else False)
              or (stem in ui_names and tail in ui_names[stem])
              or (not head and any(cid in s for s in ui_names.values()))
              or (not head and cid in ui_names)                       # a dialog named by its .ui file
              or (cid.endswith('_toggleViewAction') and cid[:-len('_toggleViewAction')] in names))
        if ok:
            found += 1
        elif re.search(r"setObjectName\(['\"]%s['\"]\)|self\.%s\s*=" % (re.escape(tail or cid), re.escape(tail or cid)), code):
            code_only += 1
            report.warn('--window: %s found only in mainwindow.py text (built later, e.g. with data)' % cid)
        else:
            report.problem('--window: inventory id %s (%s) is not in the window, its dialogs or a .ui file' % (cid, e['_file']))
    report.note('--window: %d of %d inventory ids resolved; %d in code text only' % (found, len(entries), code_only))
    unlisted = uninventoried_controls(w, entries)
    for kind, name in unlisted:
        report.problem('--window: control %s (%s) is in the window but not in the inventory: add an entry to '
                       'docs/gui/inventory/<area>.yaml (schema: docs/gui/README.md)' % (name, kind))
    report.note('--window: every named control of the main window is inventoried' if not unlisted else
                '--window: %d named control(s) of the main window not inventoried' % len(unlisted))
    w.close()


# Qt's own children (tab-bar scroll arrows and the like), never the reader's
QT_INTERNAL = ('ScrollLeftButton', 'ScrollRightButton')


def uninventoried_controls(w, entries):
    """(class name, objectName) of every named interactive control of the
    window and its code-built dialogs that no inventory id names, exactly or
    as the widget part of ``<dialog>.<widget>``. This is the direction that
    catches a control added to the window without a map entry (2026-11-23:
    the covariance box added on 2026-11-22 went unnoticed by the other
    checks)."""
    from PyQt5.QtWidgets import (QAbstractButton, QComboBox, QLineEdit, QAbstractSpinBox, QAbstractSlider,
                                 QAbstractItemView, QTextEdit, QPlainTextEdit, QScrollBar)
    known = set()
    for e in entries:
        cid = str(e['id'])
        known.update((cid, cid.split('.')[-1]))
    kinds = (QAbstractButton, QComboBox, QLineEdit, QAbstractSpinBox, QAbstractSlider, QAbstractItemView,
             QTextEdit, QPlainTextEdit)
    out = set()
    for o in w.findChildren(kinds):
        name = o.objectName()
        if (not name or name.startswith('qt_') or name in QT_INTERNAL or isinstance(o, QScrollBar)
                or name in known):
            continue
        out.add((type(o).__name__, name))
    return sorted(out, key=lambda t: t[1])


# ---------------------------------------------------------------- rendering

def cell(v):
    if v is None:
        return ''
    if isinstance(v, (list, tuple)):
        v = '; '.join(str(x) for x in v)
    return str(v).replace('|', '\\|').replace('\n', ' ').strip()


def mermaid_text(s, n=60):
    s = cell(s)
    s = s if len(s) <= n else s[:n - 1].rstrip() + '…'
    return s.replace('"', '#quot;').replace('<', '&lt;').replace('>', '&gt;')


def node(sid):
    return re.sub(r'[^A-Za-z0-9_]', '_', str(sid))


def flowchart(steps):
    out = ['```mermaid', 'flowchart TD']
    for s in steps:
        shape = '(["%s"])' if s.get('automatic') == 'yes' else '["%s"]'
        out.append('    %s%s' % (node(s['id']), shape % ('%s: %s' % (s['id'].split('.')[-1], mermaid_text(s.get('do'))))))
        if s.get('decision'):
            out.append('    %s_d{"%s"}' % (node(s['id']), mermaid_text(s['decision'], 50)))
    for k, s in enumerate(steps):
        nxt = steps[k + 1]['id'] if k + 1 < len(steps) else None
        src = node(s['id'])
        if s.get('decision'):
            out.append('    %s --> %s_d' % (src, src))
            src = src + '_d'
            for label, target in (s.get('goto') or {}).items():
                out.append('    %s -- "%s" --> %s' % (src, mermaid_text(label, 40), node(target)))
            if nxt:
                out.append('    %s -- "yes" --> %s' % (src, node(nxt)))
        elif nxt:
            out.append('    %s --> %s' % (src, node(nxt)))
    out += ['    classDef auto fill:#e6f4ea,stroke:#4a8;',
            '    class %s auto;' % ','.join(node(s['id']) for s in steps if s.get('automatic') == 'yes') if any(
                s.get('automatic') == 'yes' for s in steps) else '', '```']
    return [l for l in out if l]


def render_workflows(inv, entries, shared, flows, missing):
    L = ['# The workflow map', '',
         'Generated by `python tests/tools/gui_map.py` from `docs/gui/workflows.yaml` and '
         '`docs/gui/inventory/*.yaml`; do not edit by hand. Schema and plan: `docs/gui/README.md`. '
         'Questions for the owner: `docs/gui/questions/workflows.md`.', '',
         'In the flowcharts, rounded green boxes are steps that are automatic today; diamonds are the user\'s '
         'decisions. In the tables, a control marked `?` is not (yet) in the inventory.', '',
         '| Workflow | Priority | Steps | Automatic today (yes / partly / no) | Issues |', '|---|---|---|---|---|']
    for f in sorted(flows, key=lambda f: (f.get('priority', 9), WORKFLOW_IDS.index(f['id']) if f.get('id') in WORKFLOW_IDS else 99)):
        st = resolved_steps(f, shared)
        a = [s.get('automatic') for s in st]
        L.append('| [%s](#%s) | %s | %d | %d / %d / %d | %d |' % (
            f.get('id'), f.get('id'), f.get('priority', ''), len(st), a.count('yes'), a.count('partly'), a.count('no'),
            sum(len(s['issues']) for s in st)))
    L.append('')
    for f in sorted(flows, key=lambda f: f.get('priority', 9)):
        st = resolved_steps(f, shared)
        L += ['<a id="%s"></a>' % f.get('id'), '## %s — %s' % (f.get('id'), f.get('name', '')), '',
              '**Priority** %s. **Known from:** %s.' % (f.get('priority', ''), cell(f.get('known_from'))), '',
              '**Experiment.** %s' % cell(f.get('experiment')), '',
              '**Recognised by.** %s' % cell(f.get('recognised_by')), '',
              '**Outputs:** %s. **Script:** `%s`. **Questions:** %s.' % (
                  cell(f.get('outputs')), cell(f.get('scripted_as')), cell(f.get('questions'))), '']
        L += flowchart(st) + ['']
        L += ['| Step | Do | Where | Controls | User decides | Automatic | Could be automatic | Known from | Issues |',
              '|---|---|---|---|---|---|---|---|---|']
        for s in st:
            ctr = ', '.join('`%s`%s' % (c, '' if match_control(str(c), inv)[0] else ' ?') for c in s['controls'])
            L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                cell(s['id']) + (' (%s)' % s['uses'] if s.get('uses') else ''), cell(s.get('do')), cell(s.get('where')),
                ctr, cell(s.get('user_decides')), cell(s.get('automatic')), cell(s.get('could_be_automatic')),
                cell(s.get('known_from')), '<br>'.join(cell(i) for i in s['issues'])))
        L.append('')
    # control x workflow matrix per tab
    L += ['## Controls by workflow', '',
          '`S` named in a workflow step; `i` listed for the workflow in the inventory only; `B` both. '
          'Rows: inventory entries grouped by the first part of `where` (the tab or dialog); controls named in '
          'the map but missing from the inventory are listed at the end.', '']
    named = {}
    for f in flows:
        for s in resolved_steps(f, shared):
            for c in s['controls']:
                got = match_control(str(c), inv)[0] or str(c)
                named.setdefault(got, set()).add(f.get('id'))
    cols = [w for w in WORKFLOW_IDS]
    groups = {}
    for e in entries:
        groups.setdefault(str(e.get('where') or e['_file']).split('>')[0].strip() or e['_file'], []).append(e)
    head = '| Control | ' + ' | '.join(cols) + ' |'
    sep = '|---|' + '---|' * len(cols)
    for g in sorted(groups):
        L += ['### %s' % g, '', head, sep]
        for e in groups[g]:
            inv_w = set(e.get('workflows') or [])
            map_w = named.get(e['id'], set())
            marks = ['B' if (w in inv_w and w in map_w) else 'S' if w in map_w else 'i' if w in inv_w else '' for w in cols]
            L.append('| `%s` %s | %s |' % (e['id'], cell(e.get('label')), ' | '.join(marks)))
        L.append('')
    if missing:
        L += ['### Named in the map, not in the inventory', '', head, sep]
        for c in sorted(missing):
            L.append('| `%s` | %s |' % (c, ' | '.join('S' if w in missing[c] else '' for w in cols)))
        L.append('')
    return '\n'.join(L) + '\n'


def render_inventory(entries):
    L = ['# Control inventory', '',
         'Generated by `python tests/tools/gui_map.py` from `docs/gui/inventory/*.yaml`; do not edit by hand.', '']
    if not entries:
        L.append('No inventory entries yet.')
    files = {}
    for e in entries:
        files.setdefault(e['_file'], []).append(e)
    for fn in sorted(files):
        L += ['## %s' % fn.rsplit('.', 1)[0], '',
              '| Id | Kind | Label | Where | Handler | Does | Workflows | Needs | Shown | Tooltip | Notes |',
              '|---|---|---|---|---|---|---|---|---|---|---|']
        for e in files[fn]:
            L.append('| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % tuple(
                [cell(e['id'])] + [cell(e.get(k)) for k in ('kind', 'label', 'where', 'handler', 'does', 'workflows',
                                                           'needs', 'shown', 'tooltip', 'notes')]))
        L.append('')
    return '\n'.join(L) + '\n'


def rel(path):
    return os.path.relpath(path, ROOT)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--check', action='store_true', help='exit 1 when there are problems')
    ap.add_argument('--window', action='store_true', help='resolve inventory ids in a live offscreen window')
    ap.add_argument('--no-render', action='store_true', help='do not write workflows.md and inventory.md')
    args = ap.parse_args(argv)
    os.chdir(ROOT)
    report = Report()
    inv, entries = load_inventory(report)
    shared, flows = load_map(report)
    missing = check(inv, entries, shared, flows, report)
    if args.window:
        check_window(entries, report)
    if not args.no_render:
        with open(os.path.join(GUI, 'workflows.md'), 'w', encoding='utf-8') as f:
            f.write(render_workflows(inv, entries, shared, flows, missing))
        with open(os.path.join(GUI, 'inventory.md'), 'w', encoding='utf-8') as f:
            f.write(render_inventory(entries))
        report.note('Rendered docs/gui/workflows.md and docs/gui/inventory.md')
    print(report.text())
    return 1 if (args.check and report.problems) else 0


if __name__ == '__main__':
    sys.exit(main())
