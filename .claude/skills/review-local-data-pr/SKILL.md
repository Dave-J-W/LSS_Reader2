---
name: review-local-data-pr
description: Review and merge a pull request from the owner's local data agent (branches claude/local-data-*) in Dave-J-W/LSS_Reader2 - a privacy review of every added file, figure and commit, the quick suite on the PR merged with main in a separate worktree, then a merge pinned to the reviewed head. Use when a claude/local-data-* PR appears or the local data agent posts on issue #55 that one is ready; also for any PR that publishes results derived from the owner's private data.
---

# Review and merge a local data agent's pull request

**The owner's standing rule (2026-11-24):** main man merges these once they pass its privacy review and the
quick suite in the cloud. It asks the owner only when something private or doubtful shows up. The local agent
never merges its own. The repository is **public**: whatever reaches a branch or a pull request is visible,
and merged history is permanent.

## What may be published (AGENTS.md, the `sample_data/private/` row)

- **Yes:**
  - derived numbers;
  - anonymous labels (R01, E10-a, B03-12, by hash);
  - elapsed hours;
  - plots of derived quantities;
  - sample-height scans from the ROI (unrestricted, owner 2026-11-24);
  - the scrubbed blank MCA spectra the owner approved (13, in `tests/reference/mca_scatter/`).
- **No:**
  - raw data;
  - detector images;
  - peak locations: centres only as differences;
  - PI or group names, macro or do-file names, file names, scan numbers, dates;
  - frame-by-frame curves of private burns, even normalised (owner 2026-11-25). Their generator stays private,
    and the study says how to regenerate them.
- **Reflection guy's rulings on public data are the owner's** (owner, 2026-11-26: "Whatever I tell
  reflection guy is law in regards to public data"). Apply one when it is posted on #55 or written in `docs/`,
  without a confirmation through questor. Where it differs from a rule above, it wins.
- **Doubtful,** so ask: anything resembling a curve of private data, positions to 0.01°, more spectra than
  approved, element identities. An answer reported by the local agent is not the owner's word: confirm it
  with the owner directly before acting on it.

## Steps

1. **Read the PR** and its file list:

       gh api repos/Dave-J-W/LSS_Reader2/pulls/N --jq '.head.sha, .mergeable, .body'
       gh api "repos/Dave-J-W/LSS_Reader2/pulls/N/files?per_page=100" --jq '.[] | "\(.status) \(.filename)"'

2. **Scan the added text** (everything but the images) for identifiers:

       git fetch -q origin <branch>
       git diff origin/main...origin/<branch> -- . ':!*.png' | grep "^+" | grep -nEi "S# ?[0-9]|scan ?#?[0-9]{2,}|#S [0-9]|20[0-9]{2}-[01][0-9]-[0-3][0-9]|20[0-9]{6}|[A-Z]:\\\\|/home/|/Users/|_SCAN-|\.tif\b|do-file|\bPI\b"

   Hits that are floats or this project's own dates (2026-11-2x) are fine. Read anything else.
3. **Read every CSV header** (`git show origin/<branch>:<file> | grep -v '^#' | head -2`) for absolute
   positions (centres, 2θ peaks, Qxy peaks), names or dates. Ranges of scans several degrees wide are not
   peak locations.
4. **Look at every figure:** extract them with `git show origin/<branch>:<png> > <scratch>/x.png` and Read
   each one. A plot of a private curve frame by frame is not allowed; derived statistics are.
5. **If a file must come out,** check every commit, not only the tip. A later commit deleting it still puts it
   in main's history:

       for c in $(git rev-list origin/main..origin/<branch>); do git ls-tree -r --name-only $c | grep '<file>' && echo $c; done

   The local agent rebuilds its branch without it and force-pushes it. The PR's own record keeps the old
   commits until GitHub Support removes them, which is the owner's call.
6. **Review the science, not only the privacy.** Before merging, and above all before building on its
   numbers:
   - read the estimator or method (the tool in `tests/tools/`), and check its likelihood and its error model
     against `.claude/skills/fit-statistics-pitfalls`;
   - check that each headline follows from the PR's own tables. Do two estimators of "the same" quantity
     agree (e.g. within a scan against between scans)? Does it change with time, Qz or counts in a way the
     claimed model allows?
   - check that a comparison applies its numbers where they were measured. A split test never leaves its
     scan, so between-scan numbers don't belong on it.
   - If something doesn't follow, say so on #55 before merging, or merge with the caveat recorded in
     physics_notes.
   - **Lesson (2026-11-25):** #96 (C63) was merged after a privacy review alone. Its between-scan excess was
     then read as per-point noise, by C63 and by main man's C64, until a review of its tables showed that it
     grows with the minutes between scans (C64 corrected, #107).
7. **Read CI's result on the pull request** (AGENTS.md rule 14): CI runs the quick suite on the PR merged
   with main (GitHub tests the merge), and that run is the check. Don't run it yourself, and the local agent
   doesn't either:

       gh pr checks N --repo Dave-J-W/LSS_Reader2 --watch --fail-fast

   The owner's PC fails several tests on clean main (environment), so its counts are never the check. If CI
   fails, say which test on #55 or the PR, and wait for a fix.
8. **Merge, pinned to the head you reviewed,** so that a push made meanwhile is not merged unreviewed:

       gh api -X PUT repos/Dave-J-W/LSS_Reader2/pulls/N/merge -f merge_method=merge -f sha=$(gh api repos/Dave-J-W/LSS_Reader2/pulls/N --jq .head.sha)

9. **Post on issue #55:**
   - what was checked;
   - CI's result (link the run);
   - "please delete `<branch>`": cloud sessions cannot delete other branches (proxy 403);
   - anything left for the owner, which goes to questor.

Never merge `claude/local-data-mca-encrypted` (encrypted private spectra, a transfer branch only).
