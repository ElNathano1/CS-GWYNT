"""Tests for Game Engine"""

import unittest
from backend.app.services.game_engine import GameEngine
from backend.app.models.player import Player
from backend.app.models.game import GameState


class TestGameEngine(unittest.TestCase):
    """Test cases for GameEngine"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = GameEngine()
        self.player1 = Player(1, "Alice")
        self.player2 = Player(2, "Bob")

    def test_create_game(self):
        """Test creating a game"""
        game = self.engine.create_game(1, self.player1)
        self.assertIsNotNone(game)
        self.assertEqual(game.player1.username, "Alice")
        self.assertEqual(game.state, GameState.WAITING)

    def test_join_game(self):
        """Test joining a game"""
        self.engine.create_game(1, self.player1)
        result = self.engine.join_game(1, self.player2)
        self.assertTrue(result)
        game = self.engine.get_game(1)
        self.assertEqual(game.state, GameState.PLAYING)

    def test_get_game(self):
        """Test retrieving a game"""
        self.engine.create_game(1, self.player1)
        game = self.engine.get_game(1)
        self.assertIsNotNone(game)
        self.assertEqual(game.id, 1)


if __name__ == "__main__":
    unittest.main()
