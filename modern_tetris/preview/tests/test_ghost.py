from modern_tetris.preview.ghost import ghost_for
from modern_tetris.preview.pieces import PieceKind, Tetromino


def make_predicate(floor_row=20, walls=None, board_width=10):
    walls = walls or set()

    def is_blocked(cells):
        for c, r in cells:
            if r >= floor_row:
                return True
            if c < 0 or c >= board_width:
                return True
            if (c, r) in walls:
                return True
        return False

    return is_blocked


def test_ghost_drops_to_floor_for_each_kind():
    floor = make_predicate(floor_row=20)
    for kind in PieceKind:
        piece = Tetromino.spawn(kind, board_width=10, spawn_row=0)
        ghost = ghost_for(piece, floor)
        assert ghost.kind == kind
        # The ghost's bottom-most cell should rest on row 19 (floor at 20).
        assert max(r for _, r in ghost.cells) == 19
        # Columns are unchanged — ghost only translates vertically.
        assert {c for c, _ in ghost.cells} == {c for c, _ in piece.cells}


def test_ghost_preserves_relative_shape():
    floor = make_predicate(floor_row=20)
    piece = Tetromino.spawn(PieceKind.T)
    ghost = ghost_for(piece, floor)
    dy = max(r for _, r in ghost.cells) - max(r for _, r in piece.cells)
    expected = frozenset((c, r + dy) for c, r in piece.cells)
    assert ghost.cells == expected


def test_ghost_stops_on_obstacle():
    # O-piece spawn cells are (4,0),(5,0),(4,1),(5,1). Place wall directly under it.
    walls = {(4, 5), (5, 5)}
    pred = make_predicate(floor_row=20, walls=walls)
    piece = Tetromino.spawn(PieceKind.O)
    ghost = ghost_for(piece, pred)
    assert max(r for _, r in ghost.cells) == 4  # rests at row 4, on top of row-5 wall


def test_ghost_equals_active_when_resting_on_floor():
    piece = Tetromino.spawn(PieceKind.I, board_width=10, spawn_row=18)
    # I-piece shape row is 1, so spawn_row=18 puts cells at row 19 — already touching floor=20.
    pred = make_predicate(floor_row=20)
    ghost = ghost_for(piece, pred)
    assert ghost.cells == piece.cells


def test_ghost_when_active_is_already_blocked_returns_active():
    piece = Tetromino.spawn(PieceKind.T)

    def always_blocked(cells):
        return True

    ghost = ghost_for(piece, always_blocked)
    assert ghost.cells == piece.cells
    assert ghost.kind == piece.kind


def test_ghost_max_drop_cap_prevents_runaway():
    piece = Tetromino.spawn(PieceKind.T)

    def never_blocked(cells):
        return False

    ghost = ghost_for(piece, never_blocked, max_drop=10)
    dy = max(r for _, r in ghost.cells) - max(r for _, r in piece.cells)
    assert dy == 10


def test_ghost_with_obstacle_higher_than_floor():
    # Stagger pillar at column 5: floor at row 20, but pillar starts at row 8.
    walls = {(5, r) for r in range(8, 20)}
    pred = make_predicate(floor_row=20, walls=walls)
    # O occupies cols 4 and 5; the column-5 cells will hit the pillar first.
    piece = Tetromino.spawn(PieceKind.O)
    ghost = ghost_for(piece, pred)
    assert max(r for _, r in ghost.cells) == 7


def test_ghost_after_horizontal_translation():
    pred = make_predicate(floor_row=20)
    piece = Tetromino.spawn(PieceKind.T).translated(-3, 0)
    ghost = ghost_for(piece, pred)
    assert max(r for _, r in ghost.cells) == 19
    assert {c for c, _ in ghost.cells} == {c for c, _ in piece.cells}


def test_ghost_after_rotation_via_with_cells():
    # Simulate a Game-Loop rotation by handing the ghost calculation a
    # piece whose cells differ from spawn cells.
    pred = make_predicate(floor_row=20)
    rotated = Tetromino(
        kind=PieceKind.T,
        cells=frozenset({(4, 0), (4, 1), (5, 1), (4, 2)}),  # T rotated right
    )
    ghost = ghost_for(rotated, pred)
    # Rotated T extends 3 rows; bottom cell should rest at row 19.
    assert max(r for _, r in ghost.cells) == 19
    # All cells preserve their column.
    assert {c for c, _ in ghost.cells} == {c for c, _ in rotated.cells}
