---
group: Agent AI & Behavior
---
# Rich Memory Toggle — LLM-Generated vs Template Observations

**Filed**: 2026-07-29  
**Completed**: 2026-07-30  
**Priority**: Low  
**Status**: Done

---

## Summary

Add a setting under LLM/Agent config that controls how observations are stored:

- **Template mode** (current, but in past tense): Fast, consistent, low token cost.
  ```
  [5 minutes ago] 👁️ Saw the Blizzard Forest Clearing — freezing and bright, smelled like pine.
  ```

- **LLM-generated mode** (rich): Uses the LLM to write a narrative observation in past tense. Higher quality, more tokens, slower.
  ```
  [5 minutes ago] 👁️ I stood at the edge of the Blizzard Forest Clearing, the wind cutting through my coat. A path led toward a two-story house through the driving snow. An axe sat embedded in a stump — useful, if I come back for it.
  ```

### Implementation

- The setting controls whether `agent-engine.js:185` uses the template or dispatches an LLM call to generate the observation
- LLM-generated observations should be stored asynchronously (fire-and-forget after the main step completes)
- Configuration field in the LLM settings UI (e.g. `"rich_memories": true/false`)
- Both modes should produce past-tense output

### Scope
- `static/js/agent-engine.js` — observation storage at line 185, added `_generateRichObservation()`
- `static/js/config.js` — added `richMemories` config field with persistence
- `static/js/ui/settings-view.js` — populate form for the toggle
- `templates/index.html` — toggle UI in Agent Behavior settings group

### Implementation Notes
- Template observation stored immediately (fast path) regardless of mode
- When `richMemories` is on, an async fire-and-forget LLM call generates a narrative version and stores it as an additional `observation` memory
- No blocking — agent step continues without waiting for the LLM call
- Failures silently caught (non-critical)
- Both modes produce past-tense output
