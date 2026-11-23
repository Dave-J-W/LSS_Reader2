"""MCA files parsed once per file version (lss_core.mcafiles, 2026-11-23).

The window re-read every selected scan's MCA file on each change of the
scan selection: 20 files of 30 spectra took 0.38 s per click, and longer
over a network drive; from the memory cache, 8 ms."""
import os

import numpy as np

import synth
from lss_core import cache as cachemod
from lss_core import images, mcafiles
from mca_routines import mcaread


def _spectra(n, seed=0):
    rng = np.random.default_rng(seed)
    return [rng.poisson(50.0, size=256) for _ in range(n)]


def test_read_mca_gives_mcareads_result_once_per_file_version(tmp_path, monkeypatch):
    monkeypatch.setattr(images, 'CACHE', cachemod.MemoryCache(budget_bytes=10 ** 8))
    monkeypatch.setattr(mcafiles, 'CACHE', images.CACHE)
    path = str(tmp_path / 'sample_3_mca')
    synth.write_mca(path, _spectra(4))
    ref = mcaread(path)
    data, par = mcafiles.read_mca(path)
    assert data['NumOfScans'] == ref.Data['NumOfScans'] == 4
    assert all(data[j] == ref.Data[j] and par[j] == ref.Par[j] for j in range(4))
    data[0]['Vortex'][0] = -1                        # a caller's change does not reach the cache
    par[0]['Q'][2] = 99.0
    again, par2 = mcafiles.read_mca(path)
    assert again[0] == ref.Data[0] and par2[0] == ref.Par[0]
    assert images.CACHE.hits == 1 and images.CACHE.misses == 1
    synth.write_mca(path, _spectra(6, seed=1))       # the file changed: read again
    os.utime(path, ns=(os.stat(path).st_atime_ns, os.stat(path).st_mtime_ns + 10 ** 9))
    grown, _ = mcafiles.read_mca(path)
    assert grown['NumOfScans'] == 6 and images.CACHE.misses == 2


def test_the_cache_counts_the_lists_mca_spectra_are_held_in():
    assert mcafiles._nbytes([1] * 2048) > 2048 * 30
    assert mcafiles._nbytes({0: {'Vortex': [0] * 100}, 'NumOfScans': 1}) > 100 * 30
