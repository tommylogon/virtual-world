---
type: task
status: todo
area: characters
priority: medium
---

# task-507: Structured appearance & personality fields for characters (optional, LLM-fillable)

**Filed:** 2026-09-24
**Related:** task-96, task-505

## Goal

Add OPTIONAL structured appearance/personality fields to characters, alongside the existing prose. Two authoring modes must both work: (a) prose-only (personality + base_description), or (b) full structured fields. Curated, mechanic-backed set only: appearance {height_cm, weight_kg, build, hair{color,length,style}, eyes{color}, skin{tone}} and personality {likes, dislikes, fears, kinks, turn_offs}. Reference other entities by id (never display name). After fields are set, run 'generate description' ONCE to render prose (description already auto-generates from base_description + equipment, so structured fields feed it); structured is source of truth where present, prose is the narrative layer and stays the LLM voice. LLM-fill flow: send the model the JSON schema of all fields plus the character card/personality/description and have it populate them; the rest hand-authored. Mechanics to unlock: contact lenses set hair/eyes, haircut, weight gain/loss (Hunger/traits/items), kinks -> arousal spike, turn_offs -> disgust / negative arousal (maps to engine.emotion axes), likes/dislikes/fears -> targeting by gifts/threats/dialogue. Reuse graph-editor (WorldGraph) field names where they overlap so authored persons import cleanly. Fields optional + defaulted, so existing prose-only library characters and saves are unaffected (migration). Grow per-feature; do not dump the full editor catalog (media/mbti/alignment have no runtime mechanic).

## Acceptance

- TODO
