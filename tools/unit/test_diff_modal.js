/**
 * tools/unit/test_diff_modal.js
 *
 * Unit tests for DiffModal V3 Hybrid Merge Workbench (task-982):
 * - wordDiff inline diffing
 * - isSeedMemory detection
 * - buildAxisRows smart-merge defaults
 * - applyEntrySelection (backward-compatible string[] and per-axis/remove spec)
 * - DiffModal.show V3 layout, hide-identical default, untruncated memory text,
 *   seed safety lock, and per-axis smart merge output.
 */

(() => {
    if (typeof window.DiffModal === 'undefined' && typeof __readFile === 'function') {
        eval(__readFile('static/js/shared/diff-modal.js'));
    }
    const DM = window.DiffModal;

    test('DiffModal.wordDiff produces inline word-level del/add chunks', () => {
        const chunks = DM.wordDiff('A quiet tavern keeper', 'A cheerful tavern owner');
        const dels = chunks.filter((c) => c.type === 'del').map((c) => c.text.trim());
        const adds = chunks.filter((c) => c.type === 'add').map((c) => c.text.trim());
        assertTrue(dels.includes('quiet'), 'marks removed word');
        assertTrue(dels.includes('keeper'), 'marks removed trailing word');
        assertTrue(adds.includes('cheerful'), 'marks added word');
        assertTrue(adds.includes('owner'), 'marks added trailing word');

        const sameOnly = DM.wordDiff('hello world', 'hello world');
        assertEq(sameOnly.length, 1, 'identical text collapses to one chunk');
        assertEq(sameOnly[0].type, 'same', 'chunk type is same');
    });

    test('DiffModal.isSeedMemory detects seed source, flag, and tags', () => {
        assertTrue(DM.isSeedMemory({ text: 'born here', source: 'seed' }), 'source=seed');
        assertTrue(DM.isSeedMemory({ text: 'childhood', tags: ['backstory', 'SEED'] }), 'tag=SEED');
        assertTrue(DM.isSeedMemory({ text: 'origin', seed: true }), 'seed=true');
        assertFalse(DM.isSeedMemory({ text: 'met at bar', source: 'runtime', tags: ['social'] }), 'runtime memory is not seed');
    });

    test('DiffModal.buildAxisRows preserves live target axes and adopts missing source axes', () => {
        const worldRel = { closeness: 8, interaction_count: 15, label: 'close friend', same_field: 'x' };
        const libRel = { closeness: 5, interaction_count: 0, label: 'acquaintance', same_field: 'x', trust: 4, respect: 7 };
        const axes = DM.buildAxisRows(worldRel, libRel);
        const byName = Object.fromEntries(axes.map((a) => [a.axis, a]));

        assertEq(byName.closeness.bucket, 'changed', 'closeness is changed');
        assertEq(byName.closeness.defaultPick, 'target', 'closeness keeps live world value');
        assertEq(byName.interaction_count.defaultPick, 'target', 'interaction_count keeps live world value');
        assertEq(byName.label.defaultPick, 'target', 'label keeps live world value');
        assertEq(byName.trust.bucket, 'new', 'trust is new from library');
        assertEq(byName.trust.defaultPick, 'source', 'trust adopts from library by default');
        assertEq(byName.respect.defaultPick, 'source', 'respect adopts from library by default');
        assertEq(byName.same_field.bucket, 'same', 'identical axis marked same');
    });

    test('DiffModal.applyEntrySelection supports per-axis smart merge and explicit remove', () => {
        const currentRels = {
            'lulu ashford': { closeness: 8, interaction_count: 15, label: 'close friend' },
            'world_npc': { closeness: 3, label: 'stranger' },
        };
        const incomingRels = {
            'lulu ashford': { closeness: 5, interaction_count: 0, label: 'acquaintance', trust: 4, respect: 7 },
        };
        const mergedRels = DM.applyEntrySelection(currentRels, incomingRels, {
            keys: [],
            axes: { 'lulu ashford': ['trust', 'respect'] },
        });
        assertEq(mergedRels['lulu ashford'].closeness, 8, 'kept live closeness');
        assertEq(mergedRels['lulu ashford'].interaction_count, 15, 'kept live interaction_count');
        assertEq(mergedRels['lulu ashford'].trust, 4, 'adopted missing trust');
        assertEq(mergedRels['lulu ashford'].respect, 7, 'adopted missing respect');
        assertEq(mergedRels['world_npc'].closeness, 3, 'preserved world-only relationship');

        // Array memories: keep safe by default, remove only when explicitly in remove[]
        const curMems = [
            { id: 'seed_1', text: 'seed one', source: 'seed' },
            { id: 'seed_2', text: 'seed two', source: 'seed' },
        ];
        const incMems = [
            { id: 'lib_1', text: 'new lib memory' },
        ];
        const mergedMems = DM.applyEntrySelection(curMems, incMems, {
            keys: ['lib_1'],
            remove: ['seed_1'],
        });
        const ids = mergedMems.map((m) => m.id);
        assertFalse(ids.includes('seed_1'), 'explicitly removed seed_1 is dropped');
        assertTrue(ids.includes('seed_2'), 'unmarked seed_2 is kept safe');
        assertTrue(ids.includes('lib_1'), 'selected lib_1 is added');
    });

    test('DiffModal.show V3 workbench renders fluid layout, hides identical, preserves full memory text & seed lock', async () => {
        const longMemText = 'A'.repeat(240) + ' full untruncated memory ending.';
        const libEntry = {
            name: 'Kyrie',
            description: 'A quiet scholar in the old library.',
            memories: [
                { id: 'm_same', text: 'identical memory', importance: 5 },
                { id: 'm_lib', text: longMemText, importance: 8, tags: ['lore'] },
            ],
            relationships: {
                'lulu ashford': { closeness: 5, interaction_count: 0, label: 'acquaintance', trust: 4, respect: 7 },
            },
        };
        const worldPayload = {
            name: 'Kyrie',
            description: 'A restless scholar in the new library.',
            memories: [
                { id: 'm_same', text: 'identical memory', importance: 5 },
                { id: 'm_seed', text: 'Childhood promise under the oak tree.', source: 'seed', tags: ['seed'] },
            ],
            relationships: {
                'lulu ashford': { closeness: 8, interaction_count: 15, label: 'close friend' },
            },
        };
        const sections = [
            { key: 'name', label: 'Name' },
            { key: 'description', label: 'Description' },
            { key: 'memories', label: 'Memories', perEntry: true },
            { key: 'relationships', label: 'Relationships', perEntry: true },
        ];

        // Lightweight DOM harness for DiffModal.show
        const prevLit = window.Lit;
        const prevDoc = window.document;
        let capturedHtml = '';
        const makeEl = (tag) => {
            const attrs = new Set();
            const classes = new Set();
            return {
                tagName: (tag || 'DIV').toUpperCase(),
                style: {},
                dataset: {},
                children: [],
                disabled: false,
                checked: false,
                value: '',
                id: '',
                textContent: '',
                className: '',
                classList: {
                    add: (c) => classes.add(c),
                    remove: (c) => classes.delete(c),
                    toggle: (c, force) => {
                        const on = force !== undefined ? !!force : !classes.has(c);
                        if (on) classes.add(c); else classes.delete(c);
                        return on;
                    },
                    contains: (c) => classes.has(c),
                },
                setAttribute: (k) => attrs.add(k),
                hasAttribute: (k) => attrs.has(k),
                toggleAttribute: (k) => { if (attrs.has(k)) attrs.delete(k); else attrs.add(k); },
                appendChild(c) { this.children.push(c); return c; },
                removeChild() {},
                addEventListener() {},
                removeEventListener() {},
                querySelector: () => null,
                querySelectorAll: () => [],
            };
        };

        const dryRunEl = makeEl('div');
        const bodyEl = makeEl('div');
        bodyEl.classList.add('dm-hide-same');
        const updateBtn = makeEl('button');

        const peMemGroup = makeEl('div');
        peMemGroup.dataset.key = 'memories';
        const memEntryCb = makeEl('input');
        memEntryCb.checked = true;
        memEntryCb.dataset.entry = 'm_lib';
        const seedSafeBtn = makeEl('button');
        seedSafeBtn.dataset.entry = 'm_seed';
        seedSafeBtn.dataset.state = 'safe';
        seedSafeBtn.dataset.seed = '1';
        peMemGroup.querySelector = (sel) => (sel === '.pe-chevron' || sel === '.pe-body' ? makeEl('div') : null);
        peMemGroup.querySelectorAll = (sel) => {
            if (sel === '.pe-entry') return [memEntryCb];
            if (sel === '.dm-safe-toggle') return [seedSafeBtn];
            return [];
        };

        const peRelGroup = makeEl('div');
        peRelGroup.dataset.key = 'relationships';
        const axTrust = makeEl('tr');
        axTrust.dataset.entry = 'lulu ashford';
        axTrust.dataset.axis = 'trust';
        axTrust.dataset.pick = 'source';
        const axCloseness = makeEl('tr');
        axCloseness.dataset.entry = 'lulu ashford';
        axCloseness.dataset.axis = 'closeness';
        axCloseness.dataset.pick = 'target';
        peRelGroup.querySelector = (sel) => (sel === '.pe-chevron' || sel === '.pe-body' ? makeEl('div') : null);
        peRelGroup.querySelectorAll = (sel) => {
            if (sel === '.dm-axis-row') return [axTrust, axCloseness];
            return [];
        };

        const descSec = makeEl('div');
        descSec.dataset.key = 'description';
        const descCb = makeEl('input');
        descCb.checked = true;
        descSec.querySelector = (sel) => (sel === '.diff-section-toggle' ? descCb : null);
        descSec.querySelectorAll = () => [];

        const modalMock = makeEl('div');
        modalMock.querySelectorAll = (sel) => {
            if (sel === '.pe') return [peMemGroup, peRelGroup];
            if (sel === '.diff-section:not(.pe)') return [descSec];
            if (sel === '.dm-safe-toggle[data-state="safe"]') return [seedSafeBtn];
            return [];
        };

        window.Lit = {
            unsafeHTML: (s) => s,
            render: (html) => { capturedHtml = String(html); },
        };
        window.document = {
            head: makeEl('head'),
            body: makeEl('body'),
            createElement: (tag) => (tag === 'div' && !modalMock._used ? (modalMock._used = true, makeEl('div')) : modalMock),
            getElementById: (id) => {
                if (id === 'dm-dry-run-summary') return dryRunEl;
                if (id === 'dm-body') return bodyEl;
                if (id === 'diff-modal-update') return updateBtn;
                return null;
            },
            addEventListener: () => {},
            removeEventListener: () => {},
        };

        try {
            const promise = DM.show(libEntry, worldPayload, sections, {
                title: 'Refresh Character from Library',
                name: 'Kyrie',
                direction: 'to-world',
            });

            assertTrue(capturedHtml.includes('Library -> World'), 'renders Library -> World direction banner');
            assertTrue(capturedHtml.includes('dm-hide-same'), 'hides identical items by default');
            assertTrue(capturedHtml.includes('dm-word-del'), 'renders inline word-diff deletions');
            assertTrue(capturedHtml.includes('dm-word-add'), 'renders inline word-diff additions');
            assertTrue(capturedHtml.includes(longMemText), 'renders full untruncated memory text');
            assertTrue(capturedHtml.includes('Keep Safe'), 'protects world-only seed memory as Keep Safe');
            assertTrue(capturedHtml.includes('Keep all Seed'), 'renders Keep all Seed bulk facet chip');
            assertTrue(capturedHtml.includes('dm-axis-table'), 'renders per-axis smart merge table');

            // Simulate user clicking Apply Selected
            updateBtn.onclick();
            const result = await promise;
            assertEq(result.action, 'update', 'resolves with update action');
            assertTrue(result.sections.includes('description'), 'description selected');
            assertFalse(result.sections.includes('memories'), 'memories NOT whole-section overwritten');
            assertEq(result.entries.memories, ['m_lib'], 'only m_lib selected; m_seed kept safe');
            assertEq(result.entries.relationships.axes['lulu ashford'], ['trust'], 'only missing trust axis adopted');
        } finally {
            window.Lit = prevLit;
            window.document = prevDoc;
        }
    });
})();
