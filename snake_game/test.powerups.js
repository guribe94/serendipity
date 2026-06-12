// Power-up coverage: pickup, exact durations, expiry, gameplay effects of all
// five types (bolt, slow, star, shield, shrink), plus board spawn/despawn.
// Run: node snake_game/test.powerups.js

'use strict';

const { createGame, expect, summary } = require('./test.harness');

const DURATIONS = { bolt: 6000, slow: 6000, star: 8000, shield: 6000 };

// --- Pickup mechanics shared by all timed power-ups ---
for (const type of Object.keys(DURATIONS)) {
  const t = createGame();
  const { game, plant, advance, clock } = t;
  plant({ snake: [{ x: 5, y: 12 }, { x: 4, y: 12 }, { x: 3, y: 12 }] });
  game.powerup = { type, x: 6, y: 12, spawnAt: clock.now };
  const lenBefore = game.snake.length;
  advance(130); // one tick: head steps onto the power-up
  expect(game.actives[type] && game.actives[type].expiresAt === clock.now + DURATIONS[type],
    `${type}: pickup activates it for exactly ${DURATIONS[type]}ms (actives=${JSON.stringify(game.actives[type])})`);
  expect(game.powerup === null, `${type}: item removed from the board on pickup`);
  expect(game.nextPowerupAt > clock.now, `${type}: next spawn rescheduled after pickup`);
  expect(game.snake.length === lenBefore, `${type}: picking up a power-up does not grow the snake (len ${game.snake.length})`);
}

// --- bolt: faster ticks while active, normal speed after expiry ---
{
  const t = createGame();
  const { game, plant, advance, idle, clock } = t;

  // Baseline at level 1: 130ms per step -> 5 steps in 650ms
  plant({ snake: [{ x: 2, y: 12 }, { x: 1, y: 12 }, { x: 0, y: 12 }] });
  advance(650);
  expect(game.snake[0].x === 7, `baseline speed: 5 steps in 650ms (head x=${game.snake[0].x})`);

  // bolt: tick = max(45, 130 * 0.55) = 71.5ms -> 9 steps in 650ms
  plant({ snake: [{ x: 2, y: 12 }, { x: 1, y: 12 }, { x: 0, y: 12 }] });
  game.actives.bolt = { expiresAt: clock.now + 6000 };
  advance(650);
  expect(game.snake[0].x === 11, `bolt active: 9 steps in 650ms (head x=${game.snake[0].x})`);

  // expiry: once the 6000ms window passes, speed is back to baseline
  plant({ snake: [{ x: 2, y: 12 }, { x: 1, y: 12 }, { x: 0, y: 12 }] });
  game.actives.bolt = { expiresAt: clock.now + 6000 };
  idle(6001);
  advance(650);
  expect(game.snake[0].x === 7, `bolt expired: back to 5 steps in 650ms (head x=${game.snake[0].x})`);
}

// --- slow: stretched ticks while active, normal speed after expiry ---
{
  const t = createGame();
  const { game, plant, advance, idle, clock } = t;

  // slow: tick = 130 * 1.7 = 221ms -> 2 steps in 650ms
  plant({ snake: [{ x: 2, y: 12 }, { x: 1, y: 12 }, { x: 0, y: 12 }] });
  game.actives.slow = { expiresAt: clock.now + 6000 };
  advance(650);
  expect(game.snake[0].x === 4, `slow active: 2 steps in 650ms (head x=${game.snake[0].x})`);

  plant({ snake: [{ x: 2, y: 12 }, { x: 1, y: 12 }, { x: 0, y: 12 }] });
  game.actives.slow = { expiresAt: clock.now + 6000 };
  idle(6001);
  advance(650);
  expect(game.snake[0].x === 7, `slow expired: back to 5 steps in 650ms (head x=${game.snake[0].x})`);
}

// --- star: 2x score on normal and bonus food, tray pill, back to 1x on expiry ---
{
  const t = createGame();
  const { game, plant, advance, idle, elements, clock } = t;
  plant({ snake: [{ x: 5, y: 12 }, { x: 4, y: 12 }, { x: 3, y: 12 }] });
  game.powerup = { type: 'star', x: 6, y: 12, spawnAt: clock.now };
  advance(130); // pick up star
  game.nextPowerupAt = clock.now + 1e12; // keep the random spawner out of this test

  game.food = { x: 7, y: 12, bonus: false };
  const s0 = game.score;
  advance(130);
  expect(game.score - s0 === 20, `star: normal food scores 20 while 2x is active (got +${game.score - s0})`);

  game.food = { x: 8, y: 12, bonus: true };
  const s1 = game.score;
  advance(130);
  expect(game.score - s1 === 100, `star: bonus food scores 100 while 2x is active (got +${game.score - s1})`);

  expect(elements.powerTray.children.length === 1
      && elements.powerTray.children[0].className === 'power-pill'
      && elements.powerTray.children[0].innerHTML.includes('2x Score'),
    'star: power tray shows one "2x Score" pill while active');

  idle(8001); // past star's 8000ms duration
  game.food = { x: 9, y: 12, bonus: false };
  const s2 = game.score;
  advance(130);
  expect(game.score - s2 === 10, `star expired: normal food back to 10 points (got +${game.score - s2})`);
  expect(elements.powerTray.children.length === 0, 'star expired: power tray pill removed');
}

// --- shield: wall pass-through while active, lethal again after expiry ---
{
  const t = createGame();
  const { game, plant, advance, idle, clock } = t;

  plant({ snake: [{ x: 23, y: 12 }, { x: 22, y: 12 }, { x: 21, y: 12 }] });
  game.actives.shield = { expiresAt: clock.now + 6000 };
  advance(130); // 23 -> 24
  advance(130); // 24 -> wraps to 0
  expect(game.state === 'playing' && game.snake[0].x === 0,
    `shield active: wrapped through the right wall (state=${game.state}, head x=${game.snake[0].x})`);

  plant({ snake: [{ x: 24, y: 12 }, { x: 23, y: 12 }, { x: 22, y: 12 }] });
  game.actives.shield = { expiresAt: clock.now + 6000 };
  idle(6001);
  advance(130);
  expect(game.state === 'gameover', `shield expired: wall hit is lethal again (state=${game.state})`);
}

// --- shrink: instant, cuts length to half the pre-pickup length, minimum 3 ---
{
  const cases = [
    { len: 20, want: 10 },
    { len: 12, want: 6 },
    { len: 7, want: 3 },
    { len: 5, want: 3 },
    { len: 3, want: 3 }, // already at minimum: unchanged
  ];
  for (const { len, want } of cases) {
    const t = createGame();
    const { game, plant, advance, clock } = t;
    const snake = [];
    for (let i = 0; i < len; i++) snake.push({ x: 21 - i, y: 12 }); // head (21,12), body trailing left
    plant({ snake });
    game.powerup = { type: 'shrink', x: 22, y: 12, spawnAt: clock.now };
    advance(130);
    expect(game.snake.length === want, `shrink: length ${len} -> ${want} (got ${game.snake.length})`);
    if (len === 12) {
      expect(game.actives.shrink === undefined, 'shrink: instant effect, no timed active entry');
      expect(game.powerup === null, 'shrink: item removed from the board on pickup');
      expect(game.state === 'playing', 'shrink: game keeps playing after pickup');
    }
  }
}

// --- board spawn and 9000ms lifetime despawn ---
{
  const t = createGame();
  const { game, plant, advance, idle, rng, clock } = t;
  plant({ snake: [{ x: 2, y: 5 }, { x: 1, y: 5 }, { x: 0, y: 5 }] });
  game.nextPowerupAt = clock.now + 100;
  rng.set(() => 0.5); // type index floor(0.5*5)=2 -> 'star'; cell (12,12)
  advance(130);
  expect(game.powerup && game.powerup.type === 'star' && game.powerup.x === 12 && game.powerup.y === 12,
    `power-up spawns once nextPowerupAt passes, RNG-chosen type/cell (got ${JSON.stringify(game.powerup)})`);
  expect(game.powerup.spawnAt === clock.now, 'spawned power-up is stamped with the spawn frame time');

  idle(9001); // past POWERUP_LIFETIME_MS
  expect(game.powerup === null, 'uncollected power-up despawns after its 9000ms lifetime');
  expect(game.nextPowerupAt === clock.now + 4500 + 0.5 * 5000,
    `despawn reschedules the next spawn inside the 4500-9500ms window (got +${game.nextPowerupAt - clock.now}ms)`);
  rng.clear();
}

summary('power-up tests');
