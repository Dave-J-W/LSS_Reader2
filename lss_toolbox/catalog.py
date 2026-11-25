"""The catalogue: every demonstration and figure generator of the
repository, one entry per item of the Tools menu.

An item names its script (``tests/tools/*.py``); the script stays the
authority on what it accepts (``introspect.capture_parsers`` reads its
parser) and on what it says about itself (its docstring, shown in the
window). The catalogue adds what the script cannot say: the menu it belongs
to, what it demonstrates in one line, where its committed products live,
which documents explain it, how long it takes, and the **variations** the
documents describe ("change this parameter and regenerate the figure to
show that"), each with the document line it comes from.

Kept in step by ``tests/test_toolbox.py``: every script in ``tests/tools``
is an item or a listed helper; every option a variation sets exists in the
script's parser; every figure committed under ``docs/`` belongs to an
item; ``docs/TOOLS.md`` is the rendering of this file.

Values in ``defaults`` and ``variations`` are keyed by option strings (the
first one the parser lists) or a positional's name; ``'{out}'`` stands for
the run's own folder. ``True`` ticks a flag; ``''`` clears a field.
"""
from dataclasses import dataclass, field

NX = 'sample_data/NX_school/2026sep/20260923'
OUT = '{out}'

# Menu order: the owner's workflow priority (burn tests, reflectivity, GID),
# then the measurements behind the error model, synthetic data, the GUI.
CATEGORIES = (
    ('burn', 'Burn tests'),
    ('refl', 'Reflectivity patching'),
    ('gid', 'GID and pinhole geometry'),
    ('monitor', 'Monitor, scans, SPEC files'),
    ('fluo', 'Fluorescence (MCA)'),
    ('synthetic', 'Synthetic data sets'),
    ('gui', "The reader's window and manual"),
    ('external', 'Made elsewhere'),
)

KINDS = {
    'window': 'an interactive window (its own process)',
    'figures': 'figures (PNG) and the numbers behind them',
    'data': 'tables (CSV) and a summary for later figures',
    'text': 'a printed report (tables in the output pane)',
    'check': 'a check of the repository (pass or fail)',
    'dataset': 'a synthetic data set to open in the reader',
    'external': 'figures made outside this repository (shown, not regenerated)',
}

# Python files in tests/tools that are libraries for other tools, not items.
HELPERS = {
    'pinhole_frames.py': 'frame parameters of SPEC scans for lss_core.pinhole (used by pinhole_figures and '
                         'docs/SCRIPTING.md)',
}


@dataclass(frozen=True)
class Variation:
    """A documented change of settings and what it shows. ``args`` keyed by
    option string; ``source`` the document passage that describes it, as
    'path#text': ``text`` occurs on exactly one line of ``path`` (a heading,
    a ledger id such as '| C42 |', or a short quote), so that inserting
    lines elsewhere moves nothing (Main, 2026-11-24). ``locate`` finds it."""
    label: str
    args: dict
    shows: str
    source: str = ''


@dataclass(frozen=True)
class Tool:
    id: str
    title: str
    category: str
    kind: str
    script: str = ''
    demonstrates: str = ''
    committed: tuple = ()          # repository paths (folders, files, git globs) of its committed products
    docs: tuple = ()               # documents that explain it (repository paths, optionally path#text)
    data: str = 'synthetic'        # synthetic | public (NX school) | any (a SPEC file you choose) | private
    defaults: dict = field(default_factory=dict)
    variations: tuple = ()
    repo_out: str = None           # where {out} points when the committed products are replaced (None: the
    #                                script's own default output, the option is left out)
    scratch_args: dict = field(default_factory=dict)   # forced in a run folder (e.g. "do not render into docs")
    free: str = ''                 # default arguments of a script without argparse
    free_help: str = ''
    repo_stdout: str = None        # file the printed output replaces in a repository run
    inputs: tuple = ()             # dependencies besides imported Python files (data, .ui, YAML)
    imports: tuple = ()            # Python files it uses without importing them
    seconds: float = None          # measured run time with the defaults (this container, 2026-11-23)
    spec_option: str = None        # option (or 'free') that takes a SPEC file: filled from the reader's open file
    repo_ok: bool = True           # its committed products may be replaced from the window (defaults only)
    subcommand: str = None         # for a script with subcommands: the one this item runs
    committed_with: dict = None    # settings (over the defaults) that made the committed products, when the
    #                                defaults are a quicker look; None: the defaults made them
    volatile: tuple = ()           # regular expressions: lines of its text products that record how it ran
    #                                (wall times), left out when the audit compares them (2026-11-25)

    @property
    def runnable(self):
        return bool(self.script)

    def committed_args(self):
        """The settings (as option -> value) that made the committed products."""
        args = dict(self.defaults)
        args.update(self.committed_with or {})
        return args


def split_ref(ref):
    """'docs/x.md#some text' -> ('docs/x.md', 'some text'); no anchor: ''."""
    path, _, anchor = ref.partition('#')
    return path, anchor


def locate(ref, root=None):
    """(absolute path, 1-based line of the anchor or None, number of lines
    holding it) for a reference 'path#text'."""
    import os
    path, anchor = split_ref(ref)
    full = os.path.join(root or _root(), path)
    if not anchor or not os.path.isfile(full):
        return full, None, 0
    with open(full, encoding='utf-8') as f:
        hits = [k for k, line in enumerate(f, start=1) if anchor in line]
    return full, (hits[0] if hits else None), len(hits)


def _root():
    from . import ROOT
    return ROOT


def V(label, shows, source='', **args):
    """A variation; keyword names are option strings with '-' as '_'."""
    return Variation(label, {('--' + k.replace('_', '-')) if not k.startswith('_') else k[1:]: v
                             for k, v in args.items()}, shows, source)


UI = ('mainwindow.ui', 'mainwindow.py')


def ALL_SAMPLE_DATA(key, shows, source):
    """The variation that clears an NX-only default: the script's own
    default, which includes the private sets when they are on this machine
    (2026-11-23: the pages default to the public file, so that a page never
    shows private counts unasked)."""
    return Variation('All sample data (private sets too, when present)', {key: ''},
                     shows + ' Prints counts of private files when they are present; never write them into docs.',
                     source)

TOOLS = (
    # ------------------------------------------------------------ burn tests
    Tool('patch_demo_burn', 'Burn line-cut demonstrator (window)', 'burn', 'window',
         'tests/tools/patch_demo.py',
         'GID line cuts of one spot over time: every burn estimator (template, moments, fit) against the '
         'known change; space bar for a new noise replicate.',
         docs=('docs/reports/patch_demo.md', 'docs/handoff_out/07-burn-trends.md'),
         defaults={'--mode': 'burn'},
         variations=(
             V('Fade', 'Intensity falls at constant shape; every estimator under-reads it (the window holds part of the '
               'shoulder), and the Gaussian fit also reads a +13 % broadening.',
               'docs/reports/patch_demo.md#fade: spurious FWHM', mode='burn', set='change=fade'),
             V('Broadening at constant area', 'The template estimator reads a broadening as a shift and a gain '
               '(the report\'s caveat on the default estimator).', 'docs/reports/patch_demo.md#Gaussian fit reads a fade as +13 % FWHM',
               mode='burn', set='change=broaden'),
             V('Fade under a 3x shoulder', 'A peak fading by 20 % under a broad shoulder: the template reads -9 %, the '
               'moments -4 %, the Gaussian fit a gain (+3 %).',
               'docs/reports/patch_demo.md#fade under a 3× shoulder (−20 %)', mode='burn', set='change=shoulder'),
             V('Low counts (monitor 1e5)', '"Lower monitor until each estimator fails": the counts per frame at '
               'which each estimator becomes unusable.', 'docs/handoff_out/07-burn-trends.md#4. **Noise level.**',
               mode='burn', set='monitor=1e5'),
             V('No change', 'A stable spot: the trends should find no significant change (false alarms).',
               'docs/SYNTHETIC_DATA.md#**GID burn profiles**', mode='burn', set='change=none'),
         ),
         repo_ok=False, seconds=None),
    Tool('patch_demo_burn_survey', 'Burn estimators: survey over replicates', 'burn', 'text',
         'tests/tools/patch_demo.py',
         'Every burn estimator over many noise replicates of a synthetic burn: the change it reads against the '
         'truth (bias, scatter) and how often it calls a quantity stable.',
         docs=('docs/reports/patch_demo.md', 'docs/handoff_out/07-burn-trends.md#4. **Noise level.**'),
         defaults={'--mode': 'burn', '--survey': '20'},
         variations=(
             V('Low counts (monitor 1e5)', '"Lower monitor until each estimator fails": the counts at which each '
               'estimator\'s scatter swamps the change.', 'docs/SYNTHETIC_DATA.md#estimator reads which', set='burn.monitor=1e5'),
             V('Fade under a shoulder', 'A peak fading under a broad shoulder: where moments mislead.',
               'docs/SYNTHETIC_DATA.md#**GID burn profiles**', set='change=shoulder'),
             V('No change', 'A stable spot: how often each estimator calls it stable (false alarms).',
               'docs/SYNTHETIC_DATA.md#**GID burn profiles**', set='change=none'),
         ),
         seconds=19.0, repo_ok=False),
    Tool('burn_figures', 'Burn trends of NX scans 14 and 15', 'burn', 'figures',
         'tests/tools/burn_figures.py',
         'Burn tests over time as the Trends tab draws them (every model, the confident 5 % time) for the '
         'template and legacy moments estimators, and the three estimators compared.',
         committed=('docs/figures/burn_trends', 'docs/comparisons_data/burn_nx'),
         docs=('docs/handoff_out/07-burn-trends.md', 'docs/COMPARISONS.md#| C31 |'),
         data='public', defaults={'--out': OUT}, spec_option='--spec',
         variations=(
             V('Scan 14 only', 'One burn scan: absorber 12, the lower dose of the pair.',
               'docs/physics_notes.md#Qz by (4π/λ)', scans='14'),
             V('Scan 15 only', 'The second scan of the spot at absorber 8 (4.1x the flux of scan 14): dose against '
               'time, beam damage or a changing sample.', 'docs/physics_notes.md#Qz by (4π/λ)', scans='15'),
         ),
         seconds=5.4),

    Tool('reciprocity_study', 'Beam damage or the sample by itself? The dose-or-time test (F76)', 'burn', 'figures',
         'tests/tools/reciprocity_study.py',
         'Synthetic burns at several fluxes with a known law (the dose, time, a dose-rate effect, a mixture, no '
         'change) and strip-to-strip scatter: how often lss_core.reciprocity calls each truth right, beta\'s pulls, '
         'and NX school burns 14 and 15: figures R1-R5.',
         committed=('docs/studies/reciprocity',),
         docs=('docs/studies/reciprocity/summary.md', 'docs/COMPARISONS.md#| C58 |', 'docs/FEATURE_REQUESTS.md#| F76 |'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('The anatomy and NX only', 'R1 and R5, which need no replicates (a few seconds): two burns against time '
               'and dose, and the NX pair.', 'docs/studies/reciprocity/summary.md## 5. NX school burns 14 and 15', only='R1,R5'),
             V('Strip scatter', 'Four burns over x8 with 20 % and 50 % strip scatter: ignored, as one constant, as a '
               'share of each rate.', 'docs/studies/reciprocity/summary.md## 2. Strip scatter', design='strip'),
             V('Flux span and number of burns', 'Two burns x2 to x20 apart, and 2-4 burns over x10.',
               'docs/studies/reciprocity/summary.md## 1. How often is each truth called right?', design='span,burns'),
             V('Few frames, little change', '11-41 frames, 0.3-3 % noise, a 2-20 % fall: when time cannot be shown.',
               'docs/studies/reciprocity/summary.md## 3. Few frames, little change', design='frames,noise,change'),
             V('More replicates (1000)', 'Every design with 1000 replicates (about 2 min).',
               'docs/studies/reciprocity/summary.md## 1. How often is each truth called right?', replicates='1000'),
         ),
         repo_out='docs/studies/reciprocity', repo_ok=False, seconds=35.0),

    Tool('burn_dose_figure', 'Burns against dose: damage or a changing sample?', 'burn', 'figures',
         'tests/tools/burn_dose_figure.py',
         'NX burn scans 14 and 15 (absorbers 12 and 8) against clock time and against dose (Σ Monc × foil '
         'transmission): a beam-driven change coincides against dose, a sample changing by itself against time.',
         committed=('docs/figures/burn_dose',),
         docs=('docs/figures/burn_dose/README.md', 'docs/handoff_out/07-burn-trends.md#**Dose instead of',
               'docs/physics_notes.md#α = 3°'),
         data='any', defaults={'--out': OUT}, spec_option='--spec',
         variations=(
             V('Nominal foils (1.4247 per unit)', 'The flux ratio of the docs\' "4.1x" instead of the calibrated '
               '4.68: the dose ratio of the drifts moves from 0.79 to 0.90.', 'docs/physics_notes.md#The position drifts',
               absorbers='nominal'),
             V('One spot measured twice', 'Scan 15\'s dose and time follow scan 14\'s: 15 starts where 14 '
               'ended, as one spot would.', 'docs/handoff_out/07-burn-trends.md#scans at different', join=True),
             V('Moments estimator', 'The legacy moments instead of the template.', 'docs/handoff_out/07-burn-trends.md',
               estimator='moments'),
         ),
         inputs=(NX,), seconds=3.1),

    # ------------------------------------------------------------ reflectivity
    Tool('patch_demo', 'Fit demonstrator (window)', 'refl', 'window',
         'tests/tools/patch_demo.py',
         'Reflectivity patching on synthetic scans with known truth: every method, the denoised data, '
         'pulls, factors, error bands; space bar for a new noise replicate.',
         docs=('docs/reports/patch_demo.md',),
         variations=(
             V('Bare water', 'No fringes: the joins rest on a smooth curve.', 'docs/reports/patch_demo.md#**Reflectivity controls**: truth',
               set='truth=water'),
             V('DPPC monolayer', 'A lipid monolayer\'s gentle modulation.', 'docs/reports/patch_demo.md#**Reflectivity controls**: truth',
               set='truth=dppc'),
             V('Thick film (250 Å)', 'Kiessig fringes of period 2π/d = 0.025 Å⁻¹: denser fringes at the joins.',
               'docs/SYNTHETIC_DATA.md#(Qc/2Qz)⁴ with a', set='thickness=250'),
             V('Staggered overlaps', 'No coinciding points at the joins: the coinciding-points ratio is unavailable, '
               'curve models must interpolate.', 'docs/reports/patch_demo.md#**Reflectivity controls**: truth', set='plan=nx_staggered'),
             V('Critical-edge aside', 'A staggered overlap across Qc (P1): the legacy factor is 16.6 % low; the '
               'owner does not patch there.', 'docs/reports/patch_demo.md#the default joint fit is +2.44 %', set=['truth=water', 'plan=edge']),
             V('Counts x100', 'Every method within 0.15 % of the truth: what remains is bias, not noise.',
               'docs/reports/patch_demo.md#0.15 % of', set='counts=100'),
             V('Poisson monitor', 'Monc as Poisson counts (the older model) instead of the owner\'s strict 0.05 %: '
               'legacy pull SD 1.3-1.4.', 'docs/reports/patch_demo.md#a Poisson Monc is', set='monitor=poisson'),
         ),
         repo_ok=False),
    Tool('patch_demo_survey', 'Fit demonstrator: survey over replicates', 'refl', 'text',
         'tests/tools/patch_demo.py',
         'Every patching method over many noise replicates of the demonstrator\'s synthetic scans: bias, pull '
         'mean and pull SD per join, failures (the numbers behind the window\'s single replicate).',
         docs=('docs/reports/patch_demo.md', 'docs/SYNTHETIC_DATA.md#summary, rows ='),
         defaults={'--survey': '50'},
         variations=(
             V('Staggered overlaps (200)', 'No coinciding points at any join: the documents\' '
               'refl.survey(Config(plan=\'staggered\'), range(200)).', 'docs/SYNTHETIC_DATA.md#summary, rows =',
               survey='200', set='plan=staggered'),
             V('Poisson monitor', 'Monc as Poisson counts: the legacy method\'s pull SD 1.3-1.4.',
               'docs/reports/patch_demo.md#0.05 % relative', set='monitor=poisson'),
             V('Every method', 'All 15 methods, not only the window\'s four.', 'docs/reports/patch_demo.md',
               methods='all'),
         ),
         seconds=3.5, repo_ok=False),
    Tool('patch_demo_figures', 'Fit demonstrator report figures', 'refl', 'figures',
         'tests/tools/patch_demo.py',
         'The six figures, numbers.json and summary CSVs of the fit demonstrator report (200 replicates per '
         'survey).',
         committed=('docs/figures/patch_demo',),
         docs=('docs/reports/patch_demo.md', 'docs/COMPARISONS.md#| C34 |'),
         defaults={'--save': OUT},
         variations=(
             V('Smoke run', 'The same figures from a few replicates (seconds instead of minutes).',
               'docs/reports/patch_demo.md#python tests/tools/patch_demo.py --save DIR', save=OUT, quick=True),
             V('At today\'s guard (p 0.7)', 'The report\'s figures with the joint fit\'s guard at the reader\'s '
               'default since 2026-11-24 (p 0.7, study A) instead of the report\'s p 0.3: pull SDs within 0.05.',
               'docs/reports/patch_demo.md#Run at the joint fit\'s guard p 0.3', save=OUT, guard_p=0.7),
             V('The two default views', 'Only the window\'s two default views as PNG.',
               'docs/reports/patch_demo.md#python tests/tools/patch_demo.py --views', save='', views=OUT),
             V('Views: DPPC and a fading burn', 'The window\'s two views for a DPPC monolayer and a fading burn.',
               'docs/reports/patch_demo.md#**Reflectivity controls**: truth', save='', views=OUT, set=['truth=dppc', 'change=fade']),
         ),
         repo_out='docs/figures/patch_demo', seconds=None),
    Tool('ref_patch_gauntlet', 'Patching gauntlet (synthetic, judged)', 'refl', 'data',
         'tests/tools/ref_patch_gauntlet.py',
         'Every patching method on many noise replicates of synthetic reflectivity under many conditions, '
         'judged by hand-off 08\'s rules (|mean pull| < 0.2, pull SD 0.9-1.15).',
         committed=('docs/comparisons_data/ref_patch_gauntlet',),
         docs=('docs/handoff_out/08-ref-patch-comparison.md', 'docs/comparisons_data/ref_patch_gauntlet/summary.md',
               'docs/COMPARISONS.md#| C36 |'),
         defaults={'--out': OUT, '--design': 'core', '--methods': 'key', '--replicates': '100'},
         variations=(
             V('Core, all methods', 'The seven core conditions with every method (about 3 min).',
               'docs/COMPARISONS.md#| C36 |', design='core', methods='all', replicates='400'),
             V('Full gauntlet (as committed)', 'Core, grid and random designs with the key methods (the six of '
               '--methods key and the default with the foil prior, computed always): the run behind the default '
               '(about 25 min; every committed row reproduced exactly, 2026-11-23).',
               'docs/COMPARISONS.md#| C36 |', design='all', methods='key', replicates='400'),
             V('Full gauntlet, every method', 'The same designs with every method of the tool, including those '
               'added since (hybrid, other orders and windows).', 'docs/COMPARISONS.md#| C36 |', design='all',
               methods='all', replicates='400'),
             V('Poisson monitor', 'Monc with Poisson noise: the χ² test is blunter, the verdict the same.',
               'docs/physics_notes.md#with `series.all_series`: GID,', monitor='poisson'),
             V('Counting errors only', 'The monitor\'s 0.05 % left out of the per-point errors: pulls wider than 1 '
               'above about 3e5 counts.', 'docs/SYNTHETIC_DATA.md#reported 0.66–0.84 %).', errors='counting'),
             V('Grid: films and roughness', 'One factor at a time from the baseline: film thickness and roughness.',
               'docs/physics_notes.md#**Done** (`tests/tools/ref_patch_gauntlet.py --design', design='grid', methods='key',
               conditions='layer_film50,layer_film250,layer_film400,rough_film_2.5,rough_film_6'),
             V('Grid: planted faults', 'A slit change the monitor misses and a foil 2 % off: where the foil prior '
               'misleads.', 'docs/physics_notes.md#**Done** (`tests/tools/ref_patch_gauntlet.py --design', design='grid', methods='all',
               conditions='fault_slits_missed,fault_foil_2pc'),
             V('Grid: low flux', 'Flux x0.3 to x0.03: how the methods degrade as counts fall.',
               'docs/physics_notes.md#**Done** (`tests/tools/ref_patch_gauntlet.py --design', design='grid', methods='key',
               conditions='flux_x0.3,flux_x0.1,flux_x0.03'),
         ),
         committed_with={'--design': 'all', '--methods': 'key', '--replicates': '400'},
         repo_out='docs/comparisons_data/ref_patch_gauntlet', repo_ok=False, seconds=None),
    Tool('ref_patch_biased_joins', 'Why five gauntlet joins are biased (extension 4)', 'refl', 'data',
         'tests/tools/ref_patch_biased_joins.py',
         'The default joint fit\'s five biased designed joins and the covariance study\'s first join, redrawn '
         'with the gauntlet\'s seeds and fitted with the guard off, other orders and windows, noise-free.',
         committed=('docs/comparisons_data/ref_patch_biased_joins',),
         docs=('docs/comparisons_data/ref_patch_gauntlet/summary.md', 'docs/COMPARISONS.md',
               'docs/comparisons_data/ref_patch_biased_joins/summary.md'),
         defaults={'--out': OUT},
         variations=(V('Fewer replicates', 'A quick look: 100 replicates per join and 100 seeds of the covariance '
                       'study; the default\'s pulls no longer match the gauntlet\'s exactly.',
                       'tests/tools/ref_patch_biased_joins.py', replicates='100', covariance_seeds='100'),),
         repo_out='docs/comparisons_data/ref_patch_biased_joins', seconds=15),
    Tool('coincidence_synth', 'Do joins need coincident Qz? (synthetic)', 'refl', 'figures',
         'tests/tools/coincidence_synth.py',
         'Two synthetic scans of known curves meeting at a join with no overlap, k coincident points, a '
         'staggered overlap or a coarser second grid, fitted by every patching method and scored against the '
         'truth: bias, pull SD, error size, share answered.',
         committed=('docs/studies/coincident_points',),
         docs=('docs/studies/coincident_points/summary.md', 'docs/COMPARISONS.md#| C57 |'),
         defaults={'--out': OUT, '--trials': '200'},
         variations=(
             V('Example fits only', 'Figure C1 alone: one join per geometry, in a second or two.',
               'docs/studies/coincident_points/summary.md### The test', examples=True),
             V('More trials', '1000 joins per cell: the pooled biases to about ±0.02 %.',
               'docs/studies/coincident_points/summary.md### The answer', trials='1000'),
         ),
         repo_out='docs/studies/coincident_points', seconds=10),
    Tool('qoff_study', 'Qoff and Qc of R/R_F: the proposer\'s study (F79)', 'refl', 'figures',
         'tests/tools/qoff_study.py',
         'Synthetic reflectivity with a known angle offset: the edge fit and the roughness of ln R/R_F (robust and '
         'least squares) and the joint Qc + Qoff fit against the truth over offsets, samples, counts, outliers, '
         'resolution, a wrong Qc and the reader\'s patch; the NX school scans at the GUI\'s preset and at the '
         'proposals: figures Q1-Q5.',
         committed=('docs/studies/qoff',),
         docs=('docs/studies/qoff/summary.md', 'docs/COMPARISONS.md#| C50 |', 'docs/FEATURE_REQUESTS.md#| F79 |'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('The anatomy and NX only', 'Q1 and Q5, which need no replicates (about 20 s): what a wrong Qoff does at '
               'the edge, and the NX school proposal against the preset.', 'docs/studies/qoff/summary.md### 6. The NX school scans',
               only='Q1,Q5'),
             V('Outliers', 'One or two points off by 30 %, and the worst case, the first point above the edge: the '
               'edge fit holds, the roughness is pulled.', 'docs/studies/qoff/summary.md### 2. Outliers', design='outliers'),
             V('Resolution', 'A Qz resolution of 0.0002 to 0.001 Å⁻¹ FWHM smears the edge and reads as a negative Qoff.',
               'docs/studies/qoff/summary.md### 3. Resolution', design='resolution'),
             V('A wrong Qc', '1 M NaCl reduced at water\'s Qc and the other way round: Qoff absorbs the error one for one; '
               'the joint fit lies on Qc − Qoff = constant.', 'docs/studies/qoff/summary.md### 4. A wrong Qc, and Qc with Qoff', design='qc'),
             V('More replicates (200)', 'Every design with 200 replicates (about 15 min).', 'docs/studies/qoff/summary.md### 1. Do they find the offset?',
               replicates='200'),
         ),
         repo_out='docs/studies/qoff', repo_ok=False),

    Tool('ref_guard_study', 'Study A: how strict the joint fit\'s guard should be', 'refl', 'figures',
         'tests/tools/ref_guard_study.py',
         'The guard\'s p from 0.001 to 0.9, the guard off, an AICc average and the legacy factor on C45\'s six '
         'joins (C45 reproduced first), a downstream fit, the NX school joins beside the foil ratio, and a '
         'robustness map over fringe sampling and counts, on coinciding and staggered grids: figures A1-A8, R and RS.',
         committed=('docs/studies/reflectivity_guard',),
         docs=('docs/studies/2026-11-24_two_decisions_plan.md### Study A: reflectivity joins and the guard',
               'docs/studies/reflectivity_guard/data_summary.md', 'docs/COMPARISONS.md#| C48 |'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('Smoke run', 'Every figure from a few replicates (about 10 s): checks the tool, not the numbers.',
               'docs/studies/reflectivity_guard/data_summary.md#(`--quick`)', quick=True),
             V('C45 and the decision curve only', 'The six joins on the gauntlet\'s seeds (C45 comes back exactly), '
               'figures A2-A6 and the 2000-replicate precision check.',
               'docs/studies/2026-11-24_two_decisions_plan.md#so that today\'s numbers come back exactly first',
               figures='A2,A3,A4,A5,A6'),
             V('Decision curve, 5000 replicates', 'A5 with the precision run at 5000 replicates per join: how much '
               'of the first join\'s pull SD is sampling.',
               'docs/studies/reflectivity_guard/data_summary.md#(precision check)', figures='A5', precision='5000'),
             V('Robustness map, 2000 per cell', 'R with 2000 replicates per cell (500 per fringe phase).',
               'docs/studies/reflectivity_guard/data_summary.md### R. Robustness map', figures='R',
               r_replicates='2000'),
             V('Real data only', 'A8: the NX school joins under each choice beside the calibrated foil ratio.',
               'docs/studies/reflectivity_guard/data_summary.md### A8. NX school, scans 6–9', figures='A8'),
         ),
         inputs=(NX,), repo_out='docs/studies/reflectivity_guard', seconds=54,
         volatile=(r'Total wall time', r'^- .+: \d+(\.\d+)? s$')),     # data_summary.md's timings
    Tool('ref_patch_survey', 'Patching methods on real scans (survey)', 'refl', 'data',
         'tests/tools/ref_patch_survey.py',
         'Every patching method at every join of a SPEC file\'s reflectivity series; split scans give known '
         'truth on real curves; repeated scans give empirical pulls.',
         committed=('docs/comparisons_data/ref_patch_nx',),
         docs=('docs/handoff_out/08-ref-patch-comparison.md', 'docs/reports/ref_patch_joint_fit.md',
               'docs/COMPARISONS.md#| C33 |'),
         data='any', defaults={'--spec': NX, '--out': OUT, '--split': True, '--repeats': True},
         spec_option='--spec',
         variations=(
             V('Joins only', 'The methods at the measured joins, without the split and repeat tests.',
               'docs/handoff_out/08-ref-patch-comparison.md#python tests/tools/ref_patch_survey.py --spec', split=False, repeats=False),
         ),
         repo_out='docs/comparisons_data/ref_patch_nx', seconds=1.3),
    Tool('covariance_pulls', 'Downstream fits with and without the covariance', 'refl', 'data',
         'tests/tools/covariance_pulls.py',
         'Synthetic NX-like scans of a 25 Å film reduced by each patch method and fitted for thickness, '
         'density and roughness under four error treatments: pull SD is 1 only with the full covariance.',
         committed=('docs/comparisons_data/downstream_covariance',),
         docs=('docs/reports/downstream_covariance.md', 'docs/COMPARISONS.md#| C35 |'),
         defaults={'--out': OUT, '--seeds': '60'},
         variations=(
             V('As committed (300 seeds, NX σ)', 'The run behind the report: 300 seeds and the NX scans\' σ table.',
               'docs/reports/downstream_covariance.md#`python tests/tools/covariance_pulls.py --seeds', seeds='300', nx=True),
             V('Poisson monitor', '"A covariance is only as good as its diagonal": with the older Poisson Monc the '
               'legacy column\'s pulls change.', 'docs/reports/downstream_covariance.md#The same with', poisson_monitor=True),
         ),
         committed_with={'--seeds': '300', '--nx': True},
         repo_out='docs/comparisons_data/downstream_covariance', repo_ok=False, seconds=3.2),
    Tool('compare_methods', 'Old and new methods as CSV (C2, C10, C11, ...)', 'refl', 'data',
         'tests/tools/compare_methods.py',
         'Old and new methods side by side on the same data, as CSV files with a manifest: error models, '
         'legacy vs pinhole GID, pinhole distance, exact vs per-axis pinhole angles, the footprint window, '
         'absorber factors, "Sum All" as the counts over the monitors vs the mean of the normalised frames, '
         'each frame\'s true incidence (header In_Rot vs α from L).',
         committed=('docs/comparisons_data/manifest.json', 'docs/comparisons_data/C2_*',
                    'docs/comparisons_data/C6_*', 'docs/comparisons_data/C10_*', 'docs/comparisons_data/C11_*',
                    'docs/comparisons_data/C21_*', 'docs/comparisons_data/C24_*', 'docs/comparisons_data/C41_*',
                    'docs/comparisons_data/C43_*'),
         docs=('docs/COMPARISONS.md',), data='any',
         defaults={'--out': OUT, '--spec': NX}, spec_option='--spec',
         variations=(
             V('Without the 2D maps', 'Skips the large GID maps (the CSVs of profiles only).',
               'docs/COMPARISONS.md#Gaps (what the figure agent will not find yet)', no_maps=True),
             V('Reflectivity only', 'Only the error-model comparison of scans 6-9 (C2/C3).',
               'docs/COMPARISONS.md#| C3 |', gid=''),
             V('GID only, one level', 'Only scan 11 (C10, C11, C21).', 'docs/COMPARISONS.md#| C10 |', ref='', gid='11'),
         ),
         repo_out='docs/comparisons_data', seconds=39.0),
    Tool('absorber_steps', 'Absorber steps measured between scans', 'refl', 'text',
         'tests/tools/absorber_steps.py',
         'Measured absorber steps between overlapping reflectivity scans against the nominal absfac^-Δn, and '
         'the extra Al thickness each implies (P28).',
         docs=('docs/COMPARISONS.md#| C8 |', 'docs/PHYSICS_ISSUES.md'), data='any',
         free=NX + ' 6,7,8,9', free_help='SPEC file, then the scans as 6,7,8,9', spec_option='free',
         seconds=1.3),
    Tool('foil_fit_from_joins', 'Foil thicknesses from the joins table', 'refl', 'text',
         'tests/tools/foil_fit_from_joins.py',
         'Six binary foil thicknesses fitted to the owner\'s 963 measured joins (hand-off 03), and every join\'s '
         'residual: a foil effect separated from a monitor that missed a slit change.',
         docs=('docs/handoff_out/03-check-foil-fit-and-figures.md', 'docs/handoff_out/03-answer/ABSORBER_RATIOS.md'),
         data='public', defaults={'joins': 'docs/handoff_out/03-answer/joins.csv'},
         inputs=('docs/handoff_out/03-answer/joins.csv',),
         variations=(
             V('Strict cuts', 'Monc/Monp within 1 %, χ²/dof < 5, no error floor: each foil moves by at most '
               '0.9 µm (the fit is robust to its cuts).', 'docs/physics_notes.md#*Fit quality.* The',
               monc_tol='0.01', chi2_max='5', floor='0'),
             V('Loose cuts', 'Monc/Monp within 3 %, no χ² cut, 1 % floor.', 'docs/physics_notes.md#*Fit quality.* The',
               chi2_max='inf', floor='0.01'),
             V('Less clipping', 'Clip at 10 robust SDs instead of 5: outlying joins pull the foils.',
               'tests/tools/foil_fit_from_joins.py', clip='10'),
         ),
         seconds=0.1),

    # ------------------------------------------------------------ GID
    Tool('pinhole_figures', 'Pinhole GID geometry: eight figures', 'gid', 'figures',
         'tests/tools/pinhole_figures.py',
         'The pinhole geometry drawn from the reader\'s own code: lab frame, direct beam, top view, β per '
         'column, the raised arm, the second module, footprint and usable columns, the S4 opening.',
         committed=('docs/figures/pinhole',), docs=('docs/figures/pinhole/README.md',), data='public',
         defaults={'--out': OUT}, spec_option='--spec',
         variations=tuple(
             V('Case %d only' % n, what, 'docs/figures/pinhole/README.md', only=str(n)) for n, what in (
                 (3, 'Top view: each column through the S4 pinhole.'),
                 (4, 'β depends on the column, not only on the row.'),
                 (7, 'Footprint and usable columns; the second module reached only below α ≈ 0.037°.'),
                 (8, 'The S4 opening swept 0.05-1.0 mm: 2θ acceptance, edge ramps, counts proportional to the '
                     'opening; Det_Th 14/16/18°.'))) + (
             V('Case 8 at Det_Th 14°', 'The S4 figure for the frame at Det_Th 14° instead of 16°: the footprint '
               'seen per column grows (2.1 -> 2.4 mm).', 'docs/figures/pinhole/README.md#**The numbers** (NX,',
               only='8', case8_dth='14'),
             V('Case 8 with S4 0.05, 0.2 and 1.0 mm', 'The 2θ acceptance of one column for a pinhole four times '
               'narrower and five times wider than NX\'s 0.2 mm.', 'docs/figures/pinhole/README.md#| S4 opening',
               only='8', case8_openings='0.05,0.2,1.0'))),
    Tool('gid_patching_diagrams', 'GID patching diagrams (manual)', 'gid', 'figures',
         'tests/tools/gid_patching_diagrams.py',
         'The manual\'s eight diagrams of GID patching: frame anatomy, columns to 2θ, frames covering 2θ, '
         'pixels to cells, levels and overlaps, the join factor, 2θ within a scan, the scan join.',
         committed=('docs/manual/figures/gid_patching',),
         docs=('docs/manual/gid_patching.md', 'docs/manual/figures/gid_patching/README.md'), data='public',
         defaults={'--out': OUT},
         variations=(
             V('Diagram 6: the join factor', 'How the level join factor is fitted, with the NX 11 + 12 numbers.',
               'docs/manual/gid_patching.md', only='6'),
             V('Diagram 8: the scan join', 'Scan 11 split in two, scan B x 0.8: the scan join recovers 1.25 (P42).',
               'docs/manual/gid_patching.md#**8. Joining two', only='8'),
         ),
         inputs=(NX,), seconds=35.7),
    Tool('gid_compare_figures', 'Legacy vs pinhole GID patch', 'gid', 'figures',
         'tests/tools/gid_compare_figures.py',
         'Before and after: the legacy 3-column patch against the pinhole patch on the same scans (maps, '
         'profiles, joins).',
         committed=('docs/figures/gid_compare',),
         docs=('docs/figures/gid_compare/README.md', 'docs/COMPARISONS.md#| C10 |'), data='any',
         defaults={'--scans': '11', '--out': OUT}, spec_option='--spec',
         variations=(
             V('Two Qz levels (11 + 12)', 'The level join as well; not like for like (scan 12 stopped after 4 '
               'frames).', 'docs/figures/gid_compare/README.md#python tests/tools/gid_compare_figures.py --scans 11 --out',
               scans='11,12', peak='none', note='not like for like: scan 12 stopped after 4 frames'),
         ),
         inputs=(NX,), seconds=7.3),
    Tool('pinhole_beam_figure', 'Beam profile from GID data', 'gid', 'figures',
         'tests/tools/pinhole_beam_figure.py',
         'The beam profile the "beam" response measures along the beam axis, and the beam height it implies '
         '(about 52 µm on NX scan 11).',
         committed=('docs/figures/pinhole_beam',), docs=('docs/figures/pinhole_beam/README.md',
                                                         'docs/physics_notes.md#outer-column diagnosis (the lower level gains columns'),
         data='any', defaults={'--out': OUT}, spec_option='--spec', inputs=(NX,), seconds=7.2),
    Tool('pinhole_beam_profile', 'Gaussian beam vs uniform footprint', 'gid', 'text',
         'tests/tools/pinhole_beam_profile.py',
         'What a Gaussian beam does to the pinhole patch, which assumes a uniform footprint: the column '
         'response it predicts and the bias left in a map.',
         docs=('docs/physics_notes.md#**A (computed, `tests/tools/pinhole_beam_profile.py`,', 'docs/COMPARISONS.md#| C23 |'), data='public',
         variations=(
             V('Beam 60 µm', 'A wider beam: bias inside the map 0.97-1.03 (against 0.93-1.04 at 30 µm), edges '
               '0.91-1.37 (against 0.71-2.8).', 'docs/physics_notes.md#all frames, but', fwhm_v='0.060'),
             V('Beam 52 µm (as NX implies)', 'The beam height NX scan 11\'s data imply.',
               'docs/physics_notes.md#FWHM 18.0 mm', fwhm_v='0.052'),
             V('Narrow horizontal beam (0.1 mm)', 'The horizontal width smears which point of the beam axis a '
               'column sees, never its 2θ.', 'docs/physics_notes.md#The reader takes', fwhm_h='0.1'),
         ),
         inputs=(NX,), seconds=10.6),
    Tool('gid_stray_light', 'Stray light in pinhole GID frames', 'gid', 'figures',
         'tests/tools/gid_stray_light.py',
         'β profiles of column bands inside and outside the usable window, per Qz level: light that cannot '
         'have come from the footprint through the pinhole (P40).',
         committed=('docs/figures/gid_stray_light',), docs=('docs/figures/gid_stray_light/README.md',),
         data='any', defaults={'--out': OUT}, spec_option='--spec',
         variations=(V('Scan 11 alone', 'One level.', 'docs/figures/gid_stray_light/README.md', scans='11'),),
         inputs=(NX,), seconds=2.7),
    Tool('single_frame_truth', 'Single frames as ground truth', 'gid', 'text',
         'tests/tools/single_frame_truth.py',
         'Each unpatched frame already puts the Bragg peak at its 2θ: frames must agree, and the patched map '
         'must give back their centre and width; the S4-detector distance that makes them agree.',
         docs=('docs/manual/gid_patching.md#**Measured (2026-11-21), NX', 'docs/COMPARISONS.md#| C28 |'), data='any',
         defaults={'--scans': '11', '--peak': '16.63'}, spec_option='--spec',
         variations=(
             V('Fine distance scan', 'Distances 260-272 mm in 1 mm steps around the calibrated 265 mm.',
               'docs/manual/gid_patching.md#**Measured (2026-11-21), NX', distances='260:273:1'),
         ),
         inputs=(NX,), seconds=74.3),
    Tool('gid_movie', 'GID movie on one 2θ axis', 'gid', 'figures',
         'tests/tools/gid_movie.py',
         'GID frames played on a common 2θ axis with the zoom and the colour scale fixed: a real Bragg peak '
         'stands still while the detector window and anything fixed on it slide (M7, F69).',
         committed=('docs/figures/gid_movie',),
         docs=('docs/figures/gid_movie/README.md', 'docs/gui/image_display.md#**M7 (M): a'), data='any',
         defaults={'--out': OUT}, spec_option='--spec',
         variations=(
             V('Also on detector pixels', 'The opposite view: the peak walks across the columns, detector-fixed '
               'features stay put.', 'docs/gui/image_display.md#scattering) moves. A', pixels=True),
             V('Zoomed on the peak', 'The zoom held in angle while the frames play (no change of zoom or colour '
               'between frames).', 'docs/gui/image_display.md#brightest column stays', window='15.5,18', beta='-0.5,3'),
             V('Calibrated S4-detector distance', 'At 265.7 mm the peak stands stiller: the drift with Det_Th '
               '(+0.018 °/° at the header 271 mm) vanishes.', 'docs/manual/gid_patching.md#NX scan 11 calibrates',
               pinhole_mm='265.7'),
         ),
         inputs=(NX,), seconds=6.8),
    Tool('gid_column_groups', 'GID level join from groups of columns', 'gid', 'figures',
         'tests/tools/gid_column_groups.py',
         'The pinhole patch of each Qz level made from groups of detector columns, and the level join\'s factor '
         'per group with the cells of the β overlap: why the factor depends on which columns are used.',
         committed=('docs/figures/gid_column_groups',),
         docs=('docs/figures/gid_column_groups/README.md', 'docs/physics_notes.md#the β-per-row geometry'), data='any',
         defaults={'--out': OUT}, spec_option='--spec',
         variations=(
             V('The same columns at both levels', 'Groups inside the columns every level has: the pooled group '
               'factors then agree within errors (1.024, 1.009, 0.985).', 'docs/physics_notes.md#upstream tail is',
               columns='common'),
             V('Beam response', 'The response along the beam axis instead of one factor per column: the column '
               'dependence remains.', 'docs/physics_notes.md#changes the upper level', response='beam'),
             V('No response', 'Each group\'s map keeps its columns\' own light.', 'docs/physics_notes.md#nor on a',
               response='none'),
             V('Angle maps (faster)', 'The maps of the cells themselves, in (2θ, β), without the regridding to Q.',
               'tests/tools/gid_column_groups.py', axes='Angles'),
         ),
         inputs=(NX,), seconds=25.6),
    Tool('gid_method_survey', 'GID patching methods (survey)', 'gid', 'data',
         'tests/tools/gid_method_survey.py',
         'Every GID patching method on every GID set of SPEC files: frames-agree χ², distance calibration, '
         'single frames against patches, scale recovery.',
         committed=('docs/comparisons_data/gid_survey_nx',),
         docs=('docs/handoff_out/06-gid-method-comparison.md', 'docs/comparisons_data/gid_survey_nx/summary.md'),
         data='any', defaults={'--spec': NX, '--out': OUT, '--split': True}, spec_option='--spec',
         variations=(
             V('Without the split test', 'Only the methods and the calibration.',
               'docs/handoff_out/06-gid-method-comparison.md#python tests/tools/gid_method_survey.py --spec', split=False),
             V('Header distance only', 'No distance calibration: the methods at the header\'s S4-detector distance.',
               'docs/handoff_out/06-gid-method-comparison.md#python tests/tools/gid_method_survey.py --spec', no_calibration=True),
         ),
         repo_out='docs/comparisons_data/gid_survey_nx', inputs=(NX,), seconds=None),

    # ------------------------------------------------------------ monitor, absorbers, SPEC
    Tool('monitor_noise_mc', 'Monitor normalisation: Monte Carlo', 'monitor', 'text',
         'tests/tools/monitor_noise_mc.py',
         'The error the reader propagates for monitor-normalised counts, checked by Monte Carlo against the '
         'derived formula; mean of ratios against ratio of sums; the NX monitors\' scatter.',
         docs=('docs/reports/monitor_noise.md', 'docs/COMPARISONS.md#| C4 |'), data='public',
         variations=(V('Simulation only', 'Parts 1 and 2 without the real-data look.',
                       'docs/reports/monitor_noise.md#`python3 tests/tools/monitor_noise_mc.py`; seed', no_real=True),
                     V('Bright regimes, Poisson vs noiseless monitor', 'Regimes A and C2: the reader\'s error is '
                       'too small with a Poisson monitor and 3.5 % too large with a noiseless one.',
                       'docs/reports/monitor_noise.md#| A |', regimes='A,C2', monitors='poisson,exact', no_real=True),
                     V('High Qz (regime B)', 'Few counts: every formula agrees, the monitor term does not matter.',
                       'docs/reports/monitor_noise.md#| B |', regimes='B', no_real=True),
                     V('Quick look (5000 trials)', 'The same tables from fewer trials (±1 % on each σ).',
                       'tests/tools/monitor_noise_mc.py', trials='5000', no_real=True)),
         seconds=16.3),
    Tool('monitor_distribution', 'Monitor scatter: its distribution', 'monitor', 'text',
         'tests/tools/monitor_distribution.py',
         'Frame-to-frame deviations of Monc pooled over the sample SPEC files: Gaussian, Student t or Laplace; '
         'drift or noise; what share of each point\'s variance the monitor takes.',
         docs=('docs/physics_notes.md#uncertainty about 3×.', 'docs/COMPARISONS.md#| C3 |'),
         data='any', defaults={'paths': NX}, spec_option='paths',
         variations=(ALL_SAMPLE_DATA('paths', 'Part A pooled over every SPEC file the reader can see.',
                                        'docs/physics_notes.md#uncertainty about 3×.'),),
         inputs=(NX,), seconds=1.9),
    Tool('monitor_ratio', 'Monc/Monp: beam variation or noise', 'monitor', 'text',
         'tests/tools/monitor_ratio.py',
         'The two monitors\' common scatter (beam variation, cancels in the ratio) against each one\'s own '
         'noise, per scan.', docs=('docs/reports/monitor_noise.md', 'docs/physics_notes.md#**A.** Measured on'), data='any',
         free=NX, free_help='a SPEC file (default: NX school)', spec_option='free', seconds=0.1),
    Tool('monitor_witness', 'Monc jumps: the detector as witness', 'monitor', 'text',
         'tests/tools/monitor_witness.py',
         'Whether Monc\'s large jumps are real flux (the detector follows) or monitor errors (it does not), '
         'from second differences along each scan.',
         docs=('docs/handoff_out/01-monitor-noise-analysis.md',), data='public', inputs=(NX,), seconds=0.7),
    Tool('monitor_gains', 'Monitor gain lines the reader cannot read', 'monitor', 'text',
         'tests/tools/monitor_gains.py',
         'Every #M Monc Gain line that is not a number with a known unit, and the scans without one (F52).',
         docs=('docs/reports/monitor_gains.md',), data='any', defaults={'paths': NX}, spec_option='paths',
         variations=(ALL_SAMPLE_DATA('paths', 'Every gain line the reader cannot read, in every SPEC file it '
                                              'can see (the report\'s table was made this way).',
                                     'docs/reports/monitor_gains.md#Measured on every'),),
         seconds=0.1),
    Tool('spec_epoch', 'What the SPEC Epoch column measures', 'monitor', 'text',
         'tests/tools/spec_epoch.py',
         'Epoch of each scan\'s first point against its header time: seconds since the file\'s #E, plus the '
         'local-time offset of #D.', docs=('docs/physics_notes.md#time; for each',), data='any',
         defaults={'specs': NX}, spec_option='specs',
         variations=(ALL_SAMPLE_DATA('specs', 'The nine sample files of the 2026-11-16 answer: NX and the bu '
                                              'files.', 'docs/physics_notes.md#time; for each'),),
         seconds=0.1),

    Tool('fit_scan_survey', 'Scan-shape fits of every column (survey)', 'monitor', 'data',
         'tests/tools/fit_scan_survey.py',
         'The scan-shape fit the SpecPlot shows (peak, edge, box, flat, weak) on every scan and column of a SPEC '
         'file, as CSV: what the fit rules decide and how long they take.',
         committed=('docs/comparisons_data/C37_fit_scan_new_nx.csv', 'docs/comparisons_data/C37_fit_scan_old_nx.csv'),
         docs=('docs/COMPARISONS.md',), data='any', spec_option='--spec',
         defaults={'--out': OUT + '/C37_fit_scan_new_nx.csv'},
         variations=(
             V('Rules before 2026-11-23', 'No flat test and 20000 evaluations: the old rules, for comparison.',
               'tests/tools/fit_scan_survey.py', old=True, out=OUT + '/C37_fit_scan_old_nx.csv'),
         ),
         inputs=(NX,)),
    Tool('timeline_survey', 'Sample timeline: what a SPEC file holds', 'monitor', 'text',
         'tests/tools/timeline_mock.py',
         'Counts only, safe for private files: scans and their kinds, sample-height scans, motor redefinitions, '
         'sx changes, sample-environment columns (research for the timeline tab, F83).',
         docs=('docs/gui/timeline/research.md',), data='any', subcommand='survey',
         defaults={'paths': NX}, spec_option='paths', inputs=(NX,)),

    # ------------------------------------------------------------ synthetic data
    Tool('synthetic_dataset', 'Open a synthetic data set', 'synthetic', 'dataset',
         'tests/tools/synthetic_dataset.py',
         'A SPEC file with Pilatus frames (or MCA files) drawn from a known truth, written to a folder of its '
         'own and opened in the reader: reduce it and compare with the truth.',
         docs=('docs/SYNTHETIC_DATA.md',),
         defaults={'--out': OUT},
         variations=(
             V('Bare water', 'Fresnel with water\'s critical edge and roughness: R/R_F falls as exp(-Qz²σ²).',
               'docs/SYNTHETIC_DATA.md#2.1 New (`tests/synthetic/`)', truth='water'),
             V('DPPC monolayer', 'A lipid monolayer on water.', 'docs/SYNTHETIC_DATA.md#2.1 New (`tests/synthetic/`)', truth='dppc'),
             V('Thick film (250 Å)', 'Kiessig fringes of period 2π/d: check the period in Ref Patch.',
               'docs/SYNTHETIC_DATA.md#(Qc/2Qz)⁴ with a', thickness='250'),
             V('Missed slit change (P29)', 'The monitor misses a slit change: the foil prior misleads at that join.',
               'docs/SYNTHETIC_DATA.md#Faults, one value', fault='slits'),
             V('Low counts (x0.1)', 'One tenth of the NX rates: the joins\' errors grow by √10.',
               'docs/SYNTHETIC_DATA.md#`measure(..., expected=True)` gives', counts='0.1'),
             V('Rough interfaces (6 Å)', 'R/R_F falls as exp(−Qz²σ²): twice the roughness, four times the '
               'decay rate.', 'docs/SYNTHETIC_DATA.md#2.1 New (`tests/synthetic/`)', roughness='6'),
             V('Background ×100', 'A diffuse background a hundred times NX\'s: the ROI background boxes earn '
               'their keep at high Qz.', 'docs/physics_notes.md#reaching back), 3–5', background='100'),
             V('XFNTR series', 'Fluorescence near total reflection: one MCA file per Qz, a surface and a bulk ion.',
               'docs/SYNTHETIC_DATA.md#| `gid_levels` |', kind='xfntr'),
             V('Burn series', 'One spot measured 21 times, the peak decaying with τ = 400 s.',
               'docs/SYNTHETIC_DATA.md#| `pilatus_image`, `write_pilatus_tif`', kind='burn'),
             V('MCA: the hard case (Zn under 10 keV)', 'Study B\'s hard case as ten MCA spectra: select them all, '
               'Fit lines, and compare with the true line counts in truth.json (the O 1s wing defeats every fit).',
               'docs/reports/mca_fit_demo.md#**In the reader itself.**', kind='mca'),
             V('MCA: Zn under a 12 keV beam', 'The beam-energy route: the scatter has moved away, and Fit lines with '
               'Poisson weights (Preferences) finds the line within 1 %.', 'docs/reports/mca_fit_demo.md#4.4 The beam-energy route',
               kind='mca', beam='12'),
         ),
         repo_ok=False),

    # ------------------------------------------------------------ fluorescence
    Tool('mca_fit_gauntlet', 'MCA line-fit gauntlet (synthetic, judged)', 'fluo', 'data',
         'tests/tools/mca_fit_gauntlet.py',
         'Fitted fluorescence lines against the window sum on synthetic MCA spectra with the beam\'s Rayleigh and '
         'Compton scatter, Si escape peaks, tails and shelves under them (F90; the hard case Zn Kα under 10 keV), '
         'judged by hand-off 08\'s pull rule and a 1 % bias rule.',
         committed=('docs/comparisons_data/mca_fit_gauntlet',),
         docs=('docs/FEATURE_REQUESTS.md#| F90 |', 'docs/reports/mca_fit_demo.md', 'docs/comparisons_data/mca_fit_gauntlet/summary.md',
               'docs/COMPARISONS.md#| C42 |', 'docs/SYNTHETIC_DATA.md#**MCA spectra with', 'docs/physics_notes.md#2026-11-23 — F90,'),
         defaults={'--out': OUT, '--design': 'core', '--replicates': '50'},
         variations=(
             V('Full gauntlet (as committed)', 'Core, grid, random and series designs with the key estimators: the '
               'run behind C42 (about 10 min on 4 CPUs).', 'docs/COMPARISONS.md#| C42 |', design='all',
               replicates='200'),
             V('Every estimator', 'The core conditions with the other backgrounds (linear, cubic) and a spectrum '
               'fitted alone with its own error.', 'tests/tools/mca_fit_gauntlet.py', methods='all'),
             V('Grid: the box', 'The fit range from ±1.5 to ±4 FWHM and short on the Compton side: the valence '
               'Compton tail curves across a wide box and a quadratic cannot follow it.', 'docs/physics_notes.md#| ±3 FWHM',
               design='grid', conditions='box_1.5,box_3,box_4,box_3_1.5'),
             V('Grid: the O 1s Compton wing', 'The core electrons\' Compton wing at 2 to 20 % of the Compton photons: '
               'what breaks the fit first.', 'docs/physics_notes.md#| O 1s Compton wing at 2 %', design='grid',
               conditions='compton_core_0.02,compton_core_0.05,compton_core_0.1,compton_core_0.2'),
             V('Grid: Si escapes and stripping', 'Escape peaks at 0.3 to 5 × Reed\'s fraction, and stripping with '
               'the fraction half or twice the true one.', 'docs/physics_notes.md#(3) **Si escape', design='grid',
               conditions='escape_x0.3,escape_x1,escape_x5,escape_assumed_x0.5,escape_assumed_x2'),
             V('Grid: counts and line/elastic', 'From 1e-2 to 1e-4 of the elastic and from 0.03 to 10 times the '
               'counts.', 'docs/physics_notes.md#| Neyman bias, 270', design='grid',
               conditions='ratio_0.01,ratio_0.003,ratio_0.0003,ratio_0.0001,counts_x0.1,counts_x10'),
             V('XFNTR series', 'Whole XFNTR curves, smooth and hard: does each estimator keep the curve\'s shape '
               'where the elastic grows above Qc?', 'docs/physics_notes.md#distorts XFNTR curves:', design='series'),
             V('Study B run (shells Compton, P1-P3)', 'The study\'s run: water\'s Compton shell by shell, the '
               'reader\'s options P1, P2, P3, the robustness sweep and the counts design (about 25 min; its products '
               'are docs/studies/mca_fit/gauntlet).', 'docs/studies/2026-11-24_two_decisions_plan.md#Study B: MCA line',
               design='all,robust,counts', methods='study', compton='shells', replicates='200'),
             V('Robustness sweep only', 'Escape fraction x O 1s wing, Doppler width and counts from the hard case.',
               'docs/studies/2026-11-24_two_decisions_plan.md#Then the robustness sweep over',
               design='robust', methods='study', compton='shells', replicates='100'),
         ),
         committed_with={'--design': 'all', '--replicates': '200'},
         repo_out='docs/comparisons_data/mca_fit_gauntlet', repo_ok=False, seconds=None),

    Tool('mca_fit_demo', 'MCA fit demo: the beam-energy story (F90)', 'fluo', 'figures',
         'tests/tools/mca_fit_demo.py',
         'The same Zn spectrum under 10, 11 and 12 keV beams: its parts stacked, the box, one drawn spectrum with '
         'P1\'s fit, and P1\'s bias over 200 series on each panel (the window sum\'s beside it). The wrap-up of '
         'the synthetic MCA project (paused 2026-11-24).',
         committed=('docs/figures/mca_fit_demo',),
         docs=('docs/reports/mca_fit_demo.md', 'docs/studies/mca_fit/summary.md', 'docs/COMPARISONS.md#| C47 |'),
         defaults={'--out': OUT},
         variations=(
             V('Beams 10, 12 and 14 keV', 'The scatter moves up with the beam and Zn Kα stays put: from failing at '
               '10 keV to within 1 % at 12 keV and above.', 'docs/reports/mca_fit_demo.md#4.4 The beam-energy route', beams='10,12,14'),
             V('Half of water\'s O 1s wing', 'A smaller wing than the shell model\'s: still out of reach at 10 keV, '
               'the same at 12 keV.', 'docs/reports/mca_fit_demo.md#4.3 Why Zn at 10 keV is out of reach', wing='0.5'),
             V('No O 1s wing', 'The wing taken away: what is left at 10 keV is the escape peak and the shelves.',
               'docs/reports/mca_fit_demo.md#4.3 Why Zn at 10 keV is out of reach', wing='0'),
             V('Escapes three times Reed\'s', 'At 11 keV the Compton escape sits on the box\'s edge and P1 reads '
               'low; at 12 keV it has moved away.', 'docs/reports/mca_fit_demo.md#**Si escape peaks.**', escape='3'),
             V('No escape peaks', 'The Si escapes taken away (a detector with none).', 'docs/reports/mca_fit_demo.md#**Si escape peaks.**',
               escape='0'),
             V('Ten times the line (1e4 photons)', 'The scatter matters less: no failures at 10 keV, but the wing '
               'still pulls P1 6 % high.', 'docs/reports/mca_fit_demo.md#- `--photons 1e4`: ten times the line', photons='1e4'),
             V('A weak line (300 photons)', 'Fewer counts: the errors grow, and P1 stays unbiased where it does not '
               'fail.', 'docs/reports/mca_fit_demo.md#4.1 P1 against data weights', photons='300'),
             V('Fe instead of Zn', 'Fe Kα (6.40 keV) far from the scatter: P1 within 1 % at 10 keV already.',
               'docs/reports/mca_fit_demo.md#- `--element Fe`: Fe Kα', element='Fe'),
             V('12 keV with 40 % fewer line photons', 'The K excitation falls from 10 to 12 keV: P1 is still '
               'unbiased with 600 photons.', 'docs/reports/mca_fit_demo.md#**What this assumes.**', beams='12', photons='600'),
         ),
         repo_out='docs/figures/mca_fit_demo', seconds=17.0),

    Tool('mca_study', 'Study B figures: MCA line intensities (F90)', 'fluo', 'figures',
         'tests/tools/mca_study.py',
         'The owner\'s study of how to measure an MCA line (F90): the anatomy of the hard case, replicates with '
         'every estimator\'s fit, the weighting bias against counts, one feature at a time, XFNTR curves, pass '
         'rates and the robustness map (B1-B7), from the gauntlet\'s study run.',
         committed=('docs/studies/mca_fit',),
         docs=('docs/reports/mca_fit_demo.md', 'docs/studies/2026-11-24_two_decisions_plan.md#Study B: MCA line',
               'docs/studies/mca_fit/summary.md', 'docs/COMPARISONS.md#| C47 |'),
         defaults={'--gauntlet': 'docs/studies/mca_fit/gauntlet', '--out': OUT},
         variations=(V('Replicates and anatomy only', 'B1 and B2, which need no gauntlet run (about 20 s).',
                       'docs/studies/2026-11-24_two_decisions_plan.md#B2. Replicates and their fits', only='B1,B2'),),
         inputs=('docs/studies/mca_fit/gauntlet',),
         repo_out='docs/studies/mca_fit', repo_ok=False),

    Tool('mca_scatter', 'Scatter in real MCA spectra against the generator (F90)', 'fluo', 'figures',
         'tests/tools/mca_scatter.py',
         "Real spectra of the scattered beam at 6-10 keV fitted with the synthetic generator's own physics, every "
         "uncertain axis free: the Si escape fraction against Reed's, the O 1s Compton wing, the detector tails, the "
         "resolution and the counts under a line against study B's hard case (DATA_NEEDS row 3); and P1 against data "
         "weights on real series of repeated spectra. From the anonymised tables only.",
         committed=('docs/studies/mca_scatter',),
         docs=('docs/studies/mca_scatter/summary.md', 'docs/DATA_NEEDS.md#MCA fit gauntlet spectra',
               'docs/studies/mca_fit/summary.md'),
         data='public', defaults={'--out': OUT},
         variations=(V('Numbers against beam energy only', 'S2 from the anonymised table (a few seconds).',
                       'docs/studies/mca_scatter/summary.md#| `S2_vs_energy.png` |', only='S2'),
                     V('Example fits on the committed blanks', 'S1: the 13 real scatter-only blanks the owner '
                       'allowed, refitted with their parts and residuals (about a minute).',
                       'docs/studies/mca_scatter/summary.md#Committed blanks (`tests/reference/mca_scatter/`)', only='S1',
                       fixtures='tests/reference/mca_scatter')),
         inputs=('docs/studies/mca_scatter/scatter_fits.csv', 'docs/studies/mca_scatter/quantities.csv'),
         repo_out='docs/studies/mca_scatter', seconds=8.0),

    # ------------------------------------------------------------ the reader's window
    Tool('gui_screens', 'Screenshots of every area of the window', 'gui', 'figures',
         'tests/tools/gui_screens.py',
         'Screenshots of every tab, area and dialog of the reader on the NX school data and synthetic MCA and '
         'burn data, with an index.',
         committed=('docs/gui/screens',), docs=('docs/gui/screens/README.md', 'docs/gui/README.md'),
         data='public', defaults={'--out': OUT},
         variations=(V('Quick (skip the slow areas)', 'Leaves out Ref Patch, GID patch, cuts and burn on the real '
                       'data.', 'tests/tools/gui_screens.py', skip_slow=True),),
         inputs=UI + ('docs/gui/screens/README.md',), seconds=None),
    Tool('plot_speed_mca', 'Plot speed: MCA spectra', 'gui', 'text',
         'tests/tools/plot_speed.py',
         'How long the real window takes to plot N MCA spectra (linear and log y, and switching log y on) on '
         'synthetic data: where plotting time goes.',
         docs=('docs/COMPARISONS.md',), data='synthetic', subcommand='mca',
         variations=(V('Many spectra (200, 4096 channels)', 'A long fluorescence series with a fine MCA: the '
                       'log-scale cost grows with the points drawn.', 'tests/tools/plot_speed.py',
                       spectra='200', channels='4096'),),
         inputs=UI),
    Tool('plot_speed_images', 'Plot speed: Pilatus frames', 'gui', 'text',
         'tests/tools/plot_speed.py',
         'How long the real window takes to show N Pilatus frames at once, linear or log scale, on synthetic '
         'frames.', docs=('docs/COMPARISONS.md',), data='synthetic', subcommand='images',
         variations=(V('Log scale', 'The same frames on a log colour scale.', 'tests/tools/plot_speed.py',
                       log=True),),
         inputs=UI),
    Tool('dump_tooltips', 'Every control and its tooltip (manual)', 'gui', 'text',
         'tests/tools/dump_tooltips.py',
         'Every control of the window and its dialogs with its tooltip, as Markdown: the raw material for the '
         'manual (the "why" lives in tooltips).',
         committed=('docs/manual/controls.md',), docs=('docs/MANUAL_NOTES.md',), data='synthetic',
         repo_stdout='docs/manual/controls.md', inputs=UI, seconds=3.7),
    Tool('gui_map', 'Check the workflow map against the window', 'gui', 'check',
         'tests/tools/gui_map.py',
         'The GUI workflow map and control inventory checked against each other and against a live window; '
         'rendered as workflows.md and inventory.md.',
         committed=('docs/gui/workflows.md', 'docs/gui/inventory.md'), docs=('docs/gui/README.md',),
         data='synthetic', defaults={'--check': True},
         scratch_args={'--no-render': True},
         variations=(V('Against a live window', 'Also resolve every inventory id in an offscreen window and find '
                       'named controls the inventory lacks.', 'docs/gui/README.md', window=True),),
         inputs=UI + ('docs/gui/workflows.yaml', 'docs/gui/inventory'), seconds=0.4),

    Tool('ngui_screens', 'Screenshots of the new-layout prototype', 'gui', 'figures',
         'tests/tools/ngui_screens.py',
         'The prototype of the new layout (ngui, F82) on each tab, its panes and sketch dialogs, at 1440 x 900, '
         'with an index; placeholders only, no data.',
         committed=('docs/gui/prototype/screens',), docs=('docs/gui/prototype.md',), data='synthetic',
         defaults={'--out': OUT}, inputs=('docs/gui/inventory',)),
    Tool('timeline_mock', 'Sample timeline: the mock tab', 'gui', 'figures',
         'tests/tools/timeline_mock.py',
         'A low-fidelity picture of the proposed sample timeline tab drawn from one SPEC file, with the '
         'reflectivity series re-reduced for its thumbnails (F83).',
         committed=('docs/gui/timeline/mock_nx.png',), docs=('docs/gui/timeline/research.md',), data='public',
         subcommand='mock', defaults={'--out': OUT + '/mock_nx.png'},
         variations=(V('Placeholders for the thumbnails', 'Draws the mock without re-reducing the series (fast).',
                       'tests/tools/timeline_mock.py', no_reduce=True),),
         inputs=(NX,)),
    Tool('ngui_inventory', 'Check the prototype\'s inventory text', 'gui', 'check',
         'tests/tools/ngui_inventory.py',
         'The prototype window\'s tooltips are copied from the control inventory into ngui/inventory_text.py; '
         'this checks the copy is current (or rewrites it).',
         committed=('ngui/inventory_text.py',), docs=('docs/gui/prototype.md',), data='synthetic',
         free='--check', free_help='--check: exit 1 if out of date; empty: rewrite ngui/inventory_text.py',
         inputs=('docs/gui/inventory',) + UI, repo_ok=False),

    # ------------------------------------------------------------ made elsewhere
    Tool('absorber_answer_figures', 'Absorber steps and foils (hand-off 03 answer)', 'external', 'external',
         demonstrates='Figures of the owner\'s analysing repository (tools/absorber_steps.py, absorber_review.py, '
                      'absorber_trust.py) from private data: measured steps, foil fits, the review of '
                      'anomalous joins. Not regenerable here; the numbers behind them are in figdata/ and joins.csv.',
         committed=('docs/handoff_out/03-answer/figures',),
         docs=('docs/handoff_out/03-answer/README.md', 'docs/handoff_out/03-answer/HANDOFF.md',
               'docs/handoff_out/03-answer/ABSORBER_RATIOS.md'),
         data='private', repo_ok=False),
    Tool('sh_beam_size', 'sh-scan beam size (private data)', 'external', 'external',
         demonstrates='The beam\'s vertical profile at the sample from the rising edge of every height scan and the '
                      'direct beam in their Pilatus images (DATA_NEEDS row 9, OQ-2): sigma against the S1 gap, the '
                      'core + tail profile, the factor to the dose height, a liquid half-cut; single height scans with their fits, '
                      'the guards, rise against fall and what the meniscus does. Made by the non-cloud '
                      'agent\'s private generator (sample_data/private/sh_beam/); not regenerable here; the numbers '
                      'behind the figures are the CSVs beside them.',
         committed=('docs/studies/sh_beam_size',), docs=('docs/studies/sh_beam_size/summary.md', 'docs/studies/sh_beam_size/height_scans.md'),
         data='private', repo_ok=False),
    Tool('gid_stray_light_private', 'GID stray light over many sets (private data)', 'external', 'external',
         demonstrates='P40 on every private GID set (DATA_NEEDS row 10): light past S5 and beyond the footprint at '
                      'both arm heights, per beamtime, and the beam-path background from frames with the sample '
                      'lowered. Made by the non-cloud agent\'s private generator (sample_data/private/gid/); not '
                      'regenerable here; the numbers behind the figures are the CSVs beside them.',
         committed=('docs/studies/gid_stray_light',), docs=('docs/studies/gid_stray_light/summary.md',),
         data='private', repo_ok=False),
    Tool('gid_method_survey_private', 'GID defaults judged on many sets (private data)', 'external', 'external',
         demonstrates='Hand-off 06 on every private GID set (DATA_NEEDS row 12): the S4-detector distance '
                      'calibration per beamtime, the column responses ranked by frames agree, the joins as '
                      'collected and fitted, the split test and the single frames as ground truth. Made by '
                      'tests/tools/gid_method_survey.py on the private sets and the non-cloud agent\'s private '
                      'aggregation (sample_data/private/gid/); not regenerable here; the numbers are the CSVs beside them.',
         committed=('docs/studies/gid_method_survey',), docs=('docs/studies/gid_method_survey/summary.md',
                                                              'docs/handoff_out/06-gid-method-comparison.md'),
         data='private', repo_ok=False),
    Tool('xr_burns', 'Real reflectivity burns: trends, dose or time (private data)', 'external', 'external',
         demonstrates="The reader's burn test on 78 real reflectivity burns (DATA_NEEDS row 11, F76, F77): the drift "
                      'rate against flux and the dose-or-time verdicts per series. Made by the non-cloud '
                      "agent's private generator (sample_data/private/xr/); not regenerable here; the numbers "
                      'are the CSVs beside them. The frame-by-frame curves (B1) are private (owner, 2026-11-25).',
         committed=('docs/studies/xr_burns',), docs=('docs/studies/xr_burns/summary.md',),
         data='private', repo_ok=False),
    Tool('qz_resolution', 'Qz resolution near the critical edge (private data)', 'external', 'external',
         demonstrates="The width of the critical edge in 378 real reflectivity scans at 10 keV (DATA_NEEDS row 13, "
                      "F79): the resolution per run and S1 gap, the fit's sensitivity, a known-truth check and the "
                      "coverage of the fits' errors. Made by the non-cloud agent's private generator "
                      "(sample_data/private/xr/); not regenerable here; the numbers are the CSVs beside them.",
         committed=('docs/studies/qz_resolution',), docs=('docs/studies/qz_resolution/summary.md',),
         data='private', repo_ok=False),
    Tool('ref_patch_real', 'Reflectivity patching on real series (private data)', 'external', 'external',
         demonstrates="Hand-off 08's survey on 1832 real joins (DATA_NEEDS row 1): split-truth bias and pull SD per "
                      "method and Qz class with bootstrap intervals, the guard at p 0.7, 0.3 and off. Made by the "
                      "non-cloud agent from tests/tools/ref_patch_survey.py on private files; not regenerable here; "
                      "the numbers are the CSVs beside the figure.",
         committed=('docs/studies/ref_patch_real',), docs=('docs/studies/ref_patch_real/summary.md',),
         data='private', repo_ok=False),
)

BY_ID = {t.id: t for t in TOOLS}


def get(item_id):
    return BY_ID[item_id]


def in_category(cat):
    return [t for t in TOOLS if t.category == cat]


def scripts():
    """Repository paths of every script the catalogue runs."""
    return sorted({t.script for t in TOOLS if t.script})
