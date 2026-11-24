"""The reflectivity ROI close-up panel (F71; docs/gui/image_display.md §2.4,
R1-R6). One panel, the same on the Pilatus tab (beside the frame, following
the movie) and on the Reflectivity tab (the Qz list): owner, Q-IMG-7.

What is drawn (display only; no sum is made here):
- the frame zoomed to the signal box, both background boxes and a margin of
  diffuse scattering (``display.roi_region``), on its own colour scale from
  the signal box (``display.roi_limits``), log by default;
- the boxes as outlines (patches) from ``display.roi_boxes``, which is
  ``TwoDDetector.sumROI``'s arithmetic: the pixels outlined are the pixels
  summed (invariant I38). The boxes before the peak search are dashed
  (owner, Q-IMG-16);
- the column profile (rows of the signal box summed) and the row profile
  (its columns summed), with the boxes shaded and the background level
  netROI subtracts dotted;
- the sums (``display.roi_numbers_text``) and the cues
  (``display.roi_cues``), short on screen, the reasons in tooltips (rule 9).

The window computes what is shown (``MainWindow.pilRoiView``,
``refRoiView``) and calls ``show`` or ``clear``. Artists are made once and
updated in place, so a movie frame costs one redraw of this small canvas.
"""
import numpy as np
from matplotlib import patheffects
from matplotlib.colors import LogNorm, Normalize
from matplotlib.patches import Rectangle
from matplotlib.ticker import FormatStrFormatter, LogLocator, NullLocator

from lss_core import display

SIGNAL_COLOUR = 'white'
BG_COLOUR = 'cyan'
STROKE = [patheffects.withStroke(linewidth=2.8, foreground='black')]
CUE_COLOURS = {'stop': '#b00000', 'warn': '#a05a00', None: '#555555'}

CHECKS_TIP = ('Checks of the boxes on this frame, display only (owner, Q-IMG-7, 2026-11-23): the peak off '
              'centre by more than %d %% of the half-width; more than %g %% of the net intensity on or beyond '
              'the box edge (clipped); a background box %d px or less from the signal box; pixels above the '
              'count-rate limits (F97); the direct beam inside a box; a box that runs off the frame. Position '
              'and clipping are judged only when the net signal is above %g σ.'
              % (round(100 * display.OFF_CENTRE_FRACTION), 100 * display.CLIPPED_FRACTION, display.BG_GAP_PX,
                 display.PEAK_SIGMAS))


class RoiPanel:
    """The close-up drawn into ``canvas`` (a matplotlib FigureCanvas), with
    the Qt labels ``numbers``, ``cues`` and ``cursor`` and the ``logbox``
    check box. ``wide``: the close-up on the left and the profiles on the
    right (the Reflectivity tab's short, wide canvas); otherwise stacked
    (the Pilatus tab's side panel)."""

    def __init__(self, canvas, numbers, cues, cursor, logbox, wide=False):
        self.canvas = canvas
        self.fig = canvas.figure
        self.numbers, self.cues, self.cursor, self.logbox = numbers, cues, cursor, logbox
        self.wide = wide
        self.art = None
        self.view = None
        self.cmap = None
        canvas.mpl_connect('motion_notify_event', self._moved)
        canvas.mpl_connect('resize_event', self._resized)

    def _resized(self, event=None):
        if self.view is not None and self.art is not None and self.art['ax'] in self.fig.axes:
            self.show(self.view)

    def _view_limits(self, region):
        """The close-up's view, ((x0, x1), (y0, y1)): the region, widened in one direction so that pixels
        are square in the axes box (more of the diffuse scattering around it, never less than the region)."""
        ax = self.art['ax']
        r0, r1, c0, c1 = region
        w, h = float(c1 - c0), float(r1 - r0)
        fw, fh = self.fig.get_size_inches()
        pos = ax.get_position()
        box = (pos.height * fh) / max(pos.width * fw, 1e-9)          # height / width of the box
        if h / w < box:
            h = w * box
        else:
            w = h / box
        xc, yc = (c0 + c1 - 1) / 2.0, (r0 + r1 - 1) / 2.0
        xlim, ylim = (xc - w / 2.0, xc + w / 2.0), (yc - h / 2.0, yc + h / 2.0)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        return xlim, ylim

    # ---- artists, made once
    def _build(self):
        fig = self.fig
        fig.clf()
        ax, cax, axc, axr = [fig.add_axes([0.1, 0.1, 0.5, 0.5]) for _ in range(4)]
        ax.set_facecolor('0.85')
        im = ax.imshow(np.ones((2, 2)), origin='lower', interpolation=display.INTERPOLATION, aspect='auto')
        cbar = fig.colorbar(im, cax=cax, format='%.0e')
        cbar.ax.tick_params(labelsize='x-small')
        boxes, old = [], []
        for k in range(3):
            colour = SIGNAL_COLOUR if k == 0 else BG_COLOUR
            boxes.append(ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, ec=colour, lw=1.4, path_effects=STROKE,
                                                zorder=4)))
            old.append(ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, ec=colour, lw=1.0, ls='--', zorder=3)))
        soft, = ax.plot([], [], 's', mfc='none', mec=display.SOFT_RGBA[:3], ms=5, mew=1.2, zorder=5)
        hard, = ax.plot([], [], 's', mfc='none', mec=display.HARD_RGBA[:3], ms=5, mew=1.4, zorder=5)
        beam, = ax.plot([], [], 'x', color='white', ms=9, mew=2, path_effects=STROKE, zorder=6)
        lines, levels, spans = {}, {}, {}
        for key, a in (('col', axc), ('row', axr)):
            lines[key], = a.plot([], [], '-', color='k', lw=1.0, drawstyle='steps-mid')
            levels[key], = a.plot([], [], ':', color='0.35', lw=1.0)
            spans[key] = [a.add_patch(Rectangle((0, 0), 1, 1, transform=a.get_xaxis_transform(), ec='none',
                                                fc='0.55' if k == 0 else BG_COLOUR, alpha=0.3, zorder=0))
                          for k in range(3)]
            a.tick_params(labelsize='x-small')
        axc.set_xlabel('column', fontsize='x-small', labelpad=1)
        axr.set_xlabel('row', fontsize='x-small', labelpad=1)
        axc.set_ylabel('Σ rows', fontsize='x-small')
        axr.set_ylabel('Σ columns', fontsize='x-small')
        ax.tick_params(labelsize='x-small')
        note = fig.text(0.5, 0.5, '', ha='center', va='center', fontsize='small', color='0.3', wrap=True)
        self.art = {'ax': ax, 'cax': cax, 'axc': axc, 'axr': axr, 'im': im, 'cbar': cbar, 'boxes': boxes,
                    'old': old, 'soft': soft, 'hard': hard, 'beam': beam, 'lines': lines, 'levels': levels,
                    'spans': spans, 'note': note, 'yscale': 'linear', 'placed': None}
        self._place((1, 3))

    def _place(self, region_shape):
        """Positions of the four axes (figure fractions). Wide: the close-up on the left, the profiles on
        the right. Stacked: the close-up on top, as tall as the region's shape asks for (between a fifth and
        a half of the panel), the profiles below sharing the rest."""
        a = self.art
        rows, cols = region_shape
        if self.wide:
            key = 'wide'
            pos = {'ax': [0.06, 0.15, 0.50, 0.66], 'cax': [0.57, 0.15, 0.012, 0.66],
                   'axc': [0.71, 0.62, 0.275, 0.30], 'axr': [0.71, 0.16, 0.275, 0.30]}
        else:
            w, h = self.fig.get_size_inches()
            frac = 0.62 * w * rows / max(cols, 1) / max(h, 1e-6)
            frac = round(min(max(frac, 0.2), 0.5), 2)
            key = ('tall', frac)
            top = 0.90
            low = top - frac
            prof = (low - 0.06 - 0.16) / 2.0
            pos = {'ax': [0.17, low, 0.62, frac], 'cax': [0.81, low, 0.03, frac],
                   'axc': [0.17, 0.06 + prof + 0.09, 0.78, prof], 'axr': [0.17, 0.06, 0.78, prof]}
        if a['placed'] != key:
            for name, p in pos.items():
                a[name].set_position(p)
            a['placed'] = key

    def _ready(self):
        if self.art is None or self.art['ax'] not in self.fig.axes:
            self._build()
        return self.art

    def _axes_visible(self, on):
        a = self.art
        for ax in (a['ax'], a['cax'], a['axc'], a['axr']):
            ax.set_visible(on)
        a['note'].set_visible(not on)

    # ---- what is shown
    def clear(self, message, tip=''):
        """No close-up: ``message`` on the canvas, the labels emptied."""
        a = self._ready()
        self.view = None
        self._axes_visible(False)
        a['note'].set_text(message)
        self.numbers.setText('')
        self.numbers.setToolTip(tip or self.numbers_tip(None))
        self.cues.setText('')
        self.cues.setToolTip(CHECKS_TIP)
        self.cursor.setText('')
        self.canvas.draw_idle()

    def show(self, view):
        """Draw ``view`` (a dict made by the window):

        image, error: the frame summed, its errors (2D, same units); region;
        boxes, old (dashed, or None): roi_boxes; direction; sums (8 values,
        or None); cues; title; units; saturated ((soft, hard) or None);
        beam ((row, col) or None); tip: what the numbers are (their
        tooltip); cmap: the colour map."""
        a = self._ready()
        self.view = view
        self._axes_visible(True)
        img = np.asarray(view['image'], dtype=float)
        shape = img.shape
        region = view['region']
        r0, r1, c0, c1 = region
        log = self.logbox.isChecked()
        vmin, vmax = display.roi_limits(img, view['boxes'], region, log)
        self._place((r1 - r0, c1 - c0))
        ax, im = a['ax'], a['im']
        xlim, ylim = self._view_limits(region)
        if self.wide:                          # the whole frame: the toolbar may pan and zoom out
            v0, v1, u0, u1 = 0, shape[0], 0, shape[1]
        else:                                  # the movie's panel: only the pixels in view (5-10 x faster)
            v0, v1 = max(int(np.floor(ylim[0] + 0.5)), 0), min(int(np.ceil(ylim[1] + 0.5)), shape[0])
            u0, u1 = max(int(np.floor(xlim[0] + 0.5)), 0), min(int(np.ceil(xlim[1] + 0.5)), shape[1])
        im.set_data(img[v0:v1, u0:u1])
        im.set_extent((u0 - 0.5, u1 - 0.5, v0 - 0.5, v1 - 0.5))
        # the colour bar follows the image's 'changed' signal: change the map and norm only when they differ
        cmap = view.get('cmap')
        if cmap is not None and cmap is not im.get_cmap():
            im.set_cmap(cmap)
        key = (log, vmin, vmax)
        if a.get('norm') != key:
            im.set_norm(LogNorm(vmin=vmin, vmax=vmax) if log else Normalize(vmin=vmin, vmax=vmax))
            a['cbar'].minorticks_off()         # a log colour bar's minor ticks were most of the redraw time
            a['norm'] = key
        units = view.get('units', '')
        title = view.get('title', '')
        ax.set_title('%s\n%s' % (title, units) if units else title, fontsize='small')
        self._outlines(a['boxes'], view['boxes'], shape)
        self._outlines(a['old'], view.get('old') or [], shape)
        self._marks(view, shape)
        self._profiles(view, img, region, log)
        sums = view.get('sums')
        self.numbers.setText(display.roi_numbers_text(sums) if sums is not None else '')
        self.numbers.setToolTip(self.numbers_tip(view))
        cues = view.get('cues') or []
        level = 'stop' if any(c['level'] == 'stop' for c in cues) else 'warn' if cues else None
        self.cues.setText(display.roi_cues_text(cues) if cues else 'no cue')
        self.cues.setStyleSheet('color: %s' % CUE_COLOURS[level])
        self.cues.setToolTip('\n\n'.join(c['reason'] for c in cues) + ('\n\n' if cues else '') + CHECKS_TIP)
        self.canvas.draw_idle()

    @staticmethod
    def _outlines(patches, boxes, shape):
        for k, p in enumerate(patches):
            on = display.box_on_frame(boxes[k][1], shape) if k < len(boxes) else None
            if on is None:
                p.set_visible(False)
                continue
            p.set_bounds(on[2] - 0.5, on[0] - 0.5, on[3] - on[2], on[1] - on[0])
            p.set_visible(True)

    def _marks(self, view, shape):
        """Squares on the pixels above the count-rate limits, × on the direct beam (anywhere on the frame:
        the view may show more than the region)."""
        a = self.art
        sat = view.get('saturated')
        soft = hard = None
        if sat is not None and sat[0] is not None and np.shape(sat[0]) == tuple(shape):
            soft, hard = np.asarray(sat[0], bool) & ~np.asarray(sat[1], bool), np.asarray(sat[1], bool)
        for key, mask in (('soft', soft), ('hard', hard)):
            if mask is None:
                a[key].set_data([], [])
                continue
            rows, cols = np.nonzero(mask)
            a[key].set_data(cols, rows)
        beam = view.get('beam')
        if beam is not None and -0.5 <= beam[0] <= shape[0] - 0.5 and -0.5 <= beam[1] <= shape[1] - 0.5:
            a['beam'].set_data([beam[1]], [beam[0]])
        else:
            a['beam'].set_data([], [])

    def _profiles(self, view, img, region, log):
        a = self.art
        prof = display.roi_profiles(img, view['boxes'], region)
        sig = display.box_on_frame(view['boxes'][0][1], img.shape)
        sums = view.get('sums')
        level = None
        if sig is not None and sums is not None and len(view['boxes']) > 1:
            level = (float(sums[2]) + float(sums[4])) / 2.0 / ((sig[1] - sig[0]) * (sig[3] - sig[2]))
        scale = 'log' if log else 'linear'
        for key, axis in (('col', a['axc']), ('row', a['axr'])):
            line, lev = a['lines'][key], a['levels'][key]
            if prof is None:
                line.set_data([], [])
                lev.set_data([], [])
                continue
            x, y = (prof[0], prof[1]) if key == 'col' else (prof[2], prof[3])
            line.set_data(x, y)
            n = (sig[1] - sig[0]) if key == 'col' else (sig[3] - sig[2])
            if level is not None:
                lev.set_data([x[0] - 0.5, x[-1] + 0.5], [level * n] * 2)
            else:
                lev.set_data([], [])
            along = 'H' if key == 'col' else 'V'          # the boxes that lie along this profile
            for k, p in enumerate(a['spans'][key]):
                show = k < len(view['boxes']) and (k == 0 or (view.get('direction') == 'H') == (along == 'H'))
                on = display.box_on_frame(view['boxes'][k][1], img.shape) if show else None
                if on is None:
                    p.set_visible(False)
                    continue
                lo, hi = (on[2], on[3]) if key == 'col' else (on[0], on[1])
                p.set_bounds(lo - 0.5, 0, hi - lo, 1)
                p.set_visible(True)
            if a['yscale'] != scale:
                axis.set_yscale(scale)
                if log:                         # few ticks, plain labels: each is a line and a text to lay out
                    axis.yaxis.set_major_locator(LogLocator(numticks=4))
                    axis.yaxis.set_major_formatter(FormatStrFormatter('%.0e'))
                axis.yaxis.set_minor_locator(NullLocator())
            axis.set_xlim(x[0] - 0.5, x[-1] + 0.5)
            yy = np.asarray(y, dtype=float)
            yy = yy[np.isfinite(yy)]
            if log:
                yy = yy[yy > 0]
                if yy.size:
                    axis.set_ylim(yy.min() / 1.5, yy.max() * 1.5)
            elif yy.size:
                lo, hi = min(float(yy.min()), 0.0), float(yy.max())
                pad = 0.05 * (hi - lo) if hi > lo else 1.0
                axis.set_ylim(lo - pad, hi + pad)
        a['yscale'] = scale

    def numbers_tip(self, view):
        tip = ('The sums of the boxes outlined, as the reduction makes them (TwoDDetector.sumROI, netROI): S, the '
               'signal box ± its error; B, the two background boxes; net = S − (B1 + B2)/2 ± its error, and the '
               'error in per cent.')
        if view is not None and view.get('tip'):
            tip += ' ' + view['tip']
        return tip

    # ---- the cursor readout (R6)
    def _moved(self, event):
        v, a = self.view, self.art
        if v is None or a is None or event.inaxes is None or event.xdata is None:
            self.cursor.setText('')
            return
        img = v['image']
        if event.inaxes is a['ax']:
            col, row = int(np.floor(event.xdata + 0.5)), int(np.floor(event.ydata + 0.5))
            if 0 <= row < img.shape[0] and 0 <= col < img.shape[1]:
                self.cursor.setText('col %d, row %d: %.4g' % (col, row, img[row, col]))
                return
        for key, axis in (('col', a['axc']), ('row', a['axr'])):
            if event.inaxes is axis:
                x, y = a['lines'][key].get_data()
                if len(x):
                    k = int(np.clip(np.floor(event.xdata + 0.5) - x[0], 0, len(x) - 1))
                    self.cursor.setText('%s %d: %.4g' % ('col' if key == 'col' else 'row', x[k], y[k]))
                    return
        self.cursor.setText('')
