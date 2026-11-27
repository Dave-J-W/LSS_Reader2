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
         repo_out='docs/studies/reciprocity', repo_ok=False, seconds=85.0),

    Tool('qoff_walkthrough', 'Walkthrough: the Qz offset from the raw frames to the judgment (F79, ELI5)', 'refl',
         'figures', 'tests/tools/qoff_walkthrough.py',
         'The whole chain on NX school scans 6-9, for the owner\'s standing order (2026-11-25): a raw frame and its '
         'counted box, R and R/R_F at the edge at Qoff 0 and at the proposal, the edge fit drawn over its data '
         'with its residuals (chi2/dof 75: the rounded edge), the bootstrap, and what the beamline\'s resolution '
         'reads as: figures QW1-QW5.',
         committed=('docs/studies/qoff/walkthrough',),
         docs=('docs/studies/qoff/walkthrough.md', 'docs/studies/qoff/summary.md'),
         data='public', defaults={'--out': OUT},
         repo_out='docs/studies/qoff/walkthrough', repo_ok=False, seconds=60.0),

    Tool('reciprocity_walkthrough', 'Walkthrough: from the frames to the dose-or-time verdict (F76, ELI5)', 'burn',
         'figures', 'tests/tools/reciprocity_walkthrough.py',
         'The whole chain on public data, for the owner\'s standing order (2026-11-25): an NX school frame and its '
         'line cut, one position per frame, the straight-line drift with its residuals, the rates against flux '
         'with chi2(beta), C54\'s strip scatter by REML, one real series under three error models, and the '
         'calibration of the intervals: figures W1-W6.',
         committed=('docs/studies/reciprocity/walkthrough',),
         docs=('docs/studies/reciprocity/walkthrough.md', 'docs/studies/reciprocity/summary.md'),
         data='public', defaults={'--out': OUT},
         inputs=('docs/studies/xr_burns/burns.csv',),
         repo_out='docs/studies/reciprocity/walkthrough', repo_ok=False, seconds=60.0),

    Tool('reciprocity_real', 'Dose or time on C54\'s 19 real burn series, and the strip scatter (F76)', 'burn',
         'figures', 'tests/tools/reciprocity_real.py',
         'lss_core.reciprocity on the public, anonymised rates of the real reflectivity burns (C54): the strip '
         'scatter from the six repeated absorbers (additive and relative, REML), each series\' verdict and beta '
         'under counting errors, tau and rho beside C54\'s, and how many strips per flux would decide at that rho: '
         'figure R6.',
         committed=('docs/studies/reciprocity/c54',),
         docs=('docs/studies/reciprocity/summary.md## 6. C54\'s 19 real series (2026-11-25)',
               'docs/studies/xr_burns/summary.md', 'docs/COMPARISONS.md#| C58 |'),
         data='public', defaults={'--out': OUT},
         inputs=('docs/studies/xr_burns/burns.csv', 'docs/studies/xr_burns/series_dose_or_time.csv'),
         variations=(
             V('Without the design (seconds)', 'Only the strip scatter, the verdicts and R6; no strips-per-flux '
               'simulation.', 'docs/studies/reciprocity/summary.md## 6. C54\'s 19 real series (2026-11-25)',
               design_replicates='0'),
             V('Strips per flux, 1000 replicates', 'The design at the fitted rho with 1000 replicates per cell (about '
               '7 min).', 'docs/studies/reciprocity/summary.md#12–16 strips per flux', design_replicates='1000'),
             V('Another additive strip scatter', 'C54\'s tau replaced (here 150 %/h) beside the one fitted.',
               'docs/studies/xr_burns/summary.md#88 %/h (64–122)', tau_c54='150'),
         ),
         repo_out='docs/studies/reciprocity/c54', repo_ok=False, seconds=90.0),

    Tool('burn_shoulder_study', 'A peak on a shoulder: which burn estimator reads the truth? (P44)', 'burn',
         'figures', 'tests/tools/burn_shoulder_study.py',
         'Synthetic GID burns with a known truth (fade, broadening, shift, a growing or fading shoulder, an NX '
         '15-like broadening fade) on four shoulder shapes and at fewer counts: the bias, pulls, coverage and '
         'verdicts of the template, the legacy moments and the two split estimators (the shoulder held '
         'unstretched), and NX school burns 14 and 15 under every estimator: figures S1-S5.',
         committed=('docs/studies/burn_shoulder',),
         docs=('docs/studies/burn_shoulder/summary.md', 'docs/PHYSICS_ISSUES.md#| P44 |'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('NX only', 'S5 alone, no replicates (about a minute): burns 14 and 15 under every estimator.',
               'docs/studies/burn_shoulder/summary.md## 5. NX school burns 14 and 15 (S5)', only='S5'),
             V('A quick look (30 replicates)', 'Every case and shape with 30 replicates (about 8 min): the biases '
               'hold, the coverages are rough.', 'docs/studies/burn_shoulder/summary.md## How to regenerate',
               replicates='30'),
             V('Fewer counts only', 'Part B: the Gaussian shoulder at 10 and 100 times fewer counts.',
               'docs/studies/burn_shoulder/summary.md## 4. Fewer counts (S4)', parts='B'),
             V('Shoulders that are not Gaussian', 'Part A on the Lorentzian, lopsided and two-component shoulders.',
               'docs/studies/burn_shoulder/summary.md## 2. Other shoulder shapes (S2)', parts='A',
               shapes='lorentzian,asymmetric,two'),
             V('The reference\'s noise (part R)', 'Each frame measured against the frames\' mean (the reader), '
               'the mean smoothed and the noiseless mean, at high counts and at NX 14\'s and 15\'s counts: S6, '
               'about 10 min.', 'docs/studies/burn_shoulder/summary.md## 6. The reference\'s noise (S6)', only='R'),
             V('Real GID burns (R1-R7)', 'The private GID burns\' published summaries (docs/studies/xr_burns/'
               'gid_split*.csv): the split against the template, the shift a smoothed mean frame gives against '
               'the mean frame\'s noise, and how each of section 8\'s numbers is made (the selection, the '
               'disagreement statistic, the shoulder\'s three signs, χ²/dof, the dose-or-time fit). Seconds; no '
               'private data needed.',
               'docs/studies/burn_shoulder/summary.md## 8. Real GID burns (non-cloud agent)', only='G'),
         ),
         repo_out='docs/studies/burn_shoulder', repo_ok=False, seconds=5400.0),

    Tool('burn_shoulder_walkthrough', 'Walkthrough: a GID burn from the frames to the verdict, split or not (P44, '
         'ELI5)', 'burn', 'figures', 'tests/tools/burn_shoulder_walkthrough.py',
         'The whole chain on NX school burn 15, for the owner\'s standing order (2026-11-25): a raw frame and its '
         'line cut, the mean frame split into a shoulder and a peak, one frame fitted by the template and by the '
         'split with residuals, the per-frame intensity and width with their lines, the verdicts by AICc, and the '
         'calibration of the intervals on 60 synthetic burns: figures BW1-BW6.',
         committed=('docs/studies/burn_shoulder/walkthrough',),
         docs=('docs/studies/burn_shoulder/walkthrough.md', 'docs/studies/burn_shoulder/summary.md'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('More calibration burns (300)', 'BW6 with 300 synthetic burns: the coverage to about ±1 %.',
               'docs/studies/burn_shoulder/walkthrough.md## Step 6. Calibration: do the intervals hold the truth? '
               '(figure BW6)', replicates='300'),
         ),
         repo_out='docs/studies/burn_shoulder/walkthrough', repo_ok=False, seconds=60.0),

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
    Tool('qoff_resolution_study', 'Qoff and the Qz resolution fitted together at the edge (hand-off 09)', 'refl',
         'figures', 'tests/tools/qoff_resolution_study.py',
         'Synthetic edges with a known angle offset and resolution, read by the joint fit (R_F with absorption '
         'smeared by a Gaussian, Qoff and σ_Q free), the same with water\'s roughness, and today\'s sharp proposer: '
         'the offset, the resolution, the sampling, a wrong β, counts, an outlier, fringes, DPPC; the NX school '
         'edge and its χ² at a fixed σ_Q: figures K1-K4.',
         committed=('docs/studies/qoff_resolution',),
         docs=('docs/studies/qoff_resolution/summary.md', 'docs/COMPARISONS.md#| C71 |', 'docs/studies/qz_resolution/summary.md'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('NX only', 'K4: NX school scan 6 under both fits, and the fit at a fixed σ_Q (about a minute).',
               'docs/studies/qoff_resolution/summary.md## 4. NX school scan 6 (K4)', only='nx'),
             V('A quick look (20 replicates)', 'Every condition with 20 replicates (about 3 min): the biases hold, the '
               'coverages are rough.', 'docs/studies/qoff_resolution/summary.md## How to regenerate', replicates='20'),
             V('Known truth at the owner\'s sampling', 'One point of the known truth (hand-off 09, item 4): steps of '
               '0.001 from 0.015, the beamline\'s σ_Q, 50 replicates; truth.csv and a printed summary.',
               'docs/studies/qoff_resolution/summary.md## For the local data agent', truth=True, qoff='-2e-4', sigma_q='3.8e-4', counts='1',
               step='0.001', start='0.015'),
             V('Known truth at NX\'s sampling', 'The same at NX school scan 6\'s sampling (0.00125 from 0.0175).',
               'docs/studies/qoff_resolution/summary.md## For the local data agent', truth=True, step='0.00125', start='0.0175'),
             V('A wrong β', 'The fit given twice and half the subphase\'s absorption: σ_Q moves, Qoff barely.',
               'docs/studies/qoff_resolution/summary.md## 3. What moves it', designs='beta'),
         ),
         repo_out='docs/studies/qoff_resolution', repo_ok=False, seconds=1800.0),
    Tool('qoff_resolution_survey', 'Qoff and the Qz resolution on real edge scans (survey)', 'refl', 'data',
         'tests/tools/qoff_resolution_survey.py',
         'Every reflectivity scan of a SPEC file that crosses the edge, reduced alone and fitted for Qoff and σ_Q '
         'together (with today\'s sharp proposal beside it): one CSV row per scan, for the local data agent\'s '
         'private edges (hand-off 09).',
         docs=('docs/studies/qoff_resolution/summary.md', 'docs/studies/qz_resolution/summary.md'),
         data='any', defaults={'--spec': NX, '--out': OUT}, spec_option='--spec',
         variations=(
             V('Water\'s roughness in R_F', 'A fixed 3 Å Névot–Croce roughness in the model: what it changes on real '
               'edges.', 'docs/studies/qoff_resolution/summary.md## For the local data agent', roughness='3'),
             V('β × 2', 'Twice the subphase\'s absorption, DATA_NEEDS row 13\'s check (σ_Q −15 % there).',
               'docs/studies/qoff_resolution/summary.md## For the local data agent', beta_scale='2'),
         ),
         seconds=1.0),

    Tool('excess_remedy_study', 'The join\'s error budget with the measured excess: scale, X, robust weights, '
         'clipping (C64)', 'refl', 'figures', 'tests/tools/excess_remedy_study.py',
         'C61\'s six synthetic joins under truths built from C63 (its between-scan numbers on every point, the '
         'first and mistaken reading; the within-scan excess; the within-scan excess plus the between-scan part on '
         'the later scan\'s overlap points; none), fitted by today\'s joint fit with the stated sigma, sigma x 1.12, '
         'with or without 4-sigma clipping, the budget with X by Qz or by counts, Student-t or Cauchy '
         're-weighting, or an oracle; the NX school split. Figures E1-E4: the pulls, the catastrophic misses, one '
         'join rescued and one ruined by clipping.',
         committed=('docs/studies/excess_remedy',),
         docs=('docs/studies/excess_remedy/walkthrough.md', 'docs/studies/excess_remedy/summary.md',
               'docs/COMPARISONS.md#| C64 |'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('Quick look', 'Every figure from 40 replicates per join (about 5 s): the pattern, not the decimals.',
               'docs/studies/excess_remedy/walkthrough.md#400 replicates each', reps='40'),
             V('Synthetic only', 'Without the NX school split.',
               'docs/studies/excess_remedy/walkthrough.md#The NX split', no_nx=True),
         ),
         repo_out='docs/studies/excess_remedy', repo_ok=False, seconds=95.0),

    Tool('roi_bad_pixel_study', 'A bad-pixel pass on the reflectivity ROI: hot pixels, sparse frames, the factor '
         '(F95 B3, C62)', 'refl', 'figures', 'tests/tools/roi_bad_pixel_study.py',
         'Synthetic frames with known truth (bright, sharp and sparse beams; 0-0.5 hot pixels per frame) reduced by '
         'the reader\'s frame_row after no pass, the whole-frame pass at factor 4, the ROI pass at factors 3, 10 and '
         '40, or the background boxes only; the NX school frames. Figures R1-R5: one sparse frame, the extra scatter '
         'per point, the threshold, the join pulls, and how close clean frames come to a correction.',
         committed=('docs/studies/roi_bad_pixels',),
         docs=('docs/studies/roi_bad_pixels/walkthrough.md', 'docs/studies/roi_bad_pixels/summary.md',
               'docs/COMPARISONS.md#| C62 |'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('Quick look', 'Every figure from 5 replicates (about 20 s): the pattern, not the decimals.',
               'docs/studies/roi_bad_pixels/walkthrough.md#30 replicates', reps='5'),
             V('Synthetic only', 'Without the NX school frames.',
               'docs/studies/roi_bad_pixels/walkthrough.md#NX school (real, public)', no_nx=True),
         ),
         repo_out='docs/studies/roi_bad_pixels', repo_ok=False, seconds=110.0),

    Tool('guard_error_walkthrough', 'Walkthrough: why join error bars are too small, from two scans to the verdict '
         '(C61, ELI5)', 'refl', 'figures', 'tests/tools/guard_error_walkthrough.py',
         'The whole chain of the guard\'s-error study, for the owner\'s standing order (2026-11-25): two scans and the '
         'factor read off their shared points, with and without 2 % hidden scatter; the joint fit drawn over its data '
         'with its residuals; the guard\'s ladder of p-values; the pulls and coverage over 400 replicates, today\'s '
         'rule against honest per-point errors; a fringed join, where inflating by the order-4 chi2 fails; and a '
         'real NX school scan split with a known factor: figures W1-W6.',
         committed=('docs/studies/guard_error/walkthrough',),
         docs=('docs/studies/guard_error/walkthrough.md', 'docs/studies/guard_error/summary.md'),
         data='public', defaults={'--out': OUT},
         variations=(
             V('Quick look', 'The pulls of W4 from 40 replicates (about 2 s): the pattern, not the decimals.',
               'docs/studies/guard_error/walkthrough.md#Over 400 replicates of this join', reps='40'),
         ),
         repo_out='docs/studies/guard_error/walkthrough', repo_ok=False, seconds=6.0),
    Tool('excess_scatter', 'Scatter beyond counting statistics: the estimators on known truth (DATA_NEEDS row 15)',
         'refl', 'figures', 'tests/tools/excess_scatter.py',
         'Synthetic reflectivity series (water, DPPC, a 100 Å film) with a known per-point excess X, a slow drift '
         'or outliers (0.3 % and 3 % of points): the 6-point within-scan difference (core plus outliers, one '
         'Gaussian, median) against the truth (figure X1); a stated σ too small by a known s, and the scale model '
         'that finds it (figure X2); then the pull SD of today\'s joint fit on C61\'s joins with the within-scan '
         'excess measured on real data (pulls.csv).',
         committed=('docs/studies/excess_scatter/X1_known_truth.png', 'docs/studies/excess_scatter/known_truth.csv',
                    'docs/studies/excess_scatter/X2_scale_known_truth.png',
                    'docs/studies/excess_scatter/known_truth_scale.csv',
                    'docs/studies/excess_scatter/pulls.csv', 'docs/studies/excess_scatter/numbers.json'),
         docs=('docs/studies/excess_scatter/summary.md', 'docs/COMPARISONS.md#| C63 |'),
         defaults={'--out': OUT, '--trials': '40', '--pulls': '400'},
         variations=(
             V('Quick look', '5 estimates per cell and no pull check: the pattern of X1 and X2 in a few minutes.',
               'docs/studies/excess_scatter/summary.md## The known-truth check', trials='5', pulls='0'),
         ),
         repo_out='docs/studies/excess_scatter', seconds=900),
    Tool('excess_scatter_walkthrough', 'Walkthrough: scatter beyond counting, from one scan to the verdict '
         '(DATA_NEEDS row 15, ELI5)', 'refl', 'figures', 'tests/tools/excess_scatter_walkthrough.py',
         'The whole chain of the excess-scatter study (rule 13): one NX school scan with its counting errors; the '
         '6-point difference within the scan; the likelihood and the core + outlier model on known truth; the '
         'real within-scan results by what they might follow, from the committed derived tables: figures W1-W4.',
         committed=('docs/studies/excess_scatter/walkthrough',),
         docs=('docs/studies/excess_scatter/walkthrough.md', 'docs/studies/excess_scatter/summary.md'),
         data='public', defaults={'--out': OUT},
         repo_out='docs/studies/excess_scatter/walkthrough', repo_ok=False, seconds=40.0),
    Tool('excess_scatter_released', 'Real examples: frames, series and windows from released runs (C63, before 2019)',
         'refl', 'figures', 'tests/tools/excess_scatter_released.py',
         'The excess-scatter study on real data anyone can rerun: two reflectivity frames with the reader\'s boxes '
         '(R1), four cherry-picked series and their window pulls (R2), single windows, their weights, where the big ones sit and why six points (R3), and every '
         'window of 96 released series pooled against the 18 private runs (R4). From the committed extract in '
         'docs/studies/excess_scatter/released/ (runs before 2019, released by the owner for figures, anonymous).',
         committed=('docs/studies/excess_scatter/released/R1_frames.png',
                    'docs/studies/excess_scatter/released/R2_series.png',
                    'docs/studies/excess_scatter/released/R3_windows.png',
                    'docs/studies/excess_scatter/released/R4_pool.png',
                    'docs/studies/excess_scatter/released/numbers.json'),
         docs=('docs/studies/excess_scatter/walkthrough.md', 'docs/studies/excess_scatter/summary.md'),
         data='public', defaults={'--out': OUT, '--boot': '40'},
         repo_out='docs/studies/excess_scatter/released', seconds=10.0),

    Tool('guard_error_study', 'The guard\'s error: why join error bars are too small on real data', 'refl', 'figures',
         'tests/tools/guard_error_study.py',
         'Study A\'s six joins with hidden per-point scatter (0-3 %): today\'s error rule against inflating by the '
         'unguarded fit\'s chi2, the larger inflation, the larger error, the guard off, and an oracle per-point '
         'budget; the NX school split. Figures G1-G3: only honest per-point errors fix both smooth and fringed joins.',
         committed=('docs/studies/guard_error',),
         docs=('docs/studies/guard_error/summary.md', 'docs/studies/ref_patch_real/summary.md',
               'docs/COMPARISONS.md#| C61 |'),
         data='public', defaults={'--out': 'docs/studies/guard_error'},
         variations=(
             V('Quick look', 'Every figure from 40 replicates per case (about 5 s): the pattern, not the decimals.',
               'docs/studies/guard_error/summary.md#400 replicates per join and condition', reps='40'),
             V('Synthetic only', 'Without the NX school split (3 scans long enough: too few to decide).',
               'docs/studies/guard_error/summary.md#too few to decide anything', no_nx=True),
         ),
         inputs=(NX,), repo_out='docs/studies/guard_error', seconds=35),

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
    Tool('xrf_tables', 'X-ray tables from xraylib for the synthetic spectra', 'fluo', 'data',
         'tests/tools/xrf_tables.py',
         'Line energies and relative intensities (K and L families, at each beam energy) and water\'s Hartree-Fock '
         'Compton profiles, from xraylib, written as the JSON the extended generator reads '
         '(tests/synthetic/mca_more.py); and every constant the generator took from memory against xraylib. '
         'Needs xraylib.',
         committed=('tests/synthetic/data/xrf_tables.json', 'docs/studies/xrf_shootout/physics_check.csv'),
         docs=('docs/studies/xrf_shootout/summary.md', 'docs/studies/xrf_shootout/QUESTIONS.md'),
         defaults={'--out': OUT + '/xrf_tables.json', '--check': OUT},
         repo_ok=False, seconds=None),
    Tool('xrf_shootout', 'XRF shootout: the reader against PyMca, PyXRF, Larch and XeRay', 'fluo', 'data',
         'tests/tools/xrf_shootout.py',
         'The reader\'s window sum and line fits against the open-source XRF packages on synthetic spectra with '
         'known truth: 43 conditions (scatter, counts, overlaps, other elements and L lines, calibration and '
         'detector errors, a measured detector) and 8 XFNTR curves. Needs PyMca5, scikit-beam and xraylarch (a method whose package is '
         'missing is skipped); about an hour on 30 CPUs as committed.',
         committed=('docs/studies/xrf_shootout/run', 'docs/studies/xrf_shootout/run_measured',
                    'docs/studies/xrf_shootout/run_pymca'),
         docs=('docs/studies/xrf_shootout/summary.md', 'docs/studies/xrf_shootout/survey.md', 'docs/studies/xrf_shootout/README.md',
               'docs/studies/xrf_shootout/QUESTIONS.md'),
         defaults={'--out': OUT, '--replicates': '10', '--series-replicates': '4',
                   '--methods': 'window,fit_data,p1,p1p2p3,xeray'},
         variations=(
             V('As committed', 'Every method, 100 series per condition and 40 per XFNTR curve (about an hour on 30 '
               'CPUs).', 'docs/studies/xrf_shootout/README.md#2. the shootout: 40 conditions', replicates='100',
               series_replicates='40', methods='all'),
             V('The hard case only', 'Zn under 10 keV with every method: the case that separates them.',
               'docs/studies/xrf_shootout/README.md### Commands', conditions='hard,xfntr_hard', methods='all'),
         ),
         committed_with={'--replicates': '100', '--series-replicates': '40', '--methods': 'all'},
         repo_out='docs/studies/xrf_shootout/run', repo_ok=False, seconds=None),
    Tool('xrf_blanks', 'XRF shootout on real blanks: synthetic lines in measured scatter', 'fluo', 'data',
         'tests/tools/xrf_blanks.py',
         'Synthetic fluorescence lines of known photons (Zn, Cu, Ni, Cr, Ti K and La L) injected into the 10 clean '
         'real scatter-only blanks the owner allowed (tests/reference/mca_scatter), each thinned to 1000 or 3000 '
         'background counts in the line box and given its own measured detector; every method of the shootout '
         'scored on them, and the false line each reports on the bare blank. Needs the shootout packages; about '
         '50 minutes on 22 CPUs as committed.',
         committed=('docs/studies/xrf_shootout/run_blanks', 'docs/studies/xrf_shootout/run_blanks_options',
                    'docs/studies/xrf_models/scatter/run_full', 'docs/studies/xrf_models/scatter/run_generator',
                    'docs/studies/xrf_models/scatter/run_gaussian', 'docs/studies/xrf_models/scatter/run_full_redraw',
                    'docs/studies/xrf_models/shape'),
         docs=('docs/studies/xrf_shootout/summary.md', 'docs/studies/xrf_shootout/README.md',
               'docs/studies/xrf_shootout/QUESTIONS.md', 'docs/studies/xrf_models/README.md'),
         data='public',
         defaults={'--out': OUT, '--replicates': '2', '--blanks': 'E10-k,E6.1-a',
                   '--methods': 'window,p1,p1p2p3,xeray'},
         variations=(
             V('As committed', 'Every method but Larch one spectrum at a time, the ten clean blanks, 50 series of 10 '
               'per condition (about 50 minutes on 22 CPUs).',
               'docs/studies/xrf_shootout/README.md#2d. lines injected into the real blanks', replicates='50',
               blanks='E10-k,E10-f,E9.2-a,E9.2-b,E9.2-c,E9.2-d,E6.1-a,E6.1-b,E6.1-c,E6.1-d', methods='all'),
             V('The single options', 'P1+P2 and P1+P3 on the same spectra: which of the two options helps on real '
               'scatter (about a minute).', "docs/studies/xrf_shootout/README.md#2e. the reader's single options",
               replicates='50', blanks='E10-k,E10-f,E9.2-a,E9.2-b,E9.2-c,E9.2-d,E6.1-a,E6.1-b,E6.1-c,E6.1-d',
               methods='p1p2,p1p3'),
             V('On model twins of the blanks', 'The same shootout on twins drawn from the full scatter model fitted '
               'to each blank (tests/tools/xrf_models.py scatter): does the model stand in for the real scatter? '
               'Also twins_generator and twins_gaussian (about 40 minutes on 12 CPUs each).',
               'docs/studies/xrf_models/README.md#1b. The twins in the shootout', replicates='50',
               blanks='E10-k,E10-f,E9.2-a,E9.2-b,E9.2-c,E9.2-d,E6.1-a,E6.1-b,E6.1-c,E6.1-d',
               methods='window,fit_data,p1,p1p3,p1p2p3,xeray,pymca,pyxrf',
               blank_dir='docs/studies/xrf_models/scatter/twins_full'),
             V('Real-shaped lines', "The lines injected with the shape measured on real lines (readout B: 46 % in a "
               "58 eV tail) instead of the elastic's; also --line-shape gaussian (about 40 minutes on 12 CPUs).",
               "docs/studies/xrf_models/README.md#2c. Does the line's shape change the verdicts?", replicates='50',
               blanks='E10-k,E10-f,E9.2-a,E9.2-b,E9.2-c,E9.2-d,E6.1-a,E6.1-b,E6.1-c,E6.1-d',
               methods='window,fit_data,p1,p1p3,p1p2p3,xeray,pymca,pyxrf', line_shape='line'),
         ),
         inputs=('tests/reference/mca_scatter', 'docs/studies/mca_scatter/scatter_fits.csv',
                 'docs/studies/mca_scatter/quantities.csv', 'tests/synthetic/data/xrf_tables.json'),
         committed_with={'--replicates': '50', '--blanks': 'E10-k,E10-f,E9.2-a,E9.2-b,E9.2-c,E9.2-d,E6.1-a,E6.1-b,'
                         'E6.1-c,E6.1-d', '--methods': 'all'},
         repo_out='docs/studies/xrf_shootout/run_blanks', repo_ok=False, seconds=None),
    Tool('xrf_real_series', 'XRF shootout on real lines: the private burn series', 'fluo', 'data',
         'tests/tools/xrf_real_series.py',
         'Every shootout method on the 19 private burn series (readout A, 10 keV, a line near 8 keV), each '
         'against 20 resampled twins with the series own shape and a known answer, successive-difference pulls '
         'and agreement on the sums. Needs the decrypted private bundle (docs/studies/xrf_shootout/README.md, '
         'step 2f) and the shootout packages; writes summary values only.',
         committed=('docs/studies/xrf_shootout/run_real',),
         docs=('docs/studies/xrf_shootout/summary.md', 'docs/studies/xrf_shootout/README.md',
               'docs/studies/xrf_shootout/QUESTIONS.md'),
         data='private',
         defaults={'--out': OUT, '--twins': '2', '--methods': 'window,p1,p1p2p3'},
         variations=(
             V('As committed', 'Every method, 20 twins per series (a few minutes on 19 CPUs).',
               'docs/studies/xrf_shootout/README.md#2f. real lines in real scatter', twins='20', methods='all'),
         ),
         committed_with={'--twins': '20', '--methods': 'all'},
         repo_out='docs/studies/xrf_shootout/run_real', repo_ok=False, seconds=None),
    Tool('xrf_models_scatter', 'Scatter models against the real blanks', 'fluo', 'data',
         'tests/tools/xrf_models.py',
         "Every committed blank fitted by three scatter models (the synthetic shootout's generator, a Gaussian "
         "detector, the full model with tails and shelf free): the misfit in the boxes a line is fitted in, at full "
         "counts and at the shootout's, the nuisance lines each fit puts in, and a model twin of each clean blank "
         "drawn from its scatter alone (for xrf_blanks.py --blank-dir). About 4 minutes on 13 CPUs.",
         committed=('docs/studies/xrf_models/scatter/ladder.csv', 'docs/studies/xrf_models/scatter/residuals.csv',
                    'docs/studies/xrf_models/scatter/twins_full', 'docs/studies/xrf_models/scatter/twins_generator',
                    'docs/studies/xrf_models/scatter/twins_gaussian',
                    'docs/studies/xrf_models/scatter/twins_full_redraw'),
         docs=('docs/studies/xrf_models/README.md',), data='public', subcommand='scatter',
         defaults={'--out': OUT},
         variations=(V('The floor: a second draw', "A second, independent draw of the full model's twins "
                       "(twins_full_redraw/): how far apart two draws of one truth land in the shootout.",
                       'docs/studies/xrf_models/README.md#One real blank is one Poisson draw', models='full', redraw=True),),
         inputs=('tests/reference/mca_scatter', 'docs/studies/mca_scatter/scatter_fits.csv',
                 'docs/studies/mca_scatter/quantities.csv'),
         repo_out='docs/studies/xrf_models/scatter', repo_ok=False, seconds=None),
    Tool('xrf_models_compare', "Scatter models: the twins' shootout against the real blanks'", 'fluo', 'data',
         'tests/tools/xrf_models.py',
         "Every method's bias on the model twins of the blanks against its bias on the real blanks (C66), per "
         "condition, and the verdicts: whether a scatter model can stand in for the real scatter in tests of line "
         "fits. Reads the runs of xrf_blanks.py on the twins (seconds).",
         committed=('docs/studies/xrf_models/scatter/compare.csv', 'docs/studies/xrf_models/scatter/compare_zero.csv',
                    'docs/studies/xrf_models/scatter/compare_summary.csv'),
         docs=('docs/studies/xrf_models/README.md',), data='public', subcommand='compare',
         defaults={'--out': 'docs/studies/xrf_models/scatter'},
         inputs=('docs/studies/xrf_models/scatter', 'docs/studies/xrf_shootout/run_blanks',
                 'docs/studies/xrf_shootout/run_blanks_options'),
         repo_out='docs/studies/xrf_models/scatter', repo_ok=False, seconds=None),
    Tool('xrf_lineshape', 'Real line shapes on both detectors', 'fluo', 'data',
         'tests/tools/xrf_lineshape.py',
         "Real fluorescence lines of the single-element readout (an L family at 10^6 counts, the burn series' K line) "
         "and of every element of the seven-element readout, fitted with a ladder of shapes from a Gaussian at the "
         "resolution to two tails and a shelf: is a Gaussian enough? Needs the decrypted private bundle; the public "
         "table holds derived numbers only (about a minute).",
         committed=('docs/studies/xrf_models/lines',),
         docs=('docs/studies/xrf_models/README.md',), data='private',
         defaults={'--out': OUT},
         variations=(V('Also the public table', 'line_shapes.csv beside the private fits.',
                       'docs/studies/xrf_models/README.md#2a. Probes and shapes', public=OUT),),
         committed_with={'--public': 'docs/studies/xrf_models/lines'},
         repo_ok=False, seconds=None),
    Tool('xrf_scatter_energy', 'Scatter at beam energies with no data: leave one energy out', 'fluo', 'data',
         'tests/tools/xrf_scatter_energy.py',
         "How to synthesise the excitation scatter at a beam energy with no measured spectrum: every readout B "
         "pre-edge sum fitted with the scatter model, each energy held out in turn and predicted from the others by "
         "the generator's defaults, the nearest spectrum shifted, smooth parameters, and a whole measured parameter "
         "set carried by the physics (the recommended one); and readout B's sets tried on readout A. Needs the "
         "decrypted private bundle; its tables and figures stay private (about 15 minutes on 8 CPUs).",
         docs=('docs/studies/xrf_models/scatter_energy.md', 'docs/studies/xrf_models/README.md'), data='private',
         defaults={'--out': OUT},
         variations=(V('Leave one energy out only', 'The validation table from fits already made.',
                       'docs/studies/xrf_models/scatter_energy.md', stage='loo'),),
         repo_ok=False, seconds=None),
    Tool('xrf_walkthrough', 'Walkthrough: an XRF test from the raw spectrum to the verdict (ELI5)', 'fluo', 'figures',
         'tests/tools/xrf_walkthrough.py',
         "The whole chain on public data, for the owner's standing order (2026-11-25): a real blank as it comes in, "
         "one test spectrum made from it with a Ni K line of known photons, the reader's three fits over it with "
         "residuals, 500 spectra turned into a bias, pulls and the 'accurate' verdict (the committed run's own "
         "draws), and the false signal: figures W1-W5.",
         committed=('docs/studies/xrf_shootout/walkthrough',),
         docs=('docs/studies/xrf_shootout/walkthrough.md',),
         data='public', defaults={'--part': 'shootout', '--shootout-out': OUT},
         inputs=('tests/reference/mca_scatter', 'docs/studies/xrf_shootout/run_blanks',
                 'docs/studies/xrf_shootout/run_blanks_options'),
         repo_out='docs/studies/xrf_shootout/walkthrough', repo_ok=False, seconds=40.0),
    Tool('xrf_walkthrough_models', 'Walkthrough: can a model replace the real scatter? (ELI5)', 'fluo', 'figures',
         'tests/tools/xrf_walkthrough.py',
         "The models study on one public blank: three scatter models over it with residuals, the misfit at the "
         "shootout's counts, a twin and a second draw, the floor, and a line with the 7-element detector's "
         "measured skew fitted by a Gaussian and by one tail: figures W1-W5.",
         committed=('docs/studies/xrf_models/walkthrough',),
         docs=('docs/studies/xrf_models/walkthrough.md',),
         data='public', defaults={'--part': 'models', '--models-out': OUT},
         inputs=('tests/reference/mca_scatter', 'docs/studies/xrf_shootout/run_blanks',
                 'docs/studies/xrf_models/scatter'),
         repo_out='docs/studies/xrf_models/walkthrough', repo_ok=False, seconds=60.0),
    Tool('xrf_models_figures', 'Models study figures (M1-M5)', 'fluo', 'figures',
         'tests/tools/xrf_models_figures.py',
         "The scatter models on four public blanks with residuals, their misfit in the line boxes, every method's "
         "bias on the model twins against the real blanks, the shape ladder on real lines (numbers only), and the "
         "verdicts with Gaussian and real-shaped lines.",
         committed=('docs/studies/xrf_models/M*.png',),
         docs=('docs/studies/xrf_models/README.md',), data='public',
         defaults={'--out': OUT},
         variations=(V('The scatter fits only', 'M1 and M2, from the ladder (seconds).',
                       'docs/studies/xrf_models/README.md#1a. The ladder', only='1,2'),),
         inputs=('docs/studies/xrf_models/scatter', 'docs/studies/xrf_models/lines', 'docs/studies/xrf_models/shape',
                 'docs/studies/xrf_shootout/run_blanks'),
         repo_out='docs/studies/xrf_models', repo_ok=False),
    Tool('xrf_shootout_figures', 'XRF shootout figures (X1-X12)', 'fluo', 'figures',
         'tests/tools/xrf_shootout_figures.py',
         'The scoreboard of bias by condition and method, bias against counts, XFNTR curves divided by the truth, '
         'the honesty of the error bars, better-same-worse per condition, the new synthetic spectra part by part, '
         'the three Compton models with the remembered constants checked, speed, and the lines injected into the '
         'real blanks (X9-X11, blanks_tables.md) and the real burn series (X12, real_tables.md).',
         committed=('docs/studies/xrf_shootout/X*.png', 'docs/studies/xrf_shootout/wins.csv',
                    'docs/studies/xrf_shootout/tables.md', 'docs/studies/xrf_shootout/blanks_tables.md',
                    'docs/studies/xrf_shootout/real_tables.md'),
         docs=('docs/studies/xrf_shootout/summary.md',),
         defaults={'--run': 'docs/studies/xrf_shootout/run,docs/studies/xrf_shootout/run_measured,docs/studies/xrf_shootout/run_pymca', '--out': OUT},
         variations=(V('Synthetic spectra only', 'X6 and X7, which need no shootout run (seconds).',
                       'docs/studies/xrf_shootout/README.md#3. figures, tables.md and wins.csv', only='6,7'),),
         inputs=('docs/studies/xrf_shootout/run', 'docs/studies/xrf_shootout/run_measured',
                 'docs/studies/xrf_shootout/run_pymca', 'docs/studies/xrf_shootout/run_blanks',
                 'docs/studies/xrf_shootout/run_blanks_options', 'docs/studies/xrf_shootout/run_real',
                 'docs/studies/xrf_shootout/physics_check.csv', 'tests/reference/mca_scatter'),
         repo_out='docs/studies/xrf_shootout', repo_ok=False),

    # ------------------------------------------------------------ the reader's window
    Tool('gui_screens', 'Screenshots of every area of the window', 'gui', 'figures',
         'tests/tools/gui_screens.py',
         'Screenshots of every tab, area and dialog of the reader on the NX school data and synthetic MCA and '
         'burn data, with an index.',
         committed=('docs/gui/screens',), docs=('docs/gui/screens/README.md', 'docs/gui/README.md'),
         data='public', defaults={'--out': OUT},
         variations=(V('Quick (skip the slow areas)', 'Leaves out Ref Patch, GID patch, cuts and burn on the real '
                       'data.', 'tests/tools/gui_screens.py', skip_slow=True),),
         inputs=UI + ('docs/gui/screens/README.md',), seconds=None,
         volatile=(r'last run took', r'drawing took [0-9.]+ s')),          # README.md's timings
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
    Tool('xr_excess_scatter', 'Real reflectivity: scatter beyond counting statistics (private data)', 'external',
         'external',
         demonstrates="The excess per-point scatter of 384 real reflectivity series (DATA_NEEDS row 15): the core "
                      'excess, the scale on σ and the outlier share within a scan, overall and by Qz, counts, '
                      'background and monitor (between-scan numbers set aside, owner 2026-11-25). Made by the '
                      "non-cloud agent's private generator (sample_data/private/xr/); not regenerable here; the "
                      'numbers are the real_*.csv beside the study, and the walkthrough draws them (W4).',
         committed=('docs/studies/excess_scatter/real_overall.csv', 'docs/studies/excess_scatter/real_by.csv',
                    'docs/studies/excess_scatter/real_runs.csv', 'docs/studies/excess_scatter/real_tails.csv',
                    'docs/studies/excess_scatter/real_scale.csv',
                    'docs/studies/excess_scatter/real_numbers.json'),
         docs=('docs/studies/excess_scatter/summary.md',),
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
    Tool('qoff_edge_explainer', 'The pieces of the puzzle: the edge, Qoff, the resolution, absorption', 'refl',
         'figures', 'tests/tools/qoff_edge_explainer.py',
         'One calculated figure (bare water, 10 keV, no data) that shows what the Qoff and resolution studies mean: '
         'a whole reflectivity curve, a close-up of the critical edge shifted by the angle offset and blurred by the '
         'resolution, what absorption does to the edge, how a wrong offset tilts R/R_F, and a glossary.',
         committed=('docs/studies/qoff_resolution_real/Q0_the_pieces.png',),
         docs=('docs/studies/qoff_resolution_real/summary.md',),
         data='public', defaults={'--out': OUT},
         repo_out='docs/studies/qoff_resolution_real', repo_ok=False, seconds=10.0),

    Tool('qoff_resolution_real','Angle offset and Qz resolution on real edges (private data)', 'external', 'external',
         demonstrates="Tools man's new edge fit (fresnel.fit_edge_resolution: angle offset and resolution width together) on 400 real edge scans "
                      "and 96 released ones: simulated edges sampled like the real ones, the fit "
                      "against the earlier Qz-resolution study, the residual pattern, the offset from series to series and what moves it. Made by "
                      "the owner's PC's private generator (sample_data/private/xr/); not regenerable here; the "
                      'numbers are the CSVs beside the figures.',
         committed=('docs/studies/qoff_resolution_real',), docs=('docs/studies/qoff_resolution_real/summary.md',),
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
