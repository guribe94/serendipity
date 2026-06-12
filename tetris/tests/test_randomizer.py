from collections import Counter

from tetris.randomizer import SevenBag
from tetris.tetromino import KINDS


def test_first_seven_pieces_form_a_full_bag():
    bag = SevenBag(seed=1)
    pieces = [bag.next() for _ in range(7)]
    assert sorted(pieces) == sorted(KINDS)


def test_each_subsequent_bag_is_also_a_permutation():
    bag = SevenBag(seed=1)
    for _ in range(5):
        chunk = [bag.next() for _ in range(7)]
        assert sorted(chunk) == sorted(KINDS)


def test_peek_does_not_consume():
    bag = SevenBag(seed=2, preview=5)
    preview = bag.peek(5)
    actual = [bag.next() for _ in range(5)]
    assert preview == tuple(actual)


def test_same_seed_yields_same_sequence():
    a = SevenBag(seed=99)
    b = SevenBag(seed=99)
    seq_a = [a.next() for _ in range(40)]
    seq_b = [b.next() for _ in range(40)]
    assert seq_a == seq_b


def test_different_seeds_diverge():
    a = [SevenBag(seed=1).next() for _ in range(20)]
    b = [SevenBag(seed=2).next() for _ in range(20)]
    assert a != b


def test_long_run_keeps_bag_proportions_balanced():
    bag = SevenBag(seed=42)
    counts = Counter(bag.next() for _ in range(7 * 50))
    assert all(v == 50 for v in counts.values())


def test_peek_default_uses_configured_preview_length():
    bag = SevenBag(seed=3, preview=6)
    assert len(bag.peek()) == 6


def test_same_kind_never_more_than_twelve_pieces_apart():
    """7-bag guarantee: at most 12 other pieces between two of the same kind."""
    bag = SevenBag(seed=11)
    last_seen = {}
    for i in range(7 * 40):
        kind = bag.next()
        if kind in last_seen:
            assert i - last_seen[kind] <= 13
        last_seen[kind] = i


def test_preview_is_clamped_to_at_least_one():
    bag = SevenBag(seed=5, preview=0)
    assert len(bag.peek()) == 1


def test_unseeded_bag_still_emits_full_permutations():
    bag = SevenBag()
    assert sorted(bag.next() for _ in range(7)) == sorted(KINDS)


def test_peek_stays_full_length_while_consuming():
    bag = SevenBag(seed=8, preview=5)
    for _ in range(100):
        assert len(bag.peek(5)) == 5
        bag.next()
