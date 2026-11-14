"""Robustness on the private `bu` sample set (not in the repository).

Skipped when sample_data/bu is absent. For every SPEC file: open it, select
each scan in turn and its first frame, and require that nothing raises.
Run with ``pytest -m slow``. Set LSS_BU_REPORT=path to also write what was
seen (frames, detector, messages, exceptions, seconds) as JSON.
"""
import glob
import json
import os
import time
import traceback

import pytest

import sweep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BU = os.path.join(ROOT, 'sample_data', 'bu')


def _spec_files():
    out = []
    for path in sorted(glob.glob(os.path.join(BU, '*', '*'))):
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                if f.read(2) == b'#F':
                    out.append(os.path.relpath(path, BU))
    return out


pytestmark = [pytest.mark.gui, pytest.mark.slow,
              pytest.mark.skipif(not os.path.isdir(BU),
                                 reason='private bu sample data not present')]


KNOWN = {
    '2026June/20260615': 'duplicate scan numbers in the file: the detector '
                         'paths are never set and selecting the scan raises',
}


def _params():
    return [pytest.param(rel, marks=pytest.mark.xfail(
                strict=True, reason=KNOWN[rel.replace(os.sep, '/')]))
            if rel.replace(os.sep, '/') in KNOWN else rel
            for rel in _spec_files()]


@pytest.mark.parametrize('rel', _params())
def test_every_scan_opens_without_raising(rel, window, qapp, recorder,
                                          tmp_path):
    t0 = time.time()
    window.openSpecFile(fname=os.path.join(BU, rel))
    window.directory = str(tmp_path)
    qapp.processEvents()
    report = {'open': {'seconds': round(time.time() - t0, 2),
                       'messages': list(recorder.messages),
                       'exceptions': _exc(recorder)}}
    failures = list(report['open']['exceptions'])
    lw = window.ui.scanListWidget
    for row in range(lw.count()):
        recorder.messages.clear()
        recorder.exceptions.clear()
        label = lw.item(row).text().strip()
        t0 = time.time()
        try:
            sweep._select_scans(window, qapp, [row])
            frames = window.ui.imageListWidget.count()
            if frames:
                sweep._select_images(window, qapp, [0])
        except Exception:
            recorder.exceptions.append((None, None, None))
            frames = -1
        num = int(label.split()[1])
        entry = {'scan': label, 'frames': frames,
                 'detector': window.specPar.get(num, {}).get('Detector'),
                 'seconds': round(time.time() - t0, 2),
                 'messages': [m for m in recorder.messages
                              if 'not identical' not in m],
                 'exceptions': _exc(recorder)}
        report[str(num)] = entry
        failures += ['%s: %s' % (label, e) for e in entry['exceptions']]
    out = os.environ.get('LSS_BU_REPORT')
    if out:
        data = {}
        if os.path.exists(out):
            with open(out) as f:
                data = json.load(f)
        data[rel] = report
        with open(out, 'w') as f:
            json.dump(data, f, indent=1)
    recorder.exceptions.clear()
    assert not failures, '\n'.join(failures[:20])


def _exc(recorder):
    out = []
    for t, v, tb in recorder.exceptions:
        if t is None:
            out.append('raised outside a slot')
            continue
        where = traceback.extract_tb(tb)[-1]
        out.append('%s: %s @ %s:%d' % (t.__name__, str(v)[:80],
                                       os.path.basename(where.filename),
                                       where.lineno))
    return out
