# LSS_Reader
Software to reduce and visualize the x-ray scattering data from liquid surface/interface at NSF's ChemMatCARS

This fork (LSS_Reader2) is being rebuilt stage by stage: a GUI-free core
(`lss_core/`) that scripts can use, pinhole GID patching, fitting and burn
tests, scan series, a per-SPEC Excel workbook that saves every reduction,
and live updates while data are being taken.

- What has been built: `docs/ACCOMPLISHMENTS.md`
- What the program is for: `docs/PROJECT_CONTEXT.md`
- Working list: `docs/TODO.md`; plan: `docs/SCOPE.md`
- Scripting: `docs/SCRIPTING.md`; tests: `docs/TESTING.md`
- For contributors and coding agents: `AGENTS.md`

Run from the repository root: `python LSS_Reader.py`. Tests: `pytest`
(quick), `pytest -m slow` (real data), `pytest -m sweep` (crash inventory).
