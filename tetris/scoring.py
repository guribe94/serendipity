"""Tetris-guideline scoring.

Tracks score, total lines cleared, current level, combo counter, and the
back-to-back chain. Levels advance every LINES_PER_LEVEL lines.
"""

from dataclasses import dataclass
from typing import Optional


LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}
TSPIN_SCORES = {0: 400, 1: 800, 2: 1200, 3: 1600}
TSPIN_MINI_SCORES = {0: 100, 1: 200, 2: 400}
LINES_PER_LEVEL = 10
SOFT_DROP_POINTS = 1
HARD_DROP_POINTS = 2


@dataclass
class ScoreState:
    score: int = 0
    lines: int = 0
    level: int = 1
    combo: int = -1
    last_was_difficult: bool = False
    singles: int = 0
    doubles: int = 0
    triples: int = 0
    tetrises: int = 0
    tspins: int = 0
    tspin_minis: int = 0
    max_combo: int = 0


class Scoring:
    def __init__(self, starting_level: int = 1) -> None:
        self.state = ScoreState(level=max(1, starting_level))

    @property
    def score(self) -> int:
        return self.state.score

    @property
    def lines(self) -> int:
        return self.state.lines

    @property
    def level(self) -> int:
        return self.state.level

    @property
    def stats(self) -> dict:
        return {
            "singles": self.state.singles,
            "doubles": self.state.doubles,
            "triples": self.state.triples,
            "tetrises": self.state.tetrises,
            "tspins": self.state.tspins,
            "tspin_minis": self.state.tspin_minis,
            "max_combo": self.state.max_combo,
        }

    def add_soft_drop(self, cells: int) -> int:
        delta = SOFT_DROP_POINTS * max(0, cells)
        self.state.score += delta
        return delta

    def add_hard_drop(self, cells: int) -> int:
        delta = HARD_DROP_POINTS * max(0, cells)
        self.state.score += delta
        return delta

    def add_line_clear(self, lines_cleared: int, tspin: Optional[str] = None) -> int:
        """Apply scoring for one lock. Returns the score delta added."""
        delta = 0

        if tspin == "full":
            base = TSPIN_SCORES.get(lines_cleared, 0)
        elif tspin == "mini":
            base = TSPIN_MINI_SCORES.get(lines_cleared, 0)
        else:
            base = LINE_SCORES.get(lines_cleared, 0)
        delta += base * self.state.level

        is_difficult = lines_cleared > 0 and (
            lines_cleared == 4 or tspin in ("full", "mini")
        )
        if lines_cleared > 0:
            if is_difficult and self.state.last_was_difficult:
                delta = (delta * 3) // 2
            self.state.last_was_difficult = is_difficult
            self.state.combo += 1
            if self.state.combo > 0:
                delta += 50 * self.state.combo * self.state.level
        else:
            self.state.combo = -1
            # last_was_difficult stays — only a non-difficult clear resets it.

        self.state.score += delta
        self.state.lines += lines_cleared
        new_level = max(self.state.level, self.state.lines // LINES_PER_LEVEL + 1)
        self.state.level = new_level

        # Additive clear-type bookkeeping (does not affect score/level/lines).
        if lines_cleared == 1:
            self.state.singles += 1
        elif lines_cleared == 2:
            self.state.doubles += 1
        elif lines_cleared == 3:
            self.state.triples += 1
        elif lines_cleared == 4:
            self.state.tetrises += 1
        if tspin == "full":
            self.state.tspins += 1
        elif tspin == "mini":
            self.state.tspin_minis += 1
        self.state.max_combo = max(self.state.max_combo, self.state.combo)
        return delta
