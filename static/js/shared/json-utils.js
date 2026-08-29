/**
 * Shared JSON parsing utilities.
 * Many functions across the codebase strip ```json code fences and extract JSON.
 * This centralises that pattern.
 */

/** Strip code fences (```json ... ```) and extract JSON from a response string.
 *  Returns {json, raw} where json is the parsed object or null, raw is the extracted string. */
function parseJSONFromResponse(response) {
    if (!response) return { json: null, raw: '' };
    let content = response.trim();
    const match = content.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    if (match) {
        content = match[1].trim();
    } else {
        // Fallback: find first { and last }
        const firstBrace = content.indexOf('{');
        const lastBrace = content.lastIndexOf('}');
        if (firstBrace !== -1 && lastBrace > firstBrace) {
            content = content.substring(firstBrace, lastBrace + 1);
        }
    }
    try {
        return { json: JSON.parse(content), raw: content };
    } catch {
        return { json: null, raw: content };
    }
}

/** Safe parse a JSON string, returning null on failure instead of throwing */
function parseJsonSafely(str) {
    try {
        return JSON.parse(str);
    } catch {
        return null;
    }
}

/** Recursively sort object keys + normalize so deep comparison is key-order insensitive. */
function canonicalizeJSON(value) {
    if (value === null || value === undefined) return value;
    if (Array.isArray(value)) return value.map(canonicalizeJSON);
    if (typeof value === 'object') {
        const out = {};
        for (const k of Object.keys(value).sort()) out[k] = canonicalizeJSON(value[k]);
        return out;
    }
    return value;
}

/** Key-order-insensitive deep equality between two values. */
function jsonDeepEqual(a, b) {
    const ca = canonicalizeJSON(a);
    const cb = canonicalizeJSON(b);
    const sa = ca === undefined || ca === null ? '' : JSON.stringify(ca);
    const sb = cb === undefined || cb === null ? '' : JSON.stringify(cb);
    return sa === sb;
}


/** Extract assistant-visible text from raw LLM output (API envelope, thinking prefix, fences). */
function extractAssistantText(raw) {
    if (raw == null) return '';
    let text = String(raw).trim();
    if (!text) return '';

    if (text.startsWith('{') && text.includes('"choices"')) {
        try {
            const envelope = JSON.parse(text);
            const fromMessage = envelope?.choices?.[0]?.message?.content;
            if (fromMessage) text = String(fromMessage).trim();
        } catch {
            // repairJSON may still salvage inner JSON
        }
    }

    text = text.replace(/^\uFEFF/, '');
    text = text.replace(/^🧠\s*thinking\.\.\./i, '').trim();
    text = text.replace(/^thinking\.\.\./i, '').trim();
    text = text.replace(/<think>[\s\S]*?<\/think>\s*/gi, '').trim();

    const fenced = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    if (fenced) text = fenced[1].trim();

    return text;
}

/** Repair common LLM JSON formatting failures before parsing.
 *  Handles: code fences, raw newlines/tabs in strings, non-ASCII chars,
 *  trailing commas before ]/}, missing commas between properties, and
 *  missing closing braces/brackets.
 *  Returns the repaired string; falls back to the raw input on failure.
 *  Sets window.__repairStats.repaired = true when the input needed fixing,
 *  so callers can surface "salvaged from broken JSON" instead of silently
 *  dropping fields (N1). */
function repairJSON(raw) {
    window.__repairStats = window.__repairStats || { repaired: false };
    window.__repairStats.repaired = false;
    let s = raw.trim();
    s = s.replace(/^\uFEFF/, '');
    const fence = s.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    if (fence) {
        s = fence[1].trim();
    } else {
        const first = s.indexOf('{');
        const last = s.lastIndexOf('}');
        if (first !== -1) {
            s = last > first ? s.substring(first, last + 1) : s.substring(first);
        } else if (last !== -1) {
            s = '{' + s.substring(0, last).trim() + '}';
        } else if (!/[:]/.test(s)) {
            return s;
        }
    }
    // If it already parses cleanly, return as-is and skip aggressive repair
    try { JSON.parse(s); return s; } catch {}
    // Anything past this point was repaired — flag it.
    window.__repairStats.repaired = true;
    // Qwen 3.5 with empty-assistant-message workaround sometimes drops the outer {}.
    // If the string does not start with { or [, wrap it in {} so the parser
    // gets a valid object. Only do this if the content looks like JSON.
    const trimmed = s.trim();
    if (!/^[{\[]/.test(trimmed) && /[:]/.test(trimmed)) {
        s = '{' + s + '}';
    }
    if (!s.includes('{')) return s;
    // Fix missing commas between properties: a closing-quote not preceded
    // by backslash, followed by whitespace (including newlines), followed
    // by an opening-quote of the next key. Skips escaped quotes inside
    // string values (\").
    s = s.replace(/(?<!")\s+"/g, ',"');
    s = s.replace(/\r\n/g, '\n');
    s = s.replace(/\\n/g, '\\\\n');
    s = s.replace(/\\r/g, '\\\\r');
    s = s.replace(/\\t/g, '\\\\t');
    s = s.replace(/[^\u0020-\u007E\n\t]/g, c => {
        const code = c.charCodeAt(0);
        if (code > 0x7F) return '\\u' + code.toString(16).padStart(4, '0');
        return c;
    });
    s = s.replace(/\n/g, '\\n');
    s = s.replace(/\r/g, '\\r');
    s = s.replace(/\t/g, '\\t');
    s = s.replace(/,([ \t]*[}\]])/g, '$1');
    const openBrackets = (s.match(/\[/g) || []).length;
    const closeBrackets = (s.match(/\]/g) || []).length;
    if (openBrackets > closeBrackets) s += ']'.repeat(openBrackets - closeBrackets);
    const openBraces = (s.match(/\{/g) || []).length;
    const closeBraces = (s.match(/\}/g) || []).length;
    if (openBraces > closeBraces) s += '}'.repeat(openBraces - closeBraces);
    return s;
}
