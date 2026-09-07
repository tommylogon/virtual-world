/**
 * TriggerSuggestAI — shared AI trigger suggester for graph nodes.
 *
 * Uses the same shared AIGenerator as every other AI feature in the app
 * (scenario wizard, mock generation, item improve...). Given raw node fields
 * and a kind ('item' | 'way' | 'area'), asks the LLM for a full set of triggers
 * and returns them cleaned to the trigger-editor's schema shape.
 *
 * Usage:
 *   const triggers = await TriggerSuggestAI.suggest(fields, 'item');
 *   // → [{ trigger_type, target_name, target_state, conditions, effects,
 *   //      success_message, fail_message }, ...]  |  null (config/failure)
 */
window.TriggerSuggestAI = (() => {
    /**
     * Build the trigger-suggestion system prompt for a node kind.
     * @param {string} kind - 'item' | 'way' | 'area'
     * @returns {string}
     */
    function buildSystem(kind) {
        const kindLine = kind === 'way'
            ? `\nThis is a WAY — a door, passage or path between two areas. Suggest: on_examine (appearance), on_open / on_close (action flavor), on_enter (arrive/leave narration), on_use_on (unlock). Do NOT use adjust_vital or spawn_item on a way.`
            : kind === 'area'
            ? `\nThis is an AREA — a room or location. Suggest: on_enter (arrival flavor), on_examine (survey of the room), on_tick ambience gated by a random_chance condition so it does not repeat every tick, on_speech if it reacts to words. Do NOT use adjust_vital here unless the area directly heals/harms.`
            : '';
        return `You are a trigger author for a text adventure game. Given a game node, return a single valid JSON OBJECT (never a bare array — always wrap in {"triggers": [...]}). No markdown, no code fences.${kindLine}

THE ONLY top-level key is "triggers", holding the array of trigger objects the engine can run. EVERY trigger MUST have a non-empty "effects" array (1+ effects); a trigger with effects: [] fires and does NOTHING. Put ALL narrative text inside the effect's params.message OR adjust_vital's params.success_message. Leave the trigger's top-level "success_message"/"fail_message" as "" unless a specific example below says otherwise.

Trigger object shape:
{
  "trigger_type": "on_use",          // string — a single valid type
  "target_name": "",                 // string
  "target_state": "",                // string
  "conditions": [],                  // array — gate; empty array = always fire
  "effects": [ ... ],                // array — 1+ effects, run in order
  "success_message": "",             // string — leave "" unless a consume/empty case
  "fail_message": ""                 // string — e.g. "The bread is all gone."
}

============================================================
TRIGGER TYPES (fires on event; use ONE per trigger)
============================================================
Item interaction:
on_take      — player picks item up. Best for whispers / weight / cursed reaction.
on_drop      — player drops it.
on_examine   — player examines it. Ideal for save-gated or skill-gated reveals.
on_inspect   — upgraded examine (study closely).
on_use       — the generic action; NOTE: co-fires when eating/drinking.
on_use_on    — used ON a target (item/way/character). Unlock keys, use-on-door.
on_eat       — consume as food (already co-fires on_use — never pair with on_use).
on_drink     — consume as drink (already co-fires on_use — never pair with on_use).
on_read      — read a book/note — write the excerpt.
on_light     — a toggleable turns ON (companion to on_toggle_on; both fire together).
on_activate  — activate a mechanism/switch.
on_equip / on_unequip — equip/unequip (weapon threat, curses, worn effects).
on_throw     — throw it (breaks, propulsion).
on_break     — it breaks (shards, snapped).
on_depleted  — uses reach 0 (runs out / burns out; fires after system flips unlit).
on_toggle_on / on_toggle_off — a toggleable flips ON / OFF (REAL toggle triggers).
on_toggle_off — used to douse a light.
on_state_enter / on_state_exit — when the node's current_state changes (recursive).
on_enter     — player enters an AREA (arrival, traps, ambience). Also on ways.
on_open / on_close — a door/container opens/closes.
on_tick      — every engine tick (carried items fire it too).
on_delayed   — a schedule_trigger effect fires later on this node.
on_dawn/on_dusk/on_day/on_night/on_full_moon/on_blood_moon — clock/moon phases.
on_speech    — someone speaks near it (match with speech_matches condition).

DO NOT use on_light + on_toggle_on on the same item (they fire together; use one).

============================================================
CONDITIONS (gate the whole trigger; empty = always)
============================================================
{"type":"uses_above","value":0}           — item still has uses left (not empty)
{"type":"uses_reached","value":0}         — uses dropped to ≤ N
{"type":"has_item","item":"rusty_key","target":"player"}  — player carries it
{"type":"has_items","value":["a","b"]}    — player carries ALL listed
{"type":"is_equipped","item":"lantern"}   — currently equipped
{"type":"skill_check","skill":"Investigation","dc":14}    — gate an examine on a skill
{"type":"state_equals","target":"self","value":"lit"}     — a node's state
{"type":"random_chance","value":25}       — 25% chance (0–100)
{"type":"sound_heard","pattern":"glass"}  — a sound crossed the room
{"type":"speech_matches","phrase":"help","mode":"contains"}
{"type":"temperature_below","value":5}    /  {"type":"temperature_above","value":30}
{"type":"weather","value":"fog"}
{"type":"vital","stat":"HP","value":15}   — compare a vital
combine: {"operator":"and"|"or","conditions":[...]}

============================================================
EFFECTS (used inside each trigger's "effects" array)
============================================================
message        — print narration:        {"type":"message","params":{"message":"You wind the key. A sad, tinny lullaby creaks out."}}
adjust_vital   — change a vital:         {"type":"adjust_vital","params":{"stat":"Hunger","amount":-30,"target":"self"}}
heal           — restore HP/stat:        {"type":"heal","params":{"amount":15,"target":"self"}}
damage         — deal damage:            {"type":"damage","params":{"amount":10,"target":"self","save":{"stat":"DEX","dc":14,"on_success":"half"}}}
save           — hold roll + branch:     {"type":"save","params":{"stat":"CON","dc":13,"target":"self","on_success":[{"type":"message","params":{...}}],"on_fail":[{"type":"apply_condition","params":{"condition":"poisoned","duration":8,"target":"self"}}]}}
set_state      — set node state:         {"type":"set_state","params":{"node_id":"self","state":"open"}}
set_environment— override area env:      {"type":"set_environment","params":{"light":40,"smell":"woodsmoke"}}
unlock_way     — unlock a door:          {"type":"unlock_way","params":{"way_id":"way_attic_door"}}
spawn_item     — create a new item:      {"type":"spawn_item","params":{"item_id":"bread","into":"area"}}   — ONLY for things that produce items (vending machine, conjure). Gate it so it can't be farmed infinitely.
give_item      — put into a character:   {"type":"give_item","params":{"item_id":"note"}}
remove_item / consume_item / destroy_self
add_tag/remove_tag — change a node's tags
set_parameter / adjust_parameter
schedule_trigger — queue on_delayed:     {"type":"schedule_trigger","params":{"delay_ticks":5,"target":"self"}}
surface_memory / teleport / set_time / set_weather

Engine rules you MUST follow:
1) EVERY trigger needs >=1 effect in "effects". Put the message/prose in effects[].params.message (or adjust_vital.success_message). Do NOT stuff prose into the trigger's top-level success_message.
2) NEVER use BOTH "on_use" and "on_eat"/"on_drink" on one trigger ("on_eat"/"on_drink" co-fire "on_use" internally → double-applies). Use exactly ONE consume type.
3) Finite-uses (uses >= 1): add condition {"type":"uses_above","value":0} and a fail_message like "The <name> is empty." so the trigger never fires when depleted. The engine auto-decrements uses and removes the item at 0 — do NOT hand-add adjust_uses/destroy_item.
4) Heat sources: target_temperature & heating_rate are item PROPERTIES, NOT triggers. Do not generate set_environment/adjust_environment on heat sources.
5) Light sources: "toggleable" tag + on_toggle_on (or on_light) for lighting flavor only — the SYSTEM handles actual on/off state. on_light fires as companion when toggle_on happens. Do not set_state lit.

============================================================
CATEGORY INSTINCT (when tags/description tell you the kind)
============================================================
- Food → on_eat + adjust_vital Hunger −30. drink → on_drink + adjust_vital Thirst −30. energy → energy +30. medicine → heal/HP. alcohol → Sanity.
- Suspicious/poisoned/cursed: put a skill_check in the CONDITION; on success message reveals it, on fail a generic "looks safe enough." The consume effect then has a save (CON) that applies poison on fail.
- Book/note → on_read message (write the excerpt inline).
- Key/tool → on_use_on + unlock_way.
- Light source (non-toggleable): a single set_state lit + message is fine, or on_use.
- Haunted/cursed object: on_take message + schedule_trigger for suspense.
- Grounded in second-person: "You wind the key. A sad, tinny lullaby creaks out."

============================================================
WORKED EXAMPLES (match this style — vivid, concrete, second-person)
============================================================
A food item:
{"trigger_type":"on_eat","target_name":"","target_state":"","conditions":[{"type":"uses_above","value":0}],"effects":[{"type":"adjust_vital","params":{"stat":"Hunger","amount":-35,"target":"self","success_message":"You tear off a hunk of dark rye. Coarse and a little stale, but it fills the hollow in your stomach."}}],"success_message":"","fail_message":"The bread is all gone — just crumbs."}

A tainted drink (skill-gated examine + CON save that poisons on fail):
{"trigger_type":"on_examine","target_name":"","target_state":"","conditions":[{"type":"skill_check","skill":"Investigation","dc":14}],"effects":[{"type":"message","params":{"message":"It's poisoned. That should NOT go in anyone's mouth."}}],"success_message":"","fail_message":""}
{"trigger_type":"on_drink","target_name":"","target_state":"","conditions":[{"type":"uses_above","value":0}],"effects":[{"type":"adjust_vital","params":{"stat":"Thirst","amount":-20,"target":"self","success_message":"You take a sour sip."}},{"type":"save","params":{"stat":"CON","dc":13,"target":"self","on_success":[{"type":"message","params":{"message":"It's bitter and wrong, but you keep it down."}}],"on_fail":[{"type":"apply_condition","params":{"condition":"poisoned","duration":8,"target":"self","source_type":"item"}},{"type":"damage","params":{"amount":6,"target":"self"}},{"type":"message","params":{"message":"Your stomach lurches violently — the wine was poisoned."}}]}}],"success_message":"","fail_message":"The bottle is empty."}

A haunted object (take-whisper + scheduled dread):
{"trigger_type":"on_take","target_name":"","target_state":"","conditions":[],"effects":[{"type":"message","params":{"message":"The doll's head turns, just a fraction, to face you. Its painted eyes are wet."}},{"type":"schedule_trigger","params":{"delay_ticks":5,"target":"self"}}],"success_message":"","fail_message":""}

Return ONLY the JSON object {"triggers": [...]}.`;
    }

    /**
     * Build the trigger-suggestion user prompt for raw fields.
     * @param {object} fields - { name, description, tags, actions, uses, current_state, requires }
     * @param {string} kind   - 'item' | 'way' | 'area'
     * @param {string[]} plan - ordered trigger_type list to author (optional)
     * @returns {string}
     */
    function buildPrompt(fields, kind, plan) {
        const f = fields || {};
        const name = f.name || '';
        const description = f.description || '';
        const tags = (f.tags || []).join(', ');
        const actions = (f.actions || []).join(', ');
        const usesRaw = parseInt(f.uses ?? -1);
        const uses = Number.isNaN(usesRaw) || usesRaw === -1 ? 'infinite' : String(usesRaw);
        const extras = [];
        if (f.current_state) extras.push(`current_state: ${f.current_state}`);
        if (f.requires) extras.push(`requires: ${f.requires}`);
        let prompt = `Node kind: ${kind}\nName: ${name}\nDescription: ${description}\nTags: ${tags || '(none)'}\nActions: ${actions || '(none)'}\nUses: ${uses}`;
        if (extras.length) prompt += `\n${extras.join('\n')}`;
        if (plan && plan.length) {
            prompt += `\n\nREQUIRED: the "triggers" array must contain EXACTLY these trigger types, in this order, one trigger object per type, with none missing and no extras: ${plan.join(', ')}.`;
        } else {
            prompt += `\n\nGenerate a full set of useful triggers for this ${kind}.`;
        }
        return prompt;
    }

    /**
     * Ask the shared AIGenerator for suggested triggers.
     * @param {object} fields - { name, description, tags, actions, uses, ... }
     * @param {string} kind   - 'item' | 'way' | 'area'
     * @param {string[]} [plan] - ordered trigger types the model must produce
     * @returns {Promise<Array|null>} trigger array; null when config missing or
     *   the call failed; [] when the model returned nothing usable.
     */
    async function suggest(fields, kind, plan) {
        if (typeof AIGenerator === 'undefined' || !AIGenerator.isConfigured()) return null;
        const label = `✨ trigger-AI (${kind || 'item'})`;
        const result = await AIGenerator.generate(buildPrompt(fields, kind, plan), buildSystem(kind), { temperature: 0.7 });
        if (!result.success) {
            if (typeof toastError === 'function') toastError(result.error || 'AI trigger generation failed.');
            return null;
        }
        // Surface the raw LLM reply in the event stream exactly like every
        // other generator — a collapsed chip the user can expand.
        if (typeof events !== 'undefined' && events.logRawLLMResponse && result.raw) {
            events.logRawLLMResponse(label, result.raw);
        }
        const triggers = Array.isArray(result.data) ? result.data : (result.data && result.data.triggers);
        if (!Array.isArray(triggers)) {
            if (typeof events !== 'undefined' && events.log) {
                events.log(`${label} returned no trigger array — nothing usable.`, 'error-msg');
            }
            return [];
        }
        const cleaned = triggers
            .filter(t => t && t.trigger_type)
            .map(t => ({
                trigger_type: t.trigger_type,
                target_name: t.target_name || '',
                target_state: t.target_state || '',
                conditions: Array.isArray(t.conditions) ? t.conditions : [],
                effects: Array.isArray(t.effects) ? t.effects : [],
                success_message: t.success_message || '',
                fail_message: t.fail_message || '',
            }));
        // When a plan is required, key results to the plan: keep the AI's data
        // for types it produced, ignore extras (the caller backfills missing
        // plan types from the heuristic floor).
        if (plan && plan.length) {
            const byType = new Map(cleaned.map(t => [t.trigger_type, t]));
            cleaned.length = 0;
            cleaned.push(...plan
                .filter(type => byType.has(type))
                .map(type => byType.get(type)));
        }
        if (typeof events !== 'undefined' && events.log) {
            events.log(`${label} suggested ${cleaned.length} trigger${cleaned.length === 1 ? '' : 's'}: ${cleaned.map(t => t.trigger_type).join(', ') || '(none)'}`, 'system-msg');
        }
        return cleaned;
    }

    return { suggest, buildSystem, buildPrompt };
})();