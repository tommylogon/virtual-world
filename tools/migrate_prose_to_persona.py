"""Migrate unstructured character descriptions to structured persona blocks.

@module tools/migrate_prose_to_persona
@contributes extract_persona_heuristics, migrate_scenario_characters
@powers offline conversion of prose character descriptions to 4-part persona records (task-918)
@relates engine/character_appearance.py, engine/character_store.py
@docs docs/virtualWorld/Characters/Persona.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.character_appearance import (
    HEIGHT_CM_RANGE,
    WEIGHT_KG_RANGE,
    normalize_slug,
    validate,
)
from engine.species import SPECIES_PROFILES

COMMON_OCCUPATIONS = (
    "blacksmith", "merchant", "guard", "cook", "chef", "hunter", "scout",
    "alchemist", "innkeeper", "farmer", "fisherman", "miner", "scholar",
    "cleric", "priest", "rogue", "soldier", "captain", "baker", "weaver",
    "carpenter", "herbalist", "healer", "artisan", "bartender",
)

HAIR_COLORS = ("black", "brown", "blonde", "blond", "red", "white", "grey", "gray", "silver", "golden", "auburn")
HAIR_LENGTHS = ("short", "long", "medium", "shoulder-length", "cropped", "waist-length")
HAIR_STYLES = ("braided", "ponytail", "messy", "curly", "wavy", "straight", "shaved", "buzzcut")
EYE_COLORS = ("blue", "green", "brown", "hazel", "amber", "grey", "gray", "dark", "golden", "violet")
SKIN_TONES = ("pale", "fair", "tan", "tanned", "dark", "olive", "green", "pale green", "brown", "bronze")
BUILDS = ("lean and wiry", "lean", "wiry", "stocky", "muscular", "slender", "athletic", "heavy", "stout", "tall", "petite")


def extract_persona_heuristics(prose: str, name: str = "") -> Dict[str, Any]:
    """Parse unstructured character prose into a 4-part persona block.

    Keeps the full prose context intact while mapping detectable traits to
    identity, appearance, personality, and narrative sections.
    """
    if not prose or not prose.strip():
        return {}

    text = prose.strip()
    lowered = text.lower()

    identity: Dict[str, Any] = {}
    appearance: Dict[str, Any] = {}
    personality: Dict[str, Any] = {}
    narrative: Dict[str, Any] = {}

    # ── Identity ──
    # Age
    age_match = re.search(r"\b(\d{1,3})[- ]years?[- ]old\b", text, re.I)
    if not age_match:
        age_match = re.search(r"\baged?\s+(\d{1,3})\b", text, re.I)
    if age_match:
        try:
            age = float(age_match.group(1))
            if 0 <= age <= 10000:
                identity["age"] = age
        except (ValueError, TypeError):
            pass

    # Gender & Pronouns
    she_count = len(re.findall(r"\b(she|her|hers)\b", lowered))
    he_count = len(re.findall(r"\b(he|him|his)\b", lowered))
    they_count = len(re.findall(r"\b(they|them|theirs)\b", lowered))

    if she_count > he_count and she_count > they_count:
        identity["pronouns"] = "she/her"
        identity["gender"] = "woman"
    elif he_count > she_count and he_count > they_count:
        identity["pronouns"] = "he/him"
        identity["gender"] = "man"
    elif they_count > 0:
        identity["pronouns"] = "they/them"
        identity["gender"] = "non-binary"

    # Species
    for sp in sorted(SPECIES_PROFILES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(sp)}\b", lowered):
            identity["species"] = sp
            break

    # Occupation
    for occ in COMMON_OCCUPATIONS:
        if re.search(rf"\b{re.escape(occ)}\b", lowered):
            identity["occupation"] = occ
            break

    # ── Appearance ──
    # Height
    cm_match = re.search(r"\b(\d{2,3})\s*(?:cm|centimeters?|centimetres?)\b", lowered)
    if cm_match:
        try:
            h = float(cm_match.group(1))
            if HEIGHT_CM_RANGE[0] <= h <= HEIGHT_CM_RANGE[1]:
                appearance["height_cm"] = h
        except (ValueError, TypeError):
            pass
    else:
        ft_match = re.search(r"\b(\d+)\s*(?:foot|feet|ft|\')\s*(\d+)?\s*(?:inches|in|\")?\b", lowered)
        if ft_match:
            try:
                feet = float(ft_match.group(1))
                inches = float(ft_match.group(2) or 0)
                h = round((feet * 12 + inches) * 2.54)
                if HEIGHT_CM_RANGE[0] <= h <= HEIGHT_CM_RANGE[1]:
                    appearance["height_cm"] = float(h)
            except (ValueError, TypeError):
                pass

    # Weight
    kg_match = re.search(r"\b(\d{2,3})\s*(?:kg|kilos?|kilograms?)\b", lowered)
    if kg_match:
        try:
            w = float(kg_match.group(1))
            if WEIGHT_KG_RANGE[0] <= w <= WEIGHT_KG_RANGE[1]:
                appearance["weight_kg"] = w
        except (ValueError, TypeError):
            pass

    # Build
    for b in BUILDS:
        if re.search(rf"\b{re.escape(b)}\b", lowered):
            appearance["build"] = b
            break

    # Hair
    hair: Dict[str, str] = {}
    for col in HAIR_COLORS:
        if re.search(rf"\b{col}\s+hair\b", lowered) or re.search(rf"\bhair\s+is\s+{col}\b", lowered):
            hair["color"] = col
            break
    for length in HAIR_LENGTHS:
        if re.search(rf"\b{length}\s+hair\b", lowered):
            hair["length"] = length
            break
    for style in HAIR_STYLES:
        if re.search(rf"\b{style}\s+hair\b", lowered) or re.search(rf"\bhair\b.*\b{style}\b", lowered):
            hair["style"] = style
            break
    if hair:
        appearance["hair"] = hair

    # Eyes
    eyes: Dict[str, str] = {}
    for col in EYE_COLORS:
        if re.search(rf"\b{col}\s+eyes\b", lowered):
            eyes["color"] = col
            break
    if eyes:
        appearance["eyes"] = eyes

    # Skin
    skin: Dict[str, str] = {}
    for tone in SKIN_TONES:
        if re.search(rf"\b{tone}\s+skin\b", lowered):
            skin["tone"] = tone
            break
    if skin:
        appearance["skin"] = skin

    # ── Personality ──
    traits: List[str] = []
    likes: List[str] = []
    fears: List[str] = []

    # Detect likes
    likes_match = re.search(r"\b(?:likes|fond of|enjoys)\s+([^.,;]+)", lowered)
    if likes_match:
        for chunk in re.split(r"\s+(?:and|or)\s+", likes_match.group(1)):
            slug = normalize_slug(chunk)
            if slug and slug not in likes:
                likes.append(slug)

    # Detect fears
    fears_match = re.search(r"\b(?:fears|afraid of|terrified of)\s+([^.,;]+)", lowered)
    if fears_match:
        for chunk in re.split(r"\s+(?:and|or)\s+", fears_match.group(1)):
            slug = normalize_slug(chunk)
            if slug and slug not in fears:
                fears.append(slug)

    if likes:
        personality["likes"] = likes
    if fears:
        personality["fears"] = fears
    if traits:
        personality["traits"] = traits

    # ── Narrative ──
    narrative["biography"] = {"current_situation": text}

    candidate: Dict[str, Any] = {}
    if identity:
        candidate["identity"] = identity
    if appearance:
        candidate["appearance"] = appearance
    if personality:
        candidate["personality"] = personality
    if narrative:
        candidate["narrative"] = narrative

    return validate(candidate)


def migrate_scenario_characters(scenario_path: str, dry_run: bool = True) -> Dict[str, Any]:
    """Scan a scenario file and migrate unconfigured character prose to persona blocks."""
    path = Path(scenario_path)
    if not path.is_file():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("graph", {}).get("nodes", {})
    players = data.get("players", {})
    migrated = []

    for nid, node in nodes.items():
        if not isinstance(node, dict) or node.get("type") != "character":
            continue
        props = node.get("properties") or {}
        name = node.get("name") or nid

        # If persona already exists with identity or appearance, skip
        if props.get("persona") and any(k in props["persona"] for k in ("identity", "appearance")):
            continue

        prose = props.get("base_description") or props.get("description") or ""
        if not prose and name in players:
            p = players[name]
            prose = p.get("base_description") or p.get("description") or ""

        if not prose:
            continue

        persona = extract_persona_heuristics(prose, name=name)
        if persona:
            migrated.append({
                "node_id": nid,
                "name": name,
                "extracted": persona,
            })
            if not dry_run:
                props["persona"] = persona
                node["properties"] = props

    if not dry_run and migrated:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    return {
        "file": str(path),
        "total_characters": len([n for n in nodes.values() if isinstance(n, dict) and n.get("type") == "character"]),
        "migrated_count": len(migrated),
        "migrated": migrated,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(description="Migrate unstructured character prose into persona records.")
    parser.add_argument("--file", help="Path to scenario JSON file")
    parser.add_argument("--text", help="Single prose description string to convert")
    parser.add_argument("--apply", action="store_true", help="Apply changes to scenario JSON file (default is dry-run)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if args.text:
        record = extract_persona_heuristics(args.text)
        if args.json:
            print(json.dumps(record, indent=2))
        else:
            print("Extracted Persona:")
            print(json.dumps(record, indent=2))
        return

    if args.file:
        res = migrate_scenario_characters(args.file, dry_run=not args.apply)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            mode = "DRY RUN" if res["dry_run"] else "APPLIED"
            print(f"[{mode}] {res['migrated_count']} / {res['total_characters']} characters converted.")
            for item in res["migrated"]:
                print(f"  • {item['name']} ({item['node_id']}): {list(item['extracted'].keys())}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
