"""Seven-bag randomizer for tetromino generation.

The 7-bag (also called "random generator") is the Tetris Guideline default:
the seven distinct tetrominoes are shuffled into a bag and dealt out in order.
When the bag empties, a fresh shuffled bag is loaded. This caps the gap
between repeats of any piece at 12 and guarantees uniform long-run frequency,
which keeps the next-piece queue feeling fair rather than streaky.
"""

from __future__ import annotations

import random
from typing import Iterator, List, Optional

from .pieces import PieceKind


class SevenBag:
    """Deterministic 7-bag piece source.

    Pass an explicit ``random.Random`` for reproducible sequences in tests.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._bag: List[PieceKind] = []
        self._refill()

    def _refill(self) -> None:
        self._bag = list(PieceKind)
        self._rng.shuffle(self._bag)

    def pop(self) -> PieceKind:
        """Take the next piece, refilling the bag if it is empty."""
        if not self._bag:
            self._refill()
        return self._bag.pop(0)

    def peek_remaining(self) -> List[PieceKind]:
        """Return the pieces still in the current bag without popping or refilling."""
        return list(self._bag)

    def __iter__(self) -> Iterator[PieceKind]:
        while True:
            yield self.pop()
