"""A memory cache for data read from files, sized to the host.

Entries are keyed by (absolute path, size, modification time), so a file
that is rewritten — for instance an image still being written by the
detector, or a SPEC file that grows — is read again rather than served
stale.

The budget is ``$LSS_READER_RAM_CACHE_MB`` if set (0 disables the cache),
otherwise a quarter of the machine's physical memory, at most 4 GB, at
least 256 MB. Least recently used entries are dropped first.
"""
import os
import threading
from collections import OrderedDict

ENV_BUDGET = 'LSS_READER_RAM_CACHE_MB'
_MB = 1024 * 1024


def physical_memory_bytes():
    """Total physical memory, or None when it cannot be found."""
    try:
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    except (AttributeError, ValueError, OSError):
        pass
    try:                                   # Windows
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('sullAvailExtendedVirtual', ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
    except Exception:
        pass
    return None


def default_budget_bytes():
    value = os.environ.get(ENV_BUDGET)
    if value not in (None, ''):
        try:
            return max(0, int(float(value) * _MB))
        except ValueError:
            pass
    total = physical_memory_bytes()
    if total is None:
        return 1024 * _MB
    return int(min(4096 * _MB, max(256 * _MB, total // 4)))


def file_key(path):
    """(absolute path, size, mtime in ns) of an existing file."""
    st = os.stat(path)
    return (os.path.abspath(path), st.st_size, st.st_mtime_ns)


class MemoryCache:
    """Least-recently-used cache with a budget in bytes.

    ``get_or_load(path, loader, size_of)`` returns the cached value for the
    file's current key, or calls ``loader(path)``, stores and returns it.
    Values must not be modified by callers (callers that need to modify
    should copy).
    """

    def __init__(self, budget_bytes=None):
        self.budget = default_budget_bytes() if budget_bytes is None else budget_bytes
        self._items = OrderedDict()   # key -> (value, nbytes)
        self._by_path = {}            # path -> key currently stored
        self.used = 0
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def get_or_load(self, path, loader, size_of):
        key = file_key(path)
        with self._lock:
            item = self._items.get(key)
            if item is not None:
                self._items.move_to_end(key)
                self.hits += 1
                return item[0]
        value = loader(path)
        nbytes = int(size_of(value))
        with self._lock:
            self.misses += 1
            old = self._by_path.get(key[0])
            if old is not None and old != key:      # the file changed on disk
                self._drop(old)
            if 0 < nbytes <= self.budget:
                if key in self._items:
                    self._drop(key)
                self._items[key] = (value, nbytes)
                self._by_path[key[0]] = key
                self.used += nbytes
                while self.used > self.budget:
                    self._drop(next(iter(self._items)))
        return value

    def _drop(self, key):
        value, nbytes = self._items.pop(key)
        self.used -= nbytes
        if self._by_path.get(key[0]) == key:
            del self._by_path[key[0]]

    def clear(self):
        with self._lock:
            self._items.clear()
            self._by_path.clear()
            self.used = 0

    def __len__(self):
        return len(self._items)

    def stats(self):
        return {'entries': len(self._items), 'used_MB': self.used / _MB,
                'budget_MB': self.budget / _MB, 'hits': self.hits,
                'misses': self.misses}
