# Timings

Written by `pytest -m bench` (`tests/test_bench_selection.py`).
Local disk, offscreen Qt, x86_64, Python 3.13.18. Single run; expect
run-to-run variation of 10-20 %. Production reads from a
network drive, which these numbers do not include.

| Step | Seconds | Note |
|---|---|---|
| open SPEC file (15 scans) | 0.29 |  |
| select one scan (27 frames listed) | 0.17 |  |
| select 1 frame (read + show) | 0.59 |  |
| select the same frame again | 0.24 | nothing is cached |
| select all 27 frames of the scan | 0.86 | only the first 10 are drawn |
| add the same 27 frames one click at a time | 21.19 | every click re-reads all selected frames |
| select 4 scans (96 frames listed) | 0.11 |  |
| select all 96 frames | 2.05 |  |
| reflectivity patch: integrate 96 frames | 0.19 |  |
| reflectivity patch: accept 3 overlaps | 0.19 |  |
| open SPEC file (142 scans) | 0.98 |  |
| select 6 fluorescence scans (MCA files read) | 0.16 |  |
| select all 6 spectra | 0.58 |  |

## Where the time goes: selecting 96 Pilatus 100K frames

Own time by where the code lives, from a profiled repeat of
the step. The profiler slows everything, so only the shares
are meaningful.

| Part | Share |
|---|---|
| matplotlib (layout, text, drawing) | 77 % |
| numpy and scipy | 11 % |
| built-ins and everything else | 10 % |
| PIL | 1 % |
| image reader (TwoDDetector.py) | 0 % |
| window code (mainwindow.py) | 0 % |

## Where the time goes: selecting 6 MCA spectra

Own time by where the code lives, from a profiled repeat of
the step. The profiler slows everything, so only the shares
are meaningful.

| Part | Share |
|---|---|
| matplotlib (layout, text, drawing) | 76 % |
| numpy and scipy | 15 % |
| built-ins and everything else | 9 % |
| window code (mainwindow.py) | 0 % |
