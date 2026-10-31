---
type: task
status: done
area: characters
priority: medium
wiki: "[[Characters/Persona|Persona]]"
related: ["task-903"]
---

# task-923: Experience field split into structured intimacy history and boundaries

**Filed:** 2026-10-31
**Related:** task-903

## What

Split the monolithic `personality.experience` free-text field into structured sub-fields:
- `intimacy_level`: coarse maturity tier (e.g. `none`, `romantic_only`, `experienced`, `veteran`)
- `significant_partners`: past relationship references
- `hard_limits`: non-negotiable boundaries
- `soft_limits`: preferences open to negotiation with trust

## Why

Lumping relationship history, intimacy milestones, and hard boundaries into one unstructured string makes it impossible for `engine/intimacy.py` and consent checks to reliably guard prompts or evaluate trust thresholds.

## How

- Update `engine/character_appearance.py` schema to support the structured intimacy sub-fields while maintaining backward compatibility with single-string `experience`.
- Update the Intimacy fold in `static/js/inspector/mind-view.ts` with dedicated inputs.
- Wire consent and boundaries checks in intimacy prompt generation to read `hard_limits` and `boundaries`.

## Acceptance

- [x] Schema validates both legacy string and structured intimacy experience objects.
- [x] Hard limits and boundaries are evaluated directly during intimacy interactions.
- [x] Existing characters with string experience continue loading without error.


## Verification

- Completed and verified 2026-10-31.
- Unit tests in 	ests/test_character_appearance.py and 	ests/test_character_store.py passing.
- TS build green and zero em-dashes.
