"""Auto-refilling next-piece queue.

Holds a fixed-size buffer of upcoming pieces so the preview panel can display
them. Each ``pop`` advances the queue by one and immediately backfills from
the configured piece source, so external observers always see exactly
``size`` pieces.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional, Protocol

from .pieces import PieceKind


class PieceSource(Protocol):
    """Anything that produces a stream of ``PieceKind`` values via ``pop()``."""

    def pop(self) -> PieceKind: ...


class NextQueue:
    """Fixed-size FIFO buffer of upcoming pieces.

    ``size`` should match the number of preview slots the HUD will display
    (5 is the Tetris Guideline default).
    """

    def __init__(self, source: PieceSource, size: int = 5) -> None:
        if size < 1:
            raise ValueError("queue size must be >= 1")
        self._source = source
        self._size = size
        self._queue: Deque[PieceKind] = deque()
        self._refill()

    def _refill(self) -> None:
        while len(self._queue) < self._size:
            self._queue.append(self._source.pop())

    @property
    def size(self) -> int:
        return self._size

    def pop(self) -> PieceKind:
        """Remove and return the head, then refill from the source."""
        head = self._queue.popleft()
        self._refill()
        return head

    def peek(self, n: Optional[int] = None) -> List[PieceKind]:
        """Return up to ``n`` upcoming pieces (default: all visible)."""
        items = list(self._queue)
        if n is None:
            return items
        if n < 0:
            raise ValueError("peek n must be non-negative")
        return items[:n]
