"""The Tetris playfield grid.

The board is 10 columns wide and 22 rows tall: the top 2 rows form a hidden
buffer where pieces spawn and only become game-over relevant once a locked
piece cannot leave the buffer (lock out) or a fresh spawn cannot fit (block out).
Row 0 is the top of the buffer; row 21 is the bottom of the visible field.
"""

from typing import Iterable, List, Optional, Tuple


Cell = Optional[str]
Coord = Tuple[int, int]


class Board:
    WIDTH = 10
    VISIBLE_HEIGHT = 20
    BUFFER_HEIGHT = 2
    HEIGHT = VISIBLE_HEIGHT + BUFFER_HEIGHT

    def __init__(self) -> None:
        self.grid: List[List[Cell]] = [
            [None] * Board.WIDTH for _ in range(Board.HEIGHT)
        ]

    def reset(self) -> None:
        for row in self.grid:
            for c in range(Board.WIDTH):
                row[c] = None

    def is_inside(self, row: int, col: int) -> bool:
        return 0 <= row < Board.HEIGHT and 0 <= col < Board.WIDTH

    def is_cell_free(self, row: int, col: int) -> bool:
        if not self.is_inside(row, col):
            return False
        return self.grid[row][col] is None

    def can_place(self, cells: Iterable[Coord]) -> bool:
        return all(self.is_cell_free(r, c) for r, c in cells)

    def place(self, cells: Iterable[Coord], kind: str) -> None:
        for r, c in cells:
            self.grid[r][c] = kind

    def clear_full_lines(self) -> List[int]:
        """Remove every fully-filled row and return their original indices.

        Surviving rows keep their relative order; new empty rows are inserted
        at the top so the grid stays at HEIGHT rows.
        """
        cleared = [
            r for r in range(Board.HEIGHT)
            if all(self.grid[r][c] is not None for c in range(Board.WIDTH))
        ]
        if not cleared:
            return []

        kept = [self.grid[r] for r in range(Board.HEIGHT) if r not in cleared]
        new_top = [[None] * Board.WIDTH for _ in cleared]
        self.grid = new_top + kept
        return cleared

    def is_row_visible(self, row: int) -> bool:
        return Board.BUFFER_HEIGHT <= row < Board.HEIGHT

    def visible_rows(self):
        for r in range(Board.BUFFER_HEIGHT, Board.HEIGHT):
            yield r, self.grid[r]
