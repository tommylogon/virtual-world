---
wiki: "[[UI & Settings/Inspector Panels]]"
---

**Status**: Done — structural note, verified 2026-08-03. UI is modular under static/js/ui/ (8 modules), static/js/inspector/ (8 modules), static/js/graph/ (5 modules). No concrete feature deliverables; kept as a record of the modularization impact.

## Refactoring Impact (July 2026)

UI is fully modular under static/js/ui/, static/js/inspector/, static/js/graph/. JS libraries (Tippy.js, Choices.js, Notyf) already loaded via CDN. Improvements stay scoped to their module — no monolithic rewrite.
