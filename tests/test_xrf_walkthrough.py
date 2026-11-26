"""The XRF walkthroughs (docs/studies/xrf_shootout/walkthrough.md and
docs/studies/xrf_models/walkthrough.md, 2026-11-25) quote the numbers their
tool wrote, and the shootout's example is the committed run's own."""
import csv
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))

import xrf_walkthrough as W            # noqa: E402

SHOOT = os.path.join('docs', 'studies', 'xrf_shootout')
MODELS = os.path.join('docs', 'studies', 'xrf_models')


def _json(folder):
    with open(os.path.join(folder, 'walkthrough', 'numbers.json'), encoding='utf-8') as f:
        return json.load(f)


def _text(folder):
    with open(os.path.join(folder, 'walkthrough.md'), encoding='utf-8') as f:
        return f.read().replace('−', '-')                   # the docs write a true minus sign


def _pc(v, signed=True):
    return ('%+.1f %%' if signed else '%.1f %%') % (100 * v)


def test_the_shootout_example_is_the_committed_runs_own():
    N = _json(SHOOT)
    with open(os.path.join(SHOOT, 'run_blanks', 'scores.csv'), encoding='utf-8') as f:
        rows = {(r['condition'], r['method']): r for r in csv.DictReader(f)}
    with open(os.path.join(SHOOT, 'run_blanks_options', 'scores.csv'), encoding='utf-8') as f:
        rows.update({(r['condition'], r['method']): r for r in csv.DictReader(f)})
    cond = N['example']['condition']
    for m, v in N['replicates'].items():
        assert v['bias'] == pytest.approx(float(rows[(cond, m)]['bias']), rel=1e-3), m
        assert v['spectra'] == 500


def _rows(text, width):
    """Table rows of ``width`` cells, by their first cell (bold marks stripped)."""
    out = {}
    for line in text.splitlines():
        if line.startswith('|'):
            cells = [c.strip().strip('*').strip() for c in line.strip().strip('|').split('|')]
            if len(cells) == width:
                out.setdefault(cells[0], cells)
    return out


def test_the_shootout_walkthrough_quotes_its_numbers():
    N, t = _json(SHOOT), _text(SHOOT)
    rows = _rows(t, 6)                                   # step 4's table: bias, SE, SD, pull mean, pull SD
    for m, name in (('p1', 'Poisson fit'), ('p1p3', 'Poisson fit + escapes removed'),
                    ('p1p2p3', 'Poisson fit + fixed width + escapes removed')):
        v = N['replicates'][m]
        assert rows[name][1:] == [_pc(v['bias']), '%.2f %%' % (100 * v['bias_se']), '%.1f %%' % (100 * v['sd']),
                                  '%+.2f' % v['pull_mean'], '%.2f' % v['pull_sd']], (name, rows[name])
    for m, v in N['fit'].items():
        assert '%.0f ± %.0f' % (v['estimate'], v['error']) in t, m
        assert '%.2f' % v['chi2_dof'] in t, m
    assert '%.3f' % N['example']['thinning_p'] in t
    for m, per100 in N['false_signal_per100'].items():
        assert ('| %.0f |' % per100 in t) or ('| %.1f |' % per100 in t), (m, per100)


def test_the_models_walkthrough_quotes_its_numbers():
    N, t = _json(MODELS), _text(MODELS)
    for m in ('generator', 'gaussian', 'full'):
        assert _pc(N['box'][m]['box_residual']) in t, m
        assert '%.2f ± %.2f' % (N['at_use'][m]['thinned_measured'], N['at_use'][m]['thinned_sd']) in t, m
    for m in ('full_redraw', 'full', 'gaussian', 'generator'):
        assert _pc(N['floor_cdf'][m]['median'], signed=False) in t, m
    for s in ('gauss_res', 'gauss', 'tail'):
        assert '%.1f' % N['line_ladder'][s]['dev_per_dof'] in t or '%.2f' % N['line_ladder'][s]['dev_per_dof'] in t, s
    for case, v in N['p2_noise_free'].items():
        assert _pc(v['p1p2p3']['line']) in t, case


XRF_DOCS = [os.path.join(SHOOT, f) for f in ('walkthrough.md', 'summary.md', 'README.md', 'QUESTIONS.md',
                                              'tables.md', 'blanks_tables.md', 'real_tables.md')] + \
           [os.path.join(MODELS, f) for f in ('walkthrough.md', 'README.md', 'scatter_energy.md')]


@pytest.mark.parametrize('path', XRF_DOCS)
def test_the_xrf_docs_use_plain_names_not_codes(path):
    """Owner, 2026-11-25: "rename things with names like 'P1' and 'p1 + p2' and
    anything else written in cryptic fashion". The reader's options are named
    (Poisson fit, + fixed width, + escapes removed), the detectors are named
    (not readout A/B) and the blanks are '9.2 keV blank a' (not E9.2-a); a line
    that maps an old code to its name says F90 (the feature that numbered them)."""
    import re
    with open(path, encoding='utf-8') as f:
        bad = [line for line in f
               if re.search(r'\bP[123]\b|\b[Rr]eadout [AB]\b|(?<![/\w])E(6\.1|9\.2|10)-[a-k]\b(?!\.csv)', line)
               and 'F90' not in line]
    assert bad == [], bad[:3]


def test_the_figure_labels_use_plain_names():
    import xrf_shootout_figures as F
    for table in (F.SHORT, F.LABEL):
        for m, name in table.items():
            assert not any(c in name for c in ('P1', 'P2', 'P3')), (m, name)
    assert F.blank_name('E9.2-a') == '9.2 keV blank a'
    assert F.cond_name('hard_11keV') == 'hard case, 11 keV beam'


def test_a_perfect_model_has_unit_deviance_per_point_after_thinning():
    """The walkthrough's 'misfit at use' rule rests on this: Poisson counts
    drawn from the model itself give a deviance per point of about 1."""
    mu = np.full(4000, 40.0)
    n = np.random.default_rng(3).poisson(mu).astype(float)
    assert np.mean(W._dev(n, mu)) == pytest.approx(1.0, abs=0.05)
    assert np.mean(W._dev(1.5 * mu, mu)) > 5                  # a 50 % misfit at 40 counts is not
