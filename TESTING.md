# Testing Guide

Repo-wide test inventory: what is covered, how to run each suite, and what cannot be
tested in a Linux/CI environment and why.

## Quick start (run everything testable)

```bash
# one-time setup (Python is externally managed in the dev container)
pip install --break-system-packages "pygame>=2.5" "pytest>=7"

# Python suites (headless — no display/audio needed)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m pytest tetris modern_tetris -q

# Snake (zero-dependency Node harness, Node >= 18)
node snake_game/test.headless.js
```

## Project status

| Project | Stack | Tests | Status |
|---|---|---|---|
| `tetris/` | Python 3 + pygame | `tetris/tests/` (pytest) | ✅ tested, runs headless |
| `modern_tetris/` | Python 3 + pygame | `modern_tetris/tests/` (pytest) | ✅ tested, runs headless |
| `snake_game/` | Browser JS (no build) | `snake_game/test.headless.js` (Node, zero deps) | ✅ tested headless |
| `serendipity_django/` | Django 1.7.4 (2015, Python 2 era) | `api/tests.py` is an empty stub | ❌ untestable as-is (see below) |
| `google_place_api_search/` | Python script | none | ❌ untestable as-is (see below) |
| `serendipity_iOS/` | Xcode project (iOS + WatchKit) | `SerendipityTestTests/` | ⛔ requires macOS/Xcode |
| `Serendipity_V2/` | Xcode project (iOS + WatchKit) | `SerendipityTests/` | ⛔ requires macOS/Xcode |

## Untestable projects — details

**`serendipity_django/`** — pinned to Django 1.7.4 (`requirements.txt`), which does not run
on Python 3.12. Two modules are Python 2 *syntax* and fail to even parse on Python 3:
`google_searcher/GoogleSearcher.py` and `yelp_searcher/YelpSearcher.py` (bare `print`
statements). `api/views.py` and the project settings parse fine, but importing them pulls
in Django 1.7 + the py2 searcher modules. Testing this app means porting it (Python 3 +
modern Django) first — a rewrite, deliberately out of scope for this testing pass.

**`google_place_api_search/`** — parses on Python 3.12, but its only function performs a
live Google Places API call through the abandoned `python-google-places` package and
prints results; there is no separable pure logic to unit-test. Testing it would mean
mocking the entire third-party client to assert on `print` output, which verifies nothing
real. Document-only.

**`serendipity_iOS/`, `Serendipity_V2/`** — Xcode projects with WatchKit targets. Building
or running their test bundles requires macOS with Xcode; not possible in this Linux
container. Run via `xcodebuild test` on a Mac.

## ⚠️ Security: hardcoded credentials in legacy code

These credentials are committed in source (and present throughout git history). They are
from ~2015 and likely dead, but should be revoked and removed regardless:

- Google Places API key — `google_place_api_search/google_place_api_search.py:5` and
  `serendipity_django/google_searcher/GoogleSearcher.py:5` (same key).
- Yelp OAuth1 consumer key/secret + token/secret —
  `serendipity_django/yelp_searcher/YelpSearcher.py:31-34`.

## Suite details

### `tetris/` (pygame Tetris)

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m pytest tetris/tests -q
```

Covers board mechanics, tetromino rotation, 7-bag randomizer, scoring, game loop,
renderer (headless), and `main.py` integration.

### `modern_tetris/` (input + preview package)

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m pytest modern_tetris -q
```

Covers the DAS/ARR input controller and the `preview/` package (7-bag, NEXT queue,
ghost projection, rendering). Note the suites live in two places —
`modern_tetris/tests/` and `modern_tetris/preview/tests/` — so target the package
directory, not just `modern_tetris/tests/`.

### `snake_game/` (browser Snake)

```bash
node snake_game/test.headless.js
```

Zero-dependency harness: stubs browser globals (`document`, `canvas`, `AudioContext`,
`requestAnimationFrame`), loads `game.js`, and drives the game deterministically —
movement, food/growth, scoring, power-ups, collisions, state transitions.

The game itself is played by opening `snake_game/index.html` in a browser.
