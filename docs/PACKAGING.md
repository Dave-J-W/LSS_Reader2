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
- The Tools menu (`docs/TOOLS.md`): the fit demonstrator
  (`tests/demonstrator/`, with `tests/synthetic/`) is bundled and opens in
  a build. The figure/data generators and checks stay in `tests/tools/`
  and are not bundled: they run as Python processes and write the
  repository's documentation (`docs/`) from its data and sources, none of
  which a build has, so a build shows them disabled with that reason.
  Moving them into a package would change nothing for the user of a
  build and would break every documented command; their entries in
  `lss_tools/registry.py` are the single place they are listed.
  (Not yet checked in a build: the recipe change of 2026-11-22.)
- `packaging/requirements-build.txt`: library versions pinned to the
  ones the test suite passed with. Change them only with a full test run.
- `LSS_Reader --self-test SPEC PREFIX`: opens the window (so the `.ui`
  files and icons are found inside the build), reduces scans 6–9 and
  compares `_ref.txt`/`_rrf.txt` with `PREFIX_ref.txt`/`_rrf.txt` byte for
  byte. Exit code 0 when both match. `$LSS_SELFTEST_REPORT` also writes
  the report to a file (a Windows build has no console).

## Measured (2026-11-18, Linux, this container)

A Linux build from this recipe (PyInstaller 6.22.3, Python 3.13): 464 MB
unpacked; its self-test passed from the repository and from another
folder. The Windows and macOS builds have not been run yet: they need the
workflow to be started once on GitHub.

## Open (owner's decisions)

- **macOS signing.** An unsigned app is blocked by Gatekeeper; users can
  right-click → Open the first time, or the app can be signed and
  notarised with an Apple Developer ID (paid account, secrets in GitHub).
- **Size.** Most of the 464 MB is SciPy, SymPy and Qt; SymPy is used only
  in one calculation (`solve`) and could be dropped later.
- **Distribution.** Artifacts expire after 90 days; a GitHub Release per
  version tag would keep them.
