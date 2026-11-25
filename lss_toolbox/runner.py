"""Command lines, output folders and run records of the Tools collection.

A run writes into a folder of its own, ``<runs>/<item id>/<date-time>``
(``<runs>`` is ``$LSS_READER_TOOLS_DIR`` or ``~/.lss_reader/tools``), never
into the repository, unless the user asks to replace the committed
products (only with the item's default settings and public data; see
``Tool.repo_ok``). The token ``{out}`` in an option's value stands for
that folder. The run's environment sends the reader's logs and preferences
into the run folder too, so a tool that opens the reader's window writes
nothing beside the SPEC files and leaves the user's preferences alone.

``run.json`` in the run folder records the command, the times, the exit
code, the git commit and whether the working tree differed from it, so
that a figure on disk says what code made it. A run without a window (the
audit) goes through ``lss_toolbox.trace``, whose ``trace.json`` lists the
repository modules the script imported and the files it read: what the
products actually depend on (``staleness.verification``).
"""
import datetime
import glob
import json
import os
import shlex
import sys

from . import ROOT

OUT = '{out}'
RECORD = 'run.json'
TRACE = 'trace.json'
STDOUT = 'output.txt'
IMAGES = ('.png', '.jpg', '.jpeg', '.svg', '.gif')
TEXTS = ('.md', '.txt', '.csv', '.json', '.log')


def runs_root():
    return os.environ.get('LSS_READER_TOOLS_DIR') or os.path.join(os.path.expanduser('~'), '.lss_reader', 'tools')


def new_run_dir(item_id, now=None):
    now = now or datetime.datetime.now()
    base = os.path.join(runs_root(), item_id, now.strftime('%Y%m%d-%H%M%S'))
    path, n = base, 1
    while os.path.exists(path):
        n += 1
        path = '%s-%d' % (base, n)
    os.makedirs(path)
    return path


def past_runs(item_id):
    """Run folders of an item, newest first."""
    d = os.path.join(runs_root(), item_id)
    if not os.path.isdir(d):
        return []
    return sorted((os.path.join(d, x) for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))), reverse=True)


# ---------------------------------------------------------------- values

def effective(spec, subcommand=None):
    """The spec a form and a command line use: for a script with
    subcommands, the top-level options followed by those of ``subcommand``
    (``command`` names it, and goes first on the command line)."""
    if not spec.get('subcommands'):
        return spec
    if subcommand not in spec['subcommands']:
        raise KeyError('the script has subcommands %s; the catalogue names %r'
                       % (', '.join(spec['subcommands']), subcommand))
    sub = spec['subcommands'][subcommand]
    return {'prog': spec.get('prog', ''), 'description': sub.get('description') or spec.get('description', ''),
            'actions': list(spec['actions']) + list(sub['actions']), 'command': subcommand}


def action_for(spec, option):
    """The parser action named by an option string ('--out') or a
    positional's dest; None if the parser has none."""
    for a in spec.get('actions', []):
        if option in a['options'] or (not a['options'] and option == a['dest']):
            return a
    return None


def default_text(action):
    """An action's default as the text a form field shows."""
    d = action['default']
    if action['kind'] in ('flag', 'flag_false', 'const'):
        return False                                   # a flag's field is "given or not"; not given by default
    if d is None:
        return ''
    if isinstance(d, list):
        return ' '.join(str(x) for x in d)
    return str(d)


def values_from(spec, args):
    """Form values (option or dest -> text or bool) from a dict keyed by
    option strings, as the catalogue writes defaults and variations."""
    vals = {}
    for key, v in (args or {}).items():
        a = action_for(spec, key)
        if a is None:
            raise KeyError('the script has no option %s' % key)
        vals[a['options'][0] if a['options'] else a['dest']] = v
    return vals


def build_args(spec, values, out_dir, free=''):
    """The argument list after the script name. ``values``: option (or a
    positional's dest) -> text or bool, as the form holds them; options
    left empty or at their default are not passed (the script's own
    default applies), flags only when ticked. ``{out}`` -> ``out_dir``
    (an option whose value is ``{out}`` is dropped when ``out_dir`` is
    None: the script's own default output then applies). ``free``: extra
    arguments typed as text (scripts without argparse)."""
    args, positional = [], []
    for a in spec.get('actions', []):
        key = a['options'][0] if a['options'] else a['dest']
        if key not in values:
            continue
        v = values[key]
        if a['kind'] in ('flag', 'const'):
            if v is True or v == 'true':
                args.append(key)
            continue
        if a['kind'] == 'flag_false':                 # a store_false option: ticked means given, as any flag
            if v is True or v == 'true':
                args.append(key)
            continue
        text = str(v).strip()
        if OUT in text:
            if out_dir is None:
                continue
            text = text.replace(OUT, out_dir)
        if not text or (text == default_text(a) and not a['required']):
            continue
        many = a['nargs'] in ('+', '*') or isinstance(a['nargs'], int) and a['nargs'] > 1
        items = shlex.split(text) if (many or a['kind'] == 'append' or not a['options']) else [text]
        if not a['options']:
            positional.extend(items)
        elif a['kind'] == 'append':
            for it in items:
                args += [key, it]
        else:
            if len(items) == 1 and items[0].startswith('-') and key.startswith('--'):
                args.append('%s=%s' % (key, items[0]))      # '--beta=-0.5,3': argparse reads '-0.5,3' as an option
            else:
                args += [key] + items
    if free:
        positional += shlex.split(free.replace(OUT, out_dir or ''))
    head = [spec['command']] if spec.get('command') else []
    return head + args + positional


def missing_required(spec, values):
    """Options the parser requires that the values leave empty."""
    miss = []
    for a in spec.get('actions', []):
        key = a['options'][0] if a['options'] else a['dest']
        if a['required'] and a['kind'] in ('store', 'append') and not str(values.get(key, '')).strip():
            miss.append(key)
    return miss


def command_text(script, args):
    """The command as it would be typed at the repository root."""
    return ' '.join(shlex.quote(x) for x in ['python', script] + list(args))


def environment(run_dir, base=None, gui=False):
    """Environment of a run: no display needed for figures (``gui``: the
    run opens a window, so the display is left as it is), the reader's logs
    and preferences inside the run folder."""
    env = dict(base if base is not None else os.environ)
    if not gui:
        env['MPLBACKEND'] = 'Agg'
        env['QT_QPA_PLATFORM'] = env.get('LSS_TOOLBOX_QPA', 'offscreen')
    if run_dir:
        env['LSS_READER_LOG_DIR'] = os.path.join(run_dir, 'logs')
        env['LSS_READER_PREFS'] = os.path.join(run_dir, 'preferences.json')
    env['PYTHONUNBUFFERED'] = '1'
    return env


def interpreter():
    return sys.executable


# ---------------------------------------------------------------- records

def write_record(run_dir, item_id, script, args, started, finished=None, code=None, into_repo=False):
    from . import staleness
    rec = {
        'item': item_id,
        'command': command_text(script, args),
        'script': script,
        'args': list(args),
        'started': started,
        'finished': finished,
        'exit_code': code,
        'commit': staleness.head(),
        'modified_sources': staleness.modified(staleness.dependencies_of_script(script)) if script else [],
        'into_repository': bool(into_repo),
        'environment': environment_versions(),
    }
    with open(os.path.join(run_dir, RECORD), 'w', encoding='utf-8') as f:
        json.dump(rec, f, indent=1)
    return rec


LIBRARIES = ('numpy', 'scipy', 'matplotlib', 'PIL', 'PyQt5', 'lmfit', 'contourpy', 'kiwisolver', 'fontTools')


def environment_versions():
    """Python, the platform and the versions of what computes and draws the
    products: a figure can differ from a committed one because of these
    alone (measured 2026-11-23: the stray-light and beam figures, same code,
    other environment; 2026-11-24 the review found them differing again
    under the same pinned numpy, scipy, matplotlib and pillow). So also the
    machine, numpy's SIMD level (its ufuncs choose code by CPU), the
    freetype matplotlib draws text with (text extents place the axes under
    ``tight_layout``) and matplotlib's helper libraries, which the build
    does not pin (2026-11-25)."""
    import importlib
    import platform
    out = {'python': platform.python_version(), 'platform': platform.platform(), 'machine': platform.machine()}
    for name in LIBRARIES:
        try:
            mod = importlib.import_module(name)
            if name == 'PyQt5':
                from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
                out[name] = '%s (Qt %s)' % (PYQT_VERSION_STR, QT_VERSION_STR)
            elif name == 'fontTools':
                out[name] = getattr(mod, 'version', '?')
            else:
                out[name] = getattr(mod, '__version__', '?')
        except Exception:                      # noqa: BLE001 (absent library: not recorded)
            continue
    try:
        from matplotlib import ft2font
        out['freetype'] = '%s (%s)' % (ft2font.__freetype_version__, getattr(ft2font, '__freetype_build_type__', '?'))
    except Exception:                          # noqa: BLE001
        pass
    try:
        from numpy._core._multiarray_umath import __cpu_dispatch__, __cpu_features__
        enabled = [k for k in __cpu_dispatch__ if __cpu_features__.get(k)]
        out['numpy_simd'] = enabled[-1] if enabled else 'baseline'
    except Exception:                          # noqa: BLE001 (another numpy: not recorded)
        pass
    return out


def environment_diff(recorded, now=None):
    """['name: recorded → now', ...] for the entries of two
    ``environment_versions`` that differ (a name missing on one side counts
    as '—')."""
    now = environment_versions() if now is None else now
    return ['%s: %s → %s' % (k, recorded.get(k, '—'), now.get(k, '—'))
            for k in sorted(set(recorded) | set(now)) if recorded.get(k) != now.get(k)]


def run_item_at(item, commit, out_dir, args, timeout=3600):
    """Run ``item``'s script as it was at ``commit`` (a temporary git
    worktree; the public sample data are tracked, so they are there) with
    ``args`` (``{out}`` already replaced by ``out_dir``), in this
    environment. Returns the exit code, or None when the worktree cannot be
    made. Used by the audit to tell a change of code from a change of
    environment."""
    import subprocess
    import tempfile
    wt = tempfile.mkdtemp(prefix='lss_toolbox_wt_')
    os.rmdir(wt)
    r = subprocess.run(['git', 'worktree', 'add', '--detach', '-q', wt, commit], cwd=ROOT, capture_output=True,
                       text=True)
    if r.returncode != 0:
        return None
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, STDOUT), 'w', encoding='utf-8') as f:
            try:
                p = subprocess.run([interpreter(), os.path.join(wt, item.script)] + list(args), cwd=wt,
                                   env=environment(out_dir), stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
                return p.returncode
            except subprocess.TimeoutExpired:
                return -9
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', wt], cwd=ROOT, capture_output=True)


def classify(new_vs_committed, old_here_vs_committed, new_vs_old_here):
    """Why a product differs from the committed one, from three comparisons
    (each True when identical): the run now, the run of the products' own
    commit in this environment, the committed product. 'current' (no
    difference); 'environment' (the old code here gives what the new code
    gives: the committed one was drawn elsewhere); 'code' (the old code here
    gives the committed one: the code changed it); 'both'; 'unknown' (the
    old code could not be run)."""
    if new_vs_committed:
        return 'current'
    if old_here_vs_committed is None:
        return 'unknown'
    if new_vs_old_here and not old_here_vs_committed:
        return 'environment'
    if old_here_vs_committed and not new_vs_old_here:
        return 'code'
    return 'both'


def read_record(run_dir):
    try:
        with open(os.path.join(run_dir, RECORD), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def outputs(folder, skip=(RECORD, TRACE, 'preferences.json')):
    """(images, texts): files under ``folder`` (recursive, relative paths,
    sorted), the run's own bookkeeping and logs left out."""
    images, texts = [], []
    if not folder or not os.path.isdir(folder):
        return images, texts
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if d != 'logs')
        for name in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, name), folder)
            if rel in skip:
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in IMAGES:
                images.append(rel)
            elif ext in TEXTS:
                texts.append(rel)
    return images, texts


def repo_path(rel):
    return os.path.join(ROOT, rel)


def product_files(item, source, root=ROOT):
    """{relative name: absolute path} of a run folder or, for source
    'committed', of the item's committed products under ``root`` (names
    relative to each committed folder, so that they match a run's)."""
    out = {}
    if source == 'committed':
        for c in item.committed:
            full = os.path.join(root, c)
            if os.path.isdir(full):
                images, txts = outputs(full, skip=())
                for rel in images + txts:
                    out.setdefault(rel, os.path.join(full, rel))
            elif os.path.isfile(full):
                out.setdefault(os.path.basename(c), full)
            else:
                for p in sorted(glob.glob(full)):
                    if os.path.isfile(p):
                        out.setdefault(os.path.basename(p), p)
        return out
    if source and os.path.isdir(source):
        images, txts = outputs(source)
        for rel in images + txts:
            out[rel] = os.path.join(source, rel)
    return out


def default_args(item, spec, out_dir, committed=False):
    """The argument list of a run with the item's default settings (or,
    ``committed``, the settings that made its committed products) into
    ``out_dir`` (its scratch arguments applied)."""
    spec = effective(spec, item.subcommand)
    args = item.committed_args() if committed else item.defaults
    vals = values_from(spec, args) if spec.get('actions') else {}
    if spec.get('actions'):
        vals.update(values_from(spec, item.scratch_args))
    return build_args(spec, vals, out_dir, free=item.free)


def read_trace(run_dir):
    """What a traced run used ({'modules': [...], 'reads': [...]}, paths
    relative to the repository), or None when the run was not traced or
    did not finish."""
    try:
        with open(os.path.join(run_dir, TRACE), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def run_item(item, spec, timeout=3600, committed=False, extra_env=None, run_dir=None):
    """Run ``item`` with its defaults (``committed``: with the settings of
    its committed products) into a new run folder, without a window
    (``python -m lss_toolbox --audit``), through ``lss_toolbox.trace``
    (``trace.json`` in the run folder: what it imported and read); returns
    (run folder, exit code). ``extra_env``: variables added to the run's
    environment (the audit's stamp run sets ``compare.STAMP_ENV``);
    ``run_dir``: this folder instead of a new one."""
    import subprocess
    if run_dir is None:
        run_dir = new_run_dir(item.id)
    else:
        os.makedirs(run_dir, exist_ok=True)
    env = environment(run_dir)
    env.update(extra_env or {})
    args = default_args(item, spec, run_dir, committed)
    started = datetime.datetime.now().isoformat(timespec='seconds')
    write_record(run_dir, item.id, item.script, args, started)
    with open(os.path.join(run_dir, STDOUT), 'w', encoding='utf-8') as f:
        try:
            r = subprocess.run([interpreter(), '-m', 'lss_toolbox.trace', os.path.join(run_dir, TRACE), '--',
                                os.path.join(ROOT, item.script)] + args, cwd=ROOT,
                               env=env, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
            code = r.returncode
        except subprocess.TimeoutExpired:
            code = -9
    write_record(run_dir, item.id, item.script, args, started,
                 datetime.datetime.now().isoformat(timespec='seconds'), code)
    return run_dir, code
