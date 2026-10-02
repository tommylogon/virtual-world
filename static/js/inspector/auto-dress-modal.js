"use strict";
/**
 * AutoDressModal — confirm an outfit before it is equipped.
 *
 * Auto-dress (task-660) asks the character's LLM to pick clothing from the item
 * library and then equips whatever comes back. That was silent, and silence is
 * what hid the first real failure: the Eldenford Blacksmith node was carrying
 * **the merchant's** personality, so the model dressed a smith like a trader
 * and the report called it a success. Nothing in the flow said so.
 *
 * This modal puts the two things a person needs to see on screen together:
 *
 *   1. **The context the model was given** — name, personality, base_description.
 *      If that text belongs to somebody else, it is now obvious before anything
 *      is worn rather than three layers downstream.
 *   2. **What it proposed**, as per-slot checkboxes, so one absurd pick is
 *      unticked rather than accepted wholesale or thrown away entirely.
 *
 * `description` is deliberately NOT shown as an input. It is regenerated from
 * the equipped items on every wear/remove (`engine/equipment.py::_update_
 * equipment_description`, plus the frontend call in `static/js/api.js:652`), so
 * it is this feature's own output. Showing it would be circular.
 *
 * Pure UI: no engine calls, and the selection arithmetic is separated out
 * (`defaultSelection`, `applyToggles`) so it can be unit-tested without a DOM.
 *
 * @module inspector/auto-dress-modal — review an auto-dress proposal before equipping
 * @contributes AutoDressModal: show the context the model used and let the user accept or drop individual items
 * @powers reviewing what a character wears before it is equipped
 * @relates called by InspectorAgentView._autoDress; equips via POST /api/auto_dress
 * @docs docs/virtualWorld/Items & Inventory/Equipment & Paperdoll.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const AutoDressModal = (() => {
    const SLOT_ORDER = [
        'head', 'neck', 'torso', 'hands', 'hand_left', 'hand_right',
        'legs', 'feet', 'waist', 'accessory', 'back', 'arms',
    ];
    /** Slot labels for display. Unknown slots fall through to the raw name. */
    const SLOT_LABELS = {
        head: 'Head', neck: 'Neck', torso: 'Torso', hands: 'Hands',
        hand_left: 'Left hand', hand_right: 'Right hand', legs: 'Legs',
        feet: 'Feet', waist: 'Waist', accessory: 'Accessory', back: 'Back',
        arms: 'Arms',
    };
    /**
     * Group proposed items under the slot they will actually land in.
     *
     * Uses the item's FIRST declared slot, because that is what
     * `auto_dress` passes to `equip_item` (`engine/dressing.py`). Showing the
     * model a different slot than the engine uses is how a paperdoll and the
     * real loadout end up disagreeing.
     *
     * @param {Array} items - Validated candidate objects from the model
     * @returns {Array<{slot: string, label: string, items: Array}>} Ordered groups
     */
    function groupBySlot(items) {
        const bySlot = new Map();
        for (const item of Array.isArray(items) ? items : []) {
            const slots = Array.isArray(item?.slots) ? item.slots : [];
            const slot = slots[0] || 'accessory';
            if (!bySlot.has(slot))
                bySlot.set(slot, []);
            bySlot.get(slot).push(item);
        }
        const rank = (slot) => {
            const i = SLOT_ORDER.indexOf(slot);
            return i === -1 ? SLOT_ORDER.length : i;
        };
        return [...bySlot.entries()]
            .sort((a, b) => rank(a[0]) - rank(b[0]))
            .map(([slot, groupItems]) => ({
            slot,
            label: SLOT_LABELS[slot] || slot,
            items: groupItems,
        }));
    }
    /** Which items start checked: all of them. An empty proposal is not valid. */
    function defaultSelection(items) {
        return (Array.isArray(items) ? items : []).map((i) => i?.lib_id).filter(Boolean);
    }
    /**
     * Apply the set of ids the user unticked.
     *
     * @param {Array} items - The proposal
     * @param {Array} rejected - Ids to drop
     * @returns {Array} Ids to equip, in proposal order
     */
    function applyToggles(items, rejected) {
        const drop = new Set(Array.isArray(rejected) ? rejected : []);
        return defaultSelection(items).filter((id) => !drop.has(id));
    }
    function esc(text) {
        return String(text ?? '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
    function contextBlock(context) {
        if (!context)
            return '';
        const parts = [];
        if (context.personality) {
            parts.push(`<div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">`
                + `<b>Personality the model read</b></div>`
                + `<div style="font-size:11px;line-height:1.45;white-space:pre-wrap;`
                + `background:var(--bg-inset);border:1px solid var(--border);border-radius:4px;`
                + `padding:6px 8px;margin-bottom:8px;max-height:180px;overflow:auto;">`
                + `${esc(context.personality)}</div>`);
        }
        if (context.description) {
            parts.push(`<div style="font-size:10px;color:var(--text-muted);margin-bottom:2px;">`
                + `<b>Base description</b></div>`
                + `<div style="font-size:11px;line-height:1.45;`
                + `background:var(--bg-inset);border:1px solid var(--border);border-radius:4px;`
                + `padding:6px 8px;">${esc(context.description)}</div>`);
        }
        return parts.join('');
    }
    function wornBlock(worn) {
        const slots = Object.entries(worn || {}).filter(([, v]) => Array.isArray(v) && v.length);
        if (!slots.length)
            return '';
        const rows = slots
            .map(([slot, list]) => `<span style="opacity:0.8">${esc(SLOT_LABELS[slot] || slot)}: `
            + `${esc(list.join(', '))}</span>`)
            .join(' &nbsp;·&nbsp; ');
        return `<div style="font-size:10px;color:var(--text-muted);margin:10px 0 4px;">`
            + `<b>Already worn</b> (auto-dress never replaces these)</div>`
            + `<div style="font-size:10px;line-height:1.6;">${rows}</div>`;
    }
    function itemRow(item) {
        const tags = Array.isArray(item?.tags) ? item.tags.filter(Boolean) : [];
        const tagText = tags.length
            ? `<span style="opacity:0.55;font-size:9px;">${esc(tags.join(', '))}</span>`
            : '';
        return `<label style="display:flex;gap:6px;align-items:flex-start;padding:3px 0;cursor:pointer;">`
            + `<input type="checkbox" class="ad-item" data-lib="${esc(item.lib_id)}" checked `
            + `style="margin-top:2px;">`
            + `<span style="flex:1;">`
            + `<span style="font-size:11px;">${esc(item.name || item.lib_id)}</span>`
            + (tagText ? `<br>${tagText}` : '')
            + `</span></label>`;
    }
    /**
     * Show the proposal. Resolves to the ids to equip, or null if cancelled.
     *
     * @param {object} opts
     * @param {string} opts.character
     * @param {{personality?: string, description?: string}} [opts.context]
     * @param {Array} opts.items - Validated picks from the model
     * @param {Object} [opts.worn] - Currently equipped {slot: [names]}
     * @param {string} [opts.note] - e.g. the fallback reason
     * @returns {Promise<Array<string>|null>}
     */
    function show(opts = {}) {
        const { character, items = [], context = null, worn = null, note = '' } = opts;
        return new Promise((resolve) => {
            const groups = groupBySlot(items);
            const body = groups.length
                ? groups.map(g => `<div style="margin-bottom:8px;">`
                    + `<div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;`
                    + `letter-spacing:0.04em;">${esc(g.label)}</div>`
                    + g.items.map(itemRow).join('')
                    + `</div>`).join('')
                : `<div style="font-size:11px;opacity:0.7;">The model proposed nothing wearable.</div>`;
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);'
                + 'display:flex;align-items:center;justify-content:center;z-index:10000;';
            overlay.innerHTML = `<div style="background:var(--bg-panel,#1a1a1a);`
                + `border:1px solid var(--border);border-radius:6px;padding:14px 16px;`
                + `max-width:520px;width:92%;max-height:86vh;overflow:auto;box-shadow:0 8px 32px rgba(0,0,0,0.5);">`
                + `<div style="font-weight:600;font-size:13px;margin-bottom:8px;">`
                + `Auto-dress ${esc(character || '')}</div>`
                + (note ? `<div style="font-size:10px;color:var(--orange,#e8890c);margin-bottom:8px;">`
                    + `${esc(note)}</div>` : '')
                + contextBlock(context)
                + `<div style="font-size:10px;color:var(--text-muted);margin:10px 0 4px;">`
                + `<b>Proposed</b> — untick anything they would not wear</div>`
                + body
                + wornBlock(worn)
                + `<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">`
                + `<button class="btn btn-sm" id="ad-cancel">Cancel</button>`
                + `<button class="btn btn-sm" id="ad-apply">Equip selected</button>`
                + `</div></div>`;
            const close = (value) => {
                overlay.remove();
                document.removeEventListener('keydown', onKey);
                resolve(value);
            };
            const onKey = (ev) => { if (ev.key === 'Escape')
                close(null); };
            overlay.addEventListener('click', (ev) => {
                if (ev.target === overlay)
                    close(null);
            });
            overlay.querySelector('#ad-cancel').addEventListener('click', () => close(null));
            overlay.querySelector('#ad-apply').addEventListener('click', () => {
                const rejected = [...overlay.querySelectorAll('.ad-item')]
                    .filter((cb) => !cb.checked)
                    .map((cb) => cb.dataset.lib || '');
                close(applyToggles(items, rejected));
            });
            document.addEventListener('keydown', onKey);
            document.body.appendChild(overlay);
            overlay.querySelector('#ad-apply').focus();
        });
    }
    return { show, groupBySlot, defaultSelection, applyToggles };
})();
window.AutoDressModal = AutoDressModal;
