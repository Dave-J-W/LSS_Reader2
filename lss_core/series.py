"""Scan series: the scans one experiment macro writes (F39, Stage 3).

A reflectivity or GID measurement is several SPEC scans written by one
macro. The reader needs to know which scans belong together, how many were
planned, which one is which, and whether the macro finished, so that it can
reduce a series as a whole, refresh it live and handle a user cancelling the
later scans. The proposed header line (docs/handoff_out/05-scan-series-syntax.md):

    #U Series id=<id> i=<i> n=<N> kind=<kind> [role=<role>] [key=value ...]
    #U SeriesMacro <the macro command as typed>           (first scan only)
    #C Series id=<id> end status=<completed|aborted> [after=<i>]   (optional)

Until SPEC writes it, ``infer`` groups scans from what files already hold
(commands, Qz ranges, detectors), marked as inferred.

What SPEC writes today and is used here:
- ``#C <date>.  Scan aborted after <k> points.`` inside an aborted scan
  (seen in the NX school and bu files);
- the scan command, from which the planned number of points follows
  (intervals + 1 for the usual scans).
"""
import re
from dataclasses import dataclass, field

KINDS = ('reflectivity', 'gid', 'gisaxs', 'xfntr', 'direct_beam', 'alignment', 'burn', 'energy', 'other')
ROLES = ('data', 'align', 'direct', 'background', 'check')
ABORT = re.compile(r'Scan aborted after (\d+) points')
# commands whose last-but-one word is the number of intervals (SPEC standard macros)
INTERVAL_SCANS = {'ascan', 'a2scan', 'a3scan', 'a4scan', 'dscan', 'd2scan', 'd3scan', 'lup', 'dmesh',
                  'hklscan', 'hscan', 'kscan', 'lscan', 'escan', 'Escan', 'th2th', 'hkcircle'}


def planned_points(command):
    """Points the scan command asks for (intervals + 1), or None when the
    command is not one of the usual interval scans. ``command``: the words
    after '#S <number>'."""
    words = command.split()
    if len(words) < 3 or words[0] not in INTERVAL_SCANS:
        return None
    try:
        return int(float(words[-2])) + 1
    except ValueError:
        return None


def parse_series(words):
    """{key: value} from the words after '#U Series'; numbers for i and n.
    Unknown keys are kept; a word without '=' is ignored."""
    out = {}
    for w in words:
        if '=' not in w:
            continue
        k, v = w.split('=', 1)
        if k in ('i', 'n', 'after'):
            try:
                v = int(v)
            except ValueError:
                continue
        out[k] = v
    return out


def aborted_after(line):
    """k from '#C ... Scan aborted after k points.', else None."""
    m = ABORT.search(line)
    return int(m.group(1)) if m else None


@dataclass
class ScanInfo:
    """What grouping needs from one scan, in file order."""
    num: int
    command: str                       # words after '#S <num>'
    points: int                        # measured
    planned: int = None
    aborted_after: int = None          # from SPEC's abort comment
    series: dict = None                # the '#U Series' fields
    series_end: dict = None            # a '#C Series ... end' line in this scan's block
    detector: str = ''
    qz: tuple = None                   # (first, last) Qz of an L scan

    @property
    def aborted(self):
        """Fewer points than planned. SPEC also writes 'aborted after k
        points' when the user stops a scan at its last point (NX scan 13:
        21 of 21); that scan is complete."""
        if self.planned is not None:
            return min(self.points, self.aborted_after if self.aborted_after is not None else self.points) < self.planned
        return self.aborted_after is not None


@dataclass
class Series:
    id: str
    kind: str
    n: int                              # planned data scans (None: not known)
    scans: dict = field(default_factory=dict)      # i -> scan number (data scans)
    aux: list = field(default_factory=list)        # (scan number, role) of other scans
    status: str = ''                    # complete | partial | in_progress | aborted
    why: str = ''
    inferred: bool = False
    macro: str = ''

    @property
    def missing(self):
        return [] if self.n is None else [i for i in range(1, self.n + 1) if i not in self.scans]

    @property
    def data_scans(self):
        return [self.scans[i] for i in sorted(self.scans)]

    def label(self):
        """Short text for a list: 'reflectivity 4/7 (aborted)'."""
        done = len(self.scans)
        n = '?' if self.n is None else self.n
        tail = '' if self.status == 'complete' else ' (%s)' % self.status.replace('_', ' ')
        return '%s %d/%s%s' % (self.kind, done, n, tail)


def _status(s, info, last_in_file, growing):
    by_num = {x.num: x for x in info}
    aborted = [(i, by_num[n]) for i, n in sorted(s.scans.items()) if by_num[n].aborted]
    end = next((by_num[n].series_end for n in list(s.scans.values()) + [a for a, _ in s.aux]
                if by_num[n].series_end and by_num[n].series_end.get('id') == s.id), None)

    def scan_text(i, x):
        if x.aborted_after is not None:
            return 'scan %d (%d of %s) aborted after %d%s points' % (
                x.num, i, s.n or '?', x.aborted_after, '' if x.planned is None else ' of %d' % x.planned)
        return 'scan %d (%d of %s) has %d of %d points' % (x.num, i, s.n or '?', x.points, x.planned)

    if not s.missing:
        if aborted:
            return 'partial', '; '.join(scan_text(i, x) for i, x in aborted)
        return 'complete', ''
    if end is not None and end.get('status') == 'aborted':
        return 'aborted', 'the macro wrote that it was aborted after scan %s of %s' % (end.get('after', '?'), s.n)
    if last_in_file and growing and not aborted:
        return 'in_progress', 'scans %s of %d not written yet' % (', '.join(map(str, s.missing)), s.n)
    why = 'scans %s of %d missing' % (', '.join(map(str, s.missing)), s.n)
    if aborted:
        why += '; ' + '; '.join(scan_text(i, x) for i, x in aborted)
    elif not last_in_file:
        why += '; other scans follow it'
    else:
        why += '; the file is not growing'
    return 'aborted', why


def group(info, growing=False):
    """Series from the '#U Series' lines of ``info`` (ScanInfo in file
    order). A series is identified by its id; scans of one id that appear
    later (a resumed macro) join it. ``growing``: the file is still being
    written (the last series may be in progress). Scans without a series
    line are not grouped here (see ``infer``)."""
    out, order = {}, []
    for x in info:
        if not x.series or 'id' not in x.series:
            continue
        f = x.series
        s = out.get(f['id'])
        if s is None:
            s = out[f['id']] = Series(f['id'], f.get('kind', 'other'), f.get('n'))
            order.append(f['id'])
        if f.get('n') is not None:
            s.n = f['n']
        role = f.get('role', 'data')
        if role == 'data' and f.get('i') is not None:
            s.scans[f['i']] = x.num
        else:
            s.aux.append((x.num, role))
        if f.get('macro'):
            s.macro = f['macro']
    last = None
    for x in reversed(info):
        if x.series and 'id' in x.series:
            last = x.series['id']
            break
    tail_plain = bool(info) and not (info[-1].series and 'id' in info[-1].series)
    for k in order:
        s = out[k]
        s.status, s.why = _status(s, info, k == last and not tail_plain, growing)
    return [out[k] for k in order]


def _is_l_scan(x):
    w = x.command.split()
    return bool(w) and w[0] == 'hklscan' and x.qz is not None and x.points > 1


def infer(info, growing=False):
    """Series guessed from files without '#U Series' lines (marked
    ``inferred``), for the window's list until SPEC writes the line:

    - reflectivity: consecutive L scans (hklscan, more than one point)
      whose Qz ranges move up and overlap or touch the previous one;
      alignment scans in between (ascan/a2scan/dscan of sh, oh, ih, chi,
      th over a range; a fixed position is not one) are attached as 'align';
    - gid: consecutive ``ascan dth`` scans with images (one per Qz level).

    N is not known for an inferred series (the plan is not in the file), so
    an inferred series is 'complete' unless one of its scans is aborted
    ('partial'), or it is the last one in a growing file ('in_progress')."""
    series, cur = [], None

    def close():
        nonlocal cur
        if cur is not None:
            series.append(cur)
        cur = None

    def is_align(x):
        # a scan of a sample-height or angle motor over a range; a fixed
        # position (start == end: a burn test or time series) is not one
        w = x.command.split()
        if not (w and w[0] in ('ascan', 'a2scan', 'dscan', 'd2scan') and len(w) > 3 and w[1] in ('sh', 'oh', 'ih', 'chi', 'th')):
            return False
        return w[2] != w[3]

    prev_q = None
    for x in info:
        w = x.command.split()
        if _is_l_scan(x):
            lo, hi = min(x.qz), max(x.qz)
            if cur is not None and cur.kind == 'reflectivity' and prev_q is not None and prev_q[0] < lo <= prev_q[1] + 1e-9:
                cur.scans[len(cur.scans) + 1] = x.num
            else:
                close()
                cur = Series('inferred-%d' % x.num, 'reflectivity', None, {1: x.num}, inferred=True)
            prev_q = (lo, hi)
        elif w[:2] == ['ascan', 'dth'] and x.detector == 'Pilatus':
            if cur is not None and cur.kind == 'gid':
                cur.scans[len(cur.scans) + 1] = x.num
            else:
                close()
                cur = Series('inferred-%d' % x.num, 'gid', None, {1: x.num}, inferred=True)
            prev_q = None
        elif cur is not None and is_align(x):
            cur.aux.append((x.num, 'align'))
        else:
            close()
            prev_q = None
    close()
    by_num = {x.num: x for x in info}
    for k, s in enumerate(series):
        bad = [x for x in (by_num[n] for n in s.data_scans) if x.aborted]
        last = k == len(series) - 1 and s.data_scans[-1] == max(by_num)
        if last and growing and not bad:
            s.status, s.why = 'in_progress', 'the file is still being written'
        elif bad:
            s.status = 'partial'
            s.why = '; '.join('scan %d aborted after %s%s points' % (
                x.num, x.aborted_after if x.aborted_after is not None else x.points,
                '' if x.planned is None else ' of %d' % x.planned) for x in bad)
        else:
            s.status = 'complete'
    return series


def scan_info(data, par):
    """ScanInfo for every scan of a specread result (Data, Par), file order."""
    out = []
    for num in data.get('ScanNums', []):
        d, p = data.get(num, {}), par.get(num, {})
        line = d.get('ScanLine', '')
        cmd = ' '.join(line.split()[2:])
        cols = [v for k, v in d.items() if k not in ('ScanVar', 'ScanLine', 'StartScanLineNum', 'Message')
                and hasattr(v, '__len__') and not isinstance(v, str)]
        points = len(cols[0]) if cols else 0
        qz = None
        if 'L' in d and d['L'] is not None and len(d['L']):
            qz = (float(d['L'][0]), float(d['L'][-1]))
        out.append(ScanInfo(num, cmd, points, planned_points(cmd), p.get('AbortedAfter'), p.get('Series'),
                            p.get('SeriesEnd'), p.get('Detector', ''), qz))
    return out
