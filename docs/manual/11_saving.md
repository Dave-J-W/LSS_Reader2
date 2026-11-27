# 11. Saving, exporting and the workbook

[Contents](README.md) · previous: [Timeline and Compare](10_timeline_compare.md) · next: [Plots](12_plots.md)

The reader keeps results in two ways, and every result has a button for each:

- **Export** writes **text files**, in the formats fitting programs read (XModFit and others). You choose
  the name and the folder.
- **Save** stores the result in the SPEC file's **workbook**, an Excel file, with the settings that made
  it, tied to its scans, as a new version.

Reductions are also saved to the workbook by themselves, so nothing is lost if you forget.

## The workbook

`<SPEC file>_reader.xlsx`, beside the SPEC file. It has seven sheets, each with a header row and a filter,
so Excel sorts and filters them by kind, scan, version or time:

| Sheet | What it holds |
|---|---|
| Scans | Every scan of the file: number, kind (reflectivity, gid, xfntr, alignment, burn, …), command, series and its place in it |
| Saved | One row per saved result: id (R0001, …), time, kind, scans, label, version, note, the settings (as text), the program's version, the series it came from, the recipe that remakes it, whether it is out of date, and whether it was saved by a button ('user'), by itself ('auto') or remade in Live mode ('live') |
| Data | The reduced data, one row per point, under the result's id |
| Fits | One row per fitted peak, edge or line: centre, FWHM, height, area, each with its error, χ²/dof, shape |
| Trends | Burn-test trends: one row per quantity and model, with AICc, weight, parameters and the 5 % time |
| Maps | GID maps as grids: an x row, then a value row and an error row per y. Select the value block and add a colour scale to see the map |
| Settings | The current settings, the fit preferences, and the masks of dropped points |

Timeline notes and "new sample?" answers are kept in the Saved sheet too, as results of kind "note".

Only one reader at a time writes the workbook ([chapter 1](01_window.md#two-readers-on-one-file)).

### Save

Each **Save** asks for an optional note (Cancel saves nothing); **Shift-click** saves without asking.
**File → Preferences → Saving → Ask for a note on every Save** turns the question off, and then Shift-click
asks. Every Save of the same scans is a new version.

### Automatic saving

Every reduction carried through is saved by itself: a reflectivity patch, a cut and its fit, a GID map, an
MCA sum, line fit or merge, a burn test. No note is asked; the Saved sheet's origin says 'auto'. A result
identical to one already stored is not stored again, so redrawing does not pile up rows. The status bar says
what was saved. **Preferences → Saving → Save every reduction automatically** turns this off.

SpecPlot curves are raw data, not a reduction, so they are saved only by Save.

### Results that go out of date

Each saved result records its series as it was, and, when the reduction can be scripted, the call that
remakes it (its **recipe**). When the file grows (Update Specfile, or Live):

- results whose series has gained scans, or whose scans have gained points, are marked out of date (the
  Saved sheet's stale column, and a message);
- in Live mode they are also **remade** from their recipe and saved as a new version marked "live"; the old
  one is marked "superseded by R…" ([chapter 1](01_window.md#live-mode)).

Results without a recipe (SpecPlot curves, fitted MCA lines, cuts of GID maps) are only marked.

## Export

Most Export dialogs say in their title what they add to the name, for example "the name gets _flu.txt". A
name typed with that ending, or with .txt, is not given it twice. The dialog asks before replacing only the
name you typed, not the endings an export adds. After the reflectivity, GID, cut, MCA spectrum and
fluorescence exports, Messages and the status bar list the files written and any that were replaced.

### Every file the reader writes

| Written by | File | Columns |
|---|---|---|
| Reflectivity → Export | `<name>_ref.txt` | Qz (Å⁻¹), R, σ: normalised so the plateau reads 1 |
| | `<name>_rrf.txt` | Qz + Qoff, R/R_F, σ, at the Qc and Qoff in the fields |
| | `<name>_ref.cov.json`, `<name>_rrf.cov.json` | With + covariance: counting-only errors, scan of origin, the scale factors' covariance |
| GID → Export GID | `_qxy_gid.txt`, `_qz_gid.txt` (or `_dth_gid.txt`, `_beta_gid.txt`) | x, I, σ: the map integrated over the other axis |
| | `_q2d_gid.txt` (or `_agnle2d_gid.txt`) | Qxy, Qz, I, σ (or 2θ, β, I, σ): one map cell per row |
| Line/Area Cuts → Export | `<name>S# n_F# m_cut.txt`, `<name>S# n_sumcut.txt` | x, I, σ |
| MCA → Export Integral | `<name>_flu.txt` | x (frame, Qz or energy), I, σ: the reader's fit or the window sum |
| | `<name>_flu_xeray.txt` | x, I, σ: XeRay's fit, after Fit lines |
| MCA → Export Spectrum | `<name><scan>_<point>_<Qz>_mca.txt` | energy, I, σ |
| SpecPlot → Export | `<name>_<scan>_<x>_<y>[_<monitor>].txt` | x, y, σ |
| Burn test → Export | `<name>_burn.txt` | time (s), the dose when Axis is dose, each quantity and its error |
| | `<name>_burn_trends.txt` | every model: χ²/dof, AICc, weight, parameters, change time |
| GISAXS → Export GISAXS | `<name>_gisaxs.txt` | Qxy, Qz, I, σ |
| GIOXS → Export | `<name>_frame<A>-<B>_gio.txt`, `_bg_gio.txt` | Qz, I, σ |
| Plot → Export Gradient | `<name>_der.txt` | x, dy/dx |
| Fit Peak window | `_fit.txt`, `_par.txt` | the fitted curve; the parameters (nan where an error could not be estimated) |

Intensities are per monitor count and corrected for the absorbers ([chapter 2](02_normalisation.md)),
except SpecPlot's export, which writes y as plotted: divided by the N column when its box is ticked, raw
counts otherwise, and never corrected for the absorbers.
Some files begin with a `#` line saying how they were made.

## Folders

- The workbook and the per-file log go beside the SPEC file.
- Exports go where you choose. The Reflectivity tab's Export remembers the folder it last wrote to, between
  sessions; if that folder is gone, it uses the SPEC file's folder.
- The reader never writes into the SPEC file, the images or the spectra.

## Reading the workbook from a script

```python
from lss_core import workbook
wb = workbook.Workbook(workbook.path_for(spec, folder))   # <SPEC file>_reader.xlsx
wb.results(kind='reflectivity')   # rows of the Saved sheet
wb.data('R0001')                   # one result's data
wb.fits(scan=11)                   # its fitted peaks, edges and lines
```

`docs/SCRIPTING.md` ("Workbook") has more.
