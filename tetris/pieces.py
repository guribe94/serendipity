"""Standard tetromino cell layouts.

This is a small utility for the renderer's demo and tests. The game
loop module is expected to maintain its own piece geometry; we duplicate
just enough here to render plausible snapshots without depending on it.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .state import ActivePiece, Cell

# Spawn positions for a 10-wide board: each piece is defined by the
# (col, row) cells of its first rotation, relative to the top-left of
# the spawn region (row 0 inside the hidden zone).
_SPAWN: Dict[str, List[Cell]] = {
    "I": [(3, 1), (4, 1), (5, 1), (6, 1)],
    "O": [(4, 0), (5, 0), (4, 1), (5, 1)],
    "T": [(4, 0), (3, 1), (4, 1), (5, 1)],
    "S": [(4, 0), (5, 0), (3, 1), (4, 1)],
    "Z": [(3, 0), (4, 0), (4, 1), (5, 1)],
    "J": [(3, 0), (3, 1), (4, 1), (5, 1)],
    "L": [(5, 0), (3, 1), (4, 1), (5, 1)],
}


def spawn_piece(kind: str) -> ActivePiece:
    """Return a fresh piece of ``kind`` in spawn position."""
    cells = _SPAWN[kind]
    return ActivePiece(kind=kind, cells=list(cells))


def all_kinds() -> Tuple[str, ...]:
    return tuple(_SPAWN.keys())
