"""The sample timeline's model (F83, phase 1b): what happened when, read
from one SPEC file. No Qt: the timeline tab (phase 1c) only draws it.

Owner, 2026-11-23 (F83): "a sample timeline tab, with sample height scan
thumbnails, the 'sx' motions, new sample changes ('set sh 0' is almost
always a new sample, occasionally used on the same sample but after some
conditions have changed), tensiometer, barrier, reduced data thumbnails".
The research behind each item is docs/gui/timeline/research.md (sections
1-3; measured on the NX school file).

What the file gives, and what this reads:

- **Scan spans**: start and end of every scan (lss_core.timing from #D and
  Epoch, or Tstart/Tend), its command, points, whether it was aborted, and
  its kind (the series lss_core.series infers; sample-height scans apart).
- **Events from dated #C lines**: SPEC's ``set`` writes
  "<motor name> reset from <old> to <new>". A reset to exactly 0 of the
  sample height is the owner's "set sh 0", drawn as "new sample?" for the
  user to confirm (research §1: in the NX file it is not a new sample);
  other resets are re-referencing (1-5.5 µm after an sh scan in NX).
  Also aborts ("Scan aborted after k points") and macro files loaded
  ("do <file>"). Comments in the file header, before the first #S, belong
  to scan 0. The SPEC reader keeps no per-scan comment list, so this reads
  the file's #C lines itself (about 15 ms for 3,000 scans, research §5).
- **Session restarts**: a further #E line (SPEC reopened the file).
- **Gaps**: no scan for longer than ``gap_minutes`` between two scans.
- **Motor steps**: chosen motors (default sx, ``Sample_X``) from each
  scan's #P; a move between scans is dated only to "between the end of
  the one and the start of the next" (research §3).
- **Sample-height scans**: each with its super-Gaussian fit
  (lss_core.peaks.fit_super_gaussian, F78) on the Pilatus ROI column over
  Monc.
- **Mnemonics**: the command's motor mnemonic (sh) to the #L column name
  (Sample_H), learnt from the file's own scans.

Times are Unix seconds (UTC): #D and #C dates are local, and the file
header's #E/#D pair gives the zone (lss_core.timing.utc_offset); without
it they are read as UTC, and ``notes`` says so.
"""
import calendar
import re
import time
from dataclasses import dataclass, field

import numpy as np

from . import peaks
from . import series as sermod
from . import timing

COMMENT = re.compile(r'^#C\s+(\w{3}\s+\w{3}\s+\d+\s+\d\d:\d\d:\d\d\s+\d{4})\.\s+(.*?)\s*$')
RESET = re.compile(r'^(\S+) reset from (\S+) to (\S+?)\.?$')
MACRO = re.compile(r'^do\s+(\S+?)\.?$')
HEIGHT_MOTOR = 'Sample_H'           # the #L name of sh (NX: measured, research §1)
DEFAULT_MOTORS = ('Sample_X',)      # sx
GAP_MINUTES = 20.0                  # an assumption: research §1 leaves N open (Q-TL questions)
STEP_TOLERANCE = 1e-3               # motor units (mm): 19.9999 and 20 are one position


@dataclass
class Event:
    """One dated happening. ``kind``: 'set-zero' (a reset of the sample
    height to exactly 0: "set sh 0", new sample?), 'reset' (another
    ``set``), 'abort', 'macro', 'session' (SPEC reopened the file) or
    'gap'. ``after_scan``: the scan whose block holds it (0: the file
    header); a gap's is the scan before it."""
    t: float
    kind: str
    after_scan: int
    text: str
    motor: str = None
    old: float = None
    new: float = None
    duration: float = None          # a gap's length, s

    @property
    def shift(self):
        """new − old of a reset (motor units), else None."""
        if self.old is None or self.new is None:
            return None
        return self.new - self.old


@dataclass
class ScanSpan:
    scan: int
    command: str
    t0: float
    t1: float
    points: int
    aborted: bool
    kind: str                       # 'height', a series kind (reflectivity, gid, ...), or 'other'


@dataclass
class Step:
    """A motor that moved between two scans (from their #P)."""
    motor: str
    scan: int                       # the first scan at the new position
    t_before: float                 # end of the scan before
    t_after: float                  # start of this one
    old: float
    new: float


@dataclass
class HeightScan:
    scan: int
    t: float
    fit: peaks.SuperGaussianFit
    sx: float = None


@dataclass
class Timeline:
    spans: list = field(default_factory=list)
    events: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    heights: list = field(default_factory=list)
    mnemonics: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    utc_offset: float = 0.0         # s by which the file's local clock is ahead of UTC (0 when not known)
    positions: dict = field(default_factory=dict)   # motor -> [(scan, scan start, value at its #P)]

    def of_kind(self, kind):
        return [e for e in self.events if e.kind == kind]

    def range(self):
        """(first, last) time of the file's scans, or (None, None)."""
        if not self.spans:
            return None, None
        return min(s.t0 for s in self.spans), max(s.t1 for s in self.spans)


def _local_seconds(text):
    """A '#C'/'#D' date ('Wed Sep 23 10:37:39 2026') as seconds, read as UTC."""
    return calendar.timegm(time.strptime(' '.join(text.split()), timing.DATE_FORMAT))


def _number(text):
    try:
        return float(text.rstrip('.'))
    except ValueError:
        return None


def comments(path):
    """(after_scan, local seconds, message) of every dated #C line, and
    the line numbers of the #E lines, in file order."""
    out, sessions, scan = [], [], 0
    with open(path, errors='replace') as f:
        for k, line in enumerate(f):
            if line.startswith('#S '):
                try:
                    scan = int(line.split()[1])
                except (IndexError, ValueError):
                    pass
            elif line.startswith('#E'):
                sessions.append((k, scan))
            elif line.startswith('#C'):
                m = COMMENT.match(line.rstrip('\n'))
                if m:
                    try:
                        out.append((scan, _local_seconds(m.group(1)), m.group(2)))
                    except ValueError:
                        pass
    return out, sessions


def comment_event(after_scan, t, message, height_motor=HEIGHT_MOTOR):
    """The Event a dated comment stands for, or None."""
    m = RESET.match(message)
    if m:
        motor, old, new = m.group(1), _number(m.group(2)), _number(m.group(3))
        zero = motor == height_motor and new == 0.0
        return Event(t, 'set-zero' if zero else 'reset', after_scan,
                     ('set %s 0: new sample?' % motor) if zero else message, motor, old, new)
    if sermod.aborted_after(message) is not None or sermod.aborted_after('#C ' + message) is not None:
        return Event(t, 'abort', after_scan, message)
    m = MACRO.match(message)
    if m:
        return Event(t, 'macro', after_scan, 'do %s' % m.group(1))
    return None


def learn_mnemonics(scans):
    """{mnemonic: #L name} from scans whose command names its motors:
    ascan/dscan/lup <m> ... and a2scan/d2scan <m1> a b <m2> ...: the first
    motor is the first #L column, the second the second."""
    out = {}
    for sc in scans:
        w = sc.command.split()
        cols = list(sc.columns)
        if len(w) < 2 or not cols:
            continue
        if w[0] in ('ascan', 'dscan', 'lup') and w[1] not in out:
            out[w[1]] = cols[0]
        elif w[0] in ('a2scan', 'd2scan') and len(w) > 4 and len(cols) > 1:
            out.setdefault(w[1], cols[0])
            out.setdefault(w[4], cols[1])
    return out


def _span_times(exp, n):
    """(start, end) of scan n in Unix s, or (None, None)."""
    try:
        pt = exp.point_times(n)
    except (KeyError, ValueError, TypeError):
        return None, None
    if pt.start is None or not len(pt.start):
        return None, None
    t0 = float(pt.start[0])
    if pt.end is not None and len(pt.end):
        t1 = float(pt.end[-1])
    else:
        sec = exp.scans[n].columns.get('Seconds')
        t1 = float(pt.start[-1]) + (float(sec[-1]) if sec is not None and len(sec) else 0.0)
    return t0, t1


def build(exp, motors=DEFAULT_MOTORS, gap_minutes=GAP_MINUTES, fit_heights=True):
    """The timeline of ``exp`` (lss_core.experiment.Experiment)."""
    tl = Timeline()
    nums = sorted(exp.scans)
    info = {i.num: i for i in sermod.scan_info(exp._data, exp._par)}
    kind_of = {}
    for g in sermod.all_series(list(info.values())):
        for n in set(g.scans.values()):
            kind_of[n] = g.kind
    offset = None
    for n in nums:
        p = exp.scans[n].parameters
        offset = timing.utc_offset(p.get('FileEpoch'), p.get('FileDate'))
        if offset is not None:
            break
    if offset is None:
        tl.notes.append('dates read as UTC: the file header gives no time zone')
    tl.utc_offset = float(offset or 0.0)
    tl.mnemonics = learn_mnemonics(exp.scans[n] for n in nums)
    height_motor = tl.mnemonics.get('sh', HEIGHT_MOTOR)
    # scan spans
    for n in nums:
        sc = exp.scans[n]
        t0, t1 = _span_times(exp, n)
        if t0 is None:
            tl.notes.append('scan %d: no time' % n)
            continue
        i = info.get(n)
        kind = 'height' if peaks.is_height_scan(sc.command) else kind_of.get(n, 'other')
        npts = len(next(iter(sc.columns.values()))) if sc.columns else 0
        tl.spans.append(ScanSpan(n, sc.command, t0, t1, npts, bool(i.aborted) if i else False, kind))
    # dated comments: resets, aborts, macro files; further #E lines: session restarts
    found, sessions = comments(exp.specfile)
    for after, local, message in found:
        ev = comment_event(after, local - (offset or 0.0), message, height_motor)
        if ev is not None:
            tl.events.append(ev)
    span_of = {s.scan: s for s in tl.spans}
    for _line, after in sessions[1:]:
        nxt = [s for s in tl.spans if s.scan > after]
        t = nxt[0].t0 if nxt else (span_of[after].t1 if after in span_of else float('nan'))
        tl.events.append(Event(t, 'session', after, 'SPEC session restarted (#E)'))
    # gaps
    for a, b in zip(tl.spans, tl.spans[1:]):
        if b.t0 - a.t1 > gap_minutes * 60.0:
            tl.events.append(Event(a.t1, 'gap', a.scan, 'no scan for %.0f min' % ((b.t0 - a.t1) / 60.0),
                                   duration=b.t0 - a.t1))
    tl.events.sort(key=lambda e: (e.t, e.after_scan))
    # motor steps from #P
    for motor in motors:
        last = None
        for s in tl.spans:
            v = exp.scans[s.scan].parameters.get(motor)
            if not isinstance(v, (int, float)):
                continue
            tl.positions.setdefault(motor, []).append((s.scan, s.t0, float(v)))
            if last is not None and abs(v - last[1]) > STEP_TOLERANCE:
                tl.steps.append(Step(motor, s.scan, last[0].t1, s.t0, float(last[1]), float(v)))
            last = (s, v)
    # sample-height scans and their fits
    for s in tl.spans:
        if s.kind != 'height':
            continue
        cols = exp.scans[s.scan].columns
        sx = exp.scans[s.scan].parameters.get('Sample_X')
        if fit_heights and 'Pilatus' in cols and 'Monc' in cols and cols:
            x = cols[next(iter(cols))]
            fit = peaks.fit_super_gaussian(x, cols['Pilatus'], cols['Monc'])
        else:
            fit = peaks.SuperGaussianFit(False, 'no Pilatus and Monc columns' if fit_heights else 'not fitted')
        tl.heights.append(HeightScan(s.scan, s.t0, fit, sx if isinstance(sx, (int, float)) else None))
    return tl
