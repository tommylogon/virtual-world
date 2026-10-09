/**
 * Unit tests for the shared in-app dialog (task-751).
 *
 * The dialog is a DOM module (no pure core to load in this sandbox), so these
 * check the contract by source: the three promise-based primitives exist, the
 * keyboard/backdrop rules are wired, and the trigger graph's blueprint save
 * actually routes through it — a definition with no call site is the failure
 * class this guards against (the _referenceControl bug).
 */
'use strict';

test('the shared dialog exposes alert / confirm / prompt', () => {
    const src = window.__readFile('static/js/shared/dialog.js');
    assertTrue(/return \{ alert, confirm, prompt \}/.test(src), 'returns the three primitives');
    assertTrue(/function alert\(/.test(src), 'alert defined');
    assertTrue(/function confirm\(/.test(src), 'confirm defined');
    assertTrue(/function prompt\(/.test(src), 'prompt defined');
});

test('the dialog handles keyboard and backdrop dismissal', () => {
    const src = window.__readFile('static/js/shared/dialog.js');
    assertTrue(/e\.key === 'Escape'/.test(src), 'Esc cancels');
    assertTrue(/e\.key === 'Enter'/.test(src), 'Enter submits');
    assertTrue(/e\.target === root/.test(src), 'backdrop click cancels');
    assertTrue(/e\.key === 'Tab'/.test(src), 'Tab is trapped in the card');
});

test('the blueprint save opens the in-app dialog, not native prompts', () => {
    const src = window.__readFile('static/js/shared/trigger-graph.js');
    assertTrue(/\.prompt\(/.test(src) && /Dialog/.test(src), 'blueprint save uses dialog.prompt');
    assertTrue(/Save to library/.test(src), 'the toolbar button makes clear it saves');
});
