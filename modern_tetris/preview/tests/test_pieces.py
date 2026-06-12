import dataclasses

import pytest

from modern_tetris.preview.pieces import COLORS, SHAPES, PieceKind, Tetromino


# ---------------------------------------------------------------------------
# SHAPES / COLORS table integrity
# ---------------------------------------------------------------------------


def test_every_kind_has_shape_and_color():
    assert set(SHAPES) == set(PieceKind)
    assert set(COLORS) == set(PieceKind)


def test_shapes_have_four_distinct_cells():
    for kind, shape in SHAPES.items():
        assert len(shape) == 4, f"{kind} must have 4 cells"
        assert len(set(shape)) == 4, f"{kind} has duplicate cells"


def test_shapes_fit_in_spawn_bounding_box():
    # Guideline spawn layouts fit a 4-wide, 2-tall box (only I uses the full width).
    for kind, shape in SHAPES.items():
        for c, r in shape:
            assert 0 <= c <= 3, f"{kind} column {c} outside spawn box"
            assert 0 <= r <= 1, f"{kind} row {r} outside spawn box"


def test_shapes_are_orthogonally_connected():
    for kind, shape in SHAPES.items():
        cells = set(shape)
        seen = {next(iter(cells))}
        frontier = list(seen)
        while frontier:
            c, r = frontier.pop()
            for nb in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    frontier.append(nb)
        assert seen == cells, f"{kind} shape is not contiguous"


def test_shapes_are_distinct_between_kinds():
    normalized = set()
    for shape in SHAPES.values():
        min_c = min(c for c, _ in shape)
        min_r = min(r for _, r in shape)
        normalized.add(frozenset((c - min_c, r - min_r) for c, r in shape))
    assert len(normalized) == len(PieceKind)


def test_shape_silhouettes_match_guideline():
    expected = {
        PieceKind.I: (4, 1),
        PieceKind.O: (2, 2),
        PieceKind.T: (3, 2),
        PieceKind.S: (3, 2),
        PieceKind.Z: (3, 2),
        PieceKind.J: (3, 2),
        PieceKind.L: (3, 2),
    }
    for kind, shape in SHAPES.items():
        w = max(c for c, _ in shape) - min(c for c, _ in shape) + 1
        h = max(r for _, r in shape) - min(r for _, r in shape) + 1
        assert (w, h) == expected[kind], f"{kind} bounding box {w}x{h}"


def test_colors_are_valid_rgb_and_distinct():
    assert len(set(COLORS.values())) == len(PieceKind)
    for kind, color in COLORS.items():
        assert len(color) == 3, f"{kind} color must be RGB"
        assert all(0 <= channel <= 255 for channel in color), f"{kind} channel out of range"


# ---------------------------------------------------------------------------
# Tetromino.spawn
# ---------------------------------------------------------------------------


def test_spawn_centers_on_default_board():
    assert {c for c, _ in Tetromino.spawn(PieceKind.I).cells} == {3, 4, 5, 6}
    assert {c for c, _ in Tetromino.spawn(PieceKind.O).cells} == {4, 5}
    for kind in (PieceKind.T, PieceKind.S, PieceKind.Z, PieceKind.J, PieceKind.L):
        assert {c for c, _ in Tetromino.spawn(kind).cells} == {3, 4, 5}, kind


def test_spawn_row_offsets_all_rows():
    base = Tetromino.spawn(PieceKind.T, spawn_row=0)
    raised = Tetromino.spawn(PieceKind.T, spawn_row=-1)
    assert raised.cells == frozenset((c, r - 1) for c, r in base.cells)


def test_spawn_respects_board_width():
    for width in (4, 6, 8, 10, 12):
        piece = Tetromino.spawn(PieceKind.O, board_width=width)
        cols = {c for c, _ in piece.cells}
        assert min(cols) == (width - 2) // 2, f"O not centered on width {width}"
        assert all(0 <= c < width for c in cols)


def test_spawn_preserves_shape_geometry():
    for kind in PieceKind:
        piece = Tetromino.spawn(kind)
        shape = SHAPES[kind]
        min_c = min(c for c, _ in shape)
        min_r = min(r for _, r in shape)
        spawned_min_c = min(c for c, _ in piece.cells)
        spawned_min_r = min(r for _, r in piece.cells)
        renormalized = {
            (c - spawned_min_c, r - spawned_min_r) for c, r in piece.cells
        }
        assert renormalized == {(c - min_c, r - min_r) for c, r in shape}, kind


# ---------------------------------------------------------------------------
# Tetromino methods
# ---------------------------------------------------------------------------


def test_translated_shifts_cells_and_preserves_kind():
    piece = Tetromino.spawn(PieceKind.J)
    moved = piece.translated(2, 3)
    assert moved.kind is piece.kind
    assert moved.cells == frozenset((c + 2, r + 3) for c, r in piece.cells)


def test_translated_zero_returns_same_instance():
    piece = Tetromino.spawn(PieceKind.S)
    assert piece.translated(0, 0) is piece


def test_with_cells_replaces_cells_and_keeps_kind():
    piece = Tetromino.spawn(PieceKind.T)
    rotated = piece.with_cells([(4, 0), (4, 1), (5, 1), (4, 2)])
    assert rotated.kind is PieceKind.T
    assert rotated.cells == frozenset({(4, 0), (4, 1), (5, 1), (4, 2)})
    assert isinstance(rotated.cells, frozenset)


def test_color_property_matches_table():
    for kind in PieceKind:
        assert Tetromino.spawn(kind).color == COLORS[kind]


def test_tetromino_is_immutable():
    piece = Tetromino.spawn(PieceKind.Z)
    with pytest.raises(dataclasses.FrozenInstanceError):
        piece.kind = PieceKind.I


def test_tetromino_equality_is_structural():
    cells = frozenset({(0, 0), (1, 0), (2, 0), (2, 1)})
    a = Tetromino(kind=PieceKind.L, cells=cells)
    b = Tetromino(kind=PieceKind.L, cells=frozenset(cells))
    assert a == b
    assert a is not b
