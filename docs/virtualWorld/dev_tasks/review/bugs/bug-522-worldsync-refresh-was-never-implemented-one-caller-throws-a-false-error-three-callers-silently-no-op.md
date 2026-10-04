---
type: bug
status: review
area: bugs
priority: medium
---

# bug-522: worldSync.refresh() was never implemented: one caller throws a false error, three callers silently no-op

**Filed:** 2026-10-05
**Related:** task-492,task-441

## Goal

Found live 2026-10-04 in kraktooth_goblin_camp (Rikka's turn 4): three 'Scope change failed: window.worldSync.refresh is not a function' rows AFTER the scope change had already succeeded. static/js/world-sync.ts exported no refresh method at all; inspector/area-view.ts:537 called it guarded only on the object's existence (throwing), while graph-manager.ts:389, structures.ts:227 and worldpainter/editor.ts:600 guarded on the method and silently did nothing - exactly the dead-call pattern the TS gate's reviewed-prefix notes warn about.

## Acceptance
- [x] `worldSync.refresh()` exists: re-reads the library types, re-collects
      entities, re-renders summary + list, WITHOUT opening the modal
      (`open()` delegates to it and then shows the modal).
- [x] area-view's unguarded call no longer throws; a scope change reports
      success instead of "Scope change failed" after succeeding.
- [x] The three guarded callers (graph-manager, structures, worldpainter) are
      live code again rather than dead probes.
- [ ] Live verification: move an area between scopes in the inspector and
      confirm no error toast; the sync panel list updates on refresh.
