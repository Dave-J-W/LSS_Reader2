"""Write ngui/inventory_text.py: the inventory's text for the prototype window.

    python tests/tools/ngui_inventory.py           # rewrite the module
    python tests/tools/ngui_inventory.py --check   # exit 1 if it is out of date

The prototype of the new layout (docs/gui/prototype.md, ngui/) shows,
in each placeholder's tooltip, where the control lives today and what it
does. That text is in docs/gui/inventory/*.yaml, which the packaged program
does not ship (and PyYAML is not a run-time dependency), so it is copied
into a plain Python module here. The items of combo boxes defined in the
.ui files are copied too. tests/test_ngui.py fails when the module is
out of date with the YAML.
"""
import glob
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'ngui', 'inventory_text.py')

HEADER = '''"""The inventory's text for the prototype window (generated; do not edit).

Made by tests/tools/ngui_inventory.py from docs/gui/inventory/*.yaml
and the .ui files. INVENTORY: id -> (kind, label, where, does), in
inventory order. COMBO_ITEMS: id -> the items a .ui file gives the combo box.
"""
'''


def ui_combo_items():
    """{inventory-style id: [items]} for every combo box with items in a .ui file."""
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, '*.ui'))):
        stem = os.path.splitext(os.path.basename(path))[0]
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        for w in tree.iter('widget'):
            if w.get('class') != 'QComboBox':
                continue
            items = []
            for it in w.findall('item'):
                s = it.find("property[@name='text']/string")
                items.append(s.text or '' if s is not None else '')
            if items:
                name = w.get('name')
                out[name if stem == 'mainwindow' else '%s.%s' % (stem, name)] = items
    return out


def render():
    import yaml
    entries = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'docs', 'gui', 'inventory', '*.yaml'))):
        with open(path, encoding='utf-8') as f:
            for e in yaml.safe_load(f) or []:
                entries.append(e)
    combos = ui_combo_items()
    lines = [HEADER, 'INVENTORY = {']
    seen = set()
    for e in entries:
        cid = str(e['id'])
        if cid in seen:
            continue
        seen.add(cid)
        vals = tuple(' '.join(str(e.get(k) or '').split()) for k in ('kind', 'label', 'where', 'does'))
        lines.append('    %r: (%r, %r, %r, %r),' % ((cid,) + vals))
    lines.append('}')
    lines.append('')
    lines.append('COMBO_ITEMS = {')
    for cid in sorted(combos):
        if cid in seen:
            lines.append('    %r: %r,' % (cid, combos[cid]))
    lines.append('}')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    text = render()
    if '--check' in argv:
        try:
            with open(OUT, encoding='utf-8') as f:
                same = f.read() == text
        except OSError:
            same = False
        print('ngui/inventory_text.py is %s' % ('up to date' if same else 'OUT OF DATE: rerun this tool'))
        return 0 if same else 1
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(text)
    print('wrote %s (%d bytes)' % (os.path.relpath(OUT, ROOT), len(text)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
