import random

import pytest

from modern_tetris.preview.bag import SevenBag
from modern_tetris.preview.pieces import PieceKind


def test_bag_contains_each_piece_once_per_bag():
    bag = SevenBag(rng=random.Random(42))
    pieces = [bag.pop() for _ in range(7)]
    assert sorted(p.value for p in pieces) == sorted(p.value for p in PieceKind)


def test_bag_refills_after_exhaustion():
    bag = SevenBag(rng=random.Random(42))
    first = [bag.pop() for _ in range(7)]
    second = [bag.pop() for _ in range(7)]
    assert sorted(p.value for p in first) == sorted(p.value for p in PieceKind)
    assert sorted(p.value for p in second) == sorted(p.value for p in PieceKind)


def test_bag_never_three_in_a_row():
    # The 7-bag guarantees no piece appears 3 times consecutively: a piece
    # can appear at most once per bag, so XX across a bag boundary is the
    # maximum streak.
    bag = SevenBag(rng=random.Random(42))
    history = [bag.pop() for _ in range(7 * 50)]
    for i in range(len(history) - 2):
        assert not (history[i] == history[i + 1] == history[i + 2]), (
            f"3 identical pieces in a row at index {i}: {history[i].value}"
        )


def test_bag_seed_reproducible():
    a = SevenBag(rng=random.Random(123))
    b = SevenBag(rng=random.Random(123))
    for _ in range(50):
        assert a.pop() == b.pop()


def test_bag_distribution_uniform_over_many_bags():
    bag = SevenBag(rng=random.Random(1))
    counts = {k: 0 for k in PieceKind}
    for _ in range(7 * 1000):
        counts[bag.pop()] += 1
    for k, c in counts.items():
        assert c == 1000, f"{k}: expected 1000, got {c}"


def test_bag_iteration_yields_pieces_indefinitely():
    bag = SevenBag(rng=random.Random(7))
    iterator = iter(bag)
    pieces = [next(iterator) for _ in range(20)]
    assert len(pieces) == 20
    assert all(isinstance(p, PieceKind) for p in pieces)


def test_peek_remaining_does_not_pop():
    bag = SevenBag(rng=random.Random(2))
    bag.pop()  # 6 remaining
    first_peek = bag.peek_remaining()
    second_peek = bag.peek_remaining()
    assert first_peek == second_peek
    assert len(first_peek) == 6


def test_peek_remaining_returns_copy():
    bag = SevenBag(rng=random.Random(2))
    snapshot = bag.peek_remaining()
    snapshot.clear()
    # Mutation of the snapshot must not affect the bag.
    assert len(bag.peek_remaining()) == 7


def test_bag_default_rng_does_not_raise():
    bag = SevenBag()
    pieces = [bag.pop() for _ in range(7)]
    assert sorted(p.value for p in pieces) == sorted(p.value for p in PieceKind)
