## memory retrival logic 27.10.2026 
memory retrival (MR) is a massivly compex network of assosiations between current and past events. at its core memory retrival is attempting to answer the simple qustin of base don what si currently going on around me, what do i recall that will influence my next thought, speech or desicion. 

the problem i face in virtual world is the complete and complex model to use as the memory retrival query. exatly which part of the surrounding entities, or the characters own thoughts, should be used to fomr the retrival query. A chartcer will have countless assisiations to toher charatcers, their events, speech, items, areas, descriptins and connections, their wmotionals tate, the emotins tied to memory, the importance, age and frequency of the memory, and the current context of the character. and each of these factors will need to be split into the prose adn metadata, the enteties, and more date, to be used by either semantic search, keyword matches, multi step connections ebtween fdiffrent enteties, filtered by importance and many more factors without flooding the characters prompt with too much information. this then combined with the need for spatial memory (where something is, how to get ther,e how long ago you saw something), object permanence, how you remember items or places by assosiatin rather than direct need. how you tie the the bodys need for food into a query of where did you see food, if you dont ahve any memory of food then waht, do you remember where to find food, based on deduction? i dont ahve food so ill go to the fridge to see if it has anything, but if it is empty, do i go to the store? to a friend, look for a snack that i remember putting inmy room 2 weeks ago but cant remember having eaten? 

getting the balane right between correctly reacalling facts, patsh, locations, pesonal memories and not flooding the character, not giving them perfect memory or too fautly memory, to make them feel liek a real person, but not amnesiac, is a incredibly complex and delicate task. 
failure to recall recent, relevant and obvious facts or makign the charater act like they dont remember that they said or did something minutesa go, while makig them remember the most obscure and irrelevant fact from 3 years ago, is a very easy trap to fall into and instantly will break the illusion. 


currently....i ahv eno idea what is used. before a a cahracter gets teh descision prompt something pulls up to 10 memories from the characer. need to investigate that.
A properly designed model for structured memory query is required. based on current context, who said what, what items you spot, what recently happened, waht people said, did, what people look like, waht you or others are carrying, what you hear, what your body needs, what goals you have in your mind, hundreds of possible factors. importance, age and recalled, invalidated by help filter and weight the retrival?

some posible approaches for memory retrival:
1. LLM based summary of retrived memries. turn the retrived list of memories into natural prose that the character can use to make decisions. this is the most natural and human like approach, but also the most expensive in terms of compute and time. it also has the risk of hallucination, where the LLM may misinterpret or misrepresent the memories, leading to incorrect decisions. use a local llm as the memory model, splitting memory from the default model used elsewhere.
2. do recalling of memories like a tool call, or multipel tool calls, the agents mind will ask questions to the memory model that then does keyword adn semantic search, cross reference between enteties. the llm then itself decides what to try and recall, leading to a more relevant retrival, but looses the natural assosiations and invoulentary recollectin fo memories that humans naturally do. 
3. dual mind approach like in aura. the charatcer has a seperate thread of thought that uses the model memory to look at the current context and make a list of relevant memories, summaries, assosiatins that get fed to the main prompt.
4. using a graph based approach like graphiti, but without neo4j?

memories consist fo the prose, entity data and emtadata. 
prose: "jake told me he hates olives"
Entities: jake, olives
metadata: importance, age, frequency,, tags (food, etc) emotional state, context, location, etc.

it is inherintly graph friendly, ithink?

example situation. kayla order pizza and asks "hey jake, want olives with that"
recall asking "jake, olives, pizza, food" 

might recall 5 diffrent memories relating to olives, pizza, food, jake, kayla, and the context of the current situation. the memory model would then need to filter and rank these memories based on relevance, importance, and recency. it might recall that jake has previously expressed a dislike for olives, that he has ordered pizza with olives in the past but didn't finish it, and that he has a history of being picky about toppings.
then on kaylas reaction prompt she will then get the memory and go "oh no wait you hate olives, pussy" and then add to the recollection of that memory. 

might be usefull to split longterm and shortterm memory. 
longterm is more about the core personality, life altering events, childhood, trauma, hopes, dreams. more tied to feelings, assosiations, and identity. but also need to hold some facts, liek sammy would know where her house is as a long term memory, but she should not remember the exact detail of the first time she slammed a door in it. 

short term is the more imediate, situational, what happened lately. where you put things, what peopel said, what you saw or heard, but also maybe hold the data about what you just remembered. spesifics, relevance and detail are important here, i think?.


## memory 29.10.2026
long term memory might have more use of semantic search, emotional, formative evnts, but still needs data. but not all long term memories can be tied to entities, as they reference possibly events ovvuring years before the scenario started. might reference people that do not exist curretnyl, items that wont ever be made, places they never will return to. 

Another important piece is that memory corrupts, nostaliga, rewriting memories, false memories, assumptions, subjective believes, and the fact that the past is the past. memory is inherintly not objective, while a computer system needs objective facts to hook on to for data modifiation, retrival etc. 

Personality is basically the summary f your longterm memories, trauma and experiences.

Short term is more volatile, more prone to contridition, but holds more detail, maybe? 
memory query tupes:
semantic: take a piece of text and find matching text, cna be entity descriptions, trigger effects, spoken text.
Entity: find memories relate to another entity. name or another entity (charatcer, items, area or ways)
Keyword: take names or tags and find relevant memories with these tags
Emotion: query for memories related to ac ertain emotion.

filters:
importance: how important the memory is for the charatcer remembering it
relevance: semantic score
age: how long ago did the memory occur
recall count: how many times ahs this memory been remembered, higher means its more often on the characters mind
invalidation count / invalidation memory: has the memory been invalidated, when, why? 


do you remember the original memory, or the last time you remembered it? 
if Kyrie won a tournament when she was 11, that day liekly holds countless memories from low importance to the most important ones, like her dad cheering as she won, the fact that that she stubbed her to in the bathroom that morning has a importance of 2, what she remembers then is not the entirety of the day, but the memory she had the last time she thought about it, and then later she will remember the last time she remebered it agian. 

Orignal memory (maybe the summary of the entire day?) > recall 1 (days later remembering the summary of original memory) >recall 2 (years later, remembering the last summary, not the original summary. )

memory thus degrades over time, nostalgia effect basically.

memory is trying to answer questions about "what he says reminds me of ...", "that looks like...", "last time i did that..."
maybe remembering someone by apperance, not remembering their name, also needs the long term posibility of forgetting someones name if ht recalled?

to properly retrive relevant emories we might need to ask 10-15 questions prior to each prompt.

Memory is more than facts or reactions to situatoiuns. its assumptins, trauma, bias, prejudice, wants, dreams. and qustions.

the ability to create and retrive qustions leads to curiosity, having questoins be avswerable, like "who stole my gum?" leads to interigation, leads to suspicion, assumptins. "sammy is chewing gum, jake is a grabby little racoon. i bet jake gave sammy my gum." leads to so much more than "i remember owning a back of gum. it is now gone."

questions! that which is the foundation of curiosity, and by extention, soul 


---

## Architecture Audit & Agreed Direction (30.10.2026)

### 1. Audit of Current Runtime (`buildMemoryContext` + `/memories/retrieve`)

- **Current pre-prompt retrieval (`static/js/agent/prompt-builder/memory-context.ts`):**
  - Before each decision prompt, `PromptBuilder.buildMemoryContext(charName)` constructs a flat query string from only three inputs: `currentArea` (display name), `lastThought`, and the last 2 lines of `recent_hearing`.
  - Visible characters in the room, visible items and their descriptions/tags, carried items, active bodily needs/vitals, current emotion, and active plan steps are omitted from the query.
  - Three overlapping scorers run and merge: backend `POST /api/players/<name>/memories/retrieve` (`routes/memories.py`), a browser-side `.includes(word)` substring loop over `player.memories[]` (which pads up to 8 raw entries even at score `0`), and optional `EmbeddingClient` cosine search. Results are deduplicated by text and capped at `MAX_RECALL = 10`, with the top 3 kept unconditionally even below `MIN_RECALL_SCORE = 0.3`.
- **Existing subsystems already present in the engine:**
  - `engine/memory_dynamics.py` already persists `category` (`episodic`, `semantic`, `procedural`, `social`, `belief`), `activation` (`0..1` availability decayed per tick via `memory.decay_per_tick`), `reinforcements` and `last_recalled_tick` (recall count), `confidence`, mutual `contradicts` links (`detect_contradiction`), `reflection_depth`, `source_memory_ids`, and deterministic episode folding (`consolidate`).
  - `AgentMemory.reflect()` (`static/js/agent/memory-manager.ts`) runs every 5 character turns in reactive mode.
  - `Player.record_observation` / `record_scene_observation` (`player.py`) and `SpatialMemory` (`engine/spatial_memory.py`) maintain per-subject last-seen observations and BFS routes over visited/known areas.
  - `AgentMind.surface_need_memory` (`engine/agent_memory.py`) recalls food/water/sleep observations from vitals, but is currently called only from off-screen `engine/background_simulation.py`, not live foreground prompts.
- **Wiring defects identified during audit:**
  1. `memory-context.ts` synthesizes `current_area_id` via string formatting (`area_<slug>`) instead of passing the true graph node ID, missing hand-authored area IDs during `entity_boost`.
  2. `memory-context.ts` does not pass resolved `entities` or `emotions` to `/retrieve`; backend fallback splits `query` on whitespace, failing to resolve multi-word character and item names (`"jake halloway"`, `"pack of gum"`).
  3. `schema-fragments.ts` instructs the LLM never to put names, items, or places in `tags`, and `_sanitizeTags` (`memory-manager.ts`) strips any tag matching a world entity name while `storeMemory` defaults `entity_ids` to `[]`, dropping entity links from newly written agent memories unless relationship deltas resolve a person name.

---

### 2. Clarifications & Architectural Decisions

1. **Per-Character Associative Memory Graph (Separate from `WorldGraph`):**
   - `WorldGraph` remains strictly for physical world entities (areas, ways, items, characters).
   - Each `Player` maintains their own internal associative memory graph indexing memories across resolved world `entity_ids`, unbound backstory/concept references (people, places, or events from years prior that have no world node), tags, emotions, provenance (`source_memory_ids`), and `contradicts` links.

2. **Passive Associative Perception vs. Existing Deliberate Verbs:**
   - Passive pre-turn recall is unconscious and associative rather than question-driven: it builds structured multi-facet cues directly from perception (`roomContext` / visible people, items, tags, descriptions, carried items, heard dialogue, vitals/needs, and mood) and surfaces connected memories via association, semantics, and spreading activation.
   - Existing deliberate `recall` / `think` mechanics stay separate and unchanged.

3. **Authored Personality Stays Authoritative:**
   - The statement that personality summarizes long-term experience is a psychological framing, not a replacement for authored character `personality`. Character `personality` and persona properties remain intact; memories, beliefs, and emotional residue inform situational behavior alongside it.

4. **Dedicated Memory Model Setting:**
   - Add an optional dedicated Memory LLM configuration in Settings (separate provider/URL/key/model or shared provider with a separate model, following the same pattern as the semantic embedding model and reusing `LLMClient`).
   - Background LLM memory workflows (sleep/timeskip consolidation, reflection, question/hypothesis updates) run through this dedicated client so memory processing never bottlenecks or inflates the primary roleplay model.

5. **Segmented Prompt Lanes (Trial Replacing Flat Top-10):**
   - **Working Scene Buffer:** rolling short-term context of recent turns (recent speech, actions, and memories recalled on the prior turn to prevent mid-conversation amnesia).
   - **Spatial & Container Permanence:** last-seen item/container locations with staleness and explicit invalidation (e.g., checking an empty fridge invalidates that expectation and falls back to store priors or older stashed-item memories).
   - **Associative Recall (`0..6`):** top multi-facet associative matches above relevance threshold, with `0` allowed when nothing relevant connects (no zero-score padding).
   - **Open Questions (`0..2`):** active unresolved questions/suspicions triggered by current perception.

6. **Consolidation, Nostalgia Drift, and Two-Door Provenance:**
   - Keep `raw_fact` (immutable engine/inspector ground-truth anchor) available on experienced events while also keeping unanchored memories (`raw_fact: null`) valid for authored backstory, false memories, or pure subjective impressions.
   - Passive turn-by-turn retrieval updates `reinforcements` and `last_recalled_tick` without rewriting prose.
   - Compressing years of daily memories into layered summaries and applying subjective nostalgia drift (`Original -> Recall 1 -> Recall 2`) belongs to sleep/timeskip consolidation and emotional/social retellings (detailed multi-scale consolidation design to be covered in Pass 2).

7. **Questions as Proactive Free Actions:**
   - `category: "question"` (`"Who stole my gum?"`) is an active mental choice emitted as a zero-turn-cost free action (an optional side-channel field in the agent JSON turn response and a free action for human turns, consuming neither major nor minor turn budget).
   - Open questions act as standing perceptual tripwires that match incoming sightings, emotes, and dialogue against watched entities/concepts, driving proactive suspicion, interrogation, and eventual resolution into beliefs.


---

## Pass 2: Grounded Audit & Architectural Synthesis (01.11.2026)

Based on direct inspection of production runs (`data/exports/Millwood_tick_1-3188_event_log_2026-10-30T22-16-47.json`, `data/sandbox_autosave.json`, `data/exports/mansion_tick_6834_event_log_2026-09-07T23-26-55.md`) and the 2026 research literature (APEX-MEM, VoiceMem, HeLa-Mem, Anchor Engine, MRAgent). Full measured metrics are recorded in `docs/live-audit/2026-11-01-memory-export-audit.md`.

### 1. Concrete Ground-Truth Failures Measured in Live Exports

Inspection of raw runtime prompts and export logs revealed five specific failure mechanisms currently breaking agent memory and conversation:

1. **Client Override Breaks Lane Budgeting:**
   - The engine defines a budget of `max_results=6` (`engine/memory_retrieval.py:607`) with zero padding allowed.
   - However, `static/js/agent/prompt-builder/memory-context.ts:304` hard-codes `max_results: 10`.
   - Result: In the Millwood run, 39 of 60 recall events returned exactly 10 memories. The lane was flooded on every single turn.
2. **False Contradiction Storm from Coarse Entity Matching:**
   - In `data/sandbox_autosave.json`, 125 of 244 memories (51%) carry `contradicts` links across 414 unique pairs.
   - 405 of these 414 pairs satisfy the rule in `memory_dynamics.detect_contradiction` because the shared-entity check is satisfied by room node IDs (e.g. `area_cafeteria`). Any two memories created in the same room with negation asymmetry trigger a mutual contradiction.
   - Example from Jake: *"Searched my backpack for the anonymous love note but couldn't find it"* was linked as contradicting *"Found anonymous crimson gel pen note in bag"*. This is a chronological state transition, not an epistemological contradiction.
   - In Jake's prompt at tick 2, 6 of the 9 recalled memories were flagged with `(⚡ this conflicts with another memory)`.
3. **Temporal Invalidation Window is Unwritten:**
   - While `memory_retrieval.is_active_memory` correctly checks `invalid_at` and `superseded_by`, 0 of the 244 memories in the save had either field set.
   - The engine has no automated mechanism to expire previous world states when new facts supersede them.
4. **Verbatim Conversational Repetition Despite Anti-Repeat Prompts:**
   - In Millwood, Jake asked: *"hey guys, real quick - does anyone have a crimson gel pen? like, on them right now? i need to know if someone's carrying one, seems sketchy."* verbatim on both tick 1 and tick 2.
   - Inspection of Jake's tick 2 prompt shows `=== CONVERSATION ===` did contain his prior statement under *"You recently said:"*, alongside the instruction *"Do not repeat a line you already said"*. The LLM completely ignored the prompt negative constraint.
   - Furthermore, `Player.memories` records 0 memories of type `speech` (by design in `Memory System.md`). The agent's episodic memory substrate holds zero record of its own spoken queries, preventing associative retrieval from surfacing past dialogue commitments.
5. **No Questions Generated:**
   - The save holds 0 memories under `category: "question"`. The free-action path for proactive curiosity formulated in Pass 1 was never invoked in practice.

### 2. Architectural Answers from the 2026 Research Corpus

The research papers gathered in `research/` address these exact failure modes without requiring external graph databases:

* **Append-Only Validity Intervals (APEX-MEM arXiv:2604.14362):**
  - Solves the "could not find note" vs "found note" conflict. Instead of marking contradictory statements, fact mutations must write `invalid_at = current_tick` to the superseded memory.
  - Historical facts remain in the database for long-term narrative consistency, but drop out of active associative recall.
* **Separation of Factual World from Affective Persona (VoiceMem arXiv:2608.26005):**
  - Informational Left Brain ($G_L$): entities, physical locations, item containment, and causal sequences.
  - Affective Right Brain ($G_R$): independent traits ($V^I$) and cross-entity attitudes ($V^C$).
  - Prevents emotional surges (e.g. Jake's paranoia about the note) from being treated as factual contradictions against physical observations.
* **In-Process Deterministic Retrieval (Anchor Engine & HeLa-Mem):**
  - Traversal over local adjacency lists and Hebbian co-activation weights. Eliminates multi-turn LLM query planning while preserving sub-millisecond retrieval speeds.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply`  -  relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes**  -  [[Commands]], [[Emotion & Mood — Whole-System Analysis]], [[Feature Ledger]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]]

<!-- connected:end -->
