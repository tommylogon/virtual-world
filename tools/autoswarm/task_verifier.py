"""tools/autoswarm/task_verifier.py - Non-destructive task verification runner.

Strictly READ-ONLY by default.
1. Evaluates acceptance checkboxes.
2. Extracts and executes real test suites (pytest, node, npm).
3. Produces a detailed human sign-off dossier with real execution timings and logs.
4. NEVER moves a file to done unless explicit --move or --sign-off is specified.
Zero em-dashes anywhere in this file.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def parse_card(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    card_id = path.stem.split("-")[0] + "-" + path.stem.split("-")[1]

    checked = re.findall(r"- \[[xX]\]", text)
    unchecked = re.findall(r"- \[ \]", text)

    steps_section = ""
    pos = text.find("## Steps to verify")
    if pos != -1:
        end_pos = text.find("## ", pos + 10)
        steps_section = text[pos:end_pos] if end_pos != -1 else text[pos:]

    candidate_lines = steps_section.splitlines() if steps_section else text.splitlines()
    test_commands = []
    for line in candidate_lines:
        line_clean = line.strip().strip("`*# ")
        if any(line_clean.startswith(prefix) for prefix in (
            "pytest", "python -m pytest", "node tools/unit", "npm run build"
        )):
            test_commands.append(line_clean)
        elif any(f"`{p}" in line for p in ("pytest", "python -m pytest", "node tools/unit", "npm run build")):
            matches = re.findall(r"`([^`]+)`", line)
            for m in matches:
                if any(m.startswith(p) for p in ("pytest", "python -m pytest", "node tools/unit", "npm run build")):
                    test_commands.append(m)

    file_matches = re.findall(r"tools/unit/test_[a-zA-Z0-9_]+\.js", text)
    for fm in file_matches:
        test_commands.append(f"node tools/unit/run.cjs {fm}")

    py_matches = re.findall(r"tests/test_[a-zA-Z0-9_]+\.py", text)
    for pm in py_matches:
        test_commands.append(f"python -m pytest {pm}")

    deduped = list(dict.fromkeys(test_commands))
    if any(c.startswith("node tools/unit/run.cjs tools/unit/") for c in deduped):
        deduped = [c for c in deduped if c != "node tools/unit/run.cjs"]

    return {
        "path": path,
        "name": path.name,
        "card_id": card_id,
        "checked_count": len(checked),
        "unchecked_count": len(unchecked),
        "all_checked": len(checked) > 0 and len(unchecked) == 0,
        "test_commands": deduped,
    }


def run_test(cmd: str) -> Tuple[bool, str, float]:
    start = time.time()
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=90,
        )
        duration = time.time() - start
        return (res.returncode == 0, res.stdout, duration)
    except Exception as e:
        duration = time.time() - start
        return (False, f"Execution failed: {e}", duration)


def audit_card(card_info: Dict[str, Any]) -> Dict[str, Any]:
    """Test a card without moving it, returning verified status and evidence."""
    card_id = card_info["card_id"]
    name = card_info["name"]

    if not card_info["all_checked"]:
        return {
            "status": "BLOCKED_OPEN_CRITERIA",
            "reason": f"{card_info['unchecked_count']} open criteria remaining ({card_info['checked_count']} checked).",
            "tests_run": 0,
            "test_results": [],
        }

    test_cmds = card_info["test_commands"]
    if not test_cmds:
        return {
            "status": "NEEDS_LIVING_FIXTURE",
            "reason": "All criteria checked, but no automated test command declared in steps.",
            "tests_run": 0,
            "test_results": [],
        }

    test_results = []
    for cmd in test_cmds:
        passed, out, dur = run_test(cmd)
        test_results.append({
            "cmd": cmd,
            "passed": passed,
            "duration": dur,
            "snippet": out.strip()[-300:] if out else "",
        })
        if not passed:
            return {
                "status": "BLOCKED_FAILED_TEST",
                "failed_cmd": cmd,
                "reason": f"Command '{cmd}' failed.",
                "snippet": out.strip()[-400:] if out else "",
                "test_results": test_results,
            }

    return {
        "status": "READY_FOR_HUMAN_SIGN_OFF",
        "tests_run": len(test_results),
        "test_results": test_results,
    }


def generate_dossier(dir_path: Path, limit: int = 15) -> List[Dict[str, Any]]:
    print(f"\n=======================================================")
    print(f" [TASK VERIFIER] Auditing for Human Sign-Off: {dir_path.name}")
    print(f" Policy: Read-Only Verification (No files moved)")
    print(f"=======================================================\n")

    cards = sorted(dir_path.glob("*.md"))
    results = []
    processed = 0

    for card_path in cards:
        info = parse_card(card_path)
        if not info["all_checked"] or not info["test_commands"]:
            continue

        processed += 1
        print(f"[{processed}] Auditing {card_path.name}...")
        for cmd in info["test_commands"]:
            print(f"     Testing: {cmd}")
        res = audit_card(info)
        print(f"     Status:  {res['status']}\n")

        results.append({
            "card_id": info["card_id"],
            "name": card_path.name,
            "checked": info["checked_count"],
            "unchecked": info["unchecked_count"],
            "audit": res,
        })

        if processed >= limit:
            break

    return results


def sign_off_cards(card_ids: List[str]) -> None:
    """Manually move specifically approved cards to done."""
    print(f"\n[SIGN-OFF] Moving {len(card_ids)} approved cards to done...")
    for cid in card_ids:
        parts = cid.split("-")
        if len(parts) >= 2:
            kind = parts[0]
            num = parts[1]
            cmd = f"python tools/tasks.py move --id {num} --kind {kind} --status done"
            res = subprocess.run(cmd, shell=True, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                print(f"  [MOVED] {cid} -> done")
            else:
                print(f"  [ERROR] {cid}: {res.stderr.strip() or res.stdout.strip()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="docs/virtualWorld/dev_tasks/review/bugs")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sign-off", nargs="+", help="Approve and move specific card IDs (e.g. --sign-off task-737 bug-561)")
    args = parser.parse_args()

    if args.sign_off:
        sign_off_cards(args.sign_off)
    else:
        target = REPO_ROOT / args.dir
        dossier = generate_dossier(target, limit=args.limit)
        ready = [d for d in dossier if d["audit"]["status"] == "READY_FOR_HUMAN_SIGN_OFF"]
        blocked = [d for d in dossier if d["audit"]["status"] != "READY_FOR_HUMAN_SIGN_OFF"]
        print("\n" + "=" * 60)
        print(f" AUDIT COMPLETE: {len(ready)} ready for your sign-off, {len(blocked)} blocked by failing tests.")
        print("=" * 60)
