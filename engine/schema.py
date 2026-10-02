"""Save/scenario payload schema version gate and migrations.

The payload's *format* version (``SCHEMA_VERSION`` in ``version.py``) is distinct
from the app build version. Every load path runs the payload through
:func:`migrate` first, so a file written before a breaking format change is
either migrated or refused with a specific error — never silently read as if it
were current (task-453).

The migration itself is read-old/write-new and in memory only; it never rewrites
the source file. A file is rewritten in the new format only when it is next
saved/committed.
"""

from version import SCHEMA_VERSION


class SchemaError(Exception):
    """A payload cannot be read safely by this app version."""


# from_version -> callable(data) -> data. Each step moves N to N+1 in memory.
def _migrate_1_to_2(data):
    """v1 -> v2: the Bladder vital flipped direction (100=empty -> 0=empty)."""
    for pdata in (data.get("players", {}) or {}).values():
        vitals = pdata.get("vitals") if isinstance(pdata, dict) else None
        if isinstance(vitals, dict) and vitals.get("Bladder") is not None:
            try:
                vitals["Bladder"] = 100 - vitals["Bladder"]
            except TypeError:
                pass
    return data


SCHEMA_MIGRATIONS = {
    1: _migrate_1_to_2,
}

# A payload with no recorded version is read as *current*, not v1.
#
# Evidence: `save_autosave` has stamped `schema_version: 2` since the initial
# public release (the same commit that introduced the bladder v1->v2 migration),
# while `_save_game` and `to_scenario_dict` wrote current-format payloads
# *without* the field. So an unstamped file is overwhelmingly a current-format
# save/scenario, and assuming v1 would wrongly invert every one of their Bladder
# vitals. An explicit older version still migrates; a newer one is refused.
LEGACY_SCHEMA_VERSION = SCHEMA_VERSION


def schema_version_of(data):
    """Return the payload's declared schema version, or ``None`` if absent.

    ``_save_metadata.schema_version`` (named saves / autosave slot),
    ``_autosave_meta.schema_version`` (boot autosave), and a top-level
    ``schema_version`` (scenario payloads) are all accepted.
    """
    if not isinstance(data, dict):
        return None
    for key in ("_save_metadata", "_autosave_meta"):
        meta = data.get(key)
        if isinstance(meta, dict) and meta.get("schema_version") is not None:
            return meta.get("schema_version")
    return data.get("schema_version")


def migrate(data):
    """Return ``(data, from_version)`` with migrations applied in memory.

    Raises :class:`SchemaError` when the payload is newer than this app, or when
    a required migration step is not registered. ``from_version`` is the version
    the payload declared (``LEGACY_SCHEMA_VERSION`` — i.e. current — when it
    declared none, since unstamped payloads use the current shape), so a caller
    can tell the user "migrated from v1" when a real migration ran.
    """
    raw = schema_version_of(data)
    try:
        from_version = int(raw) if raw is not None else LEGACY_SCHEMA_VERSION
    except (TypeError, ValueError):
        raise SchemaError(f"Unrecognised schema_version {raw!r}.")

    if from_version > SCHEMA_VERSION:
        raise SchemaError(
            f"This file was written by a newer version (schema v{from_version}); "
            f"this app reads up to schema v{SCHEMA_VERSION}. Update the app to load it."
        )
    if from_version == SCHEMA_VERSION:
        return data, from_version

    migrated = data
    current = from_version
    while current < SCHEMA_VERSION:
        step = SCHEMA_MIGRATIONS.get(current)
        if step is None:
            raise SchemaError(
                f"No migration from schema v{current} to v{current + 1}; "
                f"this file cannot be loaded safely."
            )
        migrated = step(migrated)
        current += 1
    _stamp(migrated, SCHEMA_VERSION)
    return migrated, from_version


def _stamp(data, version):
    """Write the current schema version where the payload expects it."""
    meta = data.get("_save_metadata")
    if isinstance(meta, dict):
        meta["schema_version"] = version
        return
    meta = data.get("_autosave_meta")
    if isinstance(meta, dict):
        meta["schema_version"] = version
        return
    data["schema_version"] = version
