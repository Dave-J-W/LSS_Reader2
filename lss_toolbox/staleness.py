"""Are a tool's committed products older than the code that makes them?

A product (a figure folder, a CSV folder, a rendered page) was last
committed at commit P. The tool depends on its own script, on every
repository file it imports (``introspect.repo_imports``) and on the inputs
the catalogue names (data, ``.ui`` files). If any of those changed in a
commit after P (``git log P..HEAD -- files``) or is modified in the working
tree, the product may be stale: rerun the tool. "May": a change that does
not touch what the figure shows is counted too; rerunning and comparing
settles it.

Uses git only (no hashes stored beside the products): a checkout without
git reports 'unknown'.
"""
import subprocess

from . import ROOT
from . import introspect


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
    modified in the working tree, and the dependency lists."""

    def __init__(self, state, products_commit=None, changes=(), dirty=(), deps=(), direct=(), note=''):
        self.state = state
        self.products_commit = products_commit
        self.changes = list(changes)
        self.dirty = list(dirty)
        self.deps = list(deps)
        self.direct = list(direct)
        self.note = note

    @property
    def changed_files(self):
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
        sha, date, _ = self.products_commit
        if self.state == 'current':
            return 'Committed products current (made %s, %s).' % (date, sha[:7])
        if self.state == 'stale':
            n = len(self.changed_direct)
            return 'Committed products may be stale: %d file%s it uses changed since %s.' % (
                n, '' if n == 1 else 's', date)
        n = len(self.changed_files)
        return 'Committed products probably current: only %d file%s further down changed since %s.' % (
            n, '' if n == 1 else 's', date)

    def details(self):
        out = [self.line()]
        if self.products_commit:
            sha, date, subject = self.products_commit
            out.append('Products last committed in %s (%s): %s' % (sha[:10], date, subject))
        if self.changed_direct:
            out.append('Changed among the files it uses directly: ' + ', '.join(self.changed_direct))
        for h, date, subject, files in self.changes:
            out.append('  %s %s %s: %s' % (h, date, subject[:70], ', '.join(files)))
        if self.dirty:
            out.append('  modified, not committed: ' + ', '.join(self.dirty))
        if self.deps:
            out.append('Depends on %d files (%d directly): the script, what it imports, the inputs named in the '
                       'catalogue.' % (len(self.deps), len(self.direct)))
        return '\n'.join(out)


def product_status(tool, root=ROOT):
    """Staleness of ``tool.committed`` against ``dependencies(tool)``."""
    if not tool.committed:
        return Status('none')
    if not git_available(root):
        return Status('unknown', note='no git')
    deps = dependencies(tool, root=root)
    direct = dependencies(tool, root=root, direct_only=True)
    last = last_commit(list(tool.committed), root=root)
    if last is None:
        return Status('unknown', deps=deps, direct=direct, note='products not tracked by git')
    changes = commits_since(last[0], deps, root=root)
    dirty = modified(deps, root=root)
    st = Status('current', last, changes, dirty, deps, direct)
    if st.changed_direct:
        st.state = 'stale'
    elif st.changed_files:
        st.state = 'indirect'
    return st
