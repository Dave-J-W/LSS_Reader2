"""Research tool for the sample timeline tab (F83; docs/gui/timeline/research.md).

Two modes, both reading SPEC files only (never writing beside them):

    python tests/tools/timeline_mock.py survey <SPEC file or folder> ...
    python tests/tools/timeline_mock.py mock [--spec PATH] [--out PNG] [--no-reduce]

``survey`` prints counts only (scans, kinds, sample-height scans, motor
redefinitions written by SPEC's ``set``, sx changes, which column and motor
names look like sample-environment readings). It prints no comment text, no
data values and no sample names, so that it may be run on the private sets
(sample_data/bu, sample_data/private) and its output quoted in the docs
(owner's rule, AGENTS.md).

``mock`` draws a low-fidelity picture of the proposed timeline from one SPEC
file (default: the public NX school file) to ``docs/gui/timeline/mock_nx.png``
(PNG quantised to 256 colours, as tests/tools/gui_screens.py does). The
reduction thumbnails come from re-reducing the reflectivity series with
lss_core (``--no-reduce`` draws placeholders); the tab itself would draw them
from the workbook. A mock of a private file must be written under
sample_data/private/figures/ only.

What is recognised (the rules the research proposes; none is in the reader yet):

- motor redefinitions: SPEC's standard ``set`` macro writes
  ``#C <date>.  <motor name> reset from <old> to <new>.`` into the data file;
  ``set sh 0`` is ``Sample_H reset from X to 0``;
- sample-height scans: ``ascan``/``a2scan``/``dscan``/``d2scan``/``lup`` whose
  first motor is ``sh`` and moves (start != end); the motor's name is the
  first ``#L`` column (``Sample_H``);
- sx: ``Sample_X`` from each scan's ``#P`` lines (the position at the scan's
  start), or a column of that name within a scan;
- times: lss_core.timing.point_times (``#D`` plus Epoch steps for old files).

Run from the repository root with QT_QPA_PLATFORM=offscreen MPLBACKEND=Agg.
"""
import argparse
import collections
import datetime
import os
import re
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

NX = os.path.join(ROOT, 'sample_data', 'NX_school', '2026sep', '20260923')
OUT = os.path.join(ROOT, 'docs', 'gui', 'timeline', 'mock_nx.png')

COMMENT = re.compile(r'^#C\s+(?P<date>\w{3} \w{3} +\d+ \d\d:\d\d:\d\d \d{4})\.\s+(?P<text>.*?)\s*$')
RESET = re.compile(r'^(?P<motor>\S+) reset from (?P<old>\S+) to (?P<new>[^\s]+?)\.?$')
SLIT_ECHO = re.compile(r'^s\d[vh] \S+ \S+\s*$')
SH_SCANS = ('ascan', 'a2scan', 'dscan', 'd2scan', 'lup')
ENV_WORDS = re.compile(r'tens|barr|oxy|(^|_)o2|temp|press|humid|wilh|trough|^pi$|surf_?press', re.I)


# ---- reading ----------------------------------------------------------------

def comments(path):
    """[(line number, unix-like s read as UTC, kind, fields)] of the file's
    dated #C lines: 'reset' (motor, old, new), 'abort', 'do' (a macro file
    loaded), 'other'. Also the count of undated slit echo lines."""
    from lss_core import timing
    out, echoes = [], 0
    with open(path, errors='replace') as fid:
        for k, line in enumerate(fid):
            if SLIT_ECHO.match(line):
                echoes += 1
                continue
            m = COMMENT.match(line)
            if not m:
                continue
            try:
                t = timing.parse_date(m.group('date'))
            except ValueError:
                continue
            text = m.group('text')
            r = RESET.match(text)
            if r:
                try:
                    out.append((k, t, 'reset', (r.group('motor'), float(r.group('old')), float(r.group('new')))))
                    continue
                except ValueError:
                    pass
            if 'Scan aborted' in text:
                out.append((k, t, 'abort', None))
            elif text.startswith('do '):
                out.append((k, t, 'do', None))
            else:
                out.append((k, t, 'other', None))
    return out, echoes


def is_sh_scan(command):
    w = command.split()
    if len(w) < 4 or w[0] not in SH_SCANS or w[1] != 'sh':
        return False
    try:
        return float(w[2]) != float(w[3])
    except ValueError:
        return False


def scans(path):
    """Per scan: number, command, kind (lss_core.series), start and end
    (s, #D read as UTC: local wall-clock time), sx, columns, the
    reader's Data and Par dicts."""
    from spec_routines import specread
    from lss_core import series, timing
    r = specread(path)
    info = series.scan_info(r.Data, r.Par)
    kind = {}
    for s in series.all_series(info):
        for n in s.data_scans:
            kind[n] = (s.kind, s.id)
        for n, role in s.aux:
            kind.setdefault(n, ('alignment' if role == 'align' else s.kind, s.id))
    out = []
    for x in info:
        d, p = r.Data[x.num], r.Par[x.num]
        cols = {k: v for k, v in d.items() if isinstance(v, np.ndarray)}
        pt = timing.point_times(cols, p.get('Date'), 0.0)       # local wall clock, like the #C dates
        if pt.start is not None and len(pt.start):
            t0 = float(pt.start[0])
            sec = cols.get('Seconds')
            t1 = float(pt.start[-1]) + (float(sec[-1]) if sec is not None and len(sec) else 0.0)
        elif p.get('Date'):
            t0 = t1 = timing.parse_date(p['Date'])
        else:
            t0 = t1 = None
        k = kind.get(x.num, ('other', None))
        if is_sh_scan(x.command):
            k = ('sh', k[1])
        elif is_burn_like(x.command):
            k = ('burn', k[1])
        sx = p.get('Sample_X')
        out.append(dict(num=x.num, command=x.command, kind=k[0], series=k[1], t0=t0, t1=t1, sx=sx,
                        columns=list(d.get('ScanVar', []) if d.get('ScanVar') != 'Empty' else []),
                        data=cols, par=p, points=x.points, aborted=x.aborted))
    return out, r


def is_burn_like(command):
    from lss_core import series
    return series.is_burn(command)


# ---- the sample-height scan fit ----------------------------------------------

def super_gaussian(h, A, h0, w, p, b):
    return A * np.exp(-np.abs((h - h0) / w) ** p) + b


def fit_sh(x, counts, monitor):
    """Super-Gaussian I = A exp(-|(h-h0)/w|^p) + b to counts/monitor (Poisson
    errors). Returns dict(fwhm, p, p_err, chi2, gauss_chi2, centre) or
    dict(error=...) when the scan holds no reflected beam."""
    from scipy.optimize import curve_fit
    x = np.asarray(x, float)
    c = np.asarray(counts, float)
    m = np.asarray(monitor, float)
    if len(x) < 7:
        return dict(error='too few points (%d)' % len(x))
    scale = np.mean(m)
    y = c / m * scale
    s = np.sqrt(np.maximum(c, 1.0)) / m * scale
    b0 = float(np.median(np.r_[y[:2], y[-2:]]))
    A0 = float(y.max() - b0)
    # a beam that is not there: the peak must stand 10 sigma above the edges
    if A0 < 10 * np.sqrt(max(b0, 1.0)) or np.sum(y > b0 + A0 / 2) < 3:
        return dict(error='no reflected beam')
    h0 = float(np.sum(x * np.clip(y - b0, 0, None)) / np.sum(np.clip(y - b0, 0, None)))
    half = x[y > b0 + A0 / 2]
    w0 = max((half.max() - half.min()) / 2, abs(x[1] - x[0]))
    best = None
    for p0 in (2.0, 4.0):
        try:
            popt, pcov = curve_fit(super_gaussian, x, y, p0=[A0, h0, w0, p0, b0], sigma=s, absolute_sigma=True,
                                   bounds=([0, x.min(), 1e-6, 0.8, -np.inf], [np.inf, x.max(), np.ptp(x), 20, np.inf]),
                                   maxfev=4000)
        except (RuntimeError, ValueError):
            continue
        chi = float(np.sum(((y - super_gaussian(x, *popt)) / s) ** 2) / (len(x) - 5))
        if best is None or chi < best[2]:
            best = (popt, pcov, chi)
    if best is None:
        return dict(error='fit failed')
    popt, pcov, chi = best
    A, h0, w, p, b = popt
    try:
        pg, _ = curve_fit(lambda h, A, h0, w, b: super_gaussian(h, A, h0, w, 2.0, b), x, y, p0=[A, h0, w, b],
                          sigma=s, absolute_sigma=True, maxfev=4000)
        gchi = float(np.sum(((y - super_gaussian(x, pg[0], pg[1], pg[2], 2.0, pg[3])) / s) ** 2) / (len(x) - 4))
    except (RuntimeError, ValueError):
        gchi = float('nan')
    return dict(fwhm=float(2 * w * np.log(2) ** (1 / p)), p=float(p), p_err=float(np.sqrt(abs(pcov[3, 3]))),
                chi2=chi, gauss_chi2=gchi, centre=float(h0), x=x, y=y, model=popt)


def sh_signal(scan):
    d = scan['data']
    cols = scan['columns']
    if not cols:
        return None
    x = d.get(cols[0])
    c = d.get('Pilatus')
    m = d.get('Monc', d.get('monc'))
    if x is None or c is None or m is None or len(x) == 0:
        return None
    return x, c, m


# ---- survey (counts only) ----------------------------------------------------

def survey(paths):
    from spec_routines import is_spec_file
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                files += [os.path.join(root, n) for n in sorted(names) if is_spec_file(os.path.join(root, n))]
        elif is_spec_file(p):
            files.append(p)
    tot = collections.Counter()
    env_cols, env_motors = collections.Counter(), collections.Counter()
    for f in files:
        t = time.perf_counter()
        try:
            sc, r = scans(f)
        except Exception as e:                     # an odd file must not stop the survey
            print('%s: not read (%s)' % (os.path.basename(f), type(e).__name__))
            continue
        dt = time.perf_counter() - t
        com, echoes = comments(f)
        resets = [c for c in com if c[2] == 'reset']
        motors = collections.Counter(c[3][0] for c in resets)
        sh_resets = [c for c in resets if c[3][0] == 'Sample_H']
        to_zero = [c for c in sh_resets if c[3][2] == 0]
        sx = [s['sx'] for s in sc if s['sx'] is not None]
        sx_changes = sum(1 for a, b in zip(sx, sx[1:]) if abs(a - b) > 1e-3)
        sx_col = sum(1 for s in sc if 'Sample_X' in s['columns'])
        kinds = collections.Counter(s['kind'] for s in sc)
        times = [s['t0'] for s in sc if s['t0'] is not None]
        hours = (max(times) - min(times)) / 3600 if times else 0
        # after each Sample_H reset to 0: minutes to the next sh scan
        gaps = []
        for c in to_zero:
            nxt = [s['t0'] for s in sc if s['kind'] == 'sh' and s['t0'] is not None and s['t0'] >= c[1]]
            if nxt:
                gaps.append((min(nxt) - c[1]) / 60)
        fits = collections.Counter()
        for s in sc:
            if s['kind'] == 'sh':
                sig = sh_signal(s)
                if sig is None:
                    fits['no Pilatus/Monc'] += 1
                    continue
                res = fit_sh(*sig)
                if 'error' in res:
                    fits[res['error']] += 1
                else:
                    fits['fitted'] += 1
                    fits['p>2' if res['p'] > 2 else 'p<=2'] += 1
                    fits['FWHM>=65um' if res['fwhm'] >= 0.065 else 'FWHM<65um'] += 1
        cols = set(c for s in sc for c in s['columns'])
        motor_names = set(k for s in sc for k in s['par'] if isinstance(s['par'].get(k), (int, float)))
        for c in cols:
            if ENV_WORDS.search(c):
                env_cols[c] += 1
        hdr_U = sum(1 for line in open(f, errors='replace') if line.startswith('#U'))
        temp_nonzero = sum(1 for line in open(f, errors='replace')
                           if 'Ave.Temp.' in line and not re.search(r'Ave\.Temp\. = 0C', line))
        print('%s: %d scans over %.1f h (read %.2f s); kinds %s' % (
            os.path.basename(f), len(sc), hours, dt, dict(kinds)))
        print('   #C resets %d (by motor %s); Sample_H resets %d, to 0: %d; minutes from a reset to 0 to the next sh '
              'scan: %s' % (len(resets), dict(motors), len(sh_resets), len(to_zero),
                            [round(g, 1) for g in gaps[:12]] + (['...'] if len(gaps) > 12 else [])))
        print('   aborts %d, macro loads %d, other dated #C %d, slit echo lines %d, #U lines %d, '
              'non-zero Ave.Temp footers %d' % (
                  sum(1 for c in com if c[2] == 'abort'), sum(1 for c in com if c[2] == 'do'),
                  sum(1 for c in com if c[2] == 'other'), echoes, hdr_U, temp_nonzero))
        print('   sx (#P Sample_X) in %d scans, %d changes between consecutive scans, distinct %d; Sample_X as a '
              'column in %d scans' % (len(sx), sx_changes, len(set(np.round(sx, 3))), sx_col))
        print('   sh scans fitted: %s' % dict(fits))
        print('   column names that look like environment readings: %s' % sorted(c for c in cols if ENV_WORDS.search(c)))
        print('   motor names (#P) that look like environment readings: %s' % sorted(
            m for m in motor_names if ENV_WORDS.search(m) and m not in ('Absorber',)))
        tot.update(files=1, scans=len(sc), resets=len(resets), sh_resets=len(sh_resets), to_zero=len(to_zero),
                   sh_scans=kinds.get('sh', 0), sx_changes=sx_changes)
    print('TOTAL', dict(tot))


# ---- mock ---------------------------------------------------------------------

KIND_COLOURS = {'reflectivity': '#1f77b4', 'gid': '#2ca02c', 'xfntr': '#9467bd', 'burn': '#d62728',
                'sh': '#ff7f0e', 'alignment': '#bcbd22', 'energy': '#8c564b', 'other': '#7f7f7f'}


def mock(spec, out, reduce=True):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    sc, r = scans(spec)
    com, _ = comments(spec)
    to_dt = lambda t: mdates.date2num(datetime.datetime.fromtimestamp(t, datetime.timezone.utc).replace(tzinfo=None))
    times = [s['t0'] for s in sc if s['t0'] is not None] + [s['t1'] for s in sc if s['t1'] is not None]
    tmin, tmax = min(times), max(times)
    pad = (tmax - tmin) * 0.03
    x0, x1 = to_dt(tmin - pad), to_dt(tmax + pad)
    span = x1 - x0

    lanes = [('Events', 0.7), ('sx (mm)', 1.0), ('Sample height', 1.9), ('Scans', 1.0), ('Reduced', 1.9),
             ('Environment', 0.7), ('Notes', 0.8)]
    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.suptitle('Sample timeline: low-fidelity mock from %s (public NX school data); F83' % os.path.basename(spec),
                 fontsize=11, x=0.01, ha='left')
    total = sum(h for _, h in lanes)
    top, bottom, left, right = 0.93, 0.06, 0.09, 0.99
    axes = {}
    y = top
    for name, h in lanes:
        hh = (top - bottom) * h / total
        ax = fig.add_axes([left, y - hh, right - left, hh * 0.92], sharex=axes.get('Events'))
        ax.set_xlim(x0, x1)
        ax.set_ylabel(name, rotation=0, ha='right', va='center', fontsize=9)
        ax.tick_params(labelbottom=False, labelsize=7)
        ax.set_facecolor('#fafafa')
        axes[name] = ax
        y -= hh
    axes['Notes'].tick_params(labelbottom=True)
    axes['Notes'].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    for name in ('Events', 'Sample height', 'Scans', 'Reduced', 'Environment', 'Notes'):
        axes[name].set_yticks([])

    # events: Sample_H set to 0 across every lane; other resets, aborts, macro loads as ticks
    ev = axes['Events']
    ev.set_ylim(0, 1)
    for k, t, kind, f in com:
        x = to_dt(t)
        if kind == 'reset' and f[0] == 'Sample_H' and f[2] == 0:
            for ax in axes.values():
                ax.axvline(x, color='#c00000', lw=1.6, ls='--', zorder=0)
            ev.text(x, 0.55, ' set sh 0\n new sample?', color='#c00000', fontsize=8, va='center')
        elif kind == 'reset':
            ev.plot([x], [0.25], marker='v', color='#e07000', ms=7)
            ev.text(x, 0.02, '%s %+.1f µm' % ('sh' if f[0] == 'Sample_H' else f[0], (f[2] - f[1]) * 1e3),
                    fontsize=6, color='#e07000', ha='center')
        elif kind == 'abort':
            ev.plot([x], [0.8], marker='x', color='#555555', ms=6)
        elif kind == 'do':
            ev.plot([x], [0.8], marker='>', color='#1f77b4', ms=4)

    # sx: steps from the scans' #P
    ax = axes['sx (mm)']
    pts = [(to_dt(s['t0']), s['sx']) for s in sc if s['sx'] is not None and s['t0'] is not None]
    if pts:
        xs, ys = zip(*pts)
        ax.step(list(xs) + [x1], list(ys) + [ys[-1]], where='post', color='#444')
        ax.plot(xs, ys, 'o', ms=3, color='#444')
        lo, hi = min(ys), max(ys)
        ax.set_ylim(lo - 0.15 * (hi - lo + 1), hi + 0.15 * (hi - lo + 1))

    # sample-height scans: thumbnails with FWHM and exponent
    ax = axes['Sample height']
    ax.set_ylim(0, 1)
    w_thumb = span * 0.075
    slots = []
    for s in sc:
        if s['kind'] != 'sh' or s['t0'] is None:
            continue
        xc = to_dt(s['t0'])
        row = 0
        while any(abs(xc - a) < w_thumb * 1.05 and rr == row for a, rr in slots):
            row += 1
        slots.append((xc, row))
        y0 = 0.52 - 0.48 * (row % 2)
        ins = ax.inset_axes([xc - w_thumb / 2, y0, w_thumb, 0.44], transform=ax.get_xaxis_transform())
        ins.set_xticks([]); ins.set_yticks([])
        sig = sh_signal(s)
        res = fit_sh(*sig) if sig is not None else dict(error='no Pilatus/Monc')
        if 'error' in res:
            ins.set_facecolor('#eeeeee')
            ins.text(0.5, 0.5, 'S%d\n%s' % (s['num'], res['error']), ha='center', va='center', fontsize=6,
                     transform=ins.transAxes)
            edge = '#999999'
        else:
            hx = np.linspace(res['x'].min(), res['x'].max(), 200)
            ins.plot(res['x'], res['y'], '.', ms=2, color='k')
            ins.plot(hx, super_gaussian(hx, *res['model']), color='#ff7f0e', lw=1)
            good = res['fwhm'] >= 0.065 and res['p'] > 2
            edge = '#2ca02c' if good else '#c00000'
            ins.text(0.02, 0.97, 'S%d  %.0f µm  p %.1f' % (s['num'], res['fwhm'] * 1e3, res['p']),
                     transform=ins.transAxes, fontsize=6, va='top')
        for sp in ins.spines.values():
            sp.set_color(edge); sp.set_linewidth(1.5)

    # scans as bars by kind
    ax = axes['Scans']
    ax.set_ylim(0, 1)
    for s in sc:
        if s['t0'] is None:
            continue
        a, b = to_dt(s['t0']), to_dt(max(s['t1'], s['t0'] + 20))
        ax.add_patch(Rectangle((a, 0.25), b - a, 0.5, color=KIND_COLOURS.get(s['kind'], '#7f7f7f'),
                               alpha=0.5 if s['aborted'] else 0.9, lw=0))
        ax.text((a + b) / 2, 0.8, str(s['num']), fontsize=6, ha='center')
    used = sorted(set(s['kind'] for s in sc))
    for i, k in enumerate(used):
        ax.text(0.005 + i * 0.075, 0.05, '■ ' + k, color=KIND_COLOURS.get(k, '#7f7f7f'), fontsize=7,
                transform=ax.transAxes)

    # reductions: one thumbnail per reflectivity series (re-reduced here; workbook in the tab)
    ax = axes['Reduced']
    ax.set_ylim(0, 1)
    from lss_core import series as sermod
    groups = sermod.all_series(sermod.scan_info(r.Data, r.Par))
    by_num = {s['num']: s for s in sc}
    exp = None
    for g in groups:
        if g.kind not in ('reflectivity', 'gid', 'xfntr') or not g.data_scans:
            continue
        end = max(by_num[n]['t1'] for n in g.data_scans if by_num[n]['t1'] is not None)
        xc = to_dt(end) + w_thumb * 0.6
        ins = ax.inset_axes([xc - w_thumb / 2, 0.06, w_thumb * 1.1, 0.8], transform=ax.get_xaxis_transform())
        ins.set_xticks([]); ins.set_yticks([])
        label = '%s S%s' % (g.kind, '–'.join(str(n) for n in (g.data_scans[0], g.data_scans[-1]))
                            if len(g.data_scans) > 1 else g.data_scans[0])
        drawn = False
        if g.kind == 'reflectivity' and reduce and len(g.data_scans) > 1:
            try:
                if exp is None:
                    from lss_core.experiment import Experiment
                    exp = Experiment(spec)
                res = exp.reflectivity(g.data_scans)
                q, R = res.rrf[:, 0], res.rrf[:, 1]
                ok = R > 0
                ins.semilogy(q[ok], R[ok], '.', ms=2, color='#1f77b4')
                ins.set_yticks([]); ins.set_yticks([], minor=True)
                ins.text(0.03, 0.04, label + '  R/R_F', transform=ins.transAxes, fontsize=6)
                drawn = True
            except Exception as e:                  # the mock shows the failure as a placeholder
                why = type(e).__name__
        else:
            why = 'GID map: from the workbook' if g.kind == 'gid' else (
                'one scan: not patched' if len(g.data_scans) == 1 else 'not reduced in the mock')
        if not drawn:
            ins.set_facecolor('#fff4d6')
            ins.text(0.5, 0.5, '%s\n%s' % (label, why), ha='center', va='center', fontsize=6,
                     transform=ins.transAxes, wrap=True)
        for sp in ins.spines.values():
            sp.set_color(KIND_COLOURS.get(g.kind, '#777')); sp.set_linewidth(1.5)

    # environment readings: none in today's files
    ax = axes['Environment']
    ax.set_ylim(0, 1)
    cols = set(c for s in sc for c in s['columns'])
    env = sorted(c for c in cols if ENV_WORDS.search(c))
    ax.text(0.5, 0.5, ('environment columns: %s' % env) if env else
            'no tensiometer, barrier or O₂ columns in this file (F75: to be written by the macros '
            'for every point); each would be a strip chart here', ha='center', va='center', fontsize=8,
            color='#777', transform=ax.transAxes)

    # notes: an example coloured text box
    ax = axes['Notes']
    ax.set_ylim(0, 1)
    sh0 = [to_dt(t) for _, t, kind, f in com if kind == 'reset' and f[0] == 'Sample_H' and f[2] == 0]
    xn = sh0[0] if sh0 else x0 + span * 0.3
    ax.text(xn + span * 0.006, 0.5, 'note (example): new film spread;\nbarrier and tensiometer read by hand',
            fontsize=7, va='center', bbox=dict(boxstyle='round', fc='#fff2a8', ec='#b59b00'))
    ax.text(xn + span * 0.25, 0.5, 'reduction failed: S3 (example placeholder)', fontsize=7, va='center',
            bbox=dict(boxstyle='round', fc='#ffd6d6', ec='#c00000'))
    fig.text(0.01, 0.006, 'Events: red dashed = Sample_H set to 0 (new sample?), ▼ sh re-referenced by set (µm), '
             '× scan aborted, ▶ macro file loaded.   Sample height: super-Gaussian fit of Pilatus/Monc, FWHM and '
             'exponent p (2 = Gaussian), green frame = FWHM ≥ 65 µm and p > 2.\nReduced: re-reduced for the mock '
             '(the tab would read the workbook); click opens the result.   Notes: stored in the workbook.',
             fontsize=7, color='#444')

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = out + '.tmp.png'
    fig.savefig(tmp, dpi=100)
    plt.close(fig)
    from PIL import Image
    img = Image.open(tmp).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                                                  dither=Image.Dither.NONE)
    img.save(out, optimize=True)
    os.remove(tmp)
    print('wrote', out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='mode', required=True)
    s = sub.add_parser('survey', help='counts only, safe for private files')
    s.add_argument('paths', nargs='+')
    m = sub.add_parser('mock', help='draw the mock timeline')
    m.add_argument('--spec', default=NX)
    m.add_argument('--out', default=OUT)
    m.add_argument('--no-reduce', action='store_true')
    a = ap.parse_args(argv)
    os.chdir(ROOT)                               # .ui files and icons are found from the root
    if a.mode == 'survey':
        survey(a.paths)
    else:
        real = os.path.realpath(a.out)
        priv = os.path.realpath(os.path.join(ROOT, 'sample_data', 'private', 'figures'))
        if os.path.realpath(a.spec) != os.path.realpath(NX) and not real.startswith(priv + os.sep) \
                and 'sample_data' + os.sep + 'NX_school' not in os.path.realpath(a.spec):
            sys.exit('a mock of a non-public file must be written under sample_data/private/figures/')
        mock(a.spec, a.out, not a.no_reduce)


if __name__ == '__main__':
    main()
