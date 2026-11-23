"""List the '#M Monc Gain' lines the reader cannot interpret (F52).

    python tests/tools/monitor_gains.py [SPEC files or folders ...]

With no argument, every SPEC file under sample_data/. For each line that
is not '<number> <unit>' with a known unit (lss_core.monitor.UNITS), and
for every scan with no '#M' line and none above it, prints file, scan, its
command, the line number and the text, and which scans inherit it (MCA
scans without #M take the last one above). Markdown table on stdout.
Reads only; never writes to the data.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from lss_core.monitor import parse_gain  # noqa: E402


def spec_files(args):
    paths = args or [os.path.join(ROOT, 'sample_data')]
    for p in paths:
        if os.path.isdir(p):
            for d, _, names in sorted(os.walk(p)):
                for n in sorted(names):
                    yield os.path.join(d, n)
        else:
            yield p


def is_spec(path):
    if path.endswith('_mca'):          # MCA files start with #F too
        return False
    try:
        with open(path, 'rb') as f:
            return f.read(2) == b'#F'
    except OSError:
        return False


def problems(path):
    """[(scan, command, line number or None, text, inheriting scans,
    readable gain before, readable gain after)]"""
    out, current, scan, cmd, seen_m = [], None, None, None, False
    last_good, waiting = None, []
    def close():
        if scan is not None and not seen_m:
            if current is None:
                out.append([scan, cmd, None, '(no #M in or above the scan)', [], last_good, None])
                waiting.append(out[-1])
            elif current is not True:
                current[4].append(scan)
    with open(path, errors='replace') as f:
        for k, line in enumerate(f, start=1):
            if line.startswith('#S '):
                close()
                w = line.split()
                scan, cmd, seen_m = int(w[1]), w[2] if len(w) > 2 else '', False
            elif line.startswith('#M') and line[2:].split()[:2] == ['Monc', 'Gain']:
                seen_m = True
                words = line[2:].split()[2:]
                if parse_gain(words) is None:
                    current = [scan, cmd, k, '#M Monc Gain ' + ' '.join(words) if words else '#M Monc Gain (empty)', [],
                               last_good, None]
                    out.append(current)
                    waiting.append(current)
                else:
                    current = True
                    last_good = 'S%d: %s' % (scan, ' '.join(words))
                    for w in waiting:
                        w[6] = last_good
                    waiting = []
    close()
    return out


def main(argv):
    rows = []
    for p in spec_files(argv):
        if is_spec(p):
            for r in problems(p):
                rows.append([os.path.relpath(p, ROOT)] + r)
    print('| File | Scan | Command | Line | Text | Scans without #M that inherit it | Last readable gain before | Next readable gain after |')
    print('|---|---|---|---|---|---|---|---|')
    for f, scan, cmd, k, text, inh, before, after in rows:
        print('| %s | %s | %s | %s | `%s` | %s | %s | %s |' % (f, scan, cmd, k if k else '—', text,
                                                            ', '.join(map(str, inh)) or '—', before or '—', after or '—'))
    return rows


def cli(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="List the '#M Monc Gain' lines the reader cannot interpret (F52).")
    ap.add_argument('paths', nargs='*', help='SPEC files or folders (default: everything under sample_data/, '
                                             'the private sets included when present)')
    main(ap.parse_args(argv).paths)
    return 0


if __name__ == '__main__':
    sys.exit(cli())
