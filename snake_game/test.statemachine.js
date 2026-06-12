// State machine and input: pause/resume, restart, game-over overlay, keyboard
// direction handling (arrows + WASD, 180° reversal block), and touch swipes.
// Run: node snake_game/test.statemachine.js

'use strict';

const { createGame, expect, summary } = require('./test.harness');

// --- Pause / resume via Space ---
{
  const t = createGame();
  const { game, plant, advance, pressKey, clock } = t;
  plant({ snake: [{ x: 5, y: 12 }, { x: 4, y: 12 }, { x: 3, y: 12 }] });
  const e = pressKey(' ');
  expect(game.state === 'paused', `Space while playing pauses (state=${game.state})`);
  expect(e.defaultPrevented === true, 'Space keydown is preventDefault-ed');

  const headX = game.snake[0].x;
  advance(2000, 3);
  expect(game.snake[0].x === headX, `paused: snake does not move while time passes (head x=${game.snake[0].x})`);

  pressKey(' ');
  expect(game.state === 'playing', `Space while paused resumes (state=${game.state})`);
  expect(game.lastStep === clock.now, 'resume resets the step clock to now');
  advance(130);
  expect(game.snake[0].x === headX + 1,
    `after resume: exactly one step per tick, no catch-up burst (moved ${game.snake[0].x - headX} cells)`);
}

// --- Space is inert when idle and when game over ---
{
  const t = createGame();
  t.pressKey(' ');
  expect(t.game.state === 'idle', `Space at idle does nothing (state=${t.game.state})`);
  t.plant({ snake: [{ x: 24, y: 12 }, { x: 23, y: 12 }] });
  t.advance(130); // wall -> game over
  t.pressKey(' ');
  expect(t.game.state === 'gameover', `Space at game over does nothing (state=${t.game.state})`);
}

// --- R restarts from playing, but not from idle ---
{
  const t = createGame();
  expect(t.game.state === 'idle' && t.game.snake.length === 0, 'boot: idle with no snake');
  t.pressKey('r');
  expect(t.game.state === 'idle', `R at idle does not start a game (state=${t.game.state})`);

  t.start();
  expect(t.game.state === 'playing', 'start() enters playing');
  const g = t.game;
  g.score = 77;
  g.level = 4;
  g.foodEaten = 17;
  g.actives.star = { expiresAt: t.clock.now + 8000 };
  t.advance(130);
  t.pressKey('r');
  expect(g.state === 'playing' && g.score === 0 && g.level === 1 && g.foodEaten === 0,
    `R mid-game restarts with reset stats (score=${g.score}, level=${g.level}, foodEaten=${g.foodEaten})`);
  expect(g.snake.length === 3 && g.snake[0].x === 11 && g.snake[0].y === 12,
    `restart: snake back to 3 segments at center (head=${JSON.stringify(g.snake[0])})`);
  expect(Object.keys(g.actives).length === 0, 'restart: active power-ups cleared');
  expect(g.powerup === null, 'restart: board power-up cleared');
  expect(g.food !== null, 'restart: food spawned');
}

// --- Game over: overlay shown, uppercase R restarts and hides it ---
{
  const t = createGame();
  t.plant({ snake: [{ x: 24, y: 12 }, { x: 23, y: 12 }] });
  t.game.score = 40;
  t.advance(130);
  expect(t.game.state === 'gameover', `setup: wall hit reaches game over (state=${t.game.state})`);
  expect(t.elements.overlay.classList.contains('show'), 'game over shows the overlay');
  const card = t.elements.overlay.querySelector('.overlay-card');
  expect(card.innerHTML.includes('GAME OVER') && card.innerHTML.includes('Score 40'),
    'overlay card announces GAME OVER with the final score');
  t.pressKey('R');
  expect(t.game.state === 'playing', `uppercase R restarts from game over (state=${t.game.state})`);
  expect(t.elements.overlay.classList.contains('show') === false, 'restart hides the overlay');
}

// --- Start button click starts a fresh game ---
{
  const t = createGame();
  t.elements.startBtn.dispatch('click');
  expect(t.game.state === 'playing', `start button click starts the game (state=${t.game.state})`);
  expect(t.game.snake.length === 3 && t.game.score === 0, 'start button: fresh 3-segment snake, score 0');
}

// --- Keyboard direction handling ---
{
  const t = createGame();
  const { game, plant, advance, pressKey } = t;
  plant({ snake: [{ x: 5, y: 12 }, { x: 4, y: 12 }, { x: 3, y: 12 }] }); // moving right
  const e = pressKey('ArrowUp');
  expect(game.queuedDir.x === 0 && game.queuedDir.y === -1, 'ArrowUp queues an upward turn');
  expect(e.defaultPrevented === true, 'direction keydown is preventDefault-ed');
  pressKey('ArrowLeft'); // 180° reversal of the current direction (right)
  expect(game.queuedDir.x === 0 && game.queuedDir.y === -1,
    'reversal (ArrowLeft while moving right) is ignored; queued turn kept');
  advance(130);
  expect(game.dir.y === -1 && game.snake[0].y === 11,
    `queued turn is applied on the next tick (dir=${JSON.stringify(game.dir)}, head y=${game.snake[0].y})`);

  // WASD aliases, lower and upper case
  plant({ snake: [{ x: 5, y: 12 }, { x: 4, y: 12 }, { x: 3, y: 12 }] }); // moving right
  pressKey('s');
  expect(game.queuedDir.x === 0 && game.queuedDir.y === 1, '"s" queues a downward turn');
  pressKey('W');
  expect(game.queuedDir.x === 0 && game.queuedDir.y === -1, '"W" (shifted) queues an upward turn');
  pressKey('a');
  expect(game.queuedDir.x === 0 && game.queuedDir.y === -1,
    '"a" while still moving right is a reversal and is ignored');

  plant({ snake: [{ x: 5, y: 5 }, { x: 5, y: 6 }, { x: 5, y: 7 }], dir: { x: 0, y: -1 } }); // moving up
  pressKey('d');
  expect(game.queuedDir.x === 1 && game.queuedDir.y === 0, '"d" queues a rightward turn');
}

// --- Touch swipes ---
{
  const t = createGame();
  const { game, plant, canvasEl } = t;
  plant({ snake: [{ x: 5, y: 12 }, { x: 4, y: 12 }, { x: 3, y: 12 }] }); // moving right

  canvasEl.dispatch('touchstart', { touches: [{ clientX: 100, clientY: 100 }] });
  canvasEl.dispatch('touchend', { changedTouches: [{ clientX: 108, clientY: 190 }] });
  expect(game.queuedDir.x === 0 && game.queuedDir.y === 1, 'downward swipe queues a downward turn');

  canvasEl.dispatch('touchstart', { touches: [{ clientX: 100, clientY: 100 }] });
  canvasEl.dispatch('touchend', { changedTouches: [{ clientX: 110, clientY: 92 }] });
  expect(game.queuedDir.x === 0 && game.queuedDir.y === 1, 'sub-threshold swipe (<20px) is ignored');

  canvasEl.dispatch('touchstart', { touches: [{ clientX: 200, clientY: 100 }] });
  canvasEl.dispatch('touchend', { changedTouches: [{ clientX: 100, clientY: 100 }] });
  expect(game.queuedDir.x === 0 && game.queuedDir.y === 1,
    'reversal swipe (left while moving right) is ignored');
}

summary('state machine & input tests');
