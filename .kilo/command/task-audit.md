# /task-audit - Ground-truth audit for dev_tasks

Audit `todo` (and optionally `review`) dev-task cards against the live codebase
before planning, grooming, or starting work.

## Steps

1. Run the automated structural check:
   ```powershell
   python tools/task_todo_audit.py --status all
   ```
2. For every flagged task (and any card you are about to work on or rewrite):
   - Use `codesearch` (`search_code`, `get_code`, `find_references`) to check
     whether the claimed missing mechanic already exists under another module
     or name.
   - Read every file in `sections.files` and every cited line range / symbol in
     `what`, `why`, `how`, `verify`, and `custom.browser_ui`.
   - Check that `what`, `why`, `how`, `verify`, `acceptance`, and
     `custom.browser_ui` all agree on the same architecture (no half-rewritten
     contradictions).
3. Fix or flag any card that:
   - invents a duplicate of an existing engine/UI system,
   - cites non-existent files, methods, or wrong line numbers,
   - skips real blockers in the target code path (e.g. `approach_character`
     or `routes/action_handlers.py` room checks),
   - is already implemented and ready to move to `review`/`done`.
