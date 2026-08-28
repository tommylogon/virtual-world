# Relationship interpretation - prompt mockup (task-350)

> What this shows: the same moment from a real run, before and after the proposed change.
> The core rule: the recipient decides how a line landed - the speaker intent is irrelevant.
> The model outputs a discrete bucket (no raw numbers); the engine owns the number via an authorable table.

---

## 1. Today - the recipient just gets the raw lines, no interpretation

    [Tick 21 | 19:20]
      - a human turn for miki doki -

    === WITNESSED ===
    jake halloway says (to the room): you have got this, please stay
    tyler says (to miki): hey, can you move - you are blocking the counter

    === YOUR STATE ===
    You are shaking and your stomach is gnawing at you. You feel uneasy.

    What do you think, say, and do?

> Problem: nothing asks how it landed on you. The engine would apply a flat +2 for any speech
> (or nothing), so a nasty line and a sweet line move the relationship identically. And a speaker
> self-declaring a tone is wrong - a creep calling himself flirty must not charm the recipient.

---

## 2. Proposed - inject a WHAT YOU HEARD block into the recipient inner monologue

    [Tick 21 | 19:20]
      - miki doki receives lines from jake and tyler -

    === WHAT YOU HEARD ===
    - jake halloway said: you have got this, please stay
    - tyler said: hey, can you move - you are blocking the counter

    For EACH line, decide how it landed on YOU (not how it was meant).
    Pick ONE bucket per person: big_negative | minor_negative | no_change | minor_positive | big_positive.
    The engine applies the delta - you do NOT pick a number.

    === YOUR STATE ===
    You are shaking and your stomach is gnawing at you. You feel uneasy.

    What do you think, say, and do? Respond in your voice, then give your read.

### The recipient response - words plus one tiny structured field

    {
      inner_monologue: jake actually thinks I can do this, that almost made me feel like a real person for a second. Tyler is just annoyed and I get it, but being snapped at while I am already melting is the last thing I need.
      emote: hunches smaller, hugs the tray to her chest

      interpretation: {
        jake halloway: minor_positive,
        tyler: minor_negative
      },
      reason: jake believing in me actually helped; tyler snapping just made the pit in my stomach worse.
    }

> So the recipient feelings, not the speaker claim, drive the change. miki is already uneasy and fragile,
> so tyler snap is minor_negative even though he probably did not mean it harshly. And jake kindness lands
> minor_positive because she is starved for it.

---

## 3. The engine maps bucket to number (authorable, you tune it)

| bucket | delta |
|---|---|
| big_negative | -6 |
| minor_negative | -2 |
| no_change | 0 |
| minor_positive | +2 |
| big_positive | +4 |

> The model never emits these numbers. It picks the bucket; the engine applies the mapped value and clamps.
> A single line cannot spike anything - buckets are small and the delta is clamped. Missing/invalid bucket -> no_change (0).

---

## 4. The creepy-to-kid case - why subjectivity matters

    creep leans in: hey cutie, you look like you need a ride home
      -> jessica (13, scared, already on edge) reads it as:  big_negative  ->  -6
      (her word for it: i felt sick and i wanted the floor to swallow me)

    the same words, said by a friend she trusts, might read:  no_change / minor_positive
      (her word for it: ok that is weird but it is just jimmy being jimmy)

> The difference is entirely the recipient. The same sentence moves closeness differently depending on
> who said it and how the recipient feels about them - exactly what a recipient-POV read captures, and
> what a speaker-declared tone could never do.

---

## 5. Memory tie-in (your note: it is really a memory thing)

> The reason plus the felt emotion write an emotion-tagged memory (task-96 emotional residue), so
> how that made me feel persists. Later recall of that person re-surfaces the feeling, not just the fact.

    memory: { text: tyler snapped at me for blocking the counter and my stomach dropped - i felt small,
              importance: 4, tags: [tyler, shame, anxiety], emotion: {label: sad, intensity: 5} }
