---
type: task
status: review
area: ui
priority: high
---

# task-610: Human turn modal exposes 3 of ~23 backend character-to-character actions

**Filed:** 2026-09-30
**Related:** [task-602]

## Goal

The HTC person menu offers only Talk to / Examine / Attack. The backend supports ~23: attack, approach, grab, release, escape, lead, give, steal, name, teach, shout, whisper, scream, sing, wake, relieve, plus 8 intimate verbs in engine/pleasure_actions.py (kiss, lick, suck, bite, caress, pinch, blow, tickle) each with an authored default body region, plus the grapple subsystem with per-hand targeting. 8 of those verbs are body-part-targeted, so they depend on the same region mechanism task-602 fixes.

## Acceptance

- [x] The person chip menu exposes the person-directed verbs, not just three:
  Talk to / Whisper to / Examine / Attack / Grab (grapple) / Lead / Wake /
  Release, **Escape** when the character is grappled, **Give…** (submenu of
  what you are carrying → `give <item> to <name>`), **Teach…** (submenu of
  known abilities → `teach skill:<name> to <name>`), and **Intimacy…** (all 8
  verbs from `pleasure_actions.py`) shown only when `world.mature_content` (or
  the client flag) is on.
- [x] Room-level speech volumes are on the **area** chip (Say / Shout / Scream)
  and person-directed **Whisper to <name>** sets the composer's whisper volume
  *and* recipient.
- [x] The person menu is an affordance, like the way menu: every entry drafts
  text the server validates; the person target still resolves through
  `matching.py` (masked stranger labels draft fine).
- [x] Menus that need an argument the menu cannot know are deliberately not
  offered: **steal** (needs an item from the target's inventory, which the
  scene does not expose) and **name** (needs a free-text alias). Both remain
  typeable in the composer. **approach** is movement, not person-interaction,
  and already has a home in the way menu / typed box.
- [x] `action-normalizer.js` gains `wake`/`release` cases: previously the target
  was silently dropped, so `{action:'wake',item:'X'}` normalized to bare `wake`.
- [x] Directed whisper survives the human composer: `normalizeReply` carries
  `target` for `volume==='whisper'`, and agent-engine's existing `_speakLine`
  turns it into `whisper to <target>: <text>` (task-248).

## Verification (live browser, 2026-10-02)

`VW_PORT=4463`, Playwright. Real scene fetched via `TurnSceneView.fetch`, one
fixture person added, then real clicks on chips/menu entries.

```
PERSON_MENU_COUNT 10 (mature off, +1 while carrying, +1 while known)
PERSON_MENU ["Talk to Tester","Whisper to Tester","Examine Tester","Attack Tester",
  "Grab Tester (grapple)","Lead Tester","Wake Tester","Release Tester",
  "Give… (2)","Teach… (2)"]
TALK_CAPTURED [{"volume":"whisper","target":"Tester"}]
GIVE_SUB   ["‹ back","Dagger","Bread"]   GIVE_DRAFT -> draft "give Dagger to"+"Tester"
TEACH_DRAFT -> "teach skill:Swordsmanship to"+"Tester"
INTIMACY_HIDDEN_WHEN_OFF true
INTIMACY_SHOWN_WHEN_ON true
INTIMACY_SUB ["‹ back","Kiss","Caress","Lick","Suck","Bite","Pinch","Blow","Tickle"]

Composer (HumanTurnComposer.request, real panel):
VOLUME_ON ["whisper"] FOCUS htc-speech
WHISPER_PREVIEW {"speech":"meet me at midnight","volume":"whisper","target":"Tester"}
SAY_PREVIEW     {"speech":"meet me at midnight","volume":"say"}   (target cleared)
GIVE_DO_FIELD "give Dagger to Tester"
GIVE_PREVIEW  {"action":"give","item":"Dagger","target":"Tester"}
```

Screenshots: `review-verify/610-menu-top.png` (whole menu open),
`review-verify/610-intimacy-sub.png` (submenu),
`review-verify/610-composer-whisper.png` (whisper volume + directed target in
the payload preview).

## Follow-up (2026-10-02): speech audience, reviewed with the user)

Reviewing the whisper path against the current sound propagation showed the
volume→audience mapping was only half-specified, so it was checked and corrected:

- **`engine/speech.py` — a directed whisper now has a defined audience.** It was
  target-only (task-248). It now also reaches anyone standing in the same area
  who is a **friend or better** with the speaker (`WHISPER_EAVESDROP_BAND`,
  reusing the `closeness_band` ladder in `engine/relationships.py` so the two
  cannot drift). A stranger at the same table still hears nothing, and nothing
  crosses a wall (whisper penetration is already 0). The event records
  `whisper_audience`. An undirected whisper stays room-wide — that existing
  contract is unchanged.
- **Menu wording made the distinction real.** "Talk to X" was misleading: it set
  no target, so it was a room-wide line that merely sat under someone's name.
  The person menu now offers **Whisper to X** (directed) and **Say aloud
  (everyone hears)** (undirected) as two explicit choices.
- **`Speak…` kept as an option.** It focuses the speech row *without* changing
  the selected volume — "just let me say something" is distinct from picking a
  volume, so `talkFocus` is live again rather than dead.
- **`teach` added to `parseCmd`'s `VERBS`.** The Teach submenu drafts
  `teach skill:X to Y`; without the verb listed, `parseCmd` returned it as speech
  and the give/steal/teach split was unreachable. Found by review, not by the
  earlier live pass, which only captured the raw draft.

Live check (`VW_PORT=4463`, Playwright, real clicks):

```
PERSON_MENU ["Whisper to Tester","Say aloud (everyone hears)","Examine Tester",
  "Attack Tester","Grab Tester (grapple)","Lead Tester","Wake Tester","Release Tester"]
WHISPER_PREVIEW {"speech":"the vault code is 4417","volume":"whisper","target":"Tester"}
SAY_PREVIEW     {"speech":"anyone listening?","volume":"say"}
AREA_MENU ["Examine the room","Look around","Listen","Speak…","Say it to the room","Shout","Scream"]
VOL_BEFORE_SPEAK ["shout"] -> SPEECH_FOCUS_VOL_UNCHANGED ["shout"] (FOCUS_IS_SPEECH htc-speech)
```

Engine (new `TestWhisperAudience`, 6 tests):
`python -m pytest tests/test_realism_perception.py -q -> 23 passed`
(target hears; stranger does not; a friend does; an acquaintance does not; the
event names the audience).


## Files

- `static/js/agent/turn-scene-view.js` — `buildPersonMenu`, nested/talk menus,
  area speech entries.
- `static/js/agent/human-turn-composer.js` — `_pendingSpeechTarget`, talk-volume
  handler, directed-whisper target, teach parsing.
- `static/js/agent/action-normalizer.js` — `wake`/`release` target cases.

