#!/usr/bin/env python3
"""E2E verification harness for VirtualWorld.

Boots the app on a dynamic scratch port (VW_PORT != 4444), drives a headless
browser via Playwright, and validates live client and server state.

Recipe notes:
- The turn queue is client-side, so a second tab or scratch runner is safe.
- Nothing mutates world state unless a turn is committed.
- HumanTurnComposer.request(actor) opens the turn card directly.
- Turn-based mode + max-steps=1 is the safe startup.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Tuple

import requests


def allocate_free_port() -> int:
    """Find a free TCP port that is never 4444."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    if port == 4444:
        # Extremely unlikely, but explicitly guaranteed
        return allocate_free_port()
    return port


def wait_for_server(port: int, timeout_sec: float = 20.0) -> bool:
    """Poll /api/state until the server responds 200 OK and mid-boot clears."""
    start = time.time()
    url = f"http://127.0.0.1:{port}/api/state"
    while time.time() - start < timeout_sec:
        try:
            r = requests.get(url, timeout=1.0)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "graph" in data:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def run_checks(port: int, scenario_name: str, headless: bool = True) -> List[Tuple[str, bool, str]]:
    """Drive browser checks and assert live state. Returns [(check_name, passed, details)]."""
    from playwright.sync_api import sync_playwright

    results: List[Tuple[str, bool, str]] = []
    base_url = f"http://127.0.0.1:{port}"

    # Step A: Load the requested scenario
    scen_path = os.path.join("data", "scenarios", f"{scenario_name}.json")
    if not os.path.exists(scen_path):
        results.append(("scenario_load", False, f"Scenario file not found: {scen_path}"))
        return results

    with open(scen_path, "r", encoding="utf-8") as f:
        scen_data = json.load(f)

    r_load = requests.post(f"{base_url}/api/load", json=scen_data, timeout=5.0)
    if r_load.status_code != 200:
        results.append(("scenario_load", False, f"POST /api/load returned status {r_load.status_code}: {r_load.text}"))
        return results
    results.append(("scenario_load", True, f"Loaded scenario '{scenario_name}' successfully (HTTP 200)"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(f"{base_url}/", timeout=15000)
        page.wait_for_selector("#top-bar", timeout=10000)

        # -------------------------------------------------------------
        # Check 1: Library browser modal (bug-520)
        # -------------------------------------------------------------
        try:
            page.evaluate("() => { if (window.openLibraryBrowser) window.openLibraryBrowser(); else if (window.VW && window.VW.libraryBrowser) window.VW.libraryBrowser.open(); }")
            page.wait_for_selector("#library-modal", state="visible", timeout=6000)
            lib_bounds = page.evaluate("""() => {
                const el = document.getElementById('library-modal');
                if (!el) return { found: false, w: 0, h: 0 };
                const r = el.getBoundingClientRect();
                return { found: true, w: r.width, h: r.height };
            }""")
            if lib_bounds.get("found") and lib_bounds.get("w", 0) > 0 and lib_bounds.get("h", 0) > 0:
                results.append(("library_browser_open", True, f"Library modal visible with bounds {lib_bounds['w']:.0f}x{lib_bounds['h']:.0f}px (bug-520 verified)"))
            else:
                results.append(("library_browser_open", False, f"Library modal bounds invalid: {lib_bounds}"))

            # Close library browser
            page.evaluate("() => { const b = document.getElementById('close-library-browser'); if (b) b.click(); else if (window.VW && window.VW.libraryBrowser) window.VW.libraryBrowser.close(); }")
        except Exception as exc:
            results.append(("library_browser_open", False, f"Failed interacting with library browser: {exc}"))

        # -------------------------------------------------------------
        # Check 2: Duplicate character import to explicit area (bug-521)
        # -------------------------------------------------------------
        try:
            target_area = "Courtyard"
            r1 = requests.post(f"{base_url}/api/library/import/character/amber", json={"area": target_area}, timeout=5.0)
            r2 = requests.post(f"{base_url}/api/library/import/character/amber", json={"area": target_area}, timeout=5.0)
            if r1.status_code != 200 or r2.status_code != 200:
                results.append(("duplicate_character_import", False, f"Import API failed: r1={r1.status_code}, r2={r2.status_code}"))
            else:
                state = requests.get(f"{base_url}/api/state", timeout=5.0).json()
                amber_instances = [
                    (k, v.get("current_area"))
                    for k, v in state.get("players", {}).items()
                    if "amber" in k.lower()
                ]
                placed_correctly = len(amber_instances) >= 2 and all(area == target_area for _, area in amber_instances)
                if placed_correctly:
                    results.append(("duplicate_character_import", True, f"Imported {len(amber_instances)} instances into {target_area}: {amber_instances} (bug-521 verified)"))
                else:
                    results.append(("duplicate_character_import", False, f"Import instances not both in {target_area}: {amber_instances}"))
        except Exception as exc:
            results.append(("duplicate_character_import", False, f"Failed duplicate character import check: {exc}"))

        # -------------------------------------------------------------
        # Check 3: HTC Person action menu exposes task-610 actions
        # -------------------------------------------------------------
        try:
            page.evaluate("() => { void window.HumanTurnComposer.request('Explorer'); }")
            page.wait_for_selector("#htc-overlay", state="visible", timeout=6000)
            page.wait_for_selector(".tsv-person", timeout=6000)

            # Click Doc Holliday chip (or first person chip)
            clicked = page.evaluate("""() => {
                const chips = [...document.querySelectorAll('.tsv-person')];
                const c = chips.find(x => x.textContent.toLowerCase().includes('doc') || x.textContent.toLowerCase().includes('sharp-dressed'));
                if (c) { c.click(); return c.textContent.trim(); }
                if (chips.length > 0) { chips[0].click(); return chips[0].textContent.trim(); }
                return null;
            }""")

            if not clicked:
                results.append(("person_menu_actions", False, "No person chip found or clickable in HTC"))
            else:
                page.wait_for_selector(".tsv-ctx", timeout=5000)
                buttons = page.evaluate("""() => {
                    return [...document.querySelectorAll('.tsv-ctx button')].map(b => b.textContent.trim());
                }""")
                required_prefixes = ["Whisper to", "Say aloud", "Examine", "Attack", "Grab", "Lead", "Wake", "Give"]
                missing = [p for p in required_prefixes if not any(b.startswith(p) for b in buttons)]
                if not missing:
                    results.append(("person_menu_actions", True, f"Person menu exposed {len(buttons)} actions covering all required task-610 actions: {buttons}"))
                else:
                    results.append(("person_menu_actions", False, f"Person menu missing required actions: {missing}. Present: {buttons}"))
        except Exception as exc:
            results.append(("person_menu_actions", False, f"Failed testing HTC person menu: {exc}"))

        # -------------------------------------------------------------
        # Check 4: Hidden way stays absent from WAYS OUT (bug-23 negative)
        # -------------------------------------------------------------
        try:
            # Check scene ways for Library where false bookcase wall connects to Secret Vault
            doc_scene = requests.get(f"{base_url}/api/scene/Doctor%20Brown", timeout=5.0).json()
            doc_ways = [w.get("name") or w.get("label") or "" for w in doc_scene.get("ways", [])]
            explorer_scene = requests.get(f"{base_url}/api/scene/Explorer", timeout=5.0).json()
            explorer_ways = [w.get("name") or w.get("label") or "" for w in explorer_scene.get("ways", [])]

            leaked = "false bookcase wall" in doc_ways or "false bookcase wall" in explorer_ways
            if not leaked:
                results.append(("hidden_way_absent", True, f"Hidden way 'false bookcase wall' absent from scene ways (Library ways: {doc_ways}, Courtyard ways: {explorer_ways}) (bug-23 negative verified)"))
            else:
                results.append(("hidden_way_absent", False, f"Hidden way leaked into scene ways! Library: {doc_ways}, Courtyard: {explorer_ways}"))
        except Exception as exc:
            results.append(("hidden_way_absent", False, f"Failed checking hidden way perception: {exc}"))

        # -------------------------------------------------------------
        # Check 5: Scrim cleanup when closing modal with menu open (task-612)
        # -------------------------------------------------------------
        try:
            # With context menu currently open, close the modal
            page.evaluate("() => window.HumanTurnComposer.closeTurn()")
            time.sleep(0.5)
            scrim_count = page.evaluate("""() => {
                const scrims = [...document.querySelectorAll('.tsv-scrim')].filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && window.getComputedStyle(el).display !== 'none';
                });
                return scrims.length;
            }""")
            if scrim_count == 0:
                results.append(("scrim_cleanup", True, "Closing HTC modal cleanly unmounted all context scrims; 0 visible scrims remain (task-612 verified)"))
            else:
                results.append(("scrim_cleanup", False, f"Found {scrim_count} visible orphaned .tsv-scrim elements after modal close"))
        except Exception as exc:
            results.append(("scrim_cleanup", False, f"Failed testing modal scrim cleanup: {exc}"))

        # -------------------------------------------------------------
        # Check 7: React-phase result structured formatting (task-679)
        # -------------------------------------------------------------
        try:
            wall_of_text = (
                "You head through the grand_stairs. - you're in upstairs hall.\n"
                "The light is dim - you can just make out the shapes of things here, details lost in shadow.\n"
                "[grand_stairs_back] foyer is visible beyond (dimly lit, cool).\n"
                "[master_bedroom_door] a large oak door with brass filigree. It is currently closed.\n"
                "[guest_room1_door] a simple painted door.\n"
                "kayla jenkins - a sixteen-year-old with dark hair is wearing black crop top on their torso. [wearing: black crop top, denim cut-offs] [holding: nothing] at the rug\n"
                "miki - a bubbly twenty-something [wearing: oversized hoodie] [holding: phone]\n"
                "[!] The air is stale and making you tired."
            )
            page.evaluate("(text) => { void window.HumanTurnComposer.react('Explorer', [text]); }", wall_of_text)
            page.wait_for_selector("#htc-result", state="visible", timeout=5000)

            react_check = page.evaluate("""() => {
                const res = document.getElementById('htc-result');
                if (!res) return { found: false };
                const action = res.querySelector('.htc-res-action');
                const prose = res.querySelector('.htc-res-prose');
                const details = res.querySelector('.htc-res-details');
                const status = res.querySelector('.htc-res-status');
                const people = res.querySelector('.htc-res-people');
                const tailLines = [...res.querySelectorAll('.htc-res-tail-line')].map(l => l.textContent.trim());
                return {
                    found: true,
                    actionText: action ? action.textContent.trim() : '',
                    proseText: prose ? prose.textContent.trim() : '',
                    hasDetails: !!details,
                    statusText: status ? status.textContent.trim() : '',
                    peopleText: people ? people.textContent.trim() : '',
                    tailCount: tailLines.length
                };
            }""")

            if (react_check.get("found") and
                "You head through" in react_check.get("actionText", "") and
                "The light is dim" in react_check.get("proseText", "") and
                react_check.get("hasDetails") and
                react_check.get("tailCount", 0) >= 5 and
                "kayla jenkins" in react_check.get("peopleText", "").lower()):
                results.append(("react_result_structured", True, f"React result structured into action, prose, {react_check['tailCount']} collapsed details, and people summary (task-679 verified live)"))
            else:
                results.append(("react_result_structured", False, f"React result formatting check failed: {react_check}"))
        except Exception as exc:
            results.append(("react_result_structured", False, f"Failed testing react-phase result: {exc}"))

        browser.close()

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="VirtualWorld E2E Verification Harness")
    parser.add_argument("--scenario", default="htc_fixture", help="Scenario name to test (default: htc_fixture)")
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True, help="Run browser headless")
    args = parser.parse_args()

    port = allocate_free_port()
    print(f"=== E2E Harness Starting ===")
    print(f"Scenario: {args.scenario}")
    print(f"Allocated scratch port: {port} (guaranteed != 4444)")

    env = dict(os.environ)
    env["VW_PORT"] = str(port)

    # Launch server subprocess
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    all_passed = False
    try:
        print(f"Waiting for server at http://127.0.0.1:{port}/api/state...")
        ready = wait_for_server(port)
        if not ready:
            print("ERROR: Server failed to start and respond with valid world state within timeout.", file=sys.stderr)
            return 1
        print("Server online and healthy.")

        checks = run_checks(port, args.scenario, headless=args.headless)
        print(f"\n=== Verification Results ({len(checks)} checks) ===")
        all_passed = True
        for name, passed, details in checks:
            mark = "PASS" if passed else "FAIL"
            print(f"[{mark}] {name}: {details}")
            if not passed:
                all_passed = False

    finally:
        print("\nShutting down scratch server process...")
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print("Scratch server terminated cleanly.")

    print(f"=== E2E Harness Complete: {'SUCCESS' if all_passed else 'FAILURE'} ===")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
