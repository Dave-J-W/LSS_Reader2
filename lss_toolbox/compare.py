"""Pixel-for-pixel comparison of two images (Pillow and NumPy, no Qt): the
measured answer to "is the committed figure stale?" once the tool has been
rerun with its defaults. A figure that differs only in a provenance stamp
(the git revision some tools print in a corner) differs in a few hundredths
of a percent of its pixels, inside one small box; ``Diff.box`` says where,
and ``stamp_boxes`` / ``same_outside`` let the audit leave the stamp out
(2026-11-25). Text products are compared apart from how they were run
(``tables_same``).
"""
import numpy as np


class Diff:
    """``state``: 'same', 'differ', 'size' (different sizes) or 'unreadable';
    ``fraction`` of pixels that differ; ``box`` (top, bottom, left, right)
    of the differing pixels; ``mask`` (bool array) when they differ."""

    def __init__(self, state, fraction=None, box=None, mask=None, shape=None):
        self.state = state
        self.fraction = fraction
        self.box = box
        self.mask = mask
        self.shape = shape

    def text(self):
        if self.state == 'same':
            return 'identical'
        if self.state == 'size':
            return 'different size'
        if self.state == 'unreadable':
            return 'unreadable'
        t, b, l, r = self.box
        return '%.3f %% of pixels differ (rows %d-%d, columns %d-%d)' % (100 * self.fraction, t, b, l, r)


def load(path):
    from PIL import Image
    with Image.open(path) as im:
        return np.asarray(im.convert('RGBA'))


def compare(path_a, path_b):
    try:
        a, b = load(path_a), load(path_b)
    except (OSError, ValueError):
        return Diff('unreadable')
    if a.shape != b.shape:
        return Diff('size', shape=(a.shape, b.shape))
    mask = np.any(a != b, axis=2)
    if not mask.any():
        return Diff('same', 0.0, shape=a.shape)
    ys, xs = np.nonzero(mask)
    return Diff('differ', float(mask.mean()), (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())), mask,
                a.shape)


def difference_rgb(path_a, mask):
    """An RGB array: the first image darkened, the differing pixels white."""
    a = load(path_a)
    grey = (a[..., :3].mean(axis=2) * 0.25).astype(np.uint8)
    return np.ascontiguousarray(np.dstack([np.where(mask, 255, grey)] * 3).astype(np.uint8))


TIMING_COLUMNS = ('seconds',)       # wall time of a fit or a run: differs on every run by nature
# Lines of a text product that record how it was run, not what it found (2026-11-25): the command line a
# product echoes names the run's own folder (``--out``) and the settings as typed, so a rerun into a run
# folder never matches it. A catalogue item adds its own (``Tool.volatile``: wall times, a revision).
PROVENANCE = (r'^[#\s]*Command line:', r'^[#\s]*"command"\s*:')
COMMAND_KEYS = ('command',)


def _drop_keys(obj, keys):
    if isinstance(obj, dict):
        return {k: _drop_keys(v, keys) for k, v in obj.items() if k not in keys}
    if isinstance(obj, list):
        return [_drop_keys(v, keys) for v in obj]
    return obj


def _lines_kept(text, patterns):
    import re
    rx = [re.compile(p) for p in patterns]
    return [ln for ln in text.replace('\r\n', '\n').split('\n') if not any(r.search(ln) for r in rx)]


def tables_same(a, b, ignore=TIMING_COLUMNS, volatile=()):
    """Whether two text products are the same apart from how they were run:
    a CSV table apart from its timing columns (``ignore``, by header name),
    its comment lines ('#') and every other column compared as text; a JSON
    file apart from its 'command' and timing entries; other text apart from the lines
    that echo the command line. ``volatile``: more line patterns (regular
    expressions) to leave out of comment lines and text, from the item's
    catalogue entry. Files equal byte for byte are the same."""
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        da, db = fa.read(), fb.read()
    if da == db:
        return True
    name = str(a).lower()
    patterns = PROVENANCE + tuple(volatile)
    if name.endswith('.json'):
        import json
        try:
            ja, jb = json.loads(da.decode('utf-8')), json.loads(db.decode('utf-8'))
        except ValueError:
            return False
        keys = COMMAND_KEYS + tuple(ignore)                     # and timings ('seconds'), as a CSV's columns
        return _drop_keys(ja, keys) == _drop_keys(jb, keys)
    if not name.endswith('.csv'):
        return _lines_kept(da.decode('utf-8', 'replace'), patterns) == \
            _lines_kept(db.decode('utf-8', 'replace'), patterns)
    import csv
    import io

    def rows(data):
        text = data.decode('utf-8', 'replace').replace('\r\n', '\n')
        comments = _lines_kept('\n'.join(ln for ln in text.split('\n') if ln.startswith('#')), patterns)
        table = list(csv.reader(io.StringIO('\n'.join(ln for ln in text.split('\n') if not ln.startswith('#')))))
        if not table:
            return comments, []
        drop = {i for i, name in enumerate(table[0]) if name.strip() in ignore}
        return comments, [[c for i, c in enumerate(r) if i not in drop] for r in table]
    return rows(da) == rows(db)


# ---------------------------------------------------------------- the revision stamp

STAMP_ENV = 'LSS_TOOLS_REVISION'      # a tool that prints its git revision prints this instead when it is set
STAMP_DUMMY = 'W' * 16                # wider than any revision: its box covers the real one's
STAMP_PAD = 4                         # pixels added around each box
STAMP_LIMIT = 0.02                    # more of the image than this moved with the stamp: not a stamp


def stamp_boxes(run_path, stamp_path, pad=STAMP_PAD, limit=STAMP_LIMIT):
    """Boxes (top, bottom, left, right) where a figure changes with its
    revision stamp alone: the pixels that differ between two runs of the
    same code, one with ``STAMP_DUMMY`` as the revision (connected regions,
    each padded by ``pad``). [] when the runs are identical; None when they
    differ in size or in more than ``limit`` of the pixels (the stamp moved
    the layout: no mask is safe)."""
    from scipy import ndimage
    d = compare(run_path, stamp_path)
    if d.state == 'same':
        return []
    if d.state != 'differ' or d.fraction > limit:
        return None
    grown = ndimage.binary_dilation(d.mask, iterations=pad)
    labels, _ = ndimage.label(grown)
    return [(sl[0].start, sl[0].stop - 1, sl[1].start, sl[1].stop - 1) for sl in ndimage.find_objects(labels)]


def same_outside(path_a, path_b, boxes):
    """Whether two images are identical outside ``boxes`` (from
    ``stamp_boxes``: the dummy revision is wider than any real one, so its
    boxes hold the committed stamp too, and the text after a stamp, which
    moves with the stamp's length)."""
    d = compare(path_a, path_b)
    if d.state == 'same':
        return True
    if d.state != 'differ' or boxes is None:
        return False
    keep = d.mask.copy()
    for t, b, l, r in boxes:
        keep[max(t, 0):b + 1, max(l, 0):r + 1] = False
    return not keep.any()
