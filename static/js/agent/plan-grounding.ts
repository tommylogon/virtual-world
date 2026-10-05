/**
 * plan-grounding.js — Grounding validator for LLM plan steps (task-700)
 *
 * The plan phase used to emit freeform prose steps, and prose references
 * scenery: Vekka planned "eat hanging meat" against room description text and
 * burned a turn on "You don't have 'hanging meat'". This module is the fix's
 * fact side: plan steps arrive TYPED (act/item/target), and every referenced
 * entity is checked against the facts the plan prompt was built from —
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
 * @module agent/plan-grounding — typed plan-step grounding validator
 * @contributes PlanGrounding.collectFacts() + .ground() + .groundStep() + .render()
 * @powers NPC behaviour — plans composed from verifiable facts instead of prose
 * @relates consumed by agent/plan-manager (task-700); the plan executor
 *       (task-702) will consume the same typed steps; rejects what bug-185's
 *       step tracker used to forgive
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */

(window as unknown as { PlanGrounding: unknown }).PlanGrounding = (() => {
    'use strict';

    /**
     * The plan-step verbs the contract allows — the engine's own verb list
     * (task-491's single source of truth), because a plan that cannot say
     * "escape" is useless to a character who is being held. The grounding
     * rules per act follow in groundStep().
     */
    const ACTS = new Set([
        // movement & approach
        'go', 'dash', 'approach', 'crawl', 'climb', 'jump', 'fumble',
        // world interaction
        'take', 'drop', 'use', 'use_on', 'examine', 'search', 'look',
        'listen', 'read', 'open', 'close', 'put', 'craft', 'make',
        'combine', 'split', 'wear', 'remove', 'stow',
        // people
        'give', 'steal', 'grab', 'lead', 'attack', 'escape', 'struggle',
        // sustained / state
        'speak', 'perform', 'wait', 'stand', 'rest', 'relieve',
    ]);

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
        const ws = (window as unknown as {
            worldState?: {
                getItemsInArea?(name: string): Array<{ name?: string }>;
                getInventory?(name: string): string[];
            };
        }).worldState;
        const areaItems = (areaName && ws?.getItemsInArea?.(areaName) || [])
            .map((n: { name?: string }) => String(n.name || ''))
            .filter(Boolean);
        const carried = (ws?.getInventory?.(charName) || (player?.inventory || []))
            .map(String).filter(Boolean);
        const people = ((state?.players_in_area || []) as Array<{ name?: string }>)
            .map((p: { name?: string }) => String(p.name || ''))
            .filter((n: string) => n && n !== charName);
        const area = (areaName && state?.areas?.[areaName]) || {};
        const exitSource = area.exits_authoring || area.exits || {};
        const exits = Object.keys(exitSource || {})
            .map(String)
            .filter(Boolean);
        for (const e of Object.values(exitSource || {}) as Array<{ direction?: string }>) {
            if (e?.direction && !exits.includes(e.direction)) exits.push(e.direction);
        }
        const knownAreas = ((player?.known || []) as unknown[]).map(String)
            .filter(Boolean);
        if (areaName && !knownAreas.includes(areaName)) knownAreas.unshift(areaName);
        return { areaItems, carried, people, exits, knownAreas };
    }

    /**
     * Validate ONE typed step against the facts. Returns null when the step
     * grounds, else the human-readable rejection reason (with the fact list
     * so the LLM can re-compose from what exists).
     */
    function groundStep(step: any, facts: ReturnType<typeof collectFacts>, areaName: string): string | null {
        const act = String(step?.act || '').toLowerCase().trim();
        if (!ACTS.has(act)) {
            return `unknown act "${act || '(empty)'}" - use one of: ${[...ACTS].join(', ')}`;
        }
        const item = step?.item ?? step?.target ?? '';
        const target = step?.target ?? '';
        const everything = [...facts.areaItems, ...facts.carried, ...facts.people];

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
                if (!matchFact(item, [...facts.carried, ...facts.areaItems])) {
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
                if (!matchFact(item, [...facts.areaItems, ...facts.carried])) {
                    return `no interactable "${item}" here to take - interactables: ${facts.areaItems.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
                }
                return null;
            }
            case 'use':
            case 'craft':
            case 'make': {
                if (!String(item).trim()) return `${act} needs an item`;
                if (!matchFact(item, [...facts.carried, ...facts.areaItems])) {
                    return `no interactable "${item}" to ${act} - carrying: ${facts.carried.join(', ') || '(nothing)'}; interactables here: ${facts.areaItems.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
                }
                return null;
            }
            case 'use_on':
            case 'put': {
                if (!String(item).trim() || !String(target).trim()) {
                    return `${act} needs both item and target`;
                }
                if (!matchFact(item, [...facts.carried, ...facts.areaItems])) {
                    return `no interactable "${item}" to ${act}`;
                }
                if (!matchFact(target, [...everything, areaName])) {
                    return `no interactable "${target}" here to ${act} on - interactables: ${everything.join(', ') || '(none)'}`;
                }
                return null;
            }
            case 'examine':
            case 'open':
            case 'close':
            case 'attack':
            case 'grab':
            case 'read':
            case 'search': {
                if (!String(item).trim() && !String(target).trim()) {
                    return `${act} needs an item or target`;
                }
                const ref = item || target;
                if (!matchFact(ref, [...everything, areaName])) {
                    return `no interactable "${ref}" here - interactables: ${everything.join(', ') || '(none)'}. Room-description scenery is NOT interactable`;
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
     */
    function ground(steps: any[], facts: ReturnType<typeof collectFacts>, areaName: string): {
        grounded: Array<{ step: any; text: string }>;
        rejections: Array<{ step: any; reason: string }>;
    } {
        const grounded: Array<{ step: any; text: string }> = [];
        const rejections: Array<{ step: any; reason: string }> = [];
        for (const step of steps || []) {
            if (!step || typeof step !== 'object') continue;
            const reason = groundStep(step, facts, areaName);
            if (reason) rejections.push({ step, reason });
            else grounded.push({ step, text: render(step) });
        }
        return { grounded, rejections };
    }

    return { ACTS, collectFacts, groundStep, ground, render, matchFact };
})();

