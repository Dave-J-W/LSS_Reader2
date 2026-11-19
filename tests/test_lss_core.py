"""The GUI-free core: fast cached image reading."""
import glob
import os

import numpy as np
import pytest
from PIL import Image

import synth
from lss_core import cache as cachemod
from lss_core.images import read_pilatus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _old_read(path):
    """The reader's former code, kept here as the reference."""
    im = Image.open(path)
    a = np.array(im.transpose(Image.ROTATE_270).getdata())
    a.shape = (im.size[0], im.size[1])
    return a


def _sample_images():
    files = []
    for pattern in ('sample_data/NX_school/*/pilatus/*.tif',
                    'sample_data/bu/*/pilatus/*.tif',
                    'sample_data/bu/*/pilatus1m/*.tif'):
        found = sorted(glob.glob(os.path.join(ROOT, pattern)))
        files += found[::max(1, len(found) // 25)]   # a spread of each set
    return files


@pytest.mark.slow
@pytest.mark.parametrize('path', _sample_images(),
                         ids=lambda p: os.path.basename(p))
def test_fast_reader_is_bit_identical_on_real_images(path):
    a, b = _old_read(path), read_pilatus(path, cache=False)
    assert a.shape == b.shape and a.dtype == b.dtype
    assert np.array_equal(a, b)


@pytest.mark.parametrize('dtype', [np.int32, np.float32])
def test_fast_reader_is_bit_identical_on_synthetic_images(dtype, tmp_path):
    rng = np.random.default_rng(3)
    a = rng.integers(0, 10 ** 6, size=(synth.PIL_W, synth.PIL_H)).astype(dtype)
    path = str(tmp_path / 'x.tif')
    Image.fromarray(np.ascontiguousarray(np.rot90(a, 1))).save(path)
    old, new = _old_read(path), read_pilatus(path, cache=False)
    assert old.dtype == new.dtype and np.array_equal(old, new)
    assert np.array_equal(new, a)


def test_cache_serves_repeat_reads_without_opening_the_file(tmp_path, monkeypatch):
    path = synth.write_pilatus_tif(str(tmp_path / 'a.tif'), synth.pilatus_image(peak=(9, 9)))
    c = cachemod.MemoryCache(budget_bytes=10 ** 8)
    opens = []
    real = Image.open
    monkeypatch.setattr(Image, 'open', lambda *a, **k: (opens.append(1), real(*a, **k))[1])
    import lss_core.images as images
    monkeypatch.setattr(images, 'CACHE', c)
    first = read_pilatus(path)
    again = read_pilatus(path)
    assert again is first and len(opens) == 1
    assert c.hits == 1 and c.misses == 1
    assert not first.flags.writeable


def test_cache_rereads_a_file_that_changed(tmp_path, monkeypatch):
    import lss_core.images as images
    monkeypatch.setattr(images, 'CACHE', cachemod.MemoryCache(budget_bytes=10 ** 8))
    path = str(tmp_path / 'a.tif')
    synth.write_pilatus_tif(path, synth.pilatus_image(background=1))
    assert read_pilatus(path)[0, 0] == 1
    os.utime(path, ns=(1, 1))                         # old timestamp
    synth.write_pilatus_tif(path, synth.pilatus_image(background=7))
    assert read_pilatus(path)[0, 0] == 7
    assert len(images.CACHE) == 1                     # the old entry was dropped


def test_cache_budget_evicts_least_recently_used():
    c = cachemod.MemoryCache(budget_bytes=250)
    import tempfile
    d = tempfile.mkdtemp()
    paths = []
    for i in range(4):
        p = os.path.join(d, str(i))
        open(p, 'w').write(str(i))
        paths.append(p)
    load = lambda p: open(p).read()
    for p in paths[:2]:
        c.get_or_load(p, load, lambda v: 100)
    c.get_or_load(paths[0], load, lambda v: 100)     # 0 is now most recent
    c.get_or_load(paths[2], load, lambda v: 100)     # evicts 1
    keys = [k[0] for k in c._items]
    assert keys == [paths[0], paths[2]] and c.used == 200
    c.get_or_load(paths[3], load, lambda v: 1000)    # larger than the budget: not kept
    assert len(c) == 2


def test_budget_from_environment(monkeypatch):
    monkeypatch.setenv(cachemod.ENV_BUDGET, '64')
    assert cachemod.MemoryCache().budget == 64 * 1024 * 1024
    monkeypatch.setenv(cachemod.ENV_BUDGET, '0')
    assert cachemod.MemoryCache().budget == 0
    monkeypatch.delenv(cachemod.ENV_BUDGET)
    b = cachemod.MemoryCache().budget
    assert 256 * 1024 * 1024 <= b <= 4096 * 1024 * 1024


# ---- SPEC and MCA readers without eval: identical results -------------------

import importlib.util  # noqa: E402

from lss_core.numbers import spec_number  # noqa: E402


def _legacy(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, 'tests', 'legacy', name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('token', ['0', '-3', '+7', '12.5', '-0.5', '.5', '5.',
                                   '1e3', '1.2E-05', '-4.5e+2', '2.84495e-15'])
def test_spec_number_matches_eval(token):
    a, b = spec_number(token), eval(token)
    assert type(a) is type(b) and a == b


@pytest.mark.parametrize('token', ['abc', 'nan', 'inf', '1,2', '', '__import__("os")', '1-2'])
def test_spec_number_refuses_non_numbers(token):
    with pytest.raises(ValueError):
        spec_number(token)


def _same(a, b):
    """Deep equality with types (an int must stay an int)."""
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, np.ndarray):
        return isinstance(b, np.ndarray) and a.dtype == b.dtype and np.array_equal(a, b, equal_nan=True)
    return type(a) is type(b) and (a == b or (a != a and b != b))


def _mca_files():
    return sorted(glob.glob(os.path.join(ROOT, 'sample_data', '*', '*', 'vortex', '*_mca')))


def _spec_files():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'sample_data', '*', '*', '*'))):
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                if f.read(2) == b'#F':
                    out.append(path)
    return out


@pytest.mark.slow
@pytest.mark.parametrize('path', _mca_files(), ids=os.path.basename)
def test_mca_reader_identical_to_eval_version(path):
    import mca_routines
    old, new = _legacy('mca_routines_eval').mcaread(path), mca_routines.mcaread(path)
    # deliberate additions (2026-11-19): 'Point' (per-point files) and 'Channel' (#@CHANNEL,
    # multi-element detectors), which the old reader did not read
    par = {}
    for k, p in new.Par.items():
        p = dict(p)
        for key in ('Point', 'Channel'):
            if key in p:
                assert key not in old.Par[k]
                del p[key]
        par[k] = p
    assert _same(old.Data, new.Data) and _same(old.Par, par)


@pytest.mark.slow
@pytest.mark.parametrize('path', _spec_files(), ids=lambda p: os.path.relpath(p, ROOT))
def test_spec_reader_identical_to_eval_version(path, qapp):
    import spec_routines
    old = _legacy('spec_routines_eval').specread(path, data={}, par={})
    new = spec_routines.specread(path)
    # deliberate additions since the eval version, each undone below. F50/D24 (2026-11-17):
    # a scan without #A gets the last #A above it, marked by 'AbsorberFrom',
    # and Data keeps that last #A for refreshes. Only those, and only on
    # scans the old reader left without an absorber.
    # Also (F52): the Monc gain from '#M Monc Gain', read or inherited the
    # same way; the old reader did not read #M at all.
    data = dict(new.Data)
    assert 'LastAbsorber' in data and 'LastMoncGain' in data
    data.pop('LastAbsorber')
    data.pop('LastMoncGain')
    par = {}
    for num, p in new.Par.items():
        p = dict(p)
        if 'AbsorberFrom' in p:
            assert 'Absorber' not in old.Par[num]
            assert p['Absorber'] == new.Par[p['AbsorberFrom']]['Absorber']
            del p['Absorber'], p['AbsorberFrom']
        if 'MoncGainFrom' in p:
            assert p['MoncGainText'] == new.Par[p['MoncGainFrom']]['MoncGainText']
            del p['MoncGainFrom']
        for k in ('MoncGain', 'MoncGainText'):
            assert k not in old.Par[num]
            p.pop(k, None)
        # D42 (2026-11-19): the #A text is kept, and an unreadable #A is unknown
        # (None) where the old reader set 63
        if 'AbsorberText' in p:
            assert 'AbsorberText' not in old.Par[num] and isinstance(p['AbsorberText'], str)
            if p['Absorber'] is None:
                assert old.Par[num]['Absorber'] == 63
                p['Absorber'] = 63
            del p['AbsorberText']
        # F39 (2026-11-19): SPEC's "Scan aborted after k points" and the series
        # lines, which the old reader did not read
        # F37 (2026-11-19): the scan's #D, the file header (#E, #D) above it and
        # #U SeriesT0, for the per-point times (lss_core.timing)
        for k in ('AbortedAfter', 'Series', 'SeriesMacro', 'SeriesEnd', 'Date', 'FileEpoch', 'FileDate', 'SeriesT0'):
            if k in p:
                assert k not in old.Par[num]
                del p[k]
        par[num] = p
    assert _same(old.Data, data) and _same(old.Par, par)


def test_mca_reader_is_fast():
    import time
    import mca_routines
    files = sorted(_mca_files(), key=os.path.getsize)
    if not files:
        pytest.skip('no MCA sample files')
    t = time.perf_counter()
    m = mca_routines.mcaread(files[-1])
    per_spectrum = (time.perf_counter() - t) / m.Data['NumOfScans']
    assert per_spectrum < 5e-3          # was ~16 ms with eval


# ---- disk cache (F8) ---------------------------------------------------------

def test_disk_cache_serves_frames_after_a_restart(tmp_path, monkeypatch):
    import lss_core.images as images
    from lss_core import diskcache
    monkeypatch.setenv('LSS_READER_DISK_CACHE', str(tmp_path / 'cache'))
    monkeypatch.setenv('LSS_READER_DISK_CACHE_ALL', '1')
    path = synth.write_pilatus_tif(str(tmp_path / 'a.tif'), synth.pilatus_image(peak=(9, 9)))
    monkeypatch.setattr(images, 'CACHE', cachemod.MemoryCache(budget_bytes=10 ** 8))
    first = read_pilatus(path)
    assert len(glob.glob(str(tmp_path / 'cache' / '*' / '*.npy'))) == 1
    # "restart": empty memory cache; the TIFF must not be opened again
    monkeypatch.setattr(images, 'CACHE', cachemod.MemoryCache(budget_bytes=10 ** 8))
    monkeypatch.setattr(Image, 'open', lambda *a, **k: (_ for _ in ()).throw(AssertionError('opened')))
    again = read_pilatus(path)
    assert again.dtype == first.dtype and np.array_equal(again, first)


def test_disk_cache_rereads_changed_files_and_survives_damage(tmp_path, monkeypatch):
    import lss_core.images as images
    monkeypatch.setenv('LSS_READER_DISK_CACHE', str(tmp_path / 'cache'))
    monkeypatch.setenv('LSS_READER_DISK_CACHE_ALL', '1')
    monkeypatch.setattr(images, 'CACHE', cachemod.MemoryCache(budget_bytes=0))
    path = str(tmp_path / 'a.tif')
    synth.write_pilatus_tif(path, synth.pilatus_image(background=1))
    assert read_pilatus(path)[0, 0] == 1
    os.utime(path, ns=(1, 1))
    synth.write_pilatus_tif(path, synth.pilatus_image(background=7))
    assert read_pilatus(path)[0, 0] == 7
    for entry in glob.glob(str(tmp_path / 'cache' / '*' / '*.npy')):
        open(entry, 'wb').write(b'damaged')
    assert read_pilatus(path)[0, 0] == 7            # falls back to the file


def test_disk_cache_size_limit_and_local_files(tmp_path, monkeypatch):
    import lss_core.images as images
    monkeypatch.setenv('LSS_READER_DISK_CACHE', str(tmp_path / 'cache'))
    monkeypatch.setattr(images, 'CACHE', cachemod.MemoryCache(budget_bytes=0))
    path = synth.write_pilatus_tif(str(tmp_path / 'a.tif'), synth.pilatus_image())
    read_pilatus(path)                               # same file system: not cached
    assert glob.glob(str(tmp_path / 'cache' / '*' / '*.npy')) == []
    monkeypatch.setenv('LSS_READER_DISK_CACHE_ALL', '1')
    monkeypatch.setenv('LSS_READER_DISK_CACHE_MB', '1')       # one 100K frame is ~0.76 MB
    for i in range(3):
        p = synth.write_pilatus_tif(str(tmp_path / ('f%d.tif' % i)), synth.pilatus_image(background=i))
        read_pilatus(p)
    assert len(glob.glob(str(tmp_path / 'cache' / '*' / '*.npy'))) == 1
    monkeypatch.setenv('LSS_READER_DISK_CACHE', 'off')
    assert read_pilatus(p)[0, 0] == 2
