/**
 * Unit tests for SaveLoadView (task-455 and task-456).
 */
'use strict';

test('saveload-view contains zero native alert/prompt/confirm calls (task-455)', () => {
    const tsCode = window.__readFile('static/js/ui/saveload-view.ts');
    const jsCode = window.__readFile('static/js/ui/saveload-view.js');

    // No window.prompt or window.confirm
    assertFalse(/window\.(prompt|confirm|alert)\b/.test(tsCode), 'no window.prompt/confirm/alert in .ts');
    assertFalse(/window\.(prompt|confirm|alert)\b/.test(jsCode), 'no window.prompt/confirm/alert in .js');

    // No bare prompt() or confirm() calls
    const tsLines = tsCode.split('\n');
    const dialogCalls = tsLines.filter((l) => {
        const trimmed = l.trim();
        if (trimmed.startsWith('*') || trimmed.startsWith('//') || trimmed.startsWith('/*')) return false;
        return /\b(prompt|confirm)\s*\(/.test(l) && !l.includes('dialog.prompt') && !l.includes('dialog.confirm') && !l.includes('confirmDeleteAllSaves');
    });
    assertEq(dialogCalls.length, 0, 'zero native prompt/confirm calls in .ts');
});

test('renderSaveRow extracts row markup with CSS classes and autosave action narrowing (task-455, task-456)', () => {
    const code = window.__readFile('static/js/ui/saveload-view.js');

    // renderSaveRow function exists
    assertTrue(/function renderSaveRow\s*\(/.test(code), 'renderSaveRow is defined');

    // Uses CSS classes instead of inline style strings for row and badges
    assertTrue(/class="save-game-item/.test(code), 'row carries save-game-item class');
    assertTrue(/class="save-badge save-badge-auto"/.test(code), 'auto badge carries save-badge-auto class');

    // Autosave row actions: emits 💾 (overwrite/saveGameToSlot), does NOT emit ✏️ or 🗑
    const autoBlockMatch = code.match(/isAuto\s*\?[\s\S]*?💾[\s\S]*?:[\s\S]*?💾[\s\S]*?✏️[\s\S]*?🗑/);
    assertTrue(!!autoBlockMatch, 'autosave row actions are narrowed to overwrite only');
});

test('SettingsView defines extracted world settings toggles (task-456)', () => {
    const code = window.__readFile('static/js/ui/settings-view.js');

    assertTrue(/toggleSpectator/.test(code), 'SettingsView defines toggleSpectator');
    assertTrue(/updateTimePerTick/.test(code), 'SettingsView defines updateTimePerTick');
    assertTrue(/updateClockStart/.test(code), 'SettingsView defines updateClockStart');
});
