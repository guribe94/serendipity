"""Tetris rendering and HUD subsystem.

This package owns the visual presentation of a modern Tetris game: the
playfield, locked and active tetrominoes, ghost piece projection, the
next-piece preview, the score / level / lines HUD, and the start and
game-over overlays.

The renderer is decoupled from gameplay logic; it consumes the
:class:`tetris.state.RenderState` data class so that the game loop,
piece preview, and input modules can populate state independently and
have it drawn here.
"""

from .state import (
    ActivePiece,
    GamePhase,
    RenderState,
    Scoreboard,
)
from .renderer import Renderer
from .theme import Theme, default_theme

__all__ = [
    "ActivePiece",
    "GamePhase",
    "RenderState",
    "Scoreboard",
    "Renderer",
    "Theme",
    "default_theme",
]
