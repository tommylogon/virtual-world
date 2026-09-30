---
type: task
status: cancelled
area: characters
priority: medium
related: [task-593, bug-514, task-599, task-601]
---

# task-600: No data authors the structured personality shape (likes/dislikes/fears), so the mechanic is wired but unreachable

**Filed:** 2026-09-30
**Related:** task-593, bug-514, task-599

## Goal

engine/character_appearance.py reads a structured personality object with likes, dislikes, fears, kinks and turn_offs (PERSONALITY_FIELDS at :51, consumed at :146, :364, :383, :414) and tests cover it, but every character in data/ authors personality as a plain prose string instead - all 23 Kraktooth characters, and the library characters. The mechanic is implemented, wired and tested but no content can reach it, so it is untested in the simulation. Two things to settle: author the structured shape for a representative character or two so the wired mechanic can actually occur, and decide how the prose-string and structured-object forms of the same field are meant to coexist.

## Observed 2026-09-30: the Generate button produces exactly the unusable shape

Pressing **Generate from Personality** in the inspector does not fail and does not
report anything. It writes a persona, and the persona reads as generic — which is
the *symptom* of this task, not a separate one. Four defects, each traceable:

1. **The response schema forbids the useful shape.**
   `static/js/shared/json-schemas.js:154` declares `personality` as a **strict**
   schema of exactly two nullable strings: `{personality, description}`. The model
   is therefore *required* to compress an entire character into one prose blob, and
   prose is what reads as adjective soup. There is no field for a fear, a motive or
   a contradiction, so none can appear. The shape `character_appearance.py` reads
   — `fears`, `likes`, `dislikes`, `kinks`, `turn_offs`, each a list of tag **ids**
   — has no slot here at all.

2. **The prompt asks for nothing usable.**
   `static/js/inspector/agent-view.js:1338` is the whole instruction: *"You are a
   character designer. Generate a personality based on the prompt. Respond with
   ONLY raw JSON: {personality: 'Detailed character personality, fears,
   motivations, quirks.'}"* It names fears and motivations and then provides no
   place to put either.

3. **`temperature: 0.9`** (`agent-view.js:1344`) for a first draft that is saved
   permanently and — per the comment at :1471 — *"feeds EVERY prompt forever and is
   seen by other characters"*. High temperature is "surprise me" on the one output
   nobody can undo. The variety belongs in the prompt; the sampler should be cool.

4. **No context, and a silent bad fallback.** The call gets one line of user
   prompt and nothing else — no name, no role, no setting, no existing
   description — so it reaches for the nearest stock archetype. Worse,
   `agent-view.js:1353` is `parsed.personality || 'A mysterious character.'`: a
   model that returns nothing usable **silently** writes a clichÃ© over the
   character, with no error and no log. That is a failure the author cannot
   distinguish from a good result, and it is worth fixing regardless of everything
   else here.

**The authoring path already exists and is nearly right.** `_generateInterestTags`
and `_generateFearTags` (the same file) fetch `/api/tags/search`, show the model
both the world-in-use and the library vocabularies, and write ids onto
`interest_tags` / `fear_tags`. The personality button is the odd one out: it
invents prose where its siblings write ids.

## Decisions to make before implementation

1. **Does the prose `personality` field stay?** It feeds every prompt (task-345)
   and is what a person reads in the inspector, so removing it is a regression.
   *Recommendation: keep prose **and** add the id lists beside it.* The prose is
   the voice; the lists are the mechanic, and they are read by different code. The
   thing that must be settled is what happens when they disagree — and the honest
   answer is that they cannot, because the ids are generated *from* the prose in the
   same call, so the lists are a mechanical reading of the paragraph and never a
   separate claim about the character.
2. **Which id vocabulary?** `fears` feeds `engine.fear fear_tags`, which uses the
   same id vocabulary as the tag library — so the ids must come from that
   vocabulary and be validated against it, or a rename orphans every fear in the
   world. **This is blocked on task-601**, which has not settled whether a tag id
   may contain `:` and spaces (the data does; the declared pattern allows
   neither). Validating ids against a charset that is about to change is building
   the validator twice, so 601 answers this first. `kinks`/`turn_offs` may not
   have a vocabulary at all yet; check before asking for ids.
3. **Does this task absorb bug-514?** It does not reproduce — the button is not
   silent when no LLM is configured; `agent-view.js:1333` toasts *"Configure API
   key and model in Settings first."* bug-514's premise was wrong; its narrower
   case (no key) is already handled. Leave it filed unless that reading is wrong.

## Acceptance

- [ ] **The strict `personality` schema carries the id lists** — `fears`,
      `likes`, `dislikes` at minimum — alongside the existing prose fields, so the
      shape the engine reads has a slot in the response. `kinks`/`turn_offs` only
      if decision 2 finds them a vocabulary.
- [ ] **The prompt names the fields it wants populated** and does not mention
      fears and motivations while providing nowhere to put them.
- [ ] **Ids are chosen from the real vocabulary**, by the same route the interest
      and fear generators use (`/api/tags/search`, world-in-use plus library), and
      **validated** before they are written, so a rename cannot orphan them. Invented
      ids are dropped, and the drop is visible.
- [ ] **`temperature` is lowered** to roughly 0.7, with the note that the output is
      permanent.
- [ ] **The call receives context** — name, role, existing description — so it is
      not inventing a stranger.
- [ ] **The `'A mysterious character.'` silent fallback is gone.** An unusable
      response is an error with a visible message and **no write**, because the
      current behaviour overwrites a hand-authored character with a clichÃ© and calls
      it success.
- [ ] **The prose field still works.** Whatever is decided in decision 1, a
      character with only prose keeps loading and keeps feeding prompts.
- [ ] **At least one Kraktooth character and one library character carry the
      structured shape in `data/`**, so the mechanic is exercised by real content
      and not only by tests.
- [ ] `tests/test_templates.py`-style template coverage still passes, and the
      schema change is reflected in whatever validates strict schemas.

## Notes

- This is the reason the mechanic is untestable in play: a fear needs an id, an id
  needs a vocabulary, and every generator that would supply one currently writes
  prose. Nothing downstream is wrong — `character_appearance.py` and `engine/fear.py`
  are correct and covered.
- The sibling generators (`_generateInterestTags`, `_generateFearTags`) are the
  template for all of this and should not be rewritten in passing; the only thing
  they lack is the personality side.
- `bug-514` was filed from the same session on the premise that the button failed
  silently. It did not — see decision 3.

## Cancellation — the finding is refuted

Cancelled 2026-09-30. `GET /api/state` shows **all 3 players in the loaded world
carry a fully-authored `personality`**, and it is substantial prose rather than a
placeholder:

- **Kaelen Voss** -- "you are Kaelen Voss, A Human who is a Disgraced Investigator
  for the Galser Office of Justice ... Formerly a rising star in the Ulus of
  Galser's bureaucratic machine, you were exiled after you refused to hand over a
  'magical item of interest' ... your left leg clicks with a clockwork prosthetic"
- **Lyrie** -- a 79-year-old elven maiden, with Personality / Mind sections
- **rat** -- "A scruffy brown rat with bright, clever eyes and twitching whiskers."

`personality` is present on 3 of 3 players, so nothing is `[]` and nothing is
left unpopulated. The second half of the original claim also misdescribes the
field: `personality` is a **string** (prose handed to the prompt), not a
structured shape, so "no data authors the personality shape" does not describe
the thing at all.

This is the ninth finding in the live audit retracted after checking it against
the running app rather than against the markup.