/**
 * object-responder.js — browser-side LLM responses for `llm_respond` (task-330)
 *
 * The engine queues a pending request when an `llm_respond` trigger effect
 * fires (objects like a magic mirror speaking real lines). Keys live in the
 * browser (backend LLM modules are gone), so this module:
 *   1. watches worldState for `llm_pending` requests (in /api/state),
 *   2. generates a spoken line via llmClient (AIGenerator's chat pattern),
 *   3. POSTs the line back to /api/llm_respond, which broadcasts it as area
 *      speech from the object (nearby agents hear + remember it),
 *   4. falls back to the effect's `fallback_message` when no key / failure.
 *
 * Cooldown is enforced server-side (one pending request per node at a time).
 */
window.ObjectResponder = (() => {
  'use strict';

  let _handled = new Set();   // request ids done this session
  let _busy = false;

  async function _generate(request) {
    const instructions = request.instructions || 'Stay in character. Be brief.';
    const heard = (request.heard || '').trim();
    const speaker = request.speaker || 'something';
    const maxWords = request.max_words || 40;
    const system = (
      `${instructions}\n\nYou are the voice of "${speaker}". ` +
      `Speak as this object/world entity would — in-character, diegetic, never mentioning that you are an AI. ` +
      `Reply with ONLY the spoken line. Maximum ${maxWords} words. No quotes, no stage directions.`
    );
    const user = heard
      ? `What was said to you: "${heard}"\n\nYour spoken line:`
      : `Respond aloud${heard ? '' : ' (no one said anything — react naturally)'}.`;
    try {
      if (!config.apiKey || !config.model) return null;
      const resp = await llmClient.chat(
        [{ role: 'system', content: system }, { role: 'user', content: user }],
        { temperature: 0.9, max_tokens: Math.min(160, maxWords * 3) }
      );
      const line = (resp || '').trim().replace(/^["'\s]+|["'\s]+$/g, '');
      return line || null;
    } catch (e) {
      console.warn('[object-responder] LLM call failed:', e && e.message);
      return null;
    }
  }

  async function _handle(request) {
    if (!request || !request.id || _handled.has(request.id)) return;
    if (!request.id.startsWith('llm_req_')) return;
    let line = await _generate(request);
    if (!line) line = request.fallback_message || '';
    // Post back (empty line = fallback consumed, still remove the request)
    try {
      const resp = await fetch('/api/llm_respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: request.id, text: line })
      });
      await resp.json();
    } catch (e) {
      console.warn('[object-responder] postback failed:', e && e.message);
    }
    _handled.add(request.id);
  }

  async function tick() {
    if (_busy) return;
    const pending = worldState.data?.llm_pending;
    if (!Array.isArray(pending) || pending.length === 0) return;
    _busy = true;
    try {
      for (const req of pending.slice(0, 3)) {  // at most 3 per tick
        await _handle(req);
      }
    } finally {
      _busy = false;
    }
  }

  // Watch the state bus (debounced) — same pattern as scenario-status chip.
  let _timer = null;
  if (window.appEvents) {
    appEvents.on('state:updated', () => {
      if (_timer) clearTimeout(_timer);
      _timer = setTimeout(tick, 600);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tick);
  } else {
    tick();
  }

  return { tick };
})();
