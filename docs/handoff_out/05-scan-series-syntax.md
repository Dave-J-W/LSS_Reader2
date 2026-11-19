# Proposal: "scan i of N" lines in SPEC headers (F39)

For: the owner and whoever edits the 15-ID-C SPEC macros. From: the
LSS_Reader2 project, 2026-11-19. Status: **proposal**, nothing on the
beamline depends on it yet. The reader already parses the syntax below
(`spec_routines.py`, `lss_core/series.py`) and falls back to guessing
(`series.infer`) for files without it.

## What the reader needs, and why

| Field | Needed for | Without it |
|---|---|---|
| **id**: one value per macro run | Which scans belong together; two runs of the same macro on one sample are two series; a resumed run can rejoin its series | Guessing from consecutive commands and Qz ranges (works on the NX file, fails when runs are interleaved or repeated) |
| **i** and **n**: this is data scan i of n planned | Progress ("4 of 7"), when to reduce automatically, knowing that scans are *missing* rather than not planned | n is unknown: a cancelled series looks complete |
| **kind**: reflectivity, gid, gisaxs, xfntr, … | Choosing the reduction without the user (F60, contextual reduction) | Guessing from the command (`hklscan` → reflectivity, `ascan dth` with Pilatus → GID) |
| **role**: data (default), align, direct, background, check | Leaving alignment and check scans out of the reduction; finding the direct-beam scan | Alignment scans are guessed (motor sh/oh/ih/chi/th over a range) |
| macro command as typed (first scan only) | Provenance; re-running | — |
| optional: **level** (GID Qz level), **group** (several series on one sample) | GID levels are already found from Qz; group is for a later "sample" view | — |

"reflectivity, scan i of N" alone is **not quite enough**: without an id,
the reader cannot tell two runs of the same macro apart, and cannot join a
resumed run to the one it continues. Kind and role are what make
automatic reduction (F60) possible. Everything else is in the scan headers
already (Qz, absorbers, slits, detector).

## Proposed syntax

One line in every scan header the macro writes, `key=value` words so that
fields can be added later without breaking readers:

    #U Series id=<id> i=<i> n=<N> kind=<kind> [role=<role>] [level=<k>] [group=<g>]

and on the first scan only:

    #U SeriesMacro <the macro command as typed>
    #U SeriesT0 <Unix s>          (owner, 2026-11-19: taken before any motor moves)

and, optionally, when the macro ends or is aborted (see below):

    #C Series id=<id> end status=completed
    #C Series id=<id> end status=aborted after=<i>

- `id`: no spaces; unique in the file. Suggested: the first scan's number
  and the start time, `id=102-1763565132` (scan 102, Unix seconds).
- `i` counts **data** scans from 1; `n` is the number planned. Alignment or
  check scans carry the id with `role=align` (or check, direct,
  background) and **no i**, so a macro can realign as often as it needs to.
- `kind`: one of reflectivity, gid, gisaxs, xfntr, direct_beam,
  alignment, burn, energy, other.
- `#U` is SPEC's conventional "user" header line; nothing in the 15-ID-C
  files uses it today (checked on the NX school and the owner's files), and
  readers that do not know it skip it.

### Examples

A reflectivity run of four segments with a realignment before the third:

    #S 6  hklscan  0 0  0 0  0.0175 0.04  18 2
    #U Series id=6-1763565132 i=1 n=4 kind=reflectivity
    #U SeriesMacro xr_ref 0.0175 0.45 sample3
    ...
    #S 8  a2scan  sh -2.2785 -2.1185  oh -1.37117 -1.05117  20 1
    #U Series id=6-1763565132 kind=reflectivity role=align
    ...
    #S 9  hklscan  0 0  0 0  0.09 0.19  20 2
    #U Series id=6-1763565132 i=3 n=4 kind=reflectivity

A GID run at two Qz levels, the second cancelled by the user:

    #S 11  ascan  dth 14 18  40 7
    #U Series id=11-1763566001 i=1 n=2 kind=gid level=1
    #S 12  ascan  dth 14 18  40 7
    #U Series id=11-1763566001 i=2 n=2 kind=gid level=2
    ... 4 points ...
    #C Wed Sep 23 11:12:13 2026.  Scan aborted after 4 points.
    #C Series id=11-1763566001 end status=aborted after=2

## When the user cancels later scans

SPEC already writes `#C <date>.  Scan aborted after k points.` into a scan
that is stopped. What is lost today is the *rest of the plan*: the scans
the macro never wrote. The reader handles it in this order (implemented in
`lss_core.series.group`):

| Situation | Status shown | What the reader does |
|---|---|---|
| all n data scans present, none short | complete | reduce as usual |
| all present, one stopped early (fewer points than its command asked; SPEC's abort comment) | partial | reduce what was measured; say which scan is short |
| scans missing, the macro wrote `status=aborted` | aborted | reduce the scans present; say "aborted after scan i of n" |
| scans missing, a scan of another series (or none) follows | aborted | same; the next scan proves the macro ended |
| scans missing, a data scan is short and nothing follows | aborted | same |
| scans missing, it is the last series, the file is still growing, nothing short | in progress | live mode: reduce on each new scan, wait for the rest |
| scans missing, the file stopped growing | aborted | as above; "the file is not growing" |
| the same id appears again later (macro resumed) | joins the series | the missing i are filled; status recomputed |

A user stopping the scan at its last point gets "aborted after 21 points"
for a 21-point scan (NX scan 13): that scan is treated as complete.

The end line is optional because the reader can infer the end, but it
removes the guess for the last series of a file that is no longer
growing (was it stopped, or is the next scan just slow?). In SPEC it can be
written from the macro's cleanup hook, which runs when the user presses
^C. The hook names to check in the SPEC manual (certif.com, "spec_help"
on scans and macros): a per-scan header hook (`Fheader`, already how
15-ID-C writes `#A`, `#B0`, `#W`) and `cleanup_once` for the abort. This
proposal has not been tried on SPEC.

## Without the line (files written until then)

`lss_core.series.infer` groups what it can and marks it *inferred*:
consecutive `hklscan` L scans whose Qz ranges move up and overlap
(reflectivity), consecutive `ascan dth` Pilatus scans (GID), and scans of
sh/oh/ih/chi/th over a range between them (alignment). n is unknown, so a
cancelled run is "complete" unless a scan is short. On the NX school file
it finds reflectivity 3, reflectivity 6–9 (alignment 4, 5, 10), and GID
11–12 "partial: scan 12 aborted after 4 of 41 points"; the burn test
(scans 14–15, `ascan ih x x`, a fixed position) is not taken for alignment.

## Questions for the owner

1. The id: first scan number plus start time (suggested), or a counter the
   macros keep?
2. Do the macros realign conditionally (so that `n` cannot count alignment
   scans)? The proposal assumes yes.
3. Should a sample-level `group=` (e.g. reflectivity then GID on one
   sample) be written now, or later?
4. Which macros write series: reflectivity, GID, XFNTR (`getandsave_mca`
   loops), GISAXS, energy scans? XFNTR runs are many one-spectrum scans:
   `n` there is the number of Qz points.

## Added 2026-11-19 (owner): timestamps

New files carry `Tstart` and `Tend` columns in #L (Unix s, 0.01 s; counting
began, point written) instead of `Epoch`, and `#U SeriesT0 <Unix s>`, the
macro's start before any motor moves. Time since the macro started is
then Tstart − SeriesT0. The reader reads both, and the old `Epoch` files
(see `lss_core/timing.py`).

