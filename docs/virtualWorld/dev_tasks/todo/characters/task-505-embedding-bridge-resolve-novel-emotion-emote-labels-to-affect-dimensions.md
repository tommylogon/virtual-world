---
type: task
status: todo
area: characters
priority: medium
---

# task-505: Embedding bridge: resolve novel emotion/emote labels to affect dimensions

**Filed:** 2026-09-24
**Related:** task-350, task-96

## Goal

When an agent/game event declares a feeling or emote whose label is not in engine.emotion.LABEL_TO_DIM, resolve it semantically to the nearest affect dimension via the configured embedding provider (LM Studio, browser EmbeddingClient) and post {mapped:{dim:delta}} to /api/players/<name>/emotions/map, instead of the current graceful no-op. Keeps creative LLM vocabulary from being silently dropped, so events/decisions translate into the affect map and therefore select the correct expression portrait.

## Acceptance

- TODO
