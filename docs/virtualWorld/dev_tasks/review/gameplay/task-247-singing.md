# Task-247: Singing
**Status**: In Review — implemented 2026-08-31. New sing speech level (sound.py sound.speech_sing, default = say propagation), sing text command with output "[name] sings: ...", activity/block gate lists include sing, and the agent schema volume list mentions sing.

**Audit 2026-08-31** — NOT IMPLEMENTED; speech tiers stop at scream (sound.py _speech_levels), no `sing` verb. Effort S: volume tier + verb branch + agent schema entry.


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