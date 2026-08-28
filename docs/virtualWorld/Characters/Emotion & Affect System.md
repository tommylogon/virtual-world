# Emotion & Affect System

VirtualWorld gives every character a **multi-dimensional emotional state** (the *affect map*) that sits
*alongside* the vitals and relationships, and a set of **recall hooks** that let a memory's emotion
actually land on a character when it surfaces. This page documents both the player-facing behaviour and
the implementation.

---

## Non-technical overview

A character doesn't just "feel happy." They carry a rolling **affect map** — a set of emotional
dimensions on a 0–100 scale that drift toward a restful baseline over time. It's what the LLM reads as
"mood" each turn (e.g. *"You are elated — everything feels bright and possible."*).

Three things change that map:

1. **Live events** — the engine/LLM nudges dimensions directly (`happy`, `afraid`, …).
2. **Remembering your own memories** — when a memory surfaces in *your own* recall during a turn, it
   re-feels a fraction of the emotion it carried ("we remember, therefore we feel").
3. **Someone reminds you** — when another character *says something that touches one of your memories*,
   that memory re-feels in you too (even a whisper, even if you can't see who's speaking).

And importantly, a re-felt memory now **does something**: it nudges the matching **mental vital**
(Sanity / Entertainment / Social) and, when the speaker is a **known person**, the memory also nudges
your **relationship** toward them.

**Example:** *"Remember that time I made you come in the train?"* — if that maps to one of the
listener's memories tagged `aroused`/`embarrassed`, the listener genuinely re-feels it (both are live
dimensions), gets a small vital wobble, and — because the speaker is a named person they know — their
relationship toward that person shifts slightly (trust / attraction). If the line came through a wall as
*"a woman's voice"*, the emotional hit still lands, but no relationship is attributed.

---

## The affect map

Defined in `engine/emotion.py`.

### Dimensions & axes

The map is **much richer than the old 7**. It now has **36 dimensions** grouped into axes. Each has a
baseline (resting) level the map drifts toward.

| Axis | Dimensions (baseline /100) |
|------|---------------------------|
| joy | `happy` 40 · `excited` 30 · `elated` 22 · `proud` 30 |
| sadness | `sad` 8 · `lonely` 10 · `melancholic` 12 · `nostalgic` 18 |
| fear | `afraid` 10 · `anxious` 12 · `uneasy` 12 · `dread` 8 · `spooked` 10 |
| anger | `angry` 8 · `irritated` 12 · `resentful` 10 |
| arousal | `aroused` 12 · `eager` 26 · `craving` 15 · `curious` 35 |
| bond | `affectionate` 25 · `loving` 26 · `grateful` 24 · `admiring` 30 |
| shame | `ashamed` 8 · `embarrassed` 10 · `guilty` 8 |
| envy | `envious` 5 · `jealous` 8 |
| disgust | `disgusted` 5 · `repulsed` 5 |
| calm | `calm` 50 · `content` 46 · `peaceful` 46 · `satisfied` 40 |
| surprise | `surprised` 15 |

Key functions:

- `baseline()` — a fresh neutral copy of the map.
- `spike(map, dim, delta)` — bump one dimension, clamped to 0–100. **Unknown dims are ignored**
  (returns unchanged), so an invented label never crashes.
- `decay(map)` — drift every dimension toward its baseline each tick (see `emotion.decay_per_tick`).
- `dominant(map)` — the most deviant dimension and its deviation.
- `describe(map)` — first-person mood paragraph for prompts; dimensions without hand-written bands get a
  safe generic fallback.
- `felt_from_llm(raw)` — normalize an LLM `{label,intensity}` into a (dim, delta) spike.

---

## Mapping labels → dimensions

### `LABEL_TO_DIM` (`engine/emotion.py`)

A large curated vocabulary → closest dimension. Covers the editor/generator word list
(embarrassed, aroused, spooked, nostalgic, guilt, …). `map_label(label)` does exact then substring
match and returns `[(dim, weight)]`, or `[]` for a truly unknown word (graceful no-op).

### Semantic fallback — `static/js/shared/emotion-mapper.js`

`window.EmotionMapper.resolve(label)` tiers:

1. **Keyword** — `LABEL_TO_DIM` (shared with the editor) + substring.
2. **Semantic** — if embeddings are configured, embed the label and pick the **nearest dimension anchor
   by cosine similarity** (`DIM_ANCHORS`, cached after first use). This is how a novel / agent-invented
   label still lands on the closest real dimension instead of being dropped.
3. Otherwise `null` → the caller sends the raw label and lets the server's keyword map try (and if that
   fails, it stays a no-op). Nothing ever throws.

---

## How memory emotions reach the character

There are **two recall paths**, and only one existed before.

### 1. Self-recall (remembering your own memory)

`static/js/agent/prompt-builder/memory-context.js` → `_respikeFromMemories(charName, topMemories)`.

Called while a character's prompt recall block is built. It now reads the **full `memory_emotions`
list** (not just a single primary), resolves each label to a dimension via `EmotionMapper`, accumulates
the deltas (scaled by intensity, `×1.7`), and POSTs once to `/api/players/<name>/emotions/map`. Payload:
`{ mapped: { dimension: delta } }`. Rate-limited to one burst per character (5 s guard).

### 2. Social recall (someone mentions a memory of yours)

`static/js/agent/prompt-builder/room-context.js` → `_fireSocialRecall(charName, seeds)`.

Fired right after that character's **WITNESSED** block is assembled. For every spoken line the character
actually perceives (same-room events *and* cross-room `recent_hearing`), it records `{speaker, text}`,
then:

- **Matches** the spoken text against the character's memories:
  - **Semantic** — embed the line → `POST /api/memory/embeddings/search` (the vectors already live
    server-side) → top result above a `0.5` threshold.
  - **Keyword overlap** as fallback when embeddings are off.
- On a match, **re-feels that memory's `memory_emotions`** (via `/emotions/map`).
- **Name-gated relationship nudge**: includes `toward: <speaker>` only when the speaker is a real,
  known player (`worldState.players[speaker]`). An anonymized voice label (*"a woman's voice"*) stays a
  pure re-feel — we never invent a relationship with an unknown person.
- Rate-limited (~12 s per character), one recall per turn.

---

## Mental-vital coupling — `VITAL_EFFECTS` (`engine/emotion.py`)

Each dimension maps to a **mental vital** and a sign/strength. Applied **subtly** on recall so a single
memory only shifts a vital by a few points.

| Dimension | Vital | Effect |
|-----------|-------|--------|
| `happy`/`excited`/`elated` | Entertainment | + |
| `proud`/`affectionate`/`loving`/`admiring` | Social | + |
| `afraid`/`anxious`/`dread`/`spooked` | Sanity | − |
| `ashamed`/`guilty`/`melancholic` | Sanity | − |
| `lonely` | Social | − |
| `calm`/`peaceful` | Sanity | + |
| `envious`/`jealous` | Social | − |
| `content`/`satisfied`/`nostalgic`/`curious`/`eager` | Entertainment | + |

---

## Relationship coupling — `RELATIONSHIP_VALENCE` (`engine/emotion.py`)

Maps a re-felt dimension to a **relationship drive** (`trust` / `fear` / `disgust` / `attraction`) toward
the speaker. Examples: `affectionate`/`grateful`→trust+, `afraid`/`dread`→fear+, `angry`/`resentful`→trust−,
`disgusted`→disgust+, and the newer ones: **`embarrassed`/`ashamed`→trust+**, **`aroused`→attraction+**.

These write a **derive-compatible tagged experience** (`rel:<speaker>`, `<drive>:<value>`) so the
existing `engine.derive` reducer folds it into the derived relationship profile (trust/fear/consent) that
mechanics gate on — no new relationship machinery.

---

## API

### `POST /api/players/<name>/emotions/map` (`routes/player_ops.py` → `handle_map_player_emotions`)

The one endpoint both recall paths use. Request:

```json
{
  "label": "embarrassed",   // optional — server resolves via LABEL_TO_DIM
  "intensity": 7,           // optional — scale for keyword path
  "mapped": {"fear": 12.4}, // optional — client already resolved (semantic); takes precedence
  "vitals": {"Sanity": -2}, // optional — explicit vital deltas
  "toward": "elena vance"   // optional — speaker; only documented when it resolves to a known person
}
```

Behaviour:
- Resolves dimension deltas (`mapped`, else `label`+keyword), applies each `spike_emotion`.
- Computes subtle **vital** deltas from `VITAL_EFFECTS` (unless explicit `vitals` given) and applies them,
  clamped 0–100.
- If `toward` resolves to a real player, writes a derive-compatible `rel:`/drive-tagged memory to nudge
  the relationship (`emotion.rel_scale`). Unresolvable → no relationship change.
- Unknown labels never error — they're a no-op.

### `POST /api/players/<name>/emotions` (`handle_spike_emotion`)

Legacy single-label spike, now accepting the **expanded** dimension set.

---

## Config knobs (`engine/runtime_config.py`, section `emotion`)

| Key | Default | Meaning |
|-----|---------|---------|
| `emotion.decay_per_tick` | 1.5 | How fast each dimension drifts back toward baseline. |
| `emotion.llm_spike_max` | 15.0 | Cap on an LLM-declared feeling spike. |
| `emotion.recall_spike_scale` | 0.25 | Intended scale for memory-recall re-feel (the client applies its own subtle factor). |
| `emotion.spike_scale` | 1.7 | Server-side scale for label+intensity mapping on `/emotions/map`. |
| `emotion.vital_scale` | 0.25 | How strongly re-felt emotions move mental vitals (0 = off). |
| `emotion.rel_scale` | 0.25 | How strongly re-felt emotions move the relationship toward the speaker (0 = off). |

---

## Files

| File | Role |
|------|------|
| `engine/emotion.py` | dimensions/axes, `spike`/`decay`/`describe`, `LABEL_TO_DIM`, `VITAL_EFFECTS`, `RELATIONSHIP_VALENCE` |
| `engine/derive.py` | folds `rel:`/drive-tagged experiences into consumed/trust/fear profiles |
| `routes/player_ops.py` | `handle_spike_emotion`, `handle_map_player_emotions` |
| `routes/players.py` | route registration for `/emotions` and `/emotions/map` |
| `static/js/shared/emotion-mapper.js` | `EmotionMapper.resolve` (keyword + semantic) |
| `static/js/agent/prompt-builder/memory-context.js` | self-recall re-feel (`_respikeFromMemories`) |
| `static/js/agent/prompt-builder/room-context.js` | social-recall re-feel (`_fireSocialRecall`) |

## Related

- [[AI & Narration/Memory System]] — memory storage, editor, generator, and the `memory_emotions` field
- [[Characters/Vitals System]] — Sanity / Entertainment / Social
- [[Gameplay/Turn Queue & Human Turns]] — where the WITNESSED block is built
