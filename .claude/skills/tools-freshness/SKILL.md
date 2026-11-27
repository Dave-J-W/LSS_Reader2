---
name: tools-freshness
description: Keep LSS_Reader2's committed figures and tables in step with the code that makes them - since 2026-11-27 (slim rule 11) only before a release or when someone asks, never per commit; verify them with the Tools audit, keep lss_toolbox/verified.json current, handle revision stamps, run-dependent lines and environment differences, and regenerate docs/manual/controls.md when Tools items are added. Use after changing code a tool uses, after merging main, when `python -m lss_toolbox --stale` flags items, or when adding a figure generator.
---

# Committed products: fresh, verified, recorded

> **When to use this (owner, 2026-11-27, slim rule 11):** only before a release, or when someone asks (the
> Manual writing session, the owner). **Not** after every code change and **not** after merging `main`. Make
> no bookkeeping-only commits in between. `pytest -m release` checks that everything is current.

`lss_toolbox` (F84) catalogues every generator in `tests/tools/`. The design, from 2026-11-25:
- `fingerprint.py` fingerprints code without its docstrings and comments;
- `trace.py` records what a run imported and read;
- `--audit --record` writes `lss_toolbox/verified.json`;
- `--stale` reads that record first, and git history only when there is no record.

## After changing code

1. `python -m lss_toolbox --stale`: the items whose recorded inputs changed. "indirect" means only a file
   further down the imports changed.
2. Rerun the affected items into a scratch folder and compare:

       LSS_READER_TOOLS_DIR=$SCRATCH/runs python -m lss_toolbox --audit --record --only ID ...

   Each item gives one row (images and tables: same / differ / not made) and "recorded" or "not recorded".
   - **same:** done; `verified.json` now holds it.
   - **differs, and it is real:** regenerate the product into the repository with the committed settings,
     reread the text that quotes it, and audit again. Examples: the pinhole figures moved by sub-pixel
     amounts; the MCA gauntlet's table gained columns.
   - **differs only by the environment** (the products' own commit, run here, gives today's image): it is
     recorded as "environment"; there is nothing to fix.
   - **differs only by the printed revision:** the tool must take `LSS_TOOLS_REVISION`. The audit reruns
     with a dummy revision and masks what moves, recorded as "stamp" (`compare.stamp_boxes`).
   - **a table differs by run bookkeeping:**
     - echoed command lines and JSON `command`/`seconds` entries are already ignored;
     - wall times go in the item's `volatile=(regex, ...)`;
     - each pattern must match a line of the product (`tests/test_toolbox_freshness.py`).
   - **differs from run to run** with the same code: a determinism bug in the tool (ties ordered by a
     set). Fix the tool, not the comparison.
3. Commit the regenerated products with the change, then `verified.json` with them (its fingerprints are
   of the committed files).

## Adding a generator

- Add a catalogue item (`lss_toolbox/catalog.py`): `committed`, `docs`, `data`, `defaults={'--out': OUT}`,
  `inputs` for data files it reads, `repo_out`, `seconds`, and variations citing `path#heading`. Each
  anchor must match exactly one line, so rewording a quoted heading breaks `test_toolbox`.
- `python -m lss_toolbox --render` rewrites `docs/TOOLS.md`.
- **A new item is a new Tools menu action, so regenerate `docs/manual/controls.md`:**

      QT_QPA_PLATFORM=offscreen LSS_READER_LOG_DIR=$S/logs LSS_READER_PREFS=$S/prefs.json \
          python tests/tools/dump_tooltips.py > docs/manual/controls.md

  Other sessions' merges often add items without doing this. `dump_tooltips` then turns "indirect"; fix it
  in the merge.

## Merging main

- After `git merge origin/main`, run `--stale`. Merged code often makes recorded items "indirect"
  (TwoDDetector.py, mainwindow.py).
- Re-audit just those items (`--only`), then commit `verified.json`.
- Do not audit while editing files the tools import: fingerprints are taken at the end of each item, so
  an edit made mid-audit gets recorded against a run that never used it.

## Costs (this container)

- The whole audit takes about 50 min; the gauntlets and the screenshots are most of it.
- A figure item takes 5–90 s, a check item 1 s.
- `gui_screens` and `ngui_screens` belong to the GUI manager: report them, don't remake them.
