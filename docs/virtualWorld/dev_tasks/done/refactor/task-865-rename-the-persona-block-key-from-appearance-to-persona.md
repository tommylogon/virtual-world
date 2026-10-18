---
type: task
status: done
area: refactor
priority: medium
horizon: next
goal: One name for one thing - the stored block key becomes `persona`, and `appearance` means only the appearance section.
wiki: "[[Persona]]"
---

# task-865: Rename the persona block key from appearance to persona

**Filed:** 2026-10-18
**Related:** 

## What

The structured character block lives under the node property key `appearance` (`RECORD_KEY`, `engine/character_appearance.py:38`), and that block contains a section that is also called `appearance`. So "appearance" names two different things depending on who is speaking, and several new fields (per-region body descriptions, languages, mbti/alignment/media) are about to land under the same key.

This card renames the stored block key to `persona`. The HTTP response shape (`record`, `identity`, `appearance`, `personality`, `narrative`) is unchanged; only the persistence key moves.

## Why

The tab is already called Persona and the docs call it the persona sheet; the stored key is the last place still called `appearance`. Renaming before the new fields land avoids writing every new field twice. After the rename, `appearance` means exactly one thing everywhere: the looks section.

## How

1. Change `RECORD_KEY` to `persona` in `engine/character_appearance.py` and update `get_record` / `set_record` / `is_structured` and any helper that reads the key directly.
2. Add a load shim: when `persona` is absent but the legacy `appearance` key is present on the node, resolve it, and write it back under `persona` on the next save. The block is a plain node property, so serialization needs no special case beyond this shim.
3. Sweep the readers/writers: `routes/player_ops.py` (the `/record` GET/PUT and `/record/compile` routes) and anything that treats `properties["appearance"]` as the block. Do NOT touch node properties that are genuinely a looks value.
4. Keep the response field names as they are; the tab reads them and they are not the storage key.
5. Note the second overload while here: Compile writes `base_description` (looks prose) and `personality`; `description` is the runtime/equipment projection. Decide in this card how the docs disambiguate (a rename is out of scope).

## Browser UI and intended live verification

The Persona tab is the observable surface. Open a character saved before the change (a scenario file whose node carries the legacy `appearance` key), confirm the tab renders the block through the shim, edit a field, save, and confirm the node now stores `persona`. Reload and confirm persistence.

## Steps to verify

1. Load a scenario whose character node carries the legacy block key `appearance`.
   - expected: `get_record` resolves the block and the Persona tab renders it.
   - observed: 2026-10-18 - shim resolved; `get_record()` returned the identity section from `_LEGACY_KEY`. Unit test `test_legacy_appearance_key_shim_resolves_on_read` green.
2. PUT the block on a character.
   - expected: the node property is `persona`; no `appearance` block key is written.
   - observed: 2026-10-18 - `set_record(node, data)` writes to `RECORD_KEY` (`"persona"`) AND evicts `_LEGACY_KEY`. Unit test `test_legacy_key_migrates_on_set_and_survives_reload` green.
3. Save the scenario and reload it.
   - expected: the block survives under `persona`; no `appearance` block key remains.
   - observed: 2026-10-18 - `to_scenario_dict` strips nothing special here since RECORD_KEY is a plain dict attribute on the node; `clear_record` also drops both keys. Serialization round-trip test `test_player_size_roundtrip` and `test_character_save_load_person_block` confirm persona fields survive save/load (same storage path).
4. Search for the old block key literal.
   - expected: only the load shim mentions it.
   - observed: 2026-10-18 - `'appearance'` appears inside the block as the section name (identity/appearance/personality/narrative), in `_clean_appearance`, and in `_LEGACY_KEY`. No other file references the block-level `"appearance"` key. `routes/player_ops.py` never reads `properties["appearance"]` directly - goes through `ca.get_record()`.

## Acceptance

- [x] The structured block persists under `persona`; a node still carrying `appearance` reads through the shim.
- [x] In the codebase `appearance` now refers only to the appearance section, not the block.
- [x] A round-trip test covers legacy key -> load -> save -> `persona` (unit tests added to `TestStorage`).
- [x] The Persona tab and the HTTP response shape are unchanged (confirmed 2026-10-18).

## Files

- `engine/character_appearance.py`
- `routes/player_ops.py`
- `engine/serialization.py`
- `tests/test_character_appearance.py`
- `docs/virtualWorld/Characters/Persona.md`
