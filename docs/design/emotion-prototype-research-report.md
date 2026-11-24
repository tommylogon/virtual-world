# VirtualWorld Emotion System Prototype & Live Evaluation Research Report

**Date:** 2026-11-21
**Scope:** Empirical evaluation of five Track 1 emotion appraisal architectures (Prototypes A, B, C, D Unified, and E Local CPU Classifiers), the shared Coupled Emotional Matrix + 8-Channel Autonomic Body physics, subjective speech delivery tone (`task-994` / `task-996`), and unscripted multi-actor live stress tests grounded in real VirtualWorld scenarios (`taco_bell_date.json`, `Millwood.json`, and the `millwood` story archive Scene 102).

---

## 1. Executive Summary

1. **The Winning Production Architecture:**
   - **Track 1 (Reactive / Involuntary Mind):** Tier 1 deterministic structural guards (`<1 ms`) fused with **`cirimus/modernbert-base-go-emotions`** (149M, CPU-only, **`0` VRAM**, **`86 ms` median**), feeding the **Coupled 13-Family Emotional Matrix** (projected onto VirtualWorld's existing 36-dimension affect map) and the **8-Channel Non-Voluntary Autonomic Body** with physiological inertia.
   - **Measured Result:** **`14 / 14 (100%)`** across all VirtualWorld emotion scenarios, speech-tone perception splits, and Millwood Scene 102 cues, with **zero generative LLM calls in Track 1**, **zero VRAM contention** with the Actor LLM or user GPU workloads, and **~85x lower latency** than running a 9B generative LLM per listener (`~65-86 ms` vs. `5,000-6,900 ms`).
   - **Optional Spotlight Subtext:** Only when world-lore subtext cannot be inferred from sentence emotion + tone alone (e.g., an innocent word like `"married"` being a shock to a specific character), qualitative intensity bands (`slight / mild / moderate / strong`, never raw numbers) can piggyback onto the existing cue-gated Memory Intermediator (`_synthesizeConsciousThought`) for the active speaker only (`0` new LLM calls).
   - **High-Volume Soak Alternative:** `knowledgator/gliclass-edge-v3.0` (33M zero-shot, **`22.5 ms` median** on CPU, `0` VRAM, `12/14` accuracy) provides a 3.8x faster CPU option for background soak NPCs.

2. **Key Design Invariants Proven Empirically:**
   - **No separate `emotion_myths` property:** Expression suppression, secondary emotions (e.g., `fear -> shame/anger`, `cover_lie -> guilt`), and calming resistance emerge cleanly from existing VirtualWorld state (`persona.personality` traits, recalled `Player.memories`, and `event.witnesses`).
   - **No generative LLM touching raw emotion numbers:** Letting a generative LLM output raw numeric deltas caused `qwen/qwen3.5-9b` to emit 2x-7x larger deltas than `google/gemma-4-e4b` on identical 5-word input (`fear +38` vs. `+18`; `shame +55` in one turn), pushing characters into premature dissociation. Moving Track 1 to calibrated classifier probabilities (or qualitative bands mapped by Python) guarantees model-independent emotional pacing.
   - **Speech delivery tone is an explicit channel, not mind-reading:** Under `task-994` and `task-996`, `tone=None` is plain speech. Non-neutral `intended_tone` (`warm`, `teasing`, `sarcastic`, `cold`, `hostile`, `serious`, `apologetic`, `guarded`) is filtered per listener through speaker involuntary strain, listener moodiness, closeness, Insight (`WIS`), and spatial proximity (`same_area`, cross-area `distance`, intra-room `proximity_hops`).

---

## 2. Architectures Evaluated

All five prototypes ran against the exact same shared physics core (`prototypes/emotions/coupling.py`, `prototypes/emotions/autonomic.py`, `prototypes/emotions/schema.py`) and real VirtualWorld `Player`, `WorldGraph`, `SpeechBroadcaster`, `engine/sound.py`, `engine/speech_tone.py`, and 7-channel `engine/memory_retrieval.py`:

| Prototype | Track 1 Mechanism | Hardware / VRAM | Typical Latency | Strengths | Weaknesses |
|---|---|---|---|---|---|
| **Proto A** (`proto_a_matrix.py`) | Deterministic structural rules | CPU (`0` VRAM) | `0.4 ms` | Exact hard floors (betrayal, guilt/shame, envy/jealousy, fear_tags, tone guards) | Blind to unscripted phrasing without tags |
| **Proto B** (`proto_b_semantic.py`) | Local embeddings (`nomic-embed` / `qwen3-embedding`) vs. 65 DBT anchors | LM Studio embed | `29.4 ms` | Catches unseen phrasing without LLM cost | Embeddings struggle with negation and subtle sarcasm |
| **Proto C** (`proto_c_dual_mind.py`) | Pre-Actor generative Limbic LLM (`gemma-4-e4b`, `qwen3.5-9b`, `lfm3-1.7b`) | GPU VRAM | `1,500 - 6,900 ms` | Reads deep world-lore subtext against recalled memories | Slow (~22s/turn for 4 listeners); raw numeric deltas vary wildly by model size |
| **Proto D** (`proto_d_unified.py`) | Tri-Tier A + B + cue-gated C | GPU + Embed | `15 ms` (soak) / `4,500 ms` (spotlight) | Smart routing (0 LLM on soak/goals; Tier 1 hard floors prevent LLM drift) | Still pays 4-6s per spotlight listener on local GPU |
| **Proto E** (`proto_e_classifier.py`) | Tier 1 Guards + Local CPU Emotion Classifier (`ModernBERT` / `RoBERTa` / `GLiClass`) | **CPU-only (`0` VRAM)** | **`22 - 86 ms`** | **100% (14/14) on `modernbert-base-go-emotions`**, 0 VRAM, 0 JSON failures, model-independent scale | Does not know secret world-lore subtext without Memory Intermediator context |

---

## 3. Benchmark 1: Four-Way Local CPU Emotion Classifier Comparison (`0` VRAM)

All four lightweight classifiers were benchmarked head-to-head on CPU (`device=-1` / `device="cpu"`, zero GPU impact) via `prototypes/emotions/bench_classifiers.py` across 14 checks covering Scenario D (3-way `"You're a bitch"`), Miki Taco Bell (cold/hungry vulnerability + abandonment recall + reassurance), Worksheet 2A (shame vs. guilt split), Kraktooth Goblin Soak (envy vs. jealousy split), 4-case Speech Tone (`teasing` warm, `teasing -> mocking` misread, `sarcastic` tagged, `warm -> strained` leak), and two Millwood Scene 102 cues (`"But we can't, can we?"` and Astrid's `"Pads."` reaction).

Full machine-readable output: `prototypes/emotions/classifier_benchmark_report.json`.

| Model | Params | Type | Score | Median Latency | p95 Latency | Cold Load | Failed Checks |
|---|---|---|---|---|---|---|---|
| **`cirimus/modernbert-base-go-emotions`** | **149M** | 28-class GoEmotions | **14 / 14 (100%)** | `86.2 ms` (`72.0 ms` idle) | `111.8 ms` | `1.27 s` | **None** |
| `SamLowe/roberta-base-go_emotions` | 125M | 28-class GoEmotions | `13 / 14 (93%)` | `55.0 ms` | `73.3 ms` | `1.3 s` (cached) | `scene102_astrid_pads_not_happy` |
| `knowledgator/gliclass-edge-v3.0` | 33M | Zero-shot 13 custom labels | `12 / 14 (86%)` | **`22.5 ms`** | **`31.6 ms`** | `1.61 s` | `tone_teasing_warm`, `tone_sarcastic_stings` |
| `knowledgator/gliclass-modern-base-v3.0` | 151M | Zero-shot 13 custom labels | `12 / 14 (86%)` | `97.3 ms` | `147.9 ms` | `15.79 s` | `tone_teasing_warm`, `tone_warm_strained_leaks` |

**Multimodal Models Checked (Not Benchmarked for Text-Only Loop):**
- `StarJiaxing/R1-Omni-0.5B`: Inspected HuggingFace `config.json` -> uses custom `HumanOmniQwen2ForCausalLM` architecture (`HumanMLLM/R1-Omni` repo + video/audio pipeline), not standard `transformers`. Better suited for future multimodal voice/video input than text-only turns.
- `AffectGPT` / `EmoLLM`: Require custom multimodal stacks or 7B+ generative weights; superseded for text-only Track 1 by `cirimus/modernbert-base-go-emotions` (`86 ms`, `0` VRAM, `100%`).

---

## 4. Benchmark 2: Live Multi-Actor Millwood Scene 102 Stress Tests

To verify real emergent behavior beyond single-turn unit tests, `prototypes/emotions/scene102_proof.py` loads real characters (`zoe mercer`, `sammy lopez`, `kayla jenkins`, `kyrie johansen`, `jake halloway`) directly from `data/scenarios/Millwood.json` alongside `astrid lopez` (24, Dallas) and `maria lopez` (45, Bay 2) from the `millwood` archive, placed in two open-connected outdoor `WorldGraph` areas (`Gravel Driveway by Gerald` and `Dessert Tables (Bay 2)` with `noise="normal"`).

Only Turn 0 is seeded (`Zoe whispers seriously to Kayla: "But we can't, can we?"`). Turns 1 through 6 run completely unscripted with strict epistemic isolation (Kayla & Kyrie hold Tuesday/Wednesday memories; Sammy & Zoe do not; Astrid and Maria hold zero secrets).

### 4.1 Comparison Across Live Runs

| Run | Track 1 Engine | Track 2 Actor LLM | Track 1 Median / Listener | Checks Passed | Blank Dissociations (Turn 6) | Notable Emergent Outcomes |
|---|---|---|---|---|---|---|
| **Run 1 (Pre-Fix)** | Proto D (`gemma-4-e4b`) | `gemma-4-e4b` | `~4,500 ms` | `7/8` | 4/4 girls | Exposed 3 real bugs (see Section 5): additive autonomic runaway (`72/100` off a whisper), `"..."` silence broadcast spiral, and pink-elephant prompt leak. |
| **Run 2 (Tuned Physics)** | Proto D (`gemma-4-e4b`) | `gemma-4-e4b` | `~4,600 ms` | `7/8` | **0/6** | Astrid's Turn 2 `teasing` split into `teasing` (Sammy/Kyrie) and `mocking` (Kayla/Zoe); Kayla traced her scarred eyebrow and shut Astrid down cold; Turn 5 Kayla calmed Zoe (`calm +11, fear -5`). |
| **Run 3 (9B LLM)** | Proto D (`qwen3.5-9b`) | `qwen3.5-9b` | `~5,800 ms` | **`8/8`** | 2/4 girls (Sammy, Zoe) | **Every mechanic fired live:** Turn 1 Sammy tried to `whisper`, hit `flustered_volume_slip` (`whisper -> normal`), blurted out `"sneaking into a guy's bedroom"`; Astrid recalled Mrs. Arredondo's gossip; Turn 6 Astrid shouted Jake's name across the yard (`cross-area d=2.75`), Sammy heard `strained` while Maria heard `serious` and froze in surprise. |
| **Run 4 (CPU Classifier)** | **Proto E (`roberta-base-go_emotions` CPU)** | `qwen3.5-9b` | **`65 ms` (85x faster)** | `7/8` | **0/6** | Zero runaway spikes (`Sammy fear +4`, `Kayla fear +9`, `Kyrie neutral` on Turn 0); Zoe hit `flustered_volume_slip` on Turn 3; Turn 5 Kayla `serious` split into `strained` (Zoe/Sammy/Kyrie) vs. `serious` (Astrid). Missed only Astrid's lore-specific shock on `"get married"` (read as `happiness +14`). |

Full untruncated JSON transcripts and telemetry are saved in:
- `prototypes/emotions/scene102_proof_report.json` (Run 2 - `gemma-4-e4b` before dissociation tuning)
- `prototypes/emotions/scene102_proof_report_tuned.json` (Run 2b - `gemma-4-e4b` after dissociation/body-ladder tuning)
- `prototypes/emotions/scene102_proof_report_qwen9b.json` (Run 3 - `qwen/qwen3.5-9b` 8/8 pass)
- `prototypes/emotions/scene102_proof_report_classifier.json` (Run 4 - CPU classifier Track 1 + `qwen3.5-9b` Track 2)

---

## 5. Critical Engineering Bugs Discovered & Resolved During Live Testing

1. **Windows `localhost` IPv6 2,000 ms Stall:**
   - Python `urllib` hitting `http://localhost:1234` incurred a 2,000 ms IPv6 `::1` fallback timeout per request on Windows. Switching to `http://127.0.0.1:1234` dropped local embedding latency from `2,055 ms` to `15 - 37 ms` (70x speedup).
2. **LM Studio Thinking-Model Leakage (`{` JSON Prefill Discovery):**
   - LM Studio ignored `enable_thinking: false` and `reasoning.exclude: true` on `google/gemma-4-e4b` and `lfm3-1.7b@q4_0`.
   - Production `LLMClient`'s `suppressLocalThinking` (`{role: "assistant", content: " "}`) sped up `lfm3-1.7b` (`22.6 s -> 3.0 s`) but caused `gemma-4-e4b` to dump its reasoning outline into visible `content`.
   - Prefilling `{role: "assistant", content: "{"}` on JSON calls dropped `reasoning_content` to `0` on both models (`lfm3-1.7b`: `22.6 s -> 1.26 s`; `gemma-4-e4b`: `27/27` clean JSON).
3. **Autonomic Linear Summation Runaway (`autonomic.py`):**
   - Summing autonomic targets linearly across 13 families caused 4 mild emotions (`fear=28, sadness=33, shame=31, surprise=50`) to sum to `heart_rate=72, breathing=72, muscle_tension=72` off a single 5-word whisper.
   - Replacing linear summation with a **dominant + diminishing-returns blend** (`1.00 * top1 + 0.30 * top2 + 0.12 * top3 + 0.05 * top4`, separated by sign on signed channels) plus **saturation damping** above `45` in `coupling.py` eliminated runaway cardiac-arrest spikes.
4. **Close Confidants Misclassified as Public Humiliation Witnesses (`coupling.py`):**
   - Treating every same-area witness as hostile public pressure caused secondary `fear->shame` and `sadness->shame` to double-fire inside a private huddle of best friends (`closeness >= 82`). Filtering `outside_witnesses` (`closeness < 60`) and capping secondary shame chains to one per step fixed the runaway spiral.
5. **Dissociation Gate & Body-Prompt Ladder (`coupling.py`, `autonomic.py`):**
   - Raising the protective dissociation gate from `overload_streak >= 4, peak >= 82` to `overload_streak >= 6, peak >= 88` and widening `heart_rate` into 3 prose bands (`28` flutter / `48` fast pulse / `72` hammering) dropped Turn 6 blank-outs from `3/4` girls to `0/6` on `gemma-4-e4b` and `0/6` on CPU Classifier Track 1.
6. **Spatial Proximity in Speech Tone (`task-996`, `engine/speech_tone.py`, `engine/speech.py`):**
   - `perceive_speech_tone()` now accepts `same_area`, cross-area `distance`, and intra-room `proximity_hops` (from `engine/character_spatial.py`), wired directly from `SpeechBroadcaster._append_hearing_entry()`. Close same-area listeners catch micro-strain and sarcasm; cross-area listeners hear casual cover lines at face value unless the speaker is outright overloaded at `distance == 1`.

---

## 6. Production Shipped vs. Queued Tasks

**Already Implemented & In `review`:**
- `task-994`: Speech delivery tone (`intended_tone -> perceived_tone`) across backend Python (`engine/speech_tone.py`, `engine/speech.py`, `engine/narration.py`, `virtual_world_engine.py`, `routes/action_handlers.py`) and frontend TypeScript (`#htc-tone`, `room-context.ts`, `agent-engine.ts`).
- `task-995`: Removed prototype-only `emotion_myths` and derived suppression/secondary emotions strictly from existing `persona` traits, memories, and witnesses.
- `task-996`: Added spatial proximity (`same_area`, `distance`, intra-room `proximity_hops`) to `perceive_speech_tone()` and `SpeechBroadcaster._append_hearing_entry()`.
- `task-997`: Added per-target live emotion overlays, `persona` habit/quirk tell hooks, and flustered volume slip in `prototypes/emotions/`.
- `task-998`: Built and verified the live 6-character Millwood Scene 102 proof harness (`prototypes/emotions/scene102_proof.py`).

**Queued Production Follow-Up Tasks:**
1. Add sarcastic banter option to zero-LLM background soak conversations (`engine/background_social.py`).
2. Use assistant `{` JSON prefill in production `LLMClient` `suppressLocalThinking` (`static/js/llm-client.ts`).
3. Integrate Coupled Emotional Matrix, 8-channel autonomic body, per-target overlays, `persona` tells, flustered volume slip, and optional CPU `cirimus/modernbert-base-go-emotions` classifier into production (`engine/emotion.py`, `player.py`, `engine/autonomic.py`, `engine/emotion_classifier.py`, `room-context.ts`, `involuntary.ts`, `mind-view.ts`).
