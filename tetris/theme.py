"""Visual theme: colors, fonts, sizing.

A :class:`Theme` is a plain dataclass so callers can override individual
fields without subclassing. Color keys correspond to tetromino kinds
plus a handful of UI colors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


# Canonical modern Tetris colors (close to the Tetris Guideline palette).
PIECE_COLORS: Dict[str, RGB] = {
    "I": (45, 200, 230),   # cyan
    "O": (240, 215, 70),   # yellow
    "T": (165, 90, 200),   # purple
    "S": (90, 200, 110),   # green
    "Z": (230, 80, 95),    # red
    "J": (75, 110, 220),   # blue
    "L": (235, 145, 55),   # orange
}


@dataclass
class Theme:
    """All knobs the renderer reads from. Construct with defaults or override fields."""

    # Geometry (in pixels).
    cell_size: int = 30
    board_cols: int = 10
    board_rows: int = 20
    hud_width: int = 200
    margin: int = 20
    next_preview_count: int = 5

    # Colors.
    bg: RGB = (18, 20, 28)
    panel_bg: RGB = (28, 32, 44)
    grid_line: RGB = (40, 46, 60)
    board_border: RGB = (90, 100, 120)
    text_primary: RGB = (235, 238, 245)
    text_secondary: RGB = (160, 170, 190)
    accent: RGB = (110, 200, 255)
    ghost_alpha: int = 70  # 0..255 for ghost translucency
    locked_highlight: RGB = (255, 255, 255)
    flash_color: RGB = (255, 255, 255)
    overlay_dim: RGBA = (0, 0, 0, 170)

    # Font sizes.
    font_small: int = 16
    font_medium: int = 22
    font_large: int = 40
    font_title: int = 56

    # Piece colors keyed by kind letter; defaults to the guideline palette.
    piece_colors: Dict[str, RGB] = field(default_factory=lambda: dict(PIECE_COLORS))

    def color_for(self, key: str) -> RGB:
        """Resolve a color key to RGB. Unknown keys fall back to a neutral grey."""
        if key in self.piece_colors:
            return self.piece_colors[key]
        # Allow themes to define arbitrary keys by extending piece_colors.
        return (140, 140, 150)

    @property
    def board_pixel_width(self) -> int:
        return self.cell_size * self.board_cols

    @property
    def board_pixel_height(self) -> int:
        return self.cell_size * self.board_rows

    @property
    def window_size(self) -> Tuple[int, int]:
        # Two HUD strips: one for next/hold on the right; left margin is
        # symmetric so the board sits center-left.
        width = self.margin + self.board_pixel_width + self.margin + self.hud_width + self.margin
        height = self.margin + self.board_pixel_height + self.margin
        return width, height

    @property
    def board_origin(self) -> Tuple[int, int]:
        return self.margin, self.margin

    @property
    def hud_origin(self) -> Tuple[int, int]:
        x = self.margin + self.board_pixel_width + self.margin
        return x, self.margin


def default_theme() -> Theme:
    """Return a fresh :class:`Theme` populated with the guideline defaults."""
    return Theme()
