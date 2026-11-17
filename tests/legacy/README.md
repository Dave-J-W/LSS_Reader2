Frozen copies of reader code as it was before a rewrite, used as oracles:
the new code must give identical results on every sample file.

- `mca_routines_eval.py`, `spec_routines_eval.py`: the MCA and SPEC readers
  as of commit 9bae5cc, which parsed every number with `eval`.

Do not import these from the program.
