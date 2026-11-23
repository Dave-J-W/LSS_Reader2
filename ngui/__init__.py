"""ngui: prototype of the new layout (F82; docs/gui/prototype.md).

A second, non-functional window that sketches the proposed organisation of
the reader: tabs by workflow, one template per tab, the selection panel at
full height, panes under the tabs. It is built from ``layout.py``, a table
that places every inventoried control of today's window (or retires it with
a reason). Nothing here reads data or imports ``lss_core``; it opens when the
preference ``ngui`` is on (off by default).
"""
