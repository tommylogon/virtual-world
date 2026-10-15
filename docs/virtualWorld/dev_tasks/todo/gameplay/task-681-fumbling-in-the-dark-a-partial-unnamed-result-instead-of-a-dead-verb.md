---
type: task
status: todo
area: gameplay
priority: medium
---

# task-681: Fumbling in the dark: a partial, unnamed result instead of a dead verb

**Filed:** 2026-10-04
**Related:** 

## What

In an area below 20 ambient light the panel now offers Feel around the shape (panel-side masking shipped), but engine/items/examine_actions.py line 143 raises a too-dark error, so the verb still returns nothing. Decide and implement the dark examine semantic: the natural one is a partial, unnamed impression (shape, texture, temperature) with no name revealed, rather than an error. Scope it so agents in the dark get the same partial read instead of being handed an exception string. This changes dark-area behaviour for the agent prompt path too, so it needs its own decision rather than a panel-side patch.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: game view in an area below 20 ambient light → select an item → **Feel around** or use the normal `examine` action. Read the resulting action line and the character prompt/event stream.

Current availability: the panel already offers **Feel around** in darkness, but the card records that `examine` still returns a too-dark error. The desired partial unnamed impression and shared agent behavior are not claimed as implemented.

Live steps when available:
1. In a scratch area below 20 ambient light, select a distinct object and choose **Feel around**. Then invoke `examine` on that same object.
   - expected: both paths give a partial impression such as shape, texture, or temperature without revealing the item's name or returning the too-dark exception.
2. Repeat with a second object of a different shape and texture.
   - expected: the partial result changes to reflect that object's actual physical properties; it does not reuse the first object's description.
3. Run an agent turn in the same dark area and inspect the prompt and response for the examine result.
   - expected: the agent receives the same partial unnamed information as the panel, not the engine exception string or the hidden item name.
4. Raise the light above the documented threshold and examine the object again.
   - expected: the normal named examination becomes available; the dark partial path does not mask lit-area behavior.

This section is not a claim that planned UI exists or works today.
