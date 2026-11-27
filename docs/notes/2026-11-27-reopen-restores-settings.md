# Reopening a SPEC file restores its workbook's settings, and lists what changed

- **Date, who:** 2026-11-27, main man (asked the owner while doing #145)
- **Question:** when a SPEC file is reopened, its workbook holds the settings last used for it. Several change
  output numbers and can differ from the reader's global preferences. Restore them, ask each time, or only on
  request?
- **Answer (owner):** "Restore, list what changed". Opening a file applies the settings recorded at its last
  save, and one message lists those that differed, old -> new. Preferences > Saving > "Restore a file's settings
  when it is opened" turns it off.
- **What is restored:**
  - the Reflectivity fields: background offset, ROI size, Qc, Qoff, the norm factor;
  - the absorber factor: not when it comes from the energy ("from E"), nor the calibrated foils;
  - Monc gain and per-photon mode;
  - the error and monitor model;
  - the GID parameters;
  - the peak and MCA fit options.
- **Global preferences are not rewritten** by a restore: it changes this session's settings only.
- **How it is known:** test `tests/test_reopen_settings.py`. The main test fails with the restore call removed.
- **Numbers that changed:** a reopened file is reduced with its own last settings rather than the current ones
  (`OUTPUT_DECISIONS`, 2026-11-27).
