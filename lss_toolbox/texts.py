"""Labels and tooltips of the Tools window, in one place: the window uses
them and ``render`` lists them in docs/TOOLS.md, so the page describing the
controls is made from the same strings (rules 9 and 11 of AGENTS.md: short
labels, the why in tooltips, a trail for the manual)."""

CONTROLS = (
    # (attribute of ToolPage or ToolsWindow, label, tooltip)
    ('tree', 'Items', 'Every demonstration and figure generator of the repository, by menu. The same list is the '
                      "reader's Tools menu and docs/TOOLS.md (lss_toolbox/catalog.py)."),
    ('variationCombo', 'Settings', 'Defaults, or a variation the documents describe ("change this parameter and '
                                   'regenerate to see that"). Choosing one fills the form; the tooltip of each says '
                                   'what it shows and where the documents say so.'),
    ('sourceButton', 'Source', 'Open the document the chosen variation comes from (its passage is the text after # in the variation\'s tooltip).'),
    ('form', 'Options', "The script's own options, read from its argparse parser each time the page opens (never "
                        'copied, so they cannot go out of date). An empty field uses the script\'s default (shown '
                        'greyed). {out} stands for this run\'s folder.'),
    ('freeEdit', 'Arguments', 'Arguments typed as on the command line (scripts without options).'),
    ('specButton', 'Open file', "Put the SPEC file open in the reader into the SPEC field."),
    ('commandEdit', 'Command', 'The exact command the run executes from the repository root: copy it to rerun the '
                               'same thing in a terminal.'),
    ('runButton', 'Run', 'Run the script as it is in the repository now, in its own process, into a new folder '
                         '(~/.lss_reader/tools/<item>/<date-time>, or $LSS_READER_TOOLS_DIR). The reader stays '
                         'usable while it runs.'),
    ('stopButton', 'Stop', 'Stop the running script.'),
    ('repoCheck', 'Replace the committed products', 'Write into the repository folders that hold this item\'s '
                                                    'committed products instead of a run folder. Only with the '
                                                    'settings that made them (the defaults, or the variation "As '
                                                    'committed") and public data. Commit them with the change that '
                                                    'made them stale (AGENTS.md rule 11).'),
    ('statusLabel', '', 'Whether the committed products are older than the code that makes them. First from the '
                        'verified record (lss_toolbox/verified.json, written by python -m lss_toolbox --audit '
                        '--record): a rerun matched the committed products, and nothing it imported or read has '
                        'changed since. Otherwise from git history: the script, the repository files it imports and '
                        'its named inputs. Changes to comments and docstrings do not count. "May be stale" is a '
                        'hint; Run with the defaults and compare with the committed products to know.'),
    ('docsBox', 'Docs', 'The documents that explain this item; each button opens one.'),
    ('log', 'Output', 'What the script prints, as it runs.'),
    ('runCombo', 'Show', 'Which products to show: a run of this item (newest first) or the committed products in '
                         'the repository.'),
    ('compareCombo', 'Compare with', 'Show a second set beside the first: the committed products or an earlier '
                                     'run. Images with the same name are compared pixel by pixel.'),
    ('diffCheck', 'Differences', 'Show where the two images differ (white) instead of the second image.'),
    ('compareAllButton', 'Compare all', 'Compare every image of the shown set with its counterpart and list which '
                                        'are the same, which differ (by how many pixels) and which are new.'),
    ('fileList', 'Files', 'The images and text files of the shown set; = same as the compared set, ≠ different, '
                          '+ not in the compared set.'),
    ('openFolderButton', 'Folder', 'Open the shown folder in the file manager.'),
    ('openSpecButton', 'Open in the reader', 'Open the SPEC file this run wrote in the reader.'),
)

TIPS = {name: tip for name, _, tip in CONTROLS}
LABELS = {name: label for name, label, _ in CONTROLS}

DATA = {
    'synthetic': 'synthetic data (public)',
    'public': 'public data (NX school or committed tables)',
    'any': 'NX school by default; any SPEC file',
    'private': 'private data (not in the repository)',
}
