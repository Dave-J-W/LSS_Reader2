# IDL reference code (pinhole and GID)

Received from the owner on 2026-11-18: the files from Mati's stash whose
contents mention "pinhole". Stored unchanged, as the reference for the
pinhole-geometry correction and GID patching (F45, F23, D36). They are
not run by the reader; routines they call (PD_GID_READ, RANGE_PROC, ...)
are not included.

| File | Version | Purpose (from its header) |
|---|---|---|
| `pd_view.pro` | 8.475 | Displays frames from a single area-detector scan (has a `pinhole` keyword) |
| `pd_gid.pro` | 8.44 | Readout and display of PD GID data; horizontal patching of several scans |
| `pd_pin.pro` | 8.44 | Readout and display of PD pinhole-type data; patching in both directions "not fully implemented yet" |
| `pd_merge.pro` | 8.31 | Merging GID and pinhole data (interactive) |
| `pd_gipi_merge.pro` | 8.31 | Merging GID and pinhole data (function) |
| `scan_pd_read.pro` | 7.0 | Reads a Pilatus frame; pixel → angle/Q with the PINHOLE option (2nd batch, 2026-11-18) |
| `scan_pd_lcoo.pro` | 8.421 | 1D coordinates of a frame; pinhole used by default when Det_Th > 1° |
| `pd_pin_range.pro` | 7.08 | Pinhole coverage (columns) from footprint, S4–detector distance and S5 |
| `pd_gid_read.pro` | 7.0 | Reads GID scans, integrates each frame horizontally, joins scans; Qxy, Qz formulas |
| `img_join.pro` | 7.0 | Joins 2D images: amplitude matching on the overlap, inverse-variance weighted overlap, common transverse range |

Still not supplied: `IMG_COO_CONV` (the pixel → angle formula itself), `SCAN_JOIN` (the scale factor and its error), `IMG_TRIG` (triangulated regridding), `SPEC_FILE_INFO` (the FILDAT fields such as PDIST, PDSDIST).

What is useful for the reader, compared with its own code:
`docs/handoff_out/04-idl-pinhole-review.md` and its answer.
