# Inspector Panels

The Inspector is a context-sensitive right-side panel for inspecting and editing world entities — areas, items, ways, characters, memories, behaviors, lore, and more.

## Architecture

The `Inspector` class (`static/js/inspector.js`) is a singleton (`window.inspector`). It delegates rendering to specialized sub-view modules in `static/js/inspector/`:

### Rendering (lit-html, task-216)

All inspector views render through a single panel owner — `InspectorPanel` (`static/js/inspector/panel.js`). **No file other than `panel.js` writes to `#inspector-panel`**; mixing `innerHTML` writes with lit's `render()` on the same container corrupts lit's part tracking.

- `static/js/vendor/lit-html/**` — vendored lit-html (no CDN / import map)
- `static/js/shared/lit-bootstrap.js` — deferred ES-module bootstrap exposing `window.Lit` (`html`, `render`, `nothing`, `unsafeHTML`, directives). Loaded as a module with `defer`, so classic scripts reference `window.Lit` only inside functions (at call time).
- `static/js/inspector/panel.js` — `InspectorPanel.render(template)` / `clear()`; the single render entrypoint.

Converted views (area, item, way, lore, behaviors, memory modal, trigger-helpers, helpers, edge-inspector) build lit `TemplateResult`s with `window.Lit.html` and hand them to `InspectorPanel`. Inline `onclick`/`onchange` became `@click`/`@change` bindings; lit auto-escaping replaces manual `esc()`.

`agent-view.js` (the largest, with ~48 inline handlers) renders its existing string template through `InspectorPanel` wrapped in lit's `unsafeHTML` directive. Helper TemplateResults that can't be string-concatenated (`graphGravityControl`, `renderAliasesSection`) are injected into placeholder `<div>`s by a deferred-render queue. `paperdoll-view.js` stays string output (consumed by agent-view) and keeps its manual `esc()` calls.

| Module | File | Renders |
|--------|------|---------|
| `InspectorAreaView` | `area-view.js` | Area properties, environment, exits |
| `InspectorItemView` | `item-view.js` | Item properties, actions, effects, costs, triggers |
| `InspectorWayView` | `way-view.js` | Way state, connections, properties |
| `InspectorAgentView` | `agent-view.js` | Character/agent full profile |
| `InspectorMemory` | `memory-view.js` | Memory list, CRUD, flat view |
| `InspectorBehaviors` | `behaviors-view.js` | Behavior editor (trigger, conditions, actions) |
| `InspectorLore` | `lore-view.js` | World lore CRUD |
| `InspectorPaperdoll` | `paperdoll-view.js` | Equipment slots, inventory context menus |
| `InspectorHelpers` | `helpers.js` | Shared utilities (tags, params, personality, etc.) |
| `TriggerHelpers` | `trigger-helpers.js` | Trigger/effect grid editing |
| `EdgeInspector` | `graph/edge-inspector.js` | Graph edge properties/type editing (via `InspectorPanel`) |
| `InspectorPanel` | `panel.js` | Single owner of `#inspector-panel` render/clear |

### Inspector.js Dispatch (line 31)

```javascript
showNode(nodeId) {
    const graphNode = worldState.getNode(nodeId);
    switch (graphNode.type) {
        case 'room':      return this._showRoom(nodeId, graphNode);
        case 'item':      return this._showItem(nodeId, graphNode);
        case 'door':      return this._showDoor(nodeId, graphNode);
        case 'character': return this.showAgent(graphNode.name);
    }
}
```

### Auto-Refresh on State Updates

The Inspector subscribes to the `state:updated` event at construction (line 8):

```javascript
if (window.appEvents) {
    appEvents.on('state:updated', () => this._reRender());
}
```

`_reRender()` (line 13) re-dispatches to the current view type, ensuring the inspector panel stays in sync with world changes without manual refresh.

## Sub-Panels

### Area View (`InspectorRoomView`)

Shows:
- Area name (editable) and description (editable textarea)
- Environment sliders: light, temperature, air, smell, noise
- AI Improve button — uses LLM to generate richer room descriptions
- Exits list with door links
- Graph physics controls (gravity toggle)

### Item View (`InspectorItemView`)

Shows:
- Item name (editable), description, weight, uses, hidden/locked flags
- Actions grid — toggle which actions are enabled (examine, take, use, eat, drink, read, activate)
- Action costs grid — set stat costs (Energy, Hunger, Thirst, HP) per action
- Skill check configuration
- Equip slots
- Tags
- AI Improve button — uses LLM to enhance item descriptions
- Move item controls (to room or container)
- Trigger/effect grid via TriggerHelpers

### Character/Agent View (`InspectorAgentView`)

Shows a multi-tab interface (line 158, `_switchAgentTab`):
- **Profile tab**: Name, personality (with AI generation), description (with AI generation), state, emotion slider, tags, stats, skills, vitals
  - The **Appearance** section has a live **"First impression:"** preview — shows exactly what a stranger sees at a glance (tag-derived handle + first sentence of the description), updating as you type. See [[Library System/Tags System#First impression (the at-a-glance look)]].
- **Inventory tab**: Paperdoll-style equipment slots and inventory list with context menus
- **Behaviors tab**: Behavior editor
- **Memories tab**: Memory list with CRUD
- **Lore tab**: World lore browser
- **Agent tab**: LLM agent configuration (model, temperature, etc.)
- **Relationships tab**: Character relationships with closeness scores

Features:
- Save/export/import character cards (library integration)
- Kill/remove character buttons
- AI personality generation from text prompt (`_generatePersonality`, line 114)

### Way View (`InspectorWayView`)

Shows:
- Way state (open/closed/locked/hidden)
- Description
- Connection info: area_from, area_to, direction
- Reconnect button to change which areas the door connects
- Pass message (text shown when passing through)
- Auto-close toggle
- Force open settings (skill + DC)
- **Passage requires** dropdown: none / crawl (crawl-only — `go` auto-crawls) / climb (`climb <dir>` only) / jump (`jump <dir>` only) — task-187
- **Max size through** dropdown: any / tiny / small / normal / huge / giant / titanic — the largest size that passes walking; one tier over auto-crawls, two+ tiers blocked — task-187

The AI Improve flow (`InspectorWayView.improveWayWithAI`) generates `requires` and `max_size` alongside the other way properties, and they are preserved in the way library save.

### Memory View (`InspectorMemory`)

Full CRUD for character memories (see Memory System docs for details):
- List all memories with type icons, importance badges, tick timestamps
- Add, edit, delete individual entries
- Flat/compact view toggle
- Clear all memories

### Behaviors View (`InspectorBehaviors`)

Editable behavior definitions for NPCs:
- Trigger types: `on_player_enter_area`, `on_item_taken`, `on_tick`, `on_use`, `on_examine`, etc.
- Conditions: state checks, item possession, random chance, compound conditions (AND/OR)
- Actions: message, speak, damage, heal, set_state, set_npc_state, give_item, set_environment, teleport, etc.

### Lore View (`InspectorLore`)

World lore editor (see `inspector.js:347-374`):
- List all lore entries
- Add, edit, delete entries
- Each entry has category, title, and content

### Agent View (tab)

Controls for the LLM agent system:
- Model, temperature, max tokens
- Turn-based mode
- Reactive mode toggle
- RPM limit

### Trigger Helpers (`trigger-helpers.js`)

Shared grid components for editing item triggers and door triggers:
- Trigger type dropdown (`on_examine`, `on_use`, `on_open`, `on_close`, `on_take`, `on_drop`)
- Effect type dropdown (`message`, `heal`, `damage`, `set_state`, `set_environment`, `teleport`, `give_item`, `remove_item`, `set_npc_state`, `flag_set`, `flag_check`, `random_chance`)
- Effect parameters editor (dynamic fields per effect type)
- Conditions editor (compound conditions with AND/OR operators)

### Paperdoll View (`InspectorPaperdoll`)

Equipment visualization:
- Body slot display (hand_left, hand_right, head, chest, legs, feet, etc.)
- Equip/unequip from context menus
- Stack management for multi-item slots
- Inventory context menus with actions (examine, take, use, drop, equip)

## Context Menus

The Inspector supports right-click context menus for:
- **Inventory items** (`_showInventoryContextMenu`, line 193): Examine, Use, Equip, Drop, Move
- **Paperdoll slots** (`_showPaperdollContextMenu`, line 197): Unequip, Replace, Inspect

Context menus are rendered via `_showContextMenu()` (line 181) which positions a `#context-menu` div at the click coordinates and auto-dismisses on click.

## Editing Capabilities

Nearly all entity properties are editable directly from the Inspector:

- **Area**: name, description, environment (light, temp, air, smell, noise), tags, graph gravity
- **Item**: name, description, weight, uses, actions, action costs, skill checks, tags, equip slots, hide/lock status, triggers, move location
- **Way**: state, description, connections, pass message, auto-close, force-open requirements
- **Character**: name, personality, description, state, emotion, tags, stats, skills, vitals, traits, behaviors, memories, relationships, equipped items, inventory, knowledge
- **World lore**: full CRUD on lore entries
- **Tags**: add/remove on any node
- **Parameters**: key-value parameter editor for any node properties

Changes are saved immediately on edit via `ApiClient.updateNode()`, `ApiClient.updateCharacter()`, or specific save endpoints.

## Related tasks

- [[dev_tasks/review/refactor/task-216-lit-html-inspector-conversion|task-216: lit-html inspector conversion]]
- [[dev_tasks/review/ui/task-13-unify_item_inspector_and_library|task-13: Unify item inspector and library]]
- [[task-86-ux_ui_improvements|task-86: UX/UI improvements]]
- [[task-89-character_inspector_polish|task-89: Character inspector polish]]
- [[dev_tasks/done/graph/task-107-id-rename-sync-and-trigger-consistency|task-107: ID rename sync and trigger consistency]]
- [[dev_tasks/review/characters/task-17-editable_characters|task-17: Editable characters]]
- [[dev_tasks/review/characters/task-24-traits_conditions_emotions_editor|task-24: Traits conditions emotions editor]]
- [[dev_tasks/review/ui/task-36-inspector_game_time|task-36: Inspector game time]]
- [[dev_tasks/review/characters/task-42-proper_memory_editor|task-42: Proper memory editor]]
- [[dev_tasks/review/ui/task-41-prevent_double_step_click|task-41: Prevent double step click]]
- [[bug_1-trigger-editor-effOpts-undefined 1|bug_1: Trigger editor effOpts undefined]]
- [[dev_tasks/done/bugs/bug_2-choices-equip-slots-white-bg|bug_2: Choices equip slots white bg]]
- [[bug_6-inspector-equip-slots-white-bg 1|bug_6: Inspector equip slots white bg]]
