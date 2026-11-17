"""Reading detector images.

``read_pilatus`` returns a Pilatus TIFF frame as the reader has always
presented it — the file's image rotated by 270° (PIL ``ROTATE_270``), shape
(width, height) of the file, integer images as int64 and floating-point
images as float64 — bit for bit identical to the earlier
``TwoDDetector.openFile`` code (checked on every image of the sample sets
in ``tests/test_lss_core.py``), about ten times faster, and cached in
memory so that selecting a frame again does not read the file again.
"""
import numpy as np
from PIL import Image

from .cache import MemoryCache

CACHE = MemoryCache()


def _read(path):
    with Image.open(path) as im:
        raw = np.asarray(im)
    frame = np.ascontiguousarray(np.rot90(raw, 3),
                                 dtype=np.float64 if raw.dtype.kind == 'f' else np.int64)
    frame.setflags(write=False)          # shared through the cache
    return frame


def read_pilatus(path, cache=True):
    """The frame in ``path`` as a read-only array (see module docstring).

    Copy it before changing it in place.
    """
    if not cache:
        return _read(path)
    return CACHE.get_or_load(path, _read, lambda a: a.nbytes)
