---
type: bug
status: todo
area: prompting
priority: high
---

# bug-523: Plan grounding facts use unmasked real names, leaking strangers and rejecting targets the room showed

**Filed:** 2026-10-07
**Related:** task-700, task-447, task-610, task-448

## Goal

Planning must be able to target what the prompt showed. The grounding facts currently use players_in_area[].name (the real name) while the room display masks unmet strangers via PromptBuilder.anonymousName, so a plan step 'approach the man' is rejected and the rejection prints the character's real name. Invariant: the grounder's facts must be the exact handles the prompt showed, and a real name must never appear for a character the player has not met.

## Measured 2026-10-07, from a live kraktooth_goblin_camp turn (turns 11–12)

Belne is in Side Tunnels with two characters he has never met. His room context shows
them masked:

```
People here:
  - the woman (frightened) beside the the man — A vague shape in the gloom — .
  - the man (awake) at the tunnel to mines — A vague shape in the gloom — .
```

His plan step `approach the man` is then rejected, with the reason:

```
nothing to walk up to called "the man" - here: Rikka, Thrazz; paths: deep passage, ...
```

Two defects in one message: a target he was **shown** is rejected, and the rejection
**hands him the real names** (Rikka, Thrazz) of characters the prompt says he has not met
(*"If someone is shown by appearance rather than a real name, you haven't met them"*).

## Root cause

Three layers disagree about how to name a stranger:

- **The prompt masks.** `room-context.ts` renders each person via
  `PromptBuilder.anonymousName(charName, person.name, desc)` — "the woman".
- **The matcher accepts the mask.** `engine/matching.py:683` — *"otherwise 'approach the
  woman' fails against a stranger"* — resolves the appearance label via
  `unknown_display_name()`. So `name the woman as …` and `approach the woman` resolve
  server-side.
- **The grounder does not.** `PlanGrounding.collectFacts`
  (`static/js/agent/plan-grounding.ts:109-111`) builds `people` from
  `state.players_in_area[].name` — the **real name** — so it compares against
  `Rikka, Thrazz` and rejects the masked handle the room actually showed, printing the
  real name in the reason.

## Why not route the grounder through the backend matcher

`engine/matching.py` is **backend**; `plan-grounding.ts` is **frontend**, run
synchronously per plan step during generation. Routing each step through the engine means
a round-trip per step and re-couples the client to engine internals. The minimal fix is
**not** to add a matcher call — it is to make the grounder's facts the **same handles the
prompt showed**. That is a frontend-only change with no round-trip, and it also removes
the leak (no real name is left in the facts or the rejection text). Note a matcher call
would **not** fix the leak on its own: a failed step still prints the fact list.

Fuzzy/alias/partial resolution (typos, "Vi" for Violet) is a separate, narrower concern:
the grounder should either match loosely (word-overlap, as its fact check already does) or
stop hard-rejecting a target it cannot resolve and let the backend be authoritative at act
time — which it already is.

## Acceptance (real criteria)

- **Invariant:** `collectFacts` produces the **exact handles the prompt shows** — masked
  (`anonymousName`) for a character the acting player has not met, real name once met.
- A plan step targeting a masked stranger the room showed (`approach the man`) **grounds**.
- A real name never appears in the facts or a rejection reason for an unmet character.
- **Test that runs the real `collectFacts`** against a fixture with an unmet stranger and
  asserts the masked handle is what grounds and that no real name leaks — the current
  `tools/unit/test_plan_grounding.js` hand-crafts `people: ['the woman', …]`, so it passes
  green while production diverges. The test must exercise `collectFacts`, not a
  hand-made list.

## Related, and a small adjacent artifact

`task-447` (nicknames/aliases) depends on this: a character can only nickname a target it
can address, and the only handle it has for a stranger is the one the room showed.

Adjacent cosmetic defect, same code path: with an empty person `description`, the dim-light
render (`room-context.ts:619`) yields *"A vague shape in the gloom — ."* — a dangling empty
clause. Fold the fix in if it is cheap, or file separately.
