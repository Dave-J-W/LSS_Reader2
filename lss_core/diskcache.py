"""A local disk cache for images read from slow (network) drives (F8).

In production the data live on a network drive. Decoded frames are kept
as ``.npy`` files in a local folder, so that a frame read once is read
from the local disk afterwards, also after the program restarts.

Settings (environment variables):

``LSS_READER_DISK_CACHE``     folder (default ``~/.lss_reader/cache``);
                              ``off`` disables the disk cache
``LSS_READER_DISK_CACHE_MB``  size limit (default 5120, i.e. 5 GB); oldest-used files
                              are removed first
``LSS_READER_DISK_CACHE_ALL`` ``1``: cache every file. Otherwise only files
                              on a different file system from the cache
                              folder are cached (a network drive is; the
                              local disk is not, and gains nothing).

Entries are keyed by path, size and modification time; a file that changes
is read again. Any problem with the cache (full disk, permissions, a
damaged entry) falls back to reading the original file.
"""
import hashlib
import os
import time

import numpy as np

_MB = 1024 * 1024


def cache_dir():
    value = os.environ.get('LSS_READER_DISK_CACHE', '')
    if value.lower() == 'off':
        return None
    return value or os.path.join(os.path.expanduser('~'), '.lss_reader', 'cache')


def limit_bytes():
    try:
        return int(float(os.environ.get('LSS_READER_DISK_CACHE_MB', '5120')) * _MB)
    except ValueError:
        return 5120 * _MB


def _wanted(path, folder):
    if os.environ.get('LSS_READER_DISK_CACHE_ALL') == '1':
        return True
    try:
        return os.stat(path).st_dev != os.stat(folder).st_dev
    except OSError:
        return False


def _entry(folder, key):
    digest = hashlib.sha1(repr(key).encode('utf-8', 'replace')).hexdigest()
    return os.path.join(folder, digest[:2], digest + '.npy')


def load(key, reader):
    """``reader(path)`` through the disk cache. ``key`` = (path, size, mtime)."""
    folder = cache_dir()
    path = key[0]
    if folder is None:
        return reader(path)
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        return reader(path)
    if not _wanted(path, folder):
        return reader(path)
    entry = _entry(folder, key)
    try:
        value = np.load(entry, allow_pickle=False)
        os.utime(entry)                    # mark as recently used
        value.setflags(write=False)
        return value
    except (OSError, ValueError):
        pass
    value = reader(path)
    try:
        os.makedirs(os.path.dirname(entry), exist_ok=True)
        tmp = entry + '.%d.tmp' % os.getpid()
        with open(tmp, 'wb') as f:
            np.save(f, value, allow_pickle=False)
        os.replace(tmp, entry)             # atomic: never a half-written entry
        _added(folder, os.path.getsize(entry))
    except OSError:
        pass
    return value


# Bytes this process knows to be in each cache folder. The folder is walked
# once, then only when the running total passes the limit, and then trimmed
# to TRIM_TO of the limit: walking it after every new entry cost 16 ms per
# frame at 6600 entries on a local disk (2026-11-23), more on Windows. Other
# processes' additions are seen at the next walk, so the limit is soft.
_KNOWN = {}
TRIM_TO = 0.9


def _added(folder, nbytes):
    known = _KNOWN.get(folder)
    if known is None:
        _KNOWN[folder] = _trim(folder)
    elif known + nbytes > limit_bytes():
        _KNOWN[folder] = _trim(folder, TRIM_TO * limit_bytes())
    else:
        _KNOWN[folder] = known + nbytes


def _trim(folder, target=None):
    """Remove least recently used entries until the cache holds at most
    ``target`` bytes (default: the size limit); return what it holds."""
    limit = limit_bytes() if target is None else target
    entries = []
    total = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if name.endswith('.npy'):
                p = os.path.join(root, name)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                entries.append((st.st_mtime, st.st_size, p))
                total += st.st_size
    for _t, size, p in sorted(entries):
        if total <= limit:
            break
        try:
            os.remove(p)
            total -= size
        except OSError:
            pass
    return total


def clear():
    folder = cache_dir()
    _KNOWN.pop(folder, None)
    if folder and os.path.isdir(folder):
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if name.endswith('.npy'):
                    try:
                        os.remove(os.path.join(root, name))
                    except OSError:
                        pass
