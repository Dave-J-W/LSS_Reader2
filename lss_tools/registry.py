"""Every demonstration, figure and data generator, and check in the
repository: one entry per tool (``TOOLS``), with the documented runs whose
outputs are committed (``Job``). The Tools menu, ``docs/TOOLS.md``,
``python -m lss_tools.regenerate`` and the freshness test all read this
list; add a tool here when you add one to ``tests/tools/``.

Paths are relative to the repository root and use '/'. A job's ``args``
are its documented command line after the script; ``{out}`` stands for
its output folder (``out``). Run times were measured on the 4-core
development machine (2026-11-22) unless marked otherwise.
"""
from dataclasses import dataclass, field
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX = 'sample_data/NX_school/2026sep/20260923'
NX_DIR = 'sample_data/NX_school'
PRIVATE_GID = 'sample_data/private/gid_scans_136-146/gid'
PRIVATE_FIGURES = 'sample_data/private/figures'

KINDS = (('demo', 'Demonstrations'), ('figures', 'Figures'), ('data', 'Data and surveys'), ('check', 'Checks'))
DATA = {'public': 'public NX school data (committed)',
        'synthetic': 'synthetic data only (public)',
        'private': "the owner's private data (git-ignored; skipped when absent)",
        'code': 'the code only (no data)',
        'mixed': 'public data; also private data when given, or found under sample_data/'}


@dataclass(frozen=True)
class Job:
    """One documented run whose outputs are committed (or, when
    ``private``, kept under sample_data/private/figures/)."""
    id: str
    title: str
    args: tuple = ()
    out: str = ''                 # output folder the documented command writes into
    outputs: tuple = ()           # globs (relative to the root) of the files this job owns
    ignore: tuple = ()            # globs it also writes that are not committed (large; git-ignored)
    keep: tuple = ()              # outputs it updates in place (reads, then rewrites): not set aside before a run
    stdout: str = ''              # the job's standard output is this file
    private: bool = False
    requires: tuple = ()          # files that must exist to run it
    inputs: tuple = ()            # if given: only traced inputs matching these globs count
    seconds: float = 0.0          # measured run time

    def argv(self, out=None):
        """The arguments, ``{out}`` replaced."""
        return [a.replace('{out}', out or self.out) for a in self.args]


@dataclass(frozen=True)
class Tool:
    id: str
    title: str                    # menu text
    kind: str                     # 'demo', 'figures', 'data', 'check'
    summary: str                  # one sentence: the menu entry's tooltip
    details: str = ''             # the dialog's tooltip: inputs, outputs, caveats
    script: str = ''              # the program, relative to the root
    module: str = ''              # or a module run with python -m
    demo: str = ''                # demonstrations: 'module:callable' building the window
    demo_kwargs: dict = field(default_factory=dict)
    data: str = 'public'          # a key of DATA
    args: tuple = ()              # default arguments when the tool has no job
    jobs: tuple = ()
    out_flag: str = ''            # the option that sends its outputs to another folder ('' = none)
    seconds: str = ''             # typical run time, as text
    sources: tuple = ()           # where the work is done (for the table)
    doc: str = ''                 # where its results are discussed

    @property
    def command(self):
        """How to run it from a shell, from the repository root."""
        return ('python -m ' + self.module) if self.module else ('python ' + self.script)


def _nx_job(id, title, args, out, outputs, **kw):
    return Job(id, title, tuple(args), out, tuple(outputs), requires=(NX,), **kw)


def _private_job(id, title, args, out, outputs, **kw):
    return Job(id, title, tuple(args), out, tuple(outputs), private=True, requires=(PRIVATE_GID,), **kw)


TOOLS = (
    # ---------------------------------------------------------------- demonstrations
    Tool('demo_refl', 'Fit demonstrator: reflectivity patching', 'demo',
         'Synthetic reflectivity measured as overlapping scans, patched by every method, with the truth '
         'beside it; space bar: a new noise replicate.',
         'Opens a window (it does not block the reader). Synthetic data only. Report: '
         'docs/reports/patch_demo.md; the same window: python tests/tools/patch_demo.py.',
         script='tests/tools/patch_demo.py', demo='demonstrator.window:open_demo',
         demo_kwargs={'mode': 'refl'}, data='synthetic', seconds='1-2 s to open',
         sources=('tests/demonstrator/',), doc='docs/reports/patch_demo.md'),
    Tool('demo_burn', 'Fit demonstrator: burn line cuts', 'demo',
         'Synthetic GID burn profiles fitted by every estimator, with the trends over time and the '
         'truth; space bar: a new replicate.',
         'Opens a window (it does not block the reader). Synthetic data only. The same window: '
         'python tests/tools/patch_demo.py --mode burn.',
         script='tests/tools/patch_demo.py', demo='demonstrator.window:open_demo',
         demo_kwargs={'mode': 'burn'}, data='synthetic', seconds='2-3 s to open',
         sources=('tests/demonstrator/',), doc='docs/reports/patch_demo.md'),

    # ---------------------------------------------------------------- figures
    Tool('patch_demo', 'Fit demonstrator report figures', 'figures',
         'The six figures, summary CSVs and numbers.json of the fit demonstrator report '
         '(reflectivity patching methods, burn estimators) on synthetic replicates.',
         'Synthetic data only; about 2.5 min (--quick: 16 s, few replicates). --rows DIR2: also the '
         'per-replicate CSVs (large, not committed). Comparison C34.',
         script='tests/tools/patch_demo.py', data='synthetic', out_flag='--save',
         jobs=(Job('patch_demo', 'Report figures (docs/figures/patch_demo)', ('--save', '{out}'),
                   'docs/figures/patch_demo',
                   ('docs/figures/patch_demo/*.png', 'docs/figures/patch_demo/*.csv',
                    'docs/figures/patch_demo/numbers.json')),),
         sources=('tests/demonstrator/',), doc='docs/reports/patch_demo.md'),
    Tool('burn_figures', 'Burn tests over time', 'figures',
         'Burn scans as the Trends tab draws them (template and legacy-moments estimators) and the '
         'table of the three estimators, from NX school scans 14 and 15.',
         'Without --out: figures into docs/figures/burn_trends/, CSVs into '
         'docs/comparisons_data/burn_nx/; with --out both go there. Another SPEC file: --spec, --scans '
         '(the tool refuses docs/ for data other than NX). Comparison C31.',
         script='tests/tools/burn_figures.py', out_flag='--out',
         jobs=(_nx_job('burn_figures', 'NX scans 14, 15', (), 'docs/figures/burn_trends',
                       ('docs/figures/burn_trends/*.png', 'docs/comparisons_data/burn_nx/*.csv')),),
         doc='docs/COMPARISONS.md C31'),
    Tool('gid_compare_figures', 'GID patching: legacy against pinhole', 'figures',
         'Maps, profiles and joins of the legacy 3-column GID patch beside the pinhole-geometry '
         'patch, on the same scans.',
         'Public: NX scan 11, and 11 + 12 (not like for like: scan 12 stopped). Private pairs '
         '(163 + 165, 386-389) go to sample_data/private/figures/ (the tool refuses other folders '
         'in the repository). Comparisons C10, C14, C21, C22.',
         script='tests/tools/gid_compare_figures.py', data='mixed', out_flag='--out',
         jobs=(_nx_job('gid_compare_S11', 'NX scan 11', ('--scans', '11', '--out', '{out}'),
                       'docs/figures/gid_compare', ('docs/figures/gid_compare/nx_S11_*',)),
               _nx_job('gid_compare_S11+12', 'NX scans 11 + 12',
                       ('--scans', '11,12', '--peak', 'none', '--note',
                        'not like for like: scan 12 stopped after 4 frames', '--out', '{out}'),
                       'docs/figures/gid_compare', ('docs/figures/gid_compare/nx_S11+12_*',)),
               _private_job('gid_compare_private_163+165', 'Private scans 163 + 165',
                            ('--spec', PRIVATE_GID, '--scans', '163,165', '--out', '{out}'),
                            PRIVATE_FIGURES + '/gid_compare',
                            (PRIVATE_FIGURES + '/gid_compare/private_S163+165_*',)),
               _private_job('gid_compare_private_386-389', 'Private scans 386-389',
                            ('--spec', PRIVATE_GID, '--scans', '386,387,388,389', '--out', '{out}'),
                            PRIVATE_FIGURES + '/gid_compare',
                            (PRIVATE_FIGURES + '/gid_compare/private_S386-389_*',))),
         doc='docs/figures/gid_compare/README.md'),
    Tool('gid_patching_diagrams', 'GID patching diagrams (manual)', 'figures',
         "The eight diagrams of the manual's GID patching addendum, every number from lss_core and "
         'NX scans 11 and 12.',
         'Only the public NX file is read (the script takes no other). --only N: some diagrams.',
         script='tests/tools/gid_patching_diagrams.py', out_flag='--out',
         jobs=(_nx_job('gid_patching_diagrams', 'Manual diagrams', (), 'docs/manual/figures/gid_patching',
                       ('docs/manual/figures/gid_patching/*.png',)),),
         doc='docs/manual/gid_patching.md'),
    Tool('gid_stray_light', 'GID stray light (P40)', 'figures',
         'Beta profiles of column bands inside and outside the usable window, per Qz level, and three '
         'frames per level: light that cannot have come through the pinhole.',
         'Public: NX scans 11, 12. Private scans go under sample_data/private/figures/. '
         'docs/PHYSICS_ISSUES.md P40.',
         script='tests/tools/gid_stray_light.py', data='mixed', out_flag='--out',
         jobs=(_nx_job('gid_stray_light', 'NX scans 11, 12', (), 'docs/figures/gid_stray_light',
                       ('docs/figures/gid_stray_light/*.png',)),
               _private_job('gid_stray_light_private_163_165', 'Private scans 163, 165',
                            ('--spec', PRIVATE_GID, '--scans', '163', '165', '--out', '{out}'),
                            PRIVATE_FIGURES + '/slit_scatter',
                            (PRIVATE_FIGURES + '/slit_scatter/*_163_165.png',)),
               _private_job('gid_stray_light_private_386_389', 'Private scans 386-389',
                            ('--spec', PRIVATE_GID, '--scans', '386', '387', '388', '389', '--out', '{out}'),
                            PRIVATE_FIGURES + '/slit_scatter',
                            (PRIVATE_FIGURES + '/slit_scatter/*_386_387_388_389.png',))),
         doc='docs/figures/gid_stray_light/README.md'),
    Tool('pinhole_beam_figure', 'Beam profile from the "beam" response', 'figures',
         'The beam profile along the beam axis that the pinhole "beam" response measures, beside the '
         'per-column response at three Det_Th, from NX scan 11.',
         'Another SPEC file: --spec, --scans (private data to a folder outside docs/). Comparison C23.',
         script='tests/tools/pinhole_beam_figure.py', out_flag='--out',
         jobs=(_nx_job('pinhole_beam_figure', 'NX scan 11', (), 'docs/figures/pinhole_beam',
                       ('docs/figures/pinhole_beam/*.png',)),),
         doc='docs/figures/pinhole_beam/README.md'),
    Tool('pinhole_figures', 'Pinhole GID geometry', 'figures',
         'Eight figures of the pinhole GID geometry (lab frame, pinhole top view, beta per column, '
         'raised arm, footprint, S4 opening), every point computed by lss_core.pinhole.',
         'Public: NX scans 11, 12. Private: --spec with --low, --high, into '
         'sample_data/private/figures/pinhole. Each figure prints git describe of the code that drew it.',
         script='tests/tools/pinhole_figures.py', data='mixed', out_flag='--out',
         jobs=(_nx_job('pinhole_figures', 'NX scans 11, 12', (), 'docs/figures/pinhole',
                       ('docs/figures/pinhole/case*.png',)),
               _private_job('pinhole_figures_private', 'Private scans 163, 165',
                            ('--spec', PRIVATE_GID, '--low', '163', '--high', '165', '--label',
                             'private GID file', '--out', '{out}'),
                            PRIVATE_FIGURES + '/pinhole', (PRIVATE_FIGURES + '/pinhole/case*.png',))),
         doc='docs/figures/pinhole/README.md'),

    # ---------------------------------------------------------------- data and surveys
    Tool('compare_methods', 'Old and new methods as CSV', 'data',
         'Old and new methods side by side as CSV for figures: error models (C2/C3), absorber factors '
         '(C6), GID legacy against pinhole (C10, C14, C21) and the pinhole distance (C11).',
         'Default: NX school into docs/comparisons_data/ with manifest.json. The 2D maps (*_map.csv) '
         'are large and git-ignored; --no-maps skips them. Other data: --spec, --ref, --gid, and '
         '--out outside the repository for private data.',
         script='tests/tools/compare_methods.py', out_flag='--out',
         jobs=(_nx_job('compare_methods', 'NX school', (), 'docs/comparisons_data',
                       ('docs/comparisons_data/C*.csv', 'docs/comparisons_data/manifest.json'),
                       ignore=('docs/comparisons_data/*_map.csv',),
                       keep=('docs/comparisons_data/manifest.json',)),),
         doc='docs/COMPARISONS.md'),
    Tool('gid_method_survey', 'GID method survey', 'data',
         'Every GID patching method at the header and the calibrated distance, the distance '
         'calibration from single frames, patched peaks against single frames, and the scale '
         'recovered from a split scan.',
         'About 2-4 min per set. Private sets: --out under sample_data/private/ (checked). '
         'Hand-off 06; comparison C29.',
         script='tests/tools/gid_method_survey.py', data='mixed', out_flag='--out',
         jobs=(_nx_job('gid_survey_nx', 'NX school (worked example)', ('--spec', NX, '--out', '{out}', '--split'),
                       'docs/comparisons_data/gid_survey_nx',
                       ('docs/comparisons_data/gid_survey_nx/*.csv', 'docs/comparisons_data/gid_survey_nx/summary.md')),
               _private_job('gid_survey_private', 'Private GID file',
                            ('--spec', PRIVATE_GID, '--out', '{out}', '--split'), PRIVATE_FIGURES + '/gid_survey',
                            (PRIVATE_FIGURES + '/gid_survey/*.csv', PRIVATE_FIGURES + '/gid_survey/summary.md'))),
         doc='docs/handoff_out/06-gid-method-comparison.md'),
    Tool('ref_patch_survey', 'Reflectivity patching survey', 'data',
         'Every reflectivity patching method at every join of the reflectivity series of a SPEC file; '
         'with --split, known truth from scans split in two; --repeats, repeated scans.',
         'Private data: --out under sample_data/private/ (checked). Hand-off 08; comparison C33.',
         script='tests/tools/ref_patch_survey.py', data='mixed', out_flag='--out',
         jobs=(_nx_job('ref_patch_nx', 'NX school', ('--spec', NX, '--out', '{out}', '--split', '--repeats'),
                       'docs/comparisons_data/ref_patch_nx', ('docs/comparisons_data/ref_patch_nx/*',)),),
         doc='docs/handoff_out/08-ref-patch-comparison.md'),
    Tool('ref_patch_gauntlet', 'Reflectivity patching gauntlet', 'data',
         'The judging rules of hand-off 08 (mean pull, pull SD per join) on many noise replicates of '
         'synthetic reflectivity with known truth, for every patching method and the reader\'s own path, '
         'over designed and random conditions.',
         'Synthetic data only. Long: the full design (--design all) takes about 25 min; --design core '
         '--methods all about 3 min. pulls.csv (every replicate, large) only with --rows, not committed. Comparison C36.',
         script='tests/tools/ref_patch_gauntlet.py', data='synthetic', out_flag='--out', seconds='3-25 min',
         jobs=(Job('ref_patch_gauntlet', 'Every design (core, grid, random)', ('--out', '{out}', '--design', 'all'),
                   'docs/comparisons_data/ref_patch_gauntlet',
                   ('docs/comparisons_data/ref_patch_gauntlet/*.csv', 'docs/comparisons_data/ref_patch_gauntlet/summary.md', 'docs/comparisons_data/ref_patch_gauntlet/log.txt'),
                   ignore=('docs/comparisons_data/ref_patch_gauntlet/pulls.csv',), seconds=1500),
               Job('ref_patch_gauntlet_core_all', 'Core conditions, every method',
                   ('--out', '{out}', '--design', 'core', '--methods', 'all'),
                   'docs/comparisons_data/ref_patch_gauntlet/core_all_methods',
                   ('docs/comparisons_data/ref_patch_gauntlet/core_all_methods/*.csv', 'docs/comparisons_data/ref_patch_gauntlet/core_all_methods/summary.md',
                    'docs/comparisons_data/ref_patch_gauntlet/core_all_methods/log.txt'),
                   ignore=('docs/comparisons_data/ref_patch_gauntlet/core_all_methods/pulls.csv',), seconds=180)),
         doc='docs/COMPARISONS.md C36'),
    Tool('dump_tooltips', 'Controls and tooltips (manual)', 'data',
         "Every control of the window and its dialogs with its tooltip, as Markdown: the manual's "
         'raw material (docs/manual/controls.md).',
         'Opens no data. Counts as stale when mainwindow.py, a .ui file, lss_tools or the script '
         'change (the tooltips live there), not for other code.',
         script='tests/tools/dump_tooltips.py', data='code',
         jobs=(Job('controls', 'docs/manual/controls.md', (), 'docs/manual',
                   ('docs/manual/controls.md',), stdout='docs/manual/controls.md',
                   inputs=('mainwindow.py', '*.ui', 'lss_tools/*.py', 'tests/tools/dump_tooltips.py')),),
         doc='docs/MANUAL_NOTES.md'),

    # ---------------------------------------------------------------- checks (print only)
    Tool('absorber_steps', 'Absorber steps between scans', 'check',
         'Measured absorber steps between overlapping reflectivity scans against the nominal '
         'absfac**-n, and the extra Al thickness they imply.',
         'Arguments: SPEC file and scans (default NX 6-9). Prints a Markdown table. Comparisons C7, C8.',
         script='tests/tools/absorber_steps.py', data='mixed', args=(NX, '6,7,8,9')),
    Tool('foil_fit_from_joins', 'Foil thicknesses from joins', 'check',
         'Per-foil Al thicknesses fitted to a joins table (hand-off 02/03), with every join\'s '
         'residual and the implied beam change.',
         'Argument: a joins CSV (default the committed hand-off 03 answer).',
         script='tests/tools/foil_fit_from_joins.py', data='public',
         args=('docs/handoff_out/03-answer/joins.csv',)),
    Tool('monitor_distribution', 'Monitor scatter: distribution', 'check',
         'Frame-to-frame scatter of Monc about a smooth trend, pooled over every SPEC file under '
         'sample_data/, and its share of each reduced point\'s variance.',
         'Reads every SPEC file found under sample_data/ (private ones too, when present); prints only.',
         script='tests/tools/monitor_distribution.py', data='mixed', doc='docs/reports/monitor_noise.md'),
    Tool('monitor_gains', 'Monitor gains not understood (F52)', 'check',
         "The '#M Monc Gain' lines the reader cannot interpret, as a Markdown table.",
         'Default: every SPEC file under sample_data/ (private ones too, when present). '
         'docs/reports/monitor_gains.md was made with it.',
         script='tests/tools/monitor_gains.py', data='mixed', doc='docs/reports/monitor_gains.md'),
    Tool('monitor_noise_mc', 'Monitor noise Monte Carlo', 'check',
         'Monte Carlo check of the error propagation of monitor normalisation, and a look at the '
         'monitors of the NX file.',
         '--no-real: Monte Carlo only. Comparison C4.',
         script='tests/tools/monitor_noise_mc.py', data='public', doc='docs/reports/monitor_noise.md'),
    Tool('monitor_ratio', 'Monitor scatter: beam or noise', 'check',
         'Correlation of the residuals of Monc and Monp per scan: how much of their scatter is beam '
         'variation and how much each monitor\'s own noise.',
         'Argument: a SPEC file (default NX). Comparison C9.',
         script='tests/tools/monitor_ratio.py', data='mixed', args=(NX,)),
    Tool('monitor_witness', 'Monitor jumps: detector as witness', 'check',
         "Whether Monc's large jumps are followed by the detector (real flux) or not (monitor error).",
         'Reads every SPEC file found under sample_data/ (private ones too, when present); prints only.',
         script='tests/tools/monitor_witness.py', data='mixed'),
    Tool('pinhole_beam_profile', 'Gaussian beam and the pinhole', 'check',
         'Predicted column response of a Gaussian beam profile against the response the pinhole patch '
         'fits on NX scan 11, and the bias left in a synthetic map.',
         '--fwhm-v, --fwhm-h (mm). Comparison C23.',
         script='tests/tools/pinhole_beam_profile.py', data='public'),
    Tool('single_frame_truth', 'Single frames as GID ground truth', 'check',
         'Peak position and width of single unpatched frames against the patched maps, and how well '
         'the frames agree at each S4-detector distance.',
         'Default: NX scan 11, peak at 16.63 deg. Comparison C28.',
         script='tests/tools/single_frame_truth.py', data='mixed', args=('--scans', '11', '--peak', '16.63')),
    Tool('spec_epoch', 'What the SPEC Epoch column measures', 'check',
         'First-point Epoch against the scan header time for every scan: the time zone offset and the '
         'lag of the first point.',
         'Arguments: SPEC files (default NX).',
         script='tests/tools/spec_epoch.py', data='mixed', args=(NX,)),
    Tool('regenerate', 'Documentation outputs: check and regenerate', 'check',
         'Whether every committed figure and data file is up to date with the code and data that made '
         'it (--check), or rerun the stale ones and update docs/figures/MANIFEST.json.',
         'Default: --check (reads only). No option: reruns the stale public jobs (minutes; it rewrites '
         'files in docs/). --private: also the private-data jobs, when the data are present. '
         '--list: every job and its state. docs/TOOLS.md explains what counts as an input.',
         module='lss_tools.regenerate', data='mixed', args=('--check',), doc='docs/TOOLS.md'),
)

HELPERS = {'tests/tools/pinhole_frames.py': 'pinhole frames of SPEC scans for lss_core.pinhole (used by '
                                            'pinhole_figures.py and pinhole_beam_profile.py; no command)'}

# Committed outputs made elsewhere or by other means: listed, not checked.
EXTERNAL = {
    'docs/handoff_out/03-answer/': "made by the owner-side analysis (tools/absorber_steps.py, "
                                   "tools/absorber_review.py in another repository, private data)",
    'docs/timings.md': 'written by pytest -m bench: a measurement of this machine, not documentation code',
}

# Committed outputs made once and kept as a record (they cannot be remade by
# today's code): not owned by any job, exempt from the unclaimed check.
FROZEN = {
    'docs/comparisons_data/C21_*.csv': 'C21 per-axis against exact pinhole angles, made once with the commit '
                                       'before the change (34c33c8) and after it; compare_methods.py keeps their '
                                       'entries in manifest.json',
}

# Folders whose every file (but README.md and the manifest) must belong to a job.
GENERATED_DIRS = ('docs/figures', 'docs/comparisons_data', 'docs/manual/figures')


def by_id(tool_id):
    for t in TOOLS:
        if t.id == tool_id:
            return t
    raise KeyError(tool_id)


def jobs(private=None):
    """(tool, job) for every job; ``private`` True/False selects, None gives all."""
    return [(t, j) for t in TOOLS for j in t.jobs if private is None or j.private == private]


def job_by_id(job_id):
    for t, j in jobs():
        if j.id == job_id:
            return t, j
    raise KeyError(job_id)
