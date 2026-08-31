/**
 * setup-checklist.js — New-scenario onboarding checklist (task-382)
 *
 * One modal listing the five setup stages (premise → map → cast → props →
 * hooks). Each row links to the actual tool used for that stage, so a fresh
 * scenario doesn't "exist but nobody knows what to do next". Check state is
 * session-local (localStorage key per scenario name) — resets together with
 * the world when the scenario name changes.
 */
window.SetupChecklist = (() => {
  'use strict';

  const STEPS = [
    { key: 'premise', icon: '📝', title: 'Premise', desc: 'What is the world, tone, and goal?', tool: () => window.ScenarioWizard?.open ? ScenarioWizard.open() : null(), toolLabel: '✨ Scenario from Text…' },
    { key: 'map', icon: '🗺️', title: 'Map', desc: 'Rooms + ways — lay out the space.', tool: () => window.CommandPalette?.open ? CommandPalette.open() : null(), toolLabel: '⚡ Graph / rooms' },
    { key: 'cast', icon: '🧍', title: 'Cast', desc: 'Characters — players and NPCs.', tool: () => { const c = document.getElementById('command-input'); if (c) { c.focus(); c.value = 'create character '; } }, toolLabel: 'Command: create character' },
    { key: 'props', icon: '📦', title: 'Props', desc: 'Items — clutter, equipment, keys.', tool: () => window.VW?.itemLib?.open ? VW.itemLib.open() : null(), toolLabel: '📚 Item Library' },
    { key: 'hooks', icon: '⚡', title: 'Hooks', desc: 'Triggers — narrative/mechanic beats.', tool: () => { const c = document.getElementById('command-input'); if (c) { c.focus(); c.value = 'add trigger '; } }, toolLabel: 'Add trigger on an item/way' },
  ];

  const KEY = (name) => 'vw_setup_checklist_' + (name || 'unnamed');

  function loadDone(name) {
    try {
      const raw = localStorage.getItem(KEY(name));
      return raw ? JSON.parse(raw) : {};
    } catch (e) { return {}; }
  }

  function saveDone(name, done) {
    try { localStorage.setItem(KEY(name), JSON.stringify(done)); } catch (e) { /* ignore */ }
  }

  function open() {
    const name = (window.worldState?.data?._scenario_name) || document.body.dataset.scenarioName || 'unnamed';
    const done = loadDone(name);
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    const box = document.createElement('div');
    box.className = 'modal-window';
    box.style.cssText = 'width:520px;max-width:92vw;';

    const doneCount = STEPS.filter(s => done[s.key]).length;
    let html = '<div class="modal-head"><h3 style="margin:0;font-size:15px;">🚀 Scenario setup checklist</h3>'
      + '<button class="modal-close-btn" id="sc-close">✕</button></div>'
      + '<div style="font-size:11px;color:var(--text-dim);margin-bottom:10px;">Scenario: <strong>' + esc(name) + '</strong> · ' + doneCount + '/' + STEPS.length + ' done</div>';

    for (const s of STEPS) {
      const checked = done[s.key] ? 'checked' : '';
      html += '<div style="display:flex;gap:8px;align-items:flex-start;padding:8px 2px;border-bottom:1px solid var(--border);">'
        + '<input type="checkbox" id="sc-step-' + s.key + '" ' + checked + ' style="margin-top:4px;">'
        + '<div style="flex:1;min-width:0;">'
        + '<div style="font-size:13px;font-weight:600;">' + s.icon + ' ' + esc(s.title) + '</div>'
        + '<div style="font-size:11px;color:var(--text-muted);">' + esc(s.desc) + '</div>'
        + '<button class="btn btn-sm btn-ghost" id="sc-go-' + s.key + '" style="font-size:9px;margin-top:2px;color:var(--accent);">' + esc(s.toolLabel) + ' →</button>'
        + '</div></div>';
    }

    html += '<div style="padding-top:10px;border-top:1px solid var(--border);margin-top:8px;font-size:10px;color:var(--text-muted);">Checklist state is per-scenario (session storage). Reset happens naturally when you open/commit a different scenario.</div>';

    box.innerHTML = html;
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    const close = () => overlay.remove();
    box.querySelector('#sc-close').onclick = close;
    overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) close(); });
    const escHandler = (e) => { if (e.key === 'Escape') { e.preventDefault(); document.removeEventListener('keydown', escHandler); close(); } };
    document.addEventListener('keydown', escHandler);

    for (const s of STEPS) {
      const cb = box.querySelector('#sc-step-' + s.key);
      if (cb) cb.onchange = () => { done[s.key] = cb.checked; saveDone(name, done); };
      const go = box.querySelector('#sc-go-' + s.key);
      if (go) go.onclick = () => { close(); s.tool(); };
    }
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  return { open };
})();
