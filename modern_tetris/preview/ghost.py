"""Ghost-piece calculation.

The ghost shows where the active piece would land if hard-dropped. It is
recomputed whenever the active piece moves or rotates. The calculation is
intentionally agnostic of the board representation: the caller supplies a
collision predicate that knows about walls, floor, and locked cells.

Convention: ``is_blocked(cells)`` must return True if placing the piece at
``cells`` would overlap any wall, floor, or locked block — but should NOT
count the active piece's own footprint as a collision. (Most game-loop
collision functions already meet this.)
"""

from __future__ import annotations

from typing import Iterable, Protocol

from .pieces import Cell, Tetromino


class CollisionPredicate(Protocol):
    def __call__(self, cells: Iterable[Cell]) -> bool: ...


def ghost_for(
    active: Tetromino,
    is_blocked: CollisionPredicate,
    *,
    max_drop: int = 40,
) -> Tetromino:
    """Return the active piece translated down to its resting position.

    ``max_drop`` caps the search so a misbehaving predicate cannot loop
    forever; 40 is comfortably more than any reasonable playfield height.

    If the active piece is already blocked at its current position (e.g. it
    overlaps locked cells in a top-out scenario), the active piece is
    returned unchanged so callers can still render something sensible.
    """
    if is_blocked(active.cells):
        return active
    dy = 0
    while dy < max_drop:
        next_cells = frozenset((c, r + dy + 1) for c, r in active.cells)
        if is_blocked(next_cells):
            break
        dy += 1
    return active.translated(0, dy)
