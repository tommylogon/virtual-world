---
type: task
status: done
area: ui
priority: high
wiki: "[[Settings]]"
related: ["task-909", "task-906"]
---

# task-910: Backend provider profiles and .env credentials persistence

**Filed:** 2026-10-30
**Related:** task-909, task-906, task-751

## What

Move LLM provider configuration and API profile persistence from volatile client-side browser IndexedDB to the backend:

1. **Backend Profile Management (`GET /api/profiles`, `POST /api/profiles`, `DELETE /api/profiles/<name>`):**
   - Parse credentials and base URLs directly from `.env` on disk:
     - `GOOGLE_GEMINI` (`GOOGLE_GEMINI_API_KEY`, `GOOGLE_GEMINI_BASE`, `GOOGLE_GEMINI_MODEL`)
     - `NVIDIA_NIM` (`NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_BASE`, `NVIDIA_NIM_MODEL`)
     - `GROQ` (`GROQ_API_KEY`, `GROQ_BASE`, `GROQ_MODEL`)
     - `MISTRAL` (`MISTRAL_API_KEY`, `MISTRAL_BASE`, `MISTRAL_MODEL`)
     - `OPENROUTER` (`OPENROUTER_API_KEY`, `OPENROUTER_BASE`, `OPENROUTER_MODEL`)
     - `ALIBABA` (`ALIBABA_API_KEY`, `ALIBABA_BASE`, `ALIBABA_MODEL`)
     - `Z_AI_GLM` (`Z_AI_GLM_KEY`, `Z_AI_GLM_BASE`, `Z_AI_GLM_MODEL`)
     - `LM Studio (Local)` (`http://localhost:1234/v1`)
   - Persist user-created custom profiles to a server-side JSON file (`data/config/profiles.json`, gitignored) rather than browser IndexedDB.
   - Serve merged profiles with clean single-provider names, eliminating the duplicate preset entries (`OpenAI 4.1-mini` vs `OpenAI 4o`, `DeepSeek` vs `DeepSeek V4 Pro`).

2. **Frontend `config.ts` and `settings-view.ts` Integration:**
   - Migrate `config.getProfiles()` to fetch from `/api/profiles` on load.
   - Migrate `config.saveProfileFromCurrent()` and `config.saveProfileAsNew()` to issue `POST /api/profiles`.
   - Migrate `config.deleteProfile_()` to issue `DELETE /api/profiles/<name>`.
   - Retain IndexedDB / localStorage solely as an offline fallback.

3. **Active Profile Synchronization:**
   - Persist `lastProfile` in `data/config/profiles.json` or server session so switching browsers or connecting via `127.0.0.1` vs `localhost` preserves the active provider.

## Why

API keys and profile configurations are currently stored exclusively in browser IndexedDB (`VirtualWorldDB` -> `profiles`). This causes critical data loss:
- Switching between `http://localhost:5000` and `http://127.0.0.1:5000` creates disjoint IndexedDB instances due to origin separation, wiping visible profiles.
- Clearing browser cache, cookies, or running in private browsing discards custom profiles.
- When IndexedDB returns empty, `config.ts` falls back to hardcoded factory presets, which redundantly define duplicate profiles for OpenAI and DeepSeek while discarding user keys for Groq, Mistral, Nvidia NIM, Google, and OpenRouter that already exist in `.env`.

Persisting profiles on the backend ensures credentials and profiles remain permanent, single-sourced, and independent of browser state.

## How

- Add a new route handler in `routes/profiles.py` (or `routes/settings.py`) registered in `app.py`:
  - Load environment variables using `python-dotenv`.
  - Read/write `data/config/profiles.json`.
  - Return combined profiles dictionary on `GET /api/profiles`.
- Update `static/js/config.ts`:
  - Replace direct `storage.getAllProfiles()` with an `ApiClient.getProfiles()` call.
  - Wire save/delete operations to server endpoints.
  - Clean up `_getDefaultProfiles()` to avoid hardcoded duplicates.
- Update `static/js/ui-controller.ts` and `static/js/ui/settings-view.ts` to refresh the profile dropdown from server state.
