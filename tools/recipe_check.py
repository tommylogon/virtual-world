#!/usr/bin/env python3
"""Validate crafting recipes against the task-831 contract.

A recipe the engine cannot read fails at the campfire, not at authoring
time: a missing output file materializes as "fails to materialize", an
unknown condition type fails closed with no explanation, and a bad tier
table silently resolves to nothing. This gate checks the four field
classes the schema promises before any of that:

- ingredients reference real library items (or real item tags);
- outputs reference existing library item files;
- conditions come from the closed set the engine evaluates;
- ``duration_min`` is a positive int and ``outcomes`` holds exactly the
  four tiers (crit_success / success / fail / crit_fail).

Usage:
    python tools/recipe_check.py --check    # exit 1 on any error
    python tools/recipe_check.py --report   # every finding, grouped
"""

import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RECIPES_DIR = os.path.join(ROOT, "data", "library", "recipes")
ITEMS_DIR = os.path.join(ROOT, "data", "library", "items")

CONDITION_TYPES = {"state_equals", "has_item", "random_chance", "skill_check"}
OUTCOME_TIERS = ("crit_success", "success", "fail", "crit_fail")


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def library_items(data_dir=None):
    """{lowercased id-or-name: filename} for every library item file."""
    items_dir = os.path.join(data_dir or ROOT, "data", "library", "items") \
        if data_dir else ITEMS_DIR
    out = {}
    if not os.path.isdir(items_dir):
        return out
    for name in sorted(os.listdir(items_dir)):
        if not name.endswith(".json"):
            continue
        stem = name[:-5].lower()
        out.setdefault(stem, name)
        try:
            data = _load_json(os.path.join(items_dir, name))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("name"):
            out.setdefault(str(data["name"]).lower(), name)
    return out


def library_tags(data_dir=None):
    """Every tag string used by any library item (ingredient alternatives)."""
    items_dir = os.path.join(data_dir or ROOT, "data", "library", "items") \
        if data_dir else ITEMS_DIR
    tags = set()
    if not os.path.isdir(items_dir):
        return tags
    for name in sorted(os.listdir(items_dir)):
        if not name.endswith(".json"):
            continue
        try:
            data = _load_json(os.path.join(items_dir, name))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        raw = data.get("tags", [])
        if isinstance(raw, str):
            raw = [raw]
        for tag in raw or []:
            tag = str(tag).strip().lower()
            if tag:
                tags.add(tag)
    return tags


def check_entry(recipe, stem, items, tags):
    """Validate one recipe dict; ``stem`` is the filename without .json."""
    errors = []
    if not isinstance(recipe, dict):
        return ["file: top level must be an object"]
    rid = recipe.get("id")
    if not isinstance(rid, str) or not rid.strip():
        errors.append("id: missing or not a string")
    elif rid != stem:
        errors.append(f"id: {rid!r} does not match filename {stem!r}")
    if not isinstance(recipe.get("name"), str) or not recipe["name"].strip():
        errors.append("name: missing or not a string")

    ingredients = recipe.get("ingredients", recipe.get("inputs", "MISSING"))
    if ingredients == "MISSING":
        errors.append("ingredients: missing (inputs accepted during migration)")
    elif not isinstance(ingredients, list) or not ingredients:
        errors.append("ingredients: must be a non-empty list")
    else:
        for i, inp in enumerate(ingredients):
            where = f"ingredients[{i}]"
            if not isinstance(inp, dict):
                errors.append(f"{where}: must be an object")
                continue
            item = str(inp.get("item", "")).strip().lower()
            if not item:
                errors.append(f"{where}.item: missing")
            elif item not in items and item not in tags:
                errors.append(f"{where}.item: {inp.get('item')!r} "
                              f"is no library item and no item tag")
            try:
                count = int(inp.get("count", 1))
            except (TypeError, ValueError):
                errors.append(f"{where}.count: not an int")
            else:
                if count < 1:
                    errors.append(f"{where}.count: must be >= 1")
            if "consumed" in inp and not isinstance(inp["consumed"], bool):
                errors.append(f"{where}.consumed: must be a bool")

    for cond in recipe.get("conditions", []) or []:
        if not isinstance(cond, dict) or cond.get("type") not in CONDITION_TYPES:
            errors.append(f"conditions: unknown type "
                          f"{(cond.get('type') if isinstance(cond, dict) else cond)!r} "
                          f"(closed set: {sorted(CONDITION_TYPES)})")

    duration = recipe.get("duration_min", "MISSING")
    if duration == "MISSING":
        errors.append("duration_min: missing (positive game minutes)")
    elif not isinstance(duration, int) or isinstance(duration, bool) or duration < 1:
        errors.append(f"duration_min: must be a positive int, got {duration!r}")

    skill = recipe.get("skill_check", None)
    if skill is not None:
        if not isinstance(skill, dict) or not str(skill.get("skill", "")).strip():
            errors.append("skill_check.skill: missing or not a string")
        try:
            int(skill.get("dc", 10))
        except (TypeError, ValueError, AttributeError):
            errors.append("skill_check.dc: not an int")

    outcomes = recipe.get("outcomes", "MISSING")
    if outcomes == "MISSING":
        errors.append("outcomes: missing (exactly the four tiers)")
    elif not isinstance(outcomes, dict) or \
            sorted(outcomes) != sorted(OUTCOME_TIERS):
        errors.append(f"outcomes: keys must be exactly "
                      f"{list(OUTCOME_TIERS)}, got {sorted(outcomes) if isinstance(outcomes, dict) else outcomes!r}")
    else:
        for tier in OUTCOME_TIERS:
            node = outcomes[tier]
            where = f"outcomes.{tier}"
            if not isinstance(node, dict):
                errors.append(f"{where}: must be an object")
                continue
            for j, out in enumerate(node.get("outputs", []) or []):
                if not isinstance(out, dict) or \
                        str(out.get("item", "")).strip().lower() not in items:
                    errors.append(f"{where}.outputs[{j}].item: "
                                  f"{(out.get('item') if isinstance(out, dict) else out)!r} "
                                  f"is no library item file")
            if "consume_inputs" in node and \
                    not isinstance(node["consume_inputs"], bool):
                errors.append(f"{where}.consume_inputs: must be a bool")
            if "message" in node and not isinstance(node["message"], str):
                errors.append(f"{where}.message: must be a string")

    top_outputs = recipe.get("outputs", None)
    if top_outputs is not None:
        if not isinstance(top_outputs, list):
            errors.append("outputs: must be a list (the success default)")
        else:
            for j, out in enumerate(top_outputs):
                if not isinstance(out, dict) or \
                        str(out.get("item", "")).strip().lower() not in items:
                    errors.append(f"outputs[{j}].item: "
                                  f"{(out.get('item') if isinstance(out, dict) else out)!r} "
                                  f"is no library item file")
    return errors


def check_recipe(path, items, tags):
    """Validate one recipe file; thin wrapper over :func:`check_entry`."""
    try:
        with open(path, encoding="utf-8") as f:
            recipe = json.load(f)
    except ValueError as e:
        return [f"file: not valid JSON ({e})"]
    return check_entry(recipe, os.path.basename(path)[:-5], items, tags)


def collect():
    items = library_items()
    tags = library_tags()
    findings = {}
    if not os.path.isdir(RECIPES_DIR):
        return findings
    for name in sorted(os.listdir(RECIPES_DIR)):
        if not name.endswith(".json"):
            continue
        errors = check_recipe(os.path.join(RECIPES_DIR, name), items, tags)
        if errors:
            findings[name] = errors
    return findings


def main(argv):
    mode = argv[1] if len(argv) > 1 else "--check"
    findings = collect()
    total = 0
    if os.path.isdir(RECIPES_DIR):
        total = len([n for n in os.listdir(RECIPES_DIR) if n.endswith(".json")])
    if mode == "--report":
        if not findings:
            print(f"recipes: all {total} clean")
        for name, errors in findings.items():
            print(f"{name}:")
            for error in errors:
                print(f"  - {error}")
    elif mode == "--check":
        if findings:
            for name, errors in findings.items():
                for error in errors:
                    print(f"{name}: {error}")
            print(f"recipe_check: {sum(len(e) for e in findings.values())} "
                  f"error(s) in {len(findings)}/{total} files")
            return 1
        print(f"recipe_check: all {total} clean")
        return 0
    else:
        print(f"unknown mode {mode!r} (want --check or --report)")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
