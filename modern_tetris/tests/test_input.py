"""Tests for the input/control subsystem.

The InputController is fully driven by explicit ``now_ms`` timestamps and
does not require pygame, a display, or a real clock.  These tests use a
``FakeGame`` recorder to verify the exact sequence of game-side calls each
input scenario produces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from modern_tetris.input import (
    Action,
    InputController,
    KeyBindings,
    TimingConfig,
)


# ---------------------------------------------------------------------------
# Fake game integration target
# ---------------------------------------------------------------------------


@dataclass
class FakeGame:
    """Captures the sequence of GameController method calls for assertions."""

    calls: List[str] = field(default_factory=list)

    def move_left(self) -> None: self.calls.append("move_left")
    def move_right(self) -> None: self.calls.append("move_right")
    def soft_drop(self) -> None: self.calls.append("soft_drop")
    def hard_drop(self) -> None: self.calls.append("hard_drop")
    def rotate_cw(self) -> None: self.calls.append("rotate_cw")
    def rotate_ccw(self) -> None: self.calls.append("rotate_ccw")
    def rotate_180(self) -> None: self.calls.append("rotate_180")
    def hold(self) -> None: self.calls.append("hold")
    def toggle_pause(self) -> None: self.calls.append("toggle_pause")

    def reset(self) -> None:
        self.calls.clear()

    def count(self, name: str) -> int:
        return sum(1 for c in self.calls if c == name)


@dataclass
class FakeEvent:
    """Mimics the minimal pygame event interface we depend on."""

    type: int
    key: int = 0


def _ctrl(timing: TimingConfig | None = None) -> tuple[InputController, FakeGame]:
    game = FakeGame()
    return (
        InputController(
            game,
            timing=timing or TimingConfig(das_ms=100, arr_ms=20, soft_drop_ms=10),
        ),
        game,
    )


# ---------------------------------------------------------------------------
# One-shot actions
# ---------------------------------------------------------------------------


def test_hard_drop_fires_once_on_press():
    ctrl, game = _ctrl()
    ctrl.press(Action.HARD_DROP, now_ms=0)
    assert game.calls == ["hard_drop"]
    # No release semantics; further updates must not produce more drops.
    ctrl.update(now_ms=500)
    ctrl.update(now_ms=1000)
    assert game.count("hard_drop") == 1


def test_rotate_actions_are_one_shot():
    ctrl, game = _ctrl()
    ctrl.press(Action.ROTATE_CW, now_ms=0)
    ctrl.press(Action.ROTATE_CCW, now_ms=50)
    ctrl.press(Action.ROTATE_180, now_ms=100)
    ctrl.update(now_ms=1000)
    assert game.calls == ["rotate_cw", "rotate_ccw", "rotate_180"]


def test_hold_fires_once():
    ctrl, game = _ctrl()
    ctrl.press(Action.HOLD, now_ms=0)
    ctrl.press(Action.HOLD, now_ms=200)
    ctrl.update(now_ms=1000)
    # Two presses == two calls; no auto-repeat in between.
    assert game.calls == ["hold", "hold"]


# ---------------------------------------------------------------------------
# Horizontal movement: initial fire, DAS, ARR
# ---------------------------------------------------------------------------


def test_horizontal_press_fires_immediately():
    ctrl, game = _ctrl()
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    assert game.calls == ["move_left"]


def test_no_auto_repeat_before_das_elapses():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=10)
    ctrl.update(now_ms=50)
    ctrl.update(now_ms=99)
    assert game.calls == ["move_left"]  # only the initial press


def test_auto_repeat_after_das_at_arr_rate():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    # At DAS=100ms, first auto-repeat fires.
    ctrl.update(now_ms=100)
    # Then at ARR=20ms intervals: 120, 140, 160, 180, 200
    ctrl.update(now_ms=120)
    ctrl.update(now_ms=140)
    ctrl.update(now_ms=160)
    ctrl.update(now_ms=180)
    ctrl.update(now_ms=200)
    # 1 initial + 6 auto-repeats == 7
    assert game.count("move_left") == 7


def test_long_stall_caps_auto_repeats_per_tick():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20, max_repeats_per_tick=4))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    # Sleep until well past DAS plus many ARR periods.
    ctrl.update(now_ms=5_000)
    # Initial press + capped repeats == 1 + 4 == 5
    assert game.count("move_left") == 5


def test_release_stops_auto_repeat():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=100)  # fire 1 auto-repeat
    ctrl.release(Action.MOVE_LEFT, now_ms=110)
    ctrl.update(now_ms=200)
    ctrl.update(now_ms=400)
    assert game.count("move_left") == 2  # initial + 1


# ---------------------------------------------------------------------------
# Opposing keys: takeover and DAS reset
# ---------------------------------------------------------------------------


def test_pressing_right_while_left_held_takes_over():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=100)            # left auto-repeats once
    ctrl.press(Action.MOVE_RIGHT, now_ms=120)
    # Right just pressed: should fire immediately, but no auto-repeat yet.
    ctrl.update(now_ms=150)
    ctrl.update(now_ms=200)
    # Right's DAS doesn't elapse until 120 + 100 == 220.
    assert "move_left" in game.calls
    assert "move_right" in game.calls
    # After this point, only right should auto-repeat.
    n_left_before = game.count("move_left")
    ctrl.update(now_ms=220)            # right's DAS fires
    ctrl.update(now_ms=240)
    assert game.count("move_left") == n_left_before
    assert game.count("move_right") >= 2


def test_releasing_active_key_hands_over_to_other():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.press(Action.MOVE_RIGHT, now_ms=50)
    # Right is now active; release right.
    ctrl.release(Action.MOVE_RIGHT, now_ms=80)
    # Active should fall back to left, with DAS reset at t=80.
    # Before t=80+100=180, no auto-repeat.
    ctrl.update(now_ms=100)
    ctrl.update(now_ms=179)
    left_before = game.count("move_left")
    # Initial left press (t=0) + nothing from auto-repeat yet.
    assert left_before == 1
    # First auto-repeat at t=180.
    ctrl.update(now_ms=180)
    assert game.count("move_left") == 2


def test_releasing_non_active_key_does_not_disrupt():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.press(Action.MOVE_RIGHT, now_ms=50)
    # Right is active.  Release LEFT (the inactive one).
    ctrl.release(Action.MOVE_LEFT, now_ms=70)
    # Right should still be active and auto-repeating off its original press.
    ctrl.update(now_ms=150)   # right's DAS fires at 50+100=150
    ctrl.update(now_ms=170)   # ARR
    assert game.count("move_right") >= 3  # initial + DAS + ARR


def test_release_both_keys_clears_active():
    ctrl, game = _ctrl()
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.press(Action.MOVE_RIGHT, now_ms=50)
    ctrl.release(Action.MOVE_RIGHT, now_ms=80)
    ctrl.release(Action.MOVE_LEFT, now_ms=90)
    assert ctrl.active_horizontal is None
    game.reset()
    ctrl.update(now_ms=500)
    assert game.calls == []


# ---------------------------------------------------------------------------
# Soft drop
# ---------------------------------------------------------------------------


def test_soft_drop_fires_on_press_then_repeats_at_period():
    ctrl, game = _ctrl(TimingConfig(soft_drop_ms=10))
    ctrl.press(Action.SOFT_DROP, now_ms=0)
    # Initial press fires; first auto-fire at t=10.
    ctrl.update(now_ms=5)
    ctrl.update(now_ms=10)
    ctrl.update(now_ms=20)
    ctrl.update(now_ms=30)
    assert game.count("soft_drop") == 4  # 1 press + 3 ticks


def test_soft_drop_release_stops_repeat():
    ctrl, game = _ctrl(TimingConfig(soft_drop_ms=10))
    ctrl.press(Action.SOFT_DROP, now_ms=0)
    ctrl.update(now_ms=10)
    ctrl.release(Action.SOFT_DROP)
    ctrl.update(now_ms=100)
    ctrl.update(now_ms=200)
    assert game.count("soft_drop") == 2  # press + 1 repeat


def test_soft_drop_is_independent_of_horizontal_movement():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20, soft_drop_ms=10))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.press(Action.SOFT_DROP, now_ms=0)
    ctrl.update(now_ms=10)
    # Soft drop should fire (period elapsed); left should NOT (DAS not elapsed).
    assert game.count("soft_drop") >= 2
    assert game.count("move_left") == 1


# ---------------------------------------------------------------------------
# Pygame event adapter
# ---------------------------------------------------------------------------


def test_handle_event_translates_keydown_to_action():
    import pygame  # safe; only imported by tests that need it
    ctrl, game = _ctrl()
    ctrl.handle_event(FakeEvent(type=pygame.KEYDOWN, key=pygame.K_SPACE), now_ms=0)
    assert game.calls == ["hard_drop"]


def test_handle_event_translates_keyup_to_release():
    import pygame
    ctrl, game = _ctrl(TimingConfig(das_ms=50, arr_ms=10))
    ctrl.handle_event(FakeEvent(type=pygame.KEYDOWN, key=pygame.K_LEFT), now_ms=0)
    ctrl.handle_event(FakeEvent(type=pygame.KEYUP, key=pygame.K_LEFT), now_ms=10)
    ctrl.update(now_ms=200)
    assert game.count("move_left") == 1


def test_handle_event_ignores_unknown_keys():
    import pygame
    ctrl, game = _ctrl()
    # Some key that's not bound to anything.
    result = ctrl.handle_event(FakeEvent(type=pygame.KEYDOWN, key=pygame.K_F12), now_ms=0)
    assert result is None
    assert game.calls == []


def test_handle_event_ignores_non_keyboard_events():
    import pygame
    ctrl, game = _ctrl()
    # Synthesise a mouse-motion-like event.
    result = ctrl.handle_event(FakeEvent(type=pygame.MOUSEMOTION, key=0), now_ms=0)
    assert result is None
    assert game.calls == []


def test_process_events_handles_a_batch():
    import pygame
    ctrl, game = _ctrl()
    events = [
        FakeEvent(type=pygame.KEYDOWN, key=pygame.K_LEFT),
        FakeEvent(type=pygame.KEYDOWN, key=pygame.K_UP),
        FakeEvent(type=pygame.KEYUP, key=pygame.K_LEFT),
    ]
    ctrl.process_events(events, now_ms=0)
    assert game.calls == ["move_left", "rotate_cw"]
    assert not ctrl.left_held


# ---------------------------------------------------------------------------
# Configuration & lifecycle
# ---------------------------------------------------------------------------


def test_custom_bindings_take_effect():
    import pygame
    bindings = KeyBindings().set(Action.HARD_DROP, [pygame.K_RETURN])
    game = FakeGame()
    ctrl = InputController(game, bindings=bindings)
    ctrl.handle_event(FakeEvent(type=pygame.KEYDOWN, key=pygame.K_RETURN), now_ms=0)
    assert game.calls == ["hard_drop"]


def test_rebind_swaps_lookup():
    import pygame
    ctrl, game = _ctrl()
    new = KeyBindings().set(Action.HARD_DROP, [pygame.K_TAB])
    ctrl.rebind(new)
    ctrl.handle_event(FakeEvent(type=pygame.KEYDOWN, key=pygame.K_TAB), now_ms=0)
    assert game.calls == ["hard_drop"]


def test_retime_applies_to_subsequent_repeats():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    # Tighten ARR before DAS elapses.
    ctrl.retime(TimingConfig(das_ms=100, arr_ms=5))
    ctrl.update(now_ms=100)  # first repeat at 100
    ctrl.update(now_ms=125)  # would be (100,105,110,115,120,125) = 6 repeats
    # initial + 6 == 7
    assert game.count("move_left") == 7


def test_reset_clears_held_state():
    ctrl, game = _ctrl()
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.press(Action.SOFT_DROP, now_ms=0)
    ctrl.reset()
    assert not ctrl.left_held
    assert not ctrl.soft_drop_held
    assert ctrl.active_horizontal is None
    game.reset()
    ctrl.update(now_ms=1000)
    assert game.calls == []


def test_disabled_controller_drops_gameplay_actions_but_routes_pause():
    ctrl, game = _ctrl()
    ctrl.enabled = False
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.press(Action.HARD_DROP, now_ms=0)
    ctrl.press(Action.PAUSE, now_ms=0)
    assert game.calls == ["toggle_pause"]


def test_disabled_controller_does_not_auto_repeat():
    ctrl, game = _ctrl(TimingConfig(das_ms=10, arr_ms=5))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    game.reset()
    ctrl.enabled = False
    ctrl.update(now_ms=100)
    ctrl.update(now_ms=200)
    assert game.calls == []


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_timing_config_rejects_negative_values():
    with pytest.raises(ValueError):
        TimingConfig(das_ms=-1)
    with pytest.raises(ValueError):
        TimingConfig(arr_ms=-1)
    with pytest.raises(ValueError):
        TimingConfig(soft_drop_ms=-1)
    with pytest.raises(ValueError):
        TimingConfig(max_repeats_per_tick=0)


def test_arr_zero_falls_back_to_safe_rate():
    """ARR=0 ("instant slide") would loop forever; we cap it at the
    max_repeats_per_tick safety net so the host gets predictable behaviour."""
    ctrl, game = _ctrl(
        TimingConfig(das_ms=10, arr_ms=0, max_repeats_per_tick=8)
    )
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=100)
    # Initial press + the cap.
    assert game.count("move_left") == 1 + 8


def test_default_bindings_cover_every_action_except_rotate_180():
    bindings = KeyBindings()
    for action in Action:
        keys = bindings.keys_for(action)
        if action is Action.ROTATE_180:
            assert keys == ()
        else:
            assert keys, f"{action} should have at least one default binding"


# ---------------------------------------------------------------------------
# DAS / ARR timing edges
# ---------------------------------------------------------------------------


def test_das_boundary_fires_exactly_at_das():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=99)
    assert game.count("move_left") == 1   # 1ms early: nothing
    ctrl.update(now_ms=100)
    assert game.count("move_left") == 2   # exactly at DAS: first repeat
    ctrl.update(now_ms=100)
    assert game.count("move_left") == 2   # same timestamp: no double fire
    ctrl.update(now_ms=119)
    assert game.count("move_left") == 2   # 1ms before the ARR boundary
    ctrl.update(now_ms=120)
    assert game.count("move_left") == 3   # exactly at DAS + ARR


def test_das_zero_starts_repeating_immediately():
    ctrl, game = _ctrl(TimingConfig(das_ms=0, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=0)
    assert game.count("move_left") == 2   # press + zero-delay repeat
    ctrl.update(now_ms=20)
    assert game.count("move_left") == 3   # then at ARR cadence


def test_single_late_update_catches_up_at_arr_rate():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=200)
    # Repeats due at 100,120,140,160,180,200 == 6, plus the initial press.
    assert game.count("move_left") == 7


def test_stall_backlog_is_dropped_after_cap():
    """Hitting the per-tick cap must also drop the remaining backlog —
    otherwise a long stall keeps bursting max-rate repeats for many frames."""
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20, max_repeats_per_tick=4))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=5_000)             # stall: capped at 4 repeats
    assert game.count("move_left") == 5
    ctrl.update(now_ms=5_010)             # next frame: backlog gone, nothing due
    assert game.count("move_left") == 5
    ctrl.update(now_ms=5_020)             # normal ARR cadence resumes
    assert game.count("move_left") == 6


def test_repress_same_direction_fires_and_restarts_das():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.update(now_ms=100)
    assert game.count("move_left") == 2
    # A second KEYDOWN without KEYUP (e.g. OS key-repeat) is a fresh press.
    ctrl.press(Action.MOVE_LEFT, now_ms=110)
    assert game.count("move_left") == 3
    ctrl.update(now_ms=130)
    assert game.count("move_left") == 3   # old ARR cadence is gone
    ctrl.update(now_ms=210)
    assert game.count("move_left") == 4   # DAS restarted from the re-press


def test_handover_without_timestamp_keeps_survivor_schedule():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)     # left DAS due at 100
    ctrl.press(Action.MOVE_RIGHT, now_ms=50)   # right takes over
    ctrl.release(Action.MOVE_RIGHT)            # no now_ms: left keeps old timing
    ctrl.update(now_ms=150)
    # Left repeats due at 100, 120, 140 == 3, plus each direction's press.
    assert game.count("move_left") == 4
    assert game.count("move_right") == 1


def test_inactive_held_direction_never_auto_repeats():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20))
    ctrl.press(Action.MOVE_LEFT, now_ms=0)
    ctrl.press(Action.MOVE_RIGHT, now_ms=10)   # right owns auto-repeat
    ctrl.update(now_ms=400)                    # way past left's original DAS
    assert game.count("move_left") == 1        # only the initial press
    assert game.count("move_right") >= 2


def test_update_with_nothing_held_is_a_noop():
    ctrl, game = _ctrl()
    ctrl.update(now_ms=0)
    ctrl.update(now_ms=1_000)
    assert game.calls == []


def test_retime_applies_to_soft_drop_repeats():
    ctrl, game = _ctrl(TimingConfig(das_ms=100, arr_ms=20, soft_drop_ms=10))
    ctrl.press(Action.SOFT_DROP, now_ms=0)     # next repeat at 10
    ctrl.update(now_ms=10)                     # fires; next scheduled at 20
    ctrl.retime(TimingConfig(das_ms=100, arr_ms=20, soft_drop_ms=50))
    ctrl.update(now_ms=20)                     # fires; next now at 20 + 50 = 70
    ctrl.update(now_ms=60)
    assert game.count("soft_drop") == 3        # nothing before 70
    ctrl.update(now_ms=70)
    assert game.count("soft_drop") == 4


def test_soft_drop_long_stall_caps_and_drops_backlog():
    ctrl, game = _ctrl(TimingConfig(soft_drop_ms=10, max_repeats_per_tick=6))
    ctrl.press(Action.SOFT_DROP, now_ms=0)
    ctrl.update(now_ms=10_000)
    assert game.count("soft_drop") == 1 + 6    # press + capped repeats
    ctrl.update(now_ms=10_005)
    assert game.count("soft_drop") == 1 + 6    # backlog dropped with the cap
    ctrl.update(now_ms=10_010)
    assert game.count("soft_drop") == 1 + 6 + 1


# ---------------------------------------------------------------------------
# Event adapter / binding edges
# ---------------------------------------------------------------------------


def test_handle_event_returns_fired_action_on_keydown_only():
    import pygame
    ctrl, game = _ctrl()
    down = ctrl.handle_event(FakeEvent(type=pygame.KEYDOWN, key=pygame.K_LEFT), now_ms=0)
    up = ctrl.handle_event(FakeEvent(type=pygame.KEYUP, key=pygame.K_LEFT), now_ms=10)
    assert down is Action.MOVE_LEFT
    assert up is None


def test_handle_event_tolerates_events_without_key_attribute():
    import pygame

    @dataclass
    class TypeOnlyEvent:
        type: int

    ctrl, game = _ctrl()
    result = ctrl.handle_event(TypeOnlyEvent(type=pygame.KEYDOWN), now_ms=0)
    assert result is None
    assert game.calls == []


def test_duplicate_key_across_actions_last_binding_wins():
    bindings = KeyBindings()
    key = ord("q")
    bindings.set(Action.HARD_DROP, [key])
    bindings.set(Action.HOLD, [key])  # HOLD comes later in the bindings table
    assert bindings.build_lookup()[key] is Action.HOLD
