---
type: bug
status: todo
area: ui
priority: high
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [task-933, task-340, task-728]
---

# bug-577: Character Inspector crashes with TypeError reading bg on directed control mode

**Filed:** 2026-11-09
**Related:** task-933, task-340, task-728

<!-- deps:start -->
**Related:** [[task-933-character-controller-selector-and-director-turn-composer]], [[task-340-event-stream-v2]], [[task-728-directed-control-mode-a-director-reviews-and-edits-an-llm-character-s-turn-before-it-acts]]
<!-- deps:end -->

## What

Selecting any character whose control mode is set to `directed` crashes the Character Inspector with an uncaught `TypeError`:

```
agent-view.js:383 Uncaught TypeError: Cannot read properties of undefined (reading 'bg')
    at window.InspectorAgentView.AV._renderStatusRow (agent-view.js:383:231)
    at window.InspectorAgentView.AV.showAgent (agent-view.js:100:71)
    at Inspector.showAgent (inspector.js:279:35)
    at UIController.selectAgent (ui-controller.js:338:24)
```

In `static/js/inspector/agent-view.ts` (lines 390-394), `_renderStatusRow` defines a lookup object `modeMeta` containing only three keys: `human`, `llm`, and `npc`:

```ts
const modeMeta = ({
    human: { label: modeBadge.emoji + ' ' + (modeBadge.label || 'Human'), bg: 'var(--accent)', fg: '#000', bd: 'var(--accent-dim)' },
    llm:   { label: modeBadge.emoji + ' ' + (modeBadge.label || 'LLM'),   bg: 'var(--bg-input)', fg: 'var(--text)', bd: 'var(--border)' },
    npc:   { label: modeBadge.emoji + ' ' + (modeBadge.label || 'NPC'),   bg: 'var(--bg-input)', fg: 'var(--text-muted)', bd: 'var(--border)' }
} as Record<string, any>)[mode];
```

When `mode` is `'directed'` (or any unlisted mode such as `'paused'`), `modeMeta` evaluates to `undefined`. Line 415 then attempts to interpolate `${modeMeta.bg}`, `${modeMeta.fg}`, `${modeMeta.bd}`, and `${modeMeta.label}`, throwing a fatal `TypeError` and aborting inspector rendering completely.

## Why

`StreamControlMode.cycleControlMode()` includes `directed` in its rotation (`human -> directed -> llm -> npc`), and `events.getControlMode(agentName)` returns `'directed'`. However, `agent-view.ts` was authored assuming control modes could only ever be `human`, `llm`, or `npc`, with no entry for `directed` and zero defensive fallback. When a character in directed mode is selected, the inspector fatally breaks on every render and every live SSE state refresh.

## How

1. In `static/js/inspector/agent-view.ts`:
   - Add explicit styling metadata for `directed` and `paused` modes:
     ```ts
     directed: { label: modeBadge.emoji + ' ' + (modeBadge.label || 'Directed'), bg: 'var(--accent)', fg: '#000', bd: 'var(--accent-dim)' },
     paused:   { label: modeBadge.emoji + ' ' + (modeBadge.label || 'Paused'),   bg: 'var(--bg-input)', fg: 'var(--text-dim)', bd: 'var(--border)' },
     ```
   - Provide a safe fallback object so an unrecognized mode never yields `undefined`:
     ```ts
     const currentMeta = modeMetaMap[mode] || {
         label: modeBadge.emoji + ' ' + (modeBadge.label || mode),
         bg: 'var(--bg-input)',
         fg: 'var(--text)',
         bd: 'var(--border)'
     };
     ```
   - Interpolate `currentMeta.bg`, `currentMeta.fg`, `currentMeta.bd`, and `currentMeta.label` on the badge element.
2. Recompile TypeScript: `npm run build:ts`.

## Browser UI and intended live verification

Intended UI home: Character Inspector header / status row for any character in directed mode.

Current availability: Clicking any character in directed mode triggers an uncaught TypeError in `_renderStatusRow` and fails to render the inspector panel.

Live steps when available:
1. Open scenario `kraktooth_goblin_camp` in the browser UI.
2. Select character `Gribba` and click the control mode badge until it cycles to `Directed` (or set `events.setControlMode('Gribba', 'directed')` in console).
3. Deselect Gribba and click Gribba again in the left agents panel or graph view.
   - expected: Character Inspector opens cleanly without console errors, displaying the `🎬 Directed` badge in the status row.
4. Cycle through all control modes (`Human`, `Directed`, `LLM`, `NPC`, and `Paused`).
   - expected: Character Inspector updates in place on each mode change without throwing errors.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In browser console, set a character to directed mode: `events.setControlMode('Gribba', 'directed')`.
2. Click Gribba in the agents list to open Character Inspector.
   - expected: Inspector opens displaying character tabs and status row with Directed badge.
   - observed: Crashes with `Uncaught TypeError: Cannot read properties of undefined (reading 'bg')`.
3. Apply fix and reselect character.
   - expected: Inspector renders successfully with zero console errors.
4. Run frontend tests: `node tools/unit/run.cjs`.
   - expected: All unit tests pass.

## Acceptance

- [ ] Selecting a character in `directed` mode renders Character Inspector without TypeErrors.
- [ ] `_renderStatusRow` defines styling for `directed` and `paused` modes.
- [ ] Safe fallback prevents undefined crashes for any arbitrary mode string.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `static/js/inspector/agent-view.ts`
- `static/js/inspector/agent-view.js`
