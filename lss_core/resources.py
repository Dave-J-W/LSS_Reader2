"""Where the program's own files (.ui layouts, icons) are.

They are found next to the program, not in the current working directory,
so the reader can be started from anywhere, and from a packaged build
(PyInstaller puts them in ``sys._MEIPASS``).
"""
import os
import sys


def program_dir():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource(name):
    return os.path.join(program_dir(), name)
