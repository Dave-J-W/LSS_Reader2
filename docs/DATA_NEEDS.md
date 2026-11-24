# Data the project is waiting for

One place for every dataset a work item needs and the repository does not
hold. Written 2026-11-23 on the owner's instruction: the owner will have a
**non-cloud agent** work on the large private datasets, so each need is
stated here so that agent (or any other) can find it, check it against the
data it has, and say what it supplies.

**How to use this file.** Find the row, read the data wanted, produce the
result in the form named in "Returned as", and put it where "Goes in" says.
Private data stays under `sample_data/private/` (git-ignored); only derived
numbers may appear in the documents, never peak locations, raw data or
images (owner, 2026-11-19; `AGENTS.md`). Public data may be committed.
Record what a dataset answered in `docs/physics_notes.md` (dated, with how
it was verified) and tick the row here and in `docs/TODO.md`.

Status as of 2026-11-23. Source documents are named so that nothing here
has to be believed on its own.

| # | Need | Data wanted | Returned as | Goes in | Blocks | Source |
|---|---|---|---|---|---|---|
| 1 | **Real reflectivity series with many joins** (the real test of the joint-fit patch, hand-off 08) | Many real reflectivity series, each with several joins and overlaps; the NX school scans 6–9 (3 joins) are the only real ones in the repository and the private `bu` set has none | The comparison hand-off 08 describes (`docs/handoff_out/08-ref-patch-comparison.md`) | `sample_data/private/`; derived numbers in `docs/reports/` | Confirming the joint fit as default on real data; B2 decisions Study A (2026-11-24, C48) found these data **not needed** for the guard decision (raise p to 0.7, or keep 0.3): the ranking holds over 3–10 points per fringe and flux 1–0.01, and the choice moves a structural fit by about 0.001 Å. Here they would confirm, and could reverse it only if fit and foil ratio disagree at real joins. | owner 2026-11-23: "not soon", by the non-cloud agent; `TODO.md` B; C36 |
| 2 | **Per-point MCA files / `#V` question** (area C) | One SPEC file with its folders for one energy scan (`MCAscanpt escan_14` or another `escan`) and one fluorescence burn (`ascan ih` with spectra), with the MCA files beside them (`vortex/`, `<date>_<scan>_mca`) | A statement of whether each scan's SPEC block has a `#V` line with spectra, or only `mca_save_point Point:p Scan:s` entries with separate files | `sample_data/private/` | Per-point MCA reading, EXAFS, fluorescence burns (F89) | `TODO.md` "Waiting on the owner"; Q-EXAFS-2 |
| 3 | **MCA fit gauntlet spectra** (F90) | **Owner, 2026-11-23: there will be no zinc data; other elements and blank spectra will be supplied.** Spectra with a strong elastic (Rayleigh) peak and Compton shoulder beside a weak line (Zn Kα 8637 eV under 10 keV excitation is the hard case the owner named; the nearest real case supplied stands in for it), with the detector's energy calibration; more cases if available. **Also a blank spectrum** (pure water, or the subphase without the element) taken at the same Qz (or Qz series), beam energy, detector position and counting time as the sample's spectra (added 2026-11-23 at the tools session's request) **Study B (2026-11-24, `docs/studies/mca_fit/summary.md`) settles what the blank must answer:** the O 1s Compton wing (counts below the Compton peak once its valence part is fitted) and the Si escape fraction (the elastic's escape peak over the elastic), at the beam energy used; one blank per energy and geometry checks the generator's two uncertain axes (B7). P1 and the verdict on the window sum need no real data. | Real spectra for the gauntlet in `tests/` and the fit's success rate against the scatter; the blank beside the sample spectra, with the energy calibration. **Why the blank:** the window sum and the line fit both fail when the scatter under the line has structure the polynomial background cannot follow; under Zn Kα at 10 keV that is the elastic line's Si escape peak at 8.26 keV and the O 1s wing of the Compton scatter. Their sizes in the synthetic generator (`tests/synthetic/mca.py`, `tests/tools/mca_fit_gauntlet.py`) are from memory (Reed's escape fraction about 0.1 %, a hydrogenic impulse-approximation profile); a blank measures the scatter directly, so the generator can be checked and a blank subtraction or template tested on real data | `sample_data/private/` (public if allowed) | Retiring the window sum (F90) | owner 2026-11-23, Q5 |
| 4 | **GISAXS example** and **GIOXS example** (F104; GIOXS = grazing-incidence off-specular scattering, the diffuse scatter around the specular beam, as in a reflectivity experiment) | One real GISAXS data set and one real GIOXS data set, with SPEC files | Examples for the requirements interview and for tests | `sample_data/private/`; no public series exists (P35) | F104 (upgrade of both) | owner 2026-11-23: "will provide later with non-cloud agent" |
| 5 | A complete low + high Q_z GID pair, **public** | A public pair (private pairs were received 2026-11-19, C22) | Comparison C14 on public data | `sample_data/` (committed) | C14 like-for-like; F62 on real data | `TODO.md` inputs #2 |
| 6 | Full two-module 200K frame; new-format fluorescence/GID SPEC file (F28); HDF5/bluesky file (F29); ME7 notes (F35); Pilatus + Vortex in one scan (F53); 1M geometry (F38) | As named | Stage 4 readers | `sample_data/private/` | Stage 4, item by item | `TODO.md` inputs #3 |
| 7 | `lss_reference.py`, `covariance_core.py` from XModJointFit (unreleased) | The two files | Hand-off acceptance tests 5 and 6 | `tests/` | Stage 5 hand-off tests 5–6 | `TODO.md` inputs #4 |
| 8 | Reflectivity series with overlaps at 6–7 keV; foil tolerance and alloy; Cu thickness at 30 keV | As named | P28 below 10 keV, F49 at 30 keV | `sample_data/private/` | Foil factors | `TODO.md` inputs #8 |
| 9 | Half-cut sh scans for the beam's vertical profile (F43) | Half-cut sh scans | The measured beam for the response `beam` and for P39 | `sample_data/private/` | Beam size | `TODO.md` inputs #16 |
| 10 | GID frames with little signal at both arm heights, same slits, sample lowered if possible, S5 nearly closed at the raised arm, lower level repeated after the upper, S4 and S5 openings and the S5 → detector path (P40) | As named | Stray light and beam-path background | `sample_data/private/` | P40 | `TODO.md` inputs #17 |
| 11 | A reflectivity burn scan | A burn scan at several absorbers | Burn trends on real reflectivity burns (F76) | `sample_data/private/` | F76, F77 | `TODO.md` "Waiting on the owner" |
| 12 | Large-data survey for the GID defaults (distance, response, joins) | Many GID sets | `docs/handoff_out/06-gid-method-comparison.md` | `sample_data/private/` | Final GID defaults | `TODO.md` A; input 19 |

Not data, but waiting on the owner and recorded elsewhere: the interview
answers (`docs/gui/questions.md`, Answers table), and the decision tables
B2 in `docs/TODO.md`.
