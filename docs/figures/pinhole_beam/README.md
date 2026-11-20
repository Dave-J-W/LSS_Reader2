# The beam profile measured by the "beam" response

`beam_response_11.png`, made by `python tests/tools/pinhole_beam_figure.py`
from the public NX school GID scan 11 (α = 0.0905°, S1v 0.1 mm, S4 0.2 mm).

**Left.** Through the S4 pinhole each column looks at one point x on the
beam axis. The response "beam" (`pinhole.beam_response`) works out how much
light comes from each x, shared by all frames of the Qz level. A beam that
meets the surface at α spreads its vertical profile along the surface by
1/sin α, so a width along x times sin α is a height in the beam (top axis).
- Width at half the maximum: 33 mm along the beam, i.e. **52 µm** of beam
  height.
- Downstream the profile does not fall to zero but levels off at about 0.6
  of the mean: light that does not come from the beam on the footprint
  (P40a, light beyond the footprint). Measured above that floor, the width
  is 23 mm, i.e. **36 µm**.
- Both are upper bounds: S4's opening and the beam's horizontal width also
  spread the light along x.
- The grey band is the footprint the reader assumes when it decides which
  columns see sample: uniform over S1v / sin α = 63 mm.

**Right.** The same light seen per column at three Det_Th (coloured), and
the per-column response "fit" (one factor per column for all frames,
black). The column that looks at a given x moves with Det_Th, so one factor
per column is an average; this is why the "beam" response exists
(physics_notes 2026-11-19, "What a Gaussian beam does to the pinhole
geometry"). Columns beyond about 94 appear only at the higher Det_Th since
the P39 fix (exact footprint window, D51).

A half-cut sh scan measured next to each GID level would give this profile
directly (F43; physics_notes 2026-11-19, half-cut answer).
