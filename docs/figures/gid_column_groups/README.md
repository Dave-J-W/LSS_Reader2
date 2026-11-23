# GID maps and the level join from groups of detector columns

Made by `python tests/tools/gid_column_groups.py` (about 25 s) from the
public NX school GID scans 11 (level 1, arm level, 41 frames) and 12
(level 2, arm raised to β0 = 6.5°, aborted after 4 frames). The figures
asked for in `docs/physics_notes.md` (2026-11-19, "maps from column groups
per level; the β-overlap cells of the join"). The usable columns of all
frames (28–107) are split into three groups; each group is patched alone
by `lss_core.gid.pinhole_patch` (the S5 window narrowed to the group; the
tool's docstring says how and what it checks).

- `NX_S11_12_maps.png`: the Qxy–Qz map of each level and the joined map,
  for all columns and for each group, on one log colour scale. Each panel
  gives its scale against the all-columns map over the same cells.
- `NX_S11_12_join.png`: (a) each level's column response R(c) (the core's
  light per column), with each group's own response; (b) the level factor
  of each group; (c, d) the cells of the β overlap, ratio lower ÷ upper,
  against β and against 2θ.
- `NX_S11_12_factors.csv`, `NX_S11_12_summary.json`: the numbers.

The factor is the core's: lower ÷ upper, the number level 2 is multiplied
by. "Pooled" is Σ⟨I_lower⟩ / Σ⟨I_upper⟩ over the same β bins (a
comparison, not the reader's estimator).

## Measured (response 'fit', 2026-11-23)

| columns (level 1 / level 2) | factor | pooled | 2θ of the overlap | counts per β bin (lower / upper) |
|---|---|---|---|---|
| all 28–107 / 28–91 | 1.088 ± 0.014 | 1.088 | 13.40–15.80° | 646 / 124 |
| group 1: 28–54 / 28–54 | 1.021 ± 0.022 | 1.022 | 13.40–14.46° | 83 / 44 |
| group 2: 55–80 / 55–80 | 1.107 ± 0.018 | 1.107 | 14.40–15.31° | 142 / 62 |
| group 3: 81–107 / 81–91 | 0.745 ± 0.040 | 0.741 | 15.49–15.67° | 6 / 6 |

The factor is the reader's (by likelihood since 2026-11-23, P46). Before,
its estimator was the inverse-variance mean of the per-β-bin ratios, and
this figure found it biased low where β bins hold few counts: 1.068,
0.951, 1.067 and 0.396 on the same cells, 2 %, 7 %, 4 % and 47 % below
the pooled ratio (ratios whose errors grow with the ratio pull such a mean
low). Panel (b) shows both.

What the numbers show:

- The factor depends on the columns used, but on these data mostly for
  a reason other than the light per column:
  - **2θ.** With 4 frames at level 2, each group's overlap is its own 2θ
    strip. The all-columns cells alone, pooled over each group's strip,
    give 0.930, 1.064 and 1.351: the all-columns ratio rises with 2θ
    across the overlap (panel d, first plot).
- Pooled, the factor of groups 1 and 2 equals, to 0.2 % and 1.2 %, the
  all-columns ratio on their strip times the ratio of their maps' scales
  (level 1 × 1.161 and × 1.176, level 2 × 1.054 and × 1.144 of the
  all-columns maps). Group 3 misses by 16 %: its level-1 map is × 0.358 of
  the all-columns map in the overlap, its level-2 map × 0.550 (not
  explained here). At level 1 it includes columns 92–107, which level 2
  does not have.
- With `--columns common` (groups inside 28–91, the columns both levels
  have) the reader's factors are 1.024 ± 0.026, 1.009 ± 0.019 and
  0.981 ± 0.026 (pooled 1.024, 1.009, 0.985): the three groups agree
  within their errors (before P46 the reader gave 0.926, 0.970, 0.808).

## Caveats

- Scan 12 has only 4 frames (Det_Th 14.0–14.3°): column group and 2θ
  cannot be separated, and the overlap is a narrow strip per group. The
  owner's private pairs, with full upper levels, are the real test.
- A group's 2θ and β grids are its own (a fraction of a bin off the
  others'), so groups are compared over ranges, not cell by cell.
- Private data: give `--spec`, `--scans` and an `--out` under
  `sample_data/private/` or outside the repository (the tool refuses
  anywhere else in it).
