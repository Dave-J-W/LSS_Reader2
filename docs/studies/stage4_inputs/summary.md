# Stage 4 inputs: which of the requested formats exist locally (DATA_NEEDS row 6)

Non-cloud data agent, 2026-11-24. Answers `docs/DATA_NEEDS.md` row 6 (TODO input 3) as an inventory
only: for each requested input, whether the owner's private data on this computer hold one, and what it
would unblock. **Read** from the headers of every SPEC file in the private copy (8255 scans, 2025-12 to
2026-10), the TIFF headers of one frame per imaging scan (6702 scans), and the document files of the one
bluesky data folder found. No file was copied into the repository; file names and scan numbers stay in
the private inventory (`sample_data/private/gid/inventory/`; generators `scripts/scan_table.py`,
`frame_shapes.py`).

## Answer

| Input | Exists? | What was found | What it would unblock |
|---|---|---|---|
| Full two-module Pilatus 200K frame (F63, D43) | **No** | Every 200K frame in all 21 run folders is one module: TIFF 487 × 195 pixels, 32-bit (6506 scans sampled, one frame each; `frame_shapes.csv`). The second module was never saved in this period. | Nothing yet: the second module's geometry (F63) still needs a frame taken on purpose at the beamline |
| New-format fluorescence/GID SPEC file (F28) | **Not identified** | All files share one header layout (`#S #D #T #G0–3 #Q #P0–9 #W #M #A #B0 #B1 #N #L`; `#B5` only with the 1M; `#V` with spectra), besides `#C` comments and the file header. No other scan header lines occur. The one newer layout is the per-point MCA files beside the SPEC file (`vortex/`, one block per point; answered under row 2). GID with fluorescence exists in one beamtime as alternating scans at a fixed Det_Th: a Vortex scan, then a Pilatus scan, each its own SPEC scan. | If "new format" means the per-point MCA files: already read (F35 first part, D49). If it means something else, the owner must say what; no candidate file was found |
| HDF5 / bluesky file (F29) | **Yes, but not surface scattering** | One folder at the other station holds a bluesky commissioning run: 307 runs saved as JSONL event documents (start, descriptor, event pages, stop; bluesky 1.15, ophyd 1.11), mostly `rel_scan` of beamline motors against an ion chamber and beam-position monitors, and 16 `count` runs of a Dante MCA. The MCA writes its own HDF5 files (100 files, about 45 kB each); the events record their path, name and number as fields, not as `resource`/`datum` documents. No area detector, no liquid-surface scan. | The document layer of an F29 reader (start/descriptor/event_page/stop, plan names, motors, detectors, scan ids) and an MCA-in-HDF5 reader. Not the Pilatus or SPEC-equivalent layout F29 needs for surface data: a surface measurement saved by bluesky is still wanted |
| Pilatus and Vortex in one scan (F53) | **Yes (two usable scans)** | 3 scans in two beamtimes have both `#V` and `#B0`. Two (horizontal sample-position scans, 17 and 15 points, Det_Th 0, sample far below the beam) have a frame per point and the per-point MCA file; the third has frames but no spectra file. | Pins the format of a scan holding both detectors (F53): which header line wins today, both detectors in the Sources layer, the two tabs. These are alignment-type scans, not a science measurement |
| Pilatus 1M geometry (F38) | **Yes** | Two beamtimes (and a partial copy of one without frames) with Pilatus 1M frames, TIFF 1043 × 981 pixels, 32-bit, 196 scans with frames (reflectivity, height, alignment scans). Each scan's header has `#B5 x y D 0`: the pixel where the reflected beam should land and the sample–detector distance (two installations: 2654.6 mm, then 2038.7 mm, the value the beamline notes give). The detector's stage motors appear in `#P` (the `CCD_X`/`CCD_Y` names in the first installation's files, `PD1M_X`/`PD1M_Z` in the second). In one beamtime the stage height takes 29 values over the reflectivity scans: the "tracked" mode. It is logged once per scan, at its start, not per point. | F38's two modes: the fixed beam pixel and distance from `#B5`; for tracked scans, the per-point detector position must come from the tracking rule or from the frames, since the file does not log it per point. Also the 30 keV 1M frames the reader cannot read yet (found by PR #68) |

## Notes

- One more 1M frame sits in a folder of its own, outside any run (a test frame, same 1043 × 981 size).
- 87 imaging scans in 15 run folders have no frame on disk (counted, not investigated; one copy folder
  accounts for 52).
- ME7 notes (F35) were not part of this inventory (mostly answered by D48, D49).

## Open questions for the owner

1. F28: what is new in the "new fluorescence & GID SPEC file"? Nothing in the private files differs in
   header layout; if it is a file not yet copied here, it is still needed.
2. F29: is a surface measurement saved by bluesky expected soon (the other station's commissioning has
   only beamline scans)?
3. F63: would a beamtime save one full two-module 200K frame on purpose?

## Files

| File | What |
|---|---|
| `frame_shapes.csv` | TIFF size per detector folder, with how many scans and run folders were sampled |
