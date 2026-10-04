---
type: task
status: todo
area: prompting
priority: high
---

# task-692: Narration v2: the DM layer is a client-side string rewriter, not a narrator

**Filed:** 2026-10-04
**Related:** task-593, task-400, task-661, bug-517, bug-518, bug-519

## Goal

Replace the `narration_mode` flag with a real DM layer that reads engine
perception, never contradicts it, and treats human narration as a
first-class mode rather than a text box.

## What exists today (measured 2026-10-04)

`static/js/narration-ui.ts` is 255 lines and is the whole system.

**It is not a backend feature.** `app.world.narration_mode` has exactly
three code paths in the repo: the `'none'` default in
`virtual_world_engine.py:66`, the setter in `routes/settings.py:279`, and
save/load in `engine/serialization.py:312,633`. **Nothing in `engine/`
reads it.** A count, not a grep impression — `rg -n "narration_mode"
engine/` returns 2 hits, both serialization. The simulation does not
change behavior based on this setting at all.

**The only live gate is one line in the agent loop**
(`static/js/agent-engine.ts:778`):

    if (narrationMode === 'ai' && config.apiKey && config.model) {

Three conditions. `config.apiKey`/`config.model` are browser-side LLM
keys, so narration silently no-ops when the active profile lacks them —
with no indication in the UI. The dropdown reads as a world-quality
switch; it is a per-action-result string substitution in one client path.

**The two gates disagree.** `room-context.ts:880` accepts
`!== 'none'` (so `player` mode works for room context);
`agent-engine.ts:778` accepts only `'ai'` (so **`player` mode never
fires for action results**). Player mode is half-wired.

**Narration replaces the description with prose the LLM invented.**
`_generateAINarration` sends `areaName`, `description`, item *names*,
character *names*, and exits — then the returned text overwrites the
`Description:` line via `contextString.replace(/^Description: .*/m, ...)`.
Everything that made the engine authoritative is discarded:
`engine/room_perception.py` is the declared ONE source of truth for what
a character can perceive (its docstring names four bugs that came from
re-implementing it), and narration bypasses it entirely. The narrator is
free to describe a door that is `requires: crawl`, a hidden item, or an
NPC that is not actually present.

**Player mode is a textarea with a prefill** built by naive template —
`` `You are in ${areaName}.` `` plus `You can see: ${items.join(', ')}`
— and whatever the human types becomes the description with no schema.

## Why this is not "add more prompt"

The prompts themselves are not the ceiling. `_generateAINarration`'s
system message is competent — second person, sensory detail, 2-4
sentences, don't list items mechanically. Adding adjectives does not fix
a narrator that is handed the wrong inputs and trusted with the output.

## The actual defect, visible in a real HTC log

Captured 2026-10-04 playing the mansion scenario. One action, three rows:

    🎭 sammy lopez  sammy lopez fumbles with the granola bar and takes a
                     hesitant bite, eyes darting around the dim foyer.
    ▶️ sammy lopez  eat granola_bar
    🔎 You          You eat the granola_bar.

**The same event is told three times, in two voices, with two
different actors.** The 🎭 row is flavor from
`static/js/agent/involuntary.ts` (task-166/534 — condition-driven
hiccups/shivers/stutters). The 🔎 row is the mechanical system result.
There is no narration in this trace at all: the LLM never ran, because
`config.apiKey`/`config.model` were unset, and nothing in the UI says so.
The badge reads "🔇 No Narration" as if narration were a choice rather
than an inactive wire.

And the 🔎 row is attributed to **You** on an action `sammy lopez`
performed. `turn-feed.ts:561` computes `isPlayer = !parsed.actor ||
parsed.actor === 'You' || parsed.actor === playerName`, and the engine's
result rows carry no actor, so every NPC result renders as if the human
did it. That is a separate defect from narration but it is in the same
trace and the same fix surface — narration returning a *structured*
result with a known actor is what makes both go away.

## The shape that fixes it

The user's model, which is the right one: **the system message is the
input to a director pass, and the director's output is the result the
player and the agent actually receive.** Not decoration stacked on a
mechanical result — a replacement for it.

    engine result (structured, actor + facts)
        │
        ├─ mode none    → render mechanical  ─┐
        ├─ mode player  → director + human edit ─┤→ ONE row: the narration
        └─ mode ai      → director pass       ─┘     + the facts, attached

Concretely, for `eat granola_bar` with a hidden `hunger` effect:

- **none** — `sammy lopez eats the granola bar. Hunger −12.`
- **ai** — `sammy lopez takes a hesitant bite, eyes still on the door.
  The stale-sweet taste of it does nothing for the gnawing in her
  stomach. (hunger −12)`

One row. One voice. The mechanical facts survive *inside* the prose
rather than beside it, so nothing is lost and nothing is said twice.

### Why one row and not two

Today `involuntary.ts` and `narration-ui.ts` are two independent prose
generators that both decorate the same action and never learn about each
other. The fix is that the **director is the only writer of flavor**.
`involuntary.ts` keeps its job — it is a condition→phrase table with no
LLM cost and it must stay cheap for background NPCs — but it becomes an
*input to* the director (the active conditions are facts the director
may use), not a parallel emitter that races it. One prose authority per
event.

## The finding that reframes the design: 582 success messages, 126 distinct

A full run export (`data/exports/mansion_...`, tick 6834, and the
2026-10-04 re-run) shows this result row:

    ▶️ kyrie johansen — use protein_bar
    ↳ kyrie johansen — ✓You use the protein_bar.
      you choke down the protein bar. it tastes like nothing, which is
      almost worse than tasting bad.

That second line is **not generated at runtime**. It is
`data/library/items/protein_bar.json` →
`triggers[0].effects[0].params.success_message`.

**Correction (2026-10-04): two earlier drafts got the provenance
wrong in opposite directions. Both are recorded here because the
corrected version is the one a future reader needs.**

*Draft 2 claimed all 582 are "hand-written" and should outrank
generated narration.* Wrong. Most of the volume is **string literals in
a batch generator**:

    tools/item_content_pass1.py:650   message="You eat it. Better than nothing and not much more."
    tools/item_content_pass2.py:339   message="You eat it. Better than nothing and not much more."
    tools/item_content_pass3.py:240   message="You eat it, gathered and not much cleaned."

Introduced by `b15786e8`, across `item_content_pass1`–`pass5`. No LLM
is in that loop.

*Draft 3 claimed none of them are authored.* Also wrong — the user
writes these, and uses AI to help design them.

**The reconciled measurement.** Splitting the distinct messages by
whether they appear verbatim in the generator scripts:

| | count |
|---|---|
| item files with a `success_message` | 557 |
| total message values | 582 |
| **distinct** values (incl. `fail_message`) | **139** |
| — of those, verbatim in a generator script | **8** |
| — **not** in any script (individually authored) | **131** |
| items where *every* message is script filler | **435** |
| items with at least one individually authored message | **122** |
| items whose only message is the single 216× template | **216** |

So the library is **two populations, not one**:

- **131 individually authored lines** — the real content. `"The lock
  clicks open and you see a book"`, `"Porcelain, tank, lever. It has
  witnessed things no employee is paid enough to scrub, yet..."`, the
  protein-bar line above. Hand-written or AI-assisted, either way
  **deliberate per-item voice**. These are the assets.
- **435 items carrying only batch filler**, dominated by one string at
  216×. Volume without voice.

The volume/dedup numbers from draft 2 still hold and are why "582
authored lines, don't overwrite them" was the wrong conclusion: 8
strings account for nearly all the repetition.

**Precedence to preserve, highest first:**
1. human override (persisted)
2. **individually authored** `success_message` / `fail_message` — the
   131 not present in any generator script
3. generated narration
4. batch filler — a message that appears verbatim in
   `tools/item_content_pass*.py`, or more than once in the library

**The authorship test is mechanical: a `success_message` that appears
verbatim in `tools/item_content_pass*.py` is filler.** That is a
greppable predicate, so assert it in a test rather than having the
director adjudicate at runtime. Assert the counts too (582 / 139 / 8),
so the split stays honest as the library grows.

**Do not "fix" the filler by generating over it.** 435 items would then
get a generated line, which at ~600 items/tick is a real cost for prose
nobody wrote. The cheaper correct answer is that the filler is *fine*
for a generic acorn and the interesting items are the 131 — v2's job is
to not damage the 131, and to let a GM replace filler deliberately.

This makes the GM payoff concrete: `player` mode is the only path that
can ever produce a *distinct* line for one of the 216 items whose sole
message is the repeated template, and today it discards it on reload. A
persisted override there is the highest-value edit available.

Note the *shape* trap this exposes: `success_message` lives at
`triggers[i].effects[j].params.success_message`, **not** at
`triggers[i].success_message` — which exists on the same trigger and is
**empty** (`protein_bar.json` has both, the outer one blank). Anything
reading the obvious location gets nothing.

## Two more defects this run exposed

**Narrator's editorial residue is stored in character memories.**
`miki`'s saved memory list contains, verbatim inside one memory's
`text` field:

    "...where she goes, i go.\n\nshorter, punchier, still sounds like
     miki rambling. keeps the asmr-brain moment, the fear, and the
     clinginess to elena all in one breath. the original had the right
     energy just needed the spelling fixed and the run-on tightened so
     it reads like nervous excitement instead of a typo soup."

That is a **rewrite note addressed to a reviewer**, not a memory. It is
in `data/scenarios/mansion.json` (not an export artifact — verified by
reading the saved `players.miki.memories[].text` directly), it is
`source: manual`, and it recurs in all three occurrences in the log. A
memory is first-person experience; this is second-person editorial
commentary about the memory. Whatever admits it does not distinguish
the two, so a character's recall can permanently contain its own
drafting notes — and it will be fed back into every future prompt.

**The result row is second person inside a third-person log.** The same
row reads `↳ kyrie johansen — ✓You use the protein_bar.` — actor named
in the gutter, then `You` in the text. The engine's authored message is
written to the acting character (`you choke down...`), which is right
for the agent prompt and wrong for a shared feed read by everyone.

Neither is strictly narration's fault, and both are in scope for a
director that owns the result row: a director returning
`{actor, narration, facts}` fixes the pronoun by construction, because
the text and the actor are produced together.

## The seven changes that would make it 10x better

Ordered by leverage. 1-3 are correctness; 4-7 are the actual 10x.

**0. A director pass that owns the result, not a post-processor.** This
is the structural change everything else hangs off. The engine's
structured output (actor, action, effects, deltas, outcome) enters a
director that returns **{narration, facts, actor}**. The event stream
renders one row. The agent prompt receives the narration *and* the
facts, because an agent that only sees prose cannot act on
`hunger −12`. Today `outputText = narratedText` throws the facts away
(`agent-engine.ts:782`) — the agent literally cannot see what happened
to its own character.

**1. Narration decorates perception; it never authors it.** The DM
should receive the *rendered perception block* — what
`room_perception.py` says this character can perceive — and be asked to
add atmosphere around a set of facts it may not contradict. The
mechanical description stays in the prompt as ground truth. Today's
`replace()` is the wrong verb; the narration should be an additional
layer, not a substitution.

**2. Give the DM the world's state, not just the room.** The prompt
gets a name and a comma list. The engine holds conditions, vitals,
relationships, memories, `recent_hearing`, world lore, time of day,
weather, and season. A DM that knows it is 2am in winter and the
character is hungry and has heard a rumor can write a sentence that
carries three facts at once. This is the single biggest quality jump
available and it is nearly free — the data already exists and is
already serialized.

**3. Respect the character's own voice and perception limits.** A
character who cannot see the back of the room does not get a description
of it. Narration should be downstream of perception filtering
(`task-467` belief/hearsay work is directly relevant), not upstream of
it.

**4. Continuity — a narrator with amnesia.** Every call is stateless:
no memory of what it said last turn, no thread. The same room
re-described five times produces five unrelated paragraphs. A DM
should hold a running state: what it has already described, what
matters, what it deliberately withheld. This is what separates a DM
from a text generator.

**5. Narration that changes the world, not just the text.** Today the
output is cosmetic — it lands in the event stream and is discarded.
The high-value version: narration *reports* consequences the engine
resolved (a failed pickpocket names the risk taken; a social failure
names the wrong read), and can surface engine state the mechanical
output omits. The memory-dynamics layer (`eed00a72`, tasks 685-691)
gives this something to narrate *about* — a character contradicting an
old memory is a story beat the DM can voice.

**6. Make `player` mode a real mode.** Today it is a blocking textarea
per room with a naive prefill, and it does not fire for action results
at all. As a first-class mode it should be: an editable draft the DM
pre-writes (so the human edits prose rather than authoring from
scratch), optional rather than modal-blocking, and able to express
*intent* ("she's lying", "he doesn't react") as structured input the
engine reads — which is the interesting thing a human DM can do that an
LLM cannot.

**The acceptance test for this is the cursed key.** The user's example:
picking up a cursed key should narrate as *"as his fingers touch the
cold metal, a coldness flows through his body"* — not *"jake picks up
key, trigger on pickup caused curse_xxx to be applied."* For a human DM
this must be **one step**: the draft is pre-written from the trigger's
own data, the human rewrites the prose, and the `curse_xxx` application
still happens mechanically and is still visible in the facts. The human
is not typing triggers; the human is writing the line. If a human DM has
to open a trigger inspector to narrate a pickup, the mode has failed.
That single interaction is the thesis of v2 and should be built first.

**7. One place decides, and it is legible.** The mode lives in three
places with two disagreeing gates and no UI indication of whether
narration is actually live. Whatever v2 is, the mode should be read in
one function, the gates should not disagree, and the UI should say
"Narration: AI (live)" vs "AI (no model configured — inactive)" rather
than a badge that lies.

## Non-goals

- Not a new engine subsystem. Narration stays a presentation layer.
- Not replacing `room_perception.py` — it is correct and is the thing
  narration should be deferring to.
- Not prompt-only. If the fix is "improve the system message," the
  ceiling is still the discarded context.
- **Not a replacement for the distinct `success_message` singletons.**
  They outrank generated narration — but they are a small minority. The
  repeated template filler does not, and preserving it would make v2
  worse, not better.
- Not a memory-quality project. The editorial-residue defect is filed
  separately — it is real, and it is not narration's to fix.

## Acceptance

**Structure — one row per event**

- An action produces exactly ONE event row, not the current three
  (🎭 involuntary + ▶️ action + 🔎 result). Assert the row count in a
  captured trace.
- The narration carries the actor, and the actor is correct: an NPC's
  action does not render as `You` (see bug-518).
- With narration `none`, the row is the mechanical result and it is
  unchanged from today's behavior.
- With narration `ai`/`player`, the row is the narration **and the
  mechanical deltas are still reachable** — assert the agent prompt
  contains the `hunger −12` style fact, not only prose. Today's
  `outputText = narratedText` drops it.

**Correctness**

- The director is given rendered perception (`room_perception.py`)
  and cannot introduce a fact absent from it — or the task states
  plainly which contradictions are accepted and why.
- `player` and `ai` modes are gated by the same code, and `player`
  mode fires for action results (today it does not).
- Regression test for bug-517 (narration must not reach
  `recent_hearing` as speech).
- Regression test for bug-518 (result rows must carry an actor).

**The cursed-key test — the one that decides whether v2 is real**

- Pick up a cursed key in `none` mode: the row reads mechanically and
  the `curse_xxx` trigger applies.
- Pick up the same key in `ai` mode: the row is prose describing the
  cold metal; the `curse_xxx` still applies; the fact survives.
- Pick up the same key in `player` mode: a draft is pre-written from the
  trigger's data, the human edits the prose in one step, and the
  trigger still applies. No trigger inspector is opened.
- If a human DM cannot narrate a pickup in one step, v2 has not landed.

**Precedence — the prose guard**

- An item whose `success_message` is **distinct** renders that text in
  `ai` mode. A test asserting the generated narration does not replace
  it. `data/library/items/protein_bar.json` is the fixture:
  `triggers[0].effects[0].params.success_message`.
- The test must read the message from `effects[].params.`, and must
  fail if it reads the empty outer `triggers[].success_message`
  instead — that field exists, is blank, and is the obvious wrong path.
- An item whose `success_message` is **batch filler** (appears
  verbatim in `tools/item_content_pass*.py`) is the one case where
  generated narration may replace it. Fixture: any item carrying
  *"You eat it. Better than nothing and not much more."* (216 items).
- Assert the authorship predicate itself — that count of messages
  appearing in the generator scripts is 8, and that the individually
  authored set is 131. A future content pass that genuinely improves
  filler should move those numbers, and the test should say so rather
  than fail mysteriously.
- Assert the ~435 filler-only items still get *a* line (the mechanical
  verb is acceptable) — v2 must not leave them blank, and must not
  pay an LLM call per generic acorn.
- A human override in `player` mode persists: reload the scenario and
  the edited text is still there. Today it is discarded on reload.
- An item with no `success_message` at all gets generated narration.

**Prose authority**

- Assert only one system writes flavor for a given event:
  `involuntary.ts` conditions appear inside the narration rather than
  as a parallel row that duplicates it.

**Live**

- Manual: play Kraktooth with narration on and confirm (a) narration
  fires, (b) it does not contradict hidden/locked/gated world state,
  (c) the same room re-entered reads continuously, (d) the UI says
  whether narration is actually live.
- Authored content: narration prompts that exercise world lore and
  character state must exist for Kraktooth, not just a generic default.

## Open questions

- Should narration be a per-character voice (the DM writes each
  character differently) or one consistent narrator voice? The former is
  stronger but costs a lot more tokens per tick.
- Where does narrated text live? Today it is written into the prompt
  context *and* separately logged, which is why bug-517 exists.
- Does the director run for background NPCs too, or only the attended
  LLM-agent set? `involuntary.ts` deliberately stays cheap for
  background NPCs; a per-action LLM call may not be affordable at that
  tier. If narration is attended-only, the cheap tier renders the
  mechanical row and that asymmetry must be visible in the UI rather
  than looking like a bug.
