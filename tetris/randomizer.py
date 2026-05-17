"""The 7-bag randomizer.

Each bag is a shuffled permutation of all seven piece kinds; consecutive bags
bound the longest run between two pieces of the same kind to 12 turns.
"""

import random
from collections import deque
from typing import Deque, Optional, Tuple

from .tetromino import KINDS


class SevenBag:
    def __init__(self, seed: Optional[int] = None, preview: int = 5) -> None:
        self._rng = random.Random(seed)
        self._queue: Deque[str] = deque()
        self._preview = max(1, preview)
        self._refill()

    def _refill(self) -> None:
        while len(self._queue) <= self._preview + 7:
            bag = list(KINDS)
            self._rng.shuffle(bag)
            self._queue.extend(bag)

    def next(self) -> str:
        self._refill()
        return self._queue.popleft()

    def peek(self, n: Optional[int] = None) -> Tuple[str, ...]:
        if n is None:
            n = self._preview
        self._refill()
        return tuple(list(self._queue)[:n])
