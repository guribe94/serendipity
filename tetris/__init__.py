"""Modern Tetris core gameplay subsystem.

Exposes the board, tetromino, randomizer, scoring, and game-loop primitives
that the rendering, input, and preview subsystems consume.
"""

from .board import Board
from .game import Game, GameState, LockEvent, gravity_period, LOCK_DELAY, MAX_LOCK_RESETS
from .randomizer import SevenBag
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
from .tetromino import COLORS, KINDS, SHAPES, Tetromino, kick_table

__all__ = [
    "Board",
    "COLORS",
    "Game",
    "GameState",
    "HARD_DROP_POINTS",
    "KINDS",
    "LINES_PER_LEVEL",
    "LINE_SCORES",
    "LOCK_DELAY",
    "LockEvent",
    "MAX_LOCK_RESETS",
    "SHAPES",
    "ScoreState",
    "Scoring",
    "SevenBag",
    "SOFT_DROP_POINTS",
    "TSPIN_MINI_SCORES",
    "TSPIN_SCORES",
    "Tetromino",
    "gravity_period",
    "kick_table",
]
