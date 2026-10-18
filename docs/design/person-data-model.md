# The person data model

Design note. Written 2026-10-18, companion to
`docs/design/persona-import-and-round-trip.md`. That note is about the import
flow; this one is about what a person's data *is* in ViWo, so an imported field
has one obvious place to land. It changes no code.

Em-dash is banned in this repo; none appear here.

---

## 1. The problem this answers

An imported file carries name parts, aliases, a residence, a partner, family,
friends, skills, languages, intimate descriptions, mbti, alignment and media.
ViWo has a home for some of these and none for others, and even the ones it has
are spread across four stores. Without a stated model, the import (and every
future field) gets assigned by whoever writes the mapping that day, and the same
value ends up in two places or in none.

This note fixes what each concept owns, then maps the source fields onto it.

---

## 2. The concepts

A person in ViWo is not one blob. The data splits by *what question it answers*:

| Concept | The question it answers | Store today | Read by |
|---|---|---|---|
| **Identity** | who they are on paper | `properties["appearance"].identity` plus `aliases` | prompts, matching, narration |
| **Appearance** | what they look like | `properties["appearance"].appearance` | compiled prose, equipment fit |
| **Personality** | who they are inside, how they act and speak | `properties["appearance"].personality` | prompts, fear, affect |
| **Narrative** | their history, secrets, arc, role | `properties["appearance"].narrative` | memories, prompts, plans |
| **Relationships** | who they know, how they feel, what they are to each other | `player.relationships` (runtime) plus a free-text `label` | prompts, social, combat |
| **Memories** | what they have experienced and learned | `player.memories`, `engine/agent_memory.py` | agent recall, reflection |
| **Tags** | the shared vocabulary other systems match on | node `properties["tags"]` / `player.tags` | fear, attention, ownership, movement gating |
| **Knowledge** | what they have actually seen | `player.known`, `engine/fog.py` | perception and fog gating |
| **Runtime** | how they are right now | vitals, mood, `current_area`, inventory | everything |

The first four live in one nested block under the node key `appearance`
(`RECORD_KEY`, `engine/character_appearance.py:38`). **That is the naming
collision this note has to settle**: the block is called `appearance` and it
contains a section also called `appearance`.

---

## 3. The boundaries (the rules)

1. **One fact, one store.** A value that two stores both claim will drift, and
   the one nobody reads is the one the UI shows.
2. **State versus projection.** The block is state; the prose is a projection
   written once by Compile. Editing the prose does not edit the block, and vice
   versa. (See `persona-import-and-round-trip.md` 3.1.)
3. **Intrinsic versus reference.** A value that names something in the world
   (residence, partner, family, workplace) is a *reference*. It resolves to a
   node id, a knowledge record and/or a memory; it is never a free string on the
   sheet. (The four buckets: `persona-import-and-round-trip.md` 7.3.)
4. **A field names its reader.** `mbti`/`alignment`/`media` were left out on
   purpose because nothing reads them (`character_appearance.py:21`). A field
   with no reader rots. To add one, name the reader first.
5. **Tags are not a store.** They are the vocabulary. A tag earns its place by
   being matched by a system (`faction:`, `held_by:`, `size_*`, `fear_tags`,
   `interest_tags`). Tags are not a place to keep a value nothing matches.

---

## 4. Decisions this note raises

### 4.1 The name: `appearance` for two things

The block key `appearance` contains a section `appearance`. One of them should
move. The options:

- **Keep the block key, rename the section** to `body` (or `looks`). Small, but
  the tab and the docs still say "Persona" while the key says `appearance`.
- **Rename the block to `persona`** (or `record`) and keep the section as
  `appearance`. Matches the tab, matches the doc, but is a persisted-key
  migration.

Recommendation: rename the **block** to `persona`, section stays `appearance`.
The tab is already "Persona"; the block name has never been user-visible, so the
migration cost is one key and a load shim, and afterward "appearance" means
exactly one thing.

### 4.2 `description` is also overloaded

Compile writes **`base_description`** (the appearance prose) and **`personality`**.
`description` is the runtime/equipment-derived projection. So "the description"
is ambiguous between `base_description` and `description`. This is not a rename
to rush (both are in the live payload and in prompts), but the docs should say
which is the compiled one: `base_description`.

### 4.3 Intimate parts: structured, from the paperdoll

The paperdoll already maps regions (`InspectorPaperdoll.AREA_TO_REGIONS`), and
the Persona tab already reads region status there. The request is to click a
region and describe it. That description is **intrinsic appearance**, so it
belongs in the block as a structured field (per region), and Compile renders it
into prose like every other look. It must **not** be typed straight into
`base_description`, or the next Compile would clobber it as stale.

Concretely: a `body.regions` group (region id -> text) beside the existing
`body.modifications[]` (which is already region-linked as `area::text`,
`mind-view.ts:1288`). The doll's region click writes the field; Compile reads it.

---

## 5. The imported fields, one by one

### 5.1 Name and aliases

You are right, and I was wrong earlier: ViWo **has** aliases. The `name <target>
as <alias>` command (`routes/action_handlers.py:1249-1309`) writes
`properties["aliases"]` on any node (character, item, way, area), and
`engine/matching.py:113` `node_aliases()` reads them back as lowercase, used by
name matching and by name masking in descriptions.

So **nicknames are aliases**, and the storage exists. The gaps are that aliases
are written only in-game, are not in the Persona tab, and are not in the
character library card, so they do not round-trip on a library save. Fix is
exposure and round-trip, not a new field.

The source splits `name.full/first/last`; ViWo keeps one name (the registry key
is the identity, `engine/matching.py` resolves it). Name *parts* have no reader
today. Drop them or add a reader; do not add a field for them yet.

### 5.2 Relationships

Today: `player.relationships[other] = {closeness, last_interaction_tick,
interaction_count, label, first_sighting}` (`engine/relationships.py:1-11`),
written by interaction and by the `label` command, with a nine-band ladder from
`mortal_enemy` to `inseparable`. So there **is** a `label` ("my brother") and
there **is** a friend/enemy band.

What is missing for "set up families, friends, enemies, to people and to
groups":

- The store is **runtime and per-character-pair**. There is no authored,
  persistent, structured relationship, and no relationship to a **faction or
  group** at all (factions are tags, `engine/ownership.py`).
- A scenario author cannot declare "A is B's sister" as authored data; at best a
  `label` string survives as runtime state.

Proposal: authored **relationship edges** (character -> character, and
character -> group/faction) carrying a `relation` type, with the existing
closeness band as the runtime consequence. The runtime dict stays the
perception/social read; the edge becomes the authored declaration it is seeded
from. A `family`/`friend`/`enemy` label is then a typed edge, not a string that
only the `label` command can write.

### 5.3 Skills

Map a source skill to a ViWo skill id where one exists (`player.skills` is the
numeric sheet), and add a new skill only when the source names one we genuinely
do not have. The import should prefer the existing list over inventing ids, or
every file grows the vocabulary.

Free-text "skills I am good at" (ASMR, graph databases) is a different thing from
the numeric skill sheet. If we keep it, it is a prose list in the personality
block, not a new skill id.

### 5.4 Languages

No language field exists today. The request is a value plus proficiency, and
maybe a per-language memory dictionary. Proposal: `narrative` or `identity` gains
`languages: [{id, proficiency}]`; a memory tagged by language is the dictionary
if we want one. This needs a reader before it ships (who asks "does this
character speak Elvish?"), or it is bucket D.

### 5.5 media, mbti, alignment, potential_storylines

This is the one to correct: **ViWo does not have media.** `character_appearance.py`
line 21 says `media`/`mbti`/`alignment` are deliberately absent because nothing
reads them, and a test enforces it (`tests/test_character_appearance.py:427`
bans all three, `:140` rejects a `media` key). So "we do have media" is not true
of the Persona sheet.

You want mbti, alignment, media kept, and potential_storylines kept for later.
That is fine, but it is a **reversal of a stated rule** and it comes with work:
add the fields, name the reader (the agent prompt context is the obvious one, so
they actually reach the model), and remove the ban plus its test. Storing them
with no reader is exactly what the rule was written to prevent.

### 5.6 Behaviours

Confirmed: `player.behaviors` is evaluated only for **simple NPCs**
(`engine/npc_behaviors.py:470`, and the header of `engine/behaviors.py`). It is
not a place for an agent or a human character's authored traits. A behaviour is
NPC decision logic, nothing else.

### 5.7 faction and ownership

Confirmed: `faction:<name>` and `held_by:<name>` are engine-only. A UI search
finds them only as placeholder text in the behaviour editor and a lore category.
There is no way to set a character's faction or an area's holder from the
inspector. If ownership is meant to be authored, it needs a surface.

### 5.8 known versus memories

Two different systems, and the request is to fold the first into the second:

- `player.known` is the **fog/perception registry** (`engine/fog.py`): a plain
  list of node ids and names the character has seen, read by room perception,
  `agent_memory.is_known`, and condition triggers. It gates what a character can
  perceive at all.
- `player.memories` are **records** (`engine/agent_memory.py`, `remember` /
  `recall`): episodic, semantic, procedural, social, belief.

They overlap in meaning ("I know this area" vs "I remember being here") but not
in reader. Folding `known` into `memories` means memory becomes the store and the
fog gate queries it, which is a real change and needs to keep the fast
id-lookup. This is worth a task, and it is the right instinct; it is not a rename.

---

## 6. Task seeds (not filed yet)

Nine seeds were drafted into cards on 2026-10-18. A filename-glob overlap check
missed the parent card, `task-733` (the character sheet), which already owns most
of them. After a content search, seven were folded and two survive.

| Seed | Disposition |
|---|---|
| Rename the block key `appearance` -> `persona` (4.1) | **task-865**, filed (no existing owner) |
| Expose area `held_by` in the inspector (5.7) | **task-872**, filed and narrowed to `held_by` only |
| Relationships: a typed role, and group/faction relations (5.2) | folded into `task-733` (its "Folded deltas"): `task-619` store, `task-742` group relation |
| Per-region body descriptions from the paperdoll (4.3) | folded into `task-733`: `task-848`, `task-744` slice 4 |
| Map imported skills onto existing ids (5.3) | folded into `task-733` / `task-843` (a second mapping is forbidden twice over) |
| Languages with proficiency and a reader (5.4) | folded into `task-733` as a correction to its `languages -> skills, traits` row |
| Aliases in the Persona tab and round-trip (5.1) | cancelled, duplicate of `task-447` (inprogress, already implemented) |
| `mbti` / `alignment` / `media` with a reader (5.5) | folded into `task-850` (existing) |
| Fold `player.known` into memories (5.8) | cancelled, duplicate of `task-734` (existing) |

What this exposed:

- **`task-733` is the parent** for the persona sheet. It already lists the
  relationship vocabulary, skills, languages, the `appearance.genitalia` region
  detail, secrets, narrative and media. A new sheet field belongs there, not in a
  parallel card.
- **`task-843` is the import card**, and it currently states "unknown fields stay
  empty, never invented". The maximal-fill policy reverses that, so 843's
  acceptance is stale regardless of the rest.
- **Relationships already have an authored store and editor** (`task-729`), and
  **nicknames/aliases already round-trip** (`task-447`). Two of the first drafts
  claimed otherwise.

Surviving new work: `task-865` (block-key rename) and `task-872` (`held_by` UI).

---

## 7. See also

- `docs/design/persona-import-and-round-trip.md` - the import flow this maps.
- [[Persona]] - the feature page.
- [[Traits System]], [[Emotion & Affect System]], [[Background Simulation]].
