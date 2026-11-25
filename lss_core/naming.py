"""File names proposed for exports (F105; owner, 2026-11-23, Q-REF-6:
"Straight into xmodfit; the reader proposes a file name from the sample and
series").

The SPEC files carry no sample name. The nearest is the macro that ran the
series (``#U SeriesMacro``, written by the newer macros), whose file name
names the sample and the measurement (a hypothetical ``dppc_xr.do``: sample
"dppc", reflectivity). So the proposal is

    <SPEC file>_<sample>_S<scans>       e.g. 20260923_dppc_S6-9

with the sample left out when it is not known. The exporter appends its own
endings (``_ref.txt``, ``_rrf.txt``, ``_ref.cov.json``), the files XModFit
reads (docs/handoff/19-lss-reader-covariance-contract.md).
"""
import os
import re

# endings of a series macro's name that say the measurement, not the sample
MEASUREMENT_SUFFIXES = ('_xr', '_ref', '_refl', '_gid', '_burn', '_xfntr', '_flu', '_gisaxs', '_gioxs', '_sh')


def sanitize(text):
    """Letters, digits, '.', '-' and '_' only; other runs become one '_'."""
    s = re.sub(r'[^A-Za-z0-9.\-]+', '_', str(text or '')).strip('_.')
    return s


def scans_tag(scans):
    """'S6-9' for a run of scans, 'S6_8_11' otherwise, 'S12' for one."""
    nums = sorted({int(s) for s in scans})
    if not nums:
        return ''
    if len(nums) > 1 and nums == list(range(nums[0], nums[-1] + 1)):
        return 'S%d-%d' % (nums[0], nums[-1])
    return 'S' + '_'.join(str(n) for n in nums)


def sample_from_macro(macro):
    """The sample a series macro's file name gives: its base name without
    the extension and without a trailing measurement word ('dppc_xr.do' →
    'dppc'); '' when there is no macro."""
    if not macro:
        return ''
    words = str(macro).split()
    name = os.path.basename(words[1] if words[:1] == ['do'] and len(words) > 1 else words[0])
    stem = os.path.splitext(name)[0]
    low = stem.lower()
    for suf in MEASUREMENT_SUFFIXES:
        if low.endswith(suf) and len(stem) > len(suf):
            stem = stem[:-len(suf)]
            break
    return sanitize(stem)


def export_base(spec_path, scans, sample=''):
    """The proposed base name of an export (no folder, no ending)."""
    parts = [sanitize(os.path.basename(str(spec_path or ''))), sanitize(sample), scans_tag(scans)]
    return '_'.join(p for p in parts if p) or 'export'
