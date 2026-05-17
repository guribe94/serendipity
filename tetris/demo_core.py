"""Run a short scripted game to verify the core gameplay subsystem end-to-end.

Usage:
    python -m tetris.demo_core

This is the text-only sibling to :mod:`tetris.demo` (which renders pygame
snapshots). It exercises board, game, scoring, and tetromino logic without
any rendering dependency.
"""

from .board import Board
from .game import Game
from .tetromino import Tetromino


def render(game: Game) -> str:
    grid = [row[:] for row in game.board.grid]
    if game.active is not None:
        ghost = game.ghost_position()
        if ghost is not None:
            for r, c in ghost.blocks():
                if game.board.is_inside(r, c) and grid[r][c] is None:
                    grid[r][c] = "."
        for r, c in game.active.blocks():
            if game.board.is_inside(r, c):
                grid[r][c] = game.active.kind

    lines = []
    for r in range(Board.HEIGHT):
        prefix = "|" if r >= Board.BUFFER_HEIGHT else ":"
        body = "".join(cell if cell else " " for cell in grid[r])
        lines.append(f"{prefix}{body}{prefix}")
    lines.append("+" + "-" * Board.WIDTH + "+")
    lines.append(
        f"score={game.scoring.score} level={game.scoring.level} "
        f"lines={game.scoring.lines} state={game.state.value}"
    )
    lines.append("next: " + " ".join(game.next_pieces(5)))
    if game.held:
        lines.append(f"held: {game.held}")
    return "\n".join(lines)


def main() -> None:
    game = Game(seed=7)
    game.start()
    print("Initial spawn:", game.active.kind)
    print(render(game))
    print()

    # Drop the first five pieces straight down with hard drops.
    for _ in range(5):
        game.hard_drop()
    print("After five hard drops:")
    print(render(game))
    print()

    # Engineer a tetris: prefill the bottom four rows except column 0 and
    # drop a vertical I-piece into the slot. Rotation-1 I has cells at col
    # offset 2, so origin col=-2 places those cells in absolute column 0.
    for r in range(Board.HEIGHT - 4, Board.HEIGHT):
        for c in range(1, Board.WIDTH):
            game.board.grid[r][c] = "X"
    game.active = Tetromino(kind="I", row=0, col=-2, rotation=1)
    score_before = game.scoring.score
    lines_before = game.scoring.lines
    game.hard_drop()
    print(
        "After scripted Tetris clear:",
        f"cleared {game.scoring.lines - lines_before} lines,",
        f"score delta = {game.scoring.score - score_before}",
    )
    print(render(game))


if __name__ == "__main__":
    main()
