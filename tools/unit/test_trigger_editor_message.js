/**
 * test_trigger_editor_message.js - bug-563.
 *
 * A trigger editor form exposes exactly one narration field for a message
 * effect (params.message). Trigger-level Success Message is removed so it
 * no longer duplicates or conflicts with params.message. Fail Message is
 * shown only when conditions exist or when an effect reads fail_message.
 * Saving writes params.message and does not write success_message.
 */

test('TriggerEditor._collectData writes params.message and does not write success_message', () => {
    const origGetElementById = document.getElementById;
    const origQuerySelectorAll = document.querySelectorAll;

    const dummyTypeEl = {
        value: 'on_use',
        selectedOptions: [{ value: 'on_use' }]
    };
    const dummyFailMsgEl = {
        value: 'fail text'
    };

    const dummyEffectRow = {
        querySelector(selector) {
            if (selector === '.eff-type') return { value: 'message' };
            if (selector === '.eff-msg-text') return { value: 'hello world from effect' };
            return null;
        }
    };

    document.getElementById = (id) => {
        if (id === 'te-trigger-type') return dummyTypeEl;
        if (id === 'te-fail-msg') return dummyFailMsgEl;
        if (id === 'te-trigger-name') return { value: 'test trigger' };
        return null;
    };

    document.querySelectorAll = (selector) => {
        if (selector === '#te-effects-container .eff-row') {
            return [dummyEffectRow];
        }
        return [];
    };

    try {
        const collected = TriggerEditor._collectData();
        assertEq(collected.effects.length, 1, 'one effect collected');
        assertEq(collected.effects[0].type, 'message', 'type is message');
        assertEq(collected.effects[0].params.message, 'hello world from effect', 'params.message populated');
        assertEq(collected.effects[0].params.success_message, undefined, 'no params.success_message written');
        assertEq(collected.success_message, undefined, 'no trigger-level success_message written');
        assertEq(collected.fail_message, 'fail text', 'fail message collected');
    } finally {
        document.getElementById = origGetElementById;
        document.querySelectorAll = origQuerySelectorAll;
    }
});

test('TriggerEditor fail message visibility triggers for fail_message reading effect types', () => {
    const origGetElementById = document.getElementById;
    const origQuerySelectorAll = document.querySelectorAll;

    const dummyFailGroup = {
        style: { display: 'none' }
    };
    const dummyCondContainer = {
        querySelector() { return null; } // no conditions
    };

    const makeRowWithEff = (effType) => ({
        querySelector(sel) {
            if (sel === '.eff-type') return { value: effType };
            return null;
        }
    });

    let currentRows = [];

    document.getElementById = (id) => {
        if (id === 'te-fail-msg-group') return dummyFailGroup;
        if (id === 'te-conditions-container') return dummyCondContainer;
        return null;
    };

    document.querySelectorAll = (sel) => {
        if (sel === '#te-effects-container .eff-row') return currentRows;
        return [];
    };

    try {
        // Plain message effect: no fail message shown
        currentRows = [makeRowWithEff('message')];
        TriggerEditor._updateFailGroupVisibility();
        assertEq(dummyFailGroup.style.display, 'none', 'plain message has no fail message');

        // Scry effect: handler reads fail_message, so fail group is shown
        currentRows = [makeRowWithEff('scry')];
        TriggerEditor._updateFailGroupVisibility();
        assertEq(dummyFailGroup.style.display, 'block', 'scry effect shows fail message');

        // Spawn item effect: handler reads fail_message
        currentRows = [makeRowWithEff('spawn_item')];
        TriggerEditor._updateFailGroupVisibility();
        assertEq(dummyFailGroup.style.display, 'block', 'spawn_item effect shows fail message');

        // Damage effect: no fail_message handler
        currentRows = [makeRowWithEff('damage')];
        TriggerEditor._updateFailGroupVisibility();
        assertEq(dummyFailGroup.style.display, 'none', 'damage effect has no fail message');
    } finally {
        document.getElementById = origGetElementById;
        document.querySelectorAll = origQuerySelectorAll;
    }
});
