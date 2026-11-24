"""Interactive ViWo Emotion Lab - live side-by-side A/B/C prototype testbench.

Usage:
    python prototypes/emotions/lab_app.py
    # Opens on http://localhost:5099 backed by real VirtualWorld scenarios!
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, Response, jsonify, request

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
from prototypes.emotions.proto_b_semantic import ProtoBSemanticEngine
from prototypes.emotions.proto_c_dual_mind import ProtoCDualMindEngine
from prototypes.emotions.proto_d_unified import ProtoDUnifiedEngine
from prototypes.emotions.schema import (
    AUTONOMIC_CHANNELS,
    FAMILIES,
    FAMILY_BASELINES,
    EmotionEvent,
)
from prototypes.emotions.viwo_adapter import (
    SCENARIOS_DIR,
    ViwoEmotionHarness,
    load_real_viwo_world,
)

LAB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>VirtualWorld Emotion Lab - Prototypes A / B / C / D</title>
<style>
  :root {
    --bg: #0f1218;
    --panel: #171c26;
    --panel-2: #1e2533;
    --border: #2c3547;
    --text: #e7edf7;
    --muted: #98a6bd;
    --accent: #6aa6ff;
    --warn: #f59e0b;
    --danger: #ef4444;
    --good: #34d399;
    --purple: #a78bfa;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    font-size: 13px;
  }
  .shell {
    display: grid;
    grid-template-rows: auto 1fr;
    min-height: 100vh;
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    padding: 10px 18px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
  }
  header h1 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
  .toolbar-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  select, input, textarea, button {
    background: var(--panel-2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 9px;
    font: inherit;
  }
  button {
    cursor: pointer;
    font-weight: 600;
    transition: background 0.12s, border-color 0.12s;
  }
  button:hover { border-color: var(--accent); background: #252f42; }
  button.primary { background: #264a85; border-color: var(--accent); }
  button.primary:hover { background: #2f5ba3; }
  button.warn { background: #4a3514; border-color: var(--warn); }
  .workspace {
    display: grid;
    grid-template-columns: minmax(290px, 24vw) 1fr;
    gap: 14px;
    padding: 14px;
    align-items: start;
  }
  @media (max-width: 1024px) {
    .workspace { grid-template-columns: 1fr; }
  }
  .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .card h2 {
    margin: 0;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
  }
  .controls-col {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field label {
    font-size: 11px;
    color: var(--muted);
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }
  .vitals-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  .chip-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--panel-2);
    font-size: 11px;
    cursor: pointer;
  }
  .chip input { margin: 0; padding: 0; }
  .compare-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
    gap: 12px;
    align-items: start;
  }
  .engine-col {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .engine-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }
  .engine-title { font-weight: 700; font-size: 13.5px; }
  .pill {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    background: var(--panel-2);
    border: 1px solid var(--border);
  }
  .pill.overload { background: #4a1919; border-color: var(--danger); color: #fecaca; }
  .pill.ok { background: #143628; border-color: var(--good); color: #a7f3d0; }
  .bar-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .bar-row {
    display: grid;
    grid-template-columns: 86px 1fr 48px;
    align-items: center;
    gap: 8px;
    font-size: 11.5px;
  }
  .bar-track {
    height: 8px;
    background: #0d1016;
    border-radius: 999px;
    overflow: hidden;
    position: relative;
  }
  .bar-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--accent);
  }
  .bar-fill.neg { background: var(--danger); }
  .bar-fill.pos { background: var(--good); }
  .bar-fill.body { background: var(--purple); }
  .prose-box {
    background: #10141c;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 9px 10px;
    line-height: 1.48;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .section-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    margin-bottom: 4px;
  }
  .ep-card {
    background: var(--panel-2);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 7px 9px;
    font-size: 11.5px;
    line-height: 1.4;
  }
  .ep-card.sec { border-left-color: var(--warn); }
  .status-line { font-size: 12px; color: var(--muted); margin-left: auto; }
</style>
</head>
<body>
<div class="shell">
  <header>
    <h1>VirtualWorld Emotion Lab (A vs B vs C vs D Unified)</h1>
    <div class="toolbar-group">
      <label for="scenario-sel">Scenario:</label>
      <select id="scenario-sel"></select>
      <label for="char-sel">Character:</label>
      <select id="char-sel"></select>
      <button id="btn-reset">Reset World</button>
    </div>
    <div class="toolbar-group">
      <label for="model-input">C/D Model:</label>
      <input id="model-input" value="qwen3.5-4b" style="width: 140px;" />
      <label class="chip"><input type="checkbox" id="chk-live-lm" checked /> Use live LM Studio</label>
    </div>
    <span class="status-line" id="status-line">Ready</span>
  </header>

  <div class="workspace">
    <div class="controls-col">
      <div class="card">
        <h2>Quick Presets</h2>
        <div class="row">
          <button class="preset-btn" data-preset="jake_crowd">Jake insult (partner + crowd)</button>
          <button class="preset-btn" data-preset="miki_hand">Miki hand hold + trauma</button>
          <button class="preset-btn" data-preset="burned_pot">Burned pot (shame + guilt)</button>
          <button class="preset-btn" data-preset="sarcasm">Subtle sarcasm (no profanity)</button>
          <button class="preset-btn" data-preset="teasing_friend">Teasing close friend</button>
          <button class="preset-btn" data-preset="strained_warm">Warm via shaking body</button>
          <button class="preset-btn" data-preset="reassure">Check facts / reassure</button>
        </div>
      </div>

      <div class="card">
        <h2>Inject Event / Dialogue</h2>
        <div class="row">
          <div class="field" style="flex: 1;">
            <label>Event Kind</label>
            <select id="evt-kind">
              <option value="speech">speech</option>
              <option value="action">action</option>
              <option value="goal">goal</option>
              <option value="threat">threat</option>
              <option value="exposure">exposure</option>
              <option value="discrepancy">discrepancy</option>
              <option value="check_facts">check_facts</option>
              <option value="reassure">reassure</option>
              <option value="repair">repair</option>
            </select>
          </div>
          <div class="field" style="flex: 1;">
            <label>Source / Speaker</label>
            <input id="evt-source" placeholder="e.g. jake halloway" />
          </div>
        </div>
        <div class="field">
          <label>Event Summary</label>
          <textarea id="evt-summary" rows="2" placeholder="What happened in the room..."></textarea>
        </div>
        <div class="row">
          <div class="field" style="flex: 2;">
            <label>Spoken Line (optional)</label>
            <input id="evt-speech" placeholder="Exact dialogue line..." />
          </div>
          <div class="field" style="flex: 1;">
            <label>Speech Tone</label>
            <select id="evt-tone">
              <option value="">plain (neutral)</option>
              <option value="warm">warm</option>
              <option value="teasing">teasing</option>
              <option value="sarcastic">sarcastic</option>
              <option value="cold">cold</option>
              <option value="hostile">hostile</option>
              <option value="serious">serious</option>
              <option value="apologetic">apologetic</option>
              <option value="guarded">guarded</option>
            </select>
          </div>
        </div>
        <div class="row">
          <label class="chip"><input type="checkbox" id="chk-spk-overloaded" /> Speaker overloaded / shaking (voice strain leak)</label>
        </div>
        <div class="row">
          <div class="field" style="flex: 1;">
            <label>Witnesses (comma-separated)</label>
            <input id="evt-witnesses" placeholder="Sammy, Kayla, Zoe" />
          </div>
          <div class="field" style="flex: 1;">
            <label>Expectation before event</label>
            <input id="evt-expectation" placeholder="Expected warmth or thanks" />
          </div>
        </div>
        <div class="row">
          <button class="primary" id="btn-run-all" style="flex: 1;">Run A vs B vs C vs D</button>
          <button id="btn-tick">+2 Ticks (Inertia)</button>
          <button class="warn" id="btn-track2">Run Track 2 Actor (D)</button>
        </div>
      </div>

      <div class="card">
        <h2>Vulnerability Vitals & Character Traits</h2>
        <div class="vitals-grid">
          <div class="field"><label>Energy (<span id="lbl-energy">50</span>)</label><input type="range" id="v-energy" min="0" max="100" value="50" /></div>
          <div class="field"><label>Hunger (<span id="lbl-hunger">40</span>)</label><input type="range" id="v-hunger" min="0" max="100" value="40" /></div>
          <div class="field"><label>Sanity (<span id="lbl-sanity">70</span>)</label><input type="range" id="v-sanity" min="0" max="100" value="70" /></div>
          <div class="field"><label>Temp C (<span id="lbl-temp">37.0</span>)</label><input type="range" id="v-temp" min="33.5" max="39.5" step="0.1" value="37.0" /></div>
        </div>
        <div class="field">
          <label>Active Character Traits (drive suppression / inertia)</label>
          <div class="chip-grid" id="traits-box"></div>
        </div>
        <div class="row">
          <label class="chip"><input type="checkbox" id="chk-override" /> Human Director Override Mode</label>
        </div>
      </div>
    </div>

    <div class="compare-grid" id="compare-grid"></div>
  </div>
</div>

<script>
const TRAIT_OPTIONS = ['stoic', 'composed', 'guarded', 'protective', 'stubborn', 'impulsive', 'jittery', 'guilt_prone', 'honest'];
const FAMILIES = __FAMILIES_JSON__;
const AUTO_CHANNELS = __AUTO_JSON__;

let currentState = null;

function setStatus(msg) {
  document.getElementById('status-line').textContent = msg;
}

function renderTraits() {
  const box = document.getElementById('traits-box');
  box.innerHTML = '';
  for (const t of TRAIT_OPTIONS) {
    const lbl = document.createElement('label');
    lbl.className = 'chip';
    lbl.innerHTML = `<input type="checkbox" value="${t}" /> ${t}`;
    box.appendChild(lbl);
  }
}

function selectedTraits() {
  return [...document.querySelectorAll('#traits-box input:checked')].map(el => el.value);
}

function bindVitalsSliders() {
  const pairs = [
    ['v-energy', 'lbl-energy'],
    ['v-hunger', 'lbl-hunger'],
    ['v-sanity', 'lbl-sanity'],
    ['v-temp', 'lbl-temp'],
  ];
  for (const [id, lbl] of pairs) {
    const inp = document.getElementById(id);
    inp.addEventListener('input', () => {
      document.getElementById(lbl).textContent = inp.value;
    });
  }
}

function renderColumns(results, track2) {
  const grid = document.getElementById('compare-grid');
  grid.innerHTML = '';
  for (const key of ['A', 'B', 'C', 'D']) {
    const r = results[key];
    if (!r) continue;
    const col = document.createElement('div');
    col.className = 'engine-col';

    const pillCls = r.overloaded ? 'pill overload' : 'pill ok';
    const pillTxt = r.overloaded ? `OVERLOAD (${r.peak_arousal}/${r.regulation_capacity})` : `Composed (${r.peak_arousal}/${r.regulation_capacity})`;

    let famBars = '';
    for (const f of FAMILIES) {
      const val = r.after_families[f] ?? 0;
      const delta = r.applied_deltas?.[f] ?? 0;
      const cls = ['happiness', 'love', 'calm'].includes(f) ? 'pos' : 'neg';
      const dTxt = Math.abs(delta) >= 0.5 ? ` (${delta > 0 ? '+' : ''}${Math.round(delta)})` : '';
      famBars += `<div class="bar-row"><span>${f}</span><div class="bar-track"><div class="bar-fill ${cls}" style="width:${Math.min(100, Math.max(0, val))}%"></div></div><span>${Math.round(val)}${dTxt}</span></div>`;
    }

    let bodyBars = '';
    for (const ch of AUTO_CHANNELS) {
      const val = r.autonomic[ch] ?? 0;
      const pct = Math.min(100, Math.abs(val));
      bodyBars += `<div class="bar-row"><span>${ch}</span><div class="bar-track"><div class="bar-fill body" style="width:${pct}%"></div></div><span>${val > 0 ? '+' : ''}${Math.round(val)}</span></div>`;
    }

    let epsHtml = '';
    for (const ep of (r.episodes || [])) {
      const cls = ep.secondary_of ? 'ep-card sec' : 'ep-card';
      epsHtml += `<div class="${cls}"><b>${ep.family}</b> (${ep.peak_delta > 0 ? '+' : ''}${ep.peak_delta}) ${ep.resolved ? '[RESOLVED]' : '[ACTIVE]'} ${ep.suppressed ? '[SUPPRESSED]' : ''}<br/>Trigger: ${ep.prompting_event?.summary || ''}<br/>Appraisal: ${ep.appraisal || ''}<br/>Urges: ${(ep.urges || []).join(', ')}</div>`;
    }

    let track2Html = '';
    if (key === 'D' && track2) {
      track2Html = `
        <div>
          <div class="section-label">Track 2 Conscious Actor Reply (${track2.latency_ms ?? 0} ms)</div>
          <div class="prose-box"><b>Inner monologue:</b> ${track2.inner_monologue || '(none)'}
<b>Speech:</b> ${track2.speech_after_involuntary || track2.speech || '(silent)'}
<b>Emote:</b> ${track2.emote || '(none)'}
<b>Action:</b> ${track2.action || 'wait'}</div>
        </div>`;
    }

    col.innerHTML = `
      <div class="engine-head">
        <span class="engine-title">${r.engine_name}</span>
        <span class="pill">${r.latency_ms} ms | ${r.metadata?.method || ''}</span>
      </div>
      <div class="row">
        <span class="pill">Dom: <b>${r.dominant_family}</b></span>
        <span class="pill">Portrait: <b>${r.portrait_expression}</b></span>
        <span class="${pillCls}">${pillTxt}</span>
        <span class="pill">V:${r.valence} A:${r.arousal}</span>
      </div>
      <div>
        <div class="section-label">=== YOUR STATE === (Embodied Prompt to Actor)</div>
        <div class="prose-box">${r.prompt_your_state || '(calm / near baseline)'}</div>
      </div>
      <div>
        <div class="section-label">People here: (What Observers See Even If Emote Is Null)</div>
        <div class="prose-box"><b>Normal light:</b> ${r.observer_tells_normal || '(nothing visible)'}
<b>Dim light:</b> ${r.observer_tells_dim || '(nothing visible)'}
<b>High Insight / Close Friend:</b> ${r.observer_tells_insight || '(nothing visible)'}</div>
      </div>
      ${track2Html}
      <div>
        <div class="section-label">Per-Target Live Feelings</div>
        <div class="box">${Object.keys(r.target_families || {}).length ? Object.entries(r.target_families).map(([t, fams]) => `<b>${t}:</b> ` + Object.entries(fams).map(([k, v]) => `${k} ${v}`).join(', ')).join('<br>') : '<span style="color:var(--muted)">(no target-specific overlay yet)</span>'}</div>
      </div>
      <div>
        <div class="section-label">13-Family Emotional Matrix</div>
        <div class="bar-list">${famBars}</div>
      </div>
      <div>
        <div class="section-label">8-Channel Autonomic Body (Outside LLM Control)</div>
        <div class="bar-list">${bodyBars}</div>
      </div>
      <div>
        <div class="section-label">Worksheet-4 Causal Episodes (${(r.episodes || []).length})</div>
        <div style="display:flex;flex-direction:column;gap:6px;">${epsHtml || '<span style="color:var(--muted)">(no active episodes)</span>'}</div>
      </div>
    `;
    grid.appendChild(col);
  }
}

async function initLab(scenario) {
  setStatus('Loading real ViWo scenario...');
  const resp = await fetch('/api/lab/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  });
  const data = await resp.json();
  currentState = data;
  const scSel = document.getElementById('scenario-sel');
  if (!scSel.options.length) {
    for (const s of data.scenarios) {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      scSel.appendChild(opt);
    }
  }
  scSel.value = data.scenario;
  const chSel = document.getElementById('char-sel');
  chSel.innerHTML = '';
  for (const c of data.characters) {
    const opt = document.createElement('option');
    opt.value = c;
    opt.textContent = c;
    chSel.appendChild(opt);
  }
  if (data.characters.includes('miki doki')) chSel.value = 'miki doki';
  setStatus(`Loaded ${data.scenario} (${data.characters.length} characters)`);
}

async function runStep(includeTrack2 = false) {
  const charName = document.getElementById('char-sel').value;
  setStatus(includeTrack2 ? 'Running Track 1 + Track 2...' : 'Running Prototypes A, B, and C...');
  const payload = {
    character: charName,
    kind: document.getElementById('evt-kind').value,
    source_name: document.getElementById('evt-source').value.trim() || null,
    summary: document.getElementById('evt-summary').value.trim(),
    speech_text: document.getElementById('evt-speech').value.trim(),
    speech_tone: document.getElementById('evt-tone').value || null,
    speaker_overloaded: document.getElementById('chk-spk-overloaded').checked,
    witnesses: document.getElementById('evt-witnesses').value.split(',').map(s => s.trim()).filter(Boolean),
    expectations: document.getElementById('evt-expectation').value.trim() ? [document.getElementById('evt-expectation').value.trim()] : [],
    vitals: {
      Energy: Number(document.getElementById('v-energy').value),
      Hunger: Number(document.getElementById('v-hunger').value),
      Sanity: Number(document.getElementById('v-sanity').value),
      Temperature: Number(document.getElementById('v-temp').value),
    },
    traits: selectedTraits(),
    live_lm: document.getElementById('chk-live-lm').checked,
    model: document.getElementById('model-input').value.trim() || 'google/gemma-4-e4b',
    run_track2: includeTrack2,
  };
  const resp = await fetch('/api/lab/step', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  renderColumns(data.results, data.track2);
  setStatus(`Done (A: ${data.results.A.latency_ms}ms | B: ${data.results.B.latency_ms}ms | C: ${data.results.C.latency_ms}ms | D: ${data.results.D.latency_ms}ms)`);
}

async function runTicks() {
  const charName = document.getElementById('char-sel').value;
  setStatus('Advancing 2 ticks...');
  const resp = await fetch('/api/lab/tick', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character: charName, ticks: 2 }),
  });
  const data = await resp.json();
  renderColumns(data.results, null);
  setStatus('Advanced +2 ticks (inertia & decay updated)');
}

const PRESETS = {
  jake_crowd: {
    kind: 'speech', source: 'jake halloway',
    summary: 'Jake snapped right after she went out of her way to help him, in front of their friends.',
    speech: "You're a bitch.", witnesses: 'Sammy, Kayla, Zoe',
    expectation: 'Expected Jake to thank her for helping',
  },
  miki_hand: {
    kind: 'speech', source: 'jake halloway',
    summary: 'Jake stepped closer on cold Elm Street, reached for her hand, and asked her real name.',
    speech: "Hey, you're shivering. Tell me your real name so I don't lose you.",
    witnesses: '', expectation: 'Trying to keep it casual so nobody gets close enough to leave',
  },
  burned_pot: {
    kind: 'action', source: 'Rosa',
    summary: "Left roommate's pot on the burner, destroyed it, and threw it away without telling her; now she is asking where it went.",
    speech: "Hey, did you see my pot? I can't find it anywhere.",
    witnesses: '', expectation: 'Terrified she will hate me and kick me out',
  },
  sarcasm: {
    kind: 'speech', source: 'Claire',
    summary: "Claire glanced at Elena's all-night presentation in front of the whole team with a flat, polite smile.",
    speech: "Oh, you really tried your best on this, didn't you? That's... adorable. Honestly, don't stress, I'll just redo the whole thing myself tonight.",
    tone: 'sarcastic', overloaded: false,
    witnesses: 'Sammy, Devon, Kayla', expectation: 'Expected Claire to appreciate the all-night effort',
  },
  teasing_friend: {
    kind: 'speech', source: 'jake halloway',
    summary: 'Jake grinned after she stole the last fry off his plate.',
    speech: "You're a bitch.",
    tone: 'teasing', overloaded: false,
    witnesses: '', expectation: '',
  },
  strained_warm: {
    kind: 'speech', source: 'jake halloway',
    summary: 'Forced a bright smile while trying to wave off concern.',
    speech: "I'm totally fine, honestly, don't worry about me!",
    tone: 'warm', overloaded: true,
    witnesses: '', expectation: '',
  },
  reassure: {
    kind: 'check_facts', source: 'jake halloway',
    summary: 'Asked directly if they were angry or going to leave; they smiled steadily and reassured her.',
    speech: "No, I'm not mad and I'm not going anywhere. Take your time.",
    tone: 'warm', overloaded: false,
    witnesses: '', expectation: '',
  },
};

document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const p = PRESETS[btn.dataset.preset];
    document.getElementById('evt-kind').value = p.kind;
    document.getElementById('evt-source').value = p.source;
    document.getElementById('evt-summary').value = p.summary;
    document.getElementById('evt-speech').value = p.speech;
    document.getElementById('evt-tone').value = p.tone || '';
    document.getElementById('chk-spk-overloaded').checked = Boolean(p.overloaded);
    document.getElementById('evt-witnesses').value = p.witnesses;
    document.getElementById('evt-expectation').value = p.expectation;
  });
});

document.getElementById('btn-reset').addEventListener('click', () => initLab(document.getElementById('scenario-sel').value));
document.getElementById('scenario-sel').addEventListener('change', e => initLab(e.target.value));
document.getElementById('btn-run-all').addEventListener('click', () => runStep(false));
document.getElementById('btn-track2').addEventListener('click', () => runStep(true));
document.getElementById('btn-tick').addEventListener('click', runTicks);

renderTraits();
bindVitalsSliders();
initLab('taco_bell_date');
</script>
</body>
</html>
"""


def create_lab_app() -> Flask:
    app = Flask(__name__)
    session: Dict[str, Any] = {
        "scenario": "taco_bell_date",
        "harnesses": {},
        "tick": 1,
        "last_results": {},
    }

    def _init_scenario(scenario_name: str) -> Dict[str, Any]:
        # Create 4 independent real ViWo worlds so A, B, C, and D evolve cleanly side-by-side!
        w_a = load_real_viwo_world(scenario_name)
        w_b = load_real_viwo_world(scenario_name)
        w_c = load_real_viwo_world(scenario_name)
        w_d = load_real_viwo_world(scenario_name)
        session["scenario"] = scenario_name
        session["tick"] = 1
        session["harnesses"] = {
            "A": ViwoEmotionHarness(w_a, ProtoAMatrixEngine()),
            "B": ViwoEmotionHarness(w_b, ProtoBSemanticEngine()),
            "C": ViwoEmotionHarness(w_c, ProtoCDualMindEngine()),
            "D": ViwoEmotionHarness(w_d, ProtoDUnifiedEngine()),
        }
        session["last_results"] = {}
        scenarios = sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
        return {
            "scenario": scenario_name,
            "scenarios": scenarios,
            "characters": sorted(w_a.players.keys()),
        }

    @app.route("/")
    def index():
        html = (
            LAB_HTML
            .replace("__FAMILIES_JSON__", json.dumps(list(FAMILIES)))
            .replace("__AUTO_JSON__", json.dumps(list(AUTONOMIC_CHANNELS)))
        )
        return Response(html, mimetype="text/html")

    @app.route("/api/lab/init", methods=["POST"])
    def api_init():
        data = request.get_json(force=True) or {}
        sc = str(data.get("scenario") or "taco_bell_date")
        return jsonify(_init_scenario(sc))

    @app.route("/api/lab/step", methods=["POST"])
    def api_step():
        data = request.get_json(force=True) or {}
        if not session["harnesses"]:
            _init_scenario("taco_bell_date")
        char_name = str(data.get("character") or "")
        live_lm = bool(data.get("live_lm", True))
        model = str(data.get("model") or "qwen3.5-4b")
        session["tick"] += 1

        event = EmotionEvent(
            kind=str(data.get("kind") or "speech"),
            summary=str(data.get("summary") or "A moment unfolds."),
            source_name=data.get("source_name") or None,
            speech_text=str(data.get("speech_text") or ""),
            speech_tone=data.get("speech_tone") or None,
            speaker_overloaded=bool(data.get("speaker_overloaded", False)),
            tick=session["tick"],
            witnesses=list(data.get("witnesses") or []),
            expectations=list(data.get("expectations") or []),
        )
        vitals = data.get("vitals") or {}
        traits_in = list(data.get("traits") or [])

        # Update live/offline mode on B, C, and D; clear B's anchor cache if provider switches
        # so embedding vector dimensions never mismatch across toggles.
        b_eng = session["harnesses"]["B"].engine
        want_offline = not live_lm
        if b_eng.backend.offline != want_offline:
            b_eng.backend.offline = want_offline
            b_eng.backend.active_provider = "uninitialized"
            b_eng._anchor_vecs = None
        session["harnesses"]["C"].engine.offline = want_offline
        session["harnesses"]["C"].engine.limbic_model = model
        session["harnesses"]["C"].engine.actor_model = model
        d_eng = session["harnesses"]["D"].engine
        d_eng.set_offline(want_offline)
        d_eng.limbic_model = model
        d_eng.actor_model = model

        results: Dict[str, Any] = {}
        d_step = None
        for key in ("A", "B", "C", "D"):
            h: ViwoEmotionHarness = session["harnesses"][key]
            p = h.world.players[char_name]
            for vk, vv in vitals.items():
                if vk in p.vitals:
                    p.vitals[vk] = vv
            if traits_in:
                p.traits = {t: 1 for t in traits_in}
            res = h.step_event(char_name, copy.deepcopy(event))
            if key == "D":
                d_step = res
            results[key] = res.to_dict()

        session["last_results"] = results
        track2 = None
        if data.get("run_track2") and d_step is not None:
            h_d: ViwoEmotionHarness = session["harnesses"]["D"]
            track2 = h_d.engine.run_track2_actor(d_step, event, h_d.world.players[char_name])
        return jsonify({"results": results, "track2": track2})

    @app.route("/api/lab/tick", methods=["POST"])
    def api_tick():
        data = request.get_json(force=True) or {}
        char_name = str(data.get("character") or "")
        ticks = int(data.get("ticks") or 2)
        results = {}
        for key in ("A", "B", "C", "D"):
            h: ViwoEmotionHarness = session["harnesses"][key]
            ticked = h.tick_all(ticks=ticks).get(char_name, {})
            prev = dict(session["last_results"].get(key) or {})
            prev["after_families"] = ticked.get("families", prev.get("after_families", {}))
            prev["autonomic"] = ticked.get("autonomic", prev.get("autonomic", {}))
            prev["dominant_family"] = ticked.get("dominant_family", prev.get("dominant_family", "neutral"))
            prev["portrait_expression"] = ticked.get("portrait_expression", prev.get("portrait_expression", "neutral"))
            prev["valence"] = ticked.get("valence", prev.get("valence", 0.0))
            prev["arousal"] = ticked.get("arousal", prev.get("arousal", 0.1))
            prev["applied_deltas"] = {}
            results[key] = prev
        session["last_results"] = results
        return jsonify({"results": results})

    return app


if __name__ == "__main__":
    app = create_lab_app()
    print("Starting VirtualWorld Emotion Lab on http://localhost:5099")
    app.run(host="127.0.0.1", port=5099, debug=False)
