"""Shared pytest fixtures for the MoneyPoly white-box tests."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from moneypoly.game import Game


@pytest.fixture
def game_two_players():
    """A new two-player game (Alice and Bob)."""
    return Game(["Alice", "Bob"])
