/**
 * setup-checklist.js — New-scenario onboarding checklist (task-382)
 *
 * One modal listing the five setup stages (premise → map → cast → props →
 * hooks). Each row links to the actual tool used for that stage, so a fresh
 * scenario doesn't "exist but nobody knows what to do next". Check state is
 * session-local (localStorage key per scenario name) — resets together with
 * the world when the scenario name changes.
 *
 * @module ui/setup-checklist — new-scenario onboarding checklist
 * @contributes SetupChecklist: the five setup stages with links to each tool, per-scenario check state
 * @powers Scenario creation — telling a fresh scenario's author what to do next (task-382)
 * @relates session-local state (localStorage keyed by scenario name)
 * @docs docs/virtualWorld/ScenarioCreationGuide.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

// Locals for cross-module globals that are not in types/globals.d.ts yet
// (ui/scenario-wizard.js and ui/command-palette.js are still .js). Read off
// `window` rather than `declare`d bare: this is a classic script, so a
// top-level declaration would become a global that collides with the owner.
interface SetupChecklistWindowSurface {
  SetupChecklist: unknown;
  ScenarioWizard?: { open?: () => void };
  CommandPalette?: { open?: () => void };
}

(window as unknown as SetupChecklistWindowSurface).SetupChecklist = (() => {
  'use strict';

  /** One checklist row: a stage, its blurb, and the tool it opens. */
  interface ChecklistStep {
    key: string;
    icon: string;
    title: string;
    desc: string;
    tool: () => void;
    toolLabel: string;
  }

  /** Per-scenario check state, keyed by step key. */
  type DoneMap = Record<string, boolean | undefined>;

  /** Prefill the command line with a partial verb — used by cast/hooks. */
  function prefillCommand(verb: string): void {
    const c = document.getElementById('command-input') as HTMLInputElement | null;
    if (c) { c.focus(); c.value = verb; }
  }

  const STEPS: ChecklistStep[] = [
    { key: 'premise', icon: '📝', title: 'Premise', desc: 'What is the world, tone, and goal?', tool: () => { (window as unknown as SetupChecklistWindowSurface).ScenarioWizard?.open?.(); }, toolLabel: '✨ Scenario from Text…' },
    { key: 'map', icon: '🗺️', title: 'Map', desc: 'Rooms + ways — lay out the space.', tool: () => { (window as unknown as SetupChecklistWindowSurface).CommandPalette?.open?.(); }, toolLabel: '⚡ Graph / rooms' },
    { key: 'cast', icon: '🧍', title: 'Cast', desc: 'Characters — players and NPCs.', tool: () => prefillCommand('create character '), toolLabel: 'Command: create character' },
    { key: 'props', icon: '📦', title: 'Props', desc: 'Items — clutter, equipment, keys.', tool: () => { window.VW?.itemLib?.open(); }, toolLabel: '📚 Item Library' },
    { key: 'hooks', icon: '⚡', title: 'Hooks', desc: 'Triggers — narrative/mechanic beats.', tool: () => prefillCommand('add trigger '), toolLabel: 'Add trigger on an item/way' },
  ];

  const KEY = (name: string): string => 'vw_setup_checklist_' + (name || 'unnamed');

  function loadDone(name: string): DoneMap {
    try {
      const raw = localStorage.getItem(KEY(name));
      return raw ? JSON.parse(raw) as DoneMap : {};
    } catch (e) { return {}; }
  }

  function saveDone(name: string, done: DoneMap): void {
    try { localStorage.setItem(KEY(name), JSON.stringify(done)); } catch (e) { /* ignore */ }
  }

  function open() {
    const name = String((window.worldState as { data?: { _scenario_name?: string } } | undefined)?.data?._scenario_name)
      || document.body.dataset.scenarioName || 'unnamed';
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
    (box.querySelector<HTMLButtonElement>('#sc-close') as HTMLButtonElement).onclick = close;
    overlay.addEventListener('mousedown', (e: MouseEvent) => { if (e.target === overlay) close(); });
    const escHandler = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.preventDefault(); document.removeEventListener('keydown', escHandler); close(); } };
    document.addEventListener('keydown', escHandler);

    for (const s of STEPS) {
      const cb = box.querySelector<HTMLInputElement>('#sc-step-' + s.key);
      if (cb) cb.onchange = () => { done[s.key] = cb.checked; saveDone(name, done); };
      const go = box.querySelector<HTMLButtonElement>('#sc-go-' + s.key);
      if (go) go.onclick = () => { close(); s.tool(); };
    }
  }

  function esc(s: unknown): string {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  return { open };
})();
