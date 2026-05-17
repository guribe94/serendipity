from tetris.tetromino import COLORS, KINDS, SHAPES, Tetromino, kick_table


def test_kinds_cover_all_seven():
    assert set(KINDS) == set("IOTSZJL")


def test_each_kind_defines_four_rotations_of_four_cells():
    for kind in KINDS:
        rotations = SHAPES[kind]
        assert len(rotations) == 4
        for cells in rotations:
            assert len(cells) == 4
            assert len(set(cells)) == 4  # no duplicates


def test_colors_defined_for_every_kind():
    for kind in KINDS:
        assert kind in COLORS


def test_blocks_offset_by_origin_for_t_spawn():
    t = Tetromino(kind="T", row=5, col=3)
    assert set(t.blocks()) == {(5, 4), (6, 3), (6, 4), (6, 5)}


def test_with_rotation_normalises_modulo_four():
    t = Tetromino(kind="T", row=0, col=0).with_rotation(5)
    assert t.rotation == 1


def test_moved_does_not_mutate_original():
    t = Tetromino(kind="L", row=0, col=0)
    t2 = t.moved(1, 2)
    assert (t.row, t.col) == (0, 0)
    assert (t2.row, t2.col) == (1, 2)


def test_o_piece_blocks_unchanged_across_rotations():
    o = Tetromino(kind="O", row=0, col=0)
    base = set(o.blocks())
    for rot in range(4):
        assert set(o.with_rotation(rot).blocks()) == base


def test_kick_table_o_returns_identity_only():
    assert kick_table("O", 0, 1) == [(0, 0)]
    assert kick_table("O", 1, 2) == [(0, 0)]


def test_kick_table_i_distinct_from_jlstz():
    assert kick_table("I", 0, 1) != kick_table("T", 0, 1)


def test_kick_table_handles_all_eight_transitions():
    for kind in ("T", "L", "I"):
        for from_rot in range(4):
            for direction in (1, -1):
                to_rot = (from_rot + direction) % 4
                kicks = kick_table(kind, from_rot, to_rot)
                assert kicks[0] == (0, 0)
                assert len(kicks) >= 1


def test_i_piece_rotation_cells_span_correct_axes():
    i_horizontal = Tetromino(kind="I", row=0, col=0, rotation=0).blocks()
    rows = {r for r, _ in i_horizontal}
    assert len(rows) == 1  # all in one row

    i_vertical = Tetromino(kind="I", row=0, col=0, rotation=1).blocks()
    cols = {c for _, c in i_vertical}
    assert len(cols) == 1  # all in one column
