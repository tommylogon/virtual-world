---
type: bug
status: todo
area: ui
priority: high
wiki: "[[Gameplay/Characters]]"
related: [task-675, bug-577, bug-578]
---

# bug-579: Character Inspector Bio tab Tags section missing selector for characters with multi-word names

**Filed:** 2026-11-09
**Related:** task-675, bug-577, bug-578

<!-- deps:start -->
**Related:** [[task-675-character-editor-three-column-body-with-section-nav-rail]], [[bug-577-character-inspector-crashes-reading-bg-on-directed-control-mode]], [[bug-578-agent-list-collapses-to-single-active-character-after-toggling-control-mode]]
<!-- deps:end -->

## What

In Character Inspector -> Bio tab, under `🏷️ TAGS`, characters with multi-word names (such as "kayla jenkins" or "jake halloway") show an empty section. There are no tag chips and no input or dropdown to search, select, or add tags. The UI jumps straight from the `🏷️ TAGS` header to `🔹 ALIASES`.

## Why

1. In `static/js/inspector/agent-view.ts` (lines 1052 and 1146), the mount target container for the `TagMultiselect` component is rendered with:
   ```html
   <div id="tag-multiselect-agent-${escName}"></div>
   ```
2. When mounting in `showAgent()` (line 185), the container is queried using:
   ```ts
   const tagContainer = root.querySelector<HTMLElement>(`#tag-multiselect-agent-${escName}`);
   ```
3. For single-word names (e.g. `elena`), this produces `#tag-multiselect-agent-elena`, which is a valid CSS identifier and is found by `querySelector`.
4. For multi-word names containing spaces (e.g. `kayla jenkins`), the rendered attribute is `id="tag-multiselect-agent-kayla jenkins"`.
5. CSS selector syntax treats unescaped spaces as descendant combinators. Therefore, `querySelector('#tag-multiselect-agent-kayla jenkins')` looks for a `<jenkins>` tag nested inside an element with ID `tag-multiselect-agent-kayla`.
6. The query returns `null`, so the `TagMultiselect` constructor is never called. The container remains an empty, invisible `<div>` in the DOM.

## How

1. In `static/js/inspector/agent-view.ts`:
   - Compute a sanitized tag container element ID that replaces spaces and non-alphanumeric characters with underscores (matching the convention used by `player-room-` input on line 395):
     ```ts
     const tagMountId = 'tag-multiselect-agent-' + escName.replace(/[^a-zA-Z0-9_-]/g, '_');
     ```
   - Use `id="${tagMountId}"` in both compact and full-surface bio tab layouts (lines 1052 and 1146).
   - In `showAgent()` (line 185), query using `document.getElementById(tagMountId)` or `root.querySelector<HTMLElement>('#' + tagMountId)`.
2. Verify that characters with multi-word names properly display the `TagMultiselect` widget with their tag chips and autocomplete input.

## Acceptance Criteria

- Characters with multi-word names (e.g., "kayla jenkins", "jake halloway") render the `TagMultiselect` search/add widget under `🏷️ TAGS` in the Character Inspector.
- Adding, searching, and removing tags updates character tags via `ApiClient.updateCharacter()`.
- No CSS syntax or selector errors are emitted when opening the inspector for characters with spaces in their names.
