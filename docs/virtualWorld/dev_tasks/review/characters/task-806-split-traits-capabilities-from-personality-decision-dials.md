---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-800, task-801, task-802, task-805]
blocked_by: [task-800]
---

# task-806: Split traits (capabilities) from personality (decision dials)

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]], [[task-801-disposition-action-features-verb-score-contributions]], [[task-802-disposition-character-weights-from-traits-plus-live-modifiers]], [[task-805-disposition-whispers-render-the-score-registry-as-words-for-the-llm]]
<!-- deps:end -->

## What

Two homes, two roles: `traits` keeps capabilities and hooks (dark_vision, hardy, phobias); a NEW key holds the 0..1 decision dials. Adds `Player.personality_dials` (a key distinct from the prose `personality` string), `engine.traits.DIAL_TRAITS` / `DIAL_NEUTRAL` / `TraitSystem.dial_value`, the serialization seam, and makes `disposition._dial` read the dials first. The character editor's Bio tab now has a **🎚 Personality dials** section that authors them, saved through `POST /api/players/<name>` with a `personality_dials` payload.

## Why

The catalogue wants normalized floats, but `player.traits[tid]` is `True|str|number` and the `personality` field is a prose string - three things wearing the name. Separate them or they collide: capabilities answer "can this character do X", dials answer "how much do they weigh X".

## How

- `player.py`: `self.personality_dials = {}` (distinct from `self.personality`).
- `engine/traits.py`: `DIAL_NEUTRAL = 0.5`, `DIAL_TRAITS`, and `TraitSystem.dial_value(player, trait_id)` which reads `personality_dials` first, then a truthy capability in `traits`, defaulting 0.5.
- `engine/disposition.py`: `_dial` delegates to `TraitSystem.dial_value`.
- `engine/serialization.py`: the payload carries `personality_dials`; `normalize_dials` clamps/coerces on load (an old save loads to `{}`); the lite projection strips it.
- `routes/player_ops.py`: `handle_update_player` accepts `personality_dials` and writes it through the same `normalize_dials`.
- `static/js/inspector/agent-view.ts`: a **🎚 Personality dials** section in the Bio tab (`_dialRowHtml`, `_renderDialsSection`, `_collectDials`, `_saveDials`, `_addDial`, `_deleteDial`), mirroring the goals editor. Each row is a trait id + a 0..1 value; save on blur via `ApiClient.updateCharacter(name, { personality_dials })`.

A trait may be a capability, a dial, or both - `DIAL_TRAITS` is the dial set; `Player.traits` is the capability set.

## Steps to verify

1. In the character editor's Bio tab, edit a character's personality dials beside their prose.
   - expected: the dials save and reload separately from the prose personality string.
   - observed: VERIFIED 2026-10-13, live on localhost:4444. `ApiClient.updateCharacter('Arix', { personality_dials: { cowardly: 0.9 } })` -> `/api/state` carries `personality_dials {cowardly: 0.9}`, the editor's `_renderDialsSection` renders a `dial-row` for `cowardly` 0.9, and the derived weight is `relief.weight.witness = 0.8` ((0.9 - 0.5) * 2.0). The dial was reverted to `{}` after verification.
2. In the 🧠 Mind panel for that character, both the prose and the numeric dials are shown.
   - observed: PARTIAL 2026-10-13, live on localhost:4444. The "Disposition - what they weigh" block renders the dial (`cowardly 0.90`) and the weight it moves (`relief.weight.witness weight +0.80`). The prose `personality` string stays in the Bio tab's Personality field, not in the panel.

## Acceptance

- [x] traits holds capabilities; personality holds dials (`personality_dials`; `dial_value` reads the dials first, `traits` as the capability fallback).
- [x] The prose personality string is untouched.
- [x] Existing characters load unchanged - dials default neutral.
- [x] The dials are authorable: the Bio tab's editor writes them through `POST /api/players/<name>`; verified live (author -> weight -> panel).
- [x] 41 passed in `tests/test_disposition.py`.

## Files

- `player.py` (`personality_dials`)
- `engine/traits.py` (`DIAL_TRAITS`, `DIAL_NEUTRAL`, `TraitSystem.dial_value`)
- `engine/disposition.py` (`_dial` delegates)
- `engine/serialization.py` (`personality_dials` + `normalize_dials` + lite strip)
- `routes/player_ops.py` (`personality_dials` accepted on update)
- `static/js/inspector/agent-view.ts` (the dials editor)
- `tests/test_disposition.py`

## Browser UI and intended live verification

Intended UI home: Character Inspector → Bio → **🎚 Personality dials**; save the character, run its decision, and inspect the resulting weight/choice in the behavior panel or event trace.

Current availability: the card records the Bio editor writing `personality_dials` through `POST /api/players/<name>`, with neutral defaults for existing characters and live author → weight → panel evidence. This section does not claim a new storage home beyond that field.

Live steps when available:
1. Open Bio for a character, change one Personality dial, save, and reopen the tab.
   - expected: the dial retains its authored value in `personality_dials`; prose `personality` and capability `traits` remain unchanged.
2. Run the same decision with the dial at neutral and at an extreme value; inspect the behavior/decision panel.
   - expected: `disposition._dial` reads the dial first and the corresponding decision score/choice moves predictably.
3. Load an existing character with no dial record.
   - expected: the editor shows neutral values and the character continues to load without migration errors.
4. Compare `traits`, `personality_dials`, and the prose personality in `/api/state` after save/reload.
   - expected: capabilities, decision dials, and personality prose remain separate and each has one source.

This section is not a claim that every dial has been browser-verified today.
