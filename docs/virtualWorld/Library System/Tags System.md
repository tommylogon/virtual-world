# Tags System

Tags are lightweight, id-keyed classifiers attached to items, areas, and characters. They
drive engine behavior (containers, surfaces, light/heat/sound sources, stranger labels,
equipment, vitals) and power library-browser filtering.

Tags are **case-insensitive** when the engine checks them, and may be stored as a list
(`["animal", "container"]`) or a comma string (`"animal, container"`).

## Where tags live

- **Tag library**: `data/library/tags/<id>.json` — one file per tag, keyed by id. Storing a
  tag with an existing id **overwrites** it (upsert), so tags dedupe naturally.
- **On entities**: characters/items carry `"tags": ["animal", "container", ...]` in their
  player/node data. `world_template.json` and per-item library files both use this.

### Tag file format

```json
{
  "id": "animal",
  "name": "Animal",
  "description": "Non-human creature or beast",
  "category": "character",
  "color": "#aa8844",
  "icon": "dY?_",
  "applies_to": ["characters"],
  "examples": ["wolf", "horse", "rat", "cat"]
}
```

## Mechanical tags (engine behavior)

These tags change how the engine treats the entity. Verified against `engine/`, `routes/`,
`player.py`, `graph.py`.

### Items

| Tag | Effect | Code |
|-----|--------|------|
| `container` | Item can hold other items. `put X in Y` works, capacity-checked. **This is the only tag placement strictly requires** — `place_item` with relation `in` refuses targets without it. | `engine/item_actions.py:717-722`, `put_item_in_container:642-646` |
| `furniture` | A surface commonly used for spatial placement (`put/place X on/under/beside/behind/at Y`). **Convention, not enforced** — `place_item` accepts any item as a surface target; only `in` requires `container`. Add it so authors/filters know the item is meant as a surface. | `engine/item_actions.py` `place_item` |
| `toggleable` | Item can be toggled on/off (`toggle <name>`). Without it, `toggle` is refused. | `engine/toggleable_items.py:30-31` |
| `electric` / `synthetic` | Only changes toggle wording — "turn on/off" instead of "light/extinguish". No electrical-circuit mechanic. | `engine/toggleable_items.py:49-53` |
| `light_source` | Emits light when toggled on; affects ambient light in the area. | `engine/lighting.py:49`, `engine/toggleable_items.py:71-79` |
| `heat_source` | Emits heat; excluded from passive heat-sink calculations so its own warmth persists. | `engine/environment_propagation.py:138` |
| `sound_source` | Emits sound that propagates through the sound system. | `engine/sound.py:265` |
| `two_handed` | Equipped item occupies both hand slots. | `engine/equipment.py:72,364` |
| `weapon` | Contributes attack bonus in combat. | `engine/equipment_bonuses.py:77` |
| `resistance` | Item grants elemental resistances (from its `resistances` property dict). | `engine/equipment_bonuses.py:88` |
| `food` | Edible (also gated by `eat` action). | `engine/trigger_system.py:955` |
| `drink` | Drinkable (also gated by `drink` action). | `engine/trigger_system.py:957-958` |
| `openable` | Can be opened (alongside `open` action). | `engine/trigger_system.py:909` |
| `cursed` / `statue` / `plant` / etc. | Content/category tags — no hardcoded engine effect, used by triggers, traits, and filters. (`magic` on an ITEM has no effect — it only matters on characters, see below.) | — |

### Characters

| Tag | Effect | Code |
|-----|--------|------|
| `male` / `man`, `female` / `woman`, `girl`, `boy`, `child`, `animal` | **Stranger label** for characters you haven't met. | `player.py` `unknown_display_name()` |
| `magic` | Grants the character a **Mana** vital (removed if the tag is removed). Mana is a spendable resource for magical abilities/spells — without this tag the character has no Mana bar at all. | `player.py:47-55` `sync_vitals_with_tags()`, called on player init + via `/api/players` routes |
| `spell` / `ability` / `innate` / `intrinsic` / `power` | Marks **intrinsic abilities** — never shown as "holding" to other characters. | `engine/equipment.py:15-17` `INTRINSIC_ABILITY_TAGS`, `engine/area_description.py:247` |

### Areas

| Tag | Effect | Code |
|-----|--------|------|
| `toilet` / `bathroom` | `relieve` finds a usable toilet in the area. | `routes/action.py:154` |

## Stranger labels from character tags

When a character is rendered to someone who **hasn't met them**, the engine shows a label
instead of their real name (`Player.unknown_display_name()`, player.py). Resolution order:

1. **`unknown_name`** — explicit author-provided label wins
2. **Gender/type tag** — `male`/`man` → "the man", `female`/`woman` → "the woman",
   `girl` → "a girl", `boy` → "a boy", `child` → "a child", `animal` → "an animal"
3. **`description`** — first sentence of the description (e.g. "A tall woman with long auburn
   hair" → "the tall woman with long auburn hair"), pronoun-starting sentences map to a
   person label ("She stands..." → "the woman who stands...")
4. no matching tag → "the stranger"

Tags are checked **before** the description: the label is a short gender/type handle, and
the full appearance is carried separately as the "first impression" (see below). So a
`simple_npc` rat with the `animal` tag renders as **"an animal is here"**, not "the
stranger is here". Give simple NPCs appropriate tags (`animal`, `male`, `female`, ...) so
they show a sensible stranger label.

### First impression (the at-a-glance look)

The **first sentence** of a character's description (up to the first `.`) is the highlight
of what you see when you look at someone. It's what appears in the room's **"People here"**
list alongside the stranger label:

```
- the man (awake) — He stands completely unadorned, the full expanse of his fit, athletic form on display.
```

- The stranger label comes from the tag/`unknown_name` logic above; the first sentence is
  the appearance handle. Both show for met **and** unmet characters — what someone looks
  like is how you perceive them regardless of whether you know their name.
- In `pitch_black` / `dim` lighting the list trims further ("You can hear them nearby — ...",
  "A vague shape in the gloom — ...").
- The **full** description is only revealed via `examine <name>` — keep the first sentence
  as the "money shot" and put the rest of the detail in the remaining sentences.
- The Inspector **Appearance** section shows a live **"First impression:"** preview that
  mirrors this logic (`InspectorAgentView._computeFirstImpression` in
  `static/js/inspector/agent-view.js`), so authors see exactly what strangers get at a
  glance as they type. It derives the handle from the character's tags and appends the
  first sentence of the current description.
- Implementation: `static/js/agent/prompt-builder/` — `anonymousName()` (tag handle,
  mirroring `voiceLabel()`), `buildRoomContext()` "People here" list (first-sentence trim).
  Backend: `player.py` `unknown_display_name()` / `_tag_unknown_name()`.

### Hearing (cross-room)

The same tag→gender mapping powers `voiceLabel()` in `static/js/agent/prompt-builder/`
for hearing characters through walls ("a woman's voice" / "a man's voice"). Physical
appearance is useless through a wall, so the voice label derives from tags first, then
pronouns in the description, then a generic "a voice".

## Tag-based queries & triggers

- `WorldGraph.get_items_by_tag(tag, area_id)` and `get_characters_by_tag(tag, area_id)` —
  case-insensitive lookups (graph.py:161-174).
- Trigger `on_use_on` supports a **`target_tag`** property — the trigger only fires when the
  use-target carries that tag (`engine/trigger_system.py:1144-1148`).
- Trait conditions can reference tags (e.g. allergen trait matching a tag on nearby items).
- `get_tagged_items_in_area(area_id)` groups items by tag for the frontend.

## Auto-registration from agent memories

When an LLM agent writes a memory with `tags`, unknown single-word tags are auto-registered
into the library (`static/js/agent/memory-manager.js` → POST `/api/library/tags`). The
id-keyed library dedupes repeats. Manual tag creation uses the `TagMultiselect` component
(also id-keyed, create-on-the-fly).

## Tag API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tags/search` | Autocomplete / list tags |
| GET | `/api/tags/validate` | Validate tag ids against the library |
| GET | `/api/tags/stats` | Per-tag usage counts |
| POST | `/api/library/tags` | Create or update a tag (upsert by id) |

## Related

- [[dev_tasks/done/items/task-106-tag-library-and-multiselect|task-106: Tag library and multiselect]]
- [[dev_tasks/done/items/task-108-tags-as-dicts-with-type-and-description|task-108: Tags as dicts]]
- [[dev_tasks/done/items/task-118-toggle-verb-by-tag|task-118: Toggle verb by tag]]
- [[dev_tasks/done/triggers/task-169-add-tag-to-target-via-trigger|task-169: Add tag to target via trigger]]
- [[dev_tasks/done/characters/task-178-unify-memory-systems|task-178: Memory unification (tag auto-registration)]]
- [[Library System/Library System Overview]]
- [[Items & Inventory/Items Overview]]
- [[AI & Narration/Memory System]]
