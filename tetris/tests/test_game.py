from tetris.board import Board
from tetris.game import (
    LOCK_DELAY,
    MAX_LOCK_RESETS,
    Game,
    GameState,
    LockEvent,
    gravity_period,
)
from tetris.scoring import LINES_PER_LEVEL, TSPIN_SCORES
from tetris.tetromino import Tetromino


def test_start_transitions_to_playing_and_spawns_piece():
    g = Game(seed=1)
    assert g.state is GameState.READY
    g.start()
    assert g.state is GameState.PLAYING
    assert g.active is not None


def test_move_left_succeeds_when_unobstructed():
    g = Game(seed=1)
    g.start()
    start_col = g.active.col
    assert g.move(-1)
    assert g.active.col == start_col - 1


def test_move_into_wall_is_rejected():
    g = Game(seed=1)
    g.start()
    while g.move(-1):
        pass
    assert not g.move(-1)


def test_soft_drop_moves_one_cell_and_scores():
    g = Game(seed=1)
    g.start()
    start_row = g.active.row
    assert g.soft_drop()
    assert g.active.row == start_row + 1
    assert g.scoring.score == 1


def test_hard_drop_locks_and_spawns_new_piece():
    g = Game(seed=1)
    g.start()
    first_kind = g.active.kind
    g.hard_drop()
    # Active is the next piece, not None.
    assert g.active is not None
    # And the previously-active piece has been written to the board.
    bottom_color_seen = any(
        cell == first_kind
        for row in g.board.grid
        for cell in row
    )
    assert bottom_color_seen


def test_hard_drop_with_empty_board_falls_to_bottom():
    g = Game(seed=1)
    g.start()
    g.active = Tetromino(kind="I", row=0, col=3, rotation=0)
    # Cells live in local row 1; horizontal I should reach bottom (row 21).
    g.hard_drop()
    assert any(cell == "I" for cell in g.board.grid[Board.HEIGHT - 1])


def test_full_row_is_cleared_after_lock():
    g = Game(seed=1)
    g.start()
    # Pre-fill bottom row except column 5.
    g.board.grid[Board.HEIGHT - 1] = ["X"] * Board.WIDTH
    g.board.grid[Board.HEIGHT - 1][5] = None
    # Vertical I dropped into the gap should clear the bottom row.
    g.active = Tetromino(kind="I", row=0, col=3, rotation=1)
    g.hard_drop()
    assert g.scoring.lines == 1
    # The I-piece's top three cells now occupy column 5 in the bottom three rows.
    for r in (Board.HEIGHT - 3, Board.HEIGHT - 2, Board.HEIGHT - 1):
        assert g.board.grid[r][5] == "I"
    for c in range(Board.WIDTH):
        if c != 5:
            assert g.board.grid[Board.HEIGHT - 1][c] is None


def test_tetris_quad_clear_increments_lines_by_four():
    g = Game(seed=1)
    g.start()
    # Fill rows 18..21 except column 9.
    for r in range(Board.HEIGHT - 4, Board.HEIGHT):
        for c in range(Board.WIDTH - 1):
            g.board.grid[r][c] = "X"
    # Vertical I-piece has its cells at col offset 2; origin col=7 places them at col 9.
    g.active = Tetromino(kind="I", row=0, col=7, rotation=1)
    g.hard_drop()
    assert g.scoring.lines == 4


def test_rotation_changes_active_rotation():
    g = Game(seed=1)
    g.start()
    g.active = Tetromino(kind="T", row=10, col=4, rotation=0)
    assert g.rotate(1)
    assert g.active.rotation == 1


def test_rotation_uses_kick_when_against_wall():
    g = Game(seed=1)
    g.start()
    # Position a T-piece flush against the right wall in rotation 0 so a CW
    # rotation would push it out without a kick.
    g.active = Tetromino(kind="T", row=10, col=Board.WIDTH - 3, rotation=0)
    assert g.rotate(1)
    # The kick may have shifted the piece sideways; cells stay inside the board.
    for r, c in g.active.blocks():
        assert g.board.is_inside(r, c)


def test_block_out_when_spawn_position_is_filled():
    g = Game(seed=1)
    g.start()
    # Fill the top of the playfield so no spawn fits.
    for r in range(4):
        for c in range(Board.WIDTH):
            g.board.grid[r][c] = "X"
    g._spawn_piece()
    assert g.is_game_over


def test_game_over_fires_hook():
    g = Game(seed=1)
    called = []
    g.hooks.on_game_over = lambda: called.append(True)
    g.start()
    for r in range(4):
        for c in range(Board.WIDTH):
            g.board.grid[r][c] = "X"
    g._spawn_piece()
    assert called == [True]


def test_ghost_position_lands_above_obstacle():
    g = Game(seed=1)
    g.start()
    # O-piece occupies cols 5-6 at the given origin; planted obstacle is in col 5.
    g.active = Tetromino(kind="O", row=0, col=4, rotation=0)
    g.board.grid[Board.HEIGHT - 5][5] = "X"
    ghost = g.ghost_position()
    assert ghost is not None
    cells = ghost.blocks()
    # Ghost bottom row sits one above the obstacle.
    assert max(r for r, _ in cells) == Board.HEIGHT - 6


def test_next_pieces_returns_requested_count():
    g = Game(seed=1)
    g.start()
    preview = g.next_pieces(5)
    assert len(preview) == 5
    # Idempotent until consumption.
    assert g.next_pieces(5) == preview


def test_hold_swaps_with_held_piece():
    g = Game(seed=1)
    g.start()
    first = g.active.kind
    assert g.hold()
    assert g.held == first
    second = g.active.kind
    assert not g.hold()  # cannot reuse hold on this piece
    g.hard_drop()  # locks second, spawns third
    third = g.active.kind
    assert g.hold()
    assert g.held == third
    assert g.active.kind == first


def test_tick_at_high_dt_applies_gravity():
    g = Game(seed=1, starting_level=1)
    g.start()
    start_row = g.active.row
    g.tick(1.5)  # well over one gravity period at level 1
    assert g.active is not None
    assert g.active.row > start_row


def test_lock_delay_locks_piece_when_grounded():
    g = Game(seed=1, starting_level=1)
    g.start()
    # Hard-place the piece at the floor for predictable lock behaviour.
    while g.soft_drop():
        pass
    grounded_kind = g.active.kind
    g.tick(LOCK_DELAY + 0.05)
    # Either we got a new spawn or the game ended; either way the previous piece locked.
    assert g.active is None or g.active.kind != grounded_kind or g.is_game_over
    # The locked piece's color should now appear on the board.
    assert any(grounded_kind in row for row in g.board.grid)


def test_lock_event_hook_carries_cleared_lines():
    g = Game(seed=1)
    g.start()
    captured = []
    g.hooks.on_lock = lambda ev: captured.append(ev)
    g.board.grid[Board.HEIGHT - 1] = ["X"] * Board.WIDTH
    g.board.grid[Board.HEIGHT - 1][5] = None
    g.active = Tetromino(kind="I", row=0, col=3, rotation=1)
    g.hard_drop()
    assert len(captured) == 1
    ev: LockEvent = captured[0]
    assert ev.cleared_lines == [Board.HEIGHT - 1]
    assert ev.score_delta > 0


def test_score_change_hook_fires_on_line_clear():
    g = Game(seed=1)
    g.start()
    captured = []
    g.hooks.on_score_change = lambda s: captured.append(s)
    g.board.grid[Board.HEIGHT - 1] = ["X"] * Board.WIDTH
    g.board.grid[Board.HEIGHT - 1][5] = None
    g.active = Tetromino(kind="I", row=0, col=3, rotation=1)
    g.hard_drop()
    assert captured  # at least one score change observed
    assert captured[-1] == g.scoring.score


def test_gravity_period_decreases_with_level():
    p1 = gravity_period(1)
    p5 = gravity_period(5)
    p10 = gravity_period(10)
    assert p1 > p5 > p10


def test_no_actions_when_in_ready_state():
    g = Game(seed=1)
    # Game has not started yet.
    assert not g.move(-1)
    assert not g.rotate(1)
    assert not g.soft_drop()
    assert g.hard_drop() == 0
    assert not g.hold()


def test_no_actions_after_game_over():
    g = Game(seed=1)
    g.start()
    g.state = GameState.GAME_OVER
    assert not g.move(-1)
    assert not g.rotate(1)
    assert not g.soft_drop()


def test_lock_out_when_piece_locks_entirely_in_buffer():
    g = Game(seed=1)
    g.start()
    # Build the stack so the next spawn would lock immediately within the buffer.
    # Fill from row 2 (top of visible) up through where the piece would rest.
    for r in range(2, Board.HEIGHT):
        for c in range(Board.WIDTH):
            g.board.grid[r][c] = "X"
    g.active = Tetromino(kind="O", row=0, col=4, rotation=0)
    g.hard_drop()
    assert g.is_game_over


def _build_tspin_slot(g: Game) -> None:
    """Bottom row full except a notch at col 5, with a T-slot above it.

    A T in rotation 2 locked at origin (19, 4) drops its nub into the notch;
    corners (19,4), (21,4), (21,6) are filled so T-spin detection sees 3/4.
    """
    for c in range(Board.WIDTH):
        if c != 5:
            g.board.grid[Board.HEIGHT - 1][c] = "X"
    g.board.grid[Board.HEIGHT - 3][4] = "X"


def test_tspin_full_detected_when_rotation_is_last_action():
    g = Game(seed=1)
    g.start()
    _build_tspin_slot(g)
    captured = []
    g.hooks.on_lock = captured.append
    # T in rotation 1 beside the slot; CW rotation drops it into rotation 2
    # with the zero kick, leaving the piece landed.
    g.active = Tetromino(kind="T", row=Board.HEIGHT - 3, col=4, rotation=1)
    assert g.rotate(1)
    g.hard_drop()  # zero-cell drop: locks in place without clearing the spin flag
    assert len(captured) == 1
    ev: LockEvent = captured[0]
    assert ev.tspin == "full"
    assert ev.cleared_lines == [Board.HEIGHT - 1]
    assert ev.score_delta == TSPIN_SCORES[1]  # level 1, no combo, no back-to-back
    assert g.scoring.lines == 1


def test_tspin_not_awarded_when_piece_falls_after_rotating():
    g = Game(seed=1)
    g.start()
    _build_tspin_slot(g)
    captured = []
    g.hooks.on_lock = captured.append
    # Rotate high above the slot, then hard drop: the descent clears the
    # rotation flag and the slot is unreachable from straight above.
    g.active = Tetromino(kind="T", row=10, col=4, rotation=1)
    assert g.rotate(1)
    g.hard_drop()
    assert len(captured) == 1
    assert captured[0].tspin is None
    assert captured[0].cleared_lines == []


def test_movement_resets_lock_delay_while_landed():
    g = Game(seed=1)
    g.start()
    locks = []
    g.hooks.on_lock = locks.append
    while g.soft_drop():
        pass
    g.tick(LOCK_DELAY * 0.8)
    assert g.move(1)  # landed move resets the lock timer
    g.tick(LOCK_DELAY * 0.8)  # would have locked without the reset
    assert locks == []
    g.tick(LOCK_DELAY * 0.4)  # 0.8 + 0.4 lock-delays since the reset
    assert len(locks) == 1


def test_lock_resets_are_capped_at_max():
    g = Game(seed=1)
    g.start()
    locks = []
    g.hooks.on_lock = locks.append
    while g.soft_drop():
        pass
    for i in range(MAX_LOCK_RESETS):
        assert g.move(1 if i % 2 == 0 else -1)
    g.tick(LOCK_DELAY * 0.8)
    assert g.move(1)  # still moves, but can no longer reset the timer
    g.tick(LOCK_DELAY * 0.4)
    assert len(locks) == 1


def test_hold_with_empty_slot_pulls_next_preview_piece():
    g = Game(seed=1)
    g.start()
    first = g.active.kind
    upcoming = g.next_pieces(1)[0]
    assert g.hold()
    assert g.held == first
    assert g.active.kind == upcoming


def test_hold_hook_reports_previous_and_current_kinds():
    g = Game(seed=1)
    g.start()
    captured = []
    g.hooks.on_hold = lambda prev, cur: captured.append((prev, cur))
    first = g.active.kind
    g.hold()
    assert captured == [(None, first)]


def test_spawn_hook_fires_on_start():
    g = Game(seed=1)
    spawned = []
    g.hooks.on_spawn = lambda piece: spawned.append(piece.kind)
    g.start()
    assert len(spawned) == 1
    assert spawned[0] == g.active.kind


def test_level_change_hook_fires_when_crossing_line_threshold():
    g = Game(seed=1)
    g.start()
    levels = []
    g.hooks.on_level_change = levels.append
    g.scoring.state.lines = LINES_PER_LEVEL - 1  # one line short of level 2
    g.board.grid[Board.HEIGHT - 1] = ["X"] * Board.WIDTH
    g.board.grid[Board.HEIGHT - 1][5] = None
    g.active = Tetromino(kind="I", row=0, col=3, rotation=1)
    g.hard_drop()
    assert levels == [2]


def test_restart_after_game_over_resets_board_and_score():
    g = Game(seed=1)
    g.start()
    g.hard_drop()
    assert g.scoring.score > 0
    g.state = GameState.GAME_OVER
    g.start()
    assert g.is_playing
    assert g.scoring.score == 0
    assert g.held is None
    assert g.active is not None
    assert all(cell is None for row in g.board.grid for cell in row)


def test_starting_level_flows_through_start():
    g = Game(seed=1, starting_level=4)
    g.start()
    assert g.scoring.level == 4


def test_gravity_period_clamps_at_both_extremes():
    # Levels below 1 are clamped up to level 1 (guideline: 1.0 s per cell).
    assert gravity_period(0) == gravity_period(-5) == gravity_period(1) == 1.0
    # Very high levels clamp to one cell per frame at 60 FPS.
    assert gravity_period(200) == 1 / 60


def test_ghost_is_none_before_start_and_matches_landed_piece():
    g = Game(seed=1)
    assert g.ghost_position() is None
    g.start()
    while g.soft_drop():
        pass
    ghost = g.ghost_position()
    assert ghost is not None
    assert ghost.row == g.active.row
    assert set(ghost.blocks()) == set(g.active.blocks())
