# Scope and plan

Written 2026-11-16, when the owner supplied "the rest of the feature set".
It orders everything in `FEATURE_REQUESTS.md` (R1–R6, D1–D16, F1–F48) into
stages. Implementation started on the owner's word (2026-11-17): Stages
0–2 are done, Stages 3 and 6 are under way; `TODO.md` holds the status.

## What must stay true throughout

1. **Numbers do not change by accident.** The quick checks, the real-data
   benchmarks and the byte-level legacy export fixtures pass after every
   step (R1, R5). A changed number is a decision, recorded with before and
   after values.
2. **The window never closes on its own** (R3, F10). The crash inventory
   only shrinks.
3. **The SPEC file is never written** (F14).
4. **Old behaviour stays available where a result changes**: "legacy" modes
   for the export (F24a), the error model (F26), and GID patching (F23).

## Target shape of the program

Today one window class holds everything. Every stage below moves toward
four layers, each usable and testable without the one above it:

| Layer | Holds | Enables |
|---|---|---|
| **Sources** | Reading SPEC (and later HDF5/bluesky), images, MCA files into plain data objects: scans, points, frames, monitors, geometry, timestamps. Detector descriptions (100K, 200K, 1M; Vortex 1/4/7 elements). Caches. | F1–F9, F17, F27–F29, F33–F35, F37, F39 |
| **Reduction** | Pure functions on those objects: normalisation and errors, ROI and window sums, cuts, stitching with covariance, GID/GISAXS maps, burn tests, fits. No Qt. | F20–F26, F31, F36, F40–F45 |
| **Session state** | One explicit, serialisable record of what is loaded and every parameter and interactive decision (dropped points as masks). Undo/redo. Saved beside the SPEC file. | F13–F16, D1–D3 |
| **Window** | Widgets that edit the session state and draw results. One central error handler and log. | F10–F12, R4, F35's config tab |

Scriptable reduction (F31) is then the Reduction layer's public API, and
export formats (F24, F25, F30) are writers on its outputs.

## Stages

Each stage ends with the checks green and something the user can see.

### Stage 0 — Safety net (small; first by agreement, D4)
- Process-wide exception handler: a failing action is logged and the window
  stays open (F10). Durable per-session log, flushed per record, with
  `faulthandler` for hard faults (F12). Log beside the SPEC file with a
  local fallback (D3).
- Routine message boxes become status-bar/log messages; the fluorescence
  "not regular Spec scan" box is retired (F11, D15).
- *Shows:* pressing any of the 420 crashing control/state combinations no
  longer closes the program. *Check:* the abort test starts passing.

### Stage 1 — Repair what is plainly broken (no design decisions)
- Defects of `ASSESSMENT.md` §4 that are typos or Python 2/NumPy 2 leftovers
  (2–7, D14 systematic scan-list formatting, `map` uses, shared default
  dictionaries), each with its expected-failure check flipped.
- Empty the crash inventory handler by handler (guards for "nothing loaded",
  "nothing selected"); graceful opening of non-SPEC files, repeated scan
  numbers, aborted scans, missing folders (F27).
- Remove the Bruker/CCD code paths and controls (D8, F38), keeping notes on
  its moving-table geometry for the 1M.
- Replace `interp2d` with an equivalent that reproduces the SciPy 1.13
  reference (defect 1), so GID patching works again exactly as before.
- Qz² export fix (F24b), the only permitted change to legacy bytes.
- *Shows:* GID patching, g_l2/g_l3 with typed centres, peak-fit save work.

### Stage 2 — Pull the readers and the reduction out of the window
- Sources and Reduction layers extracted function by function behind the
  existing tests; the window calls them. No behaviour change.
- Stop re-reading on every selection change (D5): frames held in a RAM cache
  sized to the host (F9), optional disk cache for network drives (F8),
  keyed by path, size and modification time. Faster image and MCA parsing
  (F6, F7).
- Reduction callable from a script (F31) with a small documented API; a
  console pane that prints each API call the GUI makes (F48).
- Packaged Windows and macOS builds once resources load relative to the
  program (F46).
- *Shows:* selection is fast; a notebook can reproduce a `_ref.txt`.
  *Check:* timing table improves; legacy bytes unchanged.

### Stage 3 — State, persistence, live data
- Session state object; per-SPEC config file with atomic writes, read-only
  second instance and yellow indicator (F13–F16, D1–D3); dropped points as
  masks with undo/redo.
- Live refresh: watch SPEC file and data folders by polling, append without
  discarding what is loaded, keep selections, update plots and reduced
  reflectivity (F1–F5); "Scan i of N" grouping and aborted macros (F39);
  per-point times (F37).
- *Needs from the beamline:* the "Scan i of N" header syntax.

### Stage 4 — Detectors and inputs
- Detector descriptions: 100K, 200K, 1M (F17–F19, F33) with gaps and masks
  (D11); 1M tracked and fixed geometries (F38).
- Fluorescence detector configuration tab; 1/4/7-element handling; grouped
  spectra per point; element selection for XFNTR and EXAFS (F34–F36); the
  `#V` flag once SPEC writes it.
- New fluorescence & GID SPEC file (F28); HDF5/bluesky input (F29).
- Simultaneous Pilatus and fluorescence on the same scans (F53): a scan
  holds both detectors; Pilatus and Vortex selected and reduced side by
  side (tabs "Pilatus" and "Vortex"). Needs a sample file with both.
- *Needs from the owner:* 200K data, a new-format SPEC file, an HDF5 file,
  ME7 examples, the 1M geometry conventions.

### Stage 5 — Reflectivity export and uncertainty
- Two-chain stitching with covariance sidecar per the hand-off (F24, F24a,
  F24c); same-absorber scans share a factor (F41, to be reconciled with the
  hand-off's W and Σ); stitch-factor interpolation bias removed in the
  corrected chain (D13).
- Uncertainty model: monitor term once per frame with a measured model, not
  Poisson on `Monc`; dark-rate question (F26; `reports/monitor_noise.md`).
  The measurement of `Monc`'s own noise is not needed: the Student t model
  is good enough (owner, 2026-11-19, D44).
- Per-second option (F20); photons-in estimate when SPEC has it (F21).
- Q_z offset from the reflection position using sh-scan images (F42).
- ORSO and HDF5 export (F25, F30).
- *Needs:* `lss_reference.py` and `covariance_core.py` from XModJointFit.

### Stage 6 — Sub-projects with their own scoping
- GID patching: flexible overlaps, selectable algorithms, pinhole-geometry
  correction from the IDL code, multiple exposures with cosmic-ray
  rejection, a tool to design a patched scan (F23, F32, F40, F45).
- Fitting improvements inside the reader (F22); fluorescence line markers,
  escape peaks and element identification using XrayDB/Larch (F47).
- Half-cut scans for beam size (F43), when data exists.
- GUI reorganisation (R4), informed by everything above.

## Order and dependencies

Stages 0 and 1 need nothing from anyone and remove the daily pain. Stage 2
is the hinge: Stages 3–6 all build on it. Stages 3, 4 and 5 are largely
independent of one another after Stage 2 and can be reordered to match
beam-time needs. Within Stage 5, the covariance export depends on the merge
logic being out of the dialogs (Stage 2) and on the masks (Stage 3).

## Open questions that block specific items

Updated 2026-11-19 (documentation audit). Answered since: F26 (`Monc` noise
not needed, D44; dark rate 50 Hz, D41); F23/F45 (IDL code received, pinhole
GID built, D36, D40); F22 (requirements F22a; scoping later); P7 (kept);
P13 (fixed); 9-ID-C (D17); F22 (fitting, built 2026-11-21). Still open: the rows for F24/F41, F24 tests 5–6,
F28/F29/F33–F36 sample files, F39/F34 syntax (proposal `handoff_out/05`),
P5 and P6. Requests after F48 are placed as follows: F49, F50, F52, F54–F58
(absorbers, foils, gain, per photon, preferences) built alongside Stages
1–2 (F49 at 30 keV, the Cu foil, still open); F51 (σ_scan per scan) declined,
D26; F53 (Pilatus + fluorescence in one scan) Stage 4; F59 (Q cuts) Stage 6 GUI;
F60 (contextual reduction) with F39 in Stage 3; F61–F62 (GID worksheet,
Qz joins) Stage 6 GID, built; F63 (second 200K module) Stage 4; F65 (XFNTR
merge) built without the edge check, edge estimator backlog. (F64 was not
assigned.)

| Item | Question | Who |
|---|---|---|
| F24, F41 | How do same-absorber scans enter W and Σ? | hand-off author |
| F24 tests 5–6 | XModJointFit files | owner |
| F28, F29, F33–F36 | Sample files and conventions | owner |
| F39, F34 | Exact SPEC header syntax for "Scan i of N" and the `#V` flag | beamline |
| P5, P6 | Questions in `PHYSICS_ISSUES.md` | owner |

## What is not in scope

Fitting of structural models (xmodfit does that). Changes to SPEC macros:
the project proposes them (beamline to-do in `TODO.md`, hand-off 05) and
adapts to what SPEC writes; it does not make them.
