"""Smoke test for the pygame snapshot demo in ``tetris.demo``."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from tetris.demo import main
from tetris.state import GamePhase


def test_main_writes_one_snapshot_per_phase(tmp_path):
    rc = main([str(tmp_path)])
    assert rc == 0
    files = {p.name: p for p in tmp_path.glob("*.png")}
    assert len(files) == 4
    for phase in GamePhase:
        name = f"tetris_{phase.value}.png"
        assert name in files
        assert files[name].stat().st_size > 1024  # a real image, not a stub
