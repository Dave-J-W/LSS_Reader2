"""The Tools menu: built from the catalogue, so a new item appears in the
menu, in the window and in docs/TOOLS.md at once.

``install(main_window, spec_file=..., open_spec=..., notify=...)`` adds a
Tools menu before Help (or at the end of the menu bar): "All tools…" opens
the Tools window at its overview; then one submenu per category with one
action per item, each opening the window at that item's page. The window is
made when first asked for and kept (one per main window).
"""
from PyQt5 import QtWidgets

from . import catalog


def fill(menu, open_item):
    """Add "All tools…" and the category submenus to ``menu``; each action
    calls ``open_item(item_id)`` (None for the overview). Returns
    {item id or 'all': QAction}."""
    actions = {}
    act = menu.addAction('All tools…')
    act.setObjectName('actionToolsWindow')
    act.setToolTip('Every demonstration and figure generator of the repository, run from its current code '
                   '(docs/TOOLS.md)')
    act.setStatusTip(act.toolTip())
    act.triggered.connect(lambda _=False: open_item(None))
    actions['all'] = act
    menu.addSeparator()
    for cat, name in catalog.CATEGORIES:
        members = catalog.in_category(cat)
        if not members:
            continue
        sub = menu.addMenu(name)
        sub.setObjectName('menuTools_' + cat)
        sub.setToolTipsVisible(True)
        for t in members:
            a = sub.addAction(t.title + ('…' if t.kind != 'external' else ''))
            a.setObjectName('actionTool_' + t.id)
            a.setToolTip(t.demonstrates)
            a.setStatusTip(t.demonstrates)
            a.triggered.connect(lambda _=False, i=t.id: open_item(i))
            actions[t.id] = a
    menu.setToolTipsVisible(True)
    return actions


def install(main_window, spec_file=None, open_spec=None, notify=None, before=None):
    """Add the Tools menu to ``main_window``'s menu bar (before the menu
    ``before``, default the one titled Help). Returns the QMenu; the window,
    once opened, is ``main_window.toolsWindow``."""
    from . import window as tw
    bar = main_window.menuBar()
    menu = QtWidgets.QMenu('Tools', bar)
    menu.setObjectName('menuTools')
    host = tw.Host(spec_file=spec_file, open_spec=open_spec, notify=notify)
    main_window.toolsWindow = None

    def open_item(item_id):
        if main_window.toolsWindow is None:
            main_window.toolsWindow = tw.ToolsWindow(main_window, host)
            main_window.toolsWindow.resize(1400, 900)
        w = main_window.toolsWindow
        w.show_item(item_id)
        w.show()
        w.raise_()
        w.activateWindow()
        return w

    menu.toolActions = fill(menu, open_item)
    menu.openItem = open_item
    if before is None:
        before = next((m for m in bar.findChildren(QtWidgets.QMenu)
                       if m.title().replace('&', '') == 'Help' and m.parent() is bar), None)
    if before is not None:
        bar.insertMenu(before.menuAction(), menu)
    else:
        bar.addMenu(menu)
    return menu
