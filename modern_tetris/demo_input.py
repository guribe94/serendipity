"""Runnable demo wiring :class:`InputController` to a stub game model.

Purpose
-------
This file is the canonical example of how the input subsystem plugs into a
pygame game loop.  When the sibling modules (game-loop, rendering, preview)
land, the integration point shown here is exactly how they should compose:

    1. Build a ``GameController`` implementation (real game state).
    2. Build an :class:`InputController`, passing the game as its target.
    3. In the main loop, pump events through ``controller.handle_event``,
       advance auto-repeat with ``controller.update``, then run game logic
       and render.

Two modes are supported:

    $ python -m modern_tetris.demo_input              # pygame window demo
    $ python -m modern_tetris.demo_input --headless   # text-only smoke test

The headless mode does not need a display and is suitable for CI smoke
checks; it injects a scripted sequence of events to prove the integration
wiring works end-to-end without a display server.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Tuple

from modern_tetris.input import (
    Action,
    InputController,
    KeyBindings,
    TimingConfig,
)


# ---------------------------------------------------------------------------
# Stub game model
# ---------------------------------------------------------------------------


@dataclass
class StubGame:
    """A minimal stand-in for the real game-loop module.

    Holds an (x, y) "piece" position on a 10x20 board and counts rotations
    and hard drops.  Real gameplay logic — collisions, lock delay, line
    clears — lives in the game-loop module; this stub only proves the input
    wiring works in isolation.
    """

    width: int = 10
    height: int = 20
    x: int = 4
    y: int = 0
    rotation: int = 0
    hard_drops: int = 0
    holds: int = 0
    paused: bool = False
    log: List[str] = field(default_factory=list)

    def _record(self, what: str) -> None:
        self.log.append(what)

    def move_left(self) -> None:
        if self.paused:
            return
        if self.x > 0:
            self.x -= 1
        self._record(f"move_left -> x={self.x}")

    def move_right(self) -> None:
        if self.paused:
            return
        if self.x < self.width - 1:
            self.x += 1
        self._record(f"move_right -> x={self.x}")

    def soft_drop(self) -> None:
        if self.paused:
            return
        if self.y < self.height - 1:
            self.y += 1
        self._record(f"soft_drop -> y={self.y}")

    def hard_drop(self) -> None:
        if self.paused:
            return
        self.y = self.height - 1
        self.hard_drops += 1
        self._record(f"hard_drop -> y={self.y} (#{self.hard_drops})")
        self._spawn_next()

    def rotate_cw(self) -> None:
        if self.paused:
            return
        self.rotation = (self.rotation + 1) % 4
        self._record(f"rotate_cw -> r={self.rotation}")

    def rotate_ccw(self) -> None:
        if self.paused:
            return
        self.rotation = (self.rotation - 1) % 4
        self._record(f"rotate_ccw -> r={self.rotation}")

    def rotate_180(self) -> None:
        if self.paused:
            return
        self.rotation = (self.rotation + 2) % 4
        self._record(f"rotate_180 -> r={self.rotation}")

    def hold(self) -> None:
        if self.paused:
            return
        self.holds += 1
        self._record(f"hold (#{self.holds})")

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self._record(f"pause -> {self.paused}")

    def _spawn_next(self) -> None:
        self.x = self.width // 2 - 1
        self.y = 0
        self.rotation = 0


# ---------------------------------------------------------------------------
# Headless smoke test
# ---------------------------------------------------------------------------


def _scripted_events() -> List[Tuple[int, str, Action]]:
    """A scripted sequence of (now_ms, "press"|"release", Action) tuples.

    Designed to exercise every code path: one-shot rotates, horizontal
    auto-repeat (DAS+ARR), soft-drop repeat, opposing-key takeover, and a
    final hard drop that respawns the piece.
    """
    return [
        # Rotate CW, then CCW.
        (0,   "press",   Action.ROTATE_CW),
        (50,  "press",   Action.ROTATE_CCW),
        # Hold left through DAS (~170ms) and partway into ARR.
        (100, "press",   Action.MOVE_LEFT),
        (350, "release", Action.MOVE_LEFT),
        # Soft drop for a few ticks.
        (400, "press",   Action.SOFT_DROP),
        (500, "release", Action.SOFT_DROP),
        # Roll left then right (takeover).
        (550, "press",   Action.MOVE_LEFT),
        (600, "press",   Action.MOVE_RIGHT),
        (700, "release", Action.MOVE_RIGHT),
        (800, "release", Action.MOVE_LEFT),
        # Hard drop, then hold.
        (850, "press",   Action.HARD_DROP),
        (900, "press",   Action.HOLD),
    ]


def run_headless() -> StubGame:
    """Replays the scripted event sequence through a real ``InputController``.

    Returns the resulting game state so callers (e.g. smoke tests, this
    module's __main__) can inspect or print it.
    """
    game = StubGame()
    controller = InputController(game)
    script = _scripted_events()

    # Pump events at 1ms resolution up to the last script entry + a tail
    # window so the final auto-repeat phase has time to fire.
    last_ms = script[-1][0]
    tail_ms = 200
    cursor = 0
    for now_ms in range(0, last_ms + tail_ms + 1):
        while cursor < len(script) and script[cursor][0] == now_ms:
            _, kind, action = script[cursor]
            if kind == "press":
                controller.press(action, now_ms)
            else:
                controller.release(action, now_ms)
            cursor += 1
        controller.update(now_ms)
    return game


# ---------------------------------------------------------------------------
# Interactive pygame demo
# ---------------------------------------------------------------------------


def run_pygame_demo() -> None:  # pragma: no cover - requires display
    """Open a small window and let the user drive the stub game by keyboard.

    The window simply renders the current x/y/rotation of the piece and the
    last action log entries; this is purely to verify that key handling
    feels responsive (DAS/ARR snappy, hard drop instant, etc.) before the
    real rendering module lands.
    """
    import pygame  # imported lazily so headless mode never needs a display

    pygame.init()
    screen = pygame.display.set_mode((420, 520))
    pygame.display.set_caption("Modern Tetris — input subsystem demo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 14)

    game = StubGame()
    controller = InputController(
        game,
        bindings=KeyBindings(),
        timing=TimingConfig(),  # 170 / 50 / 30 defaults
    )

    cell = 20
    board_origin = (10, 10)
    bg = (12, 16, 24)
    grid = (32, 40, 56)
    piece = (96, 192, 255)
    text_color = (220, 220, 220)

    running = True
    while running:
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                controller.handle_event(event, now)
        controller.update(now)

        screen.fill(bg)

        # Playfield outline.
        for cy in range(game.height):
            for cx in range(game.width):
                rect = pygame.Rect(
                    board_origin[0] + cx * cell,
                    board_origin[1] + cy * cell,
                    cell - 1,
                    cell - 1,
                )
                pygame.draw.rect(screen, grid, rect, 1)

        # Active "piece" (just a single coloured cell — stub).
        prect = pygame.Rect(
            board_origin[0] + game.x * cell,
            board_origin[1] + game.y * cell,
            cell - 1,
            cell - 1,
        )
        pygame.draw.rect(screen, piece, prect)

        # HUD: status + last log entries.
        status_lines = [
            f"x={game.x}  y={game.y}  r={game.rotation}",
            f"hard_drops={game.hard_drops}  holds={game.holds}",
            f"paused={game.paused}",
            "Controls: Left/Right=move  Up/X=rot CW  Z=rot CCW",
            "  Down/S=soft drop  Space=hard drop  C/Shift=hold",
            "  P/Esc=pause   close window to quit",
        ]
        for i, line in enumerate(status_lines):
            screen.blit(
                font.render(line, True, text_color),
                (board_origin[0], board_origin[1] + game.height * cell + 6 + i * 16),
            )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Modern Tetris input demo")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run a scripted smoke test instead of opening a pygame window.",
    )
    args = parser.parse_args(argv)

    if args.headless:
        game = run_headless()
        print(f"Headless demo finished. Final state:")
        print(f"  x={game.x}, y={game.y}, rotation={game.rotation}")
        print(f"  hard_drops={game.hard_drops}, holds={game.holds}")
        print(f"  log entries: {len(game.log)}")
        for entry in game.log[-10:]:
            print(f"    {entry}")
        return 0

    run_pygame_demo()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
