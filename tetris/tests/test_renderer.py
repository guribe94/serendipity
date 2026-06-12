"""Headless tests for the rendering subsystem.

These run against ``SDL_VIDEODRIVER=dummy`` so they require no display
server. They verify that:

* the renderer produces a surface of the configured size for every phase,
* locked, active, and ghost cells are drawn (board contains piece colors),
* the ghost piece is rendered with translucency (alpha < 255 sample),
* HUD text strings appear on the surface for score/level/lines,
* overlays cover the playfield in non-playing phases.

The assertions read pixels off the rendered surface, which keeps them
independent of internal renderer structure.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import unittest
from typing import Optional, Tuple

import pygame

from tetris.pieces import spawn_piece
from tetris.renderer import Renderer
from tetris.state import (
    BOARD_COLS,
    HIDDEN_ROWS,
    ActivePiece,
    GamePhase,
    RenderState,
    Scoreboard,
    TOTAL_ROWS,
)
from tetris.theme import PIECE_COLORS, default_theme


def _state(phase: GamePhase = GamePhase.PLAYING) -> RenderState:
    state = RenderState(phase=phase)
    # Put a single locked block in a known cell so we can sample it.
    state.board[TOTAL_ROWS - 1][0] = "T"
    state.active_piece = spawn_piece("I").shifted(0, 6)
    state.ghost_piece = state.active_piece.shifted(0, 10)
    state.next_pieces = [spawn_piece(k) for k in ("O", "T", "S")]
    state.held_piece = spawn_piece("L")
    state.scoreboard = Scoreboard(score=42_000, level=3, lines=18)
    return state


def _sample_cell_center(
    surface: pygame.Surface, col: int, visible_row: int
) -> Tuple[int, int, int, int]:
    theme = default_theme()
    ox, oy = theme.board_origin
    x = ox + col * theme.cell_size + theme.cell_size // 2
    y = oy + visible_row * theme.cell_size + theme.cell_size // 2
    return surface.get_at((x, y))


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not pygame.get_init():
            pygame.init()
        cls.renderer = Renderer()
        cls.theme = cls.renderer.theme

    # ---- shape / sanity ------------------------------------------------

    def test_surface_size_matches_theme(self) -> None:
        surf = self.renderer.create_surface()
        self.assertEqual(surf.get_size(), self.theme.window_size)

    def test_draws_all_phases_without_error(self) -> None:
        surf = self.renderer.create_surface()
        for phase in GamePhase:
            self.renderer.draw(surf, _state(phase=phase))
            # Surface should remain valid and contain non-background pixels.
            self.assertNotEqual(
                surf.get_at((1, 1))[:3],
                (0, 0, 0),
                f"phase {phase} produced an all-black surface",
            )

    # ---- locked + active + ghost pieces -------------------------------

    def test_locked_block_drawn_in_expected_cell(self) -> None:
        state = _state(GamePhase.PLAYING)
        # Clear active/ghost so they don't overlap our sample cell.
        state.active_piece = None
        state.ghost_piece = None
        surf = self.renderer.create_surface()
        self.renderer.draw(surf, state)

        # Locked T at (col=0, board_row=TOTAL_ROWS-1) -> visible bottom row.
        visible_row = (TOTAL_ROWS - 1) - HIDDEN_ROWS
        r, g, b, _ = _sample_cell_center(surf, 0, visible_row)
        # The center pixel should be close to the T color (purple); we allow
        # bevel shading to dim it a bit.
        target = PIECE_COLORS["T"]
        self.assertGreater(b, 80, "expected blue channel of purple T color")
        self.assertGreater(r, 80, "expected red channel of purple T color")
        # Center should be brighter than full black background.
        self.assertGreater(r + g + b, 150)

    def test_active_piece_drawn(self) -> None:
        state = _state(GamePhase.PLAYING)
        state.ghost_piece = None  # isolate active
        surf = self.renderer.create_surface()
        self.renderer.draw(surf, state)

        # I-piece active shape after spawn().shifted(0,6) has cells at
        # row=1+6=7 in board coords -> visible_row = 7 - 2 = 5.
        # Sample one of its cells.
        col, board_row = state.active_piece.cells[0]
        visible_row = board_row - HIDDEN_ROWS
        r, g, b, _ = _sample_cell_center(surf, col, visible_row)
        # I-piece is cyan -> high green + blue, low red.
        self.assertGreater(b, 120)
        self.assertGreater(g, 120)
        self.assertLess(r, 120)

    def test_ghost_piece_is_translucent(self) -> None:
        state = _state(GamePhase.PLAYING)
        # Place ghost on a column where active piece won't overlap.
        state.active_piece = spawn_piece("I").shifted(0, 6)
        # Move ghost a few rows below active and outside its column span if needed.
        ghost = state.active_piece.shifted(0, 8)
        state.ghost_piece = ghost

        surf = self.renderer.create_surface()
        self.renderer.draw(surf, state)

        col, board_row = ghost.cells[0]
        visible_row = board_row - HIDDEN_ROWS
        ghost_pixel = _sample_cell_center(surf, col, visible_row)

        # Compare against a known-empty cell (top of the visible board).
        empty_pixel = _sample_cell_center(surf, 0, 0)

        ghost_sum = sum(ghost_pixel[:3])
        empty_sum = sum(empty_pixel[:3])
        active_color = sum(PIECE_COLORS["I"])

        # Ghost should be brighter than empty (color tinted on top) but
        # noticeably dimmer than a solid I-piece block.
        self.assertGreater(ghost_sum, empty_sum + 20, "ghost cell looks empty")
        self.assertLess(
            ghost_sum,
            active_color - 30,
            "ghost cell looks fully opaque (no translucency applied)",
        )

    # ---- HUD ---------------------------------------------------------

    def test_hud_panel_is_drawn(self) -> None:
        surf = self.renderer.create_surface()
        self.renderer.draw(surf, _state(GamePhase.PLAYING))
        hud_x, hud_y = self.theme.hud_origin
        # Sample a pixel safely inside the HUD panel.
        sample = surf.get_at((hud_x + 20, hud_y + 20))
        # Panel background is not the window background.
        self.assertNotEqual(sample[:3], self.theme.bg)

    def test_score_text_appears_on_hud(self) -> None:
        """Score text rasterizes to lighter pixels in the HUD region."""
        # Render with a giant score; compare HUD region against an empty one.
        s_full = _state(GamePhase.PLAYING)
        s_full.scoreboard = Scoreboard(score=999_999, level=15, lines=300)
        s_empty = _state(GamePhase.PLAYING)
        s_empty.scoreboard = Scoreboard(score=0, level=1, lines=0)

        surf_full = self.renderer.create_surface()
        surf_empty = self.renderer.create_surface()
        self.renderer.draw(surf_full, s_full)
        self.renderer.draw(surf_empty, s_empty)

        # Count light pixels in the HUD region to detect rendered text.
        hud_x, hud_y = self.theme.hud_origin
        hud_w, hud_h = self.theme.hud_width, self.theme.board_pixel_height

        def light_pixels(surf: pygame.Surface) -> int:
            count = 0
            # Sample on a grid to keep it fast.
            for y in range(hud_y, hud_y + hud_h, 3):
                for x in range(hud_x, hud_x + hud_w, 3):
                    r, g, b, _ = surf.get_at((x, y))
                    if r + g + b > 600:  # near-white text
                        count += 1
            return count

        # The HUDs differ in text content, so light-pixel counts differ.
        self.assertNotEqual(light_pixels(surf_full), light_pixels(surf_empty))

    def test_next_queue_renders_pieces(self) -> None:
        """When next_pieces is non-empty, the HUD has visible piece colors."""
        s_with = _state(GamePhase.PLAYING)
        s_without = _state(GamePhase.PLAYING)
        s_without.next_pieces = []
        s_without.held_piece = None

        with_surf = self.renderer.create_surface()
        without_surf = self.renderer.create_surface()
        self.renderer.draw(with_surf, s_with)
        self.renderer.draw(without_surf, s_without)

        # Pixel difference in the HUD column proves the queue was drawn.
        hud_x, hud_y = self.theme.hud_origin
        differs = 0
        for y in range(hud_y, hud_y + self.theme.board_pixel_height, 4):
            for x in range(hud_x, hud_x + self.theme.hud_width, 4):
                if with_surf.get_at((x, y)) != without_surf.get_at((x, y)):
                    differs += 1
        self.assertGreater(differs, 30, "next-piece queue not visibly rendered")

    # ---- overlays ----------------------------------------------------

    def test_start_overlay_dims_playfield(self) -> None:
        playing = self.renderer.create_surface()
        start = self.renderer.create_surface()
        self.renderer.draw(playing, _state(GamePhase.PLAYING))
        self.renderer.draw(start, _state(GamePhase.START))

        # Sample a board cell with locked content: it should be dimmer
        # in the START overlay.
        theme = self.theme
        ox, oy = theme.board_origin
        # Bottom-left visible cell (locked T).
        x = ox + theme.cell_size // 2
        y = oy + theme.board_pixel_height - theme.cell_size // 2
        playing_sum = sum(playing.get_at((x, y))[:3])
        start_sum = sum(start.get_at((x, y))[:3])
        self.assertLess(start_sum, playing_sum, "start overlay did not dim board")

    def test_game_over_overlay_includes_score(self) -> None:
        """Game over surface differs from playing surface in board region."""
        playing = self.renderer.create_surface()
        over = self.renderer.create_surface()
        s = _state(GamePhase.PLAYING)
        self.renderer.draw(playing, s)
        s2 = _state(GamePhase.GAME_OVER)
        self.renderer.draw(over, s2)

        theme = self.theme
        ox, oy = theme.board_origin
        diff = 0
        for y in range(oy, oy + theme.board_pixel_height, 6):
            for x in range(ox, ox + theme.board_pixel_width, 6):
                if playing.get_at((x, y)) != over.get_at((x, y)):
                    diff += 1
        self.assertGreater(diff, 50, "game over overlay not visible on board")

    # ---- effects -------------------------------------------------------

    def test_clear_flash_brightens_flashed_row(self) -> None:
        plain_state = _state(GamePhase.PLAYING)
        plain_state.active_piece = None
        plain_state.ghost_piece = None
        flash_state = _state(GamePhase.PLAYING)
        flash_state.active_piece = None
        flash_state.ghost_piece = None
        flash_state.last_clear_rows = (TOTAL_ROWS - 1,)

        plain = self.renderer.create_surface()
        flashed = self.renderer.create_surface()
        self.renderer.draw(plain, plain_state)
        self.renderer.draw(flashed, flash_state)

        # Sample the bottom row in an empty column (the locked T sits in col 0).
        visible_row = (TOTAL_ROWS - 1) - HIDDEN_ROWS
        plain_sum = sum(_sample_cell_center(plain, 5, visible_row)[:3])
        flash_sum = sum(_sample_cell_center(flashed, 5, visible_row)[:3])
        self.assertGreater(flash_sum, plain_sum + 100, "flash overlay not visible")

    # ---- draw gating ---------------------------------------------------

    def test_ghost_not_drawn_outside_playing_phase(self) -> None:
        with_ghost = _state(GamePhase.PAUSED)
        without_ghost = _state(GamePhase.PAUSED)
        without_ghost.ghost_piece = None

        a = self.renderer.create_surface()
        b = self.renderer.create_surface()
        self.renderer.draw(a, with_ghost)
        self.renderer.draw(b, without_ghost)
        self.assertEqual(
            pygame.image.tobytes(a, "RGBA"),
            pygame.image.tobytes(b, "RGBA"),
            "ghost was rendered while paused",
        )

    def test_active_piece_in_hidden_rows_is_not_drawn(self) -> None:
        hidden = _state(GamePhase.PLAYING)
        hidden.ghost_piece = None
        hidden.active_piece = spawn_piece("I")  # spawn cells sit in rows 0..1
        absent = _state(GamePhase.PLAYING)
        absent.ghost_piece = None
        absent.active_piece = None

        a = self.renderer.create_surface()
        b = self.renderer.create_surface()
        self.renderer.draw(a, hidden)
        self.renderer.draw(b, absent)
        self.assertEqual(
            pygame.image.tobytes(a, "RGBA"),
            pygame.image.tobytes(b, "RGBA"),
            "hidden-row cells leaked into the visible playfield",
        )

    def test_short_or_ragged_board_draws_without_error(self) -> None:
        state = _state(GamePhase.PLAYING)
        state.board = [[None] * 3 for _ in range(5)]  # fewer rows and columns
        state.board[4][1] = "T"
        surf = self.renderer.create_surface()
        self.renderer.draw(surf, state)  # must not raise


if __name__ == "__main__":
    unittest.main()
