// Shared headless test harness for snake_game/game.js.
//
// Zero-dependency: follows the same stub-the-globals approach as
// test.headless.js, but packaged as a factory so each test gets a fresh,
// isolated vm context with deterministic time and RNG.
//
// createGame(opts) returns:
//   game, start        - the window.SnakeGame handle exposed by game.js
//   clock              - { now } fake performance.now() source (ms)
//   frame(n)           - run n queued requestAnimationFrame callbacks at clock.now
//   advance(ms, n)     - clock.now += ms, then frame(n); the loop's catch-up
//                        while() runs floor(ms / tick) snake steps in one frame
//   idle(ms)           - advance time WITHOUT snake steps (lastStep is pinned),
//                        for power-up expiry / lifetime tests
//   plant({...})       - put the game into a known playing state (snake, dir,
//                        food), zeroed score/level, RNG-free, no pending spawn
//   pressKey(key)      - dispatch a keydown to the game's window listener
//   rng                - { queue(...vals), set(fn), clear() } controls every
//                        Math.random() the game sees
//   elements, storage, canvasEl, timeouts - the underlying stubs
//
// Assertion helpers expect()/summary() match test.headless.js output style
// (PASS:/FAIL: lines) so a runner can tally across files.

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const source = fs.readFileSync(path.join(__dirname, 'game.js'), 'utf8');

function makeCtx2d() {
  // Canvas 2D context stub: any method is a no-op, any property is writable.
  const handler = {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (prop === 'createRadialGradient' || prop === 'createLinearGradient') {
        return () => ({ addColorStop: () => {} });
      }
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
    className: '',
    classList: {
      _set: new Set(),
      add(c) { this._set.add(c); },
      remove(c) { this._set.delete(c); },
      contains(c) { return this._set.has(c); },
      toggle(c) { this._set.has(c) ? this._set.delete(c) : this._set.add(c); },
    },
    children: [],
    _listeners: {},
    _innerHTML: '',
    addEventListener(ev, fn) {
      (this._listeners[ev] = this._listeners[ev] || []).push(fn);
    },
    removeEventListener() {},
    dispatch(ev, payload) {
      (this._listeners[ev] || []).slice().forEach((fn) => fn(payload));
    },
    appendChild(child) { this.children.push(child); return child; },
    removeChild(child) { this.children = this.children.filter((c) => c !== child); return child; },
    remove() {},
    // innerHTML = '' is how the game clears the power tray, so mirror that.
    set innerHTML(v) { this._innerHTML = String(v); if (v === '') this.children = []; },
    get innerHTML() { return this._innerHTML; },
    querySelector() {
      if (!this._card) this._card = makeElement(`${id}-card`);
      return this._card;
    },
    getContext() { return makeCtx2d(); },
    set textContent(v) { this._text = v; },
    get textContent() { return this._text; },
  };
  return el;
}

function createGame(opts = {}) {
  const clock = { now: 0 };
  const rafQueue = [];
  const timeouts = []; // captured, never auto-fired (sfx chains, flash removal)

  // Deterministic RNG: explicit override > queued values > seeded LCG.
  let seed = (opts.seed == null ? 0x9e3779b9 : opts.seed) >>> 0;
  function lcg() {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 2 ** 32;
  }
  const rngQueue = [];
  let rngOverride = null;
  const rng = {
    queue(...vals) { rngQueue.push(...vals); },
    set(fn) { rngOverride = fn; },
    clear() { rngOverride = null; rngQueue.length = 0; },
  };
  const mathStub = {};
  for (const k of Object.getOwnPropertyNames(Math)) mathStub[k] = Math[k];
  mathStub.random = () => (rngOverride ? rngOverride() : (rngQueue.length ? rngQueue.shift() : lcg()));

  const canvasEl = makeElement('board');
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
    getElementById: (id) => elements[id] || (elements[id] = makeElement(id)),
    createElement: (tag) => makeElement(tag),
    addEventListener() {},
  };

  const storage = {
    _d: Object.assign({}, opts.localStorage || {}),
    getItem(k) { return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
    setItem(k, v) { this._d[k] = String(v); },
  };

  const windowListeners = {};
  const windowStub = {
    addEventListener(ev, fn) {
      (windowListeners[ev] = windowListeners[ev] || []).push(fn);
    },
    AudioContext: function () {
      return {
        state: 'running',
        currentTime: 0,
        createOscillator() {
          return { type: '', frequency: { value: 0 }, connect() { return this; }, start() {}, stop() {} };
        },
        createGain() {
          return { gain: { value: 0, exponentialRampToValueAtTime() {} }, connect() { return this; } };
        },
        destination: {},
        resume() {},
      };
    },
  };

  const sandbox = {
    window: windowStub,
    document,
    performance: { now: () => clock.now },
    requestAnimationFrame: (cb) => { rafQueue.push(cb); return rafQueue.length; },
    localStorage: storage,
    console,
    setTimeout: (fn, ms) => { timeouts.push({ fn, ms }); return timeouts.length; },
    Math: mathStub,
  };
  sandbox.self = sandbox;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: 'game.js' });

  const api = sandbox.window.SnakeGame;
  if (!api) throw new Error('SnakeGame API not exposed by game.js');
  const game = api.game;

  function frame(n = 1) {
    for (let i = 0; i < n; i++) {
      const cb = rafQueue.shift();
      if (cb) cb(clock.now);
    }
  }
  function advance(ms, frames = 1) {
    clock.now += ms;
    frame(frames);
  }
  function idle(ms) {
    clock.now += ms;
    game.lastStep = clock.now; // no catch-up steps: time passes, snake holds still
    frame();
  }
  function pressKey(key, code) {
    const e = {
      key,
      code: code || (key === ' ' ? 'Space' : key),
      defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; },
    };
    (windowListeners.keydown || []).forEach((fn) => fn(e));
    return e;
  }
  // Put the game into a fully known playing state. nextPowerupAt is pushed far
  // out so the random spawner never interferes; tests that exercise spawning
  // set game.nextPowerupAt themselves.
  function plant({ snake, dir = { x: 1, y: 0 }, food = { x: 22, y: 22, bonus: false } } = {}) {
    game.state = 'playing';
    game.snake = snake.map((s) => ({ ...s }));
    game.dir = { ...dir };
    game.queuedDir = { ...dir };
    game.actives = {};
    game.food = food ? { ...food } : null;
    game.powerup = null;
    game.particles = [];
    game.score = 0;
    game.level = 1;
    game.foodEaten = 0;
    game.lastStep = clock.now;
    game.nextPowerupAt = clock.now + 1e12;
  }

  return {
    api, game, start: api.start,
    clock, frame, advance, idle, pressKey, plant, rng,
    elements, storage, canvasEl, windowListeners, timeouts,
  };
}

// ---------- assertion helpers ----------
let passed = 0;
let failed = 0;
function expect(cond, msg) {
  if (cond) {
    passed++;
    console.log('PASS:', msg);
  } else {
    failed++;
    process.exitCode = 1;
    console.error('FAIL:', msg);
  }
}
function summary(suiteName) {
  console.log(`\n${suiteName}: ${passed} passed, ${failed} failed.`);
  if (failed > 0) process.exit(1);
}

module.exports = { createGame, expect, summary };
