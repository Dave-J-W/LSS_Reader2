"""ORSO reflectivity files (``<name>.ort``; F25, issue #148).

The owner, 2026-11-27: Export writes the ORSO file beside ``_ref.txt`` and
``_rrf.txt`` when "+ ORSO" is ticked, and it is ticked by default; its
columns are Qz, R, sR and sQz; the owner's name and affiliation come from
Preferences and the sample's name from the series macro
(``docs/notes/2026-11-27-orso-export.md``).

The file follows the ORSO text format, version 1.2 (``orsopy``, the format's
reference implementation, writes and reads it; https://www.reflectometry.org/
and https://orsopy.readthedocs.io/). Its YAML header records:

- ``data_source``: the owner, the experiment (beamline, facility, probe
  x-ray, the date of the first scan), the sample's name, and the measurement
  (incident-angle range from the Qz range and the wavelength, the wavelength,
  the SPEC file and its scans);
- ``reduction``: the software and its version, the time, the corrections
  applied in words, and ``call``, the lss_core script that reproduces the
  curve;
- ``columns``: Qz (1/angstrom), R, sR (one standard deviation of R, the error
  model in use, as in ``_ref.txt``), and sQz (the Qz resolution, one
  standard deviation) only when the reduction carries one.

R and sR are written as in ``_ref.txt``; the legacy text files do not change.
"""
import datetime
import math
import platform

import numpy as np

INSTRUMENT = '15-ID-C ChemMatCARS liquid surface spectrometer'
FACILITY = 'Advanced Photon Source'


def available():
    """True when orsopy can be imported (it is in requirements.txt)."""
    try:
        import orsopy  # noqa: F401
        return True
    except ImportError:
        return False


def incident_angles(qz, wavelength):
    """(min, max) incident angle in degrees for Qz values (1/Å) at ``wavelength`` (Å): α = asin(Qz λ / 4π)."""
    q = np.asarray(qz, float)
    q = q[np.isfinite(q)]
    s = np.clip(q * float(wavelength) / (4 * math.pi), -1, 1)
    a = np.degrees(np.arcsin(s))
    return float(np.min(a)), float(np.max(a))


def header(data, spec_file, scans, wavelength, start_date=None, owner_name='', owner_affiliation='',
           sample_name='', corrections=(), call='', version='', comment=None):
    """The ORSO header (orsopy.fileio.Orso) of a reflectivity curve. ``data``: (N, 3) Qz, R, sR, or (N, 4)
    with sQz; ``spec_file``: its path (its base name and the scans go in data_files); ``wavelength``: Å;
    ``start_date``: datetime of the first scan (None: unknown, the file's own time is used)."""
    from orsopy import fileio as fo
    d = np.asarray(data, float)
    owner = fo.Person(name=str(owner_name or ''), affiliation=str(owner_affiliation or ''))
    when = start_date or datetime.datetime.now()
    import os
    base = os.path.basename(str(spec_file or ''))
    scans = [int(s) for s in scans]
    title = '%s, scans %s' % (base, ', '.join(str(s) for s in scans)) if base else 'reflectivity'
    lo, hi = incident_angles(d[:, 0], wavelength)
    source = fo.DataSource(
        owner=owner,
        experiment=fo.Experiment(title=title, instrument=INSTRUMENT, start_date=when, probe='x-ray',
                                 facility=FACILITY),
        sample=fo.Sample(name=str(sample_name or '')),
        measurement=fo.Measurement(
            instrument_settings=fo.InstrumentSettings(
                incident_angle=fo.ValueRange(round(lo, 6), round(hi, 6), 'deg'),
                wavelength=fo.Value(float(wavelength), 'angstrom')),
            data_files=[fo.File(file=base or str(spec_file), comment='scans %s' % ', '.join(str(s) for s in scans))],
            scheme='angle-dispersive'))
    reduction = fo.Reduction(
        software=fo.Software(name='LSS_Reader', version=str(version or ''), platform=platform.system()),
        timestamp=datetime.datetime.now(), creator=owner,
        corrections=[str(c) for c in corrections] or None, call=str(call) if call else None)
    columns = [fo.Column('Qz', '1/angstrom'), fo.Column('R'),
               fo.ErrorColumn('R', error_type='uncertainty', value_is='sigma')]
    if d.shape[1] >= 4:
        columns.append(fo.ErrorColumn('Qz', error_type='resolution', value_is='sigma'))
    return fo.Orso(data_source=source, reduction=reduction, columns=columns, comment=comment)


def write_ort(path, data, spec_file, scans, wavelength, **kw):
    """Write ``path`` (.ort): the header (``header``; its keywords) and the columns, Qz R sR [sQz] (sQz only
    when ``data`` has a fourth column with finite values). Returns the path."""
    from orsopy import fileio as fo
    d = np.asarray(data, float)
    if d.ndim != 2 or d.shape[1] < 3:
        raise ValueError('ORSO export: the data need columns Qz, R, sR')
    has_dq = d.shape[1] >= 4 and np.all(np.isfinite(d[:, 3]))
    d = d[:, :4] if has_dq else d[:, :3]
    comment = None if has_dq else 'No Qz resolution is recorded by this reduction, so there is no sQz column.'
    info = header(d, spec_file, scans, wavelength, comment=comment, **kw)
    fo.save_orso([fo.OrsoDataset(info, d)], path)
    return path
