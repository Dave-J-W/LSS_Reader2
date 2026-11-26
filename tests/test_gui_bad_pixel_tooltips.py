"""The Pilatus tab's whole-frame bad-pixel pass explains itself (main man,
issue #55, 2026-11-26; rule 9): tooltips with the arithmetic and C62's
warning, the label "factor", and a factor that can reach 10 (it stopped at
4, below the factor C62 found safe on sparse frames). Off by default."""
import pytest

pytestmark = pytest.mark.gui


def test_the_whole_frame_pass_has_tooltips_and_a_reachable_safe_factor(window, recorder):
    ui = window.ui
    assert ui.pilBPCiteSpinBox.value() == 0                                  # off by default
    for w in (ui.pilBPCiteSpinBox, ui.label_20, ui.pilBPCfacSpinBox, ui.label_35):
        tip = w.toolTip()
        assert 'every frame as it is read' in tip and 'C62' in tip and 'factor 10' in tip
    assert ui.label_35.text() == 'factor'
    assert ui.pilBPCfacSpinBox.maximum() >= 10
    assert recorder.exceptions == []
