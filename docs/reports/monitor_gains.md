# Monitor gains the reader cannot interpret

Generated 2026-11-17 by `python tests/tools/monitor_gains.py` (reads only;
run it again on other data). Owner, 2026-11-17: "make a list of the gains
you can't interpret, where they are, what they are, and then we'll sort
that out later."

The reader reads `#M Monc Gain <value> <unit>` (units pA/V, nA/V, uA/V,
mA/V, A/V; `lss_core/monitor.py`). A scan without `#M` takes the last one
above it in the file. Every entry below is treated as **unknown**: with the
"/ gain" option on, those scans get no gain factor and the Messages pane
warns. Nothing is guessed. The two right-hand columns give the readable
gain of the nearest scans, only as a hint for sorting them out.

Measured on every SPEC file under `sample_data/` (MCA data files excluded:
they carry no `#M` and take the SPEC scan's gain).

| File | Scan | Command | Line | Text | Scans without #M that inherit it | Last readable gain before | Next readable gain after |
|---|---|---|---|---|---|---|---|
| sample_data/bu/2026June/20260616 | 1 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 2 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 3 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 4 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 5 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 6 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 7 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 8 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 9 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 10 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 11 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026June/20260616 | 12 | getandsave_mca | — | `(no #M in or above the scan)` | — | — | S13: 10 uA/V |
| sample_data/bu/2026oct/20261019 | 1 | ascan | 44 | `#M Monc Gain (empty)` | — | — | S2: 200 nA/V |
| sample_data/bu/2026oct/20261019 | 7 | ascan | 257 | `#M Monc Gain 200` | — | S6: 200 nA/V | S8: 200 nA/V |
| sample_data/bu/2026oct/20261022 | 2 | a2scan | 86 | `#M Monc Gain (empty)` | — | S1: 1 uA/V | S3: 1 uA/V |

Three kinds:

1. **No `#M` in or above the scan** — bu/2026June/20260616 scans 1–12, all
   `getandsave_mca`, before the first scan that records a gain (scan 13).
   The macro writes no `#M` (beamline to-do in `TODO.md`).
2. **Empty value** (`#M Monc Gain` and nothing after it) —
   bu/2026oct/20261019 scan 1, bu/2026oct/20261022 scan 2.
3. **Value without a unit** (`#M Monc Gain 200`) — bu/2026oct/20261019
   scan 7; its neighbours record 200 nA/V.

The NX school file (public) has no problem lines.

## Owner, 2026-11-18

Another agent found the bu/2026oct gain lines malformed and no other SPEC
file like them (D33); 5 µA/V is the usual gain, on more than 90 % of runs
(D32). That covers kinds 2 and 3 (three entries). Kind 1 (bu/2026June/20260616
scans 1–12) is not a malformed line: those MCA scans come before the first
`#M` of the file. All stay unknown; nothing is guessed.

