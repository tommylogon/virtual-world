# Audio and Video Subsystems and Model Capabilities Audit

Status: Reference Audit
Date: 2026-11-01
Scope: Model Discovery & Inference, Engine Simulation, Client UI

---

## 1. Executive Summary

A codebase audit across the simulation engine, UI client, and LLM integration layers reveals distinct realities for audio and video:

1. **Model Multimodal Discovery**:
   - LM Studio `/api/v1/models` returns exactly 3 capability flags across all 90 loaded models: `reasoning`, `vision`, `trained_for_tool_use`. Neither `audio` nor `video` is returned in LM Studio's current API payload.
   - Standard OpenAI `/models` endpoints do not expose capability dictionaries.
   - The inference prompt pipeline (`engine/llm_client.py`, `static/js/agent-engine.ts`) supports text prompts with optional scene/portrait vision images. It has zero audio transcription, speech-to-text, text-to-speech, or video frame streaming hooks.

2. **Client Audio Subsystem**:
   - `static/js/audio.ts` (task-826) contains an active 216-line procedural Web Audio API synthesizer (`SoundManager`). It generates tactile mechanical clicks, hover blips, turn chimes, and refusal tones without any external audio asset files.
   - Mute state persists across browser reloads via `localStorage.getItem('vw_sound_muted')`.
   - **Audit Finding**: There is currently no UI control (toggle switch or volume slider) in the Settings modal (`templates/index.html`). Mute state can only be changed programmatically via `window.soundManager.toggleMute()`.

3. **Simulation Acoustic Propagation**:
   - Simulation sound rules exist in `engine/narration.py` and `static/js/agent/turn-feed.ts` ("speech carries through ways per the sound model").
   - Sensory conditions filter acoustic cues (e.g. `task-267-deaf` masks auditory signals, while `task-287` allows blind characters to navigate by sound).
   - Involuntary vocal reactions and startles are triggered by loud auditory events in `static/js/agent/involuntary.ts`.

4. **Video Subsystems**:
   - There is zero video rendering, playback, capture, or streaming infrastructure in VirtualWorld.
   - The presentation layer is purely composed of a 2D vis.js network canvas, SVG coordinate overlays, procedural HTML panels, and 2D character portrait thumbnails.

---

## 2. LLM Capabilities & Multimodal Telemetry

### LM Studio Native Endpoint (`/api/v1/models`)

Live verification against LM Studio running locally yielded:
- Models evaluated: 90 models.
- Capability keys detected across all models:
  ```json
  {"reasoning", "vision", "trained_for_tool_use"}
  ```
- Models with `audio`: 0
- Models with `video`: 0

### Forward-Compatibility Plan

To support multimodal models reporting audio or video capabilities (from future LM Studio releases, Ollama, Gemini, or OpenAI multimodal models):

1. **Backend Route (`routes/benchmark.py`)**:
   Extract `audio` and `video` attributes from `caps` and key name patterns:
   ```python
   'audio': bool(caps.get('audio') or 'audio' in key.lower() or 'whisper' in key.lower() or 'tts' in key.lower()),
   'video': bool(caps.get('video')),
   ```

2. **Frontend UI (`static/js/ui-controller.ts`)**:
   Render badges alongside `Vision`, `Tools`, and `Reasoning`:
   - `.model-badge-audio` -> "Audio"
   - `.model-badge-video` -> "Video"

---

## 3. In-App Audio Architecture

### `SoundManager` (`static/js/audio.ts`)

- **Synthesizer Implementation**: Procedural Web Audio API. Zero external `.mp3`, `.wav`, or `.ogg` dependencies.
- **Audio Nodes**:
  - `OscillatorNode` (sine waves for hover/chimes, sawtooth for refusal errors).
  - `BiquadFilterNode` (lowpass filtering for mechanical feedback).
  - `GainNode` with exponential decay ramps for responsive tactile feel.
- **Methods**:
  - `playHover()`: 750 Hz -> 520 Hz sine blip (20ms, debounced to 50ms).
  - `playClick()`: 320 Hz -> 80 Hz click tone with lowpass filter (25ms).
  - `playTurn()` / `playTurnChime()`: Dual harmonic chord (523.25 Hz C5 + 659.25 Hz E5) on turn queue advancement.
  - `playError()`: 130 Hz -> 55 Hz sawtooth rejection buzz (160ms).
  - `toggleMute()`, `setMuted(boolean)`, `isMuted()`.
- **Wiring**:
  - Event delegation bound to `pointerenter` and `click` on `.btn`, `.tab-btn`, `.toolbar-btn`, `.menu-item`, `.action-btn`.
  - Turn advancement sound hooked into `TurnQueue` (`static/js/agent/turn-queue.ts`).

### Recommended Action for Settings Modal

Add a dedicated audio toggle in `templates/index.html` under the General / Appearance section:
```html
<label class="setting-row">
  <span>UI Sound Effects</span>
  <input type="checkbox" id="setting-ui-sound" checked />
</label>
```
Bound to `window.soundManager.setMuted(!checked)` and synced to `localStorage['vw_sound_muted']`.

---

## 4. Video Subsystem Assessment

- **Current State**: Zero video support across engine and UI.
- **Applicability**: Not currently part of the simulation architecture. Scenes are communicated via text narrative, spatial graph nodes, area descriptions, and static character portraits.
- **Potential Future Scope**: If replay captures or animated sprite sequences are ever introduced, they would require a new canvas/video pipeline rather than existing simulation mechanics.
