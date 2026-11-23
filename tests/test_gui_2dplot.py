"""The 2D_Plot tab draws an x y z map file.

Found by the GUI assessment (2026-11-22, TODO area I): adding a file raised
AttributeError, because ``update2dPlotPlot`` called
``matplotlib.cm.get_cmap``, removed in matplotlib 3.9; and the colour-map
lists of the 2D_Plot and (hidden) Apex tabs offered ``spectral``, the name
matplotlib 2.0 changed to ``nipy_spectral`` and later removed. The crash
sweep never saw it: its file chooser returns no file.
"""
import matplotlib
import numpy as np
import pytest

pytestmark = pytest.mark.gui

NX, NY = 30, 20


def _map_file(tmp_path):
    xx, yy = np.meshgrid(np.linspace(0.1, 1.0, NX), np.linspace(0.1, 1.0, NY))
    zz = 1.0 + 100.0 * np.exp(-(((xx - 0.4) / 0.15) ** 2 + ((yy - 0.6) / 0.1) ** 2))
    path = tmp_path / 'map.txt'
    np.savetxt(path, np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()]))
    return str(path)


def test_a_map_file_is_drawn_in_every_colour_map_and_scale(window, qapp, recorder, tmp_path):
    recorder.open_names = [_map_file(tmp_path)]
    window.ui.twodPlotAddFilePushButton.click()
    qapp.processEvents()
    files = window.ui.twodPlotFileListWidget
    assert files.count() == 1
    files.item(0).setSelected(True)
    qapp.processEvents()
    assert recorder.exceptions == []
    assert window.plot2dindex == 0
    assert window.plot2d_p.get_array().size == NX * NY
    combo = window.ui.twodCMapComboBox
    for log in (False, True):
        window.ui.twodLogIntCheckBox.setChecked(log)
        for i in range(combo.count()):
            combo.setCurrentIndex(i)
            qapp.processEvents()
            assert window.plot2d_p.get_cmap().name == combo.itemText(i)
    window.ui.twodUpdatePlotPushButton.click()          # interpolated: drawn with imshow
    qapp.processEvents()
    assert window.plot2dindex == 1
    assert window.plot2d_p.get_cmap().name == combo.currentText()
    assert recorder.exceptions == []
    assert recorder.messages == []


def test_every_colour_map_offered_exists(window, recorder):
    for name in ('pilCMapComboBox', 'gixCMapComboBox', 'twodCMapComboBox'):
        combo = getattr(window.ui, name)
        for i in range(combo.count()):
            assert combo.itemText(i) in matplotlib.colormaps, (name, combo.itemText(i))
    assert recorder.exceptions == []
