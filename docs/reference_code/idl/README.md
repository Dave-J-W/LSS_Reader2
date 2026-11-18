# IDL reference code (pinhole and GID)

Received from the owner on 2026-11-18: the files from Mati's stash whose
contents mention "pinhole". Stored unchanged, as the reference for the
pinhole-geometry correction and GID patching (F45, F23, D36). They are
not run by the reader; routines they call (PD_GID_READ, RANGE_PROC, ...)
are not included.

| File | Version | Purpose (from its header) |
|---|---|---|
| `pd_view.pro` | 8.475 | Displays frames from a single area-detector scan (has a `pinhole` keyword) |
| `pd_gid.pro` | 8.44 | Readout and display of PD GID data; horizontal patching of several scans |
| `pd_pin.pro` | 8.44 | Readout and display of PD pinhole-type data; patching in both directions "not fully implemented yet" |
| `pd_merge.pro` | 8.31 | Merging GID and pinhole data (interactive) |
| `pd_gipi_merge.pro` | 8.31 | Merging GID and pinhole data (function) |

What is useful for the reader, compared with its own code:
`docs/handoff_out/04-idl-pinhole-review.md` and its answer.
