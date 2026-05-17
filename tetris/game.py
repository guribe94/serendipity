"""The Tetris game state machine: spawning, gravity, locking, line clears, game over.

Other subsystems (input, rendering, previews) drive and read this state without
needing to know how gravity and lock delay interact internally. Event hooks
(`on_spawn`, `on_lock`, `on_line_clear`, `on_score_change`, `on_level_change`,
`on_game_over`) make it easy to wire HUD updates and audio.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Tuple

from .board import Board
from .randomizer import SevenBag
from .scoring import Scoring
from .tetromino import KINDS, Tetromino, kick_table


SPAWN_ROW = 0
SPAWN_COL = 3
LOCK_DELAY = 0.5
MAX_LOCK_RESETS = 15


def gravity_period(level: int) -> float:
    """Seconds per cell at the given level (guideline formula, clamped)."""
    level = max(1, level)
    base = 0.8 - (level - 1) * 0.007
    if base <= 0:
        return 1 / 60
    return base ** (level - 1)


class GameState(Enum):
    READY = "ready"
    PLAYING = "playing"
    GAME_OVER = "game_over"


@dataclass
class LockEvent:
    piece: Tetromino
    cleared_lines: List[int]
    tspin: Optional[str]
    score_delta: int


@dataclass
class _Hooks:
    on_spawn: Optional[Callable[[Tetromino], None]] = None
    on_lock: Optional[Callable[[LockEvent], None]] = None
    on_line_clear: Optional[Callable[[List[int]], None]] = None
    on_score_change: Optional[Callable[[int], None]] = None
    on_level_change: Optional[Callable[[int], None]] = None
    on_game_over: Optional[Callable[[], None]] = None
    on_hold: Optional[Callable[[Optional[str], str], None]] = None


class Game:
    def __init__(
        self,
        seed: Optional[int] = None,
        starting_level: int = 1,
        preview: int = 5,
    ) -> None:
        self.board = Board()
        self.bag = SevenBag(seed=seed, preview=preview)
        self.scoring = Scoring(starting_level=starting_level)
        self.preview = preview
        self.state = GameState.READY

        self.active: Optional[Tetromino] = None
        self.held: Optional[str] = None
        self.hold_used: bool = False

        self.hooks = _Hooks()

        self._gravity_acc = 0.0
        self._lock_acc = 0.0
        self._lock_resets = 0
        self._last_action_was_rotation = False
        self._last_kick: Tuple[int, int] = (0, 0)

    # ------------------------------------------------------------ lifecycle

    def start(self) -> None:
        starting_level = max(1, self.scoring.state.level)
        self.board.reset()
        self.scoring = Scoring(starting_level=starting_level)
        self.state = GameState.PLAYING
        self.active = None
        self.held = None
        self.hold_used = False
        self._gravity_acc = 0.0
        self._lock_acc = 0.0
        self._lock_resets = 0
        self._last_action_was_rotation = False
        self._spawn_piece()

    def _spawn_piece(self, kind: Optional[str] = None) -> bool:
        if kind is None:
            kind = self.bag.next()
        piece = Tetromino(kind=kind, row=SPAWN_ROW, col=SPAWN_COL, rotation=0)
        self._gravity_acc = 0.0
        self._lock_acc = 0.0
        self._lock_resets = 0
        self._last_action_was_rotation = False
        if not self.board.can_place(piece.blocks()):
            self.active = piece
            self._trigger_game_over()
            return False
        self.active = piece
        self.hold_used = False
        if self.hooks.on_spawn:
            self.hooks.on_spawn(piece)
        return True

    # -------------------------------------------------------------- ticking

    def tick(self, dt: float) -> None:
        """Advance gravity and lock-delay timers by `dt` seconds."""
        if self.state is not GameState.PLAYING or self.active is None:
            return

        period = gravity_period(self.scoring.state.level)
        self._gravity_acc += dt
        while self._gravity_acc >= period:
            self._gravity_acc -= period
            if not self._step_gravity():
                break

        if self.state is not GameState.PLAYING:
            return
        if self.active is None:
            return
        if self._is_landed():
            self._lock_acc += dt
            if self._lock_acc >= LOCK_DELAY:
                self._lock_piece()
        else:
            self._lock_acc = 0.0

    def _step_gravity(self) -> bool:
        if self.active is None:
            return False
        candidate = self.active.moved(1, 0)
        if self.board.can_place(candidate.blocks()):
            self.active = candidate
            self._last_action_was_rotation = False
            return True
        return False

    def _is_landed(self) -> bool:
        if self.active is None:
            return False
        return not self.board.can_place(self.active.moved(1, 0).blocks())

    # ------------------------------------------------------------ player actions

    def move(self, dcol: int) -> bool:
        if self.state is not GameState.PLAYING or self.active is None:
            return False
        candidate = self.active.moved(0, dcol)
        if not self.board.can_place(candidate.blocks()):
            return False
        self.active = candidate
        self._last_action_was_rotation = False
        self._reset_lock_if_landed()
        return True

    def rotate(self, direction: int) -> bool:
        """+1 = clockwise, -1 = counter-clockwise. Uses SRS wall-kicks."""
        if self.state is not GameState.PLAYING or self.active is None:
            return False
        from_rot = self.active.rotation % 4
        to_rot = (from_rot + direction) % 4
        if from_rot == to_rot:
            return False
        rotated = self.active.with_rotation(to_rot)
        for dcol, drow in kick_table(self.active.kind, from_rot, to_rot):
            candidate = rotated.moved(drow, dcol)
            if self.board.can_place(candidate.blocks()):
                self.active = candidate
                self._last_action_was_rotation = True
                self._last_kick = (dcol, drow)
                self._reset_lock_if_landed()
                return True
        return False

    def soft_drop(self) -> bool:
        if self.state is not GameState.PLAYING or self.active is None:
            return False
        candidate = self.active.moved(1, 0)
        if not self.board.can_place(candidate.blocks()):
            return False
        self.active = candidate
        delta = self.scoring.add_soft_drop(1)
        self._last_action_was_rotation = False
        self._gravity_acc = 0.0
        if delta and self.hooks.on_score_change:
            self.hooks.on_score_change(self.scoring.score)
        return True

    def hard_drop(self) -> int:
        if self.state is not GameState.PLAYING or self.active is None:
            return 0
        cells = 0
        while True:
            candidate = self.active.moved(1, 0)
            if self.board.can_place(candidate.blocks()):
                self.active = candidate
                cells += 1
            else:
                break
        if cells > 0:
            delta = self.scoring.add_hard_drop(cells)
            self._last_action_was_rotation = False
            if delta and self.hooks.on_score_change:
                self.hooks.on_score_change(self.scoring.score)
        self._lock_piece()
        return cells

    def hold(self) -> bool:
        """Swap the active piece with the held one. Can only be used once per spawn."""
        if self.state is not GameState.PLAYING or self.active is None:
            return False
        if self.hold_used:
            return False
        current = self.active.kind
        previous = self.held
        self.held = current
        self.hold_used = True
        if previous is None:
            spawned = self._spawn_piece()
        else:
            spawned = self._spawn_piece(kind=previous)
        # _spawn_piece resets hold_used to False; restore it so hold can't be
        # used again on the swapped-in piece.
        if spawned:
            self.hold_used = True
        if self.hooks.on_hold:
            self.hooks.on_hold(previous, current)
        return True

    # -------------------------------------------------------------- helpers

    def _reset_lock_if_landed(self) -> None:
        if self._is_landed() and self._lock_resets < MAX_LOCK_RESETS:
            self._lock_acc = 0.0
            self._lock_resets += 1

    def ghost_position(self) -> Optional[Tetromino]:
        if self.active is None:
            return None
        piece = self.active
        while True:
            candidate = piece.moved(1, 0)
            if self.board.can_place(candidate.blocks()):
                piece = candidate
            else:
                return piece

    def next_pieces(self, n: Optional[int] = None) -> Tuple[str, ...]:
        return self.bag.peek(n if n is not None else self.preview)

    @property
    def is_playing(self) -> bool:
        return self.state is GameState.PLAYING

    @property
    def is_game_over(self) -> bool:
        return self.state is GameState.GAME_OVER

    # ---------------------------------------------------------------- locks

    def _detect_tspin(self) -> Optional[str]:
        if self.active is None or self.active.kind != "T":
            return None
        if not self._last_action_was_rotation:
            return None
        r, c = self.active.row, self.active.col
        corners = [(r, c), (r, c + 2), (r + 2, c), (r + 2, c + 2)]
        filled = sum(1 for cr, cc in corners if not self.board.is_cell_free(cr, cc))
        if filled < 3:
            return None
        facing = {
            0: [(r, c), (r, c + 2)],
            1: [(r, c + 2), (r + 2, c + 2)],
            2: [(r + 2, c), (r + 2, c + 2)],
            3: [(r, c), (r + 2, c)],
        }[self.active.rotation % 4]
        front_filled = sum(1 for cr, cc in facing if not self.board.is_cell_free(cr, cc))
        return "full" if front_filled == 2 else "mini"

    def _lock_piece(self) -> None:
        if self.active is None:
            return
        piece = self.active

        if all(r < Board.BUFFER_HEIGHT for r, _ in piece.blocks()):
            self.board.place(piece.blocks(), piece.kind)
            self._trigger_game_over()
            return

        tspin = self._detect_tspin()
        self.board.place(piece.blocks(), piece.kind)
        cleared = self.board.clear_full_lines()
        previous_level = self.scoring.state.level
        score_delta = self.scoring.add_line_clear(len(cleared), tspin=tspin)

        event = LockEvent(piece=piece, cleared_lines=cleared, tspin=tspin, score_delta=score_delta)
        if self.hooks.on_lock:
            self.hooks.on_lock(event)
        if cleared and self.hooks.on_line_clear:
            self.hooks.on_line_clear(cleared)
        if score_delta and self.hooks.on_score_change:
            self.hooks.on_score_change(self.scoring.score)
        if self.scoring.state.level != previous_level and self.hooks.on_level_change:
            self.hooks.on_level_change(self.scoring.state.level)

        self.active = None
        if self.state is GameState.PLAYING:
            self._spawn_piece()

    def _trigger_game_over(self) -> None:
        self.state = GameState.GAME_OVER
        if self.hooks.on_game_over:
            self.hooks.on_game_over()
