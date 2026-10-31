import os
import re
import json
import glob

EXPORT_FILES = [
    "event_log_2026-08-08T09-45-29.txt",
    "event_log_2026-08-10T21-45-19.txt",
    "event_log_2026-08-13T17-46-38.txt",
    "mansion_event_log_2026-08-23T15-04-54.txt",
    "taco_bell_event_log_2026-08-23T16-19-57.txt",
    "event_log_2026-08-27T11-59-17.txt",
    "event_log_2026-08-27T13-46-49.txt",
    "taco_bell_date_tick_87_event_log_2026-08-27T20-54-43.md",
    "lyrie 28082026.txt",
    "taco_bell_date_tick_179_event_log_2026-09-04T10-24-48.md",
    "world_template_tick_613_event_log_2026-09-05T02-35-04.md",
    "mansion_tick_135_event_log_2026-09-06T21-06-40.md",
    "mansion_tick_6834_event_log_2026-09-07T23-26-55.md",
    "kraktooth_goblin_camp_tick_739_event_log_2026-09-20T10-05-04.md",
    "kraktooth_goblin_camp_tick_414_event_log_2026-09-21T22-02-58.md",
    "soak-e31a7b0521c4.json",
    "export of diffrent local models responses",
    "Untitled-1.txt",
    "the valerious case_tick_84_with_action_Economy_event_log_2026-10-11T13-02-17.md",
    "benchmark_elena_vance_2026-10-25T17-20-33.json"
]

def analyze_file(fname):
    fpath = os.path.join("data/exports", fname)
    if not os.path.exists(fpath):
        return {"error": "File not found", "file": fname}
    
    size_bytes = os.path.getsize(fpath)
    
    # Check JSON files separately
    if fname.endswith(".json"):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            return {
                "file": fname,
                "size_bytes": size_bytes,
                "kind": "json",
                "keys": list(data.keys()) if isinstance(data, dict) else f"list({len(data)})",
                "summary": data.get("summary", {}) if isinstance(data, dict) else {},
                "models": data.get("summary", {}).get("models_evaluated", []) if isinstance(data, dict) else []
            }
        except Exception as e:
            return {"file": fname, "size_bytes": size_bytes, "kind": "json_error", "error": str(e)}

    # Parse text / markdown logs
    line_count = 0
    ticks = []
    turns = []
    characters = set()
    speech_count = 0
    inner_monologue_count = 0
    rejections_count = 0
    actions = {}
    telemetry_leaks = []
    
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_count += 1
            # Ticks
            m_tick = re.search(r"\[Tick\s+(\d+)", line)
            if m_tick:
                ticks.append(int(m_tick.group(1)))
            
            # Turns
            m_turn = re.search(r"Turn\s+(\d+)\s*-\s*([^\s\|]+(?:\s+[^\s\|]+)?)", line)
            if m_turn:
                turns.append(int(m_turn.group(1)))
                characters.add(m_turn.group(2).strip().lower())
            
            # Actor lines e.g. **Elena Vance** - act
            m_act = re.search(r"\*\*([^*]+)\*\*\s*-\s*act\s*.*?([a-zA-Z_]+)", line)
            if m_act:
                char_name = m_act.group(1).strip().lower()
                verb = m_act.group(2).strip().lower()
                characters.add(char_name)
                actions[verb] = actions.get(verb, 0) + 1
            
            # Speech
            if "says:" in line or "whispers:" in line or "shouts:" in line or '"speech":' in line:
                speech_count += 1
            
            # Inner monologue
            if "inner_monologue" in line:
                inner_monologue_count += 1
                # Check for telemetry leaks in inner monologue
                if re.search(r"(?:thirst|hunger|sanity|energy|bladder)\s*(?::\s*|\bis\b\s*)\d+", line, re.I):
                    telemetry_leaks.append(line.strip()[:150])
                elif re.search(r"choices:\s*activity", line, re.I):
                    telemetry_leaks.append(line.strip()[:150])

            # Rejections & failures
            if "plan stalled" in line or "error" in line.lower() or "rejected" in line.lower() or "invalid" in line.lower():
                rejections_count += 1

    max_tick = max(ticks) if ticks else 0
    max_turn = max(turns) if turns else 0

    return {
        "file": fname,
        "size_bytes": size_bytes,
        "line_count": line_count,
        "kind": "log",
        "max_tick": max_tick,
        "max_turn": max_turn,
        "characters": sorted(list(characters))[:10],
        "character_count": len(characters),
        "speech_count": speech_count,
        "inner_monologue_count": inner_monologue_count,
        "rejections_and_errors": rejections_count,
        "top_actions": sorted(actions.items(), key=lambda x: x[1], reverse=True)[:8],
        "telemetry_leak_samples": telemetry_leaks[:3]
    }

if __name__ == "__main__":
    results = []
    for f in EXPORT_FILES:
        res = analyze_file(f)
        results.append(res)
        print(f"Parsed {f}: size={res.get('size_bytes', 0):,} bytes, kind={res.get('kind')}")
    
    with open("data/exports/batch_analysis_results.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)
    print("Saved all results to data/exports/batch_analysis_results.json")
