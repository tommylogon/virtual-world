/**
 * plan-grounding.js - Grounding validator for LLM plan steps (task-700)
 *
 * The plan phase used to emit freeform prose steps, and prose references
 * scenery: Vekka planned "eat hanging meat" against room description text and
 * burned a turn on "You don't have 'hanging meat'". This module is the fix's
 * fact side: plan steps arrive TYPED (act/item/target), and every referenced
 * entity is checked against the facts the plan prompt was built from -
 * interactable items in the area, carried items, people present, visible
 * paths, and known areas. A step whose facts do not resolve is REJECTED with
 * the reason and the fact list, so the LLM re-composes from what exists.
 *
 * Design rules (task-699, Character Pursuits):
 *   - Pure and fact-driven: this module never invents, never guesses, never
 *     resolves "whatever the LLM meant". Unknown = rejected, fail closed.
 *   - Plans are intent: a grounded step still has to survive the world when
 *     executed (the decide phase / plan executor re-verify for real).
 *   - Actor sovereignty: grounding only checks the actor's own references.
 *
 * The facts are deliberately prompt-shaped (what the LLM could see), not
 * world-truth: the engine's own visibility rules still gate the real action.
 *
 * @module agent/plan-grounding - typed plan-step grounding validator
 * @contributes PlanGrounding.collectFacts() + .ground() + .groundStep() + .render()
 * @powers NPC behaviour - plans composed from verifiable facts instead of prose
 * @relates consumed by agent/plan-manager (task-700); the plan executor
 *       (task-702) will consume the same typed steps; rejects what bug-185's
 *       step tracker used to forgive
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */

(window as unknown as { PlanGrounding: unknown }).PlanGrounding = (() => {
    'use strict';

    /**
     * The plan-step verbs the contract allows.
     *
     * ONE SOURCE OF TRUTH, TWO SCHEMAS. The executor's verb list lives in
     * `window.ActionVerbs` (mirrored from engine/action_verbs.py) and is what
     * `ActionNormalizer.isValidAction` checks. The planner needs a NARROWER
     * list - verbs that mean something as a step in a plan - but it used to
     * keep that list by hand, and the two drifted: a plan could propose a
     * verb the executor would reject as unknown, burning the character's turn
     * on a command the engine could not run.
     *
     * So the plan list is now the INTERSECTION of the curated intent list and
     * the executor's registry. A plan verb the engine does not implement can
     * never be advertised, and the planner never offers engine plumbing
     * ("manifest", "do", "i") as a plan step.
     *
     * `perform` is the one plan-only verb: it describes a sustained activity
     * ("mine until dusk") and the plan executor re-checks it against the
     * world when the step actually runs.
     */
    const PLAN_INTENT_ACTS = [
        // movement & approach
        'go', 'dash', 'approach', 'crawl', 'climb', 'jump', 'fumble',
        // world interaction
        'take', 'drop', 'use', 'use_on', 'examine', 'search', 'look',
        'listen', 'read', 'open', 'close', 'put', 'craft', 'make',
        'combine', 'split', 'wear', 'remove', 'stow',
        'eat', 'drink',
        // people
        'give', 'steal', 'grab', 'lead', 'attack', 'escape', 'struggle',
        // sustained / state
        'speak', 'perform', 'wait', 'stand', 'rest', 'sleep', 'meditate', 'bathe', 'relieve',
    ];

    const ACTS = (() => {
        const registry = (window as unknown as {
            ActionVerbs?: { VALID_SET?: Set<string>; VALID_VERBS?: string[] };
        }).ActionVerbs;
        const source = registry?.VALID_SET
            || (registry?.VALID_VERBS ? new Set(registry.VALID_VERBS) : null);
        if (!source) return new Set(PLAN_INTENT_ACTS);
        const acts = new Set<string>();
        for (const act of PLAN_INTENT_ACTS) {
            // "perform" is plan-only: it has no engine verb, the world
            // resolves it when the step runs.
            if (act === 'perform' || source.has(act)) acts.add(act);
        }
        return acts;
    })();

    const STOP_WORDS = new Set([
        'the', 'a', 'an', 'to', 'of', 'and', 'or', 'at', 'in', 'on', 'for',
        'with', 'is', 'are', 'was', 'it', 'its', "it's", 'my', 'your',
    ]);

    function words(text: unknown): string[] {
        return String(text || '')
            .toLowerCase()
            .replace(/[^a-z0-9\s]/g, ' ')
            .split(/\s+/)
            .filter((w: string) => w && !STOP_WORDS.has(w));
    }

    /**
     * Lenient fact match, in the spirit of the action target matcher: a
     * reference resolves when it shares at least one significant word with a
     * fact, or one contains the other. "dried meat" resolves "Dried meat";
     * "hanging meat" resolves nothing when no interactable carries "meat".
     * Returns the matched fact name, or null.
     */
    function matchFact(reference: unknown, pool: string[]): string | null {
        const rw = words(reference);
        if (!rw.length) return null;
        const joined = rw.join(' ');
        for (const fact of pool) {
            const fw = words(fact);
            if (!fw.length) continue;
            if (rw.some((w: string) => fw.includes(w))) return fact;
            const factJoined = fw.join(' ');
            if (factJoined.includes(joined) || joined.includes(factJoined)) return fact;
        }
        return null;
    }

    /**
     * Gather the facts a plan prompt was built from, in prompt-shaped form:
     * what the character could see and reference, not world truth.
     */
    function collectFacts(
        charName: string,
        state: any,
        player: any,
        areaName: string,
    ): { areaItems: string[]; carried: string[]; people: string[]; exits: string[]; knownAreas: string[] } {
        const win = window as any;
        const ws = win.worldState;
        const pb = win.PromptBuilder;

        const areaItems = (areaName && ws?.getItemsInArea?.(areaName) || [])
            .map((n: { name?: string }) => String(n.name || ''))
            .filter(Boolean);

        // Include contained items from reachable containers if ItemContainment is present
        const ic = win.ItemContainment;
        if (ic && typeof ic.collectReachable === 'function' && ws?.graph?.edges) {
            const topLevel = (areaName && ws?.getItemsInArea?.(areaName) || []);
            for (const item of topLevel) {
                if (!item?.id) continue;
                try {
                    const contained = ic.collectReachable([item.id], {
                        getNode: (id: string) => ws.getNode(id),
                        edges: ws.graph?.edges || [],
                    }).filter((ci: { depth?: number }) => (ci.depth || 0) > 0);
                    for (const ci of contained) {
                        if (ci?.name && !areaItems.includes(ci.name)) areaItems.push(String(ci.name));
                    }
                } catch { /* containment walk optional */ }
            }
        }

        const carriedList: string[] = [];
        const rawCarried = ws?.getInventory?.(charName) || (player?.inventory || []);
        for (const item of rawCarried) {
            const name = typeof item === 'string' ? item : item?.name;
            if (name && !carriedList.includes(name)) carriedList.push(String(name));
        }
        // Include worn/equipped items so stow/remove/examine on equipped gear grounds
        if (player?.equipment && typeof player.equipment === 'object') {
            for (const val of Object.values(player.equipment)) {
                const name = typeof val === 'string' ? val : (val as any)?.name;
                if (name && !carriedList.includes(name)) carriedList.push(String(name));
            }
        }
        const carried = carriedList.filter(Boolean);

        // Stranger-masked people matching what room-context.ts presents (bug-523)
        const peopleList: string[] = [];
        const isKnown = (targetName: string): boolean => {
            if (typeof ws?.hasMet === 'function' && ws.hasMet(charName, targetName)) return true;
            const viewerKnown = (player?.known || state?.players?.[charName]?.known || ws?.data?.players?.[charName]?.known || []) as unknown[];
            const knownLower = new Set<string>(viewerKnown.map(v => String(v || '').toLowerCase()));
            const slug = String(targetName || '').toLowerCase().replace(/\s+/g, '_');
            return knownLower.has(String(targetName || '').toLowerCase())
                || knownLower.has('player_' + slug)
                || knownLower.has('character_' + slug);
        };

        const areaPlayers = (state?.players_in_area || []) as Array<{ name?: string; description?: string; aliases?: string[] }>;
        for (const p of areaPlayers) {
            const pName = String(p.name || '').trim();
            if (!pName || pName === charName) continue;
            const known = isKnown(pName);
            let displayHandle = '';
            if (known) {
                displayHandle = pName;
            } else if (pb && typeof pb.anonymousName === 'function') {
                const pDesc = p.description || state?.players?.[pName]?.description || '';
                displayHandle = pb.anonymousName(charName, pName, pDesc);
                if (displayHandle === pName) {
                    displayHandle = '';
                }
            }
            if (!displayHandle) {
                if (known) {
                    displayHandle = pName;
                } else {
                    const targetPlayer = state?.players?.[pName] || {};
                    const tags = ((targetPlayer.tags || []) as unknown[]).map(t => String(t || '').toLowerCase());
                    if (tags.includes('female') || tags.includes('woman')) {
                        displayHandle = 'the woman';
                    } else if (tags.includes('male') || tags.includes('man')) {
                        displayHandle = 'the man';
                    } else {
                        const pDesc = p.description || targetPlayer.description || '';
                        const firstSentence = pDesc.split(/[.!?]/)[0].trim();
                        if (firstSentence) {
                            const wordsList = firstSentence.split(/\s+/);
                            const lead = wordsList[0]?.toLowerCase();
                            const stripped = (lead === 'a' || lead === 'an' || lead === 'the') ? wordsList.slice(1).join(' ') : firstSentence;
                            displayHandle = `the ${stripped.toLowerCase()}`;
                        } else {
                            displayHandle = 'the stranger';
                        }
                    }
                }
            }
            if (displayHandle && !peopleList.includes(displayHandle)) {
                peopleList.push(displayHandle);
            }
            // Add known aliases so [aka Viper] grounds
            const pAliases = p.aliases || state?.players?.[pName]?.aliases || [];
            if (Array.isArray(pAliases)) {
                for (const alias of pAliases) {
                    const aStr = String(alias || '').trim();
                    if (aStr && !peopleList.includes(aStr) && (known || aStr.toLowerCase() !== pName.toLowerCase())) {
                        peopleList.push(aStr);
                    }
                }
            }
        }
        const people = peopleList.filter(Boolean);

        const area = (areaName && state?.areas?.[areaName]) || {};
        const exitSource = area.exits_authoring || area.exits || {};
        const exitList: string[] = [];
        for (const [dir, exitData] of Object.entries(exitSource as Record<string, any>)) {
            if (dir && !exitList.includes(dir)) exitList.push(dir);
            if (exitData?.direction && !exitList.includes(exitData.direction)) exitList.push(exitData.direction);
            if (exitData?.label && !exitList.includes(exitData.label)) exitList.push(exitData.label);
            // Collect authored way handles matching prompt-builder presentation
            const doorNode = exitData?.way_id && typeof ws?.getNode === 'function' ? ws.getNode(exitData.way_id) : null;
            if (pb && typeof pb.wayHandle === 'function') {
                const handle = pb.wayHandle(exitData, doorNode, areaName);
                if (handle && !exitList.includes(handle)) exitList.push(handle);
            }
            if (doorNode?.name) {
                let dName = String(doorNode.name).trim();
                if (areaName && dName.toLowerCase().startsWith(`${String(areaName).toLowerCase()} - `)) {
                    dName = dName.slice(areaName.length + 3).trim();
                }
                dName = dName.replace(/_/g, ' ').trim();
                if (dName && !exitList.includes(dName)) exitList.push(dName);
            }
        }
        const exits = exitList.filter(Boolean);

        const knownAreas = ((player?.known || []) as unknown[]).map(String)
            .filter(Boolean);
        if (areaName && !knownAreas.includes(areaName)) knownAreas.unshift(areaName);
        return { areaItems, carried, people, exits, knownAreas };
    }

    /**
     * Validate ONE typed step against the facts. Returns null when the step
     * grounds, else the human-readable rejection reason (with the fact list
     * so the LLM can re-compose from what exists).
     *
     * TARGET TYPES (the reason this validator exists). A plan step names a
     * target, and the target's TYPE decides which fact pool it must resolve
     * against:
     *
     *   - a PATH  (a door, an exit, a way)  - lives in `exits`. Legitimate
     *     target for go / dash / approach / open / close / examine.
     *   - an ITEM (a thing you can pick up, use, search) - lives in
     *     `areaItems` / `carried`. Legitimate target for take / use / search /
     *     examine / drop.
     *   - a PERSON - lives in `people`. Legitimate target for speak / give /
     *     attack / grab.
     *   - an AREA - lives in `knownAreas`. Legitimate target for go.
     *
     * Before this split, `open dining_room_door` was REJECTED because a door
     * is a path and the check only consulted the item pool - even though the
     * prompt had just listed that door under "From where you stand, you can
     * see the following paths".
     */
    function groundStep(step: any, facts: ReturnType<typeof collectFacts>, areaName: string): string | null {
        const act = String(step?.act || '').toLowerCase().trim();
        if (!ACTS.has(act)) {
            return `unknown act "${act || '(empty)'}" - use one of: ${[...ACTS].join(', ')}`;
        }
        const item = step?.item ?? step?.target ?? '';
        const target = step?.target ?? '';
        const everything = [...facts.areaItems, ...facts.carried, ...facts.people];
        // A PATH is a valid target for the movement and door verbs.
        const pathOrItem = [...everything, ...facts.exits];
        const itemOnly = [...facts.areaItems, ...facts.carried];

        switch (act) {
            case 'go':
            case 'dash':
            case 'crawl':
            case 'climb':
            case 'jump': {
                const dest = target || item;
                if (!String(dest).trim()) {
                    return `${act} needs a target - a path visible from here or a known area`;
                }
                if (!matchFact(dest, [...facts.exits, ...facts.knownAreas])) {
                    return `no such path or known area "${dest}" - paths from here: ${facts.exits.join(', ') || '(none visible)'}; known areas: ${facts.knownAreas.join(', ') || '(none)'}`;
                }
                return null;
            }
            case 'drop':
            case 'stow':
            case 'wear':
            case 'remove':
            case 'combine':
            case 'split': {
                if (!String(item).trim()) return `${act} needs an item`;
                if (!matchFact(item, itemOnly)) {
                    return `no interactable "${item}" to ${act} - carrying: ${facts.carried.join(', ') || '(nothing)'}; interactables here: ${facts.areaItems.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
                }
                return null;
            }
            case 'approach': {
                if (!String(target || item).trim()) return 'approach needs a target';
                const ref = target || item;
                if (!matchFact(ref, [...everything, ...facts.exits, areaName])) {
                    return `nothing to walk up to called "${ref}" - here: ${everything.join(', ') || '(nothing)'}; paths: ${facts.exits.join(', ') || '(none)'}`;
                }
                return null;
            }
            case 'lead':
            case 'steal': {
                if (!matchFact(target || item, facts.people)) {
                    return `no one called "${target || item}" here - people: ${facts.people.join(', ') || '(nobody)'}`;
                }
                return null;
            }
            case 'take': {
                if (!String(item).trim()) return 'take needs an item';
                if (!matchFact(item, itemOnly)) {
                    return `no interactable "${item}" here to take - interactables: ${facts.areaItems.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
                }
                // Semantic check: you cannot "take" what you already carry.
                if (facts.carried.map(s => s.toLowerCase()).includes(String(item).toLowerCase())) {
                    return `you already carry "${item}" - use "use", "examine", or "drop" instead of "take"`;
                }
                return null;
            }
            case 'use':
            case 'eat':
            case 'drink':
            case 'craft':
            case 'make': {
                if (!String(item).trim()) return `${act} needs an item`;
                if (!matchFact(item, itemOnly)) {
                    return `no interactable "${item}" to ${act} - carrying: ${facts.carried.join(', ') || '(nothing)'}; interactables here: ${facts.areaItems.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
                }
                return null;
            }
            case 'use_on':
            case 'put': {
                if (!String(item).trim() || !String(target).trim()) {
                    return `${act} needs both item and target`;
                }
                if (!matchFact(item, itemOnly)) {
                    return `no interactable "${item}" to ${act}`;
                }
                if (!matchFact(target, pathOrItem)) {
                    return `no interactable "${target}" here to ${act} on - interactables: ${everything.join(', ') || '(none)'}`;
                }
                return null;
            }
            case 'open':
            case 'close': {
                // A door is a PATH here, not an item. Opening it must resolve
                // against the exit list or the step is rejected for the wrong
                // reason (it used to be).
                if (!String(target || item).trim()) return `${act} needs a target`;
                const ref = target || item;
                if (!matchFact(ref, pathOrItem)) {
                    return `no door or container called "${ref}" to ${act} - paths from here: ${facts.exits.join(', ') || '(none visible)'}; interactables here: ${facts.areaItems.join(', ') || '(none)'}`;
                }
                return null;
            }
            case 'examine':
            case 'read': {
                if (!String(item).trim() && !String(target).trim()) {
                    return `${act} needs an item or target`;
                }
                const ref = item || target;
                if (!matchFact(ref, [...pathOrItem, areaName])) {
                    return `no interactable "${ref}" here - interactables: ${everything.join(', ') || '(none)'}; paths: ${facts.exits.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
                }
                return null;
            }
            case 'attack':
            case 'grab': {
                if (!String(item).trim() && !String(target).trim()) {
                    return `${act} needs an item or target`;
                }
                const ref = item || target;
                if (!matchFact(ref, everything)) {
                    return `no interactable "${ref}" here - interactables: ${everything.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
                }
                return null;
            }
            case 'search': {
                // Search needs a THING to search, and a thing is an item or a
                // person - not a doorway. To look through a doorway, go there
                // first and then search what the room actually lists.
                if (!String(item).trim() && !String(target).trim()) {
                    return `search needs an item or target - a thing to look through, not a place. To look in another room, "go" there first and then "look" to see what it lists`;
                }
                const ref = item || target;
                if (!matchFact(ref, everything)) {
                    return `no interactable "${ref}" here to search - interactables: ${everything.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
                }
                return null;
            }
            case 'give': {
                if (!matchFact(item, facts.carried)) {
                    return `you are not carrying "${item}" - carrying: ${facts.carried.join(', ') || '(nothing)'}`;
                }
                if (!matchFact(target, facts.people)) {
                    return `no one called "${target}" here - people: ${facts.people.join(', ') || '(nobody)'}`;
                }
                return null;
            }
            // speak/wait/look/listen/relieve/perform carry no world reference
            // that must resolve; perform's "note" is intent, checked again by
            // the world when executed.
            default:
                return null;
        }
    }

    /** Canonical one-line rendering of a typed step, for PlanTracker storage. */
    function render(step: any): string {
        const act = String(step?.act || '').toLowerCase().trim();
        const item = String(step?.item ?? '').trim();
        const target = String(step?.target ?? '').trim();
        const text = String(step?.text ?? step?.note ?? '').trim();
        const area = String(step?.area ?? '').trim();
        const until = String(step?.until ?? '').trim();
        let out = '';
        switch (act) {
            case 'speak': out = text ? `speak: "${text}"` : 'speak'; break;
            case 'perform': out = `perform: ${text || act}`; break;
            case 'use_on': out = `use ${item} on ${target}`; break;
            case 'go': out = `go ${target || item || ''}`; break;
            case 'wait': out = until ? `wait until ${until}` : 'wait'; break;
            default: out = `${act} ${item || target || ''}`.trim(); break;
        }
        if (area && act !== 'speak' && act !== 'perform') out += ` (in ${area})`;
        else if (area) out += ` (${area})`;
        if (until && act !== 'wait') out += ` until ${until}`;
        return out.replace(/\s+/g, ' ').trim();
    }

    /**
     * Ground a list of typed steps. Returns the grounded (rendered) steps and
     * every rejection with its reason. Caller decides retry/drop policy -
     * plan-manager allows exactly one bounded re-composition.
     *
     * Each entry carries its `index` in the input array, so a caller can
     * rebuild the plan positionally (the repair contract is "keep the steps
     * that already grounded, replace only the rejected ones").
     */
    function ground(steps: any[], facts: ReturnType<typeof collectFacts>, areaName: string): {
        grounded: Array<{ step: any; text: string; index: number }>;
        rejections: Array<{ step: any; reason: string; index: number }>;
    } {
        const grounded: Array<{ step: any; text: string; index: number }> = [];
        const rejections: Array<{ step: any; reason: string; index: number }> = [];
        (steps || []).forEach((step, index) => {
            if (!step || typeof step !== 'object') return;
            const reason = groundStep(step, facts, areaName);
            if (reason) rejections.push({ step, reason, index });
            else grounded.push({ step, text: render(step), index });
        });
        return { grounded, rejections };
    }

    return { ACTS, collectFacts, groundStep, ground, render, matchFact };
})();

