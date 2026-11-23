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
