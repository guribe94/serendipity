"""Main rendering orchestrator.

The :class:`Renderer` is constructed once and called every frame with a
:class:`tetris.state.RenderState`. It draws the playfield, the active
piece, the ghost projection, and delegates HUD and overlays to the
``hud`` module.

The renderer is deliberately stateless beyond cached fonts and the
theme; the surface it draws onto is owned by the caller. This makes it
trivial to test against a headless SDL surface or to embed the game in
a host application.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

import pygame

from . import hud
from .state import (
    BOARD_COLS,
    HIDDEN_ROWS,
    ActivePiece,
    Cell,
    GamePhase,
    RenderState,
)
from .theme import Theme, default_theme


class Renderer:
    """Renders a :class:`RenderState` onto a pygame surface."""

    def __init__(self, theme: Optional[Theme] = None):
        # pygame.font requires pygame.init() (or pygame.font.init()).
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        self.theme = theme or default_theme()
        self._fonts: dict[int, pygame.font.Font] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_surface(self) -> pygame.Surface:
        """Create a surface sized for this theme. Useful for offscreen renders."""
        return pygame.Surface(self.theme.window_size, flags=pygame.SRCALPHA)

    def draw(self, surface: pygame.Surface, state: RenderState) -> None:
        """Top-level draw entry point. Renders everything for one frame."""
        theme = self.theme
        surface.fill(theme.bg)

        self._draw_playfield(surface, state)
        self._draw_locked_blocks(surface, state)
        if state.ghost_piece is not None and state.phase == GamePhase.PLAYING:
            self._draw_ghost(surface, state.ghost_piece)
        if state.active_piece is not None and state.phase in (
            GamePhase.PLAYING,
            GamePhase.PAUSED,
        ):
            self._draw_piece(surface, state.active_piece)
        if state.last_clear_rows:
            self._draw_clear_flash(surface, state.last_clear_rows)

        hud.draw_hud(surface, state, theme, self._font)
        hud.draw_overlay(surface, state, theme, self._font)

    # ------------------------------------------------------------------
    # Playfield
    # ------------------------------------------------------------------

    def _draw_playfield(self, surface: pygame.Surface, state: RenderState) -> None:
        theme = self.theme
        ox, oy = theme.board_origin
        rect = pygame.Rect(ox, oy, theme.board_pixel_width, theme.board_pixel_height)
        pygame.draw.rect(surface, theme.panel_bg, rect)

        # Faint grid lines.
        for col in range(1, theme.board_cols):
            x = ox + col * theme.cell_size
            pygame.draw.line(
                surface,
                theme.grid_line,
                (x, oy),
                (x, oy + theme.board_pixel_height),
                1,
            )
        for row in range(1, theme.board_rows):
            y = oy + row * theme.cell_size
            pygame.draw.line(
                surface,
                theme.grid_line,
                (ox, y),
                (ox + theme.board_pixel_width, y),
                1,
            )
        pygame.draw.rect(surface, theme.board_border, rect, 2)

    def _draw_locked_blocks(self, surface: pygame.Surface, state: RenderState) -> None:
        for visible_row in range(self.theme.board_rows):
            board_row = visible_row + HIDDEN_ROWS
            if board_row >= len(state.board):
                continue
            row = state.board[board_row]
            for col in range(min(BOARD_COLS, len(row))):
                key = row[col]
                if key is None:
                    continue
                self._draw_block(surface, col, visible_row, self.theme.color_for(key))

    # ------------------------------------------------------------------
    # Pieces
    # ------------------------------------------------------------------

    def _draw_piece(self, surface: pygame.Surface, piece: ActivePiece) -> None:
        color = self.theme.color_for(piece.color_key or piece.kind)
        for col, row in piece.cells:
            visible_row = row - HIDDEN_ROWS
            if 0 <= visible_row < self.theme.board_rows and 0 <= col < BOARD_COLS:
                self._draw_block(surface, col, visible_row, color)

    def _draw_ghost(self, surface: pygame.Surface, piece: ActivePiece) -> None:
        """Render the ghost piece as a translucent outline + dim fill."""
        theme = self.theme
        base = theme.color_for(piece.color_key or piece.kind)
        alpha = theme.ghost_alpha
        size = theme.cell_size
        ox, oy = theme.board_origin

        ghost_surface = pygame.Surface((size, size), flags=pygame.SRCALPHA)
        ghost_surface.fill((*base, alpha))
        # Solid outline so the ghost is visible against any background.
        pygame.draw.rect(ghost_surface, (*base, 220), ghost_surface.get_rect(), 2)

        for col, row in piece.cells:
            visible_row = row - HIDDEN_ROWS
            if not (0 <= visible_row < theme.board_rows and 0 <= col < BOARD_COLS):
                continue
            x = ox + col * size
            y = oy + visible_row * size
            surface.blit(ghost_surface, (x, y))

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------

    def _draw_clear_flash(
        self, surface: pygame.Surface, rows: Sequence[int]
    ) -> None:
        theme = self.theme
        ox, oy = theme.board_origin
        flash = pygame.Surface(
            (theme.board_pixel_width, theme.cell_size), flags=pygame.SRCALPHA
        )
        flash.fill((*theme.flash_color, 160))
        for board_row in rows:
            visible_row = board_row - HIDDEN_ROWS
            if 0 <= visible_row < theme.board_rows:
                surface.blit(flash, (ox, oy + visible_row * theme.cell_size))

    # ------------------------------------------------------------------
    # Block drawing primitive
    # ------------------------------------------------------------------

    def _draw_block(
        self,
        surface: pygame.Surface,
        col: int,
        visible_row: int,
        color: Tuple[int, int, int],
    ) -> None:
        """Draw one block at visible (col, visible_row) with a soft bevel."""
        theme = self.theme
        ox, oy = theme.board_origin
        size = theme.cell_size
        x = ox + col * size
        y = oy + visible_row * size
        rect = pygame.Rect(x, y, size, size)
        pygame.draw.rect(surface, color, rect)

        # Bevel: a lighter top/left and darker bottom/right for depth.
        light = _shade(color, 1.25)
        dark = _shade(color, 0.65)
        inset = max(1, size // 12)
        pygame.draw.line(surface, light, (x, y), (x + size - 1, y), inset)
        pygame.draw.line(surface, light, (x, y), (x, y + size - 1), inset)
        pygame.draw.line(
            surface, dark, (x, y + size - 1), (x + size - 1, y + size - 1), inset
        )
        pygame.draw.line(
            surface, dark, (x + size - 1, y), (x + size - 1, y + size - 1), inset
        )
        # Inner outline for crispness.
        pygame.draw.rect(surface, _shade(color, 0.5), rect, 1)

    # ------------------------------------------------------------------
    # Font cache
    # ------------------------------------------------------------------

    def _font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            # Try a system mono first; fall back to pygame's bundled font
            # so we don't depend on fontconfig being installed.
            font: Optional[pygame.font.Font] = None
            try:
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    font = pygame.font.SysFont(
                        "dejavusansmono,monospace", size, bold=True
                    )
            except pygame.error:
                font = None
            if font is None:
                font = pygame.font.Font(None, size)
            self._fonts[size] = font
        return self._fonts[size]


def _shade(color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    """Multiply RGB by ``factor``, clamped to 0..255."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)  # type: ignore[return-value]
