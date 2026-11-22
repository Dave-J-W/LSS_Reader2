"""The repository's demonstrations, figure and data generators and checks,
in one place (owner, 2026-11-22: "including all the demonstrations and
figure generators in this repo, all be accessible from reader's GUI, under
the 'tools' menu. But make sure they are generated without stale into the
repo as well, since they are an integral part of the documentation").

- ``registry``: every tool, what it makes, from which data, how long it
  takes, and the committed files each documented run (a *job*) writes.
- ``freshness``: hashes of a job's inputs (the code it ran, the data it
  read) and outputs, the manifest ``docs/figures/MANIFEST.json``, and the
  check that every committed output is up to date.
- ``trace``: runs a tool exactly as its documented command does and
  records which files of the repository it imported and read.
- ``regenerate``: ``python -m lss_tools.regenerate`` reruns the stale jobs.
- ``gui``: the reader's Tools menu and the dialog that runs a tool.

The tools themselves stay where they are documented (``tests/tools/``,
``tests/demonstrator/``); this package only lists and runs them.
``docs/TOOLS.md`` is the table for people.
"""
