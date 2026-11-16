#!/usr/bin/env python3
"""HTTP simulation driver tool for unattended background runs and telemetry (task-860).

Connects to a running VirtualWorld server, steps turns via /api/turn/apply,
samples character state, supports vital freezing and stop conditions,
and emits structured JSONL telemetry.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


def _http_request(url: str, method: str = "GET", data: Optional[dict] = None, timeout: float = 10.0) -> Tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw.strip() else {}
            return code, payload
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"error": str(e), "detail": raw}
        return e.code, payload
    except Exception as e:
        return 0, {"error": str(e)}


class SimDriver:
    """Standardized HTTP driver for live simulation stepping and telemetry capture."""

    def __init__(self, base_url: str = "http://127.0.0.1:4444", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def reset(self) -> Tuple[bool, dict]:
        code, resp = _http_request(f"{self.base_url}/api/reset", method="POST", timeout=self.timeout)
        return code == 200, resp

    def get_state(self) -> Tuple[bool, dict]:
        code, resp = _http_request(f"{self.base_url}/api/state", method="GET", timeout=self.timeout)
        return code == 200, resp

    def apply_tick(self) -> Tuple[bool, dict]:
        code, resp = _http_request(f"{self.base_url}/api/turn/apply", method="POST", timeout=self.timeout)
        return code == 200, resp

    def patch_vital(self, character: str, vital: str, value: float) -> Tuple[bool, dict]:
        url = f"{self.base_url}/api/players/{urllib.parse.quote(character)}/vitals/{urllib.parse.quote(vital)}"
        code, resp = _http_request(url, method="PATCH", data={"value": value}, timeout=self.timeout)
        return code == 200, resp

    def freeze_vitals(self, character: str) -> None:
        """Freeze common survival vitals to neutral levels so hunger/sleep do not interrupt tests."""
        standard = {"Energy": 85, "Hunger": 85, "Thirst": 85, "Bladder": 15, "Sanity": 90}
        for vital, val in standard.items():
            self.patch_vital(character, vital, val)

    def extract_telemetry(self, state: dict, character: Optional[str] = None) -> dict:
        tick = state.get("time_ticks", 0)
        turn = state.get("turn_number", 0)
        players = state.get("players") or {}
        entry: Dict[str, Any] = {
            "time_ticks": tick,
            "turn_number": turn,
        }
        if character:
            char_data = players.get(character) or {}
            entry["character"] = character
            entry["current_area"] = char_data.get("current_area")
            entry["state"] = char_data.get("state")
            entry["vitals"] = char_data.get("vitals")
            plan = char_data.get("plan")
            if isinstance(plan, dict):
                entry["plan_index"] = plan.get("index")
                entry["plan_label"] = plan.get("label")
            pursuit = char_data.get("active_pursuit")
            if isinstance(pursuit, dict):
                entry["pursuit"] = pursuit.get("label")
                entry["pursuit_reason"] = pursuit.get("reason")
        return entry

    def run(
        self,
        ticks: int = 10,
        character: Optional[str] = None,
        sample_every: int = 1,
        stop_on_arrival: Optional[str] = None,
        stop_on_death: bool = True,
        freeze_vitals: bool = False,
        reset_first: bool = False,
        out_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a stepped run, writing telemetry and evaluating stop conditions."""
        if reset_first:
            ok, res = self.reset()
            if not ok:
                return {"success": False, "error": f"Reset failed: {res}"}

        if freeze_vitals and character:
            self.freeze_vitals(character)

        records: List[dict] = []
        stop_reason = "tick_limit_reached"

        out_file = open(out_path, "w", encoding="utf-8") if out_path else None
        try:
            for step in range(1, ticks + 1):
                ok, tick_resp = self.apply_tick()
                if not ok:
                    stop_reason = f"tick_request_failed: {tick_resp}"
                    break

                if freeze_vitals and character:
                    self.freeze_vitals(character)

                if step % sample_every == 0 or step == ticks:
                    ok_st, state = self.get_state()
                    if ok_st:
                        sample = self.extract_telemetry(state, character)
                        records.append(sample)
                        if out_file:
                            out_file.write(json.dumps(sample) + "\n")
                            out_file.flush()

                        if character:
                            c_area = sample.get("current_area")
                            c_state = sample.get("state")
                            if stop_on_arrival and c_area == stop_on_arrival:
                                stop_reason = f"arrived_at_{stop_on_arrival}"
                                break
                            if stop_on_death and c_state == "dead":
                                stop_reason = "character_died"
                                break
                    else:
                        stop_reason = f"state_fetch_failed: {state}"
                        break
        finally:
            if out_file:
                out_file.close()

        return {
            "success": True,
            "steps_executed": len(records),
            "stop_reason": stop_reason,
            "samples_count": len(records),
            "records": records,
        }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="VirtualWorld HTTP simulation driver (task-860)")
    p.add_argument("--url", default="http://127.0.0.1:4444", help="Base server URL (default: http://127.0.0.1:4444)")
    p.add_argument("--ticks", type=int, default=10, help="Number of ticks to step (default: 10)")
    p.add_argument("--character", type=str, default=None, help="Character name to track")
    p.add_argument("--sample-every", type=int, default=1, help="Sampling cadence in ticks (default: 1)")
    p.add_argument("--stop-on-arrival", type=str, default=None, help="Area name to halt on arrival")
    p.add_argument("--no-stop-on-death", dest="stop_on_death", action="store_false", default=True, help="Do not halt if character dies")
    p.add_argument("--freeze-vitals", action="store_true", default=False, help="Freeze common vitals to neutral levels")
    p.add_argument("--reset", action="store_true", default=False, help="Reset scenario via /api/reset before running")
    p.add_argument("--out", type=str, default=None, help="Output JSONL telemetry file path")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    driver = SimDriver(base_url=args.url)
    res = driver.run(
        ticks=args.ticks,
        character=args.character,
        sample_every=args.sample_every,
        stop_on_arrival=args.stop_on_arrival,
        stop_on_death=args.stop_on_death,
        freeze_vitals=args.freeze_vitals,
        reset_first=args.reset,
        out_path=args.out,
    )
    if not res.get("success"):
        print(f"Error: {res.get('error')}", file=sys.stderr)
        return 1
    print(f"Completed {res.get('samples_count')} samples. Stop reason: {res.get('stop_reason')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
