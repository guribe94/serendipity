"""Data interfaces consumed by the renderer.

Other subsystems (game loop, piece preview, input) own the gameplay
state and assemble a :class:`RenderState` snapshot every frame. The
renderer treats this snapshot as read-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence, Tuple


# Standard modern Tetris playfield: 10 wide x 20 visible rows.
# Rows 0..1 are commonly hidden (spawn zone); we accept any extra height
# but only draw rows in the range [hidden_rows, board_rows).
BOARD_COLS = 10
BOARD_ROWS = 20
HIDDEN_ROWS = 2
TOTAL_ROWS = BOARD_ROWS + HIDDEN_ROWS

Cell = Tuple[int, int]  # (col, row)


class GamePhase(str, Enum):
    """High-level UI state of the game."""

    START = "start"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"


@dataclass(frozen=True)
class ActivePiece:
    """A piece in play (the falling tetromino or its ghost projection)."""

    kind: str  # one of "I", "O", "T", "S", "Z", "J", "L"
    cells: Sequence[Cell]  # absolute (col, row) cells, may include hidden rows
    color_key: Optional[str] = None  # override; defaults to theme lookup by kind

    def shifted(self, dcol: int, drow: int) -> "ActivePiece":
        """Return a new piece translated by (dcol, drow). Useful for previews."""
        return ActivePiece(
            kind=self.kind,
            cells=[(c + dcol, r + drow) for c, r in self.cells],
            color_key=self.color_key,
        )


@dataclass(frozen=True)
class Scoreboard:
    """Numeric HUD fields produced by the game loop."""

    score: int = 0
    level: int = 1
    lines: int = 0


@dataclass
class RenderState:
    """A complete, renderable snapshot of the game.

    ``board`` is indexed ``board[row][col]``; each cell is either ``None``
    for empty or a color key (e.g. ``"T"``) the theme can resolve. The
    grid must have at least :data:`TOTAL_ROWS` rows and :data:`BOARD_COLS`
    columns; the renderer skips the top :data:`HIDDEN_ROWS` rows.
    """

    board: List[List[Optional[str]]] = field(
        default_factory=lambda: [[None] * BOARD_COLS for _ in range(TOTAL_ROWS)]
    )
    active_piece: Optional[ActivePiece] = None
    ghost_piece: Optional[ActivePiece] = None
    next_pieces: List[ActivePiece] = field(default_factory=list)
    held_piece: Optional[ActivePiece] = None
    scoreboard: Scoreboard = field(default_factory=Scoreboard)
    phase: GamePhase = GamePhase.START
    last_clear_rows: Sequence[int] = ()  # rows flashing this frame, if any
    message: Optional[str] = None  # optional HUD message, e.g. "TETRIS!"

    def empty_board(self) -> None:
        """Reset the board to all-empty in place."""
        for row in self.board:
            for c in range(len(row)):
                row[c] = None
