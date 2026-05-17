"""Renderers for ghost piece and next-piece queue.

The subsystem ships three implementations:

* ``PreviewRenderer`` — the Protocol every renderer satisfies, so the HUD
  subsystem can plug in its own implementation.
* ``NullRenderer`` — a no-op recorder used by tests and headless servers.
* ``PygameRenderer`` — a working pygame implementation that draws the ghost
  onto a playfield surface and the next-piece queue into a side panel.
  Pygame is imported lazily so this module is safe to import in environments
  where pygame isn't installed.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Protocol, Tuple

from .pieces import COLORS, SHAPES, PieceKind, Tetromino

Color = Tuple[int, int, int]


class PreviewRenderer(Protocol):
    """Anything that can draw a ghost piece and a next-piece queue."""

    def render_ghost(self, ghost: Tetromino) -> None: ...
    def render_next_queue(self, kinds: Iterable[PieceKind]) -> None: ...


class NullRenderer:
    """No-op renderer that records calls for tests and headless integration."""

    def __init__(self) -> None:
        self.ghost_calls: List[Tetromino] = []
        self.queue_calls: List[List[PieceKind]] = []

    def render_ghost(self, ghost: Tetromino) -> None:
        self.ghost_calls.append(ghost)

    def render_next_queue(self, kinds: Iterable[PieceKind]) -> None:
        self.queue_calls.append(list(kinds))


class PygameRenderer:
    """Pygame implementation of ``PreviewRenderer``.

    ``playfield_surface`` is the surface the active playfield is drawn onto;
    the ghost is blitted there using the ``playfield_origin`` offset and
    ``cell_size``. ``next_panel_surface`` is a separate side-panel surface
    that the renderer owns — it clears the panel and stacks mini pieces
    vertically.
    """

    DEFAULT_PANEL_BG: Color = (20, 20, 28)

    def __init__(
        self,
        playfield_surface,
        next_panel_surface,
        *,
        cell_size: int = 30,
        playfield_origin: Tuple[int, int] = (0, 0),
        ghost_alpha: int = 80,
        next_cell_size: Optional[int] = None,
        next_padding: int = 12,
        panel_bg: Optional[Color] = None,
    ) -> None:
        import pygame  # lazy: don't force a pygame dependency on importers

        self._pygame = pygame
        self._playfield = playfield_surface
        self._panel = next_panel_surface
        self._cell_size = cell_size
        self._origin = playfield_origin
        self._ghost_alpha = max(0, min(255, ghost_alpha))
        self._next_cell_size = next_cell_size or max(12, cell_size // 2)
        self._next_padding = next_padding
        self._panel_bg = panel_bg if panel_bg is not None else self.DEFAULT_PANEL_BG

    def render_ghost(self, ghost: Optional[Tetromino]) -> None:
        if ghost is None:
            return
        pygame = self._pygame
        cs = self._cell_size
        ox, oy = self._origin
        fill = (*ghost.color, self._ghost_alpha)
        outline = (*ghost.color, min(255, self._ghost_alpha + 120))
        cell_surf = pygame.Surface((cs, cs), pygame.SRCALPHA)
        cell_surf.fill(fill)
        pygame.draw.rect(cell_surf, outline, cell_surf.get_rect(), width=2)
        for col, row in ghost.cells:
            self._playfield.blit(cell_surf, (ox + col * cs, oy + row * cs))

    def render_next_queue(self, kinds: Iterable[PieceKind]) -> None:
        pygame = self._pygame
        cs = self._next_cell_size
        pad = self._next_padding
        panel_w = self._panel.get_width()
        self._panel.fill(self._panel_bg)
        row_height = 4 * cs + pad
        y = pad
        for kind in kinds:
            self._draw_mini_piece(kind, top=y, panel_width=panel_w, cell=cs)
            y += row_height

    def _draw_mini_piece(
        self,
        kind: PieceKind,
        *,
        top: int,
        panel_width: int,
        cell: int,
    ) -> None:
        pygame = self._pygame
        shape = SHAPES[kind]
        color = COLORS[kind]
        min_col = min(c for c, _ in shape)
        max_col = max(c for c, _ in shape)
        min_row = min(r for _, r in shape)
        max_row = max(r for _, r in shape)
        w = max_col - min_col + 1
        offset_x = (panel_width - w * cell) // 2
        offset_y = top
        for c, r in shape:
            x = offset_x + (c - min_col) * cell
            y = offset_y + (r - min_row) * cell
            pygame.draw.rect(self._panel, color, (x, y, cell - 1, cell - 1))
            pygame.draw.rect(self._panel, (250, 250, 250), (x, y, cell - 1, cell - 1), width=1)
