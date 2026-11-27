---
name: private-data-handoff
description: Write a hand-off and a runner for an analysis that only the data sessions on the owner's PC can do (private SPEC files, frames, edges, burns) in LSS_Reader2 - check the hand-off and DATA_NEEDS numbers against unmerged branches, build a runner whose public table carries anonymous labels and summary values only with a private key beside it, guard --out, test it on the public NX file (it reproduces the study and leaks nothing), take selection criteria from the real study, and write the request (what is known, numbered questions, how to run, expectations, what to publish, how to judge, what is not asked), its DATA_NEEDS row and task issue. Use whenever a study's next step needs private data, or when another session asks you to build something it will run on private data.
---

# A hand-off and runner for the data sessions on the owner's PC

Distilled from tools man's hand-off 10 (GID burns, P44) and the runner for xr-data-needs' hand-off 09 (Qoff and
σ_Q on real edges), 2026-11-27. The cloud sessions never see private data. They build the tool, the data
sessions run it, and only derived numbers come back through a `claude/local-data-*` pull request that main man
reviews (`review-local-data-pr`).

## 1. Take numbers that are free on every branch

- **Hand-off numbers** (`docs/handoff_out/NN-*.md`) and **DATA_NEEDS rows** can already be taken on an unmerged
  branch, so look beyond `main`:

      git fetch origin
      git ls-tree -r --name-only origin/main docs/handoff_out/
      gh api "repos/Dave-J-W/LSS_Reader2/pulls?state=open&per_page=100" --jq '.[] | "\(.number) \(.head.ref)"'
      git show origin/<branch>:docs/DATA_NEEDS.md | grep -n "^| 1[0-9] |"

  Also read #55 since your last post: a session may have announced a number there.
- **On a clash, renumber yours if it is not published yet,** every reference included:

      grep -rn "09-<topic>\|hand-off 09\|row 18" docs tests

  Say so in the commit and on #55. The case that taught this: hand-off 09 and row 18 were xr-data-needs', on
  branch #127. Mine became 10 and row 19.

## 2. The runner: anonymous labels, summary values, a private key

- **One entry point** in the study tool or a survey tool in `tests/tools/`:
  - `--real FILE...` or `--spec FILE ...`, finding the items itself with the reader's own tests
    (`series.is_burn`, `burn.is_gid`, the scan's Qz range);
  - `--list` for items given by hand;
  - `--scans` to restrict.
- **The public table** (`real.csv`, `edges.csv`) has:
  - anonymous labels (`G01…`, or a hash), and no file name, scan number, date, Qxy, peak position, frame or
    image;
  - only the values the owner allows: changes, errors, verdicts, fit qualities, χ²/dof, flags, shape ratios.

  The owner's lines are in AGENTS.md "Where things are", `sample_data/private/`: never peak locations, raw
  data or images, and no frame-by-frame curves of private burns. Reflection guy's rulings on public data are
  the owner's.
- **The private key** (`real_key.csv`) maps each label to its file, scan and any error. It stays in the
  private folder: say so in the docstring and in the hand-off.
- **A failure is a row, not a silence:** `failed` or `error` set in the table, and the error in the key.
- **Guard the output:**

      out = os.path.abspath(a.out)
      public = all(os.path.abspath(s).startswith(os.path.join(repo, 'sample_data', 'NX_school')) for s in specs)
      if out.startswith(repo) and not public and not out.startswith(os.path.join(repo, 'sample_data', 'private')):
          sys.exit('private data: --out must be under sample_data/private/ or outside the repository')

  This is `ref_patch_survey.py`'s guard. Test that it refuses: `test_qoff_resolution.py`.

## 3. Test it on the public NX file

- **It reproduces the study's own numbers** for the same items:
  `test_burn_shoulder_study.py::test_the_real_data_runner_on_nx`.
- **The public table leaks nothing:**

      text = (tmp_path / 'real.csv').read_text()
      assert 'NX_school' not in text and '20260923' not in text
      assert 'scan' not in text.split('\n')[0].split(',')
      assert 'NX_school' in (tmp_path / 'real_key.csv').read_text()

- **Its selection finds the public items.** The hand-off's criterion "from below 0.8 Qc" missed NX scan 6,
  which starts at 0.806 Qc. Row 13's study had in fact used 0.019 Å⁻¹ (0.875 Qc).
  - Take the criterion from the study that measured real data, expose it as an option (`--below`,
    `--above`), and say why in the docstring.

## 4. The hand-off document (`docs/handoff_out/NN-<topic>.md`)

In this order:
1. **For, from, the owner's words, DATA_NEEDS row, task issue.** Address it to "the data sessions on the
   owner's PC" with `lane:local-data`; Local yokel was archived on 2026-11-27.
2. **Read first:** AGENTS.md's private-data lines, the study's summary, its walkthrough.
3. **What is known:** the public and synthetic numbers, with their errors.
4. **The questions,** numbered, each naming the columns that answer it.
5. **How to run:** the exact commands, the output columns, the arithmetic behind each (how a change and its
   σ are computed, what a verdict means), and the public test that pins the runner.
6. **The expectation:** what the synthetic study predicts for each quantity at the real data's noise, as a
   table. Real results are then read in units of the synthetic SD, and say what each outcome would mean.
7. **What to publish, and where:** the table's destination, the summary section's heading, which figures may
   be published (summary figures; frame curves never) and where the others stay
   (`sample_data/private/figures/`, with how to regenerate them).
8. **How to judge:** thresholds for a disagreement (for example, verdicts differ, or 2 × the larger σ after
   widening a known short interval).
9. **What is not asked:** no default change, no new estimator before the questions are answered.

**Check every claim the hand-off makes against the study's tables before committing.** "A non-Gaussian
shoulder moves B with a broadening peak" was true, but needed its numbers (−4.6 to −6.3 pp against 0.1).

## 5. Records

- A **DATA_NEEDS row**: the dataset, what it must answer, where the answer goes, who supplies it, and
  "Hand-off: …".
- A **task issue** labelled `task` only, so the data session claims it with `claimed` and `lane:local-data`.
  Its body carries the questions in one line each, the command and the hand-off's path, with the footer.
- **One short notice on #55**, `tools man → <data session>, main man:`, linking the issue and hand-off.
- If you build a runner for **another session's** hand-off, end with the comment it asked for, naming the
  commit on `main` (`tools man → xr-data-needs: … at be16f51`). Name the things that will bite in its
  summary: Qc moves Qoff one for one; a parameter at its bound means "not measured".
