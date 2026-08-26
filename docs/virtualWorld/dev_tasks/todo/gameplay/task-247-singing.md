# Task-247: Singing

**Status:** In backlog — filed 2026-08-16 from developer ideas backlog.
**Source:** `dev_tasks/developer ideas.md` (singing)

## Goal

Add singing as a character action — a distinct performative behaviour (vs plain speech/
emote) with its own volume/sound-carrier semantics so songs are heard at a distance and
characters can react to them.

## Notes / open questions

- New `sing` action with `{lyrics, volume}`; route through sound propagation
  (`engine/sound.py` barriers) like a shout/speak variant.
- Narrative framing: what the room describes ("a voice singing..."), and whether it maps
  to a skill check (Performance) or an emotion/intensity modifier.
- Join the COMMANDS table + action schema + prompt examples so LLM agents can sing too.