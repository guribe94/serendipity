"""Unit tests for the demo_input stub game and headless harness.

``StubGame`` is the reference ``GameController`` implementation; these tests
pin its bounds-clamping, pause-gating, and respawn behaviour so the headless
integration test (test_demo_integration.py) sits on verified ground.
"""

from __future__ import annotations

from modern_tetris.demo_input import StubGame, main, run_headless


def test_stub_game_clamps_horizontal_movement_at_walls():
    g = StubGame()
    g.x = 0
    g.move_left()
    assert g.x == 0
    g.x = g.width - 1
    g.move_right()
    assert g.x == g.width - 1


def test_stub_game_clamps_soft_drop_at_floor():
    g = StubGame()
    g.y = g.height - 1
    g.soft_drop()
    assert g.y == g.height - 1


def test_stub_game_rotation_wraps_mod_4():
    g = StubGame()
    for _ in range(4):
        g.rotate_cw()
    assert g.rotation == 0
    g.rotate_ccw()
    assert g.rotation == 3
    g.rotate_180()
    assert g.rotation == 1


def test_stub_game_hard_drop_respawns_at_top_center():
    g = StubGame()
    g.x, g.y, g.rotation = 9, 5, 2
    g.hard_drop()
    assert g.hard_drops == 1
    assert (g.x, g.y, g.rotation) == (g.width // 2 - 1, 0, 0)


def test_stub_game_pause_gates_gameplay_actions():
    g = StubGame()
    g.toggle_pause()
    assert g.paused
    g.move_left()
    g.move_right()
    g.soft_drop()
    g.hard_drop()
    g.rotate_cw()
    g.rotate_ccw()
    g.rotate_180()
    g.hold()
    assert (g.x, g.y, g.rotation, g.hard_drops, g.holds) == (4, 0, 0, 0, 0)
    # Only the pause toggle itself was logged.
    assert g.log == ["pause -> True"]
    g.toggle_pause()
    assert not g.paused


def test_run_headless_is_deterministic():
    a, b = run_headless(), run_headless()
    assert a.log == b.log
    assert (a.x, a.y, a.rotation, a.hard_drops, a.holds) == (
        b.x,
        b.y,
        b.rotation,
        b.hard_drops,
        b.holds,
    )


def test_main_headless_returns_zero(capsys):
    assert main(["--headless"]) == 0
    out = capsys.readouterr().out
    assert "Headless demo finished" in out
