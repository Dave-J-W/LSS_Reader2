from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import Qt
from PyQt5 import QtCore
from matplotlib.backends.backend_qt5agg \
 import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class MplCanvas(FigureCanvas):
	def __init__(self):
		self.fig = Figure()
		self.ax = self.fig.add_subplot(111)
		FigureCanvas.__init__(self, self.fig)
		FigureCanvas.setSizePolicy(self, Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Expanding)
		FigureCanvas.updateGeometry(self)

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
