# Notes: one file per entry

What used to be appended to `docs/physics_notes.md` goes here: a question from the owner and its answer, a
finding, or a deliberate change of a number (AGENTS.md rules 1 and 5). Each entry is its own file, so two
sessions writing at once never clash on merge.

- **Name:** `YYYY-MM-DD-<short-topic>.md`, for example `2026-11-28-burn-dose-units.md`. Pick a new name
  instead of appending to someone else's file.
- **Keep it short:** a few lines are usual. Link to a study, an issue or a commit rather than repeating it.
- **Invariants** (quantities that must be conserved) still go in the table at the top of
  `docs/physics_notes.md`, with the test that checks them.
- **The old log** (2026-11-14 to 2026-11-27) stays in `docs/physics_notes.md`, frozen, so references into it
  keep working.

## Template

    # <the question or the finding, in one line>

    - **Date, who:** 2026-11-28, <session> (asked by the owner / found while doing #<issue>)
    - **Answer:** <what is true, in plain words>
    - **How it is known:** test `<test id>` / run `<command or study>` / reading only
    - **Numbers that changed** (rule 1, if any): before → after, and the `OUTPUT_DECISIONS` row
