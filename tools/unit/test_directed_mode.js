/**
 * Unit tests for Control Modes (Human / LLM / NPC / Paused) & Director AI in HumanTurnComposer (task-728, task-933).
 */

const StreamControlMode = new Function(window.__readFile('static/js/stream/stream-control-mode.js') + '; return StreamControlMode;')();

function makeComposerDomHarness() {
    const els = {};
    const makeEl = (id, tag = 'div') => {
        const listeners = {};
        const el = {
            id,
            tagName: tag.toUpperCase(),
            value: '',
            checked: false,
            disabled: false,
            textContent: '',
            placeholder: '',
            title: '',
            className: '',
            style: { display: id === 'htc-overlay' || id === 'htc-say-target' ? 'none' : '' },
            dataset: {},
            children: [],
            options: [],
            classList: {
                _set: new Set(),
                add(c) { this._set.add(c); },
                remove(c) { this._set.delete(c); },
                toggle(c, on) { if (on === undefined ? !this._set.has(c) : on) this._set.add(c); else this._set.delete(c); },
                contains(c) { return this._set.has(c); },
            },
            appendChild(child) {
                this.children.push(child);
                if (tag === 'select' && child && child.value !== undefined) {
                    this.options.push(child);
                }
                return child;
            },
            addEventListener(type, fn) {
                if (!listeners[type]) listeners[type] = [];
                listeners[type].push(fn);
            },
            click() {
                for (const fn of (listeners.click || [])) {
                    fn({ preventDefault() {}, stopPropagation() {} });
                }
            },
            focus() {},
            querySelector(sel) {
                if (sel && sel.startsWith('#')) return els[sel.slice(1)] || null;
                return null;
            },
            querySelectorAll() { return []; },
        };
        if (id === 'htc-emotion') {
            for (const val of ['', 'neutral', 'happy', 'angry', 'afraid', 'sad', 'surprised', 'disgusted', 'anxious', 'curious', 'determined', 'ashamed', 'relieved']) {
                el.options.push({ value: val, textContent: val || 'emotion (keep)' });
            }
        }
        els[id] = el;
        return el;
    };

    const ids = [
        ['htc-overlay', 'div'],
        ['htc-modal', 'div'],
        ['htc-composer', 'div'],
        ['htc-director-bar', 'div'],
        ['htc-ask-director', 'button'],
        ['htc-director-note', 'input'],
        ['htc-autodraft', 'input'],
        ['htc-thought-row', 'div'],
        ['htc-thought', 'input'],
        ['htc-emotion', 'select'],
        ['htc-thought-clear', 'button'],
        ['htc-do-row', 'div'],
        ['htc-do', 'input'],
        ['htc-clear-do', 'button'],
        ['htc-do-hint', 'div'],
        ['htc-speech', 'input'],
        ['htc-say-target', 'span'],
        ['htc-volseg', 'div'],
        ['htc-emote', 'input'],
        ['htc-emote-toggle', 'button'],
        ['htc-emote-palette', 'div'],
        ['htc-memory', 'input'],
        ['htc-reroll-btn', 'button'],
        ['htc-reroll', 'button'],
        ['htc-act', 'button'],
        ['htc-commit', 'button'],
        ['htc-react-btn', 'button'],
        ['htc-end', 'button'],
        ['htc-close', 'button'],
        ['htc-timeskip', 'button'],
        ['htc-advanced-toggle', 'button'],
        ['htc-advanced', 'div'],
        ['htc-relation', 'select'],
        ['htc-where', 'select'],
        ['htc-title', 'span'],
        ['htc-phase-note', 'span'],
        ['htc-result', 'div'],
        ['htc-flash', 'span'],
        ['htc-pips', 'div'],
        ['htc-budgetlab', 'div'],
        ['htc-meta', 'span'],
        ['htc-scene', 'div'],
        ['htc-feed-lines', 'div'],
        ['htc-you', 'div'],
        ['htc-names', 'datalist'],
    ];
    for (const [id, tag] of ids) makeEl(id, tag);

    const HTC = window.HumanTurnComposer;
    if (HTC) {
        els['htc-act'].addEventListener('click', () => HTC.commitStep && HTC.commitStep());
        els['htc-commit'].addEventListener('click', () => HTC.commitStep && HTC.commitStep());
        els['htc-ask-director'].addEventListener('click', () => HTC.askDirector && HTC.askDirector());
        els['htc-reroll-btn'].addEventListener('click', () => HTC.askDirector && HTC.askDirector());
        els['htc-reroll'].addEventListener('click', () => HTC.askDirector && HTC.askDirector());
    }

    return {
        els,
        withDom(fn) {
            const origQS = document.querySelector;
            const origGetById = document.getElementById;
            if (!document.createTextNode) {
                document.createTextNode = (t) => ({ nodeType: 3, textContent: String(t || '') });
            }
            document.querySelector = (sel) => {
                if (sel && sel.startsWith('#')) return els[sel.slice(1)] || null;
                return origQS ? origQS.call(document, sel) : null;
            };
            document.getElementById = (id) => els[id] || (origGetById ? origGetById.call(document, id) : null);
            return Promise.resolve()
                .then(() => fn(els))
                .finally(() => {
                    document.querySelector = origQS;
                    document.getElementById = origGetById;
                });
        },
    };
}

test('StreamControlMode supports human, llm, npc, paused and normalizes legacy directed to human + isAutoDraft', () => {
    localStorage.removeItem('vw_director_autodraft');
    const scm = new StreamControlMode({});

    // Badges for all 4 modes + legacy directed
    assertEq(scm.controlBadge('human').emoji, '👤', 'human badge emoji');
    assertEq(scm.controlBadge('human').label, 'Human', 'human badge label');
    assertEq(scm.controlBadge('llm').emoji, '🧠', 'llm badge emoji');
    assertEq(scm.controlBadge('llm').label, 'LLM', 'llm badge label');
    assertEq(scm.controlBadge('npc').emoji, '🤖', 'npc badge emoji');
    assertEq(scm.controlBadge('npc').label, 'NPC', 'npc badge label');
    assertEq(scm.controlBadge('paused').emoji, '⏸️', 'paused badge emoji');
    assertEq(scm.controlBadge('paused').label, 'Paused', 'paused badge label');
    assertEq(scm.controlBadge('directed').emoji, '🎬', 'legacy directed badge emoji');

    window.worldState = window.worldState || {};
    window.worldState.runtimePlayer = (name) => window.worldState.players?.[name] || null;
    window.worldState.players = {
        'Jake': { autonomy: 'directed' },
        'Kayla': { autonomy: false },
        'Lulu': { autonomy: true },
        'Rat': { simple_npc: true, autonomy: true },
        'Statue': { simple_npc: true, autonomy: false },
        'Sammy': { controller: 'directed' },
        'Zoe': { controller: 'human' },
        'Kyrie': { controller: 'llm' },
        'Goblin': { controller: 'npc' },
        'Frozen': { controller: 'paused' },
    };

    assertEq(scm.getControlMode('Jake'), 'human', 'autonomy:directed normalizes to human');
    assertTrue(scm.isAutoDraft('Jake'), 'autonomy:directed enables isAutoDraft');
    assertEq(scm.getControlMode('Sammy'), 'human', 'controller:directed normalizes to human');
    assertTrue(scm.isAutoDraft('Sammy'), 'controller:directed enables isAutoDraft');

    assertEq(scm.getControlMode('Kayla'), 'human', 'autonomy:false resolves to human');
    assertFalse(scm.isAutoDraft('Kayla'), 'plain human does not enable autoDraft by default');
    assertEq(scm.getControlMode('Lulu'), 'llm', 'autonomy:true resolves to llm');
    assertEq(scm.getControlMode('Rat'), 'npc', 'simple_npc with autonomy:true resolves to npc');
    assertEq(scm.getControlMode('Statue'), 'paused', 'simple_npc with autonomy:false resolves to paused');

    assertEq(scm.getControlMode('Zoe'), 'human', 'controller:human resolves to human');
    assertEq(scm.getControlMode('Kyrie'), 'llm', 'controller:llm resolves to llm');
    assertEq(scm.getControlMode('Goblin'), 'npc', 'controller:npc resolves to npc');
    assertEq(scm.getControlMode('Frozen'), 'paused', 'controller:paused resolves to paused');

    assertFalse(scm.isAutonomous('Jake'), 'directed-normalized-to-human uses HumanTurnComposer (_humanTurn)');
    assertFalse(scm.isAutonomous('Kayla'), 'human is not autonomous');
    assertFalse(scm.isAutonomous('Frozen'), 'paused is not autonomous');
    assertTrue(scm.isAutonomous('Lulu'), 'llm is autonomous');
    assertTrue(scm.isAutonomous('Rat'), 'npc is autonomous');

    scm.setAutoDraft('Zoe', true);
    assertTrue(scm.isAutoDraft('Zoe'), 'setAutoDraft enables autoDraft for human character');
    scm.setAutoDraft('Zoe', false);
    assertFalse(scm.isAutoDraft('Zoe'), 'setAutoDraft disables autoDraft');
});

test('HumanTurnComposer.applyPrefill populates editable #htc-thought, #htc-emotion, and renders #htc-say-target chip via setSpeechTarget', async () => {
    const HTC = window.HumanTurnComposer;
    const harness = makeComposerDomHarness();
    await harness.withDom((els) => {
        HTC.applyPrefill({
            action: 'examine desk',
            speech: 'What is hiding under here?',
            speechVolume: 'whisper',
            target: 'Sammy',
            emote: 'peers closely at the drawer',
            inner: 'Sammy is definitely hiding the key.',
            emotion: 'curious',
            memory: 'Checked the desk drawer',
        });

        assertEq(els['htc-do'].value, 'examine desk', '#htc-do populated with action');
        assertEq(els['htc-speech'].value, 'What is hiding under here?', '#htc-speech populated');
        assertEq(els['htc-emote'].value, 'peers closely at the drawer', '#htc-emote populated');
        assertEq(els['htc-memory'].value, 'Checked the desk drawer', '#htc-memory populated');
        assertEq(els['htc-thought'].value, 'Sammy is definitely hiding the key.', 'editable #htc-thought populated from prefill.inner');
        assertEq(els['htc-emotion'].value, 'curious', 'editable #htc-emotion populated from prefill.emotion');

        assertEq(els['htc-say-target'].style.display, 'inline-flex', '#htc-say-target chip is visible when target is set');
        assertTrue(els['htc-say-target'].textContent.includes('to Sammy'), '#htc-say-target chip displays target name');
        assertTrue(els['htc-say-target'].textContent.includes('×'), '#htc-say-target chip includes clear affordance');

        // Clearing speech target hides the chip
        HTC.setSpeechTarget(null);
        assertEq(els['htc-say-target'].style.display, 'none', '#htc-say-target chip hides when cleared');
        assertEq(els['htc-say-target'].textContent, '', '#htc-say-target text cleared');
    });
});

test('Editing #htc-thought and #htc-emotion in the DOM commits the edited values on Act (#htc-commit), never stale prefill values', async () => {
    const HTC = window.HumanTurnComposer;
    const harness = makeComposerDomHarness();
    window.worldState = window.worldState || {};
    window.worldState.runtimePlayer = () => ({ turn_slots: { major: 1, minor: 1, free: 3 } });

    await harness.withDom(async (els) => {
        HTC.closeTurn();
        const turnPromise = HTC.request('Kayla', {
            prefill: {
                action: 'look',
                speech: 'Initial speech',
                target: 'Sammy',
                inner: 'Stale prefill thought',
                emotion: 'neutral',
            },
        });

        assertEq(els['htc-thought'].value, 'Stale prefill thought', 'prefill initially populates #htc-thought');
        assertEq(els['htc-emotion'].value, 'neutral', 'prefill initially populates #htc-emotion');

        // User edits thought and emotion in the DOM before clicking #htc-commit
        els['htc-thought'].value = 'Edited private monologue';
        els['htc-emotion'].value = 'anxious';

        els['htc-commit'].click();
        const committed = await turnPromise;

        assertTrue(Boolean(committed && committed.step), 'request resolved with a committed step');
        assertEq(committed.step.inner, 'Edited private monologue', 'committed inner uses edited #htc-thought value, not stale prefill');
        assertEq(committed.step.emotion, 'anxious', 'committed emotion uses edited #htc-emotion value, not stale prefill');
        assertEq(committed.step.target, 'Sammy', 'committed target preserves active speech target');
        HTC.closeTurn();
    });
});

test('Clicking #htc-ask-director invokes VW.agent.draftTurnForCharacter with #htc-director-note and populates composer in place without closing modal', async () => {
    const HTC = window.HumanTurnComposer;
    const harness = makeComposerDomHarness();
    let capturedCall = null;

    window.VW = window.VW || {};
    window.VW.agent = {
        async draftTurnForCharacter(charName, opts) {
            capturedCall = { charName, opts };
            return {
                action: 'search crate',
                speech: 'Nothing to see here, Sammy!',
                speechVolume: 'say',
                target: 'Sammy',
                emote: 'sweats nervously',
                inner: 'I hope Sammy does not notice my shaking hands.',
                emotion: 'afraid',
                memory: 'Blamed Sammy while searching the crate',
            };
        },
    };

    await harness.withDom(async (els) => {
        HTC.closeTurn();
        const pendingTurn = HTC.request('Jake', { lastResult: 'You enter the storage room.' });
        assertEq(els['htc-overlay'].style.display, 'flex', 'modal is open');

        els['htc-director-note'].value = 'act nervous, blame Sammy';
        await HTC.askDirector();

        assertTrue(Boolean(capturedCall), 'VW.agent.draftTurnForCharacter was called');
        assertEq(capturedCall.charName, 'Jake', 'called for active character');
        assertEq(capturedCall.opts.phase, 'compose', 'called with compose phase');
        assertEq(capturedCall.opts.directorNote, 'act nervous, blame Sammy', 'passed #htc-director-note steering text');
        assertEq(capturedCall.opts.actionResult, 'You enter the storage room.', 'passed last reaction/result text');

        // Modal must remain open and populated in place
        assertEq(els['htc-overlay'].style.display, 'flex', 'modal remains open after Ask Director');
        assertEq(els['htc-do'].value, 'search crate', '#htc-do populated in place');
        assertEq(els['htc-speech'].value, 'Nothing to see here, Sammy!', '#htc-speech populated in place');
        assertEq(els['htc-emote'].value, 'sweats nervously', '#htc-emote populated in place');
        assertEq(els['htc-thought'].value, 'I hope Sammy does not notice my shaking hands.', '#htc-thought populated in place');
        assertEq(els['htc-emotion'].value, 'afraid', '#htc-emotion populated in place');
        assertEq(els['htc-memory'].value, 'Blamed Sammy while searching the crate', '#htc-memory populated in place');
        assertEq(els['htc-say-target'].style.display, 'inline-flex', '#htc-say-target chip rendered in place');
        assertTrue(els['htc-say-target'].textContent.includes('to Sammy'), '#htc-say-target shows Sammy');

        // Take 2: clicking Ask Director again passes currentDraft from the populated inputs (task-942)
        els['htc-director-note'].value = 'keep the action, just make the speech shorter';
        await HTC.askDirector();
        assertTrue(Boolean(capturedCall.opts.currentDraft), 'Take 2 passes currentDraft to draftTurnForCharacter');
        assertEq(capturedCall.opts.currentDraft.action, 'search crate', 'currentDraft.action preserves Take 1 action');
        assertEq(capturedCall.opts.currentDraft.speech, 'Nothing to see here, Sammy!', 'currentDraft.speech preserves Take 1 speech');
        assertEq(capturedCall.opts.currentDraft.target, 'Sammy', 'currentDraft.target preserves Take 1 speech target');
        assertEq(capturedCall.opts.currentDraft.emotion, 'afraid', 'currentDraft.emotion preserves Take 1 emotion');

        HTC.closeTurn();
        void pendingTurn;
    });
});

test('ResponseParser.parseReaction and parseResultReaction preserve target on directed speech and whispers (bug-581)', () => {
    const RP = window.ResponseParser;
    const whisperRx = RP.parseReaction(JSON.stringify({
        inner_monologue: 'Keep it quiet.',
        action: 'examine',
        item: "Jake's phone",
        speech: 'Look at this screen.',
        volume: 'whisper',
        target: 'kayla jenkins',
        emote: 'leans in',
    }));
    assertEq(whisperRx.action, "examine Jake's phone", 'action uses item when both item and target are present');
    assertEq(whisperRx.speechVolume, 'whisper', 'whisper volume extracted');
    assertEq(whisperRx.target, 'kayla jenkins', 'directed whisper target preserved on ParsedReaction');

    const resRx = RP.parseResultReaction(JSON.stringify({
        inner_monologue: 'Done.',
        speech: 'Over here.',
        speech_target: 'sammy lopez',
    }));
    assertEq(resRx.target, 'sammy lopez', 'parseResultReaction preserves speech_target');
});

test('AgentEngine._groundDirectorDraft and _injectDirectorSteering ground fuzzy entity names and prioritize Director Note before JSON schema (task-942)', () => {
    const prevAgent = window.agent;
    window.RateLimiter = window.RateLimiter || class {};
    const AgentEngineCtor = new Function(window.__readFile('static/js/agent-engine.js') + '; return AgentEngine;')();
    window.agent = prevAgent;
    const eng = Object.create(AgentEngineCtor.prototype);
    const state = {
        players: {
            'jake halloway': { current_area: 'kitchen', inventory: ["Jake's phone"] },
            'kayla jenkins': { current_area: 'kitchen' },
        },
        areas: {
            kitchen: {
                name: 'kitchen',
                items: ['crimson-ink note', 'coffee mug'],
                exits: [{ direction: 'north', to: 'hallway' }],
            },
        },
    };
    const player = state.players['jake halloway'];
    const area = state.areas.kitchen;

    const grounded1 = eng._groundDirectorDraft('jake halloway', state, player, area, {
        action: 'examine phone case',
        target: 'Kayla',
    });
    assertEq(grounded1.action, "examine Jake's phone", 'fuzzy "phone case" grounded to canonical "Jake\'s phone"');
    assertEq(grounded1.target, 'kayla jenkins', 'fuzzy "Kayla" grounded to canonical "kayla jenkins"');

    const grounded2 = eng._groundDirectorDraft('jake halloway', state, player, area, {
        action: 'read note',
        target: null,
    });
    assertEq(grounded2.action, 'read crimson-ink note', 'fuzzy "note" grounded to canonical "crimson-ink note"');

    const basePrompt = 'Scene context...\n\nRespond with ONLY a single raw JSON object matching this schema:\n{\n  "action": "look"\n}';
    const entities = eng._collectCanonicalSceneEntities('jake halloway', state, player, area);
    const injected = eng._injectDirectorSteering(
        basePrompt,
        'keep the action, make speech shorter',
        { action: "examine Jake's phone", speech: 'Long rambling speech here', speechVolume: 'say' },
        entities
    );
    const draftIdx = injected.indexOf('[CURRENT DRAFT IN COMPOSER (PREVIOUS TAKE)]');
    const noteIdx = injected.indexOf('[DIRECTOR STEERING NOTE]: keep the action, make speech shorter');
    assertTrue(draftIdx >= 0 && noteIdx > draftIdx, 'current draft and director steering note are injected in order');

    // Also verify repairJSON recovers LLM output with missing comma before next key and missing closing brace
    const brokenRaw = '{"action":"examine", "item":"Jake\'s phone", "target":"phone", "speech":"Ugh, look at my phone? Seriously?""emote":"lean against the table", "inner_monologue":"I need to check the note."';
    const rxBroken = window.ResponseParser.parseReaction(brokenRaw);
    assertEq(rxBroken.parseError, 'JSON repaired (truncated response)  -  fields after the break were lost', 'parseError check');
    assertEq(rxBroken.action, "examine Jake's phone", 'repairJSON + ResponseParser recovers action from broken JSON');
    assertEq(rxBroken.speech, 'Ugh, look at my phone? Seriously?', 'repairJSON + ResponseParser recovers speech from broken JSON');
    assertEq(rxBroken.emote, 'lean against the table', 'repairJSON + ResponseParser recovers emote after missing comma');
    assertEq(rxBroken.inner, 'I need to check the note.', 'repairJSON + ResponseParser recovers inner_monologue before missing brace');
});


