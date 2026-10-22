/**
 * test_play_mode_stream.js - the Play Mode stream sandbox (task-885).
 *
 * The bug this pins: a turn run in Play Mode left its rows in the event stream
 * after Stop, because nothing parked the authored log or discarded the run.
 * The sandbox is the mechanism; PlayMode.stop() calling exitSandbox() is the
 * wiring, checked as a source guard at the bottom.
 *
 * Local fakes stand in for the DOM: the sandbox only needs `children`,
 * `firstChild`, `appendChild`/`removeChild`, `remove()` and `scrollTop`, so a
 * real browser is not required to prove the detach/restore order.
 */

function mkNode(cls, dataset) {
    const n = {
        className: cls || '',
        dataset: dataset || {},
        _parent: null,
        remove() {
            if (!n._parent) return;
            const i = n._parent.children.indexOf(n);
            if (i >= 0) n._parent.children.splice(i, 1);
            n._parent = null;
        },
    };
    return n;
}

function mkFragment() {
    return {
        _isFragment: true,
        childNodes: [],
        appendChild(n) {
            if (n && n._isFragment) {
                for (const k of n.childNodes) this.appendChild(k);
                n.childNodes = [];
                return n;
            }
            if (n._parent) n.remove(); // real DOM adoption detaches from the old parent
            this.childNodes.push(n);
            return n;
        },
    };
}

function mkStream(rows) {
    const el = {
        children: [],
        scrollTop: 0,
        scrollHeight: 400,
        get firstChild() { return el.children[0] || null; },
        appendChild(c) {
            if (c && c._isFragment) {
                for (const k of c.childNodes) el.appendChild(k);
                c.childNodes = [];
                return c;
            }
            if (c._parent && c._parent !== el) c.remove(); // adoption detaches
            c._parent = el;
            el.children.push(c);
            return c;
        },
        removeChild(c) {
            const i = el.children.indexOf(c);
            if (i >= 0) el.children.splice(i, 1);
            c._parent = null;
            return c;
        },
        insertBefore(c) { return el.appendChild(c); },
        addEventListener() {},
        querySelector() { return null; },
        querySelectorAll() { return []; },
    };
    for (const row of rows || []) el.appendChild(row);
    return el;
}

/** Point the production `document` lookups at the fake stream for one call. */
function withStream(stream, fn) {
    const realGet = document.getElementById;
    const realFragment = document.createDocumentFragment;
    document.getElementById = (id) => (id === 'event-stream' ? stream : null);
    document.createDocumentFragment = () => mkFragment();
    try {
        return fn();
    } finally {
        document.getElementById = realGet;
        document.createDocumentFragment = realFragment;
    }
}

function mkBus() {
    const parkedCard = mkNode('turn-card');
    const bus = {
        _cards: {
            current: parkedCard,
            actor: 'Lyrie',
            close() { bus._cards.current = null; bus._cards.actor = null; },
        },
        _filters: { calls: 0, updateAgentFilterDropdown() { bus._filters.calls++; } },
        _scrubber: { rebuilds: 0, scheduleRebuild() { bus._scrubber.rebuilds++; } },
        _rawllm: { _rawResponses: [{ seq: 1 }], _streak: { n: 2 } },
        _areaEventLog: { 'Goblin Camp': [{ tick: 1 }] },
        _characterState: { Lyrie: { lastThought: 'hm' } },
        _knownActors: new Set(['Lyrie', 'Bork']),
        _lineSeq: 42,
        _tickCounter: 17,
        _lastGap: { minutes: 500, day: 0 },
        _streamSpans: { s1: mkNode('msg-bubble') },
        _streamLabels: { s1: 'LLM' },
        _isStreaming: true,
        persistCalls: 0,
        _persistLog() { bus.persistCalls++; },
    };
    return bus;
}

// ───────────────────────── enter ─────────────────────────

test('play-sandbox: enter parks the authored rows and drops chrome', () => {
    const authored = [mkNode('turn-card'), mkNode('msg-bubble')];
    const scrubber = mkNode('timeline-scrubber');
    const banner = mkNode('stream-scope-banner');
    const strip = mkNode('turn-queue-strip');
    const chip = mkNode('msg-bubble', { type: 'stream' });
    const stream = mkStream([scrubber, ...authored, banner, strip, chip]);
    const bus = mkBus();
    const sandbox = new StreamSandbox(bus);

    withStream(stream, () => sandbox.enter());

    assertEq(stream.children.length, 0, 'the live stream starts empty for the run');
    assertEq(sandbox._snap.fragment.childNodes.length, 2, 'only authored rows are parked');
    assertTrue(sandbox._snap.fragment.childNodes[0] === authored[0], 'order preserved, row 1');
    assertTrue(sandbox._snap.fragment.childNodes[1] === authored[1], 'order preserved, row 2');
    assertEq(sandbox.isActive(), true, 'sandbox is active');
    assertEq(bus._cards.current, null, 'the open turn card is closed for the run');
});

test('play-sandbox: enter gives the run fresh accumulators and keeps the originals', () => {
    const bus = mkBus();
    const authoredLog = bus._areaEventLog;
    const authoredChars = bus._characterState;
    const authoredActors = bus._knownActors;
    const authoredRaw = bus._rawllm._rawResponses;
    const sandbox = new StreamSandbox(bus);

    withStream(mkStream([]), () => sandbox.enter());

    assertFalse(bus._areaEventLog === authoredLog, 'area log is not shared with the run');
    assertFalse(bus._characterState === authoredChars, 'character state is not shared');
    assertFalse(bus._knownActors === authoredActors, 'actor roster is not shared');
    assertFalse(bus._rawllm._rawResponses === authoredRaw, 'raw-LLM chips are not shared');
    assertEq(bus._knownActors.size, 0, 'run starts with no known actors');
    assertEq(bus._rawllm._streak, null, 'parse-error streak reset for the run');
    assertEq(bus._isStreaming, false, 'no in-flight streaming chip survives the boundary');
    assertEq(Object.keys(bus._streamSpans).length, 0, 'stream spans cleared');
    assertEq(bus._scrubber.rebuilds, 1, 'scrubber rebuilt for the empty run');
});

test('play-sandbox: entering twice is a no-op, the parked log is not re-parked', () => {
    const stream = mkStream([mkNode('turn-card')]);
    const bus = mkBus();
    const sandbox = new StreamSandbox(bus);

    withStream(stream, () => {
        sandbox.enter();
        sandbox.enter();
    });

    assertEq(sandbox._snap.fragment.childNodes.length, 1, 'authored row still parked once');
});

// ───────────────────────── exit ─────────────────────────

test('play-sandbox: exit discards the run rows and restores the authored log', () => {
    const authoredA = mkNode('turn-card');
    const authoredB = mkNode('msg-bubble');
    const stream = mkStream([authoredA, authoredB]);
    const bus = mkBus();
    const sandbox = new StreamSandbox(bus);

    withStream(stream, () => {
        sandbox.enter();
        // What a turn in Play Mode does: log rows into the same stream.
        stream.appendChild(mkNode('msg-bubble'));
        stream.appendChild(mkNode('msg-bubble'));
        sandbox.exit();
    });

    assertEq(stream.children.length, 2, 'run rows are gone');
    assertTrue(stream.children[0] === authoredA, 'authored row 1 restored');
    assertTrue(stream.children[1] === authoredB, 'authored row 2 restored');
    assertEq(sandbox.isActive(), false, 'sandbox closed');
    assertTrue(bus._cards.current !== null, 'the authored turn card is open again');
    assertEq(bus._lineSeq, 42, 'line counter restored');
    assertEq(bus._tickCounter, 17, 'tick counter restored');
    assertEq(bus._rawllm._streak, { n: 2 }, 'parse-error streak restored');
    assertEq(bus._knownActors.has('Lyrie'), true, 'actor roster restored');
    assertEq(bus.persistCalls, 1, 'the stored log is rewritten so a refresh cannot resurrect run rows');
});

test('play-sandbox: exit without enter is a no-op', () => {
    const stream = mkStream([mkNode('turn-card')]);
    const bus = mkBus();
    const sandbox = new StreamSandbox(bus);

    withStream(stream, () => sandbox.exit());

    assertEq(stream.children.length, 1, 'the stream is untouched');
    assertEq(bus.persistCalls, 0, 'nothing persisted');
});

test('play-sandbox: discard drops the parked log without restoring it', () => {
    const stream = mkStream([mkNode('turn-card')]);
    const bus = mkBus();
    const sandbox = new StreamSandbox(bus);

    withStream(stream, () => {
        sandbox.enter();
        sandbox.discard();
        sandbox.exit();
    });

    assertEq(sandbox.isActive(), false, 'nothing left to restore');
    assertEq(stream.children.length, 0, 'the old world rows stay out of the new world');
});

// ───────────────────────── wiring ─────────────────────────

test('play-sandbox: PlayMode.enter/stop drive enterSandbox/exitSandbox', () => {
    const playMode = __readFile('static/js/ui/play-mode.ts');
    assertTrue(/enterSandbox\(\)/.test(playMode), 'enter calls enterSandbox');
    assertTrue(/exitSandbox\(\)/.test(playMode), 'stop calls exitSandbox');
    // The authored log must be back BEFORE the marker row is logged, or the
    // "stopped" line lands in the discarded run.
    assertTrue(playMode.indexOf('exitSandbox') < playMode.indexOf('Stopped Play Mode'),
        'exitSandbox runs before the stop marker is logged');

    const bus = __readFile('static/js/event-stream.ts');
    assertTrue(/enterSandbox\(\): void \{\s*this\._sandbox\.enter\(\);/.test(bus),
        'EventBus.enterSandbox delegates to the sandbox');
    assertTrue(/exitSandbox\(\): void \{\s*this\._sandbox\.exit\(\);/.test(bus),
        'EventBus.exitSandbox delegates to the sandbox');
    assertTrue(/_sandbox\.discard\(\)/.test(bus), 'a world replacement discards a parked log');
});
