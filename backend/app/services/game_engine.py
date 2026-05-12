"""Game Engine - Core game logic"""

from typing import Optional
from ..models.game import Game, GameState
from ..models.player import Player


class GameEngine:
    """Core game engine for managing game logic"""

    def __init__(self):
        self.games: dict = {}

    def create_game(self, game_id: int, player1: Player) -> Game:
        """Create a new game"""
        game = Game(game_id, player1)
        self.games[game_id] = game
        return game

    def join_game(self, game_id: int, player2: Player) -> bool:
        """Join an existing game"""
        if game_id not in self.games:
            return False

        game = self.games[game_id]
        if game.player2 is not None:
            return False

        game.player2 = player2
        game.start_game()
        return True

    def get_game(self, game_id: int) -> Optional[Game]:
        """Get game by ID"""
        return self.games.get(game_id)

    def play_turn(self, game_id: int) -> bool:
        """Execute a turn"""
        game = self.get_game(game_id)
        if not game or game.state != GameState.PLAYING:
            return False

        game.next_turn()
        return True

    def check_win_condition(self, game_id: int) -> bool:
        """Check if win condition is met"""
        game = self.get_game(game_id)
        if not game:
            return False

        # Check if player1 or player2 has 0 health
        if game.player1.health <= 0:
            game.end_game(game.player2)
            return True

        if game.player2.health <= 0:
            game.end_game(game.player1)
            return True

        return False
