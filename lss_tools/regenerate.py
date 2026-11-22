"""Rerun the jobs whose committed outputs are stale, and record them.

    python -m lss_tools.regenerate                 # the stale public jobs; updates docs/figures/MANIFEST.json
    python -m lss_tools.regenerate --check         # report only; exit status 1 if anything is not fresh
    python -m lss_tools.regenerate --list          # every job, its state and its command
    python -m lss_tools.regenerate --only burn_figures controls   # these jobs (rerun even if fresh)
    python -m lss_tools.regenerate --force         # every public job
    python -m lss_tools.regenerate --private       # also the private-data jobs, when the data are present

Run from anywhere (it works in the repository root). Each job runs its
documented command (``lss_tools/registry.py``) through
``lss_tools.trace``, which records the code it imported and the files it
read; the manifest then holds the hash of each (code by syntax tree, so
comments and docstrings do not count) and of each output. A job is stale
when one of its recorded inputs changed. The jobs run one at a time, with
the disk cache off, a fresh preferences file and a temporary log folder,
so that nothing of this machine's settings enters an output. A job's old
outputs are set aside first (so that a file it no longer writes does not
linger) and put back if the job fails. Private jobs write only under
sample_data/private/figures/ and are recorded in the git-ignored manifest
there.
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

if __package__ in (None, ''):                    # python lss_tools/regenerate.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = 'lss_tools'

from lss_tools import freshness as fr             # noqa: E402
from lss_tools import registry as reg             # noqa: E402

_current = {'proc': None}


def _stop(signum, frame):
    p = _current['proc']
    if p is not None and p.poll() is None:
        p.terminate()
    sys.exit(128 + signum)


def environment(tmp):
    env = dict(os.environ)
    env.update(MPLBACKEND='Agg', QT_QPA_PLATFORM='offscreen', LSS_READER_DISK_CACHE='off',
               LSS_READER_LOG_DIR=os.path.join(tmp, 'logs'), LSS_READER_PREFS=os.path.join(tmp, 'prefs.json'),
               PYTHONHASHSEED='0', PYTHONIOENCODING='utf-8')
    os.makedirs(env['LSS_READER_LOG_DIR'], exist_ok=True)
    return env


def runnable(job):
    missing = [r for r in job.requires if not os.path.exists(fr.abspath(r))]
    return not missing, missing


def run_job(tool, job, log=print):
    """Run one job; return its manifest entry, or raise RuntimeError."""
    tmp = tempfile.mkdtemp(prefix='lss_regen_')
    backup = os.path.join(tmp, 'old')
    old = fr.owned_files(job)
    for f in old:                                    # set aside: a file it no longer writes must not stay
        dst = os.path.join(backup, *f.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(fr.abspath(f), dst)
    record = os.path.join(tmp, 'trace.json')
    cmd = [sys.executable, '-m', 'lss_tools.trace', record, '--', fr.abspath(tool.script)] + job.argv()
    out_dir = fr.abspath(job.out) if job.out else None
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    ok = False
    try:
        stdout = open(fr.abspath(job.stdout), 'w', encoding='utf-8', newline='\n') if job.stdout else None
        try:
            p = subprocess.Popen(cmd, cwd=fr.ROOT, env=environment(tmp), stdout=stdout or subprocess.PIPE,
                                 stderr=subprocess.STDOUT if stdout is None else subprocess.PIPE,
                                 text=True, encoding='utf-8', errors='replace')
            _current['proc'] = p
            stream = p.stdout if stdout is None else p.stderr
            for line in stream:
                log('    ' + line.rstrip())
            code = p.wait()
        finally:
            _current['proc'] = None
            if stdout is not None:
                stdout.close()
        if code != 0:
            raise RuntimeError('%s exited with status %d' % (job.id, code))
        if not os.path.isfile(record):
            raise RuntimeError('%s left no trace record' % job.id)
        with open(record) as f:
            rec = json.load(f)
        e = fr.entry(tool, job, rec, time.time() - t0)
        if not e['outputs']:
            raise RuntimeError('%s wrote none of its outputs %s' % (job.id, ', '.join(job.outputs)))
        ok = True
        return e
    finally:
        if not ok:                                   # put the old outputs back
            for f in old:
                src = os.path.join(backup, *f.split('/'))
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(fr.abspath(f)), exist_ok=True)
                    shutil.move(src, fr.abspath(f))
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='report only; exit 1 if anything is not fresh')
    ap.add_argument('--list', action='store_true', help='every job, its state and command')
    ap.add_argument('--only', nargs='+', metavar='JOB', help='these jobs (rerun even if fresh)')
    ap.add_argument('--force', action='store_true', help='rerun every selected job, fresh or not')
    ap.add_argument('--private', action='store_true', help='also the private-data jobs, when their data are present')
    ap.add_argument('--dry-run', action='store_true', help='say what would run')
    a = ap.parse_args(argv)
    signal.signal(signal.SIGTERM, _stop)

    kinds = [False, True] if a.private else [False]
    states = {}
    for private in kinds:
        res, extra = fr.check(private)
        states.update({k: (private, v) for k, v in res.items()})
        if not private:
            unclaimed = extra

    if a.check or a.list:
        bad = 0
        for t, j in reg.jobs():
            if j.private and not a.private:
                continue
            ok, missing = runnable(j)
            state, why = states[j.id][1]
            if j.private and not ok:
                state, why = 'skipped', ['private data absent: ' + ', '.join(missing)]
            elif state != 'fresh':
                bad += 1
            if a.list or state != 'fresh':
                print('%-32s %-10s %s' % (j.id, state, ' '.join([t.command] + j.argv())))
                for w in why[:8]:
                    print('    ' + w)
                if len(why) > 8:
                    print('    ... and %d more' % (len(why) - 8))
        for f in unclaimed:
            bad += 1
            print('%-32s %-10s %s' % ('(no job)', 'unclaimed', f))
        print('%d of %d checked jobs fresh%s' % (
            sum(1 for k, (p, s) in states.items() if s[0] == 'fresh'), len(states),
            '; %d file(s) in generated folders belong to no job' % len(unclaimed) if unclaimed else ''))
        return 1 if (a.check and bad) else 0

    todo = []
    for t, j in reg.jobs():
        if j.private and not a.private:
            continue
        if a.only and j.id not in a.only:
            continue
        ok, missing = runnable(j)
        if not ok:
            print('skip %s: %s absent' % (j.id, ', '.join(missing)))
            continue
        if a.only or a.force or states[j.id][1][0] != 'fresh':
            todo.append((t, j))
    if a.only:
        unknown = set(a.only) - {j.id for _, j in reg.jobs()}
        if unknown:
            sys.exit('unknown job(s): %s (python -m lss_tools.regenerate --list)' % ', '.join(sorted(unknown)))
    if not todo:
        print('nothing to regenerate: every selected job is fresh')
        return 0
    failed = []
    for k, (t, j) in enumerate(todo, 1):
        print('[%d/%d] %s: %s' % (k, len(todo), j.id, ' '.join([t.command] + j.argv())), flush=True)
        if a.dry_run:
            continue
        try:
            e = run_job(t, j)
        except RuntimeError as exc:
            print('    FAILED: %s' % exc, flush=True)
            failed.append(j.id)
            continue
        m = fr.load(j.private)
        m.setdefault('jobs', {})[j.id] = e
        fr.save(m, j.private)
        print('    done in %.0f s: %d output(s), %d input(s)' % (e['seconds'], len(e['outputs']), len(e['inputs'])),
              flush=True)
    if failed:
        print('failed: ' + ', '.join(failed))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
