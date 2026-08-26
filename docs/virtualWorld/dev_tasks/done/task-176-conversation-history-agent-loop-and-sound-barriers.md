# Task-176: Conversation-History Agent Loop & Sound Barrier Attenuation

**Status:** LANDED 2026-08-03 — verified live in the Task 3 sound-propagation test world (Jane doe / Jane two / John two).
**Source:** Live playtest of the sound-propagation test area. This session also fixed a pile of prompt/agent coherence bugs found while watching the run.

## 1. Conversation-history agent loop (reactive mode)

Replaced the 3-stateless-calls-per-turn flow (observe → decide → react) with a **2-call conversation loop**:

- **Think+Decide** (1 call): full room context → `{"inner_monologue","action","say","emote"}` in one shot (reuses the existing combined builder + `_parseReaction`).
- **Act**: execute the command/speech.
- **React** (1 call): slim prompt (`"Your surroundings are unchanged — see your observation above"`) + WHAT HAPPENED → `{"inner_monologue","say","emote"}`.

Every prompt is pushed to the per-character history as a `user` message and every LLM reply as an `assistant` message — `[system, user, assistant, user, assistant, ...]`. The agent now sees its own earlier words in context, so the "favorite colour changed between decide and react" self-contradiction class of bug is impossible (the react call literally contains its own prior "teal" assistant message). Context window manager (9500 tokens / 30 msgs) prunes per call.

Why this matters: the old flow made each phase a fresh `[system, prompt]` call with no memory of the agent's own recent output.

## 2. Sound barrier attenuation (`engine/sound.py`)

Open ways previously had **barrier 0** — a normal voice carried through *any* chain of open doors (a shout rang through an entire open map). New values:

| Way state | Barrier |
|---|---|
| open | **0.5** |
| see-through (window/grate) | **0.75** |
| closed | 1 |
| locked / blocked / hidden | 2 |

Result: normal speech (pen 1) reaches only the adjacent room through open doors (1 − 0.5 = 0.5, second door = 0); shout carries ~4 open doors or one closed + one open; scream ~6 open doors or two closed + one open. Propagation still BFS over cumulative barriers, no distance cap. COMMANDS table + task-149 spec updated to match.

## 3. Prompt system fixes (live-verified)

- **React defaults to silence** — inner_monologue + emote only; speak only if something genuinely demands it; explicitly told not to advance the plan in react (fixed the whisper→say→shout→scream rapid-fire escalation — one volume per turn now).
- **`action` must be a command** — never prose; `wait` is the sanctioned do-nothing command (added to COMMANDS table + validator; no-op dispatch, turn still passes).
- **Empty volume fields** — explicitly omitted, no `"say":""`.
- **Speech volume in event stream** — `💬 Jane doe whispers/shouts/screams: "..."` (was duplicated `[Jane doe] [Jane doe]` with no volume).
- **Self-appearance in second person** — `secondPersonDesc()` converts "A woman stands... her..." → "You are a woman who stands... your..." (pronoun + verb-agreement handling).
- **Rich item descriptions** — items render as `- Name: description` in good light (dim = names only, pitch black = none); restores the world_template-style narration that was lost in an earlier observe-context unification.
- **Voice labels from tags** — cross-room heard speech uses the speaker's tags (`female`/`male`/`girl`/`boy`/...), e.g. "a woman's voice said:", instead of a physical description. `player.tags` now survives save/load round-trip (was dropped in `load_from_dict`).
- **Memory fallback** — `=== I REMEMBER ===` always renders ("You don't remember anything relevant right now.").
- **System hints aren't memories** — rejected-action feedback stays in `lastActionResult`; the persistent memory is character-POV, not `[System]` meta-text.
- **Stranger rule moved to system prompt** (was observe-specific, mansion-specific wording).
- **Rules trimmed** — removed redundant bullets (one-action-per-turn, "go needs a destination", sound prose duplicated in the COMMANDS table).

## Verification

- Backend: `pytest tests/ -k "not mcp and not emote"` → green (442 passed, 1 skipped at the time of writing; barrier tests updated for 0.5/0.75).
- Live: whisper reached only the adjacent room, normal speech died at the open-door chain boundary, react stayed silent between volumes, `wait` executed as a no-op, tags survived reload.
