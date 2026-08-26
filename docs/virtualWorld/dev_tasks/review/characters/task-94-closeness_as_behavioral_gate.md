---
group: Agent AI & Behavior
wiki: "[[Characters/NPC Behavior System]]"
---
# Closeness as Behavioral Gate

**Filed**: 2026-07-22
**Priority**: Medium
**Status**: In Review — implemented 2026-08-21 (cheap variant), moved from todo/

## Implemented (2026-08-21) — the no-extra-LLM-call variant

- **Prompt-side gate**: `character-state.js` `buildRelationshipContext` now appends a behavioral clause per
  tier via `relationshipGuidance(closeness)` — e.g. "…a rival (-30/100) — keep interactions cold and
  minimal; never turn your back on them". Injected into observe/decide/react phases (existing plumbing).
- **Heuristic closeness movement** (no sentiment LLM calls):
  - Directed whisper (task-248): +2 both directions (`narration.py`, after event build).
  - `give_item`: recipient → giver +5 (`item_actions.py`).
  - Attack: −30 attacker-directed already existed in `combat.py`.
- **Deliberate deviation from the doc's steps 1+2+4**: no boolean reaction LLM call, no post-conversation
  sentiment LLM call, no new endpoint — the guidance clauses shape tone inside prompts the engine already
  sends, and outcomes move closeness heuristically. Same realism, zero added latency/cost.
- Tests: `tests/test_realism_perception.py::TestClosenessHooks` (2 tests).

---

## Summary

Relationships with closeness values exist but are purely informational — injected into the prompt as context. humanoidagents uses closeness as a **behavioral gate**: it checks closeness before deciding whether to react to another agent, and adjusts dialogue tone based on closeness level.

This task makes closeness actively gate agent social behavior, not just decorate the prompt.

---

## Evidence

humanoidagents `humanoid_agent.py:357-373`:

```python
def get_closeness_between_self_and_other_agent(self, other_agent):
    closeness_value = self.social_relationships[other_agent.name]['closeness']
    if closeness_value < 5:    description = "distant"
    elif closeness_value < 10: description = "rather close"
    elif closeness_value < 15: description = "close"
    else:                      description = "very close"
```

humanoidagents `humanoid_agent.py:376-407` — closeness is included in the **boolean reaction check**:
```
Should {self.name} react to the observation? Please respond with only yes or no.
```

humanoidagents `humanoid_agent.py:212-219` — closeness adjusts **after conversation**:
```python
def get_sentiment_about_conversation(self, conversation_history, other_agent):
    prompt = f"Did {self.name} enjoy the conversation?"
    response = self.LLM.get_llm_response(prompt)
    self.social_relationships[other_agent.name]['closeness'] += 1 if 'yes' else -1
```

**Virtual_world currently:**
- `player.py:122-124` — relationships dict with closeness (-100 to 100)
- `player.py:233-271` — `update_relationship()` / `get_relationship_description()`
- `prompt-builder.js:80-91` — `buildRelationshipContext()` injects labels like "Piper considers Tommy a friend (closeness: 50/100)"
- BUT: no behavioral consequences — closeness doesn't gate reactions, doesn't affect dialogue initiation, doesn't change after conversation

---

## Changes

### 1. Add closeness gate to agent reaction check

In `agent-engine.js`, before the agent generates a reaction/speech, add a boolean check like humanoidagents:

```
Closeness: Piper is feeling distant/close/very close to Tommy
Should Piper react to what just happened?
```

If the LLM says no, the agent doesn't generate speech that turn (just inner monologue + action).

### 2. Add post-conversation closeness adjustment

After an agent speaks to another character, make a lightweight LLM call:
```
Piper just spoke with Tommy: "{dialogue}"
Did Piper enjoy this interaction? Answer yes or no.
```
Adjust closeness by ±5 (on the -100 to 100 scale).

### 3. Include closeness in reaction prompt generation

The closeness description is already in `buildRelationshipContext()` — but make sure it appears in the reaction-prompt path (not just the observation prompt). Check that `buildReactionPrompt()` injects relationship context. Currently it does at line 586, so this may already work — verify.

### 4. Add backend endpoint for closeness adjustment

Currently `player.py:233` has `update_relationship()` but it's only called from specific actions (attack, etc.). Add a generic endpoint or method so the frontend can report closeness changes after LLM sentiment analysis.

---

## Test

1. Set up two characters with closeness=0 (neutral)
2. Observe that they rarely react to each other's actions
3. Increase closeness to 75 (close friend)
4. Observe that they react more frequently and warmly
