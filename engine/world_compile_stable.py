"""Stable hashing/selection helpers for the grid compiler.

Owner of the deterministic primitives used by ``engine.world_compile``:
``_stable_index`` (weighted character sum, for description-fragment picking)
and ``stable_digest`` (FNV-1a 32-bit, for percentage decisions such as way
blocking). Extracted so the determinism contract has one home; behaviour
unchanged.
"""

_FNV_OFFSET = 0x811C9DC5
_FNV_PRIME = 0x01000193
_FNV_MASK = 0xFFFFFFFF


def _stable_index(text: str, n: int) -> int:
    """Deterministic 0..n-1 index for *text* (no ``random``/``hash``)."""
    if n <= 1:
        return 0
    acc = 0
    for i, ch in enumerate(text):
        acc += (i + 1) * ord(ch)
    return acc % n


def stable_digest(text: str) -> int:
    """A stable 32-bit hash of *text* - no ``random``, no clock, no ``hash()``.

    ``hash()`` is out: CPython salts str hashing per process, so a "hash of
    ``seed:way_id``" using it would produce a different blocked set on every run
    and fail the task's non-negotiable determinism without looking wrong.

    :func:`_stable_index` is deliberately NOT used here either. It is a weighted
    character sum, which is fine for picking one of three description fragments
    but clusters badly for a *percentage* decision: over ``way_0..way_499`` the
    only varying characters sit in the last three positions, and measured at
    73%/27% across the id space for a 12% threshold. A blocked set that is
    visibly lopsided reads as a bug even when it is deterministic, so this is the
    real hash and ``_stable_index`` keeps the old job.
    """
    acc = _FNV_OFFSET
    for byte in str(text).encode("utf-8"):
        acc = ((acc ^ byte) * _FNV_PRIME) & _FNV_MASK
    return acc