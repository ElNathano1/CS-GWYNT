"""Game Model"""

from enum import Enum
from typing import Optional
from .player import Player


class GameState(str, Enum):
    """Game states"""

    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class Game:
    """Represents a game session"""

    def __init__(self, id: int, player1: Player, player2: Optional[Player] = None):
        self.id = id
        self.player1 = player1
        self.player2 = player2
        self.state = GameState.WAITING if player2 is None else GameState.PLAYING
        self.current_turn: int = 0
        self.winner: Optional[Player] = None

    def start_game(self) -> bool:
        """Start the game"""
        if self.player2 and self.state == GameState.WAITING:
            self.state = GameState.PLAYING
            return True
        return False

    def end_game(self, winner: Player) -> None:
        """End the game and set winner"""
        self.state = GameState.FINISHED
        self.winner = winner

    def get_current_player(self) -> Player:
        """Get the player whose turn it is"""
        return self.player1 if self.current_turn % 2 == 0 else self.player2

    def next_turn(self) -> None:
        """Move to next turn"""
        self.current_turn += 1

    def __repr__(self) -> str:
        return f"Game(id={self.id}, state={self.state}, turn={self.current_turn})"
