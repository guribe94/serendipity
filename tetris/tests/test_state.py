"""Tests for the renderer-facing data interfaces in ``tetris.state``."""

import dataclasses

import pytest

from tetris.state import (
    BOARD_COLS,
    BOARD_ROWS,
    HIDDEN_ROWS,
    TOTAL_ROWS,
    ActivePiece,
    GamePhase,
    RenderState,
    Scoreboard,
)


def test_board_constants_are_consistent():
    assert BOARD_COLS == 10
    assert BOARD_ROWS == 20
    assert TOTAL_ROWS == BOARD_ROWS + HIDDEN_ROWS


def test_game_phase_has_four_states_with_stable_values():
    assert {p.value for p in GamePhase} == {"start", "playing", "paused", "game_over"}
    # str-enum round trip: the value can be used to look the phase back up.
    assert GamePhase("playing") is GamePhase.PLAYING


def test_active_piece_shifted_translates_all_cells():
    piece = ActivePiece(kind="T", cells=[(4, 0), (3, 1), (4, 1), (5, 1)])
    moved = piece.shifted(2, 5)
    assert list(moved.cells) == [(6, 5), (5, 6), (6, 6), (7, 6)]
    assert moved.kind == "T"


def test_active_piece_shifted_preserves_color_key_and_original():
    piece = ActivePiece(kind="I", cells=[(0, 0)], color_key="ghost")
    moved = piece.shifted(1, 1)
    assert moved.color_key == "ghost"
    # Original is untouched.
    assert list(piece.cells) == [(0, 0)]


def test_active_piece_is_immutable():
    piece = ActivePiece(kind="T", cells=[(0, 0)])
    with pytest.raises(dataclasses.FrozenInstanceError):
        piece.kind = "Z"


def test_scoreboard_defaults_and_immutability():
    sb = Scoreboard()
    assert (sb.score, sb.level, sb.lines) == (0, 1, 0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        sb.score = 100


def test_render_state_default_board_dimensions():
    state = RenderState()
    assert len(state.board) == TOTAL_ROWS
    assert all(len(row) == BOARD_COLS for row in state.board)
    assert all(cell is None for row in state.board for cell in row)
    assert state.phase is GamePhase.START
    assert state.active_piece is None
    assert state.next_pieces == []


def test_render_states_do_not_share_a_board():
    a = RenderState()
    b = RenderState()
    a.board[0][0] = "T"
    assert b.board[0][0] is None


def test_empty_board_resets_in_place():
    state = RenderState()
    board_ref = state.board
    state.board[5][3] = "I"
    state.board[TOTAL_ROWS - 1][BOARD_COLS - 1] = "Z"
    state.empty_board()
    assert state.board is board_ref  # same object, mutated in place
    assert all(cell is None for row in state.board for cell in row)
