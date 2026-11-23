# ngui ideas: candidates for the main window

Owner, 2026-11-23, relayed by the orchestrating session: the main window is
the priority, then the timeline tab (F83), then ngui. Ideas from ngui may be
carried into the main window, so a useful ngui idea is written down here as
a candidate, not built twice. ngui itself (`ngui/`, `docs/gui/prototype.md`)
is parked as merged: a non-functional sketch, off by default.

Each row gives the idea, where ngui shows it, the owner's answer that bears
on it (`questions.md`, Answers, 2026-11-23), and its status for the main
window.

| Idea | In ngui | Owner's answer | Main window |
|---|---|---|---|
| Panes (Script, Messages, Errors) under the tabs only, hidden by default, never raising themselves; the selection panel at full height | window; View menu | Q11: all three follow D59; Messages raises only on warnings | **to build** (D59) |
| Status-bar badges for settings that change numbers | status bar, right | Q12: badges for error model, / gain, / photon, patch method; a three-mode preference (on, on when not default, off) | **to build** (F85) |
| One provenance line under every result plot | every result | Q-UI-B5: method, error model, absorber model, scans, dropped points, saved version; detail in the tooltip | **to build** (F96) |
| Joins as a table rather than one window per join | Reflectivity > Joins | Q-UI-B7: keep the patch window, with Back, a Cancel that does not abandon silently, and a join table kept with the result; accepted joins stay accepted until the step is run again. Q-REF-2: every join is looked at, so never auto-accept | **to build** in the Ref Patch window (F96), not inline in the tab |
| Movie bar with metadata line, sticky zoom and scale | Frames > Raw frames | Q7: a movie for 3 or more frames, space and arrow keys. Q9: display and zoom sticky across redraws, scans and sessions, reset on a new SPEC file; Home and Fit all on every axis. Q8: scales by kind. Q-IMG-4: one shared absorber-corrected scale | **to build** (F69, F88) |
| "Fixed in 2θ" movie for GID | Frames > Raw frames | owner 2026-11-23 (real GID peaks stay at one 2θ) | candidate, after the movie (M7) |
| ROI close-up as a side panel | Reflectivity > ROI close-up | Q-IMG-7: a side panel, always visible, the same for both tabs; Q-IMG-16: one panel, box moved to the found peak, old box dashed | **to build** (F97, display side) |
| Raw frames and Line cuts as sub-tabs of one viewer, with Split | Frames | asked in ngui; no answer for the main window yet | candidate: the main window has a separate Line/Area Cuts tab today |
| Burn as its own place: several burns, verdict card, environment panel | Burn tab | Q-BURN-2: opens by itself, plot modes including a dose axis; burns usually at two sx positions (F98). Q-UI-B10: dock frequent windows | candidate: the burn dialog becomes a dock (F98, Q-UI-B10) |
| Frequent windows as inline groups | GID worksheet, fit options inline | Q-UI-B10: dock the frequent ones (burn, worksheet, fit options) | **to build** as docks (F95) |
| Retired controls with reasons | Help > Retired controls | Q14: the Apex tab (colour map moved first), Beamlines menu, `peakfit2`/`peakfitpara`, Command line row go | **to build** (removals) |
| Legacy paths behind "Legacy…" | Legacy… buttons | Q13: nothing is removed; a Reduction options page chooses legacy or new, Ctrl+click flips | **to build** (F86), replacing the Legacy… idea |
| Export only from File > Export…; one Save… per result | every result; File menu | Q-UI-B9: for the main window, Export (text files) and Save (workbook) beside every result. D61 applies to ngui only | **not carried**: the main window follows Q-UI-B9 |
| Save… attaching the note to the version just saved automatically | Save… tooltip | not asked for the main window | candidate: it avoids duplicate versions (TODO: per-tweak and per-Accept saves) |
| Tabs by workflow in the order of the day | the tab bar | Q-GEN answers kept GIOXS, 2D_Plot, the Calculations menu and the background block "as they are for now" | candidate for a later phase; not now |
| Greyed-out tools that do not fit the series kind | disabled placeholders | Q-UI-A10: grey out, with a tooltip saying what is needed | **to build** |

When an idea moves to the main window, mark it here with the commit, and keep
ngui's layout table (`ngui/layout.py`) in step only if ngui is resumed.
