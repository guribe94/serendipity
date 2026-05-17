"""Modern Tetris package — core gameplay, rendering, and HUD subsystems.

This package combines two cooperating subsystems:

* The **core gameplay** modules (:mod:`tetris.board`, :mod:`tetris.game`,
  :mod:`tetris.tetromino`, :mod:`tetris.randomizer`, :mod:`tetris.scoring`)
  expose the board, tetromino, randomizer, scoring, and game-loop primitives.
* The **rendering / HUD** modules (:mod:`tetris.renderer`, :mod:`tetris.state`,
  :mod:`tetris.theme`, :mod:`tetris.pieces`, :mod:`tetris.hud`) own the visual
  presentation: playfield, locked/active pieces, ghost projection, NEXT/HOLD
  panel, score/level/lines HUD, and start/paused/game-over overlays.

The renderer is decoupled from gameplay logic; it consumes the
:class:`tetris.state.RenderState` data class so that the game loop, piece
preview, and input modules can populate state independently and have it
drawn here.
"""

from .board import Board
from .game import Game, GameState, LockEvent, gravity_period, LOCK_DELAY, MAX_LOCK_RESETS
from .randomizer import SevenBag
from .renderer import Renderer
from .scoring import (
    LINE_SCORES,
    LINES_PER_LEVEL,
    HARD_DROP_POINTS,
    SOFT_DROP_POINTS,
    Scoring,
    ScoreState,
    TSPIN_MINI_SCORES,
    TSPIN_SCORES,
)
from .state import (
    ActivePiece,
    GamePhase,
    RenderState,
    Scoreboard,
)
from .tetromino import COLORS, KINDS, SHAPES, Tetromino, kick_table
from .theme import Theme, default_theme

__all__ = [
    "ActivePiece",
    "Board",
    "COLORS",
    "Game",
    "GamePhase",
    "GameState",
    "HARD_DROP_POINTS",
    "KINDS",
    "LINES_PER_LEVEL",
    "LINE_SCORES",
    "LOCK_DELAY",
    "LockEvent",
    "MAX_LOCK_RESETS",
    "RenderState",
    "Renderer",
    "SHAPES",
    "ScoreState",
    "Scoreboard",
    "Scoring",
    "SevenBag",
    "SOFT_DROP_POINTS",
    "TSPIN_MINI_SCORES",
    "TSPIN_SCORES",
    "Tetromino",
    "Theme",
    "default_theme",
    "gravity_period",
    "kick_table",
]
