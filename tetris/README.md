# Tetris

A full modern Tetris built from three subsystems in this repo:

| Module                     | Concern                                              |
|----------------------------|------------------------------------------------------|
| `tetris.game`              | Board, gravity, lock delay, 7-bag, hold, scoring     |
| `tetris.renderer` + `hud`  | Playfield, ghost piece, NEXT/HOLD panel, overlays    |
| `modern_tetris.input`      | DAS/ARR keyboard controller, hold/pause, rebindable  |

`tetris.main` wires them together into a playable game.

## Play

```bash
pip install -r tetris/requirements.txt
python -m tetris.main                   # opens a pygame window
python -m tetris.main --seed 42         # deterministic 7-bag for testing
```

Default controls: arrow keys move / soft drop, `Space` hard drops, `Up`
or `X` rotate clockwise, `Z` rotates counter-clockwise, `C` or `Shift`
holds, `P` or `Esc` pauses, `Enter` starts a new round after game over.

## Rendering subsystem (standalone)

Pure-rendering module. Other modules (game loop, piece preview, input)
produce a `RenderState` snapshot each frame; this package draws it.

## What it draws

- 10×20 playfield with grid + border
- Locked blocks (per-cell color keys, beveled)
- Active tetromino
- Ghost piece (translucent projection of landing spot)
- Right-side HUD: SCORE / LEVEL / LINES, optional HOLD slot, NEXT queue (up to 5)
- Overlays for START, PAUSED, and GAME OVER
- In-play floating message banner (e.g. `TETRIS!`)

## Public API

```python
from tetris import Renderer, RenderState, GamePhase, Scoreboard, ActivePiece

renderer = Renderer()              # uses default theme
surface = renderer.create_surface()  # or supply your own pygame.Surface
renderer.draw(surface, state)
```

`RenderState` (see `tetris/state.py`) is the contract with the rest of
the game:

| field           | type                                     | notes                                       |
|-----------------|------------------------------------------|---------------------------------------------|
| `board`         | `list[list[str \| None]]`                | `[row][col]`, color keys; `None` = empty    |
| `active_piece`  | `ActivePiece \| None`                    | falling piece, cells in board coordinates   |
| `ghost_piece`   | `ActivePiece \| None`                    | landing projection                          |
| `next_pieces`   | `list[ActivePiece]`                      | shown in NEXT queue                         |
| `held_piece`    | `ActivePiece \| None`                    | shown in HOLD slot if present               |
| `scoreboard`    | `Scoreboard`                             | `score`, `level`, `lines`                   |
| `phase`         | `GamePhase`                              | START / PLAYING / PAUSED / GAME_OVER        |
| `last_clear_rows` | `Sequence[int]`                        | rows to flash this frame                    |
| `message`       | `str \| None`                            | optional in-play banner                     |

## Running

```bash
pip install -r tetris/requirements.txt
# Headless verification (writes PNGs to /tmp/tetris_snapshots):
SDL_VIDEODRIVER=dummy python3 -m tetris.demo
# Tests:
SDL_VIDEODRIVER=dummy python3 -m pytest tetris/tests modern_tetris/tests
```
