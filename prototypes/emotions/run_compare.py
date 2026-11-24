"""Side-by-side comparison benchmark runner for Prototypes A, B, and C.

Usage:
    python prototypes/emotions/run_compare.py                # live (LM Studio B+C if available)
    python prototypes/emotions/run_compare.py --offline      # zero-network hermetic run
    python prototypes/emotions/run_compare.py --track2       # also run live Track 2 Actor LLM
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
from prototypes.emotions.proto_b_semantic import ProtoBSemanticEngine
from prototypes.emotions.proto_c_dual_mind import ProtoCDualMindEngine
from prototypes.emotions.proto_d_unified import ProtoDUnifiedEngine
from prototypes.emotions.scenarios import (
    ALL_SCENARIOS,
    run_scenario_d_jake_insult,
)
from prototypes.emotions.schema import EmotionEvent, FAMILY_BASELINES
from prototypes.emotions.viwo_adapter import (
    ViwoEmotionHarness,
    add_emotional_memory,
    load_real_viwo_world,
)


def _top_shifts(applied: Dict[str, float], limit: int = 5) -> str:
    pairs = sorted(
        ((abs(v), k, v) for k, v in applied.items() if abs(v) >= 2.0),
        reverse=True,
    )[:limit]
    if not pairs:
        return "(none)"
    return ", ".join(f"{k} {v:+.0f}" for _, k, v in pairs)


def _top_auto(auto: Dict[str, float], limit: int = 4) -> str:
    pairs = sorted(
        ((abs(v), k, v) for k, v in auto.items() if abs(v) >= 15.0),
        reverse=True,
    )[:limit]
    if not pairs:
        return "(calm)"
    return ", ".join(f"{k}={v:+.0f}" for _, k, v in pairs)


def print_side_by_side(report: Dict[str, Any]) -> None:
    eng_keys = tuple(report["engines"].keys())
    print("\n" + "=" * 90)
    print(f"  VIRTUALWORLD EMOTION PROTOTYPES - SIDE-BY-SIDE COMPARISON ({' vs '.join(eng_keys)})")
    print("=" * 90)

    # 1. Scenario D highlight
    print("\n[1] SCENARIO D: 'Jake said: \"You're a bitch.\"' (3 Contexts)")
    for case_key in ("trusted_partner_in_crowd", "hostile_stranger_alone", "exhausted_ashamed_partner_private"):
        print(f"\n  Case: {case_key}")
        for eng_key in eng_keys:
            c = report["engines"][eng_key]["scenario_d"]["cases"][case_key]
            method = c["metadata"].get("method", "?")
            tiers = c["metadata"].get("tiers_used")
            tier_tag = f" tiers={'+'.join(tiers)}" if tiers else ""
            print(
                f"    [{eng_key}] ({c['latency_ms']:6.1f} ms | {method}{tier_tag}) "
                f"dom={c['dominant_family']:9s} portrait={c['portrait_expression']:12s} "
                f"overload={str(c['overloaded']):5s} | shifts: {_top_shifts(c['applied_deltas'])}"
            )
            print(f"        body: {_top_auto(c['autonomic'])}")
            print(f"        prompt: {c['prompt_your_state']}")
            print(f"        observer sees: {c['observer_tells_normal'] or '(masked/neutral)'}")
            if c["secondary_triggered"]:
                print(f"        secondary (Prompting Event 2): {', '.join(c['secondary_triggered'])}")

    # 2. Miki Doki on real taco_bell_date.json
    print("\n[2] MIKI DOKI ON REAL taco_bell_date.json (Cold + Hungry + Abandonment + Guarded Traits + Inertia)")
    for eng_key in eng_keys:
        t1 = report["engines"][eng_key]["miki_taco_bell"]["turns"]["turn_1_trigger"]
        i2 = report["engines"][eng_key]["miki_taco_bell"]["turns"]["after_2_ticks_inertia"]
        t2 = report["engines"][eng_key]["miki_taco_bell"]["turns"]["turn_2_reassurance"]
        floors = t1["metadata"].get("floors_applied") or []
        f_tag = f" floors={floors}" if floors else ""
        print(
            f"    [{eng_key}] T1 ({t1['latency_ms']:6.1f} ms{f_tag}) vuln={t1['vulnerability_load']:.2f} "
            f"cap={t1['regulation_capacity']:.0f} peak={t1['peak_arousal']:.0f} overload={t1['overloaded']} "
            f"| shifts: {_top_shifts(t1['applied_deltas'])}"
        )
        print(f"        secondary: {t1['secondary_triggered'] or '(none)'} | suppressed: {t1['suppressed_families']}")
        print(f"        body T1: {_top_auto(t1['autonomic'])} -> after 2 ticks: {_top_auto(i2['autonomic'])}")
        print(f"        T2 reassure shifts: {_top_shifts(t2['applied_deltas'])}")

    # 3. Worksheet 2A (Shame vs Guilt + Observer De-escalation)
    print("\n[3] WORKSHEET 2A: BURNED POT (Shame vs Guilt + Observer De-escalation + Check Facts)")
    for eng_key in eng_keys:
        s1 = report["engines"][eng_key]["worksheet_2a"]["steps"]["step_1_shame_and_guilt"]
        s2 = report["engines"][eng_key]["worksheet_2a"]["steps"]["step_2_observer_social_influence"]
        s3 = report["engines"][eng_key]["worksheet_2a"]["steps"]["step_3_check_facts_resolved"]
        floors = s1["metadata"].get("floors_applied") or []
        f_tag = f" floors={floors}" if floors else ""
        print(
            f"    [{eng_key}] S1 ({s1['latency_ms']:6.1f} ms{f_tag}) shame={s1['after_families']['shame']:.0f} "
            f"guilt={s1['after_families']['guilt']:.0f} | tilts={s1['disposition_tilts']}"
        )
        print(
            f"        S2 observer Rosa anger: {s2['rosa_anger_before']} -> {s2['rosa_anger_after']} "
            f"(deltas={s2['rosa_social_deltas']})"
        )
        print(
            f"        S3 after check-facts: shame={s3['after_families']['shame']:.0f}, "
            f"calm={s3['after_families']['calm']:.0f}, resolved_eps="
            f"{sum(1 for e in s3['episodes'] if e['resolved'])}/{len(s3['episodes'])}"
        )

    # 4. Kraktooth Goblin Soak (Envy vs Jealousy + Apathetic decay)
    print("\n[4] KRAKTOOTH GOBLIN SOAK: ENVY vs JEALOUSY + APATHETIC DECAY")
    for eng_key in eng_keys:
        res = report["engines"][eng_key]["goblin_soak"]["results"]
        sk = res["skrit_envy"]
        vx = res["vex_jealousy"]
        dk = res["after_5_ticks"]
        sk_rt = sk["metadata"].get("route") or sk["metadata"].get("method")
        vx_rt = vx["metadata"].get("route") or vx["metadata"].get("method")
        print(
            f"    [{eng_key}] Skrit ({sk['latency_ms']:5.1f}ms {sk_rt}) dom={sk['dominant_family']:8s} "
            f"(envy={sk['after_families']['envy']:.0f}, jealousy={sk['after_families']['jealousy']:.0f}) | "
            f"Vex ({vx['latency_ms']:5.1f}ms {vx_rt}) dom={vx['dominant_family']:8s} "
            f"(envy={vx['after_families']['envy']:.0f}, jealousy={vx['after_families']['jealousy']:.0f}) | "
            f"5-tick anger: norm={dk['skrit_anger']:.1f} vs apath={dk['dull_apathetic_anger']:.1f}"
        )

    # 5. Subtle Untagged Sarcasm (zero profanity, zero tags)
    if "subtle_sarcasm" in report["engines"][eng_keys[0]]:
        print("\n[5] SUBTLE UNTAGGED SARCASM ('Oh, you really tried your best... adorable. I'll redo it.')")
        for eng_key in eng_keys:
            r = report["engines"][eng_key]["subtle_sarcasm"]["result"]
            rt = r["metadata"].get("route") or r["metadata"].get("method")
            print(
                f"    [{eng_key}] ({r['latency_ms']:6.1f} ms | {rt}) dom={r['dominant_family']:9s} "
                f"portrait={r['portrait_expression']:10s} | shifts: {_top_shifts(r['applied_deltas'])}"
            )
            print(f"        appraisal: {r['gut_appraisal']}")

    # 6. Speech Delivery Tone (intended_tone -> subjective perceived_tone)
    if "tone_of_speech" in report["engines"][eng_keys[0]]:
        print("\n[6] SPEECH DELIVERY TONE (Intended -> Subjective Listener-Perceived)")
        for case_key in ("teasing_close_steady", "teasing_while_ashamed", "sarcastic_subtle_tagged", "warm_through_shaking_body"):
            print(f"\n  Case: {case_key}")
            for eng_key in eng_keys:
                r = report["engines"][eng_key]["tone_of_speech"]["cases"][case_key]
                rt = r["metadata"].get("route") or r["metadata"].get("method")
                ti = r["metadata"].get("speech_tone") or {}
                tone_str = f"{ti.get('intended_tone')}->{ti.get('perceived_tone')}"
                print(
                    f"    [{eng_key}] ({r['latency_ms']:6.1f} ms | {rt} | tone={tone_str}) "
                    f"dom={r['dominant_family']:9s} portrait={r['portrait_expression']:10s} "
                    f"| shifts: {_top_shifts(r['applied_deltas'])}"
                )

    if report.get("track2_live_demo"):
        print("\n[7] LIVE TRACK 2 ACTOR DEMO (Waking up inside Proto D Track 1's reacting body)")
        demo = report["track2_live_demo"]
        print(f"    Track 1 ({demo['track1']['engine_name']} | {demo['track1']['latency_ms']} ms | route={demo['track1']['metadata'].get('route')})")
        print(f"    Track 1 body prompt: {demo['track1']['prompt_your_state']}")
        print(f"    Track 1 observer sees: {demo['track1']['observer_tells_normal']}")
        t2 = demo["track2"]
        print(f"    Track 2 Actor ({t2.get('model')} | {t2.get('latency_ms')} ms):")
        print(f"      inner_monologue: {t2.get('inner_monologue')}")
        print(f"      speech:          {t2.get('speech')}")
        print(f"      after vocal brk: {t2.get('speech_after_involuntary')} (fired={t2.get('vocal_interruption_fired')})")
        print(f"      emote:           {t2.get('emote')}")
        print(f"      action:          {t2.get('action')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run side-by-side comparison of Emotion Prototypes A, B, C, and D.")
    parser.add_argument("--offline", action="store_true", help="Do not call LM Studio; use offline fallbacks.")
    parser.add_argument("--model", default="qwen3.5-4b", help="LM Studio chat model for Prototypes C and D.")
    parser.add_argument("--embed-model", default="text-embedding-nomic-embed-text-v1.5@q4_k_m", help="LM Studio embedding model for Prototypes B and D.")
    parser.add_argument("--track2", action="store_true", help="Also run a live Track 2 Actor LLM turn inside Track 1's body.")
    parser.add_argument("--json-out", default="", help="Optional path to save full JSON comparison report.")
    args = parser.parse_args()

    engines = {
        "A": ProtoAMatrixEngine(),
        "B": ProtoBSemanticEngine(model_id=args.embed_model, offline=args.offline),
        "C": ProtoCDualMindEngine(limbic_model=args.model, offline=args.offline),
        "D": ProtoDUnifiedEngine(
            embed_model=args.embed_model,
            limbic_model=args.model,
            offline=args.offline,
        ),
    }

    report: Dict[str, Any] = {
        "offline": args.offline,
        "limbic_model": args.model,
        "embed_model": args.embed_model,
        "engines": {},
    }
    for key, eng in engines.items():
        eng_results: Dict[str, Any] = {}
        for sc_name, sc_fn in ALL_SCENARIOS:
            eng_results[sc_name] = sc_fn(eng)
        report["engines"][key] = eng_results

    if args.track2:
        world = load_real_viwo_world("taco_bell_date")
        miki = world.players["miki doki"]
        miki.vitals["Temperature"] = 34.8
        miki.vitals["Hunger"] = 78
        miki.traits = dict(miki.traits or {})
        miki.traits["guarded"] = 1
        miki.fear_tags = list(set((miki.fear_tags or []) + ["abandonment"]))
        add_emotional_memory(
            miki,
            "Being left alone on the dark sidewalk at night after someone learned too much about me and walked away.",
            tick=0, importance=9, tags=["abandonment", "rejection", "trauma", "jake"],
            emotion={"label": "afraid", "intensity": 9},
        )
        d_eng = engines["D"]
        h = ViwoEmotionHarness(world, d_eng)
        evt = EmotionEvent(
            kind="speech",
            summary="Jake reached for her cold hand under the buzzing Taco Bell sign and asked her real name.",
            source_name="jake halloway",
            speech_text="Hey, you're shivering. Tell me your real name so I don't lose you.",
            tick=179,
            expectations=["Keep it casual, do not let him get close"],
            tags=["affection", "abandonment"],
        )
        t1 = h.step_event("miki doki", evt)
        t2 = d_eng.run_track2_actor(t1, evt, miki)
        report["track2_live_demo"] = {"track1": t1.to_dict(), "track2": t2}

    print_side_by_side(report)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nSaved full JSON report to: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
