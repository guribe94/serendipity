"""HUD panel + overlay drawing.

Split out from :mod:`tetris.renderer` so the playfield code stays focused
on the board. The HUD owns the score / level / lines counters, the
next-piece preview queue, the hold slot, and the start / pause /
game-over overlays.
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional, Sequence, Tuple

import pygame

from .state import ActivePiece, GamePhase, RenderState
from .theme import Theme

FontFactory = Callable[[int], pygame.font.Font]


# ---------------------------------------------------------------------------
# HUD panel: next preview + scoreboard
# ---------------------------------------------------------------------------

def draw_hud(
    surface: pygame.Surface,
    state: RenderState,
    theme: Theme,
    font: FontFactory,
) -> None:
    """Draw the right-hand HUD panel."""
    ox, oy = theme.hud_origin
    panel_rect = pygame.Rect(ox, oy, theme.hud_width, theme.board_pixel_height)
    pygame.draw.rect(surface, theme.panel_bg, panel_rect, border_radius=8)
    pygame.draw.rect(surface, theme.board_border, panel_rect, 2, border_radius=8)

    cursor_y = oy + 14

    cursor_y = _draw_scoreboard(surface, state, theme, font, ox, cursor_y)
    cursor_y += 12

    if state.held_piece is not None:
        cursor_y = _draw_hold_slot(surface, state, theme, font, ox, cursor_y)
        cursor_y += 12

    _draw_next_queue(surface, state, theme, font, ox, cursor_y)


def _draw_scoreboard(
    surface: pygame.Surface,
    state: RenderState,
    theme: Theme,
    font: FontFactory,
    ox: int,
    y: int,
) -> int:
    sb = state.scoreboard
    label_font = font(theme.font_small)
    value_font = font(theme.font_medium)

    rows: Sequence[Tuple[str, str]] = (
        ("SCORE", f"{sb.score:,}"),
        ("LEVEL", str(sb.level)),
        ("LINES", str(sb.lines)),
    )
    inner_x = ox + 16
    for label, value in rows:
        label_surf = label_font.render(label, True, theme.text_secondary)
        value_surf = value_font.render(value, True, theme.text_primary)
        surface.blit(label_surf, (inner_x, y))
        surface.blit(
            value_surf,
            (inner_x, y + label_surf.get_height() + 2),
        )
        y += label_surf.get_height() + value_surf.get_height() + 8
    return y


def _draw_hold_slot(
    surface: pygame.Surface,
    state: RenderState,
    theme: Theme,
    font: FontFactory,
    ox: int,
    y: int,
) -> int:
    label = font(theme.font_small).render("HOLD", True, theme.text_secondary)
    surface.blit(label, (ox + 16, y))
    y += label.get_height() + 4
    box_size = theme.cell_size * 4 + 12
    box = pygame.Rect(ox + 16, y, theme.hud_width - 32, box_size // 2 + 24)
    pygame.draw.rect(surface, theme.bg, box, border_radius=6)
    pygame.draw.rect(surface, theme.grid_line, box, 1, border_radius=6)
    if state.held_piece is not None:
        _draw_piece_thumbnail(surface, state.held_piece, theme, box)
    return y + box.height


def _draw_next_queue(
    surface: pygame.Surface,
    state: RenderState,
    theme: Theme,
    font: FontFactory,
    ox: int,
    y: int,
) -> None:
    label = font(theme.font_small).render("NEXT", True, theme.text_secondary)
    surface.blit(label, (ox + 16, y))
    y += label.get_height() + 6

    # Up to ``theme.next_preview_count`` slots, each a small box.
    slot_w = theme.hud_width - 32
    slot_h = int(theme.cell_size * 2.2)
    spacing = 6
    pieces = list(state.next_pieces)[: theme.next_preview_count]
    for piece in pieces:
        slot = pygame.Rect(ox + 16, y, slot_w, slot_h)
        pygame.draw.rect(surface, theme.bg, slot, border_radius=4)
        pygame.draw.rect(surface, theme.grid_line, slot, 1, border_radius=4)
        _draw_piece_thumbnail(surface, piece, theme, slot)
        y += slot_h + spacing


def _draw_piece_thumbnail(
    surface: pygame.Surface,
    piece: ActivePiece,
    theme: Theme,
    box: pygame.Rect,
) -> None:
    """Draw a piece centered inside ``box``, scaled down to fit."""
    cells = list(piece.cells)
    if not cells:
        return
    cols = [c for c, _ in cells]
    rows = [r for _, r in cells]
    min_c, max_c = min(cols), max(cols)
    min_r, max_r = min(rows), max(rows)
    width_cells = max_c - min_c + 1
    height_cells = max_r - min_r + 1

    # Fit within box with a little padding.
    pad = 6
    max_cell_w = (box.width - 2 * pad) // max(width_cells, 1)
    max_cell_h = (box.height - 2 * pad) // max(height_cells, 1)
    cell = max(4, min(max_cell_w, max_cell_h, theme.cell_size))

    block_w = width_cells * cell
    block_h = height_cells * cell
    start_x = box.x + (box.width - block_w) // 2
    start_y = box.y + (box.height - block_h) // 2

    color = theme.color_for(piece.color_key or piece.kind)
    for c, r in cells:
        x = start_x + (c - min_c) * cell
        y = start_y + (r - min_r) * cell
        rect = pygame.Rect(x, y, cell, cell)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, _shade(color, 0.55), rect, 1)


# ---------------------------------------------------------------------------
# Overlays: start, pause, game over
# ---------------------------------------------------------------------------

def draw_overlay(
    surface: pygame.Surface,
    state: RenderState,
    theme: Theme,
    font: FontFactory,
) -> None:
    """Dim the playfield and draw a phase-specific message when not playing."""
    if state.phase == GamePhase.PLAYING:
        # In-play status message (e.g. "TETRIS!", "BACK-TO-BACK") if set.
        if state.message:
            _draw_floating_message(surface, state.message, theme, font)
        return

    _dim_board(surface, theme)
    if state.phase == GamePhase.START:
        _draw_start_screen(surface, theme, font)
    elif state.phase == GamePhase.PAUSED:
        _draw_paused(surface, theme, font)
    elif state.phase == GamePhase.GAME_OVER:
        _draw_game_over(surface, state, theme, font)


def _dim_board(surface: pygame.Surface, theme: Theme) -> None:
    ox, oy = theme.board_origin
    dim = pygame.Surface(
        (theme.board_pixel_width, theme.board_pixel_height), flags=pygame.SRCALPHA
    )
    dim.fill(theme.overlay_dim)
    surface.blit(dim, (ox, oy))


def _draw_centered(
    surface: pygame.Surface,
    text: str,
    font_obj: pygame.font.Font,
    color: Tuple[int, int, int],
    center_x: int,
    y: int,
) -> int:
    text_surf = font_obj.render(text, True, color)
    rect = text_surf.get_rect(center=(center_x, y + text_surf.get_height() // 2))
    surface.blit(text_surf, rect)
    return rect.bottom


def _draw_start_screen(
    surface: pygame.Surface, theme: Theme, font: FontFactory
) -> None:
    ox, oy = theme.board_origin
    cx = ox + theme.board_pixel_width // 2
    title_font = font(theme.font_title)
    sub_font = font(theme.font_medium)
    hint_font = font(theme.font_small)

    y = oy + theme.board_pixel_height // 2 - 110
    y = _draw_centered(surface, "TETRIS", title_font, theme.accent, cx, y)
    y += 6
    y = _draw_centered(
        surface, "Modern Edition", sub_font, theme.text_primary, cx, y
    )
    y += 30
    for line in (
        "Press ENTER to start",
        "",
        "Controls",
        "Arrows: Move / Soft drop",
        "Z / X: Rotate",
        "Space: Hard drop  |  P: Pause",
    ):
        if line:
            color = (
                theme.text_primary
                if line.startswith("Press") or line == "Controls"
                else theme.text_secondary
            )
            y = _draw_centered(surface, line, hint_font, color, cx, y)
        y += hint_font.get_height() + 2


def _draw_paused(
    surface: pygame.Surface, theme: Theme, font: FontFactory
) -> None:
    ox, oy = theme.board_origin
    cx = ox + theme.board_pixel_width // 2
    cy = oy + theme.board_pixel_height // 2
    _draw_centered(
        surface, "PAUSED", font(theme.font_title), theme.text_primary, cx, cy - 40
    )
    _draw_centered(
        surface,
        "Press P to resume",
        font(theme.font_small),
        theme.text_secondary,
        cx,
        cy + 30,
    )


def _draw_game_over(
    surface: pygame.Surface,
    state: RenderState,
    theme: Theme,
    font: FontFactory,
) -> None:
    ox, oy = theme.board_origin
    cx = ox + theme.board_pixel_width // 2
    cy = oy + theme.board_pixel_height // 2

    y = cy - 90
    y = _draw_centered(
        surface, "GAME OVER", font(theme.font_title), (235, 90, 100), cx, y
    )
    y += 18
    y = _draw_centered(
        surface,
        f"Score  {state.scoreboard.score:,}",
        font(theme.font_medium),
        theme.text_primary,
        cx,
        y,
    )
    y += 4
    y = _draw_centered(
        surface,
        f"Level {state.scoreboard.level}   Lines {state.scoreboard.lines}",
        font(theme.font_small),
        theme.text_secondary,
        cx,
        y,
    )
    y += 24
    _draw_centered(
        surface,
        "Press ENTER to play again",
        font(theme.font_small),
        theme.accent,
        cx,
        y,
    )


def _draw_floating_message(
    surface: pygame.Surface,
    text: str,
    theme: Theme,
    font: FontFactory,
) -> None:
    """In-play notification (e.g. 'TETRIS!') near the top of the board."""
    ox, oy = theme.board_origin
    cx = ox + theme.board_pixel_width // 2
    f = font(theme.font_medium)
    surf = f.render(text, True, theme.accent)
    bg = pygame.Surface(
        (surf.get_width() + 16, surf.get_height() + 8), flags=pygame.SRCALPHA
    )
    bg.fill((0, 0, 0, 140))
    bg_rect = bg.get_rect(center=(cx, oy + 28))
    surface.blit(bg, bg_rect)
    surf_rect = surf.get_rect(center=bg_rect.center)
    surface.blit(surf, surf_rect)


def _shade(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)  # type: ignore[return-value]
