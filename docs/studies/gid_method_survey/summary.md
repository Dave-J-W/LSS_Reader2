# GID patching defaults judged on the private data (hand-off 06, DATA_NEEDS row 12)

Non-cloud data agent, 2026-11-24. The final judgment that `docs/handoff_out/06-gid-method-comparison.md`
asks for, run on every GID set the reader infers in the owner's private data: **194 sets in 18
beamtimes, 882 scans, 286 Qz levels** (the public NX set is one of them). **Measured** with the reader's
own survey tool, unchanged (`tests/tools/gid_method_survey.py --split`, at the branch's `main`), in 12
processes; nothing here was checked at the beamline and no reader code was changed.

**Regenerate:** the private generators live with the data (`sample_data/private/gid/scripts/`:
`find_sets.py` and `make_lists.py` find the sets and give them anonymous labels, `run_all.sh` runs the
survey, `analyse_row12.py <survey out> <worktree>` writes this folder; about 6 h for the survey on a
network drive). Beamtimes are labelled B01…B18 and sets Bxx-nn in an order set by a salted hash. Nothing
here names a person, file, scan or date. **No peak position is published:** centres appear only as the
difference between the patched map and the single frames, widths as FWHM and ratios, and the
calibration's failure reasons as classes (the raw text can list candidate peak angles).

## Answer, decision by decision

| Decision | Now (default) | On the evidence | Recommendation |
|---|---|---|---|
| **Column response** | `fit` | `beam` has the lowest frames-agree χ²/dof on 122 of 239 levels and is within 1.40× of the best on 90 % (worst 2.85×); `fit` wins 72, median 1.13× the best, 90 % within 2.42×, **worst 14×**; `fit` and `physical+fit` degrade at low Det_Th (from < 10°: median 1.61× and 1.87×; `beam` 1.00×). Not uniform: in 3 of 15 beamtimes `fit` is better (`beam` 1.08–1.49× there). Ground truth (width ratio, centre) the same for every pinhole response. Split test: `beam` recovers 1.25 within 1 % in 37 of 38, `fit` in 34 (+0.6 % bias, median 1.257) | **Switch to `beam`** (safest worst case; best or equal in 11 of 15 beamtimes), keep `fit` as the option. Needs rule 12's tests and demonstrator first |
| **Joins** | applied | As collected (`none`), only 37 % of level joins and 29 % of scan joins are within 5 % of 1 (16–84 %: 0.93–1.21 and 0.84–1.18). ~9 % of scan joins are outside 0.5–2 with every method, on overlaps as long as the others (a different sample or setting in one inferred series, not a short overlap) | **Keep joins applied.** Show joins outside 0.5–2 as a warning |
| **S4–detector distance** | header (271 mm) unless the worksheet's Fit calibrates | 87 of 286 levels calibrate reliably (30 %), in 12 of 18 beamtimes. Calibrated: median 267.2 mm (16–84 %: 262.3–270.1), 1.4 % below the header. **Not stable within a beamtime:** in the 8 beamtimes with ≥ 5 reliable levels the SD is 1.8–6.8 mm, χ²/dof 2.3–68 about their means at the stated errors. At the calibrated distance the single frames agree better (median χ²/dof 1.95 against 4.16) and the patched peak's centre agrees with them within 2σ in 91 % of sets (header: 65 %; median \|Δ\| 0.0022° against 0.0054°). The width is the same at both (median ratio 1.011 against 1.011) | **Calibrate per set, automatically when reliable**, header otherwise; do not store one value per beamtime. A default change, so rule 12 applies |
| Footprint window | exact (P39), IDL's high edge at the raised arm | not varied by the survey tool | no judgment here; the raised-arm streak that motivates the high edge is in every beamtime (`docs/studies/gid_stray_light/`) |
| Horizontal beam FWHM (physical responses) | 1 mm | not varied by the survey tool; `physical` is the worst fitted response (median 1.70× the best; 2.72× at low Det_Th), `physical+fit` second | no judgment; the physical responses are not candidates for the default |

The **legacy** patch broadens the peak: patched FWHM / single frames 1.52 (16–84 %: 1.18–1.78) on 77
sets, against 1.01 for every pinhole response (figure R12_4). That is the strongest argument in the survey
for the pinhole patch itself.

## 1. Distance (figure R12_1, `calibration.csv`, `distance_by_beamtime.csv`)

- **Why 70 % fail:** no peak fitted in ≥ 5 single frames (70 levels); a peak but the frames disagree or
  still drift (92); every 2θ held by fewer than 6 frames because the Det_Th steps are coarse (36; median
  step 0.10°, the reliable ones 0.13°, but sets stepping 0.5° cannot calibrate by design); the best distance
  at the edge of the range tried, or poorly defined (the rest).
- **Between beamtimes** the means run from 261 to 271 mm; within one, distances scatter by more than their
  errors (χ²/dof 2.3–68 where ≥ 5 levels calibrate). Either the S4 position or the arm differs between samples, or the calibration's
  error is too small by a factor 1.5–8. The data cannot tell these apart; a per-beamtime value would hide
  either.
- **What the calibration buys:** the patched peak's centre (truth.csv: 82 sets) agrees with the single frames
  within 1σ in 63 % (header 24 %) and within 2σ in 91 % (header 65 %); its width does not change. P43's
  broadening at the header distance (one owner's set: +14 %) is not general: median width ratio 1.01 at
  both distances.

## 2. Ground truth (figure R12_4, `truth.csv`)

At the calibrated distance every pinhole response gives a patched peak 1.01–1.02 times the single frames'
FWHM (median; 16–84 %: about 0.97–1.11), with about 60 % of sets at ≤ 1.03. The handoff's criterion
(width ratio ≤ ~1.03 for every method) holds for the median but not for every set: a third are broader by
more than 3 %, under every response alike, so the cause is not the response (candidates: sample motion
during a level, the illumination slope across the peak, P40a light under it).

## 3. Response (figure R12_2, `response_by_level.csv`)

Frames-agree χ²/dof per level, divided by the best pinhole method's on that level, at the header distance
(239 levels in 177 sets; 133 levels at the calibrated distance give the same ranking):

| Response | wins | median ÷ best | 90 % ÷ best | worst ÷ best | Det_Th from < 10° (66 levels) | raised arm |
|---|---|---|---|---|---|---|
| `beam` | 122 | 1.00 | 1.40 | 2.85 | 1.00 | 1.01 |
| `fit` (default) | 72 | 1.13 | 2.42 | 14.3 | 1.61 | 1.27 |
| `physical+fit` | 46 | 1.18 | 2.39 | 32.0 | 1.87 | 1.17 |
| `physical` | 3 | 1.70 | 4.03 | 16.3 | 2.72 | 1.93 |
| `none` | 0 | 5.33 | 14.2 | 206 | 5.26 | 8.56 |

`beam` is one profile along the beam axis shared by every frame (`pinhole.beam_response`), so it
follows the light a column sees when the column-to-footprint mapping moves with Det_Th; a per-column
`fit` cannot, which is why it fails worst where that mapping moves fastest (low Det_Th). Per beamtime
`beam` is better or equal in 11 of 15; in the other 3 `fit` is better by 8–49 %.

## 4. Joins (figure R12_3, `joins.csv`)

- **Level joins** (75 with the pinhole methods; 92 legacy): as collected (`none`), the levels are a median
  3 % apart and nearly a quarter more than 20 %; with a fitted response the factor's median is 0.997 (`fit`)
  to 1.05 (`physical+fit`), with a spread as wide (16–84 % about 0.94–1.25): the levels differ for real.
- **Scan joins** (411): as collected, a median 1 % apart but 16–84 % at 0.84–1.18.
- **Repeated level** (the lower level measured again after the upper, 21 scan joins in 26 pairs of the
  stray-light study): the repeat differs by a median 4.7 % (`beam`), against 3.7 % for all scan joins: a
  measurable change in time, which joins should take up and not hide.
- **18 sets** (in 7 beamtimes) cannot be patched by any pinhole method: "the middle Qz does not
  overlap in β with the levels below it". The legacy patch handles them (it joins by Qz). That is a gap in
  the pinhole patch worth a look (follow-up).

## 5. Split test (figure R12_3, `split.csv`)

38 single-scan levels of ≥ 30 frames cut in two, the second half × 0.8: every method recovers 1.25
(medians 1.244–1.257). `beam` and `physical+fit` are within 1 % in 37 of 38; `fit` in 34 (median 1.257);
`none` 1.244. The halves join at 1.000 under `beam` (16–84 %: 0.992–1.009) and 0.990 under `fit`: the
scans did not change measurably along their length, and `fit`'s 1 % is the response taking up part of the
scale (P42's residue).

## Proposed rows for `docs/OUTPUT_DECISIONS.md` (not applied: rule 12 comes first)

| Decision | Before | After | Evidence |
|---|---|---|---|
| GID column response default | `fit` | `beam` | this study: frames agree median 1.00× the best (fit 1.13×), worst 2.85× (fit 14×), low Det_Th 1.00× (fit 1.61×); split within 1 % 37/38 (fit 34/38); ground truth equal |
| S4–detector distance | header unless the worksheet's Fit is pressed | calibrated per set when `calibrate_distance` is reliable, header otherwise; the result and its error shown | this study: reliable on 30 % of levels; the patched centre within 2σ of the single frames 91 % (header 65 %); per-beamtime storage not justified (spread beyond errors) |

The re-pins each needs (tests that pin `fit` numbers on synthetic and NX data) are for the session that
makes the switch; this study does not change them.

## Caveats

- One set is one inferred series (consecutive `ascan dth` scans with frames): it can join scans of
  different samples or settings, which is the likeliest reason for the 9 % of wild scan joins.
- Frames-agree χ²/dof is the handoff's criterion; it rewards a response that explains the frames, not
  one that is physically right. The ground truth (single frames) separates responses not at all here.
- 5 sets give no result: 4 hold a one-point Det_Th scan, which makes `Experiment.frames` raise
  `KeyError: 'monc'` (a reader defect, follow-up), and 1 has no frames on disk. 2 more lost only their split
  test, to errors of the legacy patch on a half-scan.
- The survey does not vary the footprint window or the horizontal beam width.

## Files

| File | What |
|---|---|
| `calibration.csv` | per set and level: β0, Det_Th step, reliable, calibrated distance ± error, header, frames, χ²/dof and drift at both distances, single-frame FWHM, outcome class |
| `distance_by_beamtime.csv` | per beamtime: reliable levels, weighted mean distance, error, SD, χ²/dof, range |
| `truth.csv` | per set, distance and method: single frames' χ²/dof and FWHM, patched FWHM, width ratio, centre difference (deg and σ) |
| `response_by_level.csv` | per level and distance: Det_Th range, β0, frames-agree χ²/dof of every pinhole response and its ratio to the best |
| `joins.csv` | every fitted join: kind, method, distance, overlap range (Det_Th settings), points, factor, error, χ²/dof |
| `split.csv` | the split test per level and method |
| `numbers.json` | every number quoted above |
| `R12_1_distance.png` … `R12_4_truth.png` | the four figures |
