"""Pixel-for-pixel comparison of two images (Pillow and NumPy, no Qt): the
measured answer to "is the committed figure stale?" once the tool has been
rerun with its defaults. A figure that differs only in a provenance stamp
(the git revision some tools print in a corner) differs in a few hundredths
of a percent of its pixels, inside one small box; ``Diff.box`` says where.
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


def tables_same(a, b, ignore=TIMING_COLUMNS):
    """Whether two text products are the same; for a CSV table, apart from
    its timing columns (``ignore``, by header name): comment lines ('#')
    and every other column compared as text. Other files byte for byte."""
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        da, db = fa.read(), fb.read()
    if da == db:
        return True
    if not str(a).lower().endswith('.csv'):
        return False
    import csv
    import io

    def rows(data):
        text = data.decode('utf-8', 'replace').replace('\r\n', '\n')
        comments = [ln for ln in text.split('\n') if ln.startswith('#')]
        table = list(csv.reader(io.StringIO('\n'.join(ln for ln in text.split('\n') if not ln.startswith('#')))))
        if not table:
            return comments, []
        drop = {i for i, name in enumerate(table[0]) if name.strip() in ignore}
        return comments, [[c for i, c in enumerate(r) if i not in drop] for r in table]
    return rows(da) == rows(db)
