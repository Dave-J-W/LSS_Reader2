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
PLOT_OPTION_DEFAULTS = dict(font=0, major=AS_DRAWN, minor=AS_DRAWN, direction=AS_DRAWN, mirror=AS_DRAWN, grid=AS_DRAWN,
                            index=True,        # F113: the point index numbers shown (crowded ones hidden)
                            # F114 (owner, 2026-11-27: "the comprehensive solution for plot customization"):
                            ticknum=AS_DRAWN, legend=AS_DRAWN, legend_loc='best', legend_frame=AS_DRAWN,
                            linewidth=0.0, markersize=0.0, titles=AS_DRAWN,
                            plots={})          # per plot (plot_id): labels renamed, fixed ranges, curve styles
PLOT_OPTION_CHOICES = dict(
	major=[AS_DRAWN, 3, 5, 8, 12],                  # about this many labelled ticks (linear axes)
	minor=[AS_DRAWN, 'on', 'off'],
	direction=[AS_DRAWN, 'out', 'in', 'in and out'],
	mirror=[AS_DRAWN, 'on', 'off'],                 # ticks on all four sides
	grid=[AS_DRAWN, 'off', 'major', 'major and minor'],
	ticknum=[AS_DRAWN, 'plain', 'scientific'],       # the tick numbers of linear axes
	legend=[AS_DRAWN, 'shown', 'hidden'],
	legend_loc=['best', 'upper right', 'upper left', 'lower left', 'lower right', 'right', 'center left',
	            'center right', 'lower center', 'upper center', 'center'],
	legend_frame=[AS_DRAWN, 'on', 'off'],
	titles=[AS_DRAWN, 'hidden'])
# a curve's style (F114): (shown, matplotlib's value)
CURVE_COLOURS = [(AS_DRAWN, AS_DRAWN), ('black', 'black'), ('blue', 'tab:blue'), ('orange', 'tab:orange'),
                 ('green', 'tab:green'), ('red', 'tab:red'), ('purple', 'tab:purple'), ('brown', 'tab:brown'),
                 ('pink', 'tab:pink'), ('grey', 'tab:gray'), ('olive', 'tab:olive'), ('cyan', 'tab:cyan')]
CURVE_LINES = [(AS_DRAWN, AS_DRAWN), ('solid', '-'), ('dashed', '--'), ('dotted', ':'), ('dash-dot', '-.'),
               ('none', 'None')]
CURVE_MARKERS = [(AS_DRAWN, AS_DRAWN), ('none', 'None'), ('circle', 'o'), ('square', 's'), ('triangle', '^'),
                 ('diamond', 'D'), ('plus', '+'), ('cross', 'x'), ('point', '.')]
CURVE_FIELDS = ('color', 'linestyle', 'linewidth', 'marker', 'markersize')


def curve_rule_set(rule):
	"""Whether a curve rule changes anything."""
	return any(rule.get(k, AS_DRAWN) not in (AS_DRAWN, 0, 0.0, None, '') for k in CURVE_FIELDS)


def plot_entry_set(p):
	"""Whether a plot's entry changes anything."""
	return bool(p) and bool({k: v for k, v in (p.get('labels') or {}).items() if v} or p.get('xlim') or p.get('ylim')
	                        or any(curve_rule_set(r) for r in p.get('curves') or []))


def plot_options_set(opts):
	"""Whether ``opts`` asks for anything (all 'as drawn', font 0, no plot entries: nothing)."""
	if not opts:
		return False
	if any(plot_entry_set(p) for p in (opts.get('plots') or {}).values()):
		return True
	return any(opts.get(k, v) != v for k, v in PLOT_OPTION_DEFAULTS.items() if k != 'plots')


def main_axes(fig):
	"""The plots of a figure: its drawn axes but colour bars and insets (the residual strips)."""
	return [ax for ax in fig.axes if ax.axison and not getattr(ax, '_lss_inset', False)
	        and getattr(ax, '_colorbar', None) is None]


def plot_id(name, k):
	"""A plot's key in the options: its canvas's name and its place among the figure's plots."""
	return '%s:%d' % (name or 'plot', int(k))


def data_curves(ax):
	"""The curves of a plot that a style can apply to, in drawing order: its
	lines in data coordinates, but error-bar caps and companion bar lines,
	reference lines (axhline, axvline: not in data coordinates) and zero
	lines. Returns (curve, its name: the legend label, or '' for none)."""
	caps, named = set(), {}
	for c in ax.containers:
		parts = getattr(c, 'lines', None) or ()
		for part in parts[1:2]:
			caps.update(id(x) for x in (part or ()))
		if parts and parts[0] is not None:          # errorbar: the name is the container's, not the line's
			named[id(parts[0])] = str(c.get_label() or '')
	out = []
	for l in ax.lines:
		if (id(l) in caps or getattr(l, '_lss_bar_of', None) is not None or getattr(l, '_lss_zero', False)
		        or l.get_transform() != ax.transData):
			continue
		lab = named.get(id(l)) or str(l.get_label() or '')
		out.append((l, '' if lab.startswith('_') else lab))
	return out


def _companions(ax):
	"""id(data line) -> the artists drawn in its colour: its error bars and caps."""
	out = {}
	for c in ax.containers:
		parts = getattr(c, 'lines', None)
		if parts and len(parts) == 3 and parts[0] is not None:
			out.setdefault(id(parts[0]), []).extend(list(parts[1] or ()) + list(parts[2] or ()))
	for l in ax.lines:
		of = getattr(l, '_lss_bar_of', None)
		if of is not None:
			out.setdefault(id(of), []).append(l)
	return out


def drawn_text(t):
	"""The text the reader drew in ``t`` (a title or axis label), before a rename."""
	cur = t.get_text()
	if getattr(t, '_lss_orig', None) is not None and cur == getattr(t, '_lss_set', None):
		return t._lss_orig
	return cur


def _fresh(ax):
	"""Whether ``ax`` was cleared (or made) since the last draw: fixed ranges
	are applied then only, so that zooming and panning still work."""
	if not getattr(ax, '_lss_clear_wrapped', False):
		for name in ('clear', 'cla'):
			orig = getattr(ax, name)

			def wrapped(*a, _orig=orig, **k):
				r = _orig(*a, **k)
				ax._lss_fresh = True
				return r
			setattr(ax, name, wrapped)
		ax._lss_clear_wrapped = True
		ax._lss_fresh = True
	fresh = getattr(ax, '_lss_fresh', True)
	ax._lss_fresh = False
	return fresh


def _style_curve(line, rule, companions, tabwide):
	"""Apply a tab's line width and marker size, then a curve rule, to one curve."""
	lw = float(tabwide.get('linewidth') or 0)
	ms = float(tabwide.get('markersize') or 0)
	rule = rule or {}
	if rule.get('linewidth') not in (None, 0, 0.0, AS_DRAWN):
		lw = float(rule['linewidth'])
	if rule.get('markersize') not in (None, 0, 0.0, AS_DRAWN):
		ms = float(rule['markersize'])
	if lw:
		line.set_linewidth(lw)
		for a in companions:
			a.set_linewidth(lw)
	if ms:
		line.set_markersize(ms)
	col = rule.get('color', AS_DRAWN)
	if col not in (None, '', AS_DRAWN):
		line.set_color(col)
		line.set_markeredgecolor(col)
		mfc = line.get_markerfacecolor()
		if not (isinstance(mfc, str) and mfc.lower() == 'none'):
			line.set_markerfacecolor(col)
		for a in companions:
			a.set_color(col)
	ls = rule.get('linestyle', AS_DRAWN)
	if ls not in (None, '', AS_DRAWN):
		line.set_linestyle(ls)
	mk = rule.get('marker', AS_DRAWN)
	if mk not in (None, '', AS_DRAWN):
		line.set_marker(mk)


def _rule_for(rules, pos, name):
	"""The rule of the curve at ``pos`` (from 1) named ``name``: by name first, else by position."""
	if name:
		for r in rules:
			if r.get('match') == 'name' and r.get('key') == name:
				return r
	for r in rules:
		if r.get('match') == 'position' and int(r.get('key', 0) or 0) == pos:
			return r
	return None


def _apply_plot(ax, p, tabwide):
	"""One plot's entry (F114): renamed titles and axis labels, fixed ranges
	(when the plot was redrawn), the curves' styles."""
	p = p or {}
	names = {k: v for k, v in (p.get('labels') or {}).items() if v}
	for t in (ax.title, ax.xaxis.label, ax.yaxis.label):
		base = drawn_text(t)
		if base in names:
			t._lss_orig, t._lss_set = base, names[base]
			t.set_text(names[base])
		elif getattr(t, '_lss_orig', None) is not None and t.get_text() == getattr(t, '_lss_set', None):
			t.set_text(t._lss_orig)                     # a rename taken back
			t._lss_orig = t._lss_set = None
	if _fresh(ax):
		for key, setter in (('xlim', ax.set_xlim), ('ylim', ax.set_ylim)):
			lim = p.get(key)
			if lim and len(lim) == 2 and lim[0] != lim[1]:
				setter(float(lim[0]), float(lim[1]))
	rules = [r for r in (p.get('curves') or []) if curve_rule_set(r)]
	lw, ms = float(tabwide.get('linewidth') or 0), float(tabwide.get('markersize') or 0)
	if not (rules or lw or ms):
		return False
	comp = _companions(ax)
	for pos, (line, name) in enumerate(data_curves(ax), 1):
		_style_curve(line, _rule_for(rules, pos, name), comp.get(id(line), []), tabwide)
	return True


def apply_plot_options(fig, opts, name=None):
	"""Apply a tab's plot options (F112, F114) to the axes of ``fig`` (the
	canvas ``name``, for its plots' entries): font size (tick labels, axis
	labels, legend; titles 1.2 x), tick numbers, about how many major ticks
	(linear axes), minor ticks, tick direction, ticks on all four sides,
	grid; titles; then each plot's entry (renamed labels, fixed ranges,
	curve styles with the tab's line width and marker size); then the
	legend. Colour bars take the font size only; insets (``ax._lss_inset``:
	the residual strips) are left as drawn."""
	from matplotlib.ticker import MaxNLocator
	opts = dict(PLOT_OPTION_DEFAULTS, **(opts or {}))
	plots = opts.get('plots') or {}
	for k, ax in enumerate(main_axes(fig)):
		styled = _apply_plot(ax, plots.get(plot_id(name, k)), opts)
		if opts['titles'] == 'hidden':
			ax.title.set_visible(False)
		if opts['ticknum'] != AS_DRAWN:
			for which in ('x', 'y'):
				if getattr(ax, which + 'axis').get_scale() != 'linear':
					continue
				try:
					if opts['ticknum'] == 'scientific':
						ax.ticklabel_format(axis=which, style='sci', scilimits=(0, 0), useMathText=True)
					else:
						ax.ticklabel_format(axis=which, style='plain', useOffset=False)
				except (AttributeError, ValueError):
					pass                    # not a ScalarFormatter (a date or custom axis)
		_apply_legend(ax, opts, styled)
	if opts['titles'] == 'hidden' and getattr(fig, '_suptitle', None) is not None:
		fig._suptitle.set_visible(False)
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


def _apply_legend(ax, opts, styled):
	"""The legend option (F114), and the legend's swatches brought in line
	with the curves' styles (``styled``)."""
	leg = ax.get_legend()
	want = opts.get('legend', AS_DRAWN)
	if want == 'hidden':
		if leg is not None:
			leg.set_visible(False)
		return
	if want == 'shown':
		if leg is None:
			if not any(n for _l, n in data_curves(ax)):
				return
			leg = ax.legend(loc=opts.get('legend_loc') or 'best')
		else:
			leg.set_visible(True)
			try:
				leg.set_loc(opts.get('legend_loc') or 'best')
			except (AttributeError, ValueError):
				pass
	if leg is None:
		return
	if opts.get('legend_frame', AS_DRAWN) != AS_DRAWN:
		leg.set_frame_on(opts['legend_frame'] == 'on')
	if styled:
		curves = {n: l for l, n in data_curves(ax) if n}
		for h, t in zip(getattr(leg, 'legend_handles', getattr(leg, 'legendHandles', [])), leg.get_texts()):
			src = curves.get(t.get_text())
			if src is not None and hasattr(h, 'update_from'):
				try:
					h.update_from(src)
				except (AttributeError, TypeError, ValueError):
					pass


# ---- F113 (owner, 2026-11-26): the point index numbers on the plots ----
# "spacing better, a checkbox to disable in plot prefs, autohide them when they overlap, autounhide on
# zoom to non-overlap condition"

INDEX_SCALE = 0.85          # the numbers' size, a fraction of the plots' base font (F111)
INDEX_OFFSET_PT = 4.0       # their distance from the marker, in points: the same at any zoom and on log axes


def index_labels(ax, x, y, labels, color='r', where='upper right'):
	"""Label the points (x, y) of ``ax`` with ``labels`` (their index
	numbers): each a few points from its marker (``where``: 'upper right'
	or 'lower left' of it), at INDEX_SCALE of the base font, with a thin
	white halo, and tagged for ``declutter_index_labels``, which hides
	those that would overlap at each draw. Points that are not finite get
	no label. Returns the labels."""
	import matplotlib
	from matplotlib import patheffects
	right = where == 'upper right'
	off = (INDEX_OFFSET_PT, INDEX_OFFSET_PT) if right else (-INDEX_OFFSET_PT, -INDEX_OFFSET_PT)
	size = INDEX_SCALE * float(matplotlib.rcParams['font.size'])
	halo = [patheffects.withStroke(linewidth=2.2, foreground='white')]
	out = []
	for xi, yi, s in zip(np.asarray(x, dtype=float), np.asarray(y, dtype=float), labels):
		if not (np.isfinite(xi) and np.isfinite(yi)):
			continue
		t = ax.annotate(str(s), (xi, yi), xytext=off, textcoords='offset points', color=color, fontsize=size,
		                ha='left' if right else 'right', va='bottom' if right else 'top', annotation_clip=True,
		                path_effects=halo)
		t._lss_index = True
		out.append(t)
	return out


def _corners(t):
	"""The placements tried for label ``t``, its own first: (offset x, offset
	y in points, ha, va) at its marker's four diagonal corners."""
	pref = getattr(t, '_lss_pref', None)
	if pref is None:
		ox, oy = (float(v) for v in t.xyann)
		pref = t._lss_pref = (ox, oy, t.get_horizontalalignment(), t.get_verticalalignment())
	ox, oy = abs(pref[0]), abs(pref[1])
	right, up = pref[0] >= 0, pref[1] >= 0
	out = []
	for r, u in ((right, up), (not right, up), (right, not up), (not right, not up)):
		out.append((ox if r else -ox, oy if u else -oy, 'left' if r else 'right', 'bottom' if u else 'top'))
	return out


def _box(px, py, place, size_px, n, k):
	"""Display-space box (x0, y0, x1, y1) of a label of ``n`` characters at
	pixel (px, py) placed by ``place`` (``_corners``): from an estimate of
	its size (digits are about 0.6 em wide), so thousands cost little."""
	ox, oy, ha, va = place
	w, h = 0.62 * size_px * max(n, 1) + 0.25 * size_px, 1.05 * size_px
	x0 = px + ox * k - (w if ha == 'right' else 0.0)
	y0 = py + oy * k - (h if va == 'top' else 0.0)
	return x0, y0, x0 + w, y0 + h


def _index_boxes(ax, texts, dpi):
	"""The boxes of ``texts`` as placed now (rows NaN for a point that
	cannot be drawn): for tests and checks."""
	ax.get_xlim(), ax.get_ylim()
	k = dpi / 72.0
	with np.errstate(all='ignore'):
		pts = ax.transData.transform(np.array([t.xy for t in texts], dtype=float)) if texts else np.zeros((0, 2))
	out = np.full((len(texts), 4), np.nan)
	for i, t in enumerate(texts):
		if np.all(np.isfinite(pts[i])):
			place = (float(t.xyann[0]), float(t.xyann[1]), t.get_horizontalalignment(), t.get_verticalalignment())
			out[i] = _box(pts[i, 0], pts[i, 1], place, float(t.get_fontsize()) * k, len(t.get_text()), k)
	return out


def declutter_index_labels(fig, show=True):
	"""F113: in every axes of ``fig``, the index labels (``index_labels``)
	that fit are shown and the others hidden. Each label goes at the first
	of its marker's four corners (its own first, ``_corners``) where it is
	inside the axes (not over the frame or the tick labels) and overlaps
	no label already placed, the labels taken in the order they were drawn
	(a crowded series shows an even subset: 0, 3, 6, ...); it is hidden
	when no corner fits or its point is out of view. Run at every draw, so
	zooming in to where they no longer overlap shows them again. ``show``
	False hides them all (the Plot options' "Index numbers" unticked)."""
	k = fig.dpi / 72.0
	for ax in fig.axes:
		texts = [t for t in ax.texts if getattr(t, '_lss_index', False)]
		if not texts:
			continue
		if not show:
			for t in texts:
				t.set_visible(False)
			continue
		ax.get_xlim(), ax.get_ylim()         # autoscaled limits are applied lazily: bring them up to date first
		bb = ax.bbox
		with np.errstate(all='ignore'):
			pts = ax.transData.transform(np.array([t.xy for t in texts], dtype=float))
		sizes = [float(t.get_fontsize()) * k for t in texts]
		cell = max(max(sizes) * 2.0, 1.0)
		placed, grid = [], {}

		def free(b):
			cx0, cx1, cy0, cy1 = int(b[0] // cell), int(b[2] // cell), int(b[1] // cell), int(b[3] // cell)
			for gx in range(cx0 - 1, cx1 + 2):
				for gy in range(cy0 - 1, cy1 + 2):
					for j in grid.get((gx, gy), ()):
						a = placed[j]
						if b[0] < a[2] and a[0] < b[2] and b[1] < a[3] and a[1] < b[3]:
							return False
			return True
		for i, t in enumerate(texts):
			px, py = pts[i]
			chosen = None
			if (np.isfinite(px) and np.isfinite(py) and bb.x0 - 0.5 <= px <= bb.x1 + 0.5
			        and bb.y0 - 0.5 <= py <= bb.y1 + 0.5):
				for place in _corners(t):
					b = _box(px, py, place, sizes[i], len(t.get_text()), k)
					if (b[0] >= bb.x0 - 1 and b[2] <= bb.x1 + 1 and b[1] >= bb.y0 - 1 and b[3] <= bb.y1 + 1
					        and free(b)):
						chosen = (place, b)
						break
			if chosen is None:
				t.set_visible(False)
				continue
			(ox, oy, ha, va), b = chosen
			t.xyann = (ox, oy)
			t.set_horizontalalignment(ha)
			t.set_verticalalignment(va)
			t.set_visible(True)
			placed.append(b)
			n = len(placed) - 1
			for gx in range(int(b[0] // cell), int(b[2] // cell) + 1):
				for gy in range(int(b[1] // cell), int(b[3] // cell) + 1):
					grid.setdefault((gx, gy), []).append(n)


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
		ax.title.set_visible(True)                    # F114: titles hidden, renamed labels, the legend
		for t in (ax.title, ax.xaxis.label, ax.yaxis.label):
			if getattr(t, '_lss_orig', None) is not None and t.get_text() == getattr(t, '_lss_set', None):
				t.set_text(t._lss_orig)
			t._lss_orig = t._lss_set = None
		if ax.get_legend() is not None:
			ax.get_legend().set_visible(True)
		ax._lss_fresh = True                          # fixed ranges: applied at the next draw
	if getattr(fig, '_suptitle', None) is not None:
		fig._suptitle.set_visible(True)


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

	def plot_name(self):
		"""This canvas's name in the plots' keys (its widget's object name)."""
		p = self.parent()
		return (p.objectName() if p is not None else '') or self.objectName() or 'plot'

	def draw(self):
		get = getattr(self, 'plot_options', None)
		opts = None
		try:
			if callable(get):
				opts = get()
				if opts is not None or any(getattr(t, '_lss_orig', None) is not None for ax in self.figure.axes
				                           for t in (ax.title, ax.xaxis.label, ax.yaxis.label)):
					# every step is a no-op when unset; run so that a rename taken back is restored too
					apply_plot_options(self.figure, opts or {}, self.plot_name())
			# F113: the index numbers that fit at this zoom, every draw (any canvas, the Ref Patch window's too)
			declutter_index_labels(self.figure, show=(opts or {}).get('index', True))
		except Exception:                        # a style must never stop a plot: logged, drawn as it is
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
	bars._lss_bar_of = line          # F114: a curve's style recolours its bars too
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
