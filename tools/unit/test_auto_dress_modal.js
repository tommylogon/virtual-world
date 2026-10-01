/**
 * tools/unit/test_auto_dress_modal.js
 *
 * The modal exists because the first auto-dress run silently dressed the
 * Eldenford Blacksmith as the *merchant* -- the node was carrying the wrong
 * personality, the model judged that text faithfully, and the report called it a
 * success. Its value is not the checkboxes; it is that a person sees the
 * context the model read before anything is worn.
 *
 * These cover the selection arithmetic and the slot grouping, which are the two
 * places a mistake would quietly equip the wrong thing.
 *
 * `description` is deliberately absent from the context: it is regenerated from
 * the equipped items, so showing it would be this feature reading its own output.
 */

const M = window.AutoDressModal;

const ITEMS = [
    { lib_id: 'coif_linen', name: 'coif_linen', tags: ['clothing'], slots: ['head'] },
    { lib_id: 'apron', name: 'apron', tags: ['clothing', 'meat'], slots: ['torso'] },
    { lib_id: 'belt_leather', name: 'belt_leather', tags: ['metal'], slots: ['waist'] },
    { lib_id: 'dark_cargo_pants', name: 'dark cargo pants', tags: ['legs'], slots: ['legs'] },
];

// ───────────────────────────── grouping by slot ──────────────────────────────

test('groups by the FIRST declared slot, which is what the engine equips into', () => {
    const groups = M.groupBySlot(ITEMS);
    const flat = groups.flatMap(g => g.items.map(i => i.lib_id));
    assertEq(flat.sort(), ['apron', 'belt_leather', 'coif_linen', 'dark_cargo_pants'],
        'every proposal is shown exactly once');
});

test('an item declaring several slots is filed under the first', () => {
    // `auto_dress` passes slot=cand["slots"][0] to equip_item, so the modal must
    // show the same one or the paperdoll disagrees with the real loadout.
    const groups = M.groupBySlot([{ lib_id: 'x', name: 'x', slots: ['hand_right', 'hands'] }]);
    assertEq(groups[0].slot, 'hand_right', 'matches the slot the engine will use');
});

test('groups come back in a stable, sensible body order', () => {
    const groups = M.groupBySlot(ITEMS);
    assertEq(groups.map(g => g.slot), ['head', 'torso', 'legs', 'waist'],
        'head first, then torso, legs, waist -- not the order the model listed them');
});

test('an unknown slot still renders rather than disappearing', () => {
    const groups = M.groupBySlot([{ lib_id: 'y', name: 'y', slots: ['tail'] }]);
    assertEq(groups.length, 1, 'an item with a slot we do not label must still be offered');
    assertEq(groups[0].label, 'tail', 'falls back to the raw slot name');
});

test('an item with no slots is offered rather than dropped', () => {
    const groups = M.groupBySlot([{ lib_id: 'z', name: 'z', slots: [] }]);
    assertEq(groups.length, 1, 'never silently lose a pick the model made');
});

test('grouping tolerates junk input', () => {
    assertEq(M.groupBySlot(null), [], 'null proposal groups to nothing');
    assertEq(M.groupBySlot([]), [], 'empty proposal groups to nothing');
});

// ──────────────────────────────── selection ──────────────────────────────────

test('everything starts selected', () => {
    assertEq(M.defaultSelection(ITEMS), ['coif_linen', 'apron', 'belt_leather', 'dark_cargo_pants'],
        'the model proposed it; opting out is the deliberate act');
});

test('unticking drops only that item', () => {
    assertEq(
        M.applyToggles(ITEMS, ['coif_linen']),
        ['apron', 'belt_leather', 'dark_cargo_pants'],
        'one absurd pick is dropped, not the whole outfit'
    );
});

test('unticking everything yields an empty list, not a fallback', () => {
    assertEq(
        M.applyToggles(ITEMS, ITEMS.map(i => i.lib_id)),
        [],
        'the user cleared it: that is an answer, and the caller must honour it'
    );
});

test('selection keeps the model order, not the untick order', () => {
    assertEq(
        M.applyToggles(ITEMS, ['dark_cargo_pants', 'belt_leather']),
        ['coif_linen', 'apron'],
        'order follows the proposal so the equipped stack is predictable'
    );
});

test('unticking an id that is not proposed is a no-op', () => {
    assertEq(
        M.applyToggles(ITEMS, ['guiding_cane']),
        ['coif_linen', 'apron', 'belt_leather', 'dark_cargo_pants'],
        'a stale checkbox cannot remove something the model never asked for'
    );
});

test('selection tolerates junk input', () => {
    assertEq(M.applyToggles(null, []), [], 'null proposal equips nothing');
    assertEq(M.applyToggles(ITEMS, null), M.defaultSelection(ITEMS), 'no rejections means all');
    assertEq(M.defaultSelection([{ lib_id: '' }, { name: 'no id' }]), [],
        'an entry with no lib_id cannot be equipped, so it is not offered');
});