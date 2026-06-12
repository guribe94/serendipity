(() => {
  'use strict';

  // ---------- Configuration ----------
  const CELL = 24;
  const COLS = 25;
  const ROWS = 25;
  const BASE_TICK_MS = 130;          // milliseconds per snake step at level 1
  const LEVEL_SPEEDUP_MS = 8;        // ms shaved per level
  const MIN_TICK_MS = 55;            // floor on speed
  const LEVEL_THRESHOLD = 5;         // foods per level
  const FOOD_SCORE = 10;
  const BONUS_FOOD_SCORE = 50;
  const POWERUP_LIFETIME_MS = 9000;  // power-up disappears if not collected
  const POWERUP_SPAWN_MIN_MS = 4500;
  const POWERUP_SPAWN_MAX_MS = 9500;
  const BONUS_FOOD_CHANCE = 0.18;    // chance a food spawns as bonus

  // Power-up types
  const POWERUPS = {
    bolt:    { label: 'Speed',    icon: '⚡', cls: 'chip-bolt',   color: '#ffd86b', duration: 6000 },
    slow:    { label: 'Slow Mo',  icon: '⌛', cls: 'chip-slow',   color: '#66a6ff', duration: 6000 },
    star:    { label: '2x Score', icon: '★', cls: 'chip-star',   color: '#b186ff', duration: 8000 },
    shield:  { label: 'Shield',   icon: '🛡', cls: 'chip-shield', color: '#6cf0c2', duration: 6000 },
    shrink:  { label: 'Shrink',   icon: '✂', cls: 'chip-shrink', color: '#ff8fb1', duration: 0 },
  };
  const POWERUP_KEYS = Object.keys(POWERUPS);

  // ---------- DOM ----------
  const canvas = document.getElementById('board');
  const ctx = canvas.getContext('2d');
  const scoreEl = document.getElementById('score');
  const highEl = document.getElementById('highScore');
  const levelEl = document.getElementById('level');
  const lengthEl = document.getElementById('length');
  const overlay = document.getElementById('overlay');
  const startBtn = document.getElementById('startBtn');
  const powerTray = document.getElementById('powerTray');

  // Match canvas pixel size to CSS so it scales crisply
  function resizeCanvas() {
    const pixelSize = COLS * CELL;
    canvas.width = pixelSize;
    canvas.height = pixelSize;
  }
  resizeCanvas();

  // ---------- Audio (Web Audio API — no external assets) ----------
  let audioCtx = null;
  function audio() {
    if (!audioCtx) {
      try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
      catch (e) { audioCtx = null; }
    }
    return audioCtx;
  }
  function beep(freq = 440, duration = 0.08, type = 'square', gain = 0.05) {
    const ac = audio();
    if (!ac) return;
    const osc = ac.createOscillator();
    const g = ac.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.value = gain;
    g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + duration);
    osc.connect(g).connect(ac.destination);
    osc.start();
    osc.stop(ac.currentTime + duration);
  }
  function sfxEat()      { beep(660, 0.08, 'square', 0.06); }
  function sfxBonus()    { beep(880, 0.05, 'triangle', 0.06); setTimeout(() => beep(1320, 0.08, 'triangle', 0.06), 60); }
  function sfxPowerup()  { beep(520, 0.05, 'sine', 0.06); setTimeout(() => beep(780, 0.08, 'sine', 0.06), 50); setTimeout(() => beep(1040, 0.12, 'sine', 0.06), 110); }
  function sfxDeath()    { beep(220, 0.18, 'sawtooth', 0.08); setTimeout(() => beep(160, 0.22, 'sawtooth', 0.08), 120); setTimeout(() => beep(110, 0.28, 'sawtooth', 0.08), 280); }
  function sfxLevelUp()  { beep(660, 0.08, 'triangle', 0.06); setTimeout(() => beep(880, 0.08, 'triangle', 0.06), 80); setTimeout(() => beep(1175, 0.12, 'triangle', 0.06), 160); }

  // ---------- State ----------
  const STATE = {
    IDLE: 'idle',
    PLAYING: 'playing',
    PAUSED: 'paused',
    GAMEOVER: 'gameover',
  };

  const game = {
    state: STATE.IDLE,
    snake: [],
    dir: { x: 1, y: 0 },
    queuedDir: { x: 1, y: 0 },
    food: null,           // { x, y, bonus: boolean }
    powerup: null,        // { type, x, y, spawnAt }
    score: 0,
    high: 0,
    level: 1,
    foodEaten: 0,
    lastStep: 0,
    nextPowerupAt: 0,
    actives: {},          // type -> { expiresAt }
    deathFlashAt: 0,
    particles: [],
  };

  function loadHigh() {
    try {
      const v = parseInt(localStorage.getItem('snake_high') || '0', 10);
      if (Number.isFinite(v)) game.high = v;
    } catch (e) { /* localStorage unavailable */ }
    highEl.textContent = game.high;
  }
  function saveHigh() {
    if (game.score > game.high) {
      game.high = game.score;
      highEl.textContent = game.high;
      try { localStorage.setItem('snake_high', String(game.high)); } catch (e) {}
    }
  }

  // ---------- Helpers ----------
  function randomCell() {
    return { x: Math.floor(Math.random() * COLS), y: Math.floor(Math.random() * ROWS) };
  }
  function occupied(x, y) {
    if (game.food && game.food.x === x && game.food.y === y) return true;
    if (game.powerup && game.powerup.x === x && game.powerup.y === y) return true;
    for (const s of game.snake) if (s.x === x && s.y === y) return true;
    return false;
  }
  function emptyCell() {
    let attempts = 0;
    let c;
    do {
      c = randomCell();
      attempts++;
    } while (occupied(c.x, c.y) && attempts < 800);
    return c;
  }
  function spawnFood() {
    const c = emptyCell();
    const bonus = Math.random() < BONUS_FOOD_CHANCE;
    game.food = { x: c.x, y: c.y, bonus };
  }
  function scheduleNextPowerup(now) {
    const range = POWERUP_SPAWN_MAX_MS - POWERUP_SPAWN_MIN_MS;
    game.nextPowerupAt = now + POWERUP_SPAWN_MIN_MS + Math.random() * range;
  }
  function spawnPowerup(now) {
    if (game.powerup) return;
    const type = POWERUP_KEYS[Math.floor(Math.random() * POWERUP_KEYS.length)];
    const c = emptyCell();
    game.powerup = { type, x: c.x, y: c.y, spawnAt: now };
  }
  function isActive(type) {
    return game.actives[type] && game.actives[type].expiresAt > performance.now();
  }
  function activatePowerup(type, now) {
    const cfg = POWERUPS[type];
    if (cfg.duration > 0) {
      game.actives[type] = { expiresAt: now + cfg.duration };
    } else if (type === 'shrink') {
      // Instant: cut length in half, minimum length 3.
      // The new head is already unshifted and step() will still pop the tail,
      // so compute from the pre-pickup length and keep one extra segment.
      const preLength = game.snake.length - 1;
      const keep = Math.max(3, Math.floor(preLength / 2)) + 1;
      game.snake.splice(keep);
    }
  }

  // ---------- Initialization ----------
  function resetGame() {
    game.snake = [
      { x: Math.floor(COLS / 2) - 1, y: Math.floor(ROWS / 2) },
      { x: Math.floor(COLS / 2) - 2, y: Math.floor(ROWS / 2) },
      { x: Math.floor(COLS / 2) - 3, y: Math.floor(ROWS / 2) },
    ];
    game.dir = { x: 1, y: 0 };
    game.queuedDir = { x: 1, y: 0 };
    game.score = 0;
    game.level = 1;
    game.foodEaten = 0;
    game.actives = {};
    game.particles = [];
    game.powerup = null;
    game.lastStep = performance.now();
    scheduleNextPowerup(game.lastStep);
    spawnFood();
    updateHUD();
    renderPowerTray();
  }

  function startGame() {
    resetGame();
    game.state = STATE.PLAYING;
    overlay.classList.remove('show');
    if (audio() && audio().state === 'suspended') audio().resume();
  }

  function gameOver() {
    game.state = STATE.GAMEOVER;
    saveHigh();
    sfxDeath();
    showOverlay({
      title: 'GAME OVER',
      subtitle: `Score ${game.score} · Length ${game.snake.length} · Level ${game.level}`,
      buttonLabel: 'PLAY AGAIN',
    });
  }

  function showOverlay({ title, subtitle, buttonLabel }) {
    const card = overlay.querySelector('.overlay-card');
    card.innerHTML = `
      <h1 class="title">${title}<span class="title-accent">${subtitle}</span></h1>
      <div class="legend">
        <h2>Best Score</h2>
        <p style="font-size: 28px; font-weight: 800; color: var(--accent); margin: 4px 0;">${game.high}</p>
      </div>
      <button id="startBtn" class="primary-btn" type="button">${buttonLabel}</button>
    `;
    overlay.classList.add('show');
    document.getElementById('startBtn').addEventListener('click', startGame, { once: true });
  }

  // ---------- HUD ----------
  function updateHUD() {
    scoreEl.textContent = game.score;
    levelEl.textContent = game.level;
    lengthEl.textContent = game.snake.length;
  }

  function renderPowerTray() {
    const now = performance.now();
    powerTray.innerHTML = '';
    for (const key of POWERUP_KEYS) {
      const active = game.actives[key];
      if (!active || active.expiresAt <= now) continue;
      const cfg = POWERUPS[key];
      const remaining = active.expiresAt - now;
      const pct = Math.max(0, Math.min(1, remaining / cfg.duration));
      const pill = document.createElement('div');
      pill.className = 'power-pill';
      pill.innerHTML = `
        <span class="chip ${cfg.cls}">${cfg.icon}</span>
        <span>${cfg.label}</span>
        <span class="timebar"><span class="timebar-fill" style="width:${pct * 100}%"></span></span>
      `;
      powerTray.appendChild(pill);
    }
  }

  // ---------- Tick / Update ----------
  function currentTickMs() {
    let ms = BASE_TICK_MS - (game.level - 1) * LEVEL_SPEEDUP_MS;
    if (isActive('bolt')) ms = Math.max(MIN_TICK_MS - 10, ms * 0.55);
    if (isActive('slow')) ms = ms * 1.7;
    return Math.max(MIN_TICK_MS, ms);
  }

  function step(now) {
    // Commit queued direction (prevents 180s within one tick)
    if (
      (game.queuedDir.x !== -game.dir.x || game.queuedDir.y !== -game.dir.y)
      && (game.queuedDir.x !== game.dir.x || game.queuedDir.y !== game.dir.y)
    ) {
      game.dir = game.queuedDir;
    }

    const head = game.snake[0];
    let nx = head.x + game.dir.x;
    let ny = head.y + game.dir.y;

    const invincible = isActive('shield');

    // Wall handling
    if (nx < 0 || nx >= COLS || ny < 0 || ny >= ROWS) {
      if (invincible) {
        nx = (nx + COLS) % COLS;
        ny = (ny + ROWS) % ROWS;
      } else {
        return gameOver();
      }
    }

    // Self collision
    // Skip tail because it will move out of the way unless we are eating.
    const willEat =
      (game.food && nx === game.food.x && ny === game.food.y) ||
      (game.powerup && nx === game.powerup.x && ny === game.powerup.y);

    for (let i = 0; i < game.snake.length; i++) {
      // If not eating, the tail will move, so skip last segment in collision check
      if (!willEat && i === game.snake.length - 1) continue;
      const s = game.snake[i];
      if (s.x === nx && s.y === ny) {
        if (!invincible) return gameOver();
        // When invincible, skip self-collision (passes through)
        break;
      }
    }

    // Move
    game.snake.unshift({ x: nx, y: ny });

    let grew = false;
    if (game.food && nx === game.food.x && ny === game.food.y) {
      const points = (game.food.bonus ? BONUS_FOOD_SCORE : FOOD_SCORE) * (isActive('star') ? 2 : 1);
      game.score += points;
      game.foodEaten += 1;
      grew = true;
      emitParticles(nx, ny, game.food.bonus ? '#ff5577' : '#6cf0c2', game.food.bonus ? 18 : 10);
      if (game.food.bonus) sfxBonus(); else sfxEat();
      // Level up
      const newLevel = 1 + Math.floor(game.foodEaten / LEVEL_THRESHOLD);
      if (newLevel > game.level) {
        game.level = newLevel;
        sfxLevelUp();
        flashScreen();
      }
      spawnFood();
    }

    if (game.powerup && nx === game.powerup.x && ny === game.powerup.y) {
      const type = game.powerup.type;
      emitParticles(nx, ny, POWERUPS[type].color, 20);
      activatePowerup(type, now);
      sfxPowerup();
      game.powerup = null;
      scheduleNextPowerup(now);
    }

    if (!grew) game.snake.pop();

    updateHUD();
  }

  // ---------- Particles (eye candy) ----------
  function emitParticles(cx, cy, color, count) {
    const px = (cx + 0.5) * CELL;
    const py = (cy + 0.5) * CELL;
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 1 + Math.random() * 3;
      game.particles.push({
        x: px,
        y: py,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1,
        color,
      });
    }
  }
  function updateParticles(dt) {
    for (let i = game.particles.length - 1; i >= 0; i--) {
      const p = game.particles[i];
      p.x += p.vx * dt * 60;
      p.y += p.vy * dt * 60;
      p.vx *= 0.92;
      p.vy *= 0.92;
      p.life -= dt * 1.6;
      if (p.life <= 0) game.particles.splice(i, 1);
    }
  }
  function drawParticles() {
    for (const p of game.particles) {
      ctx.globalAlpha = Math.max(0, p.life);
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3 * p.life, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // ---------- Rendering ----------
  function drawBackground() {
    // subtle gradient already on canvas via CSS, but draw grid lines on top
    ctx.fillStyle = '#070b1a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = 'rgba(102, 166, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= COLS; x++) {
      ctx.beginPath();
      ctx.moveTo(x * CELL + 0.5, 0);
      ctx.lineTo(x * CELL + 0.5, ROWS * CELL);
      ctx.stroke();
    }
    for (let y = 0; y <= ROWS; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * CELL + 0.5);
      ctx.lineTo(COLS * CELL, y * CELL + 0.5);
      ctx.stroke();
    }

    // border glow
    ctx.strokeStyle = isActive('shield') ? 'rgba(108, 240, 194, 0.7)' : 'rgba(102, 166, 255, 0.18)';
    ctx.lineWidth = 2;
    ctx.strokeRect(1, 1, canvas.width - 2, canvas.height - 2);
  }

  function drawFood() {
    if (!game.food) return;
    const f = game.food;
    const cx = (f.x + 0.5) * CELL;
    const cy = (f.y + 0.5) * CELL;
    const pulse = 0.5 + 0.5 * Math.sin(performance.now() / 200);
    const r = (CELL * 0.32) + pulse * 1.5;
    const color = f.bonus ? '#ff5577' : '#6cf0c2';

    // glow
    const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, CELL * 1.2);
    grd.addColorStop(0, color + 'cc');
    grd.addColorStop(1, color + '00');
    ctx.fillStyle = grd;
    ctx.fillRect((f.x - 1) * CELL, (f.y - 1) * CELL, CELL * 3, CELL * 3);

    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();

    if (f.bonus) {
      // sparkle
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(cx - r * 0.35, cy - r * 0.35, r * 0.25, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  function drawPowerup() {
    if (!game.powerup) return;
    const now = performance.now();
    const cfg = POWERUPS[game.powerup.type];
    const age = now - game.powerup.spawnAt;
    if (age > POWERUP_LIFETIME_MS) {
      game.powerup = null;
      scheduleNextPowerup(now);
      return;
    }
    // Blink as it nears expiry
    const remaining = POWERUP_LIFETIME_MS - age;
    if (remaining < 2000 && Math.floor(now / 120) % 2 === 0) return;

    const px = (game.powerup.x + 0.5) * CELL;
    const py = (game.powerup.y + 0.5) * CELL;
    const pulse = 0.5 + 0.5 * Math.sin(now / 180);

    const grd = ctx.createRadialGradient(px, py, 0, px, py, CELL * 1.5);
    grd.addColorStop(0, cfg.color + 'aa');
    grd.addColorStop(1, cfg.color + '00');
    ctx.fillStyle = grd;
    ctx.fillRect((game.powerup.x - 1) * CELL, (game.powerup.y - 1) * CELL, CELL * 3, CELL * 3);

    // rotating diamond
    ctx.save();
    ctx.translate(px, py);
    ctx.rotate(now / 600);
    ctx.fillStyle = cfg.color;
    const size = CELL * 0.32 + pulse * 2;
    ctx.beginPath();
    ctx.moveTo(0, -size);
    ctx.lineTo(size, 0);
    ctx.lineTo(0, size);
    ctx.lineTo(-size, 0);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    // icon
    ctx.fillStyle = '#0a0d20';
    ctx.font = `bold ${Math.floor(CELL * 0.55)}px system-ui`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(cfg.icon, px, py + 1);
  }

  function drawSnake() {
    const shield = isActive('shield');
    const star = isActive('star');
    const bolt = isActive('bolt');
    const slow = isActive('slow');

    let baseColor = '#6cf0c2';
    if (shield) baseColor = '#9efff0';
    else if (star) baseColor = '#b186ff';
    else if (bolt) baseColor = '#ffd86b';
    else if (slow) baseColor = '#66a6ff';

    // Draw body from tail to head so head sits on top
    for (let i = game.snake.length - 1; i >= 0; i--) {
      const s = game.snake[i];
      const x = s.x * CELL;
      const y = s.y * CELL;
      const t = i / Math.max(1, game.snake.length - 1); // 0 head -> 1 tail
      const r = CELL * 0.5 - 1;

      // Shimmer for active power-ups
      const shimmer = (shield || star || bolt || slow) ? (0.6 + 0.4 * Math.sin(performance.now() / 100 + i * 0.4)) : 1;

      ctx.fillStyle = blendColor(baseColor, '#1a2350', t * 0.55);
      ctx.globalAlpha = shimmer;
      roundRect(ctx, x + 1, y + 1, CELL - 2, CELL - 2, r * 0.4);
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    // Head highlight + eyes
    if (game.snake.length > 0) {
      const head = game.snake[0];
      const hx = head.x * CELL;
      const hy = head.y * CELL;
      ctx.fillStyle = '#ffffff';
      // eyes oriented to direction
      const ex1 = hx + CELL / 2 + game.dir.y * CELL * 0.18 - CELL * 0.1;
      const ey1 = hy + CELL / 2 + game.dir.x * CELL * 0.18 - CELL * 0.1;
      const ex2 = hx + CELL / 2 - game.dir.y * CELL * 0.18 - CELL * 0.1;
      const ey2 = hy + CELL / 2 - game.dir.x * CELL * 0.18 - CELL * 0.1;
      ctx.beginPath(); ctx.arc(ex1 + CELL * 0.1, ey1 + CELL * 0.1, CELL * 0.08, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(ex2 + CELL * 0.1, ey2 + CELL * 0.1, CELL * 0.08, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#04101a';
      ctx.beginPath(); ctx.arc(ex1 + CELL * 0.1 + game.dir.x * 1.5, ey1 + CELL * 0.1 + game.dir.y * 1.5, CELL * 0.04, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(ex2 + CELL * 0.1 + game.dir.x * 1.5, ey2 + CELL * 0.1 + game.dir.y * 1.5, CELL * 0.04, 0, Math.PI * 2); ctx.fill();
    }
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function blendColor(hexA, hexB, t) {
    const a = hexToRgb(hexA);
    const b = hexToRgb(hexB);
    const r = Math.round(a.r + (b.r - a.r) * t);
    const g = Math.round(a.g + (b.g - a.g) * t);
    const bl = Math.round(a.b + (b.b - a.b) * t);
    return `rgb(${r}, ${g}, ${bl})`;
  }
  function hexToRgb(hex) {
    const h = hex.replace('#', '');
    return {
      r: parseInt(h.substring(0, 2), 16),
      g: parseInt(h.substring(2, 4), 16),
      b: parseInt(h.substring(4, 6), 16),
    };
  }

  function drawPausedOverlay() {
    ctx.fillStyle = 'rgba(4, 6, 14, 0.65)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#6cf0c2';
    ctx.font = 'bold 36px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('PAUSED', canvas.width / 2, canvas.height / 2 - 10);
    ctx.fillStyle = '#8a91b4';
    ctx.font = '13px system-ui';
    ctx.fillText('Press SPACE to resume', canvas.width / 2, canvas.height / 2 + 24);
  }

  function flashScreen() {
    const flash = document.createElement('div');
    flash.className = 'flash fire';
    canvas.parentElement.appendChild(flash);
    setTimeout(() => flash.remove(), 240);
  }

  // ---------- Game loop ----------
  let lastFrame = performance.now();
  function loop(now) {
    const dt = Math.min(0.05, (now - lastFrame) / 1000);
    lastFrame = now;

    if (game.state === STATE.PLAYING) {
      // Schedule power-up spawn
      if (!game.powerup && now >= game.nextPowerupAt) {
        spawnPowerup(now);
      }
      // Expire stale power-up
      if (game.powerup && now - game.powerup.spawnAt > POWERUP_LIFETIME_MS) {
        game.powerup = null;
        scheduleNextPowerup(now);
      }

      // Snake step
      const tick = currentTickMs();
      while (now - game.lastStep >= tick) {
        game.lastStep += tick;
        step(now);
        if (game.state !== STATE.PLAYING) break;
      }

      updateParticles(dt);
    }

    // Draw
    drawBackground();
    drawFood();
    drawPowerup();
    drawSnake();
    drawParticles();

    if (game.state === STATE.PAUSED) drawPausedOverlay();

    renderPowerTray();

    requestAnimationFrame(loop);
  }

  // ---------- Input ----------
  const KEY_DIRS = {
    'ArrowUp':    { x: 0, y: -1 },
    'ArrowDown':  { x: 0, y: 1 },
    'ArrowLeft':  { x: -1, y: 0 },
    'ArrowRight': { x: 1, y: 0 },
    'w': { x: 0, y: -1 },
    's': { x: 0, y: 1 },
    'a': { x: -1, y: 0 },
    'd': { x: 1, y: 0 },
    'W': { x: 0, y: -1 },
    'S': { x: 0, y: 1 },
    'A': { x: -1, y: 0 },
    'D': { x: 1, y: 0 },
  };

  window.addEventListener('keydown', (e) => {
    if (KEY_DIRS[e.key]) {
      const d = KEY_DIRS[e.key];
      // Disallow direct 180-degree reversal
      if (d.x === -game.dir.x && d.y === -game.dir.y) return;
      game.queuedDir = d;
      e.preventDefault();
      return;
    }

    if (e.key === ' ' || e.code === 'Space') {
      if (game.state === STATE.PLAYING) {
        game.state = STATE.PAUSED;
      } else if (game.state === STATE.PAUSED) {
        game.state = STATE.PLAYING;
        game.lastStep = performance.now(); // avoid burst-catchup after unpause
      }
      e.preventDefault();
      return;
    }

    if (e.key === 'r' || e.key === 'R') {
      if (game.state !== STATE.IDLE) {
        startGame();
        e.preventDefault();
      }
    }
  });

  // Touch / swipe (basic)
  let touchStart = null;
  canvas.addEventListener('touchstart', (e) => {
    if (e.touches.length > 0) {
      touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  }, { passive: true });
  canvas.addEventListener('touchend', (e) => {
    if (!touchStart || !e.changedTouches[0]) return;
    const dx = e.changedTouches[0].clientX - touchStart.x;
    const dy = e.changedTouches[0].clientY - touchStart.y;
    if (Math.abs(dx) < 20 && Math.abs(dy) < 20) return;
    let dir;
    if (Math.abs(dx) > Math.abs(dy)) {
      dir = dx > 0 ? { x: 1, y: 0 } : { x: -1, y: 0 };
    } else {
      dir = dy > 0 ? { x: 0, y: 1 } : { x: 0, y: -1 };
    }
    if (!(dir.x === -game.dir.x && dir.y === -game.dir.y)) {
      game.queuedDir = dir;
    }
    touchStart = null;
  }, { passive: true });

  startBtn.addEventListener('click', startGame);

  // ---------- Boot ----------
  loadHigh();
  updateHUD();
  requestAnimationFrame(loop);

  // Expose minimal handle for debugging / tests
  window.SnakeGame = { game, start: startGame };
})();
