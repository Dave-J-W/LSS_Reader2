# GID patching: diagrams for the manual

Figures of `docs/manual/gid_patching.md`, drawn by
`python tests/tools/gid_patching_diagrams.py [--out DIR] [--only N ...]`
from lss_core and the public NX school data (`sample_data/NX_school/2026sep/20260923`,
GID scans 11 and 12); every number on them is computed, none typed.

- `01_frame_anatomy.png`: one frame (scan 11, Det_Th 16°): direct-beam pixel, rows used, sample horizon, and the S5 window, footprint windows (exact, IDL's), usable columns and legacy column band in columns.
- `02_columns_to_two_theta.png`: schematic top view: three columns' rays through the S4 pinhole, each at its own 2θ, against the legacy band placed at Det_Th.
- `03_frames_cover_two_theta.png`: the 2θ each frame's usable columns cover (both Qz levels), a 2θ overlap (scan 11 split into scans A/B as an illustration), frames per 2θ bin with min_frames and the map edges, and one 2θ bin against the 2θ resolution.
- `04_pixels_to_cells.png`: exact per-pixel (2θ, β) of one frame at the arm level (scan 11) and with the arm raised (scan 12), over the grid of cells (2θ bin × β bin).
- `05_levels_and_overlaps.png`: the two Qz levels in (2θ, β), the β overlap where the level join factor is fitted, the transverse range ('intersection', 'union'), and the legacy patch's edge copies.
- `06_join_factor.png`: how the level join factor is fitted: cells both levels have (schematic), the mean intensities per β bin and their ratio for NX 11 + 12, with the factor and χ²/dof.
