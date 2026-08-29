import os
import json
import time
import logging
from logger import setup_logger
from version import APP_VERSION

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUTOSAVE_PATH = os.path.join(PROJECT_ROOT, 'data', 'autosave.json')

# Autosave ALSO lands in the saves directory (marked ``autosave: True``) so it
# appears in the save/load modal alongside manual slots — an always-current,
# always-restorable snapshot without manual saves piling up.
SAVES_DIR = os.path.join(PROJECT_ROOT, 'saves')
AUTOSAVE_SLOT = os.path.join(SAVES_DIR, 'autosave.json')


def save_autosave(world):
    """Write full world state to data/autosave.json (boot restore) AND to the
    saves/autosave.json slot (visible in the save/load modal)."""
    try:
        os.makedirs(os.path.dirname(AUTOSAVE_PATH), exist_ok=True)
        data = world.to_dict()
        data['_autosave_meta'] = {
            'timestamp': time.time(),
            'tick': getattr(world, 'time_ticks', 0),
            'turn': getattr(world, 'turn_number', 0),
            'scenario_source': getattr(world, '_scenario_source', None),
            'schema_version': 2,
        }
        with open(AUTOSAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        _write_autosave_slot(data)
    except Exception as e:
        logger.warning(f"Autosave failed: {e}")


def _write_autosave_slot(data):
    """Write the same snapshot to saves/autosave.json (modal slot entry).

    Uses a shallow copy so the boot-autosave dict keeps only ``_autosave_meta``
    while the modal slot gets ``_save_metadata`` (which the save list reads).
    """
    try:
        slot_data = dict(data)  # shallow — same nested structures
        scenario = ''
        source = slot_data.get('_autosave_meta', {}).get('scenario_source') or ''
        if source:
            scenario = os.path.splitext(os.path.basename(source))[0]
        slot_data['_save_metadata'] = {
            'name': 'Autosave',
            'scenario': scenario,
            'timestamp': time.strftime('%Y%m%d_%H%M%S'),
            'tick': slot_data.get('_autosave_meta', {}).get('tick', 0),
            'turn': slot_data.get('_autosave_meta', {}).get('turn', 0),
            'player': slot_data.get('active_player', ''),
            'version': APP_VERSION,
            'autosave': True,
        }
        slot_data.pop('_autosave_meta', None)
        os.makedirs(SAVES_DIR, exist_ok=True)
        with open(AUTOSAVE_SLOT, 'w', encoding='utf-8') as f:
            json.dump(slot_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Autosave slot write failed: {e}")


def load_autosave_if_exists(world):
    """Load autosave on top of current world state if present. Returns True if loaded."""
    if os.path.exists(AUTOSAVE_PATH):
        try:
            with open(AUTOSAVE_PATH, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            world.load_from_dict(data)

            # Restore scenario source from autosave meta so restart loads the right file
            meta = data.get('_autosave_meta', {})
            saved_source = meta.get('scenario_source')
            if saved_source and os.path.exists(saved_source):
                world._scenario_source = saved_source

            # Migrate bladder values from schema v1 (100=empty → 0=empty, 100=full)
            schema_version = meta.get('schema_version', 1)
            if schema_version < 2:
                migrated = 0
                for pname, pdata in data.get('players', {}).items():
                    old_val = pdata.get('vitals', {}).get('Bladder')
                    if old_val is not None:
                        new_val = 100 - old_val
                        player_obj = world.player_manager.players.get(pname)
                        if player_obj and 'Bladder' in player_obj.vitals:
                            player_obj.vitals['Bladder'] = new_val
                            migrated += 1
                if migrated:
                    logger.info(f"Migrated {migrated} player(s) from bladder schema v1 → v2")

            logger.info(f"Loaded autosave ({os.path.getsize(AUTOSAVE_PATH)} bytes)")
            return True
        except Exception as e:
            logger.warning(f"Could not load autosave: {e}")
    return False


def tokenize_command(cmd):
    """Split command string into tokens, respecting single and double quotes."""
    tokens, _ = tokenize_command_detailed(cmd)
    return tokens


def tokenize_command_detailed(cmd):
    """Split command into tokens, tracking which tokens came from quoted text.

    Returns ``(tokens, quoted_flags)`` where ``quoted_flags[i]`` is True when
    ``tokens[i]`` was wrapped in single/double quotes.  Useful for callers that
    need to distinguish a quoted multi-word name (e.g. the target of
    ``use X on "dried flower crown"``) from free text that should be treated
    as a parameter.
    """
    tokens = []
    quoted_flags = []
    buf = []
    quote_char = None
    for ch in cmd:
        if quote_char:
            if ch == quote_char:
                if buf:
                    tokens.append(''.join(buf))
                    quoted_flags.append(True)
                    buf = []
                quote_char = None
            else:
                buf.append(ch)
        elif ch in ('"', "'"):
            if buf:
                tokens.append(''.join(buf))
                quoted_flags.append(False)
                buf = []
            quote_char = ch
        elif ch == ' ':
            if buf:
                tokens.append(''.join(buf))
                quoted_flags.append(False)
                buf = []
        else:
            buf.append(ch)
    if buf:
        tokens.append(''.join(buf))
        quoted_flags.append(False)
    return tokens, quoted_flags


def _registry_subdir(data_dir, filename):
    """Map a registry filename like 'items.json' to its library subdirectory."""
    name = filename.replace('.json', '')
    path = os.path.join(data_dir, 'library', name)
    os.makedirs(path, exist_ok=True)
    return path


def load_registry(data_dir, filename):
    """Load a registry by reading individual JSON files from data/library/<name>/.

    Each file in the directory becomes one entry in the returned dict,
    keyed by the filename (without .json extension).
    """
    subdir = _registry_subdir(data_dir, filename)
    result = {}
    try:
        for entry in os.listdir(subdir):
            if not entry.endswith('.json'):
                continue
            key = entry[:-5]
            path = os.path.join(subdir, entry)
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    result[key] = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load library entry {entry}: {e}")
    except FileNotFoundError:
        return result
    return result


def save_registry(data_dir, filename, data):
    """Save a registry as individual JSON files under data/library/<name>/.

    Writes one file per key. **Never deletes files** — a caller that passes a
    partial dict (e.g. a single test entry) must not silently wipe the rest of
    the registry. Use ``delete_registry_entry()`` to remove a specific entry.
    """
    subdir = _registry_subdir(data_dir, filename)

    for key, value in data.items():
        path = os.path.join(subdir, f"{key}.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(value, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Could not save library entry {key}: {e}")


def delete_registry_entry(data_dir, filename, key):
    """Delete a single entry file from a registry directory. No-op if absent."""
    subdir = _registry_subdir(data_dir, filename)
    path = os.path.join(subdir, f"{key}.json")
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
    except Exception as e:
        logger.warning(f"Could not remove library entry {key}: {e}")
    return False


def validate_tags_on_save(tags, data_dir=None):
    """Validate a tag list against the tag library. Never blocks — warns only.

    Returns a list of warning strings for unknown/misspelled tags (with a
    closest-match suggestion when available). Callers log the warnings and/or
    surface them to the client; saves proceed regardless.
    """
    import difflib
    if not tags:
        return []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if data_dir is None:
        data_dir = os.path.join(PROJECT_ROOT, 'data')
    tags_dir = os.path.join(data_dir, 'library', 'tags')
    library = {}
    if os.path.isdir(tags_dir):
        for fn in os.listdir(tags_dir):
            if not fn.endswith('.json'):
                continue
            try:
                with open(os.path.join(tags_dir, fn), 'r', encoding='utf-8-sig') as f:
                    entry = json.load(f)
                library[entry.get('id', fn[:-5])] = entry.get('name', fn[:-5])
            except Exception:
                continue
    warnings = []
    for tag in tags:
        tag = str(tag).strip()
        if not tag:
            continue
        if tag.lower() not in library:
            suggestions = difflib.get_close_matches(tag.lower(), list(library.keys()), n=1, cutoff=0.6)
            hint = f" — did you mean '{suggestions[0]}'?" if suggestions else ""
            warnings.append(f"Tag '{tag}' not in library{hint}")
            logger.warning(f"Tag validation: {warnings[-1]}")
    return warnings


def _save_scenario(world, name=None):
    """Persist authorial content to a scenario file (strips play artifacts).

    If name is provided, saves to data/scenarios/<name>.json and updates
    world._scenario_source. Otherwise uses world._scenario_source.
    """
    try:
        if name:
            scenarios_dir = os.path.join(PROJECT_ROOT, 'data', 'scenarios')
            os.makedirs(scenarios_dir, exist_ok=True)
            safe_name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in name)
            source = os.path.join(scenarios_dir, f"{safe_name}.json")
        else:
            source = getattr(world, '_scenario_source', None)
            if not source:
                logger.warning("No scenario source — use Save Game or provide a name.")
                return
        data = world.to_scenario_dict()
        with open(source, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        world._scenario_source = source
    except Exception as e:
        logger.warning(f"Could not save scenario: {e}")


def _save_game(world, name=None, slot=None):
    """Save a full runtime snapshot to saves/ as a named save (or overwrite a slot).

    ``slot``: existing filename to overwrite in place (keeps its timestamped /
    custom identity). ``name``: display name stored in ``_save_metadata``.
    """
    try:
        saves_dir = SAVES_DIR
        os.makedirs(saves_dir, exist_ok=True)
        scenario = os.path.splitext(os.path.basename(world._scenario_source or 'world_template'))[0]
        ts = time.strftime('%Y%m%d_%H%M%S')
        safe_name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in (name or scenario))
        if slot:
            base = os.path.basename(slot or '')
            if not base.endswith('.json') or base in ('', '.', '..') or base != slot:
                raise ValueError("Invalid slot name")
            filename = base
            # Overwriting a slot without a new name keeps its existing label.
            if not name:
                try:
                    existing_path = os.path.join(saves_dir, filename)
                    if os.path.exists(existing_path):
                        with open(existing_path, 'r', encoding='utf-8-sig') as f:
                            existing_meta = json.load(f).get('_save_metadata', {})
                        name = existing_meta.get('name')
                except Exception:
                    name = None
        else:
            filename = f"{safe_name}_{ts}.json"
        path = os.path.join(saves_dir, filename)
        data = world.to_dict()
        is_auto_slot = slot and os.path.basename(slot) == os.path.basename(AUTOSAVE_SLOT)
        data['_save_metadata'] = {
            'name': name or scenario,
            'scenario': scenario,
            'timestamp': ts,
            'tick': world.time_ticks,
            'turn': world.turn_number,
            'player': world.active_player,
            'version': APP_VERSION,
            'autosave': bool(is_auto_slot),
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filename
    except Exception as e:
        logger.error(f"Could not save game: {e}")
        return None
