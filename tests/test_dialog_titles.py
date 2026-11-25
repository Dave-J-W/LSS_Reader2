"""Every dialog has a title that says what it is (F95, owner Q-UI-B10,
2026-11-23: "phase 1b keeps modeless windows with proper titles"); before
2026-11-25 most were "Dialog" or "Scan Details"."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERIC = {'Dialog', 'Form', 'Form1', 'Scan Details', ''}


def test_every_dialog_says_what_it_is():
    titles = {}
    for f in glob.glob(os.path.join(ROOT, '*.ui')):
        if os.path.basename(f) == 'mainwindow.ui':           # the program sets its own title (LSS_Reader.create_app)
            continue
        m = re.search(r'<property name="windowTitle">\s*<string>([^<]*)</string>', open(f).read())
        titles[os.path.basename(f)] = m.group(1) if m else ''
    assert titles and not [f for f, t in titles.items() if t in GENERIC]
    assert len(set(titles.values())) == len(titles)                 # no two alike
