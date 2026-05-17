"""PreviewSystem: spawn pipeline, active-piece sync, ghost calculation.

The ``PreviewSystem`` is the single integration surface for the rest of the
game. It owns the next-piece queue (and therefore the spawn pipeline) and
keeps the ghost piece in lockstep with the active piece.

Typical wiring inside the game loop::

    preview = PreviewSystem(queue_size=5)
    active = preview.spawn_next(board.is_blocked)

    # Every time the game loop mutates the active piece (move, rotate,
    # gravity tick) it informs the preview so the ghost stays accurate:
    preview.update_active(new_active, board.is_blocked)

    # On lock:
    preview.clear_active()
    next_active = preview.spawn_next(board.is_blocked)
"""

from __future__ import annotations

from typing import List, Optional

from .bag import SevenBag
from .ghost import CollisionPredicate, ghost_for
from .pieces import PieceKind, Tetromino
from .queue import NextQueue, PieceSource


class PreviewSystem:
    """Coordinates the next-piece queue, the active piece, and the ghost piece."""

    def __init__(
        self,
        *,
        queue_size: int = 5,
        bag: Optional[PieceSource] = None,
        board_width: int = 10,
        spawn_row: int = 0,
    ) -> None:
        self._bag: PieceSource = bag if bag is not None else SevenBag()
        self._queue = NextQueue(self._bag, size=queue_size)
        self._board_width = board_width
        self._spawn_row = spawn_row
        self._active: Optional[Tetromino] = None
        self._ghost: Optional[Tetromino] = None

    @property
    def active(self) -> Optional[Tetromino]:
        return self._active

    @property
    def ghost(self) -> Optional[Tetromino]:
        return self._ghost

    @property
    def queue_size(self) -> int:
        return self._queue.size

    def upcoming(self, n: Optional[int] = None) -> List[PieceKind]:
        """Peek upcoming pieces for the preview panel."""
        return self._queue.peek(n)

    def spawn_next(self, is_blocked: CollisionPredicate) -> Tetromino:
        """Advance the queue, set the head piece as active, and recompute the ghost.

        Returns the new active Tetromino. ``is_blocked`` is the game's
        collision predicate; it is used immediately to position the ghost.
        """
        kind = self._queue.pop()
        self._active = Tetromino.spawn(
            kind,
            board_width=self._board_width,
            spawn_row=self._spawn_row,
        )
        self._ghost = ghost_for(self._active, is_blocked)
        return self._active

    def update_active(
        self,
        active: Tetromino,
        is_blocked: CollisionPredicate,
    ) -> None:
        """Synchronize with an externally-mutated active piece and recompute the ghost.

        Call this from the game loop whenever movement, rotation, or gravity
        changes the active piece's cells.
        """
        self._active = active
        self._ghost = ghost_for(active, is_blocked)

    def clear_active(self) -> None:
        """Drop active-piece state (e.g. on lock or game-over)."""
        self._active = None
        self._ghost = None

    def reset(
        self,
        bag: Optional[PieceSource] = None,
        *,
        queue_size: Optional[int] = None,
    ) -> None:
        """Reset queue and active state, optionally with a fresh bag / new size."""
        self._bag = bag if bag is not None else SevenBag()
        size = queue_size if queue_size is not None else self._queue.size
        self._queue = NextQueue(self._bag, size=size)
        self.clear_active()
