/**
 * prompt-builder/system-prompt.js - Character system prompt (compact ACTIONS core
 * + rules). Per-verb availability is dynamic and lives in the per-turn context via
 * contextual-actions.js (=== AVAILABLE ACTIONS ===); this file holds only the
 * static instruction text.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). Almost all static
 * template text with minimal logic - isolated so it can't get tangled with the
 * dynamic prompt builders. Exports merge into window.PromptBuilder.
 *
 * Load order: schema-fragments.js must load BEFORE this file (uses
 * PromptBuilder.EMOTE_RULES_SYSTEM).
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 *
 * @module prompt-builder/system-prompt - the static character system prompt
 * @contributes buildCharacterSystemPrompt / buildReactSystemPrompt (+ shared _loreHeader/_brevityRule helpers)
 * @powers the standing rules every character is given (ACTIONS, emote voice, speech, JSON rules, lore)
 * @relates needs schema-fragments.js loaded first (EMOTE_RULES_SYSTEM); per-verb availability lives in contextual-actions.js
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    const ACTIONS_CORE = `

=== ACTIONS ===
Emit ONE action per response as a structured object:
- "action": a single verb word (go, dash, approach, crawl, climb, take, drop, use, use_on, eat, drink, examine, open, close, attack, grab, wait, rest, put, give, search, look, inventory, stats, relieve, stow, craft, make, ...).
- "item" and "target": the full multi-word name of what you act on, never truncated (matched leniently by exact name, alias, or keywords).
- If you wait, listen, or hold still, use "action": "wait".

Your turn context shows what's around you - each item, door, exit, person, and carried/worn thing already lists the actions you can take with it. === AVAILABLE ACTIONS === lists the remaining actions you can take this turn.
When your major-action budget is exhausted (=== AVAILABLE ACTIONS === shows no major actions), do not attempt another major action; choose a minor/free action, speak, or "wait".
If an action was just rejected or failed, do not repeat the same action immediately. Choose a different approach, examine the situation, or use "wait".

## Rules
- Food uses "eat"; drink uses "drink". "use" is for standalone self-use items (Create Flame, candles). Use "use_on" only when an item must be used on something else.
- "put" needs a "relation": on, under, beside, behind, at, or in (e.g. put X on a table, put X in a chest).
- "give"/"steal" need a target character in the same area as you.
- Locked doors and items need the right item: use [item] on [target]. Examine the target first if you need to learn what it requires.
- Examining a door, item, or person positions you near them for a closer look. Physical actions walk you there automatically (open, close, use_on, take, attack).
- Some items you spot give no useful information, and some are hidden from view - explore and examine to find them.
- "go" passes THROUGH exits. To walk UP TO an exit/item/person and stop there, use "approach" or "go to <target>".
- If someone is shown by appearance rather than a real name, you haven't met them - judge them by what you see.
- You can combine speech + volume + emote with *FIX* action in the same response.
- Your inner_monologue must align with your actions. If you intend to speak, do not think "I'll stay quiet." If you intend to stay silent, omit the speech field entirely.
  - CONVERSATION INSTINCT: The === WITNESSED === section shows what you notice around you:
    - [Heard -> addressed to you]: directly addressed to you; consider responding.
    - [Heard -> to you] or [Heard -> to the group]: room-wide call or group address.
    - bare [Heard]: overheard chatter.
  - ANTI-REPEAT: Do not repeat lines you already said in === CONVERSATION ===.
  - GROUP COLLABORATION: Build on what companions did rather than duplicating their actions.

Examples:
- {"action":"eat","item":"bread"}                             -> eat food
- {"action":"drink","item":"water"}                           -> drink liquid
- {"action":"use","item":"create flame"}                       -> light a magical ember
- {"action":"use_on","item":"brass key","target":"locked door"} -> unlock a door with a key
- {"action":"go","target":"north"}                             -> pass through an exit
- {"action":"approach","target":"the front door"}              -> walk up to a door and stop
- {"action":"take","item":"the flower crown"}                  -> pick up an item
- {"action":"put","item":"the pen","target":"table","relation":"on"} -> place on a surface
- {"action":"give","item":"the key","target":"the stranger"}   -> hand to someone nearby
- {"action":"use_on","item":"ink pen","target":"parchment","text":"Don't go there"} -> write text
`;

    const GHOST_ACTIONS = `

You are dead. You can observe and move as a ghost, but cannot interact physically without a skill check.
| Manifest | manifest | manifest | Ghost only: become visible |
| Vanish | vanish | vanish | Ghost only: become invisible |`;

    const ITEMS_VS_FLAVOR = `

=== ITEMS vs FLAVOR ===
The "Items that catch your attention:" list is everything you can interact with in the area. Items you carry or have equipped are always accessible (see your "Wearing:" and "Carrying:" lines). Area descriptions may mention things that are NOT separate items - if it's not in either list, you can't examine/take/use it separately. Use "inventory" to see what you're carrying, "look" for the full area view.`;

    const ACTION_STRUCTURE = '';

    const _regMatureList = (window as unknown as { ActionVerbs?: { MATURE_VERBS?: string[] } }).ActionVerbs?.MATURE_VERBS?.join(', ') || 'kiss, caress, lick, suck, bite, pinch, blow, tickle';
    const MATURE_ACTIONS = `

=== INTIMACY (adult worlds only) ===
Intimate verbs are available: ${_regMatureList}. Schema: {"action":"kiss","target":"lydia","where":"neck","intensity":"light|normal|firm"} - "where" is the body part (neck, lips, left nipple, ...), "intensity" defaults to normal. These are interact-type actions: they never damage, they land through clothing (weaker), and the other character reacts on their own terms - consent matters; pushing someone who pulls away changes how they feel about you.
- {"action":"kiss","target":"lydia","where":"lips"}             → a kiss
- {"action":"pinch","target":"lydia","where":"left nipple","intensity":"firm"}  → sharp contact - can hurt
`;

    const SPEECH_VOLUME = `

=== SPEECH & VOLUME ===
Put speech in the "speech" field and volume in the "volume" field - whisper | say | sing | shout | scream (default say). The volume word is the KEY name, never part of the speech text.
DIRECTED WHISPER: add "target":"<character name>" for a private aside - only that character hears it. A plain whisper (no target) is heard by the whole room.
For a speech-only turn, omit "action". If you say nothing, set "speech": null. To do nothing, respond {"action":"wait"}.

=== JSON RULES ===
- One comma between every field: {"inner_monologue":"...","action":"wait"}
- Never repeat keys; use null or "" for unused fields ("speech": null, "emote": null)
- Never add fields that aren't in the examples (no "stats", no "inventory", no extras)

`;

    /** World-lore header shared by both system prompts ('' when there is no lore). */
    function _loreHeader(player?: SystemPromptPlayerLike | null) {
        const lore: LoreEntry[] = worldState.data?.world_lore || [];
        if (!lore.length) return '';
        const charTags = (player?.tags || []).map((t: unknown) => String(t).toLowerCase());
        const visible = lore.filter((entry: LoreEntry) => {
            const allowed: unknown[] = (entry.allowed_tags as unknown[]) || [];
            if (!allowed.length) return true;
            return allowed.some((t: unknown) => charTags.includes(String(t).toLowerCase()));
        });
        if (!visible.length) return '';
        const lines = visible.map((entry: LoreEntry) => `[${entry.category || 'general'}] ${entry.title}: ${entry.content}`);
        return `\n=== WORLD LORE ===\n${lines.join('\n')}\n`;
    }

    /** Brevity instruction; `tail` names the fields this phase is allowed to emit. */
    function _brevityRule(softMaxTokens: number, tail: string) {
        const limit = softMaxTokens || Number(config.maxTokens) || 512;
        return `\n\n=== RESPONSE LENGTH ===\nKeep your response under ${limit} tokens. Be concise - ${tail}`;
    }

    /**
     * Build the character system prompt - the core personality and rules prompt
     * that defines how the character should behave and what commands are available.
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {number} softMaxTokens - Soft token limit for system prompt instruction (0 = use hard limit)
     * @returns {string} Full system prompt string
     */
    function buildCharacterSystemPrompt(charName: string, player: SystemPromptPlayerLike, softMaxTokens: number) {
        if (!player) throw new Error(`buildCharacterSystemPrompt: player is null for "${charName}" - call site should validate before caching history`);
        const dead = player.state === 'dead';

        let prompt = _loreHeader(player);
        const brevityRule = _brevityRule(softMaxTokens, 'inner monologue, speech, and action should be brief and natural.');

        const parts = [
            ACTIONS_CORE,
            PromptBuilder.EMOTE_RULES_SYSTEM,
        ];
        if (dead) parts.push(GHOST_ACTIONS);
        if (config?.matureContent) parts.push(MATURE_ACTIONS);
        parts.push(ITEMS_VS_FLAVOR, ACTION_STRUCTURE, SPEECH_VOLUME, brevityRule);

        prompt += parts.join('');

        return prompt;
    }

    /**
     * Dedicated minimal system prompt for the result-reaction call. The react
     * phase cannot take actions, so the action-law blocks (ACTIONS / ACTION
     * STRUCTURE / ITEMS vs FLAVOR / INTIMACY) are dropped - they were ~1.2k of
     * weight that also directly contradicted the react user message's
     * "MUST NOT include action or item fields". Kept: lore, emote rules,
     * speech & volume (the react instructions reference it), JSON rules, length.
     */
    function buildReactSystemPrompt(charName: string, player: SystemPromptPlayerLike, softMaxTokens: number) {
        if (!player) throw new Error(`buildReactSystemPrompt: player is null for "${charName}"`);
        let prompt = _loreHeader(player);
        const brevityRule = _brevityRule(softMaxTokens, 'inner monologue, speech, and emote should be brief and natural.');

        const parts = [
            `\n=== REACT MODE ===\nThis is the instant after your own action resolved. You cannot take new actions in this phase - respond only with inner_monologue, speech (rarely), emote, memory, and emotion.`,
            PromptBuilder.EMOTE_RULES_SYSTEM,
            SPEECH_VOLUME,
            brevityRule,
        ];

        prompt += parts.join('');

        return prompt;
    }

    Object.assign(window.PromptBuilder, {
        buildCharacterSystemPrompt,
        buildReactSystemPrompt
    });
})();

// NOTE: these shape declarations sit AFTER the first value statement on purpose.
// A leading `interface`/`type` makes TypeScript drop the file's leading JSDoc
// block from the emitted .js, and tools/js_module_index.py reads the `@module`
// tag out of that emitted .js.
interface LoreEntry {
    category?: string;
    title?: string;
    content?: string;
    allowed_tags?: unknown;
}

interface SystemPromptPlayerLike {
    tags?: unknown[];
    state?: string;
}
