"""Qc from the subphase and a proposed Qoff on the Reflectivity tab (F79;
the core is lss_core.fresnel, tools session). Nothing is applied by itself
(rule 12): the menus offer values and a field changes only when one is
picked."""
import numpy as np
import pytest

from lss_core import fresnel

pytestmark = pytest.mark.gui

QOFF_TRUE = 0.0006


def _curve(qc=fresnel.QC_WATER, qoff=QOFF_TRUE, n=60, seed=3):
    """A Fresnel reflectivity seen with a Qz offset: R(q) = R_F(q + Qoff), 2 % errors, scaled."""
    rng = np.random.default_rng(seed)
    q = np.linspace(0.012, 0.06, n)
    r = fresnel.fresnel(q + qoff, qc) * 3.0e5
    e = 0.02 * r
    return [[a, b + rng.normal(0, c), c] for a, b, c in zip(q, r, e)]


def _show(w, rows):
    w.refData = rows
    w.refpatchindex = 1                  # a patched curve: no per-point scan labels needed
    w.updateRefPlotData()


def test_the_buttons_sit_beside_their_fields(window, recorder):
    w = window
    for field, button in ((w.ui.refQcLineEdit, w.refQcSubphaseToolButton),
                          (w.ui.refQoffLineEdit, w.refQoffProposePushButton)):
        lay = w._layoutHolding(field)
        assert lay is not None and lay.indexOf(button) == lay.indexOf(field) + 1
    assert 'from memory' in w.refQcSubphaseToolButton.toolTip()
    assert 'only when one is picked' in w.refQoffProposePushButton.toolTip()
    assert recorder.exceptions == []


def test_the_subphase_menu_sets_qc_from_the_tabulated_density(window, recorder):
    w = window
    acts = [a for a in w.refQcMenu.actions() if not a.isSeparator()]
    assert len(acts) == len(fresnel.SUBPHASES) + 1
    for act, sp in zip(acts, fresnel.SUBPHASES):
        assert act.text().startswith(sp.name) and sp.source in act.toolTip()
    nacl = next(sp for sp in fresnel.SUBPHASES if sp.name.startswith('NaCl'))
    acts[fresnel.SUBPHASES.index(nacl)].trigger()
    assert w.ui.refQcLineEdit.text() == '%.5f' % nacl.qc
    assert any(nacl.name in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_qc_from_a_typed_electron_density(window, recorder, monkeypatch):
    from PyQt5 import QtWidgets
    w = window
    monkeypatch.setattr(QtWidgets.QInputDialog, 'getText', staticmethod(lambda *a, **k: ('0.40', True)))
    w.refQcFromDensity()
    assert w.ui.refQcLineEdit.text() == '%.5f' % fresnel.qc_from_density(0.40)
    monkeypatch.setattr(QtWidgets.QInputDialog, 'getText', staticmethod(lambda *a, **k: ('heavy', True)))
    w.refQcFromDensity()                                       # refused, said, Qc kept
    assert w.ui.refQcLineEdit.text() == '%.5f' % fresnel.qc_from_density(0.40)
    assert any('not an electron density' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_propose_without_a_reflectivity_says_so(window, recorder):
    w = window
    w.refData = []
    w.refQoffProposePushButton.click()
    assert recorder.menus == [] and any('make a reflectivity first' in m for m in recorder.messages)
    assert recorder.exceptions == []


def test_the_proposal_is_offered_not_applied(window, recorder):
    """The edge fit finds the offset put in (within 3 σ); the field changes
    only when its entry is picked, and R/R_F is redrawn with it."""
    w = window
    w.ui.refQcLineEdit.setText('%.5f' % fresnel.QC_WATER)
    w.ui.refQoffLineEdit.setText('0')
    _show(w, _curve())
    w.refQoffProposePushButton.click()
    (menu,) = recorder.menus
    edge, smooth = w.refQoffProposal
    assert edge.ok and abs(edge.qoff - QOFF_TRUE) < max(3 * edge.sigma, 1e-4), edge
    assert w.ui.refQoffLineEdit.text() == '0'                  # offered, not applied (rule 12)
    acts = menu.actions()
    assert '+/-' in acts[0].text() and 'edge fit' in acts[0].text()
    assert 'roughness' in acts[1].text()
    assert any('Proposed' in m for m in recorder.messages)
    acts[0].trigger()
    assert float(w.ui.refQoffLineEdit.text()) == pytest.approx(edge.qoff, abs=6e-6)
    assert w.refQoff == pytest.approx(edge.qoff, abs=6e-6)     # updateRefPlotData ran with it
    assert recorder.exceptions == []
