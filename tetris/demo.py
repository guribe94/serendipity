"""Headless demo: render each game phase to a PNG for visual inspection.

Run with::

    SDL_VIDEODRIVER=dummy python3 -m tetris.demo [output_dir]

This is the verification path used by Canvas delivery: it exercises the
renderer end-to-end against an SDL surface without needing a display,
saves snapshots, and exits 0 on success.

A companion text-only demo of the core gameplay subsystem is available
as :mod:`tetris.demo_core` (no pygame dependency).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

# Headless default; callers can override before importing pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from .pieces import spawn_piece
from .renderer import Renderer
from .state import (
    BOARD_COLS,
    HIDDEN_ROWS,
    ActivePiece,
    GamePhase,
    RenderState,
    Scoreboard,
    TOTAL_ROWS,
)


def _sample_board() -> list[list[str | None]]:
    board: list[list[str | None]] = [
        [None] * BOARD_COLS for _ in range(TOTAL_ROWS)
    ]
    # Stack some debris in the bottom rows, leaving a deliberate gap so
    # the renderer has interesting content.
    debris = [
        ("Z", "L", "L", "L", "T", "S", "S", "J", "J", None),
        ("Z", "Z", "O", "O", "T", "T", "S", "S", "J", None),
        ("L", "L", "O", "O", "T", "I", "I", "I", "I", None),
    ]
    for offset, row_kinds in enumerate(reversed(debris)):
        target = TOTAL_ROWS - 1 - offset
        for col, key in enumerate(row_kinds):
            board[target][col] = key
    return board


def _active_and_ghost() -> tuple[ActivePiece, ActivePiece]:
    active = spawn_piece("T").shifted(0, 6)  # mid-board
    # Ghost: same shape projected down to just above the debris stack.
    ghost = active.shifted(0, 10)
    return active, ghost


def render_phase(renderer: Renderer, phase: GamePhase) -> pygame.Surface:
    state = RenderState(
        board=_sample_board(),
        scoreboard=Scoreboard(score=12_840, level=4, lines=27),
        next_pieces=[spawn_piece(k) for k in ("I", "O", "T", "S", "Z")],
        held_piece=spawn_piece("J"),
        phase=phase,
    )
    active, ghost = _active_and_ghost()
    state.active_piece = active
    state.ghost_piece = ghost
    if phase == GamePhase.PLAYING:
        state.message = "TETRIS!"
    surface = renderer.create_surface()
    renderer.draw(surface, state)
    return surface


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = list(argv)
    out_dir = Path(args[0]) if args else Path("/tmp/tetris_snapshots")
    out_dir.mkdir(parents=True, exist_ok=True)

    renderer = Renderer()
    phases = (
        GamePhase.START,
        GamePhase.PLAYING,
        GamePhase.PAUSED,
        GamePhase.GAME_OVER,
    )
    written = []
    for phase in phases:
        surf = render_phase(renderer, phase)
        path = out_dir / f"tetris_{phase.value}.png"
        pygame.image.save(surf, str(path))
        written.append(path)

    print(f"Wrote {len(written)} snapshots:")
    for p in written:
        print(f"  {p} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
