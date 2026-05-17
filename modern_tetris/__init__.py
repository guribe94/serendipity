"""Modern Tetris — Python package.

This package houses the modular subsystems of a modern Tetris build:
    - input:  player input and control subsystem (this module)
    - (game loop, piece preview, rendering — built by sibling modules)

The input subsystem is intentionally decoupled from any concrete game model.
It dispatches `Action` calls through a `GameController` Protocol so it can be
wired to whatever board/piece logic the game-loop module exposes.
"""
