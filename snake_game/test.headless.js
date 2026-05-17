// Minimal headless smoke test for snake_game/game.js.
// Stubs out DOM/canvas/timer APIs and exercises the IIFE to verify the
// game boots, starts, ticks, eats food, and handles a wall collision.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const sourcePath = path.join(__dirname, 'game.js');
const source = fs.readFileSync(sourcePath, 'utf8');

let now = 0;
const rafQueue = [];
function tickRaf() {
  const cb = rafQueue.shift();
  if (cb) cb(now);
}

function makeChainable() {
  // ctx stub: any method/property returns chainable or no-op
  const handler = {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (prop === 'createRadialGradient' || prop === 'createLinearGradient') {
        return () => ({ addColorStop: () => {} });
      }
      // method stub
      return () => {};
    },
    set(target, prop, val) { target[prop] = val; return true; },
  };
  return new Proxy({}, handler);
}

function makeElement(id) {
  const el = {
    id,
    width: 0,
    height: 0,
    style: {},
    classList: {
      _set: new Set(),
      add(c) { this._set.add(c); },
      remove(c) { this._set.delete(c); },
      contains(c) { return this._set.has(c); },
      toggle(c) { this._set.has(c) ? this._set.delete(c) : this._set.add(c); },
    },
    children: [],
    _listeners: {},
    addEventListener(ev, fn) {
      (this._listeners[ev] = this._listeners[ev] || []).push(fn);
    },
    removeEventListener() {},
    dispatch(ev, payload) {
      (this._listeners[ev] || []).forEach((fn) => fn(payload));
    },
    appendChild(child) { this.children.push(child); return child; },
    removeChild(child) { this.children = this.children.filter((c) => c !== child); return child; },
    remove() {},
    set innerHTML(_v) {},
    get innerHTML() { return ''; },
    querySelector() { return makeElement('q'); },
    getContext() { return makeChainable(); },
    set textContent(v) { this._text = v; },
    get textContent() { return this._text; },
  };
  return el;
}

const canvasEl = makeElement('board');
canvasEl.getContext = () => makeChainable();
canvasEl.parentElement = makeElement('stage');

const elements = {
  board: canvasEl,
  score: makeElement('score'),
  highScore: makeElement('highScore'),
  level: makeElement('level'),
  length: makeElement('length'),
  overlay: makeElement('overlay'),
  startBtn: makeElement('startBtn'),
  powerTray: makeElement('powerTray'),
};

const document = {
  getElementById: (id) => elements[id] || makeElement(id),
  createElement: (tag) => makeElement(tag),
  addEventListener() {},
};

const storage = {
  _d: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
  setItem(k, v) { this._d[k] = String(v); },
};

const windowStub = {
  addEventListener() {},
  AudioContext: function () {
    return {
      state: 'running',
      currentTime: 0,
      createOscillator() { return { type: '', frequency: { value: 0 }, connect() { return this; }, start() {}, stop() {} }; },
      createGain() { return { gain: { value: 0, exponentialRampToValueAtTime() {} }, connect() { return this; } }; },
      destination: {},
      resume() {},
    };
  },
};

const ctxObj = {
  window: windowStub,
  document,
  performance: { now: () => now },
  requestAnimationFrame: (cb) => { rafQueue.push(cb); return rafQueue.length; },
  localStorage: storage,
  console,
  setTimeout: (fn, t) => setTimeout(fn, t),
  Math, Date, Object, Array, JSON, String, Number, Boolean, parseInt, parseFloat, isNaN, isFinite,
};
ctxObj.self = ctxObj;
ctxObj.globalThis = ctxObj;

// Make window.* lookups also work via the global proxy: copy fields from windowStub
for (const k of Object.keys(windowStub)) ctxObj[k] = windowStub[k];

vm.createContext(ctxObj);
vm.runInContext(source, ctxObj, { filename: 'game.js' });

const api = ctxObj.SnakeGame || ctxObj.window?.SnakeGame;
if (!api) throw new Error('SnakeGame API not exposed');

const { game, start } = api;

function expect(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg);
    process.exit(1);
  }
  console.log('PASS:', msg);
}

// Boot checks
expect(typeof start === 'function', 'startGame exposed');
expect(game.state === 'idle', 'starts idle');

// Start the game and run a few raf frames to settle
start();
expect(game.state === 'playing', 'state becomes playing after start');
expect(game.snake.length === 3, 'snake starts at length 3');
expect(game.food !== null, 'food is spawned');

// Advance simulated time and let the loop step
const initialScore = game.score;
const headBefore = { ...game.snake[0] };

// Force food directly in front of the snake head, then advance one tick.
// Snake moves right (1,0), so place food one cell to the right of head.
game.food = { x: headBefore.x + 1, y: headBefore.y, bonus: false };

// Advance time by enough ms to trigger one tick and let raf fire
now += 5000;
// run several raf callbacks to drive the loop
for (let i = 0; i < 5; i++) {
  tickRaf();
}

expect(game.score > initialScore, `score increased after eating food (was ${initialScore}, now ${game.score})`);
expect(game.snake.length >= 4, `snake grew after eating (length ${game.snake.length})`);
expect(game.snake[0].x > headBefore.x, `head advanced past starting x (was ${headBefore.x}, now ${game.snake[0].x})`);

// Reset to a fresh playing state for power-up tests
function resetToPlaying(snakeCells, dir = { x: 1, y: 0 }) {
  game.state = 'playing';
  game.snake = snakeCells.slice();
  game.dir = { ...dir };
  game.queuedDir = { ...dir };
  game.actives = {};
  game.food = { x: 20, y: 20, bonus: false };
  game.powerup = null;
  game.lastStep = now;
}

resetToPlaying([{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }]);
const before = now;
game.powerup = { type: 'star', x: 6, y: 5, spawnAt: now };
now += 200; // single-tick advance
for (let i = 0; i < 5; i++) tickRaf();
expect(game.actives.star && game.actives.star.expiresAt > before, `star power-up activated on pickup (actives=${JSON.stringify(game.actives)})`);

// Test shrink: snake should be shortened in half on pickup
resetToPlaying([
  { x: 5, y: 8 }, { x: 4, y: 8 }, { x: 3, y: 8 }, { x: 2, y: 8 },
  { x: 1, y: 8 }, { x: 0, y: 8 }, { x: 0, y: 9 }, { x: 0, y: 10 },
  { x: 1, y: 10 }, { x: 2, y: 10 }, { x: 3, y: 10 }, { x: 4, y: 10 },
]);
const lenBefore = game.snake.length;
game.powerup = { type: 'shrink', x: 6, y: 8, spawnAt: now };
now += 200;
for (let i = 0; i < 5; i++) tickRaf();
expect(game.snake.length < lenBefore, `shrink reduced snake length (was ${lenBefore}, now ${game.snake.length})`);

// Test wall collision: move snake to a wall and step into it
resetToPlaying([{ x: 24, y: 0 }, { x: 23, y: 0 }]);
now += 200;
for (let i = 0; i < 5; i++) tickRaf();
expect(game.state === 'gameover', `game over on wall collision (state=${game.state})`);

// Test invincibility: same setup but with shield active wraps instead
resetToPlaying([{ x: 24, y: 0 }, { x: 23, y: 0 }]);
game.actives = { shield: { expiresAt: now + 10000 } };
now += 200;
for (let i = 0; i < 5; i++) tickRaf();
expect(game.state === 'playing', `shielded: still playing after wall hit (state=${game.state})`);
expect(game.snake[0].x === 0, `shielded: wrapped to x=0 (got ${game.snake[0].x})`);

console.log('\nAll smoke tests passed.');
