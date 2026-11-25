"""``python -m lss_toolbox``: the Tools window on its own.

    python -m lss_toolbox                  # the window (no reader needed)
    python -m lss_toolbox --item pinhole_figures
    python -m lss_toolbox --render         # rewrite docs/TOOLS.md from the catalogue
    python -m lss_toolbox --stale          # committed products older than their code
    python -m lss_toolbox --list           # items, one per line
    python -m lss_toolbox --audit [--only ID ...] [--max-seconds 60] [--report FILE] [--record]
                                           # rerun items with their defaults, compare with the committed figures;
                                           # --record: keep what matched in lss_toolbox/verified.json (--stale reads it)
"""
import argparse
import os
import sys

from . import ROOT, catalog


def stale_report():
    from . import staleness
    rows = []
    for t in catalog.TOOLS:
        if not t.committed or not t.runnable:
            continue
        s = staleness.product_status(t)
        rows.append((t, s))
        print('%-24s %-8s %s' % (t.id, s.state, s.line()))
        for h, date, subject, files in s.changes[:6]:
            print('    %s %s %s: %s' % (h, date, subject[:60], ', '.join(files)))
        if len(s.changes) > 6:
            print('    ... and %d more commits' % (len(s.changes) - 6))
        if s.dirty:
            print('    modified, not committed: ' + ', '.join(s.dirty))
    return rows


SKIP_TEXT = ('output.txt', 'log.txt', 'run.json')     # run logs, timings: differ by nature


def _prints_revision(tool):
    """Whether the tool's script takes its printed revision from
    ``compare.STAMP_ENV`` (the audit can then find the stamp)."""
    try:
        with open(os.path.join(ROOT, tool.script), encoding='utf-8') as f:
            from . import compare
            return compare.STAMP_ENV in f.read()
    except OSError:
        return False


def record_verdict(image_kinds, counts):
    """Whether an audited item's products are verified, from the reasons
    its images differ ({'environment': n, 'code': n, ...}) and the counts
    {kind: (same, differ, not made)}: 'same' when every product it made is
    identical; 'stamp' when only images differ, and only where the tool
    prints its git revision (``compare.stamp_boxes``); 'environment' when
    the products' own commit run here gives what the new code gives (the
    committed images were drawn elsewhere), for some or all of them, the
    rest differing only by their stamp; None otherwise (nothing compared, a
    table differs, or the code changed a product)."""
    same = sum(c[0] for c in counts.values())
    image_differ, text_differ = counts['image'][1], counts['text'][1]
    if same == 0 and image_differ == 0 or text_differ:
        return None
    if image_differ == 0:
        return 'same'
    if image_kinds and set(image_kinds) <= {'environment', 'stamp'} and sum(image_kinds.values()) == image_differ:
        return 'environment' if 'environment' in image_kinds else 'stamp'
    return None


def audit(only=None, max_seconds=None, report=None, record=False):
    """Rerun each item that has committed products with the settings that
    made them (into run folders) and compare: every image with its committed
    counterpart, pixel for pixel, and every table or text file byte for
    byte. Where images differ, the products' own commit is run here too (a
    temporary git worktree), so that a change of code ('code') is told from
    a committed figure drawn in another environment ('environment': the old
    code here gives what the new code gives). The measured staleness; git
    history only says what might have changed.

    ``record``: for each item whose products are verified
    (``record_verdict``), keep the fingerprints of what its run imported
    and read, and of the products it reproduced, in
    ``lss_toolbox/verified.json``; ``--stale`` and the Tools window then
    call them current until one of those changes."""
    from . import compare, introspect, runner, staleness
    items = [t for t in catalog.TOOLS if t.runnable and t.committed and t.kind in ('figures', 'data')
             and (not only or t.id in only)
             and (max_seconds is None or (t.seconds is not None and t.seconds <= max_seconds))]
    specs = introspect.capture_parsers([t.script for t in items])
    lines = ['| Item | git says | Exit | Images same / differ / not made | Tables same / differ / not made | '
             'Why images differ | Differences |', '|---|---|---|---|---|---|---|']

    recorded = {}
    for t in items:
        volatile = getattr(t, 'volatile', ())

        def same_file(a, b):
            if os.path.splitext(a)[1].lower() in runner.IMAGES:
                return compare.compare(a, b).state == 'same'
            return compare.tables_same(a, b, volatile=volatile)     # apart from how it was run

        st = staleness.product_status(t)
        run_dir, code = runner.run_item(t, specs[t.script], committed=True)
        new = runner.product_files(t, run_dir)
        old = runner.product_files(t, 'committed')
        counts, notes, differing, matched, missing = {}, [], [], [], []
        for kind in ('image', 'text'):
            def pick(d):
                return {n: p for n, p in d.items() if (os.path.splitext(n)[1].lower() in runner.IMAGES) ==
                        (kind == 'image') and os.path.basename(n) not in SKIP_TEXT}
            a, b = pick(new), pick(old)
            same = differ = 0
            for n in sorted(set(a) & set(b)):
                if kind == 'image':
                    d = compare.compare(a[n], b[n])
                    ok = d.state == 'same'
                    text = d.text()
                    if not ok:
                        differing.append(n)
                else:
                    ok = same_file(a[n], b[n])
                    text = 'differs'
                same += ok
                differ += not ok
                if ok:
                    matched.append(b[n])
                else:
                    notes.append('%s: %s' % (n, text))
            missing.extend(b[n] for n in set(b) - set(a))
            counts[kind] = (same, differ, len(set(b) - set(a)))
        why, kinds = '—', {}
        stamped = []
        if differing and _prints_revision(t):
            # the same code with a dummy revision: what moves is the stamp; compare the rest
            sdir, scode = runner.run_item(t, specs[t.script], committed=True, run_dir=run_dir + '-stamp',
                                          extra_env={compare.STAMP_ENV: compare.STAMP_DUMMY})
            sfiles = runner.product_files(t, sdir) if scode == 0 else {}
            for n in differing:
                if n in sfiles and compare.same_outside(new[n], old[n], compare.stamp_boxes(new[n], sfiles[n])):
                    stamped.append(n)
            if stamped:
                kinds['stamp'] = len(stamped)
                why = 'stamp %d' % len(stamped)
        differing = [n for n in differing if n not in stamped]
        products_commit = st.products_commit or staleness.last_commit(list(t.committed))
        if differing and products_commit:
            # the products' own commit, run here: separates a change of code from a change of environment
            old_dir = run_dir + '-at-' + products_commit[0][:7]
            rec = runner.read_record(run_dir) or {}
            args = [x.replace(run_dir, old_dir) for x in rec.get('args', [])]
            rc = runner.run_item_at(t, products_commit[0], old_dir, args)
            here = runner.product_files(t, old_dir) if rc == 0 else {}
            for n in differing:
                k = runner.classify(False, same_file(here[n], old[n]) if n in here else None,
                                    same_file(new[n], here[n]) if n in here else False)
                kinds[k] = kinds.get(k, 0) + 1
            why = ', '.join('%s %d' % kv for kv in sorted(kinds.items()))
            env = (staleness.load_verified().get(t.id) or {}).get('environment')
            if env:                                  # what changed since the products were verified
                changed = runner.environment_diff(env)
                notes.append('environment since the record: %s' % ('; '.join(changed) if changed else 'the same'))
        lines.append('| %s | %s | %d | %s | %s | %s | %s |' % (
            t.id, st.state, code, '%d / %d / %d' % counts['image'], '%d / %d / %d' % counts['text'], why,
            '; '.join(notes) or '—'))
        print(lines[-1], flush=True)
        print('    run folder: %s' % run_dir, flush=True)
        verdict = record_verdict(kinds, counts) if code == 0 else None
        trace = runner.read_trace(run_dir)
        if record and verdict and trace:
            rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, '/')   # noqa: E731
            products = [rel(p) for p in matched] + [rel(old[n]) for n in differing + stamped]
            recorded[t.id] = staleness.verification(t, trace, products, verdict,
                                                    unverified=[rel(p) for p in missing])
            staleness.save_verified({t.id: recorded[t.id]})          # item by item: a long audit keeps what it has
            print('    recorded: %s, %d products, %d modules, %d files read' % (
                verdict, len(products), len(trace.get('modules', [])), len(trace.get('reads', []))), flush=True)
        elif record:
            print('    not recorded: %s' % ('the run failed' if code else 'no trace' if not trace
                                            else 'its products differ'), flush=True)
    if report:
        with open(report, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m lss_toolbox', description=__doc__.split('\n')[0])
    ap.add_argument('--item', help='open the window at this item (an id from --list)')
    ap.add_argument('--render', action='store_true', help='rewrite docs/TOOLS.md')
    ap.add_argument('--stale', action='store_true', help='report the staleness of every committed product')
    ap.add_argument('--list', action='store_true', help='list the items')
    ap.add_argument('--audit', action='store_true', help='rerun items with committed figures and compare them')
    ap.add_argument('--only', nargs='*', help='--audit: only these items')
    ap.add_argument('--max-seconds', type=float, help='--audit: only items measured to take at most this long')
    ap.add_argument('--report', help='--audit: also write the table to this file')
    ap.add_argument('--record', action='store_true',
                    help='--audit: keep the items whose products matched in lss_toolbox/verified.json')
    a = ap.parse_args(argv)
    os.chdir(ROOT)                       # the reader's .ui files and the tools' relative paths
    if a.render:
        from . import render
        print(render.write())
        return 0
    if a.stale:
        stale_report()
        return 0
    if a.audit:
        audit(a.only, a.max_seconds, a.report, a.record)
        return 0
    if a.list:
        for cat, name in catalog.CATEGORIES:
            for t in catalog.in_category(cat):
                print('%-24s %-10s %s > %s' % (t.id, t.kind, name, t.title))
        return 0
    from PyQt5 import QtWidgets
    from . import window
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    w = window.ToolsWindow()
    w.show_item(a.item or catalog.TOOLS[0].id)
    w.resize(1400, 900)
    w.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
