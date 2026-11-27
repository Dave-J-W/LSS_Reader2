# Packaged builds (F46)

Users get a folder (Windows) or an app (macOS) with Python and every
library inside; nothing to install.

## Making a build

On GitHub: Actions tab → **build** → *Run workflow* (or push a tag
`v1.2`). Windows and macOS are built on GitHub's machines, each build runs
its self-test on the NX school data, and the results are kept as
artifacts `LSS_Reader-Windows` and `LSS_Reader-macOS` (zip files on the
run's page). Ordinary pushes do not start it.

On your own machine (same platform as the build you want):

    pip install -r packaging/requirements-build.txt
    pyinstaller --noconfirm packaging/lss_reader.spec
    dist/LSS_Reader/LSS_Reader --self-test sample_data/NX_school/2026sep/20260923 tests/reference/legacy_export/nx_scans_6-9

## What is in it

- `packaging/lss_reader.spec`: every `.ui` file and the four icons; the
  custom widget modules the `.ui` files import (`mplwidget`,
  `mpl2dwidget`). No machine-specific paths.
- `packaging/requirements-build.txt`: library versions pinned to the
  ones the test suite passed with. Change them only with a full test run.
- `LSS_Reader --self-test SPEC PREFIX`: opens the window (so the `.ui`
  files and icons are found inside the build), reduces scans 6–9 with
  the legacy patch (the reference files are the legacy reduction, rule 3) and
  compares `_ref.txt`/`_rrf.txt` with `PREFIX_ref.txt`/`_rrf.txt` byte for
  byte. Exit code 0 when both match. `$LSS_SELFTEST_REPORT` also writes
  the report to a file (a Windows build has no console).

## Measured

- **2026-11-18, Linux, this container:** a build from this recipe (PyInstaller 6.22.3, Python 3.13), 464 MB
  unpacked; its self-test passed from the repository and from another folder.
- **2026-11-26, Linux, again** (the code of `main` at d69f054, for the release): 466 MB; the self-test passed
  from another folder (window with 9 tabs; `_ref.txt` and `_rrf.txt` identical).
- **2026-11-26, GitHub, the workflow started by hand on `main` at d69f054** (run 45751301360, 4 min): **both
  built and passed their self-test.** On Windows: the window opened with 9 tabs, and `_ref.txt` and `_rrf.txt`
  were identical to the reference. Downloads: `LSS_Reader-Windows` 129 MB and `LSS_Reader-macOS` 292 MB
  (zipped), kept until 2027-02-24. The sample-data download is added from the next run on. Not yet done:
  the clean-PC test below (a person on a Windows PC without Python).
- **2026-11-26, the build to ship** (main at ce38cf4, run 45879045324, at main man's request: after F110,
  the open-time lock, the crash and export fixes, the export rule and F112): **Windows built and passed its
  self-test** (window with 9 tabs, `_ref.txt` and `_rrf.txt` identical); downloads `LSS_Reader-Windows`
  129 MB and `LSS_Reader-sample-data` (304 files). macOS: GitHub had no macOS runner free for 15 min
  ("not acquired by Runner"); re-run, it **built and passed its self-test too** (`LSS_Reader-macOS`
  292 MB). The clean-PC test should use the next run's download (it adds #132 and #135).
- **2026-11-27, the build for the tag** (main at cc599e4, run 45918527279, started by main man at the owner's
  request while tools man was busy): after #132 (index numbers) and #135 (Plot options takes the Customize
  editor). Windows and macOS built and passed the self-test: window with 9 tabs, `_ref.txt` and `_rrf.txt`
  identical. Downloads kept to 2027-02-25. The owner tags `v2.0.0` on cc599e4.
- **Near-clean test, the owner's PC** (project manager, 2026-11-26, run 45751301360's Windows build): Python
  off PATH, every `PYTHON*`, `CONDA*` and `QT_*` variable unset. The self-test passed in 9 s, and a plain
  start showed the window in 4 s and closed cleanly. Not a truly clean PC: Python and the Visual C++
  runtimes are installed there.

## Clean-PC test (release blocker 4, `docs/RELEASE_PLAN.md`)

Done by a person on a Windows PC that has never had Python or the reader on it: a beamline PC or a
spare laptop. **Do not use Windows Sandbox on the owner's PC** (project manager, 2026-11-26/27: enabling and
running it there was followed by an unexpected shutdown, then a hard freeze that left half-written files as
zeros and a startup disk the PC could not find until the owner repaired it; no test result came out;
`docs/RELEASE_PLAN.md`, blocker 4).

1. **Download** both zip files from the build run's page (Actions → build → the run → Artifacts):
   `LSS_Reader-Windows` (the program) and `LSS_Reader-sample-data` (the NX school data and the reference
   files). Unzip both into one folder, say `C:\LSS`.
2. **Start it:** double-click `C:\LSS\LSS_Reader\LSS_Reader.exe`. The window should open within about
   30 s, with no console and no error. Help → About shows the version.
3. **The self-test,** in a Command Prompt:

       set LSS_SELFTEST_REPORT=C:\LSS\selftest.txt
       C:\LSS\LSS_Reader\LSS_Reader.exe --self-test C:\LSS\sample_data\NX_school\2026sep\20260923 C:\LSS\tests\reference\legacy_export\nx_scans_6-9
       type C:\LSS\selftest.txt

   The last lines should read `_ref.txt: identical`, `_rrf.txt: identical`, `self-test passed`.
4. **By hand,** following `docs/manual/quick_start.md`:
   - File → Open Spec File: `C:\LSS\sample_data\NX_school\2026sep\20260923`;
   - choose the series of scans 6–9, tick Select All, then Pilatus → Ref Patch, and Next>> three times;
   - Reflectivity → Export, to the Desktop. Two files appear: `<name>_ref.txt` and `<name>_rrf.txt`.
5. **XModFit** (on the owner's machine) reads the `_ref.txt`.
6. **Report on #55:** pass or fail for each step, the Windows version, and anything in the Messages pane
   (View → Messages).

## Open (owner's decisions)

- **macOS signing.** An unsigned app is blocked by Gatekeeper; users can
  right-click → Open the first time, or the app can be signed and
  notarised with an Apple Developer ID (paid account, secrets in GitHub).
- **Size.** Most of the 464 MB is SciPy, SymPy and Qt; SymPy is used only
  in one calculation (`solve`) and could be dropped later.
- **Distribution.** Artifacts expire after 90 days; a GitHub Release per
  version tag would keep them.
