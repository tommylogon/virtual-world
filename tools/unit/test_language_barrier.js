import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert';

function loadPromptBuilder(state) {
    const windowObj = {
        PromptBuilder: {},
        worldState: {
            data: state,
            getKnownPlaces: () => new Set(),
            getItemsInArea: () => [],
            getNodeByIdentifier: () => null,
        },
    };
    const ctx = vm.createContext({
        window: windowObj,
        PromptBuilder: windowObj.PromptBuilder,
        worldState: windowObj.worldState,
        console,
        Date,
        Math,
        Set,
        Map,
        RegExp,
        Object,
        Array,
        String,
        Number,
        Boolean,
        JSON,
    });
    windowObj.window = windowObj;

    for (const rel of [
        'static/js/agent/prompt-builder/helpers.js',
        'static/js/agent/prompt-builder/character-state.js',
        'static/js/agent/prompt-builder/room-context.js',
    ]) {
        const code = fs.readFileSync(path.join(process.cwd(), rel), 'utf8');
        vm.runInContext(code, ctx);
    }
    windowObj.PromptBuilder.carriedItemNodes = windowObj.PromptBuilder.carriedItemNodes || (() => []);
    windowObj.PromptBuilder.knownAbilityNodes = windowObj.PromptBuilder.knownAbilityNodes || (() => []);
    windowObj.PromptBuilder.buildAvailableActionsBlock = windowObj.PromptBuilder.buildAvailableActionsBlock || (() => '');
    windowObj.PromptBuilder.buildConversationInstinct = windowObj.PromptBuilder.buildConversationInstinct || (() => '');
    windowObj.PromptBuilder.markSpeechLine = windowObj.PromptBuilder.markSpeechLine || ((line) => line);
    return windowObj.PromptBuilder;
}

const kenji = {
    name: 'Kenji',
    current_area: 'Hallway',
    languages: [
        { language: 'japanese', fluency: 'native', known_words: [], literate: true },
        { language: 'english', fluency: 'broken', known_words: ['wait', 'bathroom'], literate: true },
    ],
    relationships: {
        Sarah: { first_sighting: false },
    },
};

const miki = {
    name: 'Miki',
    current_area: 'Hallway',
    languages: [
        { language: 'japanese', fluency: 'native', known_words: [], literate: true },
        { language: 'english', fluency: 'fluent', known_words: [], literate: true },
    ],
};

const baseState = {
    time_ticks: 10,
    current_area: { name: 'Hallway', description: 'A quiet hallway.', exits: {} },
    areas: {
        Hallway: { name: 'Hallway', description: 'A quiet hallway.', exits: {} },
    },
    players: {
        Kenji: kenji,
        Miki: miki,
        Sarah: { name: 'Sarah', current_area: 'Hallway', description: 'A tall woman.' },
    },
    players_in_area: [{ name: 'Kenji' }, { name: 'Sarah' }, { name: 'Miki' }],
    turn_events: [
        {
            area: 'Hallway',
            actor: 'Sarah',
            action: 'speak',
            description: 'said: "Wait here while I check the hallway upstairs"',
            tick: 10,
            lang: 'english',
        },
    ],
    area_presence: { Hallway: { Kenji: 0, Miki: 0 } },
};

const pb = loadPromptBuilder(baseState);
const kenjiCtx = pb.buildRoomContext(baseState, 'Kenji', kenji, baseState.current_area, { preview: true });
assert.ok(kenjiCtx.includes('=== WITNESSED ==='), 'Expected WITNESSED section');
assert.ok(kenjiCtx.includes('Wait ??? ??? ??? ??? ??? ??? ???'), 'Kenji should see masked English speech with Wait preserved');
assert.ok(!kenjiCtx.includes('upstairs'), 'Unknown word upstairs must not leak into Kenji prompt');

const mikiCtx = pb.buildRoomContext(baseState, 'Miki', miki, baseState.current_area, { preview: true });
assert.ok(mikiCtx.includes('Wait here while I check the hallway upstairs'), 'Fluent listener Miki should see full speech');

const langInfo = pb.buildLanguageAndLingoContext({
    ...kenji,
    active_language: 'japanese',
});
assert.ok(langInfo.includes('Active speaking language: japanese.'), 'Speaker prompt should surface active_language');
assert.ok(langInfo.includes('[only knows: wait, bathroom]'), 'Speaker prompt should surface known_words');

console.log('test_language_barrier.js: ALL PASSED (3 assertions groups)');
