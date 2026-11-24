# Handoff: GUI manager session (written 2026-11-23, 21:30 UTC)

Owner: "Main is orchestrator; go ahead and build" (main window first, then
the timeline F83, then ngui). Report to Main (session_017UNj94caCtuQh48DiL9JQC,
send_message) and message it before large `mainwindow.py` edits. Standing
permission: merge my branch into `main` by PR + "Create a merge commit"
once the quick suite (and, for GUI changes, the sweep) pass; then merge
`main` back into the branch.

## State (updated 2026-11-24, 17:40 UTC)

- **On main:** everything through #57 (33f7151):
  - the Timeline tab, furthest right: lanes, sh thumbnails, notes and the 'new sample?' answers as workbook notes;
  - the Compare tab (F80, F105) just left of it;
  - the ROI close-up (F71, F97);
  - F96, F95 part, F74, F78; the GID refusal fixes.
- **Work in:** the worktree `.claude/worktrees/agent-ab9975ffcaf2237a8`. Fast-forward `claude/funny-noether-09opxa` from it and push that branch.
- **Messages to main man** (the orchestrator, renamed from Main) failed at 17:40 UTC: "needs proof of a trusted device". The owner was told; check whether it works again before relying on it.

## Next, in order (main man's order of 2026-11-24)

1. F105's Export: a file name proposed from the sample and series, and the hand-over to xmodfit (Q-REF-6; contract in docs/handoff/).
2. F79's window side: Propose buttons by refQoffLineEdit and refQcLineEdit (tools man's core on main, #56). No default changes before a demonstrator (rule 12).
3. F97's diffuse cut axes, window side (main man's core, #59, lss_core.cuts): the axis choice on the cut tab.
4. F92's mask in the Ref Patch window (core #54): drops recorded as the mask, Restore all, masked points drawn apart, read-only for a second reader.
5. F98 / F107 with the dose (core #52) when reached; timeline reduced-data and environment lanes; F95 B9/B10; B3 (rule 12).

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
