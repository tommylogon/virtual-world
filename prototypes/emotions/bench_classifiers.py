"""Head-to-head CPU benchmark of lightweight local emotion classifiers (0 VRAM).

Compares:
  1. SamLowe/roberta-base-go_emotions (125M RoBERTa, 28 GoEmotions classes)
  2. cirimus/modernbert-base-go-emotions (149M ModernBERT, 28 GoEmotions classes)
  3. knowledgator/gliclass-edge-v3.0 (33M zero-shot over our exact 13 Matrix families)

Runs all 6 ViWo emotion scenarios + 4 Millwood Scene 102 subtext cues on CPU
(zero GPU interference), measuring warm latency (median/p95 ms) and accuracy.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prototypes.emotions.proto_e_classifier import ProtoEClassifierEngine
from prototypes.emotions.scenarios import (
    run_scenario_d_jake_insult,
    run_scenario_goblin_soak,
    run_scenario_miki_taco_bell,
    run_scenario_subtle_sarcasm,
    run_scenario_tone_of_speech,
    run_scenario_worksheet_2a_pot,
)
from prototypes.emotions.schema import EmotionEvent, FAMILY_BASELINES
from prototypes.emotions.scene102_proof import build_scene102_world
from prototypes.emotions.viwo_adapter import ViwoEmotionHarness


def _eval_engine(label: str, eng: ProtoEClassifierEngine) -> Dict[str, Any]:
    # Warm-up load (not counted in per-call latency).
    t_load = time.perf_counter()
    eng.backend.classify("Warmup text.")
    load_s = round(time.perf_counter() - t_load, 2)

    latencies: List[float] = []
    checks: Dict[str, bool] = {}

    # 1. Scenario D (3-way insult)
    d = run_scenario_d_jake_insult(eng)["cases"]
    for c in d.values():
        latencies.append(c["latency_ms"])
    c1, c2, c3 = (
        d["trusted_partner_in_crowd"],
        d["hostile_stranger_alone"],
        d["exhausted_ashamed_partner_private"],
    )
    checks["scen_d_partner_hurt_and_shame"] = (
        c1["after_families"]["sadness"] > FAMILY_BASELINES["sadness"] + 15
        and c1["after_families"]["shame"] > c2["after_families"]["shame"]
    )
    checks["scen_d_stranger_anger"] = c2["after_families"]["anger"] > FAMILY_BASELINES["anger"] + 25
    checks["scen_d_inward_shame"] = c3["after_families"]["shame"] > c2["after_families"]["shame"]

    # 2. Miki Taco Bell (vulnerability + inertia + reassurance)
    m = run_scenario_miki_taco_bell(eng)["turns"]
    latencies.append(m["turn_1_trigger"]["latency_ms"])
    latencies.append(m["turn_2_reassurance"]["latency_ms"])
    checks["miki_fear_spike"] = m["turn_1_trigger"]["after_families"]["fear"] > FAMILY_BASELINES["fear"] + 18
    checks["miki_reassurance_calms"] = m["turn_2_reassurance"]["applied_deltas"].get("calm", 0) > 0

    # 3. Worksheet 2A (shame vs guilt)
    w = run_scenario_worksheet_2a_pot(eng)["steps"]
    latencies.append(w["step_1_shame_and_guilt"]["latency_ms"])
    latencies.append(w["step_3_check_facts_resolved"]["latency_ms"])
    s1 = w["step_1_shame_and_guilt"]
    checks["ws2a_shame_and_guilt_both"] = (
        s1["after_families"]["shame"] > FAMILY_BASELINES["shame"] + 15
        and s1["after_families"]["guilt"] > FAMILY_BASELINES["guilt"] + 15
    )

    # 4. Goblin soak (envy vs jealousy)
    g = run_scenario_goblin_soak(eng)["results"]
    latencies.append(g["skrit_envy"]["latency_ms"])
    latencies.append(g["vex_jealousy"]["latency_ms"])
    checks["goblin_envy_not_jealousy"] = (
        g["skrit_envy"]["after_families"]["envy"] > g["skrit_envy"]["after_families"]["jealousy"] + 15
    )
    checks["goblin_jealousy_not_envy"] = (
        g["vex_jealousy"]["after_families"]["jealousy"] > g["vex_jealousy"]["after_families"]["envy"] + 15
    )

    # 5. 4-case Speech Tone (under task-994 contract: tone=None is plain speech; sarcasm is tagged)
    st = run_scenario_tone_of_speech(eng)["cases"]
    for c in st.values():
        latencies.append(c["latency_ms"])
    checks["tone_teasing_warm"] = st["teasing_close_steady"]["after_families"]["happiness"] > FAMILY_BASELINES["happiness"] + 5
    checks["tone_teasing_mocking"] = st["teasing_while_ashamed"]["after_families"]["shame"] > FAMILY_BASELINES["shame"] + 20
    checks["tone_sarcastic_stings"] = st["sarcastic_subtle_tagged"]["after_families"]["anger"] > FAMILY_BASELINES["anger"] + 10
    checks["tone_warm_strained_leaks"] = st["warm_through_shaking_body"]["after_families"]["fear"] > FAMILY_BASELINES["fear"] + 8

    # 7. Millwood Scene 102 specific cues
    mw, _ = build_scene102_world()
    h = ViwoEmotionHarness(mw, eng)
    r_zoe = h.step_event(
        "kayla jenkins",
        EmotionEvent(
            kind="speech",
            summary="Zoe quietly asked about their impossible four-way future in Oklahoma.",
            source_name="zoe mercer",
            speech_text="But we can't, can we?",
            speech_tone="serious",
            tick=21,
        ),
    )
    latencies.append(r_zoe.latency_ms)
    checks["scene102_zoe_question_unease"] = (
        r_zoe.applied_deltas.get("fear", 0) > 2 or r_zoe.applied_deltas.get("sadness", 0) > 2
    )

    r_pads = h.step_event(
        "astrid lopez",
        EmotionEvent(
            kind="speech",
            summary="Jake nervously defended himself to Astrid by saying he brings the girls pads even when somebody bleeds on him.",
            source_name="jake halloway",
            speech_text="I treat them like people, I bring them pads even when somebody bleeds on me, I help with homework.",
            speech_tone="apologetic",
            tick=22,
        ),
    )
    latencies.append(r_pads.latency_ms)
    checks["scene102_astrid_pads_not_happy"] = (
        r_pads.applied_deltas.get("disgust", 0) > 0
        or r_pads.applied_deltas.get("anger", 0) > 0
        or r_pads.applied_deltas.get("fear", 0) > 0
    )

    passed = sum(1 for v in checks.values() if v)
    lat_sorted = sorted(latencies)
    p95 = lat_sorted[min(len(lat_sorted) - 1, int(len(lat_sorted) * 0.95))]
    return {
        "label": label,
        "load_s": load_s,
        "score": f"{passed}/{len(checks)}",
        "passed": passed,
        "total": len(checks),
        "median_ms": round(statistics.median(latencies), 1),
        "p95_ms": round(p95, 1),
        "failed_checks": [k for k, v in checks.items() if not v],
        "checks": checks,
    }


def main() -> None:
    candidates = [
        ("roberta-base-go_emotions (125M)", ProtoEClassifierEngine("SamLowe/roberta-base-go_emotions", backend_kind="go_emotions")),
        ("modernbert-base-go-emotions (149M)", ProtoEClassifierEngine("cirimus/modernbert-base-go-emotions", backend_kind="go_emotions")),
        ("gliclass-edge-v3.0 (33M zero-shot)", ProtoEClassifierEngine("knowledgator/gliclass-edge-v3.0", backend_kind="gliclass")),
        ("gliclass-modern-base-v3.0 (151M zero-shot)", ProtoEClassifierEngine("knowledgator/gliclass-modern-base-v3.0", backend_kind="gliclass")),
    ]
    results: List[Dict[str, Any]] = []
    for label, eng in candidates:
        print(f"\n>>> Benchmarking {label} on CPU...", flush=True)
        try:
            res = _eval_engine(label, eng)
            results.append(res)
            print(
                f"    score={res['score']} | median={res['median_ms']}ms | p95={res['p95_ms']}ms | "
                f"load={res['load_s']}s | failed={res['failed_checks']}",
                flush=True,
            )
        except Exception as exc:
            print(f"    ERROR: {exc}", flush=True)
            results.append({"label": label, "error": str(exc)})

    out_path = Path(__file__).resolve().parent / "classifier_benchmark_report.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved report to {out_path}")


if __name__ == "__main__":
    main()
