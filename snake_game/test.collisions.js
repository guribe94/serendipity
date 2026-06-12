// Collision coverage: self-collision, tail-chase exemption, all four walls,
// and how the shield changes each outcome.
// Run: node snake_game/test.collisions.js

'use strict';

const { createGame, expect, summary } = require('./test.harness');

// U-shaped body: the cell to the right of the head is the snake's own body
// (index 5 of 7, not the tail).
const U_SHAPE = [
  { x: 5, y: 5 }, { x: 4, y: 5 }, { x: 4, y: 6 }, { x: 5, y: 6 },
  { x: 6, y: 6 }, { x: 6, y: 5 }, { x: 7, y: 5 },
];

// --- Self-collision ends the game ---
{
  const t = createGame();
  t.plant({ snake: U_SHAPE });
  t.advance(130);
  expect(t.game.state === 'gameover', `self-collision: running into own body is game over (state=${t.game.state})`);
}

// --- Shield lets the head pass through its own body ---
{
  const t = createGame();
  t.plant({ snake: U_SHAPE });
  t.game.actives.shield = { expiresAt: t.clock.now + 60000 };
  t.advance(130);
  expect(t.game.state === 'playing', `shield: passing through own body keeps playing (state=${t.game.state})`);
  expect(t.game.snake[0].x === 6 && t.game.snake[0].y === 5,
    `shield: head moved into the body cell (head=${JSON.stringify(t.game.snake[0])})`);
}

// --- Moving into the tail cell is safe: the tail vacates it the same tick ---
{
  const t = createGame();
  // 2x2 loop, head (5,5) moving right, tail at (6,5)
  t.plant({ snake: [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 6, y: 6 }, { x: 6, y: 5 }] });
  t.advance(130);
  expect(t.game.state === 'playing', `tail-chase: stepping into the vacating tail cell is safe (state=${t.game.state})`);
  expect(t.game.snake[0].x === 6 && t.game.snake[0].y === 5, 'tail-chase: head now occupies the old tail cell');
  expect(t.game.snake.length === 4, `tail-chase: length unchanged (len ${t.game.snake.length})`);
}

// --- ...but eating that tick keeps the tail in place, so it is a collision ---
{
  const t = createGame();
  t.plant({
    snake: [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 6, y: 6 }, { x: 6, y: 5 }],
    food: { x: 6, y: 5, bonus: false },
  });
  t.advance(130);
  expect(t.game.state === 'gameover', `tail cell holding food: tail stays put, game over (state=${t.game.state})`);
}

// --- Walls are lethal on all four sides without a shield ---
const WALLS = [
  { name: 'left', snake: [{ x: 0, y: 12 }, { x: 1, y: 12 }, { x: 2, y: 12 }], dir: { x: -1, y: 0 }, wrapped: { x: 24, y: 12 } },
  { name: 'top', snake: [{ x: 12, y: 0 }, { x: 12, y: 1 }, { x: 12, y: 2 }], dir: { x: 0, y: -1 }, wrapped: { x: 12, y: 24 } },
  { name: 'bottom', snake: [{ x: 12, y: 24 }, { x: 12, y: 23 }, { x: 12, y: 22 }], dir: { x: 0, y: 1 }, wrapped: { x: 12, y: 0 } },
  { name: 'right', snake: [{ x: 24, y: 12 }, { x: 23, y: 12 }, { x: 22, y: 12 }], dir: { x: 1, y: 0 }, wrapped: { x: 0, y: 12 } },
];

for (const w of WALLS) {
  const t = createGame();
  t.plant({ snake: w.snake, dir: w.dir });
  t.advance(130);
  expect(t.game.state === 'gameover', `${w.name} wall without shield: game over (state=${t.game.state})`);
}

// --- With a shield, every wall wraps to the opposite side ---
for (const w of WALLS) {
  const t = createGame();
  t.plant({ snake: w.snake, dir: w.dir });
  t.game.actives.shield = { expiresAt: t.clock.now + 60000 };
  t.advance(130);
  expect(t.game.state === 'playing' && t.game.snake[0].x === w.wrapped.x && t.game.snake[0].y === w.wrapped.y,
    `${w.name} wall with shield: wraps to (${w.wrapped.x},${w.wrapped.y}) (state=${t.game.state}, head=${JSON.stringify(t.game.snake[0])})`);
}

summary('collision tests');
