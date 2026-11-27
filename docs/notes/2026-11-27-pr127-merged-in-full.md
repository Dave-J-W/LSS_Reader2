# #127 merged in full: the released pre-2019 frames, series and windows are published

- **Date, who:** 2026-11-27, main man (asked of the owner).
- **Answer:** the owner: "127 is a you problem. Lets just say that's fine the way it is". Asked whether that
  meant publishing the raw pixel counts too, the owner chose "Merge all of it".
  - This replaces their earlier answer the same day, that only the 96 series' points might be committed.
  - **Published:**
    - `docs/studies/excess_scatter/released/`:
      - `frames.csv`, `frames.json`: two cropped reflectivity frames, 2233 pixels each, as row, column and
        counts, with the reader's boxes;
      - `series.csv`: 96 series' points;
      - `windows.csv`;
      - `numbers.json`;
    - figures R1–R4.
  - All are from anonymous runs before 2019, under the owner's 2026-11-25 release (the `sample_data/private/`
    row of `AGENTS.md`).
  - The rule for every other private run is unchanged: never peak locations, raw data or images.
- **Merged how:**
  - The branch conflicted with main, so it was merged through main man's branch.
  - Frozen files kept main's text (`docs/TODO.md`, `docs/RELEASE_PLAN.md`), and so did the generated
    `docs/TOOLS.md` and `docs/manual/controls.md`, which are refreshed at release.
  - `DATA_NEEDS.md` kept main's rows 18–19.
  - The log entry appended after the freeze moved, unchanged, to
    `docs/notes/2026-11-26-excess-scatter-fresnel-convergence.md`.
- **How it is known:** the owner's answer, 2026-11-27.
- **Numbers that changed:** none in the reader. The study's own numbers are those of #127.
