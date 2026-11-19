/**
 * test_action_interpreter.js
 *
 * Verifies ActionInterpreter extraction prompt generation and canonical parsing logic (task-943).
 */

test('ActionInterpreter exists on window', () => {
    assertTrue(ActionInterpreter, 'ActionInterpreter must be defined');
    assertTrue(typeof ActionInterpreter.interpretProseToAction === 'function', 'interpretProseToAction should be a function');
    assertTrue(typeof ActionInterpreter.buildExtractionPrompt === 'function', 'buildExtractionPrompt should be a function');
});

test('Extraction prompt emits canonical engine schema', () => {
    const promptObj = ActionInterpreter.buildExtractionPrompt({
        prose: "Jake clenches his jaw, spinning around toward the darkness. 'Someone help me!' he screams at the top of his lungs, scrambling back toward Willow Street East.",
        charName: "jake halloway",
        context: {
            waysOut: [
                { name: "Willow Street Central to Willow Street East", destination: "Willow Street East", direction: "west" },
                { name: "Willow Street Central to Oakwood Cemetery Gate", destination: "Oakwood Cemetery Gate", direction: "south" }
            ],
            thingsVisible: ["cracked phone", "Takis bag"],
            peopleHere: [],
            inventory: ["Jake's phone"]
        },
        directorNote: "jake should scream for help"
    });

    assertTrue(promptObj.systemPrompt.includes('inner_monologue'), 'Prompt must use canonical inner_monologue');
    assertTrue(promptObj.systemPrompt.includes('speech'), 'Prompt must use canonical speech');
    assertTrue(promptObj.systemPrompt.includes('volume'), 'Prompt must include canonical volume');
    assertTrue(promptObj.systemPrompt.includes('emote'), 'Prompt must include canonical emote');
    assertTrue(promptObj.systemPrompt.includes('emotion'), 'Prompt must include canonical emotion');
    assertTrue(promptObj.systemPrompt.includes('item'), 'Prompt must include canonical item');
    assertTrue(promptObj.systemPrompt.includes('target'), 'Prompt must include canonical target');
});

test('ActionInterpreter extracts canonical fields via ResponseParser', async () => {
    const prevConfig = window.config;
    try {
        const mockClient = {
            async chat() {
                return JSON.stringify({
                    inner_monologue: "Panicked, sensing someone watching from the dark.",
                    speech: "Someone help me!",
                    volume: "scream",
                    emote: "clenches jaw, spins around, scrambles backward",
                    action: "go",
                    item: null,
                    target: "Willow Street Central to Willow Street East",
                    memory: "Heard something in the shadows near Willow Street East",
                    emotion: "terrified"
                });
            }
        };

        window.config = {
            getInterpreterLLMClient: () => mockClient
        };

        const draft = await ActionInterpreter.interpretProseToAction({
            prose: "Jake clenches his jaw, spinning around toward the darkness. 'Someone help me!' he screams at the top of his lungs, scrambling back toward Willow Street East.",
            charName: "jake halloway"
        });

        assertTrue(draft !== null, 'Draft should not be null');
        assertEq(draft.inner_monologue, 'Panicked, sensing someone watching from the dark.', 'Canonical inner_monologue extracted');
        assertEq(draft.speech, 'Someone help me!', 'Canonical speech extracted');
        assertEq(draft.speechVolume, 'scream', 'Canonical speech volume is scream');
        assertEq(draft.action, 'go Willow Street Central to Willow Street East', 'Action action and target normalized by ActionNormalizer');
        assertEq(draft.target, 'Willow Street Central to Willow Street East', 'Target exit resolved');
        assertEq(draft.emotion, 'terrified', 'Emotion extracted');
        assertEq(draft.memory, 'Heard something in the shadows near Willow Street East', 'Memory extracted');
    } finally {
        window.config = prevConfig;
    }
});
