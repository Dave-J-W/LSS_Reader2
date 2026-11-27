# Glossary

[Contents](README.md)

| Term | Meaning |
|---|---|
| **absfac** | The absorbers' transmission factor per unit: a frame at absorber setting n is multiplied by absfacⁿ. The Absorber Ratio field ([chapter 2](02_normalisation.md#absorbers)) |
| **absorber setting** (`#A`) | The binary foils in the beam, in units; 0 is none |
| **AICc** | Akaike's information criterion for small samples: how well a model fits, penalised for its number of parameters. Lower is better; a difference below 2 cannot tell two models apart. QAICc is the same when the scatter exceeds the errors |
| **α, β** | The incidence angle and the exit angle, both from the surface. At the specular reflection β = α |
| **β − α** | The exit angle relative to the specular: the axis for diffuse scattering beside the reflected beam |
| **burn test** | Repeated exposures at one condition, to see whether the beam changes the sample ([chapter 9](09_burn_tests.md)) |
| **calibrated foils** | The absorber foils' thicknesses measured from real joins at 10 keV, used at 9.70–10.30 keV ("cal" in the field) |
| **column response** | How much light each detector column records, relative to the others, for the same scattering; corrected in GID patching ([chapter 6](06_gid.md#the-column-response)) |
| **counted box** | The signal box (white) and the two background boxes (cyan) summed for each reflectivity frame; Slit(H,V), BG Dir, BG Offset |
| **Det_Th** | The detector arm's in-plane angle. A GID scan sweeps it |
| **direct-beam pixel** | Where the direct beam would hit the detector at the frame's arm position |
| **dose** | Photons (or monitor counts) received by the sample since the first frame, with the absorbers taken out; per mm² of footprint when the beam's size is known |
| **dose per mm² of footprint** | The dose divided by the area the beam lights on the surface |
| **fast mode** | The shutter kept open between frames, so the sample is lit for the wall time, not only the exposures |
| **footprint** | The strip of surface the beam lights: long, at grazing incidence |
| **frames agree χ²/dof** | How well the frames of one GID level agree once patched; the yardstick for comparing GID methods |
| **Fresnel reflectivity R_F** | The reflectivity of an ideal, sharp surface of the subphase; R/R_F shows what the surface adds |
| **join** | Where two scans of a reflectivity (or two GID scans or levels) overlap, and the scale factor fitted there |
| **joint fit** | The default join: one smooth curve through both scans, with the factor fitted together with it |
| **kind of frame** | Reflectivity, GID, GISAXS, direct beam, dark: the display remembers settings per kind |
| **known ratio** | The calibrated foils' attenuation between two absorber settings, used at a join instead of the fit when the fit is poor ([chapter 5](05_reflectivity.md#the-known-ratio)) |
| **level** (Qz level) | All GID frames taken at one arm height; a higher level reaches higher β |
| **mask** | Points dropped in a Ref Patch, kept in the workbook and left out of the next patch of the same scans |
| **Monc, Monp, Monb** | Ionisation-chamber monitors recorded by SPEC. Monc, upstream of the absorbers, is the one the reader divides by |
| **effective monitor** | Monc divided by the absorber factor and, with / gain, by the gain: what a frame is normalised by |
| **patch** | Joining the scans of a reflectivity (Ref Patch) or a GID set (GID Patch) into one curve or map |
| **pinhole** (S4) | The slit in front of the GID detector that makes each column see one 2θ |
| **plateau** | The reflectivity below the critical edge, where R is 1; Norm Ref divides by its highest point |
| **Poisson error** | √N for N counts: the error of counting |
| **pull** | (estimate − truth)/error. Honest errors give pulls of spread 1 |
| **Qc** | The critical wavevector of the subphase, below which the beam is totally reflected (water: 0.0217 Å⁻¹) |
| **Qoff** | A small offset added to Qz before dividing by R_F, for an angle offset |
| **Qz, Qxy** | The wavevector transfer across and along the surface, in Å⁻¹ |
| **recipe** | The `lss_core` call stored with a saved result, from which Live mode remakes it |
| **residuals** | (data − fit)/σ at each fitted point: within about ±2 for a good fit with the right errors |
| **S1, S4, S5** | Slits: S1 before the sample (sets the beam's size), S4 the GID pinhole, S5 in front of the detector |
| **series** | The scans one experiment macro took together ([chapter 1](01_window.md#the-left-panel)) |
| **spot** | One place on the sample (positions within half the beam's width count as one), for the timeline's dose |
| **stable** | A burn test in which a constant fits as well as a line |
| **strip scatter ρ** | How much a burn's rate differs between spots of one sample at one flux, beyond counting |
| **sx, sh, oh** | The sample's x position; the sample height; the output height (Out_Ht), which moves with sh in height scans |
| **super-Gaussian** | exp(−|x|ᵖ): p = 2 a Gaussian, larger p flatter-topped; fitted to sample-height scans |
| **the 5 % time** | The time (or dose) until a burn's quantity changes by 5 %, as a 95 % confident lower bound |
| **2θ** | The in-plane scattering angle |
| **workbook** | `<SPEC file>_reader.xlsx`: every saved result of a SPEC file, with its settings ([chapter 11](11_saving.md)) |
| **workbook lock, write access** | Only one reader at a time writes a workbook; others are read-only ([chapter 1](01_window.md#two-readers-on-one-file)) |
| **XeRay** | The Lee group's fluorescence program; the reader shows its line fit beside its own ([chapter 8](08_fluorescence.md)) |
| **XFNTR** | X-ray fluorescence near total reflection: fluorescence against Qz across the critical edge |
| **`#B1`, `#G0`** | SPEC header lines with the beamline's geometry (distances, the direct-beam pixel); the reader takes the S4–detector distance from `#B1`'s fourth number |
