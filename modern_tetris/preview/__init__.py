"""Preview and placement-aid subsystem for Modern Tetris.

Public API:

* :class:`PreviewSystem` — spawn pipeline + ghost + next-piece queue, the
  single integration surface for the game loop.
* :class:`SevenBag` — Tetris Guideline 7-bag randomizer.
* :class:`NextQueue` — auto-refilling buffer of upcoming pieces.
* :func:`ghost_for` — pure function: active piece + collision predicate → ghost.
* :class:`Tetromino`, :class:`PieceKind`, :data:`SHAPES`, :data:`COLORS` —
  shared piece model so other subsystems can interoperate.
* :class:`PreviewRenderer` / :class:`NullRenderer` / :class:`PygameRenderer`
  — renderer protocol and reference implementations.
"""

from .bag import SevenBag
from .ghost import CollisionPredicate, ghost_for
from .pieces import COLORS, SHAPES, Cell, PieceKind, Tetromino
from .queue import NextQueue, PieceSource
from .rendering import NullRenderer, PreviewRenderer, PygameRenderer
from .system import PreviewSystem

__all__ = [
    "Cell",
    "COLORS",
    "CollisionPredicate",
    "NextQueue",
    "NullRenderer",
    "PieceKind",
    "PieceSource",
    "PreviewRenderer",
    "PreviewSystem",
    "PygameRenderer",
    "SHAPES",
    "SevenBag",
    "Tetromino",
    "ghost_for",
]
