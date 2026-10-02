/**
 * tools/unit/test_help_center.js — HelpCenter registry guard (task-521).
 *
 * The tip registry grew by a couple of dozen WorldPainter entries, and nothing
 * about a registry fails loudly: a duplicated id silently shares a seen-flag, a
 * tour step naming a deleted tip steps into the void, and a `data-help` hook with
 * no tip behind it is a control that does nothing when clicked. None of those
 * throw anywhere, so they are checked here instead.
 *
 * The dead-hook check reads the *sources* rather than a DOM: the two ways a
 * control gets a key are a `data-help="…"` attribute and the painter's
 * `_help(el, '…')` helper, plus the tool rail, whose eight keys are built at
 * runtime from the TOOLS table.
 */
'use strict';

const HC = window.HelpCenter;
const TIPS = HC.TIPS;
const TOURS = HC.TOURS;

/** Every `data-help` key the app actually emits. */
function collectHelpKeys() {
    const keys = new Set();
    const files = new Set();

    // Any static/js file may hook a control, so sweep the tree rather than guess
    // which one does. Templates carry the toolbar buttons.
    const walk = (dir) => {
        for (const name of window.__listDir(dir)) {
            if (name.endsWith('/')) { walk(dir + name); continue; }
            if (!/\.(js|html)$/.test(name)) continue;
            files.add(dir + name);
        }
    };
    walk('static/js/');
    walk('templates/');

    const attrRe = /data-help=["']([^"']+)["']/g;
    // The closing paren matters: the tool rail writes `_help(btn, 'wp-tool-' + id)`,
    // and a looser pattern would capture the literal prefix as a whole key.
    const helperRe = /_help\([^,()]+,\s*'([^']+)'\s*\)/g;
    for (const rel of files) {
        const src = window.__readFile(rel);
        for (const re of [attrRe, helperRe]) {
            re.lastIndex = 0;
            let m;
            while ((m = re.exec(src)) !== null) keys.add(m[1]);
        }
    }

    // The tool rail builds its keys as `'wp-tool-' + id` from the TOOLS table,
    // so those eight never appear as literals. Derive them from the table.
    //
    // Scope the scan to the TOOLS array itself. A bare row pattern over a
    // 3,395-line file also matches `row('exits', ['N', 'E', 'S', 'W'])`, which
    // is a compass, not a tool — that fabricated a `wp-tool-N` key with no tip
    // behind it and failed this file for a defect the app does not have.
    const editor = window.__readFile('static/js/worldpainter/editor.js');
    const table = /const\s+TOOLS\s*=\s*\[([\s\S]*?)\n\s*\];/.exec(editor);
    assertTrue(!!table, 'could not find the TOOLS table in worldpainter/editor.js');
    const toolsRe = /\[\s*'(\w+)'\s*,\s*'[^']*'\s*,\s*'[A-Z]'\s*,/g;
    let t;
    while ((t = toolsRe.exec(table[1])) !== null) keys.add('wp-tool-' + t[1]);

    return keys;
}

test('every tip has an id, group, title and body', () => {
    for (const tip of TIPS) {
        assertTrue(!!tip.id, `tip without an id: ${JSON.stringify(tip.title)}`);
        assertTrue(!!tip.group, `${tip.id} has no group`);
        assertTrue(!!tip.title, `${tip.id} has no title`);
        assertTrue(!!tip.body, `${tip.id} has no body`);
    }
});

test('tip ids are unique', () => {
    const seen = new Set();
    for (const tip of TIPS) {
        assertFalse(seen.has(tip.id), `duplicate tip id: ${tip.id}`);
        seen.add(tip.id);
    }
});

test('tip events are ones the registry knows how to fire', () => {
    const known = ['inspector:view', 'data-help', 'state:updated'];
    for (const tip of TIPS) {
        assertTrue(known.includes(tip.event),
            `${tip.id} has unknown event ${tip.event}`);
        if (tip.event === 'data-help') {
            assertEq(typeof tip.match, 'function', `${tip.id} needs a match fn`);
        }
    }
});

test('a data-help tip matches the key its target selector points at', () => {
    // The failure this catches: the tip matches on one key while spotlighting
    // `[data-help="…"]` for a different one, so the card says "Show me" and the
    // spotlight lands on a control that was never going to be explained.
    for (const tip of TIPS) {
        if (tip.event !== 'data-help' || !tip.target) continue;
        const m = /\[data-help=["']([^"']+)["']\]/.exec(tip.target);
        if (!m) continue;
        assertTrue(!!tip.match(m[1]),
            `${tip.id}: target points at "${m[1]}" but match() rejects it`);
    }
});

test('every data-help key the app emits has a tip behind it', () => {
    const keys = collectHelpKeys();
    for (const key of keys) {
        // The HelpCenter's own launcher key and the editor's private helper are
        // matched by tips directly; anything else must be covered.
        const covered = TIPS.some((t) => t.event === 'data-help'
            && typeof t.match === 'function' && t.match(key));
        assertTrue(covered, `no tip matches the data-help key "${key}"`);
    }
});

test('every tour step names a tip that exists', () => {
    for (const [id, tour] of Object.entries(TOURS)) {
        assertTrue(!!tour.title, `tour ${id} has no title`);
        assertTrue(Array.isArray(tour.steps) && tour.steps.length,
            `tour ${id} has no steps`);
        for (const step of tour.steps) {
            assertTrue(TIPS.some((t) => t.id === step),
                `tour ${id} steps to unknown tip "${step}"`);
        }
    }
});

test('every tip that claims a tour names one that exists', () => {
    for (const tip of TIPS) {
        if (!tip.tour) continue;
        assertTrue(!!TOURS[tip.tour],
            `${tip.id} claims tour "${tip.tour}", which is not defined`);
    }
});

test('a tour is reachable from the tips that belong to it', () => {
    // A tour whose steps are all unlisted still runs, but nothing in the Help
    // index points at it, so it is a chain nobody can start.
    for (const [id, tour] of Object.entries(TOURS)) {
        const linked = TIPS.some((t) => t.tour === id);
        assertTrue(linked, `tour "${id}" is not referenced by any tip`);
    }
});
