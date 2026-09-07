/**
 * ItemLibraryTriggerSuggester — "⚡ Suggest" for items (heuristic, offline).
 *
 * The item's ACTIONS decide WHICH triggers to make. Only the core actions
 * (examine, use, take, drop, equip, unequip, eat, drink, read) map to triggers,
 * one on_* per action. Tags/category then decide WHAT those triggers contain:
 *   • eat/drink → correct vital (food→Hunger, drink→Thirst, energy→Energy,
 *     medicine→HP, alcohol→Sanity)
 *   • finite uses → uses_above 0 guard + "empty" fail message
 *   • tainted/cursed → CON save that applies poisoned on fail, plus an
 *     on_examine that reveals the truth on a save
 *   • haunted → on_take whisper
 *   • lights (tag light_source/candle/etc.) → on_light (fires with the toggle)
 *     + on_toggle_off lit/unlit
 *   • books (tag book/readable) → on_read excerpt
 *   • consumables whose action list lacks eat/drink → their on_use carries the
 *     vital adjust instead
 *
 * A heuristic can only guarantee correct STRUCTURE, not great prose — so the
 * ✨ Suggest (AI) path (TriggerSuggestAI) authors the actual messages/saves.
 * Ways and areas get their own templates via suggestForNode().
 *
 * Pure heuristic — no AI calls, works offline, fully reviewable in the editor.
 * Usage:
 *   ItemLibraryTriggerSuggester.suggest({ name, description, tags, actions, uses })
 *   → [{ trigger_type, conditions, effects, ... }, ...]
 */
window.ItemLibraryTriggerSuggester = (() => {
    // ── Action → trigger type map ─────────────────────────────────────
    // The 8 core actions determine WHICH triggers to offer. Each maps to a
    // single on_* trigger (one per action). eat/drink map to their specific
    // types; the engine co-fires on_eat/on_drink with on_use, so we never make
    // a separate on_use when a consume action also exists.
    const CORE_ACTIONS = [
        { action: 'examine', type: 'on_examine' },
        { action: 'use',     type: 'on_use' },
        { action: 'take',    type: 'on_take' },
        { action: 'drop',    type: 'on_drop' },
        { action: 'equip',   type: 'on_equip' },
        { action: 'unequip', type: 'on_unequip' },
        { action: 'eat',     type: 'on_eat' },
        { action: 'drink',   type: 'on_drink' },
        { action: 'read',    type: 'on_read' },
    ];
    const CONSUME_TYPES = ['on_eat', 'on_drink'];

    // Category maps — exact whole-tag matches only (author-curated, reliable).
    // No free-text/description scanning: a word like "leather" or "earth" can
    // substring-match "eat"/"rum" and turn a spyglass into food.
    const CATEGORY_TAGS = {
        medicine: ['medicine', 'medicinal', 'bandage', 'bandages', 'antidote', 'salve', 'potion', 'healing', 'medical'],
        energy: ['energy', 'energy_drink', 'stimulant', 'caffeine'],
        alcohol: ['alcohol', 'wine', 'whiskey', 'whisky', 'beer', 'ale', 'brandy', 'scotch', 'rum', 'vodka', 'liquor', 'spirits', 'booze'],
        food: ['food', 'snack', 'meal', 'ration', 'rations', 'provisions', 'fruit', 'vegetable', 'meat', 'bread', 'cheese', 'mushroom', 'berry', 'candy', 'pastry', 'dessert', 'produce'],
        drink: ['drink', 'drinkable', 'beverage', 'water', 'liquid', 'fluid', 'tea', 'juice', 'soda', 'milk', 'soup', 'broth', 'hydration'],
        weapon: ['weapon', 'sword', 'knife', 'knives', 'dagger', 'blade', 'axe', 'mace', 'spear', 'bow', 'arrow', 'gun', 'pistol', 'rifle', 'sharp', 'melee', 'ranged'],
        tool: ['key', 'keys', 'lockpick', 'lockpicks', 'crowbar', 'screwdriver', 'wrench', 'pick', 'wire', 'tool', 'tools', 'multitool'],
        light: ['light', 'light_source', 'lantern', 'torch', 'candle', 'candles', 'lamp', 'flashlight', 'glowstick', 'lit'],
        book: ['book', 'note', 'notes', 'journal', 'letter', 'scroll', 'pamphlet', 'map', 'newspaper', 'diary', 'manual', 'bible', 'codex', 'readable', 'document'],
        container: ['container', 'box', 'chest', 'jar', 'pouch', 'satchel', 'crate', 'bag', 'backpack', 'cabinet', 'vial', 'case', 'bottle'],
        wearable: ['clothing', 'clothes', 'armor', 'armour', 'accessory', 'jewelry', 'ring', 'necklace', 'glasses', 'hat', 'boots', 'shoes', 'shirt', 'pants', 'underwear', 'bra', 'panties', 'briefs', 'socks', 'belt', 'coat', 'jacket', 'dress', 'gown'],
    };
    const CONSUMABLE_ORDER = ['medicine', 'energy', 'alcohol', 'food', 'drink'];
    const SUSPICION_TAGS = ['tainted', 'poisoned', 'poison', 'cursed', 'haunted', 'occult', 'arcane', 'magic', 'forbidden'];
    const HAUNT_TAGS = ['cursed', 'haunted', 'possessed'];

    const hasTag = (tags, list) => (tags || []).some(t => list.includes(String(t).trim().toLowerCase()));

    /** Normalize an item's actions string/array to a lowercased Set. */
    function actionSet(fields) {
        const raw = Array.isArray(fields?.actions)
            ? fields.actions
            : (typeof fields?.actions === 'string' ? fields.actions.split(',').map(s => s.trim()).filter(Boolean) : []);
        return new Set(raw.map(a => String(a).trim().toLowerCase()));
    }

    /**
     * The action → trigger_type pairs to generate, from an item's actions.
     * Only the 8 core actions produce triggers; consume (eat/drink) collapses
     * to its specific type (never also on_use, since the engine co-fires).
     */
    function actionTriggerPairs(fields) {
        const act = actionSet(fields);
        const pairs = [];
        for (const { action, type } of CORE_ACTIONS) {
            if (!act.has(action)) continue;
            if (type === 'on_use' && act.has('eat') && act.has('drink')) {
                // both consume actions — still include bare on_use for "use" alone
                pairs.push({ type, action });
                continue;
            }
            if (type === 'on_use') {
                // if any consume action exists, the engine's consume trigger
                // already covers "use"; don't double-offer on_use.
                if (act.has('eat') || act.has('drink')) continue;
            }
            pairs.push({ type, action });
        }
        return pairs;
    }

    function firstSentence(desc) {
        const raw = String(desc || '').trim();
        if (!raw) return '';
        const m = raw.match(/^[^.!?\n]+[.!?]/);
        return m ? m[0].trim() : raw;
    }

    function isSuspicious({ tags }) {
        return hasTag(tags, SUSPICION_TAGS);
    }

    function isHaunted({ tags }) {
        return hasTag(tags, HAUNT_TAGS);
    }

    function basicTrigger(triggerType, effects, extra = {}) {
        return {
            trigger_type: triggerType,
            target_name: '',
            target_state: '',
            conditions: extra.conditions || [],
            effects,
            success_message: extra.success_message || '',
            fail_message: extra.fail_message || '',
        };
    }

    const msg = (text) => ({ type: 'message', params: { message: text } });

    /**
     * Classify an item from its tags + explicit actions only.
     *  1. First tag that maps to a category wins (consumable kinds ordered so
     *     energy/alcohol/medicine beat a generic food/drink tag).
     *  2. No tag → explicit actions decide: drink → drink, eat → food,
     *     read → book, equip/wear → wearable.
     *  3. Otherwise generic (examine/use only — never "eat the spyglass").
     */
    function categorize({ tags, actions, equip_slots }) {
        const tagsL = (tags || []).map(t => String(t).trim().toLowerCase());
        const act = new Set((actions || []).map(a => String(a).trim().toLowerCase()));

        let fallbackCat = null;
        for (const cat of CONSUMABLE_ORDER) {
            if (hasTag(tagsL, CATEGORY_TAGS[cat])) return { cat };
        }
        for (const cat of ['weapon', 'tool', 'light', 'book', 'container', 'wearable']) {
            if (hasTag(tagsL, CATEGORY_TAGS[cat])) { fallbackCat = cat; break; }
        }
        if (fallbackCat) return { cat: fallbackCat };

        if (act.has('drink') || act.has('drinkable')) return { cat: 'drink' };
        if (act.has('eat')) return { cat: 'food' };
        if (act.has('read')) return { cat: 'book' };
        if (act.has('equip') || act.has('wear')) return { cat: 'wearable' };
        if (equip_slots && equip_slots.length) return { cat: 'wearable' };

        return { cat: 'generic' };
    }

    function consumeVital(type, cat, suspicious) {
        if (suspicious && ['food', 'drink', 'alcohol'].includes(cat)) return { stat: 'Thirst', amount: -20 };
        if (cat === 'medicine') return { stat: 'HP', amount: 10 };
        if (cat === 'energy') return { stat: 'Energy', amount: 30 };
        if (cat === 'alcohol') return { stat: 'Sanity', amount: 15 };
        if (type === 'on_eat') return { stat: 'Hunger', amount: -30 };
        if (type === 'on_drink') return { stat: 'Thirst', amount: -30 };
        if (cat === 'food') return { stat: 'Hunger', amount: -30 };
        return { stat: 'Thirst', amount: -20 };
    }

    function examineSkill({ tags }) {
        if (hasTag(tags, ['occult', 'cursed', 'arcane', 'magic', 'forbidden'])) return 'Arcana';
        if (hasTag(tags, ['food', 'drink', 'water', 'supplies', 'alcohol', 'wine'])) return 'Survival';
        return 'Perception';
    }

    /**
     * Build a single trigger skeleton for one on_* type, with sensible
     * parameters derived from category/tags/description. This is the heuristic
     * floor — good structure, correct types, placeholders. The AI path authors
     * the actual messages/vitals/saves instead.
     */
    function buildSkeleton(type, fields) {
        const name = String(fields.name || '').trim() || 'this item';
        const label = name;
        const description = String(fields.description || '');
        const tags = Array.isArray(fields.tags) ? fields.tags : [];
        const usesRaw = parseInt(fields.uses ?? -1);
        const uses = Number.isNaN(usesRaw) ? -1 : usesRaw;
        const finite = uses > 0;
        const cat = categorize(fields).cat;
        const act = actionSet(fields);
        const hasEatDrink = act.has('eat') || act.has('drink');
        const suspicious = isSuspicious({ tags });
        const haunted = isHaunted({ tags });
        const taste = firstSentence(description);
        const skill = examineSkill({ tags });
        const truth = hasTag(tags, ['cursed', 'haunted', 'occult', 'arcane'])
            ? `there's something deeply wrong with it — a wrongness that doesn't feel natural.`
            : `a sharp, off note hides in it — this has been tampered with.`;

        const effects = [];
        let conditions = [];
        let fail_message = '';

        if (type === 'on_examine') {
            if (suspicious) {
                effects.push({ type: 'save', params: {
                    stat: skill,
                    dc: 12,
                    target: 'self',
                    on_success: [msg(`You examine the ${label} closely. ${truth}`)],
                    on_fail: [msg(`The ${label} looks ordinary enough. Seems safe.`)],
                } });
            } else {
                effects.push(msg(`You look over the ${label}.${taste ? ' ' + taste : ''}`.trim()));
            }
        } else if (type === 'on_use') {
            // A consumable whose action list lacks eat/drink uses "use" to
            // consume — carry the category's vital adjust here (so a "use"
            // that closes the flavor gap still works).
            if (['food', 'drink', 'alcohol', 'energy', 'medicine'].includes(cat) && !hasEatDrink) {
                const cVital = consumeVital('on_use', cat, suspicious);
                effects.push({ type: 'adjust_vital', params: {
                    stat: cVital.stat,
                    amount: cVital.amount,
                    target: 'self',
                    success_message: `You use the ${label}.${taste ? ' ' + taste : ''}`,
                } });
                if (suspicious) {
                    effects.push({ type: 'save', params: {
                        stat: 'CON',
                        dc: 12,
                        target: 'self',
                        on_success: [msg(`You use the ${label} — it settles.`)],
                        on_fail: [
                            { type: 'apply_condition', params: { condition: 'poisoned', duration: 6, target: 'self', source_type: 'item' } },
                            msg(`Your stomach lurches — the ${label} was wrong. You feel poisoned.`),
                        ],
                    } });
                }
                if (finite) {
                    conditions = [{ type: 'uses_above', value: 0 }];
                    fail_message = `The ${label} is empty.`;
                }
            } else {
                effects.push(msg(`You handle the ${label} — nothing obvious happens.`));
            }
        } else if (type === 'on_take') {
            if (haunted) {
                effects.push(msg(`As you lift the ${label}, a faint whisper curls at the edge of your hearing.`));
            } else {
                effects.push(msg(`You pick up the ${label}.`));
            }
        } else if (type === 'on_drop') {
            effects.push(msg(`You set down the ${label}.`));
        } else if (type === 'on_equip') {
            effects.push(msg(`You ready the ${label}.`));
        } else if (type === 'on_unequip') {
            effects.push(msg(`You stow the ${label}.`));
        } else if (type === 'on_read') {
            const lead = taste ? ' ' + taste : '';
            effects.push(msg(`You open ${label}.${lead}`));
        } else if (type === 'on_light') {
            effects.push({ type: 'set_state', params: { node_id: 'self', state: 'lit', target: 'self' } });
            effects.push(msg(`You light the ${label}.`));
        } else if (type === 'on_toggle_off') {
            effects.push({ type: 'set_state', params: { node_id: 'self', state: 'unlit', target: 'self' } });
            effects.push(msg(`The ${label} goes dark.`));
        } else if (CONSUME_TYPES.includes(type)) {
            const verb = type === 'on_eat' ? 'eat' : 'drink';
            const cVital = consumeVital(type, cat, suspicious);
            effects.push({ type: 'adjust_vital', params: {
                stat: cVital.stat,
                amount: cVital.amount,
                target: 'self',
                success_message: `You ${verb} the ${label}.${taste ? ' ' + taste : ''}`,
            } });
            if (suspicious) {
                effects.push({ type: 'save', params: {
                    stat: 'CON',
                    dc: 12,
                    target: 'self',
                    on_success: [msg(`You ${verb} the ${label} — it settles.`)],
                    on_fail: [
                        { type: 'apply_condition', params: { condition: 'poisoned', duration: 6, target: 'self', source_type: 'item' } },
                        msg(`Your stomach lurches — the ${label} was wrong. You feel poisoned.`),
                    ],
                } });
            }
            if (finite) {
                conditions = [{ type: 'uses_above', value: 0 }];
                fail_message = `The ${label} is empty.`;
            }
        } else {
            effects.push(msg(`You ${type.replace(/^on_/, '')} the ${label}.`));
        }

        return basicTrigger(type, effects, { conditions, fail_message });
    }

    /**
     * Generate a full trigger set for an item.
     * WHICH triggers: from the item's own actions (examine/use/take/drop/
     * equip/unequip/eat/drink). WHAT they contain: category/tag-based defaults
     * (vital adjust, suspicious reveal, haunted whisper, empty guard).
     */
    /**
     * Generate a full trigger set for an item.
     * WHICH triggers: from the item's own actions (the action→trigger map).
     * WHAT they contain: category/tag-based defaults (vital adjust, suspicious
     * reveal, haunted whisper, empty guard). A few high-value extras are added
     * from tags when the item clearly is one: lights get lit/unlit toggles,
     * books get on_read, containers holding stuff get on_depleted.
     */
    /**
     * Decide WHICH on_* trigger types an item should have, based on its actions
     * plus a couple of tag/category augments (lights → on_light + toggles,
     * books → on_read). Returns an ordered, de-duplicated array.
     */
    function plan(fields = {}) {
        const { cat } = categorize(fields);
        const tags = Array.isArray(fields.tags) ? fields.tags : [];
        const typeSet = new Set();

        for (const { type } of actionTriggerPairs(fields)) typeSet.add(type);

        const isLight = cat === 'light' || hasTag(tags, ['light', 'light_source', 'toggleable', 'lantern', 'candle', 'flashlight', 'lamp']);
        if (isLight) {
            // `on_light` and `on_toggle_on` fire together on a toggle-on
            // (task-396: on_light is the companion hook). Emit just `on_light`
            // for the on-side + `on_toggle_off` for the off-side — never both
            // on-side triggers on the same item.
            typeSet.add('on_light');
            typeSet.add('on_toggle_off');
        }
        if (cat === 'book') typeSet.add('on_read');

        // Category priority for menu order.
        const priority = { on_examine: 0, on_read: 1, on_use: 2, on_eat: 3, on_drink: 3, on_take: 4, on_drop: 5, on_equip: 6, on_unequip: 7, on_light: 8, on_toggle_off: 9 };
        return Array.from(typeSet).sort((a, b) => (priority[a] ?? 99) - (priority[b] ?? 99));
    }

    /**
     * Generate a full trigger set for an item (heuristic floor). Actions decide
     * the set; tags/category decide the content. Use plan() to get the same set
     * of trigger types the AI path receives.
     */
    function generate(fields = {}) {
        const out = [];
        for (const type of plan(fields)) {
            out.push(buildSkeleton(type, fields));
        }
        return out;
    }

    // ── Public API ────────────────────────────────────────────────────

    /**
     * Generate a full trigger set for an item — actions decide WHICH triggers,
     * tags/category decide WHAT they contain.
     */
    function suggest(fields = {}) {
        return generate(fields);
    }

    // ── Way (door/passage) suggestions ────────────────────────────────
    function waySuggestions(fields = {}) {
        const name = String(fields.name || '').trim() || 'this way';
        const description = String(fields.description || '').trim();
        const tags = Array.isArray(fields.tags) ? fields.tags : [];
        const state = String(fields.current_state || '').trim() || 'closed';
        const descLine = description ? ` ${description}` : '';
        const out = [];

        out.push(basicTrigger('on_examine', [msg(`You examine the ${name}.${descLine}`)]));
        if (state !== 'open' && state !== 'hidden') {
            out.push(basicTrigger('on_open', [msg(`You push the ${name} open.`)]));
        } else {
            out.push(basicTrigger('on_close', [msg(`You close the ${name}.`)]));
        }
        out.push(basicTrigger('on_enter', [msg(`You pass through the ${name}.`)]));
        if (isHaunted({ tags })) {
            out.push(basicTrigger('on_open', [{ type: 'save', params: {
                stat: 'WIS', dc: 12, target: 'self',
                on_success: [msg(`The ${name} gives way grudgingly.`)],
                on_fail: [msg(`A cold dread grips you — the ${name} seems to resist being moved.`)],
            } }]));
        }
        return out;
    }

    // ── Area (room) suggestions ───────────────────────────────────────
    function areaSuggestions(fields = {}) {
        const name = String(fields.name || '').trim() || 'this place';
        const description = String(fields.description || '').trim();
        const lead = firstSentence(description) || `You step into ${name}.`;
        return [
            basicTrigger('on_enter', [msg(`${lead}`)]),
            basicTrigger('on_examine', [msg(`You survey ${name}. ${firstSentence(description) || ''}`.trim())]),
            basicTrigger('on_tick', [msg(`${name} settles around you.`)], { conditions: [{ type: 'random_chance', value: 10 }] }),
        ];
    }

    /**
     * Suggest triggers for a graph node by kind.
     * item → action-driven set; way → door/passage flavor
     * (examine/open/close/enter + haunted WIS gate); area → enter/examine/tick
     * ambience.
     */
    function suggestForNode(kind, fields = {}) {
        if (kind === 'way') return waySuggestions(fields);
        if (kind === 'area') return areaSuggestions(fields);
        return suggest(fields);
    }

    /**
     * The ordered trigger-type plan for any node kind — what the heuristic will
     * build and exactly what the AI path is asked to author (one entry per type).
     */
    function planForNode(kind, fields = {}) {
        if (kind === 'way') {
            const state = String(fields.current_state || '').trim() || 'closed';
            const out = ['on_examine', 'on_enter'];
            out.push(state === 'open' || state === 'hidden' ? 'on_close' : 'on_open');
            if (isHaunted({ tags: Array.isArray(fields.tags) ? fields.tags : [] })) out.push('on_open');
            return out;
        }
        if (kind === 'area') return ['on_enter', 'on_examine', 'on_tick'];
        return plan(fields);
    }

    return {
        suggest,
        suggestForNode,
        generate,
        plan,
        planForNode,
        categorize,
        actionTriggerPairs,
        _test: { consumeVital, isSuspicious, isHaunted, examineSkill, categorize, actionTriggerPairs, plan },
    };
})();