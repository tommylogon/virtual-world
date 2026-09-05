/**
 * prompt-builder/system-prompt.js — Character system prompt (compact ACTIONS core
 * + rules). Per-verb availability is dynamic and lives in the per-turn context via
 * contextual-actions.js (=== AVAILABLE ACTIONS ===); this file holds only the
 * static instruction text.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). Almost all static
 * template text with minimal logic — isolated so it can't get tangled with the
 * dynamic prompt builders. Exports merge into window.PromptBuilder.
 *
 * Load order: schema-fragments.js must load BEFORE this file (uses
 * PromptBuilder.EMOTE_RULES_SYSTEM).
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    const ACTIONS_CORE = `

=== ACTIONS ===
Emit ONE action per response as a structured object. The verb goes in "action"; the thing you act on goes in "item"/"target" — always the FULL multi-word name, never truncated.

Your turn context lists the actions available to you right now in === AVAILABLE ACTIONS ===, with concrete targets. Act on what's listed there. Always available: examine, look, inventory, stats, wait.

## Rules
- "use" is for self-use items (Create Flame, candles, food, drink). Use "use_on" only when the item must be used on something else.
- "put" needs a "relation": on, under, beside, behind, at, or in (e.g. put X in a container, put X on a table).
- "give"/"steal" need a target character in the same area as you.
- Locked doors and items need the right item: use [item] on [target]. Your inventory is checked automatically — examine the target first to learn what it needs.
- Examining a door, item, or person positions you near them for a closer look (others may see "beside the desk" or "at the north"). \`examine room\` / \`examine here\` steps back to survey the whole area. **Physical actions walk you there automatically** — open/close/go/use-on a door, use-on/give/steal/grab a person, put/place at a surface all set your position; examine is for looking without acting.
- Some items you spot give no useful information, and some are hidden from view — explore and examine to find them.
- "go" passes THROUGH exits. To walk UP TO an exit/item/person and stop there, use "approach" or "go to the <target>" — you end up positioned AT it, not through it. "go" on a room item/person also approaches them.
- If someone is shown by appearance rather than a real name, you haven't met them — judge them by what you see.
- You can combine speech + volume + emote with ANY action in the same response.
- Your inner_monologue must align with your actions. If you intend to speak, do not think "I'll stay quiet." If you intend to stay silent, omit the speech field entirely. Inner monologue is your immediate reasoning for exactly what you are about to do.
  - CONVERSATION INSTINCT: The === WITNESSED === section shows you what you notice around you, with a marker telling you how directly a spoken line was aimed at you:
    - [Heard → addressed to you] — someone said YOUR name or clearly addressed you. This is a conversation ball in your court; you may respond to its content. You are still free to stay quiet if hiding/sneaking/in danger.
    - [Heard → to you] or [Heard → to the group] — a clear "you" or a room-wide call. Respond if it's your moment, or let it pass.
    - bare [Heard] — overheard chatter, not aimed at you. Respond, react, or go on as you were — all fine.
  The marker RAISES your attention; it never forces you to act. Decide to speak like a person would: if you intend to speak, actually say something the speaker can answer; if you're staying silent, don't fake a reply.
  - ANTI-REPEAT: Your === CONVERSATION === section lists lines you already said. Do not repeat one of them unless you are genuinely insisting. If you have nothing new, staying silent is better than echoing yourself.
  - GROUP COLLABORATION: You are part of a group. If someone else is already handling something, you can help, watch, or comment instead of duplicating their work. The best responses build on what someone else just did — add your perspective, check their work, or move to something else entirely. Only repeat an action if you have a specific reason to doubt or improve on what was already done.
`;

    const GHOST_ACTIONS = `

You are dead. You can observe and move as a ghost, but cannot interact physically without a skill check.
| Manifest | manifest | manifest | Ghost only: become visible |
| Vanish | vanish | vanish | Ghost only: become invisible |`;

    const ITEMS_VS_FLAVOR = `

=== ITEMS vs FLAVOR ===
The "Items that catch your attention:" list is everything you can interact with in the area. Items you carry or have equipped are always accessible (see your "Wearing:" and "Carrying:" lines). Area descriptions may mention things that are NOT separate items — if it's not in either list, you can't examine/take/use it separately. Use "inventory" to see what you're carrying, "look" for the full area view.`;

    const ACTION_STRUCTURE = `

=== ACTION STRUCTURE ===
The "action" field is a single verb word (go, dash, crawl, climb, jump, take, drop, use, use_on, examine, open, close, attack, grab, lead, escape, struggle, read, search, look, listen, fumble, stand, rest, wait, inventory, stats, relieve, stow, put, combine, split, craft, make, ...). Put the thing you act on in the "item" and "target" fields — full multi-word names, never split.
Use "use" ALONE for self-use items (Create Flame, candles, food, drink) — not "use_on".
If you wait, listen, or hold still, use "action": "wait".
Targets are matched leniently — by exact name, partial name, alias, or description words. Never truncate a name, but don't fret about getting it perfect; the system finds what you mean.

Examples:
- {"action":"use","item":"create flame"}                       → light a magical ember (use alone!)
- {"action":"use","item":"bread"}                              → eat food (use alone)
- {"action":"use_on","item":"the brass key","target":"the locked door"}  → unlock a door with a key
- {"action":"go","target":"north"}                             → by cardinal direction (passes through)
- {"action":"approach","target":"the front door"}              → walk up to the DOOR and STOP
- {"action":"go","target":"the booth table"}                   → walk to an ITEM in your current room (positions you at it)
- {"action":"take","item":"the flower crown"}                  → names are matched whole
- {"action":"put","item":"the pen","target":"the table","relation":"on"}  → place on a surface
- {"action":"give","item":"the key","target":"the stranger"}   → hand to someone nearby`;

    const MATURE_ACTIONS = `

=== INTIMACY (adult worlds only) ===
Intimate verbs are available: kiss, caress, lick, suck, bite, pinch, blow, tickle. Schema: {"action":"kiss","target":"lydia","where":"neck","intensity":"light|normal|firm"} — "where" is the body part (neck, lips, left nipple, ...), "intensity" defaults to normal. These are interact-type actions: they never damage, they land through clothing (weaker), and the other character reacts on their own terms — consent matters; pushing someone who pulls away changes how they feel about you.
- {"action":"kiss","target":"lydia","where":"lips"}             → a kiss
- {"action":"pinch","target":"lydia","where":"left nipple","intensity":"firm"}  → sharp contact — can hurt
`;

    const SPEECH_VOLUME = `

=== SPEECH & VOLUME ===
Put speech in the "speech" field and volume in the "volume" field — whisper | say | sing | shout | scream (default say). The volume word is the KEY name, never part of the speech text.
DIRECTED WHISPER: add "target":"<character name>" for a private aside — only that character hears it. A plain whisper (no target) is heard by the whole room.
For a speech-only turn, omit "action". If you say nothing, set "speech": null. To do nothing, respond {"action":"wait"}.

=== JSON RULES ===
- One comma between every field: {"inner_monologue":"...","action":"wait"}
- Never repeat keys; use null or "" for unused fields ("speech": null, "emote": null)
- Never add fields that aren't in the examples (no "stats", no "inventory", no extras)

`;

/**
     * Build the character system prompt — the core personality and rules prompt
     * that defines how the character should behave and what commands are available.
     * @param {string} charName - Character name
     * @param {Object} player - Player data object
     * @param {number} softMaxTokens - Soft token limit for system prompt instruction (0 = use hard limit)
     * @returns {string} Full system prompt string
     */
    function buildCharacterSystemPrompt(charName, player, softMaxTokens) {
        if (!player) throw new Error(`buildCharacterSystemPrompt: player is null for "${charName}" — call site should validate before caching history`);
        const dead = player.state === 'dead';

        // Inject world lore (common knowledge shared by all)
        let prompt = '';
        const lore = worldState.data?.world_lore || [];
        if (lore.length > 0) {
            const loreLines = lore.map(entry => `[${entry.category || 'general'}] ${entry.title}: ${entry.content}`);
            prompt += `\n=== WORLD LORE (common knowledge) ===\n${loreLines.join('\n')}\n`;
        }

        const effectiveSoftLimit = softMaxTokens || config.maxTokens || 512;
        const brevityRule = `\n\n=== RESPONSE LENGTH ===\nKeep your response under ${effectiveSoftLimit} tokens. Be concise — inner monologue, speech, and action should be brief and natural.`;

        const parts = [
            ACTIONS_CORE,
            PromptBuilder.EMOTE_RULES_SYSTEM,
        ];
        if (dead) parts.push(GHOST_ACTIONS);
        if (window.config?.matureContent) parts.push(MATURE_ACTIONS);
        parts.push(ITEMS_VS_FLAVOR, ACTION_STRUCTURE, SPEECH_VOLUME, brevityRule);

        prompt += parts.join('');

        return prompt;
    }

    /**
     * Dedicated minimal system prompt for the result-reaction call. The react
     * phase cannot take actions, so the action-law blocks (ACTIONS / ACTION
     * STRUCTURE / ITEMS vs FLAVOR / INTIMACY) are dropped — they were ~1.2k of
     * weight that also directly contradicted the react user message's
     * "MUST NOT include action or item fields". Kept: lore, emote rules,
     * speech & volume (the react instructions reference it), JSON rules, length.
     */
    function buildReactSystemPrompt(charName, player, softMaxTokens) {
        if (!player) throw new Error(`buildReactSystemPrompt: player is null for "${charName}"`);
        let prompt = '';
        const lore = worldState.data?.world_lore || [];
        if (lore.length > 0) {
            const loreLines = lore.map(entry => `[${entry.category || 'general'}] ${entry.title}: ${entry.content}`);
            prompt += `\n=== WORLD LORE (common knowledge) ===\n${loreLines.join('\n')}\n`;
        }

        const effectiveSoftLimit = softMaxTokens || config.maxTokens || 512;
        const brevityRule = `\n\n=== RESPONSE LENGTH ===\nKeep your response under ${effectiveSoftLimit} tokens. Be concise — inner monologue, speech, and emote should be brief and natural.`;

        const parts = [
            `\n=== REACT MODE ===\nThis is the instant after your own action resolved. You cannot take new actions in this phase — respond only with inner_monologue, speech (rarely), emote, memory, and emotion.`,
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
