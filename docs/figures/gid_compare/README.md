# GID patching before/after: legacy 3-column patch vs pinhole geometry

The owner asked (2026-11-19) to see "the before/after on a big GID patch
using the pinhole mode versus the old way". These figures put the legacy
patch (`GIDParams(pinhole=False)`: 3 columns at the direct beam, one 2θ
per frame, interpolated joins) beside the pinhole-geometry patch (the
default: every usable column at its exact per-pixel 2θ and β, joins on
summed counts) for the same scans. Comparisons C10, C14, C21 and C22 in
`docs/COMPARISONS.md`. Only public NX school data are here; the same
figures for the owner's private scans (163 + 165, 386–389) are made
outside the repository.

Made with

    python tests/tools/gid_compare_figures.py --scans 11 --out docs/figures/gid_compare
    python tests/tools/gid_compare_figures.py --scans 11,12 --peak none \
        --note "not like for like: scan 12 stopped after 4 frames" --out docs/figures/gid_compare

(the script uses only `lss_core.experiment`, i.e. the window's code; it
refuses to write private data into the repository).

## Files (per scan set)

| File | What it shows |
|---|---|
| `nx_S11_maps.png`, `nx_S11+12_maps.png` | The two Qxy–Qz maps side by side, same axes, one log colour scale. The legacy map is multiplied by k (below) because it is in other units (a 3-column sum against a per-pixel mean). Hatched: no data. Thin lines: the overlaps where join factors were fitted. On 11 + 12 the legacy map's region filled with copies of scan 12's edge column (P33) is outlined, and the pinhole map's narrower range (only the 2θ range both Qz levels have, IDL rule, F62) is labelled. |
| `nx_S11_profiles.png`, `nx_S11+12_profiles.png` | Left: the Qxy profile (∫ I dQz over the Qz range both maps have); right: the Qz profile (∫ I dQxy over the common Qxy range). Top: both methods with ±1σ bands. Middle: ratio pinhole / (k × legacy) on common bins. Bottom: σ/I per bin of each method and of the pinhole profile summed to the legacy bins (equal resolution); the panel title gives the median ratio of the relative errors on equal bins and the gain in counts it implies (its square). The largest Qxy maximum is fitted with a Gaussian on a line in the shaded window (11 only). |
| `nx_S11_joins.png`, `nx_S11+12_joins.png` | Where each join was fitted (2θ overlaps, β overlap of the Qz join), the factors ± errors with χ²/dof, and the summary table (bins, Qxy and Qz ranges, raw counts used, peak position and FWHM, σ/I at the peak, join factors, k). Scan 11 alone has no join. |
| `*_summary.json` | The numbers of the table, the joins and levels of both methods, k, the common ranges and the command. |

Regenerated 2026-11-20 after the P39 fix (exact footprint window, D51):
the pinhole map of scan 11 reaches 2θ 19.93° (was 19.82°), 177 Qxy bins
(was 174), 5.65e5 raw counts (was 5.47e5), peak FWHM 0.0155 (was 0.0157);
the 11 + 12 Qz join is 1.068 ± 0.013 (was 1.097). Regenerated 2026-11-23
after P46 (the join factor by likelihood): the 11 + 12 join is
1.088 ± 0.014; the scan-11 figures are unchanged.

## How to read them

- **k** is fitted over the lowest Qz level and the common Qxy range,
  which neither method rescales, so the higher level shows how the two
  joins differ. k ≈ 0.38–0.55 because the legacy map sums 3 columns while
  the pinhole map is a per-pixel mean (plus different corrections).
- **Raw counts used**: legacy, the counts in its 3-column window (rows
  15–486) of every frame; pinhole, `info['levels'][…]['counts_used']`.
- **σ/I on equal bins** is the fair comparison of statistics: the pinhole
  profile is summed to the legacy bins (each fine bin's integral and
  variance shared by overlap, as Poisson counts), so the resolution is the
  same and only the counts differ.
- **Join factors** of the two methods are not comparable as numbers: each
  multiplies its own unjoined level, normalised differently. Compare the
  joined profiles (ratio panels) instead.
- **11 + 12 is not like for like**: scan 12 stopped after 4 frames
  (2θ 13.4–15.8°), so the pinhole map keeps only that range and misses the
  DPPC peak, while the legacy map fills the rest of the higher level with
  edge copies (P33): its Qz profile above the join is the noise of those
  copies, not data.

Scan 11 (one level): DPPC peak Qxy 1.4663 ± 0.0004 (legacy) and
1.4665 ± 0.0001 Å⁻¹ (pinhole), FWHM 0.0180 ± 0.0009 vs 0.0155 ± 0.0002 Å⁻¹
(fit window 1.424–1.512), 40 vs 177 Qxy bins, 3.2e4 vs 5.65e5 raw counts;
σ/I at the peak 2.55 % vs 1.02 % per own bin, 0.66 % on the legacy bins;
relative errors on equal bins 3.8× smaller (≈ 15× the counts).
