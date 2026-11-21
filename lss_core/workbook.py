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
           points, column names, the settings used (JSON), program version
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
Maps       two-dimensional results (GID maps), one row per cell: result
           id, kind, scans, x, y, value, error
Settings   the current settings (section, key, value, time), the fitting
           preferences among them
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
              'settings', 'program'],
    'Data': ['id', 'kind', 'first_scan', 'scans', 'label', 'version', 'point', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6',
             'v7', 'v8'],
    'Fits': ['id', 'kind', 'first_scan', 'scans', 'label', 'version', 'curve', 'peak', 'centre', 'centre_err',
             'fwhm', 'fwhm_err', 'height', 'height_err', 'area', 'area_err', 'chi2_dof', 'shape', 'background',
             'fit', 'saved'],
    'Trends': ['id', 'kind', 'first_scan', 'scans', 'label', 'version', 'quantity', 'model', 'k', 'points',
               'chi2_dof', 'criterion', 'value', 'delta', 'weight', 'best', 'stable', 'params', 'change',
               'change_time', 'change_time_confident', 'confidence', 'time_axis', 'saved'],
    'Maps': ['id', 'kind', 'first_scan', 'scans', 'label', 'version', 'x', 'y', 'value', 'error'],
    'Settings': ['section', 'key', 'value', 'updated'],
}
KINDS = ('reflectivity', 'gid map', 'gid cut', 'line cut', 'fluorescence', 'scan', 'peak fit', 'burn test',
         'other')
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


class Workbook:
    """One SPEC file's workbook. Opens the file when it exists, otherwise
    starts the sheets (an older workbook gains any sheet or column it lacks); ``save`` writes it (atomically: a temporary file
    replaced in one step, so a crash never leaves half a workbook)."""

    def __init__(self, path):
        import openpyxl
        self.path = path
        if os.path.exists(path):
            self.wb = openpyxl.load_workbook(path)
            for name in SHEETS:
                if name not in self.wb.sheetnames:
                    self._new_sheet(name)
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
                   map_xyz=None, program=None, trends=(), time_axis=''):
        """Store one result and return its id. ``kind``: one of ``KINDS``
        (or another short text); ``scans``: the scan numbers it comes from;
        ``data``: (N, k ≤ 6) array, named by ``columns``; ``fits``: (curve
        label, lss_core.peaks.FitResult or a list of them) pairs; ``map_xyz``:
        (X, Y, value, error) 2-D arrays of a map; ``trends``: (quantity,
        lss_core.trends.TrendComparison) pairs, over ``time_axis``;
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
        self.wb['Saved'].append([rid, now, kind, first, st, label, version, note, npts, ', '.join(columns),
                                 json.dumps(settings or {}, default=str), program or program_version()])
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
            X, Y, V, E = (np.asarray(a, float) for a in map_xyz)
            ws = self.wb['Maps']
            for x, y, v, e in zip(X.ravel(), Y.ravel(), V.ravel(), E.ravel()):
                if np.isfinite(v):
                    ws.append([rid, kind, first, st, label, version, _clean(x), _clean(y), _clean(v), _clean(e)])
        return rid

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


def scan_rows(data, par):
    """Rows for the Scans sheet from a specread result: the experiment kind
    from the ``#U Series`` lines or the series the reader infers
    (lss_core.series), alignment scans marked."""
    from . import series
    info = series.scan_info(data, par)
    kinds, where = {}, {}
    groups = series.group(info) if any(i.series for i in info) else []
    for s in list(groups) + list(series.infer(info)):
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
