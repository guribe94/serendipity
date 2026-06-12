"""Tests for ``tetris.theme``: palette lookups and layout geometry."""

from tetris.tetromino import KINDS
from tetris.theme import PIECE_COLORS, Theme, default_theme


def test_guideline_palette_covers_all_seven_kinds():
    assert set(PIECE_COLORS) == set(KINDS)
    for rgb in PIECE_COLORS.values():
        assert len(rgb) == 3
        assert all(0 <= channel <= 255 for channel in rgb)


def test_color_for_resolves_known_piece_kinds():
    theme = default_theme()
    for kind in KINDS:
        assert theme.color_for(kind) == PIECE_COLORS[kind]


def test_color_for_unknown_key_falls_back_to_neutral_grey():
    theme = default_theme()
    fallback = theme.color_for("not-a-kind")
    assert fallback == (140, 140, 150)


def test_color_for_resolves_custom_extended_keys():
    theme = default_theme()
    theme.piece_colors["garbage"] = (90, 90, 90)
    assert theme.color_for("garbage") == (90, 90, 90)


def test_default_themes_do_not_share_piece_color_dicts():
    a = default_theme()
    a.piece_colors["I"] = (0, 0, 0)
    b = default_theme()
    assert b.piece_colors["I"] == PIECE_COLORS["I"]


def test_board_pixel_dimensions_derive_from_cell_size():
    theme = Theme(cell_size=24, board_cols=10, board_rows=20)
    assert theme.board_pixel_width == 240
    assert theme.board_pixel_height == 480


def test_window_size_accounts_for_board_hud_and_margins():
    theme = default_theme()
    width, height = theme.window_size
    assert width == theme.margin * 3 + theme.board_pixel_width + theme.hud_width
    assert height == theme.margin * 2 + theme.board_pixel_height


def test_origins_place_board_at_margin_and_hud_beside_it():
    theme = default_theme()
    assert theme.board_origin == (theme.margin, theme.margin)
    hud_x, hud_y = theme.hud_origin
    assert hud_x == theme.margin * 2 + theme.board_pixel_width
    assert hud_y == theme.margin


def test_geometry_overrides_flow_through_derived_properties():
    theme = Theme(cell_size=10, board_cols=6, board_rows=8, margin=5, hud_width=50)
    assert theme.board_pixel_width == 60
    assert theme.window_size == (5 + 60 + 5 + 50 + 5, 5 + 80 + 5)
    assert theme.hud_origin == (70, 5)
