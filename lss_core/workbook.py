"""The per-SPEC-file workbook: settings and saved results in one Excel file
(owner, 2026-11-21: "Perhaps the config file should actually be an Excel
file with sheets, such that results (reduced data and fits) are stored
inside it in an organized fashion, always tied to their scan number. Then
saving a reduced data vector is one click, with an optional notes dialog
box to allow for saving different versions of the same scans ... Label
each experiment type in the output and make easily sortable in the Excel
file ... keep the number of sheets ... below 8, but at least 4").

``<SPEC file name>_reader.xlsx`` in the output directory, never beside or
inside the SPEC file itself. Seven sheets, each with a header row, frozen
panes and a filter, so that Excel sorts and filters them by kind, scan,
version or time:

=========  ================================================================
Scans      every scan of the SPEC file: number, command, experiment kind
           (reflectivity, gid, xfntr, alignment, other; from the series the
           reader infers or the ``#U Series`` lines), series and position
Saved      one row per saved result: id (R0001…), time, kind, scans, first
           scan, label, version (1, 2, … per kind, scans and label), note,
           points, column names, the settings used (JSON), program version;
           the series it came from (id, kind, its data scans and status at
           the time of saving), the lss_core call that remakes it
           (``recipe``, when the reduction is scriptable) and ``stale``:
           why it is out of date when its series has changed since
           (``mark_stale``; the step towards live updates, F1–F5);
           ``origin``: 'user' (a Save button) or 'auto' (saved when the
           reduction finished, owner 2026-11-22); ``content``: a digest
           of the result, so that an identical result is not stored twice
           by the automatic saving
Data       the reduced data vectors, one row per point: result id, kind,
           first scan, scans, label, version, point, then the values
           (columns named in Saved)
Fits       one row per fitted peak, edge or line: result id, kind, scans,
           label, curve, peak, centre, FWHM, height, area with errors,
           χ²/dof, shape, background, fit kind, time
Trends     quantities over time (burn tests, lss_core.trends): one row
           per quantity and model: χ²/dof, AICc (or QAICc), Δ, Akaike
           weight, parameters, best, stable, the time to a 5 % change
           and its confident lower bound
Maps       two-dimensional results (GID maps) as grids, so that Excel can
           show them (a colour scale on the block) and a map costs few
           cells: per map an 'x' row (the x values across), then one
           'value' row per y and one 'error' row per y; every row carries
           id, kind, scans, label and version, so the filter picks a map.
           Maps that are not on a grid are stored as 'cell' rows (y, x,
           value, error). (Until 2026-11-22 one row per cell: 5 × the
           cells and 6 s per later save for one NX map.)
Settings   the current settings (section, key, value, time), the fitting
           preferences among them; the masks of dropped points (section
           ``masks``, lss_core.masks, F92)
=========  ================================================================

Exports (the legacy text files) are unchanged; the workbook is in
addition. Reading back: ``Workbook.results``, ``Workbook.data``,
``Workbook.fits``.
"""
import datetime
import json
import os

import numpy as np

SHEETS = ('Scans', 'Saved', 'Data', 'Fits', 'Trends', 'Maps', 'Settings')
HEADERS = {
    'Scans': ['scan', 'kind', 'command', 'points', 'series', 'series_position', 'role', 'status'],
    'Saved': ['id', 'saved', 'kind', 'first_scan', 'scans', 'label', 'version', 'note', 'points', 'columns',
              'settings', 'program', 'series', 'series_kind', 'series_scans', 'series_status', 'recipe', 'stale',
              'origin', 'content', 'series_points', 'scan_points'],
    'Data': ['id', 'kind', 'first_scan', 'scans', 'label', 'version', 'point', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6',
             'v7', 'v8'],
    'Fits': ['id', 'kind', 'first_scan', 'scans', 'label', 'version', 'curve', 'peak', 'centre', 'centre_err',
             'fwhm', 'fwhm_err', 'height', 'height_err', 'area', 'area_err', 'chi2_dof', 'shape', 'background',
             'fit', 'saved'],
    'Trends': ['id', 'kind', 'first_scan', 'scans', 'label', 'version', 'quantity', 'model', 'k', 'points',
               'chi2_dof', 'criterion', 'value', 'delta', 'weight', 'best', 'stable', 'params', 'change',
               'change_time', 'change_time_confident', 'confidence', 'time_axis', 'saved'],
    'Maps': ['id', 'kind', 'first_scan', 'scans', 'label', 'version', 'part', 'y', 'values (x across)'],
    'Settings': ['section', 'key', 'value', 'updated'],
}
KINDS = ('reflectivity', 'gid map', 'gid cut', 'line cut', 'fluorescence', 'scan', 'peak fit', 'burn test',
         'note', 'other')     # 'note': a timeline note or a "new sample?" answer (lss_core.timeline, F83)
MAX_VALUES = 8


def path_for(spec_path, directory):
    """The workbook of a SPEC file, in ``directory`` (the output folder)."""
    return os.path.join(directory, os.path.basename(spec_path) + '_reader.xlsx')


def program_version():
    try:
        import subprocess
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return subprocess.run(['git', '-C', here, 'describe', '--always', '--dirty'], capture_output=True,
                              text=True, timeout=5).stdout.strip() or 'unknown'
    except Exception:
        return 'unknown'


def _scans_text(scans):
    return ','.join(str(int(s)) for s in scans)


def _now():
    return datetime.datetime.now().replace(microsecond=0).isoformat(sep=' ')


def _clean(v):
    """A value openpyxl writes: numbers as float/int, NaN as empty."""
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else float(v)
    return str(v)


class WorkbookReadOnly(PermissionError):
    """A read-only workbook was asked to save: another reader writes it
    (D1, ``lss_core.readerlock``)."""


class Workbook:
    """One SPEC file's workbook. Opens the file when it exists, otherwise
    starts the sheets (an older workbook gains any sheet or column it lacks); ``save`` writes it (atomically: a temporary file
    replaced in one step, so a crash never leaves half a workbook). ``read_only``: another reader holds the
    workbook's lock (``lss_core.readerlock``, D1): everything can be read and changed in memory, but ``save``
    raises ``WorkbookReadOnly`` and writes nothing."""

    def __init__(self, path, read_only=False):
        import openpyxl
        self.path = path
        self.read_only = bool(read_only)
        if os.path.exists(path):
            self.wb = openpyxl.load_workbook(path)
            for name in SHEETS:
                if name not in self.wb.sheetnames:
                    self._new_sheet(name)
                elif name == 'Maps' and [c.value for c in self.wb[name][1]][6:10] == ['x', 'y', 'value', 'error']:
                    self._convert_old_maps()
                else:
                    self._extend_header(name)
            for i, name in enumerate(SHEETS):          # a sheet added later goes to its place
                self.wb.move_sheet(name, offset=i - self.wb.sheetnames.index(name))
        else:
            self.wb = openpyxl.Workbook()
            self.wb.remove(self.wb.active)
            for name in SHEETS:
                self._new_sheet(name)

    def _new_sheet(self, name):
        ws = self.wb.create_sheet(name)
        ws.append(HEADERS[name])
        ws.freeze_panes = 'A2'
        from openpyxl.styles import Font
        for c in ws[1]:
            c.font = Font(bold=True)
        return ws

    def _convert_old_maps(self):
        """A Maps sheet of one row per cell (2026-11-21 format) becomes
        'cell' rows of the present layout, values kept."""
        ws = self.wb['Maps']
        old = [list(r) for r in ws.iter_rows(min_row=2, values_only=True) if any(v is not None for v in r)]
        ws.delete_rows(1, ws.max_row)
        ws.append(HEADERS['Maps'])
        from openpyxl.styles import Font
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in old:
            ws.append(r[:6] + ['cell', r[7], r[6], r[8], r[9]])

    def _extend_header(self, name):
        """Add the header names a workbook from an earlier version lacks
        (new columns are only ever added at the end)."""
        ws = self.wb[name]
        head = [c.value for c in ws[1]]
        from openpyxl.styles import Font
        for j, h in enumerate(HEADERS[name][len(head):], start=len(head) + 1):
            ws.cell(row=1, column=j, value=h).font = Font(bold=True)

    def _rows(self, name):
        ws = self.wb[name]
        head = [c.value for c in ws[1]]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if any(v is not None for v in row):
                yield dict(zip(head, row))

    def save(self):
        if self.read_only:
            raise WorkbookReadOnly('%s is open read-only: another reader writes it (D1)' % self.path)
        for name in SHEETS:
            ws = self.wb[name]
            ws.auto_filter.ref = ws.dimensions
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + '.tmp'
        self.wb.save(tmp)
        os.replace(tmp, self.path)
        return self.path

    # ---- scans and settings ----------------------------------------------

    def set_scans(self, rows):
        """Replace the Scans sheet: ``rows`` of dicts with the Scans headers."""
        ws = self.wb['Scans']
        ws.delete_rows(2, ws.max_row)
        for r in rows:
            ws.append([_clean(r.get(k)) for k in HEADERS['Scans']])

    def set_settings(self, section, values):
        """Write ``values`` (a dict) under ``section``, replacing that
        section's rows; values that are not numbers or text are stored as
        JSON."""
        ws = self.wb['Settings']
        keep = [r for r in self._rows('Settings') if r['section'] != section]
        ws.delete_rows(2, ws.max_row)
        for r in keep:
            ws.append([r[k] for k in HEADERS['Settings']])
        now = _now()
        for k, v in values.items():
            if not isinstance(v, (int, float, str, bool)) or isinstance(v, np.generic):
                v = json.dumps(v, default=lambda o: list(o) if hasattr(o, '__iter__') else str(o))
            ws.append([section, str(k), _clean(v) if not isinstance(v, str) else v, now])

    def settings(self, section):
        out = {}
        for r in self._rows('Settings'):
            if r['section'] == section:
                v = r['value']
                if isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except ValueError:
                        pass
                out[r['key']] = v
        return out

    # ---- results -----------------------------------------------------------

    def next_id(self):
        n = 0
        for r in self._rows('Saved'):
            try:
                n = max(n, int(str(r['id']).lstrip('R')))
            except ValueError:
                pass
        return 'R%04d' % (n + 1)

    def next_version(self, kind, scans, label):
        st = _scans_text(scans)
        return 1 + sum(1 for r in self._rows('Saved')
                       if r['kind'] == kind and str(r['scans']) == st and (r['label'] or '') == (label or ''))

    def add_result(self, kind, scans, data=None, columns=(), label='', note='', settings=None, fits=(),
                   map_xyz=None, program=None, trends=(), time_axis='', series=None, recipe='', origin='user'):
        """Store one result and return its id. ``kind``: one of ``KINDS``
        (or another short text); ``scans``: the scan numbers it comes from;
        ``data``: (N, k ≤ 6) array, named by ``columns``; ``fits``: (curve
        label, lss_core.peaks.FitResult or a list of them) pairs; ``map_xyz``:
        (X, Y, value, error) 2-D arrays of a map; ``trends``: (quantity,
        lss_core.trends.TrendComparison) pairs, over ``time_axis``;
        ``series``: the series the scans belong to (``series_for``: dict with
        id, kind, scans, status); ``recipe``: the lss_core call that remakes
        the result;
        ``settings``: what produced it (stored as JSON in Saved)."""
        scans = [int(s) for s in scans]
        first = min(scans) if scans else None
        rid = self.next_id()
        version = self.next_version(kind, scans, label)
        st = _scans_text(scans)
        now = _now()
        data = None if data is None else np.asarray(data, float)
        if data is not None and data.ndim == 1:
            data = data[:, None]
        if data is not None and data.shape[1] > MAX_VALUES:
            raise ValueError('at most %d columns per data vector' % MAX_VALUES)
        npts = 0 if data is None else len(data)
        se = series or {}
        digest = content_key(kind, scans, data, columns, label, settings, fits, map_xyz, trends)
        self.wb['Saved'].append([rid, now, kind, first, st, label, version, note, npts, ', '.join(columns),
                                 json.dumps(settings or {}, default=str), program or program_version(),
                                 se.get('id'), se.get('kind'), _scans_text(se['scans']) if se.get('scans') else None,
                                 se.get('status'), recipe or None, None, origin, digest, se.get('points'),
                                 json.dumps(se['scan_points']) if se.get('scan_points') else None])
        if data is not None:
            ws = self.wb['Data']
            for i, row in enumerate(data):
                ws.append([rid, kind, first, st, label, version, i] + [_clean(v) for v in row] +
                          [None] * (MAX_VALUES - len(row)))
        for curve, res in fits:
            for r in (res if isinstance(res, (list, tuple)) else [res]):
                self._add_fit(rid, kind, first, st, label, version, curve, r, now)
        for quantity, comp in trends:
            self._add_trend(rid, kind, first, st, label, version, quantity, comp, time_axis, now)
        if map_xyz is not None:
            self._add_map(rid, [rid, kind, first, st, label, version], *map_xyz)
        return rid

    def _add_map(self, rid, ident, X, Y, V, E):
        X, Y, V, E = (np.asarray(a, float) for a in (X, Y, V, E))
        ws = self.wb['Maps']
        grid = (V.ndim == 2 and X.shape == V.shape and Y.shape == V.shape
                and np.allclose(X, X[0:1, :], equal_nan=True) and np.allclose(Y, Y[:, 0:1], equal_nan=True))
        if grid:
            ws.append(ident + ['x', None] + [_clean(v) for v in X[0]])
            for part, A in (('value', V), ('error', E)):
                for k in range(A.shape[0]):
                    ws.append(ident + [part, _clean(Y[k, 0])] + [_clean(v) for v in A[k]])
            return
        for x, y, v, e in zip(X.ravel(), Y.ravel(), V.ravel(), E.ravel()):
            if np.isfinite(v):
                ws.append(ident + ['cell', _clean(y), _clean(x), _clean(v), _clean(e)])

    def map(self, rid):
        """A saved map: (X, Y, value, error) as 2-D arrays for a grid (NaN
        where nothing was measured), or 1-D arrays for 'cell' rows."""
        ws = self.wb['Maps']
        xs, rows, cells = None, {'value': [], 'error': []}, []
        for r in ws.iter_rows(min_row=2, values_only=True):
            if r[0] != rid:
                continue
            part = r[6]
            if part == 'x':
                xs = [np.nan if v is None else v for v in r[8:]]
            elif part in rows:
                rows[part].append((r[7], [np.nan if v is None else v for v in r[8:]]))
            elif part == 'cell':
                cells.append(r[7:11])
        if xs is not None:
            n = len(xs)
            while n and np.isnan(xs[n - 1]):
                n -= 1
            ys = np.array([y for y, _ in rows['value']], float)
            V = np.array([(v + [np.nan] * n)[:n] for _, v in rows['value']], float)
            E = np.array([(v + [np.nan] * n)[:n] for _, v in rows['error']], float)
            X, Y = np.meshgrid(np.array(xs[:n], float), ys)
            return X, Y, V, E
        if not cells:
            raise KeyError('no map %s' % rid)
        a = np.array([[np.nan if v is None else v for v in c] for c in cells], float)
        return a[:, 1], a[:, 0], a[:, 2], a[:, 3]

    def _add_fit(self, rid, kind, first, st, label, version, curve, r, now):
        ws = self.wb['Fits']
        o = getattr(r, 'options', None)
        fitkind = getattr(r, 'kind', 'peak')
        if not r.peaks:
            ws.append([rid, kind, first, st, label, version, curve, 0] + [None] * 9 +
                      [getattr(o, 'shape', None), getattr(o, 'background', None), 'failed: ' + r.message, now])
            return
        for k, p in enumerate(r.peaks):
            ws.append([rid, kind, first, st, label, version, curve, k + 1] +
                      [_clean(v) for v in (p.centre, p.centre_err, p.fwhm, p.fwhm_err, p.height, p.height_err,
                                           p.area, p.area_err, r.chi2_dof)] +
                      [p.shape, getattr(o, 'background', None), fitkind, now])

    def _add_trend(self, rid, kind, first, st, label, version, quantity, comp, time_axis, now):
        ws = self.wb['Trends']
        ch = comp.change
        for r in comp.table():
            mine = ch is not None and r['model'] == ch.model
            ws.append([rid, kind, first, st, label, version, quantity, r['model'], r['k'], len(comp.t),
                       _clean(r['chi2_dof']), comp.criterion, _clean(r['criterion']), _clean(r['delta']),
                       _clean(r['weight']), r['model'] == comp.best, _clean(comp.stable),
                       r['params'] or (r['message'] or None),
                       _clean(ch.threshold) if mine else None, _clean(ch.best) if mine and np.isfinite(ch.best) else
                       ('> %g' % ch.horizon if mine and ch.best == float('inf') else None),
                       _clean(ch.confident) if mine and np.isfinite(ch.confident) else
                       ('> %g' % ch.horizon if mine and ch.confident == float('inf') else None),
                       _clean(ch.confidence) if mine else None, time_axis, now])

    def trends(self, rid=None, scan=None):
        """Trends rows (dicts) of one result or containing a scan."""
        out = []
        for r in self._rows('Trends'):
            if rid is not None and r['id'] != rid:
                continue
            if scan is not None and int(scan) not in [int(s) for s in str(r['scans']).split(',') if s]:
                continue
            out.append(r)
        return out

    def mark_stale(self, current, points=None):
        """Compare every saved result's series with ``current`` (the file's
        series now, lss_core.series.Series) and write why it is out of date
        into ``stale`` (or clear it): the series has data scans it did not
        have, its status changed (e.g. in progress → complete), or it is
        gone, or (``points``: {scan: points now}) its scans hold more
        points than when it was saved (the last scan still being written).
        A guessed series' id is its first scan's number, so a result
        is matched by id first, then by the series that holds its first
        scan. Rows already remade ('superseded by …') are left as they
        are. Returns {result id: reason} of the stale ones."""
        ws = self.wb['Saved']
        head = [c.value for c in ws[1]]
        if 'stale' not in head:
            return {}
        col = {h: k for k, h in enumerate(head)}
        by_id = {s.id: s for s in current}
        out = {}
        for row in ws.iter_rows(min_row=2):
            sid = row[col['series']].value
            if not sid or str(row[col['stale']].value or '').startswith('superseded'):
                continue
            saved = [int(x) for x in str(row[col['series_scans']].value or '').split(',') if x.strip()]
            s = by_id.get(sid)
            if s is None and saved:
                s = next((c for c in current if saved[0] in c.data_scans), None)
            reason = ''
            if s is None:
                reason = 'series %s no longer found' % sid
            else:
                new = [n for n in s.data_scans if n not in saved]
                gone = [n for n in saved if n not in s.data_scans]
                if new:
                    reason = 'series %s gained scans %s' % (s.id, _scans_text(new))
                if gone:
                    reason += ('; ' if reason else '') + 'scans %s left the series' % _scans_text(gone)
                was = row[col['series_status']].value
                if was and s.status and was != s.status:
                    reason += ('; ' if reason else '') + 'status %s → %s' % (was, s.status)
                had = row[col['series_points']].value if 'series_points' in col else None
                if points is not None and had is not None and not new and not gone:
                    now_pts = sum(points.get(n, 0) for n in s.data_scans)
                    if now_pts > had:
                        reason += ('; ' if reason else '') + 'points %d → %d' % (had, now_pts)
            row[col['stale']].value = reason or None
            if reason:
                out[row[col['id']].value] = reason
        return out

    def find_content(self, digest):
        """The id of a saved result with this ``content`` digest, or None."""
        for r in self._rows('Saved'):
            if r.get('content') == digest:
                return r['id']
        return None

    def supersede(self, rid, by):
        """Mark result ``rid`` as remade by ``by`` (live updates)."""
        ws = self.wb['Saved']
        head = [c.value for c in ws[1]]
        for row in ws.iter_rows(min_row=2):
            if row[head.index('id')].value == rid:
                row[head.index('stale')].value = 'superseded by %s (%s)' % (by, row[head.index('stale')].value or '')
                return

    def stale(self):
        """Saved rows (dicts) whose ``stale`` says why they are out of date."""
        return [r for r in self._rows('Saved') if r.get('stale')]

    def results(self, kind=None, scan=None):
        """Saved rows (dicts), optionally of one kind or containing a scan."""
        out = []
        for r in self._rows('Saved'):
            if kind is not None and r['kind'] != kind:
                continue
            if scan is not None and int(scan) not in [int(s) for s in str(r['scans']).split(',') if s]:
                continue
            out.append(r)
        return out

    def all_data(self):
        """{id: (N, k) array} of every result, in one pass over the Data sheet
        (``data`` scans the whole sheet for each id: 0.48 s per result on a
        300-result workbook, against 0.37 s for all of them this way; the
        timeline research, F83)."""
        rows = {}
        for r in self._rows('Data'):
            rows.setdefault(r['id'], []).append(r)
        out = {}
        for rid, rs in rows.items():
            rs.sort(key=lambda r: r['point'])
            k = max((j for j in range(1, MAX_VALUES + 1) if any(r['v%d' % j] is not None for r in rs)), default=0)
            out[rid] = np.array([[np.nan if r['v%d' % j] is None else r['v%d' % j] for j in range(1, k + 1)]
                                 for r in rs], float) if k else np.zeros((0, 0))
        return out

    def data(self, rid):
        """The data vector of result ``rid``: (N, k) array."""
        rows = [r for r in self._rows('Data') if r['id'] == rid]
        rows.sort(key=lambda r: r['point'])
        if not rows:
            return np.zeros((0, 0))
        k = max(j for j in range(1, MAX_VALUES + 1) if any(r['v%d' % j] is not None for r in rows))
        return np.array([[np.nan if r['v%d' % j] is None else r['v%d' % j] for j in range(1, k + 1)]
                         for r in rows], float)

    def fits(self, rid=None, scan=None):
        out = []
        for r in self._rows('Fits'):
            if rid is not None and r['id'] != rid:
                continue
            if scan is not None and int(scan) not in [int(s) for s in str(r['scans']).split(',') if s]:
                continue
            out.append(r)
        return out


def content_key(kind, scans, data=None, columns=(), label='', settings=None, fits=(), map_xyz=None, trends=(),
                **ignored):
    """A short digest of a result's content (kind, scans, label, columns,
    values, settings, fits, map, trends): equal for a result redrawn
    without change, different as soon as anything that was computed
    differs."""
    import hashlib
    h = hashlib.sha1()
    h.update(json.dumps([kind, [int(x) for x in scans], label or '', list(columns)], default=str).encode())
    for arr in ([data] if data is not None else []) + (list(map_xyz) if map_xyz is not None else []):
        a = np.ascontiguousarray(np.asarray(arr, float))
        h.update(str(a.shape).encode())
        h.update(np.round(a, 12).tobytes())
    h.update(json.dumps(settings or {}, sort_keys=True, default=str).encode())
    for curve, res in fits:
        for r in (res if isinstance(res, (list, tuple)) else [res]):
            h.update(('%s|%s' % (curve, r.summary() if hasattr(r, 'summary') else r)).encode())
    for q, comp in trends:
        h.update(('%s|%s' % (q, json.dumps(comp.table(), default=str))).encode())
    return h.hexdigest()[:16]


def series_for(scans, current, points=None):
    """The series (of ``current``, lss_core.series.Series) that the most of
    ``scans`` belong to, as the dict ``add_result`` stores (with the total
    of its scans' points when ``points``, {scan: points}, is given); None
    when no scan is in a series."""
    scans = set(int(n) for n in scans)
    best, hits = None, 0
    for s in current:
        k = len(scans & set(s.data_scans))
        if k > hits:
            best, hits = s, k
    if best is None:
        return None
    out = dict(id=best.id, kind=best.kind, scans=list(best.data_scans), status=best.status)
    if points is not None:
        out['points'] = int(sum(points.get(n, 0) for n in best.data_scans))
        out['scan_points'] = {str(n): int(points.get(n, 0)) for n in best.data_scans}
    return out


def scan_points_of(row):
    """{scan: points} a saved row recorded (its series' scans when saved), or {}."""
    try:
        return {int(k): int(v) for k, v in json.loads(row.get('scan_points') or '{}').items()}
    except (ValueError, TypeError, AttributeError):
        return {}


def scan_rows(data, par):
    """Rows for the Scans sheet from a specread result: the experiment kind
    from the ``#U Series`` lines or the series the reader infers
    (lss_core.series), alignment scans marked."""
    from . import series
    info = series.scan_info(data, par)
    kinds, where = {}, {}
    for s in series.all_series(info):
        for pos, num in s.scans.items():
            kinds.setdefault(num, (s.kind, s.id, pos, 'data', s.status))
        for num, role in s.aux:
            kinds.setdefault(num, ('alignment' if role == 'align' else s.kind, s.id, None, role, s.status))
    rows = []
    for i in info:
        k = kinds.get(i.num)
        rows.append(dict(scan=i.num, kind=k[0] if k else 'other', command=i.command, points=i.points,
                         series=k[1] if k else None, series_position=k[2] if k else None,
                         role=k[3] if k else None, status=k[4] if k else None))
    return rows
