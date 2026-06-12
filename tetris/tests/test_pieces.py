"""Tests for the spawn-position piece layouts in ``tetris.pieces``."""

import pytest

from tetris.pieces import all_kinds, spawn_piece
from tetris.state import BOARD_COLS, HIDDEN_ROWS
from tetris.tetromino import KINDS, Tetromino


def test_all_kinds_covers_the_seven_tetrominoes():
    assert sorted(all_kinds()) == sorted("IOTSZJL")


def test_spawn_piece_has_four_unique_cells_for_every_kind():
    for kind in all_kinds():
        piece = spawn_piece(kind)
        assert piece.kind == kind
        assert len(piece.cells) == 4
        assert len(set(piece.cells)) == 4


def test_spawn_cells_sit_inside_the_hidden_spawn_zone():
    for kind in all_kinds():
        for col, row in spawn_piece(kind).cells:
            assert 0 <= col < BOARD_COLS
            assert 0 <= row < HIDDEN_ROWS


def test_spawn_layouts_match_core_tetromino_spawn_geometry():
    """pieces.py duplicates the core SHAPES; the copies must agree.

    The core game spawns ``Tetromino(kind, row=0, col=3, rotation=0)``;
    its (row, col) blocks transposed to (col, row) must equal the
    renderer-side spawn cells.
    """
    for kind in KINDS:
        core = Tetromino(kind=kind, row=0, col=3, rotation=0)
        expected = {(c, r) for r, c in core.blocks()}
        assert set(spawn_piece(kind).cells) == expected, kind


def test_spawn_piece_returns_independent_cell_lists():
    first = spawn_piece("T")
    first.cells.append((9, 9))  # the list is a copy; mutating it is harmless
    assert len(spawn_piece("T").cells) == 4


def test_spawn_piece_rejects_unknown_kind():
    with pytest.raises(KeyError):
        spawn_piece("Q")
