"""The frame movie in the main window (F69; owner's answers of 2026-11-23,
docs/gui/questions.md: Q7 a movie whenever 3 or more frames are selected,
space pauses or plays, any arrow key pauses and then steps, up/back/left
backward and down/forward/right forward; Q-IMG-4 one shared colour scale;
zoom, colour map and colour mode never change while it plays).

Before (image_display.md §1.2, measured): a blocking loop of 0.5 s per
frame with no stop, which left the Axes box at Q. Synthetic data: scan 1
has 9 frames."""
import pytest
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeyEvent

import sweep
from lss_core import display

pytestmark = pytest.mark.gui


def _all_of_scan_1(w, qapp):
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp)
    w.flushPendingSelection()


def _image_axes(w):
    return [ax for ax in w.ui.pilMplWidget.canvas.fig.axes if ax.images]


def _key(w, qapp, key):
    canvas = w.ui.pilMplWidget.canvas
    ev = QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier, ' ' if key == Qt.Key_Space else '')
    qapp.sendEvent(canvas, ev)


def test_three_or_more_frames_play_as_a_movie(loaded, qapp, recorder):
    w = loaded
    _all_of_scan_1(w, qapp)
    assert recorder.exceptions == []
    assert w.pilMode == 'movie' and len(_image_axes(w)) == 1
    assert w.pilMovieTimer.isActive()                                  # it plays
    assert w.pilMovieTimer.interval() == 500                           # 2 fps by default
    assert _image_axes(w)[0].get_title() == 'S# 1 pt 0'
    assert w.ui.pilMovieCounterLabel.text() == '1 / 9'
    info = w.ui.pilMovieInfoLabel.text()
    assert info.startswith('S# 1 · pt 0 · Qz 0.0100') and 'Monc' in info
    for name in ('pilViewComboBox', 'pilMoviePlayPushButton', 'pilMovieBackPushButton',
                 'pilMovieForwardPushButton', 'pilMovieSlider', 'pilMovieCounterLabel', 'pilMovieSpeedComboBox',
                 'pilMovieLoopCheckBox', 'pilMovieInfoLabel'):
        assert getattr(w.ui, name).toolTip(), name
    sweep._select_images(w, qapp, [0, 1])                              # 2 frames: tiles
    w.flushPendingSelection()
    assert w.pilMode == 'tiles' and not w.pilMovieTimer.isActive()
    assert not w.ui.pilMoviePlayPushButton.isEnabled()


def test_frames_advance_without_changing_zoom_map_or_scale(loaded, qapp, recorder):
    w = loaded
    _all_of_scan_1(w, qapp)
    ax = _image_axes(w)[0]
    ax.set_xlim(50.0, 130.0)                                           # the user's zoom
    ax.set_ylim(70.0, 150.0)
    im = ax.images[0]
    norm, cmap = im.norm, im.cmap
    for k in range(1, 4):
        w.pilMovieTick()
        assert w.pilMovieIndex == k
        assert _image_axes(w)[0] is ax and ax.images[0] is im
        assert ax.get_xlim() == pytest.approx((50.0, 130.0)) and ax.get_ylim() == pytest.approx((70.0, 150.0))
        assert im.norm is norm and im.cmap is cmap                     # one scale for the whole movie
        assert ax.get_title() == 'S# 1 pt %d' % k
    assert w.ui.pilMovieCounterLabel.text() == '4 / 9' and w.ui.pilMovieSlider.value() == 3
    # the image list marks the frame shown without changing the selection
    assert w.ui.imageListWidget.currentRow() == 3
    assert len(w.ui.imageListWidget.selectedItems()) == 9
    assert recorder.exceptions == []


def test_keys_q7(loaded, qapp, recorder):
    w = loaded
    _all_of_scan_1(w, qapp)
    assert w.pilMovieTimer.isActive()
    _key(w, qapp, Qt.Key_Space)                                        # pause
    assert not w.pilMovieTimer.isActive()
    _key(w, qapp, Qt.Key_Space)                                        # play
    assert w.pilMovieTimer.isActive()
    _key(w, qapp, Qt.Key_Right)                                        # pauses, then forward
    assert not w.pilMovieTimer.isActive() and w.pilMovieIndex == 1
    for key, k in ((Qt.Key_Down, 2), (Qt.Key_Forward, 3), (Qt.Key_Up, 2), (Qt.Key_Left, 1), (Qt.Key_Back, 0),
                   (Qt.Key_Left, 0)):                                  # held at the first frame
        _key(w, qapp, key)
        assert w.pilMovieIndex == k, key
    assert _image_axes(w)[0].get_title() == 'S# 1 pt 0'
    assert recorder.exceptions == []


def test_end_loop_slider_and_speed(loaded, qapp, recorder):
    w = loaded
    _all_of_scan_1(w, qapp)
    w.ui.pilMovieSlider.setValue(8)                                    # the last frame
    assert w.pilMovieIndex == 8
    w.pilMoviePlay(True)
    w.pilMovieTick()                                                   # no loop: back to the start, playing
    assert w.pilMovieIndex == 1
    w.ui.pilMovieSlider.setValue(8)
    w.pilMovieTick()
    assert w.pilMovieIndex == 8 and not w.pilMovieTimer.isActive()     # stops on the last frame
    w.ui.pilMovieLoopCheckBox.setChecked(True)
    w.pilMoviePlay(True)
    w.pilMovieTick()
    assert w.pilMovieIndex == 0                                        # loops round
    w.ui.pilMovieSpeedComboBox.setCurrentIndex(w.ui.pilMovieSpeedComboBox.findData(10.0))
    assert w.pilMovieTimer.interval() == 100
    assert w.prefs['pil_display']['fps'] == 10.0 and w.prefs['pil_display']['loop'] is True
    assert recorder.exceptions == []


def test_tiles_instead_of_the_movie(loaded, qapp, recorder):
    w = loaded
    w.ui.pilViewComboBox.setCurrentIndex(w.ui.pilViewComboBox.findData('tiles4'))
    _all_of_scan_1(w, qapp)
    axs = _image_axes(w)
    assert w.pilMode == 'tiles' and len(axs) == 4
    assert [ax.get_title() for ax in axs] == ['S# 1 pt %d' % p for p in display.sample(9, 4)]
    assert '4 of 9 shown (sampled)' in w.ui.pilMplWidget.canvas.fig._suptitle.get_text()
    assert not w.pilMovieTimer.isActive()
    assert w.prefs['pil_display']['view'] == 'tiles4'
    w.ui.pilViewComboBox.setCurrentIndex(w.ui.pilViewComboBox.findData('movie'))
    assert w.pilMode == 'movie' and len(_image_axes(w)) == 1
    assert recorder.exceptions == []


def test_movie_button_leaves_the_axes_and_does_not_block(loaded, qapp, recorder):
    """The recorded defect: the old movie set Axes to Q and left it there."""
    w = loaded
    sweep._select_scans(w, qapp, [0])
    sweep._select_images(w, qapp, [2, 3])
    w.flushPendingSelection()
    w.ui.pilAxesComboBox.setCurrentIndex(w.ui.pilAxesComboBox.findText('Angles'))
    w.ui.pilMoviePushButton.click()
    assert w.ui.pilAxesComboBox.currentText() == 'Angles'
    assert w.pilMode == 'movie' and w.pilMovieTimer.isActive()        # two frames, played on request
    w.ui.gixSumCheckBox.setChecked(True)                               # "Sum All" of two Qz: refused, paused
    assert not w.pilMovieTimer.isActive() and 'different qz' in recorder.messages[-1]
    sweep._select_images(w, qapp, [2])
    w.flushPendingSelection()
    assert w.pilMode == 'sum'
    assert recorder.exceptions == []
