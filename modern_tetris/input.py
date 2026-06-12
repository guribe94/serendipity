"""Input and control subsystem for the modern Tetris build.

Public surface
--------------
- ``Action``           — enum of high-level player actions.
- ``GameController``   — Protocol the game-loop module implements so the
                         controller can dispatch actions into it.
- ``KeyBindings``      — configurable mapping from physical keys to actions.
- ``TimingConfig``     — DAS / ARR / soft-drop period in milliseconds.
- ``InputController``  — translates pygame KEYDOWN/KEYUP events (or direct
                         ``press``/``release`` calls in tests) into game
                         actions, with proper DAS + ARR repeat behaviour.

Design notes
------------
The controller is built around the modern Tetris "DAS / ARR" repeat model:

    * DAS (Delayed Auto-Shift): the delay after a movement key first goes
      down before auto-repeat kicks in.  Default 170 ms.
    * ARR (Auto-Repeat Rate): the period between auto-repeated moves once
      DAS has elapsed.  Default 50 ms.
    * Soft drop: continuous repeat at ``soft_drop_ms`` with no DAS delay.
    * Hard drop, rotation, hold, pause: one-shot on KEYDOWN; never auto-
      repeated.

Opposing-key handling follows the modern guideline: if the player presses
LEFT and then RIGHT without releasing LEFT, RIGHT takes over.  If RIGHT is
then released while LEFT is still held, LEFT resumes — with its DAS timer
restarted so the rollover feels predictable.

The core repeat logic is driven from explicit timestamps passed in by the
game loop (``now_ms``).  That makes the controller fully deterministic and
unit-testable without spinning up pygame, a display, or a real clock.
``handle_event`` is the thin pygame adapter; ``press`` / ``release`` are the
generic primitives used by tests and by anyone who wants to drive the
controller from a non-pygame event source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, Iterable, Optional, Protocol, Tuple

try:  # pygame is optional at import-time so that pure-logic tests don't need it.
    import pygame  # type: ignore
    _PYGAME_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only on systems without pygame
    pygame = None  # type: ignore
    _PYGAME_AVAILABLE = False


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


class Action(Enum):
    """High-level player actions emitted by the input controller."""

    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    SOFT_DROP = auto()
    HARD_DROP = auto()
    ROTATE_CW = auto()
    ROTATE_CCW = auto()
    ROTATE_180 = auto()
    HOLD = auto()
    PAUSE = auto()


_ONE_SHOT_ACTIONS = frozenset(
    {
        Action.HARD_DROP,
        Action.ROTATE_CW,
        Action.ROTATE_CCW,
        Action.ROTATE_180,
        Action.HOLD,
        Action.PAUSE,
    }
)


# ---------------------------------------------------------------------------
# Game integration protocol
# ---------------------------------------------------------------------------


class GameController(Protocol):
    """Methods the game-loop module exposes to receive input actions.

    Implementations should be cheap and idempotent: the input controller may
    call them many times per frame during auto-repeat.  Methods return
    nothing; the game state owns the decision of whether a given move is
    legal and silently no-ops otherwise.
    """

    def move_left(self) -> None: ...
    def move_right(self) -> None: ...
    def soft_drop(self) -> None: ...
    def hard_drop(self) -> None: ...
    def rotate_cw(self) -> None: ...
    def rotate_ccw(self) -> None: ...
    def rotate_180(self) -> None: ...
    def hold(self) -> None: ...
    def toggle_pause(self) -> None: ...


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


# Fallback key codes used when pygame is not importable (e.g. CI with no SDL).
# They mirror pygame's K_* constants so unit tests can still use realistic
# integer codes without importing pygame.
_FALLBACK_KEYS = {
    "K_LEFT": 1073741904,
    "K_RIGHT": 1073741903,
    "K_DOWN": 1073741905,
    "K_UP": 1073741906,
    "K_SPACE": 32,
    "K_ESCAPE": 27,
    "K_LCTRL": 1073742048,
    "K_RCTRL": 1073742052,
    "K_LSHIFT": 1073742049,
    "K_RSHIFT": 1073742053,
}


def _key(name: str) -> int:
    """Resolve a key name to its integer code via pygame or the fallback table."""
    if _PYGAME_AVAILABLE and hasattr(pygame, name):
        return int(getattr(pygame, name))
    if name in _FALLBACK_KEYS:
        return _FALLBACK_KEYS[name]
    # Single-letter ASCII keys: 'a' .. 'z'
    if name.startswith("K_") and len(name) == 3:
        return ord(name[2])
    raise KeyError(name)


def _default_bindings() -> Dict[Action, Tuple[int, ...]]:
    """Default keyboard layout, modelled on common modern-Tetris controls."""
    return {
        Action.MOVE_LEFT: (_key("K_LEFT"), ord("a")),
        Action.MOVE_RIGHT: (_key("K_RIGHT"), ord("d")),
        Action.SOFT_DROP: (_key("K_DOWN"), ord("s")),
        Action.HARD_DROP: (_key("K_SPACE"), ord("w")),
        Action.ROTATE_CW: (_key("K_UP"), ord("x")),
        Action.ROTATE_CCW: (ord("z"), _key("K_LCTRL"), _key("K_RCTRL")),
        Action.ROTATE_180: (),  # unbound by default; opt-in via rebind()
        Action.HOLD: (ord("c"), _key("K_LSHIFT"), _key("K_RSHIFT")),
        Action.PAUSE: (ord("p"), _key("K_ESCAPE")),
    }


@dataclass
class KeyBindings:
    """Maps each :class:`Action` to one or more physical key codes.

    Multiple keys per action are allowed (e.g. arrow keys *and* WASD).  Pass
    a custom mapping to override entries while keeping the defaults for the
    rest.  Use :py:meth:`set` to rebind a single action fluently.
    """

    bindings: Dict[Action, Tuple[int, ...]] = field(default_factory=_default_bindings)

    def keys_for(self, action: Action) -> Tuple[int, ...]:
        return self.bindings.get(action, ())

    def set(self, action: Action, keys: Iterable[int]) -> "KeyBindings":
        """Replace the keys for ``action``; returns ``self`` for chaining."""
        self.bindings[action] = tuple(keys)
        return self

    def build_lookup(self) -> Dict[int, Action]:
        """Inverted map: physical key code -> Action.

        If a key appears under more than one action the *last* action in the
        bindings table wins.  Callers should keep their bindings disjoint.
        """
        lookup: Dict[int, Action] = {}
        for action, keys in self.bindings.items():
            for key in keys:
                lookup[key] = action
        return lookup


@dataclass
class TimingConfig:
    """Repeat timing in milliseconds.

    The defaults (DAS=170, ARR=50, soft_drop=30) sit comfortably between
    casual play and tournament-tight inputs.  Surfaces a ``max_repeats_per_tick``
    safety cap so a stalled game loop cannot generate hundreds of moves at
    once when it resumes.
    """

    das_ms: int = 170
    arr_ms: int = 50
    soft_drop_ms: int = 30
    max_repeats_per_tick: int = 16

    def __post_init__(self) -> None:
        if self.das_ms < 0:
            raise ValueError("das_ms must be non-negative")
        if self.arr_ms < 0:
            raise ValueError("arr_ms must be non-negative")
        if self.soft_drop_ms < 0:
            raise ValueError("soft_drop_ms must be non-negative")
        if self.max_repeats_per_tick < 1:
            raise ValueError("max_repeats_per_tick must be >= 1")


# ---------------------------------------------------------------------------
# Internal repeat-state bookkeeping
# ---------------------------------------------------------------------------


@dataclass
class _RepeatState:
    """Tracks a single held-key channel (left, right, or soft drop)."""

    pressed: bool = False
    pressed_at_ms: int = 0
    next_repeat_ms: int = 0  # wall-clock time the next repeat fires


# ---------------------------------------------------------------------------
# InputController
# ---------------------------------------------------------------------------


class InputController:
    """Translate keyboard events into Tetris actions.

    Typical wiring inside a pygame game loop::

        controller = InputController(game)
        while running:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    controller.handle_event(event, now)
            controller.update(now)   # auto-repeat
            game.tick(now)           # gravity, line clears, etc.
            renderer.draw(game)
            pygame.display.flip()
            clock.tick(60)

    The controller is also fully usable without pygame: call :py:meth:`press`
    and :py:meth:`release` directly with an :class:`Action`, then advance
    time with :py:meth:`update`.  That is what the unit tests do.
    """

    def __init__(
        self,
        game: GameController,
        bindings: Optional[KeyBindings] = None,
        timing: Optional[TimingConfig] = None,
    ) -> None:
        self.game = game
        self.bindings = bindings or KeyBindings()
        self.timing = timing or TimingConfig()

        # When False, all gameplay actions are dropped.  PAUSE still routes
        # through so the host can offer "un-pause" without rebuilding the
        # controller.  Hosts toggle this on game-over / paused / menu states.
        self.enabled: bool = True

        self._left = _RepeatState()
        self._right = _RepeatState()
        self._soft = _RepeatState()

        # Tracks which of LEFT / RIGHT currently "owns" auto-repeat.  When
        # both keys are held simultaneously, the most recently pressed wins;
        # if that key is released, ownership falls back to the other.
        self._active_horizontal: Optional[Action] = None

        self._key_lookup: Dict[int, Action] = self.bindings.build_lookup()

        # Dispatch table — instance-level so subclasses can swap individual
        # entries.  Each entry maps an Action to a zero-arg call into the
        # game controller.
        self._dispatch: Dict[Action, Callable[[], None]] = {
            Action.MOVE_LEFT: lambda: self.game.move_left(),
            Action.MOVE_RIGHT: lambda: self.game.move_right(),
            Action.SOFT_DROP: lambda: self.game.soft_drop(),
            Action.HARD_DROP: lambda: self.game.hard_drop(),
            Action.ROTATE_CW: lambda: self.game.rotate_cw(),
            Action.ROTATE_CCW: lambda: self.game.rotate_ccw(),
            Action.ROTATE_180: lambda: self.game.rotate_180(),
            Action.HOLD: lambda: self.game.hold(),
            Action.PAUSE: lambda: self.game.toggle_pause(),
        }

    # -- configuration -----------------------------------------------------

    def rebind(self, bindings: KeyBindings) -> None:
        """Hot-swap the entire key binding map (e.g. after a settings save)."""
        self.bindings = bindings
        self._key_lookup = bindings.build_lookup()

    def retime(self, timing: TimingConfig) -> None:
        """Hot-swap timing config.  Held keys remain held; new timings take
        effect on the next repeat boundary."""
        self.timing = timing

    # -- direct (framework-agnostic) API -----------------------------------

    def press(self, action: Action, now_ms: int) -> None:
        """Record a key-down for *action* at ``now_ms`` and fire it once.

        This is the generic primitive.  Pygame events are translated to a
        ``press`` call inside :py:meth:`handle_event`; tests call it
        directly.  The action runs synchronously via the dispatch table.
        """
        if action is Action.PAUSE:
            # PAUSE always passes through so a paused game can be resumed.
            self._dispatch[action]()
            return

        if not self.enabled:
            return

        if action is Action.MOVE_LEFT:
            self._press_horizontal(self._left, now_ms, Action.MOVE_LEFT)
        elif action is Action.MOVE_RIGHT:
            self._press_horizontal(self._right, now_ms, Action.MOVE_RIGHT)
        elif action is Action.SOFT_DROP:
            self._soft.pressed = True
            self._soft.pressed_at_ms = now_ms
            self._soft.next_repeat_ms = now_ms + self.timing.soft_drop_ms
            self._dispatch[action]()
        elif action in _ONE_SHOT_ACTIONS:
            self._dispatch[action]()
        else:  # pragma: no cover - exhaustive fallback
            raise ValueError(f"Unhandled action: {action!r}")

    def release(self, action: Action, now_ms: Optional[int] = None) -> None:
        """Record a key-up for *action*.

        For LEFT / RIGHT, supplying ``now_ms`` enables proper DAS-reset
        takeover when the surviving key resumes auto-repeat.  If omitted,
        the surviving key continues with whatever timing state it already
        had (which may already be past DAS — useful for tests that don't
        care about takeover semantics).
        """
        if action is Action.MOVE_LEFT:
            self._left.pressed = False
            if self._active_horizontal is Action.MOVE_LEFT:
                self._handover_horizontal(self._right, Action.MOVE_RIGHT, now_ms)
        elif action is Action.MOVE_RIGHT:
            self._right.pressed = False
            if self._active_horizontal is Action.MOVE_RIGHT:
                self._handover_horizontal(self._left, Action.MOVE_LEFT, now_ms)
        elif action is Action.SOFT_DROP:
            self._soft.pressed = False
        # one-shot actions don't track press state, so release is a no-op.

    # -- pygame adapter ----------------------------------------------------

    def handle_event(self, event, now_ms: int) -> Optional[Action]:
        """Process a single pygame event.

        Returns the :class:`Action` that fired on KEYDOWN (handy for
        logging / replay capture), ``None`` otherwise.  Unknown keys and
        non-keyboard events are silently ignored so the host can pump every
        event through this method without prefiltering.
        """
        etype = getattr(event, "type", None)
        if etype is None:
            return None

        if _PYGAME_AVAILABLE:
            keydown = pygame.KEYDOWN
            keyup = pygame.KEYUP
        else:  # pragma: no cover - exercised only on systems without pygame
            keydown = 768
            keyup = 769

        if etype == keydown:
            key = getattr(event, "key", None)
            action = self._key_lookup.get(key)
            if action is None:
                return None
            self.press(action, now_ms)
            return action
        if etype == keyup:
            key = getattr(event, "key", None)
            action = self._key_lookup.get(key)
            if action is None:
                return None
            self.release(action, now_ms)
            return None
        return None

    def process_events(self, events: Iterable, now_ms: int) -> None:
        """Process a batch of pygame events in order."""
        for event in events:
            self.handle_event(event, now_ms)

    # -- per-frame tick ----------------------------------------------------

    def update(self, now_ms: int) -> None:
        """Advance auto-repeat state.  Call once per game-loop tick.

        Emits movement actions for the active horizontal channel (after
        DAS) and soft-drop actions while ``SOFT_DROP`` is held.  Each
        channel is capped at ``timing.max_repeats_per_tick`` to keep
        behaviour sane after long stalls (e.g. a debugger break).
        """
        if not self.enabled:
            return

        if self._active_horizontal is Action.MOVE_LEFT:
            self._tick_movement(self._left, now_ms, Action.MOVE_LEFT)
        elif self._active_horizontal is Action.MOVE_RIGHT:
            self._tick_movement(self._right, now_ms, Action.MOVE_RIGHT)

        self._tick_soft_drop(now_ms)

    def reset(self) -> None:
        """Drop all held-key state — call on game-over, level transitions, etc."""
        self._left = _RepeatState()
        self._right = _RepeatState()
        self._soft = _RepeatState()
        self._active_horizontal = None

    # -- introspection (handy for tests / debug HUD) -----------------------

    @property
    def left_held(self) -> bool:
        return self._left.pressed

    @property
    def right_held(self) -> bool:
        return self._right.pressed

    @property
    def soft_drop_held(self) -> bool:
        return self._soft.pressed

    @property
    def active_horizontal(self) -> Optional[Action]:
        return self._active_horizontal

    # -- internals ---------------------------------------------------------

    def _press_horizontal(
        self,
        state: _RepeatState,
        now_ms: int,
        action: Action,
    ) -> None:
        """Handle a fresh KEYDOWN for a horizontal movement action."""
        state.pressed = True
        state.pressed_at_ms = now_ms
        state.next_repeat_ms = now_ms + self.timing.das_ms
        self._active_horizontal = action
        self._dispatch[action]()

    def _handover_horizontal(
        self,
        survivor: _RepeatState,
        survivor_action: Action,
        now_ms: Optional[int],
    ) -> None:
        """Transfer auto-repeat ownership to the other horizontal channel
        after the active key is released.  Restarts DAS on the survivor so
        the rollover feels predictable (matches modern guideline behaviour)."""
        if survivor.pressed:
            self._active_horizontal = survivor_action
            if now_ms is not None:
                survivor.pressed_at_ms = now_ms
                survivor.next_repeat_ms = now_ms + self.timing.das_ms
        else:
            self._active_horizontal = None

    def _tick_movement(
        self,
        state: _RepeatState,
        now_ms: int,
        action: Action,
    ) -> None:
        if not state.pressed:
            return
        if now_ms < state.next_repeat_ms:
            return
        period = self.timing.arr_ms if self.timing.arr_ms > 0 else 1
        fired = 0
        cap = self.timing.max_repeats_per_tick
        while state.next_repeat_ms <= now_ms and fired < cap:
            self._dispatch[action]()
            state.next_repeat_ms += period
            fired += 1
        if state.next_repeat_ms <= now_ms:
            # Cap hit with backlog remaining: drop it, otherwise a long stall
            # keeps bursting capped repeats on every following tick.
            state.next_repeat_ms = now_ms + period

    def _tick_soft_drop(self, now_ms: int) -> None:
        state = self._soft
        if not state.pressed:
            return
        if now_ms < state.next_repeat_ms:
            return
        period = self.timing.soft_drop_ms if self.timing.soft_drop_ms > 0 else 1
        fired = 0
        cap = self.timing.max_repeats_per_tick
        while state.next_repeat_ms <= now_ms and fired < cap:
            self._dispatch[Action.SOFT_DROP]()
            state.next_repeat_ms += period
            fired += 1
        if state.next_repeat_ms <= now_ms:
            # Same backlog-drop rule as horizontal movement (see _tick_movement).
            state.next_repeat_ms = now_ms + period


__all__ = [
    "Action",
    "GameController",
    "InputController",
    "KeyBindings",
    "TimingConfig",
]
