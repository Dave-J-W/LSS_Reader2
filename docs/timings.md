# Timings

Written by `pytest -m bench` (`tests/test_bench_selection.py`).
Local disk, offscreen Qt, x86_64, Python 3.13.18. Single run; expect
run-to-run variation of 10-20 %. Production reads from a
network drive, which these numbers do not include.

"Files" and "MB" count data files opened during the step and
their total size; they do not depend on disk speed.

| Step | Seconds | Files | MB | Note |
|---|---|---|---|---|
| open SPEC file (15 scans) | 0.44 | 2 | 0.1 |  |
| select one scan (27 frames listed) | 0.27 | 0 | 0.0 |  |
| select 1 frame (read + show) | 0.62 | 1 | 0.4 |  |
| select the same frame again | 0.32 | 0 | 0.0 | served from the memory cache |
| select all 27 frames of the scan | 1.14 | 26 | 9.9 | only the first 10 are drawn |
| add the same 27 frames one click at a time | 26.03 | 0 | 0.0 | frames come from the cache; every click redraws all selected frames |
| select 4 scans (96 frames listed) | 0.15 | 0 | 0.0 |  |
| select all 96 frames | 1.55 | 69 | 26.3 |  |
| reflectivity patch: integrate 96 frames | 0.25 | 0 | 0.0 |  |
| reflectivity patch: accept 3 overlaps | 0.26 | 0 | 0.0 |  |
| open SPEC file (142 scans) | 1.20 | 2 | 1.4 |  |
| select 6 fluorescence scans (MCA files read) | 0.19 | 6 | 0.1 |  |
| select all 6 spectra | 0.54 | 0 | 0.0 |  |

## Where the time goes: selecting 96 Pilatus 100K frames

Own time by where the code lives, from a profiled repeat of
the step. The profiler slows everything, so only the shares
are meaningful.

| Part | Share |
|---|---|
| matplotlib (layout, text, drawing) | 82 % |
| built-ins and everything else | 12 % |
| numpy and scipy | 5 % |
| image reader (TwoDDetector.py) | 0 % |
| window code (mainwindow.py) | 0 % |

## Where the time goes: selecting 6 MCA spectra

Own time by where the code lives, from a profiled repeat of
the step. The profiler slows everything, so only the shares
are meaningful.

| Part | Share |
|---|---|
| matplotlib (layout, text, drawing) | 77 % |
| numpy and scipy | 14 % |
| built-ins and everything else | 9 % |
| window code (mainwindow.py) | 0 % |
