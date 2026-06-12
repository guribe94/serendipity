// Scoring, bonus food, level progression, and high-score persistence.
// Run: node snake_game/test.scoring.js

'use strict';

const { createGame, expect, summary } = require('./test.harness');

// --- Normal food: +10, grows by one, HUD updated, replacement food spawns ---
{
  const t = createGame();
  const { game, plant, advance, elements, rng } = t;
  plant({ snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }], food: { x: 6, y: 5, bonus: false } });
  rng.set(() => 0.5); // next spawnFood -> cell (12,12); bonus roll 0.5 >= 0.18 -> normal
  advance(130);
  rng.clear();
  expect(game.score === 10, `normal food scores 10 (got ${game.score})`);
  expect(game.snake.length === 4, `snake grows by one (len ${game.snake.length})`);
  expect(game.foodEaten === 1, `foodEaten incremented (got ${game.foodEaten})`);
  expect(String(elements.score.textContent) === '10', `score HUD shows 10 (got ${elements.score.textContent})`);
  expect(String(elements.length.textContent) === '4', `length HUD shows 4 (got ${elements.length.textContent})`);
  expect(game.food && game.food.x === 12 && game.food.y === 12 && game.food.bonus === false,
    `replacement food spawned at the RNG cell, not bonus (got ${JSON.stringify(game.food)})`);
  expect(game.particles.length === 10, `eating normal food emits 10 particles (got ${game.particles.length})`);
}

// --- Bonus food spawn condition: roll < 0.18 makes the next food a bonus ---
{
  const t = createGame();
  const { game, plant, advance, rng } = t;
  plant({ snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }], food: { x: 6, y: 5, bonus: false } });
  rng.set(() => 0.05); // cell (1,1); 0.05 < 0.18 -> bonus
  advance(130);
  rng.clear();
  expect(game.food && game.food.bonus === true && game.food.x === 1 && game.food.y === 1,
    `bonus food spawns when the roll is under 0.18 (got ${JSON.stringify(game.food)})`);
}

// --- Bonus food: +50, bigger particle burst; food has no despawn timer ---
{
  const t = createGame();
  const { game, plant, advance, idle } = t;
  plant({ snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }], food: { x: 6, y: 5, bonus: true } });
  idle(60000); // a long wait: game.js implements no food timeout, bonus or otherwise
  expect(game.food && game.food.bonus === true && game.food.x === 6 && game.food.y === 5,
    'bonus food persists indefinitely (no despawn timer is implemented)');
  advance(130);
  expect(game.score === 50, `bonus food scores 50 (got ${game.score})`);
  expect(game.particles.length === 18, `bonus food emits 18 particles (got ${game.particles.length})`);
}

// --- Level-up at every 5 foods, announced via HUD and a screen flash ---
{
  const t = createGame();
  const { game, plant, advance, elements, canvasEl } = t;
  plant({ snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }], food: { x: 6, y: 5, bonus: false } });
  game.foodEaten = 4;
  const flashesBefore = canvasEl.parentElement.children.length;
  advance(130); // 5th food
  expect(game.level === 2, `5th food bumps level to 2 (got ${game.level})`);
  expect(String(elements.level.textContent) === '2', `level HUD shows 2 (got ${elements.level.textContent})`);
  expect(canvasEl.parentElement.children.length === flashesBefore + 1,
    'level-up appends a screen-flash element to the stage');
}

// --- Threshold edges: 10th food -> level 3; 4th food -> still level 1 ---
{
  const t = createGame();
  const { game, plant, advance } = t;
  plant({ snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }], food: { x: 6, y: 5, bonus: false } });
  game.foodEaten = 9;
  game.level = 2;
  advance(130);
  expect(game.level === 3, `10th food bumps level to 3 (got ${game.level})`);

  plant({ snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }], food: { x: 6, y: 5, bonus: false } });
  game.foodEaten = 3;
  advance(130);
  expect(game.level === 1, `4th food does not level up (got ${game.level})`);
}

// --- Speed scales with level: -8ms per level, clamped at the 55ms floor ---
{
  const t = createGame();
  const { game, plant, advance } = t;

  plant({ snake: [{ x: 2, y: 12 }, { x: 1, y: 12 }, { x: 0, y: 12 }] });
  game.level = 2; // tick = 130 - 8 = 122ms
  advance(610);
  expect(game.snake[0].x === 7, `level 2: 5 steps in 610ms at 122ms/tick (head x=${game.snake[0].x})`);

  plant({ snake: [{ x: 2, y: 12 }, { x: 1, y: 12 }, { x: 0, y: 12 }] });
  game.level = 10; // tick = 130 - 72 = 58ms
  advance(580);
  expect(game.snake[0].x === 12, `level 10: 10 steps in 580ms at 58ms/tick (head x=${game.snake[0].x})`);

  plant({ snake: [{ x: 2, y: 12 }, { x: 1, y: 12 }, { x: 0, y: 12 }] });
  game.level = 11; // raw 50ms clamps to the 55ms floor
  advance(550);
  expect(game.snake[0].x === 12, `level 11: clamped to 55ms/tick -> 10 steps in 550ms, not 11 (head x=${game.snake[0].x})`);
}

// --- High score: saved on game over, only when beaten, persisted ---
{
  const t = createGame();
  const { game, plant, advance, elements, storage } = t;
  plant({ snake: [{ x: 24, y: 12 }, { x: 23, y: 12 }, { x: 22, y: 12 }] });
  game.score = 30;
  advance(130); // wall -> game over
  expect(game.state === 'gameover' && game.high === 30, `game over saves a new high score (high=${game.high})`);
  expect(storage._d.snake_high === '30', `high score persisted to localStorage (got ${storage._d.snake_high})`);
  expect(String(elements.highScore.textContent) === '30', `high score HUD updated (got ${elements.highScore.textContent})`);

  plant({ snake: [{ x: 24, y: 12 }, { x: 23, y: 12 }, { x: 22, y: 12 }] });
  game.score = 10;
  advance(130);
  expect(game.high === 30 && storage._d.snake_high === '30', 'a worse run does not lower the saved high score');
}

// --- Boot: high score loads from localStorage ---
{
  const t = createGame({ localStorage: { snake_high: '120' } });
  expect(t.game.high === 120, `boot loads the stored high score (got ${t.game.high})`);
  expect(String(t.elements.highScore.textContent) === '120',
    `boot shows the stored high score in the HUD (got ${t.elements.highScore.textContent})`);
}
{
  const t = createGame({ localStorage: { snake_high: 'garbage' } });
  expect(t.game.high === 0, `non-numeric stored high score falls back to 0 (got ${t.game.high})`);
}

summary('scoring & level tests');
