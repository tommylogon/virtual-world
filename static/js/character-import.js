"use strict";
// Character file import — deterministic pre-parse + LLM convert (task-843).
//
// Any character data in, one ViWo Persona sheet out. The deterministic
// layer pulls what is certain without a model (names, tag candidates,
// dialogue lines, lorebook split); the LLM fills only the 828 schema,
// and `PUT /record` validates its answer (fail closed, field named).
// Pure core: no DOM, no network — the caller (Mind Persona tab) owns
// files, the model call, and the save. Unit-tested in
// `tools/unit/test_character_import.js`.
//
// NOTE: the @module contract block lives directly below, ahead of the
// first real statement — tsc drops comments attached to erased
// `interface` declarations, so interfaces sit at the bottom of this
// file (types resolve regardless of order).
/**
 * @module character-import — card/prose → Persona-sheet pre-parse + prompt
 * @contributes parseInputFile, buildConvertPrompt, extractJsonBlock
 * @powers inspector/mind-view Persona tab import button
 * @docs docs/virtualWorld/Characters/Persona.md
 */
function _lines(text) {
    const parts = Array.isArray(text) ? text : [text];
    const out = [];
    for (const part of parts) {
        for (const s of String(part ?? '').split(/\r?\n/)) {
            const line = s.trim();
            if (line)
                out.push(line);
        }
    }
    return out;
}
/**
 * Split a card file into certain facts and model food.
 *
 * `.json` in SillyTavern/Chub shape (`{data: {name, description,
 * personality, mes_example, scenario, tags, character_book, ...}}` or the
 * same keys top-level) is a card; `.md` / `.txt` is prose. Anything else
 * (images, binary) is rejected, not guessed at.
 */
function parseInputFile(text, fileName) {
    const lower = String(fileName || '').toLowerCase();
    const warnings = [];
    if (lower.endsWith('.json')) {
        let raw;
        try {
            raw = JSON.parse(String(text ?? ''));
        }
        catch {
            throw new Error(`not JSON: ${fileName} does not parse; send .md/.txt prose instead`);
        }
        return _parseCard(raw, fileName, warnings);
    }
    if (lower.endsWith('.md') || lower.endsWith('.txt') || lower === '') {
        const source = String(text ?? '').trim();
        if (!source)
            throw new Error(`${fileName || 'file'} is empty`);
        return {
            kind: 'prose', fileName, sourceText: source,
            deterministic: { tagCandidates: [], dialogueCandidates: [], lorebook: [] },
            warnings,
        };
    }
    throw new Error(`cannot import ${fileName}: send .json (card) or .md/.txt (prose)`);
}
function _parseCard(raw, fileName, warnings) {
    const root = (raw && typeof raw === 'object' ? raw : {});
    const data = (root.data && typeof root.data === 'object'
        ? root.data : root);
    if (typeof data.name !== 'string' || !data.name.trim()) {
        // A JSON file without a card shape is prose that happens to parse:
        // treat the whole text as source rather than failing the author.
        const source = String(JSON.stringify(raw)).slice(0, 20000);
        warnings.push('no card fields found; reading as free prose');
        return {
            kind: 'prose', fileName, sourceText: source,
            deterministic: { tagCandidates: [], dialogueCandidates: [], lorebook: [] },
            warnings,
        };
    }
    const det = { tagCandidates: [], dialogueCandidates: [], lorebook: [] };
    const parts = [];
    const push = (label, value) => {
        const text = String(value ?? '').trim();
        if (text)
            parts.push(`[${label}]\n${text}`);
    };
    push('name', data.name);
    push('description', data.description);
    push('personality', data.personality);
    push('scenario', data.scenario);
    push('system prompt', data.system_prompt);
    const tags = Array.isArray(data.tags)
        ? data.tags.map((t) => String(t).trim()).filter((t) => t) : [];
    det.tagCandidates = tags.slice(0, 24);
    const dialogues = _lines(data.mes_example).slice(0, 12);
    det.dialogueCandidates = dialogues;
    if (dialogues.length)
        parts.push(`[example dialogue]\n${dialogues.join('\n')}`);
    const book = data.character_book?.entries;
    if (Array.isArray(book)) {
        for (const entry of book.slice(0, 60)) {
            const e = (entry && typeof entry === 'object' ? entry : {});
            const content = String((e.content ?? e.text ?? '')).trim();
            if (!content)
                continue;
            const keys = Array.isArray(e.keys) ? e.keys.map((k) => String(k)) : [];
            det.lorebook.push({ name: keys.join('/') || 'lore', text: content.slice(0, 2000) });
        }
        // Lorebook entries are knowledge, not sheet fields: they ride
        // memories, so the sheet prompt names them but never inlines them.
        warnings.push(`${det.lorebook.length} lorebook entries set aside for memories, not the sheet`);
    }
    return {
        kind: 'card', fileName,
        sourceText: parts.join('\n\n').slice(0, 24000),
        deterministic: { ...det, name: String(data.name).trim() },
        warnings,
    };
}
/**
 * Build the conversion chat: the 828 schema IS the contract (the same
 * object `PUT /record` validates against, so the prompt and the gate
 * cannot disagree). Unknown → empty, never invented; ids are slugs.
 */
function buildConvertPrompt(sourceText, schema) {
    return [
        {
            role: 'system',
            content: [
                'Convert the character material below into ONE JSON object matching the schema.',
                'Rules, no exceptions:',
                '- output ONLY the JSON object, no prose around it;',
                '- fill only what the material states; leave everything else out (absent, not null);',
                '- id-list fields (likes, fears, kinks, interests, ...) hold slugs: lowercase, digits, _ or -;',
                '- prose-list fields (traits, quirks, ...) hold free text;',
                '- never invent names, ids, memories, or backstory;',
                '- biography/secrets stay brief; secrets are never expanded beyond what is stated.',
            ].join('\n'),
        },
        {
            role: 'user',
            content: `SCHEMA:\n${JSON.stringify(schema)}\n\nMATERIAL:\n${String(sourceText ?? '').slice(0, 24000)}`,
        },
    ];
}
/**
 * Pull the JSON object out of a model answer (fences tolerated, prose
 * around it tolerated); anything unparseable is a failure with a reason,
 * never a partial store.
 */
function extractJsonBlock(text) {
    const raw = String(text ?? '').trim();
    if (!raw)
        throw new Error('empty model answer');
    const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
    const candidate = (fenced ? fenced[1] : raw).trim();
    const start = candidate.indexOf('{');
    const end = candidate.lastIndexOf('}');
    if (start < 0 || end <= start)
        throw new Error('no JSON object in the model answer');
    try {
        const parsed = JSON.parse(candidate.slice(start, end + 1));
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
            throw new Error('top level is not an object');
        }
        return parsed;
    }
    catch (e) {
        throw new Error(`model answer is not valid JSON: ${e instanceof Error ? e.message : String(e)}`);
    }
}
window.CharacterImport = { parseInputFile, buildConvertPrompt, extractJsonBlock };
