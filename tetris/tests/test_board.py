from tetris.board import Board


def test_initial_grid_is_empty_and_correctly_sized():
    b = Board()
    assert len(b.grid) == Board.HEIGHT
    assert all(len(row) == Board.WIDTH for row in b.grid)
    assert all(cell is None for row in b.grid for cell in row)


def test_is_inside_boundaries():
    b = Board()
    assert b.is_inside(0, 0)
    assert b.is_inside(Board.HEIGHT - 1, Board.WIDTH - 1)
    assert not b.is_inside(-1, 0)
    assert not b.is_inside(0, -1)
    assert not b.is_inside(Board.HEIGHT, 0)
    assert not b.is_inside(0, Board.WIDTH)


def test_can_place_inside_empty_grid():
    b = Board()
    assert b.can_place([(0, 0), (5, 5), (Board.HEIGHT - 1, Board.WIDTH - 1)])


def test_can_place_rejects_outside_cells():
    b = Board()
    assert not b.can_place([(0, -1)])
    assert not b.can_place([(Board.HEIGHT, 0)])
    assert not b.can_place([(0, Board.WIDTH)])


def test_can_place_rejects_occupied_cells():
    b = Board()
    b.place([(5, 5)], "I")
    assert not b.can_place([(5, 5)])
    assert b.can_place([(5, 4)])


def test_clear_single_full_row_shifts_above_down():
    b = Board()
    for c in range(Board.WIDTH):
        b.grid[Board.HEIGHT - 1][c] = "X"
    b.grid[Board.HEIGHT - 2][0] = "M"
    cleared = b.clear_full_lines()
    assert cleared == [Board.HEIGHT - 1]
    assert b.grid[Board.HEIGHT - 1][0] == "M"
    assert b.grid[0][0] is None


def test_clear_four_lines_returns_all_indices():
    b = Board()
    for r in range(Board.HEIGHT - 4, Board.HEIGHT):
        for c in range(Board.WIDTH):
            b.grid[r][c] = "I"
    cleared = b.clear_full_lines()
    assert cleared == [Board.HEIGHT - 4, Board.HEIGHT - 3, Board.HEIGHT - 2, Board.HEIGHT - 1]
    assert all(cell is None for row in b.grid for cell in row)


def test_partial_row_is_not_cleared():
    b = Board()
    for c in range(Board.WIDTH - 1):
        b.grid[Board.HEIGHT - 1][c] = "X"
    assert b.clear_full_lines() == []
    assert b.grid[Board.HEIGHT - 1][0] == "X"


def test_non_contiguous_clears_preserve_between_rows():
    b = Board()
    for c in range(Board.WIDTH):
        b.grid[Board.HEIGHT - 1][c] = "X"
        b.grid[Board.HEIGHT - 3][c] = "Y"
    b.grid[Board.HEIGHT - 2][3] = "M"
    cleared = b.clear_full_lines()
    assert sorted(cleared) == [Board.HEIGHT - 3, Board.HEIGHT - 1]
    # The middle row (originally HEIGHT-2 with marker) shifts down one row.
    assert b.grid[Board.HEIGHT - 1][3] == "M"


def test_reset_clears_grid():
    b = Board()
    b.place([(1, 1), (2, 2)], "T")
    b.reset()
    assert all(cell is None for row in b.grid for cell in row)


def test_visible_rows_skips_buffer():
    b = Board()
    rows = list(b.visible_rows())
    assert len(rows) == Board.VISIBLE_HEIGHT
    assert rows[0][0] == Board.BUFFER_HEIGHT


def test_full_buffer_row_is_clearable_too():
    b = Board()
    for c in range(Board.WIDTH):
        b.grid[0][c] = "X"
    assert b.clear_full_lines() == [0]
    assert all(cell is None for cell in b.grid[0])


def test_grid_shape_is_preserved_after_clears():
    b = Board()
    for r in (Board.HEIGHT - 1, Board.HEIGHT - 2):
        for c in range(Board.WIDTH):
            b.grid[r][c] = "X"
    assert len(b.clear_full_lines()) == 2
    assert len(b.grid) == Board.HEIGHT
    assert all(len(row) == Board.WIDTH for row in b.grid)


def test_is_cell_free_for_occupied_and_outside_cells():
    b = Board()
    b.place([(3, 3)], "T")
    assert not b.is_cell_free(3, 3)
    assert b.is_cell_free(3, 4)
    assert not b.is_cell_free(-1, 0)
    assert not b.is_cell_free(0, Board.WIDTH)


def test_can_place_with_no_cells_is_vacuously_true():
    b = Board()
    assert b.can_place([])
