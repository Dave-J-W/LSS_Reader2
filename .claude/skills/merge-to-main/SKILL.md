---
name: merge-to-main
description: Bring a cloud session's claude/<name> branch into main of Dave-J-W/LSS_Reader2 the way AGENTS.md "Where to commit" (D60) requires - merge main in, run the right suites, open a pull request and merge it at once with a merge commit, then fast-forward the branch. Use whenever a finished piece of work (code, tests, docs) should reach main from a session that cannot push to main, including docs-only changes.
---

# Merge a session branch into main (D60)

A cloud session can push only its own `claude/<name>` branch: GitHub refuses pushes to `main` (HTTP 403).
So work reaches `main` through a pull request that is merged at once, as a record, never left open. Sessions
with the owner's standing permission (main man, tools man, the GUI manager) do this themselves.

## Steps

1. **Commit** each defect or feature separately, with its test in the same commit (AGENTS.md).
   - End every message with the two attribution lines from the session's system reminder: `Co-Authored-By: …`
     and `Claude-Session: …`.
   - No model names in commits or pull requests.
2. **Merge main in:**

       git fetch -q origin main && git merge --no-edit origin/main

   - On a conflict in `docs/physics_notes.md` (two sessions appended entries), keep both, in date order. A
     small script that splits on the markers and joins `mine + '\n\n' + theirs` does it.
   - On a clash of COMPARISONS numbers (`| C61 |` taken on main meanwhile), take the next free number
     (`grep -o "^| C[0-9]*" docs/COMPARISONS.md | sort -t C -k2 -n | tail -1`) and re-point every reference.
     Say so in the merge commit.
3. **Run the suites** on the merged tree:
   - **always** the quick suite: `timeout 1200 python -m pytest -q -p no:cacheprovider` (about 4 min);
   - **real-data tests** for the area when numbers can move: `python -m pytest -q -m slow -k "<area>"`;
   - **the crash sweep, in the background,** when the window is touched:

         timeout 3000 python -m pytest -q -m sweep -p no:cacheprovider > <scratch>/sweep.txt 2>&1; echo "PYTEST_EXIT=$?" >> <scratch>/sweep.txt

     It takes about 9 min alone. Its limit must exceed its run time, and the exit code must be recorded: a
     trailing `tail` hides it.
   - **after catalogue changes:** `python -m lss_toolbox --render`, then `tests/test_toolbox.py`.
4. **Push and open the pull request.** Its body says what changed and **which suites ran with their
   results**: no workflow tests pull requests. End the body with the attribution the system reminder gives.

       git push -q origin claude/<name>
       n=$(gh api repos/Dave-J-W/LSS_Reader2/pulls -X POST -f title="…" -f head=claude/<name> -f base=main -F body=@<scratch>/pr.md --jq .number)

5. **Merge it at once with a merge commit** (never squash or rebase: they give main other commits), then
   bring the branch level with main:

       gh api -X PUT repos/Dave-J-W/LSS_Reader2/pulls/$n/merge -f merge_method=merge --jq .merged
       git fetch -q origin main && git merge --ff-only origin/main && git push -q origin claude/<name>

   - **HTTP 405 "merge conflicts"** means main moved after step 2. Do step 2 again, push, and merge again.
6. **Tell the others on issue #55** when the change matters to them: an API, a changed default, a new time
   for a suite.

## Records that go with a change (AGENTS.md rule 11)

- an output number changes: an `docs/OUTPUT_DECISIONS.md` row;
- a method changes: a `docs/COMPARISONS.md` row;
- something must be conserved: an invariant in `docs/physics_notes.md`;
- the owner asked or answered something: a dated physics_notes entry;
- a script call changes: `docs/SCRIPTING.md`;
- the state of a feature changes: `docs/FEATURE_REQUESTS.md`;
- who is on what changes: `docs/TODO.md`;
- something was built: a line in `docs/ACCOMPLISHMENTS.md`.
