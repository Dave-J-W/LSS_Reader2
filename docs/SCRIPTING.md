# Scripting the reduction

The `lss_core` package reads SPEC files and images and reduces them
without the window and without Qt. It is the same code the window uses,
so a script gives the same numbers as the GUI. For reflectivity this is
checked byte for byte against files saved by the window
(`tests/test_api.py`).

Run scripts from the repository folder, or put that folder on `sys.path`.

## Reflectivity

```python
from lss_core.experiment import Experiment

exp = Experiment('sample_data/NX_school/2026sep/20260923')
result = exp.reflectivity([6, 7, 8, 9])
result.save('dppc')                     # dppc_ref.txt and dppc_rrf.txt
```

Options, with the window's defaults for Pilatus data:

| Option | Default | Window control |
|---|---|---|
| `slit=(21, 11)` | 21 × 11 pixels | Slit |
| `bg_offset=0.5` | degrees | BG offset |
| `direction='H'` | `'H'` or `'V'` | BG direction |
| `qc=0.0217` | Å⁻¹ | Qc |
| `qoff=0.0` | Å⁻¹, R/R_F only | Qoff |
| `norm_factor=None` | extra division | Norm. factor box |
| `rrf=True` | also compute R/R_F | R/RF box |
| `drops={0: [-1], 2: [0, -1]}` | none | "Drop" in the patch dialog, per join |
| `merge_repeats=False` | | "Merge" in the identical-scans dialog |
| `low_qz_slit=False` | | Low Qz Corr. |
| `merge=[[2, 3]]` | | groups merged in the identical-scans dialog |
| `points={7: [0, 1, 3]}` | all points | frames selected in the image list |
| `bad_pixel_iterations=0`, `bad_pixel_factor=1` | | BPC iterations, factor |

`result` holds the per-scan points (`per_scan`, columns Qz, net signal,
error, signal, signal error, background 1, background 2), the scan order,
the patched curve before normalisation, `ref`, `rrf`, and the frames whose
beam was more than 2 pixels from its recorded position (`beam_offsets`).

Not yet available from scripts: background images, single-scan export,
GID, GISAXS, cuts, burn tests, peak fits. They follow in Stage 2.

## Fluorescence (XFNTR)

```python
exp = Experiment('sample_data/bu/2026sep/20260902')
flu = exp.fluorescence([74, 75, 76, 77, 78, 79], window=(1, 1000))
flu.save('zinc', x='qz')               # zinc_flu.txt, as "Export" in the MCA tab
```

`window` is the "Sum" range (energy with the file's calibration);
`monitor` is `'Monc'` (default), `'Monb'`, `'Mond'` or `None`;
`calibration=(c0, c1, c2)` overrides the file's; `absfac` (default
1.4247, 50 µm Al at 10 keV, `lss_core.absorbers`) is the transmission factor per absorber unit: normalised spectra
are multiplied by absfac**n, n the scan's absorber setting, which for
`getandsave_mca` scans is the last `#A` above them in the SPEC file
(`exp.scans[n].parameters['AbsorberFrom']` names that scan; no `#A` above:
no factor).
The normalised value is N · (t_real/t_live) · absfac**n / M per channel:
proportional to fluorescence per photon on the sample while the monitor
gain, energy and geometry stay the same (`physics_notes.md`, 2026-11-17;
the monitor gain is not yet included, F52). `flu.spectra` holds the
normalised spectra, `flu.rows` the [frame, Qz, energy, intensity, error]
rows. Checked byte for byte against the window's `_flu.txt` on synthetic
and real data.

## Error model

Both `reflectivity` and `fluorescence` take `errors=`: `'legacy'` (the
default, the window's numbers byte for byte) or `'budget'`, or a dict with
the monitor model:

```python
ref = exp.reflectivity([6, 7, 8, 9], errors='budget')    # monitor: Gaussian, 0.04 %
ref = exp.reflectivity([6, 7, 8, 9],
                       errors={'mode': 'budget', 'kind': 'student_t',
                               'sigma_scan': 0.00039, 'width': 0.94, 'nu': 4.0})
ref = exp.reflectivity([6, 7, 8, 9],
                       errors={'mode': 'budget', 'kind': 'counting', 'f': 0.0, 'sigma_dark': 0.0, 'g': 10.0})
```

Budget applies the monitor's relative uncertainty once to each whole sum
of a frame (`lss_core/errors.py`, `docs/reports/error_propagation.md`).
The default, a Gaussian of 0.04 % at every count, and the Student t
(scale width × σ_scan, ν = 4) describe the present `Monc` electronics
(SR570 + V2F). The window's
Errors pane sets the same model, and the Script pane writes the matching
`errors=`.

## The Script pane

The window has a "Script" pane (bottom, next to Messages). Opening a
SPEC file, exporting a patched reflectivity and exporting fluorescence
intensities add the equivalent Python
there, with every setting, merge and drop the user made; running it writes
the same files. It is also written to the log.

## Lower-level pieces

| Module | What |
|---|---|
| `lss_core.experiment` | `Experiment`: scans, frames, reflectivity |
| `lss_core.reflectivity` | per-frame signal, scan ordering, merging repeats, drops, patching, normalisation, saving |
| `lss_core.fluorescence` | spectrum normalisation, window sum, `_flu.txt` |
| `lss_core.normalise` | monitor and absorber normalisation of a frame |
| `lss_core.stitching` | joining two curves (`join`), Fresnel reflectivity |
| `lss_core.images` | `read_pilatus`: fast, cached, bit-identical image reading |
| `lss_core.cache` | the memory cache (budget from `LSS_READER_RAM_CACHE_MB`) |
| `lss_core.numbers` | number parsing for SPEC/MCA text, without `eval` |
| `spec_routines.specread` | the SPEC reader (no Qt needed) |
