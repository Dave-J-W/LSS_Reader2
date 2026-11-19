"""When each point of a scan was measured (F37; owner, 2026-11-19).

Two file formats, told apart by the scan's #L line alone, both handled
without complaint:

- **New** (#L has ``Tstart`` and ``Tend``, no ``Epoch``): ``Tstart`` is when
  counting began and ``Tend`` when the point was written, Unix seconds to
  0.01 s. Overhead per point = Tend − Tstart − Seconds. Time since the
  macro started = Tstart − SeriesT0, from the scan header line
  ``#U SeriesT0 <Unix s>``, taken before any motor moves.
- **Old** (#L has ``Epoch``): ``Epoch``'s starting point is wrong (#E + Epoch
  is more than an hour off in 4,458 of 8,043 scans of the owner's files), but
  its steps within a scan are right (189,439 steps in c51_surface: none goes
  backwards, none is shorter than the count time). So the absolute time is
  the scan's #D (1 s) as anchor plus Epoch differences within the scan:
  good to about 1 s, plus an unknown lag before the first point (sleep,
  count, readout). **Never #E + Epoch.** Time since the macro started is not
  recorded; the best guess is the #D of the first scan of the series the
  reader infers (lss_core.series.infer), which misses the slit, absorber
  and umk moves before it.
- Neither: no per-point times (the scan's #D only).

#D is local time without a zone. Its offset from UTC is taken from the
file header, where #E (Unix s) and #D give the same moment; when that pair
is missing or implausible (more than 14 h apart), #D is read as UTC and
the result says so. A file that spans a daylight-saving change is off by
an hour after the change (rare; noted, not corrected).

Source of the rules: the owner's table "Guidance for the reader on
timestamps and epoch", 2026-11-19 (docs/physics_notes.md).
"""
import calendar
import time
from dataclasses import dataclass, field

import numpy as np

DATE_FORMAT = '%a %b %d %H:%M:%S %Y'


def time_format(columns):
    """'new' (Tstart and Tend), 'old' (Epoch) or 'none', from #L names."""
    names = set(columns)
    if {'Tstart', 'Tend'} <= names:
        return 'new'
    if 'Epoch' in names:
        return 'old'
    return 'none'


def parse_date(text):
    """A #D text ('Wed Sep 23 09:29:57 2026') as seconds, read as if UTC."""
    return calendar.timegm(time.strptime(text.strip(), DATE_FORMAT))


def utc_offset(file_epoch, file_date):
    """Seconds by which #D (local) is ahead of UTC, from the file header's
    #E and #D; None when either is missing or they are more than 14 h
    apart (not one moment)."""
    if file_epoch is None or not file_date:
        return None
    try:
        off = parse_date(file_date) - float(file_epoch)
    except ValueError:
        return None
    return off if abs(off) <= 14 * 3600 else None


@dataclass
class PointTimes:
    """Times of a scan's points. ``start``: Unix s when each point's
    counting began (old format: the best estimate, see ``precision``);
    ``end``: when it was written (new format only); ``overhead``: Tend −
    Tstart − Seconds (new format only); ``since_series``: seconds since the
    macro started (new: Tstart − SeriesT0; old: from the inferred series'
    first #D, a lower bound of the true time); ``format``: 'new', 'old' or
    'none'; ``notes``: how each was obtained, for tooltips and logs."""
    format: str
    start: np.ndarray = None
    end: np.ndarray = None
    overhead: np.ndarray = None
    since_series: np.ndarray = None
    precision_s: float = None
    notes: list = field(default_factory=list)


def point_times(columns, date=None, offset=None, series_t0=None, series_first_date=None):
    """Per-point times of one scan.

    ``columns``: the scan's data, {name: array} as the SPEC reader gives it;
    ``date``: its #D text; ``offset``: ``utc_offset`` of its file;
    ``series_t0``: its #U SeriesT0 (new format); ``series_first_date``: the
    #D text of the first scan of its inferred series (old format)."""
    fmt = time_format(columns)
    out = PointTimes(fmt)
    anchor = None
    if date:
        try:
            anchor = parse_date(date) - (offset or 0.0)
        except ValueError:
            anchor = None
        if anchor is not None and offset is None:
            out.notes.append('#D read as UTC: the file header gives no time zone')
    if fmt == 'new':
        t0 = np.asarray(columns['Tstart'], float)
        t1 = np.asarray(columns['Tend'], float)
        out.start, out.end = t0, t1
        out.precision_s = 0.01
        out.notes.append('Tstart and Tend from the scan (Unix s, 0.01 s)')
        if 'Seconds' in columns and columns['Seconds'] is not None:
            out.overhead = t1 - t0 - np.asarray(columns['Seconds'], float)
        if series_t0 is not None:
            out.since_series = t0 - float(series_t0)
            out.notes.append('since the macro started: Tstart - SeriesT0')
        else:
            out.notes.append('no #U SeriesT0 line: time since the macro started not known')
        return out
    if fmt == 'old':
        ep = np.asarray(columns['Epoch'], float)
        if anchor is None:
            # no usable #D (e.g. dates removed): Epoch's own clock, whose base is
            # arbitrary but common to a SPEC session, so scans still line up
            out.notes.append("no #D: Epoch's own clock (base arbitrary; spacing and order right within a session)")
            out.start = ep.copy()
            return out
        out.start = anchor + (ep - ep[0])
        out.precision_s = 1.0
        out.notes.append('scan #D + Epoch differences within the scan: about 1 s, plus an unknown lag '
                         'before the first point (#E + Epoch is not used: its start is wrong)')
        if series_first_date:
            try:
                t_first = parse_date(series_first_date) - (offset or 0.0)
                out.since_series = out.start - t_first
                out.notes.append('since the macro started: from the #D of the first scan of the inferred series '
                                 '(misses the moves before it: a lower bound)')
            except ValueError:
                pass
        return out
    if anchor is not None and 'Seconds' in columns and columns['Seconds'] is not None:
        sec = np.asarray(columns['Seconds'], float)
        out.start = anchor + np.concatenate([[0.0], np.cumsum(sec[:-1])])
        out.precision_s = 1.0
        out.notes.append('no per-point times (#L has neither Tstart/Tend nor Epoch): scan #D plus the count '
                         'times before each point (overhead between points not known, ignored)')
    elif anchor is not None:
        out.notes.append('no per-point times in this scan (#L has neither Tstart/Tend nor Epoch); scan #D only')
    else:
        out.notes.append('no times in this scan')
    return out
