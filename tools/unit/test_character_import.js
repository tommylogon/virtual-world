/**
 * Unit tests for character-import (task-843): deterministic pre-parse,
 * prompt contract, and answer extraction. The LLM itself is never called
 * here — conversion quality is reviewed in the Persona tab, not in tests.
 */
'use strict';

const CARD = JSON.stringify({
    data: {
        name: 'Kiala',
        description: 'A young goblin squire. Green eyes, cropped black hair.',
        personality: 'Eager, clumsy, brave to a fault.',
        mes_example: ['Hold my spear!', 'I can do it, watch!'],
        scenario: 'Serves as squire in the goblin camp.',
        tags: ['goblin', 'squire'],
        character_book: { entries: [{ keys: ['camp'], content: 'The camp sits by the river.' }] },
    },
});

test('a SillyTavern card splits certain facts from model food', () => {
    const parsed = CharacterImport.parseInputFile(CARD, 'main_kiala.json');
    assertEq(parsed.kind, 'card', 'card kind');
    assertEq(parsed.deterministic.name, 'Kiala', 'name is certain');
    assertTrue(parsed.deterministic.tagCandidates.includes('goblin'), 'tags kept');
    assertEq(parsed.deterministic.dialogueCandidates.length, 2, 'dialogue lines kept');
    assertEq(parsed.deterministic.lorebook.length, 1, 'lorebook split out');
    assertTrue(parsed.warnings.some((w) => w.includes('memories')), 'lorebook warning names memories');
    assertTrue(parsed.sourceText.includes('Eager, clumsy'), 'personality reaches the model');
    assertFalse(parsed.sourceText.includes('camp sits by the river'), 'lorebook body stays out of the sheet prompt');
});

test('markdown and txt read as prose', () => {
    for (const name of ['backstory.md', 'notes.txt']) {
        const parsed = CharacterImport.parseInputFile('A scarred old smith.', name);
        assertEq(parsed.kind, 'prose', name + ' is prose');
        assertEq(parsed.sourceText, 'A scarred old smith.', 'prose passes through');
    }
});

test('garbage is rejected, not guessed at', () => {
    let threw = false;
    try { CharacterImport.parseInputFile('{nope', 'card.json'); } catch { threw = true; }
    assertTrue(threw, 'bad JSON throws');
    threw = false;
    try { CharacterImport.parseInputFile('data', 'card.png'); } catch { threw = true; }
    assertTrue(threw, 'images rejected');
    threw = false;
    try { CharacterImport.parseInputFile('   ', 'empty.md'); } catch { threw = true; }
    assertTrue(threw, 'empty prose rejected');
});

test('a JSON file with no card fields reads as prose', () => {
    const parsed = CharacterImport.parseInputFile('{"a": 1}', 'weird.json');
    assertEq(parsed.kind, 'prose', 'falls back to prose');
    assertTrue(parsed.warnings.length > 0, 'fallback is announced');
});

test('the prompt carries the schema as the contract, with maximal fill', () => {
    const schema = { type: 'object', properties: { identity: {} } };
    const messages = CharacterImport.buildConvertPrompt('someone', schema);
    assertEq(messages.length, 2, 'system + user');
    assertEq(messages[0].role, 'system', 'system first');
    assertTrue(messages[0].content.includes('ONLY that JSON object'), 'output rule present');
    assertTrue(messages[0].content.includes('INVENT a value'), 'maximal-fill rule present');
    assertTrue(messages[0].content.includes('"inferred"'), 'provenance key demanded');
    assertTrue(messages[1].content.includes('"identity"'), 'schema inlined');
    assertTrue(messages[1].content.includes('someone'), 'material inlined');
});

test('the answer splits into record and provenance', () => {
    const wrapped = CharacterImport.splitConvertAnswer({
        record: { identity: { age: 12 } },
        inferred: ['identity.age', ' appearance.hair.color ', ''],
    });
    assertEq(wrapped.record.identity.age, 12, 'record unwrapped');
    assertFalse('record' in wrapped.record, 'the wrapper key does not leak into the record');
    assertEq(wrapped.inferred.length, 2, 'blank provenance entries dropped');
    // A bare record (a model ignoring the wrapper) still imports, no provenance.
    const bare = CharacterImport.splitConvertAnswer({ identity: { age: 3 } });
    assertEq(bare.record.identity.age, 3, 'bare record tolerated');
    assertEq(bare.inferred.length, 0, 'no provenance rather than a failure');
});

test('answer extraction tolerates fences, never fragments', () => {
    const obj = CharacterImport.extractJsonBlock('```json\n{"a": 1}\n```');
    assertEq(obj.a, 1, 'fenced object parses');
    const bare = CharacterImport.extractJsonBlock('prefix {"b": 2} suffix');
    assertEq(bare.b, 2, 'wrapped object parses');
    let threw = false;
    try { CharacterImport.extractJsonBlock('no braces here'); } catch { threw = true; }
    assertTrue(threw, 'prose-only answer fails with a reason');
    threw = false;
    try { CharacterImport.extractJsonBlock('{"a": }'); } catch { threw = true; }
    assertTrue(threw, 'broken JSON fails with a reason');
});
