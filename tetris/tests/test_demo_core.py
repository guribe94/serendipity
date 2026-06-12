"""Tests for the text-only gameplay demo in ``tetris.demo_core``."""

from tetris.board import Board
from tetris.demo_core import main, render
from tetris.game import Game
from tetris.tetromino import KINDS


def _fresh_game() -> Game:
    game = Game(seed=7)
    game.start()
    return game


def test_render_emits_full_board_with_buffer_markers():
    game = _fresh_game()
    lines = render(game).splitlines()

    body = lines[: Board.HEIGHT]
    assert len(body) == Board.HEIGHT
    # Hidden buffer rows use ':' walls, visible rows use '|'.
    for r, line in enumerate(body):
        expected = ":" if r < Board.BUFFER_HEIGHT else "|"
        assert line[0] == expected and line[-1] == expected
        assert len(line) == Board.WIDTH + 2

    assert lines[Board.HEIGHT] == "+" + "-" * Board.WIDTH + "+"


def test_render_reports_score_state_and_next_queue():
    game = _fresh_game()
    lines = render(game).splitlines()

    status = lines[Board.HEIGHT + 1]
    assert "score=0" in status
    assert "level=1" in status
    assert "lines=0" in status
    assert "state=playing" in status

    next_line = lines[Board.HEIGHT + 2]
    assert next_line.startswith("next: ")
    kinds = next_line.removeprefix("next: ").split()
    assert len(kinds) == 5
    assert all(k in KINDS for k in kinds)


def test_render_draws_active_piece_and_ghost_dots():
    game = _fresh_game()
    body = render(game).splitlines()[: Board.HEIGHT]
    grid_text = "".join(body)
    # On an empty board the freshly spawned piece and its ghost never
    # overlap, so each contributes exactly four cells.
    assert grid_text.count(game.active.kind) == 4
    assert grid_text.count(".") == 4


def test_render_lists_held_piece_only_after_hold():
    game = _fresh_game()
    assert not any(line.startswith("held: ") for line in render(game).splitlines())
    held_kind = game.active.kind
    game.hold()
    held_lines = [l for l in render(game).splitlines() if l.startswith("held: ")]
    assert held_lines == [f"held: {held_kind}"]


def test_main_script_clears_a_tetris(capsys):
    main()
    out = capsys.readouterr().out
    assert "Initial spawn:" in out
    assert "After five hard drops:" in out
    # The scripted I-piece drop into the prepared well clears exactly 4 lines.
    assert "cleared 4 lines," in out
