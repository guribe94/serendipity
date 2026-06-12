"""End-to-end smoke tests for ``tetris.main``.

These exercise the wired-together game, renderer, and input subsystems
(the three Canvas Build deliveries) running through a headless SDL
surface so no display is needed.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from modern_tetris.input import Action  # noqa: E402
from tetris import GameState  # noqa: E402
from tetris.main import GameAdapter, _Effects, build_render_state, run  # noqa: E402
from tetris.state import GamePhase  # noqa: E402
from tetris.game import Game  # noqa: E402


def test_run_renders_n_frames_headlessly(tmp_path):
    """Running the main loop headlessly produces a non-empty PNG snapshot."""
    snapshot = tmp_path / "frame.png"
    rc = run(seed=42, headless=True, frames=5, snapshot_path=str(snapshot))
    assert rc == 0
    assert snapshot.exists()
    assert snapshot.stat().st_size > 1024  # a real image, not a header stub


def test_run_with_scripted_actions_updates_game_state(tmp_path):
    """Scripted MOVE_LEFT + HARD_DROP routes through to the game (piece locks)."""
    snapshot = tmp_path / "after_drop.png"
    rc = run(
        seed=42,
        headless=True,
        frames=2,
        snapshot_path=str(snapshot),
        scripted=[Action.MOVE_LEFT, Action.MOVE_LEFT, Action.HARD_DROP],
    )
    assert rc == 0


def test_adapter_blocks_actions_while_paused():
    """The adapter must drop gameplay actions while paused but accept pause toggles."""
    game = Game(seed=1)
    game.start()
    adapter = GameAdapter(game)
    start_col = game.active.col

    adapter.toggle_pause()
    assert adapter.paused is True
    adapter.move_left()
    assert game.active.col == start_col  # ignored while paused

    adapter.toggle_pause()
    assert adapter.paused is False
    adapter.move_left()
    assert game.active.col == start_col - 1


def test_adapter_drops_actions_when_game_not_playing():
    """Before start() or after game-over the adapter must no-op."""
    game = Game(seed=1)
    adapter = GameAdapter(game)
    # READY: nothing should happen
    adapter.move_left()
    adapter.hard_drop()
    assert game.state is GameState.READY


def test_adapter_rotate_180_applies_two_cw_rotations():
    game = Game(seed=1)
    game.start()
    adapter = GameAdapter(game)
    from tetris.tetromino import Tetromino

    game.active = Tetromino(kind="T", row=10, col=4, rotation=0)
    adapter.rotate_180()
    assert game.active.rotation == 2


def test_build_render_state_maps_game_phase_correctly():
    game = Game(seed=1)
    adapter = GameAdapter(game)
    effects = _Effects()

    # READY -> START phase
    state = build_render_state(adapter, effects)
    assert state.phase is GamePhase.START

    game.start()
    state = build_render_state(adapter, effects)
    assert state.phase is GamePhase.PLAYING
    assert state.active_piece is not None
    assert state.ghost_piece is not None  # fresh spawn is far from the floor
    assert len(state.next_pieces) == 5

    adapter.toggle_pause()
    state = build_render_state(adapter, effects)
    assert state.phase is GamePhase.PAUSED

    adapter.toggle_pause()
    game.state = GameState.GAME_OVER
    state = build_render_state(adapter, effects)
    assert state.phase is GamePhase.GAME_OVER


def test_effects_banner_and_flash_expire_independently():
    effects = _Effects()
    effects.set_banner("TETRIS!", now_ms=1_000)  # expires at 2_100
    effects.set_flash([20, 21], now_ms=1_000)    # expires at 1_220
    effects.tick(1_219)
    assert effects.banner == "TETRIS!"
    assert effects.flash_rows == [20, 21]
    effects.tick(1_220)
    assert effects.flash_rows == []
    assert effects.banner == "TETRIS!"
    effects.tick(2_100)
    assert effects.banner is None


def test_install_hooks_maps_lock_events_to_banners_and_flashes():
    from tetris.game import LockEvent
    from tetris.main import _install_hooks
    from tetris.tetromino import Tetromino

    cases = [
        ([], None, None),
        ([21], None, "SINGLE"),
        ([20, 21], None, "DOUBLE"),
        ([18, 19, 20, 21], None, "TETRIS!"),
        ([21], "full", "T-SPIN SINGLE"),
        ([], "full", "T-SPIN"),
        ([], "mini", "T-SPIN"),
    ]
    for cleared, tspin, expected in cases:
        game = Game(seed=1)
        effects = _Effects()
        _install_hooks(game, effects, lambda: 0)
        ev = LockEvent(
            piece=Tetromino(kind="T", row=0, col=3),
            cleared_lines=list(cleared),
            tspin=tspin,
            score_delta=0,
        )
        game.hooks.on_lock(ev)
        assert effects.banner == expected, (cleared, tspin)
        assert effects.flash_rows == list(cleared)


def test_toggle_pause_is_noop_before_start():
    adapter = GameAdapter(Game(seed=1))
    adapter.toggle_pause()
    assert adapter.paused is False


def test_restart_unpauses_and_starts_a_fresh_round():
    game = Game(seed=1)
    game.start()
    game.hard_drop()
    assert game.scoring.score > 0
    adapter = GameAdapter(game)
    adapter.toggle_pause()
    assert adapter.paused is True
    adapter.restart()
    assert adapter.paused is False
    assert game.is_playing
    assert game.scoring.score == 0


def test_build_render_state_reflects_hold_and_omits_landed_ghost():
    game = Game(seed=1)
    game.start()
    adapter = GameAdapter(game)
    effects = _Effects()

    held_kind = game.active.kind
    game.hold()
    state = build_render_state(adapter, effects)
    assert state.held_piece is not None
    assert state.held_piece.kind == held_kind

    while game.soft_drop():
        pass
    state = build_render_state(adapter, effects)
    assert state.active_piece is not None
    assert state.ghost_piece is None  # ghost coincides with the landed piece


def test_build_render_state_copies_the_board():
    from tetris.board import Board

    game = Game(seed=1)
    game.start()
    state = build_render_state(GameAdapter(game), _Effects())
    state.board[Board.HEIGHT - 1][0] = "X"
    assert game.board.grid[Board.HEIGHT - 1][0] is None


def test_build_render_state_emits_tetris_banner_after_quad_clear():
    """A full 4-line clear fires the on_lock hook and surfaces a TETRIS! banner."""
    from tetris.board import Board
    from tetris.tetromino import Tetromino

    game = Game(seed=1)
    game.start()
    adapter = GameAdapter(game)
    effects = _Effects()
    # install hook the same way tetris.main does
    from tetris.main import _install_hooks

    _install_hooks(game, effects, lambda: 0)

    # Engineer a quad clear: fill bottom 4 rows except col 9, drop vertical I.
    for r in range(Board.HEIGHT - 4, Board.HEIGHT):
        for c in range(Board.WIDTH - 1):
            game.board.grid[r][c] = "X"
    game.active = Tetromino(kind="I", row=0, col=7, rotation=1)
    game.hard_drop()
    assert game.scoring.lines == 4
    assert effects.banner == "TETRIS!"
    state = build_render_state(adapter, effects)
    assert state.message == "TETRIS!"
