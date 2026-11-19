# Method comparisons: old against new

For the agent who will make figures comparing the reader's new methods
with the old ones across data sets (owner, 2026-11-19). One row per
comparison. Each row says what was compared, on which data, what was
found, **how the result is known** (test, tool run, or reading only), and
how to regenerate it. Details and dates are in `physics_notes.md`; the
row links the entry.

Started 2026-11-19 from the records up to then. Rule (AGENTS.md rule 11):
a commit that adds or changes a method adds or updates its row here.

## How to run old and new side by side

Every new method has a switch that gives the old one back. Use these in
scripts (`docs/SCRIPTING.md`); the window has the same switches.

| Method | Old | New | Switch (script / window) |
|---|---|---|---|
| Error bars | Legacy per-pixel formula | Budget (monitor term on whole sums) | `errors=None` / `errors={'mode': 'budget', ...}` (the Script pane writes the full form); Errors pane |
| Monitor uncertainty (budget) | counting model (Poisson-like, g) | Gaussian 0.04 % (default), or Student t | the `errors=` dict; Errors pane |
| Absorber factor | 1.606 typed (original), then 1.4247 | Calibrated foils at 9.70–10.30 keV; nominal Al elsewhere | `absfac=1.4247` / `absfac=absorbers.calibrated(10.0)`; Preferences "calibrated foils", Absorber field "from E" |
| Patch factor | Fitted on the overlap | Known foil ratio when the fit is poorer | `reflectivity(factors=None)` / `factors={join: (k, σ)}`; Preferences "use known ratio", threshold |
| Monitor normalisation | Counts M | M·S/(5 µA/V); per incident photon | `monitor_gain=True`, `per_photon=True`; "/ gain", "/ photon" |
| GID columns | Legacy 3-column patch | Pinhole geometry, angle per column | `exp.gid(scans, params=GIDParams(pinhole=False))` / `exp.gid(scans)`; GID worksheet |
| GID Qz levels join | Legacy vertical join (`imagevjoin`, interpolated) | Shared 2θ grid, common β grid (`pinhole.join_levels`) | follows the pinhole switch; range `transverse='intersection'`/`'union'`, worksheet "2θ range across levels" |
| Cuts' horizontal distance | Sample–detector (551 mm) | S4–detector (271 mm) at Det_Th > 1° | `cut(pinhole=False)`; Line/Area Cuts "pinhole" box |

The legacy reductions are also frozen as byte-exact fixtures
(`tests/reference/legacy_export/`, `tests/legacy/`); they are the "old"
curves for the NX school data.

## Data sets

| Name | Where | May be shown? |
|---|---|---|
| NX school (2026-09-23) | `sample_data/NX_school/` (committed) | yes |
| Synthetic (known truth) | `tests/synth.py` generators | yes |
| bu (owner's runs, 2026 June–Oct) | `sample_data/bu/` (git-ignored) | **no**: figures stay local; commit nothing derived but SHA-256 |
| Private GID (scans 136–146) | `sample_data/private/` (git-ignored) | **no**; dates removed |
| Owner's absorber-join set (hand-off 02/03) | answers in `docs/handoff_out/03-answer/` | yes, as published there |

## Ledger

Kind of evidence: **T** a test asserts it (re-run with pytest); **R** a
tool or a one-off run measured it (numbers in the notes, command given);
**C** reported in chat only (private data; re-run locally); **D** derived
or read, not measured.

| ID | Comparison | Data | Result | Evidence | Figure-ready data | Regenerate | Notes entry |
|---|---|---|---|---|---|---|---|
| C1 | Refactored reduction vs original program (Ref Patch, `_ref`/`_rrf`) | NX school 6–9; synthetic | byte-identical | T | fixtures in `tests/reference/legacy_export/` | `pytest -m slow tests/test_real_nx_school.py` | 2026-11-17 Stage 1/2 |
| C2 | Budget vs legacy error bars, σ ratio per frame | NX school 6–9 | budget (counting monitor model, g = 1) ÷ legacy: median 1.03, max 1.74 (Qz 0.0187); values move ≤ 4e-5 | R | `C2_ref_nx_*` (final `_ref` curve, all three models) | `compare_methods.py` | 2026-11-17 "error budget, built" |
| C3 | Budget (Gaussian 0.04 %; Student t) vs legacy σ | NX school 6–9 | per frame: Gaussian 0.86–1.03 (median 1.00), t 0.92–1.08; final `_ref` (2026-11-19): Gaussian 0.861–1.002, t 0.893–1.004; values move < 5e-6 | R | `C2_ref_nx_*` | `compare_methods.py` | 2026-11-17 "Monitor uncertainty decided" |
| C4 | Monitor-noise Monte Carlo: legacy formula vs budget | simulated | defects roughly cancel at g = 10 | R | `tests/tools/monitor_noise_mc.py` output | `python tests/tools/monitor_noise_mc.py` | `docs/reports/monitor_noise.md` |
| C5 | Absorber factor 1.606 (original default) vs 1.4247 (50 µm Al) | — | ×(1.4247/1.606)ⁿ on any non-patched output | D | — | — | 2026-11-17 "50 µm Al" |
| C6 | Nominal 1.4247ⁿ vs calibrated foils | 10 keV | n = 3: 2.892 → 3.259 (+12.7 %); full table in ABSORBER_RATIOS | T, R | `C6_absorber_factors_10keV.csv` (n = 0–63); `docs/handoff_out/03-answer/figdata/` | `pytest tests/test_absorbers.py tests/test_foil_fit_from_joins.py` | 2026-11-18 "Calibrated foils in the reader" |
| C7 | Fitted patch factor vs known foil ratio, per join | owner's joins (hand-off 03); synthetic | step errors before → after: 42→33 1.23 % → 0.86 % (low Qz) / 2.75 % (high Qz) | T, R | `docs/handoff_out/03-answer/joins.csv`, `figures/` | `python tests/tools/absorber_steps.py`; `pytest tests/test_known_ratio_patch.py` | 2026-11-18 "How far the absorber ratios can be trusted" |
| C8 | Nominal absorber steps vs measured (P28) | NX school | 7–11 % off | R | no | `python tests/tools/absorber_steps.py SPEC scan,scan,...` | 2026-11-18 "Binary foil set" |
| C9 | Monc/Monp across slit changes (P29) | owner's joins | Monc registered ×1.55–1.62 instead of ×2.0–2.3 | R | `03-answer/joins.csv` | `tests/tools/monitor_ratio.py` | 2026-11-18 "Answer to hand-off 02" |
| C10 | Legacy 3-column GID vs pinhole geometry | NX scan 11 (public); private 137/139 | ~17× the counts; scan 11: DPPC peak Qxy 1.4631 (legacy) vs 1.4679 1/Å (pinhole), 40 vs 174 Qxy bins (176 before the exact geometry), error at the peak 2.5 % vs 1.0 %; private: ×23–24 counts, join 0.952 ± 0.002 | R (NX), C (private) | `docs/comparisons_data/C10_*` (Qxy, Qz integrals; maps regenerable) | `python tests/tools/compare_methods.py` | 2026-11-18 "Pinhole-geometry GID built"; 2026-11-19 "GID scriptable" |
| C11 | Pinhole distance: header 271 mm vs fitted | NX scan 11 | fit 258–280 mm depending on columns (±2–3 mm each); peak Qxy 1.4695 / 1.4679 / 1.4665 at 258 / 271 / 280 mm (exact geometry; 1.4666 at 280 before) | R | `C11_*` | `compare_methods.py`; worksheet Fit | same entry |
| C12 | Pinhole binning vs near-sample mapping (synthetic line) | synthetic | one bin vs > 5 bins; unbiased 1.00 ± 0.01 | T | — | `pytest tests/test_pinhole.py` | same entry |
| C13 | Pinhole Qz-level join: summed counts vs equal-weight cells | synthetic, factor 1.25 | 1.283 (biased) → 1.25 ± 0.0004 | T | — | `pytest tests/test_pinhole.py -k join` | 2026-11-19 "Joining Qz levels" |
| C14 | Legacy vertical join vs pinhole join | NX scans 11 + 12 | not like for like on this pair: scan 12 stopped after 4 frames (2θ 13.4–15.8°), so the pinhole "common" range ends there and misses the DPPC peak (16.65°); the legacy join fills 14–18° with copies of scan 12's edge (P33) | R | `C10_gid_nx_S11-12_*` | `compare_methods.py` | 2026-11-19 "GID scriptable" |
| C15 | Pix V cut β: cut distance vs sample distance (P34) | geometry | top row 15.46° → 7.79° | T | — | `pytest tests/test_cut_script.py -k pix_v` | 2026-11-18 "Pinhole is the default" |
| C16 | Monitor gain option on vs off | synthetic; bu (gains) | ×S_ref/S; one flux at two gains equal (I18) | T | — | `pytest tests/test_monitor_gain.py` | 2026-11-17 "Foils at other energies; monitor gain" |
| C17 | Per photon vs per count | synthetic | ×M/N; I20 | T | — | `pytest tests/test_per_photon.py` | 2026-11-19 "per incident photon" |
| C18 | Unknown `#A` as 63 vs unknown (no factor), patched | synthetic | patched `_ref` equal (rel 1e-6) | T | — | `pytest tests/test_absorber_unknown.py` | 2026-11-19 "unreadable `#A`" |
| C19 | XFNTR before/after absorber scaling | bu 74–79 | hash `77be46ea…` → `e23206a9…` → `1cfab3ab…`; ×absfacⁿ | R (hashes only) | no (private) | `pytest -m slow tests/test_real_bu.py` | 2026-11-17 "Was XFNTR scaled by absorbers before?" |
| C20 | Image reading speed old vs cached | NX, bu | frame 5.5 → 0.7 ms (100K); 378 → 0 file opens | R | `docs/timings.md` | `pytest -m bench -s` | 2026-11-17 "images are read once" |
| C21 | Pinhole angles per axis vs exact per pixel (IMG_COO_CONV) | NX 11; NX 11+12; synthetic | inside each frame's usable columns β off by ≤ 0.41° (arm level) / 0.74° (β0 = 6.5°), 2θ ≤ 0.04°; NX 11 map nearly unchanged (peak +0.002°); NX 11+12 level factor 1.029 → 1.097, join χ²/dof 1.31 → 0.83; a line at fixed β stays in one β bin (was spread over > 10 rows) | T, R | `C21_*` (Qxy and Qz integrals, per axis and exact) | `pytest tests/test_pinhole.py`; the per-axis arrays were made with the commit before the change (34c33c8) | 2026-11-19 "Is the pinhole trig exact?" |

## Gaps (what the figure agent will not find yet)

- `tests/tools/compare_methods.py` writes C2/C3, C6, C10, C11 and C14 as
  CSV with a header line and `manifest.json` (2026-11-19). Run it with
  `--spec`, `--ref`, `--gid` on other data sets; private data to a folder
  outside the repository. Each CSV's first line names comparison, method,
  data and columns.
- C14 needs a public GID pair whose high-Qz scan is complete; NX 11 + 12
  is not (scan 12 stopped).
- Private-data comparisons (C10 private, C19) can be plotted only on the
  owner's machine; nothing derived goes in the repository.
- Not compared at all yet: Student t vs Gaussian at the level of a
  finished `_ref` curve; calibrated foils vs nominal on a whole unpatched
  cut series; per-photon values across energies on real data.
