# Stray light and beam-path background in pinhole GID frames (P40, DATA_NEEDS row 10)

Non-cloud data agent, 2026-11-24. Answers `docs/DATA_NEEDS.md` row 10 (TODO input 17) as far as the
private data allow. **Measured** on the private SPEC files and Pilatus 200K frames of every GID set the
reader infers (189 sets with frames, 286 Qz levels, 18 beamtimes), and on the off-specular frames of one
beamtime that were taken with the sample lowered. Nothing was checked at the beamline and no code of the
reader was changed.

**Regenerate:** the generators read private files and live with them (`sample_data/private/gid/scripts/`:
`find_sets.py` and `make_lists.py` list the sets and give them anonymous labels, `stray.py` measures the
bands per level, `stray_analyse.py` and `stray_ratios.py` pair the levels, `offspec_bg.py` and
`offspec_pairs.py` measure the sample-lowered frames, `products_row10.py <worktree>` writes this folder). The
band measurement follows `tests/tools/gid_stray_light.py` and uses the reader's own geometry
(`pinhole.frame_columns`, `s5_window`, `rows_for_beta`, `vertical_distance`). Beamtimes are labelled
B01…B18 and sets Bxx-nn in an order set by a salted hash, not by name or date. Only derived numbers are
published: band means of counts per pixel per monitor count and their ratios; no frame, profile, peak
position, file name, scan number or date.

## What row 10 asked for, and what exists

| Asked for | In the private data | Measured here |
|---|---|---|
| GID frames with little signal at both arm heights, same slits | Few. Of 94 level pairs with the same S4, S5 and absorber, 1 has no feature above 10 % of the local level at either height, 4 below 30 %, 6 below 50 %. No GID set of a bare subphase was found. | the 4–6 quietest pairs, quoted below; the band ratios on all 94 pairs (the bands beyond S5 and beyond the footprint hold no GID signal by construction) |
| Sample lowered | Not in any GID set. Three GID pairs (two beamtimes) have the sample 1.95 mm from its working height in one of the two levels. **One beamtime's off-specular frames** (fixed Det_Th 0.3°, α 0.10°, below the critical angle) include 7 scans with the sample lowered 2 mm and the same slits: a direct measurement of the beam-path background | the 6 lowered scans that have same-absorber sample scans beside them (figure R10_3, `beam_path_background.csv`) |
| S5 nearly closed at the raised arm | No. Every pair uses the same S5 at both heights (S5 3 mm low side, 14 mm high side in all 94). | — |
| Lower level repeated after the upper | Yes: 26 pairs (25 sets, 5 beamtimes). | the scan factors of the repeated level are in the large-data survey (`docs/studies/gid_method_survey/summary.md`, "Joins") |
| S4 and S5 openings, S5 → detector path | S4 0.2 mm wide (0.1 + 0.1) with S4T/S4B 51/7.3 mm in 278 of 286 levels; S5 3 + 14 mm in 253 of them and 3 + 8 mm in 25 (one beamtime, no level pair with the same slits). The other 8 levels (2–4 mm wide S4, S5 0.1 + 0.1 mm) are not pinhole GID. All at 10 keV except one set at 9.2 keV. The S5 → detector path is not recorded in the files (the reader's constants: `pinhole.S5_TO_DETECTOR_MM`). | — |

## Results

**1. The streak past S5's high edge at the raised arm (P40b) is in every beamtime, at 31× the level-arm
light there** (median of 94 pairs; 16–84 %: 13–110×; beamtime medians 7–146×). At the level arm the same
columns hold 1.5 × 10⁻⁹ counts per pixel per monitor count (16–84 %: 1.2–1.9 × 10⁻⁹), at the raised arm
5.7 × 10⁻⁸ (1.7 × 10⁻⁸ – 2.0 × 10⁻⁷). Beyond S5's low edge there is no excess (raised/level 0.77). So the
streak is a property of the high-side S5 blade at the raised arm, as P40b said from one pair, and its size
changes from beamtime to beamtime by 20× (figure R10_1). Keeping IDL's high edge on raised-arm frames (the
P39 decision) stays necessary; a fixed mask width would not fit every beamtime.

**2. Light beyond the footprint but inside S5 (P40a) is 0.41 of the usable columns' light near the
horizon at the level arm** (median; 16–84 %: 0.33–0.50; 91 levels), and 1.34× brighter at the raised arm
than at the level arm (1.17–1.54). Below the sample's horizon (β −1.5…−0.3°), where nothing from the
footprint can arrive, the usable columns still hold 1.6 % of their near-horizon light (1.1–2.6 %), and the
columns beyond the footprint 22 % (19–32 %) (figure R10_2). The near-horizon band also holds the sample's
GID signal, so these fractions understate the stray light's share between peaks; in the quietest pairs
(peak excess < 0.3, 4 pairs) the beyond-footprint band is 0.48–0.73 of the usable band.

**3. The two arm heights see the same light in the usable columns** at the same β (5–9°): raised/level
0.93 (0.86–1.02, 94 pairs). So the illumination difference between levels that P40c describes is a few
per cent in the mean; its column dependence is what each level's response absorbs.

**4. With the sample lowered, the beam path alone gives 10–14 % of an off-specular frame near the horizon
and 33–49 % at β 3–6°** (6 pairs, one beamtime; ratio to the two nearest same-absorber sample scans;
figure R10_3). The lowered frames are flat in β at 0.6–1.2 × 10⁻⁸ counts per pixel per monitor count
(mean over all columns), while the sample's off-specular scatter falls with β. This is the background that the
users' own sample-lowered scans were taken to subtract. It is not a GID measurement (fixed geometry, S4 and
S5 0.12 mm wide), so it bounds, rather than measures, the beam-path part of P40a.

**5. Sample displaced in one level (3 pairs, two beamtimes):** with the sample 1.95 mm from its working
height at the level arm, the usable columns there hold 0.10–0.29 of the raised arm's light at β 5–9°, and
30 % of their near-horizon light below the horizon (against 1.6 % normally). That is what remains when the
footprint is not where the geometry puts it: a rough upper bound on light that does not come from the
footprint.

## What it means for the reader

- **P40 stays open, with the sizes known**: (b) is universal and variable (mask it, as now); (a) is
  0.4 of the usable light at the horizon and does not depend much on the arm height; a background frame
  per beamtime would be needed to subtract it. The data hold no such GID frames; the beamline would have
  to take them (same slits, sample lowered 2 mm, both arm heights, a few Det_Th positions), as the
  off-specular users already do for their own geometry.
- **No default changes.** This is a characterisation; no reader number moves.

## Caveats

- Band means are raw counts per monitor count with no response, polarisation, area or absorber
  correction; pairs with different absorbers are left out.
- The β of each row is that of the direct-beam column (good to a few tenths of a degree away from it, as
  in `gid_stray_light.py`).
- The off-specular lowered frames come from one beamtime; their geometry differs from GID.
- Five sets could not be measured: four lack the monitor counter the reader expects, one has no frames on
  disk.

## Open questions for the owner

1. Would a beamtime take the background frames listed above (same slits, sample lowered 2 mm, both arm
   heights)? That is the only way to subtract P40a rather than bound it.
2. May the off-specular group's own background scans be cited as such (they are anonymised here)?

## Files

| File | What |
|---|---|
| `pairs.csv` | one row per same-slit, same-absorber level pair: beamtime, β0 of the raised arm, α, energy, S5, whether the lower level was repeated after the upper, the largest peak excess, band means (counts per pixel per monitor count) and ratios |
| `beam_path_background.csv` | the sample-lowered off-specular frames: per pair, elapsed hours in the file, ratio to the sample frames per β band with counting errors, absolute background |
| `R10_1_band_ratios.png` | raised/level per column band and beamtime |
| `R10_2_level_arm_fractions.png` | light beyond the footprint and below the horizon at the level arm |
| `R10_3_beam_path_background.png` | the sample-lowered frames against the sample frames |
