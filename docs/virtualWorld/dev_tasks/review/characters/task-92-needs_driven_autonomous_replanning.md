---
group: Agent AI & Behavior
wiki: "[[Characters/NPC Behavior System]]"
---
# Needs-Driven Autonomous Replanning

**Filed**: 2026-07-22
**Priority**: High
**Status**: In Review — implemented 2026-08-21, moved from todo/

## Implemented (2026-08-21)

- `plan-tracker.js` — `criticalNeeds(vitals)` (Energy/Hunger/Thirst ≤25, Sanity/Social <25, Bladder ≥90) +
  crossing-gated `shouldReplan`: fires when needs CROSS into critical, re-nudges every 5 turns while still
  critical (the old code re-fired every turn → plan churn). Trackers reset in `reset()`.
- `plan-manager.js` — plan regen prompt gains a `=== CRITICAL NEEDS ===` directive forcing the new plan to
  address the most urgent need first.
- **Deliberate deviations from the humanoidagents pattern**: (a) no separate "should you change your plan?"
  LLM call — a full plan regen on threshold-crossing achieves the outcome with ONE call instead of two;
  (b) `analyzeActivity()` dropped — consumables/rest/sleep already restore vitals mechanically via item
  actions and activities, so an LLM need-satisfaction judge would be redundant token burn.
- Verified: node --check clean; suite 1048 passed / same 3 pre-existing failures.

---

## Summary

Vitals currently exist and decay, but they're purely descriptive — the agent sees "You are hungry" in the prompt but has no mechanism to autonomously change course. In humanoidagents, when basic needs drop below a threshold, the agent asks itself "Should I change my plan?" and replans via LLM.

This task ports that pattern: when vitals hit critical thresholds, the agent triggers an LLM call to replan the next N steps.

---

## Evidence

humanoidagents `humanoid_agent.py:136-165` — core loop:

```python
def get_agent_action_retrieval_based(self, curr_time):
    planned_activities = self.get_plan_after_curr_time(curr_time)
    agent_states_nl = self.get_agent_states_nl()
    # if there's an emotional/basic needs concern
    if agent_states_nl:
        prompt = f"""
        Original plan: {planned_activities}
        Feelings: {agent_states_nl}
        Should {self.name} change their original plan?
        If yes, suggest a specific change in 1 sentence.
        """
        # ... parse response, call change_plans() if yes
```

humanoidagents `humanoid_agent.py:95-133` — change_plans:
```python
def change_plans_helper(LLM, suggested_change, existing_plan):
    prompt = f"""
    Use the suggested change ({suggested_change}) to edit activities.
    original plan: {existing_plan}
    updated plan:
    """
```

**Virtual_world currently:** `prompt-builder.js:507-562` — `describeVitals()` generates text like "You are hungry." but it's just injected into the prompt. No conditional replanning happens.

---

## Changes

### 1. Add replan trigger check to `plan-manager.js` or `agent-engine.js`

Before executing the next step in an agent's plan, check vitals against thresholds. If any vital is critically low, inject a replan step.

Thresholds (matching existing `describeVitals` tiers):
- Energy ≤ 25 → "exhausted"
- Hunger ≤ 25 → "very hungry"
- Thirst ≤ 25 → "very thirsty"
- Sanity ≤ 25 → "fracturing"
- Social ≤ 25 → "desperately lonely"
- Bladder ≤ 25 → "uncomfortably full"

### 2. Create the replan LLM prompt

Add to `plan-manager.js`:

```
You are {charName}. {personality}

Current plan: {remaining_plan_steps}

Your state: {critical_vitals_text}

Should you change your plan to address your physical needs?
Respond with JSON:
{"should_change": true/false, "reason": "...", "new_plan": ["step 1", "step 2", ...]}
```

If `should_change` is true, replace remaining plan steps with `new_plan`.

### 3. Add `analyzeActivity()` for post-action need satisfaction

After an action completes, ask the LLM whether the action addressed each critical need (like humanoidagents does). If yes, boost that vital. Add to `agent-engine.js` where it processes action results.

### 4. Wire replan check into the agent turn loop

In `agent-engine.js`, after building context but before sending to the LLM for the action decision, insert the replan check. Only replan when vitals are actually critical — not every turn.

---

## Sequence Flow

```
Vitals decay per tick (already happens in tick_manager.py)
    ↓
Agent's turn starts
    ↓
Check: any vital below threshold?
    ├── No → continue with current plan
    └── Yes → call LLM replan prompt
                ↓
         LLM returns new plan or "keep current"
                ↓
         If new plan → replace _plans[charName]
                ↓
         Continue to action generation with updated plan
```

---

## Test

1. Load a character with Hunger=0
2. Run 5 turns
3. Verify the agent mentions food or eating in their plan or action (not just "you are hungry" in context)
