"""Reopening a SPEC file applies the settings its workbook recorded (issue #145;
the owner, 2026-11-27: "Restore, list what changed"). One message lists the
settings that differed, old -> new; the preference 'restore_workbook_settings'
turns it off."""
import numpy as np
import pytest

from lss_core import workbook as wbmod

pytestmark = pytest.mark.gui


def test_read_settings_and_the_changes(tmp_path):
    path = str(tmp_path / 'x_reader.xlsx')
    wb = wbmod.Workbook(path)
    wb.set_settings('reduction', {'error_model': 'budget', 'gid': {'columns': 4, 'row_min': 15}})
    wb.set_settings('reflectivity', {'qc': '0.0230', 'slit': '25,13'})
    wb.save()
    saved = wbmod.read_settings(path)
    assert saved['reduction'] == {'error_model': 'budget', 'gid': {'columns': 4, 'row_min': 15}}
    assert saved['reflectivity']['slit'] == '25,13'
    assert wbmod.read_settings(str(tmp_path / 'none.xlsx')) == {}
    current = {'reduction': {'error_model': 'legacy', 'gid': {'columns': 3, 'row_min': 15}},
               'reflectivity': {'qc': '0.0230', 'slit': '21,11', 'qoff': '0'}}
    changes = wbmod.settings_changes(current, saved)
    assert ('reduction', 'error_model', 'legacy', 'budget') in changes
    assert ('reduction', 'gid.columns', 3, 4) in changes
    assert ('reflectivity', 'slit', '21,11', '25,13') in changes
    assert not any(k in ('qc', 'gid.row_min') for _, k, _, _ in changes)     # '0.0230' == 0.023: unchanged
    assert wbmod.settings_changes({'reduction': {}}, saved) == []           # a setting the reader no longer has


def _reduce_and_save(w):
    """Change settings the way a user would, then save a result (the save writes the Settings sheet)."""
    w.ui.refQcLineEdit.setText('0.0231')
    w.ui.refSlitLineEdit.setText('25,13')
    w.ui.refBGOffLineEdit.setText('0.7')
    w.errorModeComboBox.setCurrentIndex(1)
    w.setErrorModel()
    from lss_core import gid as gidmod
    w.gidParams = gidmod.GIDParams(columns=4)
    w.saveToWorkbook('spec', [dict(scans=[1], data=np.array([[0.0, 1.0], [1.0, 2.0]]), columns=['x', 'y'],
                                   label='t')], auto=True)


def test_reopening_restores_and_lists_the_changes(loaded, qapp, dataset, recorder):
    w = loaded
    _reduce_and_save(w)
    saved = wbmod.read_settings(w.workbookPath())
    assert saved['reflectivity']['slit'] == '25,13' and saved['reduction']['monitor_model']['kind'] == 'gaussian'
    w.ui.refQcLineEdit.setText('0.0217')                    # as if the reader had been reset
    w.ui.refSlitLineEdit.setText('21,11')
    w.errorModeComboBox.setCurrentIndex(0)
    w.setErrorModel()
    from lss_core import gid as gidmod
    w.gidParams = gidmod.GIDParams()
    recorder.messages.clear()
    w.openSpecFile(fname=dataset)
    qapp.processEvents()
    assert w.ui.refQcLineEdit.text() == '0.0231' and w.ui.refSlitLineEdit.text() == '25,13'
    assert w.ui.refBGOffLineEdit.text() == '0.7'
    assert w.errorModel.budget and w.errorModeComboBox.currentIndex() == 1
    assert w.gidParams.columns == 4
    said = [m for m in recorder.messages if m.startswith('Settings restored')]
    assert len(said) == 1 and 'ROI size 21,11 -> 25,13' in said[0] and 'error model legacy -> budget' in said[0]
    assert not any(m.startswith('Error model:') for m in recorder.messages)     # one message, not one per setting
    assert recorder.exceptions == []


def test_nothing_restored_when_the_preference_is_off(loaded, qapp, dataset, recorder):
    w = loaded
    _reduce_and_save(w)
    w.setPreference('restore_workbook_settings', False)
    w.ui.refSlitLineEdit.setText('21,11')
    recorder.messages.clear()
    w.openSpecFile(fname=dataset)
    qapp.processEvents()
    assert w.ui.refSlitLineEdit.text() != '25,13'
    assert not any(m.startswith('Settings restored') for m in recorder.messages)
    assert recorder.exceptions == []


def test_a_file_without_a_workbook_opens_as_before(window, qapp, dataset, recorder):
    window.openSpecFile(fname=dataset)
    qapp.processEvents()
    assert not any(m.startswith('Settings restored') for m in recorder.messages)
    assert recorder.exceptions == []
