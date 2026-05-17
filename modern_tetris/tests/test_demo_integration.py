"""Headless integration smoke test for the input subsystem.

Verifies that ``run_headless()`` wires :class:`InputController` to a
``StubGame`` and produces a sensible end-state when fed a scripted event
sequence.  This is the closest we can get to a CI-grade end-to-end check
without spinning up a display.
"""

from __future__ import annotations

from modern_tetris.demo_input import run_headless


def test_run_headless_executes_scripted_sequence():
    game = run_headless()
    # Hard drop must have fired exactly once, respawning the piece.
    assert game.hard_drops == 1
    # Hold must have fired once.
    assert game.holds == 1
    # We logged a non-trivial number of events.
    assert len(game.log) > 10
    # We saw all major event categories.
    event_kinds = {entry.split(" ")[0] for entry in game.log}
    expected = {
        "move_left",
        "move_right",
        "soft_drop",
        "hard_drop",
        "rotate_cw",
        "rotate_ccw",
        "hold",
    }
    assert expected.issubset(event_kinds), (
        f"Missing event categories: {expected - event_kinds}"
    )


def test_run_headless_respects_board_bounds():
    game = run_headless()
    assert 0 <= game.x < game.width
    assert 0 <= game.y < game.height
