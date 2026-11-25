"""Are a tool's committed products older than the code that makes them?

Two sources, the first that applies wins (2026-11-25, after the former
patching session's review: "`--stale` flags 23 of 28 items, mostly
wrongly"):

1. **The verified record** (``lss_toolbox/verified.json``, written by
   ``python -m lss_toolbox --audit --record``). The audit reran the tool
   through ``lss_toolbox.trace`` and found its products identical to the
   committed ones (or different only through the environment: fonts,
   library versions). The record holds the fingerprints
   (``lss_toolbox.fingerprint``) of the modules the run actually imported,
   the files it read, and the products it reproduced. While the products
   still match the record, they are **current** if every recorded input
   has the same fingerprint now, and **may be stale** if one changed. The
   fingerprint of Python code ignores docstrings and comments, so editing
   prose does not count; a module that is imported only on a path the tool
   never takes is not in the record at all.

2. **Git history**, when there is no record or the products changed since
   it was made. A product was last committed at commit P. The tool depends
   on its own script, on every repository file it imports
   (``introspect.repo_imports``, read statically: an over-estimate) and on
   the inputs the catalogue names. A file that changed in a commit after P
   (``git log P..HEAD -- files``) or is modified in the working tree counts
   only if its fingerprint now differs from its fingerprint at P: a change
   to comments or docstrings alone does not.

"May": a change to code the figure does not show is counted too; rerunning
and comparing (``--audit``) settles it, and ``--record`` keeps the answer.
A checkout without git can still use the record; without a record it
reports 'unknown'.
"""
import datetime
import json
import os
import subprocess

from . import ROOT
from . import fingerprint
from . import introspect

VERIFIED = 'lss_toolbox/verified.json'


def _git(*args, root=ROOT):
    try:
        r = subprocess.run(('git',) + args, cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def git_available(root=ROOT):
    return _git('rev-parse', '--is-inside-work-tree', root=root) is not None


def head(root=ROOT):
    out = _git('rev-parse', '--short=10', 'HEAD', root=root)
    return out.strip() if out else None


def last_commit(paths, root=ROOT):
    """(sha, date, subject) of the last commit touching any of ``paths``;
    None when none of them is tracked."""
    paths = [p for p in paths if p]
    if not paths:
        return None
    out = _git('log', '-1', '--format=%H%x09%cs%x09%s', '--', *paths, root=root)
    if not out or not out.strip():
        return None
    sha, date, subject = out.strip().split('\t', 2)
    return sha, date, subject


def commits_since(sha, paths, root=ROOT):
    """[(sha, date, subject, [files])] of the commits after ``sha`` (not its
    ancestors) that touch any of ``paths``, newest first; only the touched
    files among ``paths`` are listed."""
    if not paths:
        return []
    out = _git('log', '--no-merges', '--format=@@%H%x09%cs%x09%s', '--name-only', '%s..HEAD' % sha, '--', *paths,
               root=root)
    if not out:
        return []
    wanted = set(paths)
    res = []
    for block in out.split('@@')[1:]:
        lines = [x for x in block.strip().split('\n') if x.strip()]
        h, date, subject = lines[0].split('\t', 2)
        files = [f for f in lines[1:] if f in wanted or any(f.startswith(w.rstrip('/') + '/') for w in wanted)]
        res.append((h[:10], date, subject, files))
    return res


def blobs_at(sha, paths, root=ROOT):
    """{path: bytes, or None when absent} of ``paths`` as they were at
    commit ``sha`` (one ``git cat-file --batch``)."""
    paths = sorted(set(paths))
    if not paths:
        return {}
    data = ''.join('%s:%s\n' % (sha, p) for p in paths).encode('utf-8')
    try:
        r = subprocess.run(['git', 'cat-file', '--batch'], input=data, cwd=root, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    out, i, res = r.stdout, 0, {}
    for p in paths:
        j = out.find(b'\n', i)
        if j < 0:
            break
        parts = out[i:j].split(b' ')
        i = j + 1
        if len(parts) == 3 and parts[1] == b'blob':
            n = int(parts[2])
            res[p] = out[i:i + n]
            i += n + 1
        else:
            res[p] = None                                   # 'missing': not in that commit
    return res


def code_changed(sha, paths, root=ROOT):
    """The files among ``paths`` whose fingerprint now differs from the one
    at commit ``sha`` (prose-only changes to Python files dropped)."""
    then = blobs_at(sha, paths, root)
    out = []
    for p in sorted(set(paths)):
        raw = then.get(p)
        before = 'missing' if raw is None else fingerprint.of_bytes(p, raw)
        if before != fingerprint.of_file(p, root):
            out.append(p)
    return out


def modified(paths, root=ROOT):
    """Files among ``paths`` that differ from HEAD in the working tree."""
    if not paths:
        return []
    out = _git('status', '--porcelain', '--untracked-files=no', '--', *paths, root=root)
    if not out:
        return []
    return sorted(line[3:].strip() for line in out.splitlines() if line.strip())


def dependencies_of_script(script, root=ROOT):
    return introspect.repo_imports(script, root=root)


def dependencies(tool, root=ROOT, direct_only=False):
    """Repository-relative files a catalogue item depends on: its script and
    what it imports (``direct_only``: what it and its tool-side helpers
    import themselves), plus the inputs the catalogue names."""
    get = introspect.direct_imports if direct_only else introspect.repo_imports
    deps = set()
    if tool.script:
        deps.update(get(tool.script, root=root))
    for extra in tool.imports:
        deps.update(get(extra, root=root))
    for p in tool.inputs:
        deps.add(p)
    return sorted(deps)


class Status:
    """Result of ``product_status``. ``state``:

    - 'current': no dependency changed since the products' last commit;
    - 'stale': the script, a file it imports itself (or through a tool-side
      helper) or a named input changed: rerun and compare;
    - 'indirect': only files further down the imports changed (often
      unrelated to the figure; a rerun settles it);
    - 'none': no committed products; 'unknown': no git, or not tracked.

    Also the products' last commit, the changes since (per commit), files
    modified in the working tree, and the dependency lists. ``verified``:
    the record that decided it ({'commit', 'date', ...}), or None when git
    history did; ``changed``: with a record, the inputs whose fingerprint
    differs from it; ``prose_only``: files that changed only in comments
    or docstrings (not counted)."""

    def __init__(self, state, products_commit=None, changes=(), dirty=(), deps=(), direct=(), note='',
                 verified=None, changed=None, prose_only=()):
        self.state = state
        self.products_commit = products_commit
        self.changes = list(changes)
        self.dirty = list(dirty)
        self.deps = list(deps)
        self.direct = list(direct)
        self.note = note
        self.verified = verified
        self.changed = None if changed is None else list(changed)
        self.prose_only = list(prose_only)

    @property
    def changed_files(self):
        if self.changed is not None:
            return list(self.changed)
        files = []
        for _, _, _, fs in self.changes:
            files.extend(f for f in fs if f not in files)
        for f in self.dirty:
            if f not in files:
                files.append(f)
        return files

    @property
    def changed_direct(self):
        return [f for f in self.changed_files if f in self.direct]

    def line(self):
        """One short line for a label; ``details`` for the tooltip."""
        if self.state == 'none':
            return 'No committed products: runs go to a folder of their own.'
        if self.state == 'unknown':
            return 'Committed products: freshness unknown (%s).' % self.note
        if self.verified:
            date, sha = self.verified.get('date', '?'), self.verified.get('commit') or '?'
            since = 'verification (%s)' % date
            if self.state == 'current':
                return 'Committed products current (verified by a rerun on %s, at %s).' % (date, sha[:7])
        else:
            sha, date, _ = self.products_commit
            since = date
            if self.state == 'current':
                return 'Committed products current (made %s, %s).' % (date, sha[:7])
        if self.state == 'stale':
            n = len(self.changed_direct)
            return 'Committed products may be stale: %d file%s it uses changed since %s.' % (
                n, '' if n == 1 else 's', since)
        n = len(self.changed_files)
        return 'Committed products probably current: only %d file%s further down changed since %s.' % (
            n, '' if n == 1 else 's', since)

    def details(self):
        out = [self.line()]
        if self.verified:
            v = self.verified
            out.append('Verified %s at %s: the audit reran it and its %d product%s %s (%s).' % (
                v.get('date', '?'), (v.get('commit') or '?')[:10], len(v.get('products', {})),
                '' if len(v.get('products', {})) == 1 else 's',
                'matched the committed ones' if v.get('verdict') == 'same'
                else 'differed only through the environment', 'python -m lss_toolbox --audit --record'))
            if self.changed:
                out.append('Changed since, among what the run used: ' + ', '.join(self.changed))
        if self.products_commit:
            sha, date, subject = self.products_commit
            out.append('Products last committed in %s (%s): %s' % (sha[:10], date, subject))
        if self.changed_direct:
            out.append('Changed among the files it uses directly: ' + ', '.join(self.changed_direct))
        for h, date, subject, files in self.changes:
            out.append('  %s %s %s: %s' % (h, date, subject[:70], ', '.join(files)))
        if self.dirty:
            out.append('  modified, not committed: ' + ', '.join(self.dirty))
        if self.prose_only:
            out.append('Changed only in comments or docstrings (not counted): ' + ', '.join(self.prose_only))
        if self.deps:
            if self.verified:
                out.append('Depends on %d repository files (%d directly), as the rerun used them: the modules it '
                           'imported and the files it read.' % (len(self.deps), len(self.direct)))
            else:
                out.append('Depends on %d files (%d directly): the script, what it imports, the inputs named in '
                           'the catalogue.' % (len(self.deps), len(self.direct)))
        return '\n'.join(out)


# ---------------------------------------------------------------- the verified record

def load_verified(root=ROOT):
    """{item id: entry} of ``lss_toolbox/verified.json`` ({} when absent)."""
    try:
        with open(os.path.join(root, VERIFIED), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_verified(entries, root=ROOT):
    """Merge ``entries`` ({item id: entry}) into the record and write it."""
    rec = load_verified(root)
    rec.update(entries)
    path = os.path.join(root, VERIFIED)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(sorted(rec.items())), f, indent=1, sort_keys=True)
        f.write('\n')
    return rec


def verification(tool, trace, products, verdict, root=ROOT, unverified=()):
    """A record entry for ``tool``: ``trace`` is a run's ``trace.json``
    ({'modules', 'reads'}), ``products`` the committed products the run
    reproduced (paths relative to ``root``), ``verdict`` 'same' or
    'environment' (the images differ only because of where they were
    drawn). Fingerprints are taken now, from the working tree the run
    used."""
    from . import runner
    modules = set(trace.get('modules', []))
    reads = set(trace.get('reads', [])) | set(p for p in tool.inputs if os.path.isfile(os.path.join(root, p)))
    reads -= set(products)
    used = sorted(modules | reads)
    return {
        'commit': head(root),
        'date': datetime.date.today().isoformat(),
        'verdict': verdict,
        'modified': modified(used, root=root),
        'modules': fingerprint.of_files(modules, root),
        'reads': fingerprint.of_files(reads, root),
        'products': fingerprint.of_files(products, root),
        'unverified': sorted(unverified),
        'environment': runner.environment_versions(),
    }


def _from_record(tool, rec, root):
    """The Status a record gives, or None when it does not apply (the
    committed products differ from the ones it verified)."""
    prods = rec.get('products') or {}
    if not prods or any(fingerprint.of_file(p, root) != fp for p, fp in prods.items()):
        return None
    inputs = dict(rec.get('modules', {}))
    inputs.update(rec.get('reads', {}))
    changed = sorted(p for p, fp in inputs.items() if fingerprint.of_file(p, root) != fp)
    static_direct = set(dependencies(tool, root=root, direct_only=True))
    direct = sorted((static_direct & set(rec.get('modules', {}))) | set(rec.get('reads', {})) |
                    ({tool.script} if tool.script else set()))
    have_git = git_available(root)
    last = last_commit(list(tool.committed), root=root) if have_git else None
    changes = [c for c in commits_since(rec['commit'], changed, root=root)] if (have_git and changed and
                                                                                rec.get('commit')) else []
    dirty = modified(changed, root=root) if (have_git and changed) else []
    st = Status('current', last, changes, dirty, sorted(inputs), direct, verified=rec, changed=changed)
    if st.changed_direct:
        st.state = 'stale'
    elif changed:
        st.state = 'indirect'
    return st


def product_status(tool, root=ROOT, verified=None):
    """Staleness of ``tool.committed``: from the verified record when it
    applies (``verified``: the record's entries, read from ``root`` when
    None), otherwise from git history against ``dependencies(tool)``."""
    if not tool.committed:
        return Status('none')
    rec = (load_verified(root) if verified is None else verified).get(tool.id)
    if rec:
        st = _from_record(tool, rec, root)
        if st is not None:
            return st
    if not git_available(root):
        return Status('unknown', note='no git')
    deps = dependencies(tool, root=root)
    direct = dependencies(tool, root=root, direct_only=True)
    last = last_commit(list(tool.committed), root=root)
    if last is None:
        return Status('unknown', deps=deps, direct=direct, note='products not tracked by git')
    changes = commits_since(last[0], deps, root=root)
    dirty = modified(deps, root=root)
    touched = set(f for _, _, _, fs in changes for f in fs) | set(dirty)
    real = set(code_changed(last[0], touched, root=root))
    prose = sorted(touched - real)
    changes = [(h, d, subj, [f for f in fs if f in real]) for h, d, subj, fs in changes if any(f in real for f in fs)]
    dirty = [f for f in dirty if f in real]
    st = Status('current', last, changes, dirty, deps, direct, prose_only=prose)
    if st.changed_direct:
        st.state = 'stale'
    elif st.changed_files:
        st.state = 'indirect'
    return st
