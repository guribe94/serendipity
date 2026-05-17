"""Tetromino model and shape data for the preview/placement-aid subsystem.

The preview subsystem owns enough of the piece model to compute ghost
locations and render queue previews. Other subsystems (game loop, input) may
construct ``Tetromino`` values directly or pass through their own compatible
piece type — anything that exposes ``kind`` and ``cells`` integrates cleanly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import FrozenSet, Iterable, Tuple

Cell = Tuple[int, int]
Color = Tuple[int, int, int]


class PieceKind(Enum):
    """The seven standard tetrominoes."""

    I = "I"
    O = "O"
    T = "T"
    S = "S"
    Z = "Z"
    J = "J"
    L = "L"


# Spawn-rotation cell layouts within a tight bounding box (col, row).
# Top-left of bbox is (0, 0). These match Tetris Guideline spawn orientations.
SHAPES: dict[PieceKind, tuple[Cell, ...]] = {
    PieceKind.I: ((0, 1), (1, 1), (2, 1), (3, 1)),
    PieceKind.O: ((1, 0), (2, 0), (1, 1), (2, 1)),
    PieceKind.T: ((1, 0), (0, 1), (1, 1), (2, 1)),
    PieceKind.S: ((1, 0), (2, 0), (0, 1), (1, 1)),
    PieceKind.Z: ((0, 0), (1, 0), (1, 1), (2, 1)),
    PieceKind.J: ((0, 0), (0, 1), (1, 1), (2, 1)),
    PieceKind.L: ((2, 0), (0, 1), (1, 1), (2, 1)),
}


# Tetris Guideline colors. Used by preview renderers for ghost and queue.
COLORS: dict[PieceKind, Color] = {
    PieceKind.I: (0, 240, 240),
    PieceKind.O: (240, 240, 0),
    PieceKind.T: (160, 0, 240),
    PieceKind.S: (0, 240, 0),
    PieceKind.Z: (240, 0, 0),
    PieceKind.J: (0, 0, 240),
    PieceKind.L: (240, 160, 0),
}


@dataclass(frozen=True)
class Tetromino:
    """An immutable tetromino at a known board position.

    ``cells`` are stored in board coordinates (col, row) with (0, 0) at the
    top-left of the playfield. Rotation is encoded by the cell layout itself,
    keeping this type rotation-agnostic — any rotation system (SRS, ARS,
    NRS) can produce a Tetromino by computing the resulting cells.
    """

    kind: PieceKind
    cells: FrozenSet[Cell]

    @classmethod
    def spawn(
        cls,
        kind: PieceKind,
        *,
        board_width: int = 10,
        spawn_row: int = 0,
    ) -> "Tetromino":
        """Construct a Tetromino at the standard spawn location for ``kind``.

        The piece is horizontally centered on the playfield using its bounding
        box. ``spawn_row`` is added to every row so callers can place pieces
        higher (e.g. ``spawn_row=-1`` for a buffer row above row 0).
        """
        shape = SHAPES[kind]
        min_col = min(c for c, _ in shape)
        max_col = max(c for c, _ in shape)
        bbox_w = max_col - min_col + 1
        col_offset = (board_width - bbox_w) // 2 - min_col
        cells = frozenset((c + col_offset, r + spawn_row) for c, r in shape)
        return cls(kind=kind, cells=cells)

    @property
    def color(self) -> Color:
        return COLORS[self.kind]

    def translated(self, dx: int, dy: int) -> "Tetromino":
        """Return a copy shifted by (dx, dy) cells."""
        if dx == 0 and dy == 0:
            return self
        return replace(self, cells=frozenset((c + dx, r + dy) for c, r in self.cells))

    def with_cells(self, cells: Iterable[Cell]) -> "Tetromino":
        """Return a copy with new cells (e.g. after rotation by the game loop)."""
        return replace(self, cells=frozenset(cells))
