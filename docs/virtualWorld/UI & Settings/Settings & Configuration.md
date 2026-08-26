# Settings & Configuration

VirtualWorld's settings are managed through a combination of backend route handlers, a frontend `ConfigManager` with IndexedDB persistence, and a settings UI panel.

## Settings Architecture

### Backend Routes (`routes/settings.py`)

The `register_settings_routes()` function registers all settings-related API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings/ghost_mode` | Get ghost mode status |
| POST | `/api/settings/ghost_mode` | Toggle ghost mode on/off |
| GET | `/api/settings/narration` | Get narration mode |
| POST | `/api/settings/narration` | Set narration mode (`none`/`player`/`ai`) |
| GET | `/api/settings/time_per_tick` | Get minutes per game tick |
| POST | `/api/settings/time_per_tick` | Set minutes per game tick |
| GET | `/api/settings/engine_config` | Get live engine tuning constants + schema (task-304) |
| POST | `/api/settings/engine_config` | Save engine tuning overrides |
| POST | `/api/settings/engine_config/reset` | Restore engine tuning defaults |
| POST | `/api/debug/save_log` | Save a run log file for debugging |
| GET | `/api/debug/state` | Compact debug dump of world state |
| POST | `/api/path` | Find path between two areas |
| POST | `/api/embeddings` | Generate text embeddings |

### Frontend ConfigManager (`static/js/config.js`)

The `ConfigManager` class (`window.config`) manages all client-side settings with automatic IndexedDB persistence.

**Storage keys** (line 16-58):

| Key | Default | UI Control |
|-----|---------|------------|
| `api_key` | `''` | API Key input |
| `api_base` | `https://api.openai.com/v1` | API Base URL input |
| `model` | `gpt-4.1-mini` | Model select/text |
| `provider` | `openai` | (auto-detected) |
| `temperature` | `0.7` | Temperature slider |
| `max_tokens` | `512` | Max tokens input |
| `show_logs` | `false` | Show logs checkbox |
| `streaming` | `false` | Streaming checkbox |
| `turn_based` | `false` | Turn-based mode checkbox |
| `turn_order` | `sequential` | Turn order select |
| `tick_interval` | `10` | Tick interval (ms) |
| `reactive_mode` | `true` | Reactive mode checkbox |
| `ghost_mode` | `false` | Ghost mode checkbox |
| `manual_mode` | `false` | Manual mode checkbox |
| `auto_generate_descriptions` | `true` | Auto-Generate Descriptions checkbox |
| `rpm_limit` | `0` | RPM limit input |
| `tpm_limit` | `0` | TPM limit input |
| `filter_thoughts` | `true` | Event filter |
| `filter_speech` | `true` | Event filter |
| `filter_actions` | `true` | Event filter |
| `filter_system` | `true` | Event filter |
| `filter_rawllm` | `true` | Event filter |
| `last_profile` | `null` | Last used profile |
| `embedding_provider` | `local` | Embedding source (`local`/`api`) |
| `embedding_model` | `text-embedding-3-small` | Embedding model name (API mode) |

## Toggleable Settings

### Ghost Mode

When enabled (`ghost_mode: true`), dead characters can continue to act and observe as ghosts. The setting lives on `app.world.ghost_mode` and is toggled via:

- **UI**: Checkbox in the Settings panel
- **API**: `GET/POST /api/settings/ghost_mode`
- **Effect**: Dead players bypass the "skip turn" check in the agent engine, can move and observe (physical actions require DC 15 skill check)
- **System message**: Logged when toggled on/off

### Narration Mode

Controls narrative flavor text generation (see Narration System docs). Three states:

- `none`: Static descriptions only
- `player`: Player is prompted via modal to narrate
- `ai`: LLM generates narrative text automatically

### Auto-Generate Descriptions

When enabled (`auto_generate_descriptions: true`, default), equipping/unequipping items automatically rebuilds the character's appearance description. The setting lives on `app.world.auto_generate_descriptions` and is toggled via:

- **UI**: Checkbox in the Settings panel (Agent Behavior group)
- **API**: `GET/POST /api/settings/auto_generate_descriptions`
- **Effect**: When off, no description is regenerated on equip/unequip — both the backend fallback rebuild (in `engine/equipment.py`) and the frontend LLM call (in `runAction`) are skipped. The manual "🤖 Generate from Equipment" button in the inspector always works regardless of this setting.

### Turn-Based Mode

When enabled, the agent engine cycles through all characters in turn order instead of repeatedly acting for a single character. Sub-settings:

- `turn_order`: `sequential` (alphabetical), `random`, or `initiative` (d20 + DEX)
- **Reactive mode**: When on, agents use 3-phase think→act→react. When off, a single LLM call produces thought+speech+action+emote.

**Location note (task-250)**: the Turn-Based Mode toggle and Order dropdown live in the **left-panel Agents pane** (🎮 Turn Order group under the agent list), merged with the former initiative tab — not in the settings modal.

### Manual Mode

When enabled, the LLMClient returns a hardcoded manual response instead of making API calls. Used for debugging and testing LLM prompts without consuming API credits.

## Engine Config (task-304)

The settings modal also has a **⚙️ Engine Config** tab — a server-side tuning menu for the
engine's numeric constants (sound propagation, heat propagation rate, light spill). Unlike the
client-side settings above (IndexedDB), it persists to `data/engine_config.json` and applies
live without restarting the server.

- Backend: `engine/runtime_config.py` (`DEFAULTS` + overrides + `config.get()`), read at call
  time by `engine/sound.py`, `engine/environment_propagation.py`, `engine/lighting.py`.
- Routes: `GET/POST /api/settings/engine_config`, `POST /api/settings/engine_config/reset`.
- UI: `static/js/ui/engine-config-view.js` — lit-html, schema-driven; new keys appear
  automatically when registered in `DEFAULTS` + `SCHEMA`.

See [[Engine Config]] for the full key table, the "add a new tunable" recipe, and how
values flow into the engine.

## Agent Configuration from UI

The Settings panel (`static/js/ui/settings-view.js`) provides tabbed configuration:

### Connection Tab
- API Base URL (text input)
- API Key (password input)
- Model selector (dropdown + custom text input for local models)
- Temperature slider (0-2, displays current value)
- Max tokens (number input)
- Test Connection button — sends `Say "ok"` via LLM and reports success/failure

### Simulation Tab
- Reactive mode toggle (also: Ghost mode, Manual mode, RPM/TPM limits, Show Logs, Streaming)
- Turn-based mode + turn order moved to the left-panel **Agents pane** (task-250)

### Event Filters Tab
- Filter controls for: thoughts, speech, actions, system messages, raw LLM output
- Each filter controls which event types appear in the event log display

### Profiles
The settings system supports **named profiles** for storing different LLM provider configurations. Default profiles include:
- OpenAI (GPT-4.1-mini)
- OpenAI (GPT-4o)
- LM Studio (Local)
- DeepSeek
- Groq

### Embedding Tab
- Provider: **Local (sentence-transformers)** — built-in model loaded on demand, no API key needed
- Provider: **API (LLM Provider)** — uses your LLM provider's `/embeddings` endpoint
- Embedding Model (API mode): text input for model name (e.g. `text-embedding-3-small`, `text-embedding-qwen3-embedding-0.6b`)

The embedding source is persisted in IndexedDB and can be changed per session without restarting the server. `memory-store.js` respects the provider setting — API mode skips the server-side call entirely.

Profiles are managed via:
- `config.getProfiles()` — list all profiles
- `config.applyProfile(name)` — load a profile's settings
- `config.saveProfile(name, data)` — save to a profile
- `config.saveProfileFromCurrent()` — update current profile
- `config.saveProfileAsNew()` — create new profile from current settings
- `config.deleteProfile_()` — remove a profile

Profile data includes: `apiKey`, `apiBase`, `model`, `streaming`, `showLogs`, `turnBased`, `turnOrder`.

## Save/Load Configuration

### Saving (`config.saveFromForm()` at config.js:108)

Reads all form field values and persists via `config.save()` which writes to IndexedDB. Also:
- Syncs to current profile
- Updates `VW.llm` configuration
- Logs "Settings saved." to event stream

### Loading

Initial values are loaded from IndexedDB on page load via `ConfigManager._init()` → `_loadFromStorage()`.

### Profile Persistence

Profiles are stored separately from global config in IndexedDB's `profiles` store. The global `last_profile` key tracks which profile was last active. On page load, the last profile is automatically applied.

### World State Persistence

Game state (areas, players, items, etc.) is persisted via:
- **Save Game**: `_save_game()` in `routes/helpers.py:133` — full runtime snapshot to `saves/<name>_<timestamp>.json`
- **Save Scenario**: `_save_scenario()` in `routes/helpers.py:108` — strips play artifacts, saves authorial content to `data/scenarios/<name>.json`
- **Library**: Individual entity files in `data/library/<type>/<id>.json`

## Related tasks

- [[task-86-ux_ui_improvements|task-86: UX/UI improvements]]
- [[dev_tasks/todo/refactor/task-83-code_readability_refactor|task-83: Code readability refactor]]
