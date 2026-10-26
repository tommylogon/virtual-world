/**
 * Contrast check for the Commons inner-world drawer (task-893).
 * Asserts all text elements meet WCAG AA >= 4.5:1 contrast against their backgrounds.
 */
'use strict';

function _luminance(hex) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.split('').map((c) => c + c).join('');
    const r = parseInt(hex.slice(0, 2), 16) / 255;
    const g = parseInt(hex.slice(2, 4), 16) / 255;
    const b = parseInt(hex.slice(4, 6), 16) / 255;
    const toLinear = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

function _contrast(fgHex, bgHex) {
    const l1 = _luminance(fgHex);
    const l2 = _luminance(bgHex);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
}

test('commons inner drawer text elements meet WCAG AA >= 4.5:1 contrast (task-893)', () => {
    const pairs = [
        { label: 'drawer-name on header', fg: '#e6edf3', bg: '#11161d' },
        { label: 'drawer-presence on header', fg: '#a1aab5', bg: '#11161d' },
        { label: 'drawer-presence.thinking on header', fg: '#a78bfa', bg: '#11161d' },
        { label: 'drawer-personality on header', fg: '#a1aab5', bg: '#11161d' },
        { label: 'trait-badge on badge bg', fg: '#c4b5fd', bg: '#232238' },
        { label: 'section-title on drawer bg', fg: '#8b949e', bg: '#161b22' },
        { label: 'inner-quote text on quote bg', fg: '#e6edf3', bg: '#1c2128' },
        { label: 'inner-time on drawer bg', fg: '#8b949e', bg: '#161b22' },
        { label: 'decision-summary on decision-card', fg: '#a1aab5', bg: '#1c2128' },
        { label: 'decision-text on decision-text bg', fg: '#e6edf3', bg: '#11161d' },
        { label: 'empty-state on drawer bg', fg: '#8b949e', bg: '#161b22' },
        { label: 'history-header time on drawer bg', fg: '#8b949e', bg: '#161b22' },
        { label: 'history-thought on drawer bg', fg: '#c9d1d9', bg: '#161b22' },
        { label: 'decision-action default', fg: '#93c5fd', bg: '#282e44' },
        { label: 'decision-action send_chat', fg: '#7dd3fc', bg: '#0f2d4a' },
        { label: 'decision-action read_chat', fg: '#fde047', bg: '#382806' },
        { label: 'decision-action think', fg: '#d1d5db', bg: '#252d38' },
        { label: 'decision-action start_dm', fg: '#f0abfc', bg: '#3b1747' },
        { label: 'decision-action start_group', fg: '#6ee7b7', bg: '#06402b' },
    ];

    for (const p of pairs) {
        const ratio = _contrast(p.fg, p.bg);
        assertTrue(ratio >= 4.5, `${p.label} (${p.fg} on ${p.bg}) ratio ${ratio.toFixed(2)} must be >= 4.5`);
    }
});
