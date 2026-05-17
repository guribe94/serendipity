"""Playable Tetris entry point.

Wires together the three Canvas-Build subsystems already in this repo:

* :mod:`tetris.game` — gravity, locking, scoring, hold, 7-bag spawning.
* :mod:`tetris.renderer` — pygame rendering of board, HUD, overlays.
* :mod:`modern_tetris.input` — DAS/ARR keyboard controller.

Run it with::

    python -m tetris.main                       # opens a pygame window
    SDL_VIDEODRIVER=dummy python -m tetris.main --headless --frames 60

Headless mode (``--headless``) uses SDL's dummy driver and is what the
delivery verification exercises end-to-end without a display.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import pygame

from modern_tetris.input import (
    Action,
    InputController,
    KeyBindings,
    TimingConfig,
)
from tetris import (
    ActivePiece,
    Game,
    GamePhase,
    GameState,
    LockEvent,
    RenderState,
    Renderer,
    Scoreboard,
    Tetromino,
)
from tetris.pieces import spawn_piece


# ---------------------------------------------------------------------------
# Game adapter
# ---------------------------------------------------------------------------


class GameAdapter:
    """Adapt :class:`tetris.Game` to the ``GameController`` Protocol.

    Owns the pause flag (the core ``Game`` has READY/PLAYING/GAME_OVER but
    no PAUSED state — pausing is a host concern). Routes player actions
    into the game only while it is playing and unpaused.
    """

    def __init__(self, game: Game) -> None:
        self.game = game
        self.paused: bool = False

    def _gameplay_allowed(self) -> bool:
        return self.game.is_playing and not self.paused

    def move_left(self) -> None:
        if self._gameplay_allowed():
            self.game.move(-1)

    def move_right(self) -> None:
        if self._gameplay_allowed():
            self.game.move(1)

    def soft_drop(self) -> None:
        if self._gameplay_allowed():
            self.game.soft_drop()

    def hard_drop(self) -> None:
        if self._gameplay_allowed():
            self.game.hard_drop()

    def rotate_cw(self) -> None:
        if self._gameplay_allowed():
            self.game.rotate(1)

    def rotate_ccw(self) -> None:
        if self._gameplay_allowed():
            self.game.rotate(-1)

    def rotate_180(self) -> None:
        if self._gameplay_allowed():
            self.game.rotate(1)
            self.game.rotate(1)

    def hold(self) -> None:
        if self._gameplay_allowed():
            self.game.hold()

    def toggle_pause(self) -> None:
        # Pause only meaningful while a round is alive; ignored on start/game-over.
        if self.game.is_playing or self.paused:
            self.paused = not self.paused

    def restart(self) -> None:
        self.paused = False
        self.game.start()


# ---------------------------------------------------------------------------
# Banner state captured from gameplay events
# ---------------------------------------------------------------------------


_CLEAR_BANNERS = {1: "SINGLE", 2: "DOUBLE", 3: "TRIPLE", 4: "TETRIS!"}


@dataclass
class _Effects:
    """Transient HUD state owned by the runner (banner + clear flash)."""

    banner: Optional[str] = None
    banner_until_ms: int = 0
    flash_rows: List[int] = field(default_factory=list)
    flash_until_ms: int = 0

    def set_banner(self, text: str, now_ms: int, duration_ms: int = 1100) -> None:
        self.banner = text
        self.banner_until_ms = now_ms + duration_ms

    def set_flash(self, rows: Sequence[int], now_ms: int, duration_ms: int = 220) -> None:
        self.flash_rows = list(rows)
        self.flash_until_ms = now_ms + duration_ms

    def tick(self, now_ms: int) -> None:
        if self.banner is not None and now_ms >= self.banner_until_ms:
            self.banner = None
        if self.flash_rows and now_ms >= self.flash_until_ms:
            self.flash_rows = []


# ---------------------------------------------------------------------------
# RenderState construction
# ---------------------------------------------------------------------------


def _tetromino_to_active(t: Tetromino) -> ActivePiece:
    """Convert a core ``Tetromino`` (row, col cells) to a renderer ``ActivePiece``
    (col, row cells)."""
    return ActivePiece(kind=t.kind, cells=[(c, r) for (r, c) in t.blocks()])


def build_render_state(adapter: GameAdapter, effects: _Effects) -> RenderState:
    game = adapter.game
    board = [list(row) for row in game.board.grid]

    active_piece: Optional[ActivePiece] = None
    ghost_piece: Optional[ActivePiece] = None
    if game.active is not None:
        active_piece = _tetromino_to_active(game.active)
        ghost = game.ghost_position()
        if ghost is not None and ghost.row != game.active.row:
            ghost_piece = _tetromino_to_active(ghost)

    next_pieces = [spawn_piece(k) for k in game.next_pieces(5)]
    held_piece = spawn_piece(game.held) if game.held else None

    if game.state is GameState.READY:
        phase = GamePhase.START
    elif game.state is GameState.GAME_OVER:
        phase = GamePhase.GAME_OVER
    elif adapter.paused:
        phase = GamePhase.PAUSED
    else:
        phase = GamePhase.PLAYING

    return RenderState(
        board=board,
        active_piece=active_piece,
        ghost_piece=ghost_piece,
        next_pieces=next_pieces,
        held_piece=held_piece,
        scoreboard=Scoreboard(
            score=game.scoring.score,
            level=game.scoring.level,
            lines=game.scoring.lines,
        ),
        phase=phase,
        last_clear_rows=tuple(effects.flash_rows),
        message=effects.banner if phase == GamePhase.PLAYING else None,
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def _install_hooks(game: Game, effects: _Effects, now_ms_fn) -> None:
    """Wire game-event hooks into our transient HUD effects."""

    def on_lock(ev: LockEvent) -> None:
        n = len(ev.cleared_lines)
        now_ms = now_ms_fn()
        if n:
            effects.set_flash(ev.cleared_lines, now_ms)
        banner: Optional[str] = None
        if ev.tspin in ("full", "mini"):
            banner = f"T-SPIN{'!' if n else ''}"
            if n:
                banner = f"T-SPIN {_CLEAR_BANNERS.get(n, '')}".strip()
        elif n:
            banner = _CLEAR_BANNERS.get(n)
        if banner:
            effects.set_banner(banner, now_ms)

    game.hooks.on_lock = on_lock


def run(
    *,
    seed: Optional[int] = None,
    headless: bool = False,
    frames: Optional[int] = None,
    scripted: Optional[Sequence[Action]] = None,
    snapshot_path: Optional[str] = None,
) -> int:
    """Run the game.

    Parameters
    ----------
    seed:
        Optional seed for the 7-bag randomizer (deterministic for tests).
    headless:
        Force the SDL dummy driver and skip ``pygame.display.flip`` calls.
    frames:
        If set, exit after rendering this many frames (used by smoke tests).
    scripted:
        Optional one-shot actions injected before the loop starts (used by
        smoke tests to exercise the input + game pipeline).
    snapshot_path:
        If set, write a PNG of the final frame to this path.
    """
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    renderer = Renderer()

    if headless:
        screen = renderer.create_surface()
    else:
        screen = pygame.display.set_mode(renderer.theme.window_size)
        pygame.display.set_caption("Tetris")

    clock = pygame.time.Clock()

    game = Game(seed=seed)
    game.start()  # go straight into PLAYING — start screen is reachable on game-over
    adapter = GameAdapter(game)
    effects = _Effects()
    _install_hooks(game, effects, pygame.time.get_ticks)

    bindings = KeyBindings().set(
        Action.HARD_DROP, [pygame.K_SPACE]  # remove WASD W=hard-drop overlap with UI
    )
    controller = InputController(adapter, bindings=bindings, timing=TimingConfig())

    # Inject scripted actions (used by smoke tests).
    if scripted:
        for action in scripted:
            controller.press(action, 0)

    rendered = 0
    running = True
    while running:
        now_ms = pygame.time.get_ticks()
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if not game.is_playing:
                    adapter.restart()
                continue
            controller.handle_event(event, now_ms)

        controller.update(now_ms)
        if game.is_playing and not adapter.paused:
            game.tick(dt)

        effects.tick(now_ms)
        state = build_render_state(adapter, effects)
        renderer.draw(screen, state)

        if not headless:
            pygame.display.flip()

        rendered += 1
        if frames is not None and rendered >= frames:
            running = False

    if snapshot_path is not None:
        pygame.image.save(screen, snapshot_path)

    if not headless:
        pygame.quit()
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Playable Tetris (game + renderer + input).")
    parser.add_argument("--seed", type=int, default=None, help="Seed the 7-bag randomizer.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Render to an offscreen surface (SDL dummy driver); no window opens.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=None,
        help="Exit after rendering N frames (useful with --headless for smoke checks).",
    )
    parser.add_argument(
        "--snapshot",
        type=str,
        default=None,
        help="If set, save the final frame as a PNG at this path.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    return run(
        seed=args.seed,
        headless=args.headless,
        frames=args.frames,
        snapshot_path=args.snapshot,
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
