/**
 * TriggerTypes — single source of truth for trigger editor dropdowns.
 * Used by item-library.js, inspector.js, and trigger-editor consumers.
 */
window.TriggerTypes = {
    TRIGGER_TYPES: [
        'on_take', 'on_drop', 'on_examine', 'on_inspect',
        'on_use', 'on_use_on', 'on_look', 'on_tick',
        'on_eat', 'on_drink', 'on_read', 'on_light',
        'on_activate', 'on_equip', 'on_unequip',
        'on_throw', 'on_break',
        'on_depleted', 'on_toggle_on', 'on_toggle_off',
        'on_open', 'on_close',
        'on_state_enter', 'on_state_exit',
        'on_auto_open', 'on_enter', 'on_speech',
        'on_fail_jump', 'on_fail_climb',
        'on_delayed'
    ],

    CONDITION_TYPES: [
        { value: '', label: '— Always fire —', group: 'general' },
        { value: 'area_temp', label: '🌡️ Area temp (comparator)', group: 'area' },
        { value: 'vital', label: '📊 Vital (comparator)', group: 'character' },
        { value: 'vital_above', label: '📊 Vital above', group: 'character' },
        { value: 'vital_below', label: '📊 Vital below', group: 'character' },
        { value: 'is_equipped', label: '🎽 Is equipped', group: 'item' },
        { value: 'uses_reached', label: '🔢 Uses reaches N', group: 'item' },
        { value: 'uses_above', label: '🔢 Uses above N', group: 'item' },
        { value: 'has_item', label: '🎒 Has item in inventory', group: 'item' },
        { value: 'has_items', label: '🎒 Has all items', group: 'item' },
        { value: 'has_trait', label: '⭐ Has trait', group: 'character' },
        { value: 'has_tag', label: '🏷️ Has tag', group: 'tag' },
        { value: 'state_equals', label: '🔧 Node state equals', group: 'general' },
        { value: 'random_chance', label: '🎲 Random chance (%)', group: 'general' },
        { value: 'skill_check', label: '🎯 Skill check', group: 'character' },
        { value: 'save_throw', label: '🛡️ Save throw', group: 'character' },
        { value: 'time_of_day', label: '🕐 Time of day', group: 'general' },
        { value: 'weather', label: '🌧️ Weather', group: 'area' },
        { value: 'speech_matches', label: '💬 Speech matches phrase', group: 'general' }
    ],

    EFFECT_TYPES: [
        { value: 'message', label: '💬 Show Message', group: 'general' },
        { value: 'destroy_self', label: '💥 Destroy Self', group: 'general' },
        { value: 'damage', label: '💔 Deal Damage', group: 'character' },
        { value: 'save', label: '🎲 Save Gate (fear/hazard)', group: 'general' },
        { value: 'heal', label: '❤️ Heal', group: 'character' },
        { value: 'spawn_item', label: '📦 Spawn Item(s)', group: 'item' },
        { value: 'spawn_character', label: '🧑 Spawn Character', group: 'character' },
        { value: 'give_item', label: '🎁 Give Item to Character', group: 'general' },
        { value: 'remove_item', label: '🗑️ Remove Item', group: 'item' },
        { value: 'consume_item', label: '🍽️ Consume Item (from inventory)', group: 'item' },
        { value: 'set_state', label: '🔧 Set State', group: 'general' },
        { value: 'set_hidden', label: '👻 Set Hidden/Visible', group: 'general' },
        { value: 'adjust_uses', label: '🔢 Adjust Uses', group: 'item' },
        { value: 'end_scenario', label: '🏁 End Scenario', group: 'general' },
        { value: 'restart_scenario', label: '🔄 Restart Scenario', group: 'general' },
        { value: 'set_environment', label: '🌡️ Set Area Environment', group: 'area' },
        { value: 'teleport', label: '🌀 Teleport', group: 'general' },
        { value: 'rename', label: '✏️ Rename Item', group: 'general' },
        { value: 'unlock_way', label: '🔓 Unlock Way', group: 'way' },
        { value: 'set_description', label: '📝 Set Description', group: 'item' },
        { value: 'append_description', label: '📝 Append to Description', group: 'item' },
        { value: 'adjust_vital', label: '📊 Adjust Vital', group: 'character' },
        { value: 'adjust_environment', label: '🌡️ Adjust Environment (+/-)', group: 'area' },
        { value: 'add_tag', label: '🏷️ Add Tag', group: 'general' },
        { value: 'remove_tag', label: '🏷️ Remove Tag', group: 'general' },
        { value: 'apply_trait', label: '⭐ Apply Trait', group: 'character' },
        { value: 'remove_trait', label: '⭐ Remove Trait', group: 'character' },
        { value: 'apply_condition', label: '🩸 Apply Condition (poisoned, blind...)', group: 'character' },
        { value: 'remove_condition', label: '🩹 Remove Condition', group: 'character' },
        { value: 'set_parameter', label: '🔑 Set Parameter', group: 'general' },
        { value: 'adjust_parameter', label: '🔢 Adjust Parameter', group: 'general' },
        { value: 'surface_memory', label: '🧠 Surface Memory (by tag/keyword)', group: 'character' },
        { value: 'suppress_memory', label: '🚫 Suppress Memory (block recall)', group: 'character' },
        { value: 'unblock_memory', label: '🔓 Unblock Memory', group: 'character' },
        { value: 'schedule_trigger', label: '⏳ Schedule Trigger (N ticks later)', group: 'general' }
    ]
};
