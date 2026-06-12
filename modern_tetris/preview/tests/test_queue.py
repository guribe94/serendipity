import random

import pytest

from modern_tetris.preview.bag import SevenBag
from modern_tetris.preview.pieces import PieceKind
from modern_tetris.preview.queue import NextQueue


class CyclicSource:
    """Deterministic piece source that cycles through a fixed sequence."""

    def __init__(self, seq):
        self._seq = list(seq)
        self._i = 0

    def pop(self):
        p = self._seq[self._i % len(self._seq)]
        self._i += 1
        return p


SEQ = [PieceKind.I, PieceKind.O, PieceKind.T, PieceKind.S, PieceKind.Z, PieceKind.J, PieceKind.L]


def test_queue_fills_to_size_on_init():
    q = NextQueue(CyclicSource(SEQ), size=5)
    assert q.peek() == SEQ[:5]


def test_queue_pop_returns_head_and_refills():
    q = NextQueue(CyclicSource(SEQ), size=3)
    assert q.pop() == PieceKind.I
    assert q.peek() == [PieceKind.O, PieceKind.T, PieceKind.S]
    assert q.pop() == PieceKind.O
    assert q.peek() == [PieceKind.T, PieceKind.S, PieceKind.Z]


def test_queue_size_constant_after_many_pops():
    q = NextQueue(CyclicSource(SEQ), size=5)
    for _ in range(100):
        q.pop()
        assert len(q.peek()) == 5


def test_queue_peek_n_clips_to_size():
    q = NextQueue(CyclicSource(SEQ), size=5)
    assert q.peek(0) == []
    assert q.peek(1) == [PieceKind.I]
    assert q.peek(3) == [PieceKind.I, PieceKind.O, PieceKind.T]
    assert q.peek(10) == SEQ[:5]
    assert q.peek() == SEQ[:5]


def test_queue_peek_negative_n_raises():
    q = NextQueue(CyclicSource(SEQ), size=5)
    with pytest.raises(ValueError):
        q.peek(-1)


def test_queue_size_must_be_positive():
    with pytest.raises(ValueError):
        NextQueue(CyclicSource(SEQ), size=0)
    with pytest.raises(ValueError):
        NextQueue(CyclicSource(SEQ), size=-1)


def test_queue_size_property():
    q = NextQueue(SevenBag(rng=random.Random(1)), size=7)
    assert q.size == 7


def test_queue_with_seven_bag_produces_each_piece_eventually():
    q = NextQueue(SevenBag(rng=random.Random(1)), size=5)
    assert len(q.peek()) == 5
    popped = [q.pop() for _ in range(7)]
    assert sorted(p.value for p in popped) == sorted(p.value for p in PieceKind)


def test_queue_peek_does_not_mutate_state():
    q = NextQueue(CyclicSource(SEQ), size=5)
    first = q.peek()
    second = q.peek()
    assert first == second
    # Mutating the returned list does not affect the queue.
    first.clear()
    assert q.peek() == SEQ[:5]


class CountingSource(CyclicSource):
    """CyclicSource that counts how many pieces the queue has drawn."""

    def __init__(self, seq):
        super().__init__(seq)
        self.pops = 0

    def pop(self):
        self.pops += 1
        return super().pop()


def test_queue_size_one_works():
    q = NextQueue(CyclicSource(SEQ), size=1)
    assert q.peek() == [PieceKind.I]
    assert q.pop() == PieceKind.I
    assert q.peek() == [PieceKind.O]


def test_queue_draws_exactly_one_piece_per_pop():
    src = CountingSource(SEQ)
    q = NextQueue(src, size=5)
    assert src.pops == 5  # initial fill draws exactly `size`
    q.pop()
    assert src.pops == 6  # each pop backfills exactly one
    q.peek()
    q.peek(3)
    assert src.pops == 6  # peeking never draws
