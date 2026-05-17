"""Standalone pygame demo of the preview/placement-aid subsystem.

Run with::

    python -m modern_tetris.preview.demo

Controls:
    Left/Right  - move active piece horizontally
    Down        - soft drop one cell
    Space       - hard drop: lock the ghost cells, spawn next piece
    R           - reset board and queue
    Esc         - quit

The demo deliberately uses a stub board (walls + floor + locked cells only)
to focus on the preview subsystem in isolation; rotation and full game rules
belong to the game-loop subsystem.
"""

from __future__ import annotations


def main() -> int:
    import pygame

    from .rendering import PygameRenderer
    from .system import PreviewSystem

    pygame.init()

    cell = 30
    board_w, board_h = 10, 20
    panel_w = 6 * cell
    screen_w = board_w * cell + panel_w
    screen_h = board_h * cell

    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption("Modern Tetris — Preview Subsystem Demo")
    clock = pygame.time.Clock()

    playfield = screen.subsurface(pygame.Rect(0, 0, board_w * cell, screen_h))
    panel = screen.subsurface(pygame.Rect(board_w * cell, 0, panel_w, screen_h))

    renderer = PygameRenderer(
        playfield_surface=playfield,
        next_panel_surface=panel,
        cell_size=cell,
    )

    locked: set[tuple[int, int]] = set()

    def is_blocked(cells) -> bool:
        for c, r in cells:
            if c < 0 or c >= board_w or r >= board_h:
                return True
            if (c, r) in locked:
                return True
        return False

    preview = PreviewSystem(queue_size=5, board_width=board_w, spawn_row=0)
    preview.spawn_next(is_blocked)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT and preview.active:
                    moved = preview.active.translated(-1, 0)
                    if not is_blocked(moved.cells):
                        preview.update_active(moved, is_blocked)
                elif event.key == pygame.K_RIGHT and preview.active:
                    moved = preview.active.translated(1, 0)
                    if not is_blocked(moved.cells):
                        preview.update_active(moved, is_blocked)
                elif event.key == pygame.K_DOWN and preview.active:
                    moved = preview.active.translated(0, 1)
                    if not is_blocked(moved.cells):
                        preview.update_active(moved, is_blocked)
                elif event.key == pygame.K_SPACE and preview.active and preview.ghost:
                    for c, r in preview.ghost.cells:
                        locked.add((c, r))
                    preview.spawn_next(is_blocked)
                elif event.key == pygame.K_r:
                    locked.clear()
                    preview.reset()
                    preview.spawn_next(is_blocked)

        playfield.fill((10, 10, 18))
        for x in range(board_w + 1):
            pygame.draw.line(playfield, (35, 35, 50), (x * cell, 0), (x * cell, screen_h))
        for y in range(board_h + 1):
            pygame.draw.line(playfield, (35, 35, 50), (0, y * cell), (board_w * cell, y * cell))
        for c, r in locked:
            pygame.draw.rect(playfield, (140, 140, 160), (c * cell, r * cell, cell - 1, cell - 1))
        if preview.ghost:
            renderer.render_ghost(preview.ghost)
        if preview.active:
            for c, r in preview.active.cells:
                pygame.draw.rect(
                    playfield, preview.active.color, (c * cell, r * cell, cell - 1, cell - 1)
                )
                pygame.draw.rect(
                    playfield, (255, 255, 255), (c * cell, r * cell, cell - 1, cell - 1), width=1
                )
        renderer.render_next_queue(preview.upcoming())

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
