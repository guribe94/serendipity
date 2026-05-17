import os

import pytest

from modern_tetris.preview.pieces import PieceKind, Tetromino
from modern_tetris.preview.rendering import NullRenderer


def test_null_renderer_records_ghost_calls():
    r = NullRenderer()
    piece = Tetromino.spawn(PieceKind.T)
    r.render_ghost(piece)
    r.render_ghost(piece)
    assert len(r.ghost_calls) == 2
    assert r.ghost_calls[0] is piece


def test_null_renderer_records_queue_calls():
    r = NullRenderer()
    r.render_next_queue([PieceKind.I, PieceKind.O])
    r.render_next_queue([])
    assert r.queue_calls == [[PieceKind.I, PieceKind.O], []]


def test_null_renderer_materializes_queue_iterables():
    """Pass a generator — NullRenderer must materialize it for inspection."""
    r = NullRenderer()
    r.render_next_queue(k for k in (PieceKind.I, PieceKind.O, PieceKind.T))
    assert r.queue_calls == [[PieceKind.I, PieceKind.O, PieceKind.T]]


@pytest.fixture(scope="module")
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame

    pygame.init()
    yield pygame
    pygame.quit()


def test_pygame_renderer_runs_without_error(pygame_headless):
    pygame = pygame_headless
    from modern_tetris.preview.rendering import PygameRenderer

    playfield = pygame.Surface((300, 600))
    panel = pygame.Surface((150, 600))
    r = PygameRenderer(playfield_surface=playfield, next_panel_surface=panel, cell_size=30)
    ghost = Tetromino.spawn(PieceKind.T).translated(0, 18)
    r.render_ghost(ghost)
    r.render_next_queue([PieceKind.I, PieceKind.O, PieceKind.T])


def test_pygame_renderer_handles_no_ghost(pygame_headless):
    pygame = pygame_headless
    from modern_tetris.preview.rendering import PygameRenderer

    playfield = pygame.Surface((300, 600))
    panel = pygame.Surface((150, 600))
    r = PygameRenderer(playfield_surface=playfield, next_panel_surface=panel, cell_size=30)
    r.render_ghost(None)  # No active piece -> no-op


def test_pygame_renderer_clears_panel_each_call(pygame_headless):
    pygame = pygame_headless
    from modern_tetris.preview.rendering import PygameRenderer

    playfield = pygame.Surface((300, 600))
    panel = pygame.Surface((150, 600))
    panel.fill((255, 0, 255))  # Magenta sentinel — should be overwritten by bg.
    r = PygameRenderer(
        playfield_surface=playfield,
        next_panel_surface=panel,
        cell_size=30,
        panel_bg=(10, 20, 30),
    )
    r.render_next_queue([])  # Empty queue, but the bg must still be applied.
    assert panel.get_at((0, 0))[:3] == (10, 20, 30)


def test_pygame_renderer_draws_to_panel(pygame_headless):
    pygame = pygame_headless
    from modern_tetris.preview.rendering import PygameRenderer

    playfield = pygame.Surface((300, 600))
    panel = pygame.Surface((150, 600))
    panel.fill((0, 0, 0))
    r = PygameRenderer(playfield_surface=playfield, next_panel_surface=panel, cell_size=30)
    r.render_next_queue([PieceKind.I, PieceKind.O, PieceKind.T, PieceKind.S, PieceKind.Z])
    found_color = False
    for y in range(0, 600, 5):
        for x in range(0, 150, 5):
            r_, g_, b_ = panel.get_at((x, y))[:3]
            if (r_, g_, b_) not in {(0, 0, 0), PygameRenderer.DEFAULT_PANEL_BG}:
                found_color = True
                break
        if found_color:
            break
    assert found_color, "expected mini-pieces to leave colored pixels on the panel"


def test_pygame_renderer_draws_ghost_to_playfield(pygame_headless):
    pygame = pygame_headless
    from modern_tetris.preview.rendering import PygameRenderer

    playfield = pygame.Surface((300, 600))
    panel = pygame.Surface((150, 600))
    playfield.fill((0, 0, 0))
    r = PygameRenderer(
        playfield_surface=playfield,
        next_panel_surface=panel,
        cell_size=30,
        ghost_alpha=200,
    )
    # O piece spawns at cells (4,0),(5,0),(4,1),(5,1). Drop to rows 18,19.
    ghost = Tetromino.spawn(PieceKind.O).translated(0, 18)
    r.render_ghost(ghost)
    # Sample a pixel inside cell (4,18) which is pixel rect 120,540 -> 150,570.
    sampled = playfield.get_at((130, 550))
    assert sampled[:3] != (0, 0, 0), f"ghost pixel should be non-black, got {sampled}"


def test_pygame_renderer_origin_offsets_ghost(pygame_headless):
    pygame = pygame_headless
    from modern_tetris.preview.rendering import PygameRenderer

    playfield = pygame.Surface((400, 700))
    panel = pygame.Surface((150, 600))
    playfield.fill((0, 0, 0))
    r = PygameRenderer(
        playfield_surface=playfield,
        next_panel_surface=panel,
        cell_size=30,
        playfield_origin=(20, 50),
        ghost_alpha=220,
    )
    ghost = Tetromino.spawn(PieceKind.O).translated(0, 18)
    r.render_ghost(ghost)
    # Origin shifts pixel by (20, 50). Cell (4, 18) → pixel (20 + 120, 50 + 540) = (140, 590).
    sampled = playfield.get_at((150, 600))
    assert sampled[:3] != (0, 0, 0)


def test_pygame_renderer_handles_empty_queue(pygame_headless):
    pygame = pygame_headless
    from modern_tetris.preview.rendering import PygameRenderer

    playfield = pygame.Surface((300, 600))
    panel = pygame.Surface((150, 600))
    r = PygameRenderer(playfield_surface=playfield, next_panel_surface=panel, cell_size=30)
    r.render_next_queue([])  # Should not raise.


def test_pygame_renderer_consumes_generator_queue(pygame_headless):
    pygame = pygame_headless
    from modern_tetris.preview.rendering import PygameRenderer

    playfield = pygame.Surface((300, 600))
    panel = pygame.Surface((150, 600))
    r = PygameRenderer(playfield_surface=playfield, next_panel_surface=panel, cell_size=30)
    gen = (k for k in (PieceKind.I, PieceKind.T))
    r.render_next_queue(gen)  # Should iterate the generator without issue.
