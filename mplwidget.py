from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import Qt
from PyQt5 import QtCore
from matplotlib.backends.backend_qt5agg \
 import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

MPL_DEFAULT_PT = 10.0      # matplotlib's own font.size: the plots' text is never made smaller than this


def plot_font_points(text_px, dpi, floor=MPL_DEFAULT_PT):
	"""The base font size (pt) at which matplotlib's 'medium' text (tick
	labels, axis labels, legends) is ``text_px`` logical pixels high on a
	figure of ``dpi``: pt = px x 72 / dpi, and never below ``floor``. A
	figure of ``dpi`` shown at w logical pixels is w/dpi inches wide, so a
	font of p pt is p/72 x dpi logical pixels."""
	return max(float(floor), float(text_px) * 72.0 / float(dpi))


def match_plot_fonts():
	"""Owner, 2026-11-26: "axes scales and labeling ... at least as large as
	the tab label font size". Sets matplotlib's base font size (rcParams
	font.size) so that tick labels and axis labels are at least as tall as
	the tab labels' text (QApplication.font('QTabBar') at the screen's
	logical DPI), for the figures made afterwards (call it before they are
	built). The tab font follows the system's display scaling and the
	figures' DPI (rcParams figure.dpi, 100 by default) does not, so at 125 or
	150 % scaling matplotlib's 10 pt was smaller than the tabs. Returns the
	size set (pt)."""
	import matplotlib
	from PyQt5.QtGui import QFontInfo
	app = QtWidgets.QApplication.instance()
	if app is None:
		return matplotlib.rcParams['font.size']
	px = QFontInfo(QtWidgets.QApplication.font('QTabBar')).pixelSize()
	pt = round(plot_font_points(px, matplotlib.rcParams['figure.dpi']), 1)
	matplotlib.rcParams['font.size'] = pt
	return pt


# F112 (owner, 2026-11-26): "a plot preferences button that applies to the plots on that tab that has
# useful options, like font size, minor/major ticks, grid on/off". Every option's default is 'as drawn':
# the plot as the reader draws it; a choice is applied to every axes of the tab's figures at each draw.
AS_DRAWN = 'as drawn'
PLOT_OPTION_DEFAULTS = dict(font=0, major=AS_DRAWN, minor=AS_DRAWN, direction=AS_DRAWN, mirror=AS_DRAWN, grid=AS_DRAWN)
PLOT_OPTION_CHOICES = dict(
	major=[AS_DRAWN, 3, 5, 8, 12],                  # about this many labelled ticks (linear axes)
	minor=[AS_DRAWN, 'on', 'off'],
	direction=[AS_DRAWN, 'out', 'in', 'in and out'],
	mirror=[AS_DRAWN, 'on', 'off'],                 # ticks on all four sides
	grid=[AS_DRAWN, 'off', 'major', 'major and minor'])


def plot_options_set(opts):
	"""Whether ``opts`` asks for anything (all 'as drawn' and font 0: nothing)."""
	return bool(opts) and any(opts.get(k, v) != v for k, v in PLOT_OPTION_DEFAULTS.items())


def apply_plot_options(fig, opts):
	"""Apply a tab's plot options (F112) to every visible axes of ``fig``:
	font size (tick labels, axis labels, legend; titles 1.2 x), about how
	many major ticks (linear axes), minor ticks, tick direction, ticks on
	all four sides, grid. Colour bars take the font size only; insets
	(``ax._lss_inset``: the residual strips) are left as drawn."""
	from matplotlib.ticker import MaxNLocator
	opts = dict(PLOT_OPTION_DEFAULTS, **(opts or {}))
	fs = float(opts.get('font') or 0)
	if fs and getattr(fig, '_suptitle', None) is not None:
		fig._suptitle.set_fontsize(1.25 * fs)
	for ax in fig.axes:
		if not ax.axison or getattr(ax, '_lss_inset', False):
			continue
		if fs:
			ax.tick_params(which='both', labelsize=fs)
			ax.xaxis.label.set_fontsize(fs)
			ax.yaxis.label.set_fontsize(fs)
			for t in (ax.title, ax._left_title, ax._right_title):
				t.set_fontsize(1.2 * fs)
			leg = ax.get_legend()
			if leg is not None:
				for t in leg.get_texts():
					t.set_fontsize(fs)
		if getattr(ax, '_colorbar', None) is not None:
			continue
		if opts['major'] != AS_DRAWN:
			for axis in (ax.xaxis, ax.yaxis):
				if axis.get_scale() == 'linear':
					axis.set_major_locator(MaxNLocator(nbins=int(opts['major'])))
		if opts['minor'] == 'on' or opts['grid'] == 'major and minor':
			ax.minorticks_on()
		elif opts['minor'] == 'off':
			ax.minorticks_off()
		if opts['direction'] != AS_DRAWN:
			ax.tick_params(which='both', direction={'in and out': 'inout'}.get(opts['direction'], opts['direction']))
		if opts['mirror'] != AS_DRAWN:
			on = opts['mirror'] == 'on'
			ax.tick_params(which='both', top=on, right=on)
		if opts['grid'] == 'off':
			ax.grid(False, which='both')
		elif opts['grid'] == 'major':
			ax.grid(False, which='minor')
			ax.grid(True, which='major')
		elif opts['grid'] == 'major and minor':
			ax.grid(True, which='major')
			ax.grid(True, which='minor', alpha=0.35, lw=0.5)


def reset_plot_options(fig):
	"""Undo what ``apply_plot_options`` set that ``Axes.clear()`` keeps (tick
	label size, direction, top and right ticks; matplotlib keeps them in the
	axis's tick parameters): back to matplotlib's defaults, before a tab
	whose options changed is redrawn. Insets are left alone."""
	import matplotlib
	rc = matplotlib.rcParams
	for ax in fig.axes:
		if getattr(ax, '_lss_inset', False):
			continue
		ax.tick_params(axis='x', which='both', labelsize=rc['xtick.labelsize'], direction=rc['xtick.direction'],
		               top=rc['xtick.top'])
		ax.tick_params(axis='y', which='both', labelsize=rc['ytick.labelsize'], direction=rc['ytick.direction'],
		               right=rc['ytick.right'])
		ax.xaxis.label.set_fontsize(rc['axes.labelsize'])
		ax.yaxis.label.set_fontsize(rc['axes.labelsize'])


class MplCanvas(FigureCanvas):
	"""A figure with one axes (``ax``). ``plot_options``: a callable giving
	the options of the tab it sits on (F112, set by the window), applied
	at every draw so that a redrawn plot keeps them."""
	def __init__(self):
		self.fig = Figure()
		self.ax = self.fig.add_subplot(111)
		self.plot_options = None
		FigureCanvas.__init__(self, self.fig)
		FigureCanvas.setSizePolicy(self, Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Expanding)
		FigureCanvas.updateGeometry(self)

	def draw(self):
		get = getattr(self, 'plot_options', None)
		if callable(get):
			try:
				opts = get()
				if plot_options_set(opts):
					apply_plot_options(self.figure, opts)
			except Exception:                    # a style must never stop a plot: logged, drawn as it is
				import logging
				logging.getLogger('lss_reader').exception('plot options not applied')
		FigureCanvas.draw(self)

class MplWidget(QtWidgets.QWidget):
	def __init__(self, parent = None):
		QtWidgets.QWidget.__init__(self, parent)
		self.canvas = MplCanvas()
		self.toolbar = NavigationToolbar(self.canvas, parent)
		self.vbl = QtWidgets.QVBoxLayout()
		self.vbl.addWidget(self.canvas)
		self.vbl.addWidget(self.toolbar)
		self.setLayout(self.vbl)



def errorbars(ax, x, y, yerr, fmt='o-', label=None):
	"""``ax.errorbar``'s picture, drawn fast: the data as one line, and all
	its error bars as one second line with a break (NaN) between bars,
	where errorbar makes one path per bar. The bars are the same (same
	colour, width, ends y - yerr and y + yerr, just under the data); a log
	axis then transforms two paths instead of one per point, and the plot
	is built without a path object per point. Measured 2026-11-23, 100
	spectra of 2048 channels, log y: built 2.0 -> 0.07 s, redrawn (pan,
	zoom, resize) 2.4 -> 1.0 s. The legend shows the data line, without
	errorbar's bar glyph. Returns (data line, bar line)."""
	x = np.asarray(x, dtype=float)
	y = np.asarray(y, dtype=float)
	e = np.asarray(yerr, dtype=float) * np.ones_like(y)
	line, = ax.plot(x, y, fmt, label=label)
	bx = np.empty(3 * len(x))
	by = np.empty(3 * len(x))
	bx[0::3], bx[1::3], bx[2::3] = x, x, np.nan
	by[0::3], by[1::3], by[2::3] = y - e, y + e, np.nan
	bars, = ax.plot(bx, by, '-', color=line.get_color(), linewidth=line.get_linewidth(),
	                zorder=line.get_zorder() - 0.1, label='_nolegend_')
	return line, bars


def mesh(ax, X, Y, C, **kw):
	"""``ax.pcolor``'s map, drawn as one mesh (``pcolormesh``) instead of
	one polygon per cell: the same cells, colours and shading; 5-7 x faster
	(2026-11-23, 500 x 500 cells: built and drawn 1.04 -> 0.14 s, redrawn
	0.52 -> 0.09 s). Where cells are smaller than a screen pixel the two
	may show a neighbouring cell's colour in a pixel (sampling, not data).
	pcolormesh refuses non-finite coordinates, which pcolor skips: then
	pcolor is used."""
	X, Y = np.asarray(X, dtype=float), np.asarray(Y, dtype=float)
	if np.all(np.isfinite(X)) and np.all(np.isfinite(Y)):
		return ax.pcolormesh(X, Y, C, **kw)
	return ax.pcolor(X, Y, C, **kw)
