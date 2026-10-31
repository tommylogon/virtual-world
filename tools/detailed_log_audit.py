import sys, os, re, json
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

LOGS = [
    # Group 1: Taco Bell
    "taco_bell_event_log_2026-08-23T16-19-57.txt",
    "taco_bell_date_tick_87_event_log_2026-08-27T20-54-43.md",
    "taco_bell_date_tick_179_event_log_2026-09-04T10-24-48.md",
    # Group 2: Mansion
    "mansion_event_log_2026-08-23T15-04-54.txt",
    "mansion_tick_135_event_log_2026-09-06T21-06-40.md",
    "mansion_tick_6834_event_log_2026-09-07T23-26-55.md",
    # Group 3: Kraktooth
    "kraktooth_goblin_camp_tick_739_event_log_2026-09-20T10-05-04.md",
    "kraktooth_goblin_camp_tick_414_event_log_2026-09-21T22-02-58.md",
    # Group 4: Lyrie & Valerious
    "lyrie 28082026.txt",
    "the valerious case_tick_84_with_action_Economy_event_log_2026-10-11T13-02-17.md",
    # Group 5: August Baselines
    "event_log_2026-08-08T09-45-29.txt",
    "event_log_2026-08-10T21-45-19.txt",
    "event_log_2026-08-13T17-46-38.txt",
    "event_log_2026-08-27T11-59-17.txt",
    "event_log_2026-08-27T13-46-49.txt",
    # Group 6: Labs & Benchmarks
    "world_template_tick_613_event_log_2026-09-05T02-35-04.md",
    "soak-e31a7b0521c4.json",
    "export of diffrent local models responses",
    "Untitled-1.txt",
    "benchmark_elena_vance_2026-10-25T17-20-33.json"
]

def analyze_log_content(fname):
    fpath = os.path.join("data/exports", fname)
    if not os.path.exists(fpath):
        return {"file": fname, "error": "not found"}
    
    size = os.path.getsize(fpath)
    if fname.endswith(".json"):
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        return {"file": fname, "size": size, "type": "json", "summary": data.get("summary", {})}
    
    lines = []
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    # Character turn count
    char_turns = Counter()
    for l in lines:
        m = re.match(r"^##\s+Turn\s+\d+\s*[-–-]\s*([^\s\|]+(?:\s+[^\s\|]+)?)", l)
        if m:
            char_turns[m.group(1).strip().lower()] += 1
    
    # Look for specific bugs / keywords
    stalled_plans = [l.strip()[:140] for l in lines if "plan stalled" in l.lower()][:3]
    errors = [l.strip()[:140] for l in lines if "error" in l.lower() and not "payload" in l.lower()][:3]
    unconscious_lines = len([l for l in lines if "is unconscious" in l.lower()])
    
    # Check prompt size samples
    payload_lengths = []
    in_payload = False
    cur_payload = 0
    for l in lines:
        if "<details><summary>payload</summary>" in l:
            in_payload = True
            cur_payload = 0
        elif "</details>" in l and in_payload:
            in_payload = False
            payload_lengths.append(cur_payload)
        elif in_payload:
            cur_payload += len(l)
    
    avg_payload = sum(payload_lengths) // len(payload_lengths) if payload_lengths else 0
    max_payload = max(payload_lengths) if payload_lengths else 0
    
    return {
        "file": fname,
        "size": size,
        "lines": len(lines),
        "char_turns": dict(char_turns.most_common(6)),
        "stalled_samples": stalled_plans,
        "error_samples": errors,
        "unconscious_count": unconscious_lines,
        "payload_count": len(payload_lengths),
        "avg_payload_chars": avg_payload,
        "max_payload_chars": max_payload
    }

results = {}
for l in LOGS:
    res = analyze_log_content(l)
    results[l] = res
    print(f"Analyzed {l}: size={res.get('size', 0):,} lines={res.get('lines', 0)} turns={sum(res.get('char_turns', {}).values())}")

with open("data/exports/detailed_analysis.json", "w", encoding="utf-8") as out:
    json.dump(results, out, indent=2)
