/**
 * prompt-builder/helpers.js — Leaf-level utility functions for prompt building.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). These are
 * side-effect-free helpers that only reference global state (worldState, VW)
 * at call time. Exports merge into the shared window.PromptBuilder namespace
 * via Object.assign — load order between the split files does not matter, and
 * nothing executes at load time.
 *
 * Cross-file internal calls use PromptBuilder.<fn>(...).
 *
 * @module prompt-builder/helpers — leaf prompt utilities
 * @contributes lightToLevel, wayHandle, buildRelationMap, anonymousName, voiceLabel, hasPlan, secondPersonDesc, frameSelfSpeech
 * @powers Narration — consistent labelling of rooms/items/strangers, and self-framing, across every prompt
 * @relates the leaf layer; used by room-context, contextual-actions, character-state
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    /**
     * Convert a numeric light value (0-100) to a level string.
     * Mirrors engine/lighting.py:light_to_level.
     * @param {number} value - Light value 0-100
     * @returns {string} Level name: 'pitch_black' | 'dim' | 'normal' | 'bright' | 'blinding'
     */
    function lightToLevel(value: unknown): string {
        const numValue = parseInt(String(value)) || 50;
        if (numValue <= 20) return 'pitch_black';
        if (numValue <= 40) return 'dim';
        if (numValue <= 70) return 'normal';
        if (numValue <= 90) return 'bright';
        return 'blinding';
    }

    /**
     * Strip a leading article from a description fragment ("a tall man" → "tall man").
     */
    function stripLeadingArticle(text: string): string {
        return text.replace(/^(a|an|the)\s+/i, '');
    }

    /**
     * Indefinite article for an item name ("a toy_box", "an Ink Pen").
     */
    function indefiniteArticle(name: unknown): string {
        return /^[aeiou]/i.test(String(name || '')) ? 'an' : 'a';
    }

    /**
     * A reference handle for an exit/way: the exit label (direction) when set,
     * else a short name derived from the way node's name (strip the source area's
     * "Name - " prefix, underscores → spaces), else "door". Shared by room-context
     * and the contextual-actions block so both name a given exit the same way.
     * @param {Object} exitData - Exit entry (label, direction)
     * @param {Object} doorNode - The way node, or null
     * @param {string} areaName - Current area name, for stripping the node prefix
     * @returns {string} A display handle for the exit
     */
    function wayHandle(exitData: { label?: unknown; direction?: unknown } | null | undefined, doorNode: { name?: unknown } | null | undefined, areaName: string): string {
        const label = String(exitData?.label ?? exitData?.direction ?? '').trim();
        if (label) return label;
        if (doorNode?.name) {
            let name = String(doorNode.name).trim();
            if (areaName && name.toLowerCase().startsWith(`${String(areaName).toLowerCase()} - `)) {
                name = name.slice(areaName.length + 3).trim();
            }
            name = name.replace(/_/g, ' ').trim();
            if (name) return name;
        }
        return 'door';
    }

    /**
     * Map item id → { prep, anchorName } for every item that sits in a spatial
     * relation (on/under/behind/beside/at/in) to an anchor item that is itself
     * present in the area. This lets the item listing tell the agent *where*
     * each object is, instead of a flat name list (task-105).
     *
     * Edges pointing at the area itself (e.g. table → room) are not spatial
     * relations to an anchor, so those items render flat.
     */
    function buildRelationMap(areaItems: { id: string }[]): Record<string, { prep: unknown; anchorName: unknown }> {
        const relationMap: Record<string, { prep: unknown; anchorName: unknown }> = {};
        const spatialTypes = ['on', 'under', 'behind', 'beside', 'at', 'in'];
        const areaItemIds = new Set<string>(areaItems.map((item: { id: string }) => item.id));
        for (const edge of worldState.graph?.edges || []) {
            if (!spatialTypes.includes(edge.type)) continue;
            const anchorId = edge.target;
            if (!areaItemIds.has(anchorId)) continue;
            const sourceNode = worldState.getNode(edge.source);
            if (!sourceNode || sourceNode.type !== 'item') continue;
            const anchorNode = worldState.getNode(anchorId);
            relationMap[edge.source] = {
                prep: edge.type,
                anchorName: anchorNode?.name || anchorId
            };
        }
        return relationMap;
    }

    /**
     * Does *charName* already know *targetName* — either because they have met,
     * or because the authored `known` registry lists them? A known character is
     * never masked as a stranger (task-154), for faces AND for voices.
     */
    function isKnownToViewer(charName: string, targetName: string): boolean {
        if (worldState.hasMet(charName, targetName)) return true;
        const viewer = worldState.data?.players?.[charName];
        const known = new Set<string>((viewer?.known || []).map((value: unknown) => String(value)));
        const knownLower = new Set<string>([...known].map((value: string) => value.toLowerCase()));
        const targetSlug = String(targetName || '').toLowerCase().replace(/\s+/g, '_');
        return knownLower.has(String(targetName || '').toLowerCase())
            || knownLower.has('player_' + targetSlug)
            || knownLower.has('character_' + targetSlug);
    }

    /**
     * One tag → label table for an unrecognised speaker, for BOTH channels.
     *
     * `anonymousName` (you can see them) and `voiceLabel` (you can only hear
     * them) used to carry separate maps, and they drifted: the seen map had
     * `animal`, the heard map did not. The same cat therefore read "an animal"
     * in the room and, through a wall, fell through to the pronoun heuristic —
     * and because animal descriptions are freely written with "his" (whiskers:
     * "darker striping along his flanks"), came out as **"a man's voice"**. A
     * seen/heard pair that contradicts itself is worse than either being vague,
     * so the two labels now come from one row.
     */
    const SPEAKER_TAGS: Record<string, { seen: string; heard: string }> = {
        female: { seen: 'the woman', heard: "a woman's voice" },
        male: { seen: 'the man', heard: "a man's voice" },
        woman: { seen: 'the woman', heard: "a woman's voice" },
        man: { seen: 'the man', heard: "a man's voice" },
        girl: { seen: 'a girl', heard: "a girl's voice" },
        boy: { seen: 'a boy', heard: "a boy's voice" },
        child: { seen: 'a child', heard: "a child's voice" },
        animal: { seen: 'an animal', heard: "an animal's voice" },
    };

    /**
     * Species labels for a heard-only speaker, checked BEFORE the generic table.
     *
     * A voice you cannot place is better described by what is making it than by
     * the gender of a human it may not be: "a cat's voice" tells the model more
     * than "an animal's voice", and neither can be a "man's voice" by accident.
     * These are the species tags the character library already carries, so this
     * needed no new authoring.
     */
    const SPECIES_VOICE_LABELS: Record<string, string> = {
        cat: "a cat's voice", kitten: "a kitten's voice", dog: "a dog's voice",
        puppy: "a puppy's voice", fox: "a fox's voice", wolf: "a wolf's voice",
        bear: "a bear's voice", boar: "a boar's voice", worg: "a worg's voice",
        rabbit: "a rabbit's voice", rat: "a rat's voice", mouse: "a mouse's voice",
        bird: "a bird's voice", raven: "a raven's voice", crow: "a crow's voice",
        owl: "an owl's voice", frog: "a frog's voice", toad: "a toad's voice",
        sheep: "a sheep's voice", goat: "a goat's voice", cow: "a cow's voice",
        horse: "a horse's voice", deer: "a deer's voice", snake: "a snake's voice",
        insect: "an insect's voice", bat: "a bat's voice", fish: "a fish's voice",
        beast: "a beast's voice", creature: "a creature's voice",
    };

    /** Species tags too broad to be worth reporting over a named one. */
    const GENERIC_SPECIES = ['animal', 'bird', 'beast', 'creature', 'pet'];

    /** Tags that mark a character as an anthropomorph — presented as a person. */
    const ANTHRO_TAGS = ['anthro', 'anthropomorphic', 'humanoid'];

    /**
     * Return how this character should refer to another.
     * Known characters are called by their real name. Strangers (no relationship
     * record yet) are labelled by their appearance so the character never
     * learns a name they haven't been told (task-154).
     */
    function anonymousName(charName: string, targetName: string, targetDesc: string): string {
        if (isKnownToViewer(charName, targetName)) return targetName;
        const player = worldState.data?.players?.[targetName] || {};
        for (const tag of (player.tags || [])) {
            const mapped = SPEAKER_TAGS[String(tag).toLowerCase()];
            if (mapped) return mapped.seen;
        }
        const firstSentence = (targetDesc || '').split(/[.!?]/)[0].trim();
        if (firstSentence) return `the ${stripLeadingArticle(firstSentence).toLowerCase()}`;
        return 'the stranger';
    }

    /**
     * How a character should refer to someone they can HEAR but not see
     * (cross-room speech). If you know someone, you know their voice — a met or
     * authored-known speaker is named. Otherwise physical appearance is useless
     * through a wall, so a non-human is named by its species, and only then does
     * a human fall back to gender or the pronouns in their description.
     *
     * Order matters here, and getting it wrong is the bug this fixes. The animal
     * reading is checked BEFORE the gender tags, because these characters carry
     * both: `male|animal|worg` read as "a man's voice" when the gender tag was
     * consulted first. A character tagged `anthro` is deliberately exempt — it is
     * presented as a person, so "a woman's voice" agrees with the "the woman" the
     * same character gets when seen.
     */
    function voiceLabel(charName: string, targetName: string): string {
        if (isKnownToViewer(charName, targetName)) return targetName;
        const player = worldState.data?.players?.[targetName] || {};
        const tags: string[] = ((player.tags || []) as unknown[]).map((t: unknown) => String(t).toLowerCase());
        const anthro = tags.some(t => ANTHRO_TAGS.indexOf(t) >= 0);
        const nonHuman = tags.indexOf('animal') >= 0
            || tags.some(t => Object.prototype.hasOwnProperty.call(SPECIES_VOICE_LABELS, t));

        if (nonHuman && !anthro) {
            // Most specific species wins, so `bird|raven` is heard as the raven
            // rather than the bird.
            for (const allowGeneric of [false, true]) {
                for (const tag of tags) {
                    const label = SPECIES_VOICE_LABELS[tag];
                    if (!label) continue;
                    if ((GENERIC_SPECIES.indexOf(tag) >= 0) !== allowGeneric) continue;
                    return label;
                }
            }
            return "an animal's voice";
        }

        for (const tag of tags) {
            const mapped = SPEAKER_TAGS[tag];
            if (mapped) return mapped.heard;
        }
        // Pronouns are the last resort and only for a speaker nothing marks as an
        // animal: "his" in a sentence about a cat's flanks is evidence about the
        // cat, and reading it as a man is what produced "a man's voice" here.
        if (!nonHuman) {
            const desc = player.base_description || player.description || '';
            if (/\b(she|her|hers)\b/i.test(desc)) return "a woman's voice";
            if (/\b(he|him|his)\b/i.test(desc)) return "a man's voice";
        }
        return 'a voice';
    }

    /**
     * The verb a WITNESSED line uses for a spoken level.
     *
     * `speech_level` rides on every hearing entry (speech.py stamps it), so a
     * shouted or whispered line used to render as "said" purely because the verb
     * was a string literal — the model was told the wrong delivery and reacted to
     * a whisper as small talk and to a scream as conversation. The turn-event
     * description stays `said:` on purpose: that is a machine-parsed marker with
     * its own tests, and it is not what the character reads.
     */
    const SPEECH_VERBS: Record<string, string> = {
        whisper: 'whispered', normal: 'said', say: 'said', speak: 'said',
        shout: 'shouted', scream: 'screamed', sing: 'sang',
    };

    function speechVerb(level: unknown): string {
        return SPEECH_VERBS[String(level || '').trim().toLowerCase()] || 'said';
    }

    /**
     * Check if a character has an active plan in the AgentEngine.
     * @param {string} charName - Character name
     * @returns {boolean} True if plan exists and has steps remaining
     */
    function hasPlan(charName: string): boolean {
        // task-185: read via PlanTracker (the old read hit a replaced store).
        const plan = (window as unknown as { PlanTracker?: { getPlan(name: string): unknown } }).PlanTracker?.getPlan(charName);
        return !!plan && (plan as unknown[]).length > 0;
    }

    /**
     * Re-frame a third-person appearance description into second person so the
     * character reads about THEMSELVES ("You are a woman who stands... your
     * slender frame...") instead of a stranger ("A woman stands... her... ").
     * Handles leading "A/An/The <noun> <verb>s", "She/He <verb>s", pronoun
     * swaps (she/her/his/him → you/your), and verb agreement ("you stands").
     */
    function secondPersonDesc(desc: string): string {
        if (!desc) return '';
        let text = desc.trim();
        const subjectVerbs = 'stands?|sits?|lies?|rests?|leans?|kneels?|looks?|stares?|moves?|walks?|hangs?|awaits?|seems?';
        text = text.replace(new RegExp(`^(?:A|An|The)\\s+(.+?)\\s+(${subjectVerbs})\\b`, 'i'),
            (match: string, noun: string, verb: string) => {
                const article = match.startsWith('A ') ? 'a' : match.startsWith('An ') ? 'an' : match.startsWith('The ') ? 'the' : match.startsWith('a ') ? 'a' : match.startsWith('an ') ? 'an' : match.startsWith('the ') ? 'the' : '';
                return `You are ${article} ${noun} who ${verb}`;
            });
        text = text.replace(new RegExp(`^(She|He)\\s+(${subjectVerbs})\\b`, 'i'),
            (match: string, pronoun: string, verb: string) => `You ${verb.replace(/s$/, '')}`);
        text = text.replace(/\bshe\b/gi, 'you');
        text = text.replace(/\bher\b/gi, 'your');
        text = text.replace(/\bhers\b/gi, 'yours');
        text = text.replace(/\bhe\b/gi, 'you');
        text = text.replace(/\bhim\b/gi, 'you');
        text = text.replace(/\bhis\b/gi, 'your');
        // fix verb agreement after "you" (preserving case): "You stands" → "You stand"
        text = text.replace(new RegExp(`\\b(you)\\s+(${subjectVerbs})\\b`, 'gi'),
            (match: string, pronoun: string, verb: string) => `${pronoun} ${verb.replace(/s$/, '')}`);
        // fix plural possessive agreement: "your breasts rests" → "your breasts rest"
        // (nouns ending in s are treated as plural — regular plurals only)
        text = text.replace(/\byour\s+(\w+s)\s+(stands?|sits?|lies?|rests?|rises?|falls?|hangs?|looks?|moves?|seems?)\b/gi,
            (match: string, noun: string, verb: string) => `your ${noun} ${verb.replace(/s$/, '')}`);
        return text;
    }

    /**
     * Render a player's activity (task-131) as a short flavor string.
     * @param {object} activity - {type, target_item, ...}
     * @returns {string} e.g. "sleeping in the bed"
     */
    function describeActivity(activity: { type?: unknown; target_item?: unknown } | null | undefined): string {
        if (!activity) return '';
        const type = String(activity.type || '');
        const target = activity.target_item;
        if (target && (type === 'sleeping' || type === 'bathing' || type === 'resting')) {
            return `${type} in the ${target}`;
        }
        return type;
    }

    /**
     * Re-frame an agent's own action-result text in first person.
     *
     * The engine logs a `say` as "[Name] says: ..." — when that raw line is
     * fed back to the same agent (JUST HAPPENED / WHAT HAPPENED / memories)
     * it reads like a *third party* in the room, which made agents invent
     * phantom companions ("Jane confirms it too...") from their own name.
     *
     * @param {string} charName - The agent's own character name
     * @param {string} text - Raw action result text
     * @returns {string} Text with the agent's own name re-framed in first person
     */
    function frameSelfSpeech(charName: string, text: string): string {
        if (!text || !charName) return text || '';
        const escaped = charName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const nameRe = new RegExp(`\\[${escaped}\\]`, 'gi');
        if (!nameRe.test(text)) return text;
        return text
            .replace(new RegExp(`\\[${escaped}\\]\\s*says:`, 'gi'), 'You said:')
            .replace(nameRe, 'you');
    }

    Object.assign(window.PromptBuilder, {
        lightToLevel,
        stripLeadingArticle,
        indefiniteArticle,
        wayHandle,
        buildRelationMap,
        isKnownToViewer,
        anonymousName,
        voiceLabel,
        speechVerb,
        hasPlan,
        secondPersonDesc,
        describeActivity,
        frameSelfSpeech
    });
})();
