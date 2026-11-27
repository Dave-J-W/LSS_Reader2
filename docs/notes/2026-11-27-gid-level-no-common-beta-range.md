# A GID level whose 2θ bins share no β range stopped the join on a zero-size array

- **Date, who:** 2026-11-27, local data agent (the last private survey set the 2026-11-26 stopgap did not
  patch; `docs/studies/gid_unscaled_seams/`)
- **Answer:** `level_map` keeps the β range that every kept 2θ bin sees. In this set's upper level a few 2θ
  bins saw only the top of the β range, so no β bin was common. The level kept no β rows, and `join_levels`
  took the maximum of an empty array. It was not a β gap. Now, only when that rule leaves no β row, the level
  keeps the β window that keeps the most map cells (`pinhole._widest_common_window`). The 2θ bins that don't
  see all of that window are dropped and counted in `info['narrow_bins_dropped']`. A level with fewer than
  2 β rows is refused by name. A level that had a common range goes through the old code, unchanged.
- **How it is known:** test `tests/test_gid_narrow_beta_bins.py` (synthetic known truth: a level whose last
  frames have the arm 8° higher has no common β range; with the fix, its map ÷ truth is 1.000, and it joins
  the level below with factor 1.00). Run on the private set, generator
  `sample_data/private/gid/scripts/join_recheck.py`: 10 of the level's 270 bins are dropped, and the levels
  then overlap and join by default with a fitted factor. On the other 17 of the survey's 18 unjoinable sets,
  the fallback never runs.
- **Numbers that changed:** only maps that failed before. Corrected count: of the 18 unjoinable sets, 15
  have a real β gap, and the opt-in stopgap patches all 15. The other 3 patch by default: 2 had failed
  only with the `physical` responses, and 1 is this set. The 2026-11-26 entry in `docs/physics_notes.md`
  said 16 and "15 of 16". `OUTPUT_DECISIONS` row "GID level whose 2θ bins share no β range". "Most cells"
  is an assumption, not the owner's choice.
