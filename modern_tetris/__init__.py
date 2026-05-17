"""Modern Tetris — Python package.

This package houses the modular subsystems of a modern Tetris build that
are decoupled from the core gameplay engine (which lives in the
sibling :mod:`tetris` package):

* :mod:`modern_tetris.input` — player input and control subsystem
  (DAS/ARR auto-repeat, opposing-key takeover, soft/hard drop, rotation,
  hold, and pause; integrates via a ``GameController`` Protocol so it
  works with any board/piece backend).
* :mod:`modern_tetris.preview` — 7-bag randomizer, next-piece queue,
  ghost-piece calculation, spawn pipeline, and pygame renderer.

Each subpackage owns one concern of the game and is designed to be
developed and tested in parallel.
"""
