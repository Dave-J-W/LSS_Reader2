# Export's proposed name stays without the series id

- **Date, who:** 2026-11-27, GUI manager. Asked of the owner in #167, the last open point of #146 (F105).
- **Answer:** the owner said "Export name is fine as it is". The proposed name stays
  `<SPEC file>_<sample>_S<scans>`, for example `20260923_dppc_S6-9`, and does not carry the series id from
  `#U Series` (`lss_core.naming.export_base`). This confirms the second answer to Q10 of 2026-11-25
  (`docs/gui/questions.md`).
- **Collisions:** two exports get the same name only when the same scans of the same SPEC file are exported
  again. Export then replaces `_ref.txt` and `_rrf.txt` and says which files it replaced in Messages
  (`MainWindow.exportNotice`). The numeric suffix assumed under Q10 was not built, and "fine as it is"
  leaves it that way.
- **How it is known:** the owner's answer. The behaviour was read from the code and is checked by
  `tests/test_naming.py`, `tests/test_gui_export_name.py` and `tests/test_gui_export_notice.py`.
- **Numbers that changed:** none.
