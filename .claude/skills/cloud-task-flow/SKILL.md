---
name: cloud-task-flow
description: "Carry one task from claim to close as a cloud session of LSS_Reader2 under the rules of 2026-11-27 (rules 5, 11, 14, 15) and the cloud's limits - reread AGENTS.md's changes and #55 first, claim or open a task issue, put records where they now go (docs/notes/, issues; not the frozen physics_notes log, TODO or RELEASE_PLAN's backlog), keep unrelated work out of a commit and out of a test run, cite catalogue anchors that exist, wait for CI by REST (gh pr checks is refused), merge pinned to the tested sha with Closes #N, and report on the task's issue. Use at the start of every task, and whenever a merge of main changes AGENTS.md."
---

# A task from claim to close, as a cloud session

Distilled from tools man's 2026-11-27 session. The rules changed several times that day, and one commit of
records had to be redone after a merge of main brought the new ones. `merge-to-main` holds the merge mechanics; this skill is the whole loop around
them.

## 1. Before starting: what changed since you last looked

    git fetch -q origin && git log --oneline HEAD..origin/main | head -30
    git diff HEAD origin/main -- AGENTS.md .claude/skills/        # the rules move often: read every change
    gh api "repos/Dave-J-W/LSS_Reader2/issues/55/comments?since=<your last post>&per_page=100" --jq '.[] | .body[0:800]'
    gh api "repos/Dave-J-W/LSS_Reader2/issues?labels=task&state=open&per_page=100" --jq '.[] | "\(.number) [\([.labels[].name]|join(","))] \(.title)"'

A "hand-off waiting for you" usually means a #55 comment addressed `→ tools man`, with a file on another
session's branch:

    git show origin/<branch>:docs/handoff_out/<file>.md

## 2. Claim it, or open it

- **An existing task:** add the labels and say so in a comment.

      gh api repos/Dave-J-W/LSS_Reader2/issues/N/labels -X POST -f "labels[]=claimed" -f "labels[]=lane:tools"

  Comment "claimed by tools man". A `parked` issue is backlog: work it only when the owner or main man unparks
  it, or the owner asks for it directly.
- **New work** (a request on #55, or something you found): open the issue yourself, then claim it.

      gh api repos/Dave-J-W/LSS_Reader2/issues -X POST -f title=… -F body=@body.md -f "labels[]=task" -f "labels[]=claimed" -f "labels[]=lane:tools"

  End the body with the footer.

## 3. Records go where the rules say now

- **A finding or an owner's answer:** a new file `docs/notes/YYYY-MM-DD-<topic>.md`, from the template in
  `docs/notes/README.md`.
  - The log in `docs/physics_notes.md` is frozen; only its invariants table is live.
  - If a merge of main shows you appended to the log, move the entry out and re-point what cites it (a C-row's
    notes column).
- **Frozen or moved:**
  - `docs/TODO.md` is frozen.
  - RELEASE_PLAN's "After 2.0" list became issues #142–#150.
  - Revert your edits to them (`git checkout origin/main -- docs/TODO.md docs/RELEASE_PLAN.md`) and report on
    the issue instead.
- **Still in the same commit as the change** (rule 11):
  - an `OUTPUT_DECISIONS` row for any changed number;
  - a `COMPARISONS` row for a new method;
  - a catalogue item for a new `tests/tools/` script;
  - a tooltip and a `MANUAL_NOTES` line for a new control;
  - `docs/SCRIPTING.md` for a new script call;
  - a line in `docs/ACCOMPLISHMENTS.md`.
- **Not per commit:** `docs/TOOLS.md`, `docs/manual/controls.md`, figures, inventories and `verified.json`.
  If you regenerated them, `git checkout` them back.

## 4. Keep unrelated work apart

- **Two tasks in one tree:** commit by explicit paths (`git add <paths>`), never `-a` or `-A`. Stash the
  other task before merging main or running tests:

      git stash push -m "<task> wip" <paths>

- **A new `tests/tools/` script** without its catalogue item fails `tests/test_toolbox.py` for anyone who
  runs the suite on your tree. Draft new tools and tests in the scratchpad, and move them in with their item.
- **Catalogue variations cite anchors that must exist on exactly one line.** That is a heading such as
  `summary.md## 3. What moves it` or a ledger id such as `COMPARISONS.md#| C71 |`.
  - Write the summary's headings and the C-row before running `pytest tests/test_toolbox.py`.
  - Copy headings exactly: "(BW6)" against "(figure BW6)" failed the catalogue test on 2026-11-27.
- **One feature per commit, with its test.** If the tests import the study tool and the catalogue cites the
  summary, the tool, tests, summary and outputs belong in one commit.

## 5. Test what you changed; CI checks the rest

- **Locally:** `pytest tests/test_<area>.py` for what you touched, plus `tests/test_toolbox.py
  tests/test_gui_menus.py` after catalogue or doc-anchor changes.
- **`-m slow -k <area>`** only when real-data numbers can move. Say `slow: N passed on <sha>` in the PR.
- **The quick suite is CI's.** Don't run it yourself while a long study occupies the CPUs.

## 6. Pull request, CI, merge: by REST only

`gh pr …` and GraphQL are refused in cloud sessions, so `gh pr checks --watch` does not work.

    git fetch -q origin main && git merge --no-edit origin/main && git push -q origin claude/<name>
    n=$(gh api repos/Dave-J-W/LSS_Reader2/pulls -X POST -f title="…" -f head=claude/<name> -f base=main -F body=@pr.md --jq .number)
    sha=$(git rev-parse HEAD)
    until s=$(gh api repos/Dave-J-W/LSS_Reader2/commits/$sha/check-runs \
                --jq '[.check_runs[] | select(.name=="quick")][0] | "\(.status) \(.conclusion)"') \
          && [[ "$s" == completed* ]]; do sleep 30; done; echo "$s"      # in the background
    gh api -X PUT repos/Dave-J-W/LSS_Reader2/pulls/$n/merge -f merge_method=merge -f sha=$sha --jq .merged
    git fetch -q origin main && git merge --ff-only origin/main && git push -q origin claude/<name>

- **The PR body:**
  - what changed, and the findings in a few lines;
  - `Closes #N` (the merge closes the task issue);
  - the suites as `<area>: N passed on <sha>`;
  - the attribution lines from the system reminder.
- **Merge only on `completed success`,** pinned to the sha CI tested (`-f sha=`). HTTP 405 means main moved:
  merge it again, push, and wait for the new run.
- **`subscribe_pr_activity`** delivers CI and merge events. GitHub unsubscribes the session by itself when the
  PR merges. A manual unsubscribe needs a trusted device, so don't ask the user to do it.

## 7. Report and close

- **On the task's issue:** the PR and merge commit, the findings in three or four lines, and what comes next.
  `Closes #N` closed it. If it was a shared issue (a list of studies), comment and leave it open.
- **On #55:** one short notice, only to the sessions that must act (`tools man → xr-data-needs: … at
  <sha>`), linking the issue and the file instead of retelling them.
- **New work found on the way** (a real-data question, a follow-up): open its own task issue, labelled for the
  lane that will do it, rather than a line in a hand-off.

## 8. Long jobs in a cloud session

- **Start them in the background** with an exit marker in the log (`…; echo "EXIT $?" >> log`), and wait with
  an `until grep -q ^EXIT log; do sleep 20; done` loop. Chains of plain `sleep` are refused.
- **Find a job's real start** with `ps -eo pid,etime,args | grep <script>`, not by guessing.
- **Nothing in the container survives it:** push what matters before a long wait.
