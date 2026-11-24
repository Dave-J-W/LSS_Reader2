# Handoff: GUI manager session (written 2026-11-23, 21:30 UTC)

Owner: "Main is orchestrator; go ahead and build" (main window first, then
the timeline F83, then ngui). Report to Main (session_017UNj94caCtuQh48DiL9JQC,
send_message) and message it before large `mainwindow.py` edits. Standing
permission: merge my branch into `main` by PR + "Create a merge commit"
once the quick suite (and, for GUI changes, the sweep) pass; then merge
`main` back into the branch.

## State (updated 2026-11-24, 10:30 UTC)

- **On main:** everything through #37 (e4650b3):
  - F96 (Back, Cancel, the join table, refProvenanceLabel);
  - the reflectivity Save scans fix;
  - F95 part: the checks are a message plus marks, and the Bad Pixels list;
  - F74 on scan and cut fits;
  - the F97 saturation cue;
  - the movie-test timer fix and the fitCuts crash fix;
  - Main's strict xfails for the drop-first-point defect (tests/test_drop_first_point_errors.py). Main's fix removes them.
- **On my branch, not yet merged** (quick suite 1030 passed):
  - 83c605f: the Reduction options switch for mca_fit_poisson;
  - daab224: F74 on burn trends;
  - 3fd2a96: F78, timeline 1a (peaks.fit_super_gaussian; SpecPlot).
- **The full sweep on 3fd2a96** runs in `scratchpad/wt_sweep` (log `scratchpad/sweep_t5.log`). If it passes: PR, merge, fast-forward, tell Main.

## Next, in order

1. Merge the branch (above).
2. Timeline 1b: `lss_core/timeline.py` (events, sh scans, sx steps, scan spans; research.md §1, 3, 5, 6). The reset comments go into spec_routines (Par['Resets']), so tell Main first: the SPEC reader is shared.
3. F97: the ROI close-up panel and the diffuse axes. F95: B3's threshold (needs an OUTPUT_DECISIONS row), B9, B10.
4. F74 on the Ref Patch join preview and the older dialogs. Tools man does the MCA lines.
5. B7's live part: replay the stored joins through factors=.
6. Ask the owner whether the timeline tab goes in the main window (no answer yet).

## Lessons

- After `git rm`, stage with `git add -A`, not a path list: a missing path aborts the whole add.
- A new control needs:
  - an inventory entry;
  - a place in `ngui/layout.py` (check that it is not already placed);
  - `python tests/tools/ngui_inventory.py`;
  - `dump_tooltips` regenerated.
- New preference keys go into `tests/test_gui_preferences.py`'s expected dict.
- Run the sweep in a separate worktree so that editing doesn't change files under it.
- ngui: every inventory id must be placed or retired, removed: entries included; a placed id needs a widget named ngui_<id> whose tooltip has "Was:"/"Does:", and an enabled widget must be a plot, label or tab widget. Keep the default window at 1440 × 900 (test_ngui).
- Regenerate screenshots into a scratch folder, then copy only the ones the change makes stale.
- New controls change the sweep's random walks, which then reach old defects: fix them in their own commit with a test (e.g. fitCuts after ax.clear, 2026-11-24).
- matplotlib 3.11: removing an artist after ax.clear() raises NotImplementedError; check artist.axes first.
- Timer-driven GUI tests race on a loaded machine; disconnect the timer's slot and step by hand.
