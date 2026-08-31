---
id: 361
title: Invalid Action Auto-Retry Setting
status: review
priority: medium
created: 2026-07-31
tags: [agent-engine, automation, ux]
---

# Invalid Action Auto-Retry Setting

**Status**: In Review — implemented 2026-08-31. Two design details corrected from the filing:
storage is the codebase's IndexedDB `storage.getConfig` (config key `auto_retry_invalid`,
default off), not raw `localStorage`; and per Tommy's confirmation the same-turn retry fires for
BOTH verb-level rejections (ActionNormalizer gate) and engine-executed failures — one retry,
no extra step, retry outcome feeds the react phase. Frontmatter `id` corrected 150 → 361.

## Summary

Add a new automation setting that, when enabled, automatically offers the agent a retry when it performs an invalid action. Instead of just logging the error and moving on, the system will feed back the error message to the agent and prompt it to choose a different action.

## Motivation

Currently, when an agent performs an invalid action (e.g., trying to attack a non-existent target, using an item that doesn't exist, or moving to an invalid location), the action fails silently or with a brief error log. The agent wastes its turn and doesn't learn from the mistake. This setting would:

1. Improve agent success rates by giving them a second chance
2. Provide better feedback loops for agent decision-making
3. Reduce wasted turns on invalid actions
4. Make the simulation feel more responsive and intelligent

## Implementation

### Settings Panel

Add a new checkbox in the Agent Settings section:

```
☑ Auto-retry on invalid actions
```

- **Location**: Settings panel, Agent Settings section
- **Default**: Off (opt-in feature)
- **Storage**: `localStorage` key `agentAutoRetryInvalid`

### Agent Engine Changes

In `agent-engine.js`, after an action is executed and returns an error:

1. Check if `config.autoRetryInvalid` is enabled
2. If enabled and the action result contains error indicators:
   - Extract the error message from the action result
   - Re-inject the error message into the agent's context
   - Prompt the agent: "Your previous action failed: [error message]. Choose a different action."
   - Execute a new DECIDE phase with this additional context
   - Execute the new action

### Error Detection

Identify invalid actions by checking for:
- "You don't see" messages
- "You don't have" messages
- "Invalid action" messages
- "Cannot" messages
- "not found" messages
- Result contains "error" or "failed" keywords

### Context Injection

The retry prompt should include:
- The original failed action
- The error message received
- A clear instruction to choose a different action
- The current room context (unchanged)

Example prompt addition:
```
Your previous action failed: "attack Standing bare-skinned"
Error: "You don't see standing bare-skinned."

Choose a different action. You cannot repeat the failed action.
```

### Turn Counting

- The retry should NOT count as a separate turn
- The agent gets one retry per invalid action
- If the retry also fails, log the error and move on (no infinite loops)

### Logging

- Log the retry attempt: "↩️ [Agent] retrying after invalid action"
- Log the new action result normally
- Track retry statistics for debugging

## Files to Modify

1. `static/js/ui/settings-view.js` - Add checkbox to settings panel
2. `static/js/agent-engine.js` - Add retry logic after action execution
3. `static/js/agent/prompt-builder.js` - Add retry prompt builder function
4. `static/js/config.js` - Add `autoRetryInvalid` to config defaults

## Testing

- [ ] Setting appears in Agent Settings panel
- [ ] Setting persists across page reloads
- [ ] Invalid action triggers retry when enabled
- [ ] Error message is correctly extracted and fed back
- [ ] Agent chooses a different action on retry
- [ ] No infinite retry loops
- [ ] Retry doesn't count as extra turn
- [ ] Setting works in both reactive and non-reactive modes
- [ ] Works with all action types (attack, use, go, etc.)

## Edge Cases

- Agent retries with the same invalid action (should fail and move on)
- Multiple invalid actions in sequence (each gets one retry)
- Network errors vs. game logic errors (only retry game logic errors)
- Agent is resting/unconscious (don't retry)
- Rate limiting (respect rate limits on retry)

## Future Enhancements

- Configurable retry count (1, 2, or 3 retries)
- Smart error classification (only retry certain error types)
- Track retry success rate for analytics
- Visual indicator in UI when retry occurs
