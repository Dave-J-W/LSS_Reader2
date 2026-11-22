# -*- mode: python ; coding: utf-8 -*-
# PyInstaller recipe for LSS-Reader (F46). Build from the repository root:
#     pyinstaller packaging/lss_reader.spec
# Result: dist/LSS_Reader/ (Windows, Linux) or dist/LSS_Reader.app (macOS).
# Check it:  dist/LSS_Reader/LSS_Reader --self-test <SPEC file> <reference prefix>
# (docs/PACKAGING.md). Paths are relative to this file; nothing is machine-specific.
import glob
import os
import sys

ROOT = os.path.dirname(SPECPATH)          # SPECPATH: the folder holding this file

# the window's own files, found next to the program at run time (lss_core/resources.py)
datas = [(p, '.') for p in sorted(glob.glob(os.path.join(ROOT, '*.ui')))]
datas += [(os.path.join(ROOT, name), '.') for name in ('logo.png', 'stop.png', 'arrow_up.png', 'arrow_down.png')]

# .ui files name their custom widgets by module; uic imports them at run time
hidden = ['mplwidget', 'mpl2dwidget', 'matplotlib.backends.backend_qt5agg']
# Tools menu (lss_tools, docs/TOOLS.md): the demonstrations run inside the program, so the
# demonstrator and the synthetic-data modules it uses (tests/demonstrator, tests/synthetic) are
# bundled; lss_tools.gui imports them by name. The figure generators and checks are not bundled:
# they run as Python processes and write the repository's documentation, so a build shows them
# disabled (they need a source checkout).
hidden += ['lss_tools.gui', 'lss_tools.registry', 'demonstrator.window']

a = Analysis([os.path.join(ROOT, 'LSS_Reader.py')],
             pathex=[ROOT, os.path.join(ROOT, 'tests')],
             datas=datas,
             hiddenimports=hidden,
             excludes=['tkinter', 'PyQt6', 'PySide2', 'PySide6', 'IPython', 'pytest'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [],
          exclude_binaries=True,
          name='LSS_Reader',
          icon=os.path.join(ROOT, 'logo.png') if sys.platform == 'darwin' else None,
          console=sys.platform.startswith('linux'),   # Windows/macOS: no console window
          upx=False)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='LSS_Reader')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='LSS_Reader.app', bundle_identifier='edu.uchicago.chemmatcars.lssreader')
