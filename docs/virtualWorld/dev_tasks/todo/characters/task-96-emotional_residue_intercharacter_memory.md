---
group: Agent AI & Behavior
wiki: "[[AI & Narration/Memory System]]"
---
# 🧠 Emotional Residue + Inter-Character Memory Planting — Dev Task

**Filed**: 2026-07-22
**Status**: In Review — core loop implemented 2026-08-23. `engine/emotion.py`
(7 dims, baselines, clamped spikes, baseline-drift decay, band phrases,
LLM-declaration normalizer), runtime_config tunables (`emotion.decay_per_tick`,
`emotion.llm_spike_max`, `emotion.recall_spike_scale` + SCHEMA entries),
Player persistence (`emotions_map/spike_emotion/decay_emotions/load_emotions`,
serialized in to_dict + engine/serialization both directions), tick_manager
decay hook, routes `GET/POST /api/players/<name>/emotions`. Frontend round trip:
schema-fragments teach `"emotion":{"label","intensity"}` in decide/react JSON;
response-parser extracts it; agent-engine spikes at all three parse sites and
threads felt emotion into `_storeReactionMemory` → memory entries carry
`emotion`; `buildMemoryContext` re-spikes (throttled 5s, strongest hit) when
emotional memories surface in I REMEMBER; YOUR STATE renders backend-computed
`emotions_description` band phrases with legacy fallback. Tests:
`tests/test_emotion.py` 25 cases; suite 1092 passed. Also fixed a foreign WIP
breakage en route: tuple edge-types now flatten in `graph.resolve_edge_types`.
NOT verified live yet (dev server was down post-implementation) — first real
run should show Mood lines in prompts and emotion fields in LLM JSON.
Inter-character planting (path 3) intentionally deferred to a follow-up.

## What to expect on your next run

**Event stream: nothing new in format** — no new log lines. The fingerprints are
in content:
- **Exports / prompt echoes**: a `Mood:` line appears in YOUR STATE once affect
  deviates from baseline ("Mood: You are terrified — your heart hammers…"). Near
  baseline = absent, so early turns may show nothing.
- **LLM JSON** (visible via Show LLM Logs or export echoes): decide/react responses
  now include `"emotion":{"label":"afraid","intensity":6}`.
- **Behavior**: after a nasty event, the mood line persists and colors the next few
  turns, decaying per tick (`emotion.decay_per_tick`, tunable in Engine Config →
  emotion section). When an emotional memory later resurfaces in I REMEMBER, the
  character re-feels it — watch for reactions that seem to come "out of nowhere";
  check what memory just got recalled.

**Taco Bell example**: Miki reacts badly mid-date → `afraid` spikes → her Mood line
turns tense for several turns even though nothing new happened. Later, semantic
recall surfaces the under-booth memory carrying its fear tag → re-spike without any
new trigger.

**Tuning**: all three knobs live in Engine Config (`emotion.decay_per_tick`,
`emotion.llm_spike_max`, `emotion.recall_spike_scale`). If moods are flat, lower
decay; if melodramatic, raise decay or drop llm_spike_max.

---

## New design (2026-08-23)

### Emotion model — `engine/emotion.py`

Per-character affect map of numeric dimensions (NOT the old single-slot
`player.emotion`), inspired by `F:\AI\Aura\Diary`'s six stats + range→phrase
rendering, adapted to VirtualWorld:

- Dimensions: `happy, sad, afraid, angry, envious` (+`affectionate`, `disgusted`
  as stretch). Each 0–100, default neutral baseline (50 for happy/affectionate,
  ~10 for negative ones? — decide in implementation; Diary uses 0–100 with
  descriptive bands).
- `EmotionManager.set_spike(char, emotion, delta, source)` — clamp 0..100.
- Per-tick decay toward baseline in `tick_turn()` (Diary decays per day; we're
  tick-driven — decay rate via `runtime_config` per task-304 rule).
- Serialization on the player so state survives save/load.
- Prompt rendering: `format_emotional_state()` style band phrases ("afraid:
  dreading what's around the corner") into `=== YOUR STATE ===`, replacing the
  current single-emotion line.

### Three input paths (the round trip)

1. **Right now**: react-phase LLM declares a felt emotion each turn (add
   `emotion: {label, intensity}` field to think-decide/react output schema,
   prompt-builder) → spike. Witnessed events with emotional content (combat,
   gifts, threats) can add secondary spikes via emote tagging (original Layer 1).
2. **Remembered** (ties to task-91): memory entries gain an `emotion` tag at
   creation ("I remember feeling afraid"). When semantic recall surfaces a
   memory in `=== I REMEMBER ===`, apply a FRACTION of its original impact as a
   spike — remembering being betrayed makes you angry again. This only becomes
   powerful once task-91 embeddings are live (recall by meaning, not keyword).
3. **Inter-character planting** (original Layer 3 survives): targeted emotes
   plant perspective memories on recipients (`"Lyrie smiled warmly at you"`),
   which then carry their own emotion tags and re-spike via path 2.

### Output paths

- YOUR STATE phrase line every turn (mood colors all decisions).
- Closeness system stays separate (task-94 gates); a future pass may let
  sustained emotions nudge relationship drift — explicitly out of scope here.

### Files likely touched

- `engine/emotion.py` (new), `engine/tick_manager.py` (decay hook),
  `player.py` (serialization), `virtual_world_engine.py` (manager wiring)
- `static/js/agent/prompt-builder/character-state.js` (YOUR STATE block),
  `action-normalizer.js`/agent-engine (parse `emotion` field)
- `prompt-builder/memory-context.js` (re-spike on recall)
- `routes/action.py` or settings route exposing `/api/emotion/<name>`
- Tests: `tests/test_emotion.py` (decay math, clamping, serialization,
  recall-respike, planting)

### Explicit non-goals

- No event-table/d20 choice machinery from Diary (agents act freely).
- No Neo4j — player fields suffice.
- No UI beyond inspector display of current emotions (optional).

---

## Original 3-layer plan (superseded, kept for reference)

### Layer 1: Emote Intensity Tagging

The narration LLM already generates emote descriptions. Add `emotion` + `intensity` to its response.

### Layer 2: Emotion Decay Tracker

Natural fade of emotional state over game ticks. No prompt changes needed — `buildEmotionContext` already injects `player.emotion.description`.

### Layer 3: Inter-Character Memory Planting

When an emote targets specific characters, plant a copy in their memory too.

(Original detailed checklists removed 2026-08-23 — see git history if needed.)
