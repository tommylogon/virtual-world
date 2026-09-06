# Agent Quality & Evaluation — Research

## The Problem
Virtual World has a working LLM agent engine, but no way to answer: **are the NPCs good?** Not "did the LLM call succeed" — but "does this NPC feel like a character, not a chatbot?"

## What Exists in VW
- Agent engine with reactive think→act→react pipeline
- Structured JSON output (inner_monologue, action, speech, emote)
- Memory system with importance scoring and reflection
- Relationship and emotion systems
- Event stream with parse-error inspection
- Manual mode for debugging

## What's Missing
- No NPC quality metrics
- No player engagement measurement
- No A/B testing framework for prompts/models
- No benchmark scenarios
- No way to compare NPC behavior across model changes

## State of the Art

### 1. LLM-as-Judge (Industry Standard)
**Approach:** Use an LLM to evaluate NPC responses across dimensions:
- **Persona consistency** — does the response match the character's personality?
- **World coherence** — does the response respect world facts?
- **Conversational quality** — is it natural, engaging, non-repetitive?
- **Action validity** — does the proposed action make sense in context?

**Evidence:** CPDC 2025 winning solution used LLM-as-judge with these exact dimensions. Ranked 1st in Task 2 API.

**Trade-offs for VW:**
- Pro: Cheap, fast, automatable
- Con: LLM judge can have the same biases as the evaluated LLM
- Con: Doesn't capture player-specific reactions

### 2. Behavioral Metrics (Game Industry)
**Approach:** Measure observable player behavior:
- Conversation length (do players keep talking or disengage?)
- Return rate (do players come back to interact with this NPC?)
- Action diversity (does the NPC elicit varied player responses?)
- Relationship investment (do players use relationship-building actions?)

**Evidence:** Character.AI tracks conversation length and return rate as primary quality metrics. Inworld AI uses "player engagement time per character."

**Trade-offs for VW:**
- Pro: Measures actual player reaction, not just text quality
- Pro: Easy to instrument (already have event stream)
- Con: Requires live players, not testable offline
- Con: Lagging indicator (need hours of play to measure)

### 3. Human Evaluation (Academic Standard)
**Approach:** Human raters score NPC responses on believability, coherence, and engagement.

**Evidence:** Park et al. (Generative Agents) used human crowdworkers to rate agent behavior. Sam Cox (2023) analyzed player feedback from LLM-driven games.

**Trade-offs for VW:**
- Pro: Gold standard for quality
- Con: Expensive, slow, not scalable
- Con: Subjective — different raters have different standards

### 4. Automated Regression Testing
**Approach:** Fixed test scenarios with expected outcomes. Run after every prompt/model change.

**Evidence:** Gigax framework uses "dialogue simulation tests" — scripted interactions that verify NPC responses contain expected keywords or states.

**Trade-offs for VW:**
- Pro: Catches regressions immediately
- Pro: Can run in CI
- Con: Brittle — LLMs are non-deterministic
- Con: Only tests known scenarios, not edge cases

## Recommended Approach for VW

### Tier 1: Automated (Run on Every Change)
```python
def test_npc_quality(npc, scenario):
    """Run NPC through fixed scenarios, check output quality."""
    responses = []
    for input in scenario.inputs:
        response = npc.respond(input)
        responses.append({
            "input": input,
            "response": response,
            "persona_match": llm_judge_persona(npc, response),
            "world_coherent": llm_judge_coherence(npc, response, world),
            "parseable": response_parser.validate(response),
        })
    return {
        "persona_score": mean(r.persona_match for r in responses),
        "coherence_score": mean(r.world_coherent for r in responses),
        "parse_rate": mean(r.parseable for r in responses),
    }
```

### Tier 2: Behavioral (Track in Live Play)
```python
# Already available from event stream:
metrics = {
    "conversation_turns": count_turns_between(npc, player),
    "return_interval": time_between_visits(npc, player),
    "action_diversity": unique_actions_elicited(npc, player),
    "relationship_delta": relationship_change_during_interaction(npc, player),
}
```

### Tier 3: Human (Spot Checks)
- Periodically record interesting NPC interactions
- Rate 5-10 per week on believability scale
- Use for calibration of automated metrics

## Implementation Plan

### Phase 1: LLM-as-Judge (1-2 days)
1. Build `evaluate_npc_response()` function
2. Run on every NPC turn in debug mode
3. Log scores to event stream
4. Add threshold alerts (persona_score < 0.7 → warn)

### Phase 2: Behavioral Metrics (2-3 days)
1. Instrument event stream for conversation metrics
2. Build dashboard showing NPC engagement over time
3. Identify underperforming NPCs automatically

### Phase 3: Regression Tests (3-5 days)
1. Curate 20-30 test scenarios per NPC
2. Build test runner that compares against baseline
3. Integrate into dev workflow (run before prompt changes ship)

## Key Insight
**You don't need perfect evaluation — you need good enough to catch regressions.** A simple LLM-as-judge with 3 dimensions (persona, coherence, parseability) catches 80% of prompt-induced quality drops. Add behavioral metrics for the other 20% that automated tests miss.
