import random

import pytest

from modern_tetris.preview.bag import SevenBag
from modern_tetris.preview.pieces import PieceKind, Tetromino
from modern_tetris.preview.system import PreviewSystem


def floor_predicate(floor_row=20, walls=None, board_width=10):
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


def test_spawn_next_sets_active_and_ghost():
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(0)))
    floor = floor_predicate()
    piece = p.spawn_next(floor)
    assert isinstance(piece, Tetromino)
    assert p.active is piece
    assert p.ghost is not None
    assert p.ghost.kind == piece.kind


def test_spawn_next_pops_queue_head_and_refills():
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(0)))
    floor = floor_predicate()
    queue_before = p.upcoming()
    spawned = p.spawn_next(floor)
    queue_after = p.upcoming()
    # Spawned piece should be the head of the previous queue.
    assert spawned.kind == queue_before[0]
    # Queue should have shifted by one, same size.
    assert queue_after[:-1] == queue_before[1:]
    assert len(queue_after) == p.queue_size


def test_update_active_recomputes_ghost():
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(0)))
    floor = floor_predicate()
    active = p.spawn_next(floor)
    moved = active.translated(0, 5)
    p.update_active(moved, floor)
    assert p.active is moved
    assert p.ghost is not None
    # Ghost rests on row 19 (floor=20).
    assert max(r for _, r in p.ghost.cells) == 19


def test_update_active_with_replacement_tetromino():
    """The game loop may replace the active piece (e.g. after rotation)."""
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(0)))
    floor = floor_predicate()
    p.spawn_next(floor)
    external = Tetromino(kind=PieceKind.T, cells=frozenset({(4, 0), (3, 1), (4, 1), (5, 1)}))
    p.update_active(external, floor)
    assert p.active is external
    assert p.ghost is not None
    assert p.ghost.kind == PieceKind.T


def test_clear_active_drops_state():
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(0)))
    p.spawn_next(floor_predicate())
    p.clear_active()
    assert p.active is None
    assert p.ghost is None


def test_default_queue_size_is_five():
    p = PreviewSystem()
    assert p.queue_size == 5
    assert len(p.upcoming()) == 5


def test_custom_queue_size():
    p = PreviewSystem(queue_size=7)
    assert p.queue_size == 7
    assert len(p.upcoming()) == 7


def test_upcoming_n_clips_correctly():
    p = PreviewSystem(queue_size=5)
    assert len(p.upcoming(3)) == 3
    assert p.upcoming(0) == []
    assert len(p.upcoming(100)) == 5


def test_reset_replenishes_queue_and_clears_active():
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(0)))
    p.spawn_next(floor_predicate())
    p.reset()
    assert p.active is None
    assert p.ghost is None
    assert len(p.upcoming()) == 5


def test_reset_with_new_bag_changes_sequence():
    floor = floor_predicate()
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(0)))
    first_seq = [p.spawn_next(floor).kind for _ in range(7)]
    p.reset(bag=SevenBag(rng=random.Random(99)))
    second_seq = [p.spawn_next(floor).kind for _ in range(7)]
    # Different seeds → different ordering (overwhelmingly likely).
    assert first_seq != second_seq


def test_deterministic_with_same_seed():
    floor = floor_predicate()
    p1 = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(42)))
    p2 = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(42)))
    for _ in range(20):
        a = p1.spawn_next(floor)
        b = p2.spawn_next(floor)
        assert a.kind == b.kind
        assert a.cells == b.cells
        assert p1.upcoming() == p2.upcoming()


def test_full_spawn_drop_cycle_integration():
    """Simulate a realistic game cycle: spawn -> hard drop -> spawn -> ..."""
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(7)))
    locked: set[tuple[int, int]] = set()

    def is_blocked(cells):
        for c, r in cells:
            if c < 0 or c >= 10 or r >= 20:
                return True
            if (c, r) in locked:
                return True
        return False

    for _ in range(15):
        active = p.spawn_next(is_blocked)
        assert active is p.active
        ghost = p.ghost
        assert ghost is not None
        assert ghost.kind == active.kind
        # Hard drop: lock ghost cells.
        for c, r in ghost.cells:
            locked.add((c, r))
        p.clear_active()
        # Queue always has queue_size visible.
        assert len(p.upcoming()) == p.queue_size


def test_ghost_updates_when_walls_change_between_calls():
    """Mid-game, locked blocks accumulate — passing a fresh predicate must refresh ghost."""
    p = PreviewSystem(queue_size=5, bag=SevenBag(rng=random.Random(11)))
    active = p.spawn_next(floor_predicate())
    bottom_initial = max(r for _, r in p.ghost.cells)
    # Build a wall directly below the active piece.
    cols = {c for c, _ in active.cells}
    walls = {(c, r) for r in range(5, 20) for c in cols}
    p.update_active(active, floor_predicate(walls=walls))
    bottom_after = max(r for _, r in p.ghost.cells)
    assert bottom_after < bottom_initial


def test_active_property_is_none_initially():
    p = PreviewSystem(queue_size=5)
    assert p.active is None
    assert p.ghost is None
    # But queue is populated up front so the HUD has something to show.
    assert len(p.upcoming()) == 5
