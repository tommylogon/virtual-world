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

## Files

- `static/js/agent/turn-scene-view.js` — `buildPersonMenu`, nested/talk menus,
  area speech entries.
- `static/js/agent/human-turn-composer.js` — `_pendingSpeechTarget`, talk-volume
  handler, directed-whisper target, teach parsing.
- `static/js/agent/action-normalizer.js` — `wake`/`release` target cases.

