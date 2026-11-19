# IDL reference code (pinhole and GID), by Mati Meron

**Author: Mati Meron** (ChemMatCARS). Every file here names him as its
author in its MODIFICATION HISTORY ("Created … by Mati Meron"), with dates
from 2002 to 2016. Published in this repository at the owner's request
(2026-11-19: "commit all the Mati Meron IDL code publicly, and attributed
to him"), stored **unchanged**, as the reference for the reader's
pinhole-geometry correction and GID patching (F45, F23, D36). The reader
does not run them; it reimplements what it needs in Python and says so
where it does. Routines they call from Meron's MIDL library (RANGE_PROC,
LINFIT_MM, SCAN_INTER, …) are not included.

Received from the owner: the first ten files on 2026-11-18 (from Mati
Meron's code, the files whose contents mention "pinhole"); the last four on
2026-11-19.

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
| `img_coo_conv.pro` | 7.1 | Area-detector pixel → (2θ, β) or (Qxy, Qz), exact, with the horizontal pinhole transformation (2026-11-19) |
| `limg_coo_conv.pro` | 7.02 | The same for a line detector (2026-11-19) |
| `scan_join.pro` | 8.16 | Joins 1D scans: weighted order-0 fit of the ratio on the overlap, factor error, overlap merged with weights y/σ² (2026-11-19) |
| `spec_file_info.pro` | 8.475 | Reads a SPEC file into FILDAT: `#B1` is centre x, centre y, distance, pinhole distance (the larger is PDIST), orientation H/V; detector sizes 487 × 195 (Pilatus), 981 × 1043 (1M) (2026-11-19) |

Still not supplied: `IMG_TRIG` (triangulated regridding); Meron's MIDL
library routines the files call.

What is useful for the reader, compared with its own code:
`docs/handoff_out/04-idl-pinhole-review.md` and its answer.
