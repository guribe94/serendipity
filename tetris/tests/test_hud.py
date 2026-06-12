"""Headless tests for the HUD panel and overlays in ``tetris.hud``.

Like the renderer tests these run against ``SDL_VIDEODRIVER=dummy`` and
assert on rendered pixels / surface bytes rather than internals.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from tetris.hud import draw_hud, draw_overlay
from tetris.pieces import spawn_piece
from tetris.state import ActivePiece, GamePhase, RenderState, Scoreboard
from tetris.theme import default_theme

if not pygame.get_init():
    pygame.init()
if not pygame.font.get_init():
    pygame.font.init()

THEME = default_theme()


def _font(size: int) -> pygame.font.Font:
    return pygame.font.Font(None, size)


def _surface() -> pygame.Surface:
    surf = pygame.Surface(THEME.window_size, flags=pygame.SRCALPHA)
    surf.fill(THEME.bg)
    return surf


def _bytes(surf: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surf, "RGBA")


def _board_region_bytes(surf: pygame.Surface) -> bytes:
    ox, oy = THEME.board_origin
    rect = pygame.Rect(ox, oy, THEME.board_pixel_width, THEME.board_pixel_height)
    return _bytes(surf.subsurface(rect).copy())


# ---------------------------------------------------------------------------
# HUD panel
# ---------------------------------------------------------------------------

def test_draw_hud_paints_the_panel_region():
    surf = _surface()
    draw_hud(surf, RenderState(), THEME, _font)
    hud_x, hud_y = THEME.hud_origin
    sample = surf.get_at((hud_x + 8, hud_y + 8))
    assert sample[:3] != THEME.bg


def test_hold_slot_drawn_only_when_a_piece_is_held():
    without = _surface()
    draw_hud(without, RenderState(), THEME, _font)

    with_held = _surface()
    state = RenderState()
    state.held_piece = spawn_piece("L")
    draw_hud(with_held, state, THEME, _font)

    assert _bytes(without) != _bytes(with_held)


def test_next_queue_draws_at_most_preview_count_slots():
    theme = default_theme()
    theme.next_preview_count = 2
    head = [spawn_piece("I"), spawn_piece("O")]

    exact = _surface()
    state_exact = RenderState(next_pieces=list(head))
    draw_hud(exact, state_exact, theme, _font)

    overfull = _surface()
    state_overfull = RenderState(
        next_pieces=list(head) + [spawn_piece(k) for k in ("T", "S", "Z")]
    )
    draw_hud(overfull, state_overfull, theme, _font)

    # Pieces beyond the preview count must not change the rendering at all.
    assert _bytes(exact) == _bytes(overfull)


def test_scoreboard_text_varies_with_values():
    low = _surface()
    draw_hud(low, RenderState(scoreboard=Scoreboard()), THEME, _font)
    high = _surface()
    draw_hud(
        high,
        RenderState(scoreboard=Scoreboard(score=987_654, level=12, lines=240)),
        THEME,
        _font,
    )
    assert _bytes(low) != _bytes(high)


def test_piece_thumbnail_with_no_cells_is_skipped():
    surf = _surface()
    state = RenderState()
    state.held_piece = ActivePiece(kind="T", cells=[])
    state.next_pieces = [ActivePiece(kind="I", cells=[])]
    draw_hud(surf, state, THEME, _font)  # must not raise


# ---------------------------------------------------------------------------
# Overlays
# ---------------------------------------------------------------------------

def test_overlay_is_a_noop_while_playing_without_message():
    surf = _surface()
    before = _bytes(surf)
    draw_overlay(surf, RenderState(phase=GamePhase.PLAYING), THEME, _font)
    assert _bytes(surf) == before


def test_overlay_draws_floating_message_while_playing():
    surf = _surface()
    before = _bytes(surf)
    state = RenderState(phase=GamePhase.PLAYING, message="TETRIS!")
    draw_overlay(surf, state, THEME, _font)
    assert _bytes(surf) != before


def test_overlay_dims_the_board_in_every_non_playing_phase():
    ox, oy = THEME.board_origin
    board_rect = pygame.Rect(ox, oy, THEME.board_pixel_width, THEME.board_pixel_height)
    for phase in (GamePhase.START, GamePhase.PAUSED, GamePhase.GAME_OVER):
        surf = _surface()
        surf.fill((255, 255, 255), board_rect)
        draw_overlay(surf, RenderState(phase=phase), THEME, _font)
        # Sample a corner pixel inside the board where no overlay text lands.
        corner = surf.get_at((ox + 3, oy + 3))
        assert sum(corner[:3]) < 3 * 255, f"{phase} did not dim the board"


def test_game_over_overlay_renders_the_final_score():
    zero = _surface()
    draw_overlay(
        zero,
        RenderState(phase=GamePhase.GAME_OVER, scoreboard=Scoreboard()),
        THEME,
        _font,
    )
    big = _surface()
    draw_overlay(
        big,
        RenderState(
            phase=GamePhase.GAME_OVER,
            scoreboard=Scoreboard(score=9_876_543, level=20, lines=412),
        ),
        THEME,
        _font,
    )
    assert _board_region_bytes(zero) != _board_region_bytes(big)
